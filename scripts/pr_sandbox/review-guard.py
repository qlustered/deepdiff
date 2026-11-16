"""PreToolUse hook for PR-review sessions (loaded via review-settings.json by `make pr-review`).

Backstop for the permission settings: if the session is in auto or bypass mode, however it
got there, block every tool call. Exit code 2 blocks the call and shows stderr to Claude.
"""
import json
import sys

BLOCKED_MODES = {"auto", "bypassPermissions"}

try:
    mode = json.load(sys.stdin).get("permission_mode")
except (ValueError, AttributeError):
    mode = None

if mode in BLOCKED_MODES:
    print(f"PR review session: tool use is blocked in '{mode}' mode. "
          "Switch back to plan or manual mode (Shift+Tab).", file=sys.stderr)
    sys.exit(2)
