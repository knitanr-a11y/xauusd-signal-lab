from __future__ import annotations

import importlib
import sys
from pathlib import Path


def script_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/data_history"


def import_runner():
    path = str(script_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module("run_btcusdsharp_history")


def import_packager():
    path = str(script_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module("build_btcusd_chat_package")


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


def test_chat_package_defaults_keep_m1_short_and_m5_long() -> None:
    packager = import_packager()
    args = packager.parse_args([])

    assert args.m1_days == 90
    assert args.m5_days == 730
    assert args.core_days == 730
    assert args.package == "BTCUSD_HISTORY_CHAT_PACKAGE.zip"
    assert packager.TIMEFRAME_ORDER == ("M1", "M5", "M15", "H1", "H4", "D1")


def test_root_launcher_builds_one_zip_and_keeps_a_pasteable_log() -> None:
    launcher = Path(__file__).resolve().parents[2] / "RUN_BTCUSD_HISTORY_EXPORT.bat"
    text = launcher.read_text(encoding="utf-8")

    assert "build_btcusd_chat_package.py" in text
    assert "M1: latest 90 days" in text
    assert "M5: latest 730 days" in text
    assert "BTCUSD_HISTORY_CHAT_PACKAGE.zip" in text
    assert "BTCUSD_HISTORY_LAST_LOG.txt" in text
    assert "BTCUSD_HISTORY_PASTE_THIS.txt" in text
    assert "temporary CSV files will be deleted" in text
    assert "pause" in text.lower()
