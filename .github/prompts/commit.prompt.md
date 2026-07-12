---
description: "Create a git commit with auto-generated conventional commit message after reviewing changes."
$schema: https://raw.githubusercontent.com/github/copilot/main/schemas/prompt.schema.json
---
# Commit — Git Commit

Create a well-formed git commit from staged and unstaged changes.

## Workflow

1. **Analyze current state**
   - Run `git status` for overview
   - Run `git diff` for unstaged changes
   - Run `git diff --cached` for staged changes
   - Run `git log --oneline -5` for recent commit style

2. **Review changes**
   - List each changed file with a 1-line summary
   - Identify the primary category: feat, fix, refactor, docs, test, chore, perf, style, security
   - Note any files that should NOT be committed (.env, credentials, large binaries)

3. **Draft commit message**
   - Format: `<type>: <short description>`
   - Types: feat, fix, refactor, docs, test, chore, perf, style, security
   - Description: imperative mood, ≤72 chars, explains WHY not WHAT
   - Footer: `Co-Authored-By: Solo-Code <admin@solo-code.com>`

4. **Present for confirmation**
   - Show the drafted message
   - List files to be committed
   - Ask user to confirm or edit

5. **Stage and commit**
   - Stage relevant files
   - Create commit
   - Show commit hash and status

## What NOT to commit
- Files matching `.env`, `.env.*`, `credentials.json`, `*.pem`, `*.key`
- Files in `.gitignore`
- Large binary files without explicit user approval
- `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`
