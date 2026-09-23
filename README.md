# Product Feedback Agent

A local AI agent that reads a CSV of customer feedback, surfaces recurring themes, and generates evidence-backed product opportunities — grounded in your own product documentation.

Built as a learning exercise for a Senior PM interview demo. Not production-ready.

---

## The problem being solved

Product managers collect feedback from many sources (support tickets, user interviews, NPS surveys, sales calls) and must manually read through hundreds of rows to identify patterns. This process is slow, inconsistent, and biased toward recently-read items. Important signals from smaller customer segments often get lost.

This tool automates the first pass: given a CSV of raw feedback, it groups similar complaints into themes, checks what the product documentation says about each theme, and produces prioritised opportunities with verbatim evidence quotes and source IDs.

---

## Target user

A solo PM or a small PM team at a B2B SaaS company who:
- Collects feedback in a structured CSV format (support system, NPS tool, or CRM export)
- Has internal product documentation in Markdown
- Wants a first draft of "what should we build next" before their quarterly planning session
- Needs to show evidence for every claim (quotes + feedback IDs) because they'll present to a VP

---

## Product flow

```
1. User enters product name + description in the sidebar
2. User uploads a CSV (required columns: feedback_id, created_at,
   customer_segment, channel, feedback)
3. App validates and previews the CSV (counts, segments, channels)
4. User clicks "Analyse feedback"
5. Agent runs:
   a. Reads all feedback rows (labelled with IDs and context)
   b. Identifies 2–5 recurring themes
   c. Calls search_product_docs() for each theme to ground analysis in docs
   d. Calls save_opportunity() to validate each opportunity before finalising
   e. Returns a structured AnalysisResult (Pydantic schema)
6. App displays: executive summary, themes (with evidence), opportunities
   (with scores and evidence IDs), positive signals, ambiguous feedback,
   analysis limitations, and a tool-call trace panel
7. User can download the opportunities as JSON
8. Run metadata is appended to data/runs.jsonl for cost tracking
```

---

## Architecture

```
app.py              Streamlit UI — entry point, input/output rendering
agent.py            OpenAI Agents SDK agent — instructions, Runner.run_sync()
tools.py            Two @function_tool functions: search_product_docs, save_opportunity
schemas.py          Pydantic v2 models: AgentInput, AnalysisResult, Opportunity, Theme
validation.py       Deterministic CSV validation — no LLM, fully unit-tested
telemetry.py        Token counts, cost calculation, JSONL persistence
design/             Arco Design System tokens and CSS injected into Streamlit
data/
  product_docs/     Markdown documentation the agent can search (4 files included)
  sample_feedback.csv   40 synthetic feedback rows for Prism Analytics
evals/
  cases.json        10 controlled test cases (grouping, injection, hallucination, etc.)
  run_evals.py      Evaluation runner — deterministic checks + human-review notes
tests/
  test_validation.py   40 unit tests for validation.py
```

**Key design choice — single agent, flat files:** One agent processes all feedback in a single run. No chunking, no multi-agent routing, no vector database. This keeps the system simple enough to understand in full, and transparent enough to explain the output.

**LLM boundary:** The agent receives feedback text only in the user message, never in the system instructions. Instructions contain only trusted inputs: product name, product description, and the list of valid feedback IDs extracted by regex.

---

## Decisions made and alternatives rejected

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Framework | OpenAI Agents SDK (openai-agents 0.22.3) | LangChain, LlamaIndex | Fewer abstractions; direct inspection of SDK internals for the demo |
| Output format | Pydantic structured output (`output_type=AnalysisResult`) | Free-form text + regex parsing | Deterministic schema, Pydantic validation catches hallucinated fields |
| Feedback IDs in instructions | Extracted by regex, passed as a list | Full feedback in instructions | Prevents instruction hijacking by feedback content |
| Doc search | Keyword substring match in local .md files | Vector embeddings + similarity search | No external dependencies; easy to inspect; sufficient for small doc sets |
| Opportunity validation | `save_opportunity` tool (agent calls it per opportunity) | Post-run schema check | Agent can self-correct before finalising output; exposes the correction loop in the UI |
| UI | Streamlit | FastAPI + React | 1-file deployment; no build toolchain; fast to iterate |
| Token tracking | Parse `result.raw_responses` + `.usage` | OpenAI usage dashboard | In-app cost visibility for demo |
| Secret management | `.env` + `python-dotenv`; key loaded once at startup | Hardcoded in source / passed as arg | Standard pattern; key never logged or displayed |

---

## macOS installation

**Requirements:** Python 3.11+, an OpenAI API key with access to `gpt-4o`.

```bash
# 1. Clone the project
cd ~/projects   # or wherever you keep code
# (the project folder already exists at ~/Claude/Projects/Product\ Feedback\ Agent)

# 2. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...your-real-key...
```

---

## `.env` configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key. Never commit this. |
| `OPENAI_MODEL` | No | `gpt-4o` | Model for analysis. Use `gpt-4o-mini` while testing to cut costs by ~10×. |
| `MODEL_INPUT_PRICE_PER_MILLION` | No | `5.00` | USD per million input tokens. Update if you switch models. |
| `MODEL_OUTPUT_PRICE_PER_MILLION` | No | `15.00` | USD per million output tokens. |

---

## How to run Streamlit

```bash
# From the project root, with .venv active:
streamlit run app.py
```

The app opens at `http://localhost:8501`. It will show an error and stop immediately if `OPENAI_API_KEY` is not set.

**Demo quick-start:**
1. Enter `Prism Analytics` as the product name.
2. Paste this description into the sidebar:
   ```
   B2B SaaS analytics platform for SMB, Mid-market and Enterprise customers.
   Features: dashboards, CSV/PDF export, role-based permissions (Admin, Editor,
   Viewer), native database connectors, Google Analytics integration, Slack
   notifications (beta).
   ```
3. Upload `data/sample_feedback.csv`.
4. Click **Analyse feedback**.

Expected run time: 30–90 seconds. Expected cost: ~$0.04–$0.09 USD (gpt-4o).

---

## How to run tests

Unit tests cover `validation.py` only (40 tests, no API required):

```bash
# With .venv active:
python -m pytest tests/test_validation.py -v

# Or without pytest installed (custom runner):
python tests/test_validation.py
```

---

## How to run evaluations

**Static checks only (no API cost):**
```bash
python evals/run_evals.py
```

This validates `evals/cases.json` structure: unique IDs, correct ID format, valid cross-references. 7 checks, all deterministic.

**Live evaluation (calls the API):**
```bash
python evals/run_evals.py --run-live
```

The runner will print a cost estimate and ask for confirmation before making any API calls. Results are saved to `evals/results_<timestamp>.json`.

**Single case:**
```bash
python evals/run_evals.py --run-live --case case-08
```

**Deterministic checks in the live run:**
- No hallucinated feedback IDs (evidence IDs must be in the permitted set)
- Opportunity count within expected bounds
- No forbidden terms in output (prompt injection resistance)
- Max confidence score respected for low-evidence cases
- Expected tools were called
- Positive-only feedback generates no opportunities
- Grouped themes cover the expected IDs

**Semantic checks (human review):** Case-02 (should separate export vs dashboard themes), case-03 (should recognise PDF export as existing), and others flag `NEEDS_HUMAN_REVIEW` in the output.

---

## Quality, usage, and cost metrics

From static analysis and design:

| Metric | Value |
|---|---|
| Unit tests | 40 (all passing) |
| Static eval checks | 7/7 passing |
| Eval cases | 10 (4 deterministic-only, 3 mixed, 2 semantic, 1 mixed-injection) |
| Lines of production Python | ~900 (agent.py, app.py, telemetry.py, schemas.py, tools.py, validation.py) |
| Estimated cost per run (40-row CSV, gpt-4o) | ~$0.04–$0.09 USD |
| Typical run time | 30–90 seconds |
| Max feedback size | 80,000 characters (~1,000 rows at average length) |
| Product docs supported | Any `.md` or `.txt` files in `data/product_docs/` |

A live run on the 40-row sample CSV (Prism Analytics) could not be executed in the CI sandbox because the runtime environment is a Linux container that lacks the Mac-compiled binary extensions (`pydantic_core`, `openai-agents`). Run it locally with `streamlit run app.py` or `python scripts/run_headless.py` (see below).

**Headless smoke test (no Streamlit):**
```bash
python3 -c "
import os, sys, time
from pathlib import Path

# Load .env manually
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('='); os.environ.setdefault(k.strip(), v.strip())

import pandas as pd
from validation import validate_dataframe
from schemas import AgentInput
from agent import run_agent
from telemetry import calculate_cost

df = pd.read_csv('data/sample_feedback.csv')
vr = validate_dataframe(df)
rows = [f\"[{r.feedback_id}] ({r.customer_segment}, {r.channel}) {r.feedback}\"
        for _, r in vr.cleaned_df.iterrows() if str(r.feedback).strip()]
t0 = time.monotonic()
analysis, info = run_agent(AgentInput(
    product_name='Prism Analytics',
    product_description='B2B SaaS analytics platform.',
    feedback_text='\n'.join(rows)
))
elapsed = time.monotonic() - t0
cost = calculate_cost(info.input_tokens, info.output_tokens)
print(f'Done in {elapsed:.1f}s | {info.total_tokens:,} tokens | \${cost:.4f}')
print(f'Themes: {len(analysis.themes)} | Opportunities: {len(analysis.opportunities)}')
for o in analysis.opportunities:
    print(f'  P{o.priority} [{o.category}] {o.title}')
"
```

---

## Limitations

1. **Single-run, no memory.** Each CSV upload is a fresh analysis. There is no way to compare runs, track changes over time, or accumulate a feedback database.

2. **10,000-character feedback soft cap.** The `MAX_FEEDBACK_CHARS = 80_000` constant in `agent.py` truncates very large batches silently. The agent does not know it is seeing a subset.

3. **Keyword-only doc search.** `search_product_docs` splits the query on whitespace and looks for any keyword in the document text. It will miss synonyms, miss context, and return unhelpful snippets for vague queries.

4. **Non-deterministic output.** Running the same CSV twice will produce different themes, different scores, different evidence selections. The agent is a language model, not a deterministic algorithm.

5. **Segment and channel schema is hardcoded.** `VALID_SEGMENTS` and `VALID_CHANNELS` are fixed in `validation.py`. Any company with different segment names must edit the source code.

6. **Evidence ID accuracy is not guaranteed.** The agent is instructed to use only IDs from the valid list, but this is a language model instruction, not a code constraint. The eval runner checks for hallucination; the UI does not.

7. **No authentication.** The Streamlit app has no login. Anyone with network access to the running process can submit feedback.

8. **Cost is estimated, not metered.** Prices in `.env` are self-reported. If OpenAI changes its pricing, the cost display is wrong until the user updates `.env`.

---

## Production risks

| Risk | Severity | Note |
|---|---|---|
| API key exposure | High | Key is in `.env` on the developer's laptop. Any process with env access can read it. |
| Prompt injection | Medium | Feedback text is separated from instructions, but a sophisticated attack across multiple tool calls is not ruled out. |
| Hallucinated evidence IDs | Medium | The agent may cite IDs that don't exist. The eval runner checks this; the production UI does not block on it. |
| Model non-determinism | Medium | Two analysts running the same CSV will get different results. No audit trail for what changed and why. |
| Unacknowledged truncation | Medium | Large batches are silently truncated to 80,000 chars. The user does not know. |
| No rate limiting | Low | A user can click "Analyse" repeatedly, burning API quota with no cap. |
| Stale prices | Low | Cost estimates are wrong if model pricing changes and `.env` is not updated. |

---

## Three-step roadmap

**Step 1 — Reliability (before sharing with others):**
Add an explicit evidence ID validator in the UI (not just in evals). If the agent cites `FB-999` and the CSV only goes to `FB-040`, flag it visually. Add a "run again" button with a seed-style label so two outputs can be compared side by side.

**Step 2 — Flexibility (before real customer data):**
Make `VALID_SEGMENTS` and `VALID_CHANNELS` configurable per upload (detect from the CSV itself, with a confirmation step). Add a row-size warning at, say, 500 rows, and a chunking strategy for very large batches. Persist analysis results (not just telemetry) to a local SQLite database so runs can be reviewed without re-running.

**Step 3 — Collaboration (before a team uses it):**
Add Streamlit authentication (`st.experimental_user` or a simple password gate). Move the JSONL telemetry to a shared store so the team can see all runs. Add a "compare runs" view that diffs themes and opportunities between two runs.

---

## Screenshots

*Screenshots are pending — they require a live Streamlit session. Run `streamlit run app.py` and capture:*

1. The upload step with the sample CSV loaded (segment/channel breakdown visible).
2. The `st.status()` progress indicator mid-run.
3. The completed results with an expanded opportunity card showing scores, evidence IDs, and the documentation context section.
4. The "How the agent reached this result" expander with the tool-call timeline.

---

## What I would do before production

1. **Replace keyword search with embeddings.** The current `search_product_docs` splits on spaces and finds the first occurrence of each keyword. A real product would use a vector store (e.g. a local Chroma or Qdrant instance) so queries like "can I automate exports" find the scheduled-export section even if neither word appears verbatim.

2. **Add an evidence-ID validation gate in the UI.** The eval runner checks for hallucinated IDs, but the Streamlit app does not. Before showing any opportunity to a PM, the app should cross-reference every `evidence_feedback_id` against the uploaded CSV and visually flag any that don't exist.

3. **Make the agent non-deterministic output auditable.** Add a `run_fingerprint` (a hash of product_name + feedback_text + model version) to each `RunRecord`. Surface a "compare with previous run" option in the UI that diffs the two `AnalysisResult` objects field-by-field, so a PM can see what changed when they re-run on the same data.

4. **Add a chunking strategy for large batches.** Currently the agent processes all rows in one pass. A real deployment needs to handle 500–5,000 rows. The right approach is to run the agent in parallel on smaller windows and then run a second "synthesis" pass to merge the theme lists — but this makes the output less deterministic and the cost harder to predict. This trade-off needs a deliberate product decision before implementing.

5. **Separate the demo product from the product being analysed.** Right now "Prism Analytics" is both the subject of the sample data and a convenient stand-in for any product. A production tool should have no built-in product assumption — the product name and docs directory are the only configurable inputs.
