#!/usr/bin/env python3
"""
solocode-pre-push (git hook) — full verification suite before `git push`.

Runs the six project gates in sequence and blocks the push (exit 1) when any
gate fails. Stdlib-only Python for Windows/macOS/Linux portability.

Installation:
  1) Copy to `.git/hooks/pre-push` and `chmod +x`:
       cp .claude/hooks/pre_push.py .git/hooks/pre-push
       chmod +x .git/hooks/pre-push            # N/A on Windows; git uses sh
     Or symlink on Unix so updates propagate:
       ln -s ../../.claude/hooks/pre_push.py .git/hooks/pre-push
  2) Windows note: Git for Windows invokes hooks via sh, so a `python` on
     PATH is required; `.git/hooks/pre-push` needs no chmod there.

Skip: `git push --no-verify` bypasses the hook entirely (native git flag).

Timeout protection: gates share a 300s total budget; a gate that exhausts the
remainder fails as a timeout instead of hanging the push.

Exit codes: 0 = all gates passed (push allowed); 1 = a gate failed (blocked).
"""

from __future__ import annotations

import subprocess  # noqa: S404 — runs this repo's own pinned verification tools
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOTAL_BUDGET_SECONDS = 300
OUTPUT_LIMIT = 500

# (argv, display name, fix hint). Python tooling is invoked as `python` to
# match the repo's own command conventions (see AGENTS.md).
GATES: tuple[tuple[list[str], str, str], ...] = (
    (["ruff", "check", "."],
     "ruff check",
     "Review and fix ruff lint violations"),
    (["python", "tools/check_lint_budget.py"],
     "lint budget",
     "Review and fix lint budget violations"),
    (["python", "tools/validate_schemas.py"],
     "schema validation",
     "Fix invalid frontmatter schemas"),
    (["python", "tools/garden.py"],
     "garden check",
     "Fix cross-engine parity drift (see tools/garden.py)"),
    (["python", "-m", "pytest", "tools/", "-q"],
     "pytest suite",
     "Fix failing tests"),
    (["python", ".github/scripts/security_scan.py", "."],
     "security scan",
     "Review and fix security scan findings"),
)


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run one gate from the repo root, decoding output as UTF-8.

    `errors="replace"` keeps Windows consoles from raising on non-UTF-8
    output; explicit `encoding` beats the locale default (cp1252).
    """
    return subprocess.run(  # noqa: S603,S607 — fixed argv, no shell
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def truncate(text: str) -> str:
    """Cap gate output at OUTPUT_LIMIT chars for a readable failure line."""
    text = text.strip()
    if len(text) <= OUTPUT_LIMIT:
        return text or "(no output)"
    return text[:OUTPUT_LIMIT] + "..."


def report_failure(step: int, name: str, cmd: list[str],
                   exit_code: int | None, output: str, fix: str) -> None:
    """Print the failure block and block the push."""
    print(f"[PrePush] Gate {step}/{len(GATES)} failed: {name}")
    print(f"  Command: {' '.join(cmd)}")
    if exit_code is None:
        print(f"  Status: timed out after {TOTAL_BUDGET_SECONDS}s total budget")
    else:
        print(f"  Exit code: {exit_code}")
    print(f"  Output: {truncate(output)}")
    print(f"  Fix: {fix}")
    print("[PrePush] Push blocked. Fix issues or use --no-verify to skip.")


def main() -> int:
    print("[PrePush] Running verification gates...")
    start = time.monotonic()
    for step, (cmd, name, fix) in enumerate(GATES, start=1):
        remaining = max(1, TOTAL_BUDGET_SECONDS - int(time.monotonic() - start))
        try:
            proc = run(cmd, remaining)
        except subprocess.TimeoutExpired:
            print(f"  [{step}/{len(GATES)}] {name} ... TIMEOUT")
            report_failure(step, name, cmd, None, f"exceeded the {TOTAL_BUDGET_SECONDS}s total budget", fix)
            return 1
        if proc.returncode == 0:
            print(f"  [{step}/{len(GATES)}] {name} ... OK")
            continue
        output = proc.stdout or proc.stderr
        print(f"  [{step}/{len(GATES)}] {name} ... FAIL")
        report_failure(step, name, cmd, proc.returncode, output, fix)
        return 1
    print("[PrePush] All gates passed. Push allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
