# Solo-Code CLI

AI coding agent harness — rules, skills, hooks, and verification gates for disciplined Solo-Code engineering.

Triple-engine support: **OpenCode** (`.opencode/`, primary), **Kilo Code** (`.kilo/`), **Gemini/Antigravity** (`.gemini/`).

## Quick Start

```bash
# Launch OpenCode with all features enabled
.\opencode.ps1

# Generate harness artifacts
make generate

# Run all quality gates
make check

# Single gates
make test              # Harness tests (15 tests)
make security-scan     # Secret detection
make validate          # Schema validation
make garden            # Drift detection (.kilo vs .opencode)

# Integration tests (182 checks)
python tools/test_integration.py

# Guard plugin tests (63 cases)
node .opencode/tests/test-guard.mjs
```

## Structure

| Directory | Purpose |
|-----------|---------|
| `.opencode/` | **Primary** — OpenCode: agents (14), skills (39), plugin v2.5, commands (4), tools (2), state (5) |
| `.kilo/` | Kilo Code: agents (14), skills (44), hooks, memory, instruction |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (44), commands (12), knowledge |
| `.github/` | Shared scripts: `security_scan.py`, `checklist.py`, `eval_harness.py` |
| `tools/` | Generator, validator, drift detector, integration tests |
| `docs/specs/` | Architecture specs, migration plans, historical docs |

## Gates

| Gate | Command | What it checks |
|------|---------|----------------|
| Lint | `ruff check .` | Python code style |
| Schema | `make validate` | Frontmatter validity (53 files) |
| Drift | `make garden` | .kilo ↔ .opencode parity |
| Harness Tests | `make test` | Generator (15 tests) |
| Integration | `python tools/test_integration.py` | Full .opencode/ structure (182 checks) |
| Security | `make security-scan` | Hardcoded secrets (337 files) |
| Guard | `node .opencode/tests/test-guard.mjs` | Destructive command patterns (63 tests) |

## OpenCode Commands

| Command | Purpose |
|---------|---------|
| `/verify` | Run all 6 verification gates |
| `/plan` | Delegate to planner agent |
| `/decide` | Delegate to architect agent |
| `/ship` | Pre-launch checklist |

## Guard Plugin (`solocode-guard.js` v2.5)

- **33 destructive command patterns** (rm, git reset, dd, format, shutdown, chmod/chown system dirs, temp-dir destruction)
- **15 secret detection patterns** (AWS keys, JWT, GitHub tokens, DB URIs, webhooks)
- **19 protected config files** (ESLint, Prettier, Biome, Ruff, etc.)
- **Normalize stage** — strips `sudo`, `bash -c`, whitespace to defeat bypasses
- **`tool.execute.after`** — catches secrets leaked in bash output
- **`chat.message`** — auto-injects session state on startup

## MCP Servers

| Server | Status | Purpose |
|--------|--------|---------|
| `context7` | Active | Live library documentation lookup |
| `playwright` | Disabled | Browser E2E testing |
