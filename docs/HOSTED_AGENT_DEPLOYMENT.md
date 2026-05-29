# Deploy as a Microsoft Foundry hosted agent

This demo can run locally or as a Microsoft Foundry hosted agent. Hosted mode packages the LangGraph/OpenClaw agent into a container, publishes it to Azure Container Registry, and exposes it through the Foundry Responses protocol. The same hosted agent can also be exposed through Foundry A2A for the Copilot CLI finale.

The demo assumes Work IQ Mail MCP is already configured and working. The hosted agent intentionally starts with the mail MCP tools enabled; missing or invalid Work IQ settings should fail fast instead of silently disabling mailbox capabilities.

Do not commit passwords, tokens, `.env` files, MSAL caches, or App Insights connection strings. Keep those values in your shell, your CI/CD secret store, or your Foundry deployment environment.

## 1. Prerequisites

You need:

1. Azure CLI signed in to the subscription that owns the Foundry project.
2. An Azure AI Foundry account and project.
3. An Azure Container Registry that the Foundry project identity can pull from.
4. OpenAI-compatible model access for `init_chat_model("openai:gpt-5.2")`, either preconfigured in the hosted environment or supplied through secret-backed environment variables.
5. A configured Work IQ Mail MCP tenant and Entra public-client app registration.
6. An Application Insights resource if you want hosted traces.

Set these values for your environment:

```bash
export AZURE_SUBSCRIPTION_ID="<subscription-id>"
export AZURE_RESOURCE_GROUP="<resource-group>"
export AZURE_AI_ACCOUNT_NAME="<foundry-account-name>"
export AZURE_AI_PROJECT_NAME="<foundry-project-name>"
export AZURE_AI_PROJECT_ENDPOINT="https://<foundry-account-name>.services.ai.azure.com/api/projects/<foundry-project-name>"
export AZURE_CONTAINER_REGISTRY_NAME="<acr-name>"
export HOSTED_AGENT_NAME="dem333-openclaw-agent"
export APPLICATION_INSIGHTS_NAME="<app-insights-name>"

export AZURE_TENANT_ID="<work-iq-tenant-id>"
export AZURE_CLIENT_ID="<entra-public-client-app-id>"

# Omit these env entries below if your hosted environment already provides OpenAI-compatible access.
export OPENAI_BASE_URL="https://<foundry-account-name>.services.ai.azure.com/openai/v1"
export OPENAI_API_KEY="<openai-compatible-api-key>"
```

Before the hosted demo, confirm that your demo environment already has the required Work IQ auth bootstrap in place. This branch does not add an alternate mailbox mode, copy MSAL caches into the image, or accept delegated tokens through environment variables; it assumes the configured Work IQ MCP/auth path is available at runtime. Do not store the account password in this repository or in shell history.

Then move to the container build context:

```bash
cd src
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
```

## 2. Build and push the container image

Use a timestamped tag for every deployment so Foundry pulls a unique image version:

```bash
export TAG=custom-openclaw-$(date -u +%Y%m%d%H%M%S)
export IMAGE="${AZURE_CONTAINER_REGISTRY_NAME}.azurecr.io/${HOSTED_AGENT_NAME}:${TAG}"

az acr build \
  --registry "$AZURE_CONTAINER_REGISTRY_NAME" \
  --image "${HOSTED_AGENT_NAME}:${TAG}" \
  --platform linux/amd64 \
  --source-acr-auth-id "[caller]" \
  .
```

## 3. Create or update the hosted agent

Retrieve the App Insights connection string into a shell variable instead of writing it to a file:

```bash
export APPLICATION_INSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --app "$APPLICATION_INSIGHTS_NAME" \
  --query connectionString -o tsv)
```

Deploy the hosted agent with the Responses protocol:

```bash
az cognitiveservices agent create \
  --subscription "$AZURE_SUBSCRIPTION_ID" \
  --account-name "$AZURE_AI_ACCOUNT_NAME" \
  --project-name "$AZURE_AI_PROJECT_NAME" \
  --name "$HOSTED_AGENT_NAME" \
  --image "$IMAGE" \
  --cpu 1 \
  --memory 2Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --protocol responses \
  --protocol-version 1.0.0 \
  --skip-acr-check \
  --env \
    AZURE_AI_PROJECT_ENDPOINT="$AZURE_AI_PROJECT_ENDPOINT" \
    OPENAI_BASE_URL="$OPENAI_BASE_URL" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    AZURE_TENANT_ID="$AZURE_TENANT_ID" \
    AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
    APPLICATION_INSIGHTS_CONNECTION_STRING="$APPLICATION_INSIGHTS_CONNECTION_STRING" \
    AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true \
  --timeout 900 \
  --show-logs
```

Use `APPLICATION_INSIGHTS_CONNECTION_STRING`, not `APPLICATIONINSIGHTS_CONNECTION_STRING`; the latter can be reserved by the hosted-agent service.

## 4. Invoke the hosted agent

Smoke test:

```bash
export FOUNDRY_TOKEN=$(az account get-access-token \
  --resource https://ai.azure.com \
  --query accessToken -o tsv)

curl -sS -X POST \
  -H "Authorization: Bearer ${FOUNDRY_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Foundry-Features: HostedAgents=V1Preview" \
  "${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/openai/responses?api-version=2025-11-15-preview" \
  -d '{"input":"Reply with exactly: DEM333 hosted ready","stream":false}'
```

Useful demo prompts:

```text
Can you check my latest email and summarize the top 3 messages?
```

```text
Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.
```

## 5. Enable A2A and use the Copilot CLI bridge

Enable the A2A endpoint and attach an agent card that describes the demo skills:

```bash
export FOUNDRY_TOKEN=$(az account get-access-token \
  --resource https://ai.azure.com \
  --query accessToken -o tsv)

curl -fsS -X PATCH \
  -H "Authorization: Bearer ${FOUNDRY_TOKEN}" \
  -H "Content-Type: application/json" \
  "${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}?api-version=v1" \
  -d @- <<'JSON'
{
  "agent_endpoint": {
    "version_selector": {
      "version_selection_rules": [
        {
          "type": "FixedRatio",
          "agent_version": "@latest",
          "traffic_percentage": 100
        }
      ]
    },
    "protocols": ["responses", "a2a"],
    "authorization_schemes": [
      {
        "type": "Entra",
        "isolation_key_source": {
          "kind": "Entra"
        }
      }
    ]
  },
  "agent_card": {
    "version": "1.0.0",
    "description": "DEM333 OpenClaw-style demo agent that can triage mailbox work with Work IQ Mail MCP, use markdown skills, browse the web with Playwright, and explain the Build session demo flow.",
    "skills": [
      {
        "id": "inbox-triage",
        "name": "Inbox triage",
        "description": "Inspects recent mailbox items through Work IQ Mail MCP and returns safe priority summaries without exposing message contents.",
        "tags": ["mail", "mcp", "skill"],
        "examples": ["What are the top three things in my inbox right now?"]
      },
      {
        "id": "web-browsing",
        "name": "Web browsing",
        "description": "Uses Playwright CLI browser automation to inspect public web pages and summarize findings.",
        "tags": ["browser", "playwright", "skill"],
        "examples": ["Open the DEM333 session page and summarize it in three bullets."]
      }
    ]
  }
}
JSON
```

Verify the A2A card endpoint:

```bash
export FOUNDRY_A2A_URL="${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/a2a"
export FOUNDRY_A2A_AGENT_CARD_PATH="agentCard/v0.3"

curl -fsS \
  -H "Authorization: Bearer ${FOUNDRY_TOKEN}" \
  "${FOUNDRY_A2A_URL}/${FOUNDRY_A2A_AGENT_CARD_PATH}" >/dev/null
```

The local Copilot A2A bridge in `dem333/copilot_a2a_bridge.py` lets Copilot CLI call the hosted A2A endpoint through a normal Copilot MCP tool. It uses Azure CLI to get a Foundry access token unless `FOUNDRY_A2A_TOKEN` is already set.

Direct smoke test:

```bash
cd src
uv run python -m dem333.copilot_a2a_bridge --message "Reply exactly DIRECT_A2A_OK."
```

Run Copilot CLI with the bridge:

```bash
cat > /tmp/copilot-a2a-bridge.json <<JSON
{
  "mcpServers": {
    "copilot-a2a-bridge": {
      "command": "uv",
      "args": ["--directory", "$PWD", "run", "python", "-m", "dem333.copilot_a2a_bridge"],
      "env": {
        "FOUNDRY_A2A_URL": "$FOUNDRY_A2A_URL",
        "FOUNDRY_A2A_AGENT_CARD_PATH": "agentCard/v0.3"
      }
    }
  }
}
JSON

copilot --additional-mcp-config @/tmp/copilot-a2a-bridge.json --allow-all-tools --allow-all-urls
```

Then ask Copilot CLI:

```text
Use the ask_dem333_agent tool to ask: what are the top 3 things in my inbox right now?
```
