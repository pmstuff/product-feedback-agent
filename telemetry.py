"""
telemetry.py — Token usage tracking and run telemetry for the Product Feedback Agent.

Two levels of tracking:
  UsageRecord / SessionTelemetry — lightweight, in-memory per-session summary for the sidebar.
  RunRecord                      — full per-run record persisted to data/runs.jsonl.

Prices are read from env vars on each cost calculation (not at import time) so that
load_dotenv() in app.py always takes effect before any cost is computed.

All monetary values are in USD.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ─── Pricing ──────────────────────────────────────────────────────────────────

def _read_price(env_var: str, default: float) -> float:
    """Read a per-million-token price from an env var; fall back to default."""
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def current_prices() -> tuple[float, float]:
    """
    Return (input_price_per_million, output_price_per_million) in USD.

    Called on every cost computation so that any value set in .env (loaded by
    load_dotenv() in app.py before the first run) is always picked up.
    """
    return (
        _read_price("MODEL_INPUT_PRICE_PER_MILLION", 5.00),
        _read_price("MODEL_OUTPUT_PRICE_PER_MILLION", 15.00),
    )


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD for the given token counts."""
    in_price, out_price = current_prices()
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


# ─── In-session usage (sidebar) ───────────────────────────────────────────────

@dataclass
class UsageRecord:
    """Token usage and estimated cost for one agent run (shown in sidebar)."""

    input_tokens: int = 0
    output_tokens: int = 0
    run_label: str = ""

    @property
    def input_cost_usd(self) -> float:
        in_price, _ = current_prices()
        return self.input_tokens * in_price / 1_000_000

    @property
    def output_cost_usd(self) -> float:
        _, out_price = current_prices()
        return self.output_tokens * out_price / 1_000_000

    @property
    def total_cost_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd

    def summary(self) -> str:
        return (
            f"Tokens — input: {self.input_tokens:,} | "
            f"output: {self.output_tokens:,} | "
            f"cost: ${self.total_cost_usd:.4f} USD"
        )


@dataclass
class SessionTelemetry:
    """Accumulates UsageRecords across multiple runs in one Streamlit session."""

    records: list[UsageRecord] = field(default_factory=list)

    def add(self, record: UsageRecord) -> None:
        self.records.append(record)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.total_cost_usd for r in self.records)

    def session_summary(self) -> str:
        if not self.records:
            return "No runs recorded this session."
        return (
            f"Session total — "
            f"runs: {len(self.records)} | "
            f"input: {self.total_input_tokens:,} | "
            f"output: {self.total_output_tokens:,} | "
            f"cost: ${self.total_cost_usd:.4f} USD"
        )


# ─── Persistent run records ────────────────────────────────────────────────────

_RUNS_DIR = Path(__file__).parent / "data"
_RUNS_FILE = _RUNS_DIR / "runs.jsonl"


@dataclass
class RunRecord:
    """
    Full telemetry record for one agent execution.

    Persisted to data/runs.jsonl — one JSON object per line.

    Fields
    ------
    run_id          : UUID4 hex. Unique per run; use to correlate logs and results.
    timestamp       : ISO-8601 UTC start time.
    feedback_count  : Rows passed to the agent after CSV validation.
    model           : Model identifier (e.g. "gpt-4o").
    duration_seconds: Wall-clock seconds from run start to result/error.
    model_requests  : Number of LLM API calls made during the run. Each tool-call
                      round-trip counts as one request.
    input_tokens    : Total prompt tokens across all model requests in this run.
    output_tokens   : Total completion tokens across all model requests.
    total_tokens    : input_tokens + output_tokens.
    estimated_cost  : USD, computed from token counts and env-configured prices.
    tools_called    : Ordered list of tool names the agent invoked (may repeat).
    opportunity_count: Opportunities in the final AnalysisResult (0 on failure).
    success         : True if the run produced a valid AnalysisResult.
    error_type      : Exception class name if success is False, else None.
    """

    run_id: str
    timestamp: str
    feedback_count: int
    model: str
    duration_seconds: float
    model_requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    tools_called: list[str]
    opportunity_count: int
    success: bool
    error_type: Optional[str] = None

    # ── Convenience ──────────────────────────────────────────────────────────

    @staticmethod
    def new_id() -> str:
        """Generate a fresh run ID."""
        return uuid.uuid4().hex

    @staticmethod
    def now_iso() -> str:
        """Current UTC time as ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def cost_per_opportunity(self) -> Optional[float]:
        """
        USD spent divided by opportunities generated.

        Note: this is cost per *generated* opportunity (quantity), not cost per
        *valid* or *accepted* opportunity (quality). A run that produced two
        low-quality opportunities has the same denominator as one that produced
        two high-quality opportunities.  Use this metric for capacity planning,
        not for measuring analytical quality.
        """
        if self.opportunity_count == 0:
            return None
        return self.estimated_cost / self.opportunity_count


def append_run_record(record: RunRecord) -> None:
    """Append one RunRecord as a JSON line to data/runs.jsonl."""
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(record), ensure_ascii=False)
    with _RUNS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
