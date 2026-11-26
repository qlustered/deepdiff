# Reviewing outside PRs. See scripts/pr_sandbox/README.md.
#
#   make pr-sandbox PR=612                  # 1. triage risky files, run the PR's tests in the sandbox
#   make pr-merge   PR=612                  #    or, for a stale PR: merge BASE into it first
#   make pr-review  PR=612                  # 2. start Claude on it: read-only, never prompts
#   make pr-push    PR=612                  # 3. after pr-merge: push the merge to the PR (asks first)
#   make pr-clean                           # 4. delete fetched PR refs and sandbox work dirs
#
# Options: BASE=master                 branch the PR targets (default: dev)
#          TESTS="tests/test_x.py -x"  pytest arguments (default: the whole suite)
#          DEPS=merge-base             take uv.lock/pyproject.toml from the PR's merge-base with BASE
#                                      instead of this checkout (for stale PRs; default: checkout)
#          OPTS="--fail-on medium"     extra sandbox-pr.sh options (--python, --no-strace, --remote ...)
#          CLAUDE_CMD=...              default: the `claude` command from your interactive zsh
# pr-merge: AGENT=0                    resolve conflicts in your editor instead of with Claude
#           REDO=1                     redo a merge you already accepted
#           COMMIT=<sha>               use a merge you made by hand

SHELL := /bin/bash
BASE ?= dev
DEPS ?= checkout
PR_TMP ?= /tmp
CLAUDE_CMD ?= claude
SANDBOX := scripts/pr_sandbox

.DEFAULT_GOAL := help
.PHONY: help pr-sandbox pr-merge pr-review pr-push pr-clean _require-pr

help:
	@echo "Reviewing an outside PR (run from your own dev checkout, in this order):"
	@echo
	@echo "  1. make pr-sandbox PR=<N>   Show the PR's changed and risky files (build config, conftest,"
	@echo "                              CI, agent config, pickles), then after you confirm, run its"
	@echo "                              tests in the network-less sandbox and report anything"
	@echo "                              suspicious. Exit status 2 = suspicious behaviour found."
	@echo "     make pr-merge   PR=<N>   Instead of pr-sandbox, for a stale PR (conflicts with BASE,"
	@echo "                              or the contributor won't rebase): merges BASE into the PR in"
	@echo "                              memory (nothing is checked out). A locked-down Claude agent"
	@echo "                              resolves the conflicts (file tools only, confined to copies"
	@echo "                              of the conflicted files); you see every resolution and accept"
	@echo "                              it. Then it commits the merge and runs pr-sandbox's checks and"
	@echo "                              tests on it, with the current dependencies."
	@echo "  2. make pr-review  PR=<N>   Start Claude on the PR and its latest sandbox report (and the"
	@echo "                              conflict resolution, after pr-merge). It can read and search"
	@echo "                              freely without asking; everything else (running code,"
	@echo "                              network, edits) is refused automatically."
	@echo "  3. make pr-push    PR=<N>   After pr-merge: push the merge commit to the PR's branch (a"
	@echo "                              fast-forward; asks first), so the PR can be merged. If"
	@echo "                              maintainers can't push there, offers to open a new PR."
	@echo "  4. make pr-clean            Delete the fetched PR refs, merges and all sandbox work dirs."
	@echo
	@echo "Options:"
	@echo "  BASE=master                 Branch the PR targets (default: dev)"
	@echo "  TESTS=\"tests/test_x.py -x\"  pytest arguments for pr-sandbox (default: whole suite)"
	@echo "  DEPS=merge-base             Install dependencies from the PR's merge-base with BASE instead"
	@echo "                              of this checkout. For stale PRs that still need a dependency"
	@echo "                              the current branch dropped (default: checkout)"
	@echo "  OPTS=\"--fail-on medium\"     Extra sandbox-pr.sh options (--python, --no-strace, --remote)"
	@echo "  CLAUDE_CMD=...              Command pr-review and pr-merge launch (default: claude from"
	@echo "                              your zsh)"
	@echo
	@echo "Options for pr-merge (plus BASE, TESTS, CLAUDE_CMD and OPTS=\"--python ... --fail-on ...\"):"
	@echo "  AGENT=0                     Resolve conflicts in your editor instead of with Claude"
	@echo "  REDO=1                      Redo a merge you already accepted"
	@echo "  COMMIT=<sha>                Test and keep a merge you made by hand (pr-merge explains"
	@echo "                              how, for conflicts it can't handle)"
	@echo
	@echo "Details: scripts/pr_sandbox/README.md"

_require-pr:
	@[[ "$(PR)" =~ ^[0-9]+$$ ]] || { echo "usage: make $(firstword $(MAKECMDGOALS)) PR=<number>" >&2; exit 1; }

pr-sandbox: _require-pr
	$(SANDBOX)/sandbox-pr.sh --base "$(BASE)" --deps-from "$(DEPS)" \
		--out "$(PR_TMP)/deepdiff-pr-$(PR)-$$(date +%Y%m%d-%H%M%S)" $(OPTS) $(PR) $(if $(TESTS),-- $(TESTS))

pr-merge: _require-pr
	$(SANDBOX)/merge-pr.py merge --base "$(BASE)" --tmp "$(PR_TMP)" --claude-cmd '$(CLAUDE_CMD)' \
		$(if $(filter 0 no,$(AGENT)),--no-agent) $(if $(filter 1 yes,$(REDO)),--redo) \
		$(if $(COMMIT),--use-commit "$(COMMIT)") \
		--out "$(PR_TMP)/deepdiff-pr-$(PR)-$$(date +%Y%m%d-%H%M%S)" $(OPTS) $(PR) $(if $(TESTS),-- $(TESTS))

pr-push: _require-pr
	$(SANDBOX)/merge-pr.py push $(PR)

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
	merge=$$(dirname "$$report"); \
	if grep -qs '^merge ' "$$report/source.txt"; then \
		merge=$$(ls -dt "$(PR_TMP)"/deepdiff-pr-$(PR)-merge-* 2>/dev/null | head -1); \
		echo "==> the report is for a merge with $(BASE); including its conflict resolution from $$merge"; \
		prompt+=$$'\n\n'$$(sed -e "s|{PR}|$(PR)|g" -e "s|{BASE}|$(BASE)|g" -e "s|{MERGE}|$$merge|g" \
			$(SANDBOX)/review-prompt-merge.md); \
	fi; \
	zsh -ic '$(CLAUDE_CMD) --permission-mode dontAsk --settings "$$1" --add-dir "$$2" --add-dir "$$3" -- "$$4"' _ \
		"$(CURDIR)/$(SANDBOX)/review-settings.json" "$$(dirname "$$report")" "$$merge" "$$prompt"

pr-clean:
	git for-each-ref --format='%(refname)' refs/pr-sandbox | xargs -r -n1 git update-ref -d
	rm -rf "$(PR_TMP)"/deepdiff-pr-[0-9]*-[0-9]*
