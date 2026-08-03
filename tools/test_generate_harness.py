#!/usr/bin/env python3
"""
Harness Generator Tests
=======================
Guards for tools/generate_harness.py's instruction mirroring.

Background: .copilot/instruction/ and .gemini/antigravity/instruction/ were
"manually kept in parity with .kilo/ and verified by tools/garden.py". Garden
detected content drift there and told the user to run

    python tools/generate_harness.py --harness all

...which only regenerated .claude/ and therefore fixed nothing. The advertised
remedy was a no-op and the real fix was an undocumented hand copy.

Usage:
    python -m pytest tools/test_generate_harness.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import garden, generate_harness  # noqa: E402

MIRRORS = [
    (".copilot", Path(".copilot") / "instruction"),
    (".gemini/antigravity", Path(".gemini") / "antigravity" / "instruction"),
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_tree(tmp_path: Path) -> Path:
    _write(tmp_path / ".kilo" / "instruction" / "rules-git.md", "SOURCE\n")
    for _, rel in MIRRORS:
        _write(tmp_path / rel / "rules-git.md", "SOURCE\n")
    return tmp_path


def test_sync_repairs_drifted_mirror(tmp_path):
    root = _fake_tree(tmp_path)
    for _, rel in MIRRORS:
        _write(root / rel / "rules-git.md", "DRIFTED\n")

    synced = generate_harness.sync_instruction_mirrors(root / ".kilo", root)

    assert synced == len(MIRRORS)
    for _, rel in MIRRORS:
        assert (root / rel / "rules-git.md").read_text(encoding="utf-8") == "SOURCE\n"


def test_sync_is_idempotent(tmp_path):
    root = _fake_tree(tmp_path)
    assert generate_harness.sync_instruction_mirrors(root / ".kilo", root) == 0


def test_sync_does_not_invent_files(tmp_path):
    """Engines carry different instruction subsets — don't add new ones.

    garden.check_instructions() only diffs names present in both trees, so
    creating files here would manufacture parity nobody asked for.
    """
    root = _fake_tree(tmp_path)
    _write(root / ".kilo" / "instruction" / "kilo-only.md", "X\n")

    generate_harness.sync_instruction_mirrors(root / ".kilo", root)

    for _, rel in MIRRORS:
        assert not (root / rel / "kilo-only.md").exists(), "sync invented a file"


def test_sync_skips_absent_mirror_dirs(tmp_path):
    _write(tmp_path / ".kilo" / "instruction" / "a.md", "A\n")
    assert generate_harness.sync_instruction_mirrors(tmp_path / ".kilo", tmp_path) == 0


def test_garden_remediation_command_actually_fixes_drift(tmp_path):
    """The command garden prints must resolve the drift garden reports.

    This is the real regression: garden's advice was a no-op for mirror
    instruction drift. Asserted against garden's own checker so the two
    cannot diverge again.
    """
    root = _fake_tree(tmp_path)
    src, dst = root / ".kilo", root / ".copilot"
    _write(dst / "instruction" / "rules-git.md", "DRIFTED\n")

    assert garden.check_instruction_content(src, dst, ".copilot"), (
        "expected garden to report drift before sync"
    )
    generate_harness.sync_instruction_mirrors(src, root)
    assert not garden.check_instruction_content(src, dst, ".copilot"), (
        "garden still reports drift after running its own remediation"
    )


def test_real_repo_mirrors_are_in_sync():
    """The checked-in mirrors must already match .kilo/."""
    for label, rel in MIRRORS:
        issues = garden.check_instruction_content(
            ROOT / ".kilo", ROOT / rel.parent, label
        )
        assert not issues, f"{label} instruction drift in repo: {issues}"


# ─── memory mirrors ─────────────────────────────────────────────────────────
#
# Same gap as the instruction mirrors, found while pruning MEMORY.md: garden's
# check_memory() docstring said .copilot/memory/ is a "manually-kept mirror
# (no auto-generator regenerates them)", so garden reported memory drift and
# its own remediation command could not clear it.

MEMORY_MIRROR = Path(".copilot") / "memory"


def _fake_memory_tree(tmp_path: Path) -> Path:
    _write(tmp_path / ".kilo" / "memory" / "MEMORY.md", "SOURCE\n")
    _write(tmp_path / MEMORY_MIRROR / "MEMORY.md", "SOURCE\n")
    return tmp_path


def test_memory_sync_repairs_drift(tmp_path):
    root = _fake_memory_tree(tmp_path)
    _write(root / MEMORY_MIRROR / "MEMORY.md", "DRIFTED\n")

    assert generate_harness.sync_memory_mirrors(root / ".kilo", root) == 1
    assert (root / MEMORY_MIRROR / "MEMORY.md").read_text(encoding="utf-8") == "SOURCE\n"


def test_memory_sync_is_idempotent(tmp_path):
    root = _fake_memory_tree(tmp_path)
    assert generate_harness.sync_memory_mirrors(root / ".kilo", root) == 0


def test_memory_sync_does_not_invent_files(tmp_path):
    root = _fake_memory_tree(tmp_path)
    _write(root / ".kilo" / "memory" / "kilo-only.md", "X\n")
    generate_harness.sync_memory_mirrors(root / ".kilo", root)
    assert not (root / MEMORY_MIRROR / "kilo-only.md").exists()


def test_garden_memory_remediation_actually_fixes_drift(tmp_path):
    """garden's advertised fix command must clear the memory drift it reports."""
    root = _fake_memory_tree(tmp_path)
    src, dst = root / ".kilo", root / ".copilot"
    _write(dst / "memory" / "MEMORY.md", "DRIFTED\n")

    assert garden.check_memory(src, dst, ".copilot"), "expected drift before sync"
    generate_harness.sync_memory_mirrors(src, root)
    assert not garden.check_memory(src, dst, ".copilot"), (
        "garden still reports memory drift after running its own remediation"
    )


def test_real_repo_memory_mirrors_are_in_sync():
    issues = garden.check_memory(ROOT / ".kilo", ROOT / ".copilot", ".copilot")
    assert not issues, f".copilot memory drift in repo: {issues}"


def test_memory_md_is_under_the_hard_cap():
    """MEMORY.md is injected every session and blocked by memory_gate at 8k.

    Checked for every engine copy, since the hook reads .claude/memory/ while
    .kilo/ is the source people edit.
    """
    for engine in (".kilo", ".claude", ".copilot"):
        f = ROOT / engine / "memory" / "MEMORY.md"
        if not f.is_file():
            continue
        n = len(f.read_text(encoding="utf-8"))
        assert n < 8000, f"{engine}/memory/MEMORY.md is {n} chars (hard cap 8000)"
