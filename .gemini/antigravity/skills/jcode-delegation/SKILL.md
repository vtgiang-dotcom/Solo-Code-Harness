---
name: jcode-delegation
description: "Routes small well-specified subtasks to the jcode (DeepSeek) worker using a cost-optimized two-tier model split (deepseek-v4-flash for mechanical work, deepseek-v4-pro with a strict guardrail preamble for code-reasoning work). Use when considering delegating a task to jcode, when jcode is available, or when optimizing token/cost for a subtask."
license: MIT
---

# jcode Worker Delegation - Two-Tier Model Routing

## Overview

Claude Code (or Kilo Code) is always the orchestrator. jcode is a
stateless, one-shot DeepSeek worker with no memory of this conversation --
it never runs on its own initiative, never plans, never decides what to do
next. Every call is: orchestrator picks one well-specified subtask, routes
it to the cheapest model tier that can plausibly do it, reads the draft
back, then verifies it with the project's own gates. This skill exists
purely to cut token/cost/latency on subtasks the orchestrator has already
decided are safe to hand off -- it is never a substitute for the
orchestrator's own judgment, and it must never lower output quality.

Goal, stated plainly: maximize use of the cheap model for the volume of
small mechanical work, reserve the strong model for real code-reasoning
work (with guardrails, since it drifts out of scope more easily), and keep
Claude Code as the single point of verification for everything that comes
back. Cost optimization is the point; correctness is the non-negotiable
constraint on top of it.

## When to Consider Delegating At All

Small, well-specified, self-contained subtasks with a clear acceptance
criterion. NOT suited for anything needing this session's ongoing
conversational context (architecture judgment, root-cause analysis,
multi-step back-and-forth) -- jcode has no access to this conversation's
history.

If a task is trivial enough to just do directly in 1-2 tool calls, do that
instead -- delegation has fixed overhead (subprocess spin-up, prompt
inlining) that isn't worth it for genuinely tiny edits.

## Two-Tier Routing

| Tier | Model | Use for | Risk |
|------|-------|---------|------|
| simple | deepseek/deepseek-v4-flash | Formatting, boilerplate, mechanical refactors, generating a single well-defined test, summarizing/extracting from text already inlined in the prompt, doc/README generation from a spec | Low cost, low capability -- fine for bounded, unambiguous work |
| code | deepseek/deepseek-v4-pro | Real code-reasoning: non-trivial logic, bug fixes needing root-cause understanding within a bounded scope, algorithm implementation, structured refactors | Stronger, but measured to ignore scope/style constraints unless told explicitly right before the task |

Default to simple unless the task clearly needs code-tier reasoning --
escalating unnecessarily quietly erases the entire point of tiering.

## Invocation

Use the wrapper script instead of shelling out to jcode directly -- it
standardizes the token-optimized flags and, critically, auto-prepends the
strict guardrail preamble for the code tier:

```bash
python tools/jcode_delegate.py "<self-contained prompt, full context inlined>" --tier simple
python tools/jcode_delegate.py "<self-contained prompt, full context inlined>" --tier code
python tools/jcode_delegate.py "<prompt>"   # --tier auto: classifies from prompt, biased cheap
```

Every invocation logs tier, model, prompt size, token usage, and latency to
.solocode/jcode-usage.jsonl so the cost payoff is auditable, not assumed.

If you must call jcode directly (e.g. the subtask needs jcode's own
bash/read/write tools), keep the same flag discipline:

```bash
jcode run "<prompt>" --provider-profile commandcode \
  --model deepseek/deepseek-v4-pro --no-selfdev --quiet --json
```

--tool-profile none --no-selfdev cut measured input tokens from 22,376 to
7,709 (~65%) for the same prompt by skipping jcode's own tool-use
scaffolding and repo self-dev detection -- always pass both unless the
delegated task genuinely needs jcode's own tools.

## Why the code Tier Needs a Guardrail Preamble

deepseek-v4-pro is materially stronger at code-reasoning than the flash
tier, but measured behavior shows it tends to go out of scope when given a
bare task: touching unrelated files, adding dependencies, refactoring
nearby code that wasn't asked for, or inventing requirements. The existing
harness boundaries (.harness.lock, lint/format config, verification gates)
help catch some of this after the fact, but the cheapest fix is upstream:
tell the model the constraints explicitly, immediately before the task,
every time. tools/jcode_delegate.py auto-prepends this for --tier code:

```text
STRICT OPERATING CONSTRAINTS (must follow, no exceptions):
1. Modify ONLY the files explicitly named in the task below. Do not touch
   any other file, and do not refactor nearby code that wasn't asked for.
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
```

Never call the code tier without this preamble present -- a bare prompt to
deepseek-v4-pro is the highest-risk way to invoke jcode.

## After Delegating -- Verification Is Mandatory, Not Optional

Treat every jcode result, from either tier, as an untrusted draft:

1. Read the actual diff/output yourself before acting on it.
2. Run the project's real verification gates (/verify, targeted pytest,
   ruff, security_scan.py) -- never skip this because the draft "looks
   right".
3. Check the tier-code self-check line against the actual files touched;
   if they don't match, reject and re-scope the prompt rather than
   patching around the drift.
4. Never pipe jcode output straight into a commit without this review --
   quality is the orchestrator's responsibility, not the worker's.

If a code-tier result violates the guardrails (touches extra files, adds a
dependency, ignores style), do not silently accept the parts that look
fine -- re-run with a tighter prompt (narrower file list, explicit style
example) rather than manually patching every violation; a prompt that
needs constant hand-fixing has failed the point of delegating.

## Deployment

This mechanism (this skill plus tools/jcode_delegate.py plus the AGENTS.md
/ CLAUDE.md "Delegating a task to jcode" section) is harness
infrastructure, not project code -- it ships with every deploy.py
scaffold / deploy.py deploy target project exactly like the rest of
.kilo/, tools/, and the root harness docs. tools/test_jcode_delegate.py is
the one exception: it's a dev-only self-test of this repo's own tooling
and stays out of deployed targets (see tools/deploy.py EXCLUDE_FILES), the
same way test_claude_hooks.py does for .claude/hooks/.

## Anti-patterns

| Don't | Do Instead |
|-------|------------|
| Call deepseek-v4-pro with a bare, unconstrained prompt | Always go through jcode_delegate.py --tier code (or manually prepend the guardrail) |
| Delegate a task that needs this session's context/history | Do it directly -- jcode is stateless, one-shot |
| Accept jcode's output without running verification gates | Always /verify or targeted tests before trusting a delegated change |
| Escalate every task to code tier "to be safe" | Default to simple; escalate only when the task clearly needs code-reasoning |
| Patch around repeated guardrail violations by hand | Reject and re-prompt with a narrower/tighter task instead |
