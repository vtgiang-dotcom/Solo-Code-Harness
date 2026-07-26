---
slug: garden-count-check
completed: 2026-07-26T14:10:00+07:00
from: gemini
---

# Garden Count Check Report

## 1. What I changed
- [tools/garden.py](file:///d:/Project/Solo-Code-CLI/tools/garden.py): Added [check_doc_counts()](file:///d:/Project/Solo-Code-CLI/tools/garden.py#L576) to verify that hardcoded counts in documentation match reality, and registered it in [main()](file:///d:/Project/Solo-Code-CLI/tools/garden.py#L670).
- [tools/test_garden.py](file:///d:/Project/Solo-Code-CLI/tools/test_garden.py): Added [test_check_doc_counts_detects_wrong_count()](file:///d:/Project/Solo-Code-CLI/tools/test_garden.py#L207) and [test_check_doc_counts_clean_when_correct()](file:///d:/Project/Solo-Code-CLI/tools/test_garden.py#L226) to verify behavior under mock structures.

## 2. Verification

| Claim | Command run | Output (trimmed) |
|---|---|---|
| New tests pass | `python -m pytest tools/test_garden.py -q` | `20 passed in 0.30s` |
| Ruff is clean on both files | `ruff check tools/garden.py tools/test_garden.py` | `All checks passed!` |
| Stale counts are reported | `python tools/garden.py` | `[DRIFT] Stale counts in documentation: ... Total drift issues: 22` |

## 3. Counts my check currently flags
- `AGENTS.md:50`: claimed 48 skills, but ground truth is 50
- `README.md:95`: claimed 49 skills, but ground truth is 50
- `README.md:96`: claimed 49 skills, but ground truth is 50
- `README.md:96`: claimed 13 commands, but ground truth is 14
- `README.md:97`: claimed 49 skills, but ground truth is 50
- `README.md:99`: claimed 49 skills, but ground truth is 50
- `README.md:99`: claimed 12 commands, but ground truth is 14
- `README.md:177`: claimed 49 skills, but ground truth is 50
- `README.md:357`: claimed 49 skills, but ground truth is 50
- `README.md:358`: claimed 49 skills, but ground truth is 50
- `README.md:358`: claimed 13 commands, but ground truth is 14
- `README.md:359`: claimed 49 skills, but ground truth is 50
- `README.md:361`: claimed 49 skills, but ground truth is 50
- `README.md:361`: claimed 12 commands, but ground truth is 14
- `.github/copilot-instructions.md:5`: claimed 44 skills, but ground truth is 50
- `.github/copilot-instructions.md:251`: claimed 44 skills, but ground truth is 50
- `.gemini/antigravity/AGENTS.md:27`: claimed 32 skills, but ground truth is 50
- `.gemini/antigravity/AGENTS.md:27`: claimed 15 agents, but ground truth is 14
- `.claude-plugin/plugin.json:4`: claimed 47 skills, but ground truth is 50
- `.claude-plugin/plugin.json:4`: claimed 13 commands, but ground truth is 14
- `.claude-plugin/marketplace.json:4`: claimed 47 skills, but ground truth is 50
- `.claude-plugin/marketplace.json:4`: claimed 13 commands, but ground truth is 14

## 4. Anything I was unsure about
nothing
