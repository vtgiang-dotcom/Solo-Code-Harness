---
description: "Make an architectural decision with trade-off analysis. Choose between options and document the rationale."
$schema: https://raw.githubusercontent.com/github/copilot/main/schemas/prompt.schema.json
---
Evaluate the following decision: $ARGUMENTS

1. Identify at least 2 viable options
2. For each option, list:
   - Pros (with concrete reasons)
   - Cons (with concrete risks)
   - Implementation cost estimate (low/medium/high)
3. Recommend one option with clear rationale
4. Flag any irreversible consequences

Output a markdown decision record (Architecture Decision Record) with the recommended option clearly marked. If uncertainty is high, state what additional information would resolve it.

Format output as:
```markdown
# Architecture Decision: [Title]

## Context
[Problem description]

## Decision
[Chosen approach]

## Rationale
[Why chosen, trade-offs]

## Consequences
### Positive
- ...

### Negative (Risks)
- ...
- Mitigation: ...

## Alternatives Considered
1. **Option A**: [description] — rejected because [reason]
2. **Option B**: [description] — rejected because [reason]
```
