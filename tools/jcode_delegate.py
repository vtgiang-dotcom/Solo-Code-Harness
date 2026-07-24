#!/usr/bin/env python3
"""
jcode_delegate.py — Token-optimized, two-tier delegation wrapper for the
jcode (DeepSeek) worker engine.

ORCHESTRATION MODEL (important): Claude Code / Kilo Code is ALWAYS the
orchestrator. This script never runs on its own initiative — it is invoked
by the planner engine for exactly one well-specified subtask at a time,
picks the cheapest model tier that can plausibly do that subtask, and
returns a draft the orchestrator must still read and verify. jcode has no
memory of this conversation between calls; it is a stateless worker, not a
delegate that can be "trusted and forgotten".

Two tiers (see AGENTS.md "Delegating a task to jcode" for the full guide):
    simple -> deepseek/deepseek-v4-flash  cheap/fast; mechanical, bounded,
              low-risk-of-drift tasks (formatting, boilerplate, a single
              well-defined test, summarizing/extracting from provided text).
    code   -> deepseek/deepseek-v4-pro    materially stronger at code
              reasoning/refactors, but measured to ignore scope/style
              constraints unless told explicitly and immediately before the
              task — this script always prepends a strict guardrail
              preamble (CODE_TIER_GUARDRAIL) for this tier. Never call the
              pro model without it.

Usage:
    python tools/jcode_delegate.py "<self-contained prompt>"              # auto-tier
    python tools/jcode_delegate.py "<prompt>" --tier simple
    python tools/jcode_delegate.py "<prompt>" --tier code
    python tools/jcode_delegate.py "<prompt>" --with-tools   # let jcode use its own tools

Every call is logged (tier, model, prompt size, token usage, latency) to
.solocode/jcode-usage.jsonl so the cost/latency payoff of this routing is
auditable rather than assumed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_LOG = ROOT / ".solocode" / "jcode-usage.jsonl"

MODELS = {
    "simple": "deepseek/deepseek-v4-flash",
    "code": "deepseek/deepseek-v4-pro",
}

# Keyword heuristics for --tier auto. Deliberately biased toward "simple"
# (the cheaper tier) — only escalate to "code" when the prompt clearly
# signals real code-reasoning work. This is a convenience default; the
# orchestrator (Claude Code) can always override with an explicit --tier.
_CODE_TIER_HINTS = (
    "refactor", "implement", "algorithm", "bug", "fix", "architecture",
    "design pattern", "concurren", "race condition", "performance",
    "optimi", "recursive", "state machine", "edge case", "logic",
)


def classify_tier(prompt: str) -> str:
    """Best-effort auto-classification of which model tier a prompt needs.
    Biased toward the cheap tier -- false negatives (sending a code-shaped
    task to flash) are cheap to notice and re-run with --tier code; false
    positives (sending trivial tasks to the pricier pro model) quietly
    erase the whole point of tiering, so the bar to escalate is kept high.
    """
    lowered = prompt.lower()
    if any(hint in lowered for hint in _CODE_TIER_HINTS):
        return "code"
    return "simple"


# Injected verbatim before the task when tier == "code". deepseek-v4-pro is
# stronger at code-reasoning than the flash tier but has a measured
# tendency to go out of scope (touch unrelated files, add dependencies,
# "helpfully" refactor nearby code, invent requirements) unless constraints
# are stated explicitly and right next to the task -- this is the
# mitigation, not optional boilerplate. Never call the pro model without it.
CODE_TIER_GUARDRAIL = """\
STRICT OPERATING CONSTRAINTS (must follow, no exceptions):
1. Modify ONLY the files explicitly named in the task below. Do not touch
   any other file, and do not "helpfully" refactor nearby code.
2. Do NOT add new dependencies, new files, or new abstractions unless the
   task explicitly asks for them.
3. Match the existing code style/conventions of the surrounding file
   exactly (naming, formatting, error handling patterns).
4. If the task is ambiguous or underspecified, STOP and report back what
   is missing instead of guessing or inventing scope.
5. Never run destructive commands (git push, --force, rm -rf, DB
   migrations) under any circumstance.
6. End your response with a one-line self-check: "Scope check: touched
   only <file list>; no dependencies added" (or state exactly what
   deviated and why).

TASK:
"""


def build_command(
    prompt: str, tier: str, *, with_tools: bool, json_out: bool
) -> list[str]:
    model = MODELS[tier]
    full_prompt = CODE_TIER_GUARDRAIL + prompt if tier == "code" else prompt
    cmd = [
        "jcode", "run", full_prompt,
        "--provider-profile", "commandcode",
        "--model", model,
        "--quiet",
    ]
    if not with_tools:
        # Cuts measured input tokens by ~65% for tasks that don't need
        # jcode's own bash/read/write tools or repo self-dev detection.
        cmd += ["--tool-profile", "none", "--no-selfdev"]
    if json_out:
        cmd.append("--json")
    return cmd


def _log_usage(
    tier: str, model: str, prompt_len: int, result: dict | None, elapsed: float
) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "model": model,
        "prompt_chars": prompt_len,
        "elapsed_s": round(elapsed, 2),
        "usage": (result or {}).get("usage") if isinstance(result, dict) else None,
    }
    with USAGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt", help="Self-contained task prompt (inline all needed context)"
    )
    parser.add_argument(
        "--tier", choices=["simple", "code", "auto"], default="auto",
        help="Model tier. 'auto' classifies from the prompt (biased cheap).",
    )
    parser.add_argument(
        "--with-tools", action="store_true",
        help="Allow jcode's own bash/read/write tools (costs more tokens; "
             "only needed if the subtask genuinely requires them)",
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Stream text instead of --json"
    )
    args = parser.parse_args(argv)

    if shutil.which("jcode") is None:
        print("jcode binary not found on PATH -- cannot delegate.", file=sys.stderr)
        return 1

    tier = classify_tier(args.prompt) if args.tier == "auto" else args.tier
    model = MODELS[tier]
    cmd = build_command(
        args.prompt, tier, with_tools=args.with_tools, json_out=not args.no_json
    )

    print(f"[jcode_delegate] tier={tier} model={model}", file=sys.stderr)

    start = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - start

    result: dict | None = None
    if not args.no_json and proc.stdout:
        try:
            parsed = json.loads(proc.stdout)
            result = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            result = None

    _log_usage(tier, model, len(args.prompt), result, elapsed)

    if proc.returncode != 0:
        print(proc.stderr or "jcode exited non-zero with no stderr", file=sys.stderr)
        return proc.returncode

    print(proc.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
