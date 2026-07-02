from __future__ import annotations

import importlib
import sys
from pathlib import Path


def script_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/data_history"


def _import(name: str):
    path = str(script_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


def import_runner():
    return _import("run_btcusdsharp_history")


def import_packager():
    return _import("build_btcusd_chat_package")


def import_h4_packager():
    return _import("build_btcusd_h4_warmup_package")


def test_failed_run_cleanup_removes_only_current_process_stage(tmp_path: Path) -> None:
    runner = import_runner()
    lock = tmp_path / "btcusdsharp_history_export.lock"
    lock.write_text("test", encoding="utf-8")
    current = tmp_path / f".btcusdsharp_stage_test_{runner.os.getpid()}"
    other = tmp_path / ".btcusdsharp_stage_test_999999"
    current.mkdir()
    other.mkdir()

    runner._cleanup_failed_run(tmp_path)

    assert not lock.exists()
    assert not current.exists()
    assert other.exists()


def test_chat_package_defaults_keep_execution_short_and_h4_warmup_long() -> None:
    packager = import_packager()
    args = packager.parse_args([])

    assert args.m1_days == 90
    assert args.m5_days == 730
    assert args.core_days == 730
    assert args.higher_start == "2017-01-01"
    assert args.package == "BTCUSD_HISTORY_CHAT_PACKAGE.zip"
    assert packager.TIMEFRAME_ORDER == ("M1", "M5", "M15", "H1", "H4", "D1")


def test_h4_only_packager_is_small_and_starts_in_2017() -> None:
    packager = import_h4_packager()
    args = packager.parse_args([])

    assert args.start == "2017-01-01"
    assert args.package == "BTCUSD_H4_WARMUP_PACKAGE.zip"
    assert args.summary == "BTCUSD_H4_WARMUP_PASTE_THIS.txt"


def test_root_launcher_builds_one_zip_with_long_h4_history() -> None:
    launcher = Path(__file__).resolve().parents[2] / "RUN_BTCUSD_HISTORY_EXPORT.bat"
    text = launcher.read_text(encoding="utf-8")

    assert "build_btcusd_chat_package.py" in text
    assert "M1: latest 90 days" in text
    assert "M5: latest 730 days" in text
    assert "M15 H1: latest 730 days" in text
    assert "H4 D1: from 2017-01-01" in text
    assert "MT5 EMA warm-up" in text
    assert "BTCUSD_HISTORY_CHAT_PACKAGE.zip" in text
    assert "BTCUSD_HISTORY_LAST_LOG.txt" in text
    assert "BTCUSD_HISTORY_PASTE_THIS.txt" in text
    assert "temporary CSV files will be deleted" in text
    assert "pause" in text.lower()


def test_h4_warmup_launcher_exports_only_h4() -> None:
    launcher = Path(__file__).resolve().parents[2] / "RUN_BTCUSD_H4_WARMUP_EXPORT.bat"
    text = launcher.read_text(encoding="utf-8")

    assert "build_btcusd_h4_warmup_package.py" in text
    assert "Only H4 from 2017-01-01" in text
    assert "BTCUSD_H4_WARMUP_PACKAGE.zip" in text
    assert "BTCUSD_H4_WARMUP_LAST_LOG.txt" in text
    assert "pause" in text.lower()
