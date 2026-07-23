# Solo-Code jcode Launcher
# Cost-saving DeepSeek worker engine, synced with .env

$ErrorActionPreference = "Stop"

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

# ── Model ───────────────────────────────────────────────────────────
$model = if ($args[0]) { $args[0] } else { "deepseek/deepseek-v4-flash" }
Write-Host "  Model: $model" -ForegroundColor Yellow
Write-Host ""

# ── Launch ──────────────────────────────────────────────────────────
Write-Host "  Launching jcode..." -ForegroundColor Green
Write-Host ""

if ($args.Length -gt 1) {
    $remaining = $args[1..($args.Length - 1)]
    & jcode run --provider-profile commandcode --model $model $remaining
} else {
    & jcode --provider-profile commandcode --model $model
}
