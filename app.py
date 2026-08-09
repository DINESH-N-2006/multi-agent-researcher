"""
app.py
------
MULTI RESEARCH AGENT SYSTEM
A clear, user-friendly multi-page interface for multi-agent deep research.
"""

import io
import re
import uuid
import streamlit as st
import markdown2
from xhtml2pdf import pisa
from langgraph.types import Command

from config import config as app_config
from graph.workflow import research_graph

# -- PAGE CONFIGURATION ----------------------------------------------------
st.set_page_config(
    page_title="MULTI RESEARCH AGENT SYSTEM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -- SESSION STATE INITIALIZATION ------------------------------------------
if "active_page" not in st.session_state:
    st.session_state.active_page = "hub"  # 'hub', 'studio', or 'analytics'
if "stage" not in st.session_state:
    st.session_state.stage = "idle"
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "interrupt_payload" not in st.session_state:
    st.session_state.interrupt_payload = None
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "error" not in st.session_state:
    st.session_state.error = None
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "execution_path" not in st.session_state:
    st.session_state.execution_path = []
if "recent_projects" not in st.session_state:
    st.session_state.recent_projects = [
        {"topic": "Quantum Encryption Protocols 2026", "status": "Completed", "date": "Today"},
        {"topic": "Autonomous AI Agent Swarms in ERP", "status": "Completed", "date": "Yesterday"},
    ]

def reset_state() -> None:
    st.session_state.stage = "idle"
    st.session_state.thread_id = None
    st.session_state.interrupt_payload = None
    st.session_state.final_report = None
    st.session_state.error = None
    st.session_state.topic = ""
    st.session_state.execution_path = []

def run_config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}

# -- PDF GENERATION HELPERS --------------------------------------------------
def convert_mermaid_to_html_boxes(text: str) -> str:
    """Finds raw mermaid code blocks and converts them into clean HTML flowchart blocks for PDF."""
    
    # Regex to find mermaid code blocks or raw flowchart syntax
    mermaid_pattern = re.compile(r'```(?:mermaid)?\s*(.*?)\s*```', re.DOTALL)
    
    def replace_mermaid(match):
        content = match.group(1)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        nodes = []
        for line in lines:
            # Extract readable labels inside quotes, brackets, or parentheses
            extracted = re.findall(r'\["(.*?)"\]|\[(.*?)\]|\((.*?)\)', line)
            for item in extracted:
                label = next(filter(None, item), None)
                if label and label not in nodes:
                    # Clean up newline breaks for PDF
                    nodes.append(label.replace('<br>', ' - ').replace('\n', ' - '))
        
        if not nodes:
            return ""

        # Build clean HTML visual steps
        html_steps = []
        for idx, node in enumerate(nodes, 1):
            html_steps.append(f"""
            <div style="background-color: #f8fafc; border: 1px solid #6366f1; border-left: 5px solid #6366f1; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                <span style="font-weight: bold; color: #4f46e5; font-size: 9pt;">STEP {idx}:</span> 
                <span style="color: #0f172a; font-size: 10pt;">{node}</span>
            </div>
            """)
            if idx < len(nodes):
                html_steps.append("""
                <div style="text-align: center; color: #818cf8; font-size: 12pt; font-weight: bold; margin: -4px 0 4px 0;">↓</div>
                """)

        return f"""
        <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin: 16px 0;">
            <div style="font-weight: bold; color: #334155; font-size: 10pt; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;">📊 Workflow Diagram</div>
            {''.join(html_steps)}
        </div>
        """

    # Replace mermaid code blocks
    cleaned_text = mermaid_pattern.sub(replace_mermaid, text)
    
    # Fallback: Replace unformatted graph TD / flowchart LR syntax if outside code blocks
    raw_flow_pattern = re.compile(r'(graph\s+TD|flowchart\s+LR)[\s\S]*?(?=\n\n|\Z)', re.IGNORECASE)
    cleaned_text = raw_flow_pattern.sub(replace_mermaid, cleaned_text)
    
    return cleaned_text


def convert_markdown_to_pdf(md_text: str) -> bytes:
    """Converts Markdown into a clean PDF, replacing raw diagrams with formatted HTML blocks."""
    
    # Step 1: Pre-process diagrams
    formatted_md = convert_mermaid_to_html_boxes(md_text)
    
    # Step 2: Convert markdown to HTML
    html_content = markdown2.markdown(formatted_md, extras=["tables", "fenced-code-blocks", "strike"])
    
    styled_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: letter portrait; margin: 2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.6; color: #1e293b; }}
            h1 {{ color: #4f46e5; font-size: 18pt; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px; }}
            h2 {{ color: #0f172a; font-size: 13pt; margin-top: 16px; margin-bottom: 8px; }}
            h3 {{ color: #334155; font-size: 11pt; margin-top: 12px; }}
            p {{ margin-bottom: 10px; }}
            ul, ol {{ margin-left: 20px; margin-bottom: 10px; }}
            li {{ margin-bottom: 4px; }}
            code {{ font-family: Courier, monospace; background-color: #f1f5f9; color: #0f172a; font-size: 9pt; }}
            pre {{ background-color: #f8fafc; padding: 10px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 8.5pt; white-space: pre-wrap; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 12px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; font-size: 9pt; }}
            th {{ background-color: #f1f5f9; font-weight: bold; color: #0f172a; }}
        </style>
    </head>
    <body>{html_content}</body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(styled_html, dest=pdf_buffer)
    return pdf_buffer.getvalue()
# -- CSS STYLING --------------------------------------------------
# -- CSS STYLING --------------------------------------------------
st.markdown("""
<style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* 1. Main Background */
    .stApp {
        background: #0d0d11 !important;
        color: #e2e8f0 !important;
    }

    /* Ambient Glow in Top Right Corner */
    .stAppViewContainer::before {
        content: "";
        position: fixed;
        top: -150px;
        right: -150px;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, rgba(99, 102, 241, 0.05) 50%, rgba(0,0,0,0) 70%);
        pointer-events: none;
        z-index: 0;
    }

    /* 2. Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #12131a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    /* Sidebar Navigation Buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.02) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(168, 85, 247, 0.1) !important;
        border-color: rgba(168, 85, 247, 0.4) !important;
        color: #f8fafc !important;
    }

    /* Active Page Button Style */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%) !important;
        border: 1px solid rgba(168, 85, 247, 0.5) !important;
        color: #e9d5ff !important;
        font-weight: 600 !important;
    }

    /* 3. Hero Header Section */
    .hero-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        color: #ffffff;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }

    .hero-subtitle {
        text-align: center;
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 2.5rem;
    }

    /* 4. Glass Cards (Start Cards) */
    div[data-testid="stForm"], div.stContainer > div[data-testid="element-container"] {
        border-radius: 16px;
    }

    /* 5. Modern Floating Input Field with Neon Border Glow */
    .stTextInput input {
        background-color: #161722 !important;
        border: 1px solid rgba(168, 85, 247, 0.3) !important;
        border-radius: 16px !important;
        color: #f8fafc !important;
        padding: 18px 20px !important;
        font-size: 1rem !important;
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.1) !important;
        transition: all 0.25s ease !important;
    }

    .stTextInput input:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 25px rgba(168, 85, 247, 0.25) !important;
        outline: none !important;
    }

    /* 6. Action Button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 20px rgba(168, 85, 247, 0.3) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(168, 85, 247, 0.45) !important;
    }

    /* Hide standard Streamlit header clutter */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# -- GRAPH EXECUTION HELPERS -----------------------------------------------
NODE_METADATA = {
    "research": {"label": "Web Research Agent", "icon": "🔍"},
    "fact_check_and_write": {"label": "Draft Writer & Reviewer", "icon": "✍️"},
    "human_review": {"label": "Human Approval Gate", "icon": "👤"},
}

def render_sidebar_node_path(container, current_node=None):
    with container:
        st.markdown("**Live Execution Path:**")
        history = st.session_state.get("execution_path", [])
        if not history:
            st.caption("No active execution yet.")
            return
            
        for idx, node in enumerate(history):
            meta = NODE_METADATA.get(node, {"label": node, "icon": "⚙️"})
            is_active = (node == current_node and idx == len(history) - 1)
            
            if is_active:
                st.markdown(
                    f'<div style="padding: 6px 12px; margin: 4px 0; border-radius: 8px; '
                    f'background: rgba(168, 85, 247, 0.2); border: 1px solid #A855F7; '
                    f'color: #C084FC; font-size: 0.82rem; font-weight: 700;">'
                    f'⚡ Active: {meta["icon"]} {meta["label"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="padding: 6px 12px; margin: 4px 0; border-radius: 8px; '
                    f'background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); '
                    f'color: #10B981; font-size: 0.82rem;">'
                    f'✓ {meta["icon"]} {meta["label"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

def run_graph_with_progress(graph_input, path_container) -> dict:
    with st.status("⚡ Agents working...", expanded=True) as status:
        try:
            for chunk in research_graph.stream(graph_input, config=run_config(), stream_mode="updates"):
                if "__interrupt__" in chunk:
                    st.session_state.execution_path.append("human_review")
                    status.update(label="Draft ready for human approval!", state="complete")
                    render_sidebar_node_path(path_container, current_node="human_review")
                    return chunk

                for node_name in chunk:
                    st.session_state.execution_path.append(node_name)
                    meta = NODE_METADATA.get(node_name, {"label": node_name, "icon": "⚙️"})
                    
                    st.markdown(f"✓ Executed: **{meta['label']}**")
                    render_sidebar_node_path(path_container, current_node=node_name)

            status.update(label="Task finished successfully!", state="complete")
        except Exception as e:
            status.update(label="Execution error occurred", state="error")
            raise e

    return research_graph.get_state(run_config()).values

def handle_graph_result(result: dict) -> None:
    if "__interrupt__" in result:
        st.session_state.interrupt_payload = result["__interrupt__"][0].value
        st.session_state.stage = "awaiting_approval"
    else:
        st.session_state.final_report = result.get("final_report", "")
        st.session_state.stage = "done"
        st.session_state.celebrate = True
        
        st.session_state.recent_projects.insert(0, {
            "topic": st.session_state.topic,
            "status": "Completed",
            "date": "Just Now"
        })

# -- SIDEBAR NAVIGATION ----------------------------------------------------
with st.sidebar:
    st.markdown("## ⚡ **AGENT SYSTEM**")
    st.caption("Multi Research Agent Platform")
    st.divider()

    st.markdown("### 📌 Pages")
    
    if st.button("🏠 Home", use_container_width=True, type="primary" if st.session_state.active_page == "hub" else "secondary"):
        st.session_state.active_page = "hub"
        st.rerun()

    if st.button("⚡ Research Studio", use_container_width=True, type="primary" if st.session_state.active_page == "studio" else "secondary"):
        st.session_state.active_page = "studio"
        st.rerun()

    if st.button("📊 Analytics", use_container_width=True, type="primary" if st.session_state.active_page == "analytics" else "secondary"):
        st.session_state.active_page = "analytics"
        st.rerun()

    st.divider()

    st.markdown("### ⚙️ Settings")
    depth_option = st.selectbox(
        "Report Length",
        options=["Quick Overview", "Standard Report", "Detailed Breakdown"],
        index=1,
    )
    tone_option = st.selectbox(
        "Writing Style",
        options=["Simple & Clear", "Business Executive", "Academic & Technical"],
        index=0,
    )
    custom_instructions = st.text_area(
        "Special Instructions",
        placeholder="e.g. Keep it simple, explain jargon, use bullet points...",
        height=70
    )

    st.session_state.research_config = {
        "depth": depth_option,
        "style": tone_option,
        "instructions": custom_instructions
    }

    st.divider()

    st.markdown("### 🕸️ Status Tracker")
    sidebar_path_container = st.container()
    render_sidebar_node_path(sidebar_path_container)

    st.divider()
    if st.session_state.stage != "idle":
        if st.button("Start New Session", use_container_width=True):
            reset_state()
            st.session_state.active_page = "hub"
            st.rerun()

# Check API Key
if not app_config.GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is missing from `.env` file.")
    st.stop()


# ===========================================================================
# PAGE 1: HOME PAGE
# ===========================================================================
if st.session_state.active_page == "hub":

    # Center Logo Icon & Welcome
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px;">
            <div style="display: inline-block; background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(99,102,241,0.2)); padding: 16px; border-radius: 50%; border: 1px solid rgba(168,85,247,0.4); margin-bottom: 10px;">
                <span style="font-size: 2rem;">⚡</span>
            </div>
            <div style="font-size: 0.85rem; color: #a855f7; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;">Welcome to Multi Research Agent System</div>
            <h1 class="hero-title">How Can I Assist Your Research?</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    # Prompt Floating Input Box
    topic_input = st.text_input(
        "Search Prompt",
        placeholder="Ask AI anything or write your request...",
        label_visibility="collapsed"
    )

    col_center, _ = st.columns([1, 3])
    with col_center:
        if st.button("Start Research ✨", type="primary", use_container_width=True, disabled=not topic_input):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.topic = topic_input
            st.session_state.stage = "running"
            st.session_state.execution_path = []
            st.session_state.active_page = "studio"
            st.rerun()

    st.write("")
    st.write("")

    # 3 Preset Action Cards across the bottom
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="background: #14151f; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 18px; min-height: 120px;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #f1f5f9;">🔍 Deep Web Research</div>
                <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 6px;">Scrapes live internet sources and extracts verified data points.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div style="background: #14151f; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 18px; min-height: 120px;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #f1f5f9;">✍️ Technical Summaries</div>
                <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 6px;">Translates complex data into simple, readable explanations.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div style="background: #14151f; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 18px; min-height: 120px;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #f1f5f9;">👤 Human-in-the-Loop</div>
                <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 6px;">Review drafts and request changes before PDF export.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ===========================================================================
# PAGE 2: RESEARCH STUDIO
# ===========================================================================
elif st.session_state.active_page == "studio":
    st.markdown("## ⚡ **Research Studio**")

    if not st.session_state.topic:
        st.warning("No active topic. Please start a query from the Home page.")
        if st.button("← Go to Home"):
            st.session_state.active_page = "hub"
            st.rerun()
        st.stop()

    st.markdown(f"**Selected Topic:** `{st.session_state.topic}`")
    st.write("")

    # INITIAL EXECUTION
    if st.session_state.stage == "running":
        config = st.session_state.research_config
        
        # Enforce simple style in instructions
        simplified_instructions = (
            f"{config['instructions']}\n"
            "IMPORTANT: Write in plain, clear, easy-to-understand English. "
            "Avoid overly technical jargon and define complex terms simply."
        )

        initial_state = {
            "topic": st.session_state.topic,
            "depth": config["depth"],
            "style": config["style"],
            "custom_instructions": simplified_instructions,
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
        try:
            result = run_graph_with_progress(initial_state, sidebar_path_container)
            handle_graph_result(result)
        except Exception as e:
            st.session_state.error = str(e)
        st.rerun()

    # HUMAN APPROVAL INTERRUPT STAGE
    elif st.session_state.stage == "awaiting_approval":
        payload = st.session_state.interrupt_payload

        current_state_values = research_graph.get_state(run_config()).values
        sources = current_state_values.get("sources", [])
        fact_check_notes = current_state_values.get("fact_check_notes", "No additional notes.")

        st.info(" Please review the generated draft report below.")

        # SOURCES & NOTES
        with st.expander("🔍 View Discovered Sources & Fact Notes", expanded=False):
            st.markdown("**Verification Summary:**")
            st.write(fact_check_notes)

            st.divider()

            st.markdown("**Web Sources Used:**")
            if sources:
                for idx, source in enumerate(sources, 1):
                    if isinstance(source, dict):
                        title = source.get("title", f"Source {idx}")
                        url = source.get("url", "#")
                        st.markdown(f"{idx}. [{title}]({url})")
                    else:
                        st.markdown(f"- {source}")
            else:
                st.caption("No web links recorded.")

        # DRAFT REPORT DISPLAY
        with st.container(border=True):
            st.markdown("### Current Report Draft")
            st.markdown(payload["draft_report"])

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Approve Report", type="primary", use_container_width=True):
                try:
                    decision = {"decision": "approved", "feedback": ""}
                    result = run_graph_with_progress(Command(resume=decision), sidebar_path_container)
                    handle_graph_result(result)
                except Exception as e:
                    st.session_state.error = str(e)
                st.rerun()

        with col2:
            if st.button("✕ Request Changes / Revisions", use_container_width=True):
                st.session_state.show_feedback_box = True

        # FEEDBACK SUBMISSION FIX
        if st.session_state.get("show_feedback_box"):
            st.write("")
            with st.container(border=True):
                st.markdown("**Provide instructions to update the report:**")
                feedback = st.text_area(
                    "Feedback Input",
                    placeholder="e.g. Simplify the terms used, make it shorter, add a section explaining how it works in plain words...",
                    label_visibility="collapsed"
                )
                
                if st.button("Submit Instructions to Agents", type="primary"):
                    if feedback.strip():
                        try:
                            # Direct feedback instruction to ensure revisions are applied clearly
                            revised_feedback = (
                                f"REVISION REQUEST: {feedback.strip()}\n"
                                "INSTRUCTION: Rewrite the report in clear, simple language addressing the user's specific feedback above."
                            )
                            decision = {"decision": "rejected", "feedback": revised_feedback}
                            
                            # Resume graph execution with feedback payload
                            result = run_graph_with_progress(Command(resume=decision), sidebar_path_container)
                            handle_graph_result(result)
                            st.session_state.show_feedback_box = False
                        except Exception as e:
                            st.session_state.error = str(e)
                        st.rerun()
                    else:
                        st.warning("Please type your feedback before submitting.")

    # FINAL REPORT DISPLAY
    elif st.session_state.stage == "done":
        if st.session_state.get("celebrate"):
            st.balloons()
            st.session_state.celebrate = False

        st.success("✓ Final Report Approved and Ready!")
        st.write("")

        with st.container(border=True):
            st.markdown(st.session_state.final_report)

        st.write("")
        
        # DOWNLOAD BUTTONS
        col1, col2 = st.columns(2)
        file_slug = st.session_state.topic.lower().replace(" ", "_") if st.session_state.topic else "research"
        pdf_data = convert_markdown_to_pdf(st.session_state.final_report)

        with col1:
            st.download_button(
                "↓ Download PDF",
                data=pdf_data,
                file_name=f"{file_slug}_report.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        with col2:
            st.download_button(
                "↓ Download Markdown",
                data=st.session_state.final_report,
                file_name=f"{file_slug}_report.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ===========================================================================
# PAGE 3: ANALYTICS
# ===========================================================================
elif st.session_state.active_page == "analytics":
    st.markdown("## 📊 **System Analytics & Architecture**")
    st.write("")

    col_graph, col_logs = st.columns([1, 1])

    with col_graph:
        with st.container(border=True):
            st.markdown("### 🕸️ Workflow Graph")
            try:
                graph_image = research_graph.get_graph().draw_mermaid_png()
                st.image(graph_image, caption="MULTI RESEARCH AGENT SYSTEM Flow", use_container_width=True)
            except Exception:
                st.code(
                    """
  [START]
     │
     ▼
┌──────────┐
│ research │ (Web Search)
└────┬─────┘
     │
     ▼
┌──────────────────────┐
│ fact_check_and_write │
└──────────┬───────────┘
           │
           ▼
   ( Human Review )
      │        │
 Approved    Rejected
      │        │
      ▼        └─────► [research]
   [END]
                    """,
                    language="text"
                )

    with col_logs:
        with st.container(border=True):
            st.markdown("### 📜 Session Details")
            st.markdown(f"**Thread ID:** `{st.session_state.thread_id or 'N/A'}`")
            st.markdown(f"**Current Status:** `{st.session_state.stage}`")
            st.markdown(f"**Steps Run:** `{len(st.session_state.execution_path)}`")
            
            st.divider()
            
            st.markdown("**Execution Log:**")
            if st.session_state.execution_path:
                for idx, step in enumerate(st.session_state.execution_path, 1):
                    st.text(f"{idx}. Executed -> [{step}]")
            else:
                st.caption("No log history for this session.")