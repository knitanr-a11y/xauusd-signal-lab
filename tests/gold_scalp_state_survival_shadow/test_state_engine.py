from __future__ import annotations

import pandas as pd

from scripts.gold_scalp_state_survival_shadow.state_engine import build_state_frame


def _candles(times, closes, ranges=None):
    ranges = ranges or [1.0] * len(times)
    rows = []
    for time, close, width in zip(times, closes, ranges):
        rows.append({"time": time, "open": close - 0.1, "high": close + width / 2, "low": close - width / 2, "close": close})
    return pd.DataFrame(rows)


def test_state_frame_uses_closed_higher_timeframes():
    m15_times = pd.date_range("2026-01-01", periods=6000, freq="15min")
    m15 = _candles(m15_times, [2000 + i * 0.01 for i in range(len(m15_times))])
    h1_times = pd.date_range("2025-10-01", periods=3000, freq="1h")
    h1 = _candles(h1_times, [1800 + i * 0.05 for i in range(len(h1_times))])
    h4_times = pd.date_range("2025-01-01", periods=2000, freq="4h")
    h4 = _candles(h4_times, [1600 + i * 0.1 for i in range(len(h4_times))])
    result = build_state_frame(m15, h1, h4)
    row = result.iloc[-1]
    assert row["htf"] == "UP"
    assert row["fine"].count("|") == 5


def test_read_union_rejects_malformed_concatenated_boundary_and_keeps_later_source(tmp_path):
    from scripts.gold_scalp_state_survival_shadow.state_engine import read_union

    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text(
        "time,open,high,low,close,tick_volume,spread,real_volume\n"
        "2026.08.01 01:00:00,100,101,99,100.5,10,20,0\n"
        "2026.08.01 01:01:00,100,101,99,100.5,10,20,0,EXTRA,JOINED,ROW\n",
        encoding="utf-8",
    )
    second.write_text(
        "time,open,high,low,close,tick_volume,spread,real_volume\n"
        "2026.08.01 01:00:00,200,201,199,200.5,11,21,0\n"
        "2026.08.01 01:01:00,201,202,200,201.5,12,22,0\n",
        encoding="utf-8",
    )
    result = read_union([first, second])
    assert len(result) == 2
    assert result.loc[result["time"] == pd.Timestamp("2026-08-01 01:00:00"), "open"].iloc[0] == 200
    audit = result.attrs["source_audit"]
    assert audit["sources"][0]["parser_recovery_used"] is True
    assert audit["sources"][0]["parser_rejected_rows"] == 1
    assert audit["duplicate_rows_removed"] == 1
