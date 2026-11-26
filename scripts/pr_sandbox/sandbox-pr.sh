#!/usr/bin/env bash
# Review and test a GitHub PR without running its code on your machine.
#
# Usage: sandbox-pr.sh [--remote NAME] [--base BRANCH] [--deps-from WHERE] [--ref REF] [--yes]
#                      [RUN_OPTIONS...] PR_NUMBER [-- PYTEST_ARGS...]
#
#   --remote NAME   git remote of the upstream repo (default: origin)
#   --base BRANCH   branch the PR targets (default: dev)
#   --deps-from WHERE
#                   checkout (default): dependencies (uv.lock) and pytest config (pyproject.toml)
#                   come from this checkout.
#                   merge-base: they come from the merge-base of the PR with BRANCH, i.e. the
#                   commit of your own branch the PR was built on. Use it for stale PRs whose
#                   code still needs dependencies the current branch has dropped. It's as
#                   trusted as the checkout: that commit is in BRANCH's history, not the PR's.
#   --ref REF       test this local merge commit instead of the PR head: the PR merged with
#                   BASE, as made by merge-pr.py (make pr-merge). Its first parent must be the
#                   PR's current head and its second parent a commit on BASE. The triage still
#                   shows the PR's own changes, plus the files changed on both sides.
#   --yes           don't stop for confirmation after showing the risky-file diff
#   RUN_OPTIONS     passed through to run-sandboxed.sh (--python, --out, --fail-on, --no-strace)
#
# What it does:
#   1. Fetches the PR's commits into refs/pr-sandbox/<N> (just objects: no checkout, no hooks).
#   2. Shows which files changed, which of them will NOT be run, and the full diff of
#      "risky" files (build config, test harness, CI, agent config, pickles), with control
#      characters stripped so the diff can't hide lines or inject terminal escapes.
#   3. After you confirm, extracts only the PR's deepdiff/, tests/ and conftest.py and runs
#      them with run-sandboxed.sh (bubblewrap + strace + canary credentials + audit hook).
#
# Run this from your own trusted checkout (e.g. dev), never from inside a PR checkout:
# this script, the lockfile and the pytest config are all taken from where it lives
# (or, with --deps-from merge-base, from your own branch's history).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)
REMOTE=origin
BASE=dev
DEPS_FROM=checkout
TEST_REF=""
YES=0
RUN_OPTS=()

die() { echo "sandbox-pr: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --remote) REMOTE=$2; shift 2 ;;
        --base) BASE=$2; shift 2 ;;
        --deps-from) DEPS_FROM=$2; shift 2 ;;
        --yes) YES=1; shift ;;
        --python|--out|--fail-on) RUN_OPTS+=("$1" "$2"); shift 2 ;;
        --no-strace) RUN_OPTS+=("$1"); shift ;;
        --ref) TEST_REF=$2; shift 2 ;;
        -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
        -*) die "unknown option $1" ;;
        *) break ;;
    esac
done
[[ $DEPS_FROM == checkout || $DEPS_FROM == merge-base ]] || die "--deps-from must be checkout or merge-base"
[[ -z $TEST_REF || $DEPS_FROM == checkout ]] || die "--deps-from merge-base doesn't apply to a merge (--ref): it has the current dependencies"
[[ $# -ge 1 && $1 =~ ^[0-9]+$ ]] || die "usage: sandbox-pr.sh [options] PR_NUMBER [-- PYTEST_ARGS...]"
PR=$1; shift
PYTEST_PASSTHRU=("$@")   # empty, or "--" followed by pytest args

# Keep in sync with .github/labeler.yml.
RISKY=(
    ':(glob)pyproject.toml' ':(glob)uv.lock' ':(glob)setup.py' ':(glob)setup.cfg' ':(glob)**/requirements*.txt'
    ':(glob)noxfile.py' ':(glob)tox.ini' ':(glob)Makefile' ':(glob)mypy.ini' ':(glob)pyrightconfig.json*'
    ':(glob).pre-commit-config.yaml' ':(glob)MANIFEST.in'
    ':(glob)**/conftest.py' ':(glob)pytest.ini' ':(glob)**/*.pickle' ':(glob)**/*.pkl'
    ':(glob).github/**' ':(glob).claude/**' ':(glob)**/CLAUDE.md' ':(glob)**/AGENTS.md' ':(glob)**/CLAUDE.local.md'
    ':(glob).mcp.json' ':(glob).cursor/**' ':(glob).cursorrules' ':(glob).vscode/**' ':(glob).idea/**'
    ':(glob).envrc*' ':(glob).direnvrc*' ':(glob).gitattributes' ':(glob).gitmodules' ':(glob)scripts/**'
)
# Strip control characters (ANSI escapes, \r, backspaces...) from attacker-controlled text.
sanitize() { LC_ALL=C sed -e 's/[\x00-\x08\x0b-\x1f\x7f]/?/g'; }
G=(git -C "$REPO" -c core.quotePath=true)

PR_REF=refs/pr-sandbox/$PR
BASE_REF=refs/pr-sandbox/$PR-base
echo "==> fetching PR #$PR and $REMOTE/$BASE"
"${G[@]}" fetch --quiet --no-tags "$REMOTE" "+refs/pull/$PR/head:$PR_REF" "+refs/heads/$BASE:$BASE_REF"
MB=$("${G[@]}" merge-base "$BASE_REF" "$PR_REF")
HEAD_SHA=$("${G[@]}" rev-parse "$PR_REF")
TEST_SHA=$HEAD_SHA
if [[ -n $TEST_REF ]]; then
    TEST_SHA=$("${G[@]}" rev-parse --verify -q "$TEST_REF^{commit}") || die "--ref $TEST_REF is not a commit"
    read -r -a PARENTS <<<"$("${G[@]}" rev-list --parents -n1 "$TEST_SHA")"
    [[ ${#PARENTS[@]} == 3 && ${PARENTS[1]} == "$HEAD_SHA" ]] ||
        die "--ref $TEST_REF isn't a merge on top of PR #$PR's current head $HEAD_SHA (did the PR get new commits? run make pr-merge again)"
    "${G[@]}" merge-base --is-ancestor "${PARENTS[2]}" "$BASE_REF" ||
        die "--ref $TEST_REF: its second parent ${PARENTS[2]} is not on $BASE"
fi

echo
echo "==> PR #$PR head $HEAD_SHA, compared against merge-base $MB with $BASE"
echo "==> commits:"
"${G[@]}" log --no-color --format='  %h %an: %s' "$MB..$PR_REF" | sanitize
if [[ $TEST_SHA != "$HEAD_SHA" ]]; then
    echo
    echo "==> testing merge commit $TEST_SHA: the PR merged with $BASE ${PARENTS[2]}"
    echo "==> files changed on both sides (merged automatically or by conflict resolution):"
    "${G[@]}" diff-tree --no-commit-id --cc --name-only "$TEST_SHA" | sanitize | sed 's/^/  /'
fi
echo
echo "==> changed files:"
"${G[@]}" diff --no-color --no-ext-diff --no-renames --name-status "$MB" "$PR_REF" | sanitize | sed 's/^/  /'

echo
echo "==> changed files that will NOT be run (only deepdiff/, tests/ and conftest.py go into the sandbox):"
"${G[@]}" diff --no-color --no-ext-diff --no-renames --name-only "$MB" "$PR_REF" \
    -- . ':(exclude)deepdiff/**' ':(exclude)tests/**' ':(exclude)conftest.py' | sanitize | sed 's/^/  /'

RISKY_FILES=$("${G[@]}" diff --no-color --no-ext-diff --no-renames --name-only "$MB" "$PR_REF" -- "${RISKY[@]}" | sanitize)
echo
if [[ -n $RISKY_FILES ]]; then
    echo "==> RISKY files changed (review these yourself; the diff opens in a pager):"
    sed 's/^/  ! /' <<<"$RISKY_FILES"
    if [[ -t 1 ]]; then
        read -r -p "Press Enter to view the diff of the risky files..." _ </dev/tty
        "${G[@]}" diff --no-color --no-ext-diff --no-textconv --stat --patch "$MB" "$PR_REF" -- "${RISKY[@]}" \
            | sanitize | less
    else
        "${G[@]}" diff --no-color --no-ext-diff --no-textconv --stat --patch "$MB" "$PR_REF" -- "${RISKY[@]}" | sanitize
    fi
else
    echo "==> no risky files changed"
fi

if [[ $YES != 1 ]]; then
    [[ -t 0 ]] || die "not a terminal: pass --yes to run without confirmation"
    what="PR #$PR's"; [[ $TEST_SHA == "$HEAD_SHA" ]] || what="the merge's (PR #$PR + $BASE)"
    read -r -p "Run $what deepdiff/ and tests/ in the sandbox? [y/N] " answer
    [[ $answer == [yY]* ]] || { echo "aborted"; exit 1; }
fi

SRC=$(mktemp -d "${TMPDIR:-/tmp}/deepdiff-pr-$PR-src.XXXXXX")
DEPS=""
trap 'rm -rf "$SRC" ${DEPS:+"$DEPS"}' EXIT
PATHS=(deepdiff tests)
"${G[@]}" cat-file -e "$TEST_SHA:conftest.py" 2>/dev/null && PATHS+=(conftest.py)
"${G[@]}" archive --format=tar "$TEST_SHA" -- "${PATHS[@]}" | tar -x -C "$SRC"

if [[ $DEPS_FROM == merge-base ]]; then
    # Only from the merge-base, which is in BASE's history. Never from the PR's commits.
    DEPS=$(mktemp -d "${TMPDIR:-/tmp}/deepdiff-pr-$PR-deps.XXXXXX")
    for f in uv.lock pyproject.toml; do
        "${G[@]}" show "$MB:$f" >"$DEPS/$f" 2>/dev/null || die "merge-base $MB has no $f"
    done
    RUN_OPTS+=(--deps-dir "$DEPS")
    echo
    echo "==> dependencies and pytest config from merge-base $("${G[@]}" log -1 --format='%h (%ad)' --date=short "$MB")"
fi

if [[ $TEST_SHA == "$HEAD_SHA" ]]; then
    export PR_SANDBOX_SOURCE="pr $PR $HEAD_SHA"
else
    export PR_SANDBOX_SOURCE="merge $TEST_SHA of pr $PR $HEAD_SHA and $BASE ${PARENTS[2]}"
fi
echo
"$SCRIPT_DIR/run-sandboxed.sh" "${RUN_OPTS[@]}" "$SRC" "${PYTEST_PASSTHRU[@]}"
