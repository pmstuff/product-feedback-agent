"""
validation.py — Deterministic CSV validation for the Product Feedback Agent.

All logic here is pure Python / Pandas — no LLM calls, no API calls.
This module is imported by app.py and independently tested in tests/test_validation.py.

Design:
  validate_dataframe() is the single entry point. It returns a ValidationResult
  that the UI renders without needing to know the internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# ─── Constants ────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"feedback_id", "created_at", "customer_segment", "channel", "feedback"}
)

# Canonical values — used for normalisation and validation.
VALID_SEGMENTS: frozenset[str] = frozenset({"SMB", "Mid-market", "Enterprise"})
VALID_CHANNELS: frozenset[str] = frozenset({"Support", "Interview", "Survey", "Sales"})

# Case-insensitive lookup maps — map lowercased input → canonical value.
_SEGMENT_MAP: dict[str, str] = {v.lower(): v for v in VALID_SEGMENTS}
_CHANNEL_MAP: dict[str, str] = {v.lower(): v for v in VALID_CHANNELS}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """A single validation problem, categorised by severity."""

    severity: str          # "error" | "warning"
    code: str              # machine-readable identifier
    message: str           # human-readable description
    rows: list[int] = field(default_factory=list)  # 0-based row indices, if relevant


@dataclass
class ValidationResult:
    """Outcome of validate_dataframe()."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    cleaned_df: Optional[pd.DataFrame] = None   # normalised dataframe, if valid
    stats: dict = field(default_factory=dict)   # summary counts for the UI

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# ─── Validation steps ─────────────────────────────────────────────────────────

def _check_required_columns(df: pd.DataFrame) -> list[ValidationIssue]:
    """Return an error for every required column that is missing."""
    missing = REQUIRED_COLUMNS - set(df.columns.str.strip().str.lower())
    # Map lowercased back to the canonical name for a clear error message.
    canonical_missing = [
        col for col in REQUIRED_COLUMNS
        if col not in {c.strip().lower() for c in df.columns}
    ]
    if canonical_missing:
        return [ValidationIssue(
            severity="error",
            code="MISSING_COLUMNS",
            message=(
                f"Missing required column(s): {', '.join(sorted(canonical_missing))}. "
                f"Expected: {', '.join(sorted(REQUIRED_COLUMNS))}."
            ),
        )]
    return []


def _normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and lowercase column names for consistent access."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()
    return df


def _check_empty_rows(df: pd.DataFrame) -> list[ValidationIssue]:
    """Warn about rows where the feedback text is missing or blank."""
    blank_mask = df["feedback"].isna() | (df["feedback"].astype(str).str.strip() == "")
    blank_indices = df.index[blank_mask].tolist()
    if blank_indices:
        return [ValidationIssue(
            severity="warning",
            code="EMPTY_FEEDBACK",
            message=(
                f"{len(blank_indices)} row(s) have empty feedback text and will be "
                "skipped during analysis."
            ),
            rows=blank_indices,
        )]
    return []


def _normalise_segments(df: pd.DataFrame) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """
    Normalise customer_segment values case-insensitively.
    Rows with unrecognised values are flagged as errors.
    """
    issues: list[ValidationIssue] = []
    df = df.copy()

    normalised = df["customer_segment"].astype(str).str.strip().map(
        lambda v: _SEGMENT_MAP.get(v.lower(), None)
    )

    bad_mask = normalised.isna()
    bad_indices = df.index[bad_mask].tolist()

    if bad_indices:
        bad_values = df.loc[bad_mask, "customer_segment"].unique().tolist()
        issues.append(ValidationIssue(
            severity="error",
            code="INVALID_SEGMENT",
            message=(
                f"{len(bad_indices)} row(s) have an unrecognised customer_segment "
                f"value: {bad_values}. "
                f"Accepted values: {sorted(VALID_SEGMENTS)}."
            ),
            rows=bad_indices,
        ))
    else:
        df["customer_segment"] = normalised

    return df, issues


def _normalise_channels(df: pd.DataFrame) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """
    Normalise channel values case-insensitively.
    Rows with unrecognised values are flagged as errors.
    """
    issues: list[ValidationIssue] = []
    df = df.copy()

    normalised = df["channel"].astype(str).str.strip().map(
        lambda v: _CHANNEL_MAP.get(v.lower(), None)
    )

    bad_mask = normalised.isna()
    bad_indices = df.index[bad_mask].tolist()

    if bad_indices:
        bad_values = df.loc[bad_mask, "channel"].unique().tolist()
        issues.append(ValidationIssue(
            severity="error",
            code="INVALID_CHANNEL",
            message=(
                f"{len(bad_indices)} row(s) have an unrecognised channel value: "
                f"{bad_values}. "
                f"Accepted values: {sorted(VALID_CHANNELS)}."
            ),
            rows=bad_indices,
        ))
    else:
        df["channel"] = normalised

    return df, issues


def _build_stats(df: pd.DataFrame) -> dict:
    """Build a summary dict for display in the UI."""
    return {
        "total_rows": len(df),
        "non_empty_rows": int(
            (df["feedback"].notna() & (df["feedback"].astype(str).str.strip() != "")).sum()
        ),
        "segments": df["customer_segment"].value_counts().to_dict(),
        "channels": df["channel"].value_counts().to_dict(),
    }


# ─── Public entry point ───────────────────────────────────────────────────────

def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """
    Validate and normalise a feedback DataFrame.

    Steps (in order):
      1. Normalise column names (strip whitespace, lowercase)
      2. Check all required columns are present — abort if not
      3. Check for empty feedback rows (warning)
      4. Normalise and validate customer_segment values
      5. Normalise and validate channel values

    Returns:
        ValidationResult with is_valid=True and a cleaned_df if all errors pass,
        or is_valid=False with a list of issues describing what went wrong.
    """
    all_issues: list[ValidationIssue] = []

    # Step 1 — normalise column names
    df = _normalise_column_names(df)

    # Step 2 — required columns (hard stop if missing)
    col_issues = _check_required_columns(df)
    if col_issues:
        return ValidationResult(is_valid=False, issues=col_issues)

    # Step 3 — empty rows (warning only, don't block)
    all_issues.extend(_check_empty_rows(df))

    # Step 4 — segment normalisation
    df, seg_issues = _normalise_segments(df)
    all_issues.extend(seg_issues)

    # Step 5 — channel normalisation
    df, chan_issues = _normalise_channels(df)
    all_issues.extend(chan_issues)

    # Determine overall validity (warnings are fine; errors block analysis)
    has_errors = any(i.severity == "error" for i in all_issues)

    return ValidationResult(
        is_valid=not has_errors,
        issues=all_issues,
        cleaned_df=df if not has_errors else None,
        stats=_build_stats(df) if not has_errors else {},
    )
