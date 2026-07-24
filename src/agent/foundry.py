"""Foundry Agent Service client (Azure AI Foundry project endpoint).

Targets the Foundry Agent Service REST API exposed under an AI Foundry
project, e.g.:
    https://<project-resource>.services.ai.azure.com/api/projects/<project>

This client mirrors the `AzureOpenAIClient` interface (same `complete()`
contract) so it can be dropped into any Agent as the LLM backend. It is
**import-guarded** (httpx) and **never** exercises a real call in local
verification — it requires a live Foundry project + credential.

Auth (per the Foundry quickstart: `az login` before running scripts):
  Foundry Agent Service uses **Entra ID** (Bearer token from
  `az account get-access-token`), NOT an api-key, for the project endpoint.
  Provide the token via `FOUNDRY_TOKEN`, or let the client shell out to
  `az account get-access-token` on a host where `az` is installed. An
  `api-key` is also accepted as a fallback (some deployments expose one).
No client secret is hardcoded; all creds come from env / managed identity.
"""
from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from src.agent.base import LLMClient, Message, Tool

_TOKEN_RESOURCE = "https://ai.azure.com"  # Entra audience for Foundry


class FoundryClient(LLMClient):
    """Async client for Azure AI Foundry Agent Service.

    Endpoint pattern (your project):
      base   = https://qmfi-research-project-resource.services.ai.azure.com
      project= qmfi-research-project
      chat   = {base}/api/projects/{project}/openai/chat/completions

    The `agent_id` is the Foundry agent you created in the portal (or via
    `az ai project agent create`). If None, the client calls the project's
    default chat completions endpoint.
    """

    def __init__(
        self,
        project_endpoint: str,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        token: Optional[str] = None,
        api_version: str = "2024-05-01-preview",
    ) -> None:
        self.project_endpoint = project_endpoint.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
        self._token = token
        self.api_version = api_version
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import httpx  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "httpx not installed; `pip install httpx` (already in requirements)."
                ) from e
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    def _chat_url(self) -> str:
        if self.agent_id:
            return (
                f"{self.project_endpoint}/api/projects/"
                f"qmfi-research-project/aiagents/{self.agent_id}/chat/completions"
            )
        # project-level default chat completions (OpenAI-compatible)
        return f"{self.project_endpoint}/openai/chat/completions"

    def _resolve_token(self) -> Optional[str]:
        if self._token:
            return self._token
        env_tok = os.environ.get("FOUNDRY_TOKEN")
        if env_tok:
            return env_tok
        # fall back to az CLI on a host where it is available
        try:
            out = subprocess.run(
                ["az", "account", "get-access-token",
                 "--resource", _TOKEN_RESOURCE, "--query", "accessToken",
                 "-o", "tsv"],
                capture_output=True, text=True, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["api-key"] = self.api_key
        else:
            tok = self._resolve_token()
            if tok:
                h["Authorization"] = f"Bearer {tok}"
        return h

    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        client = self._ensure_client()
        payload: dict = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if tools:
            payload["tools"] = [t.to_schema() for t in tools]
        resp = await client.post(self._chat_url(), headers=self._headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Foundry chat/completions returns OpenAI-compatible shape
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return Message(role="assistant", content=content or "")
