"""Minimal ASGI/HTTP service entry point for the agent container.

In production this exposes the agent over HTTP (port 8000, matches Bicep
ingress targetPort). Uses only stdlib so it runs without extra deps; swap for
FastAPI in a real deployment. Local `python -m src.agent.service` starts it.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.agent.base import Agent, Message
from src.agent.fakellm import FakeLLM
from src.agent.azure import AzureOpenAIClient
from src.agent.foundry import FoundryClient
from src.tools.builtin import CostLookupTool, RemediationScriptTool, ClockTool


def build_llm():
    """Select the LLM backend from env (no secrets hardcoded).

    Precedence:
      1. FOUNDRY_PROJECT_ENDPOINT set  -> Foundry Agent Service client
      2. AZURE_OPENAI_ENDPOINT set     -> Azure OpenAI client
      3. neither                       -> FakeLLM (local/test)
    API key / token is read from env at call time, never stored in code.
    """
    foundry_ep = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    aoai_ep = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if foundry_ep:
        return FoundryClient(
            project_endpoint=foundry_ep,
            api_key=os.environ.get("FOUNDRY_API_KEY"),
            agent_id=os.environ.get("FOUNDRY_AGENT_ID"),
        )
    if aoai_ep:
        return AzureOpenAIClient(
            endpoint=aoai_ep,
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        )
    return FakeLLM()


def build_agent() -> Agent:
    agent = Agent(
        name="blueprint",
        system_prompt="You are the Azure Agent Blueprint service.",
        llm=build_llm(),
        tools=[CostLookupTool(), RemediationScriptTool(), ClockTool()],
    )
    return agent


AGENT = build_agent()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = body.get("prompt", "")
        answer = asyncio.run(AGENT.chat(prompt))
        payload = json.dumps({"answer": answer}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002  (silence default logging noise)
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"[service] listening on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
