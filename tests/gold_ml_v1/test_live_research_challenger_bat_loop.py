from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


def live_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "scripts/gold_ml_v1/live_research_challenger"
    )


def import_live(name: str):
    path = str(live_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


def test_live_runtime_contract_is_audit_only() -> None:
    repo = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            repo
            / "config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json"
        ).read_text(encoding="utf-8")
    )
    assert contract["runner"]["type"] == "persistent_bat_loop"
    assert contract["input"]["csv_latest_row_contract"] == "closed"
    assert set(contract["live_sleeves"]) == {
        "A_CORE",
        "B_STATE",
        "P18",
        "W024A",
    }
    assert set(contract["disabled_live_sleeves"]) == {"P16", "P19"}
    assert contract["controls"] == {
        "audit_only": True,
        "final_signal": False,
        "discord": False,
        "mt5_order": False,
        "p16_live": False,
        "p19_live": False,
    }


def test_same_m1_bar_uses_sl_priority() -> None:
    position = import_live("live_position")
    frame = pd.DataFrame(
        {
            "bar_open_time": [pd.Timestamp("2026-01-01 00:00:00")],
            "open": [100.0],
            "high": [102.0],
            "low": [98.0],
            "close": [100.0],
            "spread": [0.0],
        }
    )
    engine = position.LiveM1Engine(frame)
    long_result = engine.evaluate(
        pd.Timestamp("2026-01-01 00:00:00"),
        1.0,
        position.PositionContract("LONG", 1.0, 1, "close", "close"),
    )
    short_result = engine.evaluate(
        pd.Timestamp("2026-01-01 00:00:00"),
        1.0,
        position.PositionContract("SHORT", 1.0, 1, "close", "close"),
    )
    assert long_result["outcome"] == "SL"
    assert long_result["r"] == -1.0
    assert short_result["outcome"] == "SL"
    assert short_result["r"] == -1.0


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    frame = pd.DataFrame(
        rows,
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ],
    )
    frame.to_csv(path, index=False)


def test_reader_drops_only_trailing_incomplete_row(tmp_path: Path) -> None:
    data = import_live("live_data")
    path = tmp_path / "goldsharp_m1.csv"
    _write_csv(
        path,
        [
            ["2026.01.01 00:00:00", 100, 101, 99, 100, 1, 2, 0],
            ["2026.01.01 00:01:00", 100, 101, 99, 100, 1, 2, 0],
            ["2026.01.01 00:02:00", "", "", "", "", "", "", ""],
        ],
    )
    result = data.read_closed_bars(path, "M1")
    assert len(result) == 2
    assert result["bar_open_time"].iloc[-1] == pd.Timestamp("2026-01-01 00:01:00")


def test_reader_rejects_internal_incomplete_row(tmp_path: Path) -> None:
    data = import_live("live_data")
    path = tmp_path / "goldsharp_m1.csv"
    _write_csv(
        path,
        [
            ["2026.01.01 00:00:00", 100, 101, 99, 100, 1, 2, 0],
            ["2026.01.01 00:01:00", "", "", "", "", "", "", ""],
            ["2026.01.01 00:02:00", 100, 101, 99, 100, 1, 2, 0],
        ],
    )
    with pytest.raises(ValueError, match="invalid non-trailing rows"):
        data.read_closed_bars(path, "M1")


def _constant_bars(end: pd.Timestamp, periods: int, frequency: str) -> pd.DataFrame:
    delta = pd.Timedelta(frequency)
    times = pd.date_range(end=end - delta, periods=periods, freq=frequency)
    return pd.DataFrame(
        {
            "time": times.strftime("%Y.%m.%d %H:%M:%S"),
            "open": 100.0,
            "high": 100.1,
            "low": 99.9,
            "close": 100.0,
            "tick_volume": 100,
            "spread": 2,
            "real_volume": 0,
        }
    )


def test_first_run_initializes_without_backfill(tmp_path: Path) -> None:
    runtime = import_live("live_runtime")
    live_root = tmp_path / "live"
    output = tmp_path / "output"
    live_root.mkdir()
    end = pd.Timestamp("2026-01-10 00:00:00")
    specifications = {
        "m1": (2, "1min"),
        "m5": (2, "5min"),
        "m15": (500, "15min"),
        "h1": (200, "1h"),
        "h4": (200, "4h"),
        "d1": (100, "1d"),
    }
    for suffix, (periods, frequency) in specifications.items():
        _constant_bars(end, periods, frequency).to_csv(
            live_root / f"goldsharp_{suffix}.csv",
            index=False,
        )

    first = runtime.run_live_once(live_root, output)
    second = runtime.run_live_once(live_root, output)
    assert first["status"] == "INITIALIZED_NO_BACKFILL"
    assert first["new_candidate_count"] == 0
    assert second["status"] == "PASS"
    assert second["new_candidate_count"] == 0
    registry = pd.read_csv(output / "live_candidates.csv")
    assert registry.empty
