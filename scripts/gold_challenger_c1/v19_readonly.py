from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .shadow_common import normalize_name, parse_dt, path_value, pick, read_csv_records, read_json


EXPECTED_SHADOW_ID = "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW"
EXPECTED_CONTRACT_VERSION = "2026-08-01-v1"
RANK_LOOKBACK_DAYS = 60
ALLOWED_RUNTIME_STATUSES = {"READY", "RUNNING"}


@dataclass(frozen=True)
class V19Interval:
    entry: pd.Timestamp
    exit: pd.Timestamp | None


@dataclass
class V19View:
    ready: bool
    status: str
    activated: bool
    parity: str
    last_processed: pd.Timestamp | None
    intervals: list[V19Interval]
    entry_times: set[pd.Timestamp]
    score_ledger: pd.DataFrame
    state_root: Path
    details: dict[str, Any]

    def entry_at(self, timestamp: pd.Timestamp) -> bool:
        return pd.Timestamp(timestamp) in self.entry_times

    def open_at(self, timestamp: pd.Timestamp) -> bool:
        timestamp = pd.Timestamp(timestamp)
        return any(interval.entry <= timestamp and (interval.exit is None or timestamp <= interval.exit) for interval in self.intervals)


def _extract_interval(row: Mapping[str, Any]) -> V19Interval | None:
    entry = parse_dt(pick(row, ("entry_dt", "entry_time", "entry_datetime", "decision_dt", "decision_time", "time", "timestamp")))
    if entry is None:
        return None
    exit_time = parse_dt(pick(row, ("resolved_exit_dt", "natural_exit_dt", "exit_dt", "exit_time", "close_dt", "close_time")))
    return V19Interval(entry=entry, exit=exit_time)


def _legacy_score_ledger(root: Path) -> pd.DataFrame:
    path = root / "outputs" / "shadow_score_ledger.csv"
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"V19 legacy score ledger is missing: {path}")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.columns = [normalize_name(column) for column in frame.columns]
    if "schedule" in frame.columns:
        frame = frame[frame.schedule.astype(str).str.upper().eq("SEMIANNUAL_EXPANDING")].copy()
    aliases = {
        "entry_time": ("entry_time", "entry_dt", "decision_time", "decision_dt", "timestamp", "time"),
        "origin_id": ("origin_id", "score_id", "row_id"),
        "entry_idx": ("entry_idx", "m1_entry_idx", "origin_entry_idx"),
        "chosen_side": ("chosen_side", "selected_side", "direction", "side"),
        "chosen_rank": ("chosen_rank", "selected_rank", "rank"),
        "rank_long": ("rank_long", "long_rank", "pctl_long", "percentile_long"),
        "rank_short": ("rank_short", "short_rank", "pctl_short", "percentile_short"),
    }
    output = pd.DataFrame(index=frame.index)
    for target, names in aliases.items():
        source = next((name for name in names if name in frame.columns), None)
        if source is not None:
            output[target] = frame[source]
    if "entry_time" not in output:
        raise ValueError(f"V19 legacy score ledger missing decision timestamp; columns={list(frame.columns)}")
    for column in ("chosen_rank", "rank_long", "rank_short"):
        if column in output:
            output[column] = pd.to_numeric(output[column], errors="raise")
    if "chosen_side" not in output:
        if not {"rank_long", "rank_short"}.issubset(output.columns):
            raise ValueError("V19 legacy score ledger lacks chosen_side and directional ranks")
        output["chosen_side"] = np.where(output.rank_long >= output.rank_short, "LONG", "SHORT")
    output["chosen_side"] = output.chosen_side.astype(str).str.upper()
    if "chosen_rank" not in output:
        if not {"rank_long", "rank_short"}.issubset(output.columns):
            raise ValueError("V19 legacy score ledger lacks chosen_rank and directional ranks")
        output["chosen_rank"] = np.maximum(output.rank_long, output.rank_short)
    if output.chosen_rank.isna().any():
        raise ValueError("V19 legacy score ledger has unreconstructable chosen_rank rows")
    output["entry_time"] = pd.to_datetime(output.entry_time, errors="raise")
    if "origin_id" not in output:
        output["origin_id"] = np.arange(len(output), dtype=int)
    else:
        output["origin_id"] = pd.to_numeric(output.origin_id, errors="raise").astype(int)
    if "entry_idx" in output:
        output["entry_idx"] = pd.to_numeric(output.entry_idx, errors="raise").astype(int)
    if output.entry_time.duplicated().any():
        raise RuntimeError("V19_SCORE_LEDGER_DUPLICATE_DECISION_TIME")
    output = output.sort_values("entry_time").reset_index(drop=True)
    if not output.chosen_side.isin(["LONG", "SHORT"]).all():
        raise RuntimeError("V19_SCORE_LEDGER_INVALID_CHOSEN_SIDE")
    return output


def _read_raw_scores(path: Path, *, allow_missing: bool = False) -> pd.DataFrame:
    required = ["entry_time", "origin_id", "score_long", "score_short", "model_boundary"]
    if not path.exists():
        if allow_missing:
            return pd.DataFrame(columns=required)
        raise FileNotFoundError(f"V19 score file is missing: {path}")
    frame = pd.read_csv(path, encoding="utf-8-sig", compression="infer")
    frame.columns = [normalize_name(column) for column in frame.columns]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"V19 score file schema mismatch path={path} missing={missing} columns={list(frame.columns)}")
    frame = frame.loc[:, required].copy()
    frame["entry_time"] = pd.to_datetime(frame.entry_time, errors="raise")
    frame["origin_id"] = pd.to_numeric(frame.origin_id, errors="raise").astype(int)
    frame["score_long"] = pd.to_numeric(frame.score_long, errors="raise").astype(float)
    frame["score_short"] = pd.to_numeric(frame.score_short, errors="raise").astype(float)
    frame["model_boundary"] = pd.to_datetime(frame.model_boundary, errors="raise").dt.normalize()
    if frame.entry_time.duplicated().any():
        raise RuntimeError(f"V19_SCORE_FILE_DUPLICATE_DECISION_TIME path={path}")
    return frame.sort_values(["entry_time", "origin_id"]).reset_index(drop=True)


def _read_calibration(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"V19 calibration score file is missing: {path}")
    frame = pd.read_csv(path, encoding="utf-8-sig", compression="infer")
    frame.columns = [normalize_name(column) for column in frame.columns]
    required = ["entry_time", "score_long", "score_short"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"V19 calibration schema mismatch path={path} missing={missing} columns={list(frame.columns)}")
    frame = frame.loc[:, required].copy()
    frame["entry_time"] = pd.to_datetime(frame.entry_time, errors="raise")
    frame["score_long"] = pd.to_numeric(frame.score_long, errors="raise").astype(float)
    frame["score_short"] = pd.to_numeric(frame.score_short, errors="raise").astype(float)
    return frame.sort_values("entry_time").reset_index(drop=True)


def _rank_day_exact(current: pd.DataFrame, history: pd.DataFrame, calibration: pd.DataFrame) -> pd.DataFrame:
    if current.empty:
        return current.assign(rank_long=np.nan, rank_short=np.nan, chosen_side="", chosen_rank=np.nan)
    day = pd.DatetimeIndex(current.entry_time).normalize()[0]
    start = day - pd.Timedelta(days=RANK_LOOKBACK_DAYS)
    reference = pd.concat(
        [
            calibration[["entry_time", "score_long", "score_short"]],
            history[["entry_time", "score_long", "score_short"]],
        ],
        ignore_index=True,
    )
    reference_days = pd.DatetimeIndex(reference.entry_time).normalize()
    reference = reference[(reference_days < day) & (reference_days >= start)]
    ranked = current.copy()
    for side in ("long", "short"):
        values = np.sort(reference[f"score_{side}"].dropna().to_numpy(float))
        if len(values) < 100:
            values = np.sort(calibration[f"score_{side}"].dropna().to_numpy(float))
        if len(values) == 0:
            raise RuntimeError(f"V19_CALIBRATION_EMPTY_{side.upper()}")
        ranked[f"rank_{side}"] = np.searchsorted(
            values,
            ranked[f"score_{side}"].to_numpy(float),
            side="right",
        ) / len(values)
    ranked["chosen_side"] = np.where(ranked.rank_long >= ranked.rank_short, "LONG", "SHORT")
    ranked["chosen_rank"] = np.maximum(ranked.rank_long, ranked.rank_short)
    return ranked


def _reconstruct_score_ledger(
    root: Path,
    active_boundary: pd.Timestamp,
    last_processed: pd.Timestamp | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    history_path = root / "score_history.csv.gz"
    pending_path = root / "pending_scores.csv.gz"
    history = _read_raw_scores(history_path)
    pending = _read_raw_scores(pending_path, allow_missing=True)

    expected_boundary = pd.Timestamp(active_boundary).normalize()
    for name, frame in (("score_history", history), ("pending_scores", pending)):
        if len(frame) and not frame.model_boundary.eq(expected_boundary).all():
            observed = sorted({str(value.date()) for value in frame.model_boundary})
            raise RuntimeError(
                f"V19_{name.upper()}_MODEL_BOUNDARY_MISMATCH expected={expected_boundary.date()} observed={observed}"
            )

    raw = pd.concat([history.assign(_source="HISTORY"), pending.assign(_source="PENDING")], ignore_index=True)
    if raw.empty:
        raise RuntimeError("V19_SCORE_HISTORY_AND_PENDING_ARE_EMPTY")
    duplicate = raw.entry_time.duplicated(keep=False)
    if duplicate.any():
        rows = raw.loc[duplicate].sort_values(["entry_time", "_source"])
        for _, group in rows.groupby("entry_time", sort=True):
            comparison = group[["origin_id", "score_long", "score_short", "model_boundary"]].drop_duplicates()
            if len(comparison) != 1:
                raise RuntimeError(f"V19_SCORE_HISTORY_PENDING_CONFLICT at {group.entry_time.iloc[0]}")
        raw = raw.sort_values(["entry_time", "_source"]).drop_duplicates("entry_time", keep="first")
    raw = raw.sort_values(["entry_time", "origin_id"]).reset_index(drop=True)
    if last_processed is not None:
        raw = raw[raw.entry_time <= pd.Timestamp(last_processed)].reset_index(drop=True)
    if raw.empty:
        raise RuntimeError("V19_NO_SCORE_ROWS_AT_OR_BEFORE_RUNTIME_CURSOR")

    calibration_path = root / "models" / expected_boundary.strftime("%Y-%m-%d") / "calibration_scores.csv.gz"
    calibration = _read_calibration(calibration_path)
    ranked_parts: list[pd.DataFrame] = []
    ranked_history = pd.DataFrame(columns=["entry_time", "score_long", "score_short"])
    for _, group in raw.groupby(pd.DatetimeIndex(raw.entry_time).normalize(), sort=True):
        ranked = _rank_day_exact(group, ranked_history, calibration)
        ranked_parts.append(ranked)
        ranked_history = pd.concat(
            [ranked_history, group[["entry_time", "score_long", "score_short"]]],
            ignore_index=True,
        )
    ledger = pd.concat(ranked_parts, ignore_index=True)
    ledger = ledger[
        [
            "entry_time",
            "origin_id",
            "score_long",
            "score_short",
            "rank_long",
            "rank_short",
            "chosen_side",
            "chosen_rank",
            "model_boundary",
        ]
    ].sort_values(["entry_time", "origin_id"]).reset_index(drop=True)
    if not ledger.chosen_side.isin(["LONG", "SHORT"]).all():
        raise RuntimeError("V19_RECONSTRUCTED_LEDGER_INVALID_CHOSEN_SIDE")
    return ledger, {
        "score_source": "score_history.csv.gz+pending_scores.csv.gz",
        "score_history_path": str(history_path),
        "pending_scores_path": str(pending_path),
        "calibration_path": str(calibration_path),
        "score_history_rows": len(history),
        "pending_score_rows": len(pending),
        "reconstructed_rows": len(ledger),
    }


def _runtime_score_ledger(
    root: Path,
    active_boundary: pd.Timestamp | None,
    last_processed: pd.Timestamp | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    history_path = root / "score_history.csv.gz"
    if history_path.exists():
        if active_boundary is None:
            raise RuntimeError("V19_ACTIVE_MODEL_BOUNDARY_MISSING")
        return _reconstruct_score_ledger(root, active_boundary, last_processed)
    legacy = _legacy_score_ledger(root)
    return legacy, {
        "score_source": "outputs/shadow_score_ledger.csv",
        "reconstructed_rows": len(legacy),
    }


def load_v19_view(config: Mapping[str, Any]) -> V19View:
    v19 = config.get("v19")
    if not isinstance(v19, dict):
        raise ValueError("v19 config is missing")
    config_path = path_value(str(v19.get("local_config_path", "")))
    if not config_path.exists():
        raise FileNotFoundError(f"V19 local config not found: {config_path}")
    vcfg = read_json(config_path)
    if vcfg.get("shadow_id") != EXPECTED_SHADOW_ID:
        raise ValueError("Configured V19 local config is not the frozen V19 Shadow")
    if str(vcfg.get("contract_version", EXPECTED_CONTRACT_VERSION)) != EXPECTED_CONTRACT_VERSION:
        raise ValueError("Configured V19 contract_version is not the frozen 2026-08-01-v1 contract")

    root = path_value(str(vcfg.get("state_dir", "")))
    runtime_path = root / "runtime_state.json"
    health_path = root / "runtime_health.json"
    if not runtime_path.exists() or not health_path.exists():
        raise FileNotFoundError("V19 runtime_state.json or runtime_health.json is missing")
    runtime = read_json(runtime_path)
    health = read_json(health_path)

    status = str(health.get("status", runtime.get("status", "UNKNOWN"))).upper()
    activated = bool(runtime.get("activated", health.get("activated", False)))
    last_processed = parse_dt(pick(runtime, ("last_processed_decision_time", "last_processed_decision_dt", "last_processed_time")))
    if last_processed is None:
        last_processed = parse_dt(pick(health, ("last_processed_decision_time", "last_processed_decision_dt", "last_processed_time")))
    active_boundary = parse_dt(pick(runtime, ("active_model_boundary",)))
    if active_boundary is None:
        active_boundary = parse_dt(pick(health, ("active_model_boundary",)))

    intervals: list[V19Interval] = []
    entries: set[pd.Timestamp] = set()
    trade_path = root / "outputs" / "shadow_trade_ledger.csv"
    for row in read_csv_records(trade_path):
        interval = _extract_interval(row)
        if interval is not None:
            intervals.append(interval)
            entries.add(interval.entry)
    opened = runtime.get("open_trade")
    if isinstance(opened, dict) and opened:
        interval = _extract_interval({normalize_name(key): value for key, value in opened.items()})
        if interval is not None:
            intervals.append(V19Interval(interval.entry, None))
            entries.add(interval.entry)

    ledger, score_details = _runtime_score_ledger(root, active_boundary, last_processed)
    score_latest = pd.Timestamp(ledger.entry_time.iloc[-1]) if len(ledger) else None
    cursor_match = last_processed is not None and score_latest == last_processed

    runtime_counter = runtime.get("counters", {})
    health_counter = health.get("counters", {})
    accepted_trades = int(
        (runtime_counter.get("accepted_trades", 0) if isinstance(runtime_counter, dict) else 0)
        or (health_counter.get("accepted_trades", 0) if isinstance(health_counter, dict) else 0)
    )
    trade_ledger_contract_ok = accepted_trades == 0 or trade_path.exists()

    history_count_ok = True
    pending_count_ok = True
    if score_details.get("score_source") == "score_history.csv.gz+pending_scores.csv.gz":
        if "score_history_rows" in health:
            history_count_ok = int(health["score_history_rows"]) == int(score_details["score_history_rows"])
        if "pending_score_rows" in health:
            pending_count_ok = int(health["pending_score_rows"]) == int(score_details["pending_score_rows"])

    boundary_runtime = pd.Timestamp(active_boundary).normalize() if active_boundary is not None else None
    boundary_health = parse_dt(pick(health, ("active_model_boundary",)))
    boundary_match = (
        boundary_runtime is not None
        and (boundary_health is None or pd.Timestamp(boundary_health).normalize() == boundary_runtime)
    )
    status_ok = status in ALLOWED_RUNTIME_STATUSES
    invariants = {
        "status_allowed": status_ok,
        "activated": activated,
        "score_cursor_match": cursor_match,
        "active_model_boundary_match": boundary_match,
        "score_history_row_count_match": history_count_ok,
        "pending_score_row_count_match": pending_count_ok,
        "trade_ledger_contract_ok": trade_ledger_contract_ok,
    }
    parity = "PASS" if all(invariants.values()) else "FAIL"
    ready = parity == "PASS"

    return V19View(
        ready=ready,
        status=status,
        activated=activated,
        parity=parity,
        last_processed=last_processed,
        intervals=intervals,
        entry_times=entries,
        score_ledger=ledger,
        state_root=root,
        details={
            "runtime_path": str(runtime_path),
            "health_path": str(health_path),
            "trade_ledger_path": str(trade_path),
            "score_ledger_latest": None if score_latest is None else str(score_latest),
            "accepted_trades": accepted_trades,
            "invariants": invariants,
            **score_details,
        },
    )
