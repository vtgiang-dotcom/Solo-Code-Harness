# Solo-Code CLI

AI coding agent harness — rules, skills, hooks, and verification gates for disciplined Solo-Code engineering.

Five-engine support: **OpenCode** (`.opencode/`, primary), **Claude Code** (`.claude/` + `CLAUDE.md`), **Kilo Code** (`.kilo/`), **GitHub Copilot** (`.copilot/`), **Gemini/Antigravity** (`.gemini/`).

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

# Guard plugin tests (80 cases, v2.6)
node .opencode/tests/test-guard.mjs

# Bug reproduction suite (non-gating)
node .opencode/tests/repro/test-repro.mjs

# No-skips test policy
python .github/scripts/check_skips.py .opencode/tests/
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

# Copilot-only engine
python tools/deploy.py scaffold /path/to/new-project --engine copilot
```

Scaffold creates the directory, copies all engine configs (OpenCode + Claude Code + Kilo + Copilot + Gemini), generates `.gitignore` and `README.md`, runs `git init`, and prints post-setup instructions.

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
|---|---|
| `.opencode/` | **Primary** — OpenCode: agents (14), skills (47), plugin v2.5, commands (4), tools (2), state (5) |
| `.claude/` | Claude Code: agents (14), skills (47), commands (13), instruction (10), guard + lifecycle hooks + `settings.json`; rulebook `CLAUDE.md` at root |
| `.copilot/` | GitHub Copilot: agents (14), skills (47), commands (13), instruction (10), memory (4) |
| `.kilo/` | Kilo Code: agents (14), skills (47), hooks, memory, instruction |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (47), commands (12), knowledge |
| `.github/` | Shared scripts: `security_scan.py`, `checklist.py`, `check_skips.py`, `eval_harness.py`, `security-allowlist.txt` + `copilot-instructions.md`, `prompts/` |
| `tools/` | Generator, validator, drift detector, integration tests |
| `.vscode/` | VS Code settings + MCP config for Copilot |
| `docs/specs/` | Architecture specs, migration plans, historical docs |

## Shared State (Cross-Engine, Local-Only)

All 5 engines share a single SQLite file at `.solocode/shared-state.db` — **local-only, không commit git** (thư mục `.solocode/` đã bị `.gitignore` chặn):

- **`features`** — status + ownership (not-started / in-progress / completed / blocked)
- **`session_log`** — mỗi session được ghi lại: engine, model, files changed, verification (giữ tối đa 1000 dòng gần nhất)
- **`active_locks`** — ngăn 2 engine sửa cùng 1 file cùng lúc (tự hết hạn sau 2 giờ)
- **`shared_memory_*`** — conventions, gotchas, decisions dùng chung giữa các engine

```bash
python tools/shared_state.py show
python tools/shared_state.py features
python tools/shared_state.py locks
```

## Gates

| Gate | Command | What it checks |
|---|---|---|
| Lint | `ruff check .` | Python code style |
| Schema | `make validate` | Frontmatter validity (53 files) |
| Drift | `make garden` | .kilo ↔ .opencode parity |
| Harness Tests | `make test` | Generator (15 tests) |
| Integration | `python tools/test_integration.py` | Full .opencode/ structure (182 checks) |
| Security | `make security-scan` | Hardcoded secrets (337 files) |
| Guard | `node .opencode/tests/test-guard.mjs` | Destructive command + fuzz payloads (80 tests, v2.6) |
| No-Skips | `python .github/scripts/check_skips.py .opencode/tests/` | Unauthorized test skips (skip/skipif without reason) |
| Repro | `node .opencode/tests/repro/test-repro.mjs` | Bug reproduction suite (RED tests, non-gating) |

## OpenCode Commands

| Command | Purpose |
|---|---|
| `/verify` | Run all 6 verification gates |
| `/plan` | Delegate to planner agent |
| `/decide` | Delegate to architect agent |
| `/ship` | Pre-launch checklist |

## Copilot Setup (VS Code)

```bash
# Open project in VS Code — Copilot auto-loads:
#   .github/copilot-instructions.md   (rulebook)
#   .github/prompts/*.prompt.md       (chat commands)
#   .vscode/settings.json             (Copilot config)
#   .vscode/mcp.json                  (MCP servers)
```

**Copilot Chat Commands** — type `#` in Copilot Chat and select:

| Command | Purpose |
|---|---|
| `verify` | Run all verification gates |
| `plan` | Create an implementation plan |
| `decide` | Architectural decision record |
| `ship` | Pre-launch checklist |
| `commit` | Create conventional commit |
| `debug` | Systematic debugging workflow |

## Claude Code Setup

Claude Code loads the harness natively from generated artifacts:

```bash
# Regenerate the Claude engine from .kilo/ source
python tools/generate_harness.py --harness claude
```

| Artifact | Path | Purpose |
|---|---|---|
| Rulebook | `CLAUDE.md` | Auto-loaded project memory (boundaries + rules) |
| Subagents (14) | `.claude/agents/*.md` | Invoke via Task tool or by name |
| Skills (47) | `.claude/skills/<name>/SKILL.md` | Auto-discovered capabilities |
| Slash commands (13) | `.claude/commands/*.md` | `/verify`, `/plan`, `/decide`, `/debug`, `/commit`, … |
| Guard hook | `.claude/hooks/guard.py` + `.claude/settings.json` | `PreToolUse` — blocks destructive commands, secret leaks, protected-config edits |
| Quality-gate hook | `.claude/hooks/quality_gate.py` | `PostToolUse` (Edit/Write) — advisory ruff/prettier/biome/gofmt format check |
| Security-post hook | `.claude/hooks/security_post.py` | `PostToolUse` (Bash) — scans `git diff` for secrets after commit/push |
| Session hooks | `.claude/hooks/session_start.py`, `session_end.py` | `SessionStart`/`SessionEnd` — load git + cross-engine context; log session to shared-state |

The guard hook is a stdlib-only Python port of `solocode-guard.js` (same 33
destructive patterns + 15 secret patterns + protected config files). It blocks a
tool call by returning a `PreToolUse` deny decision and exit code 2. The
PostToolUse and Session hooks are advisory (always exit 0, never block) and are
stdlib-only Python ports of the corresponding Kilo lifecycle hooks — bringing
Claude Code to enforcement parity with the Kilo engine.

```bash
# Test the guard + lifecycle hook suites
python -m pytest tools/test_claude_guard.py tools/test_claude_hooks.py -q
```

### Launch Claude Code via FreeModel

`claude-env.ps1` loads `.env`, normalizes the gateway URL, and launches Claude Code
with a single Anthropic-compatible API key (works with [FreeModel](https://freemodel.dev)
and other gateways).

```powershell
# 1. Copy the template and fill your key
Copy-Item .env.template .env
#    then edit .env → set ANTHROPIC_API_KEY=<your-key>

# 2. Launch Claude Code with the harness environment
./claude-env.ps1

# Pass-through args work too:
./claude-env.ps1 --help
```

`.env.template` ships with the FreeModel defaults (`ANTHROPIC_BASE_URL=https://cc.freemodel.dev`)
alongside CommandCode + DeepSeek entries for OpenCode. Your real `.env` is gitignored and never deployed.

## Guard Plugin (`solocode-guard.js` v2.5)

- **33 destructive command patterns** (rm, git reset, dd, format, shutdown, chmod/chown system dirs, temp-dir destruction)
- **15 secret detection patterns** (AWS keys, JWT, GitHub tokens, DB URIs, webhooks)
- **19 protected config files** (ESLint, Prettier, Biome, Ruff, etc.)
- **Normalize stage** — strips `sudo`, `bash -c`, whitespace to defeat bypasses
- **`tool.execute.after`** — catches secrets leaked in bash output
- **`chat.message`** — auto-injects session state on startup

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

### Configuration (in `opencode.json` — already set up)

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

Plugin registers all models from `models.json` (bundled in the npm package).
Use `/models` in OpenCode to switch models.

### When key expires

```powershell
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "new-key", "User")
```

Open new PowerShell → `opencode`. No file changes needed.

## MCP Servers

| Server | Status | Purpose |
|---|---|---|
| `context7` | Active | Live library documentation lookup |
| `playwright` | Disabled | Browser E2E testing |

---

# Solo-Code CLI — Tiếng Việt

Bộ harness (dây cương) cho AI coding agent — rules, skills, hooks và verification gates dành cho kỹ thuật Solo-Code có kỷ luật.

Hỗ trợ 5 engine: **OpenCode** (`.opencode/`, chính), **Claude Code** (`.claude/` + `CLAUDE.md`), **Kilo Code** (`.kilo/`), **GitHub Copilot** (`.copilot/`), **Gemini/Antigravity** (`.gemini/`).

## Quick Start

```bash
# Mở OpenCode
opencode

# Sinh các artifact của harness
make generate

# Chạy tất cả quality gates
make check

# Gates riêng lẻ
make test              # Harness tests (15 tests)
make security-scan     # Phát hiện secret trong code
make validate          # Schema validation
make garden            # Drift detection (.kilo vs .opencode)

# Integration tests (182 checks)
python tools/test_integration.py

# Guard plugin tests (80 cases, v2.6)
node .opencode/tests/test-guard.mjs

# Bug reproduction suite (non-gating)
node .opencode/tests/repro/test-repro.mjs

# No-skips test policy
python .github/scripts/check_skips.py .opencode/tests/
```

## Scaffold & Deploy

Dùng `tools/deploy.py` để nhân bản harness này vào dự án mới hoặc dự án có sẵn.

### Scaffold — tạo dự án mới

```bash
# Tạo dự án mới kèm full harness
python tools/deploy.py scaffold /path/to/new-project

# Tuỳ chỉnh tên và mô tả
python tools/deploy.py scaffold /path/to/new-project --name my-app --description "My app"

# Chỉ engine OpenCode
python tools/deploy.py scaffold /path/to/new-project --engine opencode

# Chỉ engine Copilot
python tools/deploy.py scaffold /path/to/new-project --engine copilot
```

Scaffold tạo thư mục, copy config cho tất cả engine (OpenCode + Kilo + Copilot + Gemini), sinh `.gitignore` và `README.md`, chạy `git init`, và in hướng dẫn post-setup.

### Deploy — copy harness vào dự án có sẵn

```bash
# Copy harness vào dự án có sẵn
python tools/deploy.py deploy /path/to/existing-project

# Dry run — xem trước thay đổi mà không copy thật
python tools/deploy.py deploy . --dry-run
```

### Auto-detect

```bash
# Tự động scaffold nếu target chưa tồn tại, deploy nếu đã tồn tại
python tools/deploy.py /path/to/target
```

### Interactive mode

```bash
# Không đối số → mở wizard thiết lập tương tác
python tools/deploy.py
```

---

## Cấu trúc thư mục

| Thư mục | Mục đích |
|---|---|
| `.opencode/` | **Chính** — OpenCode: agents (14), skills (47), plugin v2.5, commands (4), tools (2), state (5) |
| `.claude/` | Claude Code: agents (14), skills (47), commands (13), instruction (10), guard hook + `settings.json`; rulebook `CLAUDE.md` ở root |
| `.copilot/` | GitHub Copilot: agents (14), skills (47), commands (13), instruction (10), memory (4) |
| `.kilo/` | Kilo Code: agents (14), skills (47), hooks, memory, instruction |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (47), commands (12), knowledge |
| `.github/` | Script dùng chung: `security_scan.py`, `checklist.py`, `eval_harness.py` + `copilot-instructions.md`, `prompts/` |
| `tools/` | Generator, validator, drift detector, integration tests |
| `.vscode/` | VS Code settings + MCP config cho Copilot |
| `docs/specs/` | Architecture specs, migration plans, historical docs |

## Verification Gates

| Gate | Lệnh | Kiểm tra |
|---|---|---|
| Lint | `ruff check .` | Python code style |
| Schema | `make validate` | Frontmatter validity (53 files) |
| Drift | `make garden` | Cân bằng .kilo ↔ .opencode |
| Harness Tests | `make test` | Generator (15 tests) |
| Integration | `python tools/test_integration.py` | Cấu trúc .opencode/ đầy đủ (182 checks) |
| Security | `make security-scan` | Secret hardcode (337 files) |
| Guard | `node .opencode/tests/test-guard.mjs` | Mẫu lệnh phá hoại + fuzz payloads (80 tests, v2.6) |
| No-Skips | `python .github/scripts/check_skips.py .opencode/tests/` | Skip/skipif không lý do |
| Repro | `node .opencode/tests/repro/test-repro.mjs` | Bug reproduction suite (RED tests, non-gating) |

## OpenCode Commands

| Lệnh | Chức năng |
|---|---|
| `/verify` | Chạy tất cả 6 verification gates |
| `/plan` | Giao việc cho planner agent |
| `/decide` | Giao việc cho architect agent |
| `/ship` | Pre-launch checklist |

## Guard Plugin (`solocode-guard.js` v2.5)

- **33 mẫu lệnh nguy hiểm** (rm, git reset, dd, format, shutdown, chmod/chown thư mục hệ thống, phá huỷ temp-dir)
- **15 mẫu phát hiện secret** (AWS keys, JWT, GitHub tokens, DB URIs, webhooks)
- **19 file config được bảo vệ** (ESLint, Prettier, Biome, Ruff, v.v.)
- **Normalize stage** — loại bỏ `sudo`, `bash -c`, khoảng trắng để chống bypass
- **`tool.execute.after`** — bắt secret rò rỉ trong output bash
- **`chat.message`** — tự động inject session state khi khởi động

## CommandCode Provider

Kết nối tới [Command Code](https://commandcode.ai) — một API key dùng được Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step và nhiều model khác.

### Thiết lập (1 lần)

```powershell
# 1. Cài plugin provider
opencode plugin commandcode-go-opencode-provider

# 2. Lưu API key vào biến môi trường Windows User
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "key-của-bạn", "User")

# 3. Mở PowerShell mới → chạy OpenCode
opencode
```

### Cấu hình (trong `opencode.json` — đã có sẵn)

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

Plugin tự động đăng ký tất cả model từ `models.json` (bundled trong npm package).
Dùng `/models` trong OpenCode để chọn model.

### Khi key hết hạn

```powershell
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "key-mới", "User")
```

Mở PowerShell mới → `opencode`. Không cần sửa file nào.

## MCP Servers

| Server | Trạng thái | Chức năng |
|---|---|---|
| `context7` | Đang chạy | Tra cứu tài liệu thư viện trực tiếp |
| `playwright` | Tắt | Browser E2E testing |
