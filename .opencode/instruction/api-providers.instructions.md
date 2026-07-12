# API Providers — DeepSeek & CommandCode

> Auto-loaded when the agent needs to call external LLM APIs or switch between model providers.

## Overview

This project supports two external LLM API providers beyond the primary Copilot model:

| Provider | API Type | Base URL Env | Key Env |
|----------|----------|-------------|---------|
| **DeepSeek** | OpenAI-compatible | `DEEPSEEK_BASE_URL` | `DEEPSEEK_API_KEY` |
| **CommandCode** | OpenAI-compatible proxy | `COMMANDCODE_BASE_URL` | `COMMANDCODE_API_KEY` |

Both providers expose OpenAI-compatible `/v1/chat/completions` endpoints. CommandCode proxies multiple models (Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step) through a single API key.

## Environment Configuration

Set these environment variables before use. Never hardcode keys in source files.

```powershell
# DeepSeek
[Environment]::SetEnvironmentVariable("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1", "User")
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-deepseek-key", "User")

# CommandCode
[Environment]::SetEnvironmentVariable("COMMANDCODE_BASE_URL", "https://api.commandcode.ai/v1", "User")
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "cc-your-commandcode-key", "User")
```

After setting, restart VS Code for Copilot to pick up the new variables.

## Model Selection

### Available Models via CommandCode

| Model ID | Provider | Best For |
|----------|----------|----------|
| `claude-sonnet-4-20250514` | Anthropic | Complex reasoning, architecture, code review |
| `claude-3.5-sonnet` | Anthropic | General coding, debugging |
| `gpt-4o` | OpenAI | Broad knowledge, explanations |
| `gpt-4o-mini` | OpenAI | Fast completions, simple tasks |
| `deepseek-chat` | DeepSeek | Cost-effective reasoning, refactoring |
| `deepseek-reasoner` | DeepSeek | Math, complex algorithms |
| `gemini-2.5-pro` | Google | Large context analysis |
| `qwen-max` | Alibaba | Chinese/English bilingual tasks |
| `kimi-latest` | Moonshot | Long-context code review |

### Available Models via DeepSeek Direct

| Model ID | Best For |
|----------|----------|
| `deepseek-chat` | General purpose, 128K context |
| `deepseek-reasoner` | Deep reasoning, chain-of-thought |

## API Usage Patterns

### Calling DeepSeek API (OpenAI-compatible)

```python
import os
import httpx

async def call_deepseek(prompt: str, system: str = "", model: str = "deepseek-chat") -> str:
    """Call DeepSeek chat completions API."""
    base_url = os.environ["DEEPSEEK_BASE_URL"]
    api_key = os.environ["DEEPSEEK_API_KEY"]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

### Calling CommandCode API (OpenAI-compatible proxy)

```python
import os
import httpx

async def call_commandcode(
    prompt: str,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Call CommandCode API — proxies multiple model providers."""
    base_url = os.environ["COMMANDCODE_BASE_URL"]
    api_key = os.environ["COMMANDCODE_API_KEY"]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

## Copilot Chat Model Switching

When using Copilot Chat in VS Code, switch the active model via:
- **Command Palette** (`Ctrl+Shift+P`) → `GitHub Copilot: Switch Model`
- Or click the model name in the Copilot Chat header

Configured models are defined in `.vscode/settings.json` under `github.copilot.chat.models`.

## When to Use Which Provider

| Scenario | Provider | Model |
|----------|----------|-------|
| **Architecture design** | CommandCode | `claude-sonnet-4-20250514` |
| **Code review** | CommandCode | `claude-sonnet-4-20250514` or `gpt-4o` |
| **Refactoring** | DeepSeek | `deepseek-chat` |
| **Test generation** | CommandCode | `gpt-4o` |
| **Complex algorithms / math** | DeepSeek | `deepseek-reasoner` |
| **Quick edits / completions** | DeepSeek | `deepseek-chat` |
| **Cost-sensitive batch work** | DeepSeek | `deepseek-chat` |
| **Long-context analysis** | CommandCode | `gemini-2.5-pro` or `kimi-latest` |

## Error Handling

```python
import httpx

async def safe_api_call(fn, *args, **kwargs):
    """Wrapper with retry and error handling."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited — exponential backoff
                await asyncio.sleep(2 ** attempt)
                continue
            if e.response.status_code == 401:
                raise RuntimeError("Invalid API key — check environment variables")
            if e.response.status_code >= 500:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                continue
            raise RuntimeError("API call timed out after retries")
    raise RuntimeError("API call failed after max retries")
```

## Security Rules

- **Never hardcode API keys** — always use environment variables
- **Never log API responses** that contain generated code or sensitive data
- **Validate response structure** before accessing `choices[0].message.content`
- **Set reasonable timeouts** — 120s for chat completions, 30s for embeddings
- **Rotate keys periodically** — CommandCode keys expire; regenerate via dashboard
