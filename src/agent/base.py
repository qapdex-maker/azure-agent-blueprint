"""Base agent abstractions for the Azure Agent Blueprint.

Pattern source: microsoft/agent-framework (multi-agent workflows, Python).
This is a dependency-free, locally-testable core. In Azure it is wired to
Foundry Agent Service / Azure OpenAI; locally we use a pluggable LLM client so
unit tests run without any cloud account.

License: MIT (matches Azure-Samples convention).
"""
from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None


@dataclass
class ToolResult:
    tool: str
    ok: bool
    output: Any
    error: Optional[str] = None


class Tool(abc.ABC):
    """A callable capability an agent can use (MCP-compatible surface)."""

    name: str = "tool"
    description: str = ""

    @abc.abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...

    def to_schema(self) -> Dict[str, Any]:
        """OpenAI / MCP-style function schema for registration."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }


class LLMClient(abc.ABC):
    """Pluggable model client. AzureOpenAI / OpenAI in prod; FakeLLM in tests."""

    @abc.abstractmethod
    async def complete(self, messages: List[Message], tools: List[Tool]) -> Message:
        ...


class Agent(abc.ABC):
    """An agent owns a system prompt, an LLM, and a set of tools."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm: LLMClient,
        tools: Optional[List[Tool]] = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm
        self.tools: List[Tool] = tools or []
        self.history: List[Message] = [Message(role="system", content=system_prompt)]

    def add_tool(self, tool: Tool) -> None:
        self.tools.append(tool)

    async def _dispatch_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        for t in self.tools:
            if t.name == tool_name:
                try:
                    return await t.run(**args)
                except Exception as e:  # never let a tool crash the agent loop
                    return ToolResult(tool=tool_name, ok=False, output=None, error=str(e))
        return ToolResult(tool=tool_name, ok=False, output=None, error="unknown tool")

    async def chat(self, user_input: str, max_steps: int = 5) -> str:
        """Single-turn agent loop: LLM -> tool calls -> LLM -> final answer.

        Implements the MAF 'orchestration chaining' pattern with a bounded
        step count to guarantee termination (no infinite tool loops)."""
        self.history.append(Message(role="user", content=user_input))
        steps = 0
        while steps < max_steps:
            steps += 1
            resp = await self.llm.complete(self.history, self.tools)
            self.history.append(resp)
            # Local harness: LLM returns tool calls as structured content.
            tool_calls = _parse_tool_calls(resp.content)
            if not tool_calls:
                return resp.content
            for call in tool_calls:
                result = await self._dispatch_tool(call["name"], call.get("args", {}))
                self.history.append(
                    Message(
                        role="tool",
                        name=call["name"],
                        content=f"[{'OK' if result.ok else 'ERR'}] {result.output}",
                    )
                )
        # Step budget exhausted: final synthesis pass
        final = await self.llm.complete(self.history, self.tools)
        self.history.append(final)
        return final.content


def _parse_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Parse a JSON tool-call block from the model output.

    Expected format (one per line):  TOOL(name=args_json)
    Keeps the loop cloud-agnostic and easy to test with FakeLLM."""
    import json
    import re

    calls: List[Dict[str, Any]] = []
    for m in re.finditer(r"TOOL\((\w+)=(.*?)\)", content, re.DOTALL):
        name, raw = m.group(1), m.group(2)
        try:
            args = json.loads(raw)
        except Exception:
            args = {}
        calls.append({"name": name, "args": args})
    return calls
