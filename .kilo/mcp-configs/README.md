# MCP Server Configuration

Solo-Code-Harness supports MCP (Model Context Protocol) servers for extended agent capabilities.

## Default MCP Servers (`.mcp.json`)

| Server | Purpose | API Key Required? |
|--------|---------|-------------------|
| `sequential-thinking` | Chain-of-thought reasoning | No |
| `memory` | Persistent knowledge graph | No |
| `context7` | Live documentation lookup | No |
| `playwright` | Browser E2E testing | No (needs `npx playwright install chromium`) |

## Optional Servers (`.kilo/mcp-configs/reference-servers.json`)

Additional servers that require API keys or specific setup:
- `github` — GitHub PRs, issues, repos (needs PAT)
- `supabase` — Database operations (needs project ref)
- `jira` — Issue tracking (needs API token)
- `exa-web-search` — Web search (needs API key)
- `firecrawl` — Web scraping (needs API key)
- `fal-ai` — AI generation (needs API key)
- `filesystem` — Local filesystem access

## Usage

1. Enable a server by copying its config to `.mcp.json`
2. Replace `YOUR_*_HERE` placeholders with actual values
3. Keep ≤ 8 MCPs enabled simultaneously (context window preservation)
4. Restart agent session to apply

## Disable Servers

Set env var to disable specific servers:
```bash
export ECC_DISABLED_MCPS=playwright,context7
```
