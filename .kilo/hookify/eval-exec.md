---
name: block-eval-exec
enabled: true
event: file
pattern: \b(?:eval|exec)\s*\(
action: warn
---

⚠️ **eval()/exec() usage detected**

These functions can be code injection vectors. Consider safer alternatives. If this is intentional, verify inputs are strictly validated.
