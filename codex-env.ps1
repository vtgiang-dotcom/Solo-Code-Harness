# codex-env.ps1 — Codex CLI launcher for the Solo-Code harness
#
# Why this exists: Codex CLI does NOT read .env files. It resolves its API key
# from the environment variable named by `env_key` in ~/.codex/config.toml, and
# its base URL from a static config value (Codex has no ${VAR} interpolation for
# `base_url` — verified 2026-09-14: `base_url = "${OPENAI_BASE_URL}/v1"` fails
# with "stream disconnected before completion: builder error").
#
# This launcher bridges the two: it loads OPENAI_BASE_URL / OPENAI_API_KEY from
# .env, exports the key for `env_key`, and passes the base URL through
# `-c model_providers.freemodel.base_url=...` so both really come from .env and
# there is exactly one place to rotate credentials.
#
# Usage:
#   .\codex-env.ps1                       # interactive Codex
#   .\codex-env.ps1 exec "run the tests"  # non-interactive
#   .\codex-env.ps1 --model gpt-5.6-luna  # any other Codex flag passes through
#
# Requires: ~/.codex/config.toml with a `freemodel` provider whose env_key is
# OPENAI_API_KEY (see docs; provider blocks cannot live in project config).

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

if (-not $config.ContainsKey("OPENAI_API_KEY") -or -not $config["OPENAI_API_KEY"]) {
    Write-Error "OPENAI_API_KEY is missing from $envFile."
    exit 1
}

# env_key in ~/.codex/config.toml names this variable, so it must be in the
# process environment before codex starts.
$env:OPENAI_API_KEY = $config["OPENAI_API_KEY"]

# Codex appends the endpoint path (/responses, /chat/completions) to base_url,
# and .env stores the bare host, so add the /v1 prefix here.
$baseUrl = $config["OPENAI_BASE_URL"]
if ($baseUrl) {
    $baseUrl = $baseUrl.TrimEnd("/")
    if (-not $baseUrl.EndsWith("/v1")) {
        $baseUrl = "$baseUrl/v1"
    }
}
else {
    Write-Warning "OPENAI_BASE_URL is missing from .env; using the base_url compiled into ~/.codex/config.toml."
    $baseUrl = $null
}

$codexArgs = @($args)
if ($baseUrl) {
    $codexArgs = @("-c", "model_providers.freemodel.base_url=`"$baseUrl`"") + $codexArgs
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    Write-Error "codex not found on PATH. Install with: npm install -g @openai/codex"
    exit 1
}

& codex @codexArgs
exit $LASTEXITCODE
