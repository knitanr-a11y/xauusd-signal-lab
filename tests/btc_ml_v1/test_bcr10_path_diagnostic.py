from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR10_holding_rollover_path_diagnostic"
    / "python"
    / "run_bcr10_path_diagnostic.py"
)
spec = importlib.util.spec_from_file_location("bcr10", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_bins() -> None:
    assert [module.holding_bin(x) for x in [1, 4, 5, 8, 9, 16, 17, 32, 33, 64, 65, 128, 129]] == [
        "H01_04", "H01_04", "H05_08", "H05_08", "H09_16", "H09_16",
        "H17_32", "H17_32", "H33_64", "H33_64", "H65_128", "H65_128", "H129_PLUS",
    ]
    assert [module.crossing_bin(x) for x in [0, 1, 2, 3, 8]] == ["D0", "D1", "D2", "D3_PLUS", "D3_PLUS"]
    assert [module.hour_bin(x) for x in [0, 3, 4, 7, 8, 11, 12, 15, 16, 19, 20, 23]] == [
        "00_03", "00_03", "04_07", "04_07", "08_11", "08_11",
        "12_15", "12_15", "16_19", "16_19", "20_23", "20_23",
    ]


def _prices(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["server_open"] = pd.to_datetime(frame["server_open"])
    frame["spread_price"] = frame["spread"] * 0.01
    frame["entry_atr14"] = 100.0
    return frame.set_index("server_open")


def test_long_mfe_mae_excludes_exit_bar_high_low() -> None:
    prices = _prices([
        {"server_open": "2026-01-01 10:00", "open": 100, "high": 110, "low": 95, "spread": 1000},
        {"server_open": "2026-01-01 10:15", "open": 105, "high": 999, "low": 1, "spread": 1000},
    ])
    row = type("R", (), {
        "entry_server_open": "2026-01-01 10:00", "exit_server_open": "2026-01-01 10:15",
        "entry_open": 100, "entry_spread_price": 10, "direction": "LONG",
        "pnl_C0_OBSERVED_SPREAD": -5,
    })()
    result = module.path_metrics_for_trade(row, prices)
    assert result["mfe_c0_usd_1lot"] == 0
    assert result["mae_c0_usd_1lot"] == 15


def test_short_uses_contemporaneous_spread() -> None:
    prices = _prices([
        {"server_open": "2026-01-01 10:00", "open": 100, "high": 105, "low": 80, "spread": 2000},
        {"server_open": "2026-01-01 10:15", "open": 90, "high": 999, "low": 1, "spread": 3000},
    ])
    row = type("R", (), {
        "entry_server_open": "2026-01-01 10:00", "exit_server_open": "2026-01-01 10:15",
        "entry_open": 100, "entry_spread_price": 20, "direction": "SHORT",
        "pnl_C0_OBSERVED_SPREAD": -20,
    })()
    result = module.path_metrics_for_trade(row, prices)
    assert result["mfe_c0_usd_1lot"] == 0
    assert result["mae_c0_usd_1lot"] == 25


def test_gap_is_explicit_and_not_interpolated() -> None:
    prices = _prices([
        {"server_open": "2026-01-01 10:00", "open": 100, "high": 101, "low": 99, "spread": 1000},
        {"server_open": "2026-01-01 10:30", "open": 100, "high": 101, "low": 99, "spread": 1000},
    ])
    row = type("R", (), {
        "entry_server_open": "2026-01-01 10:00", "exit_server_open": "2026-01-01 10:30",
        "entry_open": 100, "entry_spread_price": 10, "direction": "LONG",
        "pnl_C0_OBSERVED_SPREAD": -10,
    })()
    result = module.path_metrics_for_trade(row, prices)
    assert result["path_complete"] is False
    assert result["missing_path_rows"] == 1
    assert "mfe_c0_usd_1lot" not in result
