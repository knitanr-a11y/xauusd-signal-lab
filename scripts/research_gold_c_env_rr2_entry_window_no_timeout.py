#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research GOLD C_ENV + H1 regular bullish + M15 break with RR2 no-timeout.

Research-only script. It reads copied research CSV snapshots and writes only
research outputs. It does not touch Mochipoyo live/demo/autotrade files.

Compared condition IDs:
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_12H
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_24H
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_36H

Common rule:
    H4 C_ENV:
        Latest confirmed H4 candle at M15 signal close time:
            ema20 > ema50 and close > ema50

    H1:
        Newly confirmed H1 regular bullish divergence and loose exhaustion:
            close < ema50 OR ema20 < ema50

    M15:
        First M15 break trigger after H1 confirmation within entry window:
            close > high.shift(1).rolling(8).max()
            close > ema20
            MACD(6,13,4) > signal
            macd_hist > previous macd_hist

    Entry:
        M15 close.

    SL:
        M15 rolling low(12) - ATR14 * 0.05.

    TP:
        RR2.0.

    Outcome:
        M5 first-touch without timeout: hold until TP or SL is touched.
        If TP and SL touch in the same M5 candle, SL wins by default.

Important M5 coverage rule:
    If entry_time is earlier than the first available M5 candle, the trade is
    NO_M5_PATH. No-timeout evaluation must not skip months of missing M5 data
    and judge an old entry using the first later M5 candle.

Example:
    python scripts\research_gold_c_env_rr2_entry_window_no_timeout.py ^
      --csv-dir data\research_csv_snapshots\gold_cb_20260508_01 ^
      --out-dir data\research_results\gold_c_env_rr2_entry_window_no_timeout
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    DIRECTION,
    REQUIRED_FILES,
    SYMBOL,
    add_indicators,
    build_data_coverage,
    build_h1_events,
    build_m15_trigger_base,
    load_research_csvs,
    max_drawdown_r,
    profit_factor,
    safe_float,
    write_csv,
)
from scripts.research_gold_h4_permission_modes_h1_regular_bullish_m15_break import (  # noqa: E402
    prepare_h4_env_frame,
)

BASE_CONDITION_PREFIX = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT"
EVALUATED_OUTCOMES = {"WIN", "LOSS"}
NON_EVALUATED_OUTCOMES = {"NO_M5_PATH", "INVALID_RISK", "NO_TOUCH_BEFORE_DATA_END"}


def parse_hours_csv(text: str) -> list[float]:
    out: list[float] = []
    for raw in str(text).split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = float(raw)
        if value <= 0:
            raise ValueError(f"entry window hours must be positive: {value}")
        out.append(value)
    if not out:
        raise ValueError("--entry-window-hours-list must contain at least one value")
    return out


def condition_id_for_window(hours: float) -> str:
    if float(hours).is_integer():
        text = str(int(hours))
    else:
        text = str(hours).replace(".", "P")
    return f"{BASE_CONDITION_PREFIX}_{text}H"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare C_ENV RR2 no-timeout entry windows.")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        required=True,
        help="Copied research CSV snapshot directory containing goldsharp_h4/h1/m15/m5 CSVs.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_c_env_rr2_entry_window_no_timeout"),
        help="Research-only output directory.",
    )
    parser.add_argument("--entry-window-hours-list", type=str, default="12,24,36")
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--m15-breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def latest_h4_env_before(h4_env: pd.DataFrame, ts: pd.Timestamp) -> pd.Series | None:
    if h4_env.empty:
        return None
    eligible = h4_env[h4_env["h4_env_close_time"] <= ts]
    if eligible.empty:
        return None
    return eligible.sort_values("h4_env_close_time", kind="mergesort").iloc[-1]


def h4_env_permission_info(h4_env: pd.DataFrame, m15_close_time: pd.Timestamp) -> dict[str, object] | None:
    env_row = latest_h4_env_before(h4_env, m15_close_time)
    if env_row is None:
        return None
    if not bool(env_row.get("h4_env_up", False)):
        return None
    return {
        **env_row.to_dict(),
        "h4_permission_mode": "ENV",
        "h4_permission_reason": "h4_env_up",
        "h4_env_permission_ok": True,
        "h4_permission_ok": True,
    }


def first_m15_trigger_for_h1_event_env(
    h1_event: pd.Series,
    h4_env: pd.DataFrame,
    m15_base: pd.DataFrame,
    *,
    entry_window_hours: float,
) -> dict[str, object] | None:
    h1_confirm = pd.Timestamp(h1_event["h1_pivot_confirm_time"])
    search_end = h1_confirm + pd.to_timedelta(entry_window_hours, unit="h")
    candidates = m15_base[
        (m15_base["m15_close_time"] >= h1_confirm)
        & (m15_base["m15_close_time"] <= search_end)
    ].copy()
    if candidates.empty:
        return None

    for _, m15_row in candidates.sort_values("m15_close_time", kind="mergesort").iterrows():
        m15_close_time = pd.Timestamp(m15_row["m15_close_time"])
        perm = h4_env_permission_info(h4_env, m15_close_time)
        if perm is None:
            continue
        out: dict[str, object] = {**h1_event.to_dict(), **m15_row.to_dict(), **perm}
        out["trigger_ok"] = True
        out["entry_window_hours"] = entry_window_hours
        return out
    return None


def build_trade_candidates_for_window(
    h1_events: pd.DataFrame,
    h4_env: pd.DataFrame,
    m15_base: pd.DataFrame,
    *,
    entry_window_hours: float,
    args: argparse.Namespace,
) -> pd.DataFrame:
    condition_id = condition_id_for_window(entry_window_hours)
    rows: list[dict[str, object]] = []
    for _, h1_event in h1_events.sort_values("h1_pivot_confirm_time", kind="mergesort").iterrows():
        trigger = first_m15_trigger_for_h1_event_env(
            h1_event,
            h4_env,
            m15_base,
            entry_window_hours=entry_window_hours,
        )
        if trigger is None:
            continue

        entry_price = safe_float(trigger["m15_close"])
        sl_base_low = safe_float(trigger["m15_sl_base_low"])
        atr = safe_float(trigger["m15_atr14"])
        sl_price = sl_base_low - atr * float(args.sl_atr_buffer_mult)
        risk = entry_price - sl_price
        if not all(math.isfinite(v) for v in [entry_price, sl_price, risk]) or risk <= 0:
            initial_outcome = "INVALID_RISK"
            tp_price = np.nan
        else:
            initial_outcome = "PENDING"
            tp_price = entry_price + risk * float(args.rr)

        entry_time = pd.Timestamp(trigger["m15_close_time"])
        row = {
            "condition_id": condition_id,
            "entry_window_hours": entry_window_hours,
            "symbol": SYMBOL,
            "direction": DIRECTION,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "risk_price": risk,
            "rr": float(args.rr),
            "initial_outcome": initial_outcome,
            **trigger,
        }
        row["condition_id"] = condition_id
        row["trade_key"] = (
            f"{condition_id}|{row.get('h4_permission_reason','')}|{row.get('h1_event_id','')}|"
            f"{entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def judge_buy_first_touch_no_timeout(
    m5: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk: float,
    inbar_priority: str,
) -> dict[str, object]:
    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk]) or risk <= 0:
        return {
            "outcome": "INVALID_RISK",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": pd.NaT,
            "m5_last_time": pd.NaT,
            "m5_coverage_ok": False,
        }

    if m5.empty:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": pd.NaT,
            "m5_last_time": pd.NaT,
            "m5_coverage_ok": False,
        }

    m5_first_time = pd.Timestamp(m5["time"].min())
    m5_last_time = pd.Timestamp(m5["time"].max())

    # Critical no-timeout safety:
    # If the entry occurred before the available M5 history starts, we cannot
    # judge first-touch. Do not skip missing months and use the first later M5 bar.
    if entry_time < m5_first_time:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": m5_first_time,
            "m5_last_time": m5_last_time,
            "m5_coverage_ok": False,
        }

    path = m5[m5["time"] >= entry_time].copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    if path.empty:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": m5_first_time,
            "m5_last_time": m5_last_time,
            "m5_coverage_ok": False,
        }

    for checked, (_, bar) in enumerate(path.iterrows(), start=1):
        hit_sl = safe_float(bar["low"]) <= sl_price
        hit_tp = safe_float(bar["high"]) >= tp_price
        exit_time = pd.Timestamp(bar["time"])
        hold_minutes = (exit_time - entry_time).total_seconds() / 60.0
        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                return {
                    "outcome": "WIN",
                    "exit_time": exit_time,
                    "exit_price": tp_price,
                    "realized_r": (tp_price - entry_price) / risk,
                    "bars_checked": checked,
                    "hold_minutes": hold_minutes,
                    "m5_first_time": m5_first_time,
                    "m5_last_time": m5_last_time,
                    "m5_coverage_ok": True,
                }
            return {
                "outcome": "LOSS",
                "exit_time": exit_time,
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": checked,
                "hold_minutes": hold_minutes,
                "m5_first_time": m5_first_time,
                "m5_last_time": m5_last_time,
                "m5_coverage_ok": True,
            }
        if hit_sl:
            return {
                "outcome": "LOSS",
                "exit_time": exit_time,
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": checked,
                "hold_minutes": hold_minutes,
                "m5_first_time": m5_first_time,
                "m5_last_time": m5_last_time,
                "m5_coverage_ok": True,
            }
        if hit_tp:
            return {
                "outcome": "WIN",
                "exit_time": exit_time,
                "exit_price": tp_price,
                "realized_r": (tp_price - entry_price) / risk,
                "bars_checked": checked,
                "hold_minutes": hold_minutes,
                "m5_first_time": m5_first_time,
                "m5_last_time": m5_last_time,
                "m5_coverage_ok": True,
            }

    return {
        "outcome": "NO_TOUCH_BEFORE_DATA_END",
        "exit_time": path.iloc[-1]["time"] if not path.empty else pd.NaT,
        "exit_price": safe_float(path.iloc[-1]["close"]) if not path.empty else np.nan,
        "realized_r": np.nan,
        "bars_checked": int(len(path)),
        "hold_minutes": (pd.Timestamp(path.iloc[-1]["time"]) - entry_time).total_seconds() / 60.0 if not path.empty else np.nan,
        "m5_first_time": m5_first_time,
        "m5_last_time": m5_last_time,
        "m5_coverage_ok": True,
    }


def evaluate_trades_no_timeout(trades: pd.DataFrame, m5: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    rows: list[dict[str, object]] = []
    m5 = m5.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    for _, row in trades.iterrows():
        if str(row.get("initial_outcome")) == "INVALID_RISK":
            result = {
                "outcome": "INVALID_RISK",
                "exit_time": pd.NaT,
                "exit_price": np.nan,
                "realized_r": np.nan,
                "bars_checked": 0,
                "hold_minutes": np.nan,
                "m5_first_time": pd.Timestamp(m5["time"].min()) if not m5.empty else pd.NaT,
                "m5_last_time": pd.Timestamp(m5["time"].max()) if not m5.empty else pd.NaT,
                "m5_coverage_ok": False,
            }
        else:
            result = judge_buy_first_touch_no_timeout(
                m5,
                entry_time=pd.Timestamp(row["entry_time"]),
                entry_price=safe_float(row["entry_price"]),
                sl_price=safe_float(row["sl_price"]),
                tp_price=safe_float(row["tp_price"]),
                risk=safe_float(row["risk_price"]),
                inbar_priority=str(args.inbar_priority),
            )
        out = row.to_dict()
        out.update(result)
        rows.append(out)
    out_df = pd.DataFrame(rows).sort_values(["entry_window_hours", "entry_time"], kind="mergesort").reset_index(drop=True)
    out_df["entry_month"] = pd.to_datetime(out_df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    out_df["is_evaluated"] = out_df["outcome"].isin(EVALUATED_OUTCOMES)
    return out_df


def summarize_evaluated_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition_id",
        "entry_window_hours",
        "rr",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_dd_r",
        "max_consecutive_losses",
        "avg_hold_hours",
        "max_hold_hours",
        "first_entry_time",
        "last_entry_time",
        "months_with_trades",
    ]
    if trades_eval.empty:
        return pd.DataFrame(columns=cols)

    rows: list[dict[str, object]] = []
    for condition_id, group in trades_eval.groupby("condition_id", dropna=False):
        group = group.sort_values("entry_time", kind="mergesort").copy()
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        losses = group["outcome"].eq("LOSS").astype(int).tolist()
        max_consec = 0
        cur = 0
        for is_loss in losses:
            if is_loss:
                cur += 1
                max_consec = max(max_consec, cur)
            else:
                cur = 0
        hold_hours = pd.to_numeric(group["hold_minutes"], errors="coerce") / 60.0
        rows.append(
            {
                "condition_id": condition_id,
                "entry_window_hours": float(group["entry_window_hours"].iloc[0]),
                "rr": float(group["rr"].iloc[0]),
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "max_consecutive_losses": int(max_consec),
                "avg_hold_hours": float(hold_hours.mean()),
                "max_hold_hours": float(hold_hours.max()),
                "first_entry_time": group["entry_time"].min(),
                "last_entry_time": group["entry_time"].max(),
                "months_with_trades": int(group["entry_month"].nunique()),
            }
        )
    return pd.DataFrame(rows)[cols].sort_values("entry_window_hours").reset_index(drop=True)


def summarize_all_by_condition(trades_all: pd.DataFrame) -> pd.DataFrame:
    if trades_all.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for condition_id, group in trades_all.groupby("condition_id", dropna=False):
        rows.append(
            {
                "condition_id": condition_id,
                "entry_window_hours": float(group["entry_window_hours"].iloc[0]),
                "all_candidates": int(len(group)),
                "evaluated_candidates": int(group["outcome"].isin(EVALUATED_OUTCOMES).sum()),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "no_m5_path": int(group["outcome"].eq("NO_M5_PATH").sum()),
                "invalid_risk": int(group["outcome"].eq("INVALID_RISK").sum()),
                "no_touch_before_data_end": int(group["outcome"].eq("NO_TOUCH_BEFORE_DATA_END").sum()),
                "first_entry_time": group["entry_time"].min(),
                "last_entry_time": group["entry_time"].max(),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_window_hours").reset_index(drop=True)


def summarize_monthly_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (condition_id, month), group in trades_eval.groupby(["condition_id", "entry_month"], dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        hold_hours = pd.to_numeric(group["hold_minutes"], errors="coerce") / 60.0
        rows.append(
            {
                "condition_id": condition_id,
                "entry_window_hours": float(group["entry_window_hours"].iloc[0]),
                "entry_month": str(month),
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "max_hold_hours": float(hold_hours.max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["entry_window_hours", "entry_month"], kind="mergesort").reset_index(drop=True)


def select_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[[c for c in cols if c in df.columns]].copy() if not df.empty else pd.DataFrame(columns=cols)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    entry_windows = parse_hours_csv(args.entry_window_hours_list)

    print("[INFO] research-only C_ENV RR2 no-timeout entry-window comparison")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] entry_windows={entry_windows} rr={args.rr}")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = "GOLD_C_ENV_RR2_ENTRY_WINDOW_NO_TIMEOUT_COMPARISON"
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    print("[INFO] adding indicators")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    print("[INFO] detecting H1 context events and H4 env rows")
    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base(m15, args)

    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")

    all_pending: list[pd.DataFrame] = []
    all_evaluated: list[pd.DataFrame] = []
    for hours in entry_windows:
        print(f"[INFO] building/evaluating entry_window={hours}h")
        pending = build_trade_candidates_for_window(
            h1_events,
            h4_env,
            m15_base,
            entry_window_hours=hours,
            args=args,
        )
        evaluated = evaluate_trades_no_timeout(pending, m5, args) if not pending.empty else pd.DataFrame()
        if not pending.empty:
            all_pending.append(pending)
        if not evaluated.empty:
            all_evaluated.append(evaluated)
        suffix = f"{int(hours) if float(hours).is_integer() else str(hours).replace('.', 'p')}h"
        write_csv(pending, args.out_dir / f"trades_pending_{suffix}.csv")
        write_csv(evaluated, args.out_dir / f"trades_all_candidates_{suffix}.csv")
        evaluated_only = evaluated[evaluated["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not evaluated.empty else pd.DataFrame()
        no_m5_path = evaluated[evaluated["outcome"].eq("NO_M5_PATH")].copy() if not evaluated.empty else pd.DataFrame()
        write_csv(evaluated_only, args.out_dir / f"trades_evaluated_only_{suffix}.csv")
        write_csv(no_m5_path, args.out_dir / f"trades_no_m5_path_{suffix}.csv")

    trades_pending_all = pd.concat(all_pending, ignore_index=True) if all_pending else pd.DataFrame()
    trades_all = pd.concat(all_evaluated, ignore_index=True) if all_evaluated else pd.DataFrame()
    trades_eval = trades_all[trades_all["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not trades_all.empty else pd.DataFrame()
    trades_no_m5 = trades_all[trades_all["outcome"].eq("NO_M5_PATH")].copy() if not trades_all.empty else pd.DataFrame()

    trigger_cols = [
        "condition_id",
        "entry_window_hours",
        "h1_event_id",
        "h4_permission_reason",
        "h4_env_close_time",
        "h4_env_close",
        "h4_env_ema20",
        "h4_env_ema50",
        "m15_time",
        "m15_close_time",
        "m15_close",
        "m15_ema20",
        "m15_atr14",
        "m15_macd",
        "m15_macd_signal",
        "m15_macd_hist",
        "m15_rolling_high_8_prev",
        "h1_pivot_confirm_time",
        "trigger_ok",
    ]
    write_csv(select_cols(trades_pending_all, trigger_cols), args.out_dir / "m15_trigger_candidates_all_windows.csv")
    write_csv(trades_all, args.out_dir / "trades_all_candidates_all_windows.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only_all_windows.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path_all_windows.csv")
    write_csv(summarize_all_by_condition(trades_all), args.out_dir / "summary_all_candidates_by_window.csv")
    write_csv(summarize_evaluated_by_condition(trades_eval), args.out_dir / "summary_evaluated_only_by_window.csv")
    write_csv(summarize_monthly_by_condition(trades_eval), args.out_dir / "monthly_evaluated_only_by_window.csv")

    summary = summarize_evaluated_by_condition(trades_eval)
    print("[INFO] completed")
    print(f"[INFO] h1_events={len(h1_events)} m15_base_triggers={len(m15_base)}")
    print(f"[INFO] all_candidates={len(trades_all)} evaluated={len(trades_eval)} no_m5_path={len(trades_no_m5)}")
    print(summary.to_string(index=False) if not summary.empty else "[INFO] no evaluated trades")
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
