# opencode-env.ps1 — OpenCode CLI launcher for the Solo-Code harness
#
# Why this exists: bridges .env configuration to OpenCode runtime environment.
# It reads OPENAI_BASE_URL, OPENAI_API_KEY, and COMMANDCODE credentials from .env,
# normalizes the base URL (stripping any trailing /v1 so {env:OPENAI_BASE_URL}/v1
# in opencode config resolves cleanly), exports them into the process environment,
# and launches opencode with any pass-through arguments.
#
# Usage:
#   .\opencode-env.ps1                                # interactive OpenCode TUI
#   .\opencode-env.ps1 run "run the tests"            # non-interactive command
#   .\opencode-env.ps1 -m freemodel/gpt-5.6-terra     # specify model directly
#   .\opencode-env.ps1 --help                         # pass-through flags

$ErrorActionPreference = "Stop"

$envFile = Join-Path (Get-Location) ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "No .env found at $envFile. Run this launcher from the project root."
    exit 1
}

$config = @{}
foreach ($line in Get-Content -LiteralPath $envFile) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
        continue
    }
    $name, $value = $trimmed.Split("=", 2)
    $config[$name.Trim()] = $value.Trim()
}

# Export OpenAI / FreeModel credentials
if ($config.ContainsKey("OPENAI_API_KEY") -and $config["OPENAI_API_KEY"]) {
    $env:OPENAI_API_KEY = $config["OPENAI_API_KEY"]
    $env:FREEMODEL_API_KEY = $config["OPENAI_API_KEY"]
}

# Normalize OPENAI_BASE_URL: ensure it has no trailing /v1 or slashes
# so {env:OPENAI_BASE_URL}/v1 in opencode config resolves reliably.
if ($config.ContainsKey("OPENAI_BASE_URL") -and $config["OPENAI_BASE_URL"]) {
    $baseUrl = $config["OPENAI_BASE_URL"].Trim().TrimEnd("/")
    if ($baseUrl.EndsWith("/v1")) {
        $baseUrl = $baseUrl.Substring(0, $baseUrl.Length - 3)
    }
    $env:OPENAI_BASE_URL = $baseUrl
}

# Export CommandCode credentials if present
if ($config.ContainsKey("COMMANDCODE_API_KEY") -and $config["COMMANDCODE_API_KEY"]) {
    $env:COMMANDCODE_API_KEY = $config["COMMANDCODE_API_KEY"]
}
if ($config.ContainsKey("COMMANDCODE_BASE_URL") -and $config["COMMANDCODE_BASE_URL"]) {
    $env:COMMANDCODE_BASE_URL = $config["COMMANDCODE_BASE_URL"]
}

# Export Anthropic credentials if present
if ($config.ContainsKey("ANTHROPIC_API_KEY") -and $config["ANTHROPIC_API_KEY"]) {
    $env:ANTHROPIC_API_KEY = $config["ANTHROPIC_API_KEY"]
}
if ($config.ContainsKey("ANTHROPIC_BASE_URL") -and $config["ANTHROPIC_BASE_URL"]) {
    $env:ANTHROPIC_BASE_URL = $config["ANTHROPIC_BASE_URL"]
}

if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    Write-Error "opencode not found on PATH. Install with: npm install -g opencode-ai"
    exit 1
}

$opencodeArgs = @($args)
$exitCode = 1
try {
    & opencode @opencodeArgs
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Error $_
    $exitCode = 1
}
exit $exitCode
