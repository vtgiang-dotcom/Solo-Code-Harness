# Báo cáo công việc — Phase 1 nâng cấp từ review `open-code-review`

| | |
|---|---|
| **Ngày** | 2026-09-16 |
| **Người thực hiện** | Kilo (deepseek-v4.1-flash) |
| **Kế hoạch nguồn** | `.kilo/plans/2026-09-16_144800-upgrade-from-open-code-review.md` |
| **Báo cáo review nguồn** | `docs/review-open-code-review-2026-09-16.md` |
| **Phạm vi session** | Phase 1 — Task 6 và Task 1 |
| **Trạng thái** | Task 6 đã commit; **Task 1 đã commit (`37ae42c`)** |

---

## 1. Tóm tắt

Hai việc đã làm:

1. **Task 6 — `.gitignore`**: đưa `open-code-review-main/` ra khỏi tầm commit. Đã commit (`dc1f773`).
2. **Task 1 — churn sau mỗi lần generate**: fix gốc bằng **idempotent write** trong cả hai generator, kèm `.gitattributes` và 13 test khoá hành vi. **Chưa commit.**

**Phát hiện quan trọng nhất của session:** chẩn đoán trong plan nguồn **SAI**. Plan quy 28–29 file báo "M" sau mỗi lần generate cho EOL mismatch. Tôi phát hiện điều này khi chạy phép thử của Task 1, tìm ra nguyên nhân thật (generator ghi vô điều kiện), sửa cả code lẫn báo cáo, và ghi lại bài học phương pháp. Chi tiết ở §3.

**Phép thử quyết định đã PASS:** chạy generator 2 lần liên tiếp → không còn file generated nào bị báo modified (trước fix: 28–29 file mỗi lần).

---

## 2. Việc đã làm

### 2.1 Task 6 — `.gitignore` (đã commit `dc1f773`)

**Vấn đề:** `open-code-review-main/` là checkout tham khảo, không có `.git` riêng, nên hiện là untracked. Một lệnh `git add -A` sẽ nuốt cả cây upstream vào lịch sử harness.

**Thay đổi:** `.gitignore` +5 dòng — thêm `open-code-review-main/` cùng comment giải thích, gộp nhóm với `deepseek-harness-master/` (đã được ignore trước đó với cùng vấn đề).

**Xác minh:**
```
git status --short          -> open-code-review-main/ biến mất
git check-ignore -v open-code-review-main
                            -> .gitignore:57:open-code-review-main/
```

---

### 2.2 Task 1 — fix churn sau mỗi lần generate (đã commit `37ae42c`)

#### Triệu chứng

Mỗi lần chạy `python tools/generate_harness.py --harness all`, `git status` báo **28–29 file** là modified:

```
 M .claude/agents/*.md          (14 file)
 M .claude/commands/*.md        (14 file)
 M opencode.json
```

nhưng `git diff --numstat` trả **rỗng**.

#### Nguyên nhân thật

Generator ghi file **vô điều kiện**. `git status` so **stat** (mtime) trước và chỉ đọc nội dung sau; `git diff` thì đọc nội dung. Ghi vô điều kiện đẩy mtime lên dù nội dung y hệt, nên:

- `git status` thấy stat khác → báo "M"
- `git diff` đọc nội dung → thấy giống → im lặng

Hai lệnh đúng theo cách của chúng, ghép lại thành tín hiệu gây nhầm.

#### Chuỗi bằng chứng

| Lệnh | Kết quả | Nghĩa |
|---|---|---|
| `git diff --numstat` | rỗng | nội dung không đổi |
| byte-compare disk vs index | `identical: True` | không phải EOL, không phải BOM |
| `git update-index --refresh` | `needs update` | chỉ so stat, không đọc content |
| `git add .claude/agents` | staged rỗng, **M: 29 → 15** | `git add` refresh stat cache |
| `git add .claude/commands opencode.json` | staged rỗng, **M: 15 → 0** | xác nhận |

Byte-compare cụ thể:

```
.claude/agents/architect.md   disk 2443 B, CR=0, LF=87  |  index 2443 B, CR=0, LF=87  |  identical: True
opencode.json                 disk 1353 B, CR=0, LF=50  |  index 1353 B, CR=0, LF=50  |  identical: True
.claude/commands/ship.md      disk  963 B, CR=0, LF=30  |  index  963 B, CR=0, LF=30  |  identical: True
```

#### Thay đổi

| File | Nội dung |
|---|---|
| `tools/claude_engine.py` | `_write_lf` skip khi nội dung giống; thêm helper `_copy_if_changed`; dùng ở `generate_instructions` và `generate_memory` |
| `tools/opencode_engine.py` | thêm `import contextlib`; thêm `_write_if_changed` + `_copy_if_changed`; dùng ở 4 chỗ ghi (agents, commands, instructions, config) |
| `tools/test_generator_idempotency.py` | **mới** — 13 regression tests cho helper, cả hai full generator, và skill sync khi nguồn đổi |
| `.gitattributes` | **mới** — `* text=auto eol=lf` + 14 binary rule |

Diff hiện tại:
```
29  8   tools/claude_engine.py
30  5   tools/opencode_engine.py
```

#### Fix hoạt động thế nào

```python
def _write_lf(path: Path, content: str) -> None:
    if path.exists():
        with contextlib.suppress(OSError, UnicodeDecodeError):
            if path.read_text(encoding="utf-8") == content:
                return  # unchanged: leave mtime alone so git stays clean
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(content)
```

Lợi ích phụ: không ghi disk vô ích, nên generator nhanh hơn trên cây lớn.

#### Về `.gitattributes`

Nó **không** phải fix cho churn — chẩn đoán ban đầu quy sai cho EOL. Nó vẫn được thêm vì lý do khác:

- Đảm bảo mọi checkout (Linux CI, macOS) đều LF, không phụ thuộc `core.autocrlf` của từng máy
- Chặn warning `LF will be replaced by CRLF` khi commit
- `open-code-review` có file này, và nó đúng cho tính nhất quán đa nền tảng

---

## 3. Phát hiện: chẩn đoán trong plan nguồn SAI

Đây là phần tôi cần ghi lại rõ nhất, vì nó ảnh hưởng tới kế hoạch bạn định gửi reviewer.

**Plan nguồn viết:** 28 file báo "M" vì EOL mismatch — generator ghi LF trong khi `core.autocrlf=true` khiến repo mong đợi CRLF (549 file working tree là CRLF, index là LF).

**Số đo đó không chứng minh gì.** Nó chỉ cho thấy *định dạng* EOL của hai phía, không cho thấy chúng *khác nhau*. Byte-compare mới trả lời được câu đó, và kết quả là `identical: True` ở cả ba file kiểm tra.

**Bài học phương pháp:** *"index LF vs worktree CRLF" không kết luận được hai bên có khác nhau hay không — git normalize khi so sánh. Muốn kết luận phải so byte thô (`Path.read_bytes()` vs `git cat-file blob`).*

**Vì sao tôi kết luận sai:** trong session trước tôi từng thấy "28 file M với numstat 0/0" và kết luận đúng là "stat-cache artifact". Nhưng khi viết plan, tôi quy cho EOL dựa trên số đo định dạng mà không làm bước byte-compare — bước lẽ ra phải chặn kết luận đó ngay. Phép thử của Task 1 (chạy generator rồi kiểm tra `git status`) mới là thứ phát hiện ra.

**Đã sửa:** `docs/review-open-code-review-2026-09-16.md` §4.1 viết lại hoàn toàn với chẩn đoán đúng và bài học trên.

**Đã sửa:** `.kilo/plans/2026-09-16_144800-upgrade-from-open-code-review.md` đánh dấu quy trình EOL cũ là superseded và ghi rõ idempotent write là fix cho churn.

---

## 4. Xác minh

### 4.1 Phép thử quyết định

```
Chạy generator lần 1  ->  M count: 2
Chạy generator lần 2  ->  M count: 2
```

2 file đó là `tools/claude_engine.py` và `tools/opencode_engine.py` — **thay đổi thật của chính việc fix**, không phải churn. Không có file generated nào bị báo modified.

**Trước fix:** 28–29 file mỗi lần chạy.

### 4.2 Test mới

```
python -m pytest tools/test_generator_idempotency.py -q
-> 13 passed
```

13 test khoá hành vi theo cả hai chiều: ghi lần hai với nội dung giống **không** đổi mtime; ghi với nội dung khác **vẫn** land; tạo file khi chưa tồn tại; skill cũ bị loại bỏ khi nguồn đổi.

### 4.3 Toàn bộ gate

| Gate | Kết quả |
|---|---|
| `pytest tools/` | **522 passed, 3 skipped, 0 failed** |
| `ruff check .` | All checks passed |
| `garden.py` | **0 drift** |
| `checklist.py` | **5/5 PASSED** (Secret Scan, Ruff Linter, Boundary Audit, Harness Eval, Guard Hook Syntax) |
| `check_lint_budget.py` | 74/74 — At budget |

---

## 5. Ghi nhận phụ: một test flaky

`tools/test_claude_hooks.py::test_session_start_surfaces_and_consumes_checkpoint`

- **Fail 1 lần** trong full suite (lần chạy đầu)
- **Pass 3/3** khi chạy riêng
- **Pass** ở lần full suite thứ hai

Không liên quan tới thay đổi trong session này — tôi chỉ đụng vào hai generator, còn test đó test session hooks. Cần điều tra riêng, không chặn Phase 1.

---

## 6. Việc còn lại

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Task 1 | Đã commit: `37ae42c fix(generator): avoid rewriting unchanged artifacts` |
| 2 | Không ship `.gitattributes` sang project đích | Đã chốt: file chỉ điều chỉnh checkout của repo harness, nên không thêm vào `ROOT_FILES` hay lock template |
| 3 | Điều tra test flaky ở §5 | Tách riêng |
| 4 | Task 2 (`verify_prose.py`) và phần còn lại | Chưa bắt đầu; Task 2 trong plan cần rà lại vì vài chỗ dựa trên giả định cũ |

### Chi tiết mục 2 — quyết định cần chốt

`tools/deploy.py` hàm `copy_file` (dòng 755–776) **luôn ghi đè** — `shutil.copy2` ở cả nhánh `[UPD]` và `[NEW]`, không có nhánh skip:

```python
dst.parent.mkdir(parents=True, exist_ok=True)
if dst.exists():
    shutil.copy2(src, dst)
    return f"  [UPD] {rel}"
else:
    shutil.copy2(src, dst)
    return f"  [NEW] {rel}"
```

Nghĩa là nếu thêm `.gitattributes` vào `ROOT_FILES`, deploy sẽ **ghi đè `.gitattributes` của project đích** nếu họ có file riêng.

Hai lựa chọn:
- **Ship** — nhất quán với `.gitignore` (vốn đã được ship và cũng ghi đè)
- **Không ship** — chỉ giữ ở repo này; fix chính (idempotent write) không cần file này

**Quyết định:** không ship. `.gitattributes` chỉ điều chỉnh checkout của repo harness, nên không thêm vào `ROOT_FILES` hay `HARNESS_LOCK_TEMPLATE`.

Nếu chọn ship, **phải sửa cả `ROOT_FILES` và `HARNESS_LOCK_TEMPLATE`**. Sửa một chỗ sẽ làm `test_lock_template_root_files_match_root_files` fail — đúng lớp bug đã xảy ra với engine codex trước đó.

---

## 7. Trạng thái git

```
HEAD trước Task 1: dc1f773  chore(git): ignore open-code-review reference checkout

Task 1 sau đó đã được commit: 37ae42c  fix(generator): avoid rewriting unchanged artifacts

 M tools/claude_engine.py                              (idempotent text, file, and skill-tree writes)
 M tools/opencode_engine.py                            (idempotent text and file writes)
?? .gitattributes                                       (25 dòng)
?? tools/test_generator_idempotency.py                  (209 dòng)
?? .kilo/plans/2026-09-16_144800-upgrade-from-open-code-review.md
?? docs/review-open-code-review-2026-09-16.md
?? docs/work-report-2026-09-16.md
```

Không có gì staged. Repo **sạch về churn** — không còn file generated nào bị báo modified sau khi chạy generator.

---

## 8. Giá trị thực của session

Fix idempotent write giải quyết vấn đề đã làm mất thời gian **hai session liên tiếp** — nhưng bản thân nó chỉ là ~60 dòng thay đổi trong hai file.

Thứ đáng giá hơn là bài học ở §3: một số đo đúng về *định dạng* đã bị dùng để kết luận sai về *sự khác biệt*. Nếu không có phép thử của Task 1 — chạy generator rồi kiểm tra `git status` — thì chẩn đoán sai đã đi vào lịch sử repo qua commit và báo cáo, và người đọc sau sẽ tin `.gitattributes` là thứ đã sửa được vấn đề, trong khi nó không liên quan.
