---
description: Generate a structured implementation plan and checklist before writing code.
---
# /plan — Implementation Planning

## Purpose
Generate a detailed implementation plan before writing any code. Forces thinking through architecture, dependencies, and risks upfront.

## Behavior
1. **Analyze requirements** — What exactly needs to be built?
2. **Identify affected files** — List specific files that will be created/modified
3. **Break down into tasks** — Ordered, actionable steps
4. **Flag risks** — What could go wrong? Dependencies? Edge cases?
5. **Estimate effort** — Per task

## Output Format
```markdown
## Plan: [Feature/Task]

### Affected Files
| File | Action | Purpose |
|------|--------|---------|
| src/... | CREATE | ... |
| src/... | MODIFY | ... |

### Tasks
1. [ ] Task 1 — description
2. [ ] Task 2 — description
3. [ ] Task 3 — description

### Risks
- Risk 1: ... (mitigation)
- Risk 2: ... (mitigation)

### Verification
- [ ] Tests pass
- [ ] Manual check: ...
```
