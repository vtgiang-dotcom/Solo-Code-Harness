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


def test_check_memory_covers_decisions_archive():
    """check_memory() scans every *.md in memory/, so decisions-archive.md
    (cold storage, uncapped by memory_gate) must still be parity-checked --
    it's exempt from the SIZE cap, not from the drift check."""
    kilo = ROOT / ".kilo"
    assert (kilo / "memory" / "decisions-archive.md").is_file()
    assert (ROOT / ".claude" / "memory" / "decisions-archive.md").is_file()
    assert (ROOT / ".copilot" / "memory" / "decisions-archive.md").is_file()
    issues = garden.check_memory(kilo, ROOT / ".claude", ".claude")
    assert not any("decisions-archive" in i for i in issues)


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


def test_live_repo_claude_md_matches_template():
    """CLAUDE.md and its generator template silently diverged once, so
    regenerating would have DELETED real hand-edited content. Guard that."""
    assert garden.check_claude_md_regenerable() == []


def test_claude_md_drift_is_detected():
    """The check must actually fail on divergence -- a drift check that can
    never fail is what let the template fall behind unnoticed."""
    claude_path = ROOT / "CLAUDE.md"
    original = claude_path.read_bytes()
    try:
        claude_path.write_bytes(original + b"\n# JUNK-DRIFT-LINE\n")
        assert garden.check_claude_md_regenerable() != []
    finally:
        claude_path.write_bytes(original)


def test_claude_md_check_ignores_line_ending_differences():
    """Git checks out CRLF on Windows for this LF-committed file, so a
    byte-exact compare would fail for every Windows dev; only content counts."""
    claude_path = ROOT / "CLAUDE.md"
    original = claude_path.read_bytes()
    try:
        claude_path.write_bytes(original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        assert garden.check_claude_md_regenerable() == []
    finally:
        claude_path.write_bytes(original)


def test_check_doc_counts_detects_wrong_count(tmp_path):
    # Set up .kilo/ structure
    kilo = tmp_path / ".kilo"
    (kilo / "skill" / "skill-a").mkdir(parents=True)
    (kilo / "agents").mkdir(parents=True)
    (kilo / "agents" / "agent-a.md").write_text("body", encoding="utf-8")
    (kilo / "command").mkdir(parents=True)
    (kilo / "command" / "command-a.md").write_text("body", encoding="utf-8")
    (kilo / "instruction").mkdir(parents=True)
    (kilo / "instruction" / "instruction-a.md").write_text("body", encoding="utf-8")

    # Write a test file with a wrong count
    (tmp_path / "AGENTS.md").write_text("Solo-Code Harness active: 2 skills, 1 agent.", encoding="utf-8")

    issues = garden.check_doc_counts(root=tmp_path)
    assert len(issues) > 0
    assert any("claimed 2 skills, but ground truth is 1" in i for i in issues)


def test_check_doc_counts_clean_when_correct(tmp_path):
    # Set up .kilo/ structure
    kilo = tmp_path / ".kilo"
    (kilo / "skill" / "skill-a").mkdir(parents=True)
    (kilo / "agents").mkdir(parents=True)
    (kilo / "agents" / "agent-a.md").write_text("body", encoding="utf-8")
    (kilo / "command").mkdir(parents=True)
    (kilo / "command" / "command-a.md").write_text("body", encoding="utf-8")
    (kilo / "instruction").mkdir(parents=True)
    (kilo / "instruction" / "instruction-a.md").write_text("body", encoding="utf-8")

    # Write a test file with correct count
    (tmp_path / "AGENTS.md").write_text("Solo-Code Harness active: 1 skill, 1 agent.", encoding="utf-8")

    issues = garden.check_doc_counts(root=tmp_path)
    assert issues == []



def _make_engines(tmp_path, *, gemini_commands: int = 2):
    """Build a minimal multi-engine tree.

    .kilo/ gets 1 skill + 1 agent + 1 command + 1 instruction;
    .gemini/antigravity/ gets the same but a configurable command count, so a
    genuine per-engine divergence can be exercised.
    """
    kilo = tmp_path / ".kilo"
    (kilo / "skill" / "skill-a").mkdir(parents=True)
    for sub, name in (("agents", "agent-a.md"), ("command", "command-a.md"),
                      ("instruction", "instruction-a.md")):
        (kilo / sub).mkdir(parents=True, exist_ok=True)
        (kilo / sub / name).write_text("body", encoding="utf-8")

    gem = tmp_path / ".gemini" / "antigravity"
    (gem / "skills" / "skill-a").mkdir(parents=True)
    (gem / "agents").mkdir(parents=True)
    (gem / "agents" / "agent-a.md").write_text("body", encoding="utf-8")
    (gem / "commands").mkdir(parents=True)
    for i in range(gemini_commands):
        (gem / "commands" / f"cmd-{i}.md").write_text("body", encoding="utf-8")
    return kilo, gem


def test_check_doc_counts_respects_engine_divergence(tmp_path):
    """A line describing `.gemini/` is measured against .gemini/, not .kilo/.

    Engines legitimately differ — .gemini/ ships fewer commands than .kilo/ —
    so comparing every number to the source of truth reports false drift.
    """
    _make_engines(tmp_path, gemini_commands=2)

    (tmp_path / "README.md").write_text(
        "| `.gemini/` | Gemini: skills (1), commands (2) |\n", encoding="utf-8"
    )

    assert garden.check_doc_counts(root=tmp_path) == []


def test_check_doc_counts_flags_wrong_count_for_named_engine(tmp_path):
    """Per-engine resolution must still catch a count that is wrong *for that engine*."""
    _make_engines(tmp_path, gemini_commands=2)

    (tmp_path / "README.md").write_text(
        "| `.gemini/` | Gemini: skills (1), commands (7) |\n", encoding="utf-8"
    )

    issues = garden.check_doc_counts(root=tmp_path)
    assert any(
        "claimed 7 commands" in i and "ground truth is 2" in i and ".gemini/" in i
        for i in issues
    ), issues


def test_check_doc_counts_unnamed_line_falls_back_to_kilo(tmp_path):
    """A line naming no engine is checked against .kilo/, the source of truth."""
    _make_engines(tmp_path, gemini_commands=2)

    (tmp_path / "AGENTS.md").write_text("Harness active: 1 skill, 2 commands.", encoding="utf-8")

    issues = garden.check_doc_counts(root=tmp_path)
    assert any("claimed 2 commands, but ground truth is 1" in i for i in issues), issues
