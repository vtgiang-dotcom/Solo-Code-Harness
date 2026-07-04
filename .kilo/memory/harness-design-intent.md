# Design Intent — DO NOT REMOVE

## What This Harness Is

Solo-Code Harness is a multi-layer quality and safety system for AI coding agents. It is NOT a generic agent config — every rule, skill, hook, and gate exists because a specific failure mode was observed in real usage.

## Architecture Layers

```
AGENTS.md        → Behavior rules, anti-hallucination, prose quality, harness boundaries
.harness.lock    → Boundary manifest — which files are harness vs project code
.kilo/instruction/ → Language-specific rules (Python, TS, Git, DB)
.kilo/skill/     → 44 domain skills (code-review, debugging, testing...)
.kilo/agents/    → 14 specialized agents with handoff chains
.kilo/hooks/     → 20 lifecycle hooks (bash validation, secret scan, learning...)
.kilo/hookify/   → MD-config rules engine (user-customizable policies)
.kilo/prompts/   → Structured workflow templates (code review, feature dev...)
tools/           → Harness utilities (deploy, generate, garden, harness_config)
.github/scripts/ → Verification gates (security_scan, checklist, eval_harness)
.contracts/      → Sub-agent status contracts (DeerFlow pattern)
kilo.jsonc       → Permission model (bash allow/deny, task allow/deny)
```

## Why Each Layer Exists

| Layer | Prevents |
|-------|----------|
| Anti-hallucination rules (A1-A6) | Model invents APIs, libraries, non-existent params, loops forever |
| Harness Boundaries (AGENTS.md + .harness.lock) | AI confuses harness files with project code, modifies rules instead of fixing bugs |
| Prose quality rules (9-16) | AI-tell patterns: clichés, filler phrases, handwavy claims |
| Hierarchical config (harness_config.py) | Config scattered across .env, hardcoded values — no per-project overrides |
| 7-category gate guard | rm -rf, force push, SQL injection, disk destruction |
| Hookify MD engine | User needs custom policies without editing JS |
| Continual learning | Agent forgets everything between sessions |
| Ralph Loop | Agent stops work early, doesn't iterate |
| 4-agent parallel review | Single-agent review misses bugs |
| 14 specialized agents | Generalist agent makes mistakes in domain-specific work |
| Deploy/scaffold (deploy.py) | Manual copy-paste errors when replicating harness to new projects |

## Modification Policy

1. Before modifying any rule, ask: "Which failure mode does this prevent?"
2. If you cannot answer, do not modify.
3. Run `python .github/scripts/checklist.py .` after any change.
4. All gates must stay green.

## Key Metrics

| Metric | Target |
|--------|--------|
| Secret scan | 0 findings |
| Ruff lint | 0 errors |
| Harness eval | 59/59 pass |
| Gate guard | 0 false blocks |
| Hook uptime | 100% (all stdin.resume present) |
