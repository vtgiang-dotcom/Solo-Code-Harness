#!/usr/bin/env python3
"""
Garden Drift-Detection Tests
============================
Unit tests for tools/garden.py's content-level drift checks. Filename-only
parity (a file exists in both .kilo/ and a mirror engine) previously let
real content drift (e.g. .claude/memory/MEMORY.md 19 lines behind source,
or .copilot/.gemini skill bodies silently missing whole sections) go
undetected for a long time. These tests guard the fix: check_memory(),
check_instruction_content(), and check_skill_content() must diff actual
file content, not just names.

Usage:
    python -m pytest tools/test_garden.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import garden  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ─── check_memory (content diff) ────────────────────────────────────────────

def test_check_memory_detects_content_drift(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "memory" / "MEMORY.md", "# Memory\n- [decision] A\n")
    _write(dst / "memory" / "MEMORY.md", "# Memory\n- [decision] A\n- [decision] B\n")
    issues = garden.check_memory(src, dst, ".example")
    assert any("Content drift" in i for i in issues)


def test_check_memory_clean_when_identical(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "memory" / "MEMORY.md", "# Memory\n- [decision] A\n")
    _write(dst / "memory" / "MEMORY.md", "# Memory\n- [decision] A\n")
    assert garden.check_memory(src, dst, ".example") == []


# ─── check_instruction_content ──────────────────────────────────────────────

def test_check_instruction_content_detects_drift(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "instruction" / "rules-git.md", "line one\nline two\n")
    _write(dst / "instruction" / "rules-git.md", "line one\nline TWO (different)\n")
    issues = garden.check_instruction_content(src, dst, ".example")
    assert any("rules-git.md" in i and "Content drift" in i for i in issues)


def test_check_instruction_content_clean_when_identical(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "instruction" / "rules-git.md", "same text\n")
    _write(dst / "instruction" / "rules-git.md", "same text\n")
    assert garden.check_instruction_content(src, dst, ".example") == []


def test_check_instruction_content_missing_dirs_is_silent(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    assert garden.check_instruction_content(src, dst, ".example") == []


# ─── check_skill_content (frontmatter-agnostic) ─────────────────────────────

def test_check_skill_content_ignores_frontmatter_differences(tmp_path):
    """Copilot legitimately uses a different frontmatter schema (quoted
    description + license field) -- that alone must NOT be flagged."""
    src, dst = tmp_path / "src", tmp_path / "dst_skill"
    _write(
        src / "skill" / "plan" / "SKILL.md",
        "---\ndescription: Plan mode.\ndisable-model-invocation: true\n---\n"
        "# Plan\nBody text.\n",
    )
    _write(
        dst / "plan" / "SKILL.md",
        '---\ndescription: "Plan mode."\nlicense: MIT\n---\n'
        "# Plan\nBody text.\n",
    )
    assert garden.check_skill_content(src, dst, ".copilot") == []


def test_check_skill_content_detects_body_drift(tmp_path):
    """A real body difference (missing section) must be flagged even though
    frontmatter matches exactly."""
    src, dst = tmp_path / "src", tmp_path / "dst_skill"
    _write(
        src / "skill" / "code-review-expert" / "SKILL.md",
        "---\ndescription: x\n---\n# Title\nParagraph one.\n## Extra Section\nDetail.\n",
    )
    _write(
        dst / "code-review-expert" / "SKILL.md",
        "---\ndescription: x\n---\n# Title\nParagraph one.\n",
    )
    issues = garden.check_skill_content(src, dst, ".copilot")
    assert any("code-review-expert" in i and "Content drift" in i for i in issues)


def test_check_skill_content_missing_dirs_is_silent(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst_skill"
    assert garden.check_skill_content(src, dst, ".copilot") == []


def test_check_skill_content_skips_skills_missing_on_either_side(tmp_path):
    """A skill that only exists on one side is skill-parity's job, not
    content drift's -- must not raise or false-flag here."""
    src, dst = tmp_path / "src", tmp_path / "dst_skill"
    _write(src / "skill" / "only-in-src" / "SKILL.md", "---\n---\nbody\n")
    dst.mkdir(parents=True)
    assert garden.check_skill_content(src, dst, ".copilot") == []


# ─── _split_frontmatter ──────────────────────────────────────────────────────

def test_split_frontmatter_with_delimiters():
    text = "---\nkey: value\n---\nBody line.\n"
    fm, body = garden._split_frontmatter(text)
    assert fm == "---\nkey: value\n---\n"
    assert body == "Body line.\n"


def test_split_frontmatter_without_delimiters():
    text = "No frontmatter here.\n"
    fm, body = garden._split_frontmatter(text)
    assert fm == ""
    assert body == text


# ─── Live repo regression guard ─────────────────────────────────────────────

def test_live_repo_has_zero_memory_content_drift():
    kilo = ROOT / ".kilo"
    for engine_dir, label in (
        (ROOT / ".claude", ".claude"),
        (ROOT / ".copilot", ".copilot"),
    ):
        issues = garden.check_memory(kilo, engine_dir, label)
        assert issues == [], f"{label} memory drift: {issues}"


def test_live_repo_has_zero_skill_content_drift():
    kilo = ROOT / ".kilo"
    assert garden.check_skill_content(kilo, ROOT / ".copilot" / "skill", ".copilot") == []
    assert garden.check_skill_content(
        kilo, ROOT / ".gemini" / "antigravity" / "skills", ".gemini/antigravity"
    ) == []


def test_live_repo_has_zero_instruction_content_drift():
    kilo = ROOT / ".kilo"
    assert garden.check_instruction_content(kilo, ROOT / ".copilot", ".copilot") == []
    assert garden.check_instruction_content(
        kilo, ROOT / ".gemini" / "antigravity", ".gemini/antigravity"
    ) == []
