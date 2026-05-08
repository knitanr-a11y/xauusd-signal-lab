#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research GOLD C_ENV RR2 no-timeout SL/breakout grid.

Research-only script. It reads copied research CSV snapshots and writes only
research outputs. It does not touch Mochipoyo live/demo/autotrade files.

Fixed base rule:
    H4 C_ENV:
        Latest confirmed H4 candle at M15 signal close time:
            ema20 > ema50 and close > ema50

    H1:
        Newly confirmed H1 regular bullish divergence and loose exhaustion:
            close < ema50 OR ema20 < ema50

    M15:
        First M15 break trigger within 12h after H1 confirmation.
        close > high.shift(1).rolling(N).max()
        close > ema20
        MACD(6,13,4) > signal
        macd_hist > previous macd_hist

    Entry:
        M15 close.

    TP:
        RR2.0.

    Outcome:
        M5 first-touch without timeout. If TP and SL touch in the same M5 bar,
        SL wins by default.

Compared grid:
    breakout_lookback: 8, 12
    sl_mode:
        m15_lower12:
            SL = M15 rolling low(12) - M15 ATR14 * 0.05
        h1_pivot:
            SL = H1 regular bullish pivot low - M15 ATR14 * 0.05

Important M5 coverage rule:
    If entry_time is earlier than the first available M5 candle, the trade is
    NO_M5_PATH. Missing M5 history is never skipped.

Example:
    python scripts\research_gold_c_env_rr2_sl_breakout_grid_no_timeout.py ^
      --csv-dir data\research_csv_snapshots\gold_cb_20260508_01 ^
      --out-dir data\research_results\gold_c_env_rr2_sl_breakout_grid_no_timeout
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    DIRECTION,
    SYMBOL,
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
from scripts.research_gold_c_env_rr2_entry_window_no_timeout import (  # noqa: E402
    EVALUATED_OUTCOMES,
    evaluate_trades_no_timeout,
    first_m15_trigger_for_h1_event_env,
    parse_hours_csv,
)

SlMode = Literal["m15_lower12", "h1_pivot"]

BASE_CONDITION_PREFIX = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_12H"
SL_MODES: list[SlMode] = ["m15_lower12", "h1_pivot"]


def parse_int_csv(text: str) -> list[int]:
    out: list[int] = []
    for raw in str(text).split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw)
        if value <= 0:
            raise ValueError(f"lookback must be positive: {value}")
        out.append(value)
    if not out:
        raise ValueError("list must contain at least one value")
    return out


def parse_sl_modes(text: str) -> list[SlMode]:
    out: list[SlMode] = []
    for raw in str(text).split(","):
        value = raw.strip().lower()
        if not value:
            continue
        if value not in {"m15_lower12", "h1_pivot"}:
            raise ValueError(f"unsupported sl mode: {value}")
        out.append(value)  # type: ignore[arg-type]
    if not out:
        raise ValueError("--sl-modes must contain at least one mode")
    return out


def condition_id(*, breakout_lookback: int, sl_mode: SlMode, entry_window_hours: float, rr: float) -> str:
    win = int(entry_window_hours) if float(entry_window_hours).is_integer() else str(entry_window_hours).replace(".", "P")
    rr_text = int(rr) if float(rr).is_integer() else str(rr).replace(".", "P")
    return f"{BASE_CONDITION_PREFIX}_BO{breakout_lookback}_SL_{sl_mode.upper()}_RR{rr_text}_{win}H"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research C_ENV RR2 no-timeout SL/breakout grid.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_c_env_rr2_sl_breakout_grid_no_timeout"),
    )
    parser.add_argument("--entry-window-hours", type=float, default=12.0)
    parser.add_argument("--breakout-lookbacks", type=str, default="8,12")
    parser.add_argument("--sl-modes", type=str, default="m15_lower12,h1_pivot")
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def build_m15_trigger_base_for_lookback(m15: pd.DataFrame, *, breakout_lookback: int, sl_lookback_m15: int) -> pd.DataFrame:
    out = m15.copy()
    out["m15_rolling_high_prev"] = out["high"].shift(1).rolling(breakout_lookback, min_periods=breakout_lookback).max()
    out["m15_sl_base_low"] = out["low"].rolling(sl_lookback_m15, min_periods=sl_lookback_m15).min()
    out["m15_trigger_ok_base"] = (
        (out["close"] > out["m15_rolling_high_prev"])
        & (out["close"] > out["ema20"])
        & (out["macd"] > out["macd_signal"])
        & (out["macd_hist"] > out["macd_hist"].shift(1))
        & out["m15_sl_base_low"].notna()
        & out["atr14"].notna()
    )
    out = out[out["m15_trigger_ok_base"]].copy()
    out["m15_time"] = out["time"]
    out["m15_close_time"] = out["close_time"]
    out["m15_open"] = out["open"]
    out["m15_high"] = out["high"]
    out["m15_low"] = out["low"]
    out["m15_close"] = out["close"]
    out["m15_ema20"] = out["ema20"]
    out["m15_ema50"] = out["ema50"]
    out["m15_atr14"] = out["atr14"]
    out["m15_macd"] = out["macd"]
    out["m15_macd_signal"] = out["macd_signal"]
    out["m15_macd_hist"] = out["macd_hist"]
    out["breakout_lookback"] = breakout_lookback
    return out[
        [
            "m15_time",
            "m15_close_time",
            "m15_open",
            "m15_high",
            "m15_low",
            "m15_close",
            "m15_ema20",
            "m15_ema50",
            "m15_atr14",
            "m15_macd",
            "m15_macd_signal",
            "m15_macd_hist",
            "m15_rolling_high_prev",
            "m15_sl_base_low",
            "m15_trigger_ok_base",
            "breakout_lookback",
        ]
    ].reset_index(drop=True)


def make_sl_price(trigger: dict[str, object], *, sl_mode: SlMode, sl_atr_buffer_mult: float) -> tuple[float, str]:
    atr = safe_float(trigger.get("m15_atr14"))
    if sl_mode == "m15_lower12":
        base = safe_float(trigger.get("m15_sl_base_low"))
        label = "m15_lower12_minus_m15_atr_buffer"
    elif sl_mode == "h1_pivot":
        base = safe_float(trigger.get("h1_pivot_low"))
        label = "h1_pivot_low_minus_m15_atr_buffer"
    else:
        raise ValueError(f"unsupported sl_mode: {sl_mode}")
    if not all(math.isfinite(v) for v in [base, atr]):
        return float("nan"), label
    return base - atr * sl_atr_buffer_mult, label


def build_trade_candidates_grid(
    *,
    h1_events: pd.DataFrame,
    h4_env: pd.DataFrame,
    m15_base: pd.DataFrame,
    breakout_lookback: int,
    sl_mode: SlMode,
    args: argparse.Namespace,
) -> pd.DataFrame:
    cond = condition_id(
        breakout_lookback=breakout_lookback,
        sl_mode=sl_mode,
        entry_window_hours=float(args.entry_window_hours),
        rr=float(args.rr),
    )
    rows: list[dict[str, object]] = []
    for _, h1_event in h1_events.sort_values("h1_pivot_confirm_time", kind="mergesort").iterrows():
        trigger = first_m15_trigger_for_h1_event_env(
            h1_event,
            h4_env,
            m15_base,
            entry_window_hours=float(args.entry_window_hours),
        )
        if trigger is None:
            continue

        entry_price = safe_float(trigger.get("m15_close"))
        sl_price, sl_source = make_sl_price(trigger, sl_mode=sl_mode, sl_atr_buffer_mult=float(args.sl_atr_buffer_mult))
        risk = entry_price - sl_price
        if not all(math.isfinite(v) for v in [entry_price, sl_price, risk]) or risk <= 0:
            initial_outcome = "INVALID_RISK"
            tp_price = np.nan
        else:
            initial_outcome = "PENDING"
            tp_price = entry_price + risk * float(args.rr)

        entry_time = pd.Timestamp(trigger["m15_close_time"])
        row = {
            "condition_id": cond,
            "symbol": SYMBOL,
            "direction": DIRECTION,
            "entry_window_hours": float(args.entry_window_hours),
            "breakout_lookback": breakout_lookback,
            "sl_mode": sl_mode,
            "sl_source": sl_source,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "risk_price": risk,
            "rr": float(args.rr),
            "initial_outcome": initial_outcome,
            **trigger,
        }
        row["condition_id"] = cond
        row["trade_key"] = (
            f"{cond}|{row.get('h4_permission_reason','')}|{row.get('h1_event_id','')}|"
            f"{entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def summarize_evaluated_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition_id",
        "breakout_lookback",
        "sl_mode",
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
    for cond, group in trades_eval.groupby("condition_id", dropna=False):
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
                "condition_id": cond,
                "breakout_lookback": int(group["breakout_lookback"].iloc[0]),
                "sl_mode": str(group["sl_mode"].iloc[0]),
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
    return pd.DataFrame(rows)[cols].sort_values(["breakout_lookback", "sl_mode"], kind="mergesort").reset_index(drop=True)


def summarize_all_by_condition(trades_all: pd.DataFrame) -> pd.DataFrame:
    if trades_all.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for cond, group in trades_all.groupby("condition_id", dropna=False):
        rows.append(
            {
                "condition_id": cond,
                "breakout_lookback": int(group["breakout_lookback"].iloc[0]),
                "sl_mode": str(group["sl_mode"].iloc[0]),
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
    return pd.DataFrame(rows).sort_values(["breakout_lookback", "sl_mode"], kind="mergesort").reset_index(drop=True)


def summarize_monthly_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (cond, month), group in trades_eval.groupby(["condition_id", "entry_month"], dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        hold_hours = pd.to_numeric(group["hold_minutes"], errors="coerce") / 60.0
        rows.append(
            {
                "condition_id": cond,
                "breakout_lookback": int(group["breakout_lookback"].iloc[0]),
                "sl_mode": str(group["sl_mode"].iloc[0]),
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
    return pd.DataFrame(rows).sort_values(["breakout_lookback", "sl_mode", "entry_month"], kind="mergesort").reset_index(drop=True)


def select_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[[c for c in cols if c in df.columns]].copy() if not df.empty else pd.DataFrame(columns=cols)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    breakout_lookbacks = parse_int_csv(args.breakout_lookbacks)
    sl_modes = parse_sl_modes(args.sl_modes)

    print("[INFO] research-only C_ENV RR2 SL/breakout grid no-timeout")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] breakout_lookbacks={breakout_lookbacks} sl_modes={sl_modes} rr={args.rr} entry_window={args.entry_window_hours}h")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = "GOLD_C_ENV_RR2_SL_BREAKOUT_GRID_NO_TIMEOUT"
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    print("[INFO] adding indicators")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    print("[INFO] detecting H1 context events and H4 env rows")
    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")

    all_pending: list[pd.DataFrame] = []
    all_evaluated: list[pd.DataFrame] = []
    for breakout in breakout_lookbacks:
        m15_base = build_m15_trigger_base_for_lookback(
            m15,
            breakout_lookback=breakout,
            sl_lookback_m15=int(args.sl_lookback_m15),
        )
        write_csv(m15_base, args.out_dir / f"m15_trigger_base_bo{breakout}.csv")
        for sl_mode in sl_modes:
            print(f"[INFO] evaluating breakout={breakout} sl_mode={sl_mode}")
            pending = build_trade_candidates_grid(
                h1_events=h1_events,
                h4_env=h4_env,
                m15_base=m15_base,
                breakout_lookback=breakout,
                sl_mode=sl_mode,
                args=args,
            )
            evaluated = evaluate_trades_no_timeout(pending, m5, args) if not pending.empty else pd.DataFrame()
            if not pending.empty:
                all_pending.append(pending)
            if not evaluated.empty:
                all_evaluated.append(evaluated)
            suffix = f"bo{breakout}_sl_{sl_mode}"
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
        "breakout_lookback",
        "sl_mode",
        "sl_source",
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
        "m15_rolling_high_prev",
        "h1_pivot_confirm_time",
        "h1_pivot_low",
        "trigger_ok",
    ]
    write_csv(select_cols(trades_pending_all, trigger_cols), args.out_dir / "m15_trigger_candidates_all_grid.csv")
    write_csv(trades_all, args.out_dir / "trades_all_candidates_all_grid.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only_all_grid.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path_all_grid.csv")
    write_csv(summarize_all_by_condition(trades_all), args.out_dir / "summary_all_candidates_by_grid.csv")
    write_csv(summarize_evaluated_by_condition(trades_eval), args.out_dir / "summary_evaluated_only_by_grid.csv")
    write_csv(summarize_monthly_by_condition(trades_eval), args.out_dir / "monthly_evaluated_only_by_grid.csv")

    summary = summarize_evaluated_by_condition(trades_eval)
    print("[INFO] completed")
    print(f"[INFO] h1_events={len(h1_events)} all_candidates={len(trades_all)} evaluated={len(trades_eval)} no_m5_path={len(trades_no_m5)}")
    print(summary.to_string(index=False) if not summary.empty else "[INFO] no evaluated trades")
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
