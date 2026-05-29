# Prerequisites and Configuration

This document organizes setup for:

- Office 365 (Work IQ Mail MCP server)
- Playwright CLI browser automation

## 1. Base local setup (required)

This repository uses `uv` for Python package management and environment-aware commands.

1. Install Python and uv.
2. From [src](../src), install dependencies:

```bash
uv sync
```

3. Install Node.js 18+ (required for Playwright CLI):

```bash
node --version
npx --version
```

## 2. Office 365 setup (Work IQ Mail MCP)

This project connects to:

```text
https://agent365.svc.cloud.microsoft/agents/tenants/{tenantId}/servers/mcp_MailTools
```

The `tenantId` value comes from `AZURE_TENANT_ID`.

### 2.1 Entra app registration

Create an app registration in Microsoft Entra ID.

1. Go to Microsoft Entra admin center.
2. Navigate to **Identity > Applications > App registrations**.
3. Select **New registration**.
4. Configure:
   - Name: `DEM333 Mail MCP Client` (or your preferred name)
   - Supported account types: **Accounts in this organizational directory only**
   - Redirect URI:
     - Platform: **Mobile and desktop applications**
     - URI: `http://localhost`
5. In **Authentication > Advanced settings**, set **Allow public client flows** to **Yes**.

Record from the app Overview page:

- Application (client) ID
- Directory (tenant) ID

Use them as:

- `AZURE_CLIENT_ID` = Application (client) ID
- `AZURE_TENANT_ID` = Directory (tenant) ID

Important:

- `AZURE_CLIENT_SECRET` is not used by this repository and is not required.

### 2.2 API permissions (Microsoft Graph delegated)

1. Open the app registration.
2. Go to **API permissions**.
3. Select **Add a permission > Microsoft Graph > Delegated permissions**.
4. Add only what your scenario needs.

Typical delegated permissions for mail flows:

- `Mail.Read`
- `Mail.Send`
- `Mail.ReadWrite`
- `MailboxSettings.Read`

Notes:

- This integration uses delegated user sign-in.
- Application permissions are not required.

### 2.3 Consent and mailbox requirements

- If user consent is blocked in your tenant, an Entra admin must grant consent.
- The signed-in user must have a licensed Exchange Online mailbox.
- Conditional Access policies must allow interactive sign-in for this app/user.

### 2.4 Environment variables for mail MCP

Set before running:

```bash
export AZURE_TENANT_ID="<your-tenant-guid>"
export AZURE_CLIENT_ID="<your-app-client-guid>"
```

Optional:

- `DEM333_MSAL_CACHE_PATH` to override the local token cache file location.

Authentication behavior in this repo:

- Uses MSAL `PublicClientApplication` interactive delegated sign-in.
- Reuses cached tokens from local disk across runs.
- Requests scope `https://agent365.svc.cloud.microsoft/.default`.

## 3. Playwright CLI setup (required for web browsing tool)

The web browsing tool executes Microsoft's [@playwright/cli](https://github.com/microsoft/playwright-cli).

1. Install CLI globally:

```bash
npm install -g @playwright/cli@latest
playwright-cli --version
```

2. Perform one-time browser download and session bootstrap:

```bash
playwright-cli open about:blank --headed
playwright-cli close
```

Notes:

- The tool first tries `playwright-cli` from PATH.
- If not found, it falls back to `npx --no-install playwright-cli`.

Optional environment variables:

- `PLAYWRIGHT_CLI_SESSION` to override session name (`dem333` by default).
- `PLAYWRIGHT_CLI_HEADED=1` to force headed mode for `open` commands.

## 4. Final configuration checklist

Before running `uv run main.py` from [src](../src), verify:

1. `uv sync` completed.
2. Node.js and `@playwright/cli` are installed and `playwright-cli --version` works.
3. `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` are set.
4. Entra app is configured as a public client with `http://localhost` redirect URI.
5. Graph delegated permissions and tenant consent are in place.
6. The signed-in user has an Exchange Online mailbox.

## 5. Troubleshooting

If mail tools fail:

1. Verify `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` values.
2. If error `AADSTS7000218` appears, ensure the app is configured as a public client:
   - **Allow public client flows = Yes**
   - **Mobile/Desktop redirect URI includes `http://localhost`**
3. Confirm delegated Graph permissions are present and consented.
4. Confirm the signed-in account has an Exchange Online mailbox.
5. Retry after clearing stale MSAL cache if account or tenant changed.
