# Solo-Code CLI

AI coding agent harness — rules, skills, hooks, and verification gates for disciplined Solo-Code engineering.

Triple-engine support: **OpenCode** (`.opencode/`, primary), **Kilo Code** (`.kilo/`), **Gemini/Antigravity** (`.gemini/`).

## Quick Start

```bash
# Launch OpenCode
opencode

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

## Scaffold & Deploy

Use `tools/deploy.py` to replicate this harness into new or existing projects.

### Scaffold a new project

```bash
# Create a new project from scratch with full harness
python tools/deploy.py scaffold /path/to/new-project

# Custom project name and description
python tools/deploy.py scaffold /path/to/new-project --name my-app --description "My app"

# OpenCode-only engine
python tools/deploy.py scaffold /path/to/new-project --engine opencode
```

Scaffold creates the directory, copies all engine configs (OpenCode + Kilo + Gemini), generates `.gitignore` and `README.md`, runs `git init`, and prints post-setup instructions.

### Deploy to an existing project

```bash
# Copy harness into an existing project directory
python tools/deploy.py deploy /path/to/existing-project

# Dry run — preview changes without copying
python tools/deploy.py deploy . --dry-run
```

### Auto-detect

```bash
# Auto-detect: scaffold if target missing, deploy if exists
python tools/deploy.py /path/to/target
```

### Interactive mode

```bash
# No arguments → interactive setup wizard
python tools/deploy.py
```

---

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

## CommandCode Provider

Connects to [Command Code](https://commandcode.ai) — single API key for Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step, and other models.

### Setup (1-time)

```powershell
# 1. Install the provider plugin
opencode plugin commandcode-go-opencode-provider

# 2. Save API key as Windows User environment variable
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "your-key", "User")

# 3. Open new PowerShell → launch OpenCode
opencode
```

### Cấu hình (trong `opencode.json` — đã có)

```json
"plugin": ["commandcode-go-opencode-provider/server"],
"provider": {
    "commandcode": {
        "npm": "commandcode-go-opencode-provider",
        "name": "Command Code",
        "env": ["COMMANDCODE_API_KEY"]
    }
}
```

Plugin tự động đăng ký tất cả models từ `models.json` (bundled trong npm package).
Dùng `/models` trong OpenCode để chọn model.

### Khi key hết hạn

```powershell
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "key-mới", "User")
```

Mở PowerShell mới → `opencode`. Không cần sửa file nào.

## MCP Servers

| Server | Status | Purpose |
|--------|--------|---------|
| `context7` | Active | Live library documentation lookup |
| `playwright` | Disabled | Browser E2E testing |
