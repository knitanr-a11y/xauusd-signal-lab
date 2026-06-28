from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def discovery_module():
    repo = Path(__file__).resolve().parents[2]
    module_dir = repo / "scripts/gold_ml_v1/new_candidate_discovery"
    research_dir = repo / "scripts/gold_ml_v1/research_challenger"
    for path in (str(module_dir), str(research_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module("build_raw_proposals_v1")


def proposal_frame(overrides: list[dict[str, float]]) -> pd.DataFrame:
    base = {
        "atr14": 1.0,
        "ema20": 100.0,
        "ema50": 99.0,
        "gap_h1_atr": 0.2,
        "gap_h4_atr": 0.2,
        "prev_high_20": np.nan,
        "prev_low_20": np.nan,
        "prev_high_50": np.nan,
        "prev_low_50": np.nan,
        "bb_width_pct_lag1_256": np.nan,
        "bb_upper": 200.0,
        "bb_lower": 0.0,
        "candle_range": 1.0,
        "close_location": 0.7,
        "band_upper": 200.0,
        "band_lower": 0.0,
        "prior_long_touch4": False,
        "prior_short_touch4": False,
        "atr_pct_lag1_256": 0.5,
        "open": 100.0,
        "high": 100.2,
        "low": 100.0,
        "close": 100.1,
        "signed_body": 0.1,
    }
    opens = pd.date_range("2026-01-01", periods=len(overrides), freq="15min")
    rows = []
    for index, values in enumerate(overrides):
        rows.append(
            base
            | values
            | {
                "bar_open_time": opens[index],
                "bar_close_time": opens[index] + pd.Timedelta(minutes=15),
            }
        )
    return pd.DataFrame(rows)


def run_proposals(frame: pd.DataFrame) -> pd.DataFrame:
    module = discovery_module()
    exact_m1 = pd.DatetimeIndex(frame["bar_close_time"])
    return module.generate_raw_proposals(frame, exact_m1)


def test_invalidation_bar_does_not_rearm_same_candidate() -> None:
    frame = proposal_frame(
        [
            {
                "open": 100.0,
                "high": 100.7,
                "low": 99.9,
                "close": 100.5,
                "signed_body": 0.5,
                "prev_high_20": 100.0,
            },
            {
                "open": 99.2,
                "high": 99.8,
                "low": 99.1,
                "close": 99.7,
                "signed_body": 0.5,
                "prev_high_20": 99.0,
            },
            {
                "open": 99.15,
                "high": 99.4,
                "low": 99.1,
                "close": 99.3,
                "signed_body": 0.15,
                "prev_high_20": 101.0,
            },
        ]
    )
    assert run_proposals(frame).empty


def test_confirmation_bar_emits_once_but_does_not_rearm() -> None:
    frame = proposal_frame(
        [
            {
                "open": 100.0,
                "high": 100.7,
                "low": 99.9,
                "close": 100.5,
                "signed_body": 0.5,
                "prev_high_20": 100.0,
            },
            {
                "open": 99.8,
                "high": 100.4,
                "low": 100.0,
                "close": 100.3,
                "signed_body": 0.5,
                "prev_high_20": 99.8,
            },
            {
                "open": 99.8,
                "high": 100.1,
                "low": 99.9,
                "close": 100.0,
                "signed_body": 0.2,
                "prev_high_20": 101.0,
            },
        ]
    )
    proposals = run_proposals(frame)
    selected = proposals[proposals["candidate_id"] == "GML1-NCD-001-L"]
    assert len(selected) == 1
    assert selected.iloc[0]["decision_time"] == frame.iloc[1]["bar_close_time"]


def test_expiry_bar_does_not_rearm_same_candidate() -> None:
    rows: list[dict[str, float]] = [
        {
            "open": 100.0,
            "high": 100.7,
            "low": 99.9,
            "close": 100.5,
            "signed_body": 0.5,
            "prev_high_20": 100.0,
        }
    ]
    rows.extend(
        {
            "open": 101.0,
            "high": 101.2,
            "low": 100.5,
            "close": 101.05,
            "signed_body": 0.05,
            "prev_high_20": 102.0,
        }
        for _ in range(8)
    )
    rows.extend(
        [
            {
                "open": 100.0,
                "high": 100.7,
                "low": 100.0,
                "close": 100.5,
                "signed_body": 0.5,
                "prev_high_20": 100.0,
            },
            {
                "open": 100.0,
                "high": 100.3,
                "low": 100.1,
                "close": 100.2,
                "signed_body": 0.2,
                "prev_high_20": 102.0,
            },
        ]
    )
    assert run_proposals(proposal_frame(rows)).empty
