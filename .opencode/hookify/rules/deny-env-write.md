---
name: deny-env-file-write
enabled: true
event: file
pattern: \.env$
action: block
---

⛔ Blocked: Writing to .env files is blocked to prevent accidental secret leaks.

Environment files (.env) should only be modified manually, never by an AI agent.
They contain credentials, API keys, and other secrets that should never be
accidentally committed to version control.

If you need to update environment configuration:
1. Edit the .env file manually in your editor
2. Provide the new value to the agent as context
3. Or temporarily disable this rule by setting `enabled: false`

Do NOT disable this rule to inject credentials into code.
