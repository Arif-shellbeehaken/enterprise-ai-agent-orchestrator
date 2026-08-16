"""Unit tests for LangGraph agent pipeline nodes."""

import pytest
from uuid import uuid4

from app.engine.graph_builder import (
    planner_node,
    sanitizer_node,
    tool_decision_node,
    human_approval_gate,
    should_interrupt,
    execution_node,
    AgentState,
)


def _base_state(**kwargs) -> AgentState:
    state: AgentState = {
        "query": "hello",
        "tenant_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "user_id": str(uuid4()),
        "agent_system_prompt": "Be careful.",
        "approval_threshold_usd": 100.0,
        "requires_approval": True,
    }
    state.update(kwargs)
    return state


@pytest.mark.unit
def test_planner_node():
    out = planner_node(_base_state(query="Summarize Q3 pipeline"))
    assert "plan" in out
    assert out["status"] == "PLANNING"
    assert "PLAN" in out["plan"]


@pytest.mark.unit
def test_sanitizer_node_redacts_email():
    out = sanitizer_node(
        _base_state(query="Email john@acme.com about the deal")
    )
    assert "sanitized_query" in out
    assert "john@acme.com" not in out["sanitized_query"]
    assert out["status"] == "SANITIZED"


@pytest.mark.unit
def test_tool_decision_read_only():
    out = tool_decision_node(
        _base_state(sanitized_query="What is the status of opportunity X?")
    )
    assert out["tool_action"] == "read_only"
    assert out["needs_human_approval"] is False
    assert out["estimated_cost_usd"] < 100


@pytest.mark.unit
def test_tool_decision_sensitive_write_triggers_approval():
    out = tool_decision_node(
        _base_state(
            sanitized_query="Process a $250 payout to vendor ABC",
            requires_approval=True,
            approval_threshold_usd=100.0,
        )
    )
    assert out["tool_action"] == "external_write"
    assert out["needs_human_approval"] is True
    assert out["estimated_cost_usd"] >= 100 or out["needs_human_approval"]


@pytest.mark.unit
def test_human_approval_gate_auto():
    out = human_approval_gate(
        _base_state(needs_human_approval=False)
    )
    assert out["approval_status"] == "auto"
    assert out["status"] == "APPROVED"


@pytest.mark.unit
def test_human_approval_gate_pending():
    out = human_approval_gate(
        _base_state(
            needs_human_approval=True,
            tool_action="external_write",
            estimated_cost_usd=250.0,
        )
    )
    assert out["approval_status"] == "pending"
    assert out["status"] == "PENDING_APPROVAL"
    assert out["interrupt_reason"]


@pytest.mark.unit
def test_should_interrupt():
    assert (
        should_interrupt(
            {"needs_human_approval": True, "approval_status": "pending"}
        )
        == "interrupt"
    )
    assert (
        should_interrupt(
            {"needs_human_approval": False, "approval_status": "auto"}
        )
        == "continue"
    )


@pytest.mark.unit
def test_execution_node_completed():
    out = execution_node(
        _base_state(
            approval_status="approved",
            tool_action="external_write",
            tool_payload={"amount": 50},
        )
    )
    assert out["status"] == "COMPLETED"
    assert out["execution_result"]
    assert out["audit_id"]


@pytest.mark.unit
def test_execution_node_rejected():
    out = execution_node(_base_state(approval_status="rejected"))
    assert out["status"] == "REJECTED"
