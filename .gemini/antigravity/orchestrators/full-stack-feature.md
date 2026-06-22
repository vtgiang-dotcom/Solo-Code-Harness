---
description: Multi-phase feature development — spec → design → implement → test → review
mode: orchestrator
---

# Full-Stack Feature Orchestrator

## Phase 1: Specification
**Agent**: planner
**Action**: Read issues/specs, define problem statement and acceptance criteria
**Output**: Clear scope document

## Phase 2: Design
**Agent**: architect
**Action**: Explore codebase, design architecture, identify files to change
**Output**: Architecture doc + file list + data flow diagram

## Phase 3: Implementation
**Agent**: solo-code-engineer
**Action**: Bottom-up implementation — each layer builds on the previous
**Principle**: Read each file before editing, match existing patterns, verify syntax after each step

## Phase 4: Testing
**Agent**: tdd-guide
**Action**: Add tests for happy path, error states, edge cases, integration points
**Output**: Test suite covering all requirements

## Phase 5: Review
**Agent**: code-reviewer
**Action**: Review complete diff for correctness, security, style, completeness
**Output**: Review report with findings and verdict
