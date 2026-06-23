# Session Progress Log

> Append-only. Newest session on top. The agent reads this at startup (see CLAUDE.md → State & Session Lifecycle) and updates it before stopping.

---

## 2026-06-23 — Mở rộng deploy.py: thêm scaffold mode + README + đồng bộ GitHub

**Active Feature:** feat-019 (deploy.py scaffold mode)

### What's Done

- [x] **feat-019: deploy.py scaffold mode** — Mở rộng `tools/deploy.py` từ 245 → 658 dòng với 3 chế độ:
  - `scaffold` — Tạo dự án mới từ đầu: tạo thư mục, copy toàn bộ harness (Gemini + Kilo + OpenCode), sinh README.md từ template, git init + initial commit, in hướng dẫn post-setup
  - `deploy` — Giữ nguyên backward-compatible cho dự án có sẵn
  - Auto-detect — Nếu target không tồn tại → scaffold, nếu có → deploy
  - Interactive — `python tools/deploy.py` (không args) → hỏi đáp từng bước
- [x] **README.md** — Thêm section "Scaffold & Deploy" với ví dụ đầy đủ
- [x] **feature_list.json** — Thêm feat-019
- [x] **progress.md** — Ghi lại session này

### Verification

- [x] `python tools/deploy.py --help` — Hiển thị đúng usage, epilog
- [x] `python tools/deploy.py scaffold /tmp/test --dry-run` — 329 files, git init, README
- [x] `python tools/deploy.py deploy . --engine opencode --dry-run` — 105 files
- [x] `python tools/deploy.py . --dry-run` — Auto-detect: deploy to existing dir
- [x] `python tools/deploy.py scaffold /tmp/solo-test-new --dry-run` — Auto-detect: scaffold new project
- [x] `python .github/scripts/security_scan.py tools/deploy.py` — PASS, 0 issues

### What's Next

1. Feat-008 (Memory population) — mở rộng memory với debugging tips + deployment notes
2. Feat-009 (Cross-platform init.sh) — hỗ trợ đa nền tảng
3. Feat-010 (Automated manifest sync) — garden check agent.yaml drift
4. Feat-011 (CI gate on push) — GitHub Actions workflow

### Decisions Made

- **Giữ nguyên backward compatibility**: `deploy` subcommand hoạt động y hệt như trước, không phá vỡ workflow cũ
- **Auto-detect theo tồn tại của thư mục**: Đơn giản, predict, đúng với kỳ vọng
- **README template**: Scaffold chỉ sinh README.md nếu file chưa tồn tại (không ghi đè)
- **`.gitignore` thêm vào ROOT_FILES**: Đảm bảo file .gitignore được copy trong cả scaffold lẫn deploy

---

## 2026-06-19 — Nâng cấp harness: 7 skills từ Matt Pocock (HYBRID style)

**Active Feature:** feat-012 → feat-018 (7 new/upgraded skills from skills-main)

### What's Done

- [x] **feat-012: writing-great-skills** — Created new skill (invocation types, info hierarchy, completion criteria, leading words, failure modes). Registered in `solo-code/plugin.json`, `agent.yaml`. Linked from `using-agent-skills` router.
- [x] **feat-013: codebase-design** — Created new skill (deep-module vocabulary: module/interface/depth/seam/adapter/leverage/locality). Registered in `refactor/plugin.json`. Cross-linked from `simplify-code`.
- [x] **feat-014: interview-me grilling cadence** — Added 3-discipline section (one question at a time, every question carries GUESS:, explore codebase before asking). Trimmed redundancy to fit 12KB cap (11519B).
- [x] **feat-015: systematic-debugging Phase 0** — Added "Build a feedback loop" phase before root cause investigation. Includes loop construction strategies, tightening guidance, completion checklist. Cross-linked to `improve-codebase-architecture`.
- [x] **feat-016: domain-modeling** — Created new skill (CONTEXT.md glossary maintenance). Registered in `code-quality/plugin.json`. Cross-linked from `documentation-and-adrs` + `using-agent-skills` router.
- [x] **feat-017: handoff** — Created new skill (session-handoff.md compaction). Registered in `solo-code/plugin.json`.
- [x] **feat-018: improve-codebase-architecture** — Created new skill (deepening opportunity scan, Markdown report, no HTML). Registered in `refactor/plugin.json`. Linked from `using-agent-skills` router + `systematic-debugging`.

**Cross-cutting:**
- [x] Updated handshake numbers: CLAUDE.md + AGENTS.md "38 skills" → "42 skills"
- [x] Updated README.md artifact count: 206 → 226
- [x] Trimmed interview-me from 12845B → 11519B (fits under 12288B cap)

### What's In Progress

- (none — feat-012 through feat-018 all done)

### What's Next

1. Feat-008 (Memory population) — expand with debugging tips + deployment notes.
2. Feat-009 (Cross-platform init.sh) — auto-detect platform or require parameter?
3. Feat-010 (Automated manifest sync) — garden check bắt agent.yaml drift.
4. Feat-011 (CI gate on push) — cần tạo `.github/workflows/ci.yml`.

### Decisions Made

- **HYBRID style**: Matt Pocock conciseness + harness frontmatter/gates + single-file (no references/ subfolder). Target 4-6KB per skill.
- **Phase 0 before Phase 1**: In systematic-debugging, feedback loop construction is the most critical skill — moved before root cause investigation.
- **No HTML report**: improve-codebase-architecture uses Markdown output instead of HTML/Tailwind/Mermaid CDN.

### Evidence of Completion

- [x] `python tools/generate_harness.py --harness all` — 42 skills, 12 agents, 226 artifacts
- [x] `python tools/garden.py` — 0 errors, 0 warnings
- [x] `python .github/scripts/checklist.py .` — 4/4 PASS
- [x] `python .github/scripts/security_scan.py .` — PASS
- [x] `ruff check .` — All checks passed

---



**Active Feature:** feat-007 (Config debt cleanup) + A1-A3 (forward scope, handoff fill, memory pop)

### What's Done

- [x] **F1**: Hợp nhất ruff extend-exclude, xóa 11 stale entries. `.ruff.toml` chỉ còn `.venv` + `.kilo/node_modules`.
- [x] **F2**: Xóa toàn bộ per-file E501 ignores (dư thừa), thêm `ignore = ["E501"]` vào `[lint]`. Per-file chỉ giữ SIM114 + I001.
- [x] **F4**: Sửa self-verification handshake: AGENTS.md "10 skills"→"38 skills, 12 agents", CLAUDE.md "11 skills"→"38 skills, 12 agents".
- [x] **F5**: Makefile `PY` fallback cascade `python3 → python → py` (đồng bộ với init.sh).
- [x] **F3**: agent.yaml cập nhật: 9→38 skills, 10→12 agents (alphabetical).
- [x] **A4**: Thêm `learn-harness-engineering-main/` vào `.gitignore`.
- [x] **F6**: Xóa stale entries trong `.gitleaks.toml` (ECC-main, agents-main) và `.gitignore` (toàn bộ section "Reference projects").
- [x] **A5**: Viết lại `pyproject.toml` — `[project]` metadata + `[project.scripts]`, xóa toàn bộ `[tool.ruff]` (single source of truth = `.ruff.toml`).
- [x] **A1**: Thêm 5 forward-scope features (feat-007 → feat-011) vào `feature_list.json`.
- [x] **A2**: Fill `session-handoff.md` với dữ liệu thực tế (46 dòng → full content).
- [x] **A3**: Populate `.claude/memory/MEMORY.md` và `.kilo/memory/MEMORY.md` với Tech Stack + 6 gotchas mỗi file.

### What's In Progress

- (none — feat-007 marked done)

### What's Next

1. Feat-008 (Memory population) — memory đã có tech stack + gotchas cơ bản, có thể mở rộng thêm debugging tips + deployment notes.
2. Feat-009 (Cross-platform init.sh) — cần quyết định thiết kế: auto-detect platform hay require parameter?
3. Feat-010 (Automated manifest sync) — garden check bắt agent.yaml drift.
4. Feat-011 (CI gate on push) — cần tạo `.github/workflows/ci.yml`, yêu cầu explicit user approval.

### Decisions Made

- **ruff config single source**: `.ruff.toml` là single source of truth. `pyproject.toml` không còn `[tool.ruff]`.
- **E501**: Global ignore trong `[lint]`, không per-file. Đơn giản, nhất quán.
- **agent.yaml alphabetical**: Skills và agents sắp xếp alphabetically để dễ diff.
- **Forward scope**: 5 features seeded với các gap thực tế đã xác định từ audit.

### Evidence of Completion

- [x] `ruff check .` — All checks passed
- [x] `python .github/scripts/security_scan.py .` — 473 files, 0 issues
- [x] `python tools/garden.py` — 0 errors, 0 warnings
- [x] `python tools/validate_schemas.py` — All schema validations passed
- [x] `python .github/scripts/checklist.py .` — 4/4 PASS (Secret Scan, Ruff Linter, Harness Eval, Guard Tests)
- [x] `bash init.sh` — Bootstrap OK, feat-007 in-progress, 6/11 done
- [x] `bash init.sh --verify` — All checks PASSED (2 skip from Git Bash: ruff + guard tests not on PATH)

---

## 2026-06-18 — Add State + Lifecycle subsystems

**Active Feature:** feat-004 / feat-005 / feat-006 (State tracking, Session lifecycle, Definition of Done)

### What's Done

- [x] Audited `learn-harness-engineering` course against the harness; confirmed State + Lifecycle are the real gaps (no feature_list, no progress log, no init.sh).
- [x] Deferred (not rejected on principle) the course's "slim AGENTS.md to a 40-line router" advice. Correction: documented design intent forbids *shortening/removing* rules, which progressive disclosure does NOT do (it relocates rules into linked docs, preserving them). The earlier "violates design intent" framing was an overclaim. Real grounds for deferring: Surgical Changes + don't stack a structural refactor on a 6-file change. Revisit later as its own scoped change with a before/after eval.
- [x] Created `.claude/state/feature_list.json` + schema (machine-readable scope).
- [x] Created `.claude/state/progress.md` (this file) and `session-handoff.md` template.

- [x] Created `init.sh` wrapper (health check + state; `--verify` runs full gates / checklist.py fallback).
- [x] Added "State & Session Lifecycle" + "Definition of Done" sections to `.claude/CLAUDE.md` (additive only).
- [x] Excluded vendored `learn-harness-engineering-main/` from ruff (matches existing `*-main` exclusions).
- [x] Ran gates: ruff clean, schemas pass, integration 220/0, eval 49/49 (avg 93), security 0, garden 0 errors.

### What's In Progress

- (none — feat-004/005/006 all done)

### What's Next

1. Done: `pytest` installed; all 7 gates green. NOTE: `pytest` is test-only and lives in `.venv` (not declared in `pyproject.toml`, which is stdlib-only by design). A fresh environment needs `pip install pytest` before the `test_harness.py` gate runs.
2. Future development features get appended below feat-006.

### Decisions Made

- **State files live in `.claude/state/`**, parallel to `.claude/memory/`. Keeps root uncluttered and discoverable by Claude Code.
  - Alternatives considered: root-level (course default) — rejected to avoid root clutter; `.kilo/state/` — rejected, that namespace is Kilo-specific.
- **No rule was shortened.** Only additive sections. Reason: design intent forbids shortening rules for DeepSeek.

### Evidence of Completion

- [x] `python .github/scripts/security_scan.py .` — 1924 files, no issues
- [x] `ruff check .` — All checks passed
- [x] `python tools/garden.py` — 0 errors, 0 warnings
- [x] `python tools/test_integration.py` — 220 passed, 0 failed
- [x] `python tools/eval.py --min-score 60` — 49/49 components, avg 93
- [x] `pytest tools/test_harness.py` — 33 passed (pytest 9.1.0 installed into .venv with user approval)

### Notes for Next Session

The new state files are the source of truth for what is and isn't finished. Read `feature_list.json` first, pick ONE `in-progress` feature, finish it, then mark `done` with evidence.
