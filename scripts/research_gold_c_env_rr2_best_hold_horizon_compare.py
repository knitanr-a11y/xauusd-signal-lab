#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare hold horizons for the best GOLD C_ENV RR2 setup.

Research-only. Reads copied CSV snapshots and writes research outputs only.

Fixed setup:
- H4 C_ENV: latest confirmed H4 ema20 > ema50 and close > ema50
- H1: regular bullish divergence + loose exhaustion
- M15: first BO8 trigger within 12h after H1 confirmation
- Entry: M15 close
- SL: H1 pivot low - M15 ATR14 * 0.05
- TP: RR2.0

Compared horizons:
- 24h / 48h / 72h / 120h: first-touch until horizon, otherwise TIME_EXIT at last M5 close before horizon
- no_timeout: first-touch until TP/SL, no forced exit

M5 coverage rule:
- If entry_time is before first available M5 candle, outcome is NO_M5_PATH.
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
from scripts.research_gold_h4_permission_modes_h1_regular_bullish_m15_break import prepare_h4_env_frame  # noqa: E402

BASE_CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT"
EVALUATED_OUTCOMES = {"WIN", "LOSS", "TIME_EXIT"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare hold horizons for best C_ENV RR2 setup.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_c_env_rr2_best_hold_horizon_compare"))
    p.add_argument("--horizons", type=str, default="24,48,72,120,no_timeout")
    p.add_argument("--pivot-left", type=int, default=2)
    p.add_argument("--pivot-right", type=int, default=2)
    p.add_argument("--entry-window-hours", type=float, default=12.0)
    p.add_argument("--breakout-lookback", type=int, default=8)
    p.add_argument("--sl-lookback-m15", type=int, default=12)
    p.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return p.parse_args()


def parse_horizons(text: str) -> list[str]:
    out: list[str] = []
    for raw in str(text).split(","):
        v = raw.strip().lower()
        if not v:
            continue
        if v in {"none", "no_timeout", "notimeout", "no-timeout"}:
            out.append("no_timeout")
        else:
            n = float(v[:-1] if v.endswith("h") else v)
            if n <= 0:
                raise ValueError(f"horizon must be positive: {raw}")
            out.append(f"{int(n) if n.is_integer() else str(n).replace('.', 'p')}h")
    if not out:
        raise ValueError("--horizons is empty")
    return out


def horizon_hours(mode: str) -> float | None:
    if mode == "no_timeout":
        return None
    return float(mode[:-1].replace("p", "."))


def condition_id(mode: str) -> str:
    return f"{BASE_CONDITION_ID}_NO_TIMEOUT" if mode == "no_timeout" else f"{BASE_CONDITION_ID}_HOLD_{mode.upper()}"


def eval_trade(
    m5: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk: float,
    mode: str,
    inbar_priority: str,
) -> dict[str, object]:
    if not all(math.isfinite(x) for x in [entry_price, sl_price, tp_price, risk]) or risk <= 0:
        return {"outcome": "INVALID_RISK", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0, "hold_minutes": np.nan, "m5_coverage_ok": False}
    if m5.empty:
        return {"outcome": "NO_M5_PATH", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0, "hold_minutes": np.nan, "m5_coverage_ok": False}

    m5_first = pd.Timestamp(m5["time"].min())
    m5_last = pd.Timestamp(m5["time"].max())
    if entry_time < m5_first:
        return {"outcome": "NO_M5_PATH", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0, "hold_minutes": np.nan, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": False}

    hours = horizon_hours(mode)
    if hours is None:
        path = m5[m5["time"] >= entry_time].copy()
    else:
        end_time = entry_time + pd.to_timedelta(hours, unit="h")
        path = m5[(m5["time"] >= entry_time) & (m5["time"] < end_time)].copy()
    path = path.sort_values("time", kind="mergesort").reset_index(drop=True)
    if path.empty:
        return {"outcome": "NO_M5_PATH", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0, "hold_minutes": np.nan, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": False}

    for checked, (_, bar) in enumerate(path.iterrows(), start=1):
        hit_sl = safe_float(bar["low"]) <= sl_price
        hit_tp = safe_float(bar["high"]) >= tp_price
        t = pd.Timestamp(bar["time"])
        hold_min = (t - entry_time).total_seconds() / 60.0
        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                return {"outcome": "WIN", "exit_time": t, "exit_price": tp_price, "realized_r": (tp_price - entry_price) / risk, "bars_checked": checked, "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}
            return {"outcome": "LOSS", "exit_time": t, "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked, "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}
        if hit_sl:
            return {"outcome": "LOSS", "exit_time": t, "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked, "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}
        if hit_tp:
            return {"outcome": "WIN", "exit_time": t, "exit_price": tp_price, "realized_r": (tp_price - entry_price) / risk, "bars_checked": checked, "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}

    last = path.iloc[-1]
    t = pd.Timestamp(last["time"])
    exit_price = safe_float(last["close"])
    hold_min = (t - entry_time).total_seconds() / 60.0
    if hours is None:
        return {"outcome": "NO_TOUCH_BEFORE_DATA_END", "exit_time": t, "exit_price": exit_price, "realized_r": np.nan, "bars_checked": int(len(path)), "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}
    return {"outcome": "TIME_EXIT", "exit_time": t, "exit_price": exit_price, "realized_r": (exit_price - entry_price) / risk, "bars_checked": int(len(path)), "hold_minutes": hold_min, "m5_first_time": m5_first, "m5_last_time": m5_last, "m5_coverage_ok": True}


def evaluate_for_mode(trades: pd.DataFrame, m5: pd.DataFrame, mode: str, args: argparse.Namespace) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    rows: list[dict[str, object]] = []
    m5 = m5.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    for _, row in trades.iterrows():
        result = eval_trade(
            m5,
            entry_time=pd.Timestamp(row["entry_time"]),
            entry_price=safe_float(row["entry_price"]),
            sl_price=safe_float(row["sl_price"]),
            tp_price=safe_float(row["tp_price"]),
            risk=safe_float(row["risk_price"]),
            mode=mode,
            inbar_priority=str(args.inbar_priority),
        )
        out = row.to_dict()
        out.update(result)
        out["condition_id"] = condition_id(mode)
        out["horizon_mode"] = mode
        out["horizon_hours"] = horizon_hours(mode) if mode != "no_timeout" else np.nan
        rows.append(out)
    df = pd.DataFrame(rows).sort_values(["horizon_mode", "entry_time"], kind="mergesort").reset_index(drop=True)
    df["entry_month"] = pd.to_datetime(df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    df["is_evaluated"] = df["outcome"].isin(EVALUATED_OUTCOMES)
    df["hold_hours"] = pd.to_numeric(df["hold_minutes"], errors="coerce") / 60.0
    return df


def summarize_by_horizon(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for cond, g in trades_eval.groupby("condition_id", dropna=False):
        g = g.sort_values("entry_time", kind="mergesort").copy()
        r = pd.to_numeric(g["realized_r"], errors="coerce")
        losses = g["outcome"].eq("LOSS").astype(int).tolist()
        max_consec = cur = 0
        for is_loss in losses:
            cur = cur + 1 if is_loss else 0
            max_consec = max(max_consec, cur)
        hold = pd.to_numeric(g["hold_hours"], errors="coerce")
        rows.append({
            "condition_id": cond,
            "horizon_mode": str(g["horizon_mode"].iloc[0]),
            "horizon_hours": g["horizon_hours"].iloc[0],
            "trades": int(len(g)),
            "wins": int(g["outcome"].eq("WIN").sum()),
            "losses": int(g["outcome"].eq("LOSS").sum()),
            "time_exits": int(g["outcome"].eq("TIME_EXIT").sum()),
            "win_rate": float(g["outcome"].eq("WIN").mean()),
            "total_r": float(r.sum()),
            "avg_r": float(r.mean()),
            "pf": profit_factor(r),
            "max_dd_r": max_drawdown_r(r),
            "max_consecutive_losses": int(max_consec),
            "avg_hold_hours": float(hold.mean()),
            "max_hold_hours": float(hold.max()),
            "first_entry_time": g["entry_time"].min(),
            "last_entry_time": g["entry_time"].max(),
            "months_with_trades": int(g["entry_month"].nunique()),
        })
    out = pd.DataFrame(rows)
    order = {"24h": 0, "48h": 1, "72h": 2, "120h": 3, "no_timeout": 4}
    out["_order"] = out["horizon_mode"].map(order).fillna(999)
    return out.sort_values("_order", kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def summarize_monthly(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (cond, month), g in trades_eval.groupby(["condition_id", "entry_month"], dropna=False):
        r = pd.to_numeric(g["realized_r"], errors="coerce")
        hold = pd.to_numeric(g["hold_hours"], errors="coerce")
        rows.append({
            "condition_id": cond,
            "horizon_mode": str(g["horizon_mode"].iloc[0]),
            "horizon_hours": g["horizon_hours"].iloc[0],
            "entry_month": str(month),
            "trades": int(len(g)),
            "wins": int(g["outcome"].eq("WIN").sum()),
            "losses": int(g["outcome"].eq("LOSS").sum()),
            "time_exits": int(g["outcome"].eq("TIME_EXIT").sum()),
            "win_rate": float(g["outcome"].eq("WIN").mean()),
            "total_r": float(r.sum()),
            "avg_r": float(r.mean()),
            "pf": profit_factor(r),
            "max_dd_r": max_drawdown_r(r),
            "avg_hold_hours": float(hold.mean()),
            "max_hold_hours": float(hold.max()),
        })
    out = pd.DataFrame(rows)
    order = {"24h": 0, "48h": 1, "72h": 2, "120h": 3, "no_timeout": 4}
    out["_order"] = out["horizon_mode"].map(order).fillna(999)
    return out.sort_values(["_order", "entry_month"], kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    horizons = parse_horizons(args.horizons)

    print("[INFO] research-only best C_ENV RR2 hold horizon comparison")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] horizons={horizons}")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = "GOLD_C_ENV_RR2_BEST_HOLD_HORIZON_COMPARE"
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base_for_lookback(m15, breakout_lookback=int(args.breakout_lookback), sl_lookback_m15=int(args.sl_lookback_m15))

    pending = build_trade_candidates_grid(
        h1_events=h1_events,
        h4_env=h4_env,
        m15_base=m15_base,
        breakout_lookback=int(args.breakout_lookback),
        sl_mode="h1_pivot",
        args=args,
    )

    all_eval: list[pd.DataFrame] = []
    for h in horizons:
        evaluated = evaluate_for_mode(pending, m5, h, args) if not pending.empty else pd.DataFrame()
        all_eval.append(evaluated)
        write_csv(evaluated, args.out_dir / f"trades_all_candidates_{h}.csv")
        write_csv(evaluated[evaluated["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not evaluated.empty else pd.DataFrame(), args.out_dir / f"trades_evaluated_only_{h}.csv")

    trades_all = pd.concat(all_eval, ignore_index=True) if all_eval else pd.DataFrame()
    trades_eval = trades_all[trades_all["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not trades_all.empty else pd.DataFrame()
    trades_no_m5 = trades_all[trades_all["outcome"].eq("NO_M5_PATH")].copy() if not trades_all.empty else pd.DataFrame()

    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")
    write_csv(m15_base, args.out_dir / "m15_trigger_base_bo8.csv")
    write_csv(pending, args.out_dir / "trades_pending_base.csv")
    write_csv(trades_all, args.out_dir / "trades_all_candidates_all_horizons.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only_all_horizons.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path_all_horizons.csv")
    write_csv(summarize_by_horizon(trades_eval), args.out_dir / "summary_evaluated_only_by_horizon.csv")
    write_csv(summarize_monthly(trades_eval), args.out_dir / "monthly_evaluated_only_by_horizon.csv")

    summary = summarize_by_horizon(trades_eval)
    print("[INFO] completed")
    print(f"[INFO] base_candidates={len(pending)} evaluated_rows={len(trades_eval)} no_m5_path_rows={len(trades_no_m5)}")
    print(summary.to_string(index=False) if not summary.empty else "[INFO] no evaluated trades")
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
