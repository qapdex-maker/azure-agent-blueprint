# Roadmap — Azure Agent Blueprint

Status: **MVP complete & verified locally**. Production deploy not yet executed
(no `az`/`azd`/`docker` on the build host). Live LLM/Foundry calls not yet
exercised (no API key in scope). See `README.md` for the full picture.

Legend: ✅ done · 🟡 partial/local-only · ⬜ open

## Phase 0 — Foundation (✅ done)
- [x] Agent core (`src/agent/base.py`): Agent + Tool + LLMClient, orchestration
      chaining with bounded step count (no infinite tool loops).
- [x] MCP-compatible tools (`src/tools/builtin.py`): cost lookup, remediation
      script generation (**write, never delete** guardrail).
- [x] Multi-agent orchestrator (`src/orchestrator/chain.py`): sequential pipeline
      with pluggable checkpointing (durable-task pattern).
- [x] Observability (`src/agent/observability.py`): OpenTelemetry + Azure Monitor,
      on by default.
- [x] Local verification: 5/5 unit tests pass, `run_tests.sh` (isolated, trap-cleanup).

## Phase 1 — Cloud LLM backends (✅ code, 🟡 untested live)
- [x] Azure OpenAI client (`src/agent/azure.py`) — endpoint
      `https://qmfi-research-project-resource.openai.azure.com/openai/v1`.
- [x] Foundry Agent Service client (`src/agent/foundry.py`) — endpoint
      `https://qmfi-research-project-resource.services.ai.azure.com/api/projects/qmfi-research-project`.
- [x] Env-based backend selection (`src/agent/service.py` `build_llm()`):
      Foundry > Azure OpenAI > FakeLLM. **No secrets in code.**
- [ ] **Live call test** against Foundry project (needs `FOUNDRY_API_KEY` or
      Entra token + `FOUNDRY_AGENT_ID`). Not run — key not provided.
- [ ] **Live call test** against Azure OpenAI (needs `AZURE_OPENAI_API_KEY` +
      deployment name). Not run — key not provided.

## Phase 2 — Infrastructure & Deploy (✅ code, ⬜ not deployed)
- [x] Bicep IaC (`infra/main.bicep`): RG → Log Analytics + App Insights →
      Container App + Managed Identity; Foundry/AOAI env vars wired.
- [x] `azure.yaml` + `Dockerfile` (non-root) + `scripts/deploy.sh` (azd up).
- [x] `scripts/sync_to_github.sh` (isolated working copy → GitHub push).
- [ ] **`azd up` executed** on an Azure-capable host. Not run here (no toolchain).
- [ ] **Container image built & pushed** to ACR / MCR. Not run here.
- [ ] **End-to-end smoke test** of the deployed Container App HTTP endpoint.

## Phase 3 — Microsoft 365 MCP integration (✅ Hermes side, ⬜ blueprint side)
- [x] M365 MCP registered in Hermes (`microsoft365`, 183 tools, login valid,
      token persistent in `~/.cache/ms365-mcp/`). Built-in app (53003 risk on
      admin scopes).
- [ ] **Switch M365 to own Azure app** (`98801190-…` client + `qmfiresearch`
      tenant) to unlock admin scopes (Planner, full SharePoint, Teams-admin).
- [ ] **Expose M365 tools inside the blueprint agent** (not via Hermes MCP —
      the container would call Microsoft Graph directly with its own token,
      or the agent runtime would bridge to the Hermes MCP). Open design decision.

## Phase 4 — Hardening & next features (⬜)
- [ ] Real LLM tool-calling (parse native function_call, not scripted TOOL()).
- [ ] Durable checkpointing backend (Redis, per durable-task `reliable_streaming`).
- [ ] Auth on the HTTP service (Entra ID / API key) — currently open.
- [ ] CI: run `run_tests.sh` on push (GitHub Actions).
- [ ] Cost/usage telemetry dashboard (App Insights already wired).
- [ ] Multi-region / failover for the Container App.

## Known blockers / risks
1. Build host lacks `az`/`azd`/`docker` → Phase 2 deploy must run elsewhere.
2. Live LLM calls blocked on API key (will be provided at runtime, never in code).
3. M365 built-in app → 53003 on admin scopes until own Azure app is wired.
4. Foundry chat/completions response shape assumed OpenAI-compatible; verify
   against the actual project endpoint on first live call.

## How to verify current state
```bash
bash scripts/run_tests.sh          # 5/5 tests, EXIT=0
python3 -m src.agent.service 8000  # boots (FakeLLM); Foundry/AOAI if env set
```
