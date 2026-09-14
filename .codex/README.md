# Codex CLI integration

Codex loads the root `AGENTS.md` automatically. This directory documents the
project-specific entrypoints that replace engine lifecycle hooks:

```powershell
python tools/codex_session.py start --session-id <id>
python tools/codex_verify.py
python tools/codex_session.py end --session-id <id> --summary "..."
```

Use `codex-env.ps1` from the repository root so credentials remain in `.env`.
The launcher runs the session start/end adapter for `codex` and `codex exec`.
