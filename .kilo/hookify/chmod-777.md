---
name: warn-chmod-777
enabled: true
event: bash
pattern: chmod\s+777
action: warn
---

⚠️ **chmod 777 detected**

This grants read/write/execute to everyone. Consider more restrictive permissions (e.g., 755 or 644).
