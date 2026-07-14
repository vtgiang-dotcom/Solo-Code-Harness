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

# Windows console cp1252 không encode được Unicode tiếng Việt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
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

    # Nguồn dùng "done" thay vì "completed" — chuẩn hóa khi migrate
    status_map = {"done": "completed"}
    migrated = 0
    with SharedState() as state:
        for feat in features:
            existing = state.get_feature(feat["id"])
            if existing:
                print(f"  [{feat['id']}] Already exists — skipping")
                continue
            status = status_map.get(feat["status"], feat["status"])
            state.set_feature_status(
                feat["id"],
                status,
                engine="opencode",
                model="unknown",
                evidence=feat.get("evidence", ""),
                name=feat.get("name", ""),
            )
            migrated += 1
            display_name = feat.get("name") or feat["id"]
            print(f"  [{feat['id']}] Migrated: {feat.get('status', '?')}: {display_name}", flush=True)

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
        # Lấy summary các session hiện có để tránh duplicate khi chạy lại
        existing_summaries = {s["summary"] for s in state.get_recent_sessions(limit=10_000_000)}
        for date_str, summary in reversed(sessions):  # cũ nhất trước để giữ đúng thứ tự
            s = f"[{date_str}] {summary.strip()}"
            if s in existing_summaries:
                continue
            state.add_session_entry(
                engine="opencode",
                model="unknown",
                summary=s,
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
