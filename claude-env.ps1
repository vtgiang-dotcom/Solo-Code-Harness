$claudeArgs = @($args)

# Interactive mode with some third-party Anthropic-compatible gateways can fail auth
# in full mode. Default to --bare unless explicitly overridden.
$useBare = $true
$normalizedArgs = New-Object System.Collections.Generic.List[string]
foreach ($arg in $claudeArgs) {
    if ($arg -eq "--full-mode") {
        $useBare = $false
        continue
    }
    if ($arg -eq "--bare") {
        $useBare = $false
    }
    [void]$normalizedArgs.Add($arg)
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

# Claude Code appends /v1/messages internally.
# Strip it if the user accidentally pasted the full endpoint.
$freemodelDomains = @("api.freemodel.dev", "cc.freemodel.dev", "api-cc.freemodel.dev", "cc-t2.freemodel.dev")
foreach ($domain in $freemodelDomains) {
    $expected = "https://${domain}/v1/messages"
    if ($env:ANTHROPIC_BASE_URL -eq $expected) {
        $env:ANTHROPIC_BASE_URL = "https://${domain}"
        break
    }
}

# If apiKeyHelper is configured in ~/.claude/settings.json, unset ANTHROPIC_API_KEY
# to avoid the "Both apiKeyHelper and ANTHROPIC_API_KEY set" warning.
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

if (-not $hasApiKeyHelper -and -not $env:ANTHROPIC_API_KEY) {
    Write-Error "ANTHROPIC_API_KEY is empty. Fill it in .env first (or configure apiKeyHelper in ~/.claude/settings.json)."
    exit 1
}

if (-not $env:ANTHROPIC_BASE_URL) {
    Write-Error "ANTHROPIC_BASE_URL is empty. Fill it in .env first."
    exit 1
}

if ($useBare) {
    [void]$normalizedArgs.Insert(0, "--bare")
}

if ($normalizedArgs.Count -gt 0) {
    & claude @normalizedArgs
}
else {
    & claude --bare
}
