"""
LangGraph stateful orchestrator with Human-in-the-Loop interrupt gates.
Nodes: Planner → Sanitizer → Tool Decision → (HITL Gate) → Execution & Audit
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.engine.pii_sanitizer import get_pii_sanitizer
from app.engine.tools_adapter import ToolsAdapter

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    """Shared state flowing through the graph."""

    # Input
    query: str
    tenant_id: str
    agent_id: str
    user_id: str
    agent_system_prompt: str
    approval_threshold_usd: float
    requires_approval: bool

    # Intermediate
    sanitized_query: str
    pii_mapping: Dict[str, str]
    plan: str
    tool_action: Optional[str]
    tool_payload: Optional[Dict[str, Any]]
    estimated_cost_usd: float
    needs_human_approval: bool

    # HITL
    approval_status: Literal["pending", "approved", "rejected", "auto"]
    reviewed_by: Optional[str]
    interrupt_reason: Optional[str]

    # Output
    execution_result: Optional[str]
    status: str  # PENDING_APPROVAL | APPROVED | REJECTED | COMPLETED | FAILED
    audit_id: Optional[str]
    error: Optional[str]


def planner_node(state: AgentState) -> Dict[str, Any]:
    """1. Planner: evaluate query against permissions / memory (stub LLM)."""
    query = state.get("query", "")
    system = state.get("agent_system_prompt", "You are a helpful enterprise agent.")
    # In production: call LiteLLM / Gemini with system + query
    plan = (
        f"[PLAN] Analyze request under policy '{system[:80]}...'. "
        f"Query length={len(query)}. Decide tools required."
    )
    logger.info("Planner produced plan for tenant=%s", state.get("tenant_id"))
    return {"plan": plan, "status": "PLANNING"}


def sanitizer_node(state: AgentState) -> Dict[str, Any]:
    """2. Sanitizer: redact PII before any external LLM / tool call."""
    sanitizer = get_pii_sanitizer()
    original = state.get("query", "")
    sanitized, mapping = sanitizer.sanitize_text(original)
    logger.info("Sanitized %d PII entities", len(mapping))
    return {
        "sanitized_query": sanitized,
        "pii_mapping": mapping,
        "status": "SANITIZED",
    }


def tool_decision_node(state: AgentState) -> Dict[str, Any]:
    """
    3. Tool Decision: determine if external write is required and estimate cost.
    Heuristic for MVP; replace with LLM tool-calling in production.
    """
    query = (state.get("sanitized_query") or state.get("query") or "").lower()
    tools = ToolsAdapter(tenant_id=UUID(state["tenant_id"]))

    tool_action: Optional[str] = None
    tool_payload: Dict[str, Any] = {}
    estimated_cost = 0.0

    if any(kw in query for kw in ("update", "write", "create", "delete", "payout", "payment", "transfer")):
        tool_action = "external_write"
        # Extract a rough amount if present
        import re
        amount_match = re.search(r"\$?([\d,]+\.?\d*)", query)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 50.0
        tool_payload = {"action": "write", "amount": amount, "query": query}
        estimated_cost = amount if "payout" in query or "payment" in query else 25.0
    else:
        tool_action = "read_only"
        estimated_cost = 1.0

    threshold = float(state.get("approval_threshold_usd") or settings.APPROVAL_THRESHOLD_USD)
    requires = bool(state.get("requires_approval", True))
    needs_approval = requires and (
        estimated_cost > threshold
        or tool_action == "external_write"
    )

    return {
        "tool_action": tool_action,
        "tool_payload": tool_payload,
        "estimated_cost_usd": estimated_cost,
        "needs_human_approval": needs_approval,
        "status": "TOOL_DECISION",
    }


def human_approval_gate(state: AgentState) -> Dict[str, Any]:
    """
    4. Human Approval Gate.
    If needs_human_approval is True the graph will be interrupted by the
    checkpointer / interrupt mechanism; the frontend can then resume after
    an explicit approve/reject decision.
    """
    if not state.get("needs_human_approval"):
        return {
            "approval_status": "auto",
            "status": "APPROVED",
            "interrupt_reason": None,
        }

    reason = (
        f"Action '{state.get('tool_action')}' estimated cost "
        f"${state.get('estimated_cost_usd', 0):.2f} exceeds threshold "
        f"or touches sensitive records."
    )
    logger.warning("HITL interrupt: %s", reason)
    return {
        "approval_status": "pending",
        "status": "PENDING_APPROVAL",
        "interrupt_reason": reason,
    }


def should_interrupt(state: AgentState) -> Literal["interrupt", "continue"]:
    """Conditional edge after the approval gate."""
    if state.get("needs_human_approval") and state.get("approval_status") == "pending":
        return "interrupt"
    return "continue"


def execution_node(state: AgentState) -> Dict[str, Any]:
    """5. Execution & Audit: run approved action and record result."""
    if state.get("approval_status") == "rejected":
        return {
            "execution_result": "Action rejected by human reviewer.",
            "status": "REJECTED",
        }

    # Simulate tool execution
    action = state.get("tool_action", "noop")
    payload = state.get("tool_payload") or {}
    result = {
        "action": action,
        "payload": payload,
        "message": f"Executed '{action}' successfully (simulated).",
        "tenant_id": state.get("tenant_id"),
    }
    return {
        "execution_result": json.dumps(result),
        "status": "COMPLETED",
        "audit_id": str(uuid4()),
    }


def build_agent_graph(checkpointer: Optional[Any] = None):
    """
    Construct the LangGraph StateGraph with interrupt support.
    """
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("sanitizer", sanitizer_node)
    graph.add_node("tool_decision", tool_decision_node)
    graph.add_node("human_approval_gate", human_approval_gate)
    graph.add_node("execution", execution_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "sanitizer")
    graph.add_edge("sanitizer", "tool_decision")
    graph.add_edge("tool_decision", "human_approval_gate")

    graph.add_conditional_edges(
        "human_approval_gate",
        should_interrupt,
        {
            "interrupt": END,  # Graph pauses; caller resumes after HITL decision
            "continue": "execution",
        },
    )
    graph.add_edge("execution", END)

    memory = checkpointer or MemorySaver()
    compiled = graph.compile(
        checkpointer=memory,
        interrupt_before=[],  # We control interrupt via conditional END
        interrupt_after=["human_approval_gate"],  # Pause after gate when pending
    )
    return compiled


# Module-level compiled graph (in-memory checkpointer for demo)
_graph = None


def get_agent_graph():
    global _graph
    if _graph is None:
        _graph = build_agent_graph()
    return _graph
