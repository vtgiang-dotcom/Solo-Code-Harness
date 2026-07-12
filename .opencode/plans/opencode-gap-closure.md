NHIỆM VỤ: Đưa OpenCode từ 85% lên 95%+ Kilo — Lấp 3 gap còn lại
Mục tiêu
Hoàn thiện OpenCode harness để đạt tương đương Kilo về: skill system (47/47), memory manager tự động, hookify MD engine.

=============================================================================
GIAI ĐOẠN 1 — 5 Skill Thiếu (15 phút, 0 rủi ro)
=============================================================================

Copy 5 file SKILL.md từ `.kilo/skill/` sang `.opencode/skill/`:

| # | Skill | File nguồn | File đích |
|---|-------|-----------|----------|
| 1 | `block-no-verify` | `.kilo/skill/block-no-verify/SKILL.md` | `.opencode/skill/block-no-verify/SKILL.md` |
| 2 | `git-workflow-master` | `.kilo/skill/git-workflow-master/SKILL.md` | `.opencode/skill/git-workflow-master/SKILL.md` |
| 3 | `permission-guard` | `.kilo/skill/permission-guard/SKILL.md` | `.opencode/skill/permission-guard/SKILL.md` |
| 4 | `solo-code-harness` | `.kilo/skill/solo-code-harness/SKILL.md` | `.opencode/skill/solo-code-harness/SKILL.md` |
| 5 | `task-delegation` | `.kilo/skill/task-delegation/SKILL.md` | `.opencode/skill/task-delegation/SKILL.md` |

**Verify:** `Get-ChildItem .opencode/skill/ | Measure-Object | Select-Object Count` → phải ra 47.

**Rủi ro:** Không. Copy file thuần túy.

DỪNG LẠI sau giai đoạn 1, chạy verify 47 skill trước khi tiếp tục.

=============================================================================
GIAI ĐOẠN 2 — Memory Manager Plugin (1-2 ngày)
=============================================================================

Tạo `.opencode/plugins/solocode-memory.js` — plugin tự động quản lý memory xuyên phiên.

### 2.1 Khảo sát (read-only)

Đọc các file sau để hiểu pattern:
- `.opencode/plugins/solocode-guard.js` — template plugin (cấu trúc export, cách dùng hook)
- `docs/specs/opencode-mechanisms.md` mục B — signature `tool.execute.after`, `session.start`
- `.kilo/hooks/post-tool-use/memory-manager.js` — logic enforce limit trong Kilo
- `.kilo/hooks/session/` — session start/end pattern

### 2.2 Thiết kế

Plugin export 3 hooks:

```
session.start:
  → đọc .opencode/memory/MEMORY.md
  → inject vào context (agent biết lịch sử decisions)

tool.execute.after (Write|Edit|MultiEdit):
  → nếu file được sửa là .opencode/memory/*.md
  → kiểm tra dung lượng file
  → nếu > 200 dòng → trim (giữ 50 dòng gần nhất + header)

session.end:
  → ghi summary decisions vào .opencode/memory/MEMORY.md
  → format: ### YYYY-MM-DD — Summary + danh sách decisions
```

### 2.3 Ràng buộc cứng

- KHÔNG bịa pattern mới. Memory limit logic port từ `.kilo/hooks/post-tool-use/memory-manager.js`.
- Mỗi hàm phải ghi comment truy nguyên: `// Port from .kilo/hooks/post-tool-use/memory-manager.js:XX-YY`
- Chỉ tạo 1 file `.opencode/plugins/solocode-memory.js`. Không sửa file khác.
- Đăng ký plugin trong `opencode.json` (thêm vào field `plugins` nếu cần).

### 2.4 Verify

```bash
# Test session.start hook
node -e "import('./.opencode/plugins/solocode-memory.js').then(m => console.log(Object.keys(m.default)))"
# Phải ra: ['session.start', 'tool.execute.after', 'session.end']
```

DỪNG LẠI sau giai đoạn 2, verify plugin load được trước khi tiếp tục.

=============================================================================
GIAI ĐOẠN 3 — Hookify MD Engine (3-5 ngày)
=============================================================================

Tạo hệ thống config `.opencode/hookify/*.md` cho phép user định nghĩa custom rules
bằng markdown, tự động sinh hook code.

### 3.1 Khảo sát

- `.kilo/hooks/hookify/hookify-engine.js` — engine gốc của Kilo
- `.kilo/hooks/hookify/` — format file `.md` config
- `.kilo/hooks/hooks.json` — cách đăng ký hookify hooks

### 3.2 Thiết kế kiến trúc

```
.opencode/hookify/
├── engine.js            ← plugin chính: đọc .md, parse rules, sinh hooks
├── rules/
│   ├── bash-safety.md   ← user tự viết: quy tắc an toàn bash
│   ├── file-patterns.md ← user tự viết: quy tắc file
│   └── custom.md        ← user tự viết: quy tắc tùy chỉnh
└── generated/
    └── hooks.json       ← auto-generated từ engine (cache)
```

### 3.3 Format file .md config

```markdown
---
tool: bash
priority: 1
---

# Bash Safety Rules

## Rule: Block npm cache clean
- **Pattern**: `npm cache clean --force`
- **Action**: deny
- **Message**: "npm cache clean --force destroys local cache. Use npm cache verify instead."

## Rule: Allow pytest
- **Pattern**: `python -m pytest *`
- **Action**: allow
```

### 3.4 Engine logic

1. `session.start` → quét `.opencode/hookify/rules/*.md`
2. Parse frontmatter (`tool`, `priority`) + body (rules dạng markdown table)
3. Build rule index: `Map<toolName, Rule[]>`
4. `tool.execute.before` → match command/filePath với rules → allow/deny/ask
5. Cache vào `.opencode/hookify/generated/hooks.json` để lần sau load nhanh

### 3.5 Ràng buộc

- Parse markdown dùng `gray-matter` (đã có trong `@opencode-ai/plugin`)
- Regex match port từ `.kilo/hooks/hookify/hookify-engine.js`
- Mỗi rule trong generated code phải truy nguyên được về file `.md` gốc
- Engine phải tương thích ngược: nếu không có file `.md` nào, engine vẫn load không lỗi

### 3.6 Verify

```bash
# Tạo 1 rule test
echo '---
tool: bash
---
## Rule: Test
- **Pattern**: echo test
- **Action**: allow
' > .opencode/hookify/rules/test.md

# Chạy engine test
node .opencode/hookify/engine.js --test
# Phải thấy: "Loaded 1 rule from test.md"
```

=============================================================================
DỰ KIẾN THỜI GIAN
=============================================================================

Giai đoạnThời gianĐộ khóRủi ro15 skill copy15 phút★☆☆☆☆Không có2Memory manager1-2 ngày★★☆☆☆Thấp3Hookify engine3-5 ngày★★★☆☆Trung bình**Tổng****~1 tuần**
=============================================================================
KẾT QUẢ MONG ĐỢI
=============================================================================

Sau 3 giai đoạn:

```
OpenCode: 85% → 95%+ Kilo

Trước                    Sau
42 skill                  47 skill = Kilo
Không memory manager      Memory tự động = Kilo
Không hookify engine      Hookify MD engine = Kilo
```

Gap 5% còn lại: OpenCode không có `kilo.jsonc` unified config — nhưng không đáng kể.
