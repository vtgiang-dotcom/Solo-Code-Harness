# Solo-Code jcode Launcher
# Cost-saving DeepSeek worker engine, synced with .env

$ErrorActionPreference = "Stop"

# deepseek-v4-pro is the only supported worker model. The cheaper
# deepseek-v4-flash tier was dropped 2026-07-25: unreliable in practice,
# with the token savings lost to re-prompting and rework.
$DefaultModel = "deepseek/deepseek-v4-pro"
$FreeModelWorkerModels = @(
    "gpt-5.6-sol",
    "gpt-5.6-terra"
)

# -- Banner ----------------------------------------------------------
Write-Host ""
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |    Solo-Code jcode Launcher v1.0        |" -ForegroundColor Cyan
Write-Host "  |   DeepSeek and multi-provider workers    |" -ForegroundColor Cyan
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# ── Sync CommandCode API Key ───────────────────────────────────────
$envFile = Join-Path $PSScriptRoot ".env"
$jcodeConfigDir = "$env:USERPROFILE\AppData\Roaming\jcode"
$jcodeProviderFile = Join-Path $jcodeConfigDir "provider-commandcode.env"
$freeModelProviderFile = Join-Path $jcodeConfigDir "provider-freemodel-openai.env"
$openAiApiKey = $null
$openAiBaseUrl = $null

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
                if ($key -eq "OPENAI_API_KEY" -and $value) {
                    $openAiApiKey = $value
                }
                if ($key -eq "OPENAI_BASE_URL" -and $value) {
                    $openAiBaseUrl = $value.TrimEnd("/")
                    $openAiBaseUrl = $openAiBaseUrl -replace '/v1/(chat/completions|responses)$', ''
                    $openAiBaseUrl = $openAiBaseUrl -replace '/v1$', ''
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
if ($rest.Count -gt 0 -and (($rest[0] -match '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$') -or ($FreeModelWorkerModels -contains $rest[0]))) {
    $model = $rest[0].Replace("openai/", "")
    $rest = @($rest | Select-Object -Skip 1)
}

$useCommandCode = ($model -eq $DefaultModel)
$useFreeModel = ($FreeModelWorkerModels -contains $model)

if (-not $useCommandCode -and -not $useFreeModel) {
    Write-Error "Unsupported worker model '$model'. CommandCode is restricted to $DefaultModel; FreeModel worker choices: $($FreeModelWorkerModels -join ', ')."
    exit 1
}

if ($useFreeModel) {
    if (-not $openAiApiKey -or -not $openAiBaseUrl) {
        Write-Error "FreeModel workers require OPENAI_API_KEY and OPENAI_BASE_URL in .env."
        exit 1
    }

    if (-not (Test-Path $jcodeConfigDir)) {
        New-Item -ItemType Directory -Path $jcodeConfigDir -Force | Out-Null
    }

    Set-Content -Path $freeModelProviderFile -Value "JCODE_PROVIDER_FREEMODEL_OPENAI_API_KEY=$openAiApiKey" -NoNewline
    $env:JCODE_PROVIDER_FREEMODEL_OPENAI_API_KEY = $openAiApiKey

    # jcode openai-api uses Responses API and currently sends
    # prompt_cache_retention, which FreeModel rejects. The custom
    # openai-compatible profile uses the stable Chat Completions route.
    $providerBaseUrl = "$openAiBaseUrl/v1"
    & jcode provider add freemodel-openai `
        --base-url $providerBaseUrl `
        --model $model `
        --api-key-env JCODE_PROVIDER_FREEMODEL_OPENAI_API_KEY `
        --env-file "provider-freemodel-openai.env" `
        --auth bearer `
        --overwrite `
        --quiet
}

Write-Host "  Model: $model" -ForegroundColor Yellow
Write-Host ""

# ── Launch ──────────────────────────────────────────────────────────
Write-Host "  Launching jcode..." -ForegroundColor Green
Write-Host ""

if ($useCommandCode -and $rest.Count -gt 0) {
    & jcode run --provider-profile commandcode --model $model @rest
} elseif ($useCommandCode) {
    & jcode --provider-profile commandcode --model $model
} elseif ($rest.Count -gt 0) {
    & jcode run --provider-profile freemodel-openai --model $model @rest
} else {
    & jcode --provider-profile freemodel-openai --model $model
}
