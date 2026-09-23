"""
tools.py — Function tools for the Product Feedback Agent.

Both tools are decorated with @function_tool from the OpenAI Agents SDK so that
the Agent can call them during a run.

Security notes:
  - Feedback content is treated as data, never as instructions.
  - search_product_docs reads only from data/product_docs/ — no other filesystem access.
  - save_opportunity validates the JSON against the Opportunity schema and returns
    errors back to the agent rather than raising exceptions, so the agent can self-correct.
"""
from __future__ import annotations

import json
from pathlib import Path

from agents import function_tool

# ─── Constants ────────────────────────────────────────────────────────────────

DOCS_DIR = Path(__file__).parent / "data" / "product_docs"
_SNIPPET_CHARS = 600   # characters to return around a keyword match
_MAX_SNIPPETS = 5      # maximum number of snippets per query


# ─── Tool: search_product_docs ────────────────────────────────────────────────

@function_tool
def search_product_docs(query: str) -> str:
    """Search the product documentation for content relevant to a query.

    Performs a case-insensitive keyword search across all .md and .txt files in
    the product docs directory and returns matching snippets with their source
    file names. Use this to ground opportunities in documented product behaviour,
    limitations, or roadmap items.

    Args:
        query: A keyword or short phrase to look up (e.g. "export limit",
               "permissions", "Salesforce integration").

    Returns:
        Matching documentation snippets prefixed with [filename], or a message
        stating that nothing was found.
    """
    if not DOCS_DIR.exists():
        return "No product documentation found. The docs directory does not exist."

    doc_files = list(DOCS_DIR.glob("**/*.md")) + list(DOCS_DIR.glob("**/*.txt"))
    if not doc_files:
        return "No documentation files found in the product docs directory."

    keywords = [kw.strip().lower() for kw in query.split() if kw.strip()]
    if not keywords:
        return "Empty query — please provide at least one keyword."

    snippets: list[str] = []

    for doc_path in sorted(doc_files):
        try:
            text = doc_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        text_lower = text.lower()

        for keyword in keywords:
            idx = text_lower.find(keyword)
            if idx == -1:
                continue

            # Extract a window around the match
            start = max(0, idx - _SNIPPET_CHARS // 2)
            end = min(len(text), idx + _SNIPPET_CHARS // 2)
            snippet = text[start:end].strip()

            # Add ellipsis markers when we've trimmed the text
            if start > 0:
                snippet = "…" + snippet
            if end < len(text):
                snippet = snippet + "…"

            snippets.append(f"[{doc_path.name}]\n{snippet}")

            if len(snippets) >= _MAX_SNIPPETS:
                break

        if len(snippets) >= _MAX_SNIPPETS:
            break

    if not snippets:
        return f"No documentation found matching '{query}'."

    return "\n\n---\n\n".join(snippets)


# ─── Tool: save_opportunity ───────────────────────────────────────────────────

@function_tool
def save_opportunity(opportunity_json: str) -> str:
    """Validate and record a product opportunity identified from the feedback.

    Call this tool once per opportunity before including it in the final output.
    It validates the JSON against the Opportunity schema and returns either a
    confirmation or a list of validation errors so you can correct the data.

    The tool only validates — it does not persist data to disk. The validated
    opportunity must still appear in your final AnalysisResult output.

    Args:
        opportunity_json: A JSON string representing one opportunity. Required
            fields: title, problem_statement, rationale, linked_themes,
            evidence_feedback_ids, affected_segments, category, priority (1-5),
            impact_score (1-5), confidence_score (1-5), recommendation.

    Returns:
        "OK: <title>" on success, or a description of validation errors.
    """
    # Import here to avoid a circular import at module load time
    from schemas import Opportunity  # noqa: PLC0415

    try:
        data = json.loads(opportunity_json)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"

    try:
        opp = Opportunity.model_validate(data)
        return f"OK: '{opp.title}' validated successfully."
    except Exception as exc:  # pydantic ValidationError
        return f"Validation errors — please correct and retry:\n{exc}"
