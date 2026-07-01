# Solo-Code CLI

Bộ harness (dây cương) cho AI coding agent — rules, skills, hooks và verification gates dành cho kỹ thuật Solo-Code có kỷ luật.

Hỗ trợ 3 engine: **OpenCode** (`.opencode/`, chính), **Kilo Code** (`.kilo/`), **Gemini/Antigravity** (`.gemini/`).

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

# Guard plugin tests (63 cases)
node .opencode/tests/test-guard.mjs
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
```

Scaffold tạo thư mục, copy config cho tất cả engine (OpenCode + Kilo + Gemini), sinh `.gitignore` và `README.md`, chạy `git init`, và in hướng dẫn post-setup.

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
| `.opencode/` | **Chính** — OpenCode: agents (14), skills (39), plugin v2.5, commands (4), tools (2), state (5) |
| `.kilo/` | Kilo Code: agents (14), skills (44), hooks, memory, instruction |
| `.gemini/` | Gemini/Antigravity: agents (14), skills (44), commands (12), knowledge |
| `.github/` | Script dùng chung: `security_scan.py`, `checklist.py`, `eval_harness.py` |
| `tools/` | Generator, validator, drift detector, integration tests |
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
| Guard | `node .opencode/tests/test-guard.mjs` | Mẫu lệnh phá hoại (63 tests) |

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
