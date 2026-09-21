# Product Feedback Agent — Implementation Plan

## Overview

A local Streamlit application powered by a single OpenAI Agents SDK agent.  
It ingests customer feedback from a CSV file, identifies recurring themes, consults local product documentation, and proposes product opportunities backed by evidence.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                 │
│  CSV upload ──► run analysis ──► display results         │
└───────────────────────┬─────────────────────────────────┘
                        │ calls
┌───────────────────────▼─────────────────────────────────┐
│                 Agent (agent/core.py)                    │
│  Single OpenAI Agents SDK agent with two tools:          │
│  • analyse_feedback(csv_text) → themes + raw evidence    │
│  • lookup_docs(query)        → relevant doc snippets     │
└───────────┬───────────────────────┬─────────────────────┘
            │                       │
   OpenAI API               Local /docs folder
   (GPT-4o)                 (plain .txt / .md files)
```

**No database, no vector store, no external services beyond the model API.**

### User flow
1. User uploads a CSV file via the Streamlit sidebar.
2. The app validates the file with Pandas and extracts the feedback column.
3. The agent receives the feedback text and calls its tools in a loop:
   - First pass: cluster themes and surface evidence quotes.
   - Doc lookup: for each theme, search `/docs` for relevant context.
4. The agent returns a structured Pydantic model with themes and opportunities.
5. Streamlit renders the results as expandable cards.

---

## File Structure (minimum viable)

```
product-feedback-agent/
├── .env                    # OPENAI_API_KEY (never committed)
├── .gitignore
├── README.md
├── IMPLEMENTATION_PLAN.md  # this file
├── requirements.txt        # pinned dependencies
├── app.py                  # Streamlit entry point
├── agent/
│   ├── __init__.py
│   ├── core.py             # agent definition + runner
│   ├── tools.py            # tool functions (feedback analysis, doc lookup)
│   └── schemas.py          # Pydantic models for inputs/outputs
├── docs/                   # local product documentation (plain text / markdown)
│   └── example_product_doc.md
└── data/
    └── sample_feedback.csv # sample file for testing
```

---

## Phases and Acceptance Criteria

### Phase 1 — Project scaffold (current)
**Goal:** Establish the skeleton before writing any logic.

| # | Task | Acceptance Criteria |
|---|------|---------------------|
| 1.1 | Inspect folder & Python | Confirmed Python ≥ 3.11 on the Mac; folder is empty |
| 1.2 | Create `IMPLEMENTATION_PLAN.md` | This file exists and is committed |
| 1.3 | Create `.gitignore` | Covers Python, macOS, `.env`, venv, SQLite, generated files |
| 1.4 | Init git repository | `git status` returns clean working tree after first commit |

**Done when:** repo exists, `.gitignore` is in place, no application code yet.

---

### Phase 2 — Dependencies and configuration
**Goal:** Reproducible environment.

| # | Task | Acceptance Criteria |
|---|------|---------------------|
| 2.1 | Create `requirements.txt` | All packages pinned; `pip install -r requirements.txt` succeeds |
| 2.2 | Create `.env.example` | Shows required keys without actual values |
| 2.3 | Create `README.md` | Contains setup instructions (venv, install, run) |

**Done when:** a fresh `python -m venv venv && pip install -r requirements.txt` completes without errors.

---

### Phase 3 — Agent and tools
**Goal:** The agent can analyse feedback and look up docs without a UI.

| # | Task | Acceptance Criteria |
|---|------|---------------------|
| 3.1 | `agent/schemas.py` | Pydantic models: `FeedbackInput`, `Theme`, `Opportunity`, `AnalysisResult` |
| 3.2 | `agent/tools.py` | `analyse_feedback` and `lookup_docs` pass unit tests |
| 3.3 | `agent/core.py` | Agent runs end-to-end on `sample_feedback.csv`; returns valid `AnalysisResult` |
| 3.4 | Add sample doc to `/docs` | `lookup_docs` returns relevant snippet for a known query |

**Done when:** `python -c "from agent.core import run_agent; print(run_agent('...'))"` returns structured JSON.

---

### Phase 4 — Streamlit UI
**Goal:** Full working application, usable in a demo.

| # | Task | Acceptance Criteria |
|---|------|---------------------|
| 4.1 | `app.py` basic shell | `streamlit run app.py` opens without errors |
| 4.2 | CSV upload + validation | Bad files show a clear error; valid files show a row count |
| 4.3 | Run analysis button | Triggers agent, shows spinner, displays results |
| 4.4 | Results rendering | Themes, evidence quotes, and opportunities displayed as expandable cards |
| 4.5 | Error handling | API errors, missing key, malformed CSV all surface friendly messages |

**Done when:** full demo flow works on a real CSV with at least 20 rows of feedback.

---

### Phase 5 — Polish and interview readiness
**Goal:** Code quality and presentation fit for a Senior PM interview.

| # | Task | Acceptance Criteria |
|---|------|---------------------|
| 5.1 | Add `sample_feedback.csv` | ≥ 20 diverse feedback rows covering 3–5 themes |
| 5.2 | Add product doc(s) to `/docs` | Agent demonstrably uses them to enrich at least one opportunity |
| 5.3 | Code review pass | No hardcoded secrets; clear comments on non-obvious logic |
| 5.4 | End-to-end smoke test | Fresh venv, `streamlit run app.py`, upload CSV, get results — all pass |

---

## Risks and Open Questions

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Python version mismatch | Medium | Low | The Mac likely has 3.11+ via Homebrew/pyenv; verify before Phase 2 |
| OpenAI Agents SDK API changes | Low | High | Pin exact version in `requirements.txt`; check release notes |
| Large CSVs exceed model context window | Medium | Medium | Truncate or chunk feedback in Phase 3; document the limit |
| Doc lookup quality without embeddings | Medium | Medium | Use keyword search first; upgrade to embeddings only if quality is insufficient |
| `streamlit` not pre-installed | Low | Low | Handled by `requirements.txt` |
| Rate limits on OpenAI API | Low | Low | Add exponential back-off in Phase 3 tool wrapper |

---

## Technology Decisions

| Decision | Rationale |
|----------|-----------|
| Single agent, no orchestrator | Keeps the code readable; a PM can trace every decision |
| Tools as plain Python functions | No framework magic; easier to test and explain |
| Pydantic for outputs | Enforces structure; makes the agent's output reliable and self-documenting |
| `/docs` as plain text files | Zero infrastructure; easy to update during a demo |
| Streamlit | One-file UI, no HTML/CSS, runs locally, looks professional |
| No SQLite | Feedback is ephemeral per session; persistence adds complexity without value at this stage |
