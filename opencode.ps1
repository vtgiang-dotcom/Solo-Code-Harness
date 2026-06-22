# Solo-Code OpenCode Launcher
# Sets experimental features, shows banner, launches OpenCode with DeepSeek

$ErrorActionPreference = "Stop"

# ── Banner ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     Solo-Code OpenCode Launcher v1.0     ║" -ForegroundColor Cyan
Write-Host "  ║   Harness: 44 skills, 14 agents, v2.5    ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Experimental Features ───────────────────────────────────────────
Write-Host "  Enabling experimental features:" -ForegroundColor Green
$env:OPENCODE_EXPERIMENTAL = "true"
Write-Host "    - LSP tool (go-to-def, find-refs)" -ForegroundColor Gray
Write-Host "    - Plan mode (multi-agent workflow)" -ForegroundColor Gray
Write-Host "    - Background subagents" -ForegroundColor Gray
Write-Host "    - Event system" -ForegroundColor Gray
Write-Host ""

# ── Model ───────────────────────────────────────────────────────────
$model = if ($args[0]) { $args[0] } else { "deepseek/deepseek-v4-pro" }
Write-Host "  Model: $model" -ForegroundColor Yellow
Write-Host "  Guard plugin: v2.5 (33 destructive + 15 secret patterns)" -ForegroundColor Gray
Write-Host "  State tracking: active (.opencode/state/)" -ForegroundColor Gray
Write-Host ""

# ── Launch ──────────────────────────────────────────────────────────
Write-Host "  Launching OpenCode..." -ForegroundColor Green
Write-Host ""

& opencode --model $model $args[1..($args.Length - 1)]
