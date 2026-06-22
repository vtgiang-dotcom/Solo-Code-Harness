# Solo-Code Harness — Hook System

> Hệ thống lifecycle hooks cho AI coding agent. Ported từ ECC v2.0.0-rc.1, tối ưu cho Kilo Code.

## Architecture

```
.kilo/hooks/
├── hooks.json              # Hook registry & config
├── run-with-flags.js       # Dispatcher utility
├── pre-tool-use/           # Chạy TRƯỚC khi tool thực thi
│   ├── gate-guard.js       # Chặn lệnh bash phá hủy
│   ├── secret-scan.js      # Quét hardcoded secrets
│   ├── config-protection.js # Chặn sửa config linter/formatter
│   └── governance-capture.js # Ghi log sự kiện governance
├── post-tool-use/          # Chạy SAU khi tool hoàn thành
│   ├── quality-gate.js     # Kiểm tra format/lint
│   ├── console-log-check.js # Phát hiện debug statements
│   ├── context-monitor.js  # Theo dõi context & tool loops
│   └── edit-accumulator.js # Ghi nhận file đã edit
└── session/                # Session lifecycle
    ├── session-start.js    # Bootstrap session
    └── session-end.js      # Persist & summary
```

## Hook Profiles

| Profile  | Description |
|----------|------------|
| `minimal` | Chỉ gate-guard (an toàn tối thiểu) |
| `standard` | Gate-guard + secret-scan + quality-gate + context-monitor |
| `strict` | Tất cả hooks |

Cấu hình trong `hooks.json` → `profiles`.

## Cách dùng

```bash
# Chạy hook thủ công
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp"}}' | node .kilo/hooks/pre-tool-use/gate-guard.js
echo $?  # 2 = BLOCKED

# Bypass gate guard
GATE_GUARD_BYPASS=1 node .kilo/hooks/pre-tool-use/gate-guard.js

# Enable governance capture
ECC_GOVERNANCE_CAPTURE=1 node .kilo/hooks/pre-tool-use/governance-capture.js
```

## State Files

- `.kilo/state/tool-count.json` — Đếm tool calls trong session
- `.kilo/state/edited-files.json` — Danh sách file đã edit
- `.kilo/state/sessions/` — Session logs
- `.kilo/logs/governance-events.jsonl` — Governance event log
