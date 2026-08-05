---
description: "Run full Solo-Code verification gates: lint, schema validation, garden drift detection, harness tests, security scan. Report pass/fail for each gate."
$schema: https://raw.githubusercontent.com/github/copilot/main/schemas/prompt.schema.json
---
Run all Solo-Code verification gates:

1. `ruff check .` — Python lint
2. `python tools/check_lint_budget.py` — ratchet for the `S`/`BLE` rule families that `.ruff.toml`'s `select` omits (budget: `tools/config/lint-budget.json`)
3. `python tools/validate_schemas.py` — Agent/skill frontmatter schema validation
4. `python tools/garden.py` — .kilo ↔ .claude ↔ .copilot ↔ .gemini parity drift detection
5. `python -m pytest tools/ -q` — Full harness test suite
6. `python .github/scripts/security_scan.py .` — Hardcoded secret scan
7. `python -m pytest tools/test_claude_guard.py -q` — Guard hook destructive command tests

Report each gate result. If any gate fails, report the specific error(s) with file paths and line numbers. Do NOT proceed to fix anything — this is verification only.
