from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/btc_ml_v1/data_history/export_btcusdsharp_history.py"
)
spec = importlib.util.spec_from_file_location("export_btcusdsharp_history", MODULE_PATH)
assert spec and spec.loader
exporter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = exporter
spec.loader.exec_module(exporter)


SymbolInfo = namedtuple(
    "SymbolInfo",
    [
        "name",
        "description",
        "visible",
        "digits",
        "point",
        "trade_contract_size",
        "volume_min",
        "volume_step",
        "volume_max",
        "trade_tick_size",
        "trade_tick_value",
        "spread",
        "spread_float",
        "trade_stops_level",
        "filling_mode",
        "trade_mode",
    ],
)
TerminalInfo = namedtuple("TerminalInfo", ["company", "name", "maxbars"])
AccountInfo = namedtuple("AccountInfo", ["login", "server", "company", "currency"])


RATE_DTYPE = [
    ("time", "i8"),
    ("open", "f8"),
    ("high", "f8"),
    ("low", "f8"),
    ("close", "f8"),
    ("tick_volume", "i8"),
    ("spread", "i8"),
    ("real_volume", "i8"),
]


def rate(epoch: int, price: float) -> tuple:
    return (epoch, price, price + 2, price - 2, price + 1, 10, 25, 0)


class FakeMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440

    def __init__(self, bars: dict[int, np.ndarray]) -> None:
        self.bars = bars
        self.shutdown_called = False
        self.copy_calls = 0

    def initialize(self, *_args, **_kwargs):
        return True

    def shutdown(self):
        self.shutdown_called = True

    def last_error(self):
        return (0, "ok")

    def symbol_info(self, symbol):
        if symbol != "BTCUSD#":
            return None
        return SymbolInfo(
            "BTCUSD#",
            "Bitcoin vs US Dollar",
            True,
            2,
            0.01,
            1.0,
            0.01,
            0.01,
            100.0,
            0.01,
            0.01,
            25,
            True,
            0,
            1,
            4,
        )

    def symbol_select(self, _symbol, _enabled):
        return True

    def copy_rates_range(self, _symbol, timeframe, date_from, date_to):
        self.copy_calls += 1
        source = self.bars.get(timeframe, np.array([], dtype=RATE_DTYPE))
        start = int(date_from.timestamp())
        end = int(date_to.timestamp())
        return source[(source["time"] >= start) & (source["time"] <= end)]

    def terminal_info(self):
        return TerminalInfo("Broker", "MT5", 10_000_000)

    def account_info(self):
        return AccountInfo(12345678, "Broker-Server", "Broker", "USD")


def args(output: Path, *, timeframes: list[str] | None = None) -> Namespace:
    return Namespace(
        output_dir=str(output),
        start="2026-01-01T00:00:00+00:00",
        end="2026-01-01T00:05:30+00:00",
        timeframes=timeframes or ["M1"],
        terminal_path=None,
        login=None,
        password=None,
        server=None,
    )


def test_closed_rows_exclude_current_open_bar() -> None:
    start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    raw = np.array([rate(start + 60 * index, 100 + index) for index in range(4)], dtype=RATE_DTYPE)
    rows = exporter._closed_rows(
        raw,
        timeframe_seconds=60,
        snapshot_utc=datetime(2026, 1, 1, 0, 3, 30, tzinfo=timezone.utc),
    )
    assert [row[0] for row in rows] == [start, start + 60, start + 120]


def test_full_export_stages_then_backs_up_existing_files(tmp_path: Path) -> None:
    output = tmp_path / "Files"
    output.mkdir()
    old_path = output / "btcusdsharp_m1.csv"
    old_path.write_text("time,open\nold,1\n", encoding="utf-8")

    start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    bars = np.array(
        [rate(start + 60 * index, 100_000 + index) for index in range(7)],
        dtype=RATE_DTYPE,
    )
    mt5 = FakeMT5({FakeMT5.TIMEFRAME_M1: bars})
    manifest = exporter.run_export(mt5, args(output))

    assert manifest["symbol"] == "BTCUSD#"
    assert manifest["orders_enabled"] is False
    assert manifest["discord_enabled"] is False
    assert manifest["live_ready"] is False
    assert manifest["final_signal"] is False
    assert manifest["latest_row_contract"] == "CLOSED_ONLY"
    assert mt5.shutdown_called is True

    exported = pd.read_csv(old_path)
    assert list(exported.columns) == exporter.CSV_COLUMNS
    assert len(exported) == 5
    assert exported.iloc[-1]["time"] == "2026-01-01 00:04:00"

    backup = Path(manifest["backup_dir"])
    assert backup.is_dir()
    assert (backup / "btcusdsharp_m1.csv").read_text(encoding="utf-8") == (
        "time,open\nold,1\n"
    )
    assert (output / "btcusdsharp_history_manifest.json").is_file()
    assert not (output / "btcusdsharp_history_export.lock").exists()
    assert not list(output.glob(".btcusdsharp_stage_*"))


def test_exact_symbol_is_required(tmp_path: Path) -> None:
    class MissingSymbolMT5(FakeMT5):
        def symbol_info(self, _symbol):
            return None

    mt5 = MissingSymbolMT5({})
    try:
        exporter.run_export(mt5, args(tmp_path / "Files"))
    except RuntimeError as exc:
        assert "BTCUSD#" in str(exc)
    else:
        raise AssertionError("missing exact symbol must fail")
    assert mt5.shutdown_called is True
