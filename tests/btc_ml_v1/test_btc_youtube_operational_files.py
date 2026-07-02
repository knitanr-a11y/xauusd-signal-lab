from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_btc_youtube_candidates_operational_forever.py"
spec = importlib.util.spec_from_file_location("run_btc_youtube_candidates_operational_forever", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_candle(path: Path) -> None:
    path.write_text("time,open,high,low,close\n2026-07-03 00:00:00,1,1,1,1\n", encoding="utf-8")


def test_resolve_exact_files(tmp_path: Path) -> None:
    for name in ["btcusdsharp_m5.csv", "btcusdsharp_m15.csv", "btcusdsharp_h4.csv"]:
        write_candle(tmp_path / name)
    assert module.resolve_live_csv(tmp_path, "m5").name == "btcusdsharp_m5.csv"
    assert module.resolve_live_csv(tmp_path, "m15").name == "btcusdsharp_m15.csv"
    assert module.resolve_live_csv(tmp_path, "h4").name == "btcusdsharp_h4.csv"


def test_resolve_case_and_alias_files(tmp_path: Path) -> None:
    write_candle(tmp_path / "BTCUSDSharp_M5.CSV")
    write_candle(tmp_path / "btcusdsharp_15m.csv")
    write_candle(tmp_path / "btcusdsharp_240.csv")
    assert module.resolve_live_csv(tmp_path, "m5").name == "BTCUSDSharp_M5.CSV"
    assert module.resolve_live_csv(tmp_path, "m15").name == "btcusdsharp_15m.csv"
    assert module.resolve_live_csv(tmp_path, "h4").name == "btcusdsharp_240.csv"


def test_ambiguous_alias_timeframe_is_rejected(tmp_path: Path) -> None:
    write_candle(tmp_path / "btcusdsharp_5m.csv")
    write_candle(tmp_path / "btcusdsharp_5min.csv")
    with pytest.raises(RuntimeError, match="Multiple m5 CSV files matched"):
        module.resolve_live_csv(tmp_path, "m5")


def test_once_command_receives_resolved_csv_paths(tmp_path: Path) -> None:
    resolved = {
        "m5": tmp_path / "btcusdsharp_5m.csv",
        "m15": tmp_path / "btcusdsharp_15m.csv",
        "h4": tmp_path / "btcusdsharp_240.csv",
    }
    args = argparse.Namespace(
        files_dir=tmp_path,
        state_dir=tmp_path / "state",
        broker_symbol="BTCUSD#",
        expected_login=75539039,
        deviation=100,
        max_symbol_positions=6,
        max_symbol_lot=0.10,
        discord_webhook_env="DISCORD_WEBHOOK_URL",
        discord_username="test",
        discord_webhook_url="",
        send=False,
        allow_demo_send=False,
    )
    command = module.once_command(args, tmp_path / "out", resolved)
    assert command[command.index("--m5-csv") + 1] == str(resolved["m5"])
    assert command[command.index("--m15-csv") + 1] == str(resolved["m15"])
    assert command[command.index("--h4-csv") + 1] == str(resolved["h4"])
