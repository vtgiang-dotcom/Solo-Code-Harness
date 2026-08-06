$claudeArgs = @($args)

# Launcher profiles:
# - gateway (default): FreeModel/3rd-party gateway auth via --bare.
# - native: native Claude Code mode; prefers API key if present, otherwise lets
#   Claude Code use its normal auth flow.
# - kilo: same runtime behavior as native, but keeps a distinct profile name so
#   IDE integrations can target it explicitly without changing Claude/jcode.
#
# Why gateway defaults to --bare:
# third-party Anthropic-compatible gateways do not support Claude OAuth. In
# full mode Claude Code prompts for login instead of using ANTHROPIC_API_KEY.
# In bare mode hooks/CLAUDE.md auto-discovery are skipped, so this launcher
# restores CLAUDE.md discovery with --add-dir . and warns loudly about the
# reduced guardrails.

$profile = "gateway"
$useBare = $true
$normalizedArgs = New-Object System.Collections.Generic.List[string]

for ($i = 0; $i -lt $claudeArgs.Count; $i++) {
    $arg = $claudeArgs[$i]

    if ($arg -eq "--profile") {
        if (($i + 1) -ge $claudeArgs.Count) {
            Write-Error "Missing value for --profile. Use: gateway, native, or kilo."
            exit 1
        }
        $candidate = $claudeArgs[$i + 1].ToLowerInvariant()
        if (@("gateway", "native", "kilo") -notcontains $candidate) {
            Write-Error "Invalid --profile '$candidate'. Use: gateway, native, or kilo."
            exit 1
        }
        $profile = $candidate
        $i++
        continue
    }

    if ($arg -like "--profile=*") {
        $candidate = $arg.Substring(10).ToLowerInvariant()
        if (@("gateway", "native", "kilo") -notcontains $candidate) {
            Write-Error "Invalid --profile '$candidate'. Use: gateway, native, or kilo."
            exit 1
        }
        $profile = $candidate
        continue
    }

    if ($arg -eq "--full-mode") {
        $useBare = $false
        continue
    }

    if ($arg -eq "--bare") {
        $useBare = $false
    }

    [void]$normalizedArgs.Add($arg)
}

if ($profile -eq "gateway") {
    $useBare = $true
}
else {
    $useBare = $false
}

$envFile = Join-Path (Get-Location) ".env"
if (-not (Test-Path $envFile)) {
    Write-Error "Missing .env in current directory: $envFile"
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line.Split("=", 2)
    if ($parts.Length -ne 2) {
        return
    }

    $key = $parts[0].Trim()
    $value = $parts[1].Trim()

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    [Environment]::SetEnvironmentVariable($key, $value, "Process")
}

$freemodelDomains = @("api.freemodel.dev", "cc.freemodel.dev", "api-cc.freemodel.dev", "cc-t2.freemodel.dev")
foreach ($domain in $freemodelDomains) {
    $expected = "https://${domain}/v1/messages"
    if ($env:ANTHROPIC_BASE_URL -eq $expected) {
        $env:ANTHROPIC_BASE_URL = "https://${domain}"
        break
    }
}

$settingsPath = Join-Path $HOME ".claude\settings.json"
$settings = $null
if (Test-Path $settingsPath) {
    try { $settings = Get-Content -Raw $settingsPath | ConvertFrom-Json } catch { }
}
$hasApiKeyHelper = ($settings -and $settings.apiKeyHelper)
if ($hasApiKeyHelper -and $env:ANTHROPIC_API_KEY) {
    Write-Warning "apiKeyHelper detected -- unsetting ANTHROPIC_API_KEY to avoid auth conflict."
    Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
}

if (($profile -eq "gateway") -and (-not $hasApiKeyHelper) -and (-not $env:ANTHROPIC_API_KEY)) {
    Write-Error "ANTHROPIC_API_KEY is empty. Fill it in .env first (or configure apiKeyHelper in ~/.claude/settings.json)."
    exit 1
}

if (($profile -eq "gateway") -and (-not $env:ANTHROPIC_BASE_URL)) {
    Write-Error "ANTHROPIC_BASE_URL is empty. Fill it in .env first."
    exit 1
}

$approver = Join-Path (Get-Location) "tools\approve_api_key.py"
if ((Test-Path $approver) -and $env:ANTHROPIC_API_KEY) {
    & python $approver --check
}

if ($profile -eq "gateway") {
    Write-Warning "Profile gateway: running Claude Code with --bare for FreeModel/third-party auth. Hooks, auto-memory, and CLAUDE.md auto-discovery are reduced; this launcher restores CLAUDE.md via --add-dir . only."
}
elseif ($profile -eq "native") {
    if ($env:ANTHROPIC_API_KEY -or $hasApiKeyHelper) {
        Write-Host "Profile native: preferring API-based auth in full mode."
    }
    else {
        Write-Warning "Profile native: no API key/apiKeyHelper detected. Claude Code may prompt for native login."
    }
}
elseif ($profile -eq "kilo") {
    Write-Host "Profile kilo: full mode selected for IDE-integrated Kilo workflows."
}

if ($useBare) {
    if ($normalizedArgs -notcontains "--bare") {
        [void]$normalizedArgs.Insert(0, "--bare")
    }
    if ($normalizedArgs -notcontains "--add-dir") {
        [void]$normalizedArgs.Add("--add-dir")
        [void]$normalizedArgs.Add(".")
    }
}

& claude @normalizedArgs
