# Setup & Auth — Azure Agent Blueprint

Verified setup path, including the Foundry Agent Service auth that works
**without** the Azure CLI (the CLI does not install on Termux/Android:
`platform android is not supported` when building `psutil`).

## 1. Local verification (no cloud)
```bash
bash scripts/run_tests.sh          # 5/5 tests, EXIT=0 (hermetic, FakeLLM)
python3 -m src.agent.service 8000  # boots with FakeLLM if no cloud env set
```

## 2. Cloud LLM backends — env selection
`src/agent/service.py build_llm()` picks the backend by env (no secrets in code):

| Precedence | Env set                              | Backend            |
|-----------|--------------------------------------|--------------------|
| 1         | `FOUNDRY_PROJECT_ENDPOINT`           | Foundry Agent Svc  |
| 2         | `AZURE_OPENAI_ENDPOINT`              | Azure OpenAI       |
| 3         | (neither)                            | FakeLLM (local)    |

Endpoints for this project:
```
FOUNDRY_PROJECT_ENDPOINT=https://qmfi-research-project-resource.services.ai.azure.com/api/projects/qmfi-research-project
AZURE_OPENAI_ENDPOINT=https://qmfi-research-project-resource.openai.azure.com/openai/v1
```

## 3. Foundry auth — Entra token (NOT api-key)
The Foundry quickstart authenticates with `az login` (Entra ID), not an
api-key. The `FoundryClient` therefore supports a **Bearer token**:
- reads `FOUNDRY_TOKEN` from env, OR
- shells out to `az account get-access-token` on a host with `az`, OR
- you pass `token=` at construction.

### 3a. Get a token WITHOUT the Azure CLI (Termux/Android)
`azure-cli` fails to build on Android. Use `azure-identity` (pure Python) +
device-code login instead:

```bash
pip install azure-identity                 # system python (has working cryptography)
python3 scripts/foundry_token.py           # prints the Entra token
# or:
python3 scripts/foundry_token.py --export  # prints FOUNDRY_TOKEN=...
```
The script prints a device code to `$HOME/foundry_code.txt`; open
`https://login.microsoft.com/device`, enter the code, sign in as
`AlexanderKleine@QMFIResearch.onmicrosoft.com` (tenant `885f01ab-…`).
Token scope: `https://ai.azure.com/.default`.

### 3b. Then run with the token
```bash
export FOUNDRY_PROJECT_ENDPOINT="https://qmfi-research-project-resource.services.ai.azure.com/api/projects/qmfi-research-project"
export FOUNDRY_TOKEN="<token from step 3a>"
python3 -m src.agent.service 8000
```

## 4. Azure OpenAI backend (endpoint 1)
Needs a real API key + deployment name from the Azure OpenAI resource
`qmfi-research-project-resource`:
```bash
export AZURE_OPENAI_ENDPOINT="https://qmfi-research-project-resource.openai.azure.com/openai/v1"
export AZURE_OPENAI_API_KEY="<key from portal: Keys and Endpoint>"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"   # exact deployment name in portal
python3 -m src.agent.service 8000
```
Note: the api-key `28272…` provided during setup returned HTTP 401
("invalid subscription key") for this resource — confirm the key belongs to
`qmfi-research-project-resource` (Azure OpenAI), not a Foundry project key.

## 5. Deploy (Gold-Path — requires az/azd/docker on a capable host)
```bash
cd Microsoft/azure-agent-blueprint
azd up          # or: bash scripts/deploy.sh
```
This host (Termux/Android) cannot run `azd up`; deploy from a Linux/macOS
machine or proot-distro Ubuntu with az+azd installed.

## Known issues
- `az` CLI: not installable on Android (psutil build fails).
- `azure-identity` in a venv: its `cryptography` wheel is ABI-incompatible with
  Python 3.14 on Android → install into **system** python (`pip install
  azure-identity`), which ships a compatible `cryptography 49.0.0`.
- `/tmp` is read-only on this host; write transient files to `$HOME`.
- neo MCP: listed as enabled in Hermes but its server module `neo_mcp` is not
  installed → `hermes mcp test neo` fails with "Connection closed". Separate
  from this blueprint; fix by installing the neo server package.
- M365 MCP: built-in app retained (own-Azure-app switch not required per user).
