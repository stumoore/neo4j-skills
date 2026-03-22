# neo4j-skills Makefile
# Usage: make <target>
#
# Harness runs write JSON reports to skill-generation-validation-tools/tests/results/
# and Markdown reports alongside them (same stem, .md extension).
# Pass WORKERS=N for parallel Claude invocations, e.g.: make test-all WORKERS=4

HARNESS   := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py
REPORTER  := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/reporter.py
ANALYZER  := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/analyze-results.py
SKILL     := neo4j-cypher-authoring-skill
CASES_DIR := skill-generation-validation-tools/tests/cases
RESULTS   := skill-generation-validation-tools/tests/results
WORKERS   ?= 5

TIMESTAMP := $(shell date +%Y%m%d-%H%M%S)

# ── Validation (no DB / no Claude) ─────────────────────────────────────────────

.PHONY: dry-run
dry-run:  ## Validate all YAML test cases (no DB, no Claude)
	$(HARNESS) --cases $(CASES_DIR) --skill $(SKILL) --dry-run

.PHONY: test-extract
test-extract:  ## Run the reference extraction unit tests
	cd skill-generation-validation-tools && uv run python3 scripts/test-extract-references.py

.PHONY: smoke
smoke:  ## Smoke-test validator, reporter, and analyzer (no DB needed)
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/validator.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/reporter.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/analyze-results.py

# ── Per-domain harness runs ────────────────────────────────────────────────────

.PHONY: test-companies
test-companies:  ## Run companies domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/companies.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/companies-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/companies-run-$(TIMESTAMP).md"

.PHONY: test-recommendations
test-recommendations:  ## Run recommendations domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/recommendations.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/recommendations-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/recommendations-run-$(TIMESTAMP).md"

.PHONY: test-ucfraud
test-ucfraud:  ## Run ucfraud domain (bolt://localhost:7687, writeable, Neo4j 2026.02.1)
	$(HARNESS) \
	  --cases $(CASES_DIR)/ucfraud.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/ucfraud-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/ucfraud-run-$(TIMESTAMP).md"

.PHONY: test-all
test-all:  ## Run all domains sequentially (companies → recommendations → ucfraud)
	@echo "=== companies ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/companies.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	@echo "=== recommendations ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/recommendations.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	@echo "=== ucfraud ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/ucfraud.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose
	@echo "=== generating reports ==="
	$(REPORTER) \
	  --input $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/companies-run-$(TIMESTAMP).md
	$(REPORTER) \
	  --input $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/recommendations-run-$(TIMESTAMP).md
	$(REPORTER) \
	  --input $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/ucfraud-run-$(TIMESTAMP).md
	@echo "\n→ All reports written to $(RESULTS)/"

# ── Difficulty-filtered runs ───────────────────────────────────────────────────

.PHONY: test-basic
test-basic:  ## Run only basic-difficulty cases across all domains
	$(HARNESS) \
	  --cases $(CASES_DIR) \
	  --skill $(SKILL) \
	  --difficulty basic \
	  --report $(RESULTS)/basic-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose

.PHONY: test-expert
test-expert:  ## Run only expert-difficulty cases across all domains
	$(HARNESS) \
	  --cases $(CASES_DIR) \
	  --skill $(SKILL) \
	  --difficulty expert \
	  --report $(RESULTS)/expert-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --verbose

# ── Analysis ───────────────────────────────────────────────────────────────────

.PHONY: analyze
analyze:  ## Analyze latest results in tests/results/ and write combined report
	$(ANALYZER) \
	  --input $(RESULTS) \
	  --output $(RESULTS)/analysis-$(TIMESTAMP).md
	@echo "\n→ $(RESULTS)/analysis-$(TIMESTAMP).md"

.PHONY: report-latest
report-latest:  ## Re-render Markdown reports from the 3 most recent JSON files
	@for f in $$(ls -t $(RESULTS)/*.json | head -3); do \
	  md="$${f%.json}.md"; \
	  echo "Rendering $$md ..."; \
	  $(REPORTER) --input $$f --output $$md; \
	done

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-24s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
