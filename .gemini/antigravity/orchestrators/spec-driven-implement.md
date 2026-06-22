---
description: Spec-driven implementation — read → validate → design → implement → verify compliance
mode: orchestrator
---

# Spec-Driven Implementation Orchestrator

## Phase 1: Parse Spec
**Agent**: planner
**Action**: Extract all requirements (MUST/SHOULD/MAY), constraints (MUST NOT), data models
**Output**: Structured requirement list

## Phase 2: Validate Understanding
**Agent**: planner
**Action**: Restate requirements, identify ambiguities, ask clarifying questions
**Gate**: Must get confirmation before proceeding

## Phase 3: Design
**Agent**: architect
**Action**: Map requirements to code structure — which files, what changes
**Output**: Implementation plan with file paths

## Phase 4: Implement
**Agent**: solo-code-engineer
**Action**: Execute the plan file by file
**Principle**: Read before edit, match patterns, verify syntax

## Phase 5: Verify Compliance
**Agent**: code-reviewer
**Action**: Check each requirement against the implementation
**Output**: Compliance matrix (REQ → file:line → status)
