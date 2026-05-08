#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare max holding horizons for the current best GOLD C_ENV RR2 setup.

Research-only script. It reads copied research CSV snapshots and writes only
research outputs. It does not touch Mochipoyo live/demo/autotrade files.

Fixed setup:
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT

Compared holding horizons:
    24h, 48h, 72h, 120h, NO_TIMEOUT

For finite horizons:
    M5 first-touch is checked until entry_time + horizon. If neither TP nor SL
    is touched, the trade is TIMEOUT and realized_r is marked-to-market using
    the last M5 close inside the horizon.

For NO_TIMEOUT:
    Hold until TP or SL is touched. If entry_time is before the first available
    M5 candle, outcome is NO_M5_PATH.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_env_rr2_sl_breakout_grid_no_timeout import (  # noqa: E402
    build_m15_trigger_base_for_lookback,
    build_trade_candidates_grid,
)
from scripts.research_gold_c_env_rr2_entry_window_no_timeout import (  # noqa: E402
    evaluate_trades_no_timeout,
)
from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    add_indicators,
    build_data_coverage,
    build_h1_events,
    load_research_csvs,
    max_drawdown_r,
    profit_factor,
    safe_float,
    write_csv,
)
from scripts.research_gold_h4_permission_modes_h1_regular_bullish_m15_break import (  # noqa: E402
    prepare_h4_env_frame,
)

BASE_CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT"
FINITE_EVALUATED_OUTCOMES = {"WIN", "LOSS", "TIMEOUT"}
NO_TIMEOUT_EVALUATED = {"WIN", "LOSS"}


def parse_horizons(text: str) -> list[str]:
    out: list[str] = []
    for raw in str(text).split(","):
        value = raw.strip().upper()
        if not value:
            continue
        if value in {"NO_TIMEOUT", "NONE", "NOWAIT"}:
            out.append("NO_TIMEOUT")
            continue
        hours = float(value.replace("H", ""))
        if hours <= 0:
            raise ValueError(f"horizon must be positive: {value}")
        out.append(f"{int(hours)}H" if hours.is_integer() else f"{str(hours).replace('.', 'P')}H")
    if not out:
        raise ValueError("--horizons must contain at least one horizon")
    return out


def horizon_hours(label: str) -> float | None:
    if label == "NO_TIMEOUT":
        return None
    return float(label.replace("H", "").replace("P", "."))


def condition_id_for_horizon(label: str) -> str:
    return f"{BASE_CONDITION_ID}_HORIZON_{label}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare holding horizons for best C_ENV RR2 setup.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_c_env_rr2_best_horizon_comparison"),
    )
    parser.add_argument("--horizons", type=str, default="24,48,72,120,NO_TIMEOUT")
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--entry-window-hours", type=float, default=12.0)
    parser.add_argument("--breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def judge_buy_first_touch_with_horizon(
    m5: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk: float,
    horizon_hours_value: float,
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
            "m5_coverage_ok": False,
        }

    m5_first_time = pd.Timestamp(m5["time"].min())
    if entry_time < m5_first_time:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": m5_first_time,
            "m5_last_time": pd.Timestamp(m5["time"].max()),
            "m5_coverage_ok": False,
        }

    end_time = entry_time + pd.to_timedelta(horizon_hours_value, unit="h")
    path = m5[(m5["time"] >= entry_time) & (m5["time"] < end_time)].copy()
    path = path.sort_values("time", kind="mergesort").reset_index(drop=True)
    if path.empty:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
            "hold_minutes": np.nan,
            "m5_first_time": m5_first_time,
            "m5_last_time": pd.Timestamp(m5["time"].max()),
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
                    "m5_coverage_ok": True,
                }
            return {
                "outcome": "LOSS",
                "exit_time": exit_time,
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": checked,
                "hold_minutes": hold_minutes,
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
                "m5_coverage_ok": True,
            }

    last = path.iloc[-1]
    exit_time = pd.Timestamp(last["time"])
    exit_price = safe_float(last["close"])
    return {
        "outcome": "TIMEOUT",
        "exit_time": exit_time,
        "exit_price": exit_price,
        "realized_r": (exit_price - entry_price) / risk,
        "bars_checked": int(len(path)),
        "hold_minutes": (exit_time - entry_time).total_seconds() / 60.0,
        "m5_coverage_ok": True,
    }


def evaluate_trades_for_horizon(trades: pd.DataFrame, m5: pd.DataFrame, args: argparse.Namespace, label: str) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()

    cond = condition_id_for_horizon(label)
    m5 = m5.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    h = horizon_hours(label)

    if h is None:
        out = evaluate_trades_no_timeout(trades, m5, args)
        if out.empty:
            return out
        out = out.copy()
        out["condition_id"] = cond
        out["horizon_label"] = label
        out["horizon_hours"] = np.nan
        out["is_evaluated"] = out["outcome"].isin(NO_TIMEOUT_EVALUATED)
        return out

    rows: list[dict[str, object]] = []
    for _, row in trades.iterrows():
        if str(row.get("initial_outcome")) == "INVALID_RISK":
            result = {
                "outcome": "INVALID_RISK",
                "exit_time": pd.NaT,
                "exit_price": np.nan,
                "realized_r": np.nan,
                "bars_checked": 0,
                "hold_minutes": np.nan,
                "m5_coverage_ok": False,
            }
        else:
            result = judge_buy_first_touch_with_horizon(
                m5,
                entry_time=pd.Timestamp(row["entry_time"]),
                entry_price=safe_float(row["entry_price"]),
                sl_price=safe_float(row["sl_price"]),
                tp_price=safe_float(row["tp_price"]),
                risk=safe_float(row["risk_price"]),
                horizon_hours_value=float(h),
                inbar_priority=str(args.inbar_priority),
            )
        trade = row.to_dict()
        trade.update(result)
        trade["condition_id"] = cond
        trade["horizon_label"] = label
        trade["horizon_hours"] = h
        rows.append(trade)

    out_df = pd.DataFrame(rows).sort_values(["horizon_label", "entry_time"], kind="mergesort").reset_index(drop=True)
    out_df["entry_month"] = pd.to_datetime(out_df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    out_df["is_evaluated"] = out_df["outcome"].isin(FINITE_EVALUATED_OUTCOMES)
    return out_df


def summarize_by_horizon(trades_eval: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition_id",
        "horizon_label",
        "horizon_hours",
        "trades",
        "wins",
        "losses",
        "timeouts",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_dd_r",
        "avg_hold_hours",
        "median_hold_hours",
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
        hold_hours = pd.to_numeric(group["hold_minutes"], errors="coerce") / 60.0
        rows.append(
            {
                "condition_id": condition_id,
                "horizon_label": str(group["horizon_label"].iloc[0]),
                "horizon_hours": group["horizon_hours"].iloc[0],
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "timeouts": int(group["outcome"].eq("TIMEOUT").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "median_hold_hours": float(hold_hours.median()),
                "max_hold_hours": float(hold_hours.max()),
                "first_entry_time": group["entry_time"].min(),
                "last_entry_time": group["entry_time"].max(),
                "months_with_trades": int(group["entry_month"].nunique()),
            }
        )
    out = pd.DataFrame(rows)[cols]
    order = {"24H": 24, "48H": 48, "72H": 72, "120H": 120, "NO_TIMEOUT": 999999}
    out["_order"] = out["horizon_label"].map(order).fillna(999998)
    return out.sort_values("_order", kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def summarize_all_by_horizon(trades_all: pd.DataFrame) -> pd.DataFrame:
    if trades_all.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for condition_id, group in trades_all.groupby("condition_id", dropna=False):
        rows.append(
            {
                "condition_id": condition_id,
                "horizon_label": str(group["horizon_label"].iloc[0]),
                "horizon_hours": group["horizon_hours"].iloc[0],
                "all_candidates": int(len(group)),
                "evaluated_candidates": int(group["is_evaluated"].sum()),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "timeouts": int(group["outcome"].eq("TIMEOUT").sum()),
                "no_m5_path": int(group["outcome"].eq("NO_M5_PATH").sum()),
                "invalid_risk": int(group["outcome"].eq("INVALID_RISK").sum()),
                "first_entry_time": group["entry_time"].min(),
                "last_entry_time": group["entry_time"].max(),
            }
        )
    out = pd.DataFrame(rows)
    order = {"24H": 24, "48H": 48, "72H": 72, "120H": 120, "NO_TIMEOUT": 999999}
    out["_order"] = out["horizon_label"].map(order).fillna(999998)
    return out.sort_values("_order", kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def summarize_monthly_by_horizon(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (condition_id, month), group in trades_eval.groupby(["condition_id", "entry_month"], dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        hold_hours = pd.to_numeric(group["hold_minutes"], errors="coerce") / 60.0
        rows.append(
            {
                "condition_id": condition_id,
                "horizon_label": str(group["horizon_label"].iloc[0]),
                "horizon_hours": group["horizon_hours"].iloc[0],
                "entry_month": str(month),
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "timeouts": int(group["outcome"].eq("TIMEOUT").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "max_hold_hours": float(hold_hours.max()),
            }
        )
    out = pd.DataFrame(rows)
    order = {"24H": 24, "48H": 48, "72H": 72, "120H": 120, "NO_TIMEOUT": 999999}
    out["_order"] = out["horizon_label"].map(order).fillna(999998)
    return out.sort_values(["_order", "entry_month"], kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    horizons = parse_horizons(args.horizons)

    print("[INFO] research-only best C_ENV RR2 horizon comparison")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] horizons={horizons}")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = BASE_CONDITION_ID
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base_for_lookback(
        m15,
        breakout_lookback=int(args.breakout_lookback),
        sl_lookback_m15=int(args.sl_lookback_m15),
    )
    pending = build_trade_candidates_grid(
        h1_events=h1_events,
        h4_env=h4_env,
        m15_base=m15_base,
        breakout_lookback=int(args.breakout_lookback),
        sl_mode="h1_pivot",
        args=args,
    )
    if not pending.empty:
        pending["condition_id"] = BASE_CONDITION_ID

    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")
    write_csv(m15_base, args.out_dir / "m15_trigger_base_bo8.csv")
    write_csv(pending, args.out_dir / "trades_pending_base.csv")

    all_results: list[pd.DataFrame] = []
    for label in horizons:
        print(f"[INFO] evaluating horizon={label}")
        evaluated = evaluate_trades_for_horizon(pending, m5, args, label) if not pending.empty else pd.DataFrame()
        if not evaluated.empty:
            all_results.append(evaluated)
        suffix = label.lower()
        write_csv(evaluated, args.out_dir / f"trades_all_candidates_{suffix}.csv")
        eval_outcomes = FINITE_EVALUATED_OUTCOMES if label != "NO_TIMEOUT" else NO_TIMEOUT_EVALUATED
        evaluated_only = evaluated[evaluated["outcome"].isin(eval_outcomes)].copy() if not evaluated.empty else pd.DataFrame()
        write_csv(evaluated_only, args.out_dir / f"trades_evaluated_only_{suffix}.csv")

    trades_all = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
    trades_eval_parts: list[pd.DataFrame] = []
    if not trades_all.empty:
        for label in horizons:
            part = trades_all[trades_all["horizon_label"].eq(label)].copy()
            eval_outcomes = FINITE_EVALUATED_OUTCOMES if label != "NO_TIMEOUT" else NO_TIMEOUT_EVALUATED
            trades_eval_parts.append(part[part["outcome"].isin(eval_outcomes)].copy())
    trades_eval = pd.concat(trades_eval_parts, ignore_index=True) if trades_eval_parts else pd.DataFrame()

    write_csv(trades_all, args.out_dir / "trades_all_candidates_all_horizons.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only_all_horizons.csv")
    write_csv(summarize_all_by_horizon(trades_all), args.out_dir / "summary_all_candidates_by_horizon.csv")
    write_csv(summarize_by_horizon(trades_eval), args.out_dir / "summary_evaluated_only_by_horizon.csv")
    write_csv(summarize_monthly_by_horizon(trades_eval), args.out_dir / "monthly_evaluated_only_by_horizon.csv")

    summary = summarize_by_horizon(trades_eval)
    print("[INFO] completed")
    print(f"[INFO] base_candidates={len(pending)} all_rows={len(trades_all)} evaluated_rows={len(trades_eval)}")
    print(summary.to_string(index=False) if not summary.empty else "[INFO] no evaluated trades")
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
