"""
graph/workflow.py
------------------
The LangGraph half of the system — the "project manager" that
decides what happens, in what order, and pauses for human approval.
"""
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
from langchain_google_genai import ChatGoogleGenerativeAI

from models.state import ResearchState
from config import config
from agents.research_crew import run_research_crew
from prompts.agent_prompts import (
    FACT_CHECK_SYSTEM_PROMPT, WRITER_SYSTEM_PROMPT, REVISION_SYSTEM_PROMPT,
)

MAX_REVISIONS = 2  # safety cap so a human rejecting repeatedly can't loop forever


def _extract_text(content) -> str:
    """
    Newer langchain-google-genai versions sometimes return
    response.content as a plain string, but other times as a LIST of
    structured content blocks, e.g.:
        [{"type": "text", "text": "the actual text...", "extras": {...}}]
    Blindly stringifying the list form is what produces the ugly
    raw "[{'type': 'text', ...}]" output. This normalizes both shapes
    into a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _llm() -> ChatGoogleGenerativeAI:
    model_name = config.MODEL_NAME.replace("gemini/", "")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=config.TEMPERATURE,
        google_api_key=config.GEMINI_API_KEY,
    )


# ── NODE 1: research ─────────────────────────────────────────────
def research_node(state: ResearchState) -> dict:
    """
    Calls the CrewAI research crew (Researcher + Analyst agents) and
    stores their combined output back into the shared state.
    """
    print(f"\n[research_node] Researching topic: {state['topic']}")
    findings = run_research_crew(state["topic"])

    sources = [
        line.strip() for line in findings.splitlines()
        if line.strip().startswith("http") or "http" in line
    ]

    return {"raw_research": findings, "sources": sources}


# ── NODE 2: fact-check ───────────────────────────────────────────
def fact_check_node(state: ResearchState) -> dict:
    print("\n[fact_check_node] Verifying claims...")
    llm = _llm()
    messages = [
        ("system", FACT_CHECK_SYSTEM_PROMPT),
        ("human", f"Research summary to check:\n\n{state['raw_research']}"),
    ]
    response = llm.invoke(messages)
    notes = _extract_text(response.content)

    verified = "disputed" not in notes.lower()

    return {"fact_check_notes": notes, "verified": verified}


# ── NODE 3: write ────────────────────────────────────────────────
def write_node(state: ResearchState) -> dict:
    print("\n[write_node] Drafting report...")
    llm = _llm()

    if state.get("approval_feedback"):
        system_prompt = REVISION_SYSTEM_PROMPT
        human_content = (
            f"Previous draft:\n{state['draft_report']}\n\n"
            f"Reviewer feedback:\n{state['approval_feedback']}"
        )
    else:
        system_prompt = WRITER_SYSTEM_PROMPT
        human_content = (
            f"Topic: {state['topic']}\n\n"
            f"Research findings:\n{state['raw_research']}\n\n"
            f"Fact-check notes:\n{state['fact_check_notes']}"
        )

    response = llm.invoke([("system", system_prompt), ("human", human_content)])
    return {"draft_report": _extract_text(response.content)}


# ── NODE 4: human approval (the interrupt) ───────────────────────
def human_approval_node(state: ResearchState) -> dict:
    """
    This is where the graph PAUSES and hands control back to a human.
    """
    decision = interrupt({
        "question": "Approve this draft report?",
        "draft_report": state["draft_report"],
        "revision_count": state["revision_count"],
    })
    return {
        "approval_status": decision["decision"],
        "approval_feedback": decision.get("feedback", ""),
        "revision_count": state["revision_count"] + 1,
    }


# ── NODE 5: finalize ─────────────────────────────────────────────
def finalize_node(state: ResearchState) -> dict:
    print("\n[finalize_node] Finalizing approved report.")
    return {"final_report": state["draft_report"]}


# ── CONDITIONAL EDGE: what happens after human approval? ─────────
def route_after_approval(state: ResearchState) -> str:
    """
    A conditional edge function.
    """
    if state["approval_status"] == "approved":
        return "finalize"
    if state["revision_count"] >= MAX_REVISIONS:
        print("[route_after_approval] Max revisions reached, finalizing anyway.")
        return "finalize"
    return "write"  # go back and revise


# ── BUILD THE GRAPH ──────────────────────────────────────────────
def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("research", research_node)
    graph.add_node("fact_check", fact_check_node)
    graph.add_node("write", write_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("research")

    graph.add_edge("research", "fact_check")
    graph.add_edge("fact_check", "write")
    graph.add_edge("write", "human_approval")

    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"finalize": "finalize", "write": "write"},
    )

    graph.add_edge("finalize", END)

    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)


research_graph = build_graph()