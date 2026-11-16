# Reviewing untrusted PRs safely

Running a PR's tests means running the PR's code. These tools help you do that without
handing it your SSH keys, PyPI token or shell config, and they tell you if it tried.

## Quick start (Linux)

Requirements: `bwrap` (bubblewrap), `strace`, `uv`, `python3`. On Ubuntu:
`sudo apt install bubblewrap strace`.

```bash
# From YOUR checkout (dev or master), never from inside a PR checkout:
scripts/pr_sandbox/sandbox-pr.sh 660                     # review risky files, then run the tests
scripts/pr_sandbox/sandbox-pr.sh 660 -- tests/test_tsv.py -x
scripts/pr_sandbox/sandbox-pr.sh --base master 661       # PR targeting master
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
  to the working directory and allowed network hosts.
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
