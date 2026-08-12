# Solo-Code-Harness — Specification (SPEC) v4.1.0

> Tài liệu này mô tả harness CẦN LÀM GÌ. Khi tái tạo, agent chỉ được dùng
> SPEC này + bộ harness đang hoạt động. KHÔNG được copy file từ repo gốc.
> Bản tái tạo PHẢI vượt qua tất cả section [HARD] khi chạy `make check` không sửa đổi.
>
> Lịch sử quyết định chi tiết: `.kilo/memory/MEMORY.md` → "Decisions"
> (bản gần) + `.kilo/memory/decisions-archive.md` (bản cũ đã nén) + `git log`.
> Version của SPEC.md là version tài liệu, độc lập với `.harness.lock`'s
> `[harness] version` (engine-generation version, hiện `4.0.0`) — hai con
> số không bắt buộc phải khớp nhau.

## 0. Bản chất & phạm vi [HARD]

- Harness là bộ **cấu hình + rule + skill + script** biến AI coding agent thành
  "Solo-Code Engineer có kỷ luật". KHÔNG phải app chạy độc lập.
- Engine hỗ trợ thật (đã cài đặt + verify): **Kilo Code** (nguồn gốc),
  **Claude Code** (orchestrator, generate từ Kilo), **GitHub Copilot**
  (mirror thủ công), **Gemini/Antigravity** (mirror thủ công + human-relay
  handoff protocol, không có CLI headless).
- **OpenCode đã bị gỡ bỏ vật lý ở v4.0.0** — từng là bản mirror 100% của
  Kilo, không còn giá trị riêng sau khi Claude Code đạt full parity.
  Cursor **không** được hỗ trợ thật (không có `.cursor/`) — nếu tài liệu cũ
  còn nhắc tới, đó là aspirational, không phải hiện trạng.

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
| **External server/protocol không cần thiết** | MCP server nội bộ ôm hết tool-calling, Vector DB (Chroma) cho <100KB tri thức | Ở quy mô hiện tại, giải pháp nhẹ hơn (Bash/Grep có sẵn, SQLite FTS5 stdlib) đủ dùng — xem MEMORY.md quyết định 2026-07-24. |
| **LLM-as-judge làm cổng bảo mật chính** | Gọi LLM chấm "diff này có độc hại không" thay cho regex cứng | Non-deterministic, prompt-injectable, không unit-test được — mâu thuẫn với nguyên tắc hook phải deterministic (§3). |
| **Auto-tuning pipeline** | RL loop, hyperparameter search trên harness config | Harness là config tĩnh có chủ đích, không phải tham số cần tối ưu tự động. |

**Nguyên tắc**: Nếu một tính năng cần `pip install`, `npm install`, `docker run`,
hoặc bất kỳ bước "cài thêm" nào ngoài python3.10+/node18+/git → **KHÔNG thuộc
`tools/`/`.github/scripts/`** (những dir này phải zero-dependency, stdlib-only).

#### 0.1.1 Vùng xám: Shim mỏng thì sao?

Có một vùng hợp lệ ngay sát đường biên: **config trỏ xuống native, không clone native.**

| Hợp lệ (bên trái) | Không hợp lệ (bên phải) |
|---|---|
| `.mcp.json` — config trỏ tới MCP servers có sẵn | Tự code MCP server trong plugin |
| `kilo.jsonc` — permission rules cho bash | Tự code sandbox runtime |
| `.gitleaks.toml` — config cho công cụ có sẵn | Tự code secret scanner |

Shim mỏng = **config file (json/yaml/toml)** ra lệnh cho thứ đã tồn tại.
Nếu plugin bắt đầu chứa code tự dựng lại native capability → vượt ranh giới.

> Kiểm chứng: `python tools/garden.py` — 0 drift.

## 1. Cấu trúc thư mục [HARD]

Phải tồn tại các thư mục: `.claude/` `.copilot/` `.github/` `.gemini/` `.kilo/` `.vscode/`

> Kiểm chứng: `python .github/scripts/boundary_audit.py .` — clean.

### 1.1 File cấu hình thật (đã verify tồn tại)

| File | Mục đích | Ghi chú |
|---|---|---|
| `.harness.lock` | Ranh giới harness/project + version | Tự động generate bởi `tools/deploy.py` |
| `kilo.jsonc` | Kilo engine config | Provider, model, agent, permission |
| `CLAUDE.md` | Claude Code rulebook (ở ROOT, không phải `.claude/CLAUDE.md`) | Auto-generate từ `AGENTS.md` bởi `tools/claude_engine.py` |
| `.claude/settings.json` | Claude Code hooks + permissions | PreToolUse (`guard.py`), PostToolUse (`quality_gate.py`, `memory_gate.py`, `security_post.py`), PreCompact (`pre_compact.py`), SessionStart/SessionEnd |
| `extensions_config.json` | Extension feature flags | Mặc định TẮT một số flag |
| `.mcp.json` | MCP server config dùng chung | context7, sequential-thinking, memory, playwright |
| `.gitleaks.toml` | Git leak detection rules | Allowlist `.venv`, `node_modules` |
| `.ruff.toml` | Python lint config (KHÔNG nằm trong `pyproject.toml`) | PEP 8, E501 tắt toàn cục |
| `tools/` | Generator, validator, drift detector, integration tests, shared-state | `generate_harness.py`, `garden.py`, `test_*.py`, `deploy.py`, `validate_schemas.py`, `shared_state.py` — stdlib-only, KHÔNG deploy ra project đích |
| `.solocode/shared-state.db` | Cross-engine shared state (SQLite) | Local-only, KHÔNG commit git, chỉ dùng cho coordination state (lock/feature/session log) — KHÔNG dùng cho project memory/decisions (đó là `.kilo/memory/*.md`) |

> `opencode.json`, `docs/specs/` không còn tồn tại (đã gỡ ở v4.0.0 và
> dọn dẹp 2026-07-24 tương ứng) — nếu tài liệu khác còn nhắc, là lỗi thời.

## 2. File cấu hình hợp lệ [HARD]

- `.claude/settings.json` phải parse JSON hợp lệ.
- `kilo.jsonc` phải tồn tại và parse được.
  > Kiểm chứng: `python tools/validate_schemas.py` — 0 lỗi.

## 3. Permission Guard (cơ chế an toàn cốt lõi) [HARD]

- Guard thật nằm tại `.claude/hooks/guard.py` (Python, PreToolUse) — chặn
  bằng `sys.exit(2)` (Claude Code hard-block), KHÔNG phải file JS ở
  `.github/hooks/scripts/` (đường dẫn đó không tồn tại/đã lỗi thời).
- Bản port song song cho Kilo: `.kilo/hooks/pre-tool-use/gate-guard.js`.
- **Mọi hook phải deterministic** — không gọi LLM inline để quyết định
  block/allow (xem §0.1 loại trừ LLM-as-judge). Đây là lý do toàn bộ hook
  test được bằng pytest, chạy offline, không cần API key.
- Bộ test guard: `python -m pytest tools/test_claude_guard.py` (26 case,
  bao gồm cả ALLOW: đọc file, npm install, git status/commit, tạo file an
  toàn; và BLOCK: `rm -rf`, `git push --force`, `git reset --hard`, ghi
  `.env`/credentials/`.pem`/`.key`, v.v.)
  > Kiểm chứng: `python -m pytest tools/test_claude_guard.py -q`.

### 3.1 Secret detection — 3 bản sao phải đồng thuận [HARD]

Harness có **ba** bộ dò secret độc lập, mỗi bộ là một bản chép tay của cùng
một danh sách pattern:

| Scanner | Vai trò | Hậu quả khi bỏ lọt |
|---|---|---|
| `.claude/hooks/guard.py` | PreToolUse (Claude Code) | Secret được ghi vào file |
| `.kilo/hooks/pre-tool-use/secret-scan.js` | PreToolUse (Kilo) | Secret được ghi vào file |
| `.github/scripts/security_scan.py` | CI gate | Secret lọt vào merge |

Không có cơ chế cấu trúc nào bắt chúng phải giống nhau, và chúng **đã** lệch.
Tệ hơn, cả ba cùng mù với mọi định dạng token có tiền tố (`sk-ant-`,
`sk-proj-`, `npm_`, `glpat-`, `dop_v1_`) và dạng header `Authorization:
Bearer` — kể cả định dạng key Anthropic mà chính dự án này dùng. Nguyên nhân:
`sk-[a-zA-Z0-9]{20,}` không vượt qua dấu `-`, còn `generic_api_key` chỉ khớp
giá trị **có dấu nháy** nên dạng `KEY=sk-ant-...` trong shell/env đi thẳng qua.

`tools/test_secret_patterns.py` ghim **một corpus** vào **cả ba** scanner:
`MUST_DETECT` (11 định dạng, gồm cả regression guard cho các mẫu đã hoạt
động) và `MUST_NOT_DETECT` (7 mẫu văn xuôi/placeholder). Gate quan trọng nhất
là `test_all_three_scanners_agree` — bắt đúng loại drift "một scanner bắt
được, hai scanner kia bỏ lọt" (đã bắt thật: `github_pat_` được 2/3 scanner
nhận ra). Sửa pattern ở một file mà quên hai file kia → test đỏ.

Nguyên tắc giữ nguyên từ §7.2.1: **false positive đắt hơn bỏ sót** — ngưỡng
độ dài đặt cao hơn độ dài placeholder trong tài liệu (`sk-ant-xxxxxxxxxxxx`)
để README không kích hoạt gate.

> Kiểm chứng: `python -m pytest tools/test_secret_patterns.py -q` (65 case).

## 4. Script automation [HARD]

- `security_scan.py`: quét secret, loại trừ `.venv`/`node_modules`/build,
  chạy ra "clean" trên repo không có secret.
- Tất cả script Python trong `tools/`/`.github/scripts/` phải pass
  `ruff check .` (0 lỗi) và là stdlib-only (zero external deps).
  > Kiểm chứng: `make check` (lint + validate + garden + test + security).

## 5. Tích hợp gitleaks [HARD]

- Phải có `.gitleaks.toml` với allowlist loại `.venv`, `node_modules`,
  `gitleaks-report.json`.
- Chạy gitleaks với config này trên repo sạch → no leaks.
  > Kiểm chứng: `make gitleaks`.

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

Các năng lực phải có: code-review, debugging (≥2 hypothesis bắt buộc,
xem `/debug`), testing, file-editing, brainstorming, api-design, planning,
verify, orchestration.

> Kiểm chứng một phần tự động: `python tools/garden.py` (parity + content
> drift giữa `.kilo/` nguồn và `.claude/`/`.copilot/`/`.gemini/` mirror,
> gồm cả `check_skill_content()` — bỏ qua khác biệt frontmatter hợp lệ,
> chỉ so khớp phần body).

### 7.1 Agent resource contract

Mọi `.kilo/agents/*.md` phải có frontmatter: `description`, `mode`, và tối
thiểu một key permission (`permissions:` hoặc `permission:`).

| Loại agent | mode | Ví dụ |
|---|---|---|
| Reviewer (code-reviewer, security-auditor...) | subagent | Đọc, phân tích, báo cáo |
| Builder (solo-code-engineer, planner, architect...) | all | Tạo plan, code, kiến trúc |

### 7.2 Skill trigger validation

`python tools/validate_schemas.py` kiểm tra frontmatter mọi agent/skill.
`python tools/garden.py` kiểm tra parity + content drift, cộng 5 gate
chống "tài liệu khẳng định thứ không tồn tại" (§7.2.1). Không dependency
ngoài stdlib.

#### 7.2.1 Document-truth gates

Parity chỉ chứng minh 4 engine nói **giống nhau** — không chứng minh điều
chúng nói là **đúng**. Năm gate sau đóng khoảng trống đó; mỗi gate sinh ra
từ một lỗi thật đã sống nhiều tháng với mọi gate xanh:

| Gate | Mệnh đề kiểm tra | Lỗi đã bắt |
|---|---|---|
| `check_doc_counts()` | số đếm hardcode khớp thực tế (resolve **theo từng engine**) | `.gemini/` khai "32 skills, 15 agents" |
| `check_doc_paths()` | path trong backtick phải resolve | `.opencode/*` sót lại sau khi gỡ engine ở v4.0.0; `.claude/state/` bị gọi là "existing convention" dù `git log --all` cho thấy chưa từng tồn tại |
| `check_doc_flags()` | flag trong lệnh documented phải tồn tại | `garden.py --strict` trên script không hề đọc `sys.argv` |
| `check_enforcement_claims()` | script được mô tả là "chặn" phải có exit khác 0 | `quality-gate.js` hứa chặn khi thiếu `ALGO-CHECK`, trong khi cả 3 exit đều là `process.exit(0)` |
| `check_skill_refs()` | tên được nêu **như một skill** phải tồn tại | router `using-agent-skills` trỏ tới 5 skill chưa từng có (104 tham chiếu × 4 engine) |

Nguyên tắc thiết kế: **xác minh rộng rãi, báo lỗi hẹp.** Một gate báo bừa
sẽ bị tắt, nên false positive đắt hơn bỏ sót. Cụ thể: `check_doc_flags()`
hợp nhất `--help` cấp cao + `--help` từng subcommand + source text (parser
`sys.argv` viết tay không sinh help); `check_skill_refs()` chỉ nhận 3 dạng
có dấu hiệu tường minh — bản nháp bắt kebab-case trần cho ra 190 hit mà
gần hết là npm package và YAML key.

Giới hạn đã biết, đừng tranh luận lại nếu không có bằng chứng mới: các gate
này kiểm tra trích dẫn có **resolve**, không kiểm tra **mô tả bằng văn xuôi
có đúng**. Việc đó cần hiểu ngữ nghĩa → cần LLM → phi tất định, mà một gate
lúc bắn lúc không thì tệ hơn không có.

### 7.3 User-invoked vs Model-invoked skill classification

- **User-invoked** (`disable-model-invocation: true`): chỉ human gọi, vai
  trò orchestrator (plan, spec-driven-development, task-delegation,
  wayfinder, subagent-driven-development, shipping-and-launch,
  ci-cd-and-automation, permission-guard, requesting-code-review,
  planning-and-task-breakdown).
- **Model-invoked**: agent có thể tự động tiếp cận khi task khớp description.

### 7.4 Changelog gần đây

Lịch sử đầy đủ + lý do từng quyết định: `.kilo/memory/MEMORY.md` →
"Decisions" (bản đang hoạt động) và `.kilo/memory/decisions-archive.md`
(bản đã nén ra khỏi MEMORY.md để giữ dưới ngưỡng `memory_gate`). Các mốc
lớn kể từ v3.3.0:

- **v4.0.0**: gỡ vật lý `.opencode/` (không còn giá trị riêng); adopt
  **Kilo CLI** làm worker engine rẻ/nhanh.
- Đóng gap parity Gemini (`check_gemini()` trong `garden.py`); thêm
  file-based Claude↔Gemini/Antigravity handoff protocol
  (`.gemini/antigravity/handoff/{inbox,outbox}/`).
- Thêm `PreCompact` hook (`pre_compact.py`) + Context Summary Struct
  (`.solocode/context-checkpoint.json`, surfaced 1 lần bởi
  `session_start.py` rồi xoá).
- Thêm `memory_gate.py`/`memory-manager.js` — size gate cứng cho memory
  (WARN 4.000 / BLOCK 8.000 ký tự), cộng `garden.py`'s content-diff check
  (không chỉ existence) cho `memory/`, `instruction/`, `skill/` (bỏ qua
  frontmatter hợp lệ khác biệt theo engine).
- Thêm tầng `decisions-archive.md` — cold storage không auto-load, không
  giới hạn kích thước, cho entry bị nén ra khỏi `MEMORY.md`.
- `/debug` yêu cầu ≥2 giả thuyết trước khi test (chống confirmation bias).
- Dọn `docs/specs/` (kế hoạch OpenCode/Claude-promotion đã hoàn thành/lỗi
  thời — lịch sử đầy đủ vẫn còn trong `git log`).

## 8. Memory xuyên phiên [SOFT — nghiệm thu tay, size cap HARD]

- Mỗi nền tảng có thư mục memory riêng (`.kilo/memory/`, `.claude/memory/`,
  `.copilot/memory/`). `.kilo/memory/` là nguồn gốc; `.claude/` được
  regenerate/sync, `.copilot/` giữ song song thủ công (`garden.py` kiểm
  tra content, không chỉ tên file).
- 4 file chính: `MEMORY.md`, `project-conventions.md`,
  `harness-design-intent.md`, **`decisions-archive.md`** (mới — cold
  storage, KHÔNG auto-load, KHÔNG giới hạn kích thước).
- **`MEMORY.md`/`project-conventions.md`/`harness-design-intent.md` bị
  giới hạn cứng**: WARN ở 4.000 ký tự, BLOCK (exit 2) ở 8.000 ký tự —
  enforce bởi `.claude/hooks/memory_gate.py` (PostToolUse) và
  `.kilo/hooks/post-tool-use/memory-manager.js`. Khi chạm ngưỡng: MOVE
  (không xoá) entry cũ nhất/ít tham chiếu nhất sang `decisions-archive.md`.
- Quy ước: nạp `MEMORY.md` đầu phiên (qua rulebook/`session_start.py`),
  lệnh `/remember` để ghi. Format: YAML frontmatter `type`, `created`.
- **Không nới ngưỡng theo cửa sổ ngữ cảnh model lớn hơn** — chi phí lặp
  lại mỗi phiên, dùng chung cho engine yếu nhất (Kilo CLI); xem lý do đầy đủ
  ở MEMORY.md quyết định 2026-07-24.
  > Kiểm chứng: `python -m pytest tools/test_claude_hooks.py tools/test_garden.py -q`.

## 9. Phân loại HARD vs SOFT trong tài liệu [SOFT]

- README phải nói rõ cơ chế nào có hiệu lực kỹ thuật (enforced, exit-code
  based) vs chỉ là chỉ dẫn cho model (advisory, always exit 0). Không
  phóng đại năng lực security — xem §0.1 (loại trừ LLM-as-judge làm cổng
  chính).

## 10. Ràng buộc khi tái tạo [QUY TẮC THI]

- KHÔNG sửa test file hay hook để cho qua giả tạo.
- KHÔNG copy file từ repo gốc; chỉ dùng SPEC + harness.
- Tiêu chí ĐỖ: `make check` PASS toàn bộ (lint + schema + garden 0 drift +
  `pytest tools/` toàn bộ pass + security scan clean) + nghiệm thu tay các
  mục [SOFT].

> **Ghi chú kỹ thuật**: `verify.sh` ở root hiện là file cũ, mồ côi
> (orphaned) — không được README/CI/Makefile gọi tới, và tham chiếu các
> đường dẫn đã lỗi thời (`.github/hooks/scripts/guard.test.js` không tồn
> tại). `make check` là cơ chế verify thật đang hoạt động; `verify.sh`
> cần được dọn dẹp hoặc cập nhật ở một lượt riêng.
