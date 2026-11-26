#!/usr/bin/env bash
# Run untrusted DeepDiff code (a PR's deepdiff/ and tests/) inside a bubblewrap sandbox,
# under strace, with canary credentials planted in a fake $HOME, then report anything
# suspicious the code did or tried to do.
#
# Usage: run-sandboxed.sh [options] SRC_DIR [-- PYTEST_ARGS...]
#
#   SRC_DIR            directory holding the untrusted deepdiff/, tests/ and (optionally) conftest.py.
#                      Nothing else from it is used: dependencies and pytest config come from the
#                      trusted checkout this script lives in (or from --deps-dir).
#   --deps-dir DIR     take uv.lock and pyproject.toml from DIR instead of the trusted checkout,
#                      e.g. ones extracted from an older commit of your own branch (sandbox-pr.sh
#                      --deps-from merge-base). DIR must never hold files from the PR.
#   --python VER       Python version for the sandbox venv (default: $PR_SANDBOX_PYTHON or 3.15)
#   --out DIR          where to put the work dir and reports (default: a new temp dir)
#   --fail-on LEVEL    critical|high|medium|low: findings at or above this fail the run (default: high)
#   --monitor-only     exit status reflects only the findings, not test failures (for CI)
#   --no-strace        skip syscall tracing (faster; detection then relies on the in-process audit hook)
#
# Environment:
#   PR_SANDBOX_SHARE_GROUP   group to make the reports readable by (default: ai-dev, if it exists
#                            and you're a member; "" disables)
#   PR_SANDBOX_SOURCE        what SRC_DIR was taken from, recorded in report/source.txt
#                            (sandbox-pr.sh sets it, e.g. "pr 618 <sha>" or "merge <sha> ...")
#
# Exit status: 2 if findings reached --fail-on, otherwise pytest's exit status (0 with --monitor-only).
#
# The sandbox: no network (own empty network namespace), own PID/IPC/UTS namespaces, read-only
# /usr and venv, a throwaway $HOME full of fake credentials, and only the copied sources writable.
# See scripts/pr_sandbox/README.md for the threat model and limits.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TRUSTED_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
DEPS_ROOT=$TRUSTED_ROOT
PYVER=${PR_SANDBOX_PYTHON:-3.15}
OUT=""
FAIL_ON=high
MONITOR_ONLY=0
USE_STRACE=1

die() { echo "run-sandboxed: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python) PYVER=$2; shift 2 ;;
        --deps-dir) DEPS_ROOT=$(cd "$2" && pwd); shift 2 ;;
        --out) OUT=$2; shift 2 ;;
        --fail-on) FAIL_ON=$2; shift 2 ;;
        --monitor-only) MONITOR_ONLY=1; shift ;;
        --no-strace) USE_STRACE=0; shift ;;
        -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
        --) die "SRC_DIR must come before --" ;;
        -*) die "unknown option $1" ;;
        *) break ;;
    esac
done
[[ $# -ge 1 ]] || die "missing SRC_DIR (see --help)"
SRC=$(cd "$1" && pwd); shift
if [[ $# -gt 0 ]]; then
    [[ $1 == "--" ]] || die "expected -- before pytest arguments"
    shift
fi
PYTEST_ARGS=("$@")
[[ ${#PYTEST_ARGS[@]} -gt 0 ]] || PYTEST_ARGS=(tests)

[[ -d $SRC/deepdiff && -d $SRC/tests ]] || die "$SRC must contain deepdiff/ and tests/"
[[ -f $DEPS_ROOT/uv.lock && -f $DEPS_ROOT/pyproject.toml ]] || die "$DEPS_ROOT must contain uv.lock and pyproject.toml"
for tool in bwrap uv python3; do command -v "$tool" >/dev/null || die "$tool is required"; done
if [[ $USE_STRACE == 1 ]]; then command -v strace >/dev/null || die "strace is required (or pass --no-strace)"; fi

if [[ -z $OUT ]]; then OUT=$(mktemp -d "${TMPDIR:-/tmp}/deepdiff-pr-sandbox.XXXXXX"); fi
mkdir -p "$OUT"
WORK=$(cd "$OUT" && pwd)
[[ -z $(ls -A "$WORK") ]] || die "--out directory $WORK must be empty"
mkdir -p "$WORK"/{src,home,audit,etc,report}
REPORT=$WORK/report
echo "==> work dir: $WORK"
[[ -z ${PR_SANDBOX_SOURCE:-} ]] || printf '%s\n' "$PR_SANDBOX_SOURCE" >"$REPORT/source.txt"

# Make the reports readable by a shared group, e.g. so an agent running as another user can
# read them. Defaults to "ai-dev" if that group exists and you're in it. Set
# PR_SANDBOX_SHARE_GROUP to another group, or to "" to turn this off.
SHARE_GROUP=${PR_SANDBOX_SHARE_GROUP-ai-dev}
share_reports() {
    [[ -n $SHARE_GROUP ]] || return 0
    getent group "$SHARE_GROUP" >/dev/null || return 0
    id -nG | tr ' ' '\n' | grep -qx -- "$SHARE_GROUP" || return 0
    # The work dir itself only needs traverse+list; src/ and home/ stay private.
    chgrp "$SHARE_GROUP" "$WORK" && chmod g+rx "$WORK" || return 0
    local d
    for d in "$REPORT" "$WORK/audit"; do
        chgrp -R "$SHARE_GROUP" "$d" && chmod -R g+rX "$d" || true
    done
    echo "==> reports shared with group $SHARE_GROUP"
}
trap share_reports EXIT

# ---------------------------------------------------------------------------
# 1. Dependencies: from the TRUSTED lockfile only (the PR's pyproject.toml/uv.lock are never
#    read), hash-checked, cached per lockfile+Python version. This is exactly what your normal
#    `uv sync` installs, so building an sdist here (e.g. pyyaml on a new Python) is no new risk.
# ---------------------------------------------------------------------------
REQ=$WORK/requirements.txt
[[ $DEPS_ROOT == "$TRUSTED_ROOT" ]] || echo "==> dependencies and pytest config from $DEPS_ROOT"
(cd "$DEPS_ROOT" && uv export --quiet --frozen --no-emit-project \
    --extra cli --extra dev --extra static --extra test --extra coverage -o "$REQ")
KEY=$( (cat "$REQ"; echo "$PYVER") | sha256sum | cut -c1-16)
CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/deepdiff-pr-sandbox
VENV=$CACHE/venv-$PYVER-$KEY
if [[ ! -f $VENV/.complete ]]; then
    echo "==> building sandbox venv (python $PYVER) in $VENV"
    rm -rf "$VENV"
    mkdir -p "$CACHE"
    uv venv --quiet --python "$PYVER" "$VENV"
    uv pip install --quiet --python "$VENV/bin/python" --require-hashes -r "$REQ" ||
        die "installing dependencies failed. An older lockfile (--deps-dir) may have no wheels for python $PYVER: try an older --python"
    # Pre-compile so nothing tries to write bytecode into the read-only venv mount.
    "$VENV/bin/python" -I -m compileall -q -j 0 "$VENV/lib" >/dev/null || true
    touch "$VENV/.complete"
fi
# Trusted interpreter, no untrusted code on its path: safe to ask it where it lives.
BASE_PREFIX=$("$VENV/bin/python" -I -c 'import sys; print(sys.base_prefix)')
BASE_PREFIX_REAL=$(realpath "$BASE_PREFIX")
# The venv's python symlink may point through a symlinked prefix (uv makes e.g.
# cpython-3.15-... -> cpython-3.15.2-...); that path has to exist inside the sandbox too.
PY_LINK_PREFIX=$(dirname "$(dirname "$(readlink "$VENV/bin/python")")")

# ---------------------------------------------------------------------------
# 2. Untrusted sources. Only deepdiff/, tests/ and conftest.py are taken from the PR;
#    pyproject.toml (pytest config) comes from the trusted checkout (or --deps-dir).
# ---------------------------------------------------------------------------
cp -a "$SRC/deepdiff" "$SRC/tests" "$WORK/src/"
[[ -f $SRC/conftest.py ]] && cp -a "$SRC/conftest.py" "$WORK/src/"
cp "$DEPS_ROOT/pyproject.toml" "$WORK/src/pyproject.toml"

# ---------------------------------------------------------------------------
# 3. Fake home with canary credentials. It's mounted at the real $HOME path so the
#    sandbox looks like a developer machine. Any access to these files is reported.
# ---------------------------------------------------------------------------
TOKEN=$(python3 -I -c 'import secrets; print(secrets.token_hex(10))')
CANARY="PR-SANDBOX-CANARY-$TOKEN"
H=$WORK/home
canary() { mkdir -p "$(dirname "$H/$1")"; printf '%s\n' "$2" > "$H/$1"; }
canary .ssh/id_ed25519 "-----BEGIN OPENSSH PRIVATE KEY-----
$CANARY
-----END OPENSSH PRIVATE KEY-----"
canary .ssh/id_ed25519.pub "ssh-ed25519 AAAA$TOKEN $USER@$(hostname)"
canary .ssh/known_hosts "github.com ssh-ed25519 AAAA$TOKEN"
canary .aws/credentials "[default]
aws_access_key_id = AKIA${TOKEN:0:16}
aws_secret_access_key = $CANARY"
canary .pypirc "[pypi]
username = __token__
password = pypi-$CANARY"
canary .netrc "machine github.com login x password $CANARY"
canary .git-credentials "https://x:$CANARY@github.com"
canary .config/gh/hosts.yml "github.com:
    oauth_token: gho_$TOKEN
    user: x"
canary .docker/config.json "{\"auths\": {\"ghcr.io\": {\"auth\": \"$CANARY\"}}}"
canary .kube/config "users: [{name: x, user: {token: $CANARY}}]"
canary .claude.json "{\"oauthAccount\": {\"token\": \"$CANARY\"}}"
canary .claude/.credentials.json "{\"claudeAiOauth\": {\"accessToken\": \"$CANARY\"}}"
canary .bash_history "export GITHUB_TOKEN=ghp_$TOKEN"
canary .zsh_history "export PYPI_TOKEN=pypi-$CANARY"
canary .bashrc "# canary"
canary .zshrc "# canary"
canary .profile "# canary"
mkdir -p "$H/.gnupg" "$H/.local/bin"
chmod 700 "$H/.ssh" "$H/.gnupg"
chmod 600 "$H/.ssh/id_ed25519"

# Minimal /etc/passwd and /etc/group so the sandbox user has a name and the expected home.
printf '%s:x:%s:%s::%s:/bin/bash\n' "$(id -un)" "$(id -u)" "$(id -g)" "$HOME" > "$WORK/etc/passwd"
printf '%s:x:%s:\n' "$(id -gn)" "$(id -g)" > "$WORK/etc/group"

python3 -I "$SCRIPT_DIR/analyze.py" snapshot "$H" "$REPORT/home-before.json"

# ---------------------------------------------------------------------------
# 4. The sandbox.
# ---------------------------------------------------------------------------
BWRAP=(bwrap
    --unshare-all              # user, pid, net, ipc, uts, cgroup namespaces: no network at all
    --die-with-parent
    --new-session              # no controlling terminal: blocks TIOCSTI keystroke injection
    --hostname "$(hostname)"
    --ro-bind /usr /usr
    --proc /proc
    --dev /dev
    --tmpfs /tmp
    --tmpfs /var/tmp
    --ro-bind-try /etc/ld.so.cache /etc/ld.so.cache
    --ro-bind-try /etc/localtime /etc/localtime
    --ro-bind-try /sys/devices/system/cpu /sys/devices/system/cpu
    --ro-bind "$WORK/etc/passwd" /etc/passwd
    --ro-bind "$WORK/etc/group" /etc/group
    --bind "$H" "$HOME"        # before the venv/interpreter binds, which may live under $HOME
    --ro-bind "$VENV" "$VENV"
    --ro-bind "$SCRIPT_DIR/audit" /opt/pr-sandbox
    --bind "$WORK/src" /work
    --bind "$WORK/audit" /audit
    --chdir /work
)
for d in /bin /sbin /lib /lib32 /lib64 /libx32; do
    if [[ -L $d ]]; then BWRAP+=(--symlink "$(readlink "$d")" "$d")
    elif [[ -d $d ]]; then BWRAP+=(--ro-bind "$d" "$d"); fi
done
for p in $(printf '%s\n' "$BASE_PREFIX" "$BASE_PREFIX_REAL" "$PY_LINK_PREFIX" | sort -u); do
    case "$p" in /usr|/usr/*|.) ;; *) BWRAP+=(--ro-bind "$(realpath "$p")" "$p") ;; esac
done

# Canary environment variables: code that harvests os.environ finds these, and its
# attempt to send them anywhere shows up as a network finding.
ENV=(env -i
    PATH="$VENV/bin:/usr/bin:/bin"
    HOME="$HOME" USER="$(id -un)" LOGNAME="$(id -un)" LANG=C.UTF-8 TERM=dumb
    PYTHONPATH=/opt/pr-sandbox:/work
    PYTHONDONTWRITEBYTECODE=1
    PR_SANDBOX_AUDIT_LOG=/audit/events.jsonl
    PR_SANDBOX_SRC_ROOT=/work
    AWS_ACCESS_KEY_ID="AKIA${TOKEN:0:16}" AWS_SECRET_ACCESS_KEY="$CANARY"
    GITHUB_TOKEN="ghp_$TOKEN" PYPI_API_TOKEN="pypi-$CANARY" ANTHROPIC_API_KEY="sk-ant-$CANARY"
)

TRACE=()
if [[ $USE_STRACE == 1 ]]; then
    TRACE=(strace -f -qq -tt -y -s 256 --seccomp-bpf -e signal=none
        -e trace=%file,%network,%process,ptrace,process_vm_readv,process_vm_writev,mount,umount2,pivot_root,chroot,unshare,setns,bpf,init_module,finit_module,kexec_load,perf_event_open,keyctl,add_key,request_key,open_by_handle_at,userfaultfd
        -o "$REPORT/strace.log")
fi

echo "==> running: pytest ${PYTEST_ARGS[*]}  (sandboxed${TRACE:+, traced})"
# The test output is attacker-controlled: strip control characters (ANSI escapes, \r)
# before it reaches the terminal. The raw output is kept in the report dir.
set +e
"${ENV[@]}" "${TRACE[@]}" "${BWRAP[@]}" \
    "$VENV/bin/python" -m pytest -p no:cacheprovider --color=no --benchmark-disable "${PYTEST_ARGS[@]}" \
    </dev/null 2>&1 | tee "$REPORT/pytest-output.raw" | LC_ALL=C tr -d '\000-\010\013-\037\177'
PYTEST_RC=${PIPESTATUS[0]}
set -e

# ---------------------------------------------------------------------------
# 5. Analysis (trusted code reading untrusted logs).
# ---------------------------------------------------------------------------
python3 -I "$SCRIPT_DIR/analyze.py" snapshot "$H" "$REPORT/home-after.json"
echo
echo "==> pytest exit status: $PYTEST_RC"
set +e
python3 -I "$SCRIPT_DIR/analyze.py" report \
    ${TRACE:+--strace "$REPORT/strace.log"} \
    --audit "$WORK/audit/events.jsonl" \
    --home "$HOME" --src-root /work \
    --allow-root "$VENV" --allow-root "$BASE_PREFIX" --allow-root "$BASE_PREFIX_REAL" --allow-root "$PY_LINK_PREFIX" \
    --home-before "$REPORT/home-before.json" --home-after "$REPORT/home-after.json" \
    --markdown "$REPORT/report.md" --json "$REPORT/findings.json" --fail-on "$FAIL_ON"
ANALYZE_RC=$?
set -e
echo "==> reports: $REPORT"

if [[ $ANALYZE_RC == 2 ]]; then
    echo "==> SUSPICIOUS BEHAVIOUR DETECTED (findings at or above '$FAIL_ON'). Review before trusting this PR." >&2
    exit 2
elif [[ $ANALYZE_RC != 0 ]]; then
    die "analyzer failed (exit $ANALYZE_RC)"
fi
[[ $MONITOR_ONLY == 1 ]] && exit 0
exit "$PYTEST_RC"
