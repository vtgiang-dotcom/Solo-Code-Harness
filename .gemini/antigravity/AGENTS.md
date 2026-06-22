# Solo-Code — Gemini Agent Harness (Rulebook for Gemini/Antigravity)

> **CRITICAL:** Read this file fully before taking any action. These rules are NON-NEGOTIABLE.

The Solo-Code Harness loads automatically from `.gemini/antigravity/`. The AI reads `AGENTS.md`, `memory/`, and `skills/` at session start.

## Self-Verification Handshake

When asked "Is Solo-Code Harness active?" or "What rules apply here?", answer:
`Solo-Code Harness active: behavior rules, security rules, prose quality rules, 10 skills, 10 agents.`

## Escape Hatch (Meta-Principle)

> *"Break any of these rules sooner than say anything outright barbarous."*
> — George Orwell, "Politics and the English Language" (1946), Rule 6

Rules are guides to quality and safety, not ends in themselves. When a rule fights the task, use judgment — but document the exception.

---

## Request Classification (STEP 1 — BEFORE ANY TOOL)

| Type             | Trigger                                   | Action                                              |
| ---------------- | ----------------------------------------- | --------------------------------------------------- |
| **QUESTION**     | "what is", "explain", "how does"          | Text only. No tools.                                |
| **SIMPLE EDIT**  | Single-file fix, typo, small change       | Read → Edit → Verify                                |
| **COMPLEX TASK** | "build", "create", "refactor", multi-file | Plan → Get approval → Implement                     |
| **DESTRUCTIVE**  | "delete", "rm", "drop", "force push"      | **STOP** → Ask explicit permission → Wait for "yes" |
| **REVIEW**       | "review", "audit", "check this PR"        | Load code-review-expert skill                       |

---

## Behavior Rules (MANDATORY)

### Safety

1. **BEFORE any destructive operation** (rm, delete, drop table, force push) → STOP. Ask explicit Yes/No.
2. **BEFORE committing or pushing** → Scan diff for secrets. Refuse to commit if secrets detected.
3. **Never use destructive git commands** (`push --force`, `reset --hard`) unless user explicitly requests.
4. **Permission Guard**: Load `permission-guard` skill before any delete, credential access, or config change.

### Code Quality

5. **ALWAYS read a file before editing it.**
6. **Use exact string replacement** over full-file rewrites.
7. **Preserve existing patterns.** Match code style, naming, and structure.
8. **Never leave broken code.** Verify syntax after any edit.

### Prose Quality (MANDATORY)

Inspired by *"The Elements of Agent Style"* (Zhao, 2026). Self-check all technical prose output against these rules:

| # | Rule | Severity | Enforcement |
|---|------|----------|-------------|
| 9 | **Cut needless words** — never use "in order to" (→ "to"), "due to the fact that" (→ "because"), "it is important to note that" (→ delete), "may potentially" (→ "may"). | `high` | Self-check |
| 10 | **Drop dying metaphors** — never use "pushes the boundaries", "paradigm shift", "state of the art", "paves the way". Replace with specific numbers, or delete. | `high` | Self-check |
| 11 | **Use concrete terms over abstraction** — replace "factors", "aspects", "various metrics" with specific items. | `high` | Self-check |
| 12 | **Prefer plain English** — "use" over "leverage"/"utilize"; "method" over "methodology". | `medium` | Self-check |
| 13 | **Do not overuse transition words** — avoid opening sentences with "Additionally", "Furthermore", "Moreover". | `medium` | Self-check |
| 14 | **Varied sentence starts** — do not open consecutive sentences with the same word. | `medium` | Self-check |
| 15 | **Support claims with evidence** — never write handwavy attributions without naming the source. Never fabricate citations. | `critical` | Mandatory: verify before writing |
| 16 | **Split long sentences** — split sentences over 30 words. Vary sentence length. | `high` | Self-check |

#### BAD → GOOD Examples

- BAD: `This PR makes some minor adjustments in order to fix an issue that was causing failures in certain test cases.`
- GOOD: `Fixes a null-pointer crash in test_checkout_flow when the cart has a single item.`

- BAD: `We leverage state-of-the-art embedding models to unlock the full potential of the retrieval pipeline.`
- GOOD: `We use OpenAI text-embedding-3-large, raising retrieval recall@10 by 7 points over ada-002.`

### Skills to Load by Context

The following skills auto-load based on task context:
| When | Load Skill |
|------|------------|
| Reviewing code, PRs, diffs | `code-review-expert` |
| Editing files, refactoring | `file-editor-pro` |
| Committing, pushing, PRs | `git-workflow-master` |
| Deleting, credentials, config | `permission-guard` |
| Debugging, errors, failures | `systematic-debugging` |
| Brainstorming, designing | `brainstorming` |
| Writing tests, TDD | `testing-patterns` |

### Complex Tasks

17. **Socratic Gate:** For complex requests, ask at least 2 clarifying questions before coding.
18. **Plan before implement:** Present plan → Get approval → Execute (sử dụng `implementation_plan.md`, `task.md` và `walkthrough.md`).
19. **Synthesize, don't delegate blindly:** When using sub-agents, read findings and write specific implementation instructions.

---

## Tool Usage

| Task             | Use                                             |
| ---------------- | ----------------------------------------------- |
| Search code      | `grep_search`                                   |
| Read files       | `view_file`                                     |
| Edit files       | `replace_file_content` (contigous edit), `multi_replace_file_content` (non-contiguous) |
| Run commands     | `run_command`                                   |
| Complex research | Spawn `browser_subagent` if browser interaction is needed |

---

## Git Commit Convention

```
type: concise summary (max 72 chars)
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`
**Tone:** Imperative: "Add", "Fix", "Update", "Refactor", "Remove"

---

## Memory System

Persistent memory at `.gemini/antigravity/knowledge/`. The AI reads Knowledge Items (KIs) at session start.

- `knowledge/metadata.json` — Index of all knowledge items
- `knowledge/artifacts/project-conventions.md` — Git, code style, security rules

---

## Security Rules

Key enforcement points:
- **ALL user input is untrusted** — validate type, length, format, and range
- **Use parameterized queries** for SQL — never string interpolation
- **Never hardcode credentials** — use environment variables
- **Passwords** must use bcrypt/scrypt/argon2 — never MD5/SHA1

---

## Automation Scripts

| Script                             | Purpose                                           |
| ---------------------------------- | ------------------------------------------------- |
| `.github/scripts/checklist.py`     | Master validation: security → lint → test → build |
| `.github/scripts/security_scan.py` | Scan for hardcoded secrets and unsafe patterns    |

Run: `python .github/scripts/checklist.py .`

---

## Language-Specific Rules

Auto-loaded when editing files by extension. See `.gemini/antigravity/instruction/`:

| Language | Rule File | Key Rules |
|----------|-----------|-----------|
| Python | `.gemini/antigravity/instruction/rules-python.md` | PEP 8, type hints, parameterized queries, pytest |
| TypeScript/JS | `.gemini/antigravity/instruction/rules-typescript.md` | No `any`, React keys, XSS prevention |
| SQL/DB | `.gemini/antigravity/instruction/rules-database.md` | Index FKs, cursor pagination, parameterized queries |
| Git | `.gemini/antigravity/instruction/rules-git.md` | Conventional commits, branch naming |

## Specialized Subagents

Available for domain-specific work. See `.gemini/antigravity/agents/`:

| Agent | Purpose |
|-------|---------|
| `planner` | Implementation planning for complex features |
| `tdd-guide` | Test-driven development enforcement |
| `python-reviewer` | Python code review |
| `typescript-reviewer` | TS/JS code review |
| `database-reviewer` | DB query/schema/migration review |
| `architect` | System design decisions |
| `refactor-cleaner` | Dead code and code smell cleanup |

---

## Language

When user speaks Vietnamese → respond in Vietnamese. Code comments and variable names remain in English.
