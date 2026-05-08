#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find historical replay candidates by M1 outcome for GOLD bearish A/B classifier.

This helper searches historical A/B classifier signals and judges each trade
with M1 first-touch using the same SELL rules as the dry-run position monitor:

- SELL TP touch: M1 low <= tp_price
- SELL SL touch: M1 high >= sl_price
- same M1 TP/SL conflict: SL priority by default
- realized R: (entry_price - exit_price) / risk_price

It is research-only and does not write ledgers, notifications, order intents, or
Mochipoyo/autotrade files.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (  # noqa: E402
    CONDITION_FAMILY_ID,
    add_indicators,
    attach_context,
    build_signal_candidates,
    load_frames,
    read_ohlc_csv,
    safe_float,
    write_csv,
)
from scripts.run_gold_h1h4_bear_ab_live_scan_once import compute_live_ab_flags  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find GOLD bearish A/B historical replay candidates by M1 outcome.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_h1h4_bear_ab_replay_outcomes"))
    p.add_argument("--rank", choices=["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE", "ALL"], default="ALL")
    p.add_argument("--outcome", choices=["WIN", "LOSS", "TIME_EXIT", "OPEN", "NO_M1_PATH", "ALL"], default="LOSS")
    p.add_argument("--start", type=str, default="2025-12-02 00:00:00")
    p.add_argument("--end", type=str, default="")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--sl-usd", type=float, default=10.0)
    p.add_argument("--tp-usd", type=float, default=20.0)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=float, default=12.0)
    p.add_argument("--cooldown-bars-m15", type=int, default=8)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--base-lot", type=float, default=0.10)
    p.add_argument("--core-lot-multiplier", type=float, default=2.0)
    p.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    p.add_argument("--max-lot-per-trade", type=float, default=99.0)
    return p.parse_args()


def judge_sell_m1(
    m1: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk_price: float,
    horizon_hours: float,
    inbar_priority: str,
) -> dict[str, Any]:
    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk_price]) or risk_price <= 0:
        return {"outcome": "INVALID_RISK", "exit_time": pd.NaT, "exit_price": pd.NA, "realized_r": pd.NA, "bars_checked": 0}

    horizon_time = entry_time + pd.to_timedelta(float(horizon_hours), unit="h")
    path = m1[(m1["time"] >= entry_time) & (m1["time"] < horizon_time)].copy()
    path = path.sort_values("time", kind="mergesort").reset_index(drop=True)
    if path.empty:
        return {"outcome": "NO_M1_PATH", "exit_time": pd.NaT, "exit_price": pd.NA, "realized_r": pd.NA, "bars_checked": 0}

    for idx, bar in path.iterrows():
        checked = int(idx) + 1
        low = safe_float(bar.get("low"))
        high = safe_float(bar.get("high"))
        hit_tp = math.isfinite(low) and low <= tp_price
        hit_sl = math.isfinite(high) and high >= sl_price
        if hit_tp and hit_sl:
            if str(inbar_priority).upper() == "TP":
                return {"outcome": "WIN", "exit_time": bar["time"], "exit_price": tp_price, "realized_r": (entry_price - tp_price) / risk_price, "bars_checked": checked, "reason": "TP_AND_SL_SAME_M1_TP_PRIORITY"}
            return {"outcome": "LOSS", "exit_time": bar["time"], "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked, "reason": "TP_AND_SL_SAME_M1_SL_PRIORITY"}
        if hit_sl:
            return {"outcome": "LOSS", "exit_time": bar["time"], "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked, "reason": "SL_TOUCHED_BEFORE_TP"}
        if hit_tp:
            return {"outcome": "WIN", "exit_time": bar["time"], "exit_price": tp_price, "realized_r": (entry_price - tp_price) / risk_price, "bars_checked": checked, "reason": "TP_TOUCHED_BEFORE_SL"}

    last = path.iloc[-1]
    exit_price = safe_float(last.get("close"))
    realized_r = (entry_price - exit_price) / risk_price if math.isfinite(exit_price) else pd.NA
    return {"outcome": "TIME_EXIT", "exit_time": last["time"], "exit_price": exit_price, "realized_r": realized_r, "bars_checked": int(len(path)), "reason": "NO_TP_SL_WITHIN_HORIZON"}


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_frames(args.csv_dir)
    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    ctx = attach_context(m15, h1, h4, d1)

    flags = compute_live_ab_flags(ctx)
    candidates = flags[flags["rank"] != "NO_SIGNAL"].copy()
    candidates["as_of_m15_close_time"] = pd.to_datetime(candidates["close_time"], errors="coerce")
    candidates["signal_bar_time"] = pd.to_datetime(candidates["time"], errors="coerce")

    if args.rank != "ALL":
        candidates = candidates[candidates["rank"].eq(args.rank)].copy()
    if args.start:
        candidates = candidates[candidates["as_of_m15_close_time"] >= pd.Timestamp(args.start)].copy()
    if args.end:
        candidates = candidates[candidates["as_of_m15_close_time"] <= pd.Timestamp(args.end)].copy()

    bt = build_signal_candidates(ctx, args)
    if bt.empty:
        print("[WARN] no backtest-style candidates; cannot judge entries")
        return 0
    bt_key = bt[["m15_close_time", "entry_time", "entry_price", "sl_price", "tp_price", "rank", "condition_id"]].copy()
    bt_key["as_of_m15_close_time"] = pd.to_datetime(bt_key["m15_close_time"], errors="coerce")
    bt_key = bt_key.rename(columns={
        "entry_time": "entry_time",
        "entry_price": "entry_price",
        "sl_price": "sl_price",
        "tp_price": "tp_price",
        "rank": "backtest_rank",
        "condition_id": "backtest_condition_id",
    })
    candidates = candidates.merge(bt_key.drop(columns=["m15_close_time"]), on="as_of_m15_close_time", how="inner")

    m1 = read_ohlc_csv(args.csv_dir / "goldsharp_m1.csv").sort_values("time", kind="mergesort").reset_index(drop=True)
    rows = []
    for _, row in candidates.sort_values("as_of_m15_close_time", kind="mergesort").iterrows():
        result = judge_sell_m1(
            m1,
            entry_time=pd.Timestamp(row["entry_time"]),
            entry_price=float(row["entry_price"]),
            sl_price=float(row["sl_price"]),
            tp_price=float(row["tp_price"]),
            risk_price=float(args.sl_usd),
            horizon_hours=float(args.horizon_hours),
            inbar_priority=str(args.inbar_priority),
        )
        rows.append({
            "rank": row["rank"],
            "condition_id": row["condition_id"],
            "signal_bar_time": row["signal_bar_time"],
            "as_of_m15_close_time": row["as_of_m15_close_time"],
            "entry_time": row["entry_time"],
            "entry_price": row["entry_price"],
            "sl_price": row["sl_price"],
            "tp_price": row["tp_price"],
            "a_pass": row["a_pass"],
            "b_pass": row["b_pass"],
            "lot_multiplier": 2.0 if row["rank"] == "CORE_AB_CONFIRM" else (1.0 if row["rank"] == "B_ONLY_SAFE" else 0.0),
            **result,
        })

    out = pd.DataFrame(rows)
    if args.outcome != "ALL" and not out.empty:
        out = out[out["outcome"].eq(args.outcome)].copy()
    out = out.sort_values("as_of_m15_close_time", kind="mergesort").reset_index(drop=True)
    write_csv(out, args.out_dir / "replay_outcome_candidates_all.csv")
    head = out.head(max(args.limit, 0)).copy()
    write_csv(head, args.out_dir / "replay_outcome_candidates_head.csv")

    print(f"[INFO] outcome_candidates={len(out)} rank={args.rank} outcome={args.outcome}")
    if head.empty:
        print("[INFO] no candidates found")
        return 0
    show_cols = ["rank", "as_of_m15_close_time", "entry_price", "sl_price", "tp_price", "outcome", "exit_time", "realized_r", "reason"]
    print(head[show_cols].to_string(index=False))
    first_time = head.iloc[0]["as_of_m15_close_time"]
    print("\n[INFO] Replay command example:")
    print(
        'python scripts\\run_gold_h1h4_bear_ab_historical_replay_simple.py '
        f'--csv-dir "{args.csv_dir}" '
        '--out-dir data\\research_results\\gold_h1h4_bear_ab_historical_replay_simple_loss '
        f'--as-of-m15-close-time "{first_time}" --reset-out-dir'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
