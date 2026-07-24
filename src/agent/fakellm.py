"""Fake / scripted LLM client for local development and unit tests.

Keeps the agent loop fully exercisable WITHOUT an Azure OpenAI account. In
production this is swapped for `AzureOpenAIClient` (see src/agent/azure.py).
"""
from __future__ import annotations

from typing import List

from src.agent.base import LLMClient, Message, Tool


class FakeLLM(LLMClient):
    """Deterministic responder.

    If `script` is provided, each `complete()` call pops the next scripted line.
    A line containing 'TOOL(name={...})' triggers the tool-dispatch branch;
    otherwise it is treated as the final answer.
    """

    def __init__(self, script: List[str] | None = None) -> None:
        self._script = list(script or [])
        self.calls = 0

    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        self.calls += 1
        if self._script:
            content = self._script.pop(0)
        else:
            # Default: answer from the last user message directly.
            last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
            content = f"ANSWER: {last_user}"
        return Message(role="assistant", content=content)
