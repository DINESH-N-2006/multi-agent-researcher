"""
graph/workflow.py
------------------
The LangGraph workflow controller — coordinates research execution,
handles human approval checkpoints, and runs single-call fact-check/writing.
"""

import os
import sqlite3
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from models.state import ResearchState
from config import config
from agents.research_crew import run_research_crew
from prompts.agent_prompts import (
    FACT_CHECK_SYSTEM_PROMPT, WRITER_SYSTEM_PROMPT, REVISION_SYSTEM_PROMPT,
)

load_dotenv()

MAX_REVISIONS = 2  # Safety limit for revision iterations


def _extract_text(content) -> str:
    """
    Normalizes response content into a string regardless of whether
    LangChain returns a plain string or a list of structured content blocks.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, dict) and "text" in block:
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _llm():
    model_setting = str(getattr(config, "MODEL_NAME", "groq/llama-3.1-8b-instant")).strip()
    model_lower = model_setting.lower()

    if "groq" in model_lower or "llama" in model_lower:
        from langchain_groq import ChatGroq

        clean_model = model_setting.replace("groq/", "").replace("GROQ/", "").strip()
        groq_key = os.getenv("GROQ_API_KEY") or getattr(config, "GROQ_API_KEY", None)

        if not groq_key:
            raise ValueError("GROQ_API_KEY environment variable is missing or empty in .env")

        return ChatGroq(
            model=clean_model,
            api_key=groq_key,
            temperature=getattr(config, "TEMPERATURE", 0.7),
            max_tokens=getattr(config, "MAX_TOKENS", 4096),  # <--- Added max_tokens here to allow long outputs
            max_retries=3,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI

        clean_model = (
            model_setting
            .replace("gemini/", "")
            .replace("GEMINI/", "")
            .replace("openai/", "")
            .strip()
        )
        google_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or getattr(config, "GEMINI_API_KEY", None)
        )

        if not google_key:
            raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY environment variable is missing or empty in .env")

        return ChatGoogleGenerativeAI(
            model=clean_model,
            temperature=getattr(config, "TEMPERATURE", 0.7),
            max_output_tokens=getattr(config, "MAX_TOKENS", 4096),  # <--- Added for Gemini alternative
            google_api_key=google_key,
            max_retries=3,
        )


# ── NODE 1: research ─────────────────────────────────────────────
def research_node(state: ResearchState) -> dict:
    print(f"\n[research_node] Researching topic: {state['topic']}")
    findings = run_research_crew(state["topic"])

    sources = [
        line.strip() for line in findings.splitlines()
        if line.strip().startswith("http") or "http" in line
    ]

    return {"raw_research": findings, "sources": sources}


# ── NODE 2: fact-check + write (combined into ONE LLM call) ──────
def fact_check_and_write_node(state: ResearchState) -> dict:
    print("\n[fact_check_and_write_node] Fact-checking and drafting...")
    llm = _llm()

    raw_research = state.get("raw_research") or "No prior research findings available."

    if state.get("approval_feedback"):
        system_prompt = REVISION_SYSTEM_PROMPT
        human_content = (
            f"Previous draft:\n{state.get('draft_report', '')}\n\n"
            f"Reviewer feedback:\n{state['approval_feedback']}"
        )
        response = llm.invoke([("system", system_prompt), ("human", human_content)])
        return {"draft_report": _extract_text(response.content)}

    combined_prompt = (
        FACT_CHECK_SYSTEM_PROMPT
        + "\n\nAfter your fact-check reasoning, write the final report in Markdown "
        + "following this format:\n\n"
        + WRITER_SYSTEM_PROMPT
        + "\n\nOutput EXACTLY in this format, with no extra commentary:\n"
        + "FACT_CHECK_NOTES:\n<your fact-check notes here>\n\n"
        + "REPORT:\n<the final markdown report here>"
    )
    human_content = f"Topic: {state['topic']}\n\nResearch findings:\n{raw_research}"

    response = llm.invoke([("system", combined_prompt), ("human", human_content)])
    text = _extract_text(response.content)

    if "REPORT:" in text:
        notes_part, report_part = text.split("REPORT:", 1)
        notes = notes_part.replace("FACT_CHECK_NOTES:", "").strip()
        report = report_part.strip()
    else:
        notes, report = "", text

    # Guarantee draft report is never empty string
    if not report.strip():
        report = text if text.strip() else raw_research

    verified = "disputed" not in notes.lower()
    return {"fact_check_notes": notes, "verified": verified, "draft_report": report}


# ── NODE 3: human approval (the interrupt) ───────────────────────
def human_approval_node(state: ResearchState) -> dict:
    decision = interrupt({
        "question": "Approve this draft report?",
        "draft_report": state.get("draft_report", ""),
        "revision_count": state.get("revision_count", 0),
    })
    return {
        "approval_status": decision["decision"],
        "approval_feedback": decision.get("feedback", ""),
        "revision_count": state.get("revision_count", 0) + 1,
    }


# ── NODE 4: finalize ─────────────────────────────────────────────
def finalize_node(state: ResearchState) -> dict:
    print("\n[finalize_node] Finalizing approved report.")
    return {"final_report": state.get("draft_report", "")}


# ── CONDITIONAL EDGE ─────────────────────────────────────────────
def route_after_approval(state: ResearchState) -> str:
    if state.get("approval_status") == "approved":
        return "finalize"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        print("[route_after_approval] Max revisions reached, finalizing anyway.")
        return "finalize"
    return "fact_check_and_write"


# ── BUILD THE GRAPH ──────────────────────────────────────────────
def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("research", research_node)
    graph.add_node("fact_check_and_write", fact_check_and_write_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("research")

    graph.add_edge("research", "fact_check_and_write")
    graph.add_edge("fact_check_and_write", "human_approval")

    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"finalize": "finalize", "fact_check_and_write": "fact_check_and_write"},
    )

    graph.add_edge("finalize", END)

    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)


research_graph = build_graph()