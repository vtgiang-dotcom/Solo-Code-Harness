# OpenCode Gap Closure — Plan v2 (reviewed 2026-07-13)

## Trạng thái hiện tại

```
OpenCode feature parity với Kilo:
  Skills:      47/47  ✅ (G1 done)
  Instructions: 9/9   ✅
  Agents:       14/14 ✅
  Memory:        3/3  ✅ (copy, no manager)
  Plugin:        1    ✅ (solocode-guard.js v2.5)
  Hookify:       None ❌ (Kilo has .kilo/hookify/ engine)
  Memory mgr:    None ❌ (Kilo has .kilo/hooks/post-tool-use/memory-manager.js)
```

## Gap phân tích — thực tế vs plan cũ

### G2 — Memory Manager: cần thiết kế lại toàn bộ

| Vấn đề | Plan cũ sai | Thực tế |
|--------|-----------|---------|
| `session.start` / `session.end` hooks | Plan cũ dùng `session.start` để load memory, `session.end` để ghi summary | **OpenCode không có session lifecycle hooks.** Chỉ có `chat.message`, `tool.execute.before`, `tool.execute.after`. |
| Inject vào context | Plan cũ nói "inject vào context" | Plugin không thể inject trực tiếp vào agent context. Chỉ có thể return `chat.message` metadata hoặc dùng `experimental.*` hooks. |
| Trim >200 dòng | Hợp lý về mặt logic | Memory file trong Solo-Code là file markdown nhỏ, gần như không bao giờ vượt 200 dòng. Value của tính năng này thấp. |
| 1-2 ngày estimate | Quá cao | Thực tế: không làm được như plan cũ (thiếu hook). Để làm được cần chấp nhận workaround hoặc đợi OpenCode hỗ trợ. |

**Kết luận G2:** ❌ KHÔNG KHẢ THI với API hiện tại. Cần đợi OpenCode hỗ trợ session hooks. **XÓA G2 khỏi plan.**

### G3 — Hookify MD Engine: giữ lại nhưng giảm phạm vi

| Vấn đề | Plan cũ | Thực tế |
|--------|---------|---------|
| Plugin + engine | 2 thành phần tách biệt | Có thể gộp vào `solocode-guard.js` — tránh tạo plugin thứ 2 phải maintain |
| `generated/hooks.json` cache | 1 file cache riêng | Không cần — rules chỉ thay đổi khi developer edit file `.md`. Load on-demand mỗi session, cache in-memory là đủ. |
| `gray-matter` dependency | Dùng gray-matter parse YAML | `solocode-guard.js` đã có `fs`, có thể viết parser YAML đơn giản không dependency |
| 3-5 ngày | Cao do 7+ file mới | Giảm xuống 1-2 ngày sau khi tối ưu |
| 7+ file mới | `.opencode/hookify/engine.js`, `rules/*.md` x3, `generated/hooks.json`, `README.md` | Chỉ cần: hòa vào `solocode-guard.js` (không tạo file mới) + thư mục `hookify/rules/` chứa rules `.md` |

**Kết luận G3:** ✅ KHẢ THI sau tối ưu. Giảm từ 7+ file xuống còn sửa 1 file (`solocode-guard.js`) + tạo thư mục `hookify/rules/`.

---

## Plan v2 — tối giản

### ✅ ĐÃ HOÀN THÀNH

| Giai đoạn | Nội dung | Kết quả |
|-----------|----------|---------|
| G1 | 5 skills skip → copy vào `.opencode/` | 47/47 skills = Kilo |
| Boundary | 7-layer boundary defense | `.harness.lock` v3.3.0, `harness-boundaries.md`, `boundary_audit.py` |

### 📋 CÒN LẠI — chỉ 1 giai đoạn

### G3 — Hookify MD Engine tích hợp vào solocode-guard.js v3.0

**Mục tiêu:** Tích hợp engine đọc `.md` rule files vào plugin `solocode-guard.js` hiện có. Không tạo file mới.

**Kiến trúc:**

```
.opencode/
├── plugins/
│   └── solocode-guard.js       ← sửa file này (thêm ~100 dòng)
└── hookify/
    └── rules/
        ├── block-rm.md         ← user tự viết: block pattern cho rm
        ├── deny-env-write.md   ← user tự viết: chặn ghi .env
        └── custom.md           ← user tự viết: quy tắc tùy chỉnh
```

**Logic:**

```
1. tool.execute.before (đã có sẵn trong guard):
   → Đọc .opencode/hookify/rules/*.md (nếu thư mục tồn tại)
   → Parse YAML frontmatter + regex pattern
   → Nếu command/file_path khớp pattern → BLOCK/WARN theo action
   → Fall-through vào BLOCK_PATTERNS + SECRET_PATTERNS hiện có

2. Không cần cache file — rules thay đổi chỉ khi dev edit file .md.
   Load mỗi session, parse in-memory. Thời gian parse <5ms cho <50 rules.
```

**Format file rule `.md` (port từ Kilo hookify):**

```markdown
---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf\s+\/
action: block
---

⛔ Deleting root file system is blocked by harness hookify rule.
Use targeted file deletion instead.
```

- `event`: `bash` | `file` (Write/Edit/MultiEdit)
- `pattern`: regex string
- `action`: `block` | `warn` | `allow`
- `enabled`: `true` | `false`

**Implementation — vào `solocode-guard.js`:**

```javascript
// Thêm vào phần đầu của tool.execute.before handler:

// --- Hookify MD rules (v3.0) ---
// Port from .kilo/hooks/hookify/hookify-engine.js

const HOOKIFY_DIR = '.opencode/hookify/rules';

function loadHookifyRules() {
  if (!fs.existsSync(HOOKIFY_DIR)) return [];
  const rules = [];
  for (const file of fs.readdirSync(HOOKIFY_DIR)) {
    if (!file.endsWith('.md')) continue;
    const content = fs.readFileSync(`${HOOKIFY_DIR}/${file}`, 'utf8');
    const parsed = parseHookifyRule(content);
    if (parsed && parsed.enabled) rules.push(parsed);
  }
  return rules;
}

function parseHookifyRule(content) {
  if (!content.startsWith('---')) return null;
  const end = content.indexOf('---', 3);
  if (end === -1) return null;
  const fm = {};
  for (const line of content.slice(3, end).trim().split('\n')) {
    const [k, v] = line.split(':').map(s => s.trim().replace(/^["']|["']$/g, ''));
    if (k) fm[k] = v === 'true' ? true : v === 'false' ? false : v;
  }
  return { ...fm, message: content.slice(end + 3).trim() };
}
```

**Rủi ro:**
- Regex injection: pattern từ file `.md` do developer viết → compile `new RegExp(pattern, 'i')` có thể crash. Wrap trong try/catch + log warning.
- Performance: mỗi `tool.execute.before` call parse lại toàn bộ rules. Acceptable vì <50 rules × <5ms.

**Verify:**

```bash
# Tạo rule test
mkdir -p .opencode/hookify/rules
echo '---
name: test-block-echo
enabled: true
event: bash
pattern: echo\s+test
action: block
---
Test rule: blocks echo test' > .opencode/hookify/rules/test.md

# Chạy guard test
node .opencode/tests/test-guard.mjs
# Expect: "echo test" bị block bởi hookify rule
```

**Thời gian:** 1-2 ngày (giảm từ 3-5 ngày của plan cũ)
**Rủi ro:** Thấp — sửa 1 file, tạo 1 thư mục, port logic từ Kilo

---

## Kế hoạch thực hiện

| # | Việc | Thời gian | Dependency |
|---|-------|-----------|------------|
| 1 | Sửa `solocode-guard.js` — thêm hookify engine | 3-4 giờ | Không |
| 2 | Tạo 3 rule mẫu (`block-rm.md`, `deny-env-write.md`, `custom.md`) | 30 phút | #1 |
| 3 | Cập nhật `test-guard.mjs` — test hookify rules | 1 giờ | #1 |
| 4 | Verify garden + integration + checklist | 15 phút | #2, #3 |
| 5 | Commit & push | 15 phút | #4 |

**Tổng:** ~5-6 giờ (1 ngày)

---

## Kết quả mong đợi

```
Trước                        Sau
Plugin: solocode-guard v2.5  → Plugin: solocode-guard v3.0 (có hookify)
Không có custom rules        → User tự viết rules .md trong .opencode/hookify/rules/
                               (block pattern, deny file write, allow custom commands)
```

OpenCode đạt 90%+ Kilo. Gap còn lại (~10%):
- Không có unified `kilo.jsonc` config — không đáng kể
- Không có memory manager — đợi OpenCode hỗ trợ session hooks
- Không có Kilo hook system đầy đủ (PreToolUse/PostToolUse/SessionStart/SessionEnd/Stop) — OpenCode dùng plugin model khác

---

## Ghi chú dọn dẹp

### File đã xóa khỏi plan (so với plan cũ)

| File plan cũ định tạo | Lý do xóa |
|----------------------|-----------|
| `.opencode/plugins/solocode-memory.js` | Không khả thi — OpenCode thiếu session hooks |
| `.opencode/hookify/engine.js` | Gộp vào `solocode-guard.js` — không cần file riêng |
| `.opencode/hookify/generated/hooks.json` | Cache in-memory, không cần file |
| `.opencode/hookify/README.md` | Document trong `SKILL.md` của solo-code-harness skill |
| `.opencode/hookify/rules/bash-safety.md` | Gộp chung vào `rules/` — user tự đặt tên file |
| `.opencode/hookify/rules/file-patterns.md` | Gộp chung vào `rules/` — user tự đặt tên file |

**Tổng file rác tránh được:** 6 file (giảm từ 7+ xuống 1 file sửa + 1 thư mục)
