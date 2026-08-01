from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .shadow_common import normalize_name, parse_dt, path_value, pick, read_csv_records, read_json


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


def _score_ledger(root: Path) -> pd.DataFrame:
    path = root / "outputs" / "shadow_score_ledger.csv"
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"V19 score ledger is missing: {path}")
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
        raise ValueError(f"V19 score ledger missing decision timestamp; columns={list(frame.columns)}")
    for column in ("chosen_rank", "rank_long", "rank_short"):
        if column in output:
            output[column] = pd.to_numeric(output[column], errors="raise")
    if "chosen_side" not in output:
        if not {"rank_long", "rank_short"}.issubset(output.columns):
            raise ValueError("V19 score ledger lacks chosen_side and directional ranks")
        output["chosen_side"] = np.where(output.rank_long >= output.rank_short, "LONG", "SHORT")
    output["chosen_side"] = output.chosen_side.astype(str).str.upper()
    if "chosen_rank" not in output:
        if not {"rank_long", "rank_short"}.issubset(output.columns):
            raise ValueError("V19 score ledger lacks chosen_rank and directional ranks")
        output["chosen_rank"] = np.maximum(output.rank_long, output.rank_short)
    if output.chosen_rank.isna().any():
        raise ValueError("V19 score ledger has unreconstructable chosen_rank rows")
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


def load_v19_view(config: Mapping[str, Any]) -> V19View:
    v19 = config.get("v19")
    if not isinstance(v19, dict):
        raise ValueError("v19 config is missing")
    config_path = path_value(str(v19.get("local_config_path", "")))
    if not config_path.exists():
        raise FileNotFoundError(f"V19 local config not found: {config_path}")
    vcfg = read_json(config_path)
    if vcfg.get("shadow_id") != "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW":
        raise ValueError("Configured V19 local config is not the frozen V19 Shadow")
    root = path_value(str(vcfg.get("state_dir", "")))
    runtime_path = root / "runtime_state.json"
    health_path = root / "runtime_health.json"
    if not runtime_path.exists() or not health_path.exists():
        raise FileNotFoundError("V19 runtime_state.json or runtime_health.json is missing")
    runtime = read_json(runtime_path)
    health = read_json(health_path)
    status = str(health.get("status", runtime.get("status", "UNKNOWN"))).upper()
    activated = bool(runtime.get("activated", health.get("activated", False)))
    parity = str(health.get("v19_parity", runtime.get("v19_parity", "UNKNOWN"))).upper()
    last_processed = parse_dt(pick(runtime, ("last_processed_decision_time", "last_processed_decision_dt", "last_processed_time")))
    if last_processed is None:
        last_processed = parse_dt(pick(health, ("last_processed_decision_time", "last_processed_decision_dt", "last_processed_time")))
    intervals: list[V19Interval] = []
    entries: set[pd.Timestamp] = set()
    for row in read_csv_records(root / "outputs" / "shadow_trade_ledger.csv"):
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
    ledger = _score_ledger(root)
    score_latest = pd.Timestamp(ledger.entry_time.iloc[-1]) if len(ledger) else None
    cursor_match = last_processed is not None and score_latest == last_processed
    ready = status == "READY" and activated and parity == "PASS" and cursor_match
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
            "score_ledger_latest": None if score_latest is None else str(score_latest),
            "score_cursor_match": cursor_match,
        },
    )
