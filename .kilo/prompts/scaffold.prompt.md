---
mode: ask
description: Start a new project with proper structure, configuration, and best practices for the selected tech stack
triggers: new project, create project, scaffold, init, start project, bootstrap
---

# Scaffold New Project

Create a new project with best-practice defaults, proper configuration, and clean structure.

## Decision Tree

```
User wants to start a project → Which stack?
    ├─ Python API → FastAPI + Pydantic + uv/pip
    ├─ React SPA → Vite + React + TypeScript + Tailwind
    ├─ Full-stack → Next.js + TypeScript
    ├─ CLI Tool → Python Click/Click+rich OR Node.js Commander
    ├─ TypeScript Library → tsup + vitest + pnpm
    └─ Python Library → hatch/uv + pytest
```

## Python FastAPI Template

### Structure
```
project/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       │   └── __init__.py
│       ├── routers/
│       │   └── __init__.py
│       ├── services/
│       │   └── __init__.py
│       └── core/
│           ├── __init__.py
│           └── config.py
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

### pyproject.toml
```toml
[project]
name = "project-name"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["fastapi", "uvicorn", "pydantic"]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "httpx", "ruff"]
```

### main.py
```python
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "My API"
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

## React Vite Template

### Structure
```
project/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── styles/
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── .env.example
```

### vite.config.ts
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
});
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

## Checklist

- [ ] `.gitignore` created (Python: venv, __pycache__, .env / JS: node_modules, dist, .env)
- [ ] `.env.example` created (no secrets, only template variables)
- [ ] Linter configured (Ruff for Python, ESLint/Prettier for JS)
- [ ] Formatter configured (Ruff format, Prettier)
- [ ] Type checker configured (mypy for Python, tsc for JS)
- [ ] Test framework installed (pytest, vitest)
- [ ] README.md with setup instructions
- [ ] CI/CD template (GitHub Actions)
