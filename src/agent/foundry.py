"""Foundry Agent Service client (Azure AI Foundry project endpoint).

Targets the Foundry Agent Service OpenAI-compatible protocols exposed under
an AI Foundry project, e.g.:
    https://<project-resource>.services.ai.azure.com/api/projects/<project>

This client mirrors the `AzureOpenAIClient` interface (same `complete()`
contract) so it can be dropped into any Agent as the LLM backend. It is
**import-guarded** (httpx) and **never** exercises a real call in local
verification — it requires a live Foundry project + credential.

Auth (per the Foundry quickstart: `az login` before running scripts):
  Foundry Agent Service uses **Entra ID** (Bearer token from
  `az account get-access-token` / `azure-identity`), NOT an api-key, for the
  project endpoint. Provide the token via `FOUNDRY_TOKEN`, or let the client
  shell out to `az account get-access-token` on a host where `az` is installed.
No client secret is hardcoded; all creds come from env / managed identity.

Endpoint shape (your project):
  base    = https://qmfi-research-project-resource.services.ai.azure.com
  project = qmfi-research-project
  agent   = NatureLM-Idun-5-MoE   (set FOUNDRY_AGENT_ID)
  route   = {base}/api/projects/{project}/agents/{agent}/
             endpoint/protocols/openai/responses?api-version={FOUNDRY_API_VERSION}

The `responses` protocol is OpenAI-Responses-shaped: the answer lives in
`output[].content[].text` (not `choices[].message.content`).
"""
from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from src.agent.base import LLMClient, Message, Tool

_TOKEN_RESOURCE = "https://ai.azure.com"  # Entra audience for Foundry


class FoundryClient(LLMClient):
    """Async client for Azure AI Foundry Agent Service (OpenAI responses protocol)."""

    def __init__(
        self,
        project_endpoint: str,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        token: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        self.project_endpoint = project_endpoint.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id or os.environ.get("FOUNDRY_AGENT_ID")
        # api-version is project-specific; read from env, else default
        # verified working value for qmfi-research-project (2026-07-25).
        self.api_version = api_version or os.environ.get("FOUNDRY_API_VERSION") or "2025-05-15-preview"
        self._token = token
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
        if not self.agent_id:
            raise ValueError(
                "FOUNDRY_AGENT_ID (or agent_id=) required for the responses protocol"
            )
        # project_endpoint is the base, e.g.
        # https://<resource>.services.ai.azure.com
        base = (
            f"{self.project_endpoint}/api/projects/qmfi-research-project/"
            f"agents/{self.agent_id}/endpoint/protocols/openai/responses"
        )
        if self.api_version:
            base += f"?api-version={self.api_version}"
        return base

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

    @staticmethod
    def _extract_text(data: dict) -> str:
        # OpenAI Responses shape: data["output"] is a list of blocks, each with
        # content[]; text lives in content[].text or content[].input.
        for block in data.get("output", []):
            for c in block.get("content", []):
                if c.get("type") == "output_text" and c.get("text"):
                    return c["text"]
                if "text" in c and isinstance(c["text"], str):
                    return c["text"]
        # fallback: top-level "text" or "content"
        return data.get("text") or data.get("content") or ""

    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        client = self._ensure_client()
        # OpenAI Responses uses "input" (string or list), not "messages"
        payload: dict = {
            "input": [{"role": m.role, "content": m.content} for m in messages],
        }
        if tools:
            payload["tools"] = [t.to_schema() for t in tools]
        resp = await client.post(self._chat_url(), headers=self._headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        return Message(role="assistant", content=self._extract_text(data) or "")
