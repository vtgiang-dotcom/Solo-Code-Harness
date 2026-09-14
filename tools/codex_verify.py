#!/usr/bin/env python3
"""Run the repository verification gates from Codex CLI."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = [
    [sys.executable, ".github/scripts/security_scan.py", "."],
    [sys.executable, "tools/validate_schemas.py"],
    [sys.executable, "tools/garden.py"],
    [sys.executable, ".github/scripts/check_skips.py", "tools/"],
    [sys.executable, "-m", "pytest", "tools/", "-q"],
]


def main() -> int:
    for command in COMMANDS:
        print(f"\n$ {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"FAILED (exit {result.returncode})")
            return result.returncode
    print("\nAll Codex verification gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
