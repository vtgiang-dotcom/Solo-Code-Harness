---
mode: plan
description: Generate a detailed refactoring plan that identifies issues, preserves behavior, and provides step-by-step instructions
triggers: refactor, clean up, improve code, modernize, decouple
---

# Refactoring Workflow

## Core Rules

- **Preserve behavior**: Refactoring means changing structure WITHOUT changing external behavior. Tests must pass before AND after.
- **One thing at a time**: Each refactoring step should be a single, reversible transformation.
- **Commit often**: Commit after each successful step. If something breaks, you know exactly where.

## Pre-Refactoring Checklist

- [ ] Tests exist for the code being refactored
- [ ] Tests pass on current code (`git stash` → run tests → `git stash pop`)
- [ ] Understand the current behavior — read the code and tests
- [ ] Identify the specific problem: complexity, coupling, duplication, naming?

## Refactoring Catalog

### Extract Method
**When**: A block of code can be grouped and named.
**Signs**: Comments describing what a block does, long methods, duplicated logic.

### Rename Variable/Method/Class
**When**: Name doesn't reveal intent.
**Signs**: You need a comment to explain what `x` means.

### Move Method/Field
**When**: A method uses more features of another class than its own.
**Signs**: Method accesses many fields from another object.

### Replace Conditional with Polymorphism
**When**: Same switch/if-else appears in multiple places.
**Signs**: Adding new case requires touching multiple files.

### Introduce Parameter Object
**When**: A group of parameters always travel together.
**Signs**: Same 3+ params appear in multiple method signatures.

### Decompose Conditional
**When**: Complex conditional logic (`if/else`, `switch`).
**Signs**: You need comments to explain each branch.

### Replace Magic Number with Constant
**When**: Literal number appears without obvious meaning.
**Signs**: You need context to understand what `86400` means.

## Workflow

1. **Analyze** — Identify what needs refactoring and why
2. **Plan** — List specific refactoring steps (from catalog above)
3. **Gate** — Confirm tests pass BEFORE starting
4. **Execute** — Apply one refactoring at a time
5. **Verify** — Run tests after each step
6. **Commit** — Commit each successful step
7. **Clean** — Remove unused code your refactoring created

## Anti-Patterns to Avoid

- ❌ Refactoring and adding features in the same change
- ❌ Rewriting from scratch ("big bang refactoring")
- ❌ Changing tests to match new behavior during refactoring
- ❌ Skipping tests between steps ("I'll test at the end")
- ❌ Refactoring code without test coverage

## After Refactoring

- [ ] All original tests pass (unchanged)
- [ ] No new tests needed (behavior didn't change)
- [ ] Code is simpler (fewer lines, clearer names)
- [ ] Linter passes
