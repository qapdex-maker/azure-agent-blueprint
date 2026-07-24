"""Production LLM client: Azure OpenAI / Foundry Agent Service.

This is the cloud path used when deployed (see infra/ + azd up). It is NOT
exercised in local verification because no Azure account is available on the
build host; it is import-guarded so the rest of the codebase stays testable.
"""
from __future__ import annotations

from typing import List

from src.agent.base import LLMClient, Message, Tool


class AzureOpenAIClient(LLMClient):
    """Thin wrapper around the official OpenAI SDK pointed at Azure.

    Wiring matches microsoft/agent-framework + get-started-with-ai-agents:
    managed identity / key from env, tool schemas from `Tool.to_schema()`.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        deployment: str = "gpt-4o",
        api_version: str = "2024-10-21",
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self._client = None  # lazily imported to avoid hard dependency in tests

    def _ensure_client(self):
        if self._client is None:
            try:
                from openai import AzureOpenAI  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "openai SDK not installed; install with `pip install openai` "
                    "or use FakeLLM for local runs."
                ) from e
            self._client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        return self._client

    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        client = self._ensure_client()
        completions = client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=[t.to_schema() for t in tools] if tools else None,
            tool_choice="auto" if tools else None,
        )
        choice = completions.choices[0].message
        return Message(role="assistant", content=choice.content or "")
