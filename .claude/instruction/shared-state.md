# Shared State — Cross-Engine Collaboration (Local-Only)

> Auto-loaded at session start. Tất cả engine đọc/ghi `.solocode/shared-state.db` (SQLite).
> File này KHÔNG được commit vào git — chỉ tồn tại local trên máy đang chạy các engine.

## Session Protocol (MANDATORY)

### At Session Start: READ
1. Mở `.solocode/shared-state.db` qua `tools/shared_state.py`
2. Check `active_locks` — tránh sửa file đang bị engine khác khoá
3. Check `features` — tìm 1 feature `in-progress` (hoặc promote 1 `not-started`)
4. Load `shared_memory` (conventions/gotchas/decisions) vào context
5. Xem `session_log` gần nhất để biết bối cảnh

### At Session End: WRITE (BẮT BUỘC trước khi kết thúc phiên)
1. Cập nhật feature status (completed/in-progress/blocked)
2. Gọi `add_session_entry(...)` với summary, files_changed, verification
3. `release_lock(...)` cho mọi file đã khoá trong session
4. Thêm convention/gotcha mới nếu phát hiện

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

with SharedState() as state:
    if state.acquire_lock("src/auth.py", engine="copilot", model="deepseek-chat", reason="Fixing bug #42"):
        # ... thực hiện sửa file ...
        state.release_lock("src/auth.py", engine="copilot")
    state.set_feature_status("feat-008", "in-progress", engine="copilot", model="deepseek-chat")
    state.add_session_entry(
        engine="copilot", model="deepseek-chat",
        summary="Fixed authentication bug in login flow",
        files_changed=["src/auth.py", "tests/test_auth.py"],
        verification={"security_scan": True, "integration_tests": True},
    )
```
