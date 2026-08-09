"""
models/schemas.py
------------------
TypedDict (state.py) vs Pydantic (this file) — what's the difference?

  - TypedDict: just a type HINT for a plain dict. Python does NOT
    actually check or enforce it at runtime. It's for LangGraph's
    internal bookkeeping and your editor's autocomplete.

  - Pydantic BaseModel: a REAL class that validates data at runtime.
    If you try to create one with the wrong type, it raises an error
    immediately. We use Pydantic when we want the LLM's output
    (which is just text) to be forced into a strict, reliable shape
    we can trust in code — e.g. "the fact-checker's verdict must be
    exactly one of these three strings, and confidence must be a
    number between 0 and 1."

Rule of thumb: TypedDict for internal graph plumbing, Pydantic for
data whose correctness actually matters (LLM outputs, API payloads).
"""

from pydantic import BaseModel, Field
from typing import List, Literal


class FactCheckResult(BaseModel):
    """Structured verdict from the fact-checking step."""

    verdict: Literal["verified", "disputed", "unverifiable"]
    # Field(...) below lets us attach a human-readable description
    # AND validation rules to each field. The "..." means this field
    # is required (no default value).
    confidence: float = Field(
        ...,
        ge=0.0,  # ge = "greater than or equal to" — enforces a floor
        le=1.0,  # le = "less than or equal to" — enforces a ceiling
        description="Confidence score from 0 (no confidence) to 1 (fully confident).",
    )
    notes: str = Field(..., description="Explanation of the verdict.")
    flagged_claims: List[str] = Field(
        default_factory=list,
        description="Specific claims that could not be verified.",
    )
    # default_factory=list (not default=[]) is important: in Python,
    # mutable defaults like [] are created ONCE and shared across
    # every instance if you write it directly, causing a notorious
    # bug. default_factory calls list() fresh for each new object.


class ResearchFindings(BaseModel):
    """Structured output from the CrewAI research crew."""

    summary: str
    key_points: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    """What a human reviewer submits at the human-approval step."""

    decision: Literal["approved", "rejected"]
    feedback: str = ""
