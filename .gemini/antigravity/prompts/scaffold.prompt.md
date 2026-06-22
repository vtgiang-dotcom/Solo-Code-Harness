---
mode: plan
description: Scaffold a new component, module, or endpoint following project conventions
---

# Scaffold Workflow

## Core Principles
- **Follow existing patterns** — analyze 3-5 similar files before writing
- **Start minimal** — scaffold only what's needed, not what might be needed
- **Include tests** — every new file should have a corresponding test skeleton

## Phase 1: Analyze Patterns
1. Find 3-5 similar existing files in the codebase
2. Note: naming conventions, file structure, imports, error handling, test patterns
3. Identify the template you'll follow

## Phase 2: Create Files
1. Create the main source file(s) following identified patterns
2. Create corresponding test file(s)
3. Register/export the new module if needed

## Phase 3: Wire Up
1. Add necessary imports and references
2. Register routes, components, or commands
3. Add any required configuration

## Phase 4: Verify
1. Run existing tests to ensure nothing broke
2. Run new tests (they may fail until implementation — that's expected)
3. Verify syntax and imports resolve correctly
