"""Example MCP-compatible tools for the Azure Agent Blueprint.

These mirror the Microsoft `mcp/` repo server pattern: each tool exposes a
stable `name` + `to_schema()` and is safe to call (no deletes, per the
azure-finops-agent 'read & write, never delete' guardrail).
"""
from __future__ import annotations

import time
from typing import Any

from src.agent.base import Tool, ToolResult


class CostLookupTool(Tool):
    """Look up simulated Azure retail pricing for a SKU/region.

    In production this calls the Azure Retail Prices API (public, no auth).
    Locally it returns deterministic fixtures so unit tests are hermetic.
    """

    name = "cost_lookup"
    description = "Return estimated monthly cost for an Azure SKU in a region."

    def __init__(self, price_table: dict | None = None) -> None:
        self._prices = price_table or {
            ("Standard_D2s_v5", "eastus"): 70.0,
            ("Standard_D4s_v5", "eastus"): 140.0,
            ("Standard_D2s_v5", "westeurope"): 75.0,
        }

    async def run(self, sku: str = "", region: str = "eastus", **_: Any) -> ToolResult:
        if not sku:
            return ToolResult(self.name, False, None, "sku required")
        key = (sku, region)
        price = self._prices.get(key)
        if price is None:
            return ToolResult(self.name, False, None, f"no price for {key}")
        return ToolResult(self.name, True, {"sku": sku, "region": region, "usd_per_month": price})


class RemediationScriptTool(Tool):
    """Generate a ready-to-run `az` remediation script (write, never delete).

    Mirrors azure-finops-agent behaviour: the agent can *produce* a script but
    must not execute destructive operations autonomously.
    """

    name = "generate_remediation"
    description = "Produce an az cli script to right-size or reserve a resource."

    async def run(self, resource_id: str = "", action: str = "reserve", **_: Any) -> ToolResult:
        if not resource_id:
            return ToolResult(self.name, False, None, "resource_id required")
        if action == "reserve":
            script = f"az reservation create --scope {resource_id} --term P1Y"
        elif action == "resize":
            script = f"az vm resize --ids {resource_id} --size Standard_D2s_v5"
        else:
            return ToolResult(self.name, False, None, f"unknown action {action}")
        return ToolResult(self.name, True, {"script": script, "action": action})


class ClockTool(Tool):
    """Return current UTC epoch. Useful for SLA / scheduled-job logic."""

    name = "clock"
    description = "Return current UTC epoch seconds."

    async def run(self, **_: Any) -> ToolResult:
        return ToolResult(self.name, True, {"utc_epoch": int(time.time())})
