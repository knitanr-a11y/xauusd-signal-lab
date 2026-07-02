from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_btc_youtube_positions.py"
spec = importlib.util.spec_from_file_location("manage_btc_youtube_positions", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_waits_while_both_legs_open() -> None:
    assert module.plan_pair_action(
        pair_status="ARMED", tp1_open=True, tp2_open=True,
        tp1_profitably_closed=False, tp2_sl_at_be=False,
    ) == "WAIT_TP1"


def test_moves_tp2_only_after_profitable_tp1_close() -> None:
    assert module.plan_pair_action(
        pair_status="ARMED", tp1_open=False, tp2_open=True,
        tp1_profitably_closed=True, tp2_sl_at_be=False,
    ) == "MOVE_TP2_TO_BE"
    assert module.plan_pair_action(
        pair_status="ARMED", tp1_open=False, tp2_open=True,
        tp1_profitably_closed=False, tp2_sl_at_be=False,
    ) == "WAIT_TP1_CLOSE_CONFIRMATION"


def test_detects_missing_tp2_anomaly() -> None:
    assert module.plan_pair_action(
        pair_status="ARMED", tp1_open=True, tp2_open=False,
        tp1_profitably_closed=False, tp2_sl_at_be=False,
    ) == "ANOMALY_TP2_MISSING"
