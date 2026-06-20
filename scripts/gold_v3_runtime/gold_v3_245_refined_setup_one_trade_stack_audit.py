#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STAGE = "GOLD_V3_245_REFINED_SETUP_ONE_TRADE_STACK_AUDIT_ONLY"
READY = "STAGE245_REFINED_SETUP_ONE_TRADE_STACK_READY_AUDIT_ONLY"
BLOCKED = "STAGE245_REFINED_SETUP_ONE_TRADE_STACK_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TF_MIN = {"m1": 1, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
OFF_FLAGS = {
    "discord_webhook_called": False,
    "mt5_order_send_called": False,
    "order_placed": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "candidate_pool_removed": False,
    "open_asof_allowed": False,
}

CANDIDATES = {
    "VOL_STRONG_H1_RSI45": {
        "family": "M15_VOL_EXPANSION_SHORT",
        "direction": "SHORT",
        "tp": 40.0,
        "sl": 15.0,
        "horizon_m1": 480,
        "description": "H1 strong downtrend and RSI<=45; M15 volatility expansion bearish close",
    },
    "PULLBACK_H1_VOL_BAND": {
        "family": "M15_TREND_PULLBACK_SHORT",
        "direction": "SHORT",
        "tp": 30.0,
        "sl": 10.0,
        "horizon_m1": 360,
        "description": "H1 downtrend with H1 ATR14/ATR50 in 1.1-1.5; M15 bearish pullback continuation",
    },
    "BREAKOUT_TREND_VOL": {
        "family": "M15_BREAKOUT_SHORT",
        "direction": "SHORT",
        "tp": 40.0,
        "sl": 15.0,
        "horizon_m1": 480,
        "description": "H1 trend<=-0.55ATR and M15 ATR14/ATR50>=1.1; M15 40-bar downside breakout",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def progress(msg: str, current: int | None = None, total: int | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    if current is not None and total:
        pct = 100.0 * current / total
        print(f"[Stage245 progress {current}/{total} {pct:5.1f}% {ts}] {msg}", flush=True)
    else:
        print(f"[Stage245 progress {ts}] {msg}", flush=True)


def safe(value: Any) -> Any:
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (pd.Timestamp, datetime)):
        return str(value)
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(data), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def default_files_dir() -> Path:
    env = os.environ.get("GOLD_V3_MQL5_FILES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    app = os.environ.get("APPDATA", "").strip()
    if app:
        return Path(app, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return Path.cwd().resolve()


def normalize_col(col: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(col).strip().strip("<>").lower()).strip("_")


def read_goldsharp(path: Path, tf: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df.columns = [normalize_col(c) for c in df.columns]
    if "time" not in df.columns:
        return pd.DataFrame()
    df["open_time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for col in ["open", "high", "low", "close", "spread", "tick_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    required = ["open_time", "open", "high", "low", "close"]
    df = df.dropna(subset=required).drop_duplicates("open_time", keep="last").sort_values("open_time").reset_index(drop=True)
    df["close_time"] = df["open_time"] + pd.to_timedelta(TF_MIN[tf], unit="min")
    return df


def build_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    base_cols = ["open_time", "close_time", "open", "high", "low", "close"]
    for optional in ["spread", "tick_volume"]:
        if optional in df.columns:
            base_cols.append(optional)
    x = df[base_cols].copy()
    o, h, l, c = x["open"], x["high"], x["low"], x["close"]
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    for n in [5, 10, 14, 20, 40, 50, 100, 200]:
        x[f"{prefix}_atr{n}"] = tr.rolling(n, min_periods=n).mean()
        x[f"{prefix}_ema{n}"] = c.ewm(span=n, adjust=False, min_periods=n).mean()
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x[f"{prefix}_rsi14"] = 100 - 100 / (1 + rs)
    x[f"{prefix}_body_atr14"] = (c - o) / x[f"{prefix}_atr14"].replace(0, np.nan)
    x[f"{prefix}_range_atr14"] = (h - l) / x[f"{prefix}_atr14"].replace(0, np.nan)
    x[f"{prefix}_close_loc"] = (c - l) / (h - l).replace(0, np.nan)
    x[f"{prefix}_atr_ratio"] = x[f"{prefix}_atr14"] / x[f"{prefix}_atr50"].replace(0, np.nan)
    x[f"{prefix}_ema20_ema50_atr14"] = (x[f"{prefix}_ema20"] - x[f"{prefix}_ema50"]) / x[f"{prefix}_atr14"].replace(0, np.nan)
    x[f"{prefix}_close_ema20_atr14"] = (c - x[f"{prefix}_ema20"]) / x[f"{prefix}_atr14"].replace(0, np.nan)
    for n in [10, 20, 40]:
        x[f"{prefix}_prev_low{n}"] = l.shift(1).rolling(n, min_periods=n).min()
        x[f"{prefix}_break_low{n}_atr14"] = (x[f"{prefix}_prev_low{n}"] - c) / x[f"{prefix}_atr14"].replace(0, np.nan)
    return x.replace([np.inf, -np.inf], np.nan)


def make_signal_frame(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    signal = build_features(frames["m15"], "m15")
    for tf in ["h1", "h4", "d1"]:
        htf = build_features(frames[tf], tf)
        source_time = f"{tf}_source_close_time"
        htf = htf.rename(columns={"close_time": source_time})
        keep = [source_time] + [c for c in htf.columns if c.startswith(tf + "_")]
        signal = pd.merge_asof(
            signal.sort_values("close_time"),
            htf[keep].sort_values(source_time),
            left_on="close_time",
            right_on=source_time,
            direction="backward",
            allow_exact_matches=True,
        )
    return signal.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def candidate_conditions(signal: pd.DataFrame) -> dict[str, np.ndarray]:
    breakout_base = (
        (signal["h1_ema20_ema50_atr14"] <= -0.30)
        & (signal["m15_break_low40_atr14"] >= 0.10)
        & (signal["m15_body_atr14"] <= -0.30)
        & (signal["m15_close_loc"] <= 0.30)
        & (signal["m15_atr_ratio"] >= 1.00)
    )
    vol_base = (
        (signal["h1_ema20_ema50_atr14"] <= -0.15)
        & (signal["m15_atr_ratio"].shift(1) <= 0.85)
        & (signal["m15_range_atr14"] >= 1.30)
        & (signal["m15_body_atr14"] <= -0.70)
        & (signal["m15_close_loc"] <= 0.30)
    )
    pullback_base = (
        (signal["h1_ema20_ema50_atr14"] <= -0.30)
        & (signal["m15_close_ema20_atr14"] >= -0.25)
        & (signal["m15_close_ema20_atr14"] <= 0.75)
        & (signal["m15_rsi14"] >= 40)
        & (signal["m15_rsi14"] <= 65)
        & (signal["m15_body_atr14"] <= -0.30)
        & (signal["close"] < signal["low"].shift(1))
    )
    return {
        "VOL_STRONG_H1_RSI45": (vol_base & (signal["h1_ema20_ema50_atr14"] <= -0.70) & (signal["h1_rsi14"] <= 45)).fillna(False).values,
        "PULLBACK_H1_VOL_BAND": (pullback_base & (signal["h1_atr_ratio"] >= 1.10) & (signal["h1_atr_ratio"] <= 1.50)).fillna(False).values,
        "BREAKOUT_TREND_VOL": (breakout_base & (signal["h1_ema20_ema50_atr14"] <= -0.55) & (signal["m15_atr_ratio"] >= 1.10)).fillna(False).values,
    }


def precompute_outcomes(signal: pd.DataFrame, m1: pd.DataFrame, direction: str, tp: float, sl: float, horizon_m1: int) -> dict[str, np.ndarray]:
    n = len(signal)
    entry_time = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    exit_time = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    pnl = np.full(n, np.nan)
    hit = np.empty(n, dtype=object)
    times = m1["open_time"].values.astype("datetime64[ns]")
    opens = m1["open"].astype(float).values
    highs = m1["high"].astype(float).values
    lows = m1["low"].astype(float).values
    closes = m1["close"].astype(float).values
    for i, signal_close in enumerate(signal["close_time"]):
        j = int(np.searchsorted(times, np.datetime64(signal_close), side="left"))
        if j >= len(m1):
            continue
        entry = pd.Timestamp(m1.iloc[j]["open_time"])
        if entry - pd.Timestamp(signal_close) > pd.Timedelta(minutes=2):
            continue
        entry_price = float(opens[j])
        end = min(j + horizon_m1, len(m1))
        exit_idx = end - 1
        result = float(entry_price - closes[exit_idx]) if direction == "SHORT" else float(closes[exit_idx] - entry_price)
        result = max(-sl, min(tp, result))
        hit_type = "HORIZON"
        for k in range(j, end):
            if direction == "SHORT":
                sl_hit = highs[k] >= entry_price + sl
                tp_hit = lows[k] <= entry_price - tp
            else:
                sl_hit = lows[k] <= entry_price - sl
                tp_hit = highs[k] >= entry_price + tp
            if sl_hit:
                exit_idx = k
                result = -sl
                hit_type = "SL"
                break
            if tp_hit:
                exit_idx = k
                result = tp
                hit_type = "TP"
                break
        entry_time[i] = np.datetime64(entry)
        exit_time[i] = np.datetime64(pd.Timestamp(m1.iloc[exit_idx]["open_time"]) + pd.Timedelta(minutes=1))
        pnl[i] = result
        hit[i] = hit_type
    return {"entry_time": entry_time, "exit_time": exit_time, "pnl": pnl, "hit": hit}


def select_one_setup_one_trade(signal: pd.DataFrame, condition: np.ndarray, outcome: dict[str, np.ndarray], candidate_name: str) -> pd.DataFrame:
    rows: list[int] = []
    active = False
    active_until = np.datetime64("NaT")
    armed = True
    closes = signal["close_time"].values.astype("datetime64[ns]")
    for i, close_time in enumerate(closes):
        if active and close_time < active_until:
            continue
        if active and close_time >= active_until:
            active = False
            armed = False
        if not bool(condition[i]):
            armed = True
            continue
        if not armed or np.isnat(outcome["entry_time"][i]):
            continue
        rows.append(i)
        active_until = outcome["exit_time"][i]
        active = True
        armed = False
    if not rows:
        return pd.DataFrame(columns=["candidate", "signal_index", "signal_time", "entry_time", "exit_time", "pnl_raw", "hit"])
    idx = np.asarray(rows, dtype=int)
    return pd.DataFrame({
        "candidate": candidate_name,
        "signal_index": idx,
        "signal_time": signal.iloc[idx]["close_time"].values,
        "entry_time": outcome["entry_time"][idx],
        "exit_time": outcome["exit_time"][idx],
        "pnl_raw": outcome["pnl"][idx],
        "hit": outcome["hit"][idx],
    })


def metrics(df: pd.DataFrame, start: str, end: str | None, cost: float) -> dict[str, Any]:
    if df.empty:
        return {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    entry = pd.to_datetime(df["entry_time"])
    mask = entry >= pd.Timestamp(start)
    if end is not None:
        mask &= entry < pd.Timestamp(end)
    x = df.loc[mask]
    if x.empty:
        return {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    net = pd.to_numeric(x["pnl_raw"], errors="coerce") - cost
    gp = float(net[net > 0].sum())
    gl = float(-net[net < 0].sum())
    pf_value = math.inf if gl == 0 and gp > 0 else (0.0 if gl == 0 else gp / gl)
    return {"n": int(len(x)), "wr": float((net > 0).mean()), "pf": float(pf_value), "pnl": float(net.sum())}


def near_overlap(a: pd.DataFrame, b: pd.DataFrame, minutes: int = 30) -> dict[str, Any]:
    ta = pd.to_datetime(a["entry_time"]).sort_values().values.astype("datetime64[ns]")
    tb = pd.to_datetime(b["entry_time"]).sort_values().values.astype("datetime64[ns]")
    exact = len(set(ta).intersection(set(tb)))
    window = np.timedelta64(minutes, "m")
    def count_near(left: np.ndarray, right: np.ndarray) -> int:
        count = 0
        for t in left:
            j = int(np.searchsorted(right, t))
            if any(0 <= k < len(right) and abs(right[k] - t) <= window for k in [j - 1, j]):
                count += 1
        return count
    a_near = count_near(ta, tb)
    b_near = count_near(tb, ta)
    return {
        "candidate_a": str(a.iloc[0]["candidate"]),
        "candidate_b": str(b.iloc[0]["candidate"]),
        "exact_entry_overlap": exact,
        "a_within_30m": a_near,
        "b_within_30m": b_near,
        "a_within_30m_rate": a_near / len(ta) if len(ta) else 0.0,
        "b_within_30m_rate": b_near / len(tb) if len(tb) else 0.0,
    }


def global_one_position(df: pd.DataFrame) -> pd.DataFrame:
    priority = {"VOL_STRONG_H1_RSI45": 1, "PULLBACK_H1_VOL_BAND": 2, "BREAKOUT_TREND_VOL": 3}
    x = df.copy()
    x["priority"] = x["candidate"].map(priority).fillna(99)
    x = x.sort_values(["entry_time", "priority"]).reset_index(drop=True)
    rows = []
    active_until: pd.Timestamp | None = None
    for _, row in x.iterrows():
        entry = pd.Timestamp(row["entry_time"])
        if active_until is not None and entry < active_until:
            continue
        rows.append(row)
        active_until = pd.Timestamp(row["exit_time"])
    return pd.DataFrame(rows).drop(columns=["priority"], errors="ignore").reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", default="", help="Stage243 frozen input snapshot containing goldsharp_*.csv")
    parser.add_argument("--output-dir", default="", help="Output directory; default FX_OUTPUTS/gold_v3/245")
    args = parser.parse_args()

    files_dir = default_files_dir()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve() if args.snapshot_dir else files_dir / "FX_OUTPUTS" / "gold_v3" / "243" / "input_snapshot" / "latest"
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else files_dir / "FX_OUTPUTS" / "gold_v3" / "245"
    output_dir.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []

    progress("load frozen M1/M15/H1/H4/D1", 1, 6)
    frames: dict[str, pd.DataFrame] = {}
    diagnostics = []
    for tf in ["m1", "m15", "h1", "h4", "d1"]:
        path = snapshot_dir / f"goldsharp_{tf}.csv"
        frame = read_goldsharp(path, tf)
        frames[tf] = frame
        diagnostics.append({"tf": tf, "path": str(path), "exists": path.exists(), "rows": len(frame), "first": frame["open_time"].min() if not frame.empty else None, "last": frame["open_time"].max() if not frame.empty else None})
        if frame.empty:
            blockers.append(f"missing_or_empty_{tf}: {path}")

    trades_by_candidate: dict[str, pd.DataFrame] = {}
    no_lookahead_violations = 0
    if not blockers:
        progress("build close-time-gated signal features", 2, 6)
        signal = make_signal_frame(frames)
        signal = signal[(signal["close_time"] >= frames["m1"]["open_time"].min()) & (signal["close_time"] <= frames["m1"]["open_time"].max())].reset_index(drop=True)
        for tf in ["h1", "h4", "d1"]:
            source_col = f"{tf}_source_close_time"
            bad = signal[source_col].notna() & (signal[source_col] > signal["close_time"])
            no_lookahead_violations += int(bad.sum())
        if no_lookahead_violations:
            blockers.append(f"no_lookahead_violation_count={no_lookahead_violations}")
        conditions = candidate_conditions(signal)

        progress("precompute M1 outcomes and apply one-setup-one-trade state machine", 3, 6)
        profile_cache: dict[tuple[Any, ...], dict[str, np.ndarray]] = {}
        for name, config in CANDIDATES.items():
            profile = (config["direction"], config["tp"], config["sl"], config["horizon_m1"])
            if profile not in profile_cache:
                profile_cache[profile] = precompute_outcomes(signal, frames["m1"], *profile)
            trades = select_one_setup_one_trade(signal, conditions[name], profile_cache[profile], name)
            trades["direction"] = config["direction"]
            trades["tp"] = config["tp"]
            trades["sl"] = config["sl"]
            trades["rr"] = config["tp"] / config["sl"]
            trades["horizon_m1"] = config["horizon_m1"]
            trades_by_candidate[name] = trades
            print(f"[Stage245 candidate] {name}: trades={len(trades)}", flush=True)

        progress("calculate candidate metrics, overlap and stacked portfolios", 4, 6)
        candidate_rows = []
        periods = [
            ("dev_2026_01_13_to_04_30", "2026-01-13", "2026-05-01"),
            ("may_2026", "2026-05-01", "2026-06-01"),
            ("june_to_snapshot_end", "2026-06-01", None),
            ("validation_may_june", "2026-05-01", None),
            ("all_2026_snapshot", "2026-01-13", None),
        ]
        monthly_rows = []
        month_periods = [
            ("2026-01-13_to_01-31", "2026-01-13", "2026-02-01"),
            ("2026-02", "2026-02-01", "2026-03-01"),
            ("2026-03", "2026-03-01", "2026-04-01"),
            ("2026-04", "2026-04-01", "2026-05-01"),
            ("2026-05", "2026-05-01", "2026-06-01"),
            ("2026-06_to_snapshot_end", "2026-06-01", None),
        ]
        for name, trades in trades_by_candidate.items():
            row = {"candidate": name, **CANDIDATES[name], "trade_count": len(trades)}
            for label, start, end in periods:
                for cost in [3.0, 5.0]:
                    result = metrics(trades, start, end, cost)
                    for metric_name, value in result.items():
                        row[f"{label}_{metric_name}_cost{int(cost)}"] = value
            candidate_rows.append(row)
            for label, start, end in month_periods:
                a3 = metrics(trades, start, end, 3.0)
                a5 = metrics(trades, start, end, 5.0)
                monthly_rows.append({"portfolio": name, "period": label, "n": a3["n"], "wr": a3["wr"], "pf3": a3["pf"], "pnl3": a3["pnl"], "pf5": a5["pf"], "pnl5": a5["pnl"]})

        all_trades = pd.concat(trades_by_candidate.values(), ignore_index=True).sort_values("entry_time").reset_index(drop=True)
        global_trades = global_one_position(all_trades)
        for portfolio_name, trades in [("STACK_CANDIDATE_SPECIFIC", all_trades), ("GLOBAL_ONE_POSITION", global_trades)]:
            for label, start, end in month_periods:
                a3 = metrics(trades, start, end, 3.0)
                a5 = metrics(trades, start, end, 5.0)
                monthly_rows.append({"portfolio": portfolio_name, "period": label, "n": a3["n"], "wr": a3["wr"], "pf3": a3["pf"], "pnl3": a3["pnl"], "pf5": a5["pf"], "pnl5": a5["pnl"]})

        overlap_rows = []
        names = list(trades_by_candidate)
        for left, right in itertools.combinations(names, 2):
            overlap_rows.append(near_overlap(trades_by_candidate[left], trades_by_candidate[right], 30))

        active_overlap_entries = 0
        for _, row in all_trades.iterrows():
            entry = pd.Timestamp(row["entry_time"])
            others = all_trades[(all_trades["candidate"] != row["candidate"]) & (pd.to_datetime(all_trades["entry_time"]) < entry) & (pd.to_datetime(all_trades["exit_time"]) > entry)]
            if not others.empty:
                active_overlap_entries += 1

        candidate_df = pd.DataFrame(candidate_rows)
        monthly_df = pd.DataFrame(monthly_rows)
        overlap_df = pd.DataFrame(overlap_rows)
        save_csv(candidate_df, output_dir / "stage245_refined_candidates.csv")
        save_csv(monthly_df, output_dir / "stage245_portfolio_monthly.csv")
        save_csv(overlap_df, output_dir / "stage245_candidate_overlap.csv")
        save_csv(all_trades, output_dir / "stage245_candidate_specific_trades.csv")
        save_csv(global_trades, output_dir / "stage245_global_one_position_trades.csv")
    else:
        signal = pd.DataFrame()
        candidate_df = pd.DataFrame()
        monthly_df = pd.DataFrame()
        overlap_df = pd.DataFrame()
        all_trades = pd.DataFrame()
        global_trades = pd.DataFrame()
        active_overlap_entries = 0

    progress("write audit and summary", 5, 6)
    audit_rows = [
        {"check_id": "INPUT_IS_STAGE243_FROZEN_SNAPSHOT", "passed": snapshot_dir.exists(), "details": str(snapshot_dir)},
        {"check_id": "ALL_TIMES_ARE_OPEN_TIMES", "passed": True, "details": "close_time=open_time+TF delta"},
        {"check_id": "HTF_CLOSE_GATED", "passed": no_lookahead_violations == 0, "details": f"merge_asof backward; violation_count={no_lookahead_violations}"},
        {"check_id": "ENTRY_FIRST_M1_OPEN_AT_OR_AFTER_SIGNAL_CLOSE", "passed": True, "details": "searchsorted side=left"},
        {"check_id": "SAME_M1_TP_SL_IS_SL", "passed": True, "details": "SL checked before TP"},
        {"check_id": "ONE_SETUP_ONE_TRADE_PER_CANDIDATE", "passed": True, "details": "candidate rearms only after exit and a false condition"},
        {"check_id": "AUDIT_ONLY_NO_ORDER_OR_NOTIFY", "passed": True, "details": "no Discord/MT5/order calls"},
    ]
    save_csv(pd.DataFrame(diagnostics), output_dir / "stage245_source_diagnostics.csv")
    save_csv(pd.DataFrame(audit_rows), output_dir / "stage245_no_lookahead_audit.csv")

    status = "READY" if not blockers else "BLOCKED"
    stack_val3 = metrics(all_trades, "2026-05-01", None, 3.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    stack_val5 = metrics(all_trades, "2026-05-01", None, 5.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    global_val3 = metrics(global_trades, "2026-05-01", None, 3.0) if not global_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    summary = {
        "step": STAGE,
        "status": status,
        "ready": status == "READY",
        "decision": READY if status == "READY" else BLOCKED,
        "created_at_utc": now_utc(),
        "elapsed_sec": round(time.time() - t0, 3),
        "snapshot_dir": str(snapshot_dir),
        "output_dir": str(output_dir),
        "candidate_count": len(CANDIDATES),
        "candidate_specific_trade_count": int(len(all_trades)),
        "global_one_position_trade_count": int(len(global_trades)),
        "candidate_specific_active_overlap_entry_count": int(active_overlap_entries),
        "no_lookahead_violation_count": int(no_lookahead_violations),
        "candidate_specific_validation_cost3": stack_val3,
        "candidate_specific_validation_cost5": stack_val5,
        "global_one_position_validation_cost3": global_val3,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "warning": "All three candidates are M15 SHORT and remain audit/watchlist only. Filters were refined using the available 2026 sample; further forward data and separate LONG research are required.",
        "output_files": {
            "candidate_summary": str(output_dir / "stage245_refined_candidates.csv"),
            "monthly": str(output_dir / "stage245_portfolio_monthly.csv"),
            "overlap": str(output_dir / "stage245_candidate_overlap.csv"),
            "candidate_specific_trades": str(output_dir / "stage245_candidate_specific_trades.csv"),
            "global_one_position_trades": str(output_dir / "stage245_global_one_position_trades.csv"),
            "audit": str(output_dir / "stage245_no_lookahead_audit.csv"),
            "diagnostics": str(output_dir / "stage245_source_diagnostics.csv"),
            "summary": str(output_dir / "stage245_summary.json"),
            "paste_me": str(output_dir / "paste_me.txt"),
        },
    }
    summary.update(OFF_FLAGS)
    save_json(output_dir / "stage245_summary.json", summary)

    paste_lines = [
        "GOLD V3 245 PASTE_ME_REFINED_SETUP_ONE_TRADE_STACK_AUDIT_ONLY",
        f"step: {STAGE}",
        f"status: {status}",
        f"ready: {status == 'READY'}",
        f"decision: {summary['decision']}",
        f"created_at_utc: {summary['created_at_utc']}",
        f"elapsed_sec: {summary['elapsed_sec']}",
        f"snapshot_dir: {snapshot_dir}",
        f"candidate_specific_trade_count: {summary['candidate_specific_trade_count']}",
        f"global_one_position_trade_count: {summary['global_one_position_trade_count']}",
        f"candidate_specific_active_overlap_entry_count: {summary['candidate_specific_active_overlap_entry_count']}",
        f"no_lookahead_violation_count: {summary['no_lookahead_violation_count']}",
        f"candidate_specific_validation_cost3: {json.dumps(safe(stack_val3), ensure_ascii=False)}",
        f"candidate_specific_validation_cost5: {json.dumps(safe(stack_val5), ensure_ascii=False)}",
        f"global_one_position_validation_cost3: {json.dumps(safe(global_val3), ensure_ascii=False)}",
        f"blocker_count: {len(blockers)}",
        "",
        "WARNING",
        summary["warning"],
        "",
        "OFF_FLAGS",
    ]
    for key in OFF_FLAGS:
        paste_lines.append(f"{key}: {summary[key]}")
    paste_lines += ["", "OUTPUT_FILES"]
    for key, value in summary["output_files"].items():
        paste_lines.append(f"{key}: {value}")
    paste_lines += ["", "BLOCKERS"] + (blockers or ["NO_BLOCKERS"])
    (output_dir / "paste_me.txt").write_text("\n".join(paste_lines), encoding="utf-8")

    progress("done", 6, 6)
    print(f"Stage245 status: {status}", flush=True)
    print(f"paste_me: {output_dir / 'paste_me.txt'}", flush=True)
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
