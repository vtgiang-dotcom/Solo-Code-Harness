#!/usr/bin/env python3
"""
Garden — Drift Detection
=========================
Checks for stale artifacts, missing generated files, and dead links
between .kilo/ and .opencode/ directories.

Usage:
    python tools/garden.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_agents(kilo: Path, opencode: Path) -> list[str]:
    """Check that all .kilo/agents/ files have an .opencode/ copy."""
    issues: list[str] = []
    src = kilo / "agents"
    dst = opencode / "agents"
    if not src.is_dir():
        return issues
    src_files = {f.name for f in src.iterdir() if f.suffix == ".md"}
    dst_files = {f.name for f in dst.iterdir()} if dst.is_dir() else set()
    missing = src_files - dst_files
    for name in sorted(missing):
        issues.append(f"Missing agent: .opencode/agents/{name}")
    stale = dst_files - src_files
    for name in sorted(stale):
        issues.append(f"Stale agent (no source): .opencode/agents/{name}")
    return issues


def check_instructions(kilo: Path, opencode: Path) -> list[str]:
    """Check that all .kilo/instruction/ files have .opencode/ copy.

    .kilo/ files are named foo.md → .opencode/ files are foo.instructions.md.
    Strip .instructions suffix from dst stem before comparing.
    """
    issues: list[str] = []
    src = kilo / "instruction"
    dst = opencode / "instruction"
    if not src.is_dir():
        return issues
    src_names = {f.stem for f in src.iterdir() if f.is_file()}
    # dst stem e.g. "security-patterns.instructions" → strip suffix → "security-patterns"
    dst_names = {f.stem.replace(".instructions", "") for f in dst.iterdir()} if dst.is_dir() else set()
    missing = src_names - dst_names
    for name in sorted(missing):
        issues.append(f"Missing instruction: .opencode/instruction/{name}.instructions.md")
    return issues


def check_memory(kilo: Path, opencode: Path) -> list[str]:
    """Check that all .kilo/memory/ files have .opencode/ copy."""
    issues: list[str] = []
    src = kilo / "memory"
    dst = opencode / "memory"
    if not src.is_dir():
        return issues
    src_names = {f.name for f in src.iterdir() if f.is_file()}
    dst_names = {f.name for f in dst.iterdir()} if dst.is_dir() else set()
    missing = src_names - dst_names
    for name in sorted(missing):
        issues.append(f"Missing memory: .opencode/memory/{name}")
    return issues


def check_skill_symlinks(opencode: Path) -> list[str]:
    """Check each skill has a valid SKILL.md."""
    issues: list[str] = []
    skill_dir = opencode / "skill"
    if not skill_dir.is_dir():
        return issues
    for entry in sorted(skill_dir.iterdir()):
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                issues.append(f"Skill missing SKILL.md: {entry.name}")
    return issues


def main() -> int:
    kilo = ROOT / ".kilo"
    opencode = ROOT / ".opencode"

    all_issues: list[str] = []
    checks = [
        ("Agent drift", lambda: check_agents(kilo, opencode)),
        ("Instruction drift", lambda: check_instructions(kilo, opencode)),
        ("Memory drift", lambda: check_memory(kilo, opencode)),
        ("Skill health", lambda: check_skill_symlinks(opencode)),
    ]

    for name, check_fn in checks:
        issues = check_fn()
        if issues:
            print(f"[DRIFT] {name}:")
            for i in issues:
                print(f"  {i}")
            all_issues.extend(issues)
        else:
            print(f"[OK] {name}")

    print(f"\nTotal drift issues: {len(all_issues)}")
    if all_issues:
        print("Run 'python tools/generate_harness.py --harness all' to fix.")
        return 1
    print("Garden is clean — no drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
