from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "gold_ml_v1"
    / "prospective"
    / "prov020_fresh_filter_activation_monitor.py"
)
SPEC = importlib.util.spec_from_file_location("prov020_monitor", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "monitor_id": "TEST-PROV020",
                "audit_only": True,
                "candidate_id": "GML1-PROV-020",
                "parent_candidate_id": "GML1-PROV-015",
                "fresh_cutoff_mt5_server_close": "2026-06-23 18:15:00",
                "filter_conditions": [
                    {"feature": "HOUR", "lower": 8, "upper": 16},
                    {"feature": "SPREAD", "threshold": 0.03},
                ],
                "column_aliases": {},
                "boundaries": {
                    "live_signal": False,
                    "final_signal": False,
                    "mt5_order": False,
                    "discord": False,
                    "portfolio_activation": False,
                    "candidate_promotion": False,
                    "threshold_retuning": False,
                    "2026_diagnostic_only": True,
                    "future_outcomes_forbidden": True,
                },
            }
        ),
        encoding="utf-8",
    )


def run_monitor(tmp_path: Path, frame: pd.DataFrame):
    config = tmp_path / "config.json"
    write_config(config)
    events = tmp_path / "events.csv"
    frame.to_csv(events, index=False)
    args = argparse.Namespace(
        config=config,
        parent_events=events,
        ledger=tmp_path / "ledger.jsonl",
        summary=tmp_path / "summary.json",
    )
    MODULE.run(args)
    return args


def test_cutoff_and_activation_are_entry_time_only(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "decision_close_time": [
                "2026-06-23 18:15:00",
                "2026-06-24 10:00:00",
                "2026-06-24 17:00:00",
            ],
            "h1_spread_price_div_atr14": [0.99, 0.04, 0.04],
            "r_value": [-99.0, 99.0, -99.0],
            "exit_time": ["2099-01-01"] * 3,
        }
    )
    args = run_monitor(tmp_path, frame)
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    assert summary["fresh_parent_events"] == 2
    assert summary["fresh_filter_activations"] == 1
    assert summary["fresh_expected_prov020_emits"] == 1
    assert summary["forbidden_future_outcome_columns_used"] == []
    records = [json.loads(line) for line in args.ledger.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert all("r_value" not in row and "exit_time" not in row for row in records)


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "decision_close_time": ["2026-06-24 10:00:00"],
            "h1_spread_price_div_atr14": [0.04],
        }
    )
    args = run_monitor(tmp_path, frame)
    MODULE.run(args)
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    assert summary["new_ledger_records"] == 0
    assert summary["unchanged_existing_records"] == 1
    assert len(args.ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_hour_crosscheck_fails_closed(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    write_config(config)
    events = tmp_path / "events.csv"
    pd.DataFrame(
        {
            "decision_close_time": ["2026-06-24 10:00:00"],
            "h1_decision_close_server_hour": [11],
            "h1_spread_price_div_atr14": [0.04],
        }
    ).to_csv(events, index=False)
    try:
        MODULE.load_parent_events(events, json.loads(config.read_text()))
    except ValueError as exc:
        assert "server-hour mismatch" in str(exc)
    else:
        raise AssertionError("hour mismatch must fail closed")
