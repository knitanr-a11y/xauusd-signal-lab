from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REGISTRY_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "decision_time",
    "direction",
    "source_timeframe",
    "higher_timeframe",
    "atr",
    "target_r",
    "horizon_hours",
    "entry_price",
    "stop_price",
    "target_price",
    "position_state",
    "outcome",
    "exit_time",
    "exit_price",
    "r",
    "current_price",
    "current_r",
    "features_json",
    "first_seen_at",
    "last_updated_at",
]
DYNAMIC_COLUMNS = [
    "position_state",
    "outcome",
    "exit_time",
    "exit_price",
    "r",
    "current_price",
    "current_r",
    "last_updated_at",
]


class DeferredRun(RuntimeError):
    pass


def json_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is None or pd.isna(value):
        return None
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported state schema: {payload.get('schema_version')}")
    return payload


def load_registry(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    frame = pd.read_csv(path)
    missing = [column for column in REGISTRY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Live registry missing columns: {missing}")
    if frame["candidate_key"].duplicated().any():
        raise ValueError("Live registry contains duplicate candidate_key values")
    return frame[REGISTRY_COLUMNS].copy()


def position_from_state(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {
        "decision_time": pd.Timestamp(payload["decision_time"]),
        "atr": float(payload["atr"]),
        "candidate_key": payload.get("candidate_key"),
    }


def position_to_state(position: dict[str, Any] | None) -> dict[str, Any] | None:
    if position is None:
        return None
    return {
        "decision_time": pd.Timestamp(position["decision_time"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "atr": float(position["atr"]),
        "candidate_key": position.get("candidate_key"),
    }


def merge_registry(
    existing: pd.DataFrame,
    new_records: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    registry = existing.copy()
    if not registry.empty:
        registry = registry.set_index("candidate_key", drop=False)
        for update in updates:
            key = update["candidate_key"]
            if key in registry.index:
                for column in DYNAMIC_COLUMNS:
                    registry.loc[key, column] = update[column]
        registry = registry.reset_index(drop=True)

    new = pd.DataFrame(new_records, columns=REGISTRY_COLUMNS)
    if not new.empty:
        if new["candidate_key"].duplicated().any():
            raise ValueError("Current run produced duplicate candidate keys")
        existing_keys = set(registry["candidate_key"]) if not registry.empty else set()
        duplicate = sorted(set(new["candidate_key"]) & existing_keys)
        if duplicate:
            raise ValueError(f"Candidate keys already exist in registry: {duplicate[:10]}")
        registry = new if registry.empty else pd.concat([registry, new], ignore_index=True)

    if registry.empty:
        registry = pd.DataFrame(columns=REGISTRY_COLUMNS)
    else:
        registry = registry[REGISTRY_COLUMNS].sort_values(
            ["decision_time", "comp", "candidate_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    return registry, new
