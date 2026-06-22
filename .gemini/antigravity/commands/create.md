---
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(git *)
description: Create a new feature, component, or file following project conventions
---

## Context

- Current branch: !`git branch --show-current`
- Project structure: !`ls -la`

## Task

### 1. Analyze Patterns
Find 3-5 similar existing files to understand conventions:
- Naming style (camelCase, snake_case, PascalCase)
- File structure (imports, exports, types)
- Error handling patterns
- Test file location and naming

### 2. Plan
- What files need to be created?
- What files need to be modified?
- What tests need to be written?

### 3. Create
- Create source file(s) matching existing conventions
- Create test file(s) with placeholder tests
- Update any index/barrel files or registrations

### 4. Verify
- Imports resolve correctly
- Tests run (may fail until implemented — expected)
- Existing tests still pass
- No new lint errors
