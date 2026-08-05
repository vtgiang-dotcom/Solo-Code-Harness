# Solo-Code jcode Launcher
# Cost-saving DeepSeek worker engine, synced with .env

$ErrorActionPreference = "Stop"

# deepseek-v4-pro is the only supported worker model. The cheaper
# deepseek-v4-flash tier was dropped 2026-07-25: unreliable in practice,
# with the token savings lost to re-prompting and rework.
$DefaultModel = "deepseek/deepseek-v4-pro"

# ── Banner ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║    Solo-Code jcode Launcher v1.0        ║" -ForegroundColor Cyan
Write-Host "  ║   Cost-saving DeepSeek worker engine     ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Sync CommandCode API Key ───────────────────────────────────────
$envFile = Join-Path $PSScriptRoot ".env"
$jcodeConfigDir = "$env:USERPROFILE\AppData\Roaming\jcode"
$jcodeProviderFile = Join-Path $jcodeConfigDir "provider-commandcode.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line.Split('=', 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                if ($key -eq "COMMANDCODE_API_KEY" -and $value) {
                    # Ensure config directory exists
                    if (-not (Test-Path $jcodeConfigDir)) {
                        New-Item -ItemType Directory -Path $jcodeConfigDir -Force | Out-Null
                    }
                    Set-Content -Path $jcodeProviderFile -Value "JCODE_PROVIDER_COMMANDCODE_API_KEY=$value" -NoNewline
                    Write-Host "  CommandCode key: synced" -ForegroundColor Green
                }
            }
        }
    }
}

# ── Retired-model drift check ───────────────────────────────────────
# deepseek-v4-flash was retired 2026-07-25 (unreliable; savings lost to
# re-prompting). The launcher and tools/jcode_delegate.py always pass
# --model explicitly, so they are safe -- but ~/.jcode/config.toml is a
# machine-global file this repo does not own, and if it still pins the
# retired tier then ANY `jcode run` that omits --model silently executes on
# it. Verified: with the model omitted, jcode reported
# `model: deepseek/deepseek-v4-flash`.
#
# Warn rather than rewrite: config.toml holds unrelated user settings
# (auth, agents, failover) and silently editing a global file the user owns
# is worse than telling them precisely what to change.
$jcodeConfigToml = Join-Path $env:USERPROFILE ".jcode\config.toml"
if (Test-Path $jcodeConfigToml) {
    $tomlText = Get-Content $jcodeConfigToml -Raw
    if ($tomlText -match 'deepseek-v4-flash') {
        Write-Warning "~/.jcode/config.toml still pins the RETIRED deepseek-v4-flash tier."
        Write-Warning "  Any 'jcode run' without an explicit --model will use it."
        Write-Warning "  Fix: set default_model = `"$DefaultModel`" in [provider] and [providers.commandcode],"
        Write-Warning "       and the [[providers.commandcode.models]] id. One-liner (backs up first):"
        Write-Warning "       Copy-Item `"`$env:USERPROFILE\.jcode\config.toml`" `"`$env:USERPROFILE\.jcode\config.toml.bak`"; (Get-Content `"`$env:USERPROFILE\.jcode\config.toml`") -replace 'deepseek/deepseek-v4-flash','$DefaultModel' | Set-Content `"`$env:USERPROFILE\.jcode\config.toml`""
    }
}

# ── Model ───────────────────────────────────────────────────────────
# $args[0] used to be taken as the model unconditionally, so
# `./jcode.ps1 "fix the login bug"` sent --model "fix the login bug" to the
# gateway and the prompt was consumed as a model name (the request then
# failed on the provider side, or silently ran the wrong model).
# Only treat argument 0 as a model if it actually looks like one
# (provider/name) -- otherwise it is the start of the prompt.
$rest = @($args)
$model = $DefaultModel
if ($rest.Count -gt 0 -and $rest[0] -match '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$') {
    $model = $rest[0]
    $rest = @($rest | Select-Object -Skip 1)
}

Write-Host "  Model: $model" -ForegroundColor Yellow
Write-Host ""

# ── Launch ──────────────────────────────────────────────────────────
Write-Host "  Launching jcode..." -ForegroundColor Green
Write-Host ""

if ($rest.Count -gt 0) {
    & jcode run --provider-profile commandcode --model $model @rest
} else {
    & jcode --provider-profile commandcode --model $model
}
