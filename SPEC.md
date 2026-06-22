# Solo-Code-Harness — Specification (SPEC)

> Tài liệu này mô tả harness CẦN LÀM GÌ. Khi tái tạo, agent chỉ được dùng
> SPEC này + bộ harness đang hoạt động. KHÔNG được copy file từ repo gốc.
> Bản tái tạo PHẢI vượt qua tất cả section [HARD] khi chạy verify.sh không sửa đổi.

## 0. Bản chất & phạm vi [HARD]

- Harness là bộ **cấu hình + rule + skill + script** biến AI coding agent thành
  "Solo-Code Engineer có kỷ luật". KHÔNG phải app chạy độc lập.
- Hỗ trợ: GitHub Copilot, Claude Code, Cursor, Gemini, Kilo Code.

### 0.1 Ranh giới LOẠI TRỪ [HARD]

Nguyên tắc gốc: **Không clone thứ mà layer dưới đã làm và làm tốt hơn.**
Harness ngồi trên IDE/model/host — không thay thế chúng.

| LOẠI TRỪ | Ví dụ | Lý do thật |
|---|---|---|
| **Infrastructure runtime** | Docker container, VM sandbox, Kubernetes pod | Host OS + IDE đã cô lập process. Harness không phải container runtime. |
| **External server/protocol** | MCP memory server, ACP client, OpenTelemetry collector | Model provider + IDE đã có session management. Harness không phải middleware. |
| **Package registry** | Plugin marketplace, npm-style registry | Git repo đã là registry. Harness không cần package manager riêng. |
| **External service SDK** | Langfuse, AgentOps, Sentry SDK | IDE/terminal agent đã có tracing/logging nội bộ. Harness không phải observability backend. |
| **Benchmark farm** | Docker-based harness comparison, multi-model eval pipeline | Benchmark là bài toán của model provider, không phải của bộ rule+skill. |
| **Auto-tuning pipeline** | RL loop, hyperparameter search trên harness config | Harness là config tĩnh có chủ đích, không phải tham số cần tối ưu tự động. |

**Nguyên tắc**: Nếu một tính năng cần `pip install`, `npm install`, `docker run`,
hoặc bất kỳ bước "cài thêm" nào ngoài python3.8+/node18+/git → **KHÔNG thuộc harness**.

#### 0.1.1 Vùng xám: Shim mỏng thì sao?

Có một vùng hợp lệ ngay sát đường biên: **config trỏ xuống native, không clone native.**

| Hợp lệ (bên trái) | Không hợp lệ (bên phải) |
|---|---|
| `.mcp.json` — config trỏ tới MCP servers có sẵn | Tự code MCP server trong plugin |
| `kilo.jsonc` — permission rules cho bash | Tự code sandbox runtime |
| `.gitleaks.toml` — config cho công cụ có sẵn | Tự code secret scanner |

Shim mỏng = **config file (json/yaml/toml)** ra lệnh cho thứ đã tồn tại.
Nếu plugin bắt đầu chứa code tự dựng lại native capability → vượt ranh giới.

> Kiểm chứng: `python tools/garden.py` [BOUNDARY] — ERROR nếu plugin chứa
> Dockerfile, package.json, server.{ts,js,py}, requirements.txt, Cargo.toml, go.mod.

## 1. Cấu trúc thư mục [HARD]

Phải tồn tại các thư mục: .claude/ .github/ .gemini/ .kilo/ .vscode/

> Kiểm chứng: verify.sh [STRUCTURE].

### 1.1 File cấu hình mới

| File | Mục đích | Ghi chú |
|---|---|---|
| `contracts/subagent_status_contract.json` | Sub-agent status contract (DeerFlow pattern) | JSON valid; tham chiếu từ `.kilo/agents/*.md` |
| `docs/parity-ledger.md` | Sổ theo dõi khác biệt Kilo vs Claude Code | Cập nhật mỗi khi thêm tính năng một bên |
| `docs/plans/` | Kho plan có ngày (`YYYY-MM-DD-slug.md`) | Không commit draft vào gốc |
| `docs/specs/` | Kho spec/RFC (vd skill-evolution) | Có ngày, có status |
| `extensions_config.json` | Extension feature flags (mặc định TẮT) | Skill evolution, experimental features |
| `tools/parity_check.py` | Audit đồng bộ hai nhánh Kilo ↔ Claude Code | Chạy trước mỗi commit |
| `tools/accept_skill.py` | Moderation gate cho agent-evolved skills | Mặc định TẮT (cần bật flag) |
| `tools/schemas/skill_triggers.json` | Trigger accuracy test cases (≥15 case) | Dùng với `eval.py --check-triggers` |

## 2. File cấu hình hợp lệ [HARD]

- .claude/settings.json phải parse JSON hợp lệ.
- kilo.jsonc phải tồn tại và parse được.
  > Kiểm chứng: verify.sh [STRUCTURE].

## 3. Permission Guard (cơ chế an toàn cốt lõi) [HARD]

- Phải có guard tại .github/hooks/scripts/ chặn thao tác phá hủy.
- Phải có bộ test guard chạy được và đạt 29/29:
  - CHO QUA (ALLOW): đọc file, npm install, git status, git commit,
    tạo file an toàn, tool lạ, JSON sai định dạng.
  - CHẶN/HỎI (ASK): rm -rf, rm -r, rm --force, del /f, rmdir /s,
    DROP TABLE, TRUNCATE TABLE, git push --force, git reset --hard,
    git clean -fdx, mkfs, shred, dd if=, ghi .env, ghi credentials,
    ghi .pem, ghi .key, delete_file, remove_file, deleteFile.
    > Kiểm chứng: verify.sh [TESTS] guard.test.js 29/29.

## 4. Script automation [HARD]

- security_scan.py: quét secret, loại trừ .venv/node_modules/build...,
  chạy ra "clean" trên repo không có secret.
- Tất cả script Python phải pass `ruff check .` (0 lỗi).
  > Kiểm chứng: verify.sh [SECURITY] security_scan + [TESTS] ruff.

## 5. Tích hợp gitleaks [HARD]

- Phải có .gitleaks.toml với allowlist loại .venv, node_modules,
  gitleaks-report.json.
- Chạy gitleaks với config này trên repo sạch → no leaks.
  > Kiểm chứng: verify.sh [SECURITY] gitleaks.

## 6. Rulebook mỗi nền tảng [SOFT — nghiệm thu tay]

Mỗi nền tảng phải có rulebook (CLAUDE.md / copilot-instructions.md /
AGENTS.md) thể hiện các nguyên tắc:

- Phân loại request: Question / Simple edit / Complex / Destructive / Review.
- Chặn thao tác phá hủy đến khi có xác nhận rõ ràng.
- Đọc file trước khi sửa; ưu tiên exact-edit thay vì rewrite cả file.
- Socratic Gate: hỏi >=2 câu trước task phức tạp.
- Plan trước → implement → verify.
- Quy ước git commit (type: summary, lý do WHY).
  > Kiểm chứng: CHƯA tự động. Bạn rà tay khi nghiệm thu.

## 7. Skills & agents [SOFT — nghiệm thu tay]

Các năng lực phải có: code-review, debugging, testing, file-editing,
brainstorming, api-design, planning, verify, orchestration.

> Kiểm chứng: CHƯA tự động (chỉ kiểm tồn tại nếu thêm test sau).

### 7.1 Agent resource contract (DeerFlow)

Mọi `.kilo/agents/*.md` phải có frontmatter: `max_turns`, `model`, `skills`, `status_contract`.

| Loại agent | max_turns | Ví dụ |
|---|---|---|
| Reviewer (code-reviewer, security-auditor...) | 10 | Đọc, phân tích, báo cáo |
| Builder (solo-code-engineer, planner, architect...) | 20 | Tạo plan, code, kiến trúc |

Sub-agent status contract tại `contracts/subagent_status_contract.json`: valid statuses `[completed, failed, cancelled, timed_out]`.

### 7.2 Trigger accuracy eval

Skill triggering accuracy được đo bằng `python tools/eval.py --check-triggers` với bộ test tại `tools/schemas/skill_triggers.json` (≥15 case tập trung cặp dễ nhầm: plan vs planning, debug vs systematic-debugging, v.v.). Dùng keyword matching, không gọi LLM, không thêm dependency.

## 8. Memory xuyên phiên [SOFT — nghiệm thu tay]

- Mỗi nền tảng có thư mục memory riêng (`.kilo/memory/`, `.claude/memory/`).
- Quy ước: nạp memory đầu phiên, lệnh remember để ghi.
- Format thống nhất: YAML frontmatter `type`, `created`, `updated`.
- Hai nhánh mirror file chính: `MEMORY.md`, `project-conventions.md`, `harness-design-intent.md`.

## 9. Phân loại HARD vs SOFT trong tài liệu [SOFT]

- README phải nói rõ cơ chế nào có hiệu lực kỹ thuật (enforced) vs
  chỉ là chỉ dẫn cho model (advisory). Không phóng đại năng lực security.

## 10. Ràng buộc khi tái tạo [QUY TẮC THI]

- KHÔNG sửa verify.sh hay các file test để cho qua.
- KHÔNG copy file từ repo gốc; chỉ dùng SPEC + harness.
- Tiêu chí ĐỖ: verify.sh ra 11/11 PASS + nghiệm thu tay các mục [SOFT].
