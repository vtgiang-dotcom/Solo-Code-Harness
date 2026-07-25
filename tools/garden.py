#!/usr/bin/env python3
"""
Garden — Drift Detection
=========================
Checks for stale artifacts, missing generated files, and dead links
between .kilo/ (source of truth) ↔ .claude/ (generated) and
.kilo/ ↔ .copilot/ (manually-maintained parity) directories.

.opencode/ was deprecated in v3.7.0 and physically removed in v4.0.0 —
see .harness.lock and .kilo/memory/MEMORY.md "Decisions" section.

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


def check_instruction_content(src: Path, dst: Path, dst_label: str) -> list[str]:
    """Check src/instruction/*.md content matches dst/instruction/*.md exactly.

    Instructions have no per-engine frontmatter transform (unlike skills, whose
    SKILL.md frontmatter legitimately differs per engine schema), so a byte-
    for-byte diff is the correct check here -- any mismatch is real drift.
    """
    issues: list[str] = []
    src_dir = src / "instruction"
    dst_dir = dst / "instruction"
    if not src_dir.is_dir() or not dst_dir.is_dir():
        return issues
    src_names = {f.name for f in src_dir.iterdir() if f.is_file()}
    dst_names = {f.name for f in dst_dir.iterdir() if f.is_file()}
    for name in sorted(src_names & dst_names):
        if (src_dir / name).read_text(encoding="utf-8") != (dst_dir / name).read_text(encoding="utf-8"):
            issues.append(
                f"Content drift: {dst_label}/instruction/{name} differs from "
                f".kilo/instruction/{name} (out of sync — resync from source of truth)"
            )
    return issues


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter incl. delimiters, body). Returns
    ("", text) if there's no `---`-delimited frontmatter block."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text


def check_skill_content(src: Path, dst_skill_dir: Path, dst_label: str) -> list[str]:
    """Check SKILL.md *body* content matches between .kilo/skill/ and a
    manually-mirrored engine (dst_skill_dir), ignoring frontmatter.

    Frontmatter legitimately differs per engine (e.g. Copilot requires quoted
    `description` strings + a `license` field, Kilo doesn't) -- diffing it
    would be a constant false positive. The body (actual skill instructions)
    should be byte-identical though; any difference there is real content
    drift/loss, not an intentional platform adaptation.
    """
    issues: list[str] = []
    src_dir = src / "skill"
    if not src_dir.is_dir() or not dst_skill_dir.is_dir():
        return issues
    for skill_dir in sorted(p for p in src_dir.iterdir() if p.is_dir()):
        dst_skill_md = dst_skill_dir / skill_dir.name / "SKILL.md"
        src_skill_md = skill_dir / "SKILL.md"
        if not (src_skill_md.is_file() and dst_skill_md.is_file()):
            continue
        _, src_body = _split_frontmatter(src_skill_md.read_text(encoding="utf-8"))
        _, dst_body = _split_frontmatter(dst_skill_md.read_text(encoding="utf-8"))
        if src_body != dst_body:
            issues.append(
                f"Content drift: {dst_label}/skill/{skill_dir.name}/SKILL.md body "
                f"differs from .kilo/skill/{skill_dir.name}/SKILL.md "
                "(out of sync — resync body from source of truth, keep dst frontmatter)"
            )
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
    """Check that all src/memory/ files have a dst/ copy AND identical content.

    .kilo/memory/ is the source of truth for the project's own accumulated
    memory (MEMORY.md, project-conventions.md, harness-design-intent.md);
    .claude/memory/ and .copilot/memory/ are manually-kept mirrors (no
    auto-generator regenerates them). File-existence parity alone previously
    let content silently drift out of sync (one engine's writer updates its
    own copy but forgets the others) without garden.py ever catching it.
    """
    issues = _check_parity_dir(src, dst, dst_label, "memory")
    src_dir = src / "memory"
    dst_dir = dst / "memory"
    if not src_dir.is_dir() or not dst_dir.is_dir():
        return issues
    src_files = {f.name for f in src_dir.iterdir() if f.is_file() and f.suffix == ".md"}
    dst_files = {f.name for f in dst_dir.iterdir() if f.is_file()}
    for name in sorted(src_files & dst_files):
        src_text = (src_dir / name).read_text(encoding="utf-8")
        dst_text = (dst_dir / name).read_text(encoding="utf-8")
        if src_text != dst_text:
            issues.append(
                f"Content drift: {dst_label}/memory/{name} differs from "
                f".kilo/memory/{name} (out of sync — resync from source of truth)"
            )
    return issues


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


def check_claude(src: Path, dst: Path, *, skip_set: set[str] | None = None) -> list[str]:
    """Parity checks for the Claude engine (.claude/).

    Claude uses different directory names than the other engines:
      .kilo/agents      -> .claude/agents
      .kilo/skill       -> .claude/skills   (plural)
      .kilo/command     -> .claude/commands (plural)
      .kilo/instruction -> .claude/instruction
    Plus static infra: CLAUDE.md, settings.json, hooks/guard.py.
    """
    issues: list[str] = []
    skip_set = skip_set or set()

    # Agents (same subdir name)
    issues.extend(_check_parity_dir(src, dst, ".claude", "agents"))

    # Skills: .kilo/skill/* dirs must exist in .claude/skills/*
    src_skills = src / "skill"
    dst_skills = dst / "skills"
    if src_skills.is_dir():
        src_names = {p.name for p in src_skills.iterdir() if p.is_dir()} - skip_set
        dst_names = {p.name for p in dst_skills.iterdir() if p.is_dir()} if dst_skills.is_dir() else set()
        for name in sorted(src_names - dst_names):
            issues.append(f"Missing skill: .claude/skills/{name}/")
        for name in sorted(dst_names - src_names):
            issues.append(f"Stale skill (no source): .claude/skills/{name}/")
        # SKILL.md health
        if dst_skills.is_dir():
            for entry in sorted(dst_skills.iterdir()):
                if entry.is_dir() and not (entry / "SKILL.md").exists():
                    issues.append(f"Skill missing SKILL.md: .claude/skills/{entry.name}")

    # Commands: .kilo/command/*.md must exist in .claude/commands/*.md
    src_cmd = src / "command"
    dst_cmd = dst / "commands"
    if src_cmd.is_dir():
        src_names = {f.name for f in src_cmd.iterdir() if f.suffix == ".md"}
        dst_names = {f.name for f in dst_cmd.iterdir()} if dst_cmd.is_dir() else set()
        for name in sorted(src_names - dst_names):
            issues.append(f"Missing command: .claude/commands/{name}")
        for name in sorted(dst_names - src_names):
            issues.append(f"Stale command (no source): .claude/commands/{name}")

    # Instructions (direct copy, same filename)
    issues.extend(check_instructions(src, dst, ".claude"))

    # Memory (direct copy, same filename) — feat-008 parity
    issues.extend(check_memory(src, dst, ".claude"))

    # Static harness infra required for the Claude engine
    for rel, desc in (
        ("hooks/guard.py", "guard hook (PreToolUse)"),
        ("hooks/quality_gate.py", "quality-gate hook (PostToolUse)"),
        ("hooks/security_post.py", "security-post hook (PostToolUse)"),
        ("hooks/pre_compact.py", "pre-compact hook (PreCompact)"),
        ("hooks/session_start.py", "session-start hook (SessionStart)"),
        ("hooks/session_end.py", "session-end hook (SessionEnd)"),
        ("hooks/memory_gate.py", "memory-gate hook (PostToolUse size cap)"),
        ("settings.json", "settings (hook registration)"),
    ):
        if not (dst / rel).exists():
            issues.append(f"Missing {desc}: .claude/{rel}")
    if not (ROOT / "CLAUDE.md").exists():
        issues.append("Missing rulebook: CLAUDE.md (run 'python tools/generate_harness.py --harness claude')")
    else:
        issues.extend(check_claude_md_regenerable())

    return issues


def check_claude_md_regenerable() -> list[str]:
    """Check the committed CLAUDE.md matches what its generator produces.

    CLAUDE.md is generated from `claude_engine.py`'s template, but nothing
    used to verify that. The two silently diverged: the live file was
    hand-edited and the template was left behind, so regenerating would
    have SILENTLY DELETED real content -- the exact failure mode the
    "GENERATED ... do not edit by hand" banner is supposed to prevent.
    Comparing here makes that divergence a loud drift error instead.

    Compared on normalized line endings: the point is content parity, and
    git checks out CRLF on Windows for a LF-committed file, which would
    otherwise make this fail for everyone on Windows.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "claude_engine", ROOT / "tools" / "claude_engine.py"
    )
    claude_engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(claude_engine)

    live = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    expected = claude_engine._CLAUDE_MD_TEMPLATE.format(
        **claude_engine._claude_md_counts(ROOT)
    )
    if live.replace("\r\n", "\n") != expected.replace("\r\n", "\n"):
        return [
            "Content drift: CLAUDE.md differs from claude_engine.py's template "
            "(regenerating would overwrite hand edits -- port them into the "
            "template, then run 'python tools/generate_harness.py --harness claude')"
        ]
    return []


def check_shared_state() -> list[str]:
    """Check .solocode/shared-state.db integrity — IF it exists.

    The DB is local-only by design: gitignored + deploy-excluded, created on
    first engine run. A fresh checkout (CI, clone, deploy) legitimately has no
    DB, so its absence is NOT drift — treating it as such breaks every clean
    environment. We only validate integrity/staleness when the DB is present.
    """
    issues: list[str] = []
    db_path = ROOT / ".solocode" / "shared-state.db"

    if not db_path.exists():
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


def check_gemini(src: Path, dst: Path, *, skip_set: set[str] | None = None) -> list[str]:
    """Parity checks for the Gemini/Antigravity engine (.gemini/antigravity/).

    Gemini uses different directory names/paths than the other engines:
      .kilo/agents      -> .gemini/antigravity/agents
      .kilo/skill       -> .gemini/antigravity/skills   (plural, nested under antigravity/)
      .kilo/instruction -> .gemini/antigravity/instruction
    No memory/ parity check: Gemini stores project knowledge under
    knowledge/ (artifacts + metadata.json), not a MEMORY.md/project-
    conventions.md mirror like the other engines -- not a comparable shape.
    """
    issues: list[str] = []
    skip_set = skip_set or set()

    # Agents (same subdir name)
    issues.extend(_check_parity_dir(src, dst, ".gemini/antigravity", "agents"))

    # Skills: .kilo/skill/* dirs must exist in .gemini/antigravity/skills/*
    src_skills = src / "skill"
    dst_skills = dst / "skills"
    if src_skills.is_dir():
        src_names = {p.name for p in src_skills.iterdir() if p.is_dir()} - skip_set
        dst_names = {p.name for p in dst_skills.iterdir() if p.is_dir()} if dst_skills.is_dir() else set()
        for name in sorted(src_names - dst_names):
            issues.append(f"Missing skill: .gemini/antigravity/skills/{name}/")
        for name in sorted(dst_names - src_names):
            issues.append(f"Stale skill (no source): .gemini/antigravity/skills/{name}/")
        if dst_skills.is_dir():
            for entry in sorted(dst_skills.iterdir()):
                if entry.is_dir() and not (entry / "SKILL.md").exists():
                    issues.append(f"Skill missing SKILL.md: .gemini/antigravity/skills/{entry.name}")

    # Instructions (direct copy, same filename + identical content)
    issues.extend(check_instructions(src, dst, ".gemini/antigravity"))
    issues.extend(check_instruction_content(src, dst, ".gemini/antigravity"))

    # Skill body content (frontmatter-agnostic — see check_skill_content docstring)
    issues.extend(check_skill_content(src, dst_skills, ".gemini/antigravity"))

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
        (
            f"Instruction content drift ({dst_label})",
            lambda: [] if instruction_suffix else check_instruction_content(src, dst, dst_label),
        ),
        (f"Memory drift ({dst_label})", lambda: check_memory(src, dst, dst_label)),
        (
            f"Skill parity ({dst_label})",
            lambda: check_skill_parity(src, dst, dst_label, skip_set=skip_set),
        ),
        (
            f"Skill content drift ({dst_label})",
            lambda: check_skill_content(src, dst / "skill", dst_label),
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


def _parse_agent_yaml_list(text: str, key: str) -> list[str]:
    """Extract a top-level YAML list (e.g. `skills:` / `agents:`) without PyYAML.

    Only handles the simple `key:` followed by `  - item` block style used in
    agent.yaml. Stops at the next top-level key (a line starting in column 0
    that is not a list item). Stdlib-only to keep the harness zero-dependency.
    """
    items: list[str] = []
    in_block = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not in_block:
            # Enter the block only on the bare `key:` header (no inline value).
            if stripped == f"{key}:":
                in_block = True
            continue
        # Inside the block.
        if raw.startswith(("  - ", "- ")) or stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif stripped == "":
            continue
        elif not raw.startswith(" "):
            # New top-level key — block ended.
            break
    return items


def check_manifest(root: Path) -> list[str]:
    """feat-010: validate agent.yaml skills/agents match real .kilo/ file counts.

    Prevents drift between the published manifest (agent.yaml) and reality:
      - skills listed must match .kilo/skill/*/ directory names exactly
      - agents listed must match .kilo/agents/*.md file stems exactly
      - version must match the harness version in .harness.lock
    """
    issues: list[str] = []
    manifest = root / "agent.yaml"
    if not manifest.is_file():
        return issues
    text = manifest.read_text(encoding="utf-8")

    # Skills parity
    skill_dir = root / ".kilo" / "skill"
    if skill_dir.is_dir():
        actual = {p.name for p in skill_dir.iterdir() if p.is_dir()}
        listed = set(_parse_agent_yaml_list(text, "skills"))
        for name in sorted(actual - listed):
            issues.append(f"agent.yaml missing skill: {name} (exists in .kilo/skill/)")
        for name in sorted(listed - actual):
            issues.append(f"agent.yaml stale skill: {name} (no .kilo/skill/{name}/)")

    # Agents parity
    agent_dir = root / ".kilo" / "agents"
    if agent_dir.is_dir():
        actual_a = {f.stem for f in agent_dir.glob("*.md")}
        listed_a = set(_parse_agent_yaml_list(text, "agents"))
        for name in sorted(actual_a - listed_a):
            issues.append(f"agent.yaml missing agent: {name} (exists in .kilo/agents/)")
        for name in sorted(listed_a - actual_a):
            issues.append(f"agent.yaml stale agent: {name} (no .kilo/agents/{name}.md)")

    # Version parity with .harness.lock
    lock = root / ".harness.lock"
    if lock.is_file():
        lock_version = ""
        for line in lock.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("version"):
                lock_version = s.split("=", 1)[1].strip().strip('"') if "=" in s else ""
                break
        manifest_version = ""
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("version:"):
                manifest_version = s.split(":", 1)[1].strip().strip('"')
                break
        if lock_version and manifest_version and lock_version != manifest_version:
            issues.append(
                f"agent.yaml version {manifest_version} != .harness.lock version {lock_version}"
            )

    return issues


def main() -> int:
    kilo = ROOT / ".kilo"

    all_issues: list[str] = []
    skip_skills = _load_skip_skills()

    # .copilot/ engine — direct copy, no suffix
    print("--- .copilot/ ---")
    all_issues.extend(
        run_engine_checks(kilo, ROOT / ".copilot", ".copilot", instruction_suffix=False)
    )

    # .claude/ engine — different subdir names (skills/commands plural) + static infra
    print("\n--- .claude/ ---")
    claude_issues = check_claude(kilo, ROOT / ".claude", skip_set=skip_skills)
    if claude_issues:
        print("[DRIFT] Claude engine (.claude):")
        for i in claude_issues:
            print(f"  {i}")
        all_issues.extend(claude_issues)
    else:
        print("[OK] Claude engine (.claude)")

    # .gemini/antigravity/ engine — nested path + skills/ plural, no memory check
    print("\n--- .gemini/ ---")
    gemini_issues = check_gemini(kilo, ROOT / ".gemini" / "antigravity", skip_set=skip_skills)
    if gemini_issues:
        print("[DRIFT] Gemini engine (.gemini):")
        for i in gemini_issues:
            print(f"  {i}")
        all_issues.extend(gemini_issues)
    else:
        print("[OK] Gemini engine (.gemini)")

    # Shared state health (không thuộc riêng engine nào)
    print("\n--- Shared State ---")
    shared_issues = check_shared_state()
    if shared_issues:
        print("[DRIFT] Shared state:")
        for i in shared_issues:
            print(f"  {i}")
        all_issues.extend(shared_issues)
    else:
        print("[OK] Shared state (local DB present or absent — both valid)")

    # Manifest sync (agent.yaml vs reality) — feat-010
    print("\n--- Manifest (agent.yaml) ---")
    manifest_issues = check_manifest(ROOT)
    if manifest_issues:
        print("[DRIFT] Manifest sync:")
        for i in manifest_issues:
            print(f"  {i}")
        all_issues.extend(manifest_issues)
    else:
        print("[OK] Manifest sync (agent.yaml)")

    print(f"\nTotal drift issues: {len(all_issues)}")
    if all_issues:
        print("Run 'python tools/generate_harness.py --harness all' to fix.")
        return 1
    print("Garden is clean — no drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
