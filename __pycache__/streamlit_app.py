"""
streamlit_app.py
------------------
A browser-based UI for the same pipeline main.py runs in the
terminal. This file does NOT duplicate any research/graph logic --
it only imports and drives research_graph, the exact same object
main.py uses. That's intentional: the UI is just a different way of
talking to the same underlying system.

Run with:
    streamlit run streamlit_app.py
"""

import uuid

import streamlit as st
from langgraph.types import Command

from config import config as app_config
from graph.workflow import research_graph

st.set_page_config(page_title="Multi-Agent Research System", page_icon="🔎", layout="centered")


# ── SESSION STATE SETUP ──────────────────────────────────────────
# st.session_state persists across Streamlit reruns (every click
# reruns this whole script from the top). We use it the same way
# main.py uses local variables in its while-loop -- to remember
# where we are in the pipeline between one interaction and the next.
if "stage" not in st.session_state:
    # One of: "idle", "awaiting_approval", "done"
    st.session_state.stage = "idle"
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "interrupt_payload" not in st.session_state:
    st.session_state.interrupt_payload = None
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "error" not in st.session_state:
    st.session_state.error = None


def reset_state() -> None:
    """Clears session state so the user can start a fresh research run."""
    st.session_state.stage = "idle"
    st.session_state.thread_id = None
    st.session_state.interrupt_payload = None
    st.session_state.final_report = None
    st.session_state.error = None


def run_config() -> dict:
    """Builds the LangGraph run config for the CURRENT thread_id."""
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def handle_graph_result(result: dict) -> None:
    """
    Shared logic for after ANY graph.invoke() call (whether it's the
    first invoke or a resume). Checks whether we paused at an
    interrupt again, or reached the real end of the graph.
    """
    if "__interrupt__" in result:
        st.session_state.interrupt_payload = result["__interrupt__"][0].value
        st.session_state.stage = "awaiting_approval"
    else:
        st.session_state.final_report = result["final_report"]
        st.session_state.stage = "done"


# ── PAGE HEADER ───────────────────────────────────────────────────
st.title("🔎 Multi-Agent Research System")
st.caption("LangGraph orchestration + CrewAI research crew, with human-in-the-loop approval.")

# Fail fast with a clear message in the UI, same idea as
# app_config.validate() in main.py -- just shown as a Streamlit
# error box instead of a terminal crash.
if not app_config.GEMINI_API_KEY:
    st.error(
        "GEMINI_API_KEY is not set. Add it to your .env file, then restart "
        "this app (Ctrl+C in the terminal, then `streamlit run streamlit_app.py` again)."
    )
    st.stop()  # st.stop() halts execution of the rest of the script for this rerun


# ── STAGE: idle -- show the topic input form ─────────────────────
if st.session_state.stage == "idle":
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. The environmental impact of lithium mining",
    )
    start = st.button("Start Research", type="primary", disabled=not topic)

    if start:
        st.session_state.thread_id = str(uuid.uuid4())
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
        with st.spinner(
            "Researching, fact-checking, and drafting a report... "
            "this can take 1-3 minutes."
        ):
            try:
                result = research_graph.invoke(initial_state, config=run_config())
                handle_graph_result(result)
            except Exception as e:
                # Surface the real error in the UI instead of a raw
                # traceback, same spirit as the try/except in
                # tools/search_tool.py -- never let one failure crash
                # the whole page with no explanation.
                st.session_state.error = str(e)
        st.rerun()  # re-run the script now that session_state has changed,
                    # so the UI immediately reflects the new stage


# ── STAGE: awaiting_approval -- show the draft + approve/reject ──
elif st.session_state.stage == "awaiting_approval":
    payload = st.session_state.interrupt_payload
    st.subheader("Draft Report — Awaiting Approval")
    st.caption(f"Revision round: {payload['revision_count']}")
    st.markdown(payload["draft_report"])

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Approve", type="primary", use_container_width=True):
            with st.spinner("Finalizing report..."):
                try:
                    decision = {"decision": "approved", "feedback": ""}
                    result = research_graph.invoke(Command(resume=decision), config=run_config())
                    handle_graph_result(result)
                except Exception as e:
                    st.session_state.error = str(e)
            st.rerun()

    with col2:
        reject_clicked = st.button("❌ Reject", use_container_width=True)

    if reject_clicked:
        # Store a flag so the feedback box stays visible across the
        # rerun that this button click triggers.
        st.session_state.show_feedback_box = True

    if st.session_state.get("show_feedback_box"):
        feedback = st.text_area("What should be changed?")
        submit_feedback = st.button("Submit feedback and revise")
        if submit_feedback and feedback:
            with st.spinner("Revising report based on your feedback..."):
                try:
                    decision = {"decision": "rejected", "feedback": feedback}
                    result = research_graph.invoke(Command(resume=decision), config=run_config())
                    handle_graph_result(result)
                    st.session_state.show_feedback_box = False
                except Exception as e:
                    st.session_state.error = str(e)
            st.rerun()


# ── STAGE: done -- show the final report ──────────────────────────
elif st.session_state.stage == "done":
    st.success("Report approved and finalized!")
    st.markdown(st.session_state.final_report)

    st.download_button(
        "Download report.md",
        data=st.session_state.final_report,
        file_name="report.md",
        mime="text/markdown",
    )

    if st.button("Start New Research"):
        reset_state()
        st.rerun()


# ── ERROR DISPLAY (shown regardless of stage, if one occurred) ────
if st.session_state.error:
    st.error(f"Something went wrong: {st.session_state.error}")
    if st.button("Reset and try again"):
        reset_state()
        st.rerun()
