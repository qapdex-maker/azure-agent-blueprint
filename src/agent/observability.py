"""Observability: OpenTelemetry tracing + Azure Monitor (Application Insights).

Matches the 'monitoring by default' pattern in get-started-with-ai-agents and
foundry-agent-webapp. Import-guarded so local runs don't require the SDK.
"""
from __future__ import annotations

import functools
import time
import os
from typing import Any, Callable


def _get_tracer():
    if os.environ.get("APPINSIGHTS_CONNECTION_STRING"):
        try:
            from opentelemetry import trace  # type: ignore
            from azure.monitor.opentelemetry import configure_azure_monitor  # type: ignore
            configure_azure_monitor()
            return trace.get_tracer("azure-agent-blueprint")
        except ImportError:
            pass
    return None


TRACER = _get_tracer()


def trace_span(name: str):
    """Decorator: record a span (and duration) for any agent/tool call."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            if TRACER is None:
                return await fn(*args, **kwargs)
            with TRACER.start_as_current_span(name) as span:
                start = time.time()
                try:
                    result = await fn(*args, **kwargs)
                    span.set_attribute("status", "ok")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.record_exception(e)
                    raise
                finally:
                    span.set_attribute("duration_ms", (time.time() - start) * 1000)
        return async_wrapper

    return decorator
