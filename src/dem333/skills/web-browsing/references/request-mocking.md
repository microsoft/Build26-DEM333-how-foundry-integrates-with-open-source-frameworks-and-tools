# Request mocking

> Adapted from upstream [microsoft/playwright-cli — `references/request-mocking.md`](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/request-mocking.md) (Apache-2.0).
>
> **Note for this agent**: only the static `route` / `unroute` commands are available here. Upstream's `run-code` recipes (conditional responses, response modification, simulated network failures, delayed responses) are **blocked** by the wrapper for safety.

## Route commands

```text
# Mock with custom status.
playwright_cli("route \"**/*.jpg\" --status=404")

# Mock with JSON body.
playwright_cli("route \"**/api/users\" --body='[{\"id\":1,\"name\":\"Alice\"}]' --content-type=application/json")

# Mock with custom response headers.
playwright_cli("route \"**/api/data\" --body='{\"ok\":true}' --header=\"X-Custom: value\"")

# Strip request headers before they leave the browser.
playwright_cli("route \"**/*\" --remove-header=cookie,authorization")

# Inspect and remove routes.
playwright_cli("route-list")
playwright_cli("unroute \"**/*.jpg\"")
playwright_cli("unroute")
```

## URL patterns

```text
**/api/users           Exact path match
**/api/*/details       Wildcard in path
**/*.{png,jpg,jpeg}    Match file extensions
**/search?q=*          Match query parameters
```

## When you need conditional logic

The wrapper blocks `run-code`/`eval`, so dynamic route handlers cannot be
expressed in this agent. If a task truly requires inspecting the request body
or modifying a real response, escalate to the user — they can run the upstream
`playwright-cli` themselves in a terminal.
