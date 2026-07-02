from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "send_btc_youtube_mt5_orders.py"
spec = importlib.util.spec_from_file_location("send_btc_youtube_mt5_orders", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_normalize_volume_accepts_broker_step() -> None:
    assert module.normalize_volume(0.01, minimum=0.01, maximum=10.0, step=0.01) == 0.01
    assert module.normalize_volume(0.02, minimum=0.01, maximum=10.0, step=0.01) == 0.02


def test_position_guard_blocks_same_magic() -> None:
    errors = module.position_guard_errors(
        [{"magic": 26070441, "volume": 0.01}],
        requested_magic=26070441, requested_lot=0.01,
        max_positions=6, max_lot=0.10,
    )
    assert any("same active magic" in error for error in errors)


def test_position_guard_allows_other_magic_within_limits() -> None:
    errors = module.position_guard_errors(
        [{"magic": 999, "volume": 0.01}],
        requested_magic=26070441, requested_lot=0.01,
        max_positions=6, max_lot=0.10,
    )
    assert errors == []
