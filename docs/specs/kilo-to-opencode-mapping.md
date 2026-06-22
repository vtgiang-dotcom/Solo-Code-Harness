# Kilo → OpenCode Mapping — Thiết kế cho Generator

> Tài liệu này là bản thiết kế cho `tools/generate_harness.py`.
> Mỗi loại tài sản trong `.kilo/` được mapping sang `.opencode/` dựa trên
> source code OpenCode thật tại `opencode-dev/`.

---

## 1. Skills (42 items — cần lọc trước khi copy)

⚠️ **KHÔNG copy mù 42 skills.** Nhiều skill là Kilo-specific (IDE thao tác, Kilo command, hoặc chức năng đã được plugin thay thế). Copy mù có thể mang skill vô dụng hoặc mâu thuẫn lên OpenCode.

### Nguồn: `.kilo/skill/`

```
.kilo/skill/
├── api-patterns/SKILL.md
├── brainstorming/SKILL.md
├── git-workflow-master/SKILL.md
└── ... (42 thư mục, mỗi thư mục có SKILL.md + tài nguyên đính kèm)
```

### Lưu ý: OpenCode đọc skill từ nhiều nguồn

OpenCode discover skills từ **ba nguồn**, không chỉ project directory:
1. **Project** — `.opencode/skill/` và `.opencode/skills/` (generator kiểm soát được)
2. **Global** — `~/.agents/skills/` (dùng `env.AGENTS_DIR` hoặc mặc định `~/.agents`)
3. **Built-in** — bundled trong binary OpenCode

Generator chỉ ghi vào nguồn (1). Nguồn (2) và (3) vẫn active sau generate.
Nếu global `~/.agents/skills/` có skill cũ, chúng **vẫn được load** và có thể conflict với skill project.
→ **Cần dọn thủ công** `~/.agents/skills/` sau generate. Generator không thể dọn nguồn ngoài tầm kiểm soát.

### Format Kilo (thực tế)

```markdown
---
name: git-workflow-master
description: "Structures git workflow practices. Use when..."
---

# Git Workflow and Versioning

## Overview
...
```

### Phân Loại 42 Skills (rà soát thủ công)

Generator dùng filter list `PORTABLE_SKILLS` (copy) và `SKIP_SKILLS` (bỏ qua).
Mặc định generator copy tất cả. User override bằng flag `--filter portable` hoặc
tạo file `.opencode/skill-filter.json`.

| Trạng thái | Số lượng | Danh sách | Lý do |
|---|---|---|---|
| **✅ Portable** | 37 | api-patterns, brainstorming, browser-testing-with-devtools, ci-cd-and-automation, code-review-expert, codebase-design, context-engineering, custom-deploy-workflow, debugging-and-error-recovery, deprecation-and-migration, documentation-and-adrs, domain-modeling, doubt-driven-development, file-editor-pro, frontend-ui-engineering, handoff, idea-refine, improve-codebase-architecture, incremental-implementation, interview-me, mcp-integrator, observability-and-instrumentation, performance-optimization, plan, planning-and-task-breakdown, requesting-code-review, security-and-hardening, shipping-and-launch, simplify-code, source-driven-development, spec-driven-development, spike, subagent-driven-development, systematic-debugging, testing-patterns, using-agent-skills, writing-great-skills | Mô tả chung, không gắn IDE/engine cụ thể |
| **⚠️ Kilo-specific** | 4 | `block-no-verify` (Kilo hook), `git-workflow-master` (skill tái cấu trúc), `solo-code-harness` (chỉ deploy cho Kilo, OpenCode dùng plugin riêng), `task-delegation` (dùng `agent_manager` — Kilo tool) | Nội dung tham chiếu Kilo hooks/tools/commands |
| **⛔ Plugin thay thế** | 1 | `permission-guard` | Đã có `solocode-guard.js` — chức năng chặn destructive command nằm trong plugin, không cần skill layer nữa |

**Cơ chế filter trong generator:** Mặc định skip 5 skills trên. User dùng
`--include-all` nếu muốn copy cả.

### Format OpenCode (SkillV2)

**Nguồn:** `opencode-dev/packages/core/src/config/plugin/skill.ts:19-24`
**Disk loading:** `opencode-dev/packages/core/src/skill.ts:103-133`

OpenCode discover skills từ:
- Mọi config directory → `{directory}/skill/` và `{directory}/skills/` (số nhiều)
- Mỗi skill là file `*.md` hoặc `**/SKILL.md` — OpenCode glob cả hai
- Frontmatter bắt buộc: `name` (string), optional: `description` (string), `slash` (boolean)
- Body = content của skill

```markdown
---
name: git-workflow-master
description: "Structures git workflow practices. Use when..."
---

# Git Workflow and Versioning

## Overview
...
```

### Mapping

| Khía cạnh | Kilo | OpenCode | Chuyển? |
|---|---|---|---|
| Đường dẫn | `.kilo/skill/X/SKILL.md` | `.opencode/skill/X/SKILL.md` | Copy giữ nguyên cấu trúc |
| Số nhiều | Không | OpenCode scan cả `skill/` và `skills/` | Không ảnh hưởng — dùng `skill/` |
| Frontmatter | `name`, `description` | `name`, `description`, `slash` | **TỰ ĐỘNG** — giữ nguyên, không cần sửa |
| Body | Markdown | Markdown (field `content`) | **TỰ ĐỘNG** — copy nguyên văn |
| Tài nguyên đính kèm | File cùng thư mục (scripts, templates) | Đọc từ `location` (path gốc đến SKILL.md) | **TỰ ĐỘNG** — copy toàn bộ thư mục con |
| `slash` field | Không có | Optional boolean (skill gọi bằng `/` command) | **Mặc định `false`** — generator set `slash: false` trừ khi explicit |

### Kết luận
**Copy thuần.** Không cần transform nội dung. Generator chỉ cần copy `.kilo/skill/X/` → `.opencode/skill/X/`.

---

## 2. Agents (14 items)

### Nguồn: `.kilo/agents/`

```
.kilo/agents/
├── architect.md
├── code-reviewer.md
├── solo-code-engineer.md
├── ... (14 files)
```

### Format Kilo (V1 frontmatter)

```yaml
---
mode: primary
color: "#F59E0B"
steps: 30
permission:
  read: allow
  edit: allow
  bash:
    "*": ask
  task:
    code-reviewer: allow
    "*": deny
---
```

Body = system prompt (text tự do).

### Format OpenCode (V2 frontmatter)

**Nguồn:** `opencode-dev/packages/core/src/config/agent.ts:13-25`
**Định nghĩa:** `opencode-dev/packages/core/src/config/plugin/agent.ts:15-18`

OpenCode scan: `{agent,agents}/**/*.md` và `{mode,modes}/*.md` trong mọi config directory.

V2 frontmatter fields:

| Field | Type | Required | Mặc định |
|---|---|---|---|
| `model` | string | no | — |
| `variant` | string | no | — |
| `request` | object | no | — |
| `system` | string | no | body content |
| `description` | string | no | — |
| `mode` | `"subagent" \| "primary" \| "all"` | no | `"all"` |
| `hidden` | boolean | no | `false` |
| `color` | string | no | — |
| `steps` | positive int | no | — |
| `disabled` | boolean | no | — |
| `permissions` | array (V2 Ruleset) | no | `[]` |

### Sự khác biệt — Permission field

**Kilo (V1):** `permission` là object dạng `{ "<tool>": "<action>" }` và `{ "<tool>": { "<pattern>": "<action>" } }`.

**OpenCode (V2):** `permissions` là **array** dạng `[{ action: string, resource: string, effect: "allow"|"deny"|"ask" }]`.

**Migrate Kilo V1 → OpenCode V2:**

```python
# V1 input: { "bash": { "*": "ask" }, "read": "allow" }
# V2 output: [
#   { "action": "bash", "resource": "*", "effect": "ask" },
#   { "action": "read", "resource": "*", "effect": "allow" },
# ]
```

Công thức: mỗi entry cấp 1 → action; mỗi sub-entry (pattern → effect) → một rule object.
Nguồn tham khảo: `opencode-dev/packages/core/src/v1/config/migrate.ts:75-92`

### Mapping

| Khía cạnh | Kilo | OpenCode | Chuyển? |
|---|---|---|---|
| Đường dẫn | `.kilo/agents/X.md` | `.opencode/agents/X.md` | Copy giữ nguyên |
| Frontmatter chung | `mode`, `color`, `steps`, `hidden` | Giống hệt | **TỰ ĐỘNG** |
| `permission` → `permissions` | Object V1 | Array V2 | **CẦN MIGRATE** — transform script |
| `model` | (không có trong agents Kilo hiện tại) | Optional | Bỏ qua nếu không có |
| `description` | (không có trong agents Kilo hiện tại) | Optional | Bỏ qua nếu không có |
| Body | System prompt text | `system` (nếu không có frontmatter `system`) | **TỰ ĐỘNG** |

### Kết luận
**Bán tự động.** Copy body, copy hầu hết frontmatter. Chỉ cần migrate `permission` → `permissions` array (khoảng 10 dòng transform trong generator).

---

## 3. Instructions (7 files)

### Nguồn: `.kilo/instruction/`

```
.kilo/instruction/
├── custom-framework-rules.md
├── harness-checklist.md
├── rules-database.md
├── rules-git.md
├── rules-python.md
├── rules-typescript.md
├── security-patterns.md
```

### Cơ chế OpenCode

**Nguồn config field:** `opencode-dev/packages/core/src/config.ts:95-97`
**Nguồn auto-load global:** `opencode-dev/packages/core/src/config.ts:74-78`

OpenCode có hai cơ chế nạp instructions:

**A. Auto-load từ global directory:**
OpenCode tự động load mọi file có hậu tố `.instructions.md` từ `~/.agents/instructions/` (dùng `env.AGENTS_DIR` hoặc mặc định `~/.agents`). Không cần khai báo — chỉ cần đặt file đúng tên.

```
~/.agents/instructions/
├── security-patterns.instructions.md    # ✓ tự động load
├── rules-python.instructions.md         # ✓ tự động load
└── notes.md                             # ✗ bỏ qua (sai hậu tố)
```

**B. Khai báo trong config (V2 schema):**
Field `instructions` trong `opencode.json` là array of strings (paths hoặc URLs), dùng cho file không theo convention `.instructions.md` hoặc URL remote.

```jsonc
// opencode.json — optional
{
  "instructions": [
    ".opencode/instruction/custom-format.md"  // không có hậu tố .instructions.md
  ]
}
```

### Mapping

| Khía cạnh | Kilo | OpenCode | Chuyển? |
|---|---|---|---|
| Đường dẫn | `.kilo/instruction/*.md` | `.opencode/instruction/*.md` | Copy file |
| Auto-discover | Có (Kilo đọc `.kilo/instruction/`) | **Có, qua global** `~/.agents/instructions/*.instructions.md` | **Đổi tên file** thêm hậu tố `.instructions.md` — không cần sửa config |
| Format | Markdown thuần | Markdown thuần | **TỰ ĐỘNG** |

### Kết luận
Copy file và **đổi tên** thêm hậu tố `.instructions.md` để auto-load hoạt động. Generator có thể đặt vào `.opencode/instruction/` và generator cũng copy sang `~/.agents/instructions/` (hoặc in hướng dẫn dọn thủ công). Không cần sửa `opencode.json` trừ khi muốn dùng thêm URL remote hoặc file sai convention.

---

## 4. Memory (3 files)

### Nguồn: `.kilo/memory/`

```
.kilo/memory/
├── MEMORY.md
├── harness-design-intent.md
├── project-conventions.md
```

### Cơ chế OpenCode

OpenCode **không có hệ thống memory directory tương đương**. Memory trong OpenCode được quản lý qua:
- File được ghi trong `opencode.json` references (nếu cần context dài hạn)
- Hoặc qua plugin hook (không có cơ chế built-in tương tự Kilo MEMORY.md)

### Mapping

| Khía cạnh | Kilo | OpenCode | Chuyển? |
|---|---|---|---|
| Đường dẫn | `.kilo/memory/MEMORY.md` | `.opencode/memory/MEMORY.md` | Copy (lưu trữ) |
| Auto-load | Có (Kilo đọc đầu session) | **KHÔNG** — OpenCode không có memory system | **KHÔNG** — chỉ copy để lưu giữ |
| Giải pháp | N/A | Có thể load qua `references` hoặc `instructions` hoặc plugin tùy chỉnh | **CẦN QUYẾT ĐỊNH** kiến trúc sau |

### Kết luận
Copy file để bảo tồn nhưng OpenCode không tự động dùng. Cần quyết định kiến trúc memory cho OpenCode sau (đề bài riêng). Generator vẫn copy để không mất dữ liệu.

---

## 5. Tổng Quan Generator

### Thứ tự triển khai (phased)

| Phase | Loại | Công việc | Mức độ |
|---|---|---|---|
| Phase 1 | **Skills** | Copy nguyên thư mục `.kilo/skill/X/` → `.opencode/skill/X/` | ✅ Dễ nhất |
| Phase 2 | **Agents** | Copy + migrate frontmatter `permission` → `permissions` | ⚡ Trung bình |
| Phase 3 | **Instructions** | Copy file + cập nhật `opencode.json` | ⚡ Trung bình |
| Phase 4 | **Memory** | Copy file (lưu trữ, không có auto-load) | ✅ Dễ |

### Generator signature (khớp Makefile)

```bash
# Makefile hiện tại:
make generate              # python tools/generate_harness.py --harness all
make generate-plugin P=git-workflow-master   # python tools/generate_harness.py --harness all --plugin P
```

```python
# tools/generate_harness.py
def generate_all(opencode_root: str, kilo_root: str):
    """Generate all asset types from .kilo/ → .opencode/"""
    generate_skills(kilo_root, opencode_root)
    generate_agents(kilo_root, opencode_root)
    generate_instructions(kilo_root, opencode_root)
    generate_memory(kilo_root, opencode_root)

def generate_skills(kilo_root: str, opencode_root: str, plugin_filter: str = None):
    """Copy .kilo/skill/X/ → .opencode/skill/X/"""
    ...
```

### Cross-platform

- Dùng `pathlib.Path` (Python stdlib) — hoạt động trên Windows/Linux/Mac
- Không phụ thuộc `shutil.copytree` cho skills (dùng `os.walk` + `os.makedirs` để kiểm soát)
- Permission migrate dùng dict comprehension đơn giản, không cần thư viện ngoài

---

## 6. Danh sách file output

### Skills (42)
Generator tạo `.opencode/skill/X/SKILL.md` cho mỗi skill trong `.kilo/skill/X/`, copy kèm toàn bộ thư mục con.

### Agents (14)
Generator tạo `.opencode/agents/X.md` cho mỗi agent trong `.kilo/agents/X.md`, migrate permission.

### Instructions (7)
Generator tạo `.opencode/instruction/X.md` cho mỗi file trong `.kilo/instruction/`.

### Memory (3)
Generator tạo `.opencode/memory/X.md` cho mỗi file trong `.kilo/memory/`.

### Config update — CHỈ in hướng dẫn, KHÔNG tự sửa opencode.json

Generator không được tự động sửa `opencode.json`. File này đã chứa permission rules
được sắp xếp theo findLast, git ask rules đã chốt — generator sửa có thể làm hỏng.

Generator in ra stdout block instructions để user tự dán vào:

```
=== POST-GENERATE: Add to opencode.json ===
{
  "instructions": [
    ".opencode/instruction/custom-framework-rules.md",
    ".opencode/instruction/harness-checklist.md",
    ".opencode/instruction/rules-database.md",
    ".opencode/instruction/rules-git.md",
    ".opencode/instruction/rules-python.md",
    ".opencode/instruction/rules-typescript.md",
    ".opencode/instruction/security-patterns.md"
  ]
}
============================================
```

---

## 7. Caveats Kỹ Thuật Trước Khi Code C2

### Caveat 1 — Skill bị plugin thay thế (filter list)

Generator duy trì list `SKIP_SKILLS` hardcode gồm:
- `permission-guard` — plugin `solocode-guard.js` đã thay thế
- `block-no-verify` — Kilo hook-specific
- `git-workflow-master` — Kilo `git-workflow-master` skill
- `solo-code-harness` — chỉ deploy cho Kilo
- `task-delegation` — dùng `agent_manager` (Kilo tool)

Generator vẫn hỗ trợ `--include-all` flag để copy tất cả 42 nếu user muốn.

### Caveat 2 — Migrate permission V1→V2 cho agents

Hai dạng permission Kilo:

```python
# Dạng 1: cấp 1 trực tiếp
"read": "allow"                      # → {"action": "read", "resource": "*", "effect": "allow"}

# Dạng 2: cấp 2 có pattern
"bash": {"*": "ask"}                 # → {"action": "bash", "resource": "*", "effect": "ask"}
"task": {"reviewer": "allow", "*": "deny"}  # → {"action": "task", "resource": "reviewer", "effect": "allow"},
                                            #    {"action": "task", "resource": "*", "effect": "deny"}
```

Nguồn tham khảo: `opencode-dev/packages/core/src/v1/config/migrate.ts:75-92`
Cần unit test riêng cho hàm migrate này, không chỉ chạy thử.

### Caveat 3 — KHÔNG tự sửa opencode.json

`opencode.json` chứa permission rules được sắp xếp theo findLast + git ask rules.
Generator chỉ in ra instructions block. User tự dán vào config. (Đã nêu ở mục 6.)

### Thứ tự triển khai (phased)

| Phase | Loại | Phụ thuộc | Test |
|---|---|---|---|
| Phase 1 | **Skills** (37 portable) | Không | Chạy generator, kiểm tra file tồn tại |
| Phase 2 | **Agents** (14) | Phase 1 | Unit test migrate permission, kiểm tra output |
| Phase 3 | **Instructions** (7) | Phase 1 | Kiểm tra file + in instructions block |
| Phase 4 | **Memory** (3) | Phase 1 | Kiểm tra file |
