# Reviewing outside PRs. See scripts/pr_sandbox/README.md.
#
#   make pr-sandbox PR=612                  # 1. triage risky files, run the PR's tests in the sandbox
#   make pr-review  PR=612                  # 2. start Claude on it: read-only, never prompts
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

.DEFAULT_GOAL := help
.PHONY: help pr-sandbox pr-review pr-clean _require-pr

help:
	@echo "Reviewing an outside PR (run from your own dev checkout, in this order):"
	@echo
	@echo "  1. make pr-sandbox PR=<N>   Show the PR's changed and risky files (build config, conftest,"
	@echo "                              CI, agent config, pickles), then after you confirm, run its"
	@echo "                              tests in the network-less sandbox and report anything"
	@echo "                              suspicious. Exit status 2 = suspicious behaviour found."
	@echo "  2. make pr-review  PR=<N>   Start Claude on the PR and its latest sandbox report. It can"
	@echo "                              read and search freely without asking; everything else"
	@echo "                              (running code, network, edits) is refused automatically."
	@echo "  3. make pr-clean            Delete the fetched PR refs and all sandbox work dirs."
	@echo
	@echo "Options:"
	@echo "  BASE=master                 Branch the PR targets (default: dev)"
	@echo "  TESTS=\"tests/test_x.py -x\"  pytest arguments for pr-sandbox (default: whole suite)"
	@echo "  OPTS=\"--fail-on medium\"     Extra sandbox-pr.sh options (--python, --no-strace, --remote)"
	@echo "  CLAUDE_CMD=...              Command pr-review launches (default: claude from your zsh)"
	@echo
	@echo "Details: scripts/pr_sandbox/README.md"

_require-pr:
	@[[ "$(PR)" =~ ^[0-9]+$$ ]] || { echo "usage: make $(firstword $(MAKECMDGOALS)) PR=<number>" >&2; exit 1; }

pr-sandbox: _require-pr
	$(SANDBOX)/sandbox-pr.sh --base "$(BASE)" \
		--out "$(PR_TMP)/deepdiff-pr-$(PR)-$$(date +%Y%m%d-%H%M%S)" $(OPTS) $(PR) $(if $(TESTS),-- $(TESTS))

# Runs your `claude` from an interactive zsh so the zshrc wrapper (which switches to
# ai_agent) is used. --permission-mode dontAsk beats the user-level "auto" default: reads in
# the repo and the sandbox work dir (--add-dir), read-only commands and `gh pr view/diff`
# run without prompts; anything else is refused instead of prompting. review-settings.json
# also denies code execution, network, edits and PR-mutating gh commands outright, disables
# auto/bypass mode, and adds a hook that blocks every tool call if they're ever active.
# Nothing is written to .claude/settings.local.json, so your normal sessions keep auto mode.
pr-review: _require-pr
	@report=$$(ls -dt "$(PR_TMP)"/deepdiff-pr-$(PR)-*/report 2>/dev/null | head -1); \
	if [[ -z $$report ]]; then \
		echo "No sandbox report for PR $(PR) in $(PR_TMP). Run: make pr-sandbox PR=$(PR)" >&2; exit 1; \
	fi; \
	echo "==> reviewing PR $(PR) with report $$report"; \
	prompt=$$(sed -e "s|{PR}|$(PR)|g" -e "s|{REPORT}|$$report|g" $(SANDBOX)/review-prompt.md); \
	zsh -ic '$(CLAUDE_CMD) --permission-mode dontAsk --settings "$$1" --add-dir "$$2" "$$3"' _ \
		"$(CURDIR)/$(SANDBOX)/review-settings.json" "$$(dirname "$$report")" "$$prompt"

pr-clean:
	git for-each-ref --format='%(refname)' refs/pr-sandbox | xargs -r -n1 git update-ref -d
	rm -rf "$(PR_TMP)"/deepdiff-pr-[0-9]*-[0-9]*
