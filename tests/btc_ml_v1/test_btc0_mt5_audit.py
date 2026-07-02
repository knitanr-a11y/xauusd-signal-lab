from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from collections import namedtuple
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/btc_ml_v1/broker_audit/btc0_mt5_audit.py"
)
spec = importlib.util.spec_from_file_location("btc0_mt5_audit", MODULE_PATH)
assert spec and spec.loader
btc0 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = btc0
spec.loader.exec_module(btc0)


Info = namedtuple(
    "Info",
    [
        "name",
        "description",
        "path",
        "currency_base",
        "currency_profit",
        "currency_margin",
        "digits",
        "point",
        "trade_contract_size",
        "volume_min",
        "volume_step",
        "volume_max",
        "trade_tick_size",
        "trade_tick_value",
        "trade_tick_value_profit",
        "trade_tick_value_loss",
        "spread",
        "spread_float",
        "trade_stops_level",
        "trade_freeze_level",
        "filling_mode",
        "trade_mode",
        "order_mode",
        "expiration_mode",
        "visible",
        "select",
    ],
)
Tick = namedtuple("Tick", ["time", "bid", "ask", "last"])
Terminal = namedtuple("Terminal", ["company", "name", "path"])
Account = namedtuple(
    "Account", ["login", "server", "company", "currency", "leverage", "trade_mode"]
)


def info(name: str, *, base: str = "BTC", trade_mode: int = 4) -> Info:
    return Info(
        name,
        "Bitcoin vs US Dollar" if base in {"BTC", "XBT"} else "Gold vs US Dollar",
        "Crypto\\Majors",
        base,
        "USD",
        "USD",
        2,
        0.01,
        1.0,
        0.01,
        0.01,
        100.0,
        0.01,
        0.01,
        0.01,
        0.01,
        25,
        True,
        0,
        0,
        1,
        trade_mode,
        127,
        15,
        True,
        True,
    )


def test_symbol_discovery_does_not_assume_btcusd() -> None:
    candidates = btc0.discover_btc_symbols(
        [info("GOLD#", base="XAU"), info("BTCUSD#"), info("XBTUSD.pro", base="XBT")]
    )
    assert set(candidates["name"]) == {"BTCUSD#", "XBTUSD.pro"}
    assert btc0.choose_symbol(candidates, None) is None
    assert btc0.choose_symbol(candidates, "xbtusd.pro") == "XBTUSD.pro"
    with pytest.raises(ValueError):
        btc0.choose_symbol(candidates, "BTCUSD")


def test_rates_frame_excludes_current_open_bar_and_deduplicates() -> None:
    raw = np.array(
        [
            (100, 1.0, 2),
            (200, 2.0, 3),
            (200, 2.1, 4),
            (300, 3.0, 5),
        ],
        dtype=[("time", "i8"), ("close", "f8"), ("spread", "i8")],
    )
    frame = btc0.rates_frame(raw)
    assert frame["time"].tolist() == [100, 200]
    assert frame.loc[1, "close"] == 2.1
    assert frame["time_utc"].dt.tz is not None


def test_spread_and_weekend_statistics_use_closed_m1_only() -> None:
    frame = pd.DataFrame(
        {
            "spread": [10, 20, 30, 40],
            "time_utc": pd.to_datetime(
                [
                    "2026-06-26 10:00:00+00:00",
                    "2026-06-27 10:00:00+00:00",
                    "2026-06-28 10:00:00+00:00",
                    "2026-06-29 10:00:00+00:00",
                ],
                utc=True,
            ),
        }
    )
    spread = btc0.spread_record("BTCUSD#", 0.01, frame)
    weekend = btc0.weekend_summary(frame)
    assert spread["spread_points_p50"] == 25.0
    assert spread["spread_price_p50"] == 0.25
    assert weekend == {"weekend_closed_m1_bars": 2, "weekend_trading_observed": True}


def test_existing_btc_csv_inventory_treats_latest_row_closed_by_contract(tmp_path: Path) -> None:
    csv = tmp_path / "btc_m15.csv"
    pd.DataFrame(
        {
            "time": ["2026-07-01 10:00:00", "2026-07-01 10:15:00"],
            "close": [100.0, 101.0],
        }
    ).to_csv(csv, index=False)
    inventory = btc0.audit_csv_files(tmp_path)
    assert len(inventory) == 1
    assert inventory.loc[0, "last_time"] == "2026-07-01 10:15:00"
    assert inventory.loc[0, "latest_row_contract"] == "CLOSED_BY_EXTERNAL_CSV_CONTRACT"


class FakeMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    ORDER_TYPE_BUY = 0

    def __init__(self) -> None:
        self.shutdown_called = False

    def initialize(self, *_args, **_kwargs):
        return True

    def shutdown(self):
        self.shutdown_called = True

    def last_error(self):
        return (0, "ok")

    def symbols_get(self):
        return (info("BTCUSD#"), info("GOLD#", base="XAU"))

    def symbol_select(self, _symbol, _enable):
        return True

    def symbol_info(self, symbol):
        assert symbol == "BTCUSD#"
        return info(symbol)

    def symbol_info_tick(self, _symbol):
        return Tick(1_750_000_000, 100_000.0, 100_025.0, 100_010.0)

    def copy_rates_from_pos(self, _symbol, _timeframe, _start, _count):
        return np.array(
            [
                (1_749_999_800, 100_000.0, 20),
                (1_749_999_860, 100_010.0, 25),
                (1_749_999_920, 100_020.0, 30),
            ],
            dtype=[("time", "i8"), ("close", "f8"), ("spread", "i8")],
        )

    def terminal_info(self):
        return Terminal("Broker", "Terminal", "C:/MT5")

    def account_info(self):
        return Account(12345678, "Broker-Server", "Broker", "USD", 100, 0)

    def order_calc_profit(self, _order_type, _symbol, volume, open_price, close_price):
        return (close_price - open_price) * volume


def test_full_audit_is_read_only_and_uses_separate_btc_output(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    output = tmp_path / "outputs" / "btc_ml_v1" / "btc0_broker_data_audit"
    args = Namespace(
        symbol=None,
        output_dir=str(output),
        csv_root=str(tmp_path / "Files"),
        history_bars=100,
        terminal_path=None,
        login=None,
        password=None,
        server=None,
    )
    payload = btc0.run_audit(mt5, args)
    assert payload["selected_symbol"] == "BTCUSD#"
    assert payload["read_only"] is True
    assert payload["orders_enabled"] is False
    assert payload["live_ready"] is False
    assert payload["discord_enabled"] is False
    assert mt5.shutdown_called is True
    assert (output / "btc0_broker_contract.json").is_file()
    history = pd.read_csv(output / "history_depth.csv")
    assert set(history["timeframe"]) == set(btc0.TIMEFRAME_NAMES)
    assert history["closed_rows"].eq(2).all()
