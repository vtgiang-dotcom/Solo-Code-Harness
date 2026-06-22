# Security Patterns — Solo-Code Harness

> Auto-loaded when editing auth, controllers, middleware, config, or `.env` files.

## Input Validation
- **ALL user input is untrusted** — validate type, length, format, and range
- Whitelist allowed values; never blacklist
- Validate at the boundary (API gateway, controller) before data enters business logic

## SQL Injection Prevention
- **Use parameterized queries** — never string interpolation
- Python: `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`
- TypeScript: `pool.query("SELECT * FROM users WHERE id = $1", [userId])`
- Never: `f"SELECT * FROM users WHERE id = {user_id}"`

## Credential Management
- **Never hardcode credentials** — use environment variables
- API keys, tokens, passwords → `os.environ.get()` or `process.env`
- Rotate secrets regularly; revoke compromised keys immediately

## Authentication & Sessions
- Session tokens: `httpOnly`, `secure`, `SameSite=Strict`
- Passwords: bcrypt/scrypt/argon2 — never MD5/SHA1
- Tokens: `crypto.randomBytes()` — never `Math.random()`
- JWT: Set expiration, verify signature, never store secrets in payload

## Logging Safety
- **Never log PII**, passwords, tokens, or full credit card numbers
- Mask sensitive fields: `email.replace(/(.{3}).*(@.*)/, '$1***$2')`
- Log levels: DEBUG (dev only), INFO (prod safe), WARN, ERROR

## XSS Prevention
- Never use `innerHTML` or `dangerouslySetInnerHTML`
- Use `textContent` or framework-managed rendering
- Sanitize user-generated content before display

## Command Injection
- Never `os.system(user_input)` or `subprocess.call(user_input, shell=True)`
- Use `subprocess.run([cmd, arg1, arg2])` with list arguments
- Never `eval()` or `exec()` with user input
