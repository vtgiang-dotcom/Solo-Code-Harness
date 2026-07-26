---
slug: stale-counts-audit
completed: 2026-07-26T13:48:00+07:00
from: gemini
---

# Stale Counts Audit Report

| File | Line | Claim in doc | Actual value | Confident? |
|---|---|---|---|---|
| [AGENTS.md](file:///d:/Project/Solo-Code-CLI/AGENTS.md) | 50 | 48 skills | 50 skills | Yes |
| [AGENTS.md](file:///d:/Project/Solo-Code-CLI/.gemini/antigravity/AGENTS.md) | 27 | 32 skills, 15 agents | 50 skills, 14 agents | Yes |
| [plugin.json](file:///d:/Project/Solo-Code-CLI/.claude-plugin/plugin.json) | 3 | "version": "3.6.0" | "version": "4.0.0" | Yes |
| [plugin.json](file:///d:/Project/Solo-Code-CLI/.claude-plugin/plugin.json) | 4 | 47 skills, 13 slash commands, 5 verification gates | 50 skills, 14 slash commands, 6/8 verification gates | Yes |
| [marketplace.json](file:///d:/Project/Solo-Code-CLI/.claude-plugin/marketplace.json) | 3 | "version": "3.6.0" | "version": "4.0.0" | Yes |
| [marketplace.json](file:///d:/Project/Solo-Code-CLI/.claude-plugin/marketplace.json) | 4 | 47 skills, 13 slash commands, 5 verification gates | 50 skills, 14 slash commands, 6/8 verification gates | Yes |
| [copilot-instructions.md](file:///d:/Project/Solo-Code-CLI/.github/copilot-instructions.md) | 5 | 44 specialized skills | 50 skills | Yes |
| [copilot-instructions.md](file:///d:/Project/Solo-Code-CLI/.github/copilot-instructions.md) | 221 | 5 engines (OpenCode, Claude, Kilo, Copilot, Gemini) | 5 engines (Kilo, Claude, jcode, Copilot, Gemini) - OpenCode removed | Yes |
| [copilot-instructions.md](file:///d:/Project/Solo-Code-CLI/.github/copilot-instructions.md) | 251 | 44 specialized skills | 50 skills | Yes |
| [copilot-instructions.md](file:///d:/Project/Solo-Code-CLI/.github/copilot-instructions.md) | 304 | Solo-Code Harness v3.2.0 | Solo-Code Harness v4.0.0 | Yes |
| [README.md](file:///d:/Project/Solo-Code-CLI/README.md) | 95 | skills (49) | skills (50) | Yes |
| [README.md](file:///d:/Project/Solo-Code-CLI/README.md) | 96 | skills (49), commands (13) | skills (50), commands (14) | Yes |
| [README.md](file:///d:/Project/Solo-Code-CLI/README.md) | 97 | skills (49) | skills (50) | Yes |
| [README.md](file:///d:/Project/Solo-Code-CLI/README.md) | 99 | skills (49) | skills (50) | Yes |
| [README.md](file:///d:/Project/Solo-Code-CLI/README.md) | 106 | OpenCode, Claude Code, Kilo, Copilot, Gemini | Kilo Code, Claude Code, jcode, GitHub Copilot, Gemini/Antigravity | Yes |
| [harness-design-intent.md](file:///d:/Project/Solo-Code-CLI/.kilo/memory/harness-design-intent.md) | 13 | 44 domain skills | 50 skills | Yes |
| [harness-design-intent.md](file:///d:/Project/Solo-Code-CLI/.kilo/memory/harness-design-intent.md) | 19 | Guard tests (80 cases, v2.6) + repro suite (4 bugs) in .opencode/ | 26 guard tests in tools/test_claude_guard.py, .opencode/ removed | Yes |
| [harness-design-intent.md](file:///d:/Project/Solo-Code-CLI/.kilo/memory/harness-design-intent.md) | 58 | Harness eval: 59/59 pass | 123/123 pass | Yes |
| [harness-design-intent.md](file:///d:/Project/Solo-Code-CLI/.kilo/memory/harness-design-intent.md) | 59 | Guard tests: 80/80 pass (v2.6) | 26/26 pass | Yes |
| [harness-design-intent.md](file:///d:/Project/Solo-Code-CLI/.kilo/memory/harness-design-intent.md) | 62 | Repro suite: 4 known bugs tracked | 0 known bugs tracked | Yes |
| [test_integration.py](file:///d:/Project/Solo-Code-CLI/tools/test_integration.py) | 91, 98 | expect 10 instructions | 10 instructions (matches filesystem count) | Yes |
| [test_integration.py](file:///d:/Project/Solo-Code-CLI/tools/test_integration.py) | 131, 138 | expect 6 prompts | 6 prompts (matches filesystem count) | Yes |
| [project-architecture.md](file:///d:/Project/Solo-Code-CLI/.gemini/antigravity/knowledge/artifacts/project-architecture.md) | 9, 14, 26 | Cấu hình sinh từ source/plugins/ | Cấu hình sinh từ .kilo/ (no source/ directory exists) | Yes |

## Ground truth counts
- **skills**: 50 (directories in `.kilo/skill/`)
- **agents**: 14 (`*.md` files in `.kilo/agents/`)
- **commands**: 14 (`*.md` files in `.kilo/command/`)
- **instructions**: 10 (`*.md` files in `.kilo/instruction/`)

## Notes
- Duplicated files: `harness-design-intent.md` is duplicated/mirrored at `.claude/memory/harness-design-intent.md` and `.copilot/memory/harness-design-intent.md`, carrying the same drifts.
- No files were unreadable; all directories and files listed in `.kilo/` and the engines were successfully scanned.
