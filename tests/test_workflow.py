"""
tests/test_workflow.py
------------------------
These are structural/unit tests — they check the GRAPH is wired
correctly and individual pieces behave, WITHOUT calling the real
OpenAI API (that would cost money and be slow/flaky in CI).

Run with: pytest tests/ -v
"""

from models.state import ResearchState
from models.schemas import FactCheckResult, ApprovalDecision
from graph.workflow import build_graph, route_after_approval


def test_graph_compiles():
    """The graph should compile without raising an exception."""
    graph = build_graph()
    assert graph is not None


def test_graph_has_all_expected_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {"research", "fact_check", "write", "human_approval", "finalize"}
    assert expected.issubset(node_names)


def test_route_after_approval_when_approved():
    state: ResearchState = {
        "topic": "test", "raw_research": None, "sources": [],
        "fact_check_notes": None, "verified": None, "draft_report": None,
        "approval_status": "approved", "approval_feedback": None,
        "final_report": None, "revision_count": 1,
    }
    assert route_after_approval(state) == "finalize"


def test_route_after_approval_when_rejected_under_max():
    state: ResearchState = {
        "topic": "test", "raw_research": None, "sources": [],
        "fact_check_notes": None, "verified": None, "draft_report": None,
        "approval_status": "rejected", "approval_feedback": "too short",
        "final_report": None, "revision_count": 1,
    }
    assert route_after_approval(state) == "write"


def test_route_after_approval_caps_revisions():
    """Even if rejected again, we must stop looping once max is hit."""
    state: ResearchState = {
        "topic": "test", "raw_research": None, "sources": [],
        "fact_check_notes": None, "verified": None, "draft_report": None,
        "approval_status": "rejected", "approval_feedback": "still not right",
        "final_report": None, "revision_count": 2,  # equals MAX_REVISIONS
    }
    assert route_after_approval(state) == "finalize"


def test_fact_check_result_confidence_bounds():
    """Pydantic should reject a confidence value outside 0-1."""
    import pytest
    from pydantic import ValidationError

    # valid case
    result = FactCheckResult(verdict="verified", confidence=0.9, notes="ok")
    assert result.confidence == 0.9

    # invalid case: confidence > 1 should raise
    with pytest.raises(ValidationError):
        FactCheckResult(verdict="verified", confidence=1.5, notes="bad")


def test_approval_decision_rejects_invalid_status():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ApprovalDecision(decision="maybe", feedback="")
