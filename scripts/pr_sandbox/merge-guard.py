"""PreToolUse hook for the conflict-resolving agent started by merge-pr.py.

Usage (set by merge-pr.py in the agent's --settings): merge-guard.py FILES_DIR LOG_FILE

The agent runs with --restricted and --tools Read,Edit,Write,Glob,Grep, so it has no shell and
no network tools. This hook is the backstop, and it also lets merge-pr.py check that the
agent's settings were applied (an entry in LOG_FILE for every tool call):
- only Read, Glob and Grep inside FILES_DIR are allowed
- only Edit and Write of FILES_DIR/conflicts/* and FILES_DIR/notes.md are allowed
- every other tool, path or mode is blocked (exit 2: the call is refused and stderr goes to the agent)
"""
import json
import os
import sys

READ_TOOLS = {"Read", "Glob", "Grep"}
WRITE_TOOLS = {"Edit", "Write"}
BLOCKED_MODES = {"auto", "bypassPermissions"}


def inside(path, root):
    path = os.path.realpath(path)
    return path == root or path.startswith(root + os.sep)


def decide(event, files_dir):
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}
    if event.get("permission_mode") in BLOCKED_MODES:
        return f"tool use is blocked in '{event.get('permission_mode')}' mode"
    cwd = event.get("cwd") or files_dir
    if tool in READ_TOOLS:
        path = args.get("file_path") if tool == "Read" else args.get("path") or cwd
        if not isinstance(path, str) or not inside(os.path.join(cwd, path), files_dir):
            return f"{tool} is only allowed inside {files_dir}"
        pattern = args.get("pattern", "") if tool == "Glob" else args.get("glob", "")
        if isinstance(pattern, str) and (pattern.startswith(("/", "~")) or ".." in pattern):
            return f"{tool} patterns must stay inside {files_dir}"
        return None
    if tool in WRITE_TOOLS:
        path = args.get("file_path")
        if not isinstance(path, str):
            return f"{tool} needs a file_path"
        path = os.path.realpath(os.path.join(cwd, path))
        conflicts = os.path.join(files_dir, "conflicts")
        if os.path.dirname(path) == conflicts or path == os.path.join(files_dir, "notes.md"):
            return None
        return f"{tool} is only allowed on conflicts/* and notes.md"
    return f"{tool or 'this tool'} is not available in this session: only Read, Glob, Grep, Edit and Write"


def main():
    files_dir, log_file = os.path.realpath(sys.argv[1]), sys.argv[2]
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    reason = decide(event, files_dir)
    with open(log_file, "a") as log:
        log.write(json.dumps({"tool": event.get("tool_name"), "input": event.get("tool_input"),
                              "blocked": reason}) + "\n")
    if reason:
        print(f"Blocked: {reason}. Don't look for workarounds; note what you needed in notes.md.",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
