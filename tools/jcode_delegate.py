#!/usr/bin/env python3
"""
jcode_delegate.py — Token-optimized, single-model delegation wrapper for
the jcode (DeepSeek) worker engine.

ORCHESTRATION MODEL (important): Claude Code / Kilo Code is ALWAYS the
orchestrator. This script never runs on its own initiative — it is invoked
by the planner engine for exactly one well-specified subtask at a time and
returns a draft the orchestrator must still read and verify. jcode has no
memory of this conversation between calls; it is a stateless worker, not a
delegate that can be "trusted and forgotten".

ONE MODEL: deepseek/deepseek-v4-pro, always with the strict guardrail
preamble (GUARDRAIL) prepended. An earlier version of this wrapper routed
"mechanical" subtasks to the cheaper deepseek-v4-flash tier; in real use
that tier proved unreliable (2026-07-25) — the token saved was repeatedly
lost to re-prompting and orchestrator rework, so the cheap tier was
removed rather than left as a footgun. Cost optimization here now comes
entirely from the flag discipline below (--tool-profile none --no-selfdev,
~65% fewer input tokens), not from model downgrading.

Usage:
    python tools/jcode_delegate.py "<self-contained prompt>"
    python tools/jcode_delegate.py "<prompt>" --with-tools   # let jcode use its own tools

Every call is logged (model, prompt size, token usage, latency) to
.solocode/jcode-usage.jsonl so the cost/latency payoff is auditable rather
than assumed.
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

MODEL = "deepseek/deepseek-v4-pro"


# Injected verbatim before every task. deepseek-v4-pro is the only model
# this wrapper uses, but it has a measured tendency to go out of scope
# (touch unrelated files, add dependencies, "helpfully" refactor nearby
# code, invent requirements) unless constraints are stated explicitly and
# right next to the task -- this is the mitigation, not optional
# boilerplate. Never call the model without it.
GUARDRAIL = """\
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


def build_command(prompt: str, *, with_tools: bool, json_out: bool) -> list[str]:
    cmd = [
        "jcode", "run", GUARDRAIL + prompt,
        "--provider-profile", "commandcode",
        "--model", MODEL,
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
    model: str, prompt_len: int, result: dict | None, elapsed: float
) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
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
        "--tier", choices=["simple", "code", "auto"], default=None,
        help="DEPRECATED and ignored. The flash/simple tier was removed "
             "(unreliable in practice); every call now uses "
             f"{MODEL} with the guardrail preamble.",
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

    if args.tier is not None:
        print(
            f"[jcode_delegate] --tier is deprecated and ignored; using {MODEL}.",
            file=sys.stderr,
        )

    if shutil.which("jcode") is None:
        print("jcode binary not found on PATH -- cannot delegate.", file=sys.stderr)
        return 1

    cmd = build_command(
        args.prompt, with_tools=args.with_tools, json_out=not args.no_json
    )

    print(f"[jcode_delegate] model={MODEL}", file=sys.stderr)

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

    _log_usage(MODEL, len(args.prompt), result, elapsed)

    if proc.returncode != 0:
        print(proc.stderr or "jcode exited non-zero with no stderr", file=sys.stderr)
        return proc.returncode

    print(proc.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
