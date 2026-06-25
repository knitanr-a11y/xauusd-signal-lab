from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

POINT = 0.01
TF_DELTA = {"M1": pd.Timedelta(minutes=1), "M15": pd.Timedelta(minutes=15), "H1": pd.Timedelta(hours=1)}
YEARS = [2023, 2024, 2025, 2026]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path, timeframe: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    frame = frame.copy()
    frame["bar_open_time"] = pd.to_datetime(frame["time"], format="%Y.%m.%d %H:%M:%S", errors="raise")
    for column in required[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame["bar_open_time"].duplicated().any():
        raise ValueError(f"{path.name} contains duplicate timestamps")
    if not frame["bar_open_time"].is_monotonic_increasing:
        raise ValueError(f"{path.name} is not monotonic; silent sorting is forbidden")
    if not ((frame["high"] >= frame[["open", "close"]].max(axis=1)) & (frame["low"] <= frame[["open", "close"]].min(axis=1))).all():
        raise ValueError(f"{path.name} contains invalid OHLC rows")
    frame["bar_close_time"] = frame["bar_open_time"] + TF_DELTA[timeframe]
    return frame.reset_index(drop=True)


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame["close"].shift(1)
    return pd.concat(
        [
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous).abs(),
            (frame["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)


def wilder_average(values: pd.Series, period: int) -> pd.Series:
    source = values.to_numpy(float)
    output = np.full(len(source), np.nan)
    if len(source) >= period:
        output[period - 1] = float(np.mean(source[:period]))
        for index in range(period, len(source)):
            output[index] = (output[index - 1] * (period - 1) + source[index]) / period
    return pd.Series(output, index=values.index)


def wilder_atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return wilder_average(true_range(frame), period)


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).fillna(0.0)
    loss = (-delta.clip(upper=0)).fillna(0.0)
    avg_gain = wilder_average(gain, period)
    avg_loss = wilder_average(loss, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    rsi = rsi.where(avg_gain != 0.0, 0.0)
    both_zero = (avg_gain == 0.0) & (avg_loss == 0.0)
    return rsi.where(~both_zero, 50.0)


@dataclass(frozen=True)
class Cell:
    candidate_id: str
    direction: str
    h1_gap_atr_min: float
    rsi_long_level: int
    trigger_mode: str


def gap_code(value: float) -> str:
    return f"{int(round(value * 100)):03d}"


def build_cells(config: dict[str, Any]) -> list[Cell]:
    search = config["search_space"]
    output: list[Cell] = []
    for direction, gap, rsi, mode in itertools.product(
        search["directions"],
        search["h1_gap_atr_min"],
        search["m15_rsi_long_reentry_level"],
        search["trigger_modes"],
    ):
        direction_code = "L" if direction == "LONG" else "S"
        mode_code = "RC" if mode == "RSI_CROSS_ONLY" else "ER"
        candidate_id = f"GML1-EXP024-{direction_code}-G{gap_code(float(gap))}-R{int(rsi)}-{mode_code}"
        output.append(Cell(candidate_id, direction, float(gap), int(rsi), str(mode)))
    expected = int(search["full_cartesian_cell_count"])
    if len(output) != expected or len({item.candidate_id for item in output}) != expected:
        raise ValueError(f"Search cell count/identity mismatch: {len(output)} != {expected}")
    return output


class DirectionalM1Engine:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.times = pd.DatetimeIndex(frame["bar_open_time"]).asi8
        self.opens = frame["open"].to_numpy(float)
        self.highs = frame["high"].to_numpy(float)
        self.lows = frame["low"].to_numpy(float)
        self.closes = frame["close"].to_numpy(float)
        self.spreads = frame["spread"].to_numpy(float)
        self.latest_close = pd.Timestamp(self.times[-1] + TF_DELTA["M1"].value)

    def exact_entry_index(self, timestamp: pd.Timestamp) -> int | None:
        value = pd.Timestamp(timestamp).value
        index = int(np.searchsorted(self.times, value, side="left"))
        if index >= len(self.times) or int(self.times[index]) != value:
            return None
        return index

    def evaluate(self, entry_time: pd.Timestamp, risk: float, direction: str, horizon_minutes: int, stop_r: float, target_r: float) -> dict[str, Any]:
        start = self.exact_entry_index(entry_time)
        if start is None:
            return {"admission_state": "ENTRY_M1_MISSING", "resolution_state": "NOT_EVALUATED"}
        if not np.isfinite(risk) or risk <= 0:
            return {"admission_state": "INVALID_RISK", "resolution_state": "NOT_EVALUATED"}

        horizon_end = pd.Timestamp(entry_time) + pd.Timedelta(minutes=horizon_minutes)
        available_end = min(horizon_end, self.latest_close)
        end = int(np.searchsorted(self.times, available_end.value, side="left"))
        if end <= start:
            return {"admission_state": "EMPTY_HORIZON", "resolution_state": "NOT_EVALUATED"}

        spread_entry = self.spreads[start] * POINT
        if direction == "LONG":
            entry = float(self.opens[start] + spread_entry)
            stop = entry - stop_r * risk
            target = entry + target_r * risk
            stop_hits = np.flatnonzero(self.lows[start:end] <= stop)
            target_hits = np.flatnonzero(self.highs[start:end] >= target)
        else:
            entry = float(self.opens[start])
            stop = entry + stop_r * risk
            target = entry - target_r * risk
            ask_high = self.highs[start:end] + self.spreads[start:end] * POINT
            ask_low = self.lows[start:end] + self.spreads[start:end] * POINT
            stop_hits = np.flatnonzero(ask_high >= stop)
            target_hits = np.flatnonzero(ask_low <= target)

        has_stop = len(stop_hits) > 0
        has_target = len(target_hits) > 0
        base = {
            "admission_state": "ACCEPTED",
            "entry_time": pd.Timestamp(entry_time),
            "entry_price": entry,
            "risk_price": float(risk),
            "stop_price": float(stop),
            "target_price": float(target),
            "horizon_end_time": horizon_end,
        }
        if has_stop and (not has_target or int(stop_hits[0]) <= int(target_hits[0])):
            index = start + int(stop_hits[0])
            return {
                **base,
                "resolution_state": "RESOLVED",
                "outcome": "SL",
                "exit_time": pd.Timestamp(self.times[index] + TF_DELTA["M1"].value),
                "exit_price": float(stop),
                "r_value": -float(stop_r),
            }
        if has_target:
            index = start + int(target_hits[0])
            return {
                **base,
                "resolution_state": "RESOLVED",
                "outcome": "TP",
                "exit_time": pd.Timestamp(self.times[index] + TF_DELTA["M1"].value),
                "exit_price": float(target),
                "r_value": float(target_r),
            }
        if horizon_end <= self.latest_close:
            index = end - 1
            if direction == "LONG":
                exit_price = float(self.closes[index])
                r_value = (exit_price - entry) / risk
            else:
                exit_price = float(self.closes[index] + self.spreads[index] * POINT)
                r_value = (entry - exit_price) / risk
            return {
                **base,
                "resolution_state": "RESOLVED",
                "outcome": "TIME",
                "exit_time": pd.Timestamp(self.times[index] + TF_DELTA["M1"].value),
                "exit_price": exit_price,
                "r_value": float(r_value),
            }
        return {
            **base,
            "resolution_state": "UNRESOLVED",
            "outcome": "OPEN",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "r_value": np.nan,
        }


def prepare_decisions(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1 = h1.copy()
    h1["h1_ema20"] = h1["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    h1["h1_ema50"] = h1["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    h1["h1_atr14"] = wilder_atr(h1, 14)
    h1["h1_gap_long"] = (h1["h1_ema20"] - h1["h1_ema50"]) / h1["h1_atr14"]
    h1["h1_gap_short"] = (h1["h1_ema50"] - h1["h1_ema20"]) / h1["h1_atr14"]

    m15 = m15.copy()
    m15["m15_ema20"] = m15["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    m15["m15_rsi14"] = wilder_rsi(m15["close"], 14)
    m15["m15_rsi14_prev"] = m15["m15_rsi14"].shift(1)
    m15["m15_atr14"] = wilder_atr(m15, 14)

    confirmed = h1[
        ["bar_close_time", "h1_ema20", "h1_ema50", "h1_atr14", "h1_gap_long", "h1_gap_short"]
    ].dropna()
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time", kind="mergesort"),
        confirmed.sort_values("bar_close_time", kind="mergesort"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["decision_year"] = joined["bar_close_time"].dt.year
    return joined[joined["decision_year"].isin(YEARS)].reset_index(drop=True)


def cell_signal(frame: pd.DataFrame, cell: Cell) -> pd.Series:
    if cell.direction == "LONG":
        trend = (frame["h1_ema20"] > frame["h1_ema50"]) & (frame["h1_gap_long"] >= cell.h1_gap_atr_min)
        cross = (frame["m15_rsi14_prev"] <= cell.rsi_long_level) & (frame["m15_rsi14"] > cell.rsi_long_level)
        recross = (frame["low"] <= frame["m15_ema20"]) & (frame["close"] > frame["m15_ema20"])
    else:
        short_level = 100 - cell.rsi_long_level
        trend = (frame["h1_ema20"] < frame["h1_ema50"]) & (frame["h1_gap_short"] >= cell.h1_gap_atr_min)
        cross = (frame["m15_rsi14_prev"] >= short_level) & (frame["m15_rsi14"] < short_level)
        recross = (frame["high"] >= frame["m15_ema20"]) & (frame["close"] < frame["m15_ema20"])
    signal = trend & cross
    if cell.trigger_mode == "EMA20_TOUCH_RECLOSE":
        signal &= recross
    return signal.fillna(False)


def replay_cell(decisions: pd.DataFrame, engine: DirectionalM1Engine, cell: Cell, execution: dict[str, Any]) -> pd.DataFrame:
    signals = decisions.loc[cell_signal(decisions, cell)].copy()
    rows: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min
    for row in signals.itertuples(index=False):
        decision = pd.Timestamp(row.bar_close_time)
        base = {
            "candidate_id": cell.candidate_id,
            "lineage_id": "M15_H1_TREND_PULLBACK_LINEAGE_EXP024",
            "direction": cell.direction,
            "h1_gap_atr_min": cell.h1_gap_atr_min,
            "rsi_long_level": cell.rsi_long_level,
            "trigger_mode": cell.trigger_mode,
            "decision_close_time": decision,
            "decision_year": int(row.decision_year),
            "h1_gap_long": row.h1_gap_long,
            "h1_gap_short": row.h1_gap_short,
            "m15_rsi14": row.m15_rsi14,
            "m15_ema20": row.m15_ema20,
            "m15_atr14": row.m15_atr14,
        }
        if decision < open_until:
            rows.append({**base, "admission_state": "SUPPRESSED_OPEN_POSITION", "resolution_state": "NOT_EVALUATED"})
            continue
        result = engine.evaluate(
            decision,
            float(row.m15_atr14),
            cell.direction,
            int(execution["horizon_minutes"]),
            float(execution["stop_r_multiple"]),
            float(execution["target_r_multiple"]),
        )
        rows.append({**base, **result})
        if result["admission_state"] == "ACCEPTED":
            open_until = pd.Timestamp(result["exit_time"]) if result["resolution_state"] == "RESOLVED" else pd.Timestamp.max
    return pd.DataFrame(rows)


def profit_factor(values: pd.Series) -> tuple[float | None, str]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    gross_profit = float(numeric[numeric > 0].sum())
    gross_loss = float(-numeric[numeric < 0].sum())
    if gross_loss > 0:
        return gross_profit / gross_loss, "FINITE"
    if gross_profit > 0:
        return None, "INFINITE_NO_LOSS"
    return None, "UNDEFINED"


def metric_row(candidate_id: str, year: int, group: pd.DataFrame) -> dict[str, Any]:
    accepted = group[group["admission_state"] == "ACCEPTED"] if not group.empty else group
    resolved = accepted[accepted["resolution_state"] == "RESOLVED"] if not accepted.empty else accepted
    r_values = pd.to_numeric(resolved.get("r_value", pd.Series(dtype=float)), errors="coerce").dropna()
    pf, pf_state = profit_factor(r_values)
    return {
        "candidate_id": candidate_id,
        "year": year,
        "raw_signal_count": int(len(group)),
        "accepted_count": int(len(accepted)),
        "resolved_count": int(len(resolved)),
        "unresolved_count": int((accepted.get("resolution_state", pd.Series(dtype=str)) == "UNRESOLVED").sum()),
        "suppressed_count": int((group.get("admission_state", pd.Series(dtype=str)) == "SUPPRESSED_OPEN_POSITION").sum()),
        "missing_entry_count": int((group.get("admission_state", pd.Series(dtype=str)) == "ENTRY_M1_MISSING").sum()),
        "wins": int((r_values > 0).sum()),
        "losses": int((r_values < 0).sum()),
        "mean_r": float(r_values.mean()) if len(r_values) else np.nan,
        "total_r": float(r_values.sum()) if len(r_values) else 0.0,
        "profit_factor": pf,
        "profit_factor_state": pf_state,
        "tp_count": int((resolved.get("outcome", pd.Series(dtype=str)) == "TP").sum()),
        "sl_count": int((resolved.get("outcome", pd.Series(dtype=str)) == "SL").sum()),
        "time_count": int((resolved.get("outcome", pd.Series(dtype=str)) == "TIME").sum()),
    }


def gate_pass(metric: dict[str, Any], gate: dict[str, Any]) -> tuple[bool, str]:
    count = int(metric["resolved_count"])
    mean_r = metric["mean_r"]
    pf_state = metric["profit_factor_state"]
    pf_value = metric["profit_factor"]
    pf_ok = pf_state == "INFINITE_NO_LOSS" or (pf_value is not None and float(pf_value) >= float(gate["minimum_profit_factor"]))
    checks = {
        "trade_count": count >= int(gate["minimum_trade_count"]),
        "profit_factor": pf_ok,
        "mean_r": pd.notna(mean_r) and float(mean_r) > float(gate["minimum_mean_r_exclusive"]),
    }
    reason = ";".join(name for name, passed in checks.items() if not passed) or "PASS"
    return all(checks.values()), reason


def run_exploration(raw_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    expected = config["input_contract"]["expected_sha256"]
    filenames = config["input_contract"]["raw_dir_filenames"]
    provenance: dict[str, Any] = {"raw_dir": str(raw_dir), "files": {}}
    bars: dict[str, pd.DataFrame] = {}
    for timeframe, filename in filenames.items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        digest = sha256_file(path)
        if digest != expected[filename]:
            raise ValueError(f"{filename} sha256 mismatch: {digest} != {expected[filename]}")
        frame = read_raw(path, timeframe)
        bars[timeframe] = frame
        provenance["files"][timeframe] = {
            "filename": filename,
            "sha256": digest,
            "rows": int(len(frame)),
            "first_open": str(frame["bar_open_time"].iloc[0]),
            "last_open": str(frame["bar_open_time"].iloc[-1]),
        }

    cells = build_cells(config)
    decisions = prepare_decisions(bars["M15"], bars["H1"])
    engine = DirectionalM1Engine(bars["M1"])
    trade_frames: list[pd.DataFrame] = []
    year_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []

    for cell in cells:
        trades = replay_cell(decisions, engine, cell, config["execution_contract"])
        trade_frames.append(trades)
        metrics_by_year: dict[int, dict[str, Any]] = {}
        for year in YEARS:
            group = trades[trades["decision_year"] == year] if not trades.empty else trades
            metric = metric_row(cell.candidate_id, year, group)
            metrics_by_year[year] = metric
            year_rows.append(metric)

        pass_2023, reason_2023 = gate_pass(metrics_by_year[2023], config["gates"]["2023_EXPLORATION"])
        pass_2024, reason_2024 = gate_pass(metrics_by_year[2024], config["gates"]["2024_VALIDATION"])
        pass_2025, reason_2025 = gate_pass(metrics_by_year[2025], config["gates"]["2025_FINAL_TEST"])
        survivor = pass_2023 and pass_2024 and pass_2025
        if not pass_2023:
            status = "REJECTED_WITH_REASON"
            reason = f"2023:{reason_2023}"
        elif not pass_2024:
            status = "RESEARCH_ONLY"
            reason = f"2024:{reason_2024}"
        elif not pass_2025:
            status = "RESEARCH_ONLY"
            reason = f"2025:{reason_2025}"
        else:
            status = "RESEARCH_ONLY"
            reason = "ALL_PREDECLARED_GATES_PASS_PENDING_SEPARATE_ACCUMULATION_REVIEW"
        attempt = {
            "candidate_id": cell.candidate_id,
            "lineage_id": "M15_H1_TREND_PULLBACK_LINEAGE_EXP024",
            "direction": cell.direction,
            "h1_gap_atr_min": cell.h1_gap_atr_min,
            "rsi_long_level": cell.rsi_long_level,
            "trigger_mode": cell.trigger_mode,
            "gate_2023": "PASS" if pass_2023 else "FAIL",
            "gate_2024": "PASS" if pass_2024 else "FAIL",
            "gate_2025": "PASS" if pass_2025 else "FAIL",
            "diagnostic_2026": "REPORTED_NO_GATE",
            "survivor": survivor,
            "candidate_status": status,
            "status_reason": reason,
            "automatic_accumulation": False,
        }
        attempt_rows.append(attempt)
        if survivor:
            survivors.append(attempt)

    trade_registry = pd.concat(trade_frames, ignore_index=True, sort=False) if trade_frames else pd.DataFrame()
    attempt_registry = pd.DataFrame(attempt_rows)
    year_metrics = pd.DataFrame(year_rows)
    survivor_frame = pd.DataFrame(survivors, columns=attempt_registry.columns)
    if len(attempt_registry) != int(config["multiplicity_contract"]["attempted_cells"]):
        raise RuntimeError("Attempt registry does not contain every predeclared cell")
    return {
        "cells": cells,
        "attempt_registry": attempt_registry,
        "year_metrics": year_metrics,
        "trade_registry": trade_registry,
        "survivors": survivor_frame,
        "provenance": provenance,
        "decision_rows": int(len(decisions)),
    }


def json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_clean(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(float(value)) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    if value is None or pd.isna(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(json_clean(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
