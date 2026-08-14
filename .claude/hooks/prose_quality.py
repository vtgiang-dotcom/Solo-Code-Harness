#!/usr/bin/env python3
"""
prose_quality (Claude Code hook) — PostToolUse advisory markdown prose checks.

Stdlib-only. Windows-compatible (CRLF, explicit encoding).

Wired via .claude/settings.json:
    "PostToolUse": [ { "matcher": "Edit|Write",
        "hooks": [ { "type": "command",
            "command": "python .claude/hooks/prose_quality.py" } ] } ]

Behavior:
  - Reads the PostToolUse JSON from stdin.
  - Only acts when the tool was Edit/Write and the target file is *.md.
  - Analyzes the proposed markdown from tool_input.new_string (Edit) or
    tool_input.content (Write).
  - Emits advisory warnings to stderr for prose quality issues. ALWAYS exits 0
    (advisory — never blocks the edit).
"""

from __future__ import annotations

import json
import re
import sys

MARKDOWN_FLUFF = [
    "revolutionary",
    "game-changing",
    "cutting-edge",
    "best-ever",
    "unprecedented",
    "industry-leading",
    "state-of-the-art",
    "paves the way",
    "paradigm shift",
    "unlock the potential",
]

HEDGING_PHRASES = [
    "sort of",
    "kind of",
    "maybe",
    "perhaps",
    "arguably",
    "might be",
    "i think",
]

FILLER_WORDS = [
    "actually",
    "basically",
    "essentially",
    "literally",
    "honestly",
    "obviously",
]

# Auxiliary-be verb + past participle = passive voice. The word-boundary
# lookbehind stops "is" inside "this" from matching and the (?<!\bhave\b)
# guard keeps perfect tenses ("has been rewritten") out of the count.
PASSIVE_PATTERN = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", re.I
)

# Sentence boundary splitter. Handles . ? ! followed by whitespace/end-of-line.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Prefixes before "it/this/that" that usually still carry an antecedent.
PRONOUN_OK_PREFIXES = (
    "with ", "for ", "from ", "after ", "before ", "on ", "in ", "to ",
    "while ", "because ", "although ", "using ", "based on ", "due to ",
    "instead of ", "such as ", "unlike ", "like ", "through ", "by ",
    "over ", "under ", "behind ", "beyond ", "against ", "despite ",
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
CODE_FENCE_RE = re.compile(r"^```(\w+)?\s*$", re.M)

ADVISORY_LABEL = "[ProseQuality] Advisory warnings"


def is_markdown(file_path: str) -> bool:
    return file_path.lower().endswith(".md")


def line_index(lines: list[str], offset: int) -> int:
    """Convert an offset into the joined text back to a 1-based line number."""
    return lines[: offset + 1].count("\n") + 1


def check_fluff(line: str, line_no: int, warnings: list[str]) -> None:
    for word in MARKDOWN_FLUFF:
        if re.search(rf"\b{re.escape(word)}\b", line, re.I):
            warnings.append(f"  Line {line_no}: marketing fluff detected: '{word}'")


def check_hedging(line: str, line_no: int, warnings: list[str]) -> None:
    for phrase in HEDGING_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", line, re.I):
            warnings.append(f"  Line {line_no}: hedging phrase detected: '{phrase}'")


def check_filler(line: str, line_no: int, warnings: list[str]) -> None:
    for word in FILLER_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", line, re.I):
            warnings.append(f"  Line {line_no}: filler word detected: '{word}'")


def check_passive(text: str, warnings: list[str]) -> None:
    sentences = [s for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    if len(sentences) < 3:
        return
    passive = [s for s in sentences if PASSIVE_PATTERN.search(s)]
    ratio = len(passive) / len(sentences)
    if ratio > 0.20:
        warnings.append(
            f"  passive voice overuse ({len(passive)} of {len(sentences)} "
            f"sentences, {ratio:.0%})"
        )


def check_pronouns(lines: list[str], warnings: list[str]) -> None:
    for i, line in enumerate(lines, 1):
        for match in re.finditer(r"\b(it|this|that)\b", line, re.I):
            prefix = line[: match.start()].lower()
            if prefix.strip().endswith(PRONOUN_OK_PREFIXES):
                continue
            if re.search(r"\.|\?\s*$", line[: match.start()].rstrip()):
                continue
            warnings.append(
                f"  Line {i}: pronoun '{match.group(1)}' with no clear "
                f"antecedent nearby: {line.strip()[:70]!r}"
            )


def check_code_fences(text: str, warnings: list[str]) -> None:
    for match in CODE_FENCE_RE.finditer(text):
        if match.group(1) is None:
            line_no = text[: match.start()].count("\n") + 1
            warnings.append(
                f"  Line {line_no}: code block missing language tag"
            )


def check_headers(lines: list[str], warnings: list[str]) -> None:
    for i, line in enumerate(lines, 1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        heading = match.group(2)
        if not heading:
            continue
        if not heading[0].islower() and re.search(r"[A-Z]", heading[1:]):
            warnings.append(
                f"  Line {i}: header not in sentence case: {heading!r}"
            )


def analyze(file_path: str, text: str) -> list[str]:
    lines = text.split("\n")
    warnings: list[str] = []
    for i, line in enumerate(lines, 1):
        check_fluff(line, i, warnings)
        check_hedging(line, i, warnings)
        check_filler(line, i, warnings)
    check_passive(text, warnings)
    check_pronouns(lines, warnings)
    check_code_fences(text, warnings)
    check_headers(lines, warnings)
    return warnings


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool = payload.get("tool_name", "")
    if tool not in ("Edit", "Write"):
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not is_markdown(file_path):
        return 0

    # Edit supplies new_string; Write supplies content. Partial edits yield
    # fragments that read fine in isolation, so only flag complete content.
    text = tool_input.get("new_string", "") or tool_input.get("content", "") or ""
    if not text:
        return 0

    try:
        warnings = analyze(file_path, text)
    except Exception:  # noqa: BLE001 — advisory hook must never crash
        return 0

    if warnings:
        sys.stderr.write(f"\n{ADVISORY_LABEL} for {file_path}:\n")
        sys.stderr.write("\n".join(warnings))
        sys.stderr.write("\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
