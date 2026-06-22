---
name: warn-debug-statements
enabled: true
event: file
pattern: console\.log\(|debugger;?\b
action: warn
---

🐛 **Debug statement detected**

Remove `console.log` and `debugger` statements before committing. These are not for production code.
