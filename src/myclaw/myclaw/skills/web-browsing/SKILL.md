---
name: web-browsing
description: Use this skill whenever the user asks the agent to browse the web, open a URL, look up live information online, inspect or interact with a web page, fill out a web form, click a link or button, take a screenshot of a page, or perform any task that requires a real browser. Triggers include "open the page", "go to <url>", "search the web for", "browse to", "click that button", "fill in the form", "screenshot the page", "what's on this page", or any general web-automation request.
---

# Browser Automation with playwright-cli

This agent drives a real browser through Microsoft's `@playwright/cli`. **You do
not invoke `playwright-cli` as a shell command directly.** Instead, call the
`playwright_cli` tool with the command portion as the `args` string:

```text
playwright_cli(args="open https://example.com")
playwright_cli(args="snapshot")
playwright_cli(args="click e15")
```

A persistent named browser session (`dem333`) is kept across calls, so cookies
and page state survive between tool invocations.

## Quick start

```text
playwright_cli("open")                        # open a new browser
playwright_cli("goto https://playwright.dev") # navigate
playwright_cli("click e15")                   # use refs from the snapshot
playwright_cli("type \"page.click\"")
playwright_cli("press Enter")
playwright_cli("screenshot")                  # rarely needed; snapshot is more useful
playwright_cli("close")                       # close the browser
```

## Guardrails

- **Never** submit credentials, payment info, or any sensitive data without explicit user confirmation in the current turn.
- `run-code` and `eval` are **blocked** at the tool layer for safety. Use `snapshot`, `click`, `fill`, `type`, and `press` to accomplish the task instead.
- Ask the user before calling `state-save`, `--persistent`, or anything that writes auth/cookies to disk.
- Do not navigate to or perform actions on a site the user did not ask for.
- Always cite source URLs in answers derived from page content.

## Commands

### Core

```text
playwright_cli("open")
playwright_cli("open https://example.com/")           # open and navigate
playwright_cli("goto https://playwright.dev")
playwright_cli("type \"search query\"")
playwright_cli("click e3")
playwright_cli("dblclick e7")
playwright_cli("fill e5 \"user@example.com\" --submit")   # --submit presses Enter after filling
playwright_cli("drag e2 e8")
playwright_cli("drop e4 --path=./image.png")          # drop a file onto an element
playwright_cli("drop e4 --data=\"text/plain=hello world\"")
playwright_cli("hover e4")
playwright_cli("select e9 \"option-value\"")
playwright_cli("upload ./document.pdf")
playwright_cli("check e12")
playwright_cli("uncheck e12")
playwright_cli("snapshot")
playwright_cli("dialog-accept")
playwright_cli("dialog-accept \"confirmation text\"")
playwright_cli("dialog-dismiss")
playwright_cli("resize 1920 1080")
playwright_cli("close")
```

### Navigation

```text
playwright_cli("go-back")
playwright_cli("go-forward")
playwright_cli("reload")
```

### Keyboard

```text
playwright_cli("press Enter")
playwright_cli("press ArrowDown")
playwright_cli("keydown Shift")
playwright_cli("keyup Shift")
```

### Mouse

```text
playwright_cli("mousemove 150 300")
playwright_cli("mousedown")
playwright_cli("mousedown right")
playwright_cli("mouseup")
playwright_cli("mousewheel 0 100")
```

### Save as

```text
playwright_cli("screenshot")
playwright_cli("screenshot e5")
playwright_cli("screenshot --filename=page.png")
playwright_cli("pdf --filename=page.pdf")
```

### Tabs

```text
playwright_cli("tab-list")
playwright_cli("tab-new")
playwright_cli("tab-new https://example.com/page")
playwright_cli("tab-close")
playwright_cli("tab-close 2")
playwright_cli("tab-select 0")
```

### Storage

```text
playwright_cli("state-save")                    # ask the user first
playwright_cli("state-save auth.json")
playwright_cli("state-load auth.json")

# Cookies
playwright_cli("cookie-list")
playwright_cli("cookie-list --domain=example.com")
playwright_cli("cookie-get session_id")
playwright_cli("cookie-set session_id abc123")
playwright_cli("cookie-delete session_id")
playwright_cli("cookie-clear")

# LocalStorage
playwright_cli("localstorage-list")
playwright_cli("localstorage-get theme")
playwright_cli("localstorage-set theme dark")
playwright_cli("localstorage-delete theme")
playwright_cli("localstorage-clear")

# SessionStorage
playwright_cli("sessionstorage-list")
playwright_cli("sessionstorage-get step")
playwright_cli("sessionstorage-set step 3")
playwright_cli("sessionstorage-delete step")
playwright_cli("sessionstorage-clear")
```

### Network

```text
playwright_cli("route \"**/*.jpg\" --status=404")
playwright_cli("route \"https://api.example.com/**\" --body='{\"mock\": true}'")
playwright_cli("route-list")
playwright_cli("unroute \"**/*.jpg\"")
playwright_cli("unroute")
```

### DevTools

```text
playwright_cli("console")
playwright_cli("console warning")
playwright_cli("requests")
playwright_cli("request 5")
playwright_cli("show --annotate")             # opens the live dashboard for the user
playwright_cli("generate-locator e5 --raw")
playwright_cli("highlight e5")
playwright_cli("highlight e5 --style=\"outline: 3px dashed red\"")
playwright_cli("highlight e5 --hide")
playwright_cli("highlight --hide")
```

`run-code`, `eval`, `tracing-*`, and `video-*` are intentionally omitted — they
are either blocked at the tool layer or out of scope for this agent.

## Raw output

The global `--raw` option strips page status, generated code, and snapshot
sections from the output and returns only the result value. Useful when you
just need a single string back without the surrounding chrome:

```text
playwright_cli("--raw cookie-get session_id")
playwright_cli("--raw localstorage-get theme")
playwright_cli("--raw snapshot")              # snapshot YAML only
```

For structured output wrapping every reply as JSON, pass `--json`:

```text
playwright_cli("list --json")
```

## Open parameters

```text
playwright_cli("open --browser=chrome")
playwright_cli("open --browser=firefox")
playwright_cli("open --browser=webkit")
playwright_cli("open --browser=msedge")

# Persistent profile (default profile is in-memory). Ask user before doing this.
playwright_cli("open --persistent")
playwright_cli("open --profile=/path/to/profile")

# Attach to an already-running browser
playwright_cli("attach --extension=chrome")
playwright_cli("attach --cdp=chrome")
playwright_cli("attach --cdp=http://localhost:9222")

playwright_cli("close")
playwright_cli("detach")                      # leaves an attached browser running
playwright_cli("delete-data")
```

## Snapshots

After each command, the CLI automatically returns a snapshot of the current
browser state. Example shape:

```text
### Page
- Page URL: https://example.com/
- Page Title: Example Domain
### Snapshot
[Snapshot](.playwright-cli/page-2026-02-14T19-22-42-679Z.yml)
```

Take an explicit snapshot any time you need fresh element refs:

```text
playwright_cli("snapshot")                            # default
playwright_cli("snapshot --filename=after-click.yaml") # save by name
playwright_cli("snapshot \"#main\"")                  # snapshot a subtree
playwright_cli("snapshot --depth=4")                  # cap depth for efficiency
playwright_cli("snapshot e34")                        # snapshot one element
playwright_cli("snapshot --boxes")                    # include bounding boxes
```

When the page is large, prefer `--depth=N` or `snapshot eNN` over a full-page
snapshot — the wrapper truncates output that exceeds ~16k characters.

## Targeting elements

By default, use refs (`e1`, `e15`, …) from the snapshot:

```text
playwright_cli("snapshot")
playwright_cli("click e15")
```

You can also use CSS selectors or Playwright locators:

```text
playwright_cli("click \"#main > button.submit\"")
playwright_cli("click \"getByRole('button', { name: 'Submit' })\"")
playwright_cli("click \"getByTestId('submit-button')\"")
```

## Browser sessions

The wrapper passes `-s=dem333` automatically so calls share one browser. To use
a different named browser, pass the `session` argument to the tool:

```text
playwright_cli(args="open https://example.com --persistent", session="mysession")
playwright_cli(args="click e6", session="mysession")
playwright_cli(args="close", session="mysession")
playwright_cli(args="list")
playwright_cli(args="close-all")
```

See [references/session-management.md](references/session-management.md) for
multi-session patterns.

## Example: form submission

```text
playwright_cli("open https://example.com/form")
playwright_cli("snapshot")
playwright_cli("fill e1 \"user@example.com\"")
playwright_cli("fill e2 \"password123\"")    # only with user confirmation
playwright_cli("click e3")
playwright_cli("snapshot")
playwright_cli("close")
```

## Example: multi-tab workflow

```text
playwright_cli("open https://example.com")
playwright_cli("tab-new https://example.com/other")
playwright_cli("tab-list")
playwright_cli("tab-select 0")
playwright_cli("snapshot")
playwright_cli("close")
```

## Example: interactive UI review

When the user asks for "UI review", "design feedback", or to "ask me what I
think", open the page and launch the annotation dashboard. The user draws boxes
and types comments; you receive the annotated screenshot and notes in the
returned snapshot.

```text
playwright_cli("open https://example.com")
playwright_cli("show --annotate")
```

## Specific tasks

- **Inspecting element attributes** — [references/element-attributes.md](references/element-attributes.md)
- **Browser session management** — [references/session-management.md](references/session-management.md)
- **Storage state (cookies, localStorage)** — [references/storage-state.md](references/storage-state.md)
- **Request mocking** — [references/request-mocking.md](references/request-mocking.md)

## Source

Adapted from [microsoft/playwright-cli `skills/playwright-cli/SKILL.md`](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md)
(Apache-2.0). All `playwright-cli <args>` examples were rewritten as
`playwright_cli("<args>")` to target this agent's wrapper tool.
