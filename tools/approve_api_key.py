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
    python tools/approve_api_key.py --check    # quiet; exit 3 if rejected
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
EXIT_REJECTED = 3


def key_from_env_file(env_file: pathlib.Path) -> str:
    """Read ANTHROPIC_API_KEY out of a `.env` file, or "" if absent."""
    try:
        text = env_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == "ANTHROPIC_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def resolve_key() -> tuple[str, str]:
    """Return (key, where-it-came-from).

    Falls back to `.env` in the current directory because the failure this
    script fixes is per-key and shows up in *deployed* projects, where the
    user is standing in the target repo with no launcher-loaded shell. The
    shell wins when both are set -- that is the key the session will use.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key, "shell environment"
    env_file = pathlib.Path.cwd() / ".env"
    return key_from_env_file(env_file), str(env_file)


def is_rejected(key: str, config: pathlib.Path | None = None) -> bool:
    """True only when this key's fingerprint is in the stored `rejected` list.

    Every uncertain case is False: a missing config, unreadable JSON or a
    too-short key are not evidence of a rejection, and this answer gates a
    launcher preflight. Guessing "rejected" there would block startup over
    nothing.

    `config` resolves at call time, not as a default argument -- a default is
    bound at import, which silently pinned this to the real ~/.claude.json.
    """
    config = config if config is not None else CONFIG
    if len(key) < FINGERPRINT_LEN:
        return False
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    responses = data.get("customApiKeyResponses") or {}
    rejected = responses.get("rejected") or []
    return key[-FINGERPRINT_LEN:] in rejected


def check() -> int:
    """Preflight for the launcher: exit EXIT_REJECTED if the key is rejected.

    Deliberately near-silent -- it runs on every launch, so it prints only
    when there is a real problem the user must act on.
    """
    key, _ = resolve_key()
    if not key or not is_rejected(key):
        return 0
    print(
        "WARNING: this ANTHROPIC_API_KEY is marked *rejected* in ~/.claude.json.\n"
        "  Interactive Claude Code will fail with 'Not logged in / Please run "
        "/login'\n"
        "  (-p and --bare modes ignore the list, so this hides well).\n"
        "  Fix: python tools/approve_api_key.py --apply"
    )
    return EXIT_REJECTED


def main() -> int:
    if "--check" in sys.argv:
        return check()
    apply = "--apply" in sys.argv

    key, source = resolve_key()
    if not key:
        print("ERROR: no ANTHROPIC_API_KEY in this shell or in ./.env")
        print("Run this through the launcher, or fill in .env first.")
        return 1
    print(f"key from : {source}")
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
