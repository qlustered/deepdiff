#!/usr/bin/env python3
"""Bring a stale PR up to date with its base branch and test the result in the sandbox.

  merge-pr.py merge [options] PR [-- PYTEST_ARGS...]     (make pr-merge PR=<N>)
  merge-pr.py push  [--remote NAME] PR                   (make pr-push  PR=<N>)

merge:
  1. Fetches the PR and BASE into refs/pr-sandbox/ (no checkout, like sandbox-pr.sh).
  2. Merges BASE into the PR in memory (git merge-tree). Nothing is checked out, so none of
     the PR's files (.envrc, .claude/, CLAUDE.md...) ever land in a working tree.
  3. If there are conflicts, copies just the conflicted files (renamed to conflicts/NN.txt) to
     a scratch dir and has a locked-down Claude agent resolve them: --restricted, only the
     Read/Edit/Write/Glob/Grep tools, no MCP servers, and a guard hook that confines it to
     that dir. The script checks that the lockdown was in effect before using the result.
  4. Shows you each conflict and its resolution. Nothing is committed until you accept.
  5. Commits the merge (PR head as first parent, BASE as second) to refs/pr-sandbox/<N>-merge.
  6. Runs sandbox-pr.sh --ref on the merge: risky-file triage, then the tests in the sandbox,
     with the current lockfile.

push: pushes that merge commit to the contributor's branch (a fast-forward, after asking you),
  so the PR becomes mergeable. If maintainers can't push there, it offers to open a new PR.

Run it from your own trusted checkout, never from inside a PR checkout.
"""
import argparse
import grp
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from typing import NoReturn

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO = subprocess.run(["git", "-C", SCRIPT_DIR, "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()
GIT = ["git", "-C", REPO, "-c", "core.quotePath=true", "--literal-pathspecs"]
AGENT_TOOLS = ["Read", "Edit", "Write", "Glob", "Grep"]
SUPPORTED_CONFLICTS = {"CONFLICT (contents)", "CONFLICT (add/add)"}
TOTAL_STEPS = 6
AGENT_TIMEOUT = 20 * 60

TTY = sys.stdout.isatty()


def style(code, text):
    return f"\033[{code}m{text}\033[0m" if TTY else text


BOLD, RED, GREEN, YELLOW, CYAN, DIM = (lambda t, c=c: style(c, t) for c in ("1", "31", "32", "33", "36", "2"))

# Strip control characters (ANSI escapes, \r...) and make invisible/bidi Unicode visible in
# attacker-controlled text before printing it.
_CTRL = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁩﻿]")


def clean(text):
    return _INVISIBLE.sub(lambda m: f"<U+{ord(m.group()):04X}>", _CTRL.sub("?", text))


def say(msg=""):
    print(msg, flush=True)


def step(n, title, *lines):
    say()
    say(BOLD(f"==> [{n}/{TOTAL_STEPS}] {title}"))
    for line in lines:
        say(f"    {line}")


def warn(msg):
    say(YELLOW(f"    ! {msg}"))


def die(msg, code=1) -> NoReturn:
    say(RED(f"merge-pr: {msg}"))
    sys.exit(code)


def ask(question, choices):
    """Ask until one of `choices` (single letters) is given. The first one is the default."""
    hint = "/".join(c.upper() if i == 0 else c for i, c in enumerate(choices))
    while True:
        try:
            answer = input(f"{question} [{hint}] ").strip().lower()
        except EOFError:
            die("no answer (stdin closed)")
        if not answer:
            return choices[0]
        if answer[0] in choices:
            return answer[0]


def git(*args, check=True, input=None, env=None, binary=False):
    stdin = None if input is not None else subprocess.DEVNULL
    proc = subprocess.run(GIT + list(args), capture_output=True, input=input, env=env, text=not binary,
                          stdin=stdin)
    if check and proc.returncode != 0:
        err = proc.stderr if not binary else proc.stderr.decode(errors="replace")
        die(f"git {' '.join(args[:3])} failed:\n{clean(err)}")
    return proc.stdout if binary else proc.stdout.strip()


def rev(ref):
    out = subprocess.run(GIT + ["rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def parents(sha):
    return git("rev-list", "--parents", "-n1", sha).split()[1:]


def is_ancestor(a, b):
    return subprocess.run(GIT + ["merge-base", "--is-ancestor", a, b]).returncode == 0


def short(sha):
    return sha[:10]


def gh_pr(pr, fields):
    try:
        out = subprocess.run(["gh", "pr", "view", str(pr), "--json", ",".join(fields)], cwd=REPO,
                             capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return json.loads(out.stdout) if out.returncode == 0 else None


def share_group():
    """The group the agent shares the scratch dir through (see run-sandboxed.sh), or None."""
    name = os.environ.get("PR_SANDBOX_SHARE_GROUP", "ai-dev")
    if not name:
        return None
    try:
        gid = grp.getgrnam(name).gr_gid
    except KeyError:
        return None
    return gid if gid in os.getgroups() else None


def chmod(path, mode, gid):
    if gid is not None:
        os.chown(path, -1, gid)
    os.chmod(path, mode)


# ---------------------------------------------------------------------------------------------
# Conflict files with diff3 markers
# ---------------------------------------------------------------------------------------------
def split_conflicts(text):
    """Split a diff3-conflicted file into (contexts, blocks).

    contexts has len(blocks) + 1 strings; each block is a dict with pr/base/ancestor text and
    the 1-based line where it starts.
    """
    contexts, blocks, cur, block, part = [], [], [], None, "pr"
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        marker = re.match(r"(<{7,}|\|{7,}|={7,}|>{7,})(?: |\r?\n|$)", line)
        kind = marker.group(1)[0] if marker else None
        if block is None and kind == "<":
            contexts.append("".join(cur))
            cur, block, part = [], {"line": lineno, "pr": [], "ancestor": [], "base": [], "raw": [line]}, "pr"
            continue
        if block is not None:
            block["raw"].append(line)
        if block is not None and kind == "|" and part == "pr":
            part = "ancestor"
        elif block is not None and kind == "=" and part in ("pr", "ancestor"):
            part = "base"
        elif block is not None and kind == ">" and part == "base":
            block.pop("raw")
            blocks.append({k: "".join(v) if isinstance(v, list) else v for k, v in block.items()})
            block = None
        elif block is not None:
            block[part].append(line)
        else:
            cur.append(line)
    if block is not None:  # unterminated: treat it as context
        cur = block["raw"]
    contexts.append("".join(cur))
    return contexts, blocks


def leftover_markers(text, max_separators):
    """Conflict marker lines still in `text`. '=======' also occurs legitimately (rst), so it
    only counts beyond how often the two sides already had it."""
    found, separators = [], 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r"(<{7,}|>{7,}|\|{7,})( |$)", line):
            found.append(lineno)
        elif re.fullmatch(r"={7,}", line):
            separators += 1
            if separators > max_separators:
                found.append(lineno)
    return found


def locate_resolutions(contexts, resolved):
    """Map each conflict block to its resolved text, if everything outside the blocks is
    unchanged. Returns a list of strings (one per block), or None if the context was edited."""
    pos = 0
    if not resolved.startswith(contexts[0]):
        return None
    pos = len(contexts[0])
    spans = []
    for i, ctx in enumerate(contexts[1:], 1):
        if i == len(contexts) - 1:
            end = len(resolved) - len(ctx)
            if end < pos or not resolved.endswith(ctx):
                return None
        else:
            end = resolved.find(ctx, pos) if ctx else pos
            if end < 0:
                return None
        spans.append(resolved[pos:end])
        pos = end + len(ctx)
    return spans


# ---------------------------------------------------------------------------------------------
# Trial merge
# ---------------------------------------------------------------------------------------------
def trial_merge(pr_name, base_name):
    """Merge in memory. Returns (tree, {path: {stage: (mode, sha)}}, {path: set(conflict types)})."""
    proc = subprocess.run(GIT + ["-c", "merge.conflictStyle=diff3", "merge-tree", "--write-tree", "-z",
                                 pr_name, base_name], capture_output=True)
    if proc.returncode not in (0, 1):
        die(f"git merge-tree failed:\n{clean(proc.stderr.decode(errors='replace'))}")
    toks = proc.stdout.split(b"\0")
    tree = toks[0].decode()
    if proc.returncode == 0:
        return tree, {}, {}
    entries, i = {}, 1
    while i < len(toks) and toks[i]:
        meta, path = toks[i].split(b"\t", 1)
        mode, sha, stage = meta.decode().split()
        entries.setdefault(os.fsdecode(path), {})[int(stage)] = (mode, sha)
        i += 1
    i += 1
    types = {}
    while i < len(toks) and toks[i]:
        n = int(toks[i])
        paths = [os.fsdecode(p) for p in toks[i + 1:i + 1 + n]]
        kind = toks[i + 1 + n].decode(errors="replace")
        if kind.startswith("CONFLICT"):
            for p in paths:
                types.setdefault(p, set()).add(kind)
        i += 3 + n
    for p in entries:
        types.setdefault(p, {"CONFLICT (unknown)"})
    return tree, entries, types


def unsupported_reason(path, stages, kinds):
    if not kinds <= SUPPORTED_CONFLICTS:
        return ", ".join(sorted(kinds))
    if 2 not in stages or 3 not in stages:
        return "missing on one side"
    for mode, sha in stages.values():
        if mode not in ("100644", "100755"):
            return f"not a regular file (mode {mode})"
        if b"\0" in git("cat-file", "blob", sha, binary=True):
            return "binary file"
    return None


def blob_at(tree, path):
    return git("cat-file", "blob", f"{tree}:{path}", binary=True)


# ---------------------------------------------------------------------------------------------
# The conflict-resolving agent
# ---------------------------------------------------------------------------------------------
def describe_tool(call, files_dir):
    args = call.get("input") or {}
    target = args.get("file_path") or args.get("path") or args.get("pattern") or ""
    if isinstance(target, str) and target.startswith(files_dir + os.sep):
        target = target[len(files_dir) + 1:]
    return clean(f"{call.get('name')} {target}")


def run_agent(work, files_dir, pr, base, claude_cmd):
    guard_log = os.path.join(work, "guard", "guard.log")
    open(guard_log, "a").close()
    hook = " ".join(shlex.quote(x) for x in
                    ["python3", "-I", os.path.join(SCRIPT_DIR, "merge-guard.py"), files_dir, guard_log])
    settings = {
        "permissions": {
            "defaultMode": "dontAsk",
            "disableAutoMode": "disable",
            "disableBypassPermissionsMode": "disable",
            "allow": AGENT_TOOLS,
            "deny": ["Bash", "WebFetch", "WebSearch", "NotebookEdit"],
        },
        "hooks": {"PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": hook}]}]},
    }
    with open(os.path.join(SCRIPT_DIR, "merge-prompt.md")) as f:
        prompt = f.read().replace("{PR}", str(pr)).replace("{BASE}", base)
    args = ["-p", "--restricted", "--tools", ",".join(AGENT_TOOLS), "--strict-mcp-config",
            "--disable-slash-commands", "--no-session-persistence", "--permission-mode", "dontAsk",
            "--settings", json.dumps(settings), "--output-format", "stream-json", "--verbose",
            "--", prompt]
    # Like `make pr-review`: run `claude` from an interactive zsh so a zshrc wrapper (e.g. one
    # that switches to another user) is used.
    if shutil.which("zsh"):
        cmd = ["zsh", "-ic", claude_cmd + ' "$@"', "_"] + args
    else:
        cmd = shlex.split(claude_cmd) + args
    log = open(os.path.join(work, "agent.jsonl"), "w")
    proc = subprocess.Popen(cmd, cwd=files_dir, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            text=True)
    started, tool_calls, result, verified = time.time(), 0, None, False
    timer = threading.Timer(AGENT_TIMEOUT, proc.kill)
    timer.start()

    def abort(msg):
        proc.kill()
        proc.wait()
        die(f"{msg}\n    Not using anything the agent wrote. Resolve by hand with AGENT=0.")

    assert proc.stdout is not None
    for line in proc.stdout:
        log.write(line)
        if not line.startswith("{"):
            continue  # shell noise from zshrc, direnv...
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            tools, mcp, mode = event.get("tools"), event.get("mcp_servers"), event.get("permissionMode")
            if sorted(tools or []) != sorted(AGENT_TOOLS) or mcp or mode != "dontAsk":
                abort(f"the agent session isn't locked down as requested (tools={tools}, "
                      f"mcp_servers={mcp}, permissionMode={mode})")
            verified = True
            say(DIM(f"    agent started: tools {', '.join(tools)}; no MCP servers; dontAsk mode"))
        elif kind == "assistant":
            if not verified:
                abort("the agent acted before its session was verified")
            for part in (event.get("message") or {}).get("content") or []:
                if part.get("type") == "tool_use":
                    tool_calls += 1
                    say(DIM(f"    agent: {describe_tool(part, files_dir)}"))
        elif kind == "result":
            result = event
    proc.wait()
    timer.cancel()
    log.close()
    if time.time() - started >= AGENT_TIMEOUT:
        die(f"the agent took longer than {AGENT_TIMEOUT // 60} minutes and was stopped. "
            "Resolve by hand with AGENT=0.")
    with open(guard_log) as f:
        guarded = sum(1 for _ in f)
    if tool_calls and guarded < tool_calls:
        die(f"the guard hook saw {guarded} of the agent's {tool_calls} tool calls, so its settings "
            "were not fully applied. Not using its output. Resolve by hand with AGENT=0.")
    if result is None or proc.returncode != 0:
        warn(f"the agent exited with status {proc.returncode} and no result; see {work}/agent.jsonl")
        return
    blocked = [json.loads(line) for line in open(guard_log)]
    blocked = [b for b in blocked if b.get("blocked")]
    if blocked:
        warn(f"the guard blocked {len(blocked)} tool call(s); details in {guard_log}")
    cost = result.get("total_cost_usd")
    spent = f", ${cost:.2f}" if isinstance(cost, (int, float)) else ""
    say(DIM(f"    agent finished in {time.time() - started:.0f}s{spent}"))
    for line in clean(str(result.get("result") or "")).splitlines():
        say(f"    | {line}")


# ---------------------------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------------------------
def indent_block(text, color, prefix):
    if not text:
        return [DIM(f"      {prefix} (nothing)")]
    return [color(f"      {prefix} {clean(line)}") for line in text.rstrip("\n").split("\n")]


def review_text(conflicts, files_dir, base):
    """Build the review (one section per conflicted file). Returns (lines, problems)."""
    lines, problems = [], []
    for c in conflicts:
        resolved = open(c["file"], encoding="utf-8", errors="replace").read()
        head = f"--- {clean(c['path'])}  ({c['name']})"
        lines += ["", BOLD(head)]
        if c.get("auto"):
            lines.append(YELLOW(f"    {c['auto']}"))
            continue
        markers = leftover_markers(resolved, c["max_separators"])
        if markers:
            problems.append(f"{c['path']}: conflict markers left on line(s) {markers[:5]}")
        spans = locate_resolutions(c["contexts"], resolved)
        if spans is None:
            problems.append(f"{c['path']}: text OUTSIDE the conflict blocks was changed; "
                            "use [d] to see the whole diff")
            continue
        for n, (block, span) in enumerate(zip(c["blocks"], spans), 1):
            lines.append(CYAN(f"    conflict {n}/{len(c['blocks'])} at line {block['line']}"))
            lines.append("      PR:")
            lines += indent_block(block["pr"], RED, "|")
            lines.append(f"      {base}:")
            lines += indent_block(block["base"], RED, "|")
            lines.append(BOLD("      resolved as:"))
            lines += indent_block(span, GREEN, "|")
    notes = os.path.join(files_dir, "notes.md")
    if os.path.exists(notes):
        lines += ["", BOLD("--- agent's notes (notes.md)")]
        text = clean(open(notes, encoding="utf-8", errors="replace").read())
        for flag in ("UNCERTAIN", "SUSPICIOUS"):
            if re.search(rf"^[^\w\n]*{flag}[^\w\n]*:", text, re.M):
                problems.append(f"the agent flagged something {flag} (see its notes above)")
        lines += [f"    {line}" for line in text.splitlines()]
    return lines, problems


def page(lines):
    text = "\n".join(lines) + "\n"
    if TTY and text.count("\n") > shutil.get_terminal_size().lines - 5 and shutil.which("less"):
        subprocess.run(["less", "-R", "-F", "-X"], input=text, text=True)
    else:
        sys.stdout.write(text)


def full_diff(conflicts, work):
    out = []
    for c in conflicts:
        base_copy = os.path.join(work, "original", c["name"] + ".base")
        diff = subprocess.run(["git", "diff", "--no-index", "--no-color", "--no-ext-diff",
                               "--src-prefix=base/", "--dst-prefix=resolved/", base_copy, c["file"]],
                              capture_output=True, text=True, errors="replace").stdout
        out.append(BOLD(f"--- {clean(c['path'])}: {c['name']} compared to the base branch"))
        for line in clean(diff).splitlines():
            out.append(GREEN(line) if line.startswith("+") else RED(line) if line.startswith("-") else line)
    page(out)


def own_files(conflicts, files_dir, gid):
    """After the agent: take back ownership (it may have replaced files) and revoke its write access."""
    for c in conflicts:
        data = open(c["file"], "rb").read()
        os.unlink(c["file"])
        with open(c["file"], "wb") as f:
            f.write(data)
        os.chmod(c["file"], 0o644)
    for d in (files_dir, os.path.join(files_dir, "conflicts")):
        chmod(d, 0o2755 if gid is not None else 0o700, gid)


def edit(conflicts):
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    cmd = shlex.split(editor)
    if os.path.basename(cmd[0]) in ("vi", "vim", "nvim", "view", "gvim"):
        cmd += ["--cmd", "set nomodeline"]  # the files hold PR text: don't honour modelines
    subprocess.run(cmd + [c["file"] for c in conflicts if not c.get("auto")])


# ---------------------------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------------------------
def run_sandbox(a, ref):
    cmd = [os.path.join(SCRIPT_DIR, "sandbox-pr.sh"), "--remote", a.remote, "--base", a.base]
    if ref:
        cmd += ["--ref", ref]
    for opt in ("python", "out", "fail_on"):
        if getattr(a, opt):
            cmd += [f"--{opt.replace('_', '-')}", getattr(a, opt)]
    if a.no_strace:
        cmd.append("--no-strace")
    cmd.append(str(a.pr))
    if a.pytest_args:
        cmd += ["--"] + a.pytest_args
    return subprocess.run(cmd).returncode


def make_commit(tree, pr_sha, base_sha, pr, base, title, conflicted):
    msg = f"Merge branch '{base}' into PR #{pr}\n"
    if title:
        msg += f"\nPR #{pr}: {clean(title)}\n"
    if conflicted:
        msg += "\nConflicts resolved:\n" + "".join(f"\t{clean(p)}\n" for p in conflicted)
    return git("commit-tree", tree, "-p", pr_sha, "-p", base_sha, input=msg)


def cmd_merge(a):
    pr, base = a.pr, a.base
    pr_ref, base_ref, merge_ref = (f"refs/pr-sandbox/{pr}", f"refs/pr-sandbox/{pr}-base",
                                   f"refs/pr-sandbox/{pr}-merge")

    step(1, f"Fetching PR #{pr} and {a.remote}/{base}",
         "Only git objects are fetched, into refs/pr-sandbox/. Nothing is checked out.")
    if not a.no_fetch:
        git("fetch", "--quiet", "--no-tags", a.remote,
            f"+refs/pull/{pr}/head:{pr_ref}", f"+refs/heads/{base}:{base_ref}")
    pr_sha, base_sha = rev(pr_ref), rev(base_ref)
    if not pr_sha or not base_sha:
        die(f"missing {pr_ref} or {base_ref}" + (" (drop --no-fetch)" if a.no_fetch else ""))
    info = gh_pr(pr, ["title", "author"]) or {}
    title = info.get("title", "")
    say(f"    PR #{pr} head {short(pr_sha)}: {clean(title)}")
    say(f"    {base} head {short(base_sha)}")

    if is_ancestor(base_sha, pr_sha):
        step(2, "Nothing to merge", f"The PR already contains {base}'s latest commit.")
        say("    Testing the PR as it is, with `make pr-sandbox`'s flow.")
        sys.exit(0 if a.no_test else run_sandbox(a, None))

    merge_sha, existing = None, rev(merge_ref)
    if a.use_commit:
        step(2, "Using your merge commit", f"{a.use_commit}")
        merge_sha = rev(a.use_commit) or die(f"{a.use_commit} is not a commit")
        ps = parents(merge_sha)
        if len(ps) != 2 or ps[0] != pr_sha or not is_ancestor(ps[1], base_sha):
            die(f"{a.use_commit} must be a merge whose first parent is PR #{pr}'s head "
                f"({short(pr_sha)}) and whose second parent is on {base}.")
        for n in (3, 4, 5):
            step(n, "(skipped: you resolved the merge yourself)")
    elif existing and parents(existing) == [pr_sha, base_sha] and not a.redo:
        step(2, "Reusing the merge you accepted earlier",
             f"{merge_ref} = {short(existing)} already merges {base} {short(base_sha)} into the "
             f"PR head {short(pr_sha)}.", "To redo it: REDO=1 (make) or --redo.")
        merge_sha = existing
        for n in (3, 4, 5):
            step(n, "(skipped)")
    else:
        merge_sha = merge_and_resolve(a, pr, base, pr_sha, base_sha, title)

    if merge_sha != existing:
        git("update-ref", merge_ref, merge_sha)
        say(GREEN(f"    {merge_ref} = {short(merge_sha)}"))
    if merge_sha != existing and not a.work_dir:  # clean merge or --use-commit: a dir for the diff
        a.work_dir = os.path.join(a.tmp, f"deepdiff-pr-{pr}-merge-{time.strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(a.work_dir)
        gid = share_group()
        chmod(a.work_dir, 0o2750 if gid is not None else 0o700, gid)
    if a.work_dir:
        with open(os.path.join(a.work_dir, "resolution.diff"), "w") as f:
            f.write(clean(git("show", "--cc", "--no-color", "--no-ext-diff", "--format=fuller", merge_sha)))
            f.write("\n")

    if a.no_test:
        step(6, "Sandbox tests (skipped: --no-test)")
        status = None
    else:
        step(6, "Running the merged code's tests in the sandbox",
             "sandbox-pr.sh shows the PR's risky files and asks before running anything.",
             "Dependencies come from your current uv.lock.")
        status = run_sandbox(a, merge_ref)

    say()
    say(BOLD(f"==> Done: {merge_ref} = {short(merge_sha)} (PR #{pr} + {base})"))
    if status is not None:
        meaning = " (suspicious behaviour found!)" if status == 2 else " (tests failed)" if status else ""
        say(f"    sandbox exit status: {status}{meaning}")
    say("    Next:")
    say(f"      make pr-review PR={pr}    # AI review of the PR, the sandbox report and the conflict resolution")
    say(f"      make pr-push   PR={pr}    # push the merge to the PR's branch (asks first)")
    sys.exit(status or 0)


def merge_and_resolve(a, pr, base, pr_sha, base_sha, title):
    step(2, f"Merging {base} into PR #{pr} (in memory)",
         "git merge-tree computes the merge without touching any working tree.")
    tree, entries, kinds = trial_merge(f"pr-sandbox/{pr}", f"pr-sandbox/{pr}-base")
    if not kinds:
        say(GREEN("    Merged cleanly, no conflicts."))
        for n in (3, 4):
            step(n, "(skipped: no conflicts)")
        step(5, "Committing the merge")
        return make_commit(tree, pr_sha, base_sha, pr, base, title, [])

    paths = sorted(kinds)
    say(f"    {len(paths)} conflicted file(s):")
    unsupported = {}
    for p in paths:
        reason = unsupported_reason(p, entries.get(p, {}), kinds[p])
        if reason:
            unsupported[p] = reason
        say(f"      {'!' if reason else '-'} {clean(p)}" + (f"  ({reason})" if reason else ""))
    if unsupported:
        manual_instructions(pr, base, unsupported)

    ts = time.strftime("%Y%m%d-%H%M%S")
    work = a.work_dir = os.path.join(a.tmp, f"deepdiff-pr-{pr}-merge-{ts}")
    files_dir = os.path.join(work, "files")
    gid = share_group()
    for d, mode in ((work, 0o2750), (files_dir, 0o2770), (os.path.join(files_dir, "conflicts"), 0o2770),
                    (os.path.join(files_dir, "context"), 0o2750), (os.path.join(work, "guard"), 0o2770),
                    (os.path.join(work, "original"), 0o700)):
        os.makedirs(d)
        chmod(d, mode if gid is not None else 0o700, gid)

    mb = git("merge-base", pr_sha, base_sha)
    conflicts, manifest = [], [f"# Merging `{base}` into PR #{pr}", "",
                               f"PR title (untrusted): {clean(title)}", f"Merge base: {mb}", ""]
    for i, p in enumerate(paths, 1):
        name = f"{i:02d}.txt"
        c = {"path": p, "name": name, "file": os.path.join(files_dir, "conflicts", name)}
        conflicted = blob_at(tree, p)
        stages = entries[p]
        base_side = git("cat-file", "blob", stages[3][1], binary=True)
        pr_side = git("cat-file", "blob", stages[2][1], binary=True)
        with open(os.path.join(work, "original", name), "wb") as f:
            f.write(conflicted)
        with open(os.path.join(work, "original", name + ".base"), "wb") as f:
            f.write(base_side)
        if p == "uv.lock":
            # A lockfile can't be merged by hand: keep the base branch's and re-lock if needed.
            c["auto"] = (f"took {base}'s uv.lock as is. If the PR changed dependencies, "
                         "run `uv lock` on the merged branch before releasing.")
            data = base_side
        else:
            data = conflicted
            text = conflicted.decode("utf-8", errors="replace")
            c["contexts"], c["blocks"] = split_conflicts(text)
            c["max_separators"] = max(len(re.findall(rb"^={7,}$", s, re.M)) for s in (pr_side, base_side))
        with open(c["file"], "wb") as f:
            f.write(data)
        chmod(c["file"], 0o660 if gid is not None else 0o600, gid)
        for side, sha in (("pr", pr_sha), ("base", base_sha)):
            diff_path = os.path.join(files_dir, "context", f"{i:02d}.{side}.diff")
            with open(diff_path, "w") as f:
                f.write(git("diff", "--no-color", "--no-ext-diff", "--no-textconv", mb, sha, "--", p))
            chmod(diff_path, 0o640 if gid is not None else 0o600, gid)
        done = " (already resolved, don't edit)" if c.get("auto") else ""
        manifest += [f"## conflicts/{name} = `{clean(p)}`{done}",
                     "", f"Commits on `{base}` since the merge base touching it:"]
        manifest += [f"- {clean(s)}" for s in git("log", "--format=%h %s", f"{mb}..{base_sha}", "--", p).splitlines()]
        manifest += ["", "Commits in the PR touching it (untrusted text):"]
        manifest += [f"- {clean(s)}" for s in git("log", "--format=%h %s", f"{mb}..{pr_sha}", "--", p).splitlines()]
        manifest.append("")
        conflicts.append(c)
    manifest_path = os.path.join(files_dir, "manifest.md")
    with open(manifest_path, "w") as f:
        f.write("\n".join(manifest))
    chmod(manifest_path, 0o640 if gid is not None else 0o600, gid)
    say(f"    work dir: {work}")

    to_resolve = [c for c in conflicts if not c.get("auto")]
    if not to_resolve:
        step(3, "(skipped: nothing left to resolve)")
    elif a.no_agent:
        step(3, "Resolving by hand (AGENT=0)", "Your editor opens on the conflicted files.")
        edit(conflicts)
    else:
        step(3, "Resolving the conflicts with a locked-down Claude agent",
             "It only sees copies of the conflicted files (as conflicts/NN.txt), each side's diff and",
             f"commit subjects, in {files_dir}.",
             "It has no shell, no network tools and no MCP servers, and a guard hook keeps it in that dir.",
             "This usually takes a minute or two.")
        run_agent(work, files_dir, pr, base, a.claude_cmd)
        own_files(conflicts, files_dir, gid)

    step(4, "Review the resolution",
         "For each conflict: the PR's side, the base branch's side and the resolution.",
         "Nothing is committed until you accept.")
    while True:
        lines, problems = review_text(conflicts, files_dir, base)
        page(lines)
        say()
        for p in problems:
            warn(clean(p))
        choices = ("a", "e", "d", "q") if not problems else ("e", "d", "a", "q")
        say("    [a]ccept and commit   [e]dit the files yourself   [d]iff each file against "
            f"{base}   [q]uit (keeps the work dir)")
        choice = ask("    Your choice?", list(choices))
        if choice == "e":
            edit(conflicts)
        elif choice == "d":
            full_diff(conflicts, work)
        elif choice == "q":
            say(f"    Stopped. Nothing was committed. The files are in {files_dir}/conflicts.")
            sys.exit(1)
        elif choice == "a":
            still = [c["path"] for c in conflicts if not c.get("auto")
                     if leftover_markers(open(c["file"], errors="replace").read(), c["max_separators"])]
            if still:
                warn("conflict markers are still in: " + ", ".join(clean(p) for p in still))
                continue
            break

    step(5, "Committing the merge",
         "Written straight to git objects (no checkout). First parent: the PR head; second: "
         f"{base}.")
    index = os.path.join(work, "index")
    env = dict(os.environ, GIT_INDEX_FILE=index)
    git("read-tree", tree, env=env)
    info = []
    for c in conflicts:
        sha = git("hash-object", "-w", "--no-filters", c["file"])
        mode = entries[c["path"]][2][0]
        info.append(f"{mode} {sha}\t{c['path']}")
    git("update-index", "-z", "--index-info", input="\0".join(info) + "\0", env=env)
    resolved_tree = git("write-tree", env=env)
    return make_commit(resolved_tree, pr_sha, base_sha, pr, base, title, paths)


def manual_instructions(pr, base, unsupported):
    say()
    say(RED("    These conflicts can't be resolved automatically: ") + ", ".join(clean(p) for p in unsupported))
    say("    Resolve the merge by hand in a throwaway worktree (don't start an agent in it):")
    say(f"      git worktree add --detach /tmp/pr{pr}-merge refs/pr-sandbox/{pr}")
    say(f"      cd /tmp/pr{pr}-merge && git merge --no-ff refs/pr-sandbox/{pr}-base")
    say("      # resolve, git add ..., git commit")
    say(f"    Then test and keep it with:  make pr-merge PR={pr} COMMIT=<that commit>")
    say(f"    And clean up:                git worktree remove /tmp/pr{pr}-merge")
    sys.exit(1)


# ---------------------------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------------------------
def cmd_push(a):
    pr = a.pr
    merge_ref = f"refs/pr-sandbox/{pr}-merge"
    merge_sha = rev(merge_ref) or die(f"no {merge_ref}. Run: make pr-merge PR={pr}")
    git("fetch", "--quiet", "--no-tags", a.remote, f"+refs/pull/{pr}/head:refs/pr-sandbox/{pr}")
    head = rev(f"refs/pr-sandbox/{pr}")
    if parents(merge_sha)[0] != head:
        die(f"PR #{pr} has new commits since the merge was made. Run again: make pr-merge PR={pr}")
    info = gh_pr(pr, ["state", "title", "author", "headRefName", "headRepository",
                      "headRepositoryOwner", "isCrossRepository", "maintainerCanModify", "baseRefName"])
    if not info:
        die("couldn't read the PR with `gh pr view`")
    if info.get("state") != "OPEN":
        die(f"PR #{pr} is {info.get('state')}")
    owner = (info.get("headRepositoryOwner") or {}).get("login", "")
    repo = (info.get("headRepository") or {}).get("name", "")
    branch = info.get("headRefName", "")
    names_ok = all(re.fullmatch(r"[A-Za-z0-9_.-]+", x or "") for x in (owner, repo))
    if not names_ok or subprocess.run(["git", "check-ref-format", f"refs/heads/{branch}"]).returncode != 0:
        die("the PR's head repository or branch name looks invalid; push by hand")
    say(BOLD(f"==> PR #{pr}: {clean(info.get('title', ''))}"))
    say(f"    merge commit {short(merge_sha)} = PR head {short(head)} + {clean(info.get('baseRefName', ''))}")
    if info.get("maintainerCanModify") or not info.get("isCrossRepository"):
        url = f"https://github.com/{owner}/{repo}.git"
        say(f"    This pushes 1 merge commit to {clean(owner)}/{clean(repo)} branch {clean(branch)}.")
        say("    It's a fast-forward (no force push). The PR then contains the base branch and can be merged.")
        if ask("    Push now?", ["n", "y"]) != "y":
            say("    Not pushed.")
            return
        subprocess.run(["git", "-C", REPO, "push", url, f"{merge_sha}:refs/heads/{branch}"], check=True)
        say(GREEN(f"    Pushed. PR #{pr} now includes the merge."))
        return
    new_branch = f"pr-{pr}-merged"
    say(YELLOW("    The contributor didn't allow edits by maintainers, so their branch can't be updated."))
    say(f"    Instead: push the merge to {a.remote} as {new_branch} and open a new PR from it. The")
    say("    contributor's commits stay in the history, so they keep the credit.")
    if ask("    Do that now?", ["n", "y"]) != "y":
        say("    Nothing pushed.")
        return
    subprocess.run(["git", "-C", REPO, "push", a.remote, f"{merge_sha}:refs/heads/{new_branch}"], check=True)
    author = (info.get("author") or {}).get("login", "")
    body = (f"Supersedes #{pr} by {author}, merged with `{info.get('baseRefName')}` because the original "
            "branch couldn't be updated. Their commits are kept as they are.")
    subprocess.run(["gh", "pr", "create", "--base", info.get("baseRefName") or "dev", "--head", new_branch,
                    "--title", info.get("title", f"PR #{pr}"), "--body", body], cwd=REPO, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge", help="merge the base branch into the PR, resolve, review, test")
    m.add_argument("--remote", default="origin")
    m.add_argument("--base", default="dev", help="branch the PR targets (default: dev)")
    m.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"), help="where the work dir goes")
    m.add_argument("--claude-cmd", default=os.environ.get("CLAUDE_CMD", "claude"))
    m.add_argument("--no-agent", action="store_true", help="resolve conflicts in your editor instead")
    m.add_argument("--redo", action="store_true", help="redo the merge even if an accepted one exists")
    m.add_argument("--use-commit", help="a merge commit you made by hand, to test and keep")
    m.add_argument("--no-fetch", action="store_true", help="use the refs from an earlier fetch")
    m.add_argument("--no-test", action="store_true", help="stop after committing the merge")
    for opt in ("--python", "--out", "--fail-on"):
        m.add_argument(opt, help="passed to sandbox-pr.sh")
    m.add_argument("--no-strace", action="store_true", help="passed to sandbox-pr.sh")
    m.add_argument("pr", type=int)
    m.add_argument("pytest_args", nargs="*", help="after --: pytest arguments")
    s = sub.add_parser("push", help="push the accepted merge to the PR's branch")
    s.add_argument("--remote", default="origin")
    s.add_argument("pr", type=int)
    a = p.parse_args()
    a.work_dir = None
    cmd_merge(a) if a.cmd == "merge" else cmd_push(a)


if __name__ == "__main__":
    main()
