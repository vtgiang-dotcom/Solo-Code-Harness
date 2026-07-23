# `.solocode/shared-state.db` — Multi-Model Shared State Layer

> **DÀNH CHO MODEL CẤP THẤP (low-tier).** Đây là kế hoạch thực thi từng bước. KHÔNG tự sáng tạo code, KHÔNG tự đổi API, KHÔNG bỏ qua bước xác minh. Mọi block code trong file này là **copy-paste nguyên văn** — dán y hệt vào file được chỉ định, không sửa gì thêm trừ khi task ghi rõ "chỉnh sửa X thành Y".

## QUY TẮC BẮT BUỘC CHO MODEL THỰC THI

1. Làm **đúng 1 Task một lần**, theo thứ tự 1 → 10. Không nhảy cóc, không gộp nhiều task.
2. Sau MỖI task có khối **"✅ DỪNG LẠI & XÁC MINH"** — bắt buộc chạy lệnh trong đó, so khớp với "Kết quả mong đợi". Nếu KHÔNG khớp → dừng lại, không làm task tiếp theo, báo lỗi cho người dùng.
3. KHÔNG được tự ý sửa nội dung code trong các block ```python/```sql/```markdown — copy nguyên văn.
4. Nếu file đích đã tồn tại và task ghi "Create" → đọc trước bằng cách xem nội dung hiện tại, nếu đã có nội dung khác thì DỪNG và hỏi người dùng (không ghi đè mù).
5. Chạy `python .github/scripts/security_scan.py .` trước MỌI lệnh `git commit`.
6. KHÔNG bao giờ chạy `git add .solocode/` hoặc `git add` bất kỳ file `.db` nào — xem "Quyết định thiết kế" bên dưới.

## Quyết định thiết kế (đã chốt — KHÔNG bàn lại)

| Câu hỏi | Quyết định |
|---|---|
| Đồng bộ qua git hay chỉ local? | **Local only.** File `.solocode/shared-state.db` KHÔNG commit git (đã bị `.gitignore` dòng 23 chặn — đã xác minh bằng `git ls-files .solocode/` trả về rỗng). |
| JSON hay SQLite? | **SQLite** (`sqlite3`, stdlib Python, không thêm dependency). Lý do: JSON + tự viết file lock có race condition thật (đã kiểm chứng), SQLite dùng transaction `BEGIN IMMEDIATE` tự khoá ở mức OS. |
| Schema ở đâu? | Constant `SCHEMA_SQL` trong `tools/shared_state.py` (code, được track git). File `.db` thực tế nằm trong `.solocode/` (không track). |

**Mục tiêu cuối cùng:** Sau khi hoàn thành 10 task, có: `tools/shared_state.py` (module SQLite) + `tools/shared_state_schema.sql` (tài liệu) + `tools/test_shared_state.py` (test) + `tools/migrate_to_shared_state.py` (migration) + 4 file instruction (Kilo/OpenCode/Copilot/Gemini) + `.github/copilot-instructions.md`, `tools/garden.py`, `tools/test_integration.py` được cập nhật + README/SPEC/`.harness.lock` cập nhật.

---

## Task 1: Tạo file schema tài liệu `tools/shared_state_schema.sql`

**Hành động:** Tạo file mới (dùng công cụ tạo file, KHÔNG dùng terminal echo).

**Đường dẫn:** `tools/shared_state_schema.sql`

**Nội dung (copy nguyên văn):**

```sql
-- tools/shared_state_schema.sql
-- Schema tài liệu cho .solocode/shared-state.db (SQLite, local-only, KHÔNG track git).
-- Bảng thực tế được tạo tự động bởi tools/shared_state.py::SCHEMA_SQL khi mở kết nối lần đầu.
-- File này chỉ để đọc hiểu — sửa schema thật thì sửa trong tools/shared_state.py.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- keys hợp lệ: version, updated_at, updated_by_engine, updated_by_model

CREATE TABLE IF NOT EXISTS features (
    id           TEXT PRIMARY KEY,      -- ví dụ: 'feat-001'
    name         TEXT,
    status       TEXT NOT NULL CHECK (status IN ('not-started','in-progress','completed','blocked')),
    owner_engine TEXT,
    owner_model  TEXT,
    evidence     TEXT,
    last_updated TEXT NOT NULL          -- ISO 8601 UTC
);

CREATE TABLE IF NOT EXISTS session_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT NOT NULL,     -- ISO 8601 UTC
    engine           TEXT NOT NULL CHECK (engine IN ('kilo','opencode','copilot','gemini')),
    model            TEXT NOT NULL,
    session_id       TEXT,
    summary          TEXT NOT NULL,
    features_touched TEXT,              -- JSON array dạng text
    files_changed    TEXT,              -- JSON array dạng text
    commits          TEXT,              -- JSON array dạng text
    verification     TEXT               -- JSON object dạng text
);
CREATE INDEX IF NOT EXISTS idx_session_log_ts ON session_log(timestamp DESC);

CREATE TABLE IF NOT EXISTS active_locks (
    path       TEXT PRIMARY KEY,
    engine     TEXT NOT NULL,
    model      TEXT NOT NULL,
    session_id TEXT,
    locked_at  TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    reason     TEXT
);

CREATE TABLE IF NOT EXISTS shared_memory_conventions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    added_by_engine TEXT NOT NULL,
    added_by_model  TEXT NOT NULL,
    added_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shared_memory_gotchas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    description     TEXT NOT NULL,
    added_by_engine TEXT NOT NULL,
    added_by_model  TEXT NOT NULL,
    added_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shared_memory_decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    decision       TEXT NOT NULL,
    rationale      TEXT,
    made_by_engine TEXT NOT NULL,
    made_by_model  TEXT NOT NULL,
    made_at        TEXT NOT NULL
);
```

**Giới hạn kích thước (BẮT BUỘC nhớ, sẽ implement ở Task 2):** `session_log` tối đa 1000 dòng mới nhất. `active_locks` tự xoá dòng hết hạn (>2 giờ) trước mỗi lần đọc/ghi.

### ✅ DỪNG LẠI & XÁC MINH (Task 1)

Chạy đúng lệnh sau:

```powershell
python -c "print('file exists:', __import__('pathlib').Path('tools/shared_state_schema.sql').is_file())"
```

**Kết quả mong đợi:** `file exists: True`

Nếu đúng, chạy commit:

```powershell
python .github/scripts/security_scan.py .
git add tools/shared_state_schema.sql
git commit -m "feat: add shared-state SQLite schema reference

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

**KHÔNG làm Task 2 nếu security_scan báo lỗi.**

---

## Task 2: Tạo module `tools/shared_state.py`

**Hành động:** Tạo file mới.

**Đường dẫn:** `tools/shared_state.py`

**Nội dung (copy nguyên văn — KHÔNG rút gọn, KHÔNG đổi tên hàm/tham số):**

```python
#!/usr/bin/env python3
"""
shared_state.py — Cross-engine shared state reader/writer (SQLite backend).

Single source of truth at .solocode/shared-state.db (LOCAL ONLY — not committed to git,
directory already excluded via .gitignore). All 4 engines (Kilo, OpenCode, Copilot, Gemini)
read/write this file when running on the same machine/workspace.

Why SQLite instead of JSON + manual file locking:
  - Each mutation (acquire_lock, set_feature_status, ...) runs inside its own
    `BEGIN IMMEDIATE` transaction. SQLite's own OS-level locking (WAL mode) guarantees
    isolation between concurrent processes — no "load whole file, mutate in memory,
    save at the end" pattern that would lose concurrent writes from another engine.
  - No custom msvcrt/fcntl code needed; SQLite already handles cross-platform locking.

Usage:
    from tools.shared_state import SharedState

    with SharedState() as state:
        state.set_feature_status("feat-008", "in-progress", engine="copilot", model="deepseek-chat")
        if state.acquire_lock("src/auth.py", engine="copilot", model="deepseek-chat"):
            state.add_session_entry(engine="copilot", model="deepseek-chat", summary="Fixed bug in auth")
            state.release_lock("src/auth.py", engine="copilot")
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / ".solocode" / "shared-state.db"
LOCK_TIMEOUT_HOURS = 2
MAX_SESSION_LOG_ROWS = 1000
VALID_ENGINES = ("kilo", "opencode", "copilot", "gemini")
VALID_STATUSES = ("not-started", "in-progress", "completed", "blocked")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS features (
    id           TEXT PRIMARY KEY,
    name         TEXT,
    status       TEXT NOT NULL,
    owner_engine TEXT,
    owner_model  TEXT,
    evidence     TEXT,
    last_updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT NOT NULL,
    engine           TEXT NOT NULL,
    model            TEXT NOT NULL,
    session_id       TEXT,
    summary          TEXT NOT NULL,
    features_touched TEXT,
    files_changed    TEXT,
    commits          TEXT,
    verification     TEXT
);
CREATE INDEX IF NOT EXISTS idx_session_log_ts ON session_log(timestamp DESC);
CREATE TABLE IF NOT EXISTS active_locks (
    path       TEXT PRIMARY KEY,
    engine     TEXT NOT NULL,
    model      TEXT NOT NULL,
    session_id TEXT,
    locked_at  TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    reason     TEXT
);
CREATE TABLE IF NOT EXISTS shared_memory_conventions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    added_by_engine TEXT NOT NULL,
    added_by_model  TEXT NOT NULL,
    added_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shared_memory_gotchas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    description     TEXT NOT NULL,
    added_by_engine TEXT NOT NULL,
    added_by_model  TEXT NOT NULL,
    added_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shared_memory_decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    decision       TEXT NOT NULL,
    rationale      TEXT,
    made_by_engine TEXT NOT NULL,
    made_by_model  TEXT NOT NULL,
    made_at        TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SharedState:
    """Cross-engine shared state manager backed by SQLite (local-only)."""

    def __init__(self, path: Path | None = None):
        self.path = path or DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SharedState":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _transaction(self):
        """Context manager: BEGIN IMMEDIATE ... COMMIT/ROLLBACK."""
        return _ImmediateTransaction(self._conn)

    def _expire_locks(self) -> None:
        self._conn.execute(
            "DELETE FROM active_locks WHERE expires_at <= ?", (_now(),)
        )

    def _prune_session_log(self) -> None:
        # Sắp xếp phụ theo `id DESC` để có thứ tự xác định (deterministic) khi
        # 2 dòng có cùng `timestamp` (2 engine ghi trong cùng 1 giây) — tránh
        # xoá nhầm dòng mới do ORDER BY chỉ theo timestamp không ổn định.
        self._conn.execute(
            """
            DELETE FROM session_log WHERE id NOT IN (
                SELECT id FROM session_log ORDER BY timestamp DESC, id DESC LIMIT ?
            )
            """,
            (MAX_SESSION_LOG_ROWS,),
        )

    # ── Feature Management ────────────────────────────────────

    def get_features(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, name, status, owner_engine, owner_model, evidence, last_updated "
            "FROM features ORDER BY id"
        ).fetchall()
        return [self._feature_row_to_dict(r) for r in rows]

    def get_feature(self, feature_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT id, name, status, owner_engine, owner_model, evidence, last_updated "
            "FROM features WHERE id = ?",
            (feature_id,),
        ).fetchone()
        return self._feature_row_to_dict(row) if row else None

    @staticmethod
    def _feature_row_to_dict(row: tuple) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "owner": {"engine": row[3], "model": row[4]},
            "evidence": row[5],
            "last_updated": row[6],
        }

    def set_feature_status(
        self,
        feature_id: str,
        status: str,
        *,
        engine: str = "none",
        model: str = "none",
        evidence: str = "",
        name: str = "",
    ) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        now = _now()
        with self._transaction():
            self._conn.execute(
                """
                INSERT INTO features (id, name, status, owner_engine, owner_model, evidence, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    owner_engine = excluded.owner_engine,
                    owner_model = excluded.owner_model,
                    evidence = CASE WHEN excluded.evidence != '' THEN excluded.evidence ELSE features.evidence END,
                    last_updated = excluded.last_updated
                """,
                (feature_id, name, status, engine, model, evidence, now),
            )

    # ── Session Log ──────────────────────────────────────────

    def add_session_entry(
        self,
        *,
        engine: str,
        model: str,
        summary: str,
        session_id: str = "",
        features_touched: list[str] | None = None,
        files_changed: list[str] | None = None,
        commits: list[str] | None = None,
        verification: dict[str, bool] | None = None,
    ) -> None:
        if engine not in VALID_ENGINES:
            raise ValueError(f"Invalid engine: {engine}")
        with self._transaction():
            self._conn.execute(
                """
                INSERT INTO session_log
                    (timestamp, engine, model, session_id, summary, features_touched, files_changed, commits, verification)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(), engine, model, session_id, summary,
                    json.dumps(features_touched or []),
                    json.dumps(files_changed or []),
                    json.dumps(commits or []),
                    json.dumps(verification or {}),
                ),
            )
            self._prune_session_log()

    def get_recent_sessions(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT timestamp, engine, model, session_id, summary, features_touched, "
            "files_changed, commits, verification FROM session_log "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "timestamp": r[0], "engine": r[1], "model": r[2], "session_id": r[3],
                "summary": r[4],
                "features_touched": json.loads(r[5]), "files_changed": json.loads(r[6]),
                "commits": json.loads(r[7]), "verification": json.loads(r[8]),
            }
            for r in rows
        ]

    # ── File Locking ─────────────────────────────────────────

    def acquire_lock(
        self, path: str, *, engine: str, model: str, session_id: str = "", reason: str = ""
    ) -> bool:
        """Atomically acquire a lock. Returns False if another engine already holds it."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=LOCK_TIMEOUT_HOURS)
        with self._transaction():
            self._expire_locks()
            row = self._conn.execute(
                "SELECT engine FROM active_locks WHERE path = ?", (path,)
            ).fetchone()
            if row and row[0] != engine:
                return False  # Held by a different engine — conflict
            self._conn.execute(
                """
                INSERT INTO active_locks (path, engine, model, session_id, locked_at, expires_at, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    engine = excluded.engine, model = excluded.model,
                    session_id = excluded.session_id, locked_at = excluded.locked_at,
                    expires_at = excluded.expires_at, reason = excluded.reason
                """,
                (path, engine, model, session_id, now.isoformat(), expires.isoformat(), reason),
            )
            return True

    def release_lock(self, path: str, *, engine: str) -> None:
        with self._transaction():
            self._conn.execute(
                "DELETE FROM active_locks WHERE path = ? AND engine = ?", (path, engine)
            )

    def get_active_locks(self) -> list[dict[str, Any]]:
        self._expire_locks()
        rows = self._conn.execute(
            "SELECT path, engine, model, session_id, locked_at, expires_at, reason FROM active_locks"
        ).fetchall()
        return [
            {
                "path": r[0],
                "locked_by": {"engine": r[1], "model": r[2], "session_id": r[3]},
                "locked_at": r[4], "expires_at": r[5], "reason": r[6],
            }
            for r in rows
        ]

    # ── Shared Memory ────────────────────────────────────────

    def add_convention(self, key: str, value: str, *, engine: str, model: str) -> None:
        with self._transaction():
            self._conn.execute(
                "INSERT INTO shared_memory_conventions (key, value, added_by_engine, added_by_model, added_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, value, engine, model, _now()),
            )

    def add_gotcha(self, description: str, *, engine: str, model: str) -> None:
        with self._transaction():
            self._conn.execute(
                "INSERT INTO shared_memory_gotchas (description, added_by_engine, added_by_model, added_at) "
                "VALUES (?, ?, ?, ?)",
                (description, engine, model, _now()),
            )

    def add_decision(
        self, title: str, decision: str, rationale: str = "", *, engine: str, model: str
    ) -> None:
        with self._transaction():
            self._conn.execute(
                "INSERT INTO shared_memory_decisions "
                "(title, decision, rationale, made_by_engine, made_by_model, made_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title, decision, rationale, engine, model, _now()),
            )

    def get_shared_memory(self) -> dict[str, list[dict[str, Any]]]:
        conventions = self._conn.execute(
            "SELECT key, value, added_by_engine, added_by_model, added_at FROM shared_memory_conventions"
        ).fetchall()
        gotchas = self._conn.execute(
            "SELECT description, added_by_engine, added_by_model, added_at FROM shared_memory_gotchas"
        ).fetchall()
        decisions = self._conn.execute(
            "SELECT title, decision, rationale, made_by_engine, made_by_model, made_at FROM shared_memory_decisions"
        ).fetchall()
        return {
            "conventions": [
                {"key": r[0], "value": r[1], "added_by": {"engine": r[2], "model": r[3]}, "added_at": r[4]}
                for r in conventions
            ],
            "gotchas": [
                {"description": r[0], "added_by": {"engine": r[1], "model": r[2]}, "added_at": r[3]}
                for r in gotchas
            ],
            "decisions": [
                {"title": r[0], "decision": r[1], "rationale": r[2],
                 "made_by": {"engine": r[3], "model": r[4]}, "made_at": r[5]}
                for r in decisions
            ],
        }

    # ── Meta / Health ────────────────────────────────────────

    def touch_meta(self, *, engine: str, model: str) -> None:
        now = _now()
        with self._transaction():
            for k, v in (("version", "1.0.0"), ("updated_at", now),
                         ("updated_by_engine", engine), ("updated_by_model", model)):
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (k, v),
                )

    def integrity_check(self) -> list[str]:
        """PRAGMA integrity_check — returns [] if the DB file is healthy."""
        rows = self._conn.execute("PRAGMA integrity_check").fetchall()
        return [] if rows == [("ok",)] else [r[0] for r in rows]


class _ImmediateTransaction:
    """`BEGIN IMMEDIATE` context manager — real cross-process write isolation."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def __enter__(self) -> None:
        self._conn.execute("BEGIN IMMEDIATE")

    def __exit__(self, exc_type: object, *_rest: object) -> bool:
        if exc_type is None:
            self._conn.execute("COMMIT")
        else:
            self._conn.execute("ROLLBACK")
        return False


# ── CLI ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Solo-Code Shared State Manager (SQLite, local-only)")
    sub = parser.add_subparsers(dest="command")

    show_parser = sub.add_parser("show", help="Display current shared state summary")
    feat_parser = sub.add_parser("features", help="List feature status")
    feat_parser.add_argument("--status", choices=VALID_STATUSES, help="Filter by status")
    sess_parser = sub.add_parser("sessions", help="Show recent session log")
    sess_parser.add_argument("--limit", type=int, default=5)
    sub.add_parser("locks", help="Show active file locks")
    sub.add_parser("memory", help="Show shared memory entries")
    sub.add_parser("validate", help="Run PRAGMA integrity_check")

    args = parser.parse_args()
    with SharedState() as state:
        if args.command == "show" or args.command is None:
            features = state.get_features()
            print(f"Features: {len(features)}")
            for f in features:
                print(f"  {f['id']} [{f['status']}] — {f.get('name') or '?'} (owner: {f['owner']['engine'] or '-'})")
            print(f"Sessions: {len(state.get_recent_sessions(limit=10_000_000))}")
            print(f"Active locks: {len(state.get_active_locks())}")
        elif args.command == "features":
            for f in state.get_features():
                if args.status and f["status"] != args.status:
                    continue
                print(f"  [{f['status']}] {f['id']}: {f.get('name') or '?'} (owner: {f['owner']['engine'] or '-'})")
        elif args.command == "sessions":
            for s in state.get_recent_sessions(args.limit):
                print(f"  [{s['engine']}] {s['timestamp'][:16]} — {s['summary'][:80]}")
        elif args.command == "locks":
            for lock in state.get_active_locks():
                print(f"  {lock['path']} — locked by {lock['locked_by']['engine']} ({lock['locked_by']['model']})")
        elif args.command == "memory":
            mem = state.get_shared_memory()
            print("Conventions:")
            for c in mem["conventions"]:
                print(f"  {c['key']}: {c['value']}")
            print("Gotchas:")
            for g in mem["gotchas"]:
                print(f"  {g['description']}")
            print("Decisions:")
            for d in mem["decisions"]:
                print(f"  {d['title']}: {d['decision']}")
        elif args.command == "validate":
            errors = state.integrity_check()
            if errors:
                for e in errors:
                    print(f"  ERROR: {e}")
                sys.exit(1)
            print("  OK — valid")
```

### ✅ DỪNG LẠI & XÁC MINH (Task 2)

```powershell
python -c "from tools.shared_state import SharedState; s = SharedState(); s.set_feature_status('feat-001', 'completed', engine='copilot', model='deepseek-chat'); print('Features:', len(s.get_features())); s.close()"
```

**Kết quả mong đợi:** `Features: 1` (không có traceback/exception nào).

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add tools/shared_state.py
git commit -m "feat: add shared_state.py — SQLite-backed cross-engine state (local-only)

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

**Dọn dẹp trước khi qua Task 3:** file test vừa tạo ra `.solocode/shared-state.db` với 1 feature giả (`feat-001`) — CẦN xoá để không lẫn với dữ liệu migrate thật ở Task 4:

```powershell
Remove-Item ".solocode\shared-state.db" -ErrorAction SilentlyContinue
Remove-Item ".solocode\shared-state.db-wal" -ErrorAction SilentlyContinue
Remove-Item ".solocode\shared-state.db-shm" -ErrorAction SilentlyContinue
```

---

## Task 3: Tạo test suite `tools/test_shared_state.py`

**Hành động:** Tạo file mới.

**Đường dẫn:** `tools/test_shared_state.py`

**Nội dung (copy nguyên văn):**

```python
#!/usr/bin/env python3
"""Tests for tools/shared_state.py — SQLite-backed cross-engine shared state."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from tools.shared_state import SharedState


def test_empty_state():
    """New SharedState with no prior data returns empty state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            assert state.get_features() == []
            assert state.get_active_locks() == []


def test_set_feature_status():
    """Setting feature status persists and retrieves correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            state.set_feature_status(
                "feat-001", "in-progress",
                engine="copilot", model="deepseek-chat",
                evidence="PR #42 merged",
            )
        with SharedState(path) as state2:
            feat = state2.get_feature("feat-001")
            assert feat is not None
            assert feat["status"] == "in-progress"
            assert feat["owner"]["engine"] == "copilot"
            assert feat["owner"]["model"] == "deepseek-chat"
            assert feat["evidence"] == "PR #42 merged"


def test_update_existing_feature():
    """Updating an existing feature changes status, not creates duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            state.set_feature_status("feat-001", "not-started", engine="kilo", model="claude")
            state.set_feature_status("feat-001", "completed", engine="opencode", model="gpt-4o")
            features = state.get_features()
            assert len(features) == 1
            assert features[0]["status"] == "completed"
            assert features[0]["owner"]["engine"] == "opencode"


def test_acquire_lock():
    """Acquiring a lock marks the file as locked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            ok = state.acquire_lock("src/auth.py", engine="copilot", model="deepseek", reason="Fixing bug")
            assert ok is True
            locks = state.get_active_locks()
            assert len(locks) == 1
            assert locks[0]["path"] == "src/auth.py"
            assert locks[0]["locked_by"]["engine"] == "copilot"


def test_lock_conflict():
    """Two different engines cannot lock the same file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            assert state.acquire_lock("src/auth.py", engine="kilo", model="deepseek") is True
            assert state.acquire_lock("src/auth.py", engine="copilot", model="gpt-4o") is False


def test_release_lock():
    """Releasing a lock removes it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            state.acquire_lock("src/auth.py", engine="kilo", model="claude")
            assert len(state.get_active_locks()) == 1
            state.release_lock("src/auth.py", engine="kilo")
            assert len(state.get_active_locks()) == 0


def test_add_session_entry():
    """Session entries are ordered newest first."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            state.add_session_entry(
                engine="copilot", model="deepseek-chat",
                summary="Fixed auth bug",
                files_changed=["src/auth.py"],
                verification={"security_scan": True},
            )
            state.add_session_entry(
                engine="kilo", model="claude-sonnet",
                summary="Refactored database layer",
                files_changed=["src/db.py"],
            )
            sessions = state.get_recent_sessions(limit=5)
            assert len(sessions) == 2
            assert sessions[0]["engine"] == "kilo"
            assert sessions[1]["engine"] == "copilot"


def test_add_shared_memory():
    """Conventions, gotchas, and decisions are stored correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            state.add_convention("branch_naming", "feature/<slug>", engine="copilot", model="gpt-4o")
            state.add_gotcha("ruff config in .ruff.toml only, not pyproject.toml", engine="kilo", model="claude")
            state.add_decision(
                "Use SQLite for shared state",
                "Chose SQLite over JSON+manual locking for real cross-process transaction isolation",
                rationale="stdlib only, BEGIN IMMEDIATE gives real write isolation",
                engine="copilot", model="gpt-4o",
            )
            mem = state.get_shared_memory()
            assert len(mem["conventions"]) == 1
            assert len(mem["gotchas"]) == 1
            assert len(mem["decisions"]) == 1
            assert mem["conventions"][0]["key"] == "branch_naming"


def test_integrity_check():
    """A fresh database always passes integrity_check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        with SharedState(path) as state:
            assert state.integrity_check() == []


def test_concurrent_lock_acquire():
    """Two threads racing to lock the same path — exactly one must win, no crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "shared-state.db"
        results: list[bool] = []
        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def worker(engine: str) -> None:
            try:
                with SharedState(path) as state:
                    barrier.wait()
                    results.append(state.acquire_lock("src/shared.py", engine=engine, model="test"))
            except Exception as e:  # noqa: BLE001 — test must observe any crash, not hide it
                errors.append(e)

        t1 = threading.Thread(target=worker, args=("kilo",))
        t2 = threading.Thread(target=worker, args=("copilot",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert errors == [], f"No exception should be raised during lock contention, got: {errors}"
        assert sorted(results) == [False, True], f"Exactly one thread should win the lock, got: {results}"
```

### ✅ DỪNG LẠI & XÁC MINH (Task 3)

```powershell
python -m pytest tools/test_shared_state.py -v
```

**Kết quả mong đợi:** `10 passed` (không có `failed`, không có `error`).

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add tools/test_shared_state.py
git commit -m "test: add test_shared_state.py — unit + concurrency tests for SQLite shared state

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 4: Tạo migration script `tools/migrate_to_shared_state.py` (bước 1 — chỉ features)

**Hành động:** Tạo file mới.

**Đường dẫn:** `tools/migrate_to_shared_state.py`

**Nội dung (copy nguyên văn):**

```python
#!/usr/bin/env python3
"""
One-time migration: .opencode/state/feature_list.json → .solocode/shared-state.db
Idempotent — an toàn khi chạy nhiều lần (feature đã tồn tại sẽ bị bỏ qua, không ghi đè).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".opencode" / "state" / "feature_list.json"


def migrate_features() -> int:
    if not SRC.exists():
        print(f"[SKIP] Source not found: {SRC}")
        return 1

    from tools.shared_state import SharedState

    data = json.loads(SRC.read_text(encoding="utf-8"))
    features = data["features"]
    print(f"Found {len(features)} features in source")

    migrated = 0
    with SharedState() as state:
        for feat in features:
            existing = state.get_feature(feat["id"])
            if existing:
                print(f"  [{feat['id']}] Already exists — skipping")
                continue
            state.set_feature_status(
                feat["id"],
                feat["status"],
                engine="opencode",
                model="unknown",
                evidence=feat.get("evidence", ""),
                name=feat.get("name", ""),
            )
            migrated += 1
            print(f"  [{feat['id']}] Migrated: {feat.get('status', '?')} — {feat.get('name', feat['id'])}")

        total = len(state.get_features())

    if migrated > 0:
        print(f"\nMigrated {migrated} features")
    else:
        print("\nNo new features to migrate — all exist in shared state")
    print(f"Shared state now has {total} features")
    return 0


if __name__ == "__main__":
    sys.exit(migrate_features())
```

### ✅ DỪNG LẠI & XÁC MINH (Task 4)

```powershell
python tools/migrate_to_shared_state.py
```

**Kết quả mong đợi:** dòng cuối `Shared state now has 19 features` (hoặc số lượng feature thực tế đang có trong `.opencode/state/feature_list.json` — kiểm tra bằng lệnh dưới nếu không chắc):

```powershell
python -c "import json; print(len(json.load(open('.opencode/state/feature_list.json'))['features']))"
```

Nếu số khớp:

```powershell
python .github/scripts/security_scan.py .
git add tools/migrate_to_shared_state.py
git commit -m "feat: migrate features from opencode to shared state (SQLite)

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

**TUYỆT ĐỐI KHÔNG chạy `git add .solocode/shared-state.db`** — file này cố tình local-only.

---

## Task 5: Mở rộng migration script — thêm migrate session log

**Hành động:** THAY THẾ TOÀN BỘ nội dung file `tools/migrate_to_shared_state.py` bằng nội dung dưới đây (không phải chỉnh sửa từng phần — xoá hết nội dung cũ, dán nội dung mới vào).

**Đường dẫn:** `tools/migrate_to_shared_state.py`

**Nội dung mới (copy nguyên văn, thay thế toàn bộ file):**

```python
#!/usr/bin/env python3
"""
One-time migration:
  .opencode/state/feature_list.json → .solocode/shared-state.db (features)
  .opencode/state/progress.md       → .solocode/shared-state.db (session_log)
Idempotent — an toàn khi chạy nhiều lần.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES_SRC = ROOT / ".opencode" / "state" / "feature_list.json"
PROGRESS_SRC = ROOT / ".opencode" / "state" / "progress.md"


def migrate_features() -> int:
    if not FEATURES_SRC.exists():
        print(f"[SKIP] Source not found: {FEATURES_SRC}")
        return 1

    from tools.shared_state import SharedState

    data = json.loads(FEATURES_SRC.read_text(encoding="utf-8"))
    features = data["features"]
    print(f"Found {len(features)} features in source")

    migrated = 0
    with SharedState() as state:
        for feat in features:
            existing = state.get_feature(feat["id"])
            if existing:
                print(f"  [{feat['id']}] Already exists — skipping")
                continue
            state.set_feature_status(
                feat["id"],
                feat["status"],
                engine="opencode",
                model="unknown",
                evidence=feat.get("evidence", ""),
                name=feat.get("name", ""),
            )
            migrated += 1
            print(f"  [{feat['id']}] Migrated: {feat.get('status', '?')} — {feat.get('name', feat['id'])}")

        total = len(state.get_features())

    if migrated > 0:
        print(f"\nMigrated {migrated} features")
    else:
        print("\nNo new features to migrate — all exist in shared state")
    print(f"Shared state now has {total} features")
    return 0


def migrate_sessions() -> int:
    """Migrate .opencode/state/progress.md sessions to shared state session_log."""
    if not PROGRESS_SRC.exists():
        print("[SKIP] progress.md not found")
        return 0

    from tools.shared_state import SharedState

    content = PROGRESS_SRC.read_text(encoding="utf-8")
    # Khớp dòng dạng: "## 2026-06-23 — Mở rộng deploy.py: ..."
    sessions = re.findall(r'##\s+(\d{4}-\d{2}-\d{2})\s*[—–-]\s*(.+)', content)

    migrated = 0
    with SharedState() as state:
        existing_count = len(state.get_recent_sessions(limit=10_000_000))
        for date_str, summary in reversed(sessions):  # cũ nhất trước để giữ đúng thứ tự
            state.add_session_entry(
                engine="opencode",
                model="unknown",
                summary=f"[{date_str}] {summary.strip()}",
            )
            migrated += 1
        total = len(state.get_recent_sessions(limit=10_000_000))

    if migrated > 0:
        print(f"Migrated {migrated} session entries (had {existing_count} before)")
    else:
        print("No session entries found in progress.md")
    print(f"Shared state now has {total} session_log entries")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", action="store_true", help="Chỉ migrate session log")
    parser.add_argument("--all", action="store_true", help="Migrate cả features và sessions")
    args = parser.parse_args()

    rc = 0
    if args.all or not args.sessions:
        rc |= migrate_features()
    if args.all or args.sessions:
        rc |= migrate_sessions()
    sys.exit(rc)
```

### ✅ DỪNG LẠI & XÁC MINH (Task 5)

```powershell
python tools/migrate_to_shared_state.py --all
```

**Kết quả mong đợi:** in ra `Migrated N session entries` với N ≥ 1 (số session thực tế có trong `progress.md`), và không có traceback.

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add tools/migrate_to_shared_state.py
git commit -m "feat: migrate session log from progress.md to shared state

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 6: Tạo 4 file instruction cho 4 engine (Kilo, OpenCode, Copilot, Gemini)

**Hành động:** Tạo **4 file mới**, nội dung **giống hệt nhau**, chỉ khác đường dẫn:

1. `.copilot/instruction/shared-state.md`
2. `.kilo/instruction/shared-state.md`
3. `.opencode/instruction/shared-state.instructions.md`
4. `.gemini/antigravity/instruction/shared-state.md` (**LƯU Ý:** `.gemini/` không có thư mục `instruction/` ở root — cấu trúc thật là `.gemini/antigravity/instruction/`, đã xác minh bằng `list_dir`. KHÔNG tạo nhầm ở `.gemini/instruction/`.)

**Nội dung (copy nguyên văn cho CẢ 4 file — không đổi gì):**

```markdown
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

Nếu `python tools/shared_state.py validate` báo lỗi, hoặc thao tác đọc/ghi báo `sqlite3.DatabaseError` — xoá file DB và migrate lại từ đầu (dữ liệu gốc vẫn còn ở `.opencode/state/feature_list.json` và `progress.md`, không mất):

```bash
rm .solocode/shared-state.db .solocode/shared-state.db-wal .solocode/shared-state.db-shm
python tools/migrate_to_shared_state.py --all
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
```

### ✅ DỪNG LẠI & XÁC MINH (Task 6)

```powershell
python -c "from pathlib import Path; paths = ['.copilot/instruction/shared-state.md', '.kilo/instruction/shared-state.md', '.opencode/instruction/shared-state.instructions.md', '.gemini/antigravity/instruction/shared-state.md']; print(all(Path(p).is_file() for p in paths))"
```

**Kết quả mong đợi:** `True`

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add .copilot/instruction/shared-state.md .kilo/instruction/shared-state.md .opencode/instruction/shared-state.instructions.md .gemini/antigravity/instruction/shared-state.md
git commit -m "feat: add shared-state instruction for all 4 engines including Gemini

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 7: Thêm section vào `.github/copilot-instructions.md`

**Hành động:** Mở file `.github/copilot-instructions.md`. Tìm dòng chính xác sau (đây là dòng cuối cùng của bảng "Model Providers"):

```
- If analyzing large files / repos → prefer `gemini-2.5-pro` (1M token context)
```

Ngay **sau** dòng đó (trước dòng `## Skills System`), chèn thêm đoạn sau (giữ nguyên 1 dòng trống trước và sau):

```markdown

## Shared State — Cross-Engine Collaboration (MANDATORY)

This project uses `.solocode/shared-state.db` (SQLite, local-only — NOT committed to git) as the single source of truth for development status across all 4 engines (Kilo, OpenCode, Copilot, Gemini).

### Session Start
1. Read state via `python tools/shared_state.py show`
2. Check `active_locks` — avoid editing files locked by another engine
3. Check `features` — find one `in-progress` (or promote a `not-started` → `in-progress`)
4. Review recent session log entries for context
5. Load `shared_memory` conventions/gotchas into current session context

### Session End (MANDATORY — before stopping)
Run the following Python before ending your session:
```python
from tools.shared_state import SharedState

with SharedState() as state:
    state.set_feature_status("feat-XXX", "completed", engine="copilot", model="<your-model>", evidence="<what you did>")
    state.add_session_entry(
        engine="copilot",
        model="<your-model>",
        summary="<one-line summary of what was done>",
        features_touched=["feat-XXX"],
        files_changed=["path/to/file1.py", "path/to/file2.py"],
        verification={"security_scan": True, "integration_tests": True},
    )
```

Use `python tools/shared_state.py show` / `features` / `locks` to inspect current state.
```

### ✅ DỪNG LẠI & XÁC MINH (Task 7)

```powershell
Select-String -Path ".github/copilot-instructions.md" -Pattern "Shared State — Cross-Engine Collaboration \(MANDATORY\)"
```

**Kết quả mong đợi:** tìm thấy đúng 1 dòng khớp.

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add .github/copilot-instructions.md
git commit -m "feat: add shared state protocol to copilot rulebook

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 8: Thêm health check vào `tools/garden.py`

**Hành động:** Mở file `tools/garden.py`.

**Bước 1:** Tìm đoạn code chính xác sau (định nghĩa hàm `run_engine_checks`, ngay phía trên nó):

```python
def run_engine_checks(
    src: Path, dst: Path, dst_label: str,
    *,
    instruction_suffix: bool = False,
    skip_set: set[str] | None = None,
) -> list[str]:
```

Chèn đoạn code sau **NGAY TRƯỚC** dòng `def run_engine_checks(`:

```python
def check_shared_state() -> list[str]:
    """Check that .solocode/shared-state.db exists and passes integrity_check."""
    issues: list[str] = []
    db_path = ROOT / ".solocode" / "shared-state.db"

    if not db_path.exists():
        issues.append("Missing: .solocode/shared-state.db (run 'python tools/migrate_to_shared_state.py')")
        return issues

    from tools.shared_state import SharedState
    from datetime import datetime, timezone, timedelta

    with SharedState(db_path) as state:
        errors = state.integrity_check()
        if errors:
            issues.append(f"Corrupt DB: .solocode/shared-state.db — {errors}")
            return issues

        now = datetime.now(timezone.utc)
        for feat in state.get_features():
            if feat["status"] == "in-progress" and feat["last_updated"]:
                try:
                    dt = datetime.fromisoformat(feat["last_updated"])
                    if now - dt > timedelta(days=7):
                        issues.append(f"Stale feature: {feat['id']} in-progress since {feat['last_updated'][:10]}")
                except ValueError:
                    pass

    return issues


def run_engine_checks(
    src: Path, dst: Path, dst_label: str,
    *,
    instruction_suffix: bool = False,
    skip_set: set[str] | None = None,
) -> list[str]:
```

**QUAN TRỌNG:** đoạn `def run_engine_checks(...)` ở trên chỉ là để bạn xác định đúng vị trí — KHÔNG xoá hay viết lại thân hàm `run_engine_checks` đã có sẵn trong file, chỉ chèn `check_shared_state()` phía trước nó.

**Bước 2:** Tìm đoạn code chính xác sau trong hàm `main()`:

```python
    print(f"\nTotal drift issues: {len(all_issues)}")
    if all_issues:
        print("Run 'python tools/generate_harness.py --harness all' to fix.")
        return 1
    print("Garden is clean — no drift detected.")
    return 0
```

Thay thế bằng (thêm gọi `check_shared_state()` trước dòng in tổng số):

```python
    # Shared state health (không thuộc riêng engine nào)
    print("\n--- Shared State ---")
    shared_issues = check_shared_state()
    if shared_issues:
        print("[DRIFT] Shared state:")
        for i in shared_issues:
            print(f"  {i}")
        all_issues.extend(shared_issues)
    else:
        print("[OK] Shared state")

    print(f"\nTotal drift issues: {len(all_issues)}")
    if all_issues:
        print("Run 'python tools/generate_harness.py --harness all' to fix.")
        return 1
    print("Garden is clean — no drift detected.")
    return 0
```

### ✅ DỪNG LẠI & XÁC MINH (Task 8)

```powershell
python tools/garden.py
```

**Kết quả mong đợi:** thấy dòng `--- Shared State ---` và `[OK] Shared state` (không phải `[DRIFT]`), script kết thúc với exit code phù hợp (không traceback).

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add tools/garden.py
git commit -m "feat: add shared state health check (SQLite integrity_check) to garden

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 9: Thêm integration test vào `tools/test_integration.py`

**Hành động:** Mở file `tools/test_integration.py`.

**Bước 1:** Tìm đoạn code chính xác sau (định nghĩa hàm `main`, ngay phía trên nó):

```python
def main() -> int:
    print("=" * 60)
    print(" OpenCode + Copilot Harness — Integration Tests")
    print("=" * 60)
```

Chèn đoạn code sau **NGAY TRƯỚC** dòng `def main() -> int:`:

```python
def test_shared_state() -> None:
    print("\n--- Shared State ---")
    db_path = ROOT / ".solocode" / "shared-state.db"
    check("shared-state.db exists", db_path.is_file())

    if db_path.is_file():
        from tools.shared_state import SharedState
        with SharedState(db_path) as state:
            errors = state.integrity_check()
            check("  integrity_check passes", errors == [], f"errors: {errors}")

            features = state.get_features()
            check("  feature count >= 19", len(features) >= 19, f"got {len(features)}")

            for f in features:
                if f["status"] == "in-progress":
                    check(f"  {f['id']}: has owner", f["owner"].get("engine") is not None)
```

**QUAN TRỌNG — bắt buộc, nếu bỏ qua bước này integration test SẼ FAIL:** Task 6 vừa thêm 1 file instruction mới vào cả `.copilot/instruction/` và `.opencode/instruction/`. Trước khi thêm Task 6, cả 2 thư mục này đã có sẵn đúng 9 file (đã xác minh bằng `list_dir`), và code hiện tại của `test_integration.py` đang hard-code kiểm tra `== 9`. Sau Task 6, số file thành 10 → PHẢI cập nhật 2 chỗ sau, nếu không 2 test này sẽ FAIL:

Tìm dòng chính xác sau (trong hàm `test_instructions`, block OpenCode):

```python
def test_instructions() -> None:
    print("\n--- Instructions (expect 8) ---")
    inst_dir = OPENCODE / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.instructions.md"))
    check(f"instruction count = {len(files)}", len(files) == 9, f"got {len(files)}")
```

Thay bằng:

```python
def test_instructions() -> None:
    print("\n--- Instructions (expect 10) ---")
    inst_dir = OPENCODE / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.instructions.md"))
    check(f"instruction count = {len(files)}", len(files) == 10, f"got {len(files)}")
```

Tìm dòng chính xác sau (trong hàm `test_copilot_instructions`):

```python
def test_copilot_instructions() -> None:
    print("\n--- Copilot Instructions (expect 8) ---")
    inst_dir = COPILOT / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.md"))
    check(f"instruction count = {len(files)}", len(files) == 9, f"got {len(files)}")
```

Thay bằng:

```python
def test_copilot_instructions() -> None:
    print("\n--- Copilot Instructions (expect 10) ---")
    inst_dir = COPILOT / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.md"))
    check(f"instruction count = {len(files)}", len(files) == 10, f"got {len(files)}")
```

**Bước 2:** Tìm đoạn code chính xác sau bên trong hàm `main()`:

```python
    test_tools()
    test_config()

    print("\n  [Copilot Engine]")
```

Thay thế bằng (thêm gọi `test_shared_state()` giữa 2 block):

```python
    test_tools()
    test_config()

    test_shared_state()

    print("\n  [Copilot Engine]")
```

### ✅ DỪNG LẠI & XÁC MINH (Task 9)

```powershell
python tools/test_integration.py
```

**Kết quả mong đợi:** thấy block `--- Shared State ---` với các dòng `PASS`, dòng cuối `Results: N pass, 0 fail` (0 fail).

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add tools/test_integration.py
git commit -m "test: add shared state integration tests (SQLite integrity_check)

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Task 10: Cập nhật tài liệu — README, SPEC, `.harness.lock`

### Bước 1: `README.md`

Tìm dòng chính xác sau (dòng cuối cùng của bảng "Structure", ngay trước heading `## Gates`):

```
| `docs/specs/` | Architecture specs, migration plans, historical docs |

## Gates
```

Thay thế bằng (chèn thêm section mới giữa 2 phần, giữ nguyên `## Gates` phía sau):

```
| `docs/specs/` | Architecture specs, migration plans, historical docs |

## Shared State (Cross-Engine, Local-Only)

All 4 engines share a single SQLite file at `.solocode/shared-state.db` — **local-only, không commit git** (thư mục `.solocode/` đã bị `.gitignore` chặn):

- **`features`** — status + ownership (not-started / in-progress / completed / blocked)
- **`session_log`** — mỗi session được ghi lại: engine, model, files changed, verification (giữ tối đa 1000 dòng gần nhất)
- **`active_locks`** — ngăn 2 engine sửa cùng 1 file cùng lúc (tự hết hạn sau 2 giờ)
- **`shared_memory_*`** — conventions, gotchas, decisions dùng chung giữa các engine

```bash
python tools/shared_state.py show
python tools/shared_state.py features
python tools/shared_state.py locks
```

## Gates
```

### Bước 2: `SPEC.md`

Tìm dòng chính xác sau trong bảng "1.1 File cấu hình":

```
| `docs/specs/` | Kho spec/RFC | Có ngày, có status |

## 2. File cấu hình hợp lệ [HARD]
```

Thay thế bằng (thêm 1 dòng mới vào bảng):

```
| `docs/specs/` | Kho spec/RFC | Có ngày, có status |
| `.solocode/shared-state.db` | Cross-engine shared state (SQLite) | Local-only, KHÔNG commit git — xem `tools/shared_state.py` |

## 2. File cấu hình hợp lệ [HARD]
```

### Bước 3: `.harness.lock`

Tìm dòng chính xác sau:

```
version = "3.3.0"
```

Thay thế bằng:

```
version = "3.4.0"
```

> **Lưu ý:** version hiện tại đã là `3.3.0` (không phải `3.2.0`) — đã xác minh trước khi viết kế hoạch này. Bump lên `3.4.0` cho tính năng shared-state.

### ✅ DỪNG LẠI & XÁC MINH (Task 10)

```powershell
Select-String -Path "README.md" -Pattern "Shared State \(Cross-Engine, Local-Only\)"
Select-String -Path "SPEC.md" -Pattern "shared-state.db"
Select-String -Path ".harness.lock" -Pattern 'version = "3.4.0"'
```

**Kết quả mong đợi:** cả 3 lệnh đều tìm thấy đúng 1 dòng khớp, không lỗi.

Nếu đúng:

```powershell
python .github/scripts/security_scan.py .
git add README.md SPEC.md .harness.lock
git commit -m "docs: document local-only SQLite shared state layer in README, SPEC, harness.lock

Co-Authored-By: Solo-Code <admin@solo-code.com>"
```

---

## Xác minh tổng thể (sau khi xong CẢ 10 task)

Chạy lần lượt, TẤT CẢ phải pass trước khi báo cáo hoàn thành:

| # | Lệnh | Kết quả mong đợi |
|---|---|---|
| 1 | `python -m pytest tools/test_shared_state.py -v` | Tất cả pass, bao gồm `test_concurrent_lock_acquire` |
| 2 | `python tools/test_integration.py` | `Results: N pass, 0 fail` |
| 3 | `python tools/garden.py` | `[OK] Shared state`, `Garden is clean` |
| 4 | `python tools/migrate_to_shared_state.py --all` | Chạy lại vẫn OK (idempotent — không lỗi khi chạy lần 2) |
| 5 | `python .github/scripts/security_scan.py .` | Clean, 0 issues |
| 6 | `python .github/scripts/checklist.py .` | Pass toàn bộ |
| 7 | `ruff check tools/shared_state.py tools/test_shared_state.py tools/migrate_to_shared_state.py` | 0 errors |

Nếu CẢ 7 gate đều pass → báo cáo hoàn thành cho người dùng, liệt kê các file đã tạo/sửa và các commit đã tạo. Nếu bất kỳ gate nào fail → DỪNG, không tự sửa thêm gì khác ngoài phạm vi task liên quan, báo lỗi cụ thể cho người dùng.

## Tổng kết

| Stage | Task | File |
|---|---|---|
| 1. Foundation | Task 1–3 | `tools/shared_state_schema.sql`, `tools/shared_state.py`, `tools/test_shared_state.py` (mới) |
| 2. Migration | Task 4–5 | `tools/migrate_to_shared_state.py` (mới, viết 2 lần), `.solocode/shared-state.db` sinh ra (KHÔNG commit) |
| 3. Instructions | Task 6 | 4 file instruction — Kilo, OpenCode, Copilot, Gemini (mới) |
| 4. Engine Updates | Task 7–9 | `.github/copilot-instructions.md`, `tools/garden.py`, `tools/test_integration.py` (sửa) |
| 5. Docs | Task 10 | `README.md`, `SPEC.md`, `.harness.lock` (sửa) |

## Rủi ro đã xử lý bằng thiết kế SQLite + local-only

| Rủi ro | Trạng thái |
|---|---|
| Race condition khi 2 engine cùng ghi | Đã xử lý — mỗi ghi là 1 transaction `BEGIN IMMEDIATE` độc lập |
| Crash khi gọi lock lúc đang bị giữ | Đã xử lý — SQLite tự xử lý contention qua `timeout=30`, không còn code lock thủ công |
| Stale locks chặn công việc | Đã xử lý — `_expire_locks()` chạy trước mỗi thao tác lock |
| `session_log` phình to vô hạn | Đã xử lý — `_prune_session_log()` giữ tối đa 1000 dòng |
| Không sync multi-machine/CI | Chấp nhận (trade-off đã chọn) — local-only cho giai đoạn này |
| Gemini engine bị bỏ sót instruction | Đã xử lý — Task 6 có đủ 4 file |
| Engine không tự giác theo protocol | Chưa xử lý — vẫn dựa vào LLM đọc instruction; `garden.py` phát hiện feature "stale in-progress" >7 ngày như lưới an toàn |
| Integration test FAIL do instruction count lệch (9→10 sau khi thêm `shared-state.md`) | Đã xử lý (phát hiện bởi model cấp thấp khi review) — Task 9 cập nhật `test_instructions()` và `test_copilot_instructions()` từ `== 9` lên `== 10` |
| `_prune_session_log` xoá nhầm khi 2 session cùng `timestamp` | Đã xử lý (phát hiện bởi model cấp thấp khi review) — thêm `ORDER BY timestamp DESC, id DESC` cho thứ tự xác định |
| Không có hướng dẫn khi `.db` bị corrupt | Đã xử lý (phát hiện bởi model cấp thấp khi review) — thêm mục "Nếu DB bị hỏng" vào nội dung instruction Task 6 |
| `.gemini/` chưa có trong `garden.py` parity check | Chấp nhận — không phải regression của plan này, `garden.py` chưa từng check Gemini trước đó |
| Task 6 dùng sai path `.gemini/instruction/` (thực tế là `.gemini/antigravity/instruction/`) | Đã xử lý (phát hiện bởi DeepSeek khi review) — đã xác minh bằng `list_dir` và sửa cả 3 chỗ: danh sách file, lệnh verify, lệnh `git add` |





