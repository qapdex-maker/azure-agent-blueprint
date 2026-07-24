# Azure Agent Blueprint — Production-Grade Multi-Agent Workflow

A reproducible, cloud-ready agent scaffold built from the Microsoft **Gold-Path**
observed across 13 repos in `Microsoft/`:
`agent-framework` · `durable-task-extension` · `mcp` · `azure-finops-agent` ·
`foundry-agent-webapp` · `get-started-with-ai-agents` · `serverless-chat-langchainjs-purview`.

## What this is
- **Dependency-free agent core** (`src/agent/base.py`) — Agent + Tool + LLMClient
  abstractions implementing MAF-style **orchestration chaining** with a bounded
  step count (no infinite tool loops).
- **MCP-compatible tools** (`src/tools/builtin.py`) — cost lookup, remediation
  script generation (**write, never delete** guardrail, per azure-finops-agent).
- **Orchestrator** (`src/orchestrator/chain.py`) — sequential multi-agent pipeline
  with pluggable checkpointing (durable-task `reliable_streaming` pattern).
- **Observability** (`src/agent/observability.py`) — OpenTelemetry + Azure Monitor
  (Application Insights), on by default (matches get-started / foundry samples).
- **Two cloud LLM backends, env-selected** (no secrets in code):
  - `src/agent/azure.py` — Azure OpenAI (endpoint 1)
  - `src/agent/foundry.py` — **Azure AI Foundry Agent Service** (endpoint 2,
    project URL). Selected when `FOUNDRY_PROJECT_ENDPOINT` is set.
- **Infra-as-Code** (`infra/main.bicep` + `azure.yaml`) — `azd up` one-command
  deploy: RG → Log Analytics + App Insights → Container App + Managed Identity.
- **Container** (`Dockerfile`, non-root) + **HTTP service** (`src/agent/service.py`).

## Architecture
```
User → Container App (svc, :8000) → Managed Identity
     → Agent loop → Tools (MCP-style) | Azure OpenAI / Foundry
     → OpenTelemetry → Application Insights
     (IaC: Bicep provisioned via azd)
```

## Local verification (no Azure needed)
```bash
cd Microsoft/azure-agent-blueprint
python -m pytest tests/ -q          # or: python tests/test_core.py
python -m src.agent.service 8000     # smoke-test HTTP endpoint
bash -n scripts/deploy.sh            # syntax-check deploy script
```
Uses `FakeLLM` so the full agent loop + tool dispatch run hermetically.

## Deploy (Gold-Path — run on an Azure-capable host)
Prereqs: `az`, `azd`, `docker` installed; Azure subscription with Azure OpenAI
or Foundry quota in the target region.

Two LLM backends are supported (selected by env, no secrets in code):
- **Azure AI Foundry Agent Service** (endpoint 2): set `FOUNDRY_PROJECT_ENDPOINT`
  to your project URL, e.g.
  `https://qmfi-research-project-resource.services.ai.azure.com/api/projects/qmfi-research-project`
  and optionally `FOUNDRY_AGENT_ID` + `FOUNDRY_API_KEY` (or Entra token).
- **Azure OpenAI** (endpoint 1): set `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`
  (+ `AZURE_OPENAI_DEPLOYMENT`, default `gpt-4o`).
If neither is set, the service falls back to `FakeLLM` (hermetic local runs).
```bash
cd Microsoft/azure-agent-blueprint
export AZURE_OPENAI_ENDPOINT="https://<your>.openai.azure.com/"
bash scripts/deploy.sh
```
`azd up` provisions infra/bicep, builds the container, and deploys to Container Apps.
Swap `FakeLLM` → `AzureOpenAIClient` (already coded in `src/agent/azure.py`) by
setting `AZURE_OPENAI_ENDPOINT` in the Bicep env block.

## Guardrails (inherited from the samples)
- Tools are **read/write, never delete**.
- Step budget bounds the agent loop.
- Tool errors are caught, never crash the loop.
- Least-privilege: non-root container + user-assigned Managed Identity (no secrets).

## Status
Verified locally: unit tests pass, service boots, deploy script syntax-checks.
**Not** deployed here — the Termux build host has no `az`/`azd`/`docker`.
Run `scripts/deploy.sh` on an Azure-enabled machine to stand up the live system.
