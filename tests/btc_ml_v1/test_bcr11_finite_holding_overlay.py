from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/btc_ml_v1/BCR11_finite_causal_holding_overlay/python/run_bcr11_finite_holding_overlay.py"
BCR09 = ROOT / "scripts/btc_ml_v1/BCR09_shared_retrospective_value_gate/python/run_bcr09_shared_value_gate.py"
os.environ["BCR09_REPRODUCER_PATH"] = str(BCR09)
spec = importlib.util.spec_from_file_location("bcr11", SCRIPT)
assert spec and spec.loader
bcr11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcr11)


def row(**kwargs):
    values = dict(
        common_eligible=False,
        p_close=100.0,
        p_ema20=100.0,
        p_atr14=10.0,
        p_ret1_bps=0.0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_theoretical_age_uses_fifteen_minute_boundaries():
    entry = pd.Timestamp("2026-01-01 00:00:00")
    assert bcr11.age(entry, pd.Timestamp("2026-01-01 04:00:00")) == 16
    assert bcr11.age(entry, pd.Timestamp("2026-01-01 04:15:00")) == 17


def test_missing_2345_is_explicit_and_not_substituted():
    entry = pd.Timestamp("2026-01-01 22:00:00")
    end = pd.Timestamp("2026-01-02 00:15:00")
    assert bcr11.missing_2345(entry, end, {entry, end}) == 1


def test_b4_entry_and_exit_predicates_remain_frozen():
    long_entry = row(common_eligible=True, p_close=84.0, p_ema20=100.0, p_atr14=10.0, p_ret1_bps=1.0)
    short_entry = row(common_eligible=True, p_close=111.0, p_ema20=100.0, p_atr14=10.0, p_ret1_bps=-1.0)
    assert bcr11.b4_entry(long_entry) == "LONG"
    assert bcr11.b4_entry(short_entry) == "SHORT"
    assert bcr11.b4_exit(row(common_eligible=True, p_close=100.0, p_ema20=100.0, p_atr14=10.0), "LONG", "E0")
    assert bcr11.b4_exit(row(common_eligible=True, p_close=97.5, p_ema20=100.0, p_atr14=10.0), "LONG", "E1")


def test_overlay_inventory_is_exactly_six():
    assert list(bcr11.OVERLAYS) == [
        "O0_BASELINE",
        "O1_MAX_HOLD_16",
        "O2_MAX_HOLD_32",
        "O3_MAX_HOLD_64",
        "O4_SERVER_DAY_FLAT_2345",
        "O5_MAX_HOLD_16_AND_SERVER_DAY_FLAT_2345",
    ]
