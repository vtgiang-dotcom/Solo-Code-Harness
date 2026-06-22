---
mode: plan
description: Systematic refactoring workflow
---

# Refactoring

## Principles
- Don't change behavior — improve structure
- Small, safe, reversible steps
- Tests as safety net
- Match existing style

## Phase 1: Understand
- Read target code and its callers/callees
- Map dependencies and data flow
- Identify: complexity, duplication, coupling

## Phase 2: Plan
- Define target structure
- Break into small sequential steps
- Each step leaves code working

## Phase 3: Execute
- Extract repeated logic
- Rename for clarity
- Simplify conditionals, reduce nesting
- Remove dead code (only if 100% certain)
- Verify after each step

## Phase 4: Verify
- Run all tests
- Compare behavior before/after
- Review diff for unintended changes
