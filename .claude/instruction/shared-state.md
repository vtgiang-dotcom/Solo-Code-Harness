# Shared State — Cross-Engine Collaboration (Local-Only)

> Auto-loaded at session start. Tất cả engine đọc/ghi `.solocode/shared-state.db` (SQLite).
> File này KHÔNG được commit vào git — chỉ tồn tại local trên máy đang chạy các engine.

## Cái gì đang thực sự chạy (đo 2026-07-28)

Đừng tin mô tả, hãy tin số đo. Tại repo này, sau 9 ngày dùng thật:

| Bảng | Rows | Ai ghi |
|---|---:|---|
| `session_log` | 350 | **Tự động** — `session_end.py` + `pre_compact.py` |
| `active_locks` | 0 | Thủ công, chỉ khi delegate song song (xem dưới) |
| `features` | 0 | Không ai — dùng git log + `MEMORY.md` thay thế |
| `shared_memory_*` | 0 | Không ai — `MEMORY.md` đã làm việc này |

Một bản mô tả "Session Protocol (MANDATORY)" 9 bước từng nằm ở đây,
trong đó **0/9 bước thực sự được chạy**. Nó đã bị gỡ: một quy trình
bắt buộc mà không gì kiểm chứng chỉ dạy agent tin vào thứ không có thật.

### Session start / end — không cần làm gì thủ công
Hook lo phần này. `session_start.py` đọc `session_log` gần nhất để lấy
bối cảnh; `session_end.py` và `pre_compact.py` ghi lại phiên. Đây là lý
do `session_log` là bảng duy nhất có dữ liệu.

### Khi nào PHẢI dùng lock (còn giá trị)
`active_locks` rỗng vì mới thêm (2026-07-26), **không phải vì bị bỏ**.
Trước khi giao một tác vụ **ghi** cho worker chạy song song (Gemini/
Antigravity sửa cùng cây thư mục), hãy lấy lock cho các file trong phạm
vi — xem `acquire_lock` ở phần API bên dưới. Đây là cơ chế chống ghi đè
duy nhất giữa các engine.

### `features` và `shared_memory_*` — schema còn, không dùng
Giữ lại để tương thích ngược (`garden.py` cảnh báo feature `in-progress`
quá 7 ngày nếu có ai ghi). Với dự án solo, dùng **git log** cho task và
**`MEMORY.md`** cho convention/gotcha/decision: chúng nằm trong repo,
agent đọc được, không cần đồng bộ. Chỉ dùng các bảng này nếu bạn thật
sự chạy nhiều engine song song và cần trạng thái chung.

## Nếu DB bị hỏng (corrupt)

Nếu `python tools/shared_state.py validate` báo lỗi, hoặc thao tác đọc/ghi báo `sqlite3.DatabaseError` — xoá file DB và để nó tự tái tạo schema rỗng ở lần chạy tiếp theo (KHÔNG còn nguồn migrate dự phòng từ `.opencode/state/` — đã gỡ ở v4.0.0; lịch sử feature/session trước đó sẽ mất nếu chưa backup):

```bash
cp .solocode/shared-state.db .solocode/shared-state.db.bak   # backup trước khi xoá, nếu còn dùng được
rm .solocode/shared-state.db .solocode/shared-state.db-wal .solocode/shared-state.db-shm
# SharedState() tự tạo schema rỗng ở lần mở kế tiếp — không cần script migrate riêng.
```

## CLI Quick Reference

```bash
python tools/shared_state.py show
python tools/shared_state.py features --status in-progress
python tools/shared_state.py sessions --limit 10
python tools/shared_state.py locks
python tools/shared_state.py validate
```

## Python API

```python
from tools.shared_state import SharedState

# Trường hợp dùng thật: khoá file trước khi giao việc GHI cho worker
# chạy song song, rồi trả khoá ngay sau khi xong.
with SharedState() as state:
    if state.acquire_lock("src/auth.py", engine="claude", model="sonnet", reason="Delegating edit to Gemini"):
        # ... thực hiện/uỷ quyền sửa file ...
        state.release_lock("src/auth.py", engine="claude")

# add_session_entry() do hook tự gọi — không cần gọi tay:
#   .claude/hooks/session_end.py, .claude/hooks/pre_compact.py
# set_feature_status() còn tồn tại nhưng không dùng ở repo này (xem trên).
```
