# Browser session management

> Adapted from upstream [microsoft/playwright-cli — `references/session-management.md`](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/session-management.md) (Apache-2.0).
>
> **Note for this agent**: the wrapper passes `-s=dem333` by default. To address another browser, pass `session="<name>"` to the `playwright_cli` tool — do **not** include `-s=` in `args`.

## Named browser sessions

Each named session has independent cookies, localStorage, sessionStorage,
IndexedDB, cache, history, and tabs.

```text
playwright_cli(args="open https://app.example.com/login", session="auth")
playwright_cli(args="open https://example.com", session="public")

playwright_cli(args="fill e1 \"user@example.com\"", session="auth")
playwright_cli(args="snapshot", session="public")
```

## Listing, closing, and cleaning up

```text
playwright_cli("list")                              # list all sessions
playwright_cli("close")                             # close default browser
playwright_cli(args="close", session="auth")        # close a named browser
playwright_cli("close-all")                         # close every browser
playwright_cli("kill-all")                          # kill stale daemon procs
playwright_cli("delete-data")                       # remove default profile data
playwright_cli(args="delete-data", session="auth")  # remove named profile data
```

## Persistent profile (ask the user first)

By default, a session's profile is in-memory. To keep cookies across browser
restarts, request explicit confirmation, then:

```text
playwright_cli(args="open https://example.com --persistent", session="myproject")
playwright_cli(args="open https://example.com --profile=/path/to/profile", session="myproject")
```

## Attaching to an existing browser

```text
playwright_cli("attach --cdp=chrome")
playwright_cli("attach --cdp=msedge")
playwright_cli("attach --cdp=http://localhost:9222")
playwright_cli("attach --extension=chrome")
```

When `--session` is omitted on `attach`, the session is named after the channel
(e.g. `msedge`) so parallel attaches don't collide.

`detach` only works for sessions created via `attach`; use `close` for sessions
created via `open`:

```text
playwright_cli("detach")
playwright_cli(args="detach", session="msedge")
```

## Best practices

1. **Name sessions semantically** — e.g. `session="github-auth"`, not `"s1"`.
2. **Always clean up** — call `close` or `close-all` when finished with a task.
3. **Delete stale data** — `delete-data` reclaims disk for persistent profiles.
