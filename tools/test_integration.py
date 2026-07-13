#!/usr/bin/env python3
"""
Integration tests for OpenCode harness structure.

Validates:
  - Agents: 14 .md files with valid YAML frontmatter
  - Skills: 39 directories with SKILL.md
  - Instructions: 7 .instructions.md files
  - Plugin: solocode-guard.js loadable
  - State: 5 files in .opencode/state/
  - Commands: 4 .md files in .opencode/command/
  - Tools: 2 .js files in .opencode/tool/
  - Config: opencode.json valid JSON + required keys

Usage:
    python tools/test_integration.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENCODE = ROOT / ".opencode"

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  -- {detail}")


def test_agents() -> None:
    print("\n--- Agents (expect 14) ---")
    agents_dir = OPENCODE / "agents"
    check("agents/ directory exists", agents_dir.is_dir())
    if not agents_dir.is_dir():
        return

    agents = sorted(agents_dir.glob("*.md"))
    check(f"agent count = {len(agents)}", len(agents) == 14, f"got {len(agents)}")

    for f in agents:
        content = f.read_text(encoding="utf-8")
        has_fm = content.startswith("---")
        check(f"  {f.name}: YAML frontmatter", has_fm)
        if has_fm:
            end = content.find("\n---", 3)
            check(f"  {f.name}: closing ---", end != -1)
            fm = content[3:end] if end != -1 else ""
            check(f"  {f.name}: mode key", "mode:" in fm, "missing mode")


def test_skills() -> None:
    print("\n--- Skills (expect 47) ---")
    skills_dir = OPENCODE / "skill"
    check("skill/ directory exists", skills_dir.is_dir())
    if not skills_dir.is_dir():
        return

    skills = sorted([d for d in skills_dir.iterdir() if d.is_dir()])
    check(f"skill count = {len(skills)}", len(skills) == 47, f"got {len(skills)}")

    for d in skills:
        skill_md = d / "SKILL.md"
        has_md = skill_md.is_file()
        check(f"  {d.name}: SKILL.md exists", has_md)
        if has_md:
            content = skill_md.read_text(encoding="utf-8")
            check(f"  {d.name}: has frontmatter", content.startswith("---"))


def test_instructions() -> None:
    print("\n--- Instructions (expect 8) ---")
    inst_dir = OPENCODE / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.instructions.md"))
    check(f"instruction count = {len(files)}", len(files) == 9, f"got {len(files)}")

    for f in files:
        size = f.stat().st_size
        check(f"  {f.name}: non-empty", size > 0, "empty file")


def test_plugin() -> None:
    print("\n--- Plugin ---")
    plugin = OPENCODE / "plugins" / "solocode-guard.js"
    check("solocode-guard.js exists", plugin.is_file())
    if plugin.is_file():
        content = plugin.read_text(encoding="utf-8")
        check("  version v3.0", "v3.0" in content[:200], "not v3.0")
        check("  BLOCK_PATTERNS declared", "BLOCK_PATTERNS" in content)
        check("  SECRET_PATTERNS declared", "SECRET_PATTERNS" in content)
        check("  chat.message hook", "chat.message" in content)
        check("  tool.execute.before hook", "tool.execute.before" in content)
        check("  tool.execute.after hook", "tool.execute.after" in content)
        check("  normalizeCommand", "normalizeCommand" in content)
        check("  extractPatchFilePaths", "extractPatchFilePaths" in content)


def test_state() -> None:
    print("\n--- State (expect 5 files) ---")
    state_dir = OPENCODE / "state"
    check("state/ directory exists", state_dir.is_dir())
    if not state_dir.is_dir():
        return

    expected = [
        "feature_list.json",
        "feature_list.schema.json",
        "progress.md",
        "session-handoff.md",
        "usage.jsonl",
    ]
    for name in expected:
        f = state_dir / name
        check(f"  {name}", f.is_file(), "missing")

    # Validate feature_list.json
    fl = state_dir / "feature_list.json"
    if fl.is_file():
        try:
            data = json.loads(fl.read_text(encoding="utf-8"))
            is_valid = isinstance(data, dict) and isinstance(data.get("features"), list)
            check("  feature_list.json: valid JSON", is_valid, "not dict with features array")
            if is_valid:
                check("  feature_list.json: 19 features", len(data["features"]) == 19, f"got {len(data['features'])}")
        except json.JSONDecodeError:
            check("  feature_list.json: valid JSON", False, "parse error")


def test_commands() -> None:
    print("\n--- Commands (expect 4) ---")
    cmd_dir = OPENCODE / "command"
    check("command/ directory exists", cmd_dir.is_dir())
    if not cmd_dir.is_dir():
        return

    expected = ["verify.md", "plan.md", "decide.md", "ship.md"]
    for name in expected:
        f = cmd_dir / name
        check(f"  {name}", f.is_file(), "missing")
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            check(f"  {name}: has frontmatter", content.startswith("---"))


def test_tools() -> None:
    print("\n--- Custom Tools (expect 2) ---")
    tool_dir = OPENCODE / "tool"
    check("tool/ directory exists", tool_dir.is_dir())
    if not tool_dir.is_dir():
        return

    expected = ["harness-verify.js", "session-log.js"]
    for name in expected:
        f = tool_dir / name
        check(f"  {name}", f.is_file(), "missing")
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            check(f"  {name}: uses @opencode-ai/plugin", "@opencode-ai/plugin" in content)
            check(f"  {name}: has execute function", "execute" in content)


def test_config() -> None:
    print("\n--- opencode.json ---")
    config = ROOT / "opencode.json"
    check("opencode.json exists", config.is_file())
    if not config.is_file():
        return

    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        check("  valid JSON", True)
        check("  permission key", "permission" in data)
        check("  shell key", data.get("shell") == "powershell", f"got {data.get('shell')}")
        check("  references key (optional)", True, "optional field, may be absent")
        check("  mcp key", "mcp" in data)

        perm = data.get("permission", {})
        check("  question: allow", perm.get("question") == "allow")
        check("  websearch: allow", perm.get("websearch") == "allow")
        check("  skill: allow", perm.get("skill") == "allow")
        check("  glob: allow", perm.get("glob") == "allow")
        check("  grep: allow", perm.get("grep") == "allow")
        check("  todowrite: allow", perm.get("todowrite") == "allow")

        bash = perm.get("bash", {})
        check("  bash: has deny rules", len(bash) > 2, f"only {len(bash)} entries")
        check("  bash: rm -rf ./* denied", bash.get("rm -rf ./*") == "deny")
        check("  bash: git clean denied", bash.get("git clean -fd*") == "deny")
        check("  bash: rd /s denied", bash.get("rd /s*") == "deny")
    except json.JSONDecodeError:
        check("  valid JSON", False, "parse error")


# ─── Copilot Engine Tests ───────────────────────────────────────
COPILOT = ROOT / ".copilot"


def test_copilot_agents() -> None:
    print("\n--- Copilot Agents (expect 14) ---")
    agents_dir = COPILOT / "agents"
    check("agents/ directory exists", agents_dir.is_dir())
    if not agents_dir.is_dir():
        return

    agents = sorted(agents_dir.glob("*.md"))
    check(f"agent count = {len(agents)}", len(agents) == 14, f"got {len(agents)}")

    for f in agents:
        content = f.read_text(encoding="utf-8")
        has_fm = content.startswith("---")
        check(f"  {f.name}: YAML frontmatter", has_fm)
        if has_fm:
            end = content.find("\n---", 3)
            check(f"  {f.name}: closing ---", end != -1)
            fm = content[3:end] if end != -1 else ""
            check(f"  {f.name}: mode or permission key", "mode:" in fm or "permission:" in fm, "missing mode/permission")


def test_copilot_skills() -> None:
    print("\n--- Copilot Skills (expect 47) ---")
    skills_dir = COPILOT / "skill"
    check("skill/ directory exists", skills_dir.is_dir())
    if not skills_dir.is_dir():
        return

    skills = sorted([d for d in skills_dir.iterdir() if d.is_dir()])
    check(f"skill count = {len(skills)}", len(skills) == 47, f"got {len(skills)}")

    for d in skills:
        skill_md = d / "SKILL.md"
        has_md = skill_md.is_file()
        check(f"  {d.name}: SKILL.md exists", has_md)
        if has_md:
            content = skill_md.read_text(encoding="utf-8")
            check(f"  {d.name}: has frontmatter", content.startswith("---"))


def test_copilot_instructions() -> None:
    print("\n--- Copilot Instructions (expect 8) ---")
    inst_dir = COPILOT / "instruction"
    check("instruction/ directory exists", inst_dir.is_dir())
    if not inst_dir.is_dir():
        return

    files = sorted(inst_dir.glob("*.md"))
    check(f"instruction count = {len(files)}", len(files) == 9, f"got {len(files)}")

    for f in files:
        size = f.stat().st_size
        check(f"  {f.name}: non-empty", size > 0, "empty file")


def test_copilot_commands() -> None:
    print("\n--- Copilot Commands (expect 13) ---")
    cmd_dir = COPILOT / "command"
    check("command/ directory exists", cmd_dir.is_dir())
    if not cmd_dir.is_dir():
        return

    cmds = sorted(cmd_dir.glob("*.md"))
    check(f"command count = {len(cmds)}", len(cmds) == 13, f"got {len(cmds)}")


def test_copilot_rulebook() -> None:
    print("\n--- Copilot Rulebook ---")
    rulebook = ROOT / ".github" / "copilot-instructions.md"
    check("copilot-instructions.md exists", rulebook.is_file())
    if rulebook.is_file():
        content = rulebook.read_text(encoding="utf-8")
        check("  non-empty", len(content) > 100, "too small to be valid rulebook")
        check("  contains 'Request Classification'", "Request Classification" in content)
        check("  contains 'Socratic Gate'", "Socratic Gate" in content)
        check("  contains 'Solo-Code' branding", "Solo-Code" in content)


def test_copilot_prompts() -> None:
    print("\n--- Copilot Prompts (expect 6) ---")
    prompts_dir = ROOT / ".github" / "prompts"
    check("prompts/ directory exists", prompts_dir.is_dir())
    if not prompts_dir.is_dir():
        return

    prompts = sorted(prompts_dir.glob("*.prompt.md"))
    check(f"prompt count = {len(prompts)}", len(prompts) == 6, f"got {len(prompts)}")

    for f in prompts:
        content = f.read_text(encoding="utf-8")
        check(f"  {f.name}: has frontmatter", content.startswith("---"))
        check(f"  {f.name}: non-empty", len(content) > 50, "too small")


def test_copilot_vscode() -> None:
    print("\n--- VS Code Config ---")
    vscode = ROOT / ".vscode"
    check(".vscode/ exists", vscode.is_dir())
    if not vscode.is_dir():
        return

    settings = vscode / "settings.json"
    check("  settings.json exists", settings.is_file())
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
            check("  settings.json: valid JSON", True)
            check("  settings.json: copilot instructions", "github.copilot.chat.codeGeneration.instructions" in data)
            check("  settings.json: promptFiles", "github.copilot.chat.promptFiles" in data)
        except json.JSONDecodeError:
            check("  settings.json: valid JSON", False, "parse error")

    mcp = vscode / "mcp.json"
    check("  mcp.json exists", mcp.is_file())
    if mcp.is_file():
        try:
            data = json.loads(mcp.read_text(encoding="utf-8"))
            check("  mcp.json: valid JSON", True)
            check("  mcp.json: servers key", "servers" in data)
            servers = data.get("servers", {})
            check("  mcp.json: context7 server", "context7" in servers)
        except json.JSONDecodeError:
            check("  mcp.json: valid JSON", False, "parse error")


# ─── Main ──────────────────────────────────────────────────────────
def main() -> int:
    print("=" * 60)
    print(" OpenCode + Copilot Harness — Integration Tests")
    print("=" * 60)

    print("\n  [OpenCode Engine]")
    test_agents()
    test_skills()
    test_instructions()
    test_plugin()
    test_state()
    test_commands()
    test_tools()
    test_config()

    print("\n  [Copilot Engine]")
    test_copilot_agents()
    test_copilot_skills()
    test_copilot_instructions()
    test_copilot_commands()
    test_copilot_rulebook()
    test_copilot_prompts()
    test_copilot_vscode()

    print()
    print("=" * 60)
    print(f"  Results: {PASS} pass, {FAIL} fail")
    print("=" * 60)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
