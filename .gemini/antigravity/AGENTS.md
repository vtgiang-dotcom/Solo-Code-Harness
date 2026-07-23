# Solo-Code — Gemini Agent Harness (Rulebook for Gemini/Antigravity)

> **CRITICAL:** Read this file fully before taking any action. These rules are NON-NEGOTIABLE.

The Solo-Code Harness loads automatically from `.gemini/antigravity/`. The AI reads `AGENTS.md`, `knowledge/`, and `skills/` at session start. For boundary authority, see `.harness.lock` and root `AGENTS.md`.

## Harness Boundaries (READ FIRST)

> **DO NOT CONFUSE harness files with project source code.**

This project is powered by **Solo-Code Harness** — an AI agent discipline layer. When analyzing or modifying ANY file, first classify it:

| If the file path starts with... | Then it is... | Action |
|----------------------------------|---------------|--------|
| `.gemini/`, `.kilo/`, `.copilot/`, `.claude/` | Harness engine | Rules/skills/hooks for AI behavior — not project logic |
| `.github/scripts/` | Harness verification | `security_scan.py`, `checklist.py`, `check_skips.py`, `eval_harness.py` |
| `tools/` | Harness utilities | `deploy.py`, `generate_harness.py`, `garden.py`, `harness_config.py` |
| `.contracts/` | Harness sub-agent contracts | Status contracts for delegated agents |
| `AGENTS.md`, `agent.yaml`, `kilo.jsonc`, `.mcp.json`, `.ruff.toml`, `.gitleaks.toml`, `Makefile`, `jcode.ps1`, `verify.sh`, `extensions_config.json`, `.harness.lock`, `.solocode/`, `.pre-commit-config.yaml`, `.github/pull_request_template.md` | Harness config | Agent behavior configuration — not application config |
| **Everything else** | **Project code** | Your actual application — this is what you modify |

**Key rule:** Never modify harness files to fix a project bug. Never modify project files to fix a harness issue. Read `.harness.lock` for the authoritative boundary list.

## Self-Verification Handshake

When asked "Is Solo-Code Harness active?" or "What rules apply here?", answer:
`Solo-Code Harness active: behavior rules, anti-hallucination rules, security rules, prose quality rules, 32 skills, 15 agents. Use /verify to validate.`

## Escape Hatch (Meta-Principle)

> *"Break any of these rules sooner than say anything outright barbarous."*
> — George Orwell, "Politics and the English Language" (1946), Rule 6

Rules are guides to quality and safety, not ends in themselves. When a rule fights the task, use judgment — but document the exception.

---

## Fresh Information First (ANTI-STALENESS)

**Your training data is a snapshot. SDKs and APIs change after your cutoff.**

Before using ANY library you're not 100% certain about:
1. **Verify it exists** — Check `package.json`, `requirements.txt`, or existing imports
2. **Check for breaking changes** — API signatures change between major versions
3. **Mark uncertainty** — If unverified, tag `// VERIFY: <lib>.<symbol> against version X`

---

## Surgical Changes (TOUCH ONLY WHAT YOU MUST)

- **Don't "improve" adjacent code** — Your job is the requested change, not a style overhaul
- **Don't refactor things that aren't broken** — Refactoring is a separate task
- **Match existing style** — Consistency within a file beats your preference
- **Clean up only your own mess** — Remove only what YOUR changes made unused

---

## Request Classification (STEP 1 — BEFORE ANY TOOL)

| Type             | Trigger                                   | Action                                              |
| ---------------- | ----------------------------------------- | --------------------------------------------------- |
| **QUESTION**     | "what is", "explain", "how does"          | Text only. No tools.                                |
| **SIMPLE EDIT**  | Single-file fix, typo, small change       | Read → Edit → Verify                                |
| **COMPLEX TASK** | "build", "create", "refactor", multi-file | Plan → Get approval → Implement → Verify            |
| **DESTRUCTIVE**  | "delete", "rm", "drop", "force push"      | **STOP** → Ask explicit permission → Wait for "yes" |
| **REVIEW**       | "review", "audit", "check this PR"        | Load code-review-expert skill                       |

---

## Behavior Rules (MANDATORY)

### Safety

1. **BEFORE any destructive operation** (rm, delete, drop table, force push) → STOP. Ask explicit Yes/No.
2. **BEFORE committing or pushing** → Scan diff for secrets. Refuse to commit if secrets detected.
3. **Never use destructive git commands** (`push --force`, `reset --hard`) unless user explicitly requests. Never force-push to main/master.
4. **Permission Guard**: Load `permission-guard` skill before any delete, credential access, or config change.

### Code Quality

5. **ALWAYS read a file before editing it.**
6. **Use exact string replacement** over full-file rewrites.
7. **Preserve existing patterns.** Match code style, naming, and structure.
8. **Never leave broken code.** Verify syntax after any edit.

### AI Discipline (Anti-Hallucination)

A-1. **Verify library existence before using it.** Check `package.json`, `requirements.txt`, or imports for the actual installed version.
A-2. **No invented function signatures, parameter names, or return types.** Never guess a library's API.
A-3. **Compiling does not mean correct.** Before validating, list at least two failure modes: empty input, boundary values, or state assumptions.
A-4. **No restated-code comments.** Comments must explain WHY, not paraphrase WHAT.
A-5. **Acknowledge uncertainty explicitly.** If you do not know something, say "I do not know".
A-6. **Loop detection.** If the same tool is called 3+ times consecutively with the same parameters, change strategy immediately.

### Prose Quality (MANDATORY)

| # | Rule | Severity |
|---|------|----------|
| 9 | **Cut needless words** — never "in order to" (→ "to"), "due to the fact that" (→ "because"), "it is important to note that" (→ delete), "may potentially" (→ "may"). | `high` |
| 10 | **Drop dying metaphors** — never "pushes the boundaries", "paradigm shift", "state of the art", "cutting edge", "paves the way", "unlock the potential", "game changer". | `high` |
| 11 | **Use concrete terms** — replace "factors", "aspects", "considerations" with specific items. | `high` |
| 12 | **Prefer plain English** — "use" over "leverage"/"utilize"; "method" over "methodology". | `medium` |
| 13 | **No transition-word openers** — avoid "Additionally", "Furthermore", "Moreover" at sentence start. | `medium` |
| 14 | **Varied sentence starts** — never open two consecutive sentences with the same word. | `medium` |
| 15 | **Support claims with evidence** — never write "prior work shows" without naming the source. Never fabricate citations. | `critical` |
| 16 | **Split long sentences** — split sentences over 30 words. Vary sentence length. | `high` |

#### BAD → GOOD Examples

- BAD: `This PR makes minor adjustments to fix an issue causing test failures.`
- GOOD: `Fixes a null-pointer crash in test_checkout_flow when the cart has a single item.`
- BAD: `We leverage state-of-the-art embedding models to unlock the retrieval pipeline's potential.`
- GOOD: `We use text-embedding-3-large, raising recall@10 by 7 points over ada-002.`

### Skills to Load by Context

| When | Load Skill |
|------|------------|
| Reviewing code, PRs, diffs | `code-review-expert` |
| Editing files, refactoring | `file-editor-pro` |
| Committing, pushing, PRs | `git-workflow-master` |
| Deleting, credentials, config | `permission-guard` |
| Debugging, errors, failures | `systematic-debugging` |
| Brainstorming, designing | `brainstorming` |
| Writing tests, TDD | `testing-patterns` |
| Designing APIs, interfaces | `api-patterns` |
| Harness internals, skills, agents | `solo-code-harness` |

### Complex Tasks

17. **Socratic Gate:** For complex requests, ask at least 2 clarifying questions before coding.
18. **Plan before implement:** Present plan → Get approval → Execute.
19. **Synthesize, don't delegate blindly:** When using sub-agents, read findings and write specific implementation instructions.

---

## Tool Usage

| Task             | Use                                             |
| ---------------- | ----------------------------------------------- |
| Search code      | `grep_search`                                   |
| Read files       | `view_file`                                     |
| Edit files       | `replace_file_content` (contiguous edit), `multi_replace_file_content` (non-contiguous) |
| Run commands     | `run_command`                                   |
| Complex research | Spawn `browser_subagent` if browser interaction is needed |

---

## Git Commit Convention

```
type: concise summary (max 72 chars)

Optional body: 1-2 sentences explaining WHY.

Co-Authored-By: Solo-Code <admin@solo-code.com>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`
**Tone:** Imperative: "Add", "Fix", "Update", "Refactor", "Remove"

---

## Memory System

Persistent memory at `.gemini/antigravity/knowledge/`. The AI reads Knowledge Items (KIs) at session start.

- `knowledge/metadata.json` — Index of all knowledge items
- `knowledge/artifacts/` — Memory files (project-conventions, anti-hallucination, prose-quality, security-patterns, project-architecture)

---

## Claude Code Handoff Protocol (check at session start)

Claude Code cannot invoke Antigravity headlessly, so a human relays tasks
manually. Check `.gemini/antigravity/handoff/inbox/` for `*-plan.md` files
with `status: pending` in the frontmatter — these are tasks Claude Code
delegated to you. Full protocol: `.gemini/antigravity/handoff/README.md`.

When given a plan file to execute:
1. Read the full plan file (`Task`, `Context`, `Expected report format` sections).
2. Do the work.
3. Write your report to `.gemini/antigravity/handoff/outbox/<same-slug>-report.md`
   with a frontmatter header (`slug`, `completed`, `from: gemini`) — Claude
   Code auto-detects new files here at its next session start.
4. Do NOT delete or edit the plan file in `inbox/` — it's the durable record
   of what was asked. Update its `status:` to `done` if you want, but leave
   the file itself intact.

---

## Security Rules

Key enforcement points:
- **ALL user input is untrusted** — validate type, length, format, and range
- **Use parameterized queries** for SQL — never string interpolation
- **Never hardcode credentials** — use environment variables
- **Passwords** must use bcrypt/scrypt/argon2 — never MD5/SHA1

For full details, see `.gemini/antigravity/instruction/security-patterns.md`.

---

## Verification Gates

Before marking any task complete, verify:
- [ ] `python .github/scripts/security_scan.py .` passes
- [ ] `python .github/scripts/checklist.py .` passes
- [ ] `python .github/scripts/check_skips.py tools/` passes (0 unauthorized skips)
- [ ] No console.log/debug statements in production code
- [ ] Commit message follows project conventions

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
| Python | `instruction/rules-python.md` | PEP 8, type hints, parameterized queries, pytest |
| TypeScript/JS | `instruction/rules-typescript.md` | No `any`, React keys, XSS prevention |
| SQL/DB | `instruction/rules-database.md` | Index FKs, cursor pagination, parameterized queries |
| Git | `instruction/rules-git.md` | Conventional commits, branch naming |

## Specialized Subagents

Available for domain-specific work. See `.gemini/antigravity/agents/`:

| Agent | Purpose |
|-------|---------|
| `architect` | System architecture design, trade-off evaluation |
| `code-reviewer` | Multi-axis code review (quality, security, performance) |
| `code-simplifier` | Simplify code for clarity without changing behavior |
| `code-skeptic` | Adversarial review — stress-test assumptions |
| `database-reviewer` | DB query/schema/migration review |
| `planner` | Implementation planning for complex features |
| `python-reviewer` | Python code review — PEP 8, type hints, Pythonic patterns |
| `refactor-cleaner` | Dead code cleanup, logic simplification |
| `security-auditor` | Security audit — secrets, vulnerabilities, misconfigurations |
| `solo-code-engineer` | Primary engineer — rules enforcement, verification gates |
| `tdd-guide` | Test-driven development enforcement |
| `test-engineer` | QA — test coverage, test strategy, regression testing |
| `typescript-reviewer` | TS/JS code review — types, React patterns, XSS, async safety |
| `web-performance-auditor` | Core Web Vitals, loading, rendering, network performance |

---

## Language

When user speaks Vietnamese → respond in Vietnamese. Code comments and variable names remain in English.
