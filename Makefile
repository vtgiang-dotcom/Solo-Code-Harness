# Solo-Code Harness — Makefile
# ==============================
# All tooling runs through `python`. No `uv`, no `pip` required.
# The harness adapter has zero dependencies beyond Python stdlib.

# Resolve Python: try python3, then python, then py (Windows launcher)
PY := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo py)

.PHONY: help generate generate-all generate-claude generate-install generate-plugin validate garden test test-integration eval check security-scan gitleaks

help:
	@echo "Solo-Code Harness — Quality Gates"
	@echo "=================================="
	@echo ""
	@echo "Development:"
	@echo "  make generate           Generate all harness artifacts"
	@echo "  make generate-claude    Generate the Claude Code engine (.claude + CLAUDE.md)"
	@echo "  make generate-install   Generate + global install (instructions to ~/.agents/)"
	@echo "  make generate-plugin P=security  Generate for one skill"
	@echo "  make validate           Validate agent/skill frontmatter schemas"
	@echo "  make garden             Drift detection (.kilo/ vs .opencode/ parity)"
	@echo "  make test               Run harness generator test suite"
	@echo "  make check              Full CI gate: lint + validate + garden + test"
	@echo ""
	@echo "Security:"
	@echo "  make security-scan      Scan for hardcoded secrets"
	@echo "  make gitleaks           Scan with gitleaks (.gitleaks.toml config)"
	@echo ""

generate:
	$(PY) tools/generate_harness.py --harness all

generate-claude:
	$(PY) tools/generate_harness.py --harness claude

generate-install:
	$(PY) tools/generate_harness.py --harness all --global-install

generate-plugin:
ifndef P
	@echo "Usage: make generate-plugin P=<skill-name>"
	@echo "Example: make generate-plugin P=security"
	@exit 1
endif
	$(PY) tools/generate_harness.py --harness all --plugin $(P)

validate:
	$(PY) tools/validate_schemas.py

garden:
	$(PY) tools/garden.py

test:
	$(PY) -m pytest tools/test_harness.py tools/test_claude_engine.py tools/test_claude_guard.py tools/test_claude_hooks.py -v

check:
	@echo "=== Lint (ruff) ==="
	ruff check . --exclude "Solo-Code-Harness" || exit 1
	@echo ""
	@echo "=== Schema Validation ==="
	$(PY) tools/validate_schemas.py || exit 1
	@echo ""
	@echo "=== Garden (drift detection) ==="
	$(PY) tools/garden.py || exit 1
	@echo ""
	@echo "=== Harness Tests ==="
	$(PY) -m pytest tools/test_harness.py tools/test_claude_engine.py tools/test_claude_guard.py tools/test_claude_hooks.py -q || exit 1
	@echo ""
	@echo "=== Security Scan ==="
	$(PY) .github/scripts/security_scan.py . || exit 1
	@echo ""
	@echo "  All gates passed."

security-scan:
	$(PY) .github/scripts/security_scan.py .

gitleaks:
	gitleaks dir . --no-banner -c .gitleaks.toml
