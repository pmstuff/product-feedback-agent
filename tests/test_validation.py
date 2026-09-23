"""
tests/test_validation.py — Unit tests for validation.py

Run with:
    python -m pytest tests/test_validation.py -v

These tests are deterministic and require no API keys or network access.
"""
import pandas as pd
import pytest
import sys
import os

# Allow imports from the project root when running from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation import (
    REQUIRED_COLUMNS,
    VALID_CHANNELS,
    VALID_SEGMENTS,
    ValidationResult,
    validate_dataframe,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_df(**overrides) -> pd.DataFrame:
    """
    Return a minimal valid DataFrame with one row.
    Override any column value via kwargs.
    """
    base = {
        "feedback_id": ["FB-001"],
        "created_at": ["2026-01-01"],
        "customer_segment": ["Enterprise"],
        "channel": ["Support"],
        "feedback": ["The export is too slow."],
    }
    base.update({k: [v] for k, v in overrides.items()})
    return pd.DataFrame(base)


def _make_multi_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame from a list of row dicts."""
    base_keys = ["feedback_id", "created_at", "customer_segment", "channel", "feedback"]
    data = {k: [] for k in base_keys}
    for i, row in enumerate(rows):
        for k in base_keys:
            data[k].append(row.get(k, f"default-{i}"))
    return pd.DataFrame(data)


# ─── Happy path ───────────────────────────────────────────────────────────────

class TestHappyPath:
    def test_valid_dataframe_returns_is_valid_true(self):
        result = validate_dataframe(_make_df())
        assert result.is_valid is True

    def test_valid_dataframe_has_no_errors(self):
        result = validate_dataframe(_make_df())
        assert result.errors == []

    def test_valid_dataframe_returns_cleaned_df(self):
        result = validate_dataframe(_make_df())
        assert result.cleaned_df is not None
        assert len(result.cleaned_df) == 1

    def test_valid_dataframe_has_stats(self):
        result = validate_dataframe(_make_df())
        assert result.stats["total_rows"] == 1
        assert result.stats["non_empty_rows"] == 1

    def test_all_valid_segments_accepted(self):
        for seg in VALID_SEGMENTS:
            result = validate_dataframe(_make_df(customer_segment=seg))
            assert result.is_valid, f"Segment '{seg}' should be valid"

    def test_all_valid_channels_accepted(self):
        for chan in VALID_CHANNELS:
            result = validate_dataframe(_make_df(channel=chan))
            assert result.is_valid, f"Channel '{chan}' should be valid"

    def test_full_sample_csv_is_valid(self):
        """The sample CSV shipped with the project must pass validation."""
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_feedback.csv")
        df = pd.read_csv(csv_path)
        result = validate_dataframe(df)
        assert result.is_valid, f"Sample CSV failed: {[i.message for i in result.errors]}"
        assert result.stats["total_rows"] == 40


# ─── Missing columns ──────────────────────────────────────────────────────────

class TestMissingColumns:
    def test_missing_single_column_returns_error(self):
        df = _make_df().drop(columns=["feedback"])
        result = validate_dataframe(df)
        assert result.is_valid is False
        assert any(i.code == "MISSING_COLUMNS" for i in result.errors)

    def test_missing_multiple_columns_returns_one_error(self):
        df = _make_df().drop(columns=["feedback", "channel"])
        result = validate_dataframe(df)
        errors = [i for i in result.errors if i.code == "MISSING_COLUMNS"]
        assert len(errors) == 1
        assert "feedback" in errors[0].message
        assert "channel" in errors[0].message

    def test_missing_columns_returns_no_cleaned_df(self):
        df = _make_df().drop(columns=["created_at"])
        result = validate_dataframe(df)
        assert result.cleaned_df is None

    def test_extra_columns_are_allowed(self):
        df = _make_df()
        df["extra_col"] = "bonus"
        result = validate_dataframe(df)
        assert result.is_valid is True

    @pytest.mark.parametrize("col", list(REQUIRED_COLUMNS))
    def test_each_required_column_individually(self, col):
        df = _make_df().drop(columns=[col])
        result = validate_dataframe(df)
        assert result.is_valid is False, f"Dropping '{col}' should fail validation"

    def test_column_names_with_extra_whitespace_are_normalised(self):
        df = _make_df()
        df.columns = [f" {c} " for c in df.columns]
        result = validate_dataframe(df)
        assert result.is_valid is True


# ─── Empty rows ───────────────────────────────────────────────────────────────

class TestEmptyRows:
    def test_empty_feedback_cell_produces_warning(self):
        df = _make_df(feedback="")
        result = validate_dataframe(df)
        assert any(i.code == "EMPTY_FEEDBACK" for i in result.warnings)

    def test_whitespace_only_feedback_is_empty(self):
        df = _make_df(feedback="   ")
        result = validate_dataframe(df)
        assert any(i.code == "EMPTY_FEEDBACK" for i in result.warnings)

    def test_nan_feedback_is_empty(self):
        df = _make_df()
        df.at[0, "feedback"] = float("nan")
        result = validate_dataframe(df)
        assert any(i.code == "EMPTY_FEEDBACK" for i in result.warnings)

    def test_empty_rows_still_valid(self):
        """Empty feedback is a warning, not an error — file is still processable."""
        df = _make_df(feedback="")
        result = validate_dataframe(df)
        assert result.is_valid is True

    def test_empty_rows_reported_correctly(self):
        rows = [
            {"feedback_id": "FB-001", "created_at": "2026-01-01",
             "customer_segment": "SMB", "channel": "Survey", "feedback": "Good product"},
            {"feedback_id": "FB-002", "created_at": "2026-01-02",
             "customer_segment": "SMB", "channel": "Survey", "feedback": ""},
            {"feedback_id": "FB-003", "created_at": "2026-01-03",
             "customer_segment": "SMB", "channel": "Survey", "feedback": "Needs work"},
        ]
        df = _make_multi_df(rows)
        result = validate_dataframe(df)
        warning = next(i for i in result.warnings if i.code == "EMPTY_FEEDBACK")
        assert 1 in warning.rows   # row index 1 is blank
        assert len(warning.rows) == 1

    def test_non_empty_rows_not_flagged(self):
        df = _make_df(feedback="Something useful")
        result = validate_dataframe(df)
        assert not any(i.code == "EMPTY_FEEDBACK" for i in result.warnings)


# ─── Segment normalisation ────────────────────────────────────────────────────

class TestSegmentNormalisation:
    def test_lowercase_segment_is_normalised(self):
        result = validate_dataframe(_make_df(customer_segment="smb"))
        assert result.is_valid is True
        assert result.cleaned_df.iloc[0]["customer_segment"] == "SMB"

    def test_uppercase_segment_is_normalised(self):
        result = validate_dataframe(_make_df(customer_segment="ENTERPRISE"))
        assert result.is_valid is True
        assert result.cleaned_df.iloc[0]["customer_segment"] == "Enterprise"

    def test_mixed_case_mid_market_normalised(self):
        result = validate_dataframe(_make_df(customer_segment="MID-MARKET"))
        assert result.is_valid is True
        assert result.cleaned_df.iloc[0]["customer_segment"] == "Mid-market"

    def test_invalid_segment_returns_error(self):
        result = validate_dataframe(_make_df(customer_segment="Startup"))
        assert result.is_valid is False
        assert any(i.code == "INVALID_SEGMENT" for i in result.errors)

    def test_invalid_segment_error_names_bad_value(self):
        result = validate_dataframe(_make_df(customer_segment="Unicorn"))
        error = next(i for i in result.errors if i.code == "INVALID_SEGMENT")
        assert "Unicorn" in error.message

    def test_invalid_segment_error_lists_valid_options(self):
        result = validate_dataframe(_make_df(customer_segment="Startup"))
        error = next(i for i in result.errors if i.code == "INVALID_SEGMENT")
        for valid in VALID_SEGMENTS:
            assert valid in error.message


# ─── Channel normalisation ────────────────────────────────────────────────────

class TestChannelNormalisation:
    def test_lowercase_channel_is_normalised(self):
        result = validate_dataframe(_make_df(channel="support"))
        assert result.is_valid is True
        assert result.cleaned_df.iloc[0]["channel"] == "Support"

    def test_uppercase_channel_is_normalised(self):
        result = validate_dataframe(_make_df(channel="SURVEY"))
        assert result.is_valid is True
        assert result.cleaned_df.iloc[0]["channel"] == "Survey"

    def test_invalid_channel_returns_error(self):
        result = validate_dataframe(_make_df(channel="Twitter"))
        assert result.is_valid is False
        assert any(i.code == "INVALID_CHANNEL" for i in result.errors)

    def test_invalid_channel_error_names_bad_value(self):
        result = validate_dataframe(_make_df(channel="Email"))
        error = next(i for i in result.errors if i.code == "INVALID_CHANNEL")
        assert "Email" in error.message

    def test_invalid_channel_error_lists_valid_options(self):
        result = validate_dataframe(_make_df(channel="Reddit"))
        error = next(i for i in result.errors if i.code == "INVALID_CHANNEL")
        for valid in VALID_CHANNELS:
            assert valid in error.message


# ─── Combined / edge cases ────────────────────────────────────────────────────

class TestCombinedCases:
    def test_multiple_errors_all_reported(self):
        df = _make_df(customer_segment="Unknown", channel="Pigeon")
        result = validate_dataframe(df)
        codes = {i.code for i in result.errors}
        assert "INVALID_SEGMENT" in codes
        assert "INVALID_CHANNEL" in codes

    def test_errors_and_warnings_coexist(self):
        df = _make_df(customer_segment="Unknown", feedback="")
        result = validate_dataframe(df)
        assert not result.is_valid
        assert any(i.severity == "error" for i in result.issues)
        assert any(i.severity == "warning" for i in result.issues)

    def test_empty_dataframe_returns_warnings_only(self):
        """An empty-but-schema-correct DataFrame is valid with a warning."""
        df = pd.DataFrame(columns=list(REQUIRED_COLUMNS))
        result = validate_dataframe(df)
        assert result.is_valid is True

    def test_stats_counts_match_data(self):
        rows = [
            {"feedback_id": "FB-001", "created_at": "2026-01-01",
             "customer_segment": "SMB", "channel": "Survey", "feedback": "Good"},
            {"feedback_id": "FB-002", "created_at": "2026-01-02",
             "customer_segment": "Enterprise", "channel": "Support", "feedback": "Bad"},
            {"feedback_id": "FB-003", "created_at": "2026-01-03",
             "customer_segment": "SMB", "channel": "Survey", "feedback": ""},
        ]
        df = _make_multi_df(rows)
        result = validate_dataframe(df)
        assert result.stats["total_rows"] == 3
        assert result.stats["non_empty_rows"] == 2
        assert result.stats["segments"]["SMB"] == 2
        assert result.stats["segments"]["Enterprise"] == 1
