# Reviewing untrusted PRs safely

Running a PR's tests means running the PR's code. These tools help you do that without
handing it your SSH keys, PyPI token or shell config, and they tell you if it tried.

## Quick start (Linux)

Requirements: `bwrap` (bubblewrap), `strace`, `uv`, `python3`. On Ubuntu:
`sudo apt install bubblewrap strace`.

The usual flow, from your own `dev` checkout:

```bash
make pr-sandbox PR=612      # triage risky files, then run the PR's tests in the sandbox
make pr-review  PR=612      # start Claude on the PR and its sandbox report, auto mode locked out
make pr-clean               # delete fetched PR refs and sandbox work dirs
```

For a stale PR (one that conflicts with `dev`, or whose contributor won't rebase), use
`make pr-merge` instead of `make pr-sandbox`. It merges `dev` into the PR and tests the merge.
See [Stale PRs: `make pr-merge`](#stale-prs-make-pr-merge):

```bash
make pr-merge   PR=618      # merge dev into the PR, AI-resolve conflicts, you review, then sandbox
make pr-review  PR=618      # same review, plus the conflict resolution
make pr-push    PR=618      # push the merge to the PR's branch (asks first)
```

`make pr-review` runs your `claude` command from an interactive zsh, so a zshrc wrapper
(e.g. one that switches user) is used. It needs that wrapper to pass its arguments through
and keep the current directory. It starts Claude in `dontAsk` mode with
`--settings scripts/pr_sandbox/review-settings.json`, and adds the sandbox work dir with `--add-dir`:
- reading and searching the repo and the report, read-only commands, and
  `gh pr view/diff/checks` run **without prompts**
- anything else is **refused automatically** instead of asking you, and running code
  (`python`, `pytest`, `uv`, `make`...), network (`curl`, `gh api`, web fetches), edits and
  PR-changing `gh` commands are denied outright
- auto and bypass modes are disabled for the session
- a hook (`review-guard.py`) blocks every tool call if the session is ever in auto or bypass
  mode

The initial prompt comes from `review-prompt.md`. Nothing is written to
`.claude/settings.local.json`, so your other sessions keep their mode. Options:
`BASE=master`, `TESTS="tests/test_x.py -x"`, `DEPS=merge-base`, `OPTS="--fail-on medium"`,
`CLAUDE_CMD=...`.

The scripts can also be run directly:

```bash
# From YOUR checkout (dev or master), never from inside a PR checkout:
scripts/pr_sandbox/sandbox-pr.sh 660                     # review risky files, then run the tests
scripts/pr_sandbox/sandbox-pr.sh 660 -- tests/test_tsv.py -x
scripts/pr_sandbox/sandbox-pr.sh --base master 661       # PR targeting master
scripts/pr_sandbox/sandbox-pr.sh --deps-from merge-base 618  # stale PR: deps from its merge-base
scripts/pr_sandbox/merge-pr.py merge 618                # stale PR: merge dev into it, then sandbox
scripts/pr_sandbox/run-sandboxed.sh path/to/src          # any directory with deepdiff/ + tests/
```

Exit status: `2` means suspicious behaviour was found. Otherwise it's pytest's exit status.
Reports are written to the `report/` dir that the output names: `report.md`, `findings.json`,
`strace.log`, the audit log and the raw pytest output.

## What happens

1. **Fetch without checkout.** The PR's commits go into `refs/pr-sandbox/<N>`. Nothing is
   checked out, so no `.envrc`, `.claude/settings.json` or other config from the PR is loaded.
   Delete these refs when you're done:
   `git for-each-ref --format='%(refname)' refs/pr-sandbox | xargs -n1 git update-ref -d`.
2. **Triage.** The script shows the changed files, which of them will not be run, and the
   full diff of *risky* files: build config, `conftest.py`, pickles, CI, agent config (`CLAUDE.md`,
   `AGENTS.md`, `.claude/`), `.envrc` and `scripts/`. Control characters are stripped, so a diff
   can't hide lines with `\r` or ANSI escapes. Read these diffs yourself.
3. **Run only what's needed.** Only `deepdiff/`, `tests/` and `conftest.py` come from the PR.
   Dependencies are installed from *your* `uv.lock` (hash-checked), and the pytest config comes
   from *your* `pyproject.toml`. The PR's build backend, `noxfile.py` and dependency changes
   never run.

   An old PR's `deepdiff/` can still import a dependency that your branch has since dropped
   (e.g. `cachebox`), so its tests fail at import. Use `make pr-merge` (see below) to test it
   merged with your branch.
4. **Sandbox** (`bwrap`):
   - no network (an empty network namespace)
   - its own PID/IPC/UTS namespaces and no controlling terminal (`--new-session` blocks
     `TIOCSTI` keystroke injection)
   - read-only `/usr` and venv
   - a throwaway `$HOME`
   - only the copied sources, `/tmp` and `/var/tmp` are writable
5. **Monitoring.** Three independent signals:
   - **strace (outside the sandbox, tamper-proof).** Every file, network, process and
     privileged syscall made by every process in the sandbox, including attempts that fail.
   - **Canaries.** The fake `$HOME` holds realistic fake credentials (`~/.ssh/id_ed25519`,
     `~/.aws/credentials`, `~/.pypirc`, `~/.config/gh/hosts.yml`, `~/.claude.json`, shell
     history...), and the environment holds fake `GITHUB_TOKEN`/`AWS_*`/`PYPI_API_TOKEN`
     values. Code that harvests secrets finds something worth sending, so its exfiltration
     attempt shows up as a network finding. A before/after hash of `$HOME` catches persistence
     (`~/.zshrc`, `.pth` files, `~/.local/bin`, `authorized_keys`).
   - **Python audit hook** (`audit/sitecustomize.py`, PEP 578). Records `open`, socket, DNS,
     `subprocess`/`os.system`, `ctypes`, dangerous `pickle` globals and `exec`/`compile` from PR
     code. It adds the PR file and line (`tests/conftest.py:11`), which strace can't. It runs
     in-process, so treat it as best-effort. The analyzer notices when Python was started in a
     way that skips it (`-I`/`-E`/`-S`).
6. **Analysis** (`analyze.py`) applies a policy and ranks findings:
   - **CRITICAL:** touching credentials, writing persistence files
   - **HIGH:** network attempts (including DNS), unexpected programs, writes outside the
     sandbox dirs, reads of other users' files, `/proc/*/environ`, `ptrace`/`mount`/`bpf`,
     dangerous pickles
   - **MEDIUM:** other `$HOME` access, `ctypes`/`exec` from PR code, suspicious imports
   - **LOW:** informational

A clean run of the current test suite has no MEDIUM or higher findings. Its LOW findings are
known helpers such as pytest-benchmark calling `git`/`hg` and `platform` calling `file`. If a
legitimate change trips a rule, add to the allowlists at the top of `analyze.py` with a comment
explaining why. Don't loosen the rules to make a PR pass.

## Stale PRs: `make pr-merge`

When a PR has gone stale (it conflicts with `dev`, or its code still needs a dependency `dev`
has dropped) and the contributor won't rebase it, bring it up to date yourself:

```bash
make pr-merge PR=618        # BASE=master for PRs to master
```

It goes through six numbered steps and says at each one what it's doing and what it needs
from you:

1. **Fetch** the PR and `dev` into `refs/pr-sandbox/` (no checkout).
2. **Merge `dev` into the PR in memory** with `git merge-tree`. Nothing is checked out, so none
   of the PR's files (`.envrc`, `.claude/`, `CLAUDE.md`, hooks) land in a working tree. A merge
   (rather than a rebase) keeps the contributor's commits as they are, so it can be pushed to
   their branch as a fast-forward.
3. **Resolve conflicts with a locked-down Claude agent.** Only copies of the conflicted files
   go into a scratch dir, renamed to `conflicts/NN.txt` (so a conflicted `CLAUDE.md` or
   `.claude/settings.json` is never loaded as config), along with each side's diff and commit
   subjects. The agent runs with `claude -p --restricted --tools Read,Edit,Write,Glob,Grep
   --strict-mcp-config`: no shell, no web, no MCP connectors, user and project settings ignored.
   A guard hook (`merge-guard.py`) confines its reads to the scratch dir and its writes to
   `conflicts/*` and `notes.md`, and logs every call. Before using the result, `merge-pr.py`
   checks the session's reported tools, MCP servers and permission mode, and checks that the
   guard saw every tool call. If anything doesn't match, it stops. The prompt is
   `merge-prompt.md`.
4. **Review.** For each conflict you see the PR's side, `dev`'s side and the resolution, plus
   the agent's notes. Lines the agent starts with `UNCERTAIN:` or `SUSPICIOUS:`, leftover
   markers and edits outside the conflict blocks are flagged. `[a]ccept`, `[e]dit` (your
   `$EDITOR`, with vim modelines off), `[d]iff` against `dev`, or `[q]uit`. Nothing is
   committed before you accept.
5. **Commit** the merge straight to git objects (first parent: the PR head; second: `dev`) as
   `refs/pr-sandbox/<N>-merge`. It's reused on the next run as long as neither side has moved
   (`REDO=1` to redo it).
6. **Sandbox** the merge with `sandbox-pr.sh --ref`: the usual risky-file triage and
   confirmation, then the tests with your *current* `uv.lock`.

Then `make pr-review PR=<N>` reviews the PR and the report as usual. It also reads the merge's
conflict resolution (`resolution.diff`, i.e. `git show --cc`) and the agent's notes.
`make pr-push PR=<N>` pushes the merge commit to the contributor's branch after asking, so the
PR becomes mergeable on GitHub. If they didn't allow edits by maintainers, it offers to push
the merge as `pr-<N>-merged` and open a new PR from it. The contributor's commits stay in the
history either way.

Options: `AGENT=0` resolves in your editor instead of with the agent. A conflict it can't
handle (rename/delete, binary, symlink...) stops with instructions to merge by hand in a
throwaway worktree, then continue with `COMMIT=<sha>`. A `uv.lock` conflict is resolved by
taking `dev`'s lockfile: run `uv lock` afterwards if the PR changed dependencies.

To test a stale PR exactly as written instead (against the `dev` it was built on), use
`make pr-sandbox PR=<N> DEPS=merge-base`. `uv.lock` and `pyproject.toml` are then taken from
the PR's merge-base, which is still your own history, never the PR's. An old lockfile may
lack wheels for the default Python, so add `OPTS="--python 3.14"`.

## CI

- **`pr-sandbox-monitor.yml`** runs the same thing on every PR (`--monitor-only`: it fails on
  findings, not on test failures). The report appears in the job summary, and the logs are
  uploaded as an artifact. The tooling comes from the base commit, but GitHub runs the PR's
  own copy of this workflow file, so a PR *can* edit it to switch the check off. That's why:
- **`pr-risk-label.yml`** runs on `pull_request_target`, which uses the base branch's workflow
  and `labeler.yml`, so a PR can't change it. It labels PRs that touch risky paths
  (`risk: ci`, `risk: sandbox-tooling`, `risk: agent-config`...). A PR that edits `.github/`
  or `scripts/` always carries a label. **Never add a checkout or build of the PR to that
  workflow:** `pull_request_target` has a write token.
- Recommended repo setting: require approval before workflows run for outside contributors.
  Settings → Actions → General → "Require approval for all external contributors", or:
  `gh api -X PUT repos/qlustered/deepdiff/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors`.
  Before approving, look at the risk labels.

## Prompt injection (when an AI agent reviews the PR)

A sandbox protects the machine from the code. It does nothing about *text* in the PR (the
description, code comments, test strings, commit messages or a modified `CLAUDE.md`) that tries
to steer an agent. Keep the agent that reads untrusted text away from the combination of
"can run commands", "can reach the network" and "has your credentials":

- **Never start an agent inside a PR checkout.** The PR's `.claude/settings.json` can define
  hooks that run shell commands, and its `CLAUDE.md`/`AGENTS.md` become instructions. Review
  from your own checkout with `gh pr diff <N>`, so the PR's files are only ever read as data.
- **Don't use auto/YOLO modes when reviewing outside PRs.** Use plan mode or default
  permission prompts, and run any PR code only through `sandbox-pr.sh`.
- **Enable Claude Code's Bash sandbox** (`/sandbox`), so any command the agent runs is limited
  to the working directory and allowed network hosts. On Linux it needs `bubblewrap` and `socat`.
- **Or review in the cloud** (`/code-review ultra <N>`), where an injection can't reach this
  machine.
- **An agent saying "this PR is safe" is not a gate.** The risk labels, the risky-file diff and
  the sandbox report are.

## Limits

- Code can behave differently when it detects a sandbox or CI. That's why the sandbox mirrors
  a developer machine (real `$HOME` path, user name, hostname, canaries), but no dynamic analysis
  proves absence of malice. Only code that runs is observed. A payload hidden behind a date
  check or a rare branch can stay quiet. Reading the diff still matters.
- bwrap shares the host kernel. It stops the realistic attacks (credential theft, exfiltration,
  persistence) but not a kernel exploit. For that level, run the same script inside a throwaway
  VM.
- Code in the PR that isn't executed by the tests (docs, benchmarks, `noxfile.py`) is not
  monitored. It's listed under "will NOT be run" so you can read it.
- Linux only. On macOS, run it in a Linux VM (e.g. Lima/OrbStack) or rely on the CI monitor.
