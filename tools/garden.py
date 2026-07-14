#!/usr/bin/env python3
"""
Garden — Drift Detection
=========================
Checks for stale artifacts, missing generated files, and dead links
between .kilo/ ↔ .opencode/ and .kilo/ ↔ .copilot/ directories.

Usage:
    python tools/garden.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SKIP_FILE = ROOT / "tools" / "opencode-skip-skills.txt"


def _load_skip_skills() -> set[str]:
    """Read opencode-skip-skills.txt — skills intentionally excluded."""
    if not SKIP_FILE.is_file():
        return set()
    return {
        line.strip()
        for line in SKIP_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _check_parity_dir(
    src: Path, dst: Path, dst_label: str, subdir: str
) -> list[str]:
    """Generic parity check: all src/subdir files exist in dst/subdir with same name."""
    issues: list[str] = []
    src_dir = src / subdir
    dst_dir = dst / subdir
    if not src_dir.is_dir():
        return issues
    src_files = {f.name for f in src_dir.iterdir() if f.is_file() and f.suffix == ".md"}
    dst_files = {f.name for f in dst_dir.iterdir()} if dst_dir.is_dir() else set()
    missing = src_files - dst_files
    for name in sorted(missing):
        issues.append(f"Missing {subdir}: {dst_label}/{subdir}/{name}")
    stale = dst_files - src_files
    for name in sorted(stale):
        issues.append(f"Stale {subdir} (no source): {dst_label}/{subdir}/{name}")
    return issues


def _check_parity_dir_glob(
    src: Path, dst: Path, dst_label: str, subdir: str
) -> list[str]:
    """Parity check for directories (skills): subdirs must exist in both."""
    issues: list[str] = []
    src_dir = src / subdir
    dst_dir = dst / subdir
    if not src_dir.is_dir():
        return issues
    src_dirs = {d.name for d in src_dir.iterdir() if d.is_dir()}
    dst_dirs = {d.name for d in dst_dir.iterdir()} if dst_dir.is_dir() else set()
    missing = src_dirs - dst_dirs
    for name in sorted(missing):
        issues.append(f"Missing {subdir}: {dst_label}/{subdir}/{name}/")
    stale = dst_dirs - src_dirs
    for name in sorted(stale):
        issues.append(f"Stale {subdir} (no source): {dst_label}/{subdir}/{name}/")
    return issues


def check_agents(src: Path, dst: Path, dst_label: str) -> list[str]:
    """Check that all src/agents/ files have a dst/ copy."""
    return _check_parity_dir(src, dst, dst_label, "agents")


def check_instructions(src: Path, dst: Path, dst_label: str) -> list[str]:
    """Check that all src/instruction/ files have a direct dst/ copy (same filename)."""
    issues: list[str] = []
    src_dir = src / "instruction"
    dst_dir = dst / "instruction"
    if not src_dir.is_dir():
        return issues
    src_names = {f.name for f in src_dir.iterdir() if f.is_file()}
    dst_names = {f.name for f in dst_dir.iterdir()} if dst_dir.is_dir() else set()
    missing = src_names - dst_names
    for name in sorted(missing):
        issues.append(f"Missing instruction: {dst_label}/instruction/{name}")
    return issues


def check_instructions_opencode(src: Path, dst: Path, dst_label: str) -> list[str]:
    """Check that all src/instruction/ files have dst/ copy with .instructions.md suffix."""
    issues: list[str] = []
    src_dir = src / "instruction"
    dst_dir = dst / "instruction"
    if not src_dir.is_dir():
        return issues
    src_names = {f.stem for f in src_dir.iterdir() if f.is_file()}
    dst_names = {
        f.stem.replace(".instructions", "")
        for f in dst_dir.iterdir()
    } if dst_dir.is_dir() else set()
    missing = src_names - dst_names
    for name in sorted(missing):
        issues.append(f"Missing instruction: {dst_label}/instruction/{name}.instructions.md")
    return issues


def check_memory(src: Path, dst: Path, dst_label: str) -> list[str]:
    """Check that all src/memory/ files have dst/ copy."""
    return _check_parity_dir(src, dst, dst_label, "memory")


def check_skills(dst: Path, dst_label: str) -> list[str]:
    """Check each skill directory has a valid SKILL.md."""
    issues: list[str] = []
    skill_dir = dst / "skill"
    if not skill_dir.is_dir():
        return issues
    for entry in sorted(skill_dir.iterdir()):
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                issues.append(f"Skill missing SKILL.md: {dst_label}/skill/{entry.name}")
    return issues


def check_skill_parity(
    src: Path, dst: Path, dst_label: str, *, skip_set: set[str] | None = None
) -> list[str]:
    """Check that all src/skill/ dirs exist in dst/skill/, respecting skip list."""
    issues = _check_parity_dir_glob(src, dst, dst_label, "skill")
    if skip_set:
        issues = [i for i in issues if not _issue_matches_skip(i, skip_set)]
    return issues


def _issue_matches_skip(issue: str, skip_set: set[str]) -> bool:
    """Check if a skill parity issue is for an intentionally skipped skill."""
    # "Missing skill: .opencode/skill/block-no-verify/"
    # "Stale skill (no source): .opencode/skill/block-no-verify/"
    for name in skip_set:
        if f"/skill/{name}/" in issue or f"/skill/{name}" in issue.rstrip("/"):
            return True
    return False


def check_shared_state() -> list[str]:
    """Check that .solocode/shared-state.db exists and passes integrity_check."""
    issues: list[str] = []
    db_path = ROOT / ".solocode" / "shared-state.db"

    if not db_path.exists():
        issues.append("Missing: .solocode/shared-state.db (run 'python tools/migrate_to_shared_state.py')")
        return issues

    from tools.shared_state import SharedState

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
    """Run all parity checks for one engine."""
    issues: list[str] = []
    checks = [
        (f"Agent drift ({dst_label})", lambda: check_agents(src, dst, dst_label)),
        (
            f"Instruction drift ({dst_label})",
            lambda: (
                check_instructions_opencode(src, dst, dst_label)
                if instruction_suffix
                else check_instructions(src, dst, dst_label)
            ),
        ),
        (f"Memory drift ({dst_label})", lambda: check_memory(src, dst, dst_label)),
        (
            f"Skill parity ({dst_label})",
            lambda: check_skill_parity(src, dst, dst_label, skip_set=skip_set),
        ),
        (f"Skill health ({dst_label})", lambda: check_skills(dst, dst_label)),
    ]
    for name, check_fn in checks:
        result = check_fn()
        if result:
            print(f"[DRIFT] {name}:")
            for i in result:
                print(f"  {i}")
            issues.extend(result)
        else:
            print(f"[OK] {name}")
    return issues


def main() -> int:
    kilo = ROOT / ".kilo"

    all_issues: list[str] = []
    skip_skills = _load_skip_skills()

    # .opencode/ engine — uses .instructions.md suffix
    print("--- .opencode/ ---")
    all_issues.extend(
        run_engine_checks(kilo, ROOT / ".opencode", ".opencode", instruction_suffix=True, skip_set=skip_skills)
    )

    # .copilot/ engine — direct copy, no suffix
    print("\n--- .copilot/ ---")
    all_issues.extend(
        run_engine_checks(kilo, ROOT / ".copilot", ".copilot", instruction_suffix=False)
    )

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


if __name__ == "__main__":
    sys.exit(main())
