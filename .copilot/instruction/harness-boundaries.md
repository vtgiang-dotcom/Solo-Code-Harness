# Harness Boundary Rules

> **CRITICAL:** File này là một phần của Solo-Code Harness infrastructure. Nó tồn tại để bảo vệ các agent khỏi nhầm lẫn giữa code harness và code dự án.

## Tại sao cần file này?

Khi triển khai bộ harness vào một dự án mới (`python tools/deploy.py deploy ./target-project`), các thư mục `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.github/`, `.vscode/`, `tools/` được copy vào project đích (dạng runtime-only, không mang theo dev tooling của Solo-Code-CLI). Các file như `AGENTS.md`, `kilo.jsonc`, `jcode.ps1` cũng được copy. (`.opencode/` đã bị gỡ ở v4.0.0 — xem `.harness.lock`.)

**Agent có thể nhầm lẫn:** thấy các file này trong project đích và cho rằng đây là code hoặc tính năng dở dang của dự án đó.

## Boundary Markers

### 1. `.harness.lock` — marker chính

File này tồn tại ở gốc project. Nếu có mặt → project được deploy bởi Solo-Code Harness. Đọc nó để biết chính xác thư mục/file nào là harness.

### 2. `.solocode/` — marker phụ

Thư mục này là marker dành riêng cho harness, chứa config nội bộ (không phải code dự án).

### 3. Harness Boundary Table

| Nếu file/thư mục... | Thì nó là... | Hành động |
|---------------------|-------------|----------|
| Bắt đầu bằng `.kilo/`, `.copilot/`, `.gemini/`, `.claude/` | **Harness engine** | KHÔNG sửa, KHÔNG phân tích như code dự án |
| Bắt đầu bằng `.vscode/` | **Harness IDE config** | KHÔNG phải config của dự án |
| Bắt đầu bằng `.github/scripts/` | **Harness verification** | Script kiểm tra của harness |
| Bắt đầu bằng `tools/` | **Harness utilities** | `deploy.py`, `garden.py`, `generate_harness.py` |
| Bắt đầu bằng `.contracts/` | **Harness contracts** | Sub-agent status contracts |
| Là `AGENTS.md`, `kilo.jsonc`, `.mcp.json`, `.ruff.toml`, `.gitleaks.toml`, `Makefile`, `jcode.ps1`, `verify.sh`, `extensions_config.json`, `.harness.lock`, `.solocode/`, `.pre-commit-config.yaml`, `.github/pull_request_template.md`, `agent.yaml`, `pyproject.toml`, `eslint.config.js` | **Harness config** | File cấu hình agent — không phải config dự án |
| **Tất cả các file/thư mục khác** | **Project code** | Đây là code của dự án thực — được phép sửa |

## Quy tắc bắt buộc

1. **KHÔNG BAO GIỜ sửa file harness để fix bug dự án.**
2. **KHÔNG BAO GIỜ sửa file dự án để fix vấn đề harness.**
3. **Luôn đọc `.harness.lock` trước khi phân tích codebase.**
4. **Nếu bạn thấy file trong danh sách harness bị lỗi, báo cáo — đừng tự sửa.**
5. **Khi triển khai harness vào dự án mới, tất cả file harness được copy từ nguồn — không tự tạo.**

## Trường hợp đặc biệt: `Deploy` vs `Init`

- **Deploy:** Harness được copy từ repo nguồn vào project đích → các file harness đã tồn tại từ trước, không phải do dự án tạo ra.
- **Init:** Dự án mới được tạo → có thể có file trùng tên với harness (như `.gitignore`, `Makefile`) — đó là project config, không phải harness.

## Tự kiểm tra (Self-Check)

Khi phân tích bất kỳ file nào trong project, hãy tự hỏi:

> "File này có thể đã được copy vào từ Solo-Code Harness không?"

Nếu câu trả lời là "có thể" → kiểm tra `.harness.lock` trước khi hành động.
