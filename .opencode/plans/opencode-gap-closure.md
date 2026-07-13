# OpenCode Gap Closure — Plan v2 (updated 2026-07-13 10:16 ICT)

## Trạng thái hiện tại

```
OpenCode feature parity với Kilo:
  Skills:      47/47  ✅ (G1 done)
  Instructions: 9/9   ✅
  Agents:       14/14 ✅
  Memory:        3/3  ✅ (copy, no manager)
  Plugin:        1    ✅ (solocode-guard.js v3.0)
  Hookify:       Done ✅ (G3 done — MD engine integrated into solocode-guard.js)
  Memory mgr:    ❌    (OpenCode lacks session hooks — not feasible now)
```

```
OpenCode: 90%+ Kilo parity

Còn lại (không đáng kể):
  - Memory manager (~5%) — đợi OpenCode thêm session lifecycle hooks
  - Unified kilo.jsonc config (~5%) — architecture difference, not a gap
```

## Đã hoàn thành

### ✅ G1 — 5 Skill Thiếu (15 phút, 0 rủi ro)
Commit: `9e39ceb` — Copy 5 skills, clear skip list, update test counts.
→ `.opencode/skill/` = 47 = `.kilo/skill/` = `.copilot/skill/`

### ✅ G3 — Hookify MD Engine (1 ngày)
Commit: `6121da5` — Hookify engine integrated into `solocode-guard.js` v3.0
→ User-definable rules via `.opencode/hookify/rules/*.md`
→ 3 sample rules shipped: `block-rm.md`, `deny-env-write.md`, `custom-example.md`
→ 18 hookify tests added to `test-guard.mjs`
→ 0 external dependencies, 0 new plugin files

## Không khả thi

### ❌ G2 — Memory Manager Plugin
**Lý do:** OpenCode không có session lifecycle hooks (`session.start`, `session.end`).
Chỉ có `chat.message`, `tool.execute.before`, `tool.execute.after`.
Plugin không thể inject context trực tiếp vào agent.
→ Bỏ khỏi plan đến khi OpenCode mở rộng hook API.

| Vấn đề | Plan cũ | Thực tế |
|--------|---------|---------|
| Plugin + engine | 2 thành phần tách biệt | Có thể gộp vào `solocode-guard.js` — tránh tạo plugin thứ 2 phải maintain |
| `generated/hooks.json` cache | 1 file cache riêng | Không cần — rules chỉ thay đổi khi developer edit file `.md`. Load on-demand mỗi session, cache in-memory là đủ. |
| `gray-matter` dependency | Dùng gray-matter parse YAML | `solocode-guard.js` đã có `fs`, có thể viết parser YAML đơn giản không dependency |
| 3-5 ngày | Cao do 7+ file mới | Giảm xuống 1-2 ngày sau khi tối ưu |
| 7+ file mới | `.opencode/hookify/engine.js`, `rules/*.md` x3, `generated/hooks.json`, `README.md` | Chỉ cần: hòa vào `solocode-guard.js` (không tạo file mới) + thư mục `hookify/rules/` chứa rules `.md` |

**Kết luận G3:** ✅ KHẢ THI sau tối ưu. Giảm từ 7+ file xuống còn sửa 1 file (`solocode-guard.js`) + tạo thư mục `hookify/rules/`.

---


Giai đoạn	Nội dung	Kết quả
G1	5 skills skip → copy vào `.opencode/`	47/47 skills = Kilo
Boundary	7-layer boundary defense	`.harness.lock` v3.3.0, `harness-boundaries.md`, `boundary_audit.py`
G3	Hookify MD engine → `solocode-guard.js` v3.0	User-definable `.md` rules, 3 sample rules, 18 tests

## Ghi chú dọn dẹp

### File đã tránh tạo (so với plan v1)

| File plan v1 định tạo | Lý do không tạo |
|----------------------|-----------------|
| `.opencode/plugins/solocode-memory.js` | G2 không khả thi — OpenCode thiếu session hooks |
| `.opencode/hookify/engine.js` | Gộp vào `solocode-guard.js` |
| `.opencode/hookify/generated/hooks.json` | Cache in-memory |
| `.opencode/hookify/README.md` | Document trong `SKILL.md` |
| `.opencode/hookify/rules/bash-safety.md` | User tự đặt tên file rule |
| `.opencode/hookify/rules/file-patterns.md` | User tự đặt tên file rule |
| `.opencode/hookify/rules/custom.md` | User tự đặt tên file rule |

**7 file rác đã tránh được.** Chỉ tạo 1 thư mục + sửa 1 file.

