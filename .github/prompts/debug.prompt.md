---
description: "Systematic debugging workflow with evidence-based root cause analysis."
$schema: https://raw.githubusercontent.com/github/copilot/main/schemas/prompt.schema.json
---
# Debug — Systematic Debugging

## Purpose
Activate evidence-based debugging. Never guess — form hypotheses, test them, confirm root cause before fixing.

## Behavior
1. **Reproduce** — Can you reproduce the bug? Describe exact steps
2. **Isolate** — Narrow down to the specific file/function/line
3. **Hypothesize** — Form a theory about the root cause
4. **Test hypothesis** — Add logs, breakpoints, or write a minimal reproduction
5. **Fix** — Apply the minimal fix
6. **Verify** — Prove the fix works with a test

## Rules
- Never apply a fix without understanding the root cause
- Always write a regression test
- Read error messages and stack traces carefully
- Check git log for recent related changes
