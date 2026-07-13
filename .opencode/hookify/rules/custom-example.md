---
name: custom-example
enabled: false
event: bash
pattern: npm\s+cache\s+clean\s+--force
action: block
---

⛔ Blocked: npm cache clean --force destroys the local npm cache.

Use `npm cache verify` instead, or `npm cache clean` without --force.
This rule is disabled by default — set `enabled: true` to activate it.

To create your own custom rules:
1. Create a new .md file in .opencode/hookify/rules/
2. Add YAML frontmatter with: name, enabled, event (bash|file|all), pattern (regex), action (block|warn|allow)
3. Add a message body explaining the rule

Example block rule:
---
name: my-custom-rule
enabled: true
event: bash
pattern: dangerous-command\s+--flag
action: block
---

Example warn rule:
---
name: my-warning-rule
enabled: true
event: file
pattern: \.critical-file$
action: warn
---

Example allow rule (whitelist a command normally blocked by built-in patterns):
---
name: allow-specific-script
enabled: true
event: bash
pattern: my-safe-script\.sh
action: allow
---
