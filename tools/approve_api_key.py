"""Approve the current ANTHROPIC_API_KEY in Claude Code's interactive gate.

Why this exists: interactive Claude Code asks "use this custom API key?" and
records the answer in ~/.claude.json -> customApiKeyResponses. A stored "no"
makes interactive sessions fail with "Not logged in · Please run /login",
while `-p` (print) mode and `--bare` ignore the list entirely -- so the
failure is invisible to every non-interactive check.

PowerShell 5.1 cannot do this edit: ConvertFrom-Json rejects ~/.claude.json
because it holds case-variant project keys ("D:/..." and "d:/..."), which it
treats as duplicates. Python keeps them distinct.

Usage:
    python tools/approve_api_key.py            # dry run, writes nothing
    python tools/approve_api_key.py --apply    # back up, then write
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import sys

CONFIG = pathlib.Path(os.path.expanduser("~/.claude.json"))
FINGERPRINT_LEN = 20


def main() -> int:
    apply = "--apply" in sys.argv

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY is not set in this shell.")
        print("Run this through the launcher, or load .env first.")
        return 1
    if len(key) < FINGERPRINT_LEN:
        print(f"ERROR: key is shorter than {FINGERPRINT_LEN} chars.")
        return 1
    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} not found.")
        return 1

    # Claude Code fingerprints a custom key by its last 20 characters.
    fingerprint = key[-FINGERPRINT_LEN:]

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    responses = data.setdefault("customApiKeyResponses", {})
    approved = responses.setdefault("approved", [])
    rejected = responses.setdefault("rejected", [])

    print(f"config   : {CONFIG}")
    print(f"approved : {len(approved)} entry(s)")
    print(f"rejected : {len(rejected)} entry(s)")
    print(f"this key : {'REJECTED' if fingerprint in rejected else 'not in rejected'}"
          f" / {'approved' if fingerprint in approved else 'not approved'}")

    if fingerprint in approved and fingerprint not in rejected:
        print("\nAlready approved -- nothing to do.")
        return 0

    new_rejected = [x for x in rejected if x != fingerprint]
    new_approved = approved + ([fingerprint] if fingerprint not in approved else [])

    print("\nplanned change:")
    print(f"  approved : {len(approved)} -> {len(new_approved)}")
    print(f"  rejected : {len(rejected)} -> {len(new_rejected)}")
    print("  (other rejected entries are left alone)")

    if not apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply to commit.")
        return 0

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CONFIG.with_suffix(f".json.bak-{stamp}")
    shutil.copy2(CONFIG, backup)

    responses["approved"] = new_approved
    responses["rejected"] = new_rejected
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Re-read to prove the file is still valid JSON and the change landed.
    verify = json.loads(CONFIG.read_text(encoding="utf-8"))["customApiKeyResponses"]
    ok = fingerprint in verify["approved"] and fingerprint not in verify["rejected"]
    print(f"\nbackup   : {backup}")
    print(f"written  : approved={len(verify['approved'])} rejected={len(verify['rejected'])}")
    print(f"verified : {'OK' if ok else 'FAILED -- restore from the backup above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
