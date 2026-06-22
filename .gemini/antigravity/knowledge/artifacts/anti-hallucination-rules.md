# Anti-Hallucination Rules — Solo-Code Harness

> These rules prevent generating plausible-looking but incorrect code.

## A-1: Verify Library Existence
Before using any library, check `package.json`, `requirements.txt`, or existing imports. If unverified, mark: `// VERIFY: <lib>.<symbol> against version X`

## A-2: No Invented Signatures
Never guess function signatures, parameter names, or return types. Silent stubs are worse than refusal.

## A-3: Compiling ≠ Correct
Confirm code does what its name promises. List at least two failure modes: empty input, boundary values, state assumptions.

## A-4: No Restated-Code Comments
Comments explain WHY, not WHAT. Never write "used by X flow" — that belongs in commit messages.

## A-5: Acknowledge Uncertainty
If you don't know, say "I need to verify X". Name trade-offs explicitly.
