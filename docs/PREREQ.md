# Prerequisites for Office 365 MCP Mail Integration

This document lists the Microsoft Entra ID and Microsoft 365 setup required for this project to access mailbox tools through the Office 365 MCP server:

- `https://agent365.svc.cloud.microsoft/agents/tenants/{tenantId}/servers/mcp_MailTools`

## 1. Microsoft Entra app registration

Create an app registration in Microsoft Entra ID.

This project supports two auth modes:

- Confidential client (recommended, and required in many tenants)
- Interactive delegated sign-in fallback (local/dev convenience)

1. Go to Microsoft Entra admin center.
2. Navigate to **Identity > Applications > App registrations**.
3. Select **New registration**.
4. Configure:
   - Name: `DEM333 Mail MCP Client` (or your preferred name)
   - Supported account types: **Accounts in this organizational directory only**
   - Redirect URI (for interactive fallback):
     - Platform: **Mobile and desktop applications**
     - URI: `http://localhost`
5. Create the app.

For confidential client auth:

1. In the app registration, open **Certificates & secrets**.
2. Create a **Client secret**.
3. Copy the secret **Value** immediately and store it securely.

Record these values from the Overview page:

- Application (client) ID
- Directory (tenant) ID

Use them for:

- `AZURE_CLIENT_ID` = Application (client) ID
- `AZURE_TENANT_ID` = Directory (tenant) ID
- `AZURE_CLIENT_SECRET` = Client secret value (required for confidential flow)

## 2. API permissions (Microsoft Graph, delegated)

Grant delegated Microsoft Graph permissions to the app registration.

1. Open the app registration.
2. Go to **API permissions**.
3. Select **Add a permission > Microsoft Graph > Delegated permissions**.
4. Add only what your scenario needs.

Recommended permissions by capability:

- `Mail.Read`: Read messages
- `Mail.Send`: Send mail
- `Mail.ReadWrite`: Create/update/move/delete messages
- `MailboxSettings.Read`: Read mailbox settings

Notes:

- This integration is intended to use delegated permissions (user context).
- Application permissions are not required for this flow.

## 3. Consent model

Your tenant policy determines who can grant consent:

- If user consent is allowed, users can grant consent at first sign-in.
- If blocked, an Entra tenant admin must grant consent.

Admin flow:

1. Go to **Enterprise applications**.
2. Open your app.
3. Go to **Permissions**.
4. Select **Grant admin consent**.

## 4. Microsoft 365 mailbox prerequisites

The signed-in identity must have:

- A licensed Exchange Online mailbox
- Access policies that allow the selected Graph delegated scopes

If using Conditional Access, ensure policies permit interactive sign-in for this app and user.

## 5. Local runtime prerequisites

This repo now uses:

- `azure-identity`
- `langchain-mcp-adapters`

Install project dependencies (from `src/`):

```bash
uv sync
```

Set environment variables before running the app:

```bash
export AZURE_TENANT_ID="<your-tenant-guid>"
export AZURE_CLIENT_ID="<your-app-client-guid>"
export AZURE_CLIENT_SECRET="<your-app-client-secret>"
```

Notes:

- If `AZURE_CLIENT_SECRET` is set, the app uses confidential-client auth.
- If not set, the app falls back to interactive browser auth.
- If you see `AADSTS7000218` (`client_assertion` or `client_secret` required), set `AZURE_CLIENT_SECRET`.

### Web browsing (Playwright CLI)

The agent's web-browsing capability shells out to Microsoft's
[`@playwright/cli`](https://github.com/microsoft/playwright-cli) (no Python
dependency — the browser runs out-of-process).

1. Install **Node.js ≥ 18** and confirm `node --version` / `npx --version`.
2. Install the CLI globally:

   ```bash
   npm install -g @playwright/cli@latest
   playwright-cli --version
   ```

   If you cannot install globally, the agent will fall back to
   `npx --no-install playwright-cli` when `playwright-cli` is on PATH; otherwise
   it returns an error explaining how to install it.

3. Trigger the one-time Chromium download (any `open` call does this):

   ```bash
   playwright-cli open about:blank --headed
   playwright-cli close
   ```

Optional environment variables:

- `PLAYWRIGHT_CLI_SESSION` — override the default named browser (`dem333`).
- `PLAYWRIGHT_CLI_HEADED=1` — make the agent open the browser headed (useful
  during live demos). Headless otherwise.

## 6. Authentication behavior in this project

The agent uses `azure-identity` and follows this order:

1. `ClientSecretCredential` when `AZURE_CLIENT_SECRET` is present
2. `InteractiveBrowserCredential` fallback when no client secret is set

What this means:

- Confidential mode does not open a browser and authenticates as the app.
- Interactive fallback opens a browser for sign-in and consent on first run.
- Tokens are cached and refreshed by the credential implementation.

Token audience/scope requested by this integration:

- `https://agent365.svc.cloud.microsoft/.default`

## 7. MCP server endpoint format

The MCP Mail server URL is tenant-specific:

```text
https://agent365.svc.cloud.microsoft/agents/tenants/{tenantId}/servers/mcp_MailTools
```

In this project, `tenantId` comes from `AZURE_TENANT_ID`.

## 8. Security and operational guidance

- Do not commit tenant IDs, client IDs tied to private environments, or any secrets in code.
- `AZURE_CLIENT_SECRET` is sensitive and must only be provided through secure environment configuration.
- Prefer environment variables for configuration.
- Use least-privilege Graph permissions and remove unused scopes.

## 9. Troubleshooting checklist

If the agent cannot access mail tools:

1. Verify `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` values.
2. If error `AADSTS7000218` appears, verify `AZURE_CLIENT_SECRET` is set and valid.
3. Confirm delegated Graph permissions are present on the app registration.
4. Confirm consent has been granted (user or admin).
5. Confirm the signed-in account has an Exchange Online mailbox.
6. Confirm tenant Conditional Access policies allow interactive authentication.
7. Retry after removing stale local tokens if account/tenant was switched.
