---
description: "Solo-Code Harness self-management: deploy, configure, maintain multi-agent harness + security audit + spec-driven orchestration"
mode: orchestrator
---

# Spec-Driven Implementation Orchestrator

Coordinates structured spec-first development: requirements → spec → validation → implementation.

## Why Spec-Driven?

- **Reduces drift**: implementation stays locked to agreed spec
- **Measurable completion**: each spec item is a binary pass/fail checkpoint
- **Reviewable upfront**: architecture decisions happen before code is written
- **Auditable**: spec serves as implementation contract + documentation

## Workflow

### Phase 1: Generate Spec

**Agent**: planner
**Action**: Convert requirements into a structured specification with:
- **Purpose**: 1-2 sentences on what this feature/task achieves
- **Scope**: explicit inclusions and exclusions (non-goals)
- **Functional Requirements**: numbered list of FR-01, FR-02, ...
- **Non-Functional Requirements**: NFR-01 (perf), NFR-02 (security), ...
- **Data Model Changes**: new/updated schemas, migrations, API contracts
- **Affected Files**: concrete file paths (from codebase analysis)
- **Edge Cases & Error States**: what happens on null input, network failure, race conditions
- **Acceptance Criteria**: specific, testable conditions that define "done"

**Output**: `SPEC-<feature>.md` (written to project root or `.kilo/specs/`)

### Phase 2: Validate Spec

**Agent**: architect
**Action**: Review spec for completeness, consistency, and architectural soundness:
- Are all edge cases covered?
- Are data model changes backwards-compatible?
- Do non-functional requirements have measurable thresholds?
- Are acceptance criteria testable?
- Does the scope avoid YAGNI violations?

**Checklist** (all MUST pass before proceeding):
- [ ] Every FR has at least one acceptance criterion
- [ ] Every NFR has a measurable threshold (not "should be fast")
- [ ] All affected file paths are real (verified via codebase scan)
- [ ] Edge cases cover: null/empty input, network failure, concurrent access, auth failure
- [ ] No FR violates existing architectural constraints
- [ ] Spec size ≤ 500 lines

**Output**: validation report + approved spec (or spec returned for revision)

### Phase 3: Implement from Spec

**Agent**: solo-code-engineer
**Action**: Implement each functional requirement in order:
- For each FR: write failing test → implement → verify test passes
- Checkpoint after each FR: verify no regression on prior FRs
- After all FRs: run full test suite
- Run `python .github/scripts/security_scan.py .`

**Quality Gates** (per FR):
- [ ] Test exists and passes for this FR
- [ ] All prior FR tests still pass (no regression)
- [ ] Code matches existing project patterns (verified by file-editor-pro skill)
- [ ] No secrets introduced (security_scan.py clean)

### Phase 4: Review & Close

**Agent**: code-reviewer
**Action**: Full review against spec:
- Every acceptance criterion met?
- Test coverage adequate (≥80% on new code)?
- No dead code or debug statements left in?
- Spec updated with any implementation-learned changes?

**Output**: review report + spec closure (mark each FR as verified)

## Orchestration Rules

- **HARD GATE**: Do not write ANY implementation code until Phase 2 spec validation passes
- Phase 2 failures MUST be resolved before Phase 3 begins
- If implementation reveals a spec gap, STOP → update spec → re-validate → resume
- Security scan runs at the end of Phase 3 AND Phase 4
- Spec file is checked into version control alongside the code
