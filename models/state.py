"""
models/state.py
----------------
Defines the shared "state" object that flows through every node in
our LangGraph graph.

WHY a TypedDict? LangGraph needs to know the *shape* of the data that
moves between nodes, so it can merge updates correctly. TypedDict is
a lightweight way to say "this dictionary will always have these
keys, with these types" — you get autocomplete and type-checking in
your editor, without the overhead of a full class.

Each node function will receive the CURRENT state and return a
dictionary with just the fields it wants to UPDATE. LangGraph merges
that into the overall state automatically.
"""

from typing import TypedDict, List, Optional, Literal


class ResearchState(TypedDict):
    # --- Input ---
    topic: str
    # The research question/topic the user submitted, e.g.
    # "What are the environmental impacts of lithium mining?"

    # --- Filled in by the research_node (via the CrewAI crew) ---
    raw_research: Optional[str]
    # Unstructured findings gathered by the CrewAI research crew.

    sources: List[str]
    # List of URLs/citations the research crew used. We keep this
    # separate from raw_research so we can display "Sources:" cleanly
    # in the final report.

    # --- Filled in by the fact_check_node ---
    fact_check_notes: Optional[str]
    # Notes on which claims were verified, disputed, or unverifiable.

    verified: Optional[bool]
    # True if fact-checking passed, False if serious issues were found.
    # This is a good chance to explain WHY we use Optional[bool] and
    # not just bool: at the very start of the workflow, fact-checking
    # hasn't happened yet, so the value doesn't just default to False
    # (which would incorrectly mean "failed") — it's genuinely
    # "unknown yet", which None represents.

    # --- Filled in by the write_node ---
    draft_report: Optional[str]
    # The full written report in Markdown, before human review.

    # --- Filled in / read by the human_approval_node ---
    approval_status: Optional[Literal["pending", "approved", "rejected"]]
    # Literal restricts the value to exactly these three strings —
    # nothing else is allowed. This prevents typos like "aproved"
    # from silently breaking your workflow logic.

    approval_feedback: Optional[str]
    # If a human rejects the draft, their feedback goes here so the
    # write_node can revise and try again.

    # --- Filled in by the finalize_node ---
    final_report: Optional[str]
    # The polished, human-approved final version.

    # --- Bookkeeping ---
    revision_count: int
    # Tracks how many times we've looped back for revisions, so we
    # can cap retries and avoid an infinite loop (a real risk in
    # human-in-the-loop systems if you don't guard against it).
