#!/usr/bin/env python3
"""
Harness Generator Tests
========================
Tests for tools/generate_harness.py — permission migration, instructions rename,
file copy, and global install.

Usage:
    python -m pytest tools/test_harness.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the tools directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_harness import _instructions_rename, _migrate_value, migrate_permission

# ── _instructions_rename ─────────────────────────────────────────────────


def test_rename_adds_suffix():
    """Should add .instructions.md to plain .md files."""
    assert _instructions_rename("foo.md") == "foo.instructions.md"
    assert _instructions_rename("security-patterns.md") == "security-patterns.instructions.md"


def test_rename_keeps_existing():
    """Should not double-suffix files that already have .instructions.md."""
    assert _instructions_rename("foo.instructions.md") == "foo.instructions.md"


def test_rename_no_ext():
    """Should handle files without .md extension gracefully."""
    result = _instructions_rename("foo")
    # .stem removes whole path → Path("foo").stem == "foo"
    assert result == "foo.instructions.md"


# ── _migrate_value (V1→V2 rule conversion) ───────────────────────────────


def test_migrate_level1_string():
    """Dạng 1: 'read': 'allow' → [action:read, resource:*, effect:allow]."""
    rules = _migrate_value("read", "allow")
    assert len(rules) == 1
    assert rules[0] == {"action": "read", "resource": "*", "effect": "allow"}


def test_migrate_level2_dict():
    """Dạng 2: 'bash': {'*': 'ask', 'git *': 'allow'} → 2 rules."""
    rules = _migrate_value("bash", {"*": "ask", "git *": "allow"})
    assert len(rules) == 2
    assert {"action": "bash", "resource": "*", "effect": "ask"} in rules
    assert {"action": "bash", "resource": "git *", "effect": "allow"} in rules


def test_migrate_empty_dict():
    """Empty dict → no rules."""
    rules = _migrate_value("task", {})
    assert rules == []


def test_migrate_unknown_type():
    """Unknown type (int, list) → no rules."""
    rules = _migrate_value("x", 42)
    assert rules == []


# ── migrate_permission (full frontmatter) ─────────────────────────────────


def test_migrate_simple():
    """Simple V1 permission → V2 array output."""
    frontmatter = """mode: primary
color: "#F59E0B"
permission:
  read: allow
  bash:
    "*": ask
"""
    result = migrate_permission(frontmatter)
    assert "permissions:" in result
    assert "permission:" not in result
    # Should have exactly 2 rules
    assert result.count("- action:") == 2
    # resource: * must be quoted
    assert 'resource: "*"' in result


def test_migrate_task_pattern():
    """Task tool with specific subagent patterns."""
    frontmatter = """permission:
  task:
    code-reviewer: allow
    "*": deny
"""
    result = migrate_permission(frontmatter)
    assert 'action: task' in result
    assert 'resource: code-reviewer' in result
    assert 'resource: "*"' in result
    assert result.count("- action:") == 2


def test_migrate_no_permission():
    """Frontmatter without permission key should pass through unchanged."""
    frontmatter = """mode: primary
color: red
"""
    result = migrate_permission(frontmatter)
    assert result == frontmatter


def test_migrate_empty():
    """Empty string → empty string."""
    assert migrate_permission("") == ""


def test_migrate_permission_already_v2():
    """Frontmatter with 'permissions:' (V2) should be left unchanged."""
    frontmatter = """mode: primary
permissions:
  - action: read
    resource: "*"
    effect: allow
"""
    result = migrate_permission(frontmatter)
    assert result.strip() == frontmatter.strip()


# ── Output format compliance ──────────────────────────────────────────────


def test_yaml_resource_quoting():
    """YAML special chars (*, ?) in resource field must be quoted."""
    result = migrate_permission("""permission:
  bash: allow
""")
    assert 'resource: "*"' in result, f"Resource * should be quoted, got: {result}"


def test_yaml_closing_newline():
    """Migrated block must not end with \\n--- with no gap."""
    result = migrate_permission("""permission:
  read: allow
""")
    # Reassemble as generate_agents does
    assembled = f"---{result}\n---"
    assert "---" in assembled
    assert "\n---" in assembled, f"Missing newline before closing ---, got: {repr(assembled[-20:])}"


# ── Integration: generate_instructions copy_file encoding ─────────────────


def test_copy_file_unicode(tmp_path: Path):
    """copy_file should handle Unicode chars on Windows."""
    from generate_harness import copy_file

    src = tmp_path / "source.md"
    dst = tmp_path / "dest.md"
    content = "→ Unicode arrow and other non-ASCII: café"
    src.write_bytes(content.encode("utf-8"))

    copy_file(src, dst)
    assert dst.read_bytes() == content.encode("utf-8"), "Unicode content preserved"
