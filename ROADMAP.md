# Roadmap — Azure Agent Blueprint

Status: **MVP complete & verified locally + Live Foundry call working**.
Production `azd up` deploy not yet executed (no `az`/`azd`/`docker` on the
build host). Azure OpenAI call not exercised (key issue). See `README.md`.

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

## Phase 1 — Cloud LLM backends (✅ code, ✅ Foundry live verified)
- [x] Azure OpenAI client (`src/agent/azure.py`) — endpoint
      `https://qmfi-research-project-resource.openai.azure.com/openai/v1`.
- [x] Foundry Agent Service client (`src/agent/foundry.py`) — endpoint
      `.../api/projects/qmfi-research-project`, **OpenAI Responses protocol**
      (`/agents/{id}/endpoint/protocols/openai/responses`), api-version
      `2025-05-15-preview` (verified).
- [x] Env-based backend selection (`src/agent/service.py` `build_llm()`):
      Foundry > Azure OpenAI > FakeLLM. **No secrets in code.**
- [x] **Live Foundry call VERIFIED (2026-07-25):** Entra token via
      `azure-identity` device-code (az CLI not installable on Android);
      `FoundryClient.complete()` returns real model output (gpt-5.4, agent
      `NatureLM-Idun-5-MoE`). Model: `gpt-5.4-2026-03-05`.
- [ ] **Live call test** against Azure OpenAI (needs valid `AZURE_OPENAI_API_KEY`
      + deployment name for `qmfi-research-project-resource`). The key
      `28272…` returned HTTP 401 (wrong resource / expired) — obtain a valid
      key from the portal to close this.

## Phase 2 — Infrastructure & Deploy (✅ code, ⬜ not deployed)
- [x] Bicep IaC (`infra/main.bicep`): RG → Log Analytics + App Insights →
      Container App + Managed Identity; Foundry/AOAI env vars wired.
- [x] `azure.yaml` + `Dockerfile` (non-root) + `scripts/deploy.sh` (azd up).
- [x] `scripts/sync_to_github.sh` (isolated working copy → GitHub push).
- [x] `scripts/foundry_token.py` — device-code token helper (azure-identity).
- [ ] **`azd up` executed** on an Azure-capable host. Not run here (no toolchain).
- [ ] **Container image built & pushed** to ACR / MCR. Not run here.
- [ ] **End-to-end smoke test** of the deployed Container App HTTP endpoint.

## Phase 3 — Microsoft 365 MCP integration (✅ Hermes side, ⬜ blueprint side)
- [x] M365 MCP registered in Hermes (`microsoft365`, 183 tools, login valid,
      token persistent in `~/.cache/ms365-mcp/`). Built-in app (53003 risk on
      admin scopes).
- [x] **Switch to own Azure app NOT required** (user decision 2026-07-25) —
      built-in app retained; admin-scope gap accepted for now.
- [ ] **Expose M365 tools inside the blueprint agent** (not via Hermes MCP —
      the container would call Microsoft Graph directly with its own token,
      or the agent runtime would bridge to the Hermes MCP). Open design decision.

## Phase 3b — Web presence / landing page (✅ done)
- [x] Roadmap + repo structure on GitHub (`qapdex-maker/azure-agent-blueprint`).
- [x] **Landing page** (`site/index.html`) — self-contained HTML/CSS (stitch/jules
      CLI not available on this host, hand-built per web-dev conventions).
- [x] `docs/SETUP.md` — verified Foundry auth path (azure-identity device-code,
      api-version, agent route).

## Phase 4 — Hardening & next features (⬜)
- [ ] Real LLM tool-calling (parse native function_call, not scripted TOOL()).
- [ ] Durable checkpointing backend (Redis, per durable-task `reliable_streaming`).
- [ ] Auth on the HTTP service (Entra ID / API key) — currently open.
- [ ] CI: run `run_tests.sh` on push (GitHub Actions).
- [ ] Cost/usage telemetry dashboard (App Insights already wired).
- [ ] Multi-region / failover for the Container App.
- [ ] Wire `NatureLM-Idun-5-MoE` tools (web_search, memory_search) as blueprint
      tools so the agent can use them via the Foundry responses protocol.

## Known blockers / risks
1. Build host lacks `az`/`azd`/`docker` → Phase 2 deploy must run elsewhere
   (proot-distro ubuntu not installed; az CLI fails to build on Android).
2. Azure OpenAI key `28272…` → HTTP 401 (wrong/expired key). Obtain a valid
   key for `qmfi-research-project-resource` to verify Phase 1 AOAI path.
3. M365 built-in app → 53003 on admin scopes until own Azure app is wired.
4. neo MCP: listed enabled in Hermes but server module `neo_mcp` not installed
   → `hermes mcp test neo` fails ("Connection closed"). Separate from blueprint.

## How to verify current state
```bash
bash scripts/run_tests.sh          # 5/5 tests, EXIT=0
python3 -m src.agent.service 8000  # boots (FakeLLM); Foundry/AOAI if env set
# Live Foundry call (needs fresh token):
python3 scripts/foundry_token.py --export   # FOUNDRY_TOKEN=...
export FOUNDRY_PROJECT_ENDPOINT="https://qmfi-research-project-resource.services.ai.azure.com"
export FOUNDRY_AGENT_ID="NatureLM-Idun-5-MoE"
python3 -m src.agent.service 8000  # now uses live Foundry
```
