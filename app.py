"""
app.py — Streamlit entry point for the Product Feedback Agent.

Styled with the Arco Design System (ByteDance).
Design tokens and CSS live in /design — see design/README.md.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import json
import os
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# load_dotenv() must run before any module that reads env-based prices
load_dotenv()

from agent import AgentRunInfo, run_agent  # noqa: E402
from design.streamlit_css import ARCO_CSS  # noqa: E402
from schemas import AgentInput, AnalysisResult  # noqa: E402
from telemetry import (  # noqa: E402
    RunRecord,
    SessionTelemetry,
    UsageRecord,
    append_run_record,
    calculate_cost,
)
from validation import VALID_CHANNELS, VALID_SEGMENTS, validate_dataframe  # noqa: E402

# ─── Bootstrap ────────────────────────────────────────────────────────────────

# Must be the very first Streamlit call.
st.set_page_config(
    page_title="Product Feedback Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Arco Design System styles immediately after page config.
st.markdown(ARCO_CSS, unsafe_allow_html=True)


# ─── Startup validation ───────────────────────────────────────────────────────

def _missing_env_vars() -> list[str]:
    return [v for v in ["OPENAI_API_KEY"] if not os.getenv(v)]


missing = _missing_env_vars()
if missing:
    st.error(
        f"**Missing environment variable(s): `{'`, `'.join(missing)}`**\n\n"
        "To fix this:\n"
        "1. Copy `.env.example` to `.env` in the project folder.\n"
        "2. Open `.env` and add: `OPENAI_API_KEY=your-key-here`\n"
        "3. Restart the app (`Ctrl+C`, then `streamlit run app.py`)."
    )
    st.stop()


# ─── Session state ────────────────────────────────────────────────────────────

if "telemetry" not in st.session_state:
    st.session_state.telemetry = SessionTelemetry()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _pill(text: str, colour: str) -> str:
    """Render an inline badge with given background colour."""
    return (
        f"<span style='background:{colour}; color:#fff; border-radius:3px; "
        f"padding:2px 8px; font-size:11px; font-weight:600;'>{text}</span>"
    )


def _card(content: str, bg: str = "#F7F8FA", border: str = "#E5E6EB") -> str:
    return (
        f"<div style='background:{bg}; border:1px solid {border}; "
        f"border-radius:6px; padding:14px 16px; margin-bottom:10px;'>"
        f"{content}</div>"
    )


def _section_header(number: str, title: str) -> None:
    st.markdown(
        f"<h2 style='font-size:15px; font-weight:600; color:#1D2129; "
        f"border-bottom:1px solid #E5E6EB; padding-bottom:10px; margin-bottom:16px;'>"
        f"<span style='color:#165DFF; margin-right:8px;'>{number}</span>{title}</h2>",
        unsafe_allow_html=True,
    )


def _handle_agent_error(exc: Exception) -> None:
    """Map exception types to user-facing error messages."""
    name = type(exc).__name__
    msg = str(exc)

    if "AuthenticationError" in name or "authentication" in msg.lower():
        st.error(
            "**API key error** — OpenAI rejected the key in your `.env` file.\n\n"
            "Check that `OPENAI_API_KEY` is correct and has not expired."
        )
    elif "RateLimitError" in name or "rate_limit" in msg.lower():
        st.error(
            "**Rate limit exceeded** — OpenAI is throttling requests.\n\n"
            "Wait a minute and try again, or check your API usage quota."
        )
    elif "APITimeoutError" in name or "timeout" in msg.lower():
        st.error(
            "**Request timed out** — The API did not respond in time.\n\n"
            "The feedback batch may be too large. Try with fewer rows."
        )
    elif "MaxTurnsExceeded" in name:
        st.error(
            "**Agent exceeded turn limit** — The agent used too many steps.\n\n"
            "This can happen with very large or complex feedback batches."
        )
    elif "ValidationError" in name:
        st.error(
            "**Incomplete result** — The agent produced an output that did not match "
            "the expected structure. Try running again; if the problem persists, the "
            "feedback may be ambiguous."
        )
    else:
        st.error(
            f"**Unexpected error ({name})** — {msg[:200]}\n\n"
            "Check the terminal for the full traceback."
        )
        import traceback
        st.code(traceback.format_exc(), language="text")


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<p style='font-size:18px; font-weight:600; color:#1D2129; margin-bottom:4px;'>"
        "🔍 Feedback Agent</p>"
        "<p style='font-size:12px; color:#86909C; margin-top:0; margin-bottom:20px;'>"
        "Powered by OpenAI Agents SDK</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='font-size:11px; font-weight:600; text-transform:uppercase; "
        "letter-spacing:0.6px; color:#86909C; margin-bottom:8px;'>Product</p>",
        unsafe_allow_html=True,
    )

    product_name: str = st.text_input(
        "Product name",
        placeholder="e.g. Prism Analytics",
        label_visibility="collapsed",
    )
    st.caption("Required — used by the agent to frame its analysis.")

    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

    product_description: str = st.text_area(
        "Product description",
        placeholder=(
            "Briefly describe what the product does and who its "
            "main users are. More context → better analysis."
        ),
        height=110,
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        "<p style='font-size:12px; color:#86909C;'>"
        "💡 Drop <code>.md</code> or <code>.txt</code> files into "
        "<code>data/product_docs/</code> to give the agent access to "
        "product documentation.</p>",
        unsafe_allow_html=True,
    )

    # Telemetry footer
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-size:11px; color:#C9CDD4;'>"
        f"{st.session_state.telemetry.session_summary()}</p>",
        unsafe_allow_html=True,
    )


# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='font-size:22px; font-weight:700; color:#1D2129; margin-bottom:2px;'>"
    "Product Feedback Analysis</h1>"
    "<p style='font-size:14px; color:#4E5969; margin-top:0; margin-bottom:24px;'>"
    "Upload customer feedback, surface recurring themes, and discover "
    "evidence-backed product opportunities.</p>",
    unsafe_allow_html=True,
)


# ─── Step 01: Upload & preview ────────────────────────────────────────────────

_section_header("01", "Upload feedback")

uploaded_file = st.file_uploader(
    "Choose a CSV file with customer feedback",
    type=["csv"],
    help=(
        "Required columns: feedback_id, created_at, customer_segment, "
        "channel, feedback."
    ),
    label_visibility="collapsed",
)

df: pd.DataFrame | None = None
feedback_column: str | None = None

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the CSV file: {exc}")
        raw_df = None

    if raw_df is not None:
        validation = validate_dataframe(raw_df)

        for issue in validation.errors:
            row_hint = (
                f" (rows: {issue.rows[:5]}{'…' if len(issue.rows) > 5 else ''})"
                if issue.rows else ""
            )
            st.markdown(
                f"<div style='background:#FFECE8; border-left:3px solid #F53F3F; "
                f"border-radius:6px; padding:12px 16px; margin-bottom:8px;'>"
                f"<p style='margin:0; font-size:13px; font-weight:600; color:#F53F3F;'>"
                f"✕ Validation error — {issue.code}</p>"
                f"<p style='margin:4px 0 0; font-size:13px; color:#4E5969;'>"
                f"{issue.message}{row_hint}</p></div>",
                unsafe_allow_html=True,
            )

        for issue in validation.warnings:
            st.markdown(
                f"<div style='background:#FFF7E8; border-left:3px solid #FF7D00; "
                f"border-radius:6px; padding:10px 16px; margin-bottom:8px;'>"
                f"<p style='margin:0; font-size:13px; color:#FF7D00; font-weight:500;'>"
                f"⚠ {issue.message}</p></div>",
                unsafe_allow_html=True,
            )

        if validation.is_valid:
            df = validation.cleaned_df
            stats = validation.stats

            # ── Summary ──────────────────────────────────────────────────────
            st.markdown(
                f"<div style='display:inline-flex; align-items:center; gap:8px; "
                f"background:#E8FFEA; border-radius:4px; padding:6px 12px; "
                f"margin-bottom:16px;'>"
                f"<span style='color:#00B42A; font-size:14px;'>✓</span>"
                f"<span style='color:#00B42A; font-size:13px; font-weight:500;'>"
                f"Loaded {stats['total_rows']:,} rows "
                f"({stats['non_empty_rows']:,} with feedback text)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            col_seg, col_chan = st.columns(2)
            with col_seg:
                st.caption("By segment")
                for seg, count in sorted(stats["segments"].items()):
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; "
                        f"font-size:13px; color:#4E5969; padding:2px 0;'>"
                        f"<span>{seg}</span>"
                        f"<span style='color:#1D2129; font-weight:500;'>{count}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            with col_chan:
                st.caption("By channel")
                for chan, count in sorted(stats["channels"].items()):
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; "
                        f"font-size:13px; color:#4E5969; padding:2px 0;'>"
                        f"<span>{chan}</span>"
                        f"<span style='color:#1D2129; font-weight:500;'>{count}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            feedback_column = "feedback"

            with st.expander("Preview — first 5 rows"):
                st.dataframe(df.head(5), use_container_width=True, hide_index=True)


# ─── Step 02: Analyse ────────────────────────────────────────────────────────

st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
_section_header("02", "Run analysis")

can_run = bool(df is not None and feedback_column and product_name)

if df is not None and not product_name:
    st.markdown(
        "<p style='font-size:13px; color:#FF7D00;'>"
        "⬅ Enter a <strong>product name</strong> in the sidebar to enable analysis."
        "</p>",
        unsafe_allow_html=True,
    )

run_clicked = st.button(
    "🚀  Analyse feedback",
    disabled=not can_run,
    type="primary",
    use_container_width=False,
)


# ─── Analysis execution ───────────────────────────────────────────────────────

if run_clicked and can_run:
    assert df is not None and feedback_column is not None

    # Build feedback text with IDs and context
    non_empty = df[
        df[feedback_column].notna()
        & (df[feedback_column].astype(str).str.strip() != "")
    ]
    feedback_lines = [
        f"[{row['feedback_id']}] ({row['customer_segment']}, {row['channel']}) {row[feedback_column]}"
        for _, row in non_empty.iterrows()
    ]
    feedback_text = "\n".join(feedback_lines)
    feedback_count = len(feedback_lines)

    agent_input = AgentInput(
        product_name=product_name,
        product_description=product_description,
        feedback_text=feedback_text,
    )

    # Generate run metadata before the call
    run_id = RunRecord.new_id()
    timestamp = RunRecord.now_iso()
    t_start = time.monotonic()

    result: AnalysisResult | None = None
    run_info: AgentRunInfo | None = None
    success = False
    error_type: str | None = None

    with st.status(
        "Agent is working… this usually takes 30–60 seconds.",
        expanded=True,
    ) as run_status:
        run_status.write(
            f"Preparing {feedback_count} feedback rows for "
            f"**{product_name}**…"
        )
        try:
            run_status.write(
                "🤖 Agent is reading feedback, querying documentation, "
                "and building opportunities…"
            )
            result, run_info = run_agent(agent_input)
            success = True
        except Exception as exc:
            error_type = type(exc).__name__
            duration = round(time.monotonic() - t_start, 2)
            run_status.update(
                label=f"Analysis failed after {duration}s",
                state="error",
                expanded=True,
            )
            _handle_agent_error(exc)
        else:
            duration = round(time.monotonic() - t_start, 2)
            run_status.update(
                label=f"Analysis complete in {duration:.1f}s",
                state="complete",
                expanded=False,
            )

    duration = round(time.monotonic() - t_start, 2)

    # ── Build and persist RunRecord ───────────────────────────────────────────
    if run_info is not None:
        estimated_cost = calculate_cost(run_info.input_tokens, run_info.output_tokens)
        opp_count = len(result.opportunities) if result else 0

        record = RunRecord(
            run_id=run_id,
            timestamp=timestamp,
            feedback_count=feedback_count,
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            duration_seconds=duration,
            model_requests=run_info.model_requests,
            input_tokens=run_info.input_tokens,
            output_tokens=run_info.output_tokens,
            total_tokens=run_info.total_tokens,
            estimated_cost=estimated_cost,
            tools_called=run_info.tools_called,
            opportunity_count=opp_count,
            success=success,
            error_type=error_type,
        )
        append_run_record(record)

        # Update sidebar session telemetry
        usage_record = UsageRecord(
            input_tokens=run_info.input_tokens,
            output_tokens=run_info.output_tokens,
            run_label=f"Analysis — {product_name}",
        )
        st.session_state.telemetry.add(usage_record)

    # ── Stop here if the run failed ───────────────────────────────────────────
    if not success or result is None:
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    _section_header("03", "Results")

    # ── Run metrics strip ─────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Duration", f"{duration:.1f}s")
    with m2:
        st.metric("Total tokens", f"{run_info.total_tokens:,}")
    with m3:
        st.metric("Estimated cost", f"${estimated_cost:.4f}")
    with m4:
        cpo = record.cost_per_opportunity()
        cpo_label = f"${cpo:.4f}" if cpo is not None else "—"
        st.metric(
            "Cost / opportunity",
            cpo_label,
            help=(
                "Total cost divided by the number of opportunities generated. "
                "This is cost per generated opportunity (quantity), not cost per "
                "accepted or valid opportunity (quality). A run that generates two "
                "low-quality opportunities has the same denominator as one that "
                "generates two high-quality ones."
            ),
        )

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # ── Executive summary ─────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='font-size:14px; font-weight:600; color:#1D2129; margin:20px 0 8px;'>"
        "Executive Summary</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='background:#F0F5FF; border-left:3px solid #165DFF; "
        f"border-radius:6px; padding:14px 18px; margin-bottom:20px;'>"
        f"<p style='margin:0; font-size:14px; color:#1D2129; line-height:1.7;'>"
        f"{result.executive_summary}</p></div>",
        unsafe_allow_html=True,
    )

    # ── Themes ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='font-size:14px; font-weight:600; color:#1D2129; margin:0 0 8px;'>"
        f"Themes ({len(result.themes)} identified)</h3>",
        unsafe_allow_html=True,
    )
    for theme in result.themes:
        with st.expander(f"**{theme.title}** — {theme.frequency} mention(s)"):
            st.markdown(
                f"<p style='font-size:13px; color:#4E5969; margin-bottom:10px;'>"
                f"{theme.description}</p>",
                unsafe_allow_html=True,
            )
            if theme.evidence:
                st.markdown(
                    "<p style='font-size:11px; font-weight:600; color:#86909C; "
                    "text-transform:uppercase; letter-spacing:0.5px;'>Evidence</p>",
                    unsafe_allow_html=True,
                )
                for eq in theme.evidence:
                    fid_badge = (
                        f" <span style='color:#86909C; font-size:11px;'>[{eq.feedback_id}]</span>"
                        if eq.feedback_id else ""
                    )
                    st.markdown(
                        f"<blockquote style='border-left:3px solid #E5E6EB; "
                        f"padding:6px 12px; margin:4px 0; font-size:13px; "
                        f"color:#4E5969;'>&ldquo;{eq.quote}&rdquo;{fid_badge}"
                        f"</blockquote>",
                        unsafe_allow_html=True,
                    )

    # ── Opportunities table ───────────────────────────────────────────────────
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='font-size:14px; font-weight:600; color:#1D2129; margin:0 0 8px;'>"
        f"Opportunities ({len(result.opportunities)} identified)</h3>",
        unsafe_allow_html=True,
    )

    _priority_colour = {5: "#F53F3F", 4: "#FF7D00", 3: "#165DFF", 2: "#00B42A", 1: "#86909C"}

    for opp in result.opportunities:
        colour = _priority_colour.get(opp.priority, "#165DFF")
        with st.expander(
            f"**{opp.title}** — Priority {opp.priority}/5 · {opp.category}"
        ):
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(
                    f"<p style='font-size:13px; font-weight:600; color:#1D2129; "
                    f"margin-bottom:4px;'>Problem</p>"
                    f"<p style='font-size:13px; color:#4E5969; margin-bottom:12px;'>"
                    f"{opp.problem_statement}</p>"
                    f"<p style='font-size:13px; font-weight:600; color:#1D2129; "
                    f"margin-bottom:4px;'>Rationale</p>"
                    f"<p style='font-size:13px; color:#4E5969; margin-bottom:12px;'>"
                    f"{opp.rationale}</p>"
                    f"<p style='font-size:13px; font-weight:600; color:#1D2129; "
                    f"margin-bottom:4px;'>Recommendation</p>"
                    f"<p style='font-size:13px; color:#4E5969; margin-bottom:12px;'>"
                    f"{opp.recommendation}</p>",
                    unsafe_allow_html=True,
                )
                if opp.documentation_sources:
                    st.markdown(
                        "<p style='font-size:11px; font-weight:600; color:#86909C; "
                        "text-transform:uppercase; letter-spacing:0.5px; "
                        "margin-bottom:4px;'>Documentation context</p>",
                        unsafe_allow_html=True,
                    )
                    for src in opp.documentation_sources:
                        st.markdown(
                            f"<p style='font-size:12px; color:#86909C; margin:2px 0;'>"
                            f"📄 {src}</p>",
                            unsafe_allow_html=True,
                        )
            with col_r:
                seg_html = "".join(
                    f"<p style='font-size:12px; color:#4E5969; margin:2px 0;'>{s}</p>"
                    for s in opp.affected_segments
                )
                ids_html = ", ".join(opp.evidence_feedback_ids)
                st.markdown(
                    f"<div style='background:#F7F8FA; border-radius:6px; padding:12px;'>"
                    f"<p style='font-size:11px; font-weight:600; color:#86909C; "
                    f"text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;'>"
                    f"Scores</p>"
                    f"<div style='display:flex; justify-content:space-between; "
                    f"font-size:13px; color:#4E5969; padding:3px 0;'><span>Priority</span>"
                    f"<span style='color:{colour}; font-weight:600;'>"
                    f"{opp.priority}/5</span></div>"
                    f"<div style='display:flex; justify-content:space-between; "
                    f"font-size:13px; color:#4E5969; padding:3px 0;'><span>Impact</span>"
                    f"<span style='font-weight:600;'>{opp.impact_score}/5</span></div>"
                    f"<div style='display:flex; justify-content:space-between; "
                    f"font-size:13px; color:#4E5969; padding:3px 0;'>"
                    f"<span>Confidence</span>"
                    f"<span style='font-weight:600;'>{opp.confidence_score}/5</span>"
                    f"</div>"
                    f"<hr style='border:none; border-top:1px solid #E5E6EB; margin:8px 0;'>"
                    f"<p style='font-size:11px; font-weight:600; color:#86909C; "
                    f"text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;'>"
                    f"Segments</p>{seg_html}"
                    f"<hr style='border:none; border-top:1px solid #E5E6EB; margin:8px 0;'>"
                    f"<p style='font-size:11px; font-weight:600; color:#86909C; "
                    f"text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;'>"
                    f"Evidence IDs</p>"
                    f"<p style='font-size:12px; color:#4E5969; word-break:break-all;'>"
                    f"{ids_html}</p></div>",
                    unsafe_allow_html=True,
                )

    # ── Download opportunities JSON ───────────────────────────────────────────
    opp_json = json.dumps(
        [o.model_dump() for o in result.opportunities], indent=2, ensure_ascii=False
    )
    st.download_button(
        label="⬇ Download opportunities as JSON",
        data=opp_json.encode("utf-8"),
        file_name=f"opportunities_{run_id[:8]}.json",
        mime="application/json",
    )

    # ── Positive signals & ambiguous feedback ─────────────────────────────────
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    col_pos, col_amb = st.columns(2)

    with col_pos:
        st.markdown(
            "<h3 style='font-size:14px; font-weight:600; color:#1D2129; "
            "margin-bottom:8px;'>✓ Positive signals</h3>",
            unsafe_allow_html=True,
        )
        for signal in result.positive_signals:
            st.markdown(
                f"<div style='background:#E8FFEA; border-radius:4px; "
                f"padding:8px 12px; margin-bottom:6px; font-size:13px; "
                f"color:#1D2129;'>{signal}</div>",
                unsafe_allow_html=True,
            )
        if not result.positive_signals:
            st.caption("None identified.")

    with col_amb:
        st.markdown(
            "<h3 style='font-size:14px; font-weight:600; color:#1D2129; "
            "margin-bottom:8px;'>? Ambiguous feedback</h3>",
            unsafe_allow_html=True,
        )
        for item in result.ambiguous_feedback:
            st.markdown(
                f"<div style='background:#FFF7E8; border-radius:4px; "
                f"padding:8px 12px; margin-bottom:6px; font-size:13px; "
                f"color:#1D2129;'>{item}</div>",
                unsafe_allow_html=True,
            )
        if not result.ambiguous_feedback:
            st.caption("None identified.")

    # ── Limitations ───────────────────────────────────────────────────────────
    if result.limitations:
        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        st.markdown(
            "<h3 style='font-size:14px; font-weight:600; color:#1D2129; "
            "margin-bottom:8px;'>⚠ Analysis limitations</h3>",
            unsafe_allow_html=True,
        )
        for lim in result.limitations:
            st.markdown(
                f"<div style='background:#F7F8FA; border-left:3px solid #C9CDD4; "
                f"border-radius:4px; padding:8px 12px; margin-bottom:6px; "
                f"font-size:13px; color:#4E5969;'>{lim}</div>",
                unsafe_allow_html=True,
            )

    # ── How the agent reached this result ─────────────────────────────────────
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    with st.expander("🔍 How the agent reached this result"):
        st.markdown(
            "<p style='font-size:12px; color:#86909C; margin-bottom:12px;'>"
            "This panel shows the agent's observable actions — tool calls made "
            "and their inputs/outputs — as reported by the OpenAI Agents SDK. "
            "Internal LLM reasoning is not exposed here.</p>",
            unsafe_allow_html=True,
        )

        # Model requests and token breakdown
        st.markdown(
            f"<p style='font-size:13px; color:#4E5969; margin-bottom:12px;'>"
            f"<strong>{run_info.model_requests}</strong> model request(s) — "
            f"{run_info.input_tokens:,} input tokens, "
            f"{run_info.output_tokens:,} output tokens.</p>",
            unsafe_allow_html=True,
        )

        # Tool call timeline
        if run_info.tool_call_details:
            st.markdown(
                "<p style='font-size:12px; font-weight:600; color:#1D2129; "
                "text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;'>"
                "Tool call timeline</p>",
                unsafe_allow_html=True,
            )
            for i, tc in enumerate(run_info.tool_call_details, 1):
                status_icon = "✓" if tc.success else "✕"
                status_colour = "#00B42A" if tc.success else "#F53F3F"
                st.markdown(
                    f"<div style='font-size:13px; color:#4E5969; "
                    f"padding:6px 0; border-bottom:1px solid #F2F3F5;'>"
                    f"<span style='color:#86909C; margin-right:8px;'>#{i}</span>"
                    f"<strong style='color:#165DFF;'>{tc.tool}</strong>"
                    f"<span style='color:#86909C; margin:0 8px;'>→</span>"
                    f"<span style='font-family:monospace;'>{tc.input_summary}</span>"
                    f"<span style='color:{status_colour}; margin-left:8px;'>"
                    f"{status_icon}</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No tool calls recorded.")

        # Documentation queries
        if run_info.doc_queries:
            st.markdown(
                "<p style='font-size:12px; font-weight:600; color:#1D2129; "
                "text-transform:uppercase; letter-spacing:0.5px; "
                "margin:16px 0 8px;'>Documentation queries</p>",
                unsafe_allow_html=True,
            )
            for q in run_info.doc_queries:
                st.markdown(
                    f"<p style='font-size:13px; color:#4E5969; "
                    f"margin:3px 0;'>🔎 {q}</p>",
                    unsafe_allow_html=True,
                )

        # Sources consulted
        if run_info.doc_sources:
            st.markdown(
                "<p style='font-size:12px; font-weight:600; color:#1D2129; "
                "text-transform:uppercase; letter-spacing:0.5px; "
                "margin:16px 0 8px;'>Sources consulted</p>",
                unsafe_allow_html=True,
            )
            for src in run_info.doc_sources:
                st.markdown(
                    f"<p style='font-size:13px; color:#4E5969; "
                    f"margin:3px 0;'>📄 {src}</p>",
                    unsafe_allow_html=True,
                )

        # Validation errors / retries
        if run_info.validation_errors:
            st.markdown(
                "<p style='font-size:12px; font-weight:600; color:#FF7D00; "
                "text-transform:uppercase; letter-spacing:0.5px; "
                "margin:16px 0 8px;'>Validation errors (self-corrected)</p>",
                unsafe_allow_html=True,
            )
            for err in run_info.validation_errors:
                st.markdown(
                    f"<div style='background:#FFF7E8; border-left:3px solid #FF7D00; "
                    f"border-radius:4px; padding:8px 12px; margin-bottom:6px; "
                    f"font-size:12px; color:#4E5969;'>{err}</div>",
                    unsafe_allow_html=True,
                )

        # Raw JSON result (collapsed)
        with st.expander("Raw JSON output"):
            st.json(result.model_dump(), expanded=False)
