#!/usr/bin/env python3
"""
Claude Engine Generator Tests
=============================
Tests for tools/claude_engine.py — frontmatter parsing, permission -> tools
mapping, and command/skill generation.

Usage:
    python -m pytest tools/test_claude_engine.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from claude_engine import (
    _build_tools_allowlist,
    _parse_kilo_permissions,
    _split_frontmatter,
)

# ── _split_frontmatter ───────────────────────────────────────────────────


def test_split_frontmatter_valid():
    content = "---\nname: x\ndescription: y\n---\n# Body\ntext"
    result = _split_frontmatter(content)
    assert result is not None
    fm, body = result
    assert "name: x" in fm
    assert body.strip().startswith("# Body")


def test_split_frontmatter_none():
    assert _split_frontmatter("no frontmatter here") is None


# ── _parse_kilo_permissions ──────────────────────────────────────────────


def test_parse_simple_permissions():
    fm = (
        'description: "System architect"\n'
        "mode: subagent\n"
        "permission:\n"
        "  edit: deny\n"
        "  bash: deny\n"
        "  read: allow\n"
        "  grep: allow\n"
        "  codesearch: allow\n"
    )
    perms, desc, mode = _parse_kilo_permissions(fm)
    assert desc == "System architect"
    assert mode == "subagent"
    assert perms["read"] == "allow"
    assert perms["edit"] == "deny"
    assert perms["bash"] == "deny"


def test_parse_nested_permissions_most_permissive():
    """Nested patterns collapse to the most permissive effect."""
    fm = (
        "permission:\n"
        "  read: allow\n"
        "  edit:\n"
        '    "*": deny\n'
        '    "*.md": allow\n'
        "  bash:\n"
        '    "*": deny\n'
        '    "python *": allow\n'
    )
    perms, _desc, _mode = _parse_kilo_permissions(fm)
    # edit has an allow rule (*.md) -> most permissive is allow
    assert perms["edit"] == "allow"
    assert perms["bash"] == "allow"
    assert perms["read"] == "allow"


# ── _build_tools_allowlist ───────────────────────────────────────────────


def test_tools_allowlist_deny_excluded():
    perms = {"read": "allow", "grep": "allow", "edit": "deny", "bash": "deny"}
    tools = _build_tools_allowlist(perms)
    assert tools == ["Read", "Grep"]
    assert "Edit" not in tools
    assert "Bash" not in tools


def test_tools_allowlist_edit_maps_to_edit_and_write():
    perms = {"edit": "allow"}
    tools = _build_tools_allowlist(perms)
    assert "Edit" in tools
    assert "Write" in tools


def test_tools_allowlist_ask_is_included():
    """'ask' effect counts as allowed for tool exposure."""
    perms = {"bash": "ask"}
    tools = _build_tools_allowlist(perms)
    assert tools == ["Bash"]


def test_tools_allowlist_codesearch_folds_to_grep():
    perms = {"codesearch": "allow"}
    tools = _build_tools_allowlist(perms)
    assert tools == ["Grep"]


def test_tools_allowlist_deterministic_order():
    perms = {"bash": "allow", "read": "allow", "task": "allow", "edit": "allow"}
    tools = _build_tools_allowlist(perms)
    # Must follow _TOOL_ORDER: Read, Grep, Glob, Edit, Write, Bash, Task
    assert tools == ["Read", "Edit", "Write", "Bash", "Task"]
