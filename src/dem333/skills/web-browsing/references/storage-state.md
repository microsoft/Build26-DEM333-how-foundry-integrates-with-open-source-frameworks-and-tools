# Storage state (cookies, localStorage, sessionStorage)

> Adapted from upstream [microsoft/playwright-cli — `references/storage-state.md`](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/storage-state.md) (Apache-2.0).
>
> **Note for this agent**: `state-save`, `state-load`, and persistent profiles touch the user's auth material. **Always confirm with the user before calling them**, and never commit the resulting files. `run-code`-based recipes from upstream are **blocked** — use the plain commands listed below.

## Storage state files

```text
playwright_cli("state-save")                     # auto-named storage-state-<ts>.json
playwright_cli("state-save my-auth-state.json")
playwright_cli("state-load my-auth-state.json")
playwright_cli("open https://example.com")       # reload to apply cookies
```

File format (excerpt):

```json
{
  "cookies": [
    { "name": "session_id", "value": "abc123", "domain": "example.com", "path": "/", "httpOnly": true, "secure": true, "sameSite": "Lax" }
  ],
  "origins": [
    { "origin": "https://example.com", "localStorage": [ { "name": "theme", "value": "dark" } ] }
  ]
}
```

## Cookies

```text
playwright_cli("cookie-list")
playwright_cli("cookie-list --domain=example.com")
playwright_cli("cookie-list --path=/api")
playwright_cli("cookie-get session_id")
playwright_cli("cookie-set session abc123")
playwright_cli("cookie-set session abc123 --domain=example.com --path=/ --httpOnly --secure --sameSite=Lax")
playwright_cli("cookie-set remember_me token123 --expires=1735689600")
playwright_cli("cookie-delete session_id")
playwright_cli("cookie-clear")
```

## localStorage

```text
playwright_cli("localstorage-list")
playwright_cli("localstorage-get token")
playwright_cli("localstorage-set theme dark")
playwright_cli("localstorage-set user_settings '{\"theme\":\"dark\",\"language\":\"en\"}'")
playwright_cli("localstorage-delete token")
playwright_cli("localstorage-clear")
```

## sessionStorage

```text
playwright_cli("sessionstorage-list")
playwright_cli("sessionstorage-get form_data")
playwright_cli("sessionstorage-set step 3")
playwright_cli("sessionstorage-delete step")
playwright_cli("sessionstorage-clear")
```

## Common pattern: reuse an authenticated state

```text
# Step 1 — log in once (with user-supplied credentials).
playwright_cli("open https://app.example.com/login")
playwright_cli("snapshot")
playwright_cli("fill e1 \"user@example.com\"")
playwright_cli("fill e2 \"<password from user>\"")
playwright_cli("click e3")

# Step 2 — save the authenticated state after explicit user OK.
playwright_cli("state-save auth.json")

# Step 3 — in a later turn, restore and skip the login.
playwright_cli("state-load auth.json")
playwright_cli("open https://app.example.com/dashboard")
```

## Security notes

- Never commit storage state files containing auth tokens.
- Treat any `*.json` storage state as a secret artifact.
- Prefer in-memory (default) sessions for one-off tasks.
