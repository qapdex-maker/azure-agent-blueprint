# Tree — ~/repo/own/Microsoft/

Source of truth: `/data/data/com.termux/files/home/repo/own/Microsoft/`
(13 Microsoft repos explored + `azure-agent-blueprint` built from them)

## Repos (cloned from Microsoft/ during exploration)
```
Microsoft/
├── agent-framework/                         # MAF: Agent + Tool + orchestration (Python/.NET)
├── durable-task-extension-for-agent-framework/  # reliable_streaming checkpointing
├── mcp/                                      # Model Context Protocol (servers + SDK)
├── azure-finops-agent/                       # cost lookup + remediation (write-never-delete guardrail)
├── foundry-agent-webapp/                     # AI Foundry Agent Service reference webapp
├── get-started-with-ai-agents/               # minimal agent quickstart (observability on by default)
├── serverless-chat-langchainjs-purview/      # serverless chat + Purview guardrails
├── microsoft365-agents-toolkit-extension/    # M365 Agents Toolkit (Teams/Outlook)
├── function-calling-data-synthesizer/       # tool/function-calling data gen
├── azuresandbox/                             # sandbox runtime for agents
├── AzureLocal/                               # Azure Local (HCI) docs + scripts (not agent-related)
└── msdocs-tomcat-mysql-sample-app/           # sample app (Java/Tomcat/MySQL, not agent)
```

## azure-agent-blueprint/ — built from the Gold-Path above
```
azure-agent-blueprint/
├── README.md                  # Gold-Path overview
├── ROADMAP.md                 # phased plan (Phase 1 Foundry LIVE verified)
├── azure.yaml                 # azd config (azd up)
├── Dockerfile                 # python:3.12-slim, non-root
├── requirements.txt           # openai, azure-monitor-opentelemetry, opentelemetry-api, pytest, httpx
├── .gitignore                 # excludes .env, __pycache__, token caches
├── docs/
│   └── SETUP.md               # verified Foundry auth (azure-identity device-code, no az CLI)
├── infra/
│   └── main.bicep             # RG→LogAnalytics+AppInsights→ContainerApp+ManagedIdentity
├── site/
│   └── index.html             # landing page (self-contained HTML/CSS)
├── src/
│   ├── agent/
│   │   ├── base.py            # Agent + Tool + LLMClient (MAF-style chaining, bounded steps)
│   │   ├── fakellm.py         # hermetic local LLM (tests)
│   │   ├── azure.py           # Azure OpenAI client (endpoint 1)
│   │   ├── foundry.py         # Foundry Agent Service client (endpoint 2, Responses protocol)
│   │   ├── observability.py   # OpenTelemetry + Azure Monitor
│   │   └── service.py         # HTTP service (env backend selection)
│   ├── orchestrator/
│   │   └── chain.py          # multi-agent sequential pipeline
│   ├── tools/
│   │   └── builtin.py         # MCP-compatible cost/remediation/clock tools
│   └── (pycache excluded)
├── tests/
│   └── test_core.py           # 5 unit tests (all pass)
└── scripts/
    ├── deploy.sh              # azd up wrapper (isolated, trap-cleanup)
    ├── run_tests.sh           # mktemp isolated + py_compile + pytest
    ├── sync_to_github.sh      # isolated working copy → GitHub push
    └── foundry_token.py       # Entra device-code token helper (azure-identity)
```

## Notes
- 13 source repos were explored (see session summary) to derive the Gold-Path.
- `azure-agent-blueprint` is the deliverable, pushed to
  `github.com/qapdex-maker/azure-agent-blueprint` (public).
- Live Foundry call verified 2026-07-25 (gpt-5.4, agent NatureLM-Idun-5-MoE,
  api-version 2025-05-15-preview).
- `AzureLocal/` and `msdocs-tomcat-mysql-sample-app/` are out-of-scope
  (infra/sample-app, not agent frameworks).
