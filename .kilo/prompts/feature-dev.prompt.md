---
mode: plan
description: Systematic 7-phase feature development: Discovery → Exploration → Clarification → Architecture → Implementation → Review → Summary
triggers: build, create feature, implement, new feature, feature request
---

# Feature Development Workflow

Follow a systematic approach: understand the codebase deeply, identify underspecified details, design elegant architectures, then implement.

## Core Principles

- **Ask clarifying questions**: Identify ambiguities, edge cases, and underspecified behaviors before coding. Ask specific, concrete questions — do not make assumptions.
- **Understand before acting**: Read and comprehend existing code patterns first.
- **Read files identified by exploration**: After exploring, read the most important files before designing.
- **Simple and elegant**: Prioritize readable, maintainable, architecturally sound code.
- **Use TodoWrite**: Track all progress throughout.

---

## Phase 1: Discovery

**Goal**: Understand what needs to be built.

**Actions**:
1. Create todo list with all phases
2. If feature unclear, ask user:
   - What problem are you solving?
   - What should the feature do?
   - Any constraints or requirements?
3. Summarize understanding and confirm with user

---

## Phase 2: Codebase Exploration

**Goal**: Understand relevant existing code and patterns.

**Actions**:
1. Search for related functionality (`grep`, `glob`)
2. Read key files to understand conventions
3. Identify integration points and dependencies
4. Note established patterns to follow

---

## Phase 3: Clarification

**Goal**: Resolve all ambiguities before designing.

**Actions**:
1. List all unclear aspects
2. Ask specific questions — one at a time if many
3. Edge cases: empty input, error states, boundary values, concurrency
4. Wait for user answers before proceeding

---

## Phase 4: Architecture Design

**Goal**: Design the complete feature architecture.

**Actions**:
1. Define components and their responsibilities
2. Specify file paths: create vs modify
3. Design data flow and API contracts
4. Identify dependencies to add (if any)
5. Plan testing strategy

**Output**: Clear implementation blueprint with:
- Files to create/modify with change descriptions
- Component design with interfaces
- Data flow from entry to output
- Edge cases and error handling

---

## Phase 5: Implementation

**Goal**: Write code following the architecture.

**Actions**:
1. Create/modify files in dependency order
2. Follow existing code patterns exactly
3. Write tests alongside or before implementation
4. Keep each commit focused on one logical change
5. Run lint + typecheck after each file

---

## Phase 6: Quality Review

**Goal**: Ensure code meets standards.

**Actions**:
1. Run full test suite
2. Lint and typecheck pass
3. Verify all edge cases handled
4. Check no debug statements remain
5. Verify no accidental regressions

---

## Phase 7: Summary

**Goal**: Document what was done.

**Actions**:
1. List all files changed with brief description
2. Note any design decisions worth documenting
3. Confirm feature is ready for review
