#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare GOLD H4 permission modes for H1 regular bullish -> M15 break.

Research-only script. It reads copied research CSV snapshots and writes only
research outputs. It does not touch Mochipoyo live/demo/autotrade files.

Compared condition IDs:
    GOLD_C_STRICT_H1_REGULAR_BULLISH_M15_BREAK_48H
        H4 regular bullish divergence confirmed within 48h only.

    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK
        Latest confirmed H4 candle is in up environment only:
            H4 ema20 > ema50 and H4 close > ema50

    GOLD_C_STRICT_OR_ENV_H1_REGULAR_BULLISH_M15_BREAK_48H
        Either strict recent H4 regular bullish divergence within 48h OR H4 env up.

Common H1/M15/exit rules:
    H1 regular bullish divergence + loose exhaustion.
    First M15 break trigger within 24h after H1 confirmation.
    Entry = M15 close.
    SL = M15 rolling low(12) - ATR14 * 0.05.
    TP = RR 1.5.
    M5 first-touch, 24h horizon, same-bar TP/SL = SL loss.

Example:
    python scripts\research_gold_h4_permission_modes_h1_regular_bullish_m15_break.py ^
      --csv-dir data\research_csv_snapshots\gold_cb_20260508_01 ^
      --out-dir data\research_results\gold_h4_permission_modes_h1_regular_bullish_m15_break
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
    CONDITION_ID as STRICT_CONDITION_ID,
    DIRECTION,
    EVALUATED_OUTCOMES,
    REQUIRED_FILES,
    SYMBOL,
    add_indicators,
    build_data_coverage,
    build_h1_events,
    build_h4_events,
    build_m15_trigger_base,
    evaluate_trades,
    load_research_csvs,
    safe_float,
    summarize_all_candidates,
    summarize_evaluated,
    summarize_monthly,
    write_csv,
)

PermissionMode = Literal["STRICT", "ENV", "STRICT_OR_ENV"]

CONDITION_IDS: dict[PermissionMode, str] = {
    "STRICT": "GOLD_C_STRICT_H1_REGULAR_BULLISH_M15_BREAK_48H",
    "ENV": "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK",
    "STRICT_OR_ENV": "GOLD_C_STRICT_OR_ENV_H1_REGULAR_BULLISH_M15_BREAK_48H",
}

MODE_ORDER: list[PermissionMode] = ["STRICT", "ENV", "STRICT_OR_ENV"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare GOLD H4 permission modes for H1 regular bullish M15 break."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        required=True,
        help="Copied research CSV snapshot directory containing goldsharp_h4/h1/m15/m5 CSVs.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_h4_permission_modes_h1_regular_bullish_m15_break"),
        help="Research-only output directory.",
    )
    parser.add_argument("--h4-permission-hours", type=float, default=48.0)
    parser.add_argument("--h1-entry-search-hours", type=float, default=24.0)
    parser.add_argument("--outcome-horizon-hours", type=float, default=24.0)
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--m15-breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def prepare_h4_env_frame(h4: pd.DataFrame) -> pd.DataFrame:
    out = h4.copy().sort_values("close_time", kind="mergesort").reset_index(drop=True)
    out["h4_env_up"] = (out["ema20"] > out["ema50"]) & (out["close"] > out["ema50"])
    return out[
        [
            "time",
            "close_time",
            "open",
            "high",
            "low",
            "close",
            "ema20",
            "ema50",
            "atr14",
            "macd",
            "macd_signal",
            "macd_hist",
            "h4_env_up",
        ]
    ].rename(
        columns={
            "time": "h4_env_time",
            "close_time": "h4_env_close_time",
            "open": "h4_env_open",
            "high": "h4_env_high",
            "low": "h4_env_low",
            "close": "h4_env_close",
            "ema20": "h4_env_ema20",
            "ema50": "h4_env_ema50",
            "atr14": "h4_env_atr14",
            "macd": "h4_env_macd",
            "macd_signal": "h4_env_macd_signal",
            "macd_hist": "h4_env_macd_hist",
        }
    )


def latest_h4_event_before(h4_events: pd.DataFrame, ts: pd.Timestamp) -> pd.Series | None:
    if h4_events.empty:
        return None
    eligible = h4_events[h4_events["h4_pivot_confirm_time"] <= ts]
    if eligible.empty:
        return None
    return eligible.sort_values("h4_pivot_confirm_time", kind="mergesort").iloc[-1]


def latest_h4_env_before(h4_env: pd.DataFrame, ts: pd.Timestamp) -> pd.Series | None:
    if h4_env.empty:
        return None
    eligible = h4_env[h4_env["h4_env_close_time"] <= ts]
    if eligible.empty:
        return None
    return eligible.sort_values("h4_env_close_time", kind="mergesort").iloc[-1]


def permission_info(
    mode: PermissionMode,
    h4_events: pd.DataFrame,
    h4_env: pd.DataFrame,
    m15_close_time: pd.Timestamp,
    permission_hours: float,
) -> dict[str, object] | None:
    latest_event = latest_h4_event_before(h4_events, m15_close_time)
    latest_env = latest_h4_env_before(h4_env, m15_close_time)

    strict_ok = False
    h4_age_hours = np.nan
    event_dict: dict[str, object] = {}
    if latest_event is not None:
        h4_confirm = pd.Timestamp(latest_event["h4_pivot_confirm_time"])
        h4_age_hours = (m15_close_time - h4_confirm).total_seconds() / 3600.0
        strict_ok = 0.0 <= h4_age_hours <= float(permission_hours)
        event_dict = latest_event.to_dict()

    env_ok = False
    env_dict: dict[str, object] = {}
    if latest_env is not None:
        env_ok = bool(latest_env.get("h4_env_up", False))
        env_dict = latest_env.to_dict()

    if mode == "STRICT":
        allowed = strict_ok
    elif mode == "ENV":
        allowed = env_ok
    elif mode == "STRICT_OR_ENV":
        allowed = strict_ok or env_ok
    else:
        raise ValueError(f"Unknown permission mode: {mode}")

    if not allowed:
        return None

    if strict_ok and env_ok:
        reason = "recent_h4_regular_bullish_and_h4_env_up"
    elif strict_ok:
        reason = "recent_h4_regular_bullish"
    elif env_ok:
        reason = "h4_env_up"
    else:
        reason = "UNKNOWN_SHOULD_NOT_HAPPEN"

    return {
        **event_dict,
        **env_dict,
        "h4_permission_mode": mode,
        "h4_permission_reason": reason,
        "h4_permission_age_hours": h4_age_hours,
        "h4_strict_permission_ok": strict_ok,
        "h4_env_permission_ok": env_ok,
        "h4_permission_ok": True,
    }


def first_m15_trigger_for_h1_event_by_mode(
    mode: PermissionMode,
    h1_event: pd.Series,
    h4_events: pd.DataFrame,
    h4_env: pd.DataFrame,
    m15_base: pd.DataFrame,
    args: argparse.Namespace,
) -> dict[str, object] | None:
    h1_confirm = pd.Timestamp(h1_event["h1_pivot_confirm_time"])
    search_end = h1_confirm + pd.to_timedelta(args.h1_entry_search_hours, unit="h")
    candidates = m15_base[
        (m15_base["m15_close_time"] >= h1_confirm)
        & (m15_base["m15_close_time"] <= search_end)
    ].copy()
    if candidates.empty:
        return None

    for _, m15_row in candidates.sort_values("m15_close_time", kind="mergesort").iterrows():
        m15_close_time = pd.Timestamp(m15_row["m15_close_time"])
        perm = permission_info(
            mode,
            h4_events,
            h4_env,
            m15_close_time,
            float(args.h4_permission_hours),
        )
        if perm is None:
            continue
        out: dict[str, object] = {**h1_event.to_dict(), **m15_row.to_dict(), **perm}
        out["condition_id"] = CONDITION_IDS[mode]
        out["trigger_ok"] = True
        return out
    return None


def build_trade_candidates_by_mode(
    mode: PermissionMode,
    h1_events: pd.DataFrame,
    h4_events: pd.DataFrame,
    h4_env: pd.DataFrame,
    m15_base: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    condition_id = CONDITION_IDS[mode]
    for _, h1_event in h1_events.sort_values("h1_pivot_confirm_time", kind="mergesort").iterrows():
        trigger = first_m15_trigger_for_h1_event_by_mode(mode, h1_event, h4_events, h4_env, m15_base, args)
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
            "permission_mode": mode,
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
            f"{condition_id}|{row.get('h4_permission_reason','')}|{row.get('h4_event_id','')}|"
            f"{row.get('h1_event_id','')}|{entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def evaluate_mode_trades(trades_pending: pd.DataFrame, m5: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if trades_pending.empty:
        return trades_pending.copy()

    # Reuse base script evaluator but keep per-mode condition_id. It does not depend on STRICT_CONDITION_ID.
    original_condition_id = STRICT_CONDITION_ID
    _ = original_condition_id  # keep import explicit and lint quiet
    return evaluate_trades(trades_pending, m5, args)


def summarize_evaluated_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame(
            columns=[
                "condition_id",
                "permission_mode",
                "trades",
                "wins",
                "losses",
                "timeouts",
                "win_rate",
                "total_r",
                "avg_r",
                "pf",
                "max_dd_r",
                "first_entry_time",
                "last_entry_time",
                "months_with_trades",
            ]
        )

    rows: list[pd.DataFrame] = []
    for condition_id, group in trades_eval.groupby("condition_id", dropna=False):
        summary = summarize_evaluated(group)
        summary["condition_id"] = condition_id
        summary["permission_mode"] = group["permission_mode"].iloc[0] if "permission_mode" in group.columns else ""
        rows.append(summary)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    order_cols = ["condition_id", "permission_mode"] + [c for c in out.columns if c not in {"condition_id", "permission_mode"}]
    return out[order_cols]


def summarize_all_by_condition(trades_all: pd.DataFrame) -> pd.DataFrame:
    if trades_all.empty:
        return pd.DataFrame()
    rows: list[pd.DataFrame] = []
    for condition_id, group in trades_all.groupby("condition_id", dropna=False):
        summary = summarize_all_candidates(group)
        summary["condition_id"] = condition_id
        summary["permission_mode"] = group["permission_mode"].iloc[0] if "permission_mode" in group.columns else ""
        rows.append(summary)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    order_cols = ["condition_id", "permission_mode"] + [c for c in out.columns if c not in {"condition_id", "permission_mode"}]
    return out[order_cols]


def summarize_monthly_by_condition(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[pd.DataFrame] = []
    for condition_id, group in trades_eval.groupby("condition_id", dropna=False):
        summary = summarize_monthly(group)
        summary["condition_id"] = condition_id
        summary["permission_mode"] = group["permission_mode"].iloc[0] if "permission_mode" in group.columns else ""
        rows.append(summary)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    order_cols = ["condition_id", "permission_mode"] + [c for c in out.columns if c not in {"condition_id", "permission_mode"}]
    return out[order_cols].sort_values(["condition_id", "entry_month"], kind="mergesort").reset_index(drop=True)


def select_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[[c for c in cols if c in df.columns]].copy() if not df.empty else pd.DataFrame(columns=cols)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] research-only H4 permission mode comparison")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = "MULTI_H4_PERMISSION_MODE_COMPARISON"
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    print("[INFO] adding indicators")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    print("[INFO] detecting context events")
    h4_events = build_h4_events(h4, args)
    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base(m15, args)

    write_csv(h4_events, args.out_dir / "context_h4_regular_bullish_events.csv")
    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")

    all_pending: list[pd.DataFrame] = []
    all_evaluated: list[pd.DataFrame] = []

    for mode in MODE_ORDER:
        print(f"[INFO] building/evaluating mode={mode} condition_id={CONDITION_IDS[mode]}")
        pending = build_trade_candidates_by_mode(mode, h1_events, h4_events, h4_env, m15_base, args)
        evaluated = evaluate_mode_trades(pending, m5, args) if not pending.empty else pd.DataFrame()
        if not pending.empty:
            all_pending.append(pending)
        if not evaluated.empty:
            all_evaluated.append(evaluated)
        write_csv(pending, args.out_dir / f"trades_pending_{mode.lower()}.csv")
        write_csv(evaluated, args.out_dir / f"trades_all_candidates_{mode.lower()}.csv")
        evaluated_only = evaluated[evaluated["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not evaluated.empty else pd.DataFrame()
        no_m5 = evaluated[evaluated["outcome"].eq("NO_M5_PATH")].copy() if not evaluated.empty else pd.DataFrame()
        write_csv(evaluated_only, args.out_dir / f"trades_evaluated_only_{mode.lower()}.csv")
        write_csv(no_m5, args.out_dir / f"trades_no_m5_path_{mode.lower()}.csv")

    trades_pending_all = pd.concat(all_pending, ignore_index=True) if all_pending else pd.DataFrame()
    trades_all = pd.concat(all_evaluated, ignore_index=True) if all_evaluated else pd.DataFrame()
    trades_eval = trades_all[trades_all["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not trades_all.empty else pd.DataFrame()
    trades_no_m5 = trades_all[trades_all["outcome"].eq("NO_M5_PATH")].copy() if not trades_all.empty else pd.DataFrame()

    trigger_cols = [
        "condition_id",
        "permission_mode",
        "h1_event_id",
        "h4_event_id",
        "h4_permission_reason",
        "h4_permission_age_hours",
        "h4_strict_permission_ok",
        "h4_env_permission_ok",
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
        "h4_pivot_confirm_time",
        "trigger_ok",
    ]
    write_csv(select_cols(trades_pending_all, trigger_cols), args.out_dir / "m15_trigger_candidates_all_modes.csv")
    write_csv(trades_all, args.out_dir / "trades_all_candidates_all_modes.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only_all_modes.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path_all_modes.csv")
    write_csv(summarize_all_by_condition(trades_all), args.out_dir / "summary_all_candidates_by_condition.csv")
    write_csv(summarize_evaluated_by_condition(trades_eval), args.out_dir / "summary_evaluated_only_by_condition.csv")
    write_csv(summarize_monthly_by_condition(trades_eval), args.out_dir / "monthly_evaluated_only_by_condition.csv")

    summary = summarize_evaluated_by_condition(trades_eval)
    print("[INFO] completed")
    print(f"[INFO] h4_events={len(h4_events)} h1_events={len(h1_events)} m15_base_triggers={len(m15_base)}")
    print(f"[INFO] all_candidates={len(trades_all)} evaluated={len(trades_eval)} no_m5_path={len(trades_no_m5)}")
    print(summary.to_string(index=False) if not summary.empty else "[INFO] no evaluated trades")
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
