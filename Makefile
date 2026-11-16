# Reviewing outside PRs. See scripts/pr_sandbox/README.md.
#
#   make pr-sandbox PR=612                  # 1. triage risky files, run the PR's tests in the sandbox
#   make pr-review  PR=612                  # 2. start Claude (plan mode, auto mode locked out) on it
#   make pr-clean                           # 3. delete fetched PR refs and sandbox work dirs
#
# Options: BASE=master                 branch the PR targets (default: dev)
#          TESTS="tests/test_x.py -x"  pytest arguments (default: the whole suite)
#          OPTS="--fail-on medium"     extra sandbox-pr.sh options (--python, --no-strace, --remote ...)
#          CLAUDE_CMD=...              default: the `claude` command from your interactive zsh

SHELL := /bin/bash
BASE ?= dev
PR_TMP ?= /tmp
CLAUDE_CMD ?= claude
SANDBOX := scripts/pr_sandbox

.PHONY: pr-sandbox pr-review pr-clean _require-pr

_require-pr:
	@[[ "$(PR)" =~ ^[0-9]+$$ ]] || { echo "usage: make $(firstword $(MAKECMDGOALS)) PR=<number>" >&2; exit 1; }

pr-sandbox: _require-pr
	$(SANDBOX)/sandbox-pr.sh --base "$(BASE)" \
		--out "$(PR_TMP)/deepdiff-pr-$(PR)-$$(date +%Y%m%d-%H%M%S)" $(OPTS) $(PR) $(if $(TESTS),-- $(TESTS))

# Runs your `claude` from an interactive zsh so the zshrc wrapper (which switches to
# ai_agent) is used. --permission-mode plan beats the user-level "auto" default, and
# review-settings.json disables auto/bypass mode for the session, makes risky commands
# ask first, and adds a hook that blocks every tool call if auto/bypass mode is ever active.
# Nothing is written to .claude/settings.local.json, so your normal sessions keep auto mode.
pr-review: _require-pr
	@report=$$(ls -dt "$(PR_TMP)"/deepdiff-pr-$(PR)-*/report 2>/dev/null | head -1); \
	if [[ -z $$report ]]; then \
		echo "No sandbox report for PR $(PR) in $(PR_TMP). Run: make pr-sandbox PR=$(PR)" >&2; exit 1; \
	fi; \
	echo "==> reviewing PR $(PR) with report $$report"; \
	prompt=$$(sed -e "s|{PR}|$(PR)|g" -e "s|{REPORT}|$$report|g" $(SANDBOX)/review-prompt.md); \
	zsh -ic '$(CLAUDE_CMD) --permission-mode plan --settings "$$1" "$$2"' _ \
		"$(CURDIR)/$(SANDBOX)/review-settings.json" "$$prompt"

pr-clean:
	git for-each-ref --format='%(refname)' refs/pr-sandbox | xargs -r -n1 git update-ref -d
	rm -rf "$(PR_TMP)"/deepdiff-pr-[0-9]*-[0-9]*
