# Deploy as a Microsoft Foundry hosted agent

This demo can run locally or as a Microsoft Foundry hosted agent. Hosted mode packages the LangGraph/OpenClaw agent into a container, publishes it to Azure Container Registry, and exposes it through the Foundry Responses protocol. The same hosted agent can also be exposed through Foundry A2A for the Copilot CLI finale.

The demo assumes Work IQ Mail MCP is already configured and working. The hosted agent intentionally starts with the mail MCP tools enabled; missing or invalid Work IQ settings should fail fast instead of silently disabling mailbox capabilities.

Do not commit passwords, tokens, `.env` files, MSAL caches, or App Insights connection strings. Keep those values in your shell, your CI/CD secret store, or your Foundry deployment environment. Treat `DEM333_MSAL_CACHE_B64` and `DEM333_MSAL_CACHE_JSON` as secrets because they can contain refresh tokens.

## 1. Prerequisites

You need:

1. Azure CLI signed in to the subscription that owns the Foundry project.
2. An Azure AI Foundry account and project.
3. An Azure Container Registry that the Foundry project identity can pull from.
4. OpenAI-compatible model access for `init_chat_model("openai:gpt-5.2")`, either preconfigured in the hosted environment or supplied through secret-backed environment variables.
5. A configured Work IQ Mail MCP tenant and Entra public-client app registration.
6. An Application Insights resource if you want hosted traces.
7. `azd` with the Foundry agent extensions if you want the CLI invoke path:
   `azd ext install microsoft.foundry`; if `azd ai agent` is unavailable, also run `azd ext install azure.ai.agents`.

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

export DEM333_WORK_IQ_TENANT_ID="<work-iq-tenant-id>"
export WORK_IQ_CLIENT_ID="<entra-public-client-app-id>"
export DEM333_MSAL_CACHE_B64="$(base64 < ~/.dem333/msal_token_cache.json | tr -d '\n')"

export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="SPAN_AND_EVENT"
export OTEL_SEMCONV_STABILITY_OPT_IN="gen_ai_latest_experimental"
export AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING="true"

# Omit these env entries below if your hosted environment already provides OpenAI-compatible access.
export OPENAI_BASE_URL="https://<foundry-account-name>.services.ai.azure.com/openai/v1"
export OPENAI_API_KEY="<openai-compatible-api-key>"
```

Before the hosted demo, sign in locally once so `~/.dem333/msal_token_cache.json` exists, then pass the serialized cache as a secret runtime environment variable. Hosted containers cannot complete an interactive browser login during readiness. For a short-lived smoke test, you can instead set `DEM333_WORK_IQ_ACCESS_TOKEN` to a Work IQ access token for `https://agent365.svc.cloud.microsoft`, but that direct-token mode only lasts until the token expires.

Do not use `AZURE_CLIENT_ID` for the Work IQ app in hosted deployments. The hosted-agent runtime uses `AZURE_CLIENT_ID` to select its managed identity for Foundry storage, so setting it to the Work IQ public app ID breaks response persistence. Use `WORK_IQ_CLIENT_ID` instead, or omit it when using `DEM333_WORK_IQ_ACCESS_TOKEN`.

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
    DEM333_WORK_IQ_TENANT_ID="$DEM333_WORK_IQ_TENANT_ID" \
    WORK_IQ_CLIENT_ID="$WORK_IQ_CLIENT_ID" \
    DEM333_MSAL_CACHE_B64="$DEM333_MSAL_CACHE_B64" \
    DEM333_DISABLE_INTERACTIVE_AUTH=true \
    DEM333_DISABLE_CACHE_WRITE=true \
    APPLICATION_INSIGHTS_CONNECTION_STRING="$APPLICATION_INSIGHTS_CONNECTION_STRING" \
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="$OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT" \
    OTEL_SEMCONV_STABILITY_OPT_IN="$OTEL_SEMCONV_STABILITY_OPT_IN" \
    AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING="$AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING" \
  --timeout 900 \
  --show-logs
```

Use `APPLICATION_INSIGHTS_CONNECTION_STRING`, not `APPLICATIONINSIGHTS_CONNECTION_STRING`; the latter can be reserved by the hosted-agent service.

The three OpenTelemetry environment variables above enable the Microsoft LangChain instrumentation path and allow App Insights spans/events to include the LangGraph agent input and output message content for the demo.

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

The local A2A directory bridge in `dem333/a2a/` lets Copilot CLI search configured A2A agents and call one through a normal Copilot MCP tool. It uses Azure CLI to get a Foundry access token unless `FOUNDRY_A2A_TOKEN` is already set.

If `APPLICATIONINSIGHTS_CONNECTION_STRING` or `APPLICATION_INSIGHTS_CONNECTION_STRING` is present, the bridge also exports a local span named `invoke_agent <agent_id>` and forwards W3C trace context to the hosted A2A endpoint. In App Insights, that local bridge span and the hosted `invoke_agent LangGraph` spans should share the same `operation_Id`.

Direct smoke test:

```bash
cd src
export APPLICATIONINSIGHTS_CONNECTION_STRING="$APPLICATION_INSIGHTS_CONNECTION_STRING"
uv run python -m dem333.a2a --search "inbox triage"
uv run python -m dem333.a2a --agent-id "$HOSTED_AGENT_NAME" --message "Reply exactly DIRECT_A2A_OK."
```

Run Copilot CLI with the bridge:

```bash
cat > /tmp/copilot-a2a-bridge.json <<JSON
{
  "mcpServers": {
    "a2a-directory": {
      "command": "uv",
      "args": ["--directory", "$PWD", "run", "python", "-m", "dem333.a2a"],
      "env": {
        "FOUNDRY_A2A_URL": "$FOUNDRY_A2A_URL",
        "FOUNDRY_A2A_AGENT_CARD_PATH": "agentCard/v0.3",
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "$APPLICATION_INSIGHTS_CONNECTION_STRING"
      }
    }
  }
}
JSON

copilot --additional-mcp-config @/tmp/copilot-a2a-bridge.json --allow-all-tools --allow-all-urls
```

Then ask Copilot CLI:

```text
Search for an agent that can triage inbox messages, then call it using A2A. Return only priority/category labels and a total message count. Do not include senders, subjects, body text, or personal data.
```

To verify trace stitching after a direct bridge or Copilot CLI call, query App Insights for a recent trace that contains both roles:

```kusto
union isfuzzy=true dependencies, traces, requests, customEvents
| where timestamp > ago(30m)
| where operation_Id == "<trace-id>"
| project timestamp, itemType, cloud_RoleName, name, message, operation_ParentId, customDimensions
| order by timestamp asc
```

Expected rows include `dem333-a2a-directory-local` / `invoke_agent <agent_id>` with `dem333.a2a.trace_context_propagated=True`, followed by hosted `dem333-openclaw-agent` or `dem333-openclaw-agent-stitched` spans such as `invoke_agent LangGraph`, `model`, and `chat gpt-5.2...`.
