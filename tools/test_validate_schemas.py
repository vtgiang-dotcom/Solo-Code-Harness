"""Tests for tools/validate_schemas.py"""
import tempfile
from pathlib import Path

from tools.validate_schemas import parse_frontmatter, validate_agent, validate_skill

# ── parse_frontmatter ──────────────────────────────────────────────────────────

def test_parse_valid_frontmatter():
    content = "---\nname: test\ndescription: a test\n---\n# Body"
    result = parse_frontmatter(content)
    assert result == {"name": "test", "description": "a test"}


def test_parse_frontmatter_strips_quotes():
    content = '---\nname: "quoted"\n---\n'
    result = parse_frontmatter(content)
    assert result["name"] == "quoted"


def test_parse_frontmatter_strips_single_quotes():
    content = "---\nname: 'single'\n---\n"
    result = parse_frontmatter(content)
    assert result["name"] == "single"


def test_parse_frontmatter_no_start_marker():
    result = parse_frontmatter("name: test\n")
    assert result is None


def test_parse_frontmatter_no_end_marker():
    result = parse_frontmatter("---\nname: test\n")
    assert result is None


def test_parse_frontmatter_empty_body():
    content = "---\n---\n"
    result = parse_frontmatter(content)
    assert result == {}


def test_parse_frontmatter_skips_comments():
    content = "---\n# comment\nname: test\n---\n"
    result = parse_frontmatter(content)
    assert result == {"name": "test"}


def test_parse_frontmatter_skips_blank_lines():
    content = "---\n\nname: test\n\n---\n"
    result = parse_frontmatter(content)
    assert result == {"name": "test"}


# ── validate_agent ─────────────────────────────────────────────────────────────

def test_validate_agent_valid():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\nmodel: claude-3\nvariant: default\n---\n# Agent\n")
        path = Path(f.name)
    errors = validate_agent(path)
    assert errors == []


def test_validate_agent_missing_frontmatter():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("# No frontmatter here\n")
        path = Path(f.name)
    errors = validate_agent(path)
    assert len(errors) == 1
    assert "malformed" in errors[0].lower() or "missing" in errors[0].lower()


def test_validate_agent_empty_frontmatter():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\n---\n# minimal\n")
        path = Path(f.name)
    errors = validate_agent(path)
    assert errors == []


# ── validate_skill ─────────────────────────────────────────────────────────────

def test_validate_skill_valid():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\nname: my-skill\ndescription: does stuff\nslash: /my-skill\n---\n")
        path = Path(f.name)
    errors = validate_skill(path)
    assert errors == []


def test_validate_skill_missing_name():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\ndescription: no name\n---\n")
        path = Path(f.name)
    errors = validate_skill(path)
    assert any("name" in e for e in errors)


def test_validate_skill_missing_frontmatter():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("# just body\n")
        path = Path(f.name)
    errors = validate_skill(path)
    assert len(errors) == 1
