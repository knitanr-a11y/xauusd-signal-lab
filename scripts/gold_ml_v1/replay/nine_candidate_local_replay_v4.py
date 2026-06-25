from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

V3_PATH = Path(__file__).with_name("nine_candidate_local_replay_v3.py")
SPEC = importlib.util.spec_from_file_location("gml1_batch023_v3", V3_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load replay v3 module: {V3_PATH}")
v3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v3
SPEC.loader.exec_module(v3)

v2 = v3.v2
base = v3.base
RCI_THRESHOLD = 73.993808
SPREAD_ATR_THRESHOLD = 0.012772


def atr_wilder_local(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = frame["close"].shift(1)
    tr = pd.concat([
        (frame["high"] - frame["low"]).abs(),
        (frame["high"] - prev_close).abs(),
        (frame["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    if len(tr) >= period:
        out.iloc[period - 1] = tr.iloc[:period].mean()
        for i in range(period, len(tr)):
            out.iloc[i] = (out.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period
    return out


def rci_variant(series: pd.Series, period: int, rank_method: str, formula: str) -> pd.Series:
    time_rank = np.arange(1, period + 1, dtype=float)
    time_centered = time_rank - time_rank.mean()
    time_norm = np.sqrt(np.sum(time_centered * time_centered))

    def calculate(values: np.ndarray) -> float:
        ranks = pd.Series(values).rank(method=rank_method).to_numpy(dtype=float)
        if formula == "d2":
            diff = time_rank - ranks
            return float((1.0 - 6.0 * np.sum(diff * diff) / (period * (period * period - 1.0))) * 100.0)
        if formula == "corr":
            centered = ranks - ranks.mean()
            denominator = time_norm * np.sqrt(np.sum(centered * centered))
            return 0.0 if denominator <= 0 else float(np.sum(time_centered * centered) / denominator * 100.0)
        raise ValueError(formula)

    return series.rolling(period, min_periods=period).apply(calculate, raw=True)


def price_source(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in {"open", "high", "low", "close"}:
        return frame[name]
    if name == "hl2":
        return (frame["high"] + frame["low"]) / 2.0
    if name == "hlc3":
        return (frame["high"] + frame["low"] + frame["close"]) / 3.0
    if name == "ohlc4":
        return (frame["open"] + frame["high"] + frame["low"] + frame["close"]) / 4.0
    raise ValueError(name)


def ema_variant(series: pd.Series, name: str, period: int = 40) -> pd.Series:
    if name == "ewm_adjust_false":
        return series.ewm(span=period, adjust=False).mean()
    if name == "ewm_adjust_true":
        return series.ewm(span=period, adjust=True).mean()
    if name == "sma":
        return series.rolling(period, min_periods=1).mean()
    raise ValueError(name)


def percentile_variant(series: pd.Series, window: int, mode: str) -> pd.Series:
    def calc(values: np.ndarray) -> float:
        values = np.asarray(values, dtype=float)
        last = values[-1]
        if mode == "le":
            return float(np.mean(values <= last))
        if mode == "lt":
            return float(np.mean(values < last))
        if mode == "rank_average":
            return float(pd.Series(values).rank(method="average", pct=True).iloc[-1])
        if mode == "rank_min":
            return float(pd.Series(values).rank(method="min", pct=True).iloc[-1])
        if mode == "rank_max":
            return float(pd.Series(values).rank(method="max", pct=True).iloc[-1])
        raise ValueError(mode)

    return series.rolling(window, min_periods=window).apply(calc, raw=True)


@dataclass
class FastM1Engine:
    times: np.ndarray
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    spreads: np.ndarray

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "FastM1Engine":
        ordered = frame.sort_values("bar_open_time", kind="mergesort").reset_index(drop=True)
        return cls(
            times=pd.DatetimeIndex(ordered["bar_open_time"]).asi8,
            opens=ordered["open"].to_numpy(float),
            highs=ordered["high"].to_numpy(float),
            lows=ordered["low"].to_numpy(float),
            closes=ordered["close"].to_numpy(float),
            spreads=ordered["spread"].to_numpy(float),
        )

    @property
    def latest_close(self) -> pd.Timestamp:
        return pd.Timestamp(self.times[-1] + 60_000_000_000)

    def has_exact_entry(self, when: pd.Timestamp) -> bool:
        value = pd.Timestamp(when).value
        idx = int(np.searchsorted(self.times, value, side="left"))
        return idx < len(self.times) and int(self.times[idx]) == value

    def evaluate(self, decision: pd.Timestamp, atr: float, horizon_hours: int) -> dict[str, Any] | None:
        if not np.isfinite(atr) or atr <= 0:
            return None
        decision = pd.Timestamp(decision)
        start = int(np.searchsorted(self.times, decision.value, side="left"))
        if start >= len(self.times) or int(self.times[start]) != decision.value:
            return None
        horizon_end = decision + pd.Timedelta(hours=horizon_hours)
        if horizon_end > self.latest_close:
            return None
        end = int(np.searchsorted(self.times, horizon_end.value, side="left"))
        if end <= start:
            return None
        entry = float(self.opens[start] + self.spreads[start] * base.POINT)
        sl = entry - atr
        tp = entry + atr
        sl_hits = np.flatnonzero(self.lows[start:end] <= sl)
        tp_hits = np.flatnonzero(self.highs[start:end] >= tp)
        first_sl = int(sl_hits[0]) if len(sl_hits) else math.inf
        first_tp = int(tp_hits[0]) if len(tp_hits) else math.inf
        if first_sl <= first_tp:
            idx = start + int(first_sl)
            return {"entry_time": decision, "entry_price": entry, "exit_time": pd.Timestamp(self.times[idx]), "exit_price": float(sl), "r_value": -1.0, "outcome": "SL"}
        if first_tp < first_sl:
            idx = start + int(first_tp)
            return {"entry_time": decision, "entry_price": entry, "exit_time": pd.Timestamp(self.times[idx]), "exit_price": float(tp), "r_value": 1.0, "outcome": "TP"}
        idx = end - 1
        exit_price = float(self.closes[idx])
        r_value = (exit_price - entry) / atr
        return {
            "entry_time": decision,
            "entry_price": entry,
            "exit_time": pd.Timestamp(self.times[idx] + 60_000_000_000),
            "exit_price": exit_price,
            "r_value": float(r_value),
            "outcome": "TIME_POS" if r_value > 0 else ("TIME_NEG" if r_value < 0 else "TIME_ZERO"),
        }


def evaluate_events_fast(events: pd.DataFrame, engine: FastM1Engine, horizon_hours: int, extra_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min
    for _, event in events.sort_values("bar_close_time", kind="mergesort").iterrows():
        decision = pd.Timestamp(event["bar_close_time"])
        if decision < open_until:
            continue
        trade = engine.evaluate(decision, float(event["atr14"]), horizon_hours)
        if trade is None:
            continue
        trade.update({"decision_close_time": decision, "direction": "LONG"})
        for column in extra_columns:
            trade[column] = event[column]
        rows.append(trade)
        open_until = pd.Timestamp(trade["exit_time"])
    return pd.DataFrame(rows)


def max_abs_diff(a: pd.Series, b: pd.Series) -> float:
    values = np.abs(pd.to_numeric(a).to_numpy(float) - pd.to_numeric(b).to_numpy(float))
    return float(np.nanmax(values)) if len(values) else math.inf


def resolve_h4_geometry_contract(h4: pd.DataFrame, expected_p7: pd.DataFrame) -> dict[str, Any]:
    expected = expected_p7[["bar_close_time", "upper_wick_frac", "ema40_slope6_atr"]].copy()
    expected["bar_close_time"] = pd.to_datetime(expected["bar_close_time"])
    candidates: list[dict[str, Any]] = []
    for atr_name in ["sma14_min1", "sma14_full", "wilder14"]:
        if atr_name == "sma14_min1":
            prev = h4["close"].shift(1)
            tr = pd.concat([(h4["high"]-h4["low"]).abs(), (h4["high"]-prev).abs(), (h4["low"]-prev).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14, min_periods=1).mean()
        elif atr_name == "sma14_full":
            atr = v2.atr_simple_rolling(h4, 14)
        else:
            atr = atr_wilder_local(h4, 14)
        for ema_name in ["ewm_adjust_false", "ewm_adjust_true", "sma"]:
            frame = h4[["bar_close_time", "open", "high", "low", "close"]].copy()
            frame["atr"] = atr
            frame["ema"] = ema_variant(h4["close"], ema_name, 40)
            frame["wick"] = (frame["high"] - frame[["open", "close"]].max(axis=1)) / (frame["high"] - frame["low"]).replace(0, np.nan)
            frame["slope"] = (frame["ema"] - frame["ema"].shift(6)) / frame["atr"]
            joined = expected.merge(frame, on="bar_close_time", how="left", validate="many_to_one")
            missing = int(joined["slope"].isna().sum())
            wick_error = max_abs_diff(joined["upper_wick_frac"], joined["wick"])
            slope_error = max_abs_diff(joined["ema40_slope6_atr"], joined["slope"])
            candidates.append({"atr_name": atr_name, "ema_name": ema_name, "missing": missing, "wick_max_abs_diff": wick_error, "slope_max_abs_diff": slope_error, "score": missing * 1e6 + wick_error + slope_error})
    ranked = sorted(candidates, key=lambda x: x["score"])
    best = ranked[0]
    if best["missing"] != 0 or best["wick_max_abs_diff"] > 1e-10 or best["slope_max_abs_diff"] > 1e-8:
        raise RuntimeError(f"No exact H4 geometry contract match; top={ranked[:6]}")
    return {"selected": best, "ranked": ranked}


def atr_for_name(frame: pd.DataFrame, name: str) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat([(frame["high"]-frame["low"]).abs(), (frame["high"]-prev).abs(), (frame["low"]-prev).abs()], axis=1).max(axis=1)
    if name == "sma14_min1":
        return tr.rolling(14, min_periods=1).mean()
    if name == "sma14_full":
        return tr.rolling(14, min_periods=14).mean()
    return atr_wilder_local(frame, 14)


def build_m15_features(frame: pd.DataFrame, atr_name: str, ddof: int, percentile_mode: str) -> pd.DataFrame:
    out = frame.copy()
    out["atr14"] = atr_for_name(out, atr_name)
    for period in (20, 60):
        mean = out["close"].rolling(period, min_periods=period).mean()
        sd = out["close"].rolling(period, min_periods=period).std(ddof=ddof)
        out[f"bb{period}_upper"] = mean + 2.0 * sd
        out[f"bb{period}_width_atr"] = 4.0 * sd / out["atr14"]
    out["bb60_width_pct100"] = percentile_variant(out["bb60_width_atr"], 100, percentile_mode)
    return out


def resolve_m15_bb_contract(m15: pd.DataFrame, expected_p8: pd.DataFrame) -> dict[str, Any]:
    expected = expected_p8[["close_time", "bb20_width_atr", "bb60_width_pct100"]].copy()
    expected["close_time"] = pd.to_datetime(expected["close_time"])
    candidates: list[dict[str, Any]] = []
    for atr_name in ["sma14_min1", "sma14_full", "wilder14"]:
        for ddof in [0, 1]:
            for pct_mode in ["le", "lt", "rank_average", "rank_min", "rank_max"]:
                frame = build_m15_features(m15, atr_name, ddof, pct_mode)
                joined = expected.merge(frame[["bar_close_time", "bb20_width_atr", "bb60_width_pct100"]], left_on="close_time", right_on="bar_close_time", how="left", suffixes=("_expected", "_actual"), validate="many_to_one")
                missing = int(joined["bb20_width_atr_actual"].isna().sum())
                width_error = max_abs_diff(joined["bb20_width_atr_expected"], joined["bb20_width_atr_actual"])
                pct_error = max_abs_diff(joined["bb60_width_pct100_expected"], joined["bb60_width_pct100_actual"])
                candidates.append({"atr_name": atr_name, "ddof": ddof, "percentile_mode": pct_mode, "missing": missing, "width_max_abs_diff": width_error, "percentile_max_abs_diff": pct_error, "score": missing * 1e6 + width_error + pct_error})
    ranked = sorted(candidates, key=lambda x: x["score"])
    best = ranked[0]
    if best["missing"] != 0 or best["width_max_abs_diff"] > 1e-8 or best["percentile_max_abs_diff"] > 1e-10:
        raise RuntimeError(f"No exact M15 BB contract match; top={ranked[:8]}")
    return {"selected": best, "ranked": ranked}


def build_h4_features(h4: pd.DataFrame, atr_name: str, ema_name: str, source_name: str, rank_method: str, formula: str, shift: int) -> pd.DataFrame:
    out = h4.copy()
    out["atr14"] = atr_for_name(out, atr_name)
    out["ema40"] = ema_variant(out["close"], ema_name, 40)
    out["rci18"] = rci_variant(price_source(out, source_name), 18, rank_method, formula).shift(shift)
    out["spread_atr"] = out["spread"] * base.POINT / out["atr14"]
    out["upper_wick_frac"] = (out["high"] - out[["open", "close"]].max(axis=1)) / (out["high"] - out["low"]).replace(0, np.nan)
    out["ema40_slope6_atr"] = (out["ema40"] - out["ema40"].shift(6)) / out["atr14"]
    return out


def derive_m15_candidates(engine: FastM1Engine, m15: pd.DataFrame, h4: pd.DataFrame) -> dict[str, pd.DataFrame]:
    joined = pd.merge_asof(m15.sort_values("bar_close_time"), h4[["bar_close_time", "rci18", "spread_atr", "upper_wick_frac", "ema40_slope6_atr"]].dropna(subset=["rci18", "spread_atr"]).sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    joined["condition"] = (joined["rci18"] >= RCI_THRESHOLD) & (joined["spread_atr"] <= SPREAD_ATR_THRESHOLD)
    joined["eligible"] = (joined["source"] == "historical") & joined["bar_close_time"].map(engine.has_exact_entry) & ((joined["bar_close_time"] + pd.Timedelta(hours=6)) <= engine.latest_close)
    eligible = joined[joined["eligible"]].copy()
    eligible["event"] = eligible["condition"] & ~eligible["condition"].shift(fill_value=False)
    parent = evaluate_events_fast(eligible[eligible["event"]], engine, 6, ["upper_wick_frac", "ema40_slope6_atr", "bb20_width_atr", "bb60_width_pct100"])
    parent["candidate_id"] = "GML1-PROV-002-DIAGNOSTIC"
    p7 = parent[~((parent["upper_wick_frac"] >= 0.27488556398168634) & (parent["ema40_slope6_atr"] >= 0.6863028800058267))].copy(); p7["candidate_id"] = "GML1-PROV-007"
    p8 = parent[~((parent["bb20_width_atr"] <= 3.3719018700718184) & (parent["bb60_width_pct100"] <= 0.536))].copy(); p8["candidate_id"] = "GML1-PROV-008"
    w22 = p7[~((p7["upper_wick_frac"] <= 0.06526044468913629) & (p7["ema40_slope6_atr"] >= 0.8700779249713114))].copy(); w22["candidate_id"] = "GML1-WATCH-022-B"
    return {"GML1-PROV-002-DIAGNOSTIC": parent, "GML1-PROV-007": p7, "GML1-PROV-008": p8, "GML1-WATCH-022-B": w22}


def set_score(actual: pd.DataFrame, expected: pd.DataFrame) -> dict[str, int]:
    a = set(pd.to_datetime(actual["decision_close_time"])); e = set(pd.to_datetime(expected["decision_close_time"]))
    return {"actual": len(a), "expected": len(e), "intersection": len(a & e), "missing": len(e - a), "extra": len(a - e), "symmetric_difference": len(a ^ e)}


def resolve_rci_contract(h4: pd.DataFrame, m15: pd.DataFrame, engine: FastM1Engine, geometry: dict[str, Any], expected_p7: pd.DataFrame, expected_p8: pd.DataFrame, expected_w22: pd.DataFrame) -> dict[str, Any]:
    g = geometry["selected"]
    expected_h4_times = pd.to_datetime(expected_p7["bar_close_time"])
    candidates: list[dict[str, Any]] = []
    for source_name in ["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"]:
        for method in ["average", "min", "max", "dense", "first"]:
            for formula in ["d2", "corr"]:
                for shift in [0, 1]:
                    features = build_h4_features(h4, g["atr_name"], g["ema_name"], source_name, method, formula, shift)
                    selected_rows = pd.DataFrame({"bar_close_time": expected_h4_times}).merge(features[["bar_close_time", "rci18", "spread_atr"]], on="bar_close_time", how="left")
                    condition_pass = int(((selected_rows["rci18"] >= RCI_THRESHOLD) & (selected_rows["spread_atr"] <= SPREAD_ATR_THRESHOLD)).sum())
                    if condition_pass < len(expected_h4_times) - 3:
                        candidates.append({"source": source_name, "rank_method": method, "formula": formula, "shift": shift, "condition_pass_on_expected_p7": condition_pass, "skipped_full_replay": True, "score": 10000 + len(expected_h4_times) - condition_pass})
                        continue
                    derived = derive_m15_candidates(engine, m15, features)
                    s7 = set_score(derived["GML1-PROV-007"], expected_p7); s8 = set_score(derived["GML1-PROV-008"], expected_p8); s22 = set_score(derived["GML1-WATCH-022-B"], expected_w22)
                    score = s7["symmetric_difference"] + s8["symmetric_difference"] + s22["symmetric_difference"]
                    candidates.append({"source": source_name, "rank_method": method, "formula": formula, "shift": shift, "condition_pass_on_expected_p7": condition_pass, "p7": s7, "p8": s8, "w22": s22, "skipped_full_replay": False, "score": score})
    ranked = sorted(candidates, key=lambda x: x["score"])
    full = [row for row in ranked if not row.get("skipped_full_replay")]
    if not full or full[0]["score"] != 0:
        raise RuntimeError(f"No exact M15 evaluator contract match; top={full[:10] if full else ranked[:10]}")
    return {"selected": full[0], "ranked": ranked}


def prepare_h1_d1(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = frame.copy(); out["atr14"] = atr_for_name(out, "sma14_min1")
    if timeframe == "H1":
        mean = out["close"].rolling(60, min_periods=60).mean(); sd = out["close"].rolling(60, min_periods=60).std(ddof=0)
        out["bb60_upper"] = mean + 2 * sd; out["spread_atr"] = out["spread"] * base.POINT / out["atr14"]
    else:
        out["rci18"] = rci_variant(out["close"], 18, "average", "corr")
        out["tickvol_ratio50"] = out["tick_volume"] / out["tick_volume"].rolling(50, min_periods=1).mean()
        out["delta_atr_3"] = (out["close"] - out["close"].shift(3)) / out["atr14"]
    return out


def derive_h1_candidates(engine: FastM1Engine, h1: pd.DataFrame, d1: pd.DataFrame) -> dict[str, pd.DataFrame]:
    d1f = d1[["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]].dropna(subset=["rci18"]).sort_values("bar_close_time")
    joined = pd.merge_asof(h1.sort_values("bar_close_time"), d1f, on="bar_close_time", direction="backward", allow_exact_matches=True, suffixes=("", "_d1"))
    joined["event"] = (joined["close"].shift(1) <= joined["bb60_upper"].shift(1)) & (joined["close"] > joined["bb60_upper"]) & (joined["rci18"] >= 0) & (joined["source"] == "historical")
    joined["decision_hour"] = joined["bar_close_time"].dt.hour
    p10 = evaluate_events_fast(joined[joined["event"]], engine, 48, ["tickvol_ratio50", "delta_atr_3", "decision_hour", "spread_atr"]).rename(columns={"tickvol_ratio50": "htf_tickvol_ratio50", "delta_atr_3": "htf_delta_atr_3", "decision_hour": "ltf_hour", "spread_atr": "ltf_spread_atr"}); p10["candidate_id"] = "GML1-PROV-010"
    p15 = p10[~((p10["htf_tickvol_ratio50"] <= 0.876789995391398) & (p10["htf_delta_atr_3"] <= 0.2256991669382677))].copy(); p15["candidate_id"] = "GML1-PROV-015"
    p20 = p15[~(p15["ltf_hour"].between(8, 16) & (p15["ltf_spread_atr"] >= 0.0308778597897866))].copy(); p20["candidate_id"] = "GML1-PROV-020"
    path = h1[["bar_close_time", "open", "high", "low", "close", "atr14"]].copy(); path["range_atr"] = (path["high"]-path["low"])/path["atr14"]; path["close_pos"] = (path["close"]-path["low"])/(path["high"]-path["low"]).replace(0,np.nan); path["range_atr_lag1"] = path["range_atr"].shift(1); path["close_pos_lag5"] = path["close_pos"].shift(5); path["range_atr_lag10"] = path["range_atr"].shift(10); path["span_atr_12"] = (path["high"].rolling(12).max()-path["low"].rolling(12).min())/path["atr14"]
    pp = p15.merge(path[["bar_close_time","range_atr_lag1","span_atr_12","close_pos_lag5","range_atr_lag10"]], left_on="decision_close_time", right_on="bar_close_time", how="left", validate="one_to_one")
    a = ~((pp["range_atr_lag1"] <= 0.6571970935503249) & (pp["span_atr_12"] >= 5.058013327710588)); b = ~((pp["close_pos_lag5"] <= 0.424089068826) & (pp["range_atr_lag10"] >= 1.17215632583))
    wa=pp.loc[a].copy(); wa["candidate_id"]="GML1-WATCH-021-A"; wb=pp.loc[b].copy(); wb["candidate_id"]="GML1-WATCH-021-B"; wc=pp.loc[a&b].copy(); wc["candidate_id"]="GML1-WATCH-021-C"
    return {"GML1-PROV-010":p10,"GML1-PROV-015":p15,"GML1-PROV-020":p20,"GML1-WATCH-021-A":wa,"GML1-WATCH-021-B":wb,"GML1-WATCH-021-C":wc}


def run(paths: Any, historical_dir: Path, warmup_dir: Path, output_dir: Path) -> int:
    config = json.loads(paths.config.read_text(encoding="utf-8")); raw={}; audit={}; missing=[]
    for tf,names in config["raw_files"].items():
        hp=base.locate_case_insensitive(historical_dir,names["historical"]); wp=base.locate_case_insensitive(warmup_dir,names["live"])
        if hp is None: missing.append(names["historical"]); continue
        combined,item=v2.load_historical_with_live_prehistory(hp,wp,tf); raw[tf]=combined; audit[tf]=item
    output_dir.mkdir(parents=True,exist_ok=True)
    if missing: base.json_dump(output_dir/"missing_raw_inputs.json",{"missing":missing}); return base.EXIT_INPUT
    expected={cid:base.read_csv_auto(base.registry_path(paths,f"{cid}_exact_trade_registry.csv")) for cid in base.EXPECTED_CANDIDATES}
    for frame in expected.values():
        for col in ["decision_close_time","entry_time","exit_time","bar_close_time","close_time"]:
            if col in frame.columns: frame[col]=pd.to_datetime(frame[col])
    engine=FastM1Engine.from_frame(raw["M1"][raw["M1"]["source"]=="historical"])
    geometry=resolve_h4_geometry_contract(raw["H4"],expected["GML1-PROV-007"]); bb=resolve_m15_bb_contract(raw["M15"],expected["GML1-PROV-008"])
    m15=build_m15_features(raw["M15"],bb["selected"]["atr_name"],int(bb["selected"]["ddof"]),bb["selected"]["percentile_mode"])
    rci=resolve_rci_contract(raw["H4"],m15,engine,geometry,expected["GML1-PROV-007"],expected["GML1-PROV-008"],expected["GML1-WATCH-022-B"]); rs=rci["selected"]; gs=geometry["selected"]
    h4=build_h4_features(raw["H4"],gs["atr_name"],gs["ema_name"],rs["source"],rs["rank_method"],rs["formula"],int(rs["shift"])); generated=derive_m15_candidates(engine,m15,h4)
    generated.update(derive_h1_candidates(engine,prepare_h1_d1(raw["H1"],"H1"),prepare_h1_d1(raw["D1"],"D1")))
    base.json_dump(output_dir/"evaluator_contract_resolution.json",{"status":"RESOLVED","open_time_contract":"raw time is bar-open time; close is open plus timeframe duration","h4_geometry":geometry,"m15_bollinger":bb,"h4_rci":rci,"input_audit":audit})
    parent=generated["GML1-PROV-002-DIAGNOSTIC"].copy(); parent["year"]=pd.to_datetime(parent["decision_close_time"]).dt.year; base.stable_sort_registry(parent).to_csv(output_dir/"GML1-PROV-002_DIAGNOSTIC_local_trade_registry.csv",index=False)
    reports=[]
    for cid in base.EXPECTED_CANDIDATES:
        frame=generated[cid].copy(); frame["year"]=pd.to_datetime(frame["decision_close_time"]).dt.year; base.stable_sort_registry(frame).to_csv(output_dir/f"{cid}_local_trade_registry.csv",index=False); reports.append(base.compare_candidate(cid,frame,base.registry_path(paths,f"{cid}_exact_trade_registry.csv"),output_dir/"diffs"))
    report=pd.DataFrame(reports); report.to_csv(output_dir/"raw_replay_comparison.csv",index=False); passed=bool(report["pass"].all())
    selected={"h4_geometry":geometry["selected"],"m15_bollinger":bb["selected"],"h4_rci":rci["selected"],"h1_event_order":"event on complete H1 series before one-position execution"}; base.json_dump(output_dir/"raw_replay_summary.json",{"status":"PASS" if passed else "FAIL","parent_metrics":base.compute_metrics(parent),"reports":reports,"selected_contract":selected})
    print("Selected evaluator contract:"); print(json.dumps(selected,ensure_ascii=False,indent=2)); print("GML1-PROV-002 diagnostic:",json.dumps(base.compute_metrics(parent),ensure_ascii=False)); print(report.to_string(index=False)); return base.EXIT_OK if passed else base.EXIT_REGISTRY


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[3]); parser.add_argument("--historical-dir",type=Path,required=True); parser.add_argument("--warmup-dir",type=Path,required=True); parser.add_argument("--output-dir",type=Path,default=None); args=parser.parse_args(); output=args.output_dir or args.repo_root/"outputs/gold_ml_v1/batch023_historical_replay_v4"
    try: return run(base.resolve_repo_paths(args.repo_root),args.historical_dir.resolve(),args.warmup_dir.resolve(),output)
    except (FileNotFoundError,ValueError,RuntimeError) as exc: output.mkdir(parents=True,exist_ok=True); (output/"contract_resolution_error.txt").write_text(str(exc),encoding="utf-8"); print(f"V4 CONTRACT RESOLUTION FAILED: {exc}",file=sys.stderr); return base.EXIT_INPUT
    except Exception: output.mkdir(parents=True,exist_ok=True); (output/"unexpected_exception.txt").write_text(traceback.format_exc(),encoding="utf-8"); traceback.print_exc(); return base.EXIT_ENV

if __name__ == "__main__": sys.exit(main())
