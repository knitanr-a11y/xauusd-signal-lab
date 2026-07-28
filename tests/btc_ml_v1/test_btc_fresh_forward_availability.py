from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "btc_ml_v1"
    / "fresh_forward_availability"
    / "python"
    / "audit_btc_fresh_forward_availability.py"
)
spec = importlib.util.spec_from_file_location("audit_btc_fresh_forward_availability", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def selected_fresh_rows() -> dict[str, dict[str, object]]:
    return {
        timeframe: {
            "rows_after_cutoff_utc": 1,
            "read_error": "",
            "latest_closed_time_utc": "2026-07-03 00:00:00",
        }
        for timeframe in module.TFS
    }


def test_btc4_fresh_readiness_does_not_require_2017_warmup() -> None:
    result = module.fresh_readiness(selected_fresh_rows())
    assert result["BTC4_RISK_CAP_400"]["status"] == "READY"
    assert set(result["BTC4_RISK_CAP_400"]["requirements"]) == {
        "H4_AFTER_CUTOFF",
        "M5_AFTER_CUTOFF",
    }
    assert all(value["status"] == "READY" for value in result.values())


def test_missing_2017_h4_is_informational_only() -> None:
    context = module.historical_reproduction_context(
        [
            {
                "path": "current_h4.csv",
                "read_error": "",
                "first_time_broker_server": "2021-12-13 00:00:00",
            }
        ]
    )
    assert context["status"] == "NOT_PRESENT_INFORMATIONAL"
    assert context["required_for_fresh_forward_availability"] is False
    assert context["required_for_exact_historical_reproduction"] is True


def test_2017_h4_is_recognized_only_as_historical_context() -> None:
    context = module.historical_reproduction_context(
        [
            {
                "path": "historical_warmup_h4.csv",
                "read_error": "",
                "first_time_broker_server": "2017-01-02 04:00:00",
            }
        ]
    )
    assert context["status"] == "AVAILABLE"
    assert context["selected_path"] == "historical_warmup_h4.csv"
    assert context["required_for_fresh_forward_availability"] is False
