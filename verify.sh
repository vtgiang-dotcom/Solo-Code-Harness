#!/usr/bin/env bash
# verify.sh — Solo-Code-Harness Verification (Claude Code)
set -u

pass=0
fail=0
skip=0
ok()   { echo "  PASS  $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail+1)); }
warn() { echo "  SKIP  $1 (not available)"; skip=$((skip+1)); }

check_kw() {
  if [ -f "$1" ] && grep -qi "$2" "$1"; then ok "$3"; else bad "$3 (thieu '$2' trong $1)"; fi
}

is_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

TEMP_DIR="${TMPDIR:-${TEMP:-/tmp}}"
mkdir -p "$TEMP_DIR" 2>/dev/null || true

echo "=== Solo-Code-Harness Verification (Claude Code) ==="
if is_wsl; then echo "  (WSL detected — .exe-native tests will SKIP)" ; fi
echo

# ---------- STRUCTURE ----------
echo "[STRUCTURE]"
for d in .claude .github .vscode; do
  [ -d "$d" ] && ok "thu muc $d/ ton tai" || bad "thieu thu muc $d/"
done
for f in .claude/settings.json .claude/CLAUDE.md .mcp.json; do
  [ -f "$f" ] && ok "$f ton tai" || bad "thieu file $f"
done
echo

# ---------- TESTS ----------
echo "[TESTS]"
if is_wsl; then
  warn "guard.test.js (chay tu PowerShell)"
  warn "ruff check (chay 'ruff check .' tu PowerShell)"
else
  GUARD_LOG="$TEMP_DIR/guard.log"
  if node .github/hooks/scripts/guard.test.js >"$GUARD_LOG" 2>&1; then
    grep -q "29/29 passed" "$GUARD_LOG" && ok "guard.test.js  29/29" || bad "guard.test.js khong du 29/29"
  else
    bad "guard.test.js loi khi chay"
  fi
  if ruff check . >"$TEMP_DIR/ruff.log" 2>&1; then ok "ruff check  no errors"; else bad "ruff check co loi"; fi
fi
echo

# ---------- SECURITY ----------
echo "[SECURITY]"
if is_wsl; then
  warn "security_scan (chay tu PowerShell)"
  warn "gitleaks (chay tu PowerShell)"
else
  if python .github/scripts/security_scan.py . >"$TEMP_DIR/sec.log" 2>&1; then
    ok "security_scan  clean"
  else
    bad "security_scan co van de"
  fi
  if command -v gitleaks >/dev/null 2>&1; then
    if gitleaks dir . --no-banner -c .gitleaks.toml >"$TEMP_DIR/gl.log" 2>&1; then
      ok "gitleaks  no leaks"
    else
      bad "gitleaks tim thay leaks"
    fi
  else
    warn "gitleaks (khong co trong PATH)"
  fi
fi
echo

# ---------- RULEBOOK ----------
echo "[RULEBOOK]"
CL=.claude/CLAUDE.md
[ -f "$CL" ] && ok "CLAUDE.md ton tai" || bad "thieu CLAUDE.md"
check_kw "$CL" "destructive" "CLAUDE.md: destructive guard"
check_kw "$CL" "socratic"    "CLAUDE.md: Socratic Gate"
check_kw "$CL" "read"        "CLAUDE.md: read before edit"
check_kw "$CL" "plan"        "CLAUDE.md: plan before implement"
check_kw "$CL" "commit"      "CLAUDE.md: commit convention"
check_kw "$CL" "DeepSeek"    "CLAUDE.md: Model Selection"
echo

# ---------- SKILLS ----------
echo "[SKILLS]"
for sk in code-review-expert brainstorming systematic-debugging testing-patterns file-editor-pro git-workflow-master api-patterns permission-guard solo-code-harness block-no-verify; do
  f=".claude/skills/$sk.md"
  [ -f "$f" ] && ok "skill: $sk" || bad "thieu skill: $sk"
done
echo

# ---------- GARDEN ----------
echo "[GARDEN]"
PY=""
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
fi
if [ -n "$PY" ] && ! is_wsl; then
  if $PY tools/garden.py >"$TEMP_DIR/garden.log" 2>&1; then ok "garden  clean"; else bad "garden co drift"; fi
  if $PY -m pytest tools/test_harness.py -q >"$TEMP_DIR/harness.log" 2>&1; then ok "harness tests  pass"; else bad "harness tests fail"; fi
  if $PY tools/test_integration.py >"$TEMP_DIR/integration.log" 2>&1; then ok "integration tests  pass"; else bad "integration tests fail"; fi
else
  warn "garden + tests (chay tu PowerShell)"
fi
echo

# ---------- BOUNDARY ----------
echo "[BOUNDARY]"
VIOLATIONS=0
for f in Dockerfile docker-compose.yml docker-compose.yaml requirements.txt package.json Cargo.toml go.mod; do
  [ -f "$f" ] && { bad "Root chua $f (infrastructure)"; VIOLATIONS=$((VIOLATIONS+1)); }
done
if [ "$VIOLATIONS" -eq 0 ]; then
  ok "boundary  clean"
else
  bad "boundary  $VIOLATIONS vi pham"
fi
echo

# ---------- TOTAL ----------
echo "--------------------------------------"
echo "KET QUA: $pass PASS / $((pass+fail)) checked ($skip skipped)"
[ "$fail" -eq 0 ] && exit 0 || exit 1
