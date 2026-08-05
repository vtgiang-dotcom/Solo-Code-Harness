$claudeArgs = @($args)

# --bare is OPT-IN. Plain `./claude-env.ps1` runs the FULL harness.
#
# Per `claude --help`, --bare skips hooks, CLAUDE.md auto-discovery, LSP,
# auto-memory and MCP config. That is the entire enforcement layer this repo
# exists to provide: guard.py, memory_gate, quality_gate, security_post and
# both session hooks. Defaulting to it means shipping a harness that is
# installed but not in force.
#
# --bare was once the default as a workaround for third-party gateways
# failing auth in full mode. That is obsolete -- full mode authenticates
# fine against the FreeModel gateway (verified live, and the apiKeyHelper
# conflict detection below handles the real cause). --bare stays available
# for a gateway regression, but it WARNS: hooks-off must never be silent.
$useBare = $false
$normalizedArgs = New-Object System.Collections.Generic.List[string]
foreach ($arg in $claudeArgs) {
    # Accepted as a no-op so existing callers and docs keep working.
    # Deliberately NOT `continue`-d into oblivion: dropping the only arg
    # used to empty the list and fall through to a hardcoded --bare path.
    if ($arg -eq "--full-mode") {
        $useBare = $false
        continue
    }
    if ($arg -eq "--bare") {
        $useBare = $true
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

# A key can be present, valid and still unusable: Claude Code records a "no"
# from its custom-key prompt in ~/.claude.json and then fails interactive
# sessions with "Not logged in". -p and --bare ignore that list, so nothing
# else in the harness notices. Warn here, where the key is already loaded --
# do not block, because the key may be fine for the mode being launched.
$approver = Join-Path (Get-Location) "tools\approve_api_key.py"
if ((Test-Path $approver) -and $env:ANTHROPIC_API_KEY) {
    & python $approver --check
}

if ($useBare) {
    # Loud on purpose: bare mode disables guard.py and every other hook, so
    # the destructive-command / secret-leak gates are NOT active in this
    # session. Never let that state be silent.
    Write-Warning "--bare: hooks and CLAUDE.md auto-discovery are DISABLED for this session (guard/memory/quality/security gates will NOT run)."
    if ($normalizedArgs -notcontains "--bare") {
        [void]$normalizedArgs.Insert(0, "--bare")
    }
    # --bare skips CLAUDE.md auto-discovery; --add-dir . restores it.
    # Hooks are NOT recoverable this way -- only full mode runs them.
    if ($normalizedArgs -notcontains "--add-dir") {
        [void]$normalizedArgs.Add("--add-dir")
        [void]$normalizedArgs.Add(".")
    }
}

# Single exec path. There is deliberately no separate no-arg branch: the
# original bug was a hardcoded `& claude --bare` fallback that fired whenever
# the arg list ended up empty -- including `--full-mode`, whose whole purpose
# was to avoid bare. PowerShell splats an empty list as no args, so one line
# covers both cases and cannot drift from the logic above.
& claude @normalizedArgs
