from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "btc_youtube_candidate_signals.py"
spec = importlib.util.spec_from_file_location("btc_youtube_candidate_signals", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def base_notification(candidate_id: str, lot: float = 0.02) -> dict:
    return module._notification_row(
        candidate_id=candidate_id,
        direction="LONG",
        entry_time=pd.Timestamp("2026-07-02 12:05:00"),
        entry=100000.0,
        stop=99000.0,
        target=102000.0,
        rr=2.0,
        lot=lot,
        reason="test",
        trade_enabled=candidate_id != module.BTC6_ID,
        tp1=101000.0 if candidate_id == module.BTC4_ID else None,
        tp2=102000.0 if candidate_id == module.BTC4_ID else None,
    )


def test_synthetic_entry_row_has_no_future_range() -> None:
    frame = pd.DataFrame({
        "time": pd.to_datetime(["2026-07-02 12:00:00"]),
        "open": [100.0], "high": [110.0], "low": [90.0], "close": [105.0],
        "tick_volume": [1], "spread": [0], "real_volume": [0],
    })
    result, synthetic_time = module.append_synthetic_entry_row(frame, 5)
    assert synthetic_time == pd.Timestamp("2026-07-02 12:05:00")
    row = result.iloc[-1]
    assert row["open"] == row["high"] == row["low"] == row["close"] == 105.0


def test_btc4_split_order_contract() -> None:
    notification = base_notification(module.BTC4_ID)
    rows = pd.DataFrame([
        module._order_row(notification, role="TP1", lot=0.01, tp=101000.0, magic=module.BTC4_TP1_MAGIC),
        module._order_row(notification, role="TP2", lot=0.01, tp=102000.0, magic=module.BTC4_TP2_MAGIC),
    ])
    assert module.validate_order_group(rows) == []
    assert rows["lot"].sum() == 0.02


def test_btc5_single_order_contract() -> None:
    notification = base_notification(module.BTC5_ID, lot=0.01)
    rows = pd.DataFrame([
        module._order_row(notification, role="FULL", lot=0.01, tp=102000.0, magic=module.BTC5_MAGIC),
    ])
    assert module.validate_order_group(rows) == []


def test_btc6_is_rejected_from_order_payload() -> None:
    notification = base_notification(module.BTC6_ID, lot=0.0)
    rows = pd.DataFrame([
        module._order_row(notification, role="FULL", lot=0.01, tp=102000.0, magic=26070601),
    ])
    errors = module.validate_order_group(rows)
    assert errors
    assert "non-trade candidates" in errors[0]
