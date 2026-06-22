---
description: "Run full Solo-Code verification gates: lint, schema validation, garden drift detection, harness tests, security scan. Report pass/fail for each gate."
---
Run all Solo-Code verification gates:

1. `ruff check .` — Python lint
2. `python tools/validate_schemas.py` — Agent/skill frontmatter schema validation
3. `python tools/garden.py` — .kilo ↔ .opencode parity drift detection
4. `python -m pytest tools/test_harness.py -q` — Harness generator tests (15 tests)
5. `python .github/scripts/security_scan.py .` — Hardcoded secret scan
6. `node .opencode/tests/test-guard.mjs` — Guard plugin destructive command tests (57 cases)

Report each gate result. If any gate fails, report the specific error(s) with file paths and line numbers. Do NOT proceed to fix anything — this is verification only.
