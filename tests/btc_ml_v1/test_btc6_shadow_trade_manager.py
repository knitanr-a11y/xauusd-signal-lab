from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_btc6_shadow_trades.py"
spec = importlib.util.spec_from_file_location("manage_btc6_shadow_trades", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def candidate(direction: str = "LONG", entry: str = "2026-07-02 12:15:00", sl: float = 99000.0, tp: float = 102000.0) -> pd.DataFrame:
    return pd.DataFrame([{
        "strategy_id": module.BTC6_ID,
        "signal_key": "btc6-test-1",
        "direction": direction,
        "signal_close_time": "2026-07-02 12:00:00",
        "entry_time": entry,
        "entry_price_reference": 100000.0,
        "sl_price": sl,
        "tp_price": tp,
        "rr": 2.0,
    }])


def bars(rows: list[list[object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close"]).assign(
        time=lambda frame: pd.to_datetime(frame["time"])
    )


def test_shadow_entry_uses_next_closed_m5_open() -> None:
    trades, _ = module.register_candidates({}, candidate(), 0.01)
    trade, events = module.process_trade(
        trades["btc6-test-1"],
        bars([["2026-07-02 12:15:00", 100000, 100500, 99500, 100200]]),
        30.0,
    )
    assert trade["status"] == "OPEN"
    assert trade["lot"] == 0.01
    assert trade["actual_entry_bid"] == 100000
    assert [event["event_type"] for event in events] == ["SHADOW_OPEN"]


def test_same_m5_bar_uses_sl_first() -> None:
    trades, _ = module.register_candidates({}, candidate(sl=99500, tp=100500), 0.01)
    trade, _ = module.process_trade(
        trades["btc6-test-1"],
        bars([["2026-07-02 12:15:00", 100000, 100700, 99400, 100100]]),
        30.0,
    )
    assert trade["status"] == "CLOSED"
    assert trade["exit_reason"] == "SL"
    assert trade["r_multiple"] == -1.0


def test_tp_result_is_spread_aware() -> None:
    trades, _ = module.register_candidates({}, candidate(), 0.01)
    trade, _ = module.process_trade(
        trades["btc6-test-1"],
        bars([["2026-07-02 12:15:00", 100000, 102100, 99900, 102050]]),
        30.0,
    )
    assert trade["exit_reason"] == "TP"
    assert round(trade["pnl_pips"], 2) == 197.0
    assert round(trade["effective_risk_usd"], 2) == 1030.0


def test_closed_trade_is_idempotent() -> None:
    trades, _ = module.register_candidates({}, candidate(), 0.01)
    trade, _ = module.process_trade(
        trades["btc6-test-1"],
        bars([["2026-07-02 12:15:00", 100000, 102100, 99900, 102050]]),
        30.0,
    )
    before = dict(trade)
    trade, events = module.process_trade(
        trade,
        bars([["2026-07-02 12:15:00", 100000, 102100, 99900, 102050]]),
        30.0,
    )
    assert events == []
    assert trade == before


def test_summary_keeps_realized_and_unrealized_history() -> None:
    summary = module.summarize([
        {"status": "CLOSED", "exit_time": "1", "pnl_pips": 100, "r_multiple": 1},
        {"status": "CLOSED", "exit_time": "2", "pnl_pips": -50, "r_multiple": -1},
        {"status": "OPEN", "unrealized_pips": 20, "unrealized_r": 0.2},
    ])
    assert summary["profit_factor"] == 2.0
    assert summary["max_drawdown_r"] == 1.0
    assert summary["open_unrealized_pips"] == 20.0
