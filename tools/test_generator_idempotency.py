#!/usr/bin/env python3
"""
Generator Idempotency Tests
===========================
Both engine generators rewrite their artifacts on every run. That is fine for
content, but an unconditional write also bumps mtime -- and `git status`
compares stat before it reads content, so every generated file showed as
modified while `git diff` showed nothing at all. Measured at 28 files per run
before the guard, and the confusion cost two sessions.

These tests pin the guard in both directions: a second identical write must
leave mtime alone, and a genuine change must still land.

Usage:
    python -m pytest tools/test_generator_idempotency.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_engine
import opencode_engine

# A sentinel timestamp makes an unintended rewrite visible without relying on
# the filesystem's timestamp resolution.
_SENTINEL_MTIME_NS = 1_000_000_000


def _mtime(path: Path) -> int:
    return path.stat().st_mtime_ns


def _set_sentinel_mtime(path: Path) -> None:
    os.utime(path, ns=(_mtime(path), _SENTINEL_MTIME_NS))


# ── claude_engine._write_lf ─────────────────────────────────────────────────


def test_write_lf_skips_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    claude_engine._write_lf(target, "same\n")
    _set_sentinel_mtime(target)
    claude_engine._write_lf(target, "same\n")
    assert _mtime(target) == _SENTINEL_MTIME_NS


def test_write_lf_still_writes_on_change(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    claude_engine._write_lf(target, "one\n")
    _set_sentinel_mtime(target)
    claude_engine._write_lf(target, "two\n")
    assert target.read_text(encoding="utf-8") == "two\n"
    assert _mtime(target) != _SENTINEL_MTIME_NS


def test_write_lf_creates_missing_file(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    claude_engine._write_lf(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"


# ── claude_engine._copy_if_changed ─────────────────────────────────────────


def test_copy_if_changed_skips_identical(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_bytes(b"payload\n")
    dst = tmp_path / "dst.md"
    dst.write_bytes(b"payload\n")
    _set_sentinel_mtime(dst)
    claude_engine._copy_if_changed(src, dst)
    assert _mtime(dst) == _SENTINEL_MTIME_NS


def test_copy_if_changed_copies_different(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_bytes(b"new\n")
    dst = tmp_path / "dst.md"
    dst.write_bytes(b"old\n")
    claude_engine._copy_if_changed(src, dst)
    assert dst.read_bytes() == b"new\n"


def test_copy_if_changed_creates_missing_file(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_bytes(b"payload\n")
    dst = tmp_path / "dst.md"
    claude_engine._copy_if_changed(src, dst)
    assert dst.read_bytes() == b"payload\n"


# ── opencode_engine helpers ─────────────────────────────────────────────────


def test_opencode_write_if_changed_skips_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "agent.md"
    opencode_engine._write_if_changed(target, "same\n")
    _set_sentinel_mtime(target)
    opencode_engine._write_if_changed(target, "same\n")
    assert _mtime(target) == _SENTINEL_MTIME_NS


def test_opencode_write_if_changed_writes_on_change(tmp_path: Path) -> None:
    target = tmp_path / "agent.md"
    opencode_engine._write_if_changed(target, "one\n")
    _set_sentinel_mtime(target)
    opencode_engine._write_if_changed(target, "two\n")
    assert target.read_text(encoding="utf-8") == "two\n"
    assert _mtime(target) != _SENTINEL_MTIME_NS


def test_opencode_write_if_changed_creates_missing_file(tmp_path: Path) -> None:
    target = tmp_path / "agent.md"
    opencode_engine._write_if_changed(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"


def test_opencode_copy_if_changed_skips_identical(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_bytes(b"payload\n")
    dst = tmp_path / "dst.md"
    dst.write_bytes(b"payload\n")
    _set_sentinel_mtime(dst)
    opencode_engine._copy_if_changed(src, dst)
    assert _mtime(dst) == _SENTINEL_MTIME_NS


# ── integration: a full generator run is idempotent ─────────────────────────


@pytest.fixture
def kilo_tree(tmp_path: Path) -> Path:
    """A minimal .kilo/ tree with one artifact of each generated kind."""
    kilo = tmp_path / "kilo"
    (kilo / "agents").mkdir(parents=True)
    (kilo / "command").mkdir()
    (kilo / "instruction").mkdir()
    (kilo / "memory").mkdir()
    (kilo / "skill" / "sample-skill").mkdir(parents=True)
    (kilo / "agents" / "sample.md").write_text(
        "---\nmode: subagent\ncolor: '#ffffff'\n---\nBody text\n", encoding="utf-8"
    )
    (kilo / "command" / "ship.md").write_text(
        "---\ndescription: ship\n---\nShip it\n", encoding="utf-8"
    )
    (kilo / "instruction" / "rules.md").write_text("# Rules\n", encoding="utf-8")
    (kilo / "memory" / "MEMORY.md").write_text("# Memory\n", encoding="utf-8")
    (kilo / "skill" / "sample-skill" / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: sample\n---\n# Skill\n",
        encoding="utf-8",
    )
    return kilo


def test_opencode_generate_all_is_idempotent(tmp_path: Path, kilo_tree: Path) -> None:
    """The second run must leave every artifact's mtime untouched.

    This is the regression guard for the git churn: `git status` reports a file
    as modified on a stat mismatch alone, so an unconditional rewrite made the
    whole generated tree look dirty after every single generator run.
    """
    out = tmp_path / "opencode"
    opencode_engine.generate_all(kilo_tree, out, tmp_path, skip_names=set())
    snapshot = {p: _mtime(p) for p in out.rglob("*") if p.is_file()}
    assert snapshot, "generator produced nothing to compare"

    opencode_engine.generate_all(kilo_tree, out, tmp_path, skip_names=set())

    for path, before in snapshot.items():
        assert _mtime(path) == before, f"{path.name} was rewritten unchanged"


def test_claude_generate_all_is_idempotent(tmp_path: Path, kilo_tree: Path) -> None:
    """The second full Claude generation leaves every artifact untouched."""
    out = tmp_path / "claude"
    claude_engine.generate_all(kilo_tree, out, tmp_path)
    snapshot = {p: _mtime(p) for p in [*out.rglob("*"), tmp_path / "CLAUDE.md"] if p.is_file()}
    assert snapshot, "generator produced nothing to compare"

    claude_engine.generate_all(kilo_tree, out, tmp_path)

    for path, before in snapshot.items():
        assert _mtime(path) == before, f"{path.name} was rewritten unchanged"


def test_claude_skills_sync_changes_and_remove_stale_files(
    tmp_path: Path, kilo_tree: Path
) -> None:
    out = tmp_path / "claude"
    claude_engine.generate_skills(kilo_tree, out)
    destination = out / "skills" / "sample-skill"
    (destination / "stale.txt").write_text("stale\n", encoding="utf-8")
    source = kilo_tree / "skill" / "sample-skill" / "SKILL.md"
    source.write_text("---\nname: sample-skill\n---\n# Updated\n", encoding="utf-8")

    claude_engine.generate_skills(kilo_tree, out)

    assert (destination / "SKILL.md").read_text(encoding="utf-8") == source.read_text(
        encoding="utf-8"
    )
    assert not (destination / "stale.txt").exists()
