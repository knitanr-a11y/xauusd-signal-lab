from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mochipoyo_alert_research" / "collect_events_once.py"

spec = importlib.util.spec_from_file_location("mochipoyo_collect_events_once", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_worker_rows_response_is_accepted() -> None:
    rows = [{"id": 1}, {"id": 2}]
    events, metadata = module.extract_events(
        {"ok": True, "rows": rows, "latest_id": 2}
    )
    assert events == rows
    assert metadata == {"ok": True, "latest_id": 2}


def test_ok_false_still_fails_closed() -> None:
    try:
        module.extract_events({"ok": False, "rows": [], "error": "denied"})
    except ValueError as exc:
        assert "ok=false" in str(exc)
    else:
        raise AssertionError("ok=false response must fail closed")
