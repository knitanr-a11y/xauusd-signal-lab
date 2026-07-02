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


def test_root_launcher_is_lightweight_and_keeps_a_pasteable_log() -> None:
    launcher = Path(__file__).resolve().parents[2] / "RUN_BTCUSD_HISTORY_EXPORT.bat"
    text = launcher.read_text(encoding="utf-8")

    assert "--start \"%START_DATE%\" --timeframes M15 H1 H4 D1" in text
    assert "M1 and M5 are intentionally excluded" in text
    assert "BTCUSD_HISTORY_LAST_LOG.txt" in text
    assert "BTCUSD_HISTORY_PASTE_THIS.txt" in text
    assert "pause" in text.lower()
    assert "Select-Object -Skip 1" in text
