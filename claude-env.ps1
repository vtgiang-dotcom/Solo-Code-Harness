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

# Claude Code v2.1.x appends /v1/messages internally for Anthropic-compatible endpoints.
if ($env:ANTHROPIC_BASE_URL -eq "https://cc.freemodel.dev/v1/messages") {
    $env:ANTHROPIC_BASE_URL = "https://cc.freemodel.dev"
}

if (-not $env:ANTHROPIC_API_KEY) {
    Write-Error "ANTHROPIC_API_KEY is empty. Fill it in .env first."
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
