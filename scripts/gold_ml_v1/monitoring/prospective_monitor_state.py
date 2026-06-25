from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CANONICAL_BAR_COLUMNS = [
    "bar_open_time",
    "bar_close_time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]

CANDIDATE_KEY_COLUMNS = ["candidate_id", "decision_close_time"]
PARENT_KEY_COLUMNS = ["parent_lineage", "decision_close_time"]

CANDIDATE_DYNAMIC_COLUMNS = {
    "prospective_state",
    "resolution_state",
    "outcome",
    "exit_time",
    "exit_price",
    "r_value",
    "current_price",
    "current_r",
    "latest_observed_close_time",
}

PARENT_DYNAMIC_COLUMNS = CANDIDATE_DYNAMIC_COLUMNS | {
    "admission_state",
    "suppression_until",
}

TIMESTAMP_COLUMNS = {
    "bar_open_time",
    "bar_close_time",
    "decision_close_time",
    "entry_time",
    "exit_time",
    "horizon_end_time",
    "latest_observed_close_time",
    "suppression_until",
    "run_time_local",
    "previous_latest_m1_close",
    "latest_m1_close",
}

REQUIRED_STATE_FILES = [
    "monitor_candidate_ledger.csv",
    "monitor_parent_event_ledger.csv",
    "monitor_run_history.csv",
]


def _canonical_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not np.isfinite(number):
            return ""
        return format(number, ".17g")
    return str(value)


def canonical_bar_hash(frame: pd.DataFrame, row_count: int | None = None) -> str:
    if row_count is not None:
        frame = frame.iloc[:row_count]
    missing = [column for column in CANONICAL_BAR_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Canonical bar hash missing columns: {missing}")
    digest = hashlib.sha256()
    digest.update(("|".join(CANONICAL_BAR_COLUMNS) + "\n").encode("utf-8"))
    for row in frame[CANONICAL_BAR_COLUMNS].itertuples(index=False, name=None):
        digest.update(("|".join(_canonical_value(value) for value in row) + "\n").encode("utf-8"))
    return digest.hexdigest()


def input_continuity_snapshot(
    bars: dict[str, pd.DataFrame],
    previous_state: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    previous_files = (
        previous_state.get("input_continuity", {}).get("files", {})
        if previous_state
        else {}
    )
    files: dict[str, Any] = {}
    advanced = False

    for timeframe, frame in bars.items():
        current_count = int(len(frame))
        current_last_open = pd.Timestamp(frame["bar_open_time"].iloc[-1])
        current_last_close = pd.Timestamp(frame["bar_close_time"].iloc[-1])
        current_hash = canonical_bar_hash(frame)
        previous = previous_files.get(timeframe)
        if previous:
            previous_count = int(previous["row_count"])
            if current_count < previous_count:
                raise ValueError(
                    f"{timeframe} input truncated: previous rows={previous_count}, current rows={current_count}"
                )
            prefix_hash = canonical_bar_hash(frame, previous_count)
            if prefix_hash != str(previous["canonical_full_hash"]):
                raise ValueError(
                    f"{timeframe} historical closed-bar prefix changed; monitoring is fail-closed"
                )
            previous_last_close = pd.Timestamp(previous["last_bar_close_time"])
            if current_last_close < previous_last_close:
                raise ValueError(
                    f"{timeframe} latest close moved backward: {current_last_close} < {previous_last_close}"
                )
            if current_last_close > previous_last_close:
                advanced = True
        else:
            advanced = True

        files[timeframe] = {
            "row_count": current_count,
            "first_bar_open_time": str(pd.Timestamp(frame["bar_open_time"].iloc[0])),
            "last_bar_open_time": str(current_last_open),
            "last_bar_close_time": str(current_last_close),
            "canonical_full_hash": current_hash,
        }

    return {"files": files}, advanced


def parse_timestamp_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in frame.columns:
        if column in TIMESTAMP_COLUMNS:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return parse_timestamp_columns(pd.read_csv(path))


def load_previous_monitor(output_dir: Path) -> tuple[dict[str, Any] | None, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    state_path = output_dir / "monitor_state.json"
    existing_required = [path for path in (output_dir / name for name in REQUIRED_STATE_FILES) if path.exists()]
    if not state_path.exists():
        if existing_required:
            raise ValueError(
                "Partial monitor state exists without monitor_state.json; manual repair is required"
            )
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("monitor_state.json must contain a JSON object")
    if int(state.get("schema_version", -1)) != 1:
        raise ValueError(f"Unsupported monitor state schema: {state.get('schema_version')}")
    missing = [name for name in REQUIRED_STATE_FILES if not (output_dir / name).exists()]
    if missing:
        raise ValueError(f"Monitor state is incomplete; missing files: {missing}")
    return (
        state,
        load_csv(output_dir / "monitor_candidate_ledger.csv"),
        load_csv(output_dir / "monitor_parent_event_ledger.csv"),
        load_csv(output_dir / "monitor_run_history.csv"),
    )


def _key_series(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing key columns: {missing}")
    values: list[pd.Series] = []
    for column in columns:
        series = frame[column]
        if column in TIMESTAMP_COLUMNS:
            series = pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            series = series.astype(str)
        values.append(series)
    key = values[0]
    for series in values[1:]:
        key = key + "|" + series
    return key


def _with_unique_key(frame: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
    frame = parse_timestamp_columns(frame)
    if frame.empty:
        frame = frame.copy()
        frame["_monitor_key"] = pd.Series(dtype=str)
        return frame
    frame = frame.copy()
    frame["_monitor_key"] = _key_series(frame, columns)
    duplicated = frame["_monitor_key"].duplicated(keep=False)
    if duplicated.any():
        examples = frame.loc[duplicated, "_monitor_key"].head(10).tolist()
        raise ValueError(f"Duplicate {label} keys: {examples}")
    return frame


def _values_equal(left: Any, right: Any, column: str) -> bool:
    left_missing = left is None or pd.isna(left)
    right_missing = right is None or pd.isna(right)
    if left_missing or right_missing:
        return left_missing and right_missing
    if column in TIMESTAMP_COLUMNS:
        return pd.Timestamp(left) == pd.Timestamp(right)
    if isinstance(left, (int, float, np.integer, np.floating)) or isinstance(
        right, (int, float, np.integer, np.floating)
    ):
        try:
            return bool(np.isclose(float(left), float(right), rtol=1e-10, atol=1e-10))
        except (TypeError, ValueError):
            pass
    return str(left) == str(right)


def _compare_immutable_columns(
    previous_row: pd.Series,
    current_row: pd.Series,
    dynamic_columns: set[str],
    key: str,
    label: str,
) -> None:
    shared = set(previous_row.index) & set(current_row.index)
    ignored = dynamic_columns | {"_monitor_key"}
    for column in sorted(shared - ignored):
        if not _values_equal(previous_row[column], current_row[column], column):
            raise ValueError(
                f"{label} immutable field changed for {key}: {column}: "
                f"{previous_row[column]!r} -> {current_row[column]!r}"
            )


def _validate_resolution_transition(
    previous_row: pd.Series,
    current_row: pd.Series,
    key: str,
    label: str,
) -> bool:
    previous_state = str(previous_row.get("resolution_state", ""))
    current_state = str(current_row.get("resolution_state", ""))
    if previous_state == "RESOLVED":
        if current_state != "RESOLVED":
            raise ValueError(f"{label} resolved state regressed for {key}: {current_state}")
        for column in ("outcome", "exit_time", "exit_price", "r_value"):
            if column in previous_row.index and column in current_row.index:
                if not _values_equal(previous_row[column], current_row[column], column):
                    raise ValueError(
                        f"{label} resolved field changed for {key}: {column}: "
                        f"{previous_row[column]!r} -> {current_row[column]!r}"
                    )
        return False
    if previous_state == "UNRESOLVED":
        if current_state not in {"UNRESOLVED", "RESOLVED"}:
            raise ValueError(
                f"{label} invalid unresolved transition for {key}: {current_state}"
            )
        return current_state == "RESOLVED"
    if previous_state != current_state:
        raise ValueError(
            f"{label} unsupported resolution transition for {key}: "
            f"{previous_state} -> {current_state}"
        )
    return False


def reconcile_candidates(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    previous_keyed = _with_unique_key(previous, CANDIDATE_KEY_COLUMNS, "candidate")
    current_keyed = _with_unique_key(current, CANDIDATE_KEY_COLUMNS, "candidate")
    previous_keys = set(previous_keyed["_monitor_key"])
    current_keys = set(current_keyed["_monitor_key"])
    missing = sorted(previous_keys - current_keys)
    if missing:
        raise ValueError(
            f"Previously recorded candidates disappeared from full replay: {missing[:10]}"
        )

    previous_map = previous_keyed.set_index("_monitor_key", drop=False)
    current_map = current_keyed.set_index("_monitor_key", drop=False)
    resolved_transition_keys: list[str] = []
    for key in sorted(previous_keys):
        previous_row = previous_map.loc[key]
        current_row = current_map.loc[key]
        _compare_immutable_columns(
            previous_row,
            current_row,
            CANDIDATE_DYNAMIC_COLUMNS,
            key,
            "candidate",
        )
        if _validate_resolution_transition(previous_row, current_row, key, "candidate"):
            resolved_transition_keys.append(key)

    new_keys = sorted(current_keys - previous_keys)
    new_rows = current_keyed[current_keyed["_monitor_key"].isin(new_keys)].drop(
        columns=["_monitor_key"]
    )
    resolved_rows = current_keyed[
        current_keyed["_monitor_key"].isin(resolved_transition_keys)
    ].drop(columns=["_monitor_key"])
    ledger = current_keyed.drop(columns=["_monitor_key"]).sort_values(
        CANDIDATE_KEY_COLUMNS, kind="mergesort"
    ).reset_index(drop=True)
    return ledger, new_rows.reset_index(drop=True), resolved_rows.reset_index(drop=True)


def reconcile_parent_events(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    previous_keyed = _with_unique_key(previous, PARENT_KEY_COLUMNS, "parent event")
    current_keyed = _with_unique_key(current, PARENT_KEY_COLUMNS, "parent event")
    previous_keys = set(previous_keyed["_monitor_key"])
    current_keys = set(current_keyed["_monitor_key"])
    missing = sorted(previous_keys - current_keys)
    if missing:
        raise ValueError(
            f"Previously recorded parent events disappeared from full replay: {missing[:10]}"
        )

    previous_map = previous_keyed.set_index("_monitor_key", drop=False)
    current_map = current_keyed.set_index("_monitor_key", drop=False)
    transition_keys: list[str] = []
    for key in sorted(previous_keys):
        previous_row = previous_map.loc[key]
        current_row = current_map.loc[key]
        _compare_immutable_columns(
            previous_row,
            current_row,
            PARENT_DYNAMIC_COLUMNS,
            key,
            "parent event",
        )
        previous_admission = str(previous_row.get("admission_state", ""))
        current_admission = str(current_row.get("admission_state", ""))
        if previous_admission == "ACCEPTED_PARENT_EVENT":
            if current_admission != "ACCEPTED_PARENT_EVENT":
                raise ValueError(
                    f"Accepted parent event regressed for {key}: {current_admission}"
                )
            _validate_resolution_transition(previous_row, current_row, key, "parent event")
        elif previous_admission == "SUPPRESSED_BY_FROZEN_NON_OVERLAP":
            if current_admission not in {
                "SUPPRESSED_BY_FROZEN_NON_OVERLAP",
                "ACCEPTED_PARENT_EVENT",
            }:
                raise ValueError(
                    f"Invalid suppressed parent transition for {key}: {current_admission}"
                )
            if current_admission == "ACCEPTED_PARENT_EVENT":
                transition_keys.append(key)
        elif previous_admission != current_admission:
            raise ValueError(
                f"Unsupported parent admission transition for {key}: "
                f"{previous_admission} -> {current_admission}"
            )

    new_keys = sorted(current_keys - previous_keys)
    new_rows = current_keyed[current_keyed["_monitor_key"].isin(new_keys)].drop(
        columns=["_monitor_key"]
    )
    transitioned_rows = current_keyed[
        current_keyed["_monitor_key"].isin(transition_keys)
    ].drop(columns=["_monitor_key"])
    ledger = current_keyed.drop(columns=["_monitor_key"]).sort_values(
        PARENT_KEY_COLUMNS, kind="mergesort"
    ).reset_index(drop=True)
    return ledger, new_rows.reset_index(drop=True), transitioned_rows.reset_index(drop=True)


def append_run_history(history: pd.DataFrame, row: dict[str, Any]) -> pd.DataFrame:
    current = pd.DataFrame([row])
    if history.empty:
        result = current
    else:
        result = pd.concat([history, current], ignore_index=True, sort=False)
    if "run_id" in result.columns and result["run_id"].duplicated().any():
        raise ValueError("Duplicate run_id in monitor history")
    return parse_timestamp_columns(result)


def state_json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
