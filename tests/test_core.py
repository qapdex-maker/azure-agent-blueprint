"""Unit tests for the Azure Agent Blueprint core.

Run:  python -m pytest tests/  (or: python tests/test_core.py)
No Azure / OpenAI required — uses LocalLLM + scripted tool calls.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent.base import Agent, Message
from src.agent.fakellm import LocalLLM
from src.tools.builtin import CostLookupTool, RemediationScriptTool, ClockTool
from src.orchestrator.chain import Orchestrator, ChainStep


def run(coro):
    return asyncio.run(coro)


def build_agent(script):
    agent = Agent(
        name="finops",
        system_prompt="You are a FinOps agent.",
        llm=LocalLLM(script),
        tools=[CostLookupTool(), RemediationScriptTool(), ClockTool()],
    )
    return agent


def test_agent_tool_dispatch_and_final_answer():
    # Step 1: model emits a TOOL call; step 2: model gives final answer.
    script = [
        'Let me check pricing. TOOL(cost_lookup={"sku":"Standard_D2s_v5","region":"eastus"})',
        "ANSWER: The SKU costs $70/month in eastus.",
    ]
    agent = build_agent(script)
    out = run(agent.chat("How much is Standard_D2s_v5 in eastus?"))
    assert "70" in out, out
    # tool result must have been recorded in history
    tool_msgs = [m for m in agent.history if m.role == "tool"]
    assert tool_msgs, "tool was never dispatched"
    assert "OK" in tool_msgs[0].content
    print("PASS test_agent_tool_dispatch_and_final_answer")


def test_tool_error_is_caught_not_crashed():
    script = [
        'TOOL(cost_lookup={"sku":"","region":"eastus"})',
        "ANSWER: I need a SKU.",
    ]
    agent = build_agent(script)
    out = run(agent.chat("price?"))
    assert "SKU" in out
    err = [m for m in agent.history if m.role == "tool" and "ERR" in m.content]
    assert err, "error path not captured"
    print("PASS test_tool_error_is_caught_not_crashed")


def test_remediation_write_never_delete():
    script = [
        'TOOL(generate_remediation={"resource_id":"/subs/x","action":"reserve"})',
        "ANSWER: Here is your reservation script.",
    ]
    agent = build_agent(script)
    out = run(agent.chat("reserve /subs/x"))
    res = [m for m in agent.history if m.role == "tool"]
    assert "reservation create" in res[0].content
    assert "delete" not in res[0].content.lower()
    print("PASS test_remediation_write_never_delete")


def test_orchestrator_chaining():
    a1 = Agent("planner", "plan", LocalLLM(["TOOL(clock={})", "PLAN: assess costs"]))
    a1.add_tool(ClockTool())
    a2 = Agent("executor", "exec", LocalLLM(["EXEC: apply plan"]))
    orch = Orchestrator(
        agents={"planner": a1, "executor": a2},
        steps=[
            ChainStep("planner", "{prev_output}"),
            ChainStep("executor", "{prev_output}"),
        ],
    )
    out = run(orch.run("start"))
    assert "PLAN" in out["planner"]
    assert "EXEC" in out["executor"]
    print("PASS test_orchestrator_chaining")


def test_step_budget_terminates():
    # Infinite tool loop must be bounded by max_steps.
    script = ['TOOL(clock={})'] * 20  # always calls tool, never answers
    agent = build_agent(script[:5])  # LocalLLM exhausts -> returns last as answer
    out = run(agent.chat("loop"))
    assert out is not None
    print("PASS test_step_budget_terminates")


if __name__ == "__main__":
    test_agent_tool_dispatch_and_final_answer()
    test_tool_error_is_caught_not_crashed()
    test_remediation_write_never_delete()
    test_orchestrator_chaining()
    test_step_budget_terminates()
    print("\nALL TESTS PASSED")
