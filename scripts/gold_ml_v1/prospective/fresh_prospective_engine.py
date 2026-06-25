from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

POINT = 0.01
CUTOFF_DEFAULT = pd.Timestamp("2026-06-23 18:15:00")
TF_DELTA = {
    "M1": pd.Timedelta(minutes=1),
    "M15": pd.Timedelta(minutes=15),
    "H1": pd.Timedelta(hours=1),
    "H4": pd.Timedelta(hours=4),
    "D1": pd.Timedelta(days=1),
}
FILE_BY_TF = {
    "M1": "goldsharp_m1.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
CANDIDATE_IDS = [
    "GML1-PROV-007",
    "GML1-PROV-008",
    "GML1-WATCH-022-B",
    "GML1-PROV-010",
    "GML1-PROV-015",
    "GML1-PROV-020",
    "GML1-WATCH-021-A",
    "GML1-WATCH-021-B",
    "GML1-WATCH-021-C",
]
LINEAGE_BY_CANDIDATE = {
    "GML1-PROV-007": "M15_H4_BREAKOUT_FILTER_LINEAGE",
    "GML1-PROV-008": "M15_H4_BREAKOUT_FILTER_LINEAGE",
    "GML1-WATCH-022-B": "M15_H4_BREAKOUT_FILTER_LINEAGE",
    "GML1-PROV-010": "H1_D1_BREAKOUT_FILTER_LINEAGE",
    "GML1-PROV-015": "H1_D1_BREAKOUT_FILTER_LINEAGE",
    "GML1-PROV-020": "H1_D1_BREAKOUT_FILTER_LINEAGE",
    "GML1-WATCH-021-A": "H1_D1_BREAKOUT_FILTER_LINEAGE",
    "GML1-WATCH-021-B": "H1_D1_BREAKOUT_FILTER_LINEAGE",
    "GML1-WATCH-021-C": "H1_D1_BREAKOUT_FILTER_LINEAGE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_column(value: str) -> str:
    return (
        str(value)
        .replace("\ufeff", "")
        .strip()
        .strip("<>")
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _read_delimited(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16", "cp932"):
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=encoding)
        except Exception as exc:  # pragma: no cover - retained for local diagnostics
            errors.append(f"{encoding}:{type(exc).__name__}:{exc}")
    raise ValueError(f"Could not parse {path}: {' | '.join(errors)}")


def read_closed_bars(path: Path, timeframe: str) -> pd.DataFrame:
    if timeframe not in TF_DELTA:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if not path.exists():
        raise FileNotFoundError(path)

    raw = _read_delimited(path)
    raw.columns = [canonical_column(column) for column in raw.columns]
    aliases = {
        "tickvol": "tick_volume",
        "tickvolume": "tick_volume",
        "tick_vol": "tick_volume",
        "realvolume": "real_volume",
        "real_vol": "real_volume",
    }
    raw = raw.rename(columns={column: aliases.get(column, column) for column in raw.columns})

    if "date" in raw.columns and "time" in raw.columns:
        timestamp_text = raw["date"].astype(str).str.strip() + " " + raw["time"].astype(str).str.strip()
    elif "datetime" in raw.columns:
        timestamp_text = raw["datetime"].astype(str).str.strip()
    elif "timestamp" in raw.columns:
        timestamp_text = raw["timestamp"].astype(str).str.strip()
    elif "time" in raw.columns:
        timestamp_text = raw["time"].astype(str).str.strip()
    else:
        raise ValueError(f"{path}: no time/datetime column")

    required_numeric = ["open", "high", "low", "close", "tick_volume", "spread"]
    missing = [column for column in required_numeric if column not in raw.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")

    frame = pd.DataFrame(index=raw.index)
    frame["bar_open_time"] = pd.to_datetime(timestamp_text, errors="coerce")
    for column in required_numeric:
        frame[column] = pd.to_numeric(raw[column], errors="coerce")
    if "real_volume" in raw.columns:
        frame["real_volume"] = pd.to_numeric(raw["real_volume"], errors="coerce")
    else:
        frame["real_volume"] = 0.0

    valid = frame[["bar_open_time", *required_numeric]].notna().all(axis=1)
    if not bool(valid.all()):
        first_invalid_position = int(np.flatnonzero(~valid.to_numpy())[0])
        if bool(valid.iloc[first_invalid_position:].any()):
            bad_rows = frame.index[~valid].tolist()[:10]
            raise ValueError(f"{path}: incomplete or invalid non-trailing rows {bad_rows}")
        frame = frame.iloc[:first_invalid_position].copy()

    if frame.empty:
        raise ValueError(f"{path}: no complete rows")
    if frame["bar_open_time"].duplicated().any():
        duplicates = frame.loc[frame["bar_open_time"].duplicated(), "bar_open_time"].head().tolist()
        raise ValueError(f"{path}: duplicate times {duplicates}")
    if not frame["bar_open_time"].is_monotonic_increasing:
        raise ValueError(f"{path}: time is not monotonic increasing; silent sorting is forbidden")

    frame = frame.reset_index(drop=True)
    frame["bar_close_time"] = frame["bar_open_time"] + TF_DELTA[timeframe]
    frame["timeframe"] = timeframe
    return frame


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr_simple(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(frame).rolling(period, min_periods=period).mean()


def atr_wilder(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(frame).to_numpy(float)
    values = np.full(len(tr), np.nan)
    if len(tr) >= period:
        values[period - 1] = float(np.mean(tr[:period]))
        for index in range(period, len(tr)):
            values[index] = (values[index - 1] * (period - 1) + tr[index]) / period
    return pd.Series(values, index=frame.index)


def rci_rank_difference(series: pd.Series, period: int = 18) -> pd.Series:
    def calculate(window: np.ndarray) -> float:
        price_rank = pd.Series(window).rank(method="average").to_numpy(float)
        time_rank = np.arange(1, len(window) + 1, dtype=float)
        difference = time_rank - price_rank
        return float(
            (
                1.0
                - 6.0
                * np.sum(difference * difference)
                / (len(window) * (len(window) ** 2 - 1))
            )
            * 100.0
        )

    return series.rolling(period, min_periods=period).apply(calculate, raw=True)


def trailing_percentile_current(window: np.ndarray) -> float:
    values = np.asarray(window, dtype=float)
    return float(np.mean(values <= values[-1]))


@dataclass(frozen=True)
class EvaluationContract:
    horizon_hours: int
    hit_exit_time: str
    time_exit_time: str


class ProspectiveM1Engine:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.times = pd.DatetimeIndex(frame["bar_open_time"]).asi8
        self.opens = frame["open"].to_numpy(float)
        self.highs = frame["high"].to_numpy(float)
        self.lows = frame["low"].to_numpy(float)
        self.closes = frame["close"].to_numpy(float)
        self.spreads = frame["spread"].to_numpy(float)
        self.latest_close = pd.Timestamp(self.times[-1] + int(TF_DELTA["M1"].value))

    def has_exact_entry(self, timestamp: pd.Timestamp) -> bool:
        value = pd.Timestamp(timestamp).value
        index = int(np.searchsorted(self.times, value, side="left"))
        return index < len(self.times) and int(self.times[index]) == value

    def evaluate(
        self,
        decision: pd.Timestamp,
        atr: float,
        contract: EvaluationContract,
    ) -> dict[str, Any]:
        decision = pd.Timestamp(decision)
        if not np.isfinite(atr) or atr <= 0:
            return {
                "prospective_state": "INVALID_ATR",
                "resolution_state": "NOT_EVALUATED",
                "entry_time": decision,
            }
        start = int(np.searchsorted(self.times, decision.value, side="left"))
        if start >= len(self.times) or int(self.times[start]) != decision.value:
            return {
                "prospective_state": "ENTRY_M1_MISSING",
                "resolution_state": "NOT_EVALUATED",
                "entry_time": decision,
            }

        horizon_end = decision + pd.Timedelta(hours=contract.horizon_hours)
        available_end = min(horizon_end, self.latest_close)
        end = int(np.searchsorted(self.times, available_end.value, side="left"))
        if end <= start:
            return {
                "prospective_state": "UNRESOLVED",
                "resolution_state": "UNRESOLVED",
                "entry_time": decision,
                "horizon_end_time": horizon_end,
                "latest_observed_close_time": self.latest_close,
            }

        entry_price = float(self.opens[start] + self.spreads[start] * POINT)
        stop_price = entry_price - atr
        target_price = entry_price + atr
        stop_hits = np.flatnonzero(self.lows[start:end] <= stop_price)
        target_hits = np.flatnonzero(self.highs[start:end] >= target_price)
        has_stop = len(stop_hits) > 0
        has_target = len(target_hits) > 0

        def stored_time(index: int, mode: str) -> pd.Timestamp:
            offset = int(TF_DELTA["M1"].value) if mode == "close" else 0
            return pd.Timestamp(self.times[index] + offset)

        base = {
            "entry_time": decision,
            "entry_price": entry_price,
            "risk_price": float(atr),
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "horizon_end_time": horizon_end,
            "latest_observed_close_time": self.latest_close,
        }
        if has_stop and (not has_target or int(stop_hits[0]) <= int(target_hits[0])):
            index = start + int(stop_hits[0])
            return {
                **base,
                "prospective_state": "RESOLVED",
                "resolution_state": "RESOLVED",
                "outcome": "SL",
                "exit_time": stored_time(index, contract.hit_exit_time),
                "exit_price": float(stop_price),
                "r_value": -1.0,
                "current_r": -1.0,
            }
        if has_target:
            index = start + int(target_hits[0])
            return {
                **base,
                "prospective_state": "RESOLVED",
                "resolution_state": "RESOLVED",
                "outcome": "TP",
                "exit_time": stored_time(index, contract.hit_exit_time),
                "exit_price": float(target_price),
                "r_value": 1.0,
                "current_r": 1.0,
            }
        if horizon_end <= self.latest_close:
            index = end - 1
            exit_price = float(self.closes[index])
            r_value = float((exit_price - entry_price) / atr)
            return {
                **base,
                "prospective_state": "RESOLVED",
                "resolution_state": "RESOLVED",
                "outcome": "TIME_POS"
                if r_value > 0
                else ("TIME_NEG" if r_value < 0 else "TIME_ZERO"),
                "exit_time": stored_time(index, contract.time_exit_time),
                "exit_price": exit_price,
                "r_value": r_value,
                "current_r": r_value,
            }

        current_price = float(self.closes[end - 1])
        current_r = float((current_price - entry_price) / atr)
        return {
            **base,
            "prospective_state": "UNRESOLVED",
            "resolution_state": "UNRESOLVED",
            "outcome": "OPEN",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "r_value": np.nan,
            "current_price": current_price,
            "current_r": current_r,
        }


def evaluate_parent_events(
    events: pd.DataFrame,
    engine: ProspectiveM1Engine,
    atr_column: str,
    feature_columns: list[str],
    contract: EvaluationContract,
    parent_lineage: str,
    cutoff: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    accepted: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min

    for event in events.sort_values("bar_close_time", kind="mergesort").itertuples(index=False):
        decision = pd.Timestamp(event.bar_close_time)
        feature_values = {column: getattr(event, column) for column in feature_columns}
        if decision < open_until:
            if decision > cutoff:
                audit.append(
                    {
                        "parent_lineage": parent_lineage,
                        "decision_close_time": decision,
                        "admission_state": "SUPPRESSED_BY_FROZEN_NON_OVERLAP",
                        "suppression_until": open_until,
                        **feature_values,
                    }
                )
            continue

        evaluated = engine.evaluate(
            decision,
            float(getattr(event, atr_column)),
            contract,
        )
        state = str(evaluated["prospective_state"])
        if state in {"ENTRY_M1_MISSING", "INVALID_ATR"}:
            if decision > cutoff:
                audit.append(
                    {
                        "parent_lineage": parent_lineage,
                        "decision_close_time": decision,
                        "admission_state": state,
                        **feature_values,
                    }
                )
            continue

        row = {
            "parent_lineage": parent_lineage,
            "decision_close_time": decision,
            "direction": "LONG",
            **feature_values,
            **evaluated,
        }
        accepted.append(row)
        if decision > cutoff:
            audit.append(
                {
                    **row,
                    "admission_state": "ACCEPTED_PARENT_EVENT",
                }
            )

        if state == "RESOLVED":
            open_until = pd.Timestamp(evaluated["exit_time"])
        else:
            open_until = pd.Timestamp.max

    return pd.DataFrame(accepted), pd.DataFrame(audit)


def _candidate_rows(
    accepted: pd.DataFrame,
    candidate_id: str,
    keep: pd.Series,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    if accepted.empty:
        return pd.DataFrame()
    selected = accepted.loc[keep & (accepted["decision_close_time"] > cutoff)].copy()
    if selected.empty:
        return selected
    selected["candidate_id"] = candidate_id
    selected["lineage_id"] = LINEAGE_BY_CANDIDATE[candidate_id]
    selected["candidate_rule_state"] = "FROZEN_RULE_MATCH"
    return selected


def build_candidate_registry(
    bars: dict[str, pd.DataFrame],
    cutoff: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    m1 = bars["M1"].copy()
    m15 = bars["M15"].copy()
    h1 = bars["H1"].copy()
    h4 = bars["H4"].copy()
    d1 = bars["D1"].copy()
    engine = ProspectiveM1Engine(m1)

    m15["atr14"] = atr_simple(m15, 14)
    for period in (20, 60):
        mean = m15["close"].rolling(period, min_periods=period).mean()
        standard_deviation = m15["close"].rolling(period, min_periods=period).std(ddof=0)
        m15[f"bb{period}_width_atr"] = 4.0 * standard_deviation / m15["atr14"]
    m15["bb60_width_pct100"] = m15["bb60_width_atr"].rolling(
        100, min_periods=100
    ).apply(trailing_percentile_current, raw=True)

    h4["atr_state"] = atr_simple(h4, 14)
    h4["atr_slope"] = atr_wilder(h4, 14)
    h4["rci18"] = rci_rank_difference(h4["close"], 18)
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    range_price = (h4["high"] - h4["low"]).replace(0, np.nan)
    h4["upper_wick_frac"] = (
        h4["high"] - h4[["open", "close"]].max(axis=1)
    ) / range_price
    h4["ema40_slope6_atr"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4[
        "atr_slope"
    ]
    h4["spread_atr"] = h4["spread"] * POINT / h4["atr_state"]

    h4_features = h4[
        [
            "bar_close_time",
            "rci18",
            "spread_atr",
            "upper_wick_frac",
            "ema40_slope6_atr",
        ]
    ].dropna()
    if h4_features.empty:
        raise ValueError("H4 indicator state is unavailable; prospective run is blocked")
    m15_joined = pd.merge_asof(
        m15,
        h4_features,
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    m15_joined["state"] = (m15_joined["rci18"] >= 73.993808) & (
        m15_joined["spread_atr"] <= 0.012772
    )
    m15_joined["eligible"] = m15_joined["bar_close_time"].map(engine.has_exact_entry)
    active = m15_joined["state"] & m15_joined["eligible"]
    m15_joined["event"] = active & ~active.shift(fill_value=False)

    accepted_m15, audit_m15 = evaluate_parent_events(
        m15_joined[m15_joined["event"]],
        engine,
        "atr14",
        [
            "upper_wick_frac",
            "ema40_slope6_atr",
            "bb20_width_atr",
            "bb60_width_pct100",
        ],
        EvaluationContract(6, "close", "close"),
        "M15_H4_PARENT",
        cutoff,
    )

    candidate_frames: list[pd.DataFrame] = []
    if not accepted_m15.empty:
        keep_p7 = ~(
            (accepted_m15["upper_wick_frac"] >= 0.27488556398168634)
            & (accepted_m15["ema40_slope6_atr"] >= 0.6863028800058267)
        )
        keep_p8 = ~(
            (accepted_m15["bb20_width_atr"] <= 3.3719018700718184)
            & (accepted_m15["bb60_width_pct100"] <= 0.536)
        )
        keep_w22 = keep_p7 & ~(
            (accepted_m15["upper_wick_frac"] <= 0.06526044468913629)
            & (accepted_m15["ema40_slope6_atr"] >= 0.8700779249713114)
        )
        candidate_frames.extend(
            [
                _candidate_rows(accepted_m15, "GML1-PROV-007", keep_p7, cutoff),
                _candidate_rows(accepted_m15, "GML1-PROV-008", keep_p8, cutoff),
                _candidate_rows(accepted_m15, "GML1-WATCH-022-B", keep_w22, cutoff),
            ]
        )

    h1["atr14"] = atr_wilder(h1, 14)
    h1_mean = h1["close"].rolling(60, min_periods=60).mean()
    h1_sd = h1["close"].rolling(60, min_periods=60).std(ddof=0)
    h1["bb60_upper"] = h1_mean + 2.0 * h1_sd
    h1["spread_atr"] = h1["spread"] * POINT / h1["atr14"]

    d1["atr14"] = atr_wilder(d1, 14)
    d1["rci18"] = rci_rank_difference(d1["close"], 18)
    d1["tickvol_ratio50"] = d1["tick_volume"] / d1["tick_volume"].rolling(
        50, min_periods=50
    ).median()
    d1["delta_atr_3"] = (d1["close"] - d1["close"].shift(3)) / d1["atr14"]

    d1_features = d1[
        ["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]
    ].dropna()
    if d1_features.empty:
        raise ValueError("D1 indicator state is unavailable; prospective run is blocked")
    h1_joined = pd.merge_asof(
        h1,
        d1_features,
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    h1_joined["event"] = (
        (h1_joined["close"].shift(1) <= h1_joined["bb60_upper"].shift(1))
        & (h1_joined["close"] > h1_joined["bb60_upper"])
        & (h1_joined["rci18"] >= 0)
    )

    accepted_h1, audit_h1 = evaluate_parent_events(
        h1_joined[h1_joined["event"]],
        engine,
        "atr14",
        ["tickvol_ratio50", "delta_atr_3", "spread_atr"],
        EvaluationContract(48, "open", "open"),
        "H1_D1_PARENT",
        cutoff,
    )
    if not accepted_h1.empty:
        accepted_h1 = accepted_h1.rename(
            columns={
                "tickvol_ratio50": "htf_tickvol_ratio50",
                "delta_atr_3": "htf_delta_atr_3",
                "spread_atr": "ltf_spread_atr",
            }
        )
        accepted_h1["ltf_hour"] = accepted_h1["decision_close_time"].dt.hour.astype(float)
        keep_p10 = pd.Series(True, index=accepted_h1.index)
        keep_p15 = ~(
            (accepted_h1["htf_tickvol_ratio50"] <= 0.876789995391398)
            & (accepted_h1["htf_delta_atr_3"] <= 0.2256991669382677)
        )
        keep_p20 = keep_p15 & ~(
            accepted_h1["ltf_hour"].between(8, 16)
            & (accepted_h1["ltf_spread_atr"] >= 0.0308778597897866)
        )

        h1_path = h1[
            ["bar_close_time", "open", "high", "low", "close", "atr14"]
        ].copy()
        h1_path["range_atr"] = (h1_path["high"] - h1_path["low"]) / h1_path[
            "atr14"
        ]
        h1_path["close_pos"] = (h1_path["close"] - h1_path["low"]) / (
            h1_path["high"] - h1_path["low"]
        ).replace(0, np.nan)
        h1_path["range_atr_lag1"] = h1_path["range_atr"].shift(1)
        h1_path["close_pos_lag5"] = h1_path["close_pos"].shift(5)
        h1_path["range_atr_lag10"] = h1_path["range_atr"].shift(10)
        h1_path["span_atr_12"] = (
            h1_path["high"].rolling(12).max() - h1_path["low"].rolling(12).min()
        ) / h1_path["atr14"]
        accepted_h1 = accepted_h1.merge(
            h1_path[
                [
                    "bar_close_time",
                    "range_atr_lag1",
                    "span_atr_12",
                    "close_pos_lag5",
                    "range_atr_lag10",
                ]
            ],
            left_on="decision_close_time",
            right_on="bar_close_time",
            how="left",
        ).drop(columns=["bar_close_time"])
        keep_a = keep_p15.to_numpy() & ~(
            (accepted_h1["range_atr_lag1"] <= 0.6571970935503249)
            & (accepted_h1["span_atr_12"] >= 5.058013327710588)
        )
        keep_b = keep_p15.to_numpy() & ~(
            (accepted_h1["close_pos_lag5"] <= 0.424089068826)
            & (accepted_h1["range_atr_lag10"] >= 1.17215632583)
        )
        keep_a = pd.Series(keep_a, index=accepted_h1.index)
        keep_b = pd.Series(keep_b, index=accepted_h1.index)
        keep_p10 = pd.Series(True, index=accepted_h1.index)
        keep_p15 = ~(
            (accepted_h1["htf_tickvol_ratio50"] <= 0.876789995391398)
            & (accepted_h1["htf_delta_atr_3"] <= 0.2256991669382677)
        )
        keep_p20 = keep_p15 & ~(
            accepted_h1["ltf_hour"].between(8, 16)
            & (accepted_h1["ltf_spread_atr"] >= 0.0308778597897866)
        )
        candidate_frames.extend(
            [
                _candidate_rows(accepted_h1, "GML1-PROV-010", keep_p10, cutoff),
                _candidate_rows(accepted_h1, "GML1-PROV-015", keep_p15, cutoff),
                _candidate_rows(accepted_h1, "GML1-PROV-020", keep_p20, cutoff),
                _candidate_rows(accepted_h1, "GML1-WATCH-021-A", keep_a, cutoff),
                _candidate_rows(accepted_h1, "GML1-WATCH-021-B", keep_b, cutoff),
                _candidate_rows(accepted_h1, "GML1-WATCH-021-C", keep_a & keep_b, cutoff),
            ]
        )

    nonempty = [frame for frame in candidate_frames if not frame.empty]
    if nonempty:
        candidates = pd.concat(nonempty, ignore_index=True, sort=False)
        candidates = candidates.sort_values(
            ["decision_close_time", "candidate_id"], kind="mergesort"
        ).reset_index(drop=True)
    else:
        candidates = pd.DataFrame(
            columns=[
                "candidate_id",
                "lineage_id",
                "decision_close_time",
                "entry_time",
                "prospective_state",
                "resolution_state",
                "outcome",
                "r_value",
                "current_r",
            ]
        )

    audits = [frame for frame in (audit_m15, audit_h1) if not frame.empty]
    parent_audit = (
        pd.concat(audits, ignore_index=True, sort=False)
        .sort_values(["decision_close_time", "parent_lineage"], kind="mergesort")
        .reset_index(drop=True)
        if audits
        else pd.DataFrame(
            columns=["parent_lineage", "decision_close_time", "admission_state"]
        )
    )

    coverage = {
        "cutoff_mt5_server_close": str(cutoff),
        "latest_m1_close": str(engine.latest_close),
        "post_cutoff_parent_event_count": int(len(parent_audit)),
        "post_cutoff_accepted_parent_count": int(
            (parent_audit.get("admission_state", pd.Series(dtype=str)) == "ACCEPTED_PARENT_EVENT").sum()
        ),
        "post_cutoff_candidate_row_count": int(len(candidates)),
    }
    return candidates, parent_audit, coverage


def candidate_summary(candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate_id in CANDIDATE_IDS:
        group = candidates[candidates["candidate_id"] == candidate_id].copy()
        resolved = group[group["resolution_state"] == "RESOLVED"]
        unresolved = group[group["resolution_state"] == "UNRESOLVED"]
        positive = pd.to_numeric(resolved.get("r_value", pd.Series(dtype=float)), errors="coerce")
        wins = int((positive > 0).sum())
        losses = int((positive < 0).sum())
        gross_profit = float(positive[positive > 0].sum())
        gross_loss = float(-positive[positive < 0].sum())
        if gross_loss > 0:
            pf: float | None = gross_profit / gross_loss
            pf_state = "FINITE"
        elif gross_profit > 0:
            pf = None
            pf_state = "INFINITE_NO_LOSS"
        else:
            pf = None
            pf_state = "UNDEFINED_NO_RESOLVED_EDGE"
        if len(group) == 0:
            observation = "NO_CANDIDATE_YET"
        elif len(unresolved) == len(group):
            observation = "UNRESOLVED_ONLY"
        elif len(unresolved) > 0:
            observation = "RESOLVED_AND_UNRESOLVED"
        else:
            observation = "RESOLVED_ONLY"
        rows.append(
            {
                "candidate_id": candidate_id,
                "lineage_id": LINEAGE_BY_CANDIDATE[candidate_id],
                "candidate_count": int(len(group)),
                "resolved_count": int(len(resolved)),
                "unresolved_count": int(len(unresolved)),
                "wins": wins,
                "losses": losses,
                "tp_count": int((resolved.get("outcome", pd.Series(dtype=str)) == "TP").sum()),
                "sl_count": int((resolved.get("outcome", pd.Series(dtype=str)) == "SL").sum()),
                "time_exit_count": int(
                    resolved.get("outcome", pd.Series(dtype=str)).astype(str).str.startswith("TIME").sum()
                ),
                "mean_resolved_r": float(positive.mean()) if len(positive) else np.nan,
                "total_resolved_r": float(positive.sum()) if len(positive) else 0.0,
                "profit_factor": pf,
                "profit_factor_state": pf_state,
                "observation_state": observation,
                "performance_gate": "NOT_APPLICABLE_PROSPECTIVE_AUDIT_ONLY",
            }
        )
    return pd.DataFrame(rows)


def load_inputs(files_dir: Path, cutoff: pd.Timestamp) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    bars: dict[str, pd.DataFrame] = {}
    provenance: dict[str, Any] = {
        "files_dir": str(files_dir),
        "cutoff_mt5_server_close": str(cutoff),
        "latest_rows_closed_by_contract": True,
        "files": {},
    }
    for timeframe, filename in FILE_BY_TF.items():
        path = files_dir / filename
        frame = read_closed_bars(path, timeframe)
        if pd.Timestamp(frame["bar_close_time"].iloc[-1]) <= cutoff:
            raise ValueError(
                f"{filename}: no closed bar strictly after cutoff {cutoff}; prospective coverage unavailable"
            )
        bars[timeframe] = frame
        provenance["files"][timeframe] = {
            "filename": filename,
            "path": str(path),
            "sha256": sha256_file(path),
            "row_count": int(len(frame)),
            "first_bar_open_time": str(frame["bar_open_time"].iloc[0]),
            "last_bar_open_time": str(frame["bar_open_time"].iloc[-1]),
            "last_bar_close_time": str(frame["bar_close_time"].iloc[-1]),
        }
    return bars, provenance


def clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(float(value)) else float(value)
    if pd.isna(value):
        return None
    return value


def run_engine(files_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    cutoff = pd.Timestamp(config.get("cutoff_mt5_server_close", CUTOFF_DEFAULT))
    bars, provenance = load_inputs(files_dir, cutoff)
    candidates, parent_audit, coverage = build_candidate_registry(bars, cutoff)
    summary = candidate_summary(candidates)
    if len(candidates) == 0:
        observation_state = "NO_CANDIDATE_YET"
    elif bool((candidates["resolution_state"] == "UNRESOLVED").any()):
        observation_state = "CANDIDATES_PRESENT_WITH_UNRESOLVED"
    else:
        observation_state = "CANDIDATES_PRESENT_ALL_CURRENTLY_RESOLVED"
    return {
        "status": "PASS",
        "observation_state": observation_state,
        "cutoff_mt5_server_close": cutoff,
        "candidates": candidates,
        "parent_audit": parent_audit,
        "candidate_summary": summary,
        "coverage": coverage,
        "provenance": provenance,
        "policy": {
            "audit_only": True,
            "candidate_generation_uses_future_exit_information": False,
            "unresolved_candidates_preserved": True,
            "suppressed_parent_events_recorded": True,
            "candidate_rules_frozen": True,
            "retuning": False,
            "automatic_promotion": False,
            "live_ready": False,
            "final_signal": False,
            "mt5_order": False,
            "discord": False,
            "ai_api": False,
            "live_hook": False,
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(clean_json_value(value), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
