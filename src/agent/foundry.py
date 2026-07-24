"""Foundry Agent Service client (Azure AI Foundry project endpoint).

Targets the Foundry Agent Service REST API exposed under an AI Foundry
project, e.g.:
    https://<project-resource>.services.ai.azure.com/api/projects/<project>

This client mirrors the `AzureOpenAIClient` interface (same `complete()`
contract) so it can be dropped into any Agent as the LLM backend. It is
**import-guarded** (httpx) and **never** exercises a real call in local
verification — it requires a live Foundry project + credential.

Auth: Foundry Agent Service accepts either an API key
(`FOUNDRY_API_KEY`) or Entra ID token (`az account get-access-token`).
No client secret is hardcoded; both come from env / managed identity.
"""
from __future__ import annotations

from typing import List, Optional

from src.agent.base import LLMClient, Message, Tool


class FoundryClient(LLMClient):
    """Async client for Azure AI Foundry Agent Service.

    Endpoint pattern (your project):
      base   = https://qmfi-research-project-resource.services.ai.azure.com
      project= qmfi-research-project
      chat   = {base}/api/projects/{project}/aiagents/{agent_id}/chat/completions

    The `agent_id` is the Foundry agent you created in the portal (or via
    `az ai project agent create`). If None, the client calls the project's
    default chat completions endpoint.
    """

    def __init__(
        self,
        project_endpoint: str,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_version: str = "2024-05-01-preview",
    ) -> None:
        # normalize: accept either full project URL or base+project
        self.project_endpoint = project_endpoint.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
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
        # project-level default chat completions
        return f"{self.project_endpoint}/openai/chat/completions"

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["api-key"] = self.api_key
        return h

    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        client = self._ensure_client()
        payload = {
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
