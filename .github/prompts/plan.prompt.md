---
description: "Create an actionable implementation plan. Break down the task, write exact file paths, and present for approval before coding."
$schema: https://raw.githubusercontent.com/github/copilot/main/schemas/prompt.schema.json
---
You are in planning mode. Create an implementation plan for: $ARGUMENTS

Break the work into ordered steps. For each step, specify:
- Exact file paths to create or modify
- What change to make (create, edit, delete)
- Dependencies between steps

Format the plan as a markdown checklist. After presenting the plan, ask the user to approve before implementation begins.

Do NOT write any code. This is a planning-only task.
