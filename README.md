# Solo-Code CLI

AI coding agent harness — rules, skills, hooks, and verification gates for disciplined Solo-Code engineering.

Engine support: **Kilo Code** (`.kilo/`, source of truth — all other engine artifacts are generated from or kept in parity with it), **Claude Code** (`.claude/` + `CLAUDE.md`, orchestrator, generated from `.kilo/`), **jcode** (worker engine, DeepSeek v4 via CommandCode gateway — no dedicated dir, reads `AGENTS.md` + `.claude/skills/` + `.mcp.json` natively), **GitHub Copilot** (`.copilot/`, manually kept in parity with `.kilo/`), **Gemini/Antigravity** (`.gemini/`).

> **v4.0.0:** OpenCode engine removed. It was a 100%-parity generated mirror of `.kilo/` (verified via diff — zero content difference in agents/skills) with no unique capability once Claude Code (full agent/command parity) and jcode (faster, ~15-60x lighter RAM for concurrent DeepSeek workers) covered its runtime role. Full history in `.kilo/memory/MEMORY.md` → "Decisions".

## Quick Start

```bash
# Launch Claude Code (orchestrator) — see claude-env.ps1
./claude-env.ps1

# Launch jcode (DeepSeek worker, cost-saving)
./jcode.ps1

# Regenerate the Claude engine from .kilo/ source
python tools/generate_harness.py --harness claude

# Run all quality gates
make check

# Single gates
make test              # Harness tests
make security-scan     # Secret detection
make validate          # Schema validation (.kilo/ agents + skills)
make garden            # Drift detection (.kilo <-> .claude / .copilot)

# Integration tests (Copilot structure + shared state)
python tools/test_integration.py

# No-skips test policy
python .github/scripts/check_skips.py tools/
```

## Scaffold & Deploy

Use `tools/deploy.py` to replicate this harness into new or existing projects.
Deploy is **runtime-only**: it copies what a target project needs to actually
*run* the AI-CLI harness (agents/skills/commands/hooks/config), never
Solo-Code-CLI's own dev tooling (`deploy.py`, `garden.py`, `generate_harness.py`,
`test_*.py`), meta docs (`SPEC.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
`SECURITY.md`), CI workflows, or this repo's own accumulated memory — target
projects get fresh blank memory templates instead.

### Scaffold a new project

```bash
# Create a new project from scratch with full harness
python tools/deploy.py scaffold /path/to/new-project

# Custom project name and description
python tools/deploy.py scaffold /path/to/new-project --name my-app --description "My app"

# Kilo-only engine
python tools/deploy.py scaffold /path/to/new-project --engine kilo

# Copilot-only engine
python tools/deploy.py scaffold /path/to/new-project --engine copilot
```

Scaffold creates the directory, copies engine configs (Kilo + Claude Code + Copilot + Gemini, runtime-only — see "Deploy is runtime-only" note above), generates `.gitignore` and `README.md`, runs `git init`, and prints post-setup instructions.

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
| `.claude/` | **Orchestrator** — Claude Code: agents (14), skills (51), commands (14, incl. `ship`), instruction (10), guard + lifecycle hooks + `settings.json`; rulebook `CLAUDE.md` at root. Generated from `.kilo/` via `tools/generate_harness.py --harness claude`. |
| `.copilot/` | GitHub Copilot: agents (14), skills (51), commands (14), instruction (10), memory (4). Manually kept in parity with `.kilo/`; checked (not generated) by `tools/garden.py`. |
| `.kilo/` | **Source of truth** — Kilo Code: agents (14), skills (51), commands (14, incl. `ship`), hooks, memory, instruction. Edit here first. |
| *(jcode)* | **Worker engine** — no dedicated dir; auto-loads `AGENTS.md` + `.claude/skills/` (fallback) + `.mcp.json` natively. Launcher: `jcode.ps1`. Used for cheap/fast concurrent DeepSeek sub-tasks delegated by Claude Code. |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (51), commands (12), knowledge. Manually kept in parity with `.kilo/`; checked by `tools/garden.py`. |
| `.github/` | Shared scripts: `security_scan.py`, `checklist.py`, `check_skips.py`, `eval_harness.py`, `boundary_audit.py`, `security-allowlist.txt` + `copilot-instructions.md`, `prompts/` |
| `tools/` | Generator (`generate_harness.py`, `claude_engine.py`), validator, drift detector (`garden.py`), integration tests, `shared_state.py` (runtime dep of Claude session hooks) |
| `.vscode/` | VS Code settings + MCP config for Copilot |

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
| Schema | `make validate` | `.kilo/` agent + skill frontmatter validity |
| Drift | `make garden` | `.kilo` ↔ `.claude` (generated) / `.copilot` / `.gemini` (manual parity) |
| Document truth | `make garden` | Counts, cited paths, documented CLI flags, enforcement claims and skill references must match reality — see [SPEC.md §7.2.1](SPEC.md) |
| Harness Tests | `make test` | Generator + shared-state (`tools/test_*.py`) |
| Integration | `python tools/test_integration.py` | Copilot structure + shared state schema |
| Security | `make security-scan` | Hardcoded secrets |
| Boundary | `python .github/scripts/boundary_audit.py .` | No project files leaked into harness dirs |
| No-Skips | `python .github/scripts/check_skips.py tools/` | Unauthorized test skips (skip/skipif without reason) |

## Slash Commands (Kilo + Claude Code)

| Command | Purpose |
|---|---|
| `/verify` | Run all verification gates |
| `/plan` | Delegate to planner agent |
| `/decide` | Delegate to architect agent |
| `/ship` | Pre-launch checklist |
| `/commit` | Create conventional commit |
| `/debug` | Systematic debugging workflow |

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
| Skills (51) | `.claude/skills/<name>/SKILL.md` | Auto-discovered capabilities |
| Slash commands (14) | `.claude/commands/*.md` | `/verify`, `/plan`, `/decide`, `/ship`, `/debug`, `/commit`, … |
| Guard hook | `.claude/hooks/guard.py` + `.claude/settings.json` | `PreToolUse` — blocks destructive commands, secret leaks, protected-config edits |
| Quality-gate hook | `.claude/hooks/quality_gate.py` | `PostToolUse` (Edit/Write) — advisory ruff/prettier/biome/gofmt format check |
| Memory-gate hook | `.claude/hooks/memory_gate.py` | `PostToolUse` (Edit/Write) — caps `.claude/memory/*.md` size (WARN 4k / **hard-block 8k** chars) so memory never silently bloats every session's context; Python port of Kilo's `memory-manager.js` |
| Security-post hook | `.claude/hooks/security_post.py` | `PostToolUse` (Bash) — scans `git diff` for secrets after commit/push |
| Pre-compact hook | `.claude/hooks/pre_compact.py` | `PreCompact` — logs a git-state checkpoint to shared-state and reminds Claude to persist any settled decision to `.kilo/memory/MEMORY.md` before context is summarized/cleared |
| Session hooks | `.claude/hooks/session_start.py`, `session_end.py` | `SessionStart`/`SessionEnd` — load git + cross-engine context; log session to shared-state |

The guard hook is a stdlib-only Python port of the Kilo `gate-guard.js`/`secret-scan.js`
lifecycle hooks (33 destructive patterns + 21 secret patterns + protected config
files). It blocks a tool call by returning a `PreToolUse` deny decision and exit
code 2. The memory-gate hook can also hard-block (exit code 2) when a memory
file exceeds 8,000 chars. The remaining PostToolUse/Session hooks are advisory
(always exit 0, never block) — together bringing Claude Code to enforcement
parity with the Kilo engine. `garden.py`'s memory-drift check also diffs
`.claude/memory/*.md` content against `.kilo/memory/` (the source of truth),
not just filenames, so a silently out-of-sync mirror is always caught.

```bash
# Test the guard + lifecycle hook suites
python -m pytest tools/test_claude_guard.py tools/test_claude_hooks.py -q
```

### Launch Claude Code via FreeModel

`claude-env.ps1` loads `.env`, normalizes the gateway URL, and launches Claude Code
with profile-based behavior:

- `gateway` (default): FreeModel / third-party gateways via `--bare`
- `native`: full mode, prefer `ANTHROPIC_API_KEY` / `apiKeyHelper` if present
- `kilo`: full mode alias for IDE-integrated Kilo workflows

```powershell
# 1. Copy the template and fill your key
Copy-Item .env.template .env
#    then edit .env → set ANTHROPIC_API_KEY=<your-key>

# 2. Launch Claude Code with the default gateway profile
./claude-env.ps1

# 3. Optional profiles
./claude-env.ps1 --profile native
./claude-env.ps1 --profile kilo

# Pass-through args still work:
./claude-env.ps1 --help
```

`.env.template` ships with 3 FreeModel VIP tiers (`cc.freemodel.dev`, `api-cc.freemodel.dev`, `cc-t2.freemodel.dev`)
alongside a `COMMANDCODE_API_KEY` entry shared with jcode. Your real `.env` is gitignored and never deployed. The default `gateway` profile restores `CLAUDE.md` discovery with `--add-dir .`, but Claude Code still skips hooks and auto-memory in `--bare` mode.

## jcode Setup (DeepSeek Worker Engine)

`jcode.ps1` launches [jcode](https://github.com/1jehuang/jcode) as a stateless
worker orchestrated by Claude Code. CommandCode is restricted to
`deepseek/deepseek-v4-pro`; GPT workers use the FreeModel OpenAI-compatible
gateway through Chat Completions.

```powershell
# 1. Make sure .env has COMMANDCODE_API_KEY set (see FreeModel setup above)

# 2. Launch jcode
./jcode.ps1

# 3. DeepSeek remains the default worker
./jcode.ps1 "your task"

# 4. Stronger workers selected by Claude Code
./jcode.ps1 gpt-5.6-sol "review this complex implementation"
./jcode.ps1 gpt-5.6-terra "provide an independent second opinion"

# 5. If the launcher warns that ~/.jcode/config.toml still pins the retired
#    deepseek-v4-flash tier (any `jcode run` without --model would use it),
#    this rewrites it to the supported model, backing up to config.toml.bak
./jcode.ps1 -RepairConfig
```

Supported FreeModel choices: `gpt-5.6-sol` and `gpt-5.6-terra`. Set
`OPENAI_API_KEY` and one
host-root `OPENAI_BASE_URL` in `.env`: `work.freemodel.dev`,
`api.freemodel.dev`, or `api-t2-sg.freemodel.dev`. Do not append
`/v1/chat/completions` or `/v1/responses`; the launcher normalizes the host and
configures jcode's `freemodel-openai` profile at `/v1`.

Recommended Claude Code worker routing:

| Task | Worker model | Provider path |
|---|---|---|
| Routine, small, well-scoped coding | `deepseek/deepseek-v4-pro` | CommandCode (default) |
| Complex implementation, difficult debugging, review, verification | `gpt-5.6-sol` | FreeModel |
| Independent second opinion / fallback | `gpt-5.6-terra` | FreeModel |

Examples:

```powershell
./jcode.ps1 gpt-5.6-sol "analyze and verify this difficult change"
./jcode.ps1 gpt-5.6-terra "independently challenge this conclusion"
```

jcode has no dedicated harness directory — it auto-loads `AGENTS.md` (project
rules) and falls back to `.claude/skills/` for skill discovery, and reads
`.mcp.json` for MCP servers natively. No porting/mirroring needed.

Connects to [Command Code](https://commandcode.ai) — single API key for Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step, and other models.

## Gemini/Antigravity Handoff (manual, file-based)

Antigravity IDE has no headless CLI, so Claude Code cannot invoke it
directly (unlike jcode). Instead of copy-pasting plan/result text through
chat, use the file-based protocol in `.gemini/antigravity/handoff/`:
Claude writes a plan to `handoff/inbox/<slug>-plan.md`, you relay one line
to Antigravity ("read this plan, write your report to
`handoff/outbox/<slug>-report.md`"), and `.claude/hooks/session_start.py`
auto-detects the new report at Claude's next session start. Full protocol:
`.gemini/antigravity/handoff/README.md`.

### Which worker gets which job

Claude Code proposes a worker on its own when the shape fits — you should
not have to remember these exist. `session_start.py` announces each
engine's availability at session start.

| Work shape | Route to | Why |
|---|---|---|
| Read >5 files, then summarize/compare/audit | **Gemini** | ~20x context leverage (measured) |
| Repo-wide survey — "where else does X appear?" | **Gemini** | Breadth is its edge |
| Independent review of a design or diff | **Gemini** | A second model catches different things |
| UI verification, screenshots, recordings | **Gemini** | Claude Code cannot do this at all |
| Small mechanical edit, boilerplate, one test | **jcode** | Headless — costs you nothing |
| Architecture / product / security decisions | **Neither** | Judgment is not delegable |
| Anything needing the session's history | **Neither** | Both workers are context-blind |

jcode is headless, so Claude just uses it. Gemini needs you to relay the
task through the IDE, so Claude asks first.

**Everything both workers return is verified.** In controlled tests each
shipped an error that was invisible in its own summary — a wrong finding
marked "Confident: Yes", and two false positives reported as "unsure
about: nothing". Their evidence is reliable; their self-assessment is not.
Full guides: `.kilo/skill/gemini-delegation/SKILL.md`,
`.kilo/skill/jcode-delegation/SKILL.md`.

## MCP Servers

| Server | Status | Purpose |
|---|---|---|
| `context7` | Active | Live library documentation lookup |
| `playwright` | Disabled | Browser E2E testing |

---

# Solo-Code CLI — Tiếng Việt

Bộ harness (dây cương) cho AI coding agent — rules, skills, hooks và verification gates dành cho kỹ thuật Solo-Code có kỷ luật.

Hỗ trợ engine: **Kilo Code** (`.kilo/`, nguồn gốc — mọi engine khác được sinh ra từ đây hoặc giữ song song), **Claude Code** (`.claude/` + `CLAUDE.md`, điều phối, sinh từ `.kilo/`), **jcode** (worker chạy DeepSeek v4 qua CommandCode — không cần thư mục riêng), **GitHub Copilot** (`.copilot/`, giữ song song thủ công với `.kilo/`), **Gemini/Antigravity** (`.gemini/`).

> **v4.0.0:** đã gỡ engine OpenCode. Nó từng là bản mirror sinh 100% từ `.kilo/` (đã verify bằng diff, không khác biệt nội dung), không còn giá trị riêng khi Claude Code (parity đầy đủ agent/command) và jcode (nhanh hơn, nhẹ RAM hơn ~15-60x cho worker DeepSeek đồng thời) đã lấp vai trò runtime của nó. Lịch sử đầy đủ trong `.kilo/memory/MEMORY.md` → "Decisions".

## Bắt đầu nhanh

```bash
# Mở Claude Code (điều phối) — xem claude-env.ps1
./claude-env.ps1

# Mở jcode (worker DeepSeek, tiết kiệm chi phí)
./jcode.ps1

# Sinh lại engine Claude từ nguồn .kilo/
python tools/generate_harness.py --harness claude

# Chạy tất cả quality gates
make check

# Gates riêng lẻ
make test              # Harness tests
make security-scan     # Phát hiện secret trong code
make validate          # Schema validation (.kilo/ agents + skills)
make garden            # Drift detection (.kilo <-> .claude / .copilot)

# Integration tests (cấu trúc Copilot + shared state)
python tools/test_integration.py

# No-skips test policy
python .github/scripts/check_skips.py tools/
```

## Scaffold & Deploy

Dùng `tools/deploy.py` để nhân bản harness này vào dự án mới hoặc dự án có sẵn.
Deploy chỉ mang theo **phần runtime cần để chạy harness** (agents/skills/commands/
hooks/config) — không mang theo công cụ dev của Solo-Code-CLI (`deploy.py`,
`garden.py`, `generate_harness.py`, `test_*.py`), tài liệu nội bộ (`SPEC.md`,
`CONTRIBUTING.md`...), CI workflows, hay bộ nhớ tích luỹ của chính repo này —
dự án đích nhận memory template rỗng để tự ghi quy ước riêng.

### Scaffold — tạo dự án mới

```bash
# Tạo dự án mới kèm full harness
python tools/deploy.py scaffold /path/to/new-project

# Tuỳ chỉnh tên và mô tả
python tools/deploy.py scaffold /path/to/new-project --name my-app --description "My app"

# Chỉ engine Kilo
python tools/deploy.py scaffold /path/to/new-project --engine kilo

# Chỉ engine Copilot
python tools/deploy.py scaffold /path/to/new-project --engine copilot
```

Scaffold tạo thư mục, copy config engine (Kilo + Claude Code + Copilot + Gemini, chỉ phần runtime), sinh `.gitignore` và `README.md`, chạy `git init`, và in hướng dẫn post-setup.

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
| `.claude/` | **Điều phối** — Claude Code: agents (14), skills (51), commands (14, gồm `ship`), instruction (10), guard + lifecycle hooks + `settings.json`; rulebook `CLAUDE.md` ở root. Sinh từ `.kilo/` qua `tools/generate_harness.py --harness claude`. |
| `.copilot/` | GitHub Copilot: agents (14), skills (51), commands (14), instruction (10), memory (4). Giữ song song thủ công với `.kilo/`; `tools/garden.py` chỉ kiểm tra, không tự sinh. |
| `.kilo/` | **Nguồn gốc** — Kilo Code: agents (14), skills (51), commands (14, gồm `ship`), hooks, memory, instruction. Sửa ở đây trước tiên. |
| *(jcode)* | **Worker engine** — không có thư mục riêng; tự load `AGENTS.md` + `.claude/skills/` (fallback) + `.mcp.json`. Launcher: `jcode.ps1`. |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (51), commands (12), knowledge. Manually kept in parity with `.kilo/`; checked by `tools/garden.py`. |
| `.github/` | Script dùng chung: `security_scan.py`, `checklist.py`, `check_skips.py`, `eval_harness.py`, `boundary_audit.py` + `copilot-instructions.md`, `prompts/` |
| `tools/` | Generator (`generate_harness.py`, `claude_engine.py`), validator, drift detector (`garden.py`), integration tests, `shared_state.py` (runtime dep của Claude session hooks) |
| `.vscode/` | VS Code settings + MCP config cho Copilot |

## Verification Gates

| Gate | Lệnh | Kiểm tra |
|---|---|---|
| Lint | `ruff check .` | Python code style |
| Schema | `make validate` | Frontmatter agent + skill trong `.kilo/` |
| Drift | `make garden` | `.kilo` ↔ `.claude` (sinh tự động) / `.copilot` / `.gemini` (giữ song song thủ công) |
| Document truth | `make garden` | Số đếm, path trích dẫn, flag CLI, tuyên bố "chặn" và tên skill phải khớp thực tế — xem [SPEC.md §7.2.1](SPEC.md) |
| Harness Tests | `make test` | Generator + shared-state (`tools/test_*.py`) |
| Integration | `python tools/test_integration.py` | Cấu trúc Copilot + schema shared state |
| Security | `make security-scan` | Secret hardcode |
| Boundary | `python .github/scripts/boundary_audit.py .` | Không có file dự án lẫn vào thư mục harness |
| No-Skips | `python .github/scripts/check_skips.py tools/` | Skip/skipif không lý do |

## Slash Commands (Kilo + Claude Code)

| Lệnh | Chức năng |
|---|---|
| `/verify` | Chạy tất cả verification gates |
| `/plan` | Giao việc cho planner agent |
| `/decide` | Giao việc cho architect agent |
| `/ship` | Pre-launch checklist |
| `/commit` | Tạo conventional commit |
| `/debug` | Quy trình debug có hệ thống |

## Claude Code Setup

```bash
# Sinh lại engine Claude từ nguồn .kilo/
python tools/generate_harness.py --harness claude
```

Guard hook là bản port stdlib-only Python từ `gate-guard.js`/`secret-scan.js` của
Kilo (33 mẫu lệnh nguy hiểm + 15 mẫu secret + danh sách file config được bảo vệ).
Hook mới `memory_gate.py` (`PostToolUse`, bản port của `memory-manager.js`)
chặn cứng (exit 2) khi `.claude/memory/*.md` vượt 8.000 ký tự, tránh memory
phình to âm thầm và tốn context mỗi phiên. Các PostToolUse/Session hook còn
lại chỉ mang tính khuyến nghị (luôn exit 0) — đưa Claude Code lên ngang hàng
enforcement với Kilo. `PreCompact` hook (`pre_compact.py`) ghi checkpoint
git-state vào shared-state và nhắc lưu quyết định đã chốt vào
`.kilo/memory/MEMORY.md` trước khi context bị nén/tóm tắt. `garden.py` nay
cũng so khớp nội dung (không chỉ tên file) giữa `.claude/memory/` và
`.kilo/memory/` (nguồn gốc sự thật) để bắt drift âm thầm.

```bash
# Test bộ guard + lifecycle hook
python -m pytest tools/test_claude_guard.py tools/test_claude_hooks.py -q
```

### Chạy Claude Code qua FreeModel

```powershell
Copy-Item .env.template .env
#    rồi sửa .env → ANTHROPIC_API_KEY=<key-của-bạn>
./claude-env.ps1
```

## jcode Setup (Worker DeepSeek)

`jcode.ps1` chạy [jcode](https://github.com/1jehuang/jcode) như một worker tối
ưu chi phí/độ trễ, do Claude Code điều phối cho các sub-task chạy đồng thời.
Tự đồng bộ `COMMANDCODE_API_KEY` từ `.env` vào provider profile của jcode mỗi lần chạy.

```powershell
# 1. Đảm bảo .env đã có COMMANDCODE_API_KEY

# 2. Chạy jcode
./jcode.ps1

# 3. Hoặc chạy 1 task không tương tác (Claude Code dùng khi điều phối)
jcode run --provider-profile commandcode --model deepseek/deepseek-v4-pro "task của bạn"
```

jcode không có thư mục harness riêng — tự load `AGENTS.md` + fallback sang
`.claude/skills/` + đọc `.mcp.json` — không cần port/mirror gì thêm.

Kết nối tới [Command Code](https://commandcode.ai) — một API key dùng được Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step và nhiều model khác.

## Handoff Gemini/Antigravity (thủ công, qua file)

Antigravity IDE không có CLI headless nên Claude Code không thể gọi trực
tiếp như jcode. Thay vì copy-paste kế hoạch/kết quả qua chat, dùng giao thức
file trong `.gemini/antigravity/handoff/`: Claude ghi kế hoạch vào
`handoff/inbox/<slug>-plan.md`, bạn chỉ cần chuyển 1 dòng cho Antigravity
("đọc plan này, ghi report vào `handoff/outbox/<slug>-report.md`"), và
`.claude/hooks/session_start.py` sẽ tự phát hiện report mới ở phiên Claude
kế tiếp. Chi tiết: `.gemini/antigravity/handoff/README.md`.

### Giao việc cho ai

Claude Code tự đề xuất worker khi gặp việc phù hợp — bạn không cần nhớ là
chúng tồn tại. `session_start.py` thông báo engine nào đang sẵn sàng ở đầu
mỗi phiên.

| Dạng công việc | Giao cho | Lý do |
|---|---|---|
| Đọc >5 file rồi tóm tắt/so sánh/rà soát | **Gemini** | Đòn bẩy ngữ cảnh ~20x (đã đo) |
| Khảo sát toàn repo — "chỗ nào khác dùng X?" | **Gemini** | Bề rộng là thế mạnh của nó |
| Review độc lập một thiết kế hoặc diff | **Gemini** | Model khác bắt được lỗi khác |
| Kiểm chứng UI, chụp màn hình, quay video | **Gemini** | Claude Code hoàn toàn không làm được |
| Sửa cơ học nhỏ, boilerplate, một test | **jcode** | Headless — không tốn công bạn |
| Quyết định kiến trúc / sản phẩm / bảo mật | **Không giao** | Phán đoán không ủy quyền được |
| Việc cần lịch sử hội thoại của phiên | **Không giao** | Cả hai worker đều mù ngữ cảnh |

jcode chạy headless nên Claude dùng luôn. Gemini cần bạn chuyển đề bài qua
IDE nên Claude sẽ hỏi trước.

**Mọi kết quả từ cả hai worker đều được kiểm chứng.** Trong các bài test có
kiểm soát, mỗi bên đều trả về ít nhất một lỗi mà chính bản tóm tắt của nó
không hề lộ ra — một phát hiện sai bị đánh dấu "Confident: Yes", và hai
false positive kèm câu "không có gì không chắc". Bằng chứng nó đưa ra thì
đáng tin; phần nó tự đánh giá thì không.

## MCP Servers

| Server | Trạng thái | Chức năng |
|---|---|---|
| `context7` | Đang chạy | Tra cứu tài liệu thư viện trực tiếp |
| `playwright` | Tắt | Browser E2E testing |

## License / Giấy phép

MIT — see [`LICENSE`](LICENSE). / MIT — xem file [`LICENSE`](LICENSE).
