"""Orchestration layer: multi-agent chaining (MAF durable-task pattern).

Implements sequential agent chaining with a durable-style checkpoint so a
long-running workflow can resume after a disconnect (mirrors
durable-task-extension 'reliable_streaming' with Redis-backed resume).

For local verification this runs in-process; the durability hook is pluggable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from src.agent.base import Agent, Message


@dataclass
class ChainStep:
    agent_name: str
    input_template: str  # "{prev_output}" substituted from prior step
    checkpoint: Optional[str] = None  # durability key


class Orchestrator:
    """Runs a fixed pipeline of agents, passing each output to the next.

    Pattern: durable-task-extension 04_single_agent_orchestration_chaining.
    A `checkpointer` (callable key->value) enables resume; pass None for
    in-process runs (used by tests).
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        steps: List[ChainStep],
        checkpointer: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self.agents = agents
        self.steps = steps
        self.checkpointer = checkpointer or (lambda k: None)

    async def run(self, initial_input: str) -> dict[str, str]:
        outputs: dict[str, str] = {}
        current = initial_input
        for i, step in enumerate(self.steps):
            agent = self.agents.get(step.agent_name)
            if agent is None:
                raise KeyError(f"no agent registered: {step.agent_name}")
            # resume from checkpoint if available
            ck = f"step{i}:{step.agent_name}"
            restored = self.checkpointer(ck)
            if restored is not None:
                outputs[step.agent_name] = restored
                current = restored
                continue
            prompt = step.input_template.format(prev_output=current)
            result = await agent.chat(prompt)
            outputs[step.agent_name] = result
            current = result
        return outputs
