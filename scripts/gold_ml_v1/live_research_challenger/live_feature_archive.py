from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from live_store import atomic_write_csv

FEATURE_INDEX_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "direction",
    "decision_time",
    "source_timeframe",
    "higher_timeframe",
    "atr",
    "target_r",
    "horizon_hours",
    "entry_price",
    "fill_price",
    "stop_price",
    "target_price",
    "features_json",
    "strategy_name",
    "signal_reason",
    "higher_timeframe_context",
    "execution_status",
    "trade_state",
    "live_result",
    "closed_at",
    "close_reason",
    "close_price",
    "net_profit",
    "entry_feature_snapshot_source",
    "first_recorded_at",
    "last_recorded_at",
]

ENTRY_COLUMNS = [
    "candidate_id",
    "comp",
    "direction",
    "decision_time",
    "source_timeframe",
    "higher_timeframe",
    "atr",
    "target_r",
    "horizon_hours",
    "entry_price",
    "stop_price",
    "target_price",
    "features_json",
    "strategy_name",
    "signal_reason",
    "higher_timeframe_context",
]

EXECUTION_COLUMNS = [
    "fill_price",
    "stop_price",
    "target_price",
    "execution_status",
    "trade_state",
    "live_result",
    "closed_at",
    "close_reason",
    "close_price",
    "net_profit",
]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=object)


def _archived_execution_rows(output_dir: Path) -> pd.DataFrame:
    paths = sorted((output_dir / "trades").glob("*/live_trades_*.csv"))
    frames = [_read_csv(path) for path in paths]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _execution_rows(output_dir: Path, operational: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    archived = _archived_execution_rows(output_dir)
    if not archived.empty:
        frames.append(archived)
    if not operational.empty:
        frames.append(operational.copy())
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    if "candidate_key" not in combined.columns:
        return pd.DataFrame()
    return combined.drop_duplicates("candidate_key", keep="last").reset_index(drop=True)


def update_trade_feature_index(
    output_dir: Path,
    *,
    registry: pd.DataFrame,
    operational: pd.DataFrame,
    now_text: str,
) -> pd.DataFrame:
    """Persist entry-time feature snapshots separately from live decisions.

    The snapshot is copied from live_candidates.csv, where it was created from
    closed information at candidate admission. Resolved execution fields are
    joined only for later audit/AI evaluation and are never fed back into live
    candidate selection or order gating.
    """

    path = output_dir / "trades" / "trade_feature_index.csv"
    existing = _read_csv(path)
    execution = _execution_rows(output_dir, operational)

    registry_by_key = (
        registry.drop_duplicates("candidate_key", keep="last").set_index("candidate_key")
        if not registry.empty and "candidate_key" in registry.columns
        else pd.DataFrame()
    )
    execution_by_key = (
        execution.set_index("candidate_key")
        if not execution.empty and "candidate_key" in execution.columns
        else pd.DataFrame()
    )
    existing_by_key = (
        existing.drop_duplicates("candidate_key", keep="last").set_index("candidate_key")
        if not existing.empty and "candidate_key" in existing.columns
        else pd.DataFrame()
    )

    keys: set[str] = set()
    for frame in (registry_by_key, execution_by_key, existing_by_key):
        if not frame.empty:
            keys.update(str(value) for value in frame.index)

    rows: list[dict[str, Any]] = []
    for key in sorted(keys):
        entry = registry_by_key.loc[key] if not registry_by_key.empty and key in registry_by_key.index else None
        execution_row = (
            execution_by_key.loc[key]
            if not execution_by_key.empty and key in execution_by_key.index
            else None
        )
        old = existing_by_key.loc[key] if not existing_by_key.empty and key in existing_by_key.index else None
        record = {column: "" for column in FEATURE_INDEX_COLUMNS}
        record["candidate_key"] = key
        if old is not None:
            for column in FEATURE_INDEX_COLUMNS:
                if column in old.index:
                    record[column] = _text(old.get(column))
        if entry is not None:
            for column in ENTRY_COLUMNS:
                if column in entry.index:
                    record[column] = _text(entry.get(column))
            record["entry_feature_snapshot_source"] = (
                "LIVE_CANDIDATE_REGISTRY_CLOSED_ENTRY_TIME"
            )
        if execution_row is not None:
            for column in EXECUTION_COLUMNS:
                if column in execution_row.index:
                    value = _text(execution_row.get(column))
                    if value:
                        record[column] = value
            for column in ("candidate_id", "comp", "direction", "decision_time"):
                if not record[column] and column in execution_row.index:
                    record[column] = _text(execution_row.get(column))
        record["first_recorded_at"] = record["first_recorded_at"] or now_text
        record["last_recorded_at"] = now_text
        rows.append(record)

    updated = pd.DataFrame(rows, columns=FEATURE_INDEX_COLUMNS)
    atomic_write_csv(path, updated)
    return updated
