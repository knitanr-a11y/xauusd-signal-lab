from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd


def live_script_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "scripts/gold_ml_v1/live_research_challenger"
    )


def import_live(name: str):
    path = str(live_script_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


archive = import_live("live_feature_archive")


def test_feature_index_joins_entry_snapshot_with_resolved_trade(tmp_path: Path) -> None:
    output = tmp_path / "output"
    registry = pd.DataFrame(
        [
            {
                "candidate_key": "candidate-1",
                "candidate_id": "GML1-WATCH-022-C",
                "comp": "A_CORE",
                "direction": "LONG",
                "decision_time": "2026-07-01 10:00:00",
                "source_timeframe": "M15",
                "higher_timeframe": "H4",
                "atr": 10.0,
                "target_r": 1.0,
                "horizon_hours": 6,
                "entry_price": 3300.0,
                "stop_price": 3290.0,
                "target_price": 3310.0,
                "features_json": '{"bb_break":true,"atr_ratio":1.25}',
            }
        ]
    )
    operational = pd.DataFrame(
        [
            {
                "candidate_key": "candidate-1",
                "fill_price": 3300.5,
                "stop_price": 3290.5,
                "target_price": 3310.5,
                "execution_status": "CLOSED_BY_SL_TP_OR_MANUAL",
                "trade_state": "CLOSED",
                "live_result": "LOSS",
                "closed_at": "2026-07-01 12:00:00",
                "close_reason": "SL",
                "close_price": 3290.5,
                "net_profit": -12.5,
            }
        ]
    )

    result = archive.update_trade_feature_index(
        output,
        registry=registry,
        operational=operational,
        now_text="2026-07-01 12:01:00",
    )
    row = result.iloc[0]
    assert row["features_json"] == '{"bb_break":true,"atr_ratio":1.25}'
    assert row["entry_feature_snapshot_source"] == (
        "LIVE_CANDIDATE_REGISTRY_CLOSED_ENTRY_TIME"
    )
    assert row["live_result"] == "LOSS"
    assert row["close_reason"] == "SL"
    assert row["net_profit"] == "-12.5"
    assert (output / "trades" / "trade_feature_index.csv").is_file()


def test_existing_feature_index_first_timestamp_is_preserved(tmp_path: Path) -> None:
    output = tmp_path / "output"
    path = output / "trades" / "trade_feature_index.csv"
    path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                **{column: "" for column in archive.FEATURE_INDEX_COLUMNS},
                "candidate_key": "candidate-1",
                "features_json": '{"old":true}',
                "first_recorded_at": "2026-07-01 10:00:00",
                "last_recorded_at": "2026-07-01 10:00:00",
            }
        ],
        columns=archive.FEATURE_INDEX_COLUMNS,
    ).to_csv(path, index=False)

    registry = pd.DataFrame(
        [
            {
                "candidate_key": "candidate-1",
                "features_json": '{"entry":true}',
            }
        ]
    )
    updated = archive.update_trade_feature_index(
        output,
        registry=registry,
        operational=pd.DataFrame(),
        now_text="2026-07-02 10:00:00",
    )
    assert updated.loc[0, "first_recorded_at"] == "2026-07-01 10:00:00"
    assert updated.loc[0, "last_recorded_at"] == "2026-07-02 10:00:00"
    assert updated.loc[0, "features_json"] == '{"entry":true}'
