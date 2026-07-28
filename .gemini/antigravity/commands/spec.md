---
allowed-tools: Read, Grep, Glob
description: Read and follow the project specification (SPEC.md) for hard requirements
---

## Context

- SPEC.md: Core specification at project root
- source/plugins/: 13 composable plugins with plugin.json manifests
- tools/garden.py: Boundary enforcement per SPEC §0.1

## Task

### 1. Read SPEC.md
Read the specification to understand hard requirements.

### 2. Check Compliance
- Does the change fit within SPEC boundaries?
- No infrastructure files in plugins (SPEC §0.1)
- No new dependencies without explicit instruction
- Harness artifacts must be generated from source plugins

### 3. Validate
```bash
python tools/garden.py
python tools/validate_schemas.py
```

### 4. Report
```
SPEC CHECK
==========
Requirement: <SPEC section>
Status: COMPLIANT / NEEDS ADJUSTMENT

If non-compliant, explain why and what needs to change.
```
