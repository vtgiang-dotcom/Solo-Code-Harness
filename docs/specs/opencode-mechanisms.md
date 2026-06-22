# OpenCode Cơ Chế — Khảo sát Source Code

> **Mục đích:** Tài liệu này ghi lại cơ chế hoạt động của OpenCode dựa trên source code thật,
> phục vụ việc port các cơ chế tương tự sang Solo-Code Harness.
>
> **Nguồn:** `opencode-dev` (commit mới nhất tại `D:\Project\Solo-Code-CLI\opencode-dev`)
>
> **Nguyên tắc:** Mọi khẳng định đều kèm đường dẫn file:số-dòng chứng minh. Nếu không tìm thấy
> bằng chứng, ghi rõ "CHƯA XÁC MINH ĐƯỢC".

---

## A. Plugin Loading

### 1. Plugin được nạp từ những thư mục nào?

Plugin có hai nguồn:

**a) Internal plugins (built-in):** Được import trực tiếp trong `packages/opencode/src/plugin/index.ts:65-81`. Đây là các plugin auth (Codex, Copilot, Gitlab, Poe, Cloudflare, Azure, Xai, Snowflake) không cần cài đặt.

```typescript
// packages/opencode/src/plugin/index.ts:65-81
function internalPlugins(flags: RuntimeFlags.Info): PluginInstance[] {
  return [
    (input) => CodexAuthPlugin(input, { ... }),
    CopilotAuthPlugin,
    GitlabAuthPlugin,
    PoeAuthPlugin,
    CloudflareWorkersAuthPlugin,
    CloudflareAIGatewayAuthPlugin,
    AzureAuthPlugin,
    DigitalOceanAuthPlugin,
    SnowflakeCortexAuthPlugin,
    XaiAuthPlugin,
  ]
}
```

**b) External plugins:** Lấy từ config `plugins` field. Config được parse từ các file:
- `opencode.json` / `opencode.jsonc` / `config.json` — tìm kiếm từ project directory đi lên (`packages/core/src/config.ts:180-184`)
- `.opencode/` directories — tương tự
- Global config directory

Plugin spec có thể là **string** (npm package name) hoặc `{ package: string, options?: Record<string, unknown> }`.

Plugin sources (`packages/opencode/src/plugin/shared.ts:56-59`):
```typescript
export function pluginSource(spec: string): PluginSource {
  if (isPathPluginSpec(spec)) return "file"
  return "npm"
}
```

File plugin paths là các đường dẫn bắt đầu bằng `file://`, `.` (relative), hoặc absolute path (`packages/opencode/src/plugin/shared.ts:171-173`).

### 2. File nào chịu trách nhiệm discover và load plugin?

**Loader pipeline** (3 files chính):

| File | Vai trò |
|------|---------|
| `packages/opencode/src/plugin/loader.ts` | Resolve → Import → Load external plugins |
| `packages/opencode/src/plugin/index.ts` | Khởi tạo plugin context, chạy internal + external plugins |
| `packages/opencode/src/plugin/shared.ts` | Parse spec, resolve target, kiểm tra compatibility |

**Luồng xử lý (`PluginLoader.loadExternal`) — `packages/opencode/src/plugin/loader.ts:208-236`:**

1. `plan(spec)` — normalize config item thành `Plan { spec, options, deprecated }`
2. `resolve(plan, kind)` — install npm package, tìm entrypoint, check compatibility
3. `load(resolved)` — dynamic import module
4. Callback `finish(loaded)` — xử lý module thành PluginInstance

**Plugin được tích hợp vào hệ thống Effect qua:**

`packages/core/src/plugin/boot.ts` — `PluginBoot.add()` đăng ký plugin vào `PluginV2.Service` và provide các service dependencies (Catalog, Command, Agent, Config, ...).

```typescript
// packages/core/src/plugin/boot.ts:63-85
const add = Effect.fn("PluginBoot.add")(function* (input: InternalPlugin) {
  yield* plugin.add({
    id: input.id,
    effect: input.effect(host).pipe(
      Effect.provideService(Catalog.Service, catalog),
      Effect.provideService(CommandV2.Service, commands),
      // ... nhiều services khác
    ),
  })
})
```

### 3. Plugin export ra cái gì? (signature của plugin function)

**Plugin signature** — `packages/plugin/src/index.ts:74`:
```typescript
export type Plugin = (input: PluginInput, options?: PluginOptions) => Promise<Hooks>
```

**PluginInput** — `packages/plugin/src/index.ts:56-66`:
```typescript
export type PluginInput = {
  client: ReturnType<typeof createOpencodeClient>
  project: Project
  directory: string
  worktree: string
  experimental_workspace: { register(type: string, adapter: WorkspaceAdapter): void }
  serverUrl: URL
  $: BunShell
}
```

**PluginModule** (dạng module object) — `packages/plugin/src/index.ts:76-80`:
```typescript
export type PluginModule = {
  id?: string
  server: Plugin      // hàm chính
  tui?: never
}
```

Plugin module **bắt buộc** phải có default export là object chứa `server()` function (`packages/opencode/src/plugin/shared.ts:272-304` — `readV1Plugin`).

**Hooks** (giá trị trả về) — interface tại `packages/plugin/src/index.ts:222-335` gồm:
- `dispose()` — cleanup
- `event()` — nhận event từ hệ thống
- `config()` — nhận config hiện tại
- `tool.[key]: ToolDefinition` — đăng ký tool tùy chỉnh
- `auth` — hook xác thực
- `provider` — hook provider
- `chat.message`, `chat.params`, `chat.headers`
- `permission.ask`
- `tool.execute.before`, `tool.execute.after`
- `command.execute.before`
- `shell.env`
- `experimental.chat.*`, `experimental.provider.*`, `experimental.session.*`

---

## B. Hook Signature

### 1. Định nghĩa type/interface của `tool.execute.before` và `tool.execute.after`

**Định nghĩa trong `packages/plugin/src/index.ts:266-281`:**

```typescript
"tool.execute.before"?: (
  input: {
    tool: string       // tên của tool (vd "bash", "read", "edit")
    sessionID: string
    callID: string
  },
  output: {
    args: any          // arguments của tool call — có thể modify
  },
) => Promise<void>

"tool.execute.after"?: (
  input: {
    tool: string
    sessionID: string
    callID: string
    args: any          // arguments gốc đã dùng
  },
  output: {
    title: string
    output: string
    metadata: any
  },
) => Promise<void>
```

### 2. Các field input và output

| Hook | Input fields | Output fields |
|------|-------------|---------------|
| `before` | `tool: string`, `sessionID: string`, `callID: string` | `args: any` |
| `after` | `tool: string`, `sessionID: string`, `callID: string`, `args: any` | `title: string`, `output: string`, `metadata: any` |

### 3. Hook được trigger ở đâu?

**Cho built-in tools** — `packages/opencode/src/session/tools.ts:87-106`:
```typescript
yield* plugin.trigger(
  "tool.execute.before",
  { tool: item.id, sessionID: ctx.sessionID, callID: ctx.callID },
  { args },
)
const result = yield* item.execute(args, ctx)
// ... process attachments ...
yield* plugin.trigger(
  "tool.execute.after",
  { tool: item.id, sessionID: ctx.sessionID, callID: ctx.callID, args },
  output,
)
```

**Cho MCP tools** — `packages/opencode/src/session/tools.ts:128-150`:
```typescript
yield* plugin.trigger(
  "tool.execute.before",
  { tool: key, sessionID: ctx.sessionID, callID: opts.toolCallId },
  { args },
)
// ... execute MCP tool ...
yield* plugin.trigger(
  "tool.execute.after",
  { tool: key, sessionID: ctx.sessionID, callID: opts.toolCallId, args },
  result,
)
```

**Cho Task tool** — `packages/opencode/src/session/prompt.ts:291-377`:
```typescript
yield* plugin.trigger(
  "tool.execute.before",
  { tool: TaskTool.id, sessionID, callID: part.id },
  { args: taskArgs },
)
// ... task execution ...
yield* plugin.trigger(
  "tool.execute.after",
  { tool: TaskTool.id, sessionID, callID: part.id, args: taskArgs },
  result,
)
```

### 4. Làm cách nào để một hook CHẶN một tool execution?

Hooks được trigger thông qua `Plugin.trigger()` — `packages/opencode/src/plugin/index.ts:280-293`:
```typescript
const trigger = Effect.fn("Plugin.trigger")(function* (name, input, output) {
  if (!name) return output
  const s = yield* InstanceState.get(state)
  for (const hook of s.hooks) {
    const fn = hook[name] as any
    if (!fn) continue
    yield* Effect.promise(async () => fn(input, output))
  }
  return output
})
```

**Cơ chế chặn:** Hook có thể chặn bằng cách **throw error** bên trong function của nó. Vì hook chạy `yield* Effect.promise(async () => fn(input, output))`, nếu `fn` throw Error, Effect sẽ bắt lỗi và truyền lên trên, ngăn tool execution tiếp diễn.

Hook cũng có thể **modify `output.args`** (trong before hook) để thay đổi arguments trước khi tool chạy. `output` là object reference, mọi mutation trong hook sẽ ảnh hưởng đến code gọi.

**Không có cơ chế "return value để chặn"** — hook là `void` Promise. Cách duy nhất để chặn là throw.

---

## C. Permission Config

### 1. Field `permission` (V1) và `permissions` (V2) trong config

OpenCode có **hai hệ thống permission song song**:

| Hệ thống | Key trong config | Định nghĩa schema |
|----------|-----------------|-------------------|
| V1 (legacy) | `permission` | `packages/core/src/v1/config/permission.ts:38-48` |
| V2 (Effect) | `permissions` | `packages/core/src/permission/schema.ts:1-16` |

### 2. Valid actions

**Cả hai hệ thống đều dùng 3 action:** `"allow"`, `"deny"`, `"ask"`.

V1 — `packages/core/src/v1/config/permission.ts:5`:
```typescript
export const Action = Schema.Literals(["ask", "allow", "deny"])
```

V2 — `packages/core/src/permission/schema.ts:5`:
```typescript
export const Effect = Schema.Literals(["allow", "deny", "ask"])
```

### 3. Cú pháp object cho từng tool — parse và match

**V1 — Config syntax:**

Config dạng `"tool_name": "action"` (string) hoặc `"tool_name": { "pattern": "action" }` (object).

`packages/opencode/src/permission/index.ts:197-209` — `fromConfig()`:
```typescript
export function fromConfig(permission: ConfigPermissionV1.Info) {
  const ruleset: PermissionV1.Rule[] = []
  for (const [key, value] of Object.entries(permission)) {
    if (typeof value === "string") {
      ruleset.push({ permission: key, action: value, pattern: "*" })
      continue
    }
    ruleset.push(
      ...Object.entries(value).map(([pattern, action]) => ({
        permission: key, pattern: expand(pattern), action,
      })),
    )
  }
  return ruleset
}
```

Ví dụ config:
```jsonc
{
  "permission": {
    "bash": "deny",                      // tất cả bash: deny
    "external_directory": {              // chỉ pattern match
      "~/projects/*": "allow",
      "*": "ask"
    },
    "*": "ask"                           // tất cả tool khác: ask
  }
}
```

**V2 — Config syntax:**

Dạng `[{ action: string, resource: string, effect: "allow"|"deny"|"ask" }]`.

Config schema tại `packages/core/src/config.ts:59`:
```typescript
permissions: PermissionSchema.Ruleset.pipe(Schema.optional)
```

`packages/core/src/permission/schema.ts:8-15`:
```typescript
export const Rule = Schema.Struct({
  action: Schema.String,
  resource: Schema.String,
  effect: Effect,
})
export const Ruleset = Schema.mutable(Schema.Array(Rule))
```

### 4. Quy tắc match: first-match hay last-match?

**Last-match wins** — cả hai hệ thống đều dùng `findLast()`.

V1 — `packages/opencode/src/permission/index.ts:39-49`:
```typescript
export function evaluate(permission: string, pattern: string, ...rulesets: PermissionV1.Ruleset[]): PermissionV1.Rule {
  return (
    rulesets
      .flat()
      .findLast((rule) => Wildcard.match(permission, rule.permission) && Wildcard.match(pattern, rule.pattern)) ?? {
      action: "ask",
      permission,
      pattern: "*",
    }
  )
}
```

V2 — `packages/core/src/permission.ts:102-112`:
```typescript
export function evaluate(action: string, resource: string, ...rulesets: Ruleset[]): Rule {
  return (
    rulesets
      .flat()
      .findLast((rule) => Wildcard.match(action, rule.action) && Wildcard.match(resource, rule.resource)) ?? {
      action,
      resource: "*",
      effect: "ask",
    }
  )
}
```

**Ý nghĩa:** Rule được khai báo sau (ở cuối mảng) sẽ ghi đè rule khai báo trước. Dùng `findLast` để tìm rule cuối cùng match.

**Wildcard matching** — `packages/core/src/util/wildcard.ts:1-14`:
```typescript
export function match(input: string, pattern: string) {
  const normalized = input.replaceAll("\\", "/")
  let escaped = pattern
    .replaceAll("\\", "/")
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".")
  if (escaped.endsWith(" .*")) escaped = escaped.slice(0, -3) + "( .*)?"
  return new RegExp("^" + escaped + "$", process.platform === "win32" ? "si" : "s").test(normalized)
}
```

Hỗ trợ: `*` (any sequence), `?` (single char). Escape regex chars. Normalize backslash → slash.

### 5. Agent-level permissions

Permission cũng có thể được gán cho từng agent — `packages/core/src/agent.ts:29`:
```typescript
permissions: PermissionSchema.Ruleset,
```

Trong config agent (`packages/core/src/config/agent.ts:24`):
```typescript
permissions: PermissionSchema.Ruleset.pipe(Schema.optional),
```

Agent permissions được merge với global permissions khi agent được resolve — `packages/core/src/permission.ts:163-171`:
```typescript
const configured = EffectRuntime.fn("PermissionV2.configured")(function* (
  sessionID, agentID,
) {
  const agent = yield* agents.resolve(agentID ?? session.agent)
  return agent?.permissions ?? missingAgentPermissions
})
```

Default (nếu không có permission) là deny tất cả (`packages/core/src/permission.ts:19`):
```typescript
const missingAgentPermissions: Ruleset = [{ action: "*", resource: "*", effect: "deny" }]
```

---

## D. Agent Markdown

### 1. Nơi parse file agent markdown

**Discovery pattern** — `packages/core/src/config/plugin/agent.ts:15-18`:
```typescript
const legacySources = [
  { pattern: "{agent,agents}/**/*.md", primary: false },
  { pattern: "{mode,modes}/*.md", primary: true },
] as const
```

Các file `.md` được tìm trong mọi `Config.Directory` (bao gồm `.opencode/` và thư mục config khác) — `packages/core/src/config/plugin/agent.ts:103-113`.

**Parser** — `packages/core/src/config/markdown.ts:1-36` — dùng `gray-matter` library:
```typescript
import matter from "gray-matter"
export function parse(content: string) {
  try {
    return matter(content)
  } catch {
    return matter(sanitize(content))
  }
}
```

**Decode function** — `packages/core/src/config/plugin/agent.ts:116-141`:
```typescript
function decode(file, content: string) {
  const markdown = ConfigMarkdown.parseOption(content)
  const name = path.relative(file.directory, file.filepath)
    .replaceAll("\\", "/")
    .replace(/^(agent|agents|mode|modes)\//, "")
    .replace(/\.md$/, "")
  const body = markdown.content.trim()
  const legacy = Object.keys(markdown.data).some((key) => !agentKeys.has(key))
  const agent = Option.getOrUndefined(
    legacy
      ? decodeLegacyAgent({ name, ...markdown.data, prompt: body })
      : decodeAgent({ ...markdown.data, system: body }),
  )
  // ...
}
```

File name (without `.md` and path prefix) → agent ID. Body content → `system` (V2) / `prompt` (V1).

### 2. Frontmatter fields (V2)

`packages/core/src/config/agent.ts:13-25`:
```typescript
export class Info extends Schema.Class<Info>("ConfigV2.Agent")({
  model: Schema.String.pipe(Schema.optional),        // model ID
  variant: Schema.String.pipe(Schema.optional),       // model variant
  request: ConfigProvider.Request.pipe(Schema.optional), // provider request config
  system: Schema.String.pipe(Schema.optional),        // system prompt (body content)
  description: Schema.String.pipe(Schema.optional),   // mô tả
  mode: Schema.Literals(["subagent", "primary", "all"]).pipe(Schema.optional), // mode
  hidden: Schema.Boolean.pipe(Schema.optional),       // ẩn khỏi menu
  color: Color.pipe(Schema.optional),                 // màu sắc
  steps: PositiveInt.pipe(Schema.optional),           // max iterations
  disabled: Schema.Boolean.pipe(Schema.optional),     // disable agent
  permissions: PermissionSchema.Ruleset.pipe(Schema.optional), // permission rules
}) {}
```

### 3. Fields bắt buộc

**Không có field nào bắt buộc.** Agent có thể tồn tại với mọi field optional. Nếu không có `mode`, giá trị mặc định là `"all"` (khi decode V2). `AgentV2.empty()` tạo agent với `mode: "all"`, `hidden: false`, `permissions: []`.

Tuy nhiên, nếu `disabled: true`, agent sẽ bị xóa khỏi draft (`packages/core/src/config/plugin/agent.ts:69-71`):
```typescript
if (item.disabled) {
  draft.remove(agentID)
  continue
}
```

### 4. `mode` nhận giá trị gì?

**V2 mode** — `packages/core/src/config/agent.ts:19`:
```typescript
mode: Schema.Literals(["subagent", "primary", "all"]).pipe(Schema.optional),
```

- `"subagent"` — chỉ có thể được gọi bởi agent khác (qua task tool), không xuất hiện trong UI agent selector
- `"primary"` — agent chính, xuất hiện trong UI
- `"all"` — vừa là primary vừa có thể được gọi làm subagent

**V1 legacy mode** — `packages/core/src/v1/config/agent.ts:26`:
```typescript
mode: Schema.optional(Schema.Literals(["subagent", "primary", "all"])),
```

**Ví dụ thực tế:** Agent file `duplicate-pr.md`:
```yaml
---
mode: primary
hidden: true
model: opencode/claude-haiku-4-5
color: "#E67E22"
---
```

### 5. Xử lý V1 (legacy) frontmatter

Nếu frontmatter chứa key không thuộc `agentKeys` set (`model`, `variant`, `request`, `system`, `description`, `mode`, `hidden`, `color`, `steps`, `disabled`, `permissions`), nó được decode như V1 agent config (`packages/core/src/v1/config/agent.ts:12-41`).

V1 agent fields bổ sung: `prompt`, `temperature`, `top_p`, `tools`, `disable`, `maxSteps`, `options`.

---

## E. V1 vs V2 — Hệ thống nào đang dùng

### E1. Khi user viết config với field `permission` (V1 syntax), engine có còn đọc và áp dụng không?

**Có, V1 `permission` field là hệ thống đang hoạt động.** Config V1 (`packages/opencode/src/config/config.ts`) dùng schema `ConfigV1.Info` có chứa `permission: ConfigPermissionV1.Info` (`packages/core/src/v1/config/config.ts:125`).

Luồng load config thực tế:

1. `packages/opencode/src/config/config.ts:227` — parse config dùng V1 schema:
```typescript
const data = ConfigParse.schema(ConfigV1.Info, normalizeLoadedConfig(parsed), source)
```

2. `packages/opencode/src/config/config.ts:111-115` — runtime type `Info` kế thừa từ V1:
```typescript
type Info = ConfigV1.Info & {
  plugin_origins?: ConfigPlugin.Origin[]
}
```

3. `packages/opencode/src/config/config.ts:544-549` — `result.permission` (V1 format) được ghi trực tiếp:
```typescript
if (Flag.OPENCODE_PERMISSION) {
  try {
    result.permission = mergeDeep(result.permission ?? {}, JSON.parse(Flag.OPENCODE_PERMISSION))
  } catch (err) {
    yield* Effect.logWarning("OPENCODE_PERMISSION contains invalid JSON, skipping", { err })
  }
}
```

4. `packages/opencode/src/config/config.ts:552-563` — `result.tools` được merge vào `result.permission` (V1):
```typescript
if (result.tools) {
  const perms: Record<string, ConfigPermissionV1.Action> = {}
  for (const [tool, enabled] of Object.entries(result.tools)) {
    const action: ConfigPermissionV1.Action = enabled ? "allow" : "deny"
    if (tool === "write" || tool === "edit" || tool === "patch") {
      perms.edit = action
      continue
    }
    perms[tool] = action
  }
  result.permission = mergeDeep(perms, result.permission ?? {})
}
```

**V2 `permissions` field** (dạng array) được định nghĩa trong `packages/core/src/config.ts:59`:
```typescript
permissions: PermissionSchema.Ruleset.pipe(Schema.optional)
```
Tuy nhiên, schema này chỉ được dùng bởi V2 config layer (`packages/core/src/config.ts`) — layer này chạy nhưng đầu ra của nó (`Config.Info`) không phải là nguồn permission cho tool execution. Nguồn thực tế là `ConfigV1.Info.permission` từ `packages/opencode/src/config/config.ts`.

---

### E2. Có migrate layer chuyển V1 permission thành V2 permissions không? Nếu có, ở file nào?

**Có migrate layer nhưng chỉ dùng trong V2 config path, không ảnh hưởng đến runtime tool execution thực tế.**

Migrate layer tại `packages/core/src/v1/config/migrate.ts`:

- `isV1()` (dòng 31-34) — phát hiện config có chứa key V1:
```typescript
export function isV1(input: unknown) {
  if (typeof input !== "object" || input === null || Array.isArray(input)) return false
  return Object.keys(input).some((key) => keys.has(key))
}
```

- `migrate()` (dòng 36-73) — chuyển toàn bộ config V1 → V2. Trong đó hàm `permissions()` (dòng 75-92) chuyển `permission` (V1 object) thành `permissions` (V2 array):
```typescript
function permissions(info?: ConfigPermissionV1.Info, tools?: Readonly<Record<string, boolean>>) {
  const rules: Array<{ action: string; resource: string; effect: ConfigPermissionV1.Action }> = ...
  for (const [action, rule] of Object.entries(info ?? {})) {
    if (!rule) continue
    if (typeof rule === "string") {
      rules.push({ action, resource: "*", effect: rule })
      continue
    }
    rules.push(...Object.entries(rule).map(([resource, effect]) => ({ action, resource, effect })))
  }
  return rules.length ? rules : undefined
}
```

Migrate này được gọi ở **duy nhất một nơi** — `packages/core/src/config.ts:154-158`:
```typescript
const info = Option.getOrUndefined(
  ConfigMigrateV1.isV1(input)
    ? decodeV1Info(input).pipe(Option.map(ConfigMigrateV1.migrate), Option.flatMap(decodeInfo))
    : decodeInfo(input),
)
```

Kết quả migrate là `Config.Info` (V2) — object có field `permissions` (V2 array). Tuy nhiên, `Config.Info.permissions` (V2) **không được đọc bởi bất kỳ code agent/tool execution nào** (xem E3).

**Kết luận:** Migrate layer tồn tại nhưng chỉ phục vụ V2 config path. Runtime tool execution dùng V1 `permission` trực tiếp, không qua migrate.

---

### E3. Đường-đi-thực-tế quyết định cho phép/chặn tool execution

Đây là đường đi từ tool execution đến permission evaluation:

**Bước 1 — Config được load và permission được lưu dạng V1.**

`packages/opencode/src/config/config.ts` đọc `permission` field (V1) và lưu trong `result.permission` (dạng V1 object).

**Bước 2 — Khi khởi tạo agent, `cfg.permission` (V1) được convert thành V1 Ruleset.**

`packages/opencode/src/agent/agent.ts:136`:
```typescript
const user = Permission.fromConfig(cfg.permission ?? {})
```

Hàm `fromConfig()` (V1, `packages/opencode/src/permission/index.ts:197-209`) chuyển config object thành mảng `Rule { permission, pattern, action }`.

**Bước 3 — Mỗi agent có một V1 Ruleset.**

`packages/opencode/src/agent/agent.ts:138-263` — mỗi agent được tạo với:
```typescript
permission: Permission.merge(defaults, Permission.fromConfig({...}), user),
```
Trong đó `user` là `cfg.permission` đã convert. (dòng 149)

**Bước 4 — Khi config agent overrides, `value.permission` (V1) được merge.**

`packages/opencode/src/agent/agent.ts:291`:
```typescript
item.permission = Permission.merge(item.permission, Permission.fromConfig(value.permission ?? {}))
```

**Bước 5 — `ctx.ask()` được gọi bên trong mỗi tool trước khi thực thi.**

Ví dụ tool `read` (`packages/opencode/src/tool/read.ts:255-260`):
```typescript
yield* ctx.ask({
  permission: "read",
  patterns: [path.relative(instance.worktree, filepath)],
  always: ["*"],
  metadata: {},
})
```

**Bước 6 — `ctx.ask` gọi `permission.ask()` (V1) với ruleset là merge của agent permissions + session permissions.**

`packages/opencode/src/session/tools.ts:63-71`:
```typescript
ask: (req) =>
  permission
    .ask({
      ...req,
      sessionID: input.session.id,
      tool: { messageID: input.processor.message.id, callID: options.toolCallId },
      ruleset: Permission.merge(input.agent.permission, input.session.permission ?? []),
    })
    .pipe(Effect.orDie),
```

**Bước 7 — `Permission.ask()` (V1) evaluate từng pattern qua `findLast()`.**

`packages/opencode/src/permission/index.ts:78-118`:
```typescript
export function evaluate(permission: string, pattern: string, ...rulesets: PermissionV1.Ruleset[]): PermissionV1.Rule {
  return rulesets.flat().findLast(
    (rule) => Wildcard.match(permission, rule.permission) && Wildcard.match(pattern, rule.pattern)
  ) ?? { action: "ask", permission, pattern: "*" }
}
```

Kết quả:
- `"allow"` → tool chạy
- `"deny"` → throw `PermissionV1.DeniedError`
- `"ask"` → tạo pending request, chờ user reply

**V2 Permission system (`packages/core/src/permission.ts`) có `assert()` nhưng KHÔNG được gọi từ code session/tool.** Toàn bộ session/tool code dùng `Permission` (V1) từ `@/permission` alias (resolve thành `packages/opencode/src/permission/index.ts`). `PermissionV2.assert` chỉ được định nghĩa (`packages/core/src/permission.ts:223-243`) nhưng có zero callers trong runtime.

---

### E4. Quan hệ giữa Policy và Permission

**Policy (`packages/core/src/policy.ts`) và Permission (V1 hoặc V2) là hai hệ thống độc lập, không ảnh hưởng lẫn nhau.**

Policy:
- Chỉ hỗ trợ `"allow"` / `"deny"` — không có `"ask"` (`packages/core/src/policy.ts:7`)
- Load từ `experimental.policies` field trong config (`packages/core/src/config.ts:205-210`)
- Dùng `findLast()` với `Wildcard.match()` giống Permission
- Mục đích: kiểm soát provider access (theo mô tả trong schema)

```typescript
// packages/core/src/policy.ts:7-14
export const Effect = Schema.Literals(["allow", "deny"])
export class Info extends Schema.Class<Info>("Policy.Info")({
  action: Schema.String,
  effect: Effect,
  resource: Schema.String,
}) {}
```

Policy evaluate function (`packages/core/src/policy.ts:35-40`):
```typescript
evaluate: EffectRuntime.fn("Policy.evaluate")(function* (action, resource, fallback) {
  return (
    statements.findLast(
      (statement) => Wildcard.match(action, statement.action) && Wildcard.match(resource, statement.resource),
    )?.effect ?? fallback
  )
}),
```

**Policy KHÔNG được tham chiếu trong code tool execution hay permission evaluation.** Policy chỉ được `load()` từ config và có `evaluate()` method, nhưng không có code nào ở các package `opencode/src/session`, `opencode/src/tool`, hay `opencode/src/permission` gọi `Policy.evaluate()` để quyết định tool access.

**Kết luận:** Policy và Permission là hai hệ thống song song, độc lập, không ghi đè lẫn nhau. Policy dành cho experimental provider policies, Permission dành cho tool execution control.

---

### KẾT LUẬN CHO SECTION E

**Để cấu hình permission cho phiên bản này, NÊN dùng V1 `permission` field (dạng object) vì:**

1. Runtime config system (`packages/opencode/src/config/config.ts`) parse và lưu trữ `permission` dạng V1 object.
2. Agent initialization (`packages/opencode/src/agent/agent.ts:136`) đọc `cfg.permission` qua `Permission.fromConfig()`.
3. Tool execution path (`packages/opencode/src/session/tools.ts:69`) dùng V1 Ruleset và `Permission.ask()` (V1).
4. V2 `permissions` field (dạng array) chỉ tồn tại trong V2 config schema (`packages/core/src/config.ts:59`) — không có code nào ở session/tool layer đọc nó.
5. Migrate layer V1→V2 tồn tại (`packages/core/src/v1/config/migrate.ts`) nhưng không được dùng trong runtime tool execution path.

---

## Các điểm "CHƯA XÁC MINH ĐƯỢC"

1. **Plugin `effect` function signature trong V2 (`@opencode-ai/plugin/v2/effect`):** Các internal plugin V2 dùng `define({ id, effect })` (`packages/core/src/plugin/boot.ts`, `packages/core/src/plugin/agent.ts`). Chi tiết kiểu dữ liệu của `define()` và `effect()` nằm trong package `@opencode-ai/plugin/v2/effect` (CHƯA XÁC MINH — file này có thể ở `packages/plugin/src/v2/` hoặc ở ngoài source tree).

2. **MCP permission flow:** Cơ chế MCP tool permission (`packages/opencode/src/session/tools.ts:134`) dùng `ctx.ask()` riêng cho MCP tools. Chi tiết về việc MCP tools có chịu ảnh hưởng của global permission config không — CHƯA XÁC MINH (cần trace thêm).

3. **Tool-level `whollyDisabled` check trong `packages/core/src/tool/registry.ts:131-133`** — ĐÃ XÁC MINH là V2-only code path (Effect system). Không ảnh hưởng đến runtime tool execution V1 path.
