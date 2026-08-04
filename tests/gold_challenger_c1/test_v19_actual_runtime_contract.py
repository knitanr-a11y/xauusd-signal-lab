from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.gold_challenger_c1.v19_readonly import (
    EXPECTED_CONTRACT_VERSION,
    EXPECTED_SHADOW_ID,
    load_v19_view,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_actual_runtime(tmp_path: Path, *, cursor: str = "2026-07-31 11:45:00", accepted_trades: int = 0) -> dict:
    root = tmp_path / "v19_state"
    model = root / "models" / "2026-07-01"
    outputs = root / "outputs"
    model.mkdir(parents=True)
    outputs.mkdir(parents=True)

    calibration = pd.DataFrame(
        {
            "entry_time": pd.date_range("2026-06-01", periods=200, freq="h"),
            "score_long": np.linspace(0.10, 0.90, 200),
            "score_short": np.linspace(0.90, 0.10, 200),
        }
    )
    calibration.to_csv(model / "calibration_scores.csv.gz", index=False, compression="gzip")

    history = pd.DataFrame(
        {
            "entry_time": ["2026-07-31 11:30:00", "2026-07-31 11:45:00"],
            "origin_id": [82463, 82464],
            "score_long": [0.70, 0.80],
            "score_short": [0.40, 0.30],
            "model_boundary": ["2026-07-01", "2026-07-01"],
        }
    )
    history.to_csv(root / "score_history.csv.gz", index=False, compression="gzip")
    history.iloc[0:0].to_csv(root / "pending_scores.csv.gz", index=False, compression="gzip")

    counters = {"accepted_trades": accepted_trades}
    write_json(
        root / "runtime_state.json",
        {
            "shadow_id": EXPECTED_SHADOW_ID,
            "contract_version": EXPECTED_CONTRACT_VERSION,
            "activated": True,
            "last_processed_decision_time": cursor,
            "active_model_boundary": "2026-07-01T00:00:00",
            "open_trade": None,
            "counters": counters,
        },
    )
    write_json(
        root / "runtime_health.json",
        {
            "shadow_id": EXPECTED_SHADOW_ID,
            "contract_version": EXPECTED_CONTRACT_VERSION,
            "status": "RUNNING",
            "last_processed_decision_time": cursor,
            "active_model_boundary": "2026-07-01T00:00:00",
            "score_history_rows": 2,
            "pending_score_rows": 0,
            "counters": counters,
        },
    )
    config_path = tmp_path / "v19_config.json"
    write_json(
        config_path,
        {
            "shadow_id": EXPECTED_SHADOW_ID,
            "contract_version": EXPECTED_CONTRACT_VERSION,
            "state_dir": str(root),
            "data_sources": {},
            "discord": {},
        },
    )
    return {"v19": {"local_config_path": str(config_path)}}


def test_actual_v19_running_score_history_contract_is_ready(tmp_path: Path) -> None:
    result = load_v19_view(build_actual_runtime(tmp_path))
    assert result.ready
    assert result.status == "RUNNING"
    assert result.parity == "PASS"
    assert result.last_processed == pd.Timestamp("2026-07-31 11:45:00")
    assert result.details["score_source"] == "score_history.csv.gz+pending_scores.csv.gz"
    assert result.details["score_history_rows"] == 2
    assert result.details["pending_score_rows"] == 0
    assert result.score_ledger.chosen_side.isin(["LONG", "SHORT"]).all()
    assert result.score_ledger.chosen_rank.between(0.0, 1.0).all()


def test_actual_v19_cursor_mismatch_fails_closed(tmp_path: Path) -> None:
    result = load_v19_view(build_actual_runtime(tmp_path, cursor="2026-07-31 12:00:00"))
    assert not result.ready
    assert result.parity == "FAIL"
    assert result.details["invariants"]["score_cursor_match"] is False


def test_missing_trade_ledger_is_allowed_only_before_first_v19_trade(tmp_path: Path) -> None:
    result = load_v19_view(build_actual_runtime(tmp_path, accepted_trades=1))
    assert not result.ready
    assert result.details["invariants"]["trade_ledger_contract_ok"] is False
