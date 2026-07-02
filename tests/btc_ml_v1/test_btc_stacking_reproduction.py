from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/btc_ml_v1/research/reproduce_btc_stacking_portfolio.py"
)
spec = importlib.util.spec_from_file_location("reproduce_btc_stacking_portfolio", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_reference_manifest_covers_all_adopted_candidates_and_input_hashes() -> None:
    reference_path = (
        Path(__file__).resolve().parents[2]
        / "configs/btc_ml_v1/btc_stacking_reproduction_reference.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))

    assert set(module.CANDIDATE_IDS) == {"btc4", "btc5", "btc6", "btc7r", "btc9r"}
    assert reference["input_packages"]["BTCUSD_HISTORY_CHAT_PACKAGE.zip"]["sha256"]
    assert reference["input_packages"]["BTCUSD_H4_WARMUP_PACKAGE.zip"]["sha256"]
    assert reference["controls"]["ema_applied_price_btc4"] == "close"
    assert reference["controls"]["btc4_risk_cap_pips"] == 400
    assert reference["expected_portfolio"]["all"]["trades"] == 185


def test_simple_simulation_is_stop_first_on_same_bar() -> None:
    bars = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-01-01 00:00"]),
            "high": [110.0],
            "low": [90.0],
        }
    )
    plan = pd.Series(
        {
            "entry_time": pd.Timestamp("2026-01-01 00:00"),
            "entry_idx": 0,
            "direction": "LONG",
            "stop_chart": 95.0,
            "target_chart": 105.0,
            "risk_pips": 10.0,
            "reward_pips": 8.0,
        }
    )

    result = module.simulate_simple(plan, bars, minutes=5, index_column="entry_idx")

    assert result["exit_reason"] == "SL"
    assert result["pnl_pips"] == -10.0


def test_btc4_tp1_then_same_bar_break_even_is_not_tp2() -> None:
    bars = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-01-01 00:00"]),
            "high": [111.0],
            "low": [103.0],
        }
    )
    plan = pd.Series(
        {
            "direction": "LONG",
            "entry_m5_idx": 0,
            "entry_bid": 100.0,
            "spread_usd": 5.0,
            "stop_chart": 90.0,
            "tp1": 110.0,
            "tp2": 120.0,
            "tp1_net_usd": 5.0,
            "tp2_net_usd": 15.0,
            "risk_pips": 1.5,
        }
    )

    result = module.simulate_btc4(plan, bars)

    assert result["exit_reason"] == "TP1_THEN_BE_SAME_M5"
    assert result["pnl_pips"] == 0.25


def test_entry_fingerprint_is_order_independent() -> None:
    frame = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(["2026-01-02", "2026-01-01"]),
            "direction": ["SHORT", "LONG"],
            "risk_pips": [70.1234564, 80.0],
            "reward_pips": [56.0987654, 64.0],
        }
    )

    first = module.entry_fingerprint(frame, time_column="entry_time")
    second = module.entry_fingerprint(frame.iloc[::-1], time_column="entry_time")

    assert first == second
