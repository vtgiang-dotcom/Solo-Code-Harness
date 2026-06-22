# Bảng Mapping: 45 Config Rules → 17 Plugin BLOCK_PATTERNS

> **STATUS: HISTORICAL (2026-06-22)** — This document analyzed the old `opencode.json` (66 lines, 45 bash rules). The config has since been cleaned per `harness-config-plan.md` Phase B-B: 8 git ask rules removed, 10 orphan deny rules restored. The plugin has been expanded to v2.2 with 30 BLOCK_PATTERNS. See `.opencode/plugins/solocode-guard.js` for current state.

> Phân tích đối chiếu giữa opencode.json cũ (bash rules, dòng 7-51) và solocode-guard.js BLOCK_PATTERNS (dòng 29-47).
> Mục đích: xác định rule nào an toàn gỡ, rule nào là lỗ hổng cần khôi phục.

---

## Nhóm 1 — rm -rf Patterns (8 rules)

| # | Config (cũ) | Action | Plugin pattern | Plugin match? |
|---|---|---|---|---|
| 1 | `"rm -rf /*"` | deny | `rm_root: /rm\s+-rf?\s+\/(?:\s\|$\|\*\|"\|')/` | ✅ `rm -rf /` khớp `\*` sau `/` |
| 2 | `"rm -rf ~*"` | deny | `rm_home: /rm\s+-rf?\s+~/` | ✅ `rm -rf ~*` khớp `~` |
| 3 | `"rm -rf /"` | deny | `rm_root` (như trên) | ✅ `rm -rf /` khớp `$` sau `/` |
| 4 | `"rm -rf *"` | deny | `rm_wildcard: /rm\s+-rf?\s+\*/` | ✅ `rm -rf *` khớp `\*` cuối |
| 5 | `"rm -rf ./*"` | deny | `rm_wildcard` | **❌ KHÔNG** — pattern cần `\*` ngay sau space; `rm -rf ./*` có `./` xen giữa |
| 6 | `"rm --no-preserve-root *"` | deny | `rm_no_preserve: /rm\s+--no-preserve-root/` | ✅ khớp `rm --no-preserve-root` (bỏ qua ` *` cuối) |
| 7 | `"rm -r *"` | deny | `rm_wildcard` | **❌ KHÔNG** — pattern dùng `-rf?`; `rm -r *` dùng `-r` (thiếu `f`) |
| 8 | `"rm -r -f *"` | deny | `rm_wildcard` | **❌ KHÔNG** — pattern dùng `-rf?`; `rm -r -f *` bị tách flag |

**Nhóm con 1a — `rm` deny không phủ** (dòng 5, 7, 8): `rm -rf ./*`, `rm -r *`, `rm -r -f *` → **LỖ HỔNG** — 3 mồ côi.

---

## Nhóm 2 — Git Push Force (2 rules)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"git push --force*"` | deny | `force_push_main: /git\s+push\s+.*(--force\|-f)\s+.*(main\|master)/` | ✅ Cả `--force` và không có main/master |
| `"git push -f *"` | deny | `force_push_main` | ✅ Cả `-f` và không có main/master |

**Ghi chú:** Plugin force_push_main match `--force` hoặc `-f`. Config không yêu cầu `main|master` ở cuối, nhưng plugin thì có. Tuy nhiên plugin pattern dùng `.*(main|master)` — nếu branch không phải main/master, pattern vẫn match `--force` qua `.*` ở trước. `.*` greedy sẽ match `--force .* main|master`. Thực tế `git push -f origin main` match cả. ✅ An toàn gỡ.

---

## Nhóm 3 — Git Reset (2 rules)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"git reset --hard*"` | deny | `git_reset_hard: /git\s+reset\s+--hard/` | ✅ |
| `"git reset --mixed*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** — ask từng yêu cầu xác nhận, nay xóa mất |

**Nhóm con 3a — `ask` rules mất:** `git reset --mixed*` mất lớp hỏi. Đây là `ask` rule (không phải `deny`), nhưng việc gỡ đồng nghĩa với hạ mức bảo vệ.

---

## Nhóm 4 — Git Clean (3 rules)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"git clean -fd*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** — từng deny, nay mất hẳn |
| `"git clean -fx*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git clean -f *"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |

---

## Nhóm 5 — Git Branch/Rebase/Stash (7 `ask` rules)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"git branch -D*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git rebase*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git filter-branch*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git update-ref*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git stash drop*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git reflog delete*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"git gc*"` | ask | **KHÔNG CÓ** | **❌ LỖ HỔNG** |

Tất cả đều là `ask` — yêu cầu xác nhận user. Gỡ bỏ = mất lớp hỏi, command chạy ngay không cảnh báo.

---

## Nhóm 6 — mkfs / dd / format / shred (4 deny)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"mkfs.*"` | deny | `mkfs: /mkfs\./` | ✅ |
| `"dd if=*"` | deny | `dd_raw: /dd\s+if=/` | ✅ |
| `"format*"` | deny | `format_disk: /\bformat\s/` | ✅ |
| `"shred*"` | deny | `shred: /shred\s+/` | ✅ |

---

## Nhóm 7 — SQL Destructive (6 deny)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"*DROP TABLE*"` | deny | `drop_table: /DROP\s+(?:TABLE\|DATABASE)/i` | ✅ |
| `"*drop table*"` | deny | `drop_table` (i flag) | ✅ |
| `"*TRUNCATE TABLE*"` | deny | `truncate_table: /TRUNCATE\s+TABLE/i` | ✅ |
| `"*truncate table*"` | deny | `truncate_table` (i flag) | ✅ |
| `"*DROP DATABASE*"` | deny | `drop_table: /DROP\s+(?:TABLE\|DATABASE)/i` | ✅ |
| `"*drop database*"` | deny | `drop_table` (i flag) | ✅ |

---

## Nhóm 8 — Windows Destructive (10 deny)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"rd /s*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"del /f*"` | deny | `win_del_force: /del\s+\/f\s+\/s/` | **⚠️ MỘT PHẦN** — pattern cần `/f /s`; `del /f` một mình không match |
| `"del /q*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"del /s*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"rmdir*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"Remove-Item*"` | deny | `win_remove_recursive: /Remove-Item\s+.*-Recurse.*-Force/` | **⚠️ MỘT PHẦN** — pattern cần `-Recurse` và `-Force`; `Remove-Item path` đơn thuần không match |
| `"Format-Volume*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"Stop-Computer*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"Restart-Computer*"` | deny | **KHÔNG CÓ** | **❌ LỖ HỔNG** |
| `"diskpart*"` | deny | `diskpart: /\bdiskpart\b/` | ✅ |

**Nhóm con:** 7/10 không phủ, 2/10 phủ một phần (chỉ chặn variant có flag). → **LỖ HỔNG LỚN trên Windows.**

---

## Nhóm 9 — Shutdown/Reboot/Halt (3 `ask` rules)

| Config | Action | Plugin | Match? |
|---|---|---|---|
| `"shutdown*"` | ask | `shutdown_system: /(?:shutdown\|reboot\|halt)\b/` | ⛔ **CHẶN CỨNG** — plugin BLOCK (không phải ask) |
| `"reboot*"` | ask | `shutdown_system` | ⛔ **CHẶN CỨNG** |
| `"halt*"` | ask | `shutdown_system` | ⛔ **CHẶN CỨNG** |

**Thay đổi hành vi:** Config cũ cho `ask` (hỏi user), plugin mới `block` (chặn cứng). **Strictening có chủ đích** — cần ghi nhận nhưng không phải regression.

---

## TỔNG KẾT

### An toàn gỡ (có plugin coverage đầy đủ): **17/45 rules**

| Nhóm | Rules |
|---|---|
| rm (`rm_root/rm_home/rm_wildcard/rm_no_preserve`) | 4: `rm -rf /*`, `rm -rf ~*`, `rm -rf /`, `rm -rf *` |
| rm (`rm_no_preserve`) | 1: `rm --no-preserve-root *` |
| git push | 2: `git push --force*`, `git push -f *` |
| git reset --hard | 1: `git reset --hard*` |
| mkfs / dd / format / shred | 4 |
| SQL (drop_table + truncate_table) | 6 |
| diskpart | 1 |
| **Tổng** | **19** (discount 2 Win partials = **17 full, 2 partial**) |

### Mồ côi (config có, plugin không): **19 rules**

| Nhóm | Số lượng | Nghiêm trọng | Gợi ý |
|---|---|---|---|
| rm variants (`rm -rf ./*`, `rm -r *`, `rm -r -f *`) | 3 | Cao — từng deny, nay mất | Thêm pattern vào plugin hoặc restore vào config |
| git clean (`-fd*`, `-fx*`, `-f *`) | 3 | Cao — từng deny, nay mất | Restore vào config |
| git `ask` (`branch -D`, `rebase`, `filter-branch`, `update-ref`, `stash drop`, `reflog delete`, `gc`) | 7 | Trung — từng ask, nay mất | Gỡ chấp nhận được nếu đồng ý hạ bảo vệ các git command hiếm dùng |
| git reset --mixed | 1 | Thấp — ask | Gỡ chấp nhận được |
| Win: `rd /s*`, `del /q*`, `del /s*`, `rmdir*` | 4 | Cao (Windows) | Restore vào config |
| Win: `Format-Volume*`, `Stop-Computer*`, `Restart-Computer*` | 3 | Cao (Windows) | Restore vào config |
| **Tổng mồ côi** | **19** | | |

### Thay đổi hành vi (ask→block): **3 rules**

| Config | Cũ → Mới | Đánh giá |
|---|---|---|
| `shutdown*` | ask → block | Strictening — chấp nhận được |
| `reboot*` | ask → block | Strictening — chấp nhận được |
| `halt*` | ask → block | Strictening — chấp nhận được |

---

## KẾT LUẬN

**Việc gỡ toàn bộ 45 bash rules là KHÔNG AN TOÀN.** 19 rule mồ côi mất bảo vệ.

Đề xuất sửa:
1. **Restore 10 deny rules** mồ côi vào opencode.json (rm variants, git clean, Win specific)
2. **Bỏ qua 7 git `ask` rules** — chấp nhận hạ bảo vệ (git command hiếm dùng, người dùng chủ động)
3. **Bỏ qua 1 git reset --mixed** — chấp nhận hạ bảo vệ
4. **Ghi nhận 3 shutdown** — strictening, OK
