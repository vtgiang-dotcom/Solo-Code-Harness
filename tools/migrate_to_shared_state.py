#!/usr/bin/env python3
"""
One-time migration: .opencode/state/feature_list.json → .solocode/shared-state.db
Idempotent — an toàn khi chạy nhiều lần (feature đã tồn tại sẽ bị bỏ qua, không ghi đè).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Windows console cp1252 không encode được Unicode tiếng Việt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
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
        # Nguồn dùng "done" thay vì "completed" — chuẩn hóa khi migrate
        STATUS_MAP = {"done": "completed"}
        for feat in features:
            existing = state.get_feature(feat["id"])
            if existing:
                print(f"  [{feat['id']}] Already exists — skipping")
                continue
            status = STATUS_MAP.get(feat["status"], feat["status"])
            state.set_feature_status(
                feat["id"],
                status,
                engine="opencode",
                model="unknown",
                evidence=feat.get("evidence", ""),
                name=feat.get("name", ""),
            )
            migrated += 1
            # Tránh lỗi encoding Windows — chỉ hiển thị tên FEATURE hoặc id
            display_name = feat.get("name") or feat["id"]
            print(f"  [{feat['id']}] Migrated: {feat.get('status', '?')}: {display_name}", flush=True)

        total = len(state.get_features())

    if migrated > 0:
        print(f"\nMigrated {migrated} features")
    else:
        print("\nNo new features to migrate — all exist in shared state")
    print(f"Shared state now has {total} features")
    return 0


if __name__ == "__main__":
    sys.exit(migrate_features())
