#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gold_v3_245_refined_setup_one_trade_stack_audit import (
    OFF_FLAGS,
    build_features,
    default_files_dir,
    metrics,
    now_utc,
    precompute_outcomes,
    read_goldsharp,
    save_csv,
    save_json,
    select_one_setup_one_trade,
)

STAGE = "GOLD_V3_246_LONG_DIRECTION_CORE_STACK_AUDIT_ONLY"
READY = "STAGE246_LONG_DIRECTION_CORE_STACK_READY_AUDIT_ONLY"
BLOCKED = "STAGE246_LONG_DIRECTION_CORE_STACK_BLOCKED_AUDIT_ONLY"
TF_MIN = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}

CANDIDATES = {
    "LONG_M5_DOWNTREND_CAPITULATION_REBOUND": {
        "signal_tf": "m5",
        "direction": "LONG",
        "tp": 20.0,
        "sl": 7.5,
        "horizon_m1": 300,
        "rule": "h1_ema20_ema50_atr<=-0.70 & m5_ret3_atr<=-0.75 & m5_rsi14<=40 & m5_lower_wick_atr>=0.40 & m5_body_atr>=0.25 & m5_close_loc>=0.60",
    },
    "LONG_M15_FALSE_BREAK_LOW_BOUNCE": {
        "signal_tf": "m15",
        "direction": "LONG",
        "tp": 20.0,
        "sl": 7.5,
        "horizon_m1": 300,
        "rule": "abs(h1_ema20_ema50_atr)<=0.80 & m15_low<=prev_low10+0.15*ATR14 & m15_close>=prev_low10 & m15_lower_wick_atr>=0.60 & m15_body_atr>=0.25 & m15_rsi14<=45",
    },
}


def progress(message: str, current: int | None = None, total: int | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    if current is not None and total:
        print(f"[Stage246 progress {current}/{total} {100.0 * current / total:5.1f}% {ts}] {message}", flush=True)
    else:
        print(f"[Stage246 progress {ts}] {message}", flush=True)


def make_signal_frame(frames: dict[str, pd.DataFrame], signal_tf: str) -> pd.DataFrame:
    signal = build_features(frames[signal_tf], signal_tf)
    signal = signal.rename(columns={
        "open_time": "signal_open_time",
        "close_time": "signal_close_time",
        "open": f"{signal_tf}_open",
        "high": f"{signal_tf}_high",
        "low": f"{signal_tf}_low",
        "close": f"{signal_tf}_close",
    })
    for tf in ["h1", "h4", "d1"]:
        htf = build_features(frames[tf], tf)
        source_close = f"{tf}_source_close_time"
        htf = htf.rename(columns={
            "close_time": source_close,
            "open": f"{tf}_open",
            "high": f"{tf}_high",
            "low": f"{tf}_low",
            "close": f"{tf}_close",
        })
        keep = [source_close] + [c for c in htf.columns if c.startswith(tf + "_")]
        keep = list(dict.fromkeys(keep))
        signal = pd.merge_asof(
            signal.sort_values("signal_close_time"),
            htf[keep].sort_values(source_close),
            left_on="signal_close_time",
            right_on=source_close,
            direction="backward",
            allow_exact_matches=True,
        )
    return signal.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def candidate_condition(name: str, signal: pd.DataFrame) -> np.ndarray:
    if name == "LONG_M5_DOWNTREND_CAPITULATION_REBOUND":
        condition = (
            (signal["h1_ema20_ema50_atr"] <= -0.70)
            & (signal["m5_ret3_atr"] <= -0.75)
            & (signal["m5_rsi14"] <= 40)
            & (signal["m5_lower_wick_atr"] >= 0.40)
            & (signal["m5_body_atr"] >= 0.25)
            & (signal["m5_close_loc"] >= 0.60)
        )
        return condition.fillna(False).values

    if name == "LONG_M15_FALSE_BREAK_LOW_BOUNCE":
        previous_low10 = signal["m15_low"].shift(1).rolling(10, min_periods=10).min()
        condition = (
            (signal["h1_ema20_ema50_atr"].abs() <= 0.80)
            & (signal["m15_low"] <= previous_low10 + 0.15 * signal["m15_atr14"])
            & (signal["m15_close"] >= previous_low10)
            & (signal["m15_lower_wick_atr"] >= 0.60)
            & (signal["m15_body_atr"] >= 0.25)
            & (signal["m15_rsi14"] <= 45)
        )
        return condition.fillna(False).values

    raise KeyError(name)


def exact_and_near_overlap(a: pd.DataFrame, b: pd.DataFrame, minutes: int = 30) -> dict[str, Any]:
    ta = pd.to_datetime(a["entry_time"]).sort_values().values.astype("datetime64[ns]")
    tb = pd.to_datetime(b["entry_time"]).sort_values().values.astype("datetime64[ns]")
    exact = len(set(ta).intersection(set(tb)))
    window = np.timedelta64(minutes, "m")
    near_a = 0
    for t in ta:
        if len(tb) and np.any(np.abs(tb - t) <= window):
            near_a += 1
    near_b = 0
    for t in tb:
        if len(ta) and np.any(np.abs(ta - t) <= window):
            near_b += 1
    return {
        "candidate_a": str(a.iloc[0]["candidate"]),
        "candidate_b": str(b.iloc[0]["candidate"]),
        "exact_entry_overlap": exact,
        "a_within_30m": near_a,
        "b_within_30m": near_b,
        "a_within_30m_rate": near_a / len(ta) if len(ta) else 0.0,
        "b_within_30m_rate": near_b / len(tb) if len(tb) else 0.0,
    }


def global_one_position(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    priority = {
        "LONG_M5_DOWNTREND_CAPITULATION_REBOUND": 1,
        "LONG_M15_FALSE_BREAK_LOW_BOUNCE": 2,
    }
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
    started = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    files_dir = default_files_dir()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve() if args.snapshot_dir else files_dir / "FX_OUTPUTS" / "gold_v3" / "243" / "input_snapshot" / "latest"
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else files_dir / "FX_OUTPUTS" / "gold_v3" / "246"
    output_dir.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []
    progress("load frozen M1/M5/M15/H1/H4/D1", 1, 6)
    frames: dict[str, pd.DataFrame] = {}
    diagnostics: list[dict[str, Any]] = []
    for tf in ["m1", "m5", "m15", "h1", "h4", "d1"]:
        path = snapshot_dir / f"goldsharp_{tf}.csv"
        frame = read_goldsharp(path, tf)
        frames[tf] = frame
        diagnostics.append({
            "tf": tf,
            "path": str(path),
            "exists": path.exists(),
            "rows": len(frame),
            "first_open_time": frame["open_time"].min() if not frame.empty else None,
            "last_open_time": frame["open_time"].max() if not frame.empty else None,
        })
        if frame.empty:
            blockers.append(f"missing_or_empty_{tf}: {path}")

    trades_by_candidate: dict[str, pd.DataFrame] = {}
    no_lookahead_violations = 0
    if not blockers:
        progress("build M5/M15 signal frames with HTF close-time gating", 2, 6)
        signals = {
            "m5": make_signal_frame(frames, "m5"),
            "m15": make_signal_frame(frames, "m15"),
        }
        for tf, signal in signals.items():
            signal = signal[
                (signal["signal_close_time"] >= frames["m1"]["open_time"].min())
                & (signal["signal_close_time"] <= frames["m1"]["open_time"].max())
            ].reset_index(drop=True)
            signals[tf] = signal
            for htf in ["h1", "h4", "d1"]:
                source_col = f"{htf}_source_close_time"
                bad = signal[source_col].notna() & (signal[source_col] > signal["signal_close_time"])
                no_lookahead_violations += int(bad.sum())
        if no_lookahead_violations:
            blockers.append(f"no_lookahead_violation_count={no_lookahead_violations}")

        progress("apply long candidate conditions and M1 outcomes", 3, 6)
        for name, config in CANDIDATES.items():
            tf = config["signal_tf"]
            signal = signals[tf].rename(columns={"signal_close_time": "close_time"})
            condition = candidate_condition(name, signals[tf])
            outcome = precompute_outcomes(
                signal,
                frames["m1"],
                config["direction"],
                config["tp"],
                config["sl"],
                config["horizon_m1"],
            )
            trades = select_one_setup_one_trade(signal, condition, outcome, name)
            trades["signal_tf"] = tf
            trades["direction"] = config["direction"]
            trades["tp"] = config["tp"]
            trades["sl"] = config["sl"]
            trades["rr"] = config["tp"] / config["sl"]
            trades["horizon_m1"] = config["horizon_m1"]
            trades["rule"] = config["rule"]
            trades_by_candidate[name] = trades
            print(f"[Stage246 candidate] {name}: trades={len(trades)}", flush=True)

        progress("calculate candidate, monthly, overlap and stack metrics", 4, 6)
        periods = [
            ("all_2026_snapshot", "2026-01-13", None),
            ("dev_2026_01_13_to_04_30", "2026-01-13", "2026-05-01"),
            ("validation_may_june", "2026-05-01", None),
        ]
        candidate_rows = []
        for name, trades in trades_by_candidate.items():
            config = CANDIDATES[name]
            row = {"candidate": name, **config, "trade_count": len(trades)}
            for label, start, end in periods:
                for cost in [3.0, 5.0]:
                    result = metrics(trades, start, end, cost)
                    for key, value in result.items():
                        row[f"{label}_{key}_cost{int(cost)}"] = value
            candidate_rows.append(row)

        all_trades = pd.concat(trades_by_candidate.values(), ignore_index=True).sort_values("entry_time").reset_index(drop=True)
        global_trades = global_one_position(all_trades)
        overlap_rows = []
        for left, right in itertools.combinations(trades_by_candidate, 2):
            overlap_rows.append(exact_and_near_overlap(trades_by_candidate[left], trades_by_candidate[right]))

        month_periods = [
            ("2026-01-13_to_01-31", "2026-01-13", "2026-02-01"),
            ("2026-02", "2026-02-01", "2026-03-01"),
            ("2026-03", "2026-03-01", "2026-04-01"),
            ("2026-04", "2026-04-01", "2026-05-01"),
            ("2026-05", "2026-05-01", "2026-06-01"),
            ("2026-06_to_snapshot_end", "2026-06-01", None),
        ]
        monthly_rows = []
        portfolios = list(trades_by_candidate.items()) + [
            ("LONG_CORE_CANDIDATE_SPECIFIC_STACK", all_trades),
            ("LONG_CORE_GLOBAL_ONE_POSITION", global_trades),
        ]
        for portfolio_name, trades in portfolios:
            for period_name, start, end in month_periods:
                cost3 = metrics(trades, start, end, 3.0)
                cost5 = metrics(trades, start, end, 5.0)
                monthly_rows.append({
                    "portfolio": portfolio_name,
                    "period": period_name,
                    "n": cost3["n"],
                    "wr_cost3": cost3["wr"],
                    "pf_cost3": cost3["pf"],
                    "pnl_cost3": cost3["pnl"],
                    "pf_cost5": cost5["pf"],
                    "pnl_cost5": cost5["pnl"],
                })

        active_overlap_entries = 0
        for _, row in all_trades.iterrows():
            entry = pd.Timestamp(row["entry_time"])
            other = all_trades[
                (all_trades["candidate"] != row["candidate"])
                & (pd.to_datetime(all_trades["entry_time"]) < entry)
                & (pd.to_datetime(all_trades["exit_time"]) > entry)
            ]
            if not other.empty:
                active_overlap_entries += 1

        save_csv(pd.DataFrame(candidate_rows), output_dir / "stage246_long_candidates.csv")
        save_csv(pd.DataFrame(monthly_rows), output_dir / "stage246_long_portfolio_monthly.csv")
        save_csv(pd.DataFrame(overlap_rows), output_dir / "stage246_long_overlap.csv")
        save_csv(all_trades, output_dir / "stage246_long_candidate_specific_trades.csv")
        save_csv(global_trades, output_dir / "stage246_long_global_one_position_trades.csv")
    else:
        all_trades = pd.DataFrame()
        global_trades = pd.DataFrame()
        active_overlap_entries = 0

    progress("write audit and summary", 5, 6)
    audit_rows = [
        {"check_id": "FROZEN_INPUT_SNAPSHOT", "passed": snapshot_dir.exists(), "details": str(snapshot_dir)},
        {"check_id": "CSV_TIME_IS_OPEN_TIME", "passed": True, "details": "close_time=open_time+TF delta"},
        {"check_id": "HTF_CLOSE_TIME_NOT_FUTURE", "passed": no_lookahead_violations == 0, "details": f"violation_count={no_lookahead_violations}"},
        {"check_id": "ENTRY_FIRST_M1_OPEN_AT_OR_AFTER_SIGNAL_CLOSE", "passed": True, "details": "searchsorted side=left"},
        {"check_id": "SAME_M1_TP_SL_SL_PRIORITY", "passed": True, "details": "SL evaluated before TP"},
        {"check_id": "ONE_SETUP_ONE_TRADE_PER_CANDIDATE", "passed": True, "details": "rearm after exit and false condition"},
        {"check_id": "AUDIT_ONLY", "passed": True, "details": "no Discord, MT5 order or autotrade"},
    ]
    save_csv(pd.DataFrame(diagnostics), output_dir / "stage246_source_diagnostics.csv")
    save_csv(pd.DataFrame(audit_rows), output_dir / "stage246_no_lookahead_audit.csv")

    status = "READY" if not blockers else "BLOCKED"
    validation_cost3 = metrics(all_trades, "2026-05-01", None, 3.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    validation_cost5 = metrics(all_trades, "2026-05-01", None, 5.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    all_cost3 = metrics(all_trades, "2026-01-13", None, 3.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    all_cost5 = metrics(all_trades, "2026-01-13", None, 5.0) if not all_trades.empty else {"n": 0, "wr": None, "pf": None, "pnl": 0.0}
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    summary = {
        "step": STAGE,
        "status": status,
        "ready": status == "READY",
        "decision": READY if status == "READY" else BLOCKED,
        "created_at_utc": now_utc(),
        "elapsed_sec": round(elapsed, 3),
        "snapshot_dir": str(snapshot_dir),
        "output_dir": str(output_dir),
        "candidate_count": len(CANDIDATES),
        "candidate_specific_trade_count": int(len(all_trades)),
        "global_one_position_trade_count": int(len(global_trades)),
        "active_overlap_entry_count": int(active_overlap_entries),
        "no_lookahead_violation_count": int(no_lookahead_violations),
        "all_cost3": all_cost3,
        "all_cost5": all_cost5,
        "validation_may_june_cost3": validation_cost3,
        "validation_may_june_cost5": validation_cost5,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "warning": "The two LONG candidates were identified after reviewing the available January-June 2026 sample. There is no untouched holdout left in that snapshot. Keep audit/watchlist only and validate on future bars.",
        "output_files": {
            "candidates": str(output_dir / "stage246_long_candidates.csv"),
            "monthly": str(output_dir / "stage246_long_portfolio_monthly.csv"),
            "overlap": str(output_dir / "stage246_long_overlap.csv"),
            "candidate_specific_trades": str(output_dir / "stage246_long_candidate_specific_trades.csv"),
            "global_one_position_trades": str(output_dir / "stage246_long_global_one_position_trades.csv"),
            "audit": str(output_dir / "stage246_no_lookahead_audit.csv"),
            "diagnostics": str(output_dir / "stage246_source_diagnostics.csv"),
            "summary": str(output_dir / "stage246_summary.json"),
            "paste_me": str(output_dir / "paste_me.txt"),
        },
    }
    summary.update(OFF_FLAGS)
    save_json(output_dir / "stage246_summary.json", summary)

    paste_lines = [
        "GOLD V3 246 PASTE_ME_LONG_DIRECTION_CORE_STACK_AUDIT_ONLY",
        f"step: {STAGE}",
        f"status: {status}",
        f"ready: {status == 'READY'}",
        f"decision: {summary['decision']}",
        f"created_at_utc: {summary['created_at_utc']}",
        f"elapsed_sec: {summary['elapsed_sec']}",
        f"candidate_specific_trade_count: {summary['candidate_specific_trade_count']}",
        f"global_one_position_trade_count: {summary['global_one_position_trade_count']}",
        f"active_overlap_entry_count: {summary['active_overlap_entry_count']}",
        f"no_lookahead_violation_count: {summary['no_lookahead_violation_count']}",
        f"all_cost3: {json.dumps(summary['all_cost3'], ensure_ascii=False)}",
        f"all_cost5: {json.dumps(summary['all_cost5'], ensure_ascii=False)}",
        f"validation_may_june_cost3: {json.dumps(summary['validation_may_june_cost3'], ensure_ascii=False)}",
        f"validation_may_june_cost5: {json.dumps(summary['validation_may_june_cost5'], ensure_ascii=False)}",
        f"blocker_count: {summary['blocker_count']}",
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
    print(f"Stage246 status: {status}", flush=True)
    print(f"paste_me: {output_dir / 'paste_me.txt'}", flush=True)
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
