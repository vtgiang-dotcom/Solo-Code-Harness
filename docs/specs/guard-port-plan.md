# Guard Port Plan — OpenCode Plugin từ Kilo Hooks

> Tài liệu tóm tắt các pattern/logic cần port, kèm đường dẫn file:dòng.
> Giai đoạn 1 — Chờ duyệt trước khi viết code.

---

## 1. Destructive Command Patterns (gate-guard.js)

**Nguồn:** `.kilo/hooks/pre-tool-use/gate-guard.js`

### BLOCK_PATTERNS (dòng 23-41) — Chặn cứng, exit 2

| Tên pattern | Regex | Dòng |
|---|---|---|
| `rm_root` | `/rm\s+-rf?\s+\/(?:\s\|$\|\*\|"\|')/` | 24 |
| `rm_home` | `/rm\s+-rf?\s+~/` | 25 |
| `rm_wildcard` | `/rm\s+-rf?\s+\*/` | 26 |
| `rm_no_preserve` | `/rm\s+--no-preserve-root/` | 27 |
| `force_push_main` | `/git\s+push\s+.*(--force\|-f)\s+.*(main\|master)/` | 28 |
| `git_reset_hard` | `/git\s+reset\s+--hard/` | 29 |
| `drop_table` | `/DROP\s+(?:TABLE\|DATABASE)/i` | 30 |
| `truncate_table` | `/TRUNCATE\s+TABLE/i` | 31 |
| `dd_raw` | `/dd\s+if=/` | 32 |
| `mkfs` | `/mkfs\./` | 33 |
| `shred` | `/shred\s+/` | 34 |
| `dev_write` | `/>\s*\/dev\/sd[a-z]/` | 35 |
| `win_del_force` | `/del\s+\/f\s+\/s/` | 36 |
| `win_remove_recursive` | `/Remove-Item\s+.*-Recurse.*-Force/` | 37 |
| `format_disk` | `/\bformat\s/` | 38 |
| `diskpart` | `/\bdiskpart\b/` | 39 |
| `shutdown_system` | `/(?:shutdown\|reboot\|halt)\b/` | 40 |

### Các category khác (WARN, PATH, MODE, SED, SEMANTIC, PIPE_DESTRUCTIVE)

Các pattern này ở dòng 44-107, KHÔNG chặn cứng (chỉ cảnh báo). Theo plan gốc, chỉ port `isDestructiveCommand` (BLOCK_PATTERNS). Các warn patterns có thể bỏ qua trừ khi cần mở rộng.

---

## 2. Secret Detection Patterns (secret-scan.js)

**Nguồn:** `.kilo/hooks/pre-tool-use/secret-scan.js`

### SECRET_PATTERNS (dòng 18-34)

| Tên pattern | Regex | Dòng |
|---|---|---|
| `aws_access_key` | `/(?:AKIA\|ASIA)[A-Z0-9]{16}/` | 19 |
| `aws_secret_key` | `/(?:aws\|amazon).{0,20}(?:secret\|key\|token).{0,10}[:=]\s*["'][A-Za-z0-9\/+=]{20,}/i` | 20 |
| `generic_api_key` | `/(?:api[_-]?key\|apikey\|secret\|password)\s*[:=]\s*["'][^"']{8,}["']/i` | 21 |
| `private_key_pem` | `/-----BEGIN (?:RSA \|EC \|DSA \|OPENSSH )?PRIVATE KEY-----/` | 22 |
| `jwt_token` | `/eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/` | 23 |
| `github_token` | `/(?:gh[pousr]_\|github[_-]?pat[_-]?\|github[_-]?token[_-]?)[A-Za-z0-9_]{20,}/i` | 24 |
| `google_api_key` | `/AIza[0-9A-Za-z_-]{35}/` | 25 |
| `slack_token` | `/xox[baprs]-[0-9A-Za-z-]{10,}/` | 26 |
| `stripe_key` | `/(?:sk\|pk)_(?:test\|live)_[0-9a-zA-Z]{24,}/` | 27 |
| `mongodb_uri` | `/mongodb(?:\+srv)?:\/\/[^:]+:[^@]+@/` | 28 |
| `postgres_uri` | `/postgres(?:ql)?:\/\/[^:]+:[^@]+@/` | 29 |
| `redis_uri` | `/redis:\/\/[^:]+:[^@]+@/` | 30 |
| `hardcoded_token` | `/(?:token\|bearer)\s*[:=]\s*["'][A-Za-z0-9._\-+\/=]{20,}["']/i` | 31 |
| `discord_webhook` | `/https:\/\/discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9_-]+/i` | 32 |
| `basic_auth` | `/https?:\/\/[^:]+:[^@]+@/` | 33 |

### Helper functions cần port

| Hàm | Mô tả | Dòng |
|---|---|---|
| `scanSecrets(content, filePath)` | Duyệt từng dòng, test từng pattern | 50-68 |
| `isSecretProneExtension(filePath)` | Kiểm tra .env, .json, .pem, ... | 75-79 |
| `isExcludedPath(filePath)` | Bỏ qua node_modules, .git, ... | 84-88 |
| `SECRET_PRONE_EXTENSIONS` Set | Các đuôi file dễ chứa secret | 37-42 |
| excluded dirs list | `node_modules`, `.venv`, `venv`, `__pycache__`, `.git`, `dist`, `build`, `.next`, `.cache` | 86 |

---

## 3. Config Weakening Detection (config-protection.js)

**Nguồn:** `.kilo/hooks/pre-tool-use/config-protection.js`

### PROTECTED_FILES (dòng 21-45) — Set tên file bị bảo vệ

| Nhóm | File names |
|---|---|
| ESLint | `.eslintrc`, `.eslintrc.js`, `.eslintrc.cjs`, `.eslintrc.json`, `.eslintrc.yml`, `.eslintrc.yaml`, `eslint.config.js`, `eslint.config.mjs`, `eslint.config.cjs`, `eslint.config.ts`, `eslint.config.mts`, `eslint.config.cts` |
| Prettier | `.prettierrc`, `.prettierrc.js`, `.prettierrc.cjs`, `.prettierrc.json`, `.prettierrc.yml`, `.prettierrc.yaml`, `prettier.config.js`, `prettier.config.cjs`, `prettier.config.mjs` |
| Biome | `biome.json`, `biome.jsonc` |
| Ruff | `.ruff.toml`, `ruff.toml` |
| Shell/Style/MD | `.shellcheckrc`, `.stylelintrc`, `.stylelintrc.json`, `.stylelintrc.yml`, `.markdownlint.json`, `.markdownlint.yaml`, `.markdownlintrc` |
| Python | `.flake8`, `.pylintrc`, `tox.ini` |
| Go | `.golangci.yml`, `.golangci.yaml`, `.golangci.json` |
| General | `.editorconfig` |

### Logic chính (dòng 86-117)

1. Parse `tool_input.file_path` hoặc `tool_input.file` (dòng 86)
2. Lấy `basename` từ filePath (dòng 91)
3. Nếu basename nằm trong `PROTECTED_FILES`:
   - Kiểm tra file đã tồn tại chưa (`fs.lstatSync`) — dòng 97
   - Nếu chưa tồn tại → ALLOW (first-time creation) — dòng 104-106
   - Nếu đã tồn tại → BLOCK (exit 2) — dòng 108-113
4. Nếu basename không nằm trong set → ALLOW

### Lưu ý

- Dùng `path.basename(filePath)` — chỉ check tên file, không check đường dẫn đầy đủ
- Cho phép tạo file lần đầu (chưa tồn tại)
- Chặn sửa file đã tồn tại

---

## 4. Command Normalization Logic

**KHÔNG TÌM THẤY TRONG BẢN GỐC.**

`gate-guard.js` không có hàm normalize command riêng. Ở dòng 183-184, command được lấy trực tiếp từ input:
```javascript
const command = toolInput.command || toolInput.CommandLine || toolInput.cmd || toolInput.commandLine || '';
```
Không có bước gỡ `sudo`, gộp khoảng trắng, hay xử lý đường dẫn.

→ Theo ràng buộc của plan: **BỎ QUA**, không tự viết.

---

## 5. OpenCode Hook Signature (tham khảo)

**Nguồn:** `docs/specs/opencode-mechanisms.md` mục B

```typescript
// Hook signature
"tool.execute.before"?: (
  input: { tool: string, sessionID: string, callID: string },
  output: { args: any },
) => Promise<void>

// Chặn bằng throw
throw new Error("[SoloCode] Blocked destructive command: ...")
```

### Mapping tool names giữa Kilo ↔ OpenCode

| Kilo tool name | OpenCode tool name |
|---|---|
| `bash` | `bash` |
| `write` (file write) | `write` |
| `edit` | `edit` |
| (apply_patch trong spec) | `patch` (OpenCode tương ứng) |

---

## 6. Content Field Mapping — Mỗi Tool

**Nguồn:** Source code thật từ `opencode-dev/packages/opencode/src/tool/`

Đây là ánh xạ chính xác `output.args.<field>` cho từng tool, dùng để lấy nội dung cần scan
trong hook `tool.execute.before`:

### write tool
- **File:** `opencode-dev/packages/opencode/src/tool/write.ts:20-25`
- **Params schema:** `{ content: string, filePath: string }`
- **Content để scan secret:** `output.args.content`
- **File path cho config-protection:** `output.args.filePath`
- **File path cho secret-scan extension check:** `output.args.filePath`

### edit tool
- **File:** `opencode-dev/packages/opencode/src/tool/edit.ts:47-56`
- **Params schema:** `{ filePath: string, oldString: string, newString: string, replaceAll?: boolean }`
- **Content để scan secret:** Cả `output.args.oldString` và `output.args.newString` — vì cả hai đều có thể chứa secret
- **File path cho config-protection:** `output.args.filePath`

### apply_patch tool
- **File:** `opencode-dev/packages/opencode/src/tool/apply_patch.ts:18-20`
- **Params schema:** `{ patchText: string }`
- **Content để scan secret:** `output.args.patchText` — vì patchText chứa diff text bao gồm cả nội dung file cũ và mới
- **File path cho config-protection:** Không có filePath riêng. paths nằm trong patch text. Có thể parse từ hunk paths nhưng vượt phạm vi vòng 1. → **Known gap: apply_patch không được bảo vệ config-protection ở vòng đầu.**

### bash tool
- **Params:** `output.args.command`
- **Content để scan destructive pattern:** `output.args.command`

---

## 7. Known Gap: No Normalization (Gate-Guard Gốc)

**XÁC NHẬN:** `gate-guard.js` không có hàm normalize command. Command được lấy raw từ
`toolInput.command || toolInput.CommandLine || toolInput.cmd || toolInput.commandLine || ''`
(dòng 183-184). Không gỡ `sudo`, không gộp khoảng trắng, không xử lý đường dẫn tuyệt đối.

**Hệ quả được ghi nhận (vòng 1):**
- `sudo rm -rf /` → lọt (không match rm pattern vì có `sudo` ở đầu)
- `bash -c "rm -rf /"` → lọt (command là bash -c, không match rm pattern)
- Đường dẫn tuyệt đối với flag khác → có thể lọt

**Kế hoạch vòng 2:** Thêm normalize stage: strip `sudo`, strip `bash -c "... "`, trim whitespace.

---

## 8. Cấu trúc Plugin Đề Xuất

Một file: `.opencode/plugins/solocode-guard.js`

```
Module default export:
  server: (input, options) => {
    return {
      "tool.execute.before": async (toolInput, toolOutput) => {
        // 1. Nếu tool là bash → isDestructiveCommand(args)
        // 2. Nếu tool là write/edit/patch → containsSecret(content)
        // 3. Nếu tool là write/edit/patch → weakensConfig(filePath)
        // Throw error nếu vi phạm
      }
    }
  }
```

---

## 9. Ràng buộc

- Mọi pattern PHẢI lấy từ 3 file gốc — cấm tự sáng tạo
- Cuối file plugin: comment block bảng truy nguyên pattern → file:dòng
- Không sửa `opencode.json`
- Không tạo file nào khác ngoài `.opencode/plugins/solocode-guard.js`
