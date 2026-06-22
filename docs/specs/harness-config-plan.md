# Harness Config Plan — OpenCode Config Nền Tảng

> Phase B-A (Review & Plan) — Chờ duyệt trước khi implement Phase B-B.
> Biên soạn ngày: 2026-06-22

---

## 1. Kiểm Kê opencode.json Hiện Tại

**File:** `D:\Project\Solo-Code-CLI\opencode.json` (66 dòng)

### Cấu trúc hiện tại

V1 `permission` object syntax. 3 nhóm rule:

| Nhóm | Dòng | Rule count | Mô tả |
|---|---|---|---|
| `"*"` | 4 | 1 | Catch-all: "ask" |
| `"bash"` | 5-52 | 1 default (allow) + 43 sub-rules | 1 wildcard allow + 43 destructive patterns deny |
| `"read"` | 53-58 | 1 default (allow) + 3 sub-rules | 1 wildcard allow + 3 .env rules |
| `"glob"` | 59 | 1 | allow |
| `"grep"` | 60 | 1 | allow |
| `"todowrite"` | 61 | 1 | allow |
| `"external_directory"` | 62-64 | 1 | ask |

### Rule Tàn Dư Test

**Phát hiện:** Không có rule `echo BLOCKED_TEST*` nào trong file hiện tại. Tuy nhiên, các rule bash deny sau đây **trùng lặp với solocode-guard.js** (plugin đã chặn các pattern này ở mức cứng, không cần permission-layer overlay):

| Dòng | Pattern | Plugin coverage |
|---|---|---|
| 7-8 | `rm -rf /*`, `rm -rf ~*` | `rm_root`, `rm_home` (dòng 24-25) |
| 9-14 | `rm -rf /`, `rm -rf *`, `rm -rf ./*`, `rm --no-preserve-root *`, `rm -r *`, `rm -r -f *` | `rm_root`, `rm_wildcard`, `rm_no_preserve` (dòng 24-27) |
| 15-16 | `git push --force*`, `git push -f *` | `force_push_main` (dòng 28) |
| 17 | `git reset --hard*` | `git_reset_hard` (dòng 29) |
| 29-30 | `mkfs.*`, `dd if=*` | `mkfs`, `dd_raw` (dòng 33-34) |
| 31 | `format*` | `format_disk` (dòng 38) |
| 32 | `shred*` | `shred` (dòng 35) |
| 33-38 | `*DROP TABLE*`, `*drop table*`, `*TRUNCATE TABLE*`, `*DROP DATABASE*`, `*drop database*` | `drop_table`, `truncate_table` (dòng 30-31) |
| 39-48 | `rd /s*`, `del /f*`, `Remove-Item*`, `diskpart*`, ... | `win_del_force`, `win_remove_recursive`, `diskpart` (dòng 36-40) |
| 49-51 | `shutdown*`, `reboot*`, `halt*` | `shutdown_system` (dòng 41) |

**Đề xuất:** GỬ bỏ các rule bash deny pattern đã được plugin bảo vệ. Chỉ giữ:
- `"*": "ask"` (catch-all, line 4)
- `"bash": { "*": "allow" }` (default cho phép bash, line 6)
- Các rule `.env` cho read (lines 53-58)
- `external_directory`: ask (lines 62-64)
- Các tool non-bash: glob, grep, todowrite

### Chiến Lược Matching (findLast)

OpenCode V1 dùng `findLast()` — **rule cuối khớp thắng** (`docs/specs/opencode-mechanisms.md:339-349`).

Thứ tự khuyến nghị cho opencode.json sạch:

```jsonc
{
  "permission": {
    "*": "ask",                 // 1. catch-all — rule mặc định
    "bash": {
      "*": "allow",             // 2. cho phép bash mặc định
      // 3. (không cần pattern deny — plugin loại)
    },
    "read": {
      "*": "allow",             // 4. đọc file mặc định
      "*.env": "ask",           // 5. env file cần hỏi
      "*.env.*": "ask",         // 6. env variant cũng hỏi
      "*.env.example": "allow"  // 7. example env thì cho phép
    },
    "glob": "allow",            // 8. glob luôn cho
    "grep": "allow",            // 9. grep luôn cho
    "todowrite": "allow",       // 10. todowrite luôn cho
    "external_directory": {
      "*": "ask"                // 11. thư mục ngoài project: hỏi
    }
  }
}
```

---

## 2. Rà AGENTS.md Root — Tham Chiếu .kilo/

**File:** `D:\Project\Solo-Code-CLI\AGENTS.md` (199 dòng)

### Tổng quan tham chiếu

| Dòng | Tham chiếu `.kilo/` | Loại | Trạng thái |
|---|---|---|---|
| 5 | `.kilo/` (harness auto-load) | Mô tả cơ chế load | **OK** — mô tả Kilo-specific, OpenCode bỏ qua |
| 80 | `.kilo/hooks/post-tool-use/context-monitor.js` | Hook | **OK** — đã thay bằng `solocode-guard.js` (plugin) |
| 106 | `kilo.json` | Config | **OK** — Kilo-only, OpenCode ignores |
| 118 | `.kilo/instruction/security-patterns.md` | Security rules | **BRIDGE (ĐỀ BÀI C)** — cần port hoặc symlink |
| 132 | `.kilo/skill/git-workflow-master/SKILL.md` | Skill | **BRIDGE (ĐỀ BÀI C)** — skill cần port |
| 138 | `.kilo/memory/` | Memory | **BRIDGE (ĐỀ BÀI C)** — memory cần port |
| 146 | `.github/scripts/checklist.py` | Script | **OK** — script độc lập, chạy được cả 2 engine |
| 147 | `.github/scripts/security_scan.py` | Script | **OK** — script độc lập |
| 158 | `python .github/scripts/security_scan.py .` | Script | **OK** — script độc lập |
| 169 | `.kilo/hooks/hooks.json` | Hook config | **OK** — đã thay bằng plugin, không dùng nữa |
| 170 | `.kilo/instruction/security-patterns.md` | Security rules | **BRIDGE (ĐỀ BÀI C)** — (trùng dòng 118) |
| 191 | `python .github/scripts/security_scan.py .` | Script | **OK** — script độc lập |
| 192 | `python .github/scripts/checklist.py .` | Script | **OK** — script độc lập |

### Bản Đồ Gap — Bridge Cần Xử Lý (ĐỀ BÀI C)

| STT | File gốc (`.kilo/`) | File đích đề xuất (`.opencode/`) | Nội dung |
|---|---|---|---|
| 1 | `.kilo/instruction/security-patterns.md` | `.opencode/instruction/security-patterns.md` | Giữ nguyên, OpenCode đọc được |
| 2 | `.kilo/skill/git-workflow-master/SKILL.md` | `.opencode/skill/git-workflow-master/SKILL.md` | Port nguyên skill |
| 3 | `.kilo/memory/MEMORY.md` | `.opencode/memory/MEMORY.md` | Port nguyên memory |

**Giải thích:** OpenCode có cơ chế load từ `.opencode/` tương tự Kilo với `.kilo/`. Tuy nhiên, OpenCode không tự động đọc `.kilo/` và Kilo không tự động đọc `.opencode/`. Cần tạo bản sao (hoặc symlink) ở `.opencode/` cho các file security-patterns, skill, memory.

---

## 3. Quyết Định Kiến Trúc AGENTS.md

### Phương án A — Chung một AGENTS.md (Khuyến nghị)

**KHÔNG tách file.** Giữ một `AGENTS.md` duy nhất ở root.

**Lý do:**
1. **AGENTS.md là rulebook chứ không phải config plugin.** Rule về quality (Prose Quality Rules), anti-hallucination, request classification, escalation, verification gates — áp dụng cho mọi AI agent, không phụ thuộc engine.
2. **Kilo đọc AGENTS.md** từ root. Nếu tách, Kilo sẽ không thấy rule OpenCode.
3. **Các tham chiếu `.kilo/` trong AGENTS.md không gây hại cho OpenCode.** OpenCode chỉ đọc AGENTS.md để lấy system prompt + frontmatter. Nội dung markdown bên dưới frontmatter là text thuần — nếu có tham chiếu `.kilo/` mà OpenCode không hiểu, engine đơn giản bỏ qua.
4. **Một nguồn chân lý duy nhất.** Tránh lệch rule.

**Điều chỉnh tối thiểu cần làm** (nếu plan duyệt):
- Thêm ghi chú ở đầu file: "Some sections reference .kilo/ paths — these are Kilo-specific. OpenCode users follow .opencode/ equivalents described in ĐỀ BÀI C."
- Cập nhật Self-Verification Handshake (dòng 9-10) để phản ánh cả hai engine nếu cần.

### Phương án B — Tách biến thể (Không khuyến nghị)

Tạo `AGENTS.kilo.md` cho Kilo và `AGENTS.opencode.md` cho OpenCode.

**Lý do không chọn:** Phải duy trì hai file, dễ lệch, tăng cognitive load. Lợi ích duy nhất là loại bỏ tham chiếu `.kilo/` khỏi file OpenCode — nhưng các tham chiếu đó đã được xác định là vô hại.

---

## 4. Xác Minh Cơ Chế Load

### OpenCode có tự đọc AGENTS.md root không?

**CÓ, xác nhận.** Dựa trên `docs/specs/opencode-mechanisms.md` (mục D.1):
- OpenCode quét mọi `Config.Directory` (bao gồm root project) tìm file `.md`
- Pattern: `{agent,agents}/**/*.md` và `{mode,modes}/*.md`
- Điều kiện: file MD phải có frontmatter YAML hợp lệ

**Kết luận:** `AGENTS.md` hiện tại (dòng 1-199) **CÓ** dòng `# Solo-Code — Kilo AI Agent Harness (Root Rulebook for Kilo Code)` ở dòng 1 nhưng **KHÔNG có frontmatter YAML** — đây chỉ là H1 markdown. Với cấu trúc hiện tại, OpenCode sẽ **đọc file** nhưng **không parse được** vì thiếu `---` frontmatter.

Tuy nhiên, vì file này không được thiết kế làm OpenCode agent spec (mà là rulebook chung), OpenCode bỏ qua nó — không gây hại. Các agent/skill của OpenCode được load từ `.opencode/` directory riêng.

### Plugin local (.opencode/plugins/) có cần khai báo trong opencode.json không?

**Đã xác nhận tự nạp (PLUGIN LOADED)** — plugin `solocode-guard.js` được OpenCode auto-discover từ `.opencode/plugins/`. **Không cần khai báo trong opencode.json.**

Cơ chế: OpenCode quét `.opencode/plugins/` directory mặc định.

**Khuyến nghị:** Nếu muốn explicit config, có thể thêm `"plugin_origins"` field, nhưng không bắt buộc. Giữ nguyên `opencode.json` không có `plugins` field.

---

## 5. Cross-Platform Tương Thích

### Đường dẫn
- `opencode.json`: dùng forward slash `/` trong pattern (vd `*.env`, `rm -rf /*`)
- Windows: OpenCode normalize backslash → slash tự động (`docs/specs/opencode-mechanisms.md:372`)
- Plugin: `isExcludedPath` đã normalize `\\` → `/` (dòng 167)

### Permission patterns
- Wildcard `*` hoạt động giống nhau trên Win/Linux
- Tool names (`bash`, `write`, `read`) không đổi giữa các OS
- Các pattern `rm -rf /*`, `del /f*`, `Remove-Item*` — một số là Win-specific — đều hợp lệ trong cùng một config (findLast bỏ qua pattern không match)

### Kết luận
Một file `opencode.json` duy nhất chạy được cả Windows và Linux/Mac. Không cần biến thể OS.

---

## 6. Kế Hoạch Phase B-B (Sau Khi Duyệt)

### Việc 1 — opencode.json sạch
- Gỡ 41 dòng rule bash deny pattern (trùng plugin)
- Giữ: `"*": "ask"`, `"bash": { "*": "allow" }`, `"read"` rules, `"glob"`, `"grep"`, `"todowrite"`, `"external_directory"`
- File giảm từ 66 dòng xuống ~20 dòng

### Việc 2 — AGENTS.md (sửa tối thiểu)
- Nếu duyệt Phương án A (chung file): thêm 1-2 dòng ghi chú về dual-engine path
- Cập nhật Self-Verification Handshake (dòng 9-10) nếu cần

### Việc 3 — Xác minh
- Không tự chạy test
- Ghi rõ các bước kiểm tra thủ công cho người dùng

---

CHỜ DUYỆT. Trả lời:
1. Đồng ý phương án A (chung AGENTS.md) hay chọn B (tách)?
2. Có muốn thêm frontmatter nhỏ vào AGENTS.md để OpenCode nhận diện, hay giữ nguyên?
3. Có muốn thêm `plugin_origins` vào opencode.json để explicit, hay để auto-discover?
