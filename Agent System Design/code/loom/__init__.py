"""loom v1.0：《Agent System 設計全書》的隨書 framework（第 45 章）。

核心型別從這裡直接 import；其他模組用完整名稱，例如 `from loom.approval import ApprovalMiddleware`。
"""
from .core import (CORE_EVENTS, Agent, ConcurrencyError, Event, Guardrail, Handoff, InMemorySession, Interrupt,
                   Middleware, ModelError, ModelRequest, ModelResponse, RunContext, Runner, RunResult, StopRun,
                   Tool, ToolCall, ToolResult, intent_key, pending_calls, to_messages)

__version__ = "1.0.0"
__all__ = ["CORE_EVENTS", "Agent", "ConcurrencyError", "Event", "Guardrail", "Handoff", "InMemorySession",
           "Interrupt", "Middleware", "ModelError", "ModelRequest", "ModelResponse", "RunContext", "Runner",
           "RunResult", "StopRun", "Tool", "ToolCall", "ToolResult", "intent_key", "pending_calls", "to_messages"]
