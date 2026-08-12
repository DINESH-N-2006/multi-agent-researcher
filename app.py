"""
app.py
------
MULTI RESEARCH AGENT SYSTEM
Professional editorial-grade multi-page interface for multi-agent deep research.
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
    page_title="Multi Research Agent System",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -- SESSION STATE INITIALIZATION ------------------------------------------
if "active_page" not in st.session_state:
    st.session_state.active_page = "hub"
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

    mermaid_pattern = re.compile(r'```(?:mermaid)?\s*(.*?)\s*```', re.DOTALL)

    def replace_mermaid(match):
        content = match.group(1)
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        nodes = []
        for line in lines:
            extracted = re.findall(r'\["(.*?)"\]|\[(.*?)\]|\((.*?)\)', line)
            for item in extracted:
                label = next(filter(None, item), None)
                if label and label not in nodes:
                    nodes.append(label.replace('<br>', ' - ').replace('\n', ' - '))

        if not nodes:
            return ""

        html_steps = []
        for idx, node in enumerate(nodes, 1):
            html_steps.append(f"""
            <div style="background-color: #faf7f2; border: 1px solid #B8853A; border-left: 5px solid #B8853A; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                <span style="font-weight: bold; color: #8A5F1F; font-size: 9pt;">STEP {idx}:</span>
                <span style="color: #1c1c1c; font-size: 10pt;">{node}</span>
            </div>
            """)
            if idx < len(nodes):
                html_steps.append("""
                <div style="text-align: center; color: #B8853A; font-size: 12pt; font-weight: bold; margin: -4px 0 4px 0;">↓</div>
                """)

        return f"""
        <div style="background-color: #f6f4f0; border: 1px solid #ddd6c9; border-radius: 8px; padding: 14px; margin: 16px 0;">
            <div style="font-weight: bold; color: #4a4438; font-size: 10pt; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;">Workflow Diagram</div>
            {''.join(html_steps)}
        </div>
        """

    cleaned_text = mermaid_pattern.sub(replace_mermaid, text)

    raw_flow_pattern = re.compile(r'(graph\s+TD|flowchart\s+LR)[\s\S]*?(?=\n\n|\Z)', re.IGNORECASE)
    cleaned_text = raw_flow_pattern.sub(replace_mermaid, cleaned_text)

    return cleaned_text


def convert_markdown_to_pdf(md_text: str) -> bytes:
    """Converts Markdown into a clean PDF, replacing raw diagrams with formatted HTML blocks."""

    formatted_md = convert_mermaid_to_html_boxes(md_text)
    html_content = markdown2.markdown(formatted_md, extras=["tables", "fenced-code-blocks", "strike"])

    styled_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: letter portrait; margin: 2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.6; color: #23211c; }}
            h1 {{ color: #8A5F1F; font-size: 18pt; border-bottom: 2px solid #ddd6c9; padding-bottom: 8px; margin-bottom: 12px; }}
            h2 {{ color: #1c1c1c; font-size: 13pt; margin-top: 16px; margin-bottom: 8px; }}
            h3 {{ color: #4a4438; font-size: 11pt; margin-top: 12px; }}
            p {{ margin-bottom: 10px; }}
            ul, ol {{ margin-left: 20px; margin-bottom: 10px; }}
            li {{ margin-bottom: 4px; }}
            code {{ font-family: Courier, monospace; background-color: #f6f4f0; color: #1c1c1c; font-size: 9pt; }}
            pre {{ background-color: #faf7f2; padding: 10px; border: 1px solid #ddd6c9; border-radius: 4px; font-size: 8.5pt; white-space: pre-wrap; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 12px; }}
            th, td {{ border: 1px solid #ddd6c9; padding: 6px 8px; text-align: left; font-size: 9pt; }}
            th {{ background-color: #f6f4f0; font-weight: bold; color: #1c1c1c; }}
        </style>
    </head>
    <body>{html_content}</body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(styled_html, dest=pdf_buffer)
    return pdf_buffer.getvalue()

# -- INLINE SVG ICONS (professional, no emoji) -----------------------------
ICON = {
    "diamond": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/><path d="M2 9h20"/></svg>',
    "home": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "studio": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    "chart": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="3" y1="20" x2="21" y2="20"/></svg>',
    "search": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    "pen": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    "user": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "check": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
}

# -- CSS STYLING -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --ink: #0A0B0F;
        --ink-raised: #0F1116;
        --surface: #14171E;
        --surface-2: #191D26;
        --surface-hover: #1E222C;
        --border: rgba(255,255,255,0.06);
        --border-mid: rgba(255,255,255,0.10);
        --border-strong: rgba(255,255,255,0.16);
        --text-primary: #E8EAEF;
        --text-secondary: #9096A4;
        --text-tertiary: #5A6070;
        --text-quaternary: #3A4050;
        --brass: #C89653;
        --brass-hover: #D4A362;
        --brass-dim: rgba(200,150,83,0.10);
        --brass-line: rgba(200,150,83,0.30);
        --moss: #6B9B7B;
        --moss-dim: rgba(107,155,123,0.10);
        --moss-line: rgba(107,155,123,0.28);
    }

    html, body, [class*="css"] {
        font-family: 'Inter Tight', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp { background: var(--ink) !important; color: var(--text-primary) !important; }

    .stAppViewContainer::before {
        content: "";
        position: fixed;
        inset: 0;
        background:
            radial-gradient(ellipse at 85% 0%, rgba(200,150,83,0.035) 0%, transparent 45%),
            radial-gradient(ellipse at 0% 100%, rgba(255,255,255,0.02) 0%, transparent 40%);
        pointer-events: none;
        z-index: 0;
    }

    .main .block-container {
        position: relative;
        z-index: 1;
        padding-top: 2.5rem !important;
        max-width: 1180px !important;
    }

    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: var(--ink-raised) !important;
        border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] > div { padding-top: 1.5rem !important; }

    section[data-testid="stSidebar"] h3 {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.68rem !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        color: var(--text-quaternary) !important;
        font-weight: 500 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        font-family: 'Inter Tight', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        transition: color 0.15s ease, background 0.15s ease !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--surface-hover) !important;
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-mid) !important;
        font-weight: 600 !important;
        position: relative !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]::before {
        content: "";
        position: absolute;
        left: 0; top: 8px; bottom: 8px;
        width: 2px;
        background: var(--brass);
        border-radius: 2px;
    }

    /* HERO */
    .hero-eyebrow {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--brass);
        text-align: center;
        margin-bottom: 12px;
    }
    .hero-eyebrow span.dash {
        display: inline-block;
        width: 26px;
        height: 1px;
        background: var(--brass-line);
        vertical-align: middle;
        margin: 0 10px;
    }
    .hero-title {
        text-align: center;
        font-family: 'Newsreader', serif;
        font-weight: 500;
        font-size: 3rem;
        color: var(--text-primary);
        margin-top: 0.4rem;
        margin-bottom: 0.75rem;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }
    .hero-title em { font-style: italic; color: var(--brass); font-weight: 500; }
    .hero-subtitle {
        text-align: center;
        font-size: 0.98rem;
        color: var(--text-secondary);
        max-width: 560px;
        margin: 0 auto 2.5rem auto;
        line-height: 1.55;
    }
    .hero-mark { display: flex; justify-content: center; margin-bottom: 0.5rem; }
    .hero-mark-inner {
        width: 44px; height: 44px;
        border: 1px solid var(--brass-line);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        color: var(--brass);
        background: var(--brass-dim);
    }

    /* CAPABILITY CARDS */
    .cap-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 22px 22px 24px 22px;
        min-height: 158px;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .cap-card:hover { border-color: var(--border-strong); transform: translateY(-1px); }
    .cap-card .cap-icon {
        color: var(--brass);
        margin-bottom: 14px;
        display: inline-flex;
        width: 34px; height: 34px;
        border: 1px solid var(--brass-line);
        border-radius: 8px;
        align-items: center; justify-content: center;
        background: var(--brass-dim);
    }
    .cap-card .cap-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-tertiary);
        margin-bottom: 8px;
    }
    .cap-card .cap-title {
        font-family: 'Newsreader', serif;
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 8px;
        letter-spacing: -0.01em;
    }
    .cap-card .cap-desc { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.55; }

    /* INPUT */
    .stTextInput input {
        background-color: var(--surface) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        padding: 16px 18px !important;
        font-family: 'Inter Tight', sans-serif !important;
        font-size: 0.96rem !important;
        box-shadow: none !important;
        transition: border-color 0.15s ease, background 0.15s ease !important;
    }
    .stTextInput input::placeholder { color: var(--text-tertiary) !important; }
    .stTextInput input:focus {
        border-color: var(--brass) !important;
        background-color: var(--surface-2) !important;
        box-shadow: 0 0 0 1px var(--brass) !important;
        outline: none !important;
    }
    .stTextArea textarea {
        background-color: var(--surface) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter Tight', sans-serif !important;
        font-size: 0.9rem !important;
    }
    .stTextArea textarea:focus { border-color: var(--brass) !important; box-shadow: 0 0 0 1px var(--brass) !important; }
    .stSelectbox > div > div {
        background-color: var(--surface) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 8px !important;
    }

    /* BUTTONS */
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        background: var(--brass) !important;
        color: var(--ink) !important;
        border: 1px solid var(--brass) !important;
        border-radius: 8px !important;
        font-family: 'Inter Tight', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 12px 22px !important;
        box-shadow: none !important;
        letter-spacing: 0.01em !important;
        transition: background 0.15s ease, transform 0.1s ease !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
        background: var(--brass-hover) !important;
        border-color: var(--brass-hover) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="primary"]:disabled {
        background: var(--surface-2) !important;
        color: var(--text-tertiary) !important;
        border-color: var(--border-mid) !important;
        transform: none !important;
    }
    .main .stButton > button:not([kind="primary"]),
    .stDownloadButton > button:not([kind="primary"]) {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 8px !important;
        font-family: 'Inter Tight', sans-serif !important;
        font-weight: 500 !important;
        padding: 12px 22px !important;
        font-size: 0.9rem !important;
        transition: all 0.15s ease !important;
    }
    .main .stButton > button:not([kind="primary"]):hover,
    .stDownloadButton > button:not([kind="primary"]):hover {
        border-color: var(--brass-line) !important;
        color: var(--brass) !important;
        background: var(--surface-hover) !important;
    }

    /* STATUS STAMPS */
    .stamp {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
        margin: 4px 0;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        width: 100%;
        box-sizing: border-box;
        border: 1px solid var(--border);
    }
    .stamp-active { background: var(--brass-dim); border-color: var(--brass-line); color: var(--brass); font-weight: 600; }
    .stamp-active::before {
        content: "";
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--brass);
        box-shadow: 0 0 0 3px var(--brass-dim);
        animation: pulse 1.5s ease-in-out infinite;
        flex-shrink: 0;
    }
    .stamp-done { background: var(--moss-dim); border-color: var(--moss-line); color: var(--moss); }
    .stamp-done::before { content: "✓"; font-size: 0.8rem; line-height: 1; flex-shrink: 0; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* CONTAINERS */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--border-mid) !important;
        background: var(--surface) !important;
        border-radius: 10px !important;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid var(--border-mid) !important;
        background: var(--surface) !important;
    }
    .main h2 {
        font-family: 'Newsreader', serif !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.015em !important;
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
    }
    .main h3 {
        font-family: 'Newsreader', serif !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em !important;
    }
    hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

    .mono-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-tertiary);
        font-weight: 500;
    }
    .section-header { display: flex; align-items: baseline; gap: 14px; margin-bottom: 20px; }
    .section-header .rule { flex: 1; height: 1px; background: var(--border); }

    .topic-plate {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 2px solid var(--brass);
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }
    .topic-plate .label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.64rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--text-tertiary);
        margin-bottom: 4px;
    }
    .topic-plate .value {
        font-family: 'Newsreader', serif;
        font-size: 1.1rem;
        color: var(--text-primary);
        font-weight: 500;
    }

    div[data-testid="stStatus"] {
        background: var(--surface) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 8px !important;
    }
    .main code {
        background: var(--surface-2) !important;
        color: var(--brass) !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85em !important;
    }

    .session-line {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px dashed var(--border);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
    }
    .session-line:last-child { border-bottom: none; }
    .session-line .k {
        color: var(--text-tertiary);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-size: 0.68rem;
    }
    .session-line .v { color: var(--text-primary); }
</style>
""", unsafe_allow_html=True)

# -- GRAPH EXECUTION HELPERS -----------------------------------------------
NODE_METADATA = {
    "research": {"label": "Web Research Agent", "code": "RSC"},
    "fact_check_and_write": {"label": "Draft Writer & Reviewer", "code": "WRT"},
    "human_review": {"label": "Human Approval Gate", "code": "HRG"},
}

def render_sidebar_node_path(container, current_node=None):
    with container:
        st.markdown('<div class="mono-label" style="margin-bottom:10px;">Live execution</div>', unsafe_allow_html=True)
        history = st.session_state.get("execution_path", [])
        if not history:
            st.markdown(
                '<div style="font-family:\'JetBrains Mono\',monospace; font-size:0.72rem; color:var(--text-quaternary); padding:6px 0;">— idle —</div>',
                unsafe_allow_html=True,
            )
            return

        for idx, node in enumerate(history):
            meta = NODE_METADATA.get(node, {"label": node, "code": "···"})
            is_active = (node == current_node and idx == len(history) - 1)

            if is_active:
                st.markdown(
                    f'<div class="stamp stamp-active"><span style="opacity:0.7;">{meta["code"]}</span> {meta["label"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="stamp stamp-done"><span style="opacity:0.65; margin-left:4px;">{meta["code"]}</span> {meta["label"]}</div>',
                    unsafe_allow_html=True,
                )

def run_graph_with_progress(graph_input, path_container) -> dict:
    with st.status("Agents at work…", expanded=True) as status:
        try:
            for chunk in research_graph.stream(graph_input, config=run_config(), stream_mode="updates"):
                if "__interrupt__" in chunk:
                    st.session_state.execution_path.append("human_review")
                    status.update(label="Draft ready for human approval", state="complete")
                    render_sidebar_node_path(path_container, current_node="human_review")
                    return chunk

                for node_name in chunk:
                    st.session_state.execution_path.append(node_name)
                    meta = NODE_METADATA.get(node_name, {"label": node_name})
                    st.markdown(f"→ Executed  **{meta['label']}**")
                    render_sidebar_node_path(path_container, current_node=node_name)

            status.update(label="Task finished successfully", state="complete")
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

# -- SIDEBAR ---------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; padding: 4px 4px 2px 4px;">
            <div style="width:36px; height:36px; border:1px solid var(--brass-line); border-radius:8px;
                        display:flex; align-items:center; justify-content:center; color:var(--brass); background: var(--brass-dim);">
                {ICON["diamond"]}
            </div>
            <div>
                <div style="font-family:'Newsreader',serif; font-weight:600; font-size:1.05rem; color:var(--text-primary); line-height:1.1;">Agent System</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.6rem; letter-spacing:0.18em; text-transform:uppercase;
                            color:var(--text-quaternary); margin-top:4px;">Research · v2.0</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()

    st.markdown("### Workspace")

    if st.button("  Home", use_container_width=True,
                 type="primary" if st.session_state.active_page == "hub" else "secondary",
                 key="nav_hub"):
        st.session_state.active_page = "hub"
        st.rerun()
    if st.button("  Research Studio", use_container_width=True,
                 type="primary" if st.session_state.active_page == "studio" else "secondary",
                 key="nav_studio"):
        st.session_state.active_page = "studio"
        st.rerun()
    if st.button("  Analytics", use_container_width=True,
                 type="primary" if st.session_state.active_page == "analytics" else "secondary",
                 key="nav_analytics"):
        st.session_state.active_page = "analytics"
        st.rerun()

    st.markdown("### Report Parameters")
    depth_option = st.selectbox(
        "Length",
        options=["Quick Overview", "Standard Report", "Detailed Breakdown"],
        index=1,
    )
    tone_option = st.selectbox(
        "Tone",
        options=["Simple & Clear", "Business Executive", "Academic & Technical"],
        index=0,
    )
    custom_instructions = st.text_area(
        "Additional instructions",
        placeholder="Keep it concise, define jargon, use bullet points…",
        height=80,
    )

    st.session_state.research_config = {
        "depth": depth_option,
        "style": tone_option,
        "instructions": custom_instructions
    }

    st.markdown("### Status")
    sidebar_path_container = st.container()
    render_sidebar_node_path(sidebar_path_container)

    st.divider()
    if st.session_state.stage != "idle":
        if st.button("↺  Start new session", use_container_width=True, key="nav_reset"):
            reset_state()
            st.session_state.active_page = "hub"
            st.rerun()

# API Key check
if not app_config.GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is missing from `.env` file.")
    st.stop()


# ===========================================================================
# PAGE 1: HOME
# ===========================================================================
if st.session_state.active_page == "hub":

    st.markdown(
        f"""
        <div style="margin-top: 8px;">
            <div class="hero-mark">
                <div class="hero-mark-inner">{ICON["diamond"]}</div>
            </div>
            <div class="hero-eyebrow">
                <span class="dash"></span>Multi-Agent Research Platform<span class="dash"></span>
            </div>
            <h1 class="hero-title">How can I <em>assist</em> your research today?</h1>
            <p class="hero-subtitle">
                A coordinated workspace where autonomous agents gather sources,
                verify facts, and draft publication-ready reports — with you in the loop.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        topic_input = st.text_input(
            "Search Prompt",
            placeholder="Enter a topic, question, or brief…",
            label_visibility="collapsed"
        )

        col_a, col_b = st.columns([1, 2.2])
        with col_a:
            start = st.button(
                "Start research  →",
                type="primary",
                use_container_width=True,
                disabled=not topic_input
            )
        with col_b:
            st.markdown(
                '<div style="padding-top: 14px;"><span class="mono-label">3 agents · avg. 90s · human approval gate</span></div>',
                unsafe_allow_html=True,
            )

        if start:
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.topic = topic_input
            st.session_state.stage = "running"
            st.session_state.execution_path = []
            st.session_state.active_page = "studio"
            st.rerun()

    st.write("")
    st.write("")

    st.markdown(
        """
        <div class="section-header">
            <span class="mono-label">Capabilities</span>
            <div class="rule"></div>
            <span class="mono-label" style="color:var(--text-quaternary);">03</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="cap-card">
                <div class="cap-icon">{ICON["search"]}</div>
                <div class="cap-tag">Capability · 01</div>
                <div class="cap-title">Deep web research</div>
                <div class="cap-desc">Retrieves live internet sources and extracts verified, cited data points across domains.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="cap-card">
                <div class="cap-icon">{ICON["pen"]}</div>
                <div class="cap-tag">Capability · 02</div>
                <div class="cap-title">Editorial synthesis</div>
                <div class="cap-desc">Translates dense material into structured, readable narratives with sections and citations.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="cap-card">
                <div class="cap-icon">{ICON["user"]}</div>
                <div class="cap-tag">Capability · 03</div>
                <div class="cap-title">Human-in-the-loop</div>
                <div class="cap-desc">Review each draft before export. Request revisions or approve for PDF and Markdown output.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ===========================================================================
# PAGE 2: RESEARCH STUDIO
# ===========================================================================
elif st.session_state.active_page == "studio":
    st.markdown(
        """
        <div class="section-header">
            <h2 style="margin:0;">Research Studio</h2>
            <div class="rule"></div>
            <span class="mono-label" style="color:var(--text-quaternary);">Live</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.topic:
        st.warning("No active topic. Please start a query from the Home page.")
        if st.button("← Go to Home"):
            st.session_state.active_page = "hub"
            st.rerun()
        st.stop()

    st.markdown(
        f"""
        <div class="topic-plate">
            <div class="label">Active Topic</div>
            <div class="value">{st.session_state.topic}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.stage == "running":
        config = st.session_state.research_config
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

    elif st.session_state.stage == "awaiting_approval":
        payload = st.session_state.interrupt_payload
        current_state_values = research_graph.get_state(run_config()).values
        sources = current_state_values.get("sources", [])
        fact_check_notes = current_state_values.get("fact_check_notes", "No additional notes.")

        st.info("Draft ready. Review the report below, then approve or request revisions.")

        with st.expander("Discovered sources & fact-check notes", expanded=False):
            st.markdown("**Verification summary**")
            st.write(fact_check_notes)
            st.divider()
            st.markdown("**Web sources**")
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

        with st.container(border=True):
            st.markdown('<div class="mono-label" style="margin-bottom:12px;">Current draft</div>', unsafe_allow_html=True)
            st.markdown(payload["draft_report"])

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Approve report  ✓", type="primary", use_container_width=True):
                try:
                    decision = {"decision": "approved", "feedback": ""}
                    result = run_graph_with_progress(Command(resume=decision), sidebar_path_container)
                    handle_graph_result(result)
                except Exception as e:
                    st.session_state.error = str(e)
                st.rerun()

        with col2:
            if st.button("Request revisions", use_container_width=True):
                st.session_state.show_feedback_box = True

        if st.session_state.get("show_feedback_box"):
            st.write("")
            with st.container(border=True):
                st.markdown('<div class="mono-label" style="margin-bottom:10px;">Revision instructions</div>', unsafe_allow_html=True)
                feedback = st.text_area(
                    "Feedback Input",
                    placeholder="e.g. Simplify the terms used, add a section explaining how it works…",
                    label_visibility="collapsed",
                    height=120,
                )

                if st.button("Submit to agents  →", type="primary"):
                    if feedback.strip():
                        try:
                            revised_feedback = (
                                f"REVISION REQUEST: {feedback.strip()}\n"
                                "INSTRUCTION: Rewrite the report in clear, simple language addressing the user's specific feedback above."
                            )
                            decision = {"decision": "rejected", "feedback": revised_feedback}
                            result = run_graph_with_progress(Command(resume=decision), sidebar_path_container)
                            handle_graph_result(result)
                            st.session_state.show_feedback_box = False
                        except Exception as e:
                            st.session_state.error = str(e)
                        st.rerun()
                    else:
                        st.warning("Please type your feedback before submitting.")

    elif st.session_state.stage == "done":
        if st.session_state.get("celebrate"):
            st.balloons()
            st.session_state.celebrate = False

        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; padding:12px 16px;
                        background: var(--moss-dim); border:1px solid var(--moss-line); border-radius:8px;
                        margin-bottom: 20px;">
                <span style="color: var(--moss);">{ICON["check"]}</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.78rem;
                             letter-spacing:0.08em; text-transform:uppercase; color: var(--moss); font-weight:600;">
                    Final report approved · ready for export
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(st.session_state.final_report)

        st.write("")

        col1, col2 = st.columns(2)
        file_slug = st.session_state.topic.lower().replace(" ", "_") if st.session_state.topic else "research"
        pdf_data = convert_markdown_to_pdf(st.session_state.final_report)

        with col1:
            st.download_button(
                "Download PDF  ↓",
                data=pdf_data,
                file_name=f"{file_slug}_report.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        with col2:
            st.download_button(
                "Download Markdown  ↓",
                data=st.session_state.final_report,
                file_name=f"{file_slug}_report.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ===========================================================================
# PAGE 3: ANALYTICS
# ===========================================================================
elif st.session_state.active_page == "analytics":
    st.markdown(
        """
        <div class="section-header">
            <h2 style="margin:0;">System Analytics</h2>
            <div class="rule"></div>
            <span class="mono-label" style="color:var(--text-quaternary);">Architecture · Session</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    col_graph, col_logs = st.columns([1, 1])

    with col_graph:
        with st.container(border=True):
            st.markdown('<div class="mono-label" style="margin-bottom:12px;">Workflow graph</div>', unsafe_allow_html=True)
            try:
                graph_image = research_graph.get_graph().draw_mermaid_png()
                st.image(graph_image, caption="Multi Research Agent System — flow", use_container_width=True)
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
            st.markdown('<div class="mono-label" style="margin-bottom:12px;">Session details</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="session-line"><span class="k">Thread ID</span><span class="v">{st.session_state.thread_id or 'N / A'}</span></div>
                <div class="session-line"><span class="k">Status</span><span class="v">{st.session_state.stage}</span></div>
                <div class="session-line"><span class="k">Steps Run</span><span class="v">{len(st.session_state.execution_path)}</span></div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")
            st.markdown('<div class="mono-label" style="margin-top:8px; margin-bottom:8px;">Execution log</div>', unsafe_allow_html=True)
            if st.session_state.execution_path:
                for idx, step in enumerate(st.session_state.execution_path, 1):
                    st.markdown(
                        f'<div style="font-family:\'JetBrains Mono\',monospace; font-size:0.78rem; color:var(--text-secondary); padding:4px 0;">'
                        f'<span style="color:var(--text-quaternary);">{idx:02d}</span> &nbsp;→&nbsp; '
                        f'<span style="color:var(--brass);">{step}</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No log history for this session.")