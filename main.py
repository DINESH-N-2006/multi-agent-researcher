"""
main.py
--------
CLI entry point. This is where we actually RUN the graph and handle
the human-approval pause/resume cycle from the terminal.

KEY IDEA: thread_id
--------------------
LangGraph's checkpointer can track MANY separate graph runs at once
(e.g. many users, many topics). To tell them apart, every invocation
needs a "thread_id" — a unique string identifying THIS particular
run. We pass it inside a `config` dict: {"configurable": {"thread_id": ...}}.
When we resume after an interrupt, we MUST pass the SAME thread_id,
so LangGraph knows which saved state to continue from.
"""

import sys
import uuid

from langgraph.types import Command
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from config import config as app_config
from graph.workflow import research_graph

console = Console()


def run_pipeline(topic: str) -> None:
    app_config.validate()  # fail fast if OPENAI_API_KEY is missing

    # Each run gets its own thread_id so multiple research runs never
    # collide with each other's saved state.
    thread_id = str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    # Initial state. Every field declared in ResearchState should
    # have a starting value here (even if it's just None or []),
    # since LangGraph expects the shape to match the TypedDict.
    initial_state = {
        "topic": topic,
        "raw_research": None,
        "sources": [],
        "fact_check_notes": None,
        "verified": None,
        "draft_report": None,
        "approval_status": None,
        "approval_feedback": None,
        "final_report": None,
        "revision_count": 0,
    }

    console.print(Panel(f"Starting research on: [bold]{topic}[/bold]"))

    # First invoke: runs research -> fact_check -> write -> human_approval,
    # where it PAUSES because human_approval_node calls interrupt().
    result = research_graph.invoke(initial_state, config=run_config)

    # After invoke() returns, check if we're paused at an interrupt.
    # LangGraph surfaces this as a special "__interrupt__" key in the
    # result whose value contains the payload we passed to interrupt().
    while "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value
        console.print(Panel(
            Markdown(interrupt_data["draft_report"]),
            title="Draft Report — Awaiting Approval",
        ))

        decision = _prompt_human_decision()

        # Resuming: we call invoke() AGAIN, but this time with a
        # Command(resume=...) instead of a fresh state. LangGraph
        # loads the saved state for this thread_id, feeds our
        # `decision` back in as the return value of the interrupt()
        # call inside human_approval_node, and continues from there.
        result = research_graph.invoke(Command(resume=decision), config=run_config)

    # No more interrupts — the graph has run to completion (END).
    console.print(Panel(
        Markdown(result["final_report"]),
        title="✅ Final Approved Report",
        border_style="green",
    ))

    output_path = f"{app_config.OUTPUT_DIR}/report.md"
    with open(output_path, "w") as f:
        f.write(result["final_report"])
    console.print(f"\nSaved to [bold]{output_path}[/bold]")


def _prompt_human_decision() -> dict:
    """Asks the human at the terminal to approve/reject the draft."""
    console.print("\n[bold yellow]Approve this report?[/bold yellow] (y/n): ", end="")
    choice = input().strip().lower()

    if choice == "y":
        return {"decision": "approved", "feedback": ""}

    console.print("What should be changed? ", end="")
    feedback = input().strip()
    return {"decision": "rejected", "feedback": feedback}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("Usage: python main.py \"<research topic>\"")
        sys.exit(1)

    topic_arg = " ".join(sys.argv[1:])
    run_pipeline(topic_arg)
