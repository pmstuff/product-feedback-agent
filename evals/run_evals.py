#!/usr/bin/env python3
"""
evals/run_evals.py — Evaluation runner for the Product Feedback Agent.

Usage
-----
  # Static checks only (no API calls):
  python evals/run_evals.py

  # Live agent calls (asks for confirmation + cost estimate first):
  python evals/run_evals.py --run-live

  # Run a single case (still asks confirmation if --run-live):
  python evals/run_evals.py --run-live --case case-08

Output
------
  Console: per-case result table + aggregate metrics.
  evals/results_<timestamp>.json: full per-case record (only written on live runs).

Design notes
------------
- Deterministic checks are pure Python — no LLM judge, no second API call.
- Semantic checks are flagged as NEEDS_HUMAN_REVIEW; the runner records them
  but does not fail the case on them.
- The --run-live flag is required for any check that calls the agent. Without
  it the runner validates the cases.json file and the feedback formatting only.
- Do NOT optimise prompts before reviewing the baseline results this file reports.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

EVALS_DIR = Path(__file__).parent
PROJECT_ROOT = EVALS_DIR.parent
CASES_FILE = EVALS_DIR / "cases.json"
RESULTS_DIR = EVALS_DIR

# Make the project root importable when this script is run directly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ─── Check result dataclasses ─────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    case_type: str
    status: str                    # "PASS" | "FAIL" | "STATIC_ONLY" | "ERROR"
    checks: list[CheckResult] = field(default_factory=list)
    semantic_notes: list[str] = field(default_factory=list)
    error: Optional[str] = None
    # Populated only on live runs:
    duration_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    opportunity_count: Optional[int] = None
    tools_called: Optional[list[str]] = None

    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def passed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.passed]


# ─── Cases loading ────────────────────────────────────────────────────────────

def load_cases() -> dict[str, Any]:
    """Load and minimally validate cases.json."""
    if not CASES_FILE.exists():
        raise FileNotFoundError(f"Cases file not found: {CASES_FILE}")
    with CASES_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data.get("cases"), list), "cases.json must have a 'cases' array"
    assert isinstance(data.get("product_context"), dict), "cases.json must have 'product_context'"
    return data


# ─── Feedback text builder ────────────────────────────────────────────────────

def build_feedback_text(case: dict[str, Any]) -> str:
    """
    Format feedback rows as  [EVAL-NNN] (Segment, Channel) feedback text
    — the same format app.py uses for FB-NNN rows.
    """
    lines: list[str] = []
    for row in case["feedback_rows"]:
        fid = row["feedback_id"]
        seg = row.get("customer_segment", "Unknown")
        chan = row.get("channel", "Unknown")
        text = row["feedback"]
        lines.append(f"[{fid}] ({seg}, {chan}) {text}")
    return "\n".join(lines)


# ─── Static checks (no API) ───────────────────────────────────────────────────

def static_checks_on_cases_file(cases: list[dict]) -> list[CheckResult]:
    """
    Checks that run purely on cases.json — no agent call needed.

    Returns a flat list of CheckResults. These are global (not per-case).
    """
    results: list[CheckResult] = []

    # 1. Unique case IDs
    ids = [c["id"] for c in cases]
    dupes = [i for i in set(ids) if ids.count(i) > 1]
    results.append(CheckResult(
        name="unique_case_ids",
        passed=len(dupes) == 0,
        detail=f"Duplicate IDs: {dupes}" if dupes else "All case IDs are unique.",
    ))

    # 2. All feedback IDs use EVAL-NNN format (not FB-NNN, to avoid collision)
    import re
    bad_ids: list[str] = []
    for case in cases:
        for row in case["feedback_rows"]:
            fid = row["feedback_id"]
            if not re.match(r"^EVAL-\d+$", fid):
                bad_ids.append(f"{case['id']}: {fid}")
    results.append(CheckResult(
        name="feedback_id_format",
        passed=len(bad_ids) == 0,
        detail=(
            f"Non-EVAL-NNN IDs found: {bad_ids}" if bad_ids
            else "All feedback IDs use EVAL-NNN format."
        ),
    ))

    # 3. permitted_feedback_ids covers all feedback_row IDs in each case
    mismatch: list[str] = []
    for case in cases:
        exp = case.get("expectations", {})
        permitted = set(exp.get("permitted_feedback_ids") or [])
        row_ids = {row["feedback_id"] for row in case["feedback_rows"]}
        if permitted and row_ids - permitted:
            extra = row_ids - permitted
            mismatch.append(f"{case['id']}: row IDs {extra} not in permitted_feedback_ids")
    results.append(CheckResult(
        name="permitted_ids_cover_rows",
        passed=len(mismatch) == 0,
        detail=(
            "Permitted ID list covers all row IDs in each case."
            if not mismatch else " | ".join(mismatch)
        ),
    ))

    # 4. should_group_ids references only IDs that exist in the case
    bad_group: list[str] = []
    for case in cases:
        exp = case.get("expectations", {})
        group_ids = exp.get("should_group_ids") or []
        row_ids = {row["feedback_id"] for row in case["feedback_rows"]}
        for gid in group_ids:
            if gid not in row_ids:
                bad_group.append(f"{case['id']}: {gid} not in feedback_rows")
    results.append(CheckResult(
        name="should_group_ids_valid",
        passed=len(bad_group) == 0,
        detail=(
            "should_group_ids are all valid row IDs."
            if not bad_group else " | ".join(bad_group)
        ),
    ))

    # 5. score ranges — min <= max where both are non-null
    score_errors: list[str] = []
    for case in cases:
        exp = case.get("expectations", {})
        mn = exp.get("min_opportunity_count")
        mx = exp.get("max_opportunity_count")
        if mn is not None and mx is not None and mn > mx:
            score_errors.append(
                f"{case['id']}: min_opportunity_count ({mn}) > max_opportunity_count ({mx})"
            )
    results.append(CheckResult(
        name="opportunity_count_range_valid",
        passed=len(score_errors) == 0,
        detail=(
            "Opportunity count ranges are valid."
            if not score_errors else " | ".join(score_errors)
        ),
    ))

    # 6. Every case has at least one feedback row
    empty: list[str] = []
    for case in cases:
        if not case.get("feedback_rows"):
            empty.append(case["id"])
    results.append(CheckResult(
        name="cases_have_feedback_rows",
        passed=len(empty) == 0,
        detail=(
            "All cases have at least one feedback row."
            if not empty else f"Cases with no rows: {empty}"
        ),
    ))

    # 7. Required top-level keys present in each case
    required_keys = {"id", "description", "type", "feedback_rows", "expectations"}
    missing_keys: list[str] = []
    for case in cases:
        missing = required_keys - set(case.keys())
        if missing:
            missing_keys.append(f"{case.get('id', '?')}: missing {missing}")
    results.append(CheckResult(
        name="case_schema_complete",
        passed=len(missing_keys) == 0,
        detail=(
            "All cases have required top-level keys."
            if not missing_keys else " | ".join(missing_keys)
        ),
    ))

    return results


# ─── Deterministic checks on a single AnalysisResult ─────────────────────────

def deterministic_checks(
    case: dict[str, Any],
    result,           # AnalysisResult
    run_info,         # AgentRunInfo
) -> tuple[list[CheckResult], list[str]]:
    """
    Apply all deterministic checks from the case's expectations to the
    AnalysisResult. Returns (checks, semantic_notes).

    semantic_notes are not checked programmatically — they are passed through
    for the human reviewer.
    """
    exp = case["expectations"]
    checks: list[CheckResult] = []
    semantic_notes: list[str] = []

    permitted: set[str] = set(exp.get("permitted_feedback_ids") or [])

    # ── 1. Opportunity count ──────────────────────────────────────────────────
    opp_count = len(result.opportunities)
    should_create = exp.get("should_create_opportunity")
    if should_create is True:
        checks.append(CheckResult(
            name="should_create_opportunity",
            passed=opp_count >= 1,
            detail=f"Expected >= 1 opportunity, got {opp_count}.",
        ))
    elif should_create is False:
        checks.append(CheckResult(
            name="should_not_create_opportunity",
            passed=opp_count == 0,
            detail=f"Expected 0 opportunities, got {opp_count}.",
        ))

    min_opp = exp.get("min_opportunity_count")
    max_opp = exp.get("max_opportunity_count")
    if min_opp is not None:
        checks.append(CheckResult(
            name="min_opportunity_count",
            passed=opp_count >= min_opp,
            detail=f"Expected >= {min_opp} opportunities, got {opp_count}.",
        ))
    if max_opp is not None:
        checks.append(CheckResult(
            name="max_opportunity_count",
            passed=opp_count <= max_opp,
            detail=f"Expected <= {max_opp} opportunities, got {opp_count}.",
        ))

    # ── 2. Positive signals ───────────────────────────────────────────────────
    min_pos = exp.get("min_positive_signals")
    if min_pos is not None:
        pos_count = len(result.positive_signals)
        checks.append(CheckResult(
            name="min_positive_signals",
            passed=pos_count >= min_pos,
            detail=f"Expected >= {min_pos} positive_signals, got {pos_count}.",
        ))

    # ── 3. Feedback ID accuracy (no hallucinated IDs) ─────────────────────────
    if permitted:
        hallucinated: list[str] = []
        for opp in result.opportunities:
            for fid in opp.evidence_feedback_ids:
                if fid not in permitted:
                    hallucinated.append(f"{opp.title!r}: cited {fid!r}")
        checks.append(CheckResult(
            name="no_hallucinated_feedback_ids",
            passed=len(hallucinated) == 0,
            detail=(
                "All evidence_feedback_ids are in the permitted set."
                if not hallucinated
                else f"Hallucinated IDs: {'; '.join(hallucinated)}"
            ),
        ))

    # ── 4. Evidence present in every opportunity ──────────────────────────────
    no_evidence: list[str] = []
    for opp in result.opportunities:
        if not opp.evidence_feedback_ids:
            no_evidence.append(opp.title)
    checks.append(CheckResult(
        name="opportunities_have_evidence",
        passed=len(no_evidence) == 0,
        detail=(
            "All opportunities cite at least one feedback ID."
            if not no_evidence
            else f"Opportunities with no evidence: {no_evidence}"
        ),
    ))

    # ── 5. Forbidden terms ────────────────────────────────────────────────────
    forbidden: list[str] = exp.get("forbidden_terms") or []
    if forbidden:
        # Serialise the full result to plaintext for a case-insensitive scan
        result_text = json.dumps(
            result.model_dump(), ensure_ascii=False
        ).lower()
        found_forbidden = [t for t in forbidden if t.lower() in result_text]
        checks.append(CheckResult(
            name="no_forbidden_terms",
            passed=len(found_forbidden) == 0,
            detail=(
                "No forbidden terms found in output."
                if not found_forbidden
                else f"Forbidden terms present: {found_forbidden}"
            ),
        ))

    # ── 6. max_confidence_if_opportunity ──────────────────────────────────────
    max_conf = exp.get("max_confidence_if_opportunity")
    if max_conf is not None and result.opportunities:
        high_conf = [
            f"{opp.title!r} (confidence={opp.confidence_score})"
            for opp in result.opportunities
            if opp.confidence_score > max_conf
        ]
        checks.append(CheckResult(
            name="max_confidence_respected",
            passed=len(high_conf) == 0,
            detail=(
                f"All opportunities have confidence_score <= {max_conf}."
                if not high_conf
                else f"Opportunities exceeding max confidence {max_conf}: {high_conf}"
            ),
        ))

    # ── 7. min_theme_frequency ────────────────────────────────────────────────
    min_freq = exp.get("min_theme_frequency")
    if min_freq is not None:
        max_theme_freq = max((t.frequency for t in result.themes), default=0)
        checks.append(CheckResult(
            name="min_theme_frequency",
            passed=max_theme_freq >= min_freq,
            detail=(
                f"At least one theme has frequency >= {min_freq} "
                f"(max seen: {max_theme_freq})."
            ),
        ))

    # ── 8. Expected tools called ──────────────────────────────────────────────
    expected_tools: list[str] = exp.get("expected_tools") or []
    if expected_tools:
        called_set = set(run_info.tools_called)
        missing_tools = [t for t in expected_tools if t not in called_set]
        checks.append(CheckResult(
            name="expected_tools_called",
            passed=len(missing_tools) == 0,
            detail=(
                f"All expected tools were called: {expected_tools}."
                if not missing_tools
                else f"Expected tools not called: {missing_tools} (called: {list(called_set)})"
            ),
        ))

    # ── 9. should_group_ids — all appear in at least one common theme ─────────
    group_ids: list[str] = exp.get("should_group_ids") or []
    if group_ids:
        group_set = set(group_ids)
        # Collect theme → set of cited IDs (from evidence in themes' evidence quotes)
        # Note: Theme has evidence: list[EvidenceQuote] each with feedback_id
        found_in_common: bool = False
        for theme in result.themes:
            theme_ids = {
                eq.feedback_id
                for eq in theme.evidence
                if eq.feedback_id is not None
            }
            if group_set.issubset(theme_ids):
                found_in_common = True
                break
        checks.append(CheckResult(
            name="should_group_ids_in_one_theme",
            passed=found_in_common,
            detail=(
                f"All group IDs {group_ids} appear together in at least one theme."
                if found_in_common
                else f"Group IDs {group_ids} are not all present in any single theme."
            ),
        ))

    # ── 10. expected_category matches at least one opportunity ────────────────
    expected_cat = exp.get("expected_category")
    if expected_cat and result.opportunities:
        cats = [opp.category for opp in result.opportunities]
        # Case-insensitive substring match
        cat_match = any(
            expected_cat.lower() in c.lower() or c.lower() in expected_cat.lower()
            for c in cats
        )
        checks.append(CheckResult(
            name="expected_category_present",
            passed=cat_match,
            detail=(
                f"At least one opportunity has category matching '{expected_cat}'."
                if cat_match
                else f"No opportunity matched category '{expected_cat}'. Found: {cats}"
            ),
        ))

    # ── 11. Schema compliance — total_feedback_rows matches input ─────────────
    expected_row_count = len(case["feedback_rows"])
    checks.append(CheckResult(
        name="total_feedback_rows_correct",
        passed=result.total_feedback_rows == expected_row_count,
        detail=(
            f"total_feedback_rows={result.total_feedback_rows} matches "
            f"input row count {expected_row_count}."
            if result.total_feedback_rows == expected_row_count
            else f"total_feedback_rows={result.total_feedback_rows}, "
                 f"expected {expected_row_count}."
        ),
    ))

    # ── Semantic notes (for human review) ─────────────────────────────────────
    human_notes = exp.get("human_review_notes", "")
    if human_notes:
        semantic_notes.append(human_notes)

    return checks, semantic_notes


# ─── Cost estimation ──────────────────────────────────────────────────────────

def estimate_live_cost(cases: list[dict]) -> tuple[int, float]:
    """
    Rough cost estimate for a live eval run.

    Assumes ~2,000 input tokens and ~800 output tokens per case (conservative
    estimates for small single-case runs with a few tool calls).
    """
    INPUT_TOKENS_PER_CASE = 2_000
    OUTPUT_TOKENS_PER_CASE = 800
    INPUT_PRICE_PER_M = float(os.environ.get("MODEL_INPUT_PRICE_PER_MILLION", "5.00"))
    OUTPUT_PRICE_PER_M = float(os.environ.get("MODEL_OUTPUT_PRICE_PER_MILLION", "15.00"))

    total_cases = len(cases)
    total_input = total_cases * INPUT_TOKENS_PER_CASE
    total_output = total_cases * OUTPUT_TOKENS_PER_CASE
    cost = (total_input * INPUT_PRICE_PER_M + total_output * OUTPUT_PRICE_PER_M) / 1_000_000
    return total_cases, cost


# ─── Aggregate metrics ────────────────────────────────────────────────────────

def compute_aggregate_metrics(case_results: list[CaseResult]) -> dict[str, Any]:
    live = [r for r in case_results if r.status in ("PASS", "FAIL")]
    static_only = [r for r in case_results if r.status == "STATIC_ONLY"]
    errors = [r for r in case_results if r.status == "ERROR"]

    total = len(case_results)
    valid = len([r for r in live if r.status == "PASS"])

    metrics: dict[str, Any] = {
        "total_cases": total,
        "live_runs": len(live),
        "static_only": len(static_only),
        "errors": len(errors),
        "pass_rate": round(valid / len(live), 3) if live else None,
    }

    # Per-check category metrics across live runs
    all_checks = [c for r in live for c in r.checks]
    check_categories = {
        "feedback_id_accuracy": "no_hallucinated_feedback_ids",
        "evidence_coverage":    "opportunities_have_evidence",
        "injection_resistance": "no_forbidden_terms",
        "tool_usage_accuracy":  "expected_tools_called",
        "grouping_accuracy":    "should_group_ids_in_one_theme",
        "confidence_calibration": "max_confidence_respected",
    }
    for label, check_name in check_categories.items():
        relevant = [c for c in all_checks if c.name == check_name]
        if relevant:
            passed = sum(1 for c in relevant if c.passed)
            metrics[label] = round(passed / len(relevant), 3)
        else:
            metrics[label] = None

    # Token and cost metrics
    if live:
        tokens = [r.input_tokens + r.output_tokens for r in live if r.input_tokens is not None]
        costs = [r.estimated_cost for r in live if r.estimated_cost is not None]
        durations = [r.duration_seconds for r in live if r.duration_seconds is not None]
        metrics["avg_total_tokens"] = round(sum(tokens) / len(tokens)) if tokens else None
        metrics["avg_cost_usd"] = round(sum(costs) / len(costs), 6) if costs else None
        metrics["avg_duration_seconds"] = round(sum(durations) / len(durations), 2) if durations else None
        metrics["total_cost_usd"] = round(sum(costs), 6) if costs else None

    return metrics


# ─── Console printing ─────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def _c(text: str, colour: str) -> str:
    """Wrap text in an ANSI colour if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{colour}{text}{RESET}"
    return text


def print_static_results(static_checks: list[CheckResult]) -> None:
    print(f"\n{_c('── Static checks (cases.json validation) ──', BOLD)}")
    for chk in static_checks:
        icon = _c("✓", GREEN) if chk.passed else _c("✗", RED)
        print(f"  {icon}  {chk.name}: {chk.detail}")
    passed = sum(1 for c in static_checks if c.passed)
    total = len(static_checks)
    colour = GREEN if passed == total else RED
    print(f"\n  {_c(f'{passed}/{total} static checks passed.', colour)}\n")


def print_case_result(cr: CaseResult) -> None:
    if cr.status == "STATIC_ONLY":
        print(f"  [{_c('SKIP', YELLOW)}] {cr.case_id} ({cr.case_type}) — static only, no live run")
        return
    if cr.status == "ERROR":
        print(f"  [{_c('ERR ', RED)}] {cr.case_id} ({cr.case_type}) — {cr.error}")
        return

    colour = GREEN if cr.status == "PASS" else RED
    icon = _c(cr.status, colour)
    token_info = ""
    if cr.input_tokens is not None:
        token_info = (
            f"  tokens={cr.input_tokens + cr.output_tokens}  "
            f"cost=${cr.estimated_cost:.5f}  "
            f"time={cr.duration_seconds:.1f}s"
        )
    print(f"  [{icon}] {cr.case_id} ({cr.case_type}){token_info}")

    for chk in cr.failed_checks():
        print(f"         {_c('✗', RED)} {chk.name}: {chk.detail}")
    if cr.semantic_notes:
        for note in cr.semantic_notes:
            print(f"         {_c('↻', YELLOW)} HUMAN REVIEW: {note}")


def print_aggregate(metrics: dict[str, Any]) -> None:
    print(f"\n{_c('── Aggregate metrics ──', BOLD)}")
    for k, v in metrics.items():
        if v is None:
            continue
        if isinstance(v, float) and "rate" in k or "accuracy" in k or "resistance" in k:
            print(f"  {k}: {v:.1%}")
        else:
            print(f"  {k}: {v}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluation runner for the Product Feedback Agent."
    )
    parser.add_argument(
        "--run-live",
        action="store_true",
        help="Call the real agent (incurs API cost). Will ask for confirmation first.",
    )
    parser.add_argument(
        "--case",
        metavar="CASE_ID",
        help="Run a single case by ID (e.g. case-08). Only relevant with --run-live.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt (useful in CI).",
    )
    args = parser.parse_args()

    # ── 1. Load cases ─────────────────────────────────────────────────────────
    try:
        data = load_cases()
    except (FileNotFoundError, AssertionError) as exc:
        print(f"{_c('ERROR', RED)}: {exc}")
        sys.exit(1)

    cases: list[dict] = data["cases"]
    product_ctx: dict = data["product_context"]

    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"{_c('ERROR', RED)}: Case '{args.case}' not found in {CASES_FILE}.")
            sys.exit(1)

    # ── 2. Static checks ──────────────────────────────────────────────────────
    static_results = static_checks_on_cases_file(cases)
    print_static_results(static_results)

    static_failed = [c for c in static_results if not c.passed]
    if static_failed:
        print(_c(
            "Static checks failed. Fix cases.json before running live evals.\n",
            RED,
        ))
        if args.run_live:
            sys.exit(1)

    if not args.run_live:
        print("No live runs requested (omit --run-live to keep it this way).")
        print("Pass --run-live to call the agent and run deterministic checks.\n")
        sys.exit(0 if not static_failed else 1)

    # ── 3. Confirmation + cost estimate ───────────────────────────────────────
    n_cases, est_cost = estimate_live_cost(cases)
    print(
        f"Live eval plan: {n_cases} case(s), estimated cost ≈ ${est_cost:.4f} USD "
        f"(rough estimate; actual cost may vary)."
    )
    if not args.yes:
        answer = input("Proceed with live evals? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    # ── 4. Import project modules (deferred to avoid side-effects on static) ──
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass  # python-dotenv not installed — rely on env already being set

    try:
        from agent import run_agent, AgentRunInfo
        from schemas import AgentInput, AnalysisResult
        from telemetry import calculate_cost
    except ImportError as exc:
        print(f"{_c('ERROR', RED)}: Could not import project modules: {exc}")
        print(f"Make sure to run this script from the project root or that {PROJECT_ROOT} is on PYTHONPATH.")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print(_c("ERROR: OPENAI_API_KEY is not set.", RED))
        sys.exit(1)

    # ── 5. Run each case ──────────────────────────────────────────────────────
    print(f"\n{_c('── Live evaluation runs ──', BOLD)}")
    case_results: list[CaseResult] = []

    for case in cases:
        case_id = case["id"]
        case_type = case["type"]
        feedback_text = build_feedback_text(case)
        permitted_ids = case["expectations"].get("permitted_feedback_ids") or []

        agent_input = AgentInput(
            product_name=product_ctx["product_name"],
            product_description=product_ctx["product_description"],
            feedback_text=feedback_text,
        )

        start = time.perf_counter()
        try:
            result, run_info = run_agent(
                agent_input,
                _override_feedback_ids=permitted_ids,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            cr = CaseResult(
                case_id=case_id,
                case_type=case_type,
                status="ERROR",
                error=f"{type(exc).__name__}: {exc}",
                duration_seconds=round(elapsed, 2),
            )
            case_results.append(cr)
            print_case_result(cr)
            continue

        elapsed = time.perf_counter() - start
        cost = calculate_cost(run_info.input_tokens, run_info.output_tokens)

        # Deterministic checks
        try:
            checks, semantic_notes = deterministic_checks(case, result, run_info)
        except Exception as exc:
            checks = []
            semantic_notes = [f"Check execution error: {type(exc).__name__}: {exc}"]

        hard_failures = [c for c in checks if not c.passed]
        status = "PASS" if not hard_failures else "FAIL"

        cr = CaseResult(
            case_id=case_id,
            case_type=case_type,
            status=status,
            checks=checks,
            semantic_notes=semantic_notes,
            duration_seconds=round(elapsed, 2),
            input_tokens=run_info.input_tokens,
            output_tokens=run_info.output_tokens,
            estimated_cost=cost,
            opportunity_count=len(result.opportunities),
            tools_called=run_info.tools_called,
        )
        case_results.append(cr)
        print_case_result(cr)

    # ── 6. Aggregate metrics ──────────────────────────────────────────────────
    metrics = compute_aggregate_metrics(case_results)
    print_aggregate(metrics)

    # ── 7. Save results to JSON ───────────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = RESULTS_DIR / f"results_{timestamp}.json"

    output = {
        "timestamp": timestamp,
        "product_context": product_ctx,
        "aggregate_metrics": metrics,
        "case_results": [asdict(cr) for cr in case_results],
    }
    results_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to: {results_path}\n")

    # Exit non-zero if any live runs failed
    failed = [r for r in case_results if r.status == "FAIL"]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
