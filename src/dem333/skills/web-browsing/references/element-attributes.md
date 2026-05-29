# Inspecting element attributes

> Adapted from upstream [microsoft/playwright-cli — `references/element-attributes.md`](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/element-attributes.md) (Apache-2.0).
>
> **Note for this agent**: upstream uses `playwright-cli eval "…"`, which is **blocked** by the `playwright_cli` tool for safety. Use these tactics instead:
>
> - Prefer `snapshot --boxes` and `snapshot eNN` for visible attributes.
> - Use `generate-locator eNN --raw` to recover a stable selector.
> - When you truly need a DOM attribute that the snapshot omits, ask the user to confirm before doing anything else with the page, then call `console` and `requests` to gather indirect signals.

## What the snapshot gives you for free

```text
playwright_cli("snapshot")           # whole page with refs eNN
playwright_cli("snapshot e7")        # just one element + its descendants
playwright_cli("snapshot --boxes")   # include bounding boxes
```

## Recovering a selector for an element ref

```text
playwright_cli("generate-locator e5 --raw")
```

Returns a Playwright locator string (`getByRole(...)`, `getByTestId(...)`,
etc.) that you can reuse in later `click`/`fill` calls:

```text
playwright_cli("click \"getByRole('button', { name: 'Submit' })\"")
```

## Highlighting an element to confirm targeting

```text
playwright_cli("highlight e5")
playwright_cli("highlight e5 --style=\"outline: 3px dashed red\"")
playwright_cli("highlight --hide")
```
