---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf?\s+(?:/|~|\*|\./)
action: block
---

🛑 **Destructive rm command blocked**

This command could delete important files. Verify the exact path and use a safer approach.
