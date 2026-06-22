---
mode: ask
description: Comprehensive code review checklist — General, Frontend, Backend, Security, Performance, Testing, Documentation, Commit
triggers: code review, PR review, review my code, audit, check this diff
---

# Code Review Checklist

Use this checklist when reviewing code changes. Apply to the scope of the change only — do not flag pre-existing issues.

## General

- [ ] Code follows project conventions (AGENTS.md, .kilo/instruction/)
- [ ] No TypeScript `any` types or Python `# type: ignore`
- [ ] No hardcoded configuration values (use environment variables or constants)
- [ ] No console.log/debug statements in production code
- [ ] No commented-out code blocks
- [ ] Clear, descriptive variable/function names
- [ ] Appropriate error handling (no empty catch blocks)

## Frontend (React/TypeScript)

### Components
- [ ] Uses `memo()` + named function pattern for performance-critical components
- [ ] Proper TypeScript types (no implicit any)
- [ ] No inline styles (use CSS modules, Tailwind, or design tokens)
- [ ] Conditional classes use a utility like `cn()` or `clsx()`
- [ ] Barrel export in component folder via `index.ts`

### State
- [ ] Uses appropriate state management (Zustand, Context, Redux)
- [ ] Selects specific state slices (not entire store)
- [ ] Actions properly immutable
- [ ] Types exported alongside state

## Backend (FastAPI/Python)

### Pydantic Models
- [ ] Multi-model pattern (Base → Create → Update → Response → InDB)
- [ ] Proper aliases for camelCase JSON (`Field(..., alias="camelCase")`)
- [ ] Config has `populate_by_name = True`, Response has `from_attributes = True`

### Routers
- [ ] Proper auth dependency (authenticated vs optional)
- [ ] Returns proper HTTP status codes
- [ ] Has `response_model` defined
- [ ] Raises `HTTPException` for errors (not bare exceptions)

### Services
- [ ] Proper async/await usage
- [ ] Error handling for database operations
- [ ] Transaction boundaries documented

## Security

- [ ] No secrets in code or comments
- [ ] Auth required for write operations
- [ ] Input validation on all endpoints (via Pydantic/Joi/Zod)
- [ ] No SQL/NoSQL injection vulnerabilities (use parameterized queries)
- [ ] Cross-origin configuration locked down

## Performance

- [ ] React components properly memoized (when re-render cost is high)
- [ ] No unnecessary re-renders (use selectors)
- [ ] Expensive computations memoized with `useMemo`/`useCallback`
- [ ] API calls not in render path
- [ ] Pagination on list endpoints

## Testing

- [ ] Unit tests for new functions
- [ ] Component tests for new UI
- [ ] API tests for new endpoints
- [ ] Tests cover both success and error paths
- [ ] All tests pass locally

## Documentation

- [ ] Complex logic has explanatory comments (WHY, not WHAT)
- [ ] Public APIs have docstrings/JSDoc
- [ ] README updated if needed
- [ ] Types are self-documenting

## Commit Readiness

- [ ] Follows conventional commit format
- [ ] Commit message describes why, not just what
- [ ] No unrelated changes bundled
- [ ] Lint passes
- [ ] Build passes
- [ ] All tests pass
