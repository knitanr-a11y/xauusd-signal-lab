from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .common import path_value, read_json

REQUIRED_COLUMNS = ("time", "open", "high", "low", "close")


def _read_candle_file(path: Path, source_order: int) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    rejected_rows: list[list[str]] = []

    def reject_bad_line(fields: list[str]) -> None:
        # MT5 exports are fixed-width comma CSVs. A small number of historical
        # files contain concatenated boundary lines; they are rejected rather
        # than repaired or interpreted. Keep only a bounded sample in memory.
        if len(rejected_rows) < 20:
            rejected_rows.append([str(value) for value in fields[:12]])
        return None

    try:
        frame = pd.read_csv(path, sep=",")
        parser_recovery = False
        rejected_count = 0
    except pd.errors.ParserError:
        rejected_count_box = {"value": 0}

        def audited_reject(fields: list[str]):
            rejected_count_box["value"] += 1
            reject_bad_line(fields)
            return None

        frame = pd.read_csv(path, sep=",", engine="python", on_bad_lines=audited_reject)
        parser_recovery = True
        rejected_count = int(rejected_count_box["value"])

    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns {missing}: {path}")
    raw_rows = int(len(frame))
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    for column in ("open", "high", "low", "close", "tick_volume", "spread", "real_volume"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    before_required_drop = int(len(frame))
    frame = frame.dropna(subset=list(REQUIRED_COLUMNS))
    invalid_required_rows = before_required_drop - int(len(frame))
    frame["_source_order"] = source_order
    frame.attrs["source_audit"] = {
        "path": str(path),
        "source_order": int(source_order),
        "parser_recovery_used": parser_recovery,
        "parser_rejected_rows": rejected_count,
        "parser_rejected_sample": rejected_rows,
        "parsed_rows": raw_rows,
        "invalid_required_rows": invalid_required_rows,
        "accepted_rows": int(len(frame)),
    }
    return frame


def read_union(paths: list[Path]) -> pd.DataFrame:
    if not paths:
        raise ValueError("No candle paths configured")
    frames = [_read_candle_file(path, index) for index, path in enumerate(paths)]
    source_audit = [dict(frame.attrs.get("source_audit", {})) for frame in frames]
    union = pd.concat(frames, ignore_index=True)
    pre_dedup_rows = int(len(union))
    union = union.sort_values(["time", "_source_order"], kind="stable")
    union = union.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    duplicate_rows_removed = pre_dedup_rows - int(len(union))
    result = union.drop(columns=["_source_order"])
    result.attrs["source_audit"] = {
        "sources": source_audit,
        "pre_dedup_rows": pre_dedup_rows,
        "duplicate_rows_removed": duplicate_rows_removed,
        "union_rows": int(len(result)),
        "first_time": str(result["time"].iloc[0]) if not result.empty else None,
        "last_time": str(result["time"].iloc[-1]) if not result.empty else None,
    }
    return result


def resolve_data_sources(config: Mapping[str, Any], config_path: Path) -> dict[str, list[Path]]:
    data = config.get("data_sources")
    if not isinstance(data, dict):
        raise ValueError("data_sources is missing")
    inherited: dict[str, Any] = {}
    if data.get("inherit_from_v19", True):
        v19_path_value = config.get("v19_local_config_path")
        if not isinstance(v19_path_value, str) or not v19_path_value:
            raise ValueError("v19_local_config_path is missing")
        v19_path = path_value(v19_path_value, config_path.parent)
        v19_config = read_json(v19_path)
        inherited_data = v19_config.get("data_sources")
        if not isinstance(inherited_data, dict):
            raise ValueError("V19 local config has no data_sources")
        inherited = inherited_data
    result: dict[str, list[Path]] = {}
    for timeframe in ("M1", "M5", "M15", "H1", "H4"):
        configured = data.get(timeframe)
        raw = configured if isinstance(configured, list) and configured else inherited.get(timeframe)
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"No {timeframe} data source configured")
        result[timeframe] = [path_value(str(value), config_path.parent) for value in raw]
    return result


def load_market_data(config: Mapping[str, Any], config_path: Path) -> dict[str, pd.DataFrame]:
    sources = resolve_data_sources(config, config_path)
    return {timeframe: read_union(paths) for timeframe, paths in sources.items()}


def _ema_stack(frame: pd.DataFrame, timeframe_minutes: int) -> pd.DataFrame:
    value = frame[["time", "close"]].copy().sort_values("time")
    value["ema20"] = value["close"].ewm(span=20, adjust=False).mean()
    value["ema50"] = value["close"].ewm(span=50, adjust=False).mean()
    value["closed_at"] = value["time"] + pd.Timedelta(minutes=timeframe_minutes)
    value["up"] = (value["close"] > value["ema20"]) & (value["ema20"] > value["ema50"])
    value["down"] = (value["close"] < value["ema20"]) & (value["ema20"] < value["ema50"])
    return value[["closed_at", "up", "down", "close", "ema20", "ema50"]]


def build_state_frame(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    frame = m15.copy().sort_values("time").reset_index(drop=True)
    frame["decision_time"] = frame["time"] + pd.Timedelta(minutes=15)
    previous_close = frame["close"].shift(1)
    true_range = np.maximum(
        frame["high"] - frame["low"],
        np.maximum((frame["high"] - previous_close).abs(), (frame["low"] - previous_close).abs()),
    )
    frame["atr14"] = pd.Series(true_range, index=frame.index).rolling(14, min_periods=14).mean()

    # Causal 5,760-prior-M15 tertiles. The current bar's ATR is compared
    # with thresholds formed from earlier closed bars only.
    prior_atr = frame["atr14"].shift(1)
    frame["vol_low_boundary"] = prior_atr.rolling(5760, min_periods=5760).quantile(1.0 / 3.0)
    frame["vol_high_boundary"] = prior_atr.rolling(5760, min_periods=5760).quantile(2.0 / 3.0)
    frame["vol"] = np.where(
        frame["atr14"] < frame["vol_low_boundary"],
        "LOW",
        np.where(frame["atr14"] > frame["vol_high_boundary"], "HIGH", "MID"),
    )

    momentum_z = (frame["close"] - frame["close"].shift(4)) / frame["atr14"]
    frame["momentum_z"] = momentum_z
    frame["mom"] = np.where(momentum_z >= 0.50, "UP", np.where(momentum_z <= -0.50, "DOWN", "FLAT"))

    candle_range = frame["high"] - frame["low"]
    prior_range_median = candle_range.shift(1).rolling(96, min_periods=96).median()
    range_ratio = candle_range / prior_range_median.replace(0.0, np.nan)
    frame["range_ratio"] = range_ratio
    frame["exp"] = np.where(range_ratio <= 0.80, "COMP", np.where(range_ratio >= 1.50, "EXP", "NORM"))

    body = frame["close"] - frame["open"]
    body_fraction = body.abs() / candle_range.replace(0.0, np.nan)
    frame["body_fraction"] = body_fraction
    frame["cdir"] = np.where(
        (body > 0.0) & (body_fraction >= 0.60),
        "BULL",
        np.where((body < 0.0) & (body_fraction >= 0.60), "BEAR", "WEAK"),
    )

    # The state session is keyed by the entry-decision boundary (M15 open + 15 minutes),
    # not by the candle-open timestamp. Thus 07:45 -> S08 and 14:45 -> S15.
    hour = frame["decision_time"].dt.hour
    frame["session_x"] = np.where(hour < 8, "S01", np.where(hour < 15, "S08", "S15"))

    h1_stack = _ema_stack(h1, 60)
    h4_stack = _ema_stack(h4, 240)
    merged = pd.merge_asof(
        frame.sort_values("decision_time"),
        h1_stack.sort_values("closed_at").rename(
            columns={"up": "h1_up", "down": "h1_down", "close": "h1_close", "ema20": "h1_ema20", "ema50": "h1_ema50"}
        ),
        left_on="decision_time",
        right_on="closed_at",
        direction="backward",
    ).drop(columns=["closed_at"])
    merged = pd.merge_asof(
        merged.sort_values("decision_time"),
        h4_stack.sort_values("closed_at").rename(
            columns={"up": "h4_up", "down": "h4_down", "close": "h4_close", "ema20": "h4_ema20", "ema50": "h4_ema50"}
        ),
        left_on="decision_time",
        right_on="closed_at",
        direction="backward",
    ).drop(columns=["closed_at"])
    h1_up = merged["h1_up"].astype("boolean").fillna(False).astype(bool)
    h4_up = merged["h4_up"].astype("boolean").fillna(False).astype(bool)
    h1_down = merged["h1_down"].astype("boolean").fillna(False).astype(bool)
    h4_down = merged["h4_down"].astype("boolean").fillna(False).astype(bool)
    merged["htf"] = np.where(
        h1_up & h4_up,
        "UP",
        np.where(h1_down & h4_down, "DOWN", "MIXED"),
    )
    merged["fine"] = (
        merged["session_x"].astype(str)
        + "|"
        + merged["htf"].astype(str)
        + "|"
        + merged["vol"].astype(str)
        + "|"
        + merged["mom"].astype(str)
        + "|"
        + merged["exp"].astype(str)
        + "|"
        + merged["cdir"].astype(str)
    )
    return merged.sort_values("time").reset_index(drop=True)


def latest_state_rows(data: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    return build_state_frame(data["M15"], data["H1"], data["H4"])
