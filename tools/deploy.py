#!/usr/bin/env python3
"""
deploy.py — Deploy Solo-Code Harness to a target project.

Copies all harness files (rules, skills, plugin, config, scripts)
to a target directory. Uses existing deploy patterns from Solo-Code-Harness.

Usage:
    python tools/deploy.py /path/to/target-project
    python tools/deploy.py /path/to/target-project --dry-run
    python tools/deploy.py /path/to/target-project --engine opencode   # OpenCode only
    python tools/deploy.py /path/to/target-project --engine all        # All engines
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════
# Deployment manifest — what to copy where
# ═══════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent

# Files to copy (relative to ROOT)
ROOT_FILES = [
    "AGENTS.md",
    "opencode.json",
    "kilo.jsonc",
    ".mcp.json",
    ".gitleaks.toml",
    ".ruff.toml",
    "pyproject.toml",
    "Makefile",
    "opencode.ps1",
    "SPEC.md",
    "verify.sh",
    "agent.yaml",
    "extensions_config.json",
]

# Directories to copy (relative to ROOT)
DIRS_ALL = [
    ".opencode",
    ".kilo",
    ".gemini",
    ".github",
    ".contracts",
    "docs/specs",
]

DIRS_OPENCODE = [
    ".opencode",
    ".github",
    ".contracts",
    "docs/specs",
]

# Patterns to exclude from copy
EXCLUDE_DIRS = {
    ".pytest_cache", ".ruff_cache", "node_modules", ".git",
    "__pycache__", ".venv", "venv",
}
EXCLUDE_FILES = {
    ".env", "usage.log", "usage.jsonl",
    ".DS_Store", "Thumbs.db",
}


# ═══════════════════════════════════════════════════════════════════════
# Core logic
# ═══════════════════════════════════════════════════════════════════════

def should_copy(path: Path) -> bool:
    """Check if a file/dir should be copied (not excluded)."""
    name = path.name
    # Check if any parent directory is excluded
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    if path.is_file() and name in EXCLUDE_FILES:
        return False
    if path.is_file() and name.endswith(".pyc"):
        return False
    return True


def copy_file(src: Path, dst: Path, dry_run: bool) -> str:
    """Copy a single file. Returns status string."""
    if dry_run:
        return "  [DRY] " + str(dst.relative_to(dst.anchor))

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.copy2(src, dst)
        return "  [UPD] " + str(dst.relative_to(dst.anchor))
    else:
        shutil.copy2(src, dst)
        return "  [NEW] " + str(dst.relative_to(dst.anchor))


def copy_tree(src: Path, dst: Path, dry_run: bool) -> tuple[int, int, list[str]]:
    """Recursively copy a directory tree. Returns (new, updated, skipped)."""
    new, updated, skipped = 0, 0, []

    if not src.is_dir():
        return 0, 0, [f"  [SKIP] {src} — not found"]

    for item in src.rglob("*"):
        if not should_copy(item):
            continue

        rel = item.relative_to(src)
        target = dst / rel

        if item.is_dir():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
        else:
            if dry_run:
                skipped.append(f"  [DRY] {target}")
                new += 1
            elif target.exists():
                shutil.copy2(item, target)
                updated += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                new += 1

    return new, updated, skipped


def deploy(target: str, *, engine: str = "all", dry_run: bool = False) -> int:
    """Deploy harness to target directory."""
    target_path = Path(target).resolve()

    if not target_path.exists():
        print(f"[ERROR] Target does not exist: {target_path}")
        return 1

    if not target_path.is_dir():
        print(f"[ERROR] Target is not a directory: {target_path}")
        return 1

    # ── Select directories based on engine ───────────────────────
    if engine == "opencode":
        dirs = DIRS_OPENCODE
    else:
        dirs = DIRS_ALL

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"=== Solo-Code Harness Deploy ({mode}) ===")
    print(f"  Source : {ROOT}")
    print(f"  Target : {target_path}")
    print(f"  Engine : {engine}")
    print()

    total_new, total_upd, total_skip = 0, 0, 0

    # ── Copy root files ─────────────────────────────────────────
    print("--- Root Files ---")
    for f in ROOT_FILES:
        src = ROOT / f
        if not src.exists():
            print(f"  [SKIP] {f} — not found")
            total_skip += 1
            continue
        status = copy_file(src, target_path / f, dry_run)
        print(status)
        if "[NEW]" in status or "[DRY]" in status:
            total_new += 1
        elif "[UPD]" in status:
            total_upd += 1

    # ── Copy directories ────────────────────────────────────────
    for d in dirs:
        src = ROOT / d
        name = d.rstrip("/").replace("\\", "/")
        print(f"\n--- {name}/ ---")
        dst = target_path / d
        n, u, skipped = copy_tree(src, dst, dry_run)

        # Only show first 5 skipped for dry runs (avoids spam)
        for s in skipped[:5]:
            print(s)
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more files (use --dry-run for full list)")

        total_new += n
        total_upd += u
        total_skip += len(skipped)

        if not dry_run:
            print(f"  Copied: {n} new, {u} updated")

    # ── Summary ─────────────────────────────────────────────────
    print()
    print("=" * 60)
    if dry_run:
        print(f"  DRY RUN — would deploy {total_new} files, update {total_upd}")
    else:
        print(f"  Deployed: {total_new} new, {total_upd} updated, {total_skip} skipped")
    print("=" * 60)

    # ── Post-deploy instructions ─────────────────────────────────
    if not dry_run:
        print()
        print("  Next steps in target project:")
        print(f"    cd {target_path}")
        print("    python tools/generate_harness.py --harness all")
        print("    python tools/validate_schemas.py")
        print("    python .github/scripts/security_scan.py .")

    return 0


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy Solo-Code Harness to a target project.",
    )
    parser.add_argument(
        "target",
        help="Path to target project directory",
    )
    parser.add_argument(
        "--engine",
        choices=["all", "opencode"],
        default="all",
        help="Which engine harness to deploy (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without making changes",
    )
    args = parser.parse_args()

    return deploy(args.target, engine=args.engine, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
