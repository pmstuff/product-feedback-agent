"""
schemas.py — Pydantic v2 models for the Product Feedback Agent.

AgentInput   : what the caller passes to run_agent().
AnalysisResult : the structured output the agent must produce.

All models are used both as agent output_type (OpenAI structured output)
and for serialisation / UI display.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ─── Input ────────────────────────────────────────────────────────────────────

class AgentInput(BaseModel):
    """Caller-supplied context for a single analysis run."""

    product_name: str
    product_description: str = ""
    feedback_text: str  # pre-validated, newline-separated rows


# ─── Output building blocks ───────────────────────────────────────────────────

class EvidenceQuote(BaseModel):
    """A verbatim quote taken from the feedback, with its source row ID."""

    quote: str = Field(description="Verbatim text from the feedback.")
    feedback_id: Optional[str] = Field(
        default=None,
        description="The feedback_id of the row this quote was taken from (e.g. 'FB-012').",
    )


class Theme(BaseModel):
    """A recurring topic or complaint cluster found in the feedback."""

    title: str = Field(description="Short name for this theme (3–6 words).")
    description: str = Field(description="What the theme covers and why it matters to users.")
    frequency: int = Field(description="Number of feedback rows that mention this theme.")
    evidence: list[EvidenceQuote] = Field(
        description="2–3 verbatim quotes that best illustrate this theme."
    )


class Opportunity(BaseModel):
    """A product improvement opportunity derived from one or more themes."""

    title: str = Field(description="Short, action-oriented title (e.g. 'Add CSV export beyond 10k rows').")
    problem_statement: str = Field(
        description="One sentence describing the user problem this opportunity solves."
    )
    rationale: str = Field(
        description="Why this opportunity is worth prioritising, referencing feedback themes."
    )
    linked_themes: list[str] = Field(
        description="Titles of themes this opportunity addresses."
    )
    evidence_feedback_ids: list[str] = Field(
        description=(
            "feedback_id values (e.g. 'FB-007') of rows that support this opportunity. "
            "Must only contain IDs present in the supplied feedback."
        )
    )
    affected_segments: list[str] = Field(
        description="Customer segments most affected (e.g. ['Enterprise', 'Mid-market'])."
    )
    category: str = Field(
        description="Functional area (e.g. 'Export', 'Permissions', 'Integration', 'Onboarding', 'Performance')."
    )
    doc_reference: Optional[str] = Field(
        default=None,
        description="Name of the product-docs file most relevant to this opportunity, if any.",
    )
    documentation_sources: list[str] = Field(
        default_factory=list,
        description="Snippets or file names from product docs that informed this opportunity.",
    )
    priority: int = Field(ge=1, le=5, description="Overall priority score 1 (low) – 5 (critical).")
    impact_score: int = Field(ge=1, le=5, description="Estimated user impact 1–5.")
    confidence_score: int = Field(
        ge=1, le=5,
        description="How confident we are in this opportunity based on evidence volume 1–5.",
    )
    recommendation: str = Field(
        description="Concise recommendation for the PM team (one or two sentences)."
    )


# ─── Top-level result ─────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """Complete structured output from one analysis run."""

    product_name: str
    total_feedback_rows: int = Field(description="Total number of feedback rows analysed.")

    executive_summary: str = Field(
        description=(
            "3-sentence summary for a VP of Product: top finding, biggest risk, "
            "and highest-priority action."
        )
    )
    themes: list[Theme] = Field(description="2–5 recurring themes found in the feedback.")
    opportunities: list[Opportunity] = Field(
        description="2–4 product opportunities ordered by priority (highest first)."
    )
    summary: str = Field(
        description="One-paragraph narrative summary suitable for a product review."
    )
    positive_signals: list[str] = Field(
        description="Things users explicitly praised or said were working well."
    )
    ambiguous_feedback: list[str] = Field(
        description="Feedback items that were unclear or contradictory, worth follow-up."
    )
    limitations: list[str] = Field(
        description="Caveats about this analysis (e.g. sample size, channel bias)."
    )
