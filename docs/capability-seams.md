# Capability Seams — Service Definition / Provider / Consumer Pattern

Pattern ported từ DeepSeek Harness (`packages/core/`, `packages/skill/`, `packages/subagent/`).

---

## Vấn đề

Khi một module cần cung cấp khả năng (capability) cho phần còn lại của hệ thống, có 3 cách thông thường:

1. **Import trực tiếp** — gọi thẳng implementation. Coupling cao, không swap được.
2. **Dependency injection** — truyền object qua constructor. Tốt hơn nhưng vẫn cần biết concrete type.
3. **Capability Seam** — định nghĩa interface tại ranh giới, provider đăng ký vào registry, consumer chỉ dùng registry. Zero coupling.

Harness dùng cách 3 cho mọi tính năng quan trọng.

---

## Ba vai trò

```
Service Definition          Provider                    Consumer
────────────────────        ────────────────────        ────────────────────
Định nghĩa interface        Implement interface         Gọi qua registry key
Đặt tên registry key        Đăng ký vào ctx             Không import provider
Không chứa logic            Không biết consumer         ctx.tools.register()
                                                         ctx.skills.get()
```

**Nguyên tắc cốt lõi:** Consumer và Provider KHÔNG bao giờ import nhau. Cả hai chỉ import Service Definition.

---

## Ví dụ trong harness

### Tool Registry (`ctx.tools`)

```
Service Definition: packages/core/tools/     → interface ToolDefinition, ToolRuntime
Provider:           packages/shell/           → ctx.tools.register(bashTool)
Consumer:           packages/core/agent-loop/ → ctx.tools.execute(call)
```

`agent-loop` không import `shell`. Nó chỉ biết `ctx.tools`. Nếu swap shell sang e2b sandbox, `agent-loop` không đổi gì.

### Skill Registry (`ctx.skills`)

```
Service Definition: packages/skill/skill/         → interface SkillRegistry
Provider:           packages/skill/skill-filesystem/ → registerProvider(filesystemProvider)
Consumer:           packages/skill/tool-skill/     → ctx.skills.get(name)
```

### Subagent Runtime (`ctx.subagents`)

```
Service Definition: packages/subagent/subagent/          → interface SubagentRuntime
Provider:           packages/subagent/subagent-fork-in-process/ → registerProvider(forkProvider)
Consumer:           packages/subagent/tool-subagent/      → ctx.subagents.start(name, req)
```

---

## Pattern chuẩn (Python)

> **Lưu ý**: Các đoạn code dưới đây là **minh họa** cho pattern — không phải file thực tế trên đĩa.
> Implementation thực tế của project nằm trong `tools/agent_scope.py`.

### Bước 1: Service Definition

```python
# Minh họa: service definition (trong thực tế: tools/agent_scope.py)
from __future__ import annotations
from typing import Protocol, Any
from dataclasses import dataclass

@dataclass
class ToolDefinition:
    name: str
    description: str
    execute: Any  # callable(args) -> result

class ToolRegistry(Protocol):
    def register(self, tool: ToolDefinition) -> None: ...
    def get(self, name: str) -> ToolDefinition | None: ...
    def list(self) -> list[ToolDefinition]: ...
    def execute(self, name: str, args: dict) -> Any: ...
```

### Bước 2: Implementation (Registry)

```python
# Minh họa: implementation (trong thực tế: AgentScopeRegistry trong tools/agent_scope.py)
class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def execute(self, name: str, args: dict) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.execute(args)
```

### Bước 3: Provider (đăng ký vào registry)

```python
# Minh họa: provider
import subprocess
from tools.agent_scope import ToolDefinition  # import thực tế

def register_bash_tool(registry) -> None:
    def _execute(args: dict) -> str:
        cmd = args.get("command", "")
        result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
        return result.stdout + result.stderr

    registry.register(ToolDefinition(
        name="bash",
        description="Run a shell command",
        execute=_execute,
    ))
```

### Bước 4: Consumer (dùng qua registry)

```python
# Minh họa: consumer — KHÔNG import provider
class AgentLoop:
    def __init__(self, registry) -> None:
        self._registry = registry

    def handle_tool_call(self, name: str, args: dict):
        return self._registry.execute(name, args)
```

### Bước 5: Composition root (nơi DUY NHẤT biết tất cả)

```python
# Minh họa: composition root
from tools.agent_scope import AgentScopeRegistry, ToolDefinition

def build_agent() -> AgentLoop:
    registry = AgentScopeRegistry()
    register_bash_tool(registry)
    return AgentLoop(registry)
```

---

## Scoped Registration (per-agent override)

Pattern từ `dsh-scope`: mỗi agent có thể shadow global registry với registration riêng của nó.

```python
# Ví dụ: agent A dùng bash bình thường, agent B dùng sandbox bash
registry.register(ToolDefinition(name="bash", execute=sandbox_bash), scope="agent-b")

# Resolution: agent-b sees sandbox_bash, mọi agent khác sees global bash
def resolve(name: str, scope: str | None = None) -> ToolDefinition | None:
    if scope and (scoped := scoped_tools.get((scope, name))):
        return scoped
    return global_tools.get(name)
```

Quy tắc: **registration context quyết định cả visibility lẫn lifetime**. Đây là invariant quan trọng nhất của pattern — ngăn một registration vừa visible ở scope A vừa bị dispose cùng scope B.

---

## Khi nào dùng Capability Seam

| Tình huống | Dùng Seam? | Lý do |
|---|---|---|
| Cần swap implementation (real vs mock, local vs remote) | Có | Seam cho phép swap không đổi consumer |
| Nhiều provider cùng loại tính năng (bash, e2b, docker) | Có | Registry hợp nhất nhiều provider |
| Internal helper chỉ dùng ở 1 chỗ | Không | Over-engineering |
| Cần test với mock | Có thể | Nhưng ưu tiên integration test với real impl |

---

## Liên kết

- Xem implementation thực tế: `tools/agent_scope.py`
- Pattern scoping: `deepseek-harness-master/packages/core/scope/README.md`
- Tool registry full spec: `deepseek-harness-master/packages/core/tools/README.md`
- Subagent seam: `deepseek-harness-master/packages/subagent/subagent/README.md`
