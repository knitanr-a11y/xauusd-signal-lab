#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC multi-strategy dry-run cycle.

This script reads BTC OHLC CSVs once, calculates shared indicators once, runs all
BTC strategy detectors, and writes Mochipoyo/sender-compatible order payloads.

No MT5 calls, no Discord calls, and no state mutation happen in this script.
The guarded sender is called only by run_btc_multi_strategy_guarded_demo_send_once.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from btc_multi_strategy_signals import (  # noqa: E402
    DEFAULT_STRATEGY_TRADE_ENABLED,
    OUTPUT_COLUMNS,
    STRATEGY_BULL_STACK_BUY,
    STRATEGY_D1_LOW_BREAK_SELL,
    STRATEGY_EARLY_SELL_OBSERVE,
    STRATEGY_PULLBACK_SELL,
    StrategyParams,
    build_joined_frame,
    candidate_count_by_strategy,
    detect_candidates,
    ensure_output_columns,
    filter_live_candidates,
    latest_m15_time,
    windows_long_path,
)

DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_multi_strategy_dry_run_cycle")
SUMMARY_FILENAME = "latest_btc_multi_strategy_dry_run_cycle_result.json"

PAYLOAD_COLUMNS = [
    "payload_key", "order_key", "signal_key", "broker_symbol", "symbol",
    "direction", "lot", "entry_price_reference", "sl_price", "tp_price",
    "magic_number", "strategy_key", "strategy_alias", "strategy_id",
    "condition_id", "router_strategy_slot", "router_strategy_id",
    "candidate_rank", "source", "entry_time", "rr", "horizon_hours",
    "spread_cost_usd",
]

STRATEGY_PRIORITY = {
    "SELL_D1_LOW_BREAK": 10,
    "SELL_PULLBACK_REJECT": 20,
    "BUY_BULL_STACK_BREAK": 30,
    "SELL_EARLY_LOW_BREAK": 99,
}


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def resolve_csv(csv_dir: Path, explicit: str | None, filename: str) -> Path:
    return Path(explicit) if explicit else csv_dir / filename


def parse_bool_strategy_overrides(args: argparse.Namespace) -> dict[str, bool]:
    enabled = dict(DEFAULT_STRATEGY_TRADE_ENABLED)
    enabled[STRATEGY_PULLBACK_SELL] = bool(args.enable_sell_pullback_reject)
    enabled[STRATEGY_D1_LOW_BREAK_SELL] = bool(args.enable_sell_d1_low_break)
    enabled[STRATEGY_BULL_STACK_BUY] = bool(args.enable_buy_bull_stack_break)
    enabled[STRATEGY_EARLY_SELL_OBSERVE] = bool(args.enable_sell_early_low_break_trade)
    return enabled


def apply_cooldown(candidates: pd.DataFrame, *, cooldown_bars_m15: int) -> pd.DataFrame:
    """Keep first candidate per strategy/direction, then suppress repeats for N M15 bars."""
    if candidates.empty or int(cooldown_bars_m15) <= 0:
        return candidates.copy()
    work = candidates.copy()
    work["_entry_time_dt"] = pd.to_datetime(work["entry_time"], errors="coerce")
    work = work.sort_values(["strategy_slot", "direction", "_entry_time_dt"]).reset_index(drop=True)
    keep_indices: list[int] = []
    cooldown_minutes = int(cooldown_bars_m15) * 15
    last_kept: dict[tuple[str, str], pd.Timestamp] = {}
    for idx, row in work.iterrows():
        key = (str(row.get("strategy_slot", "")), str(row.get("direction", "")))
        ts = pd.Timestamp(row["_entry_time_dt"])
        prev = last_kept.get(key)
        if prev is None or (ts - prev).total_seconds() >= cooldown_minutes * 60:
            keep_indices.append(int(idx))
            last_kept[key] = ts
    out = work.loc[keep_indices].drop(columns=["_entry_time_dt"], errors="ignore")
    return out.sort_values(["entry_time", "strategy_slot"]).reset_index(drop=True)


def select_payload_candidates(candidates: pd.DataFrame, *, max_payload_rows: int) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    trade = candidates[candidates["trade_enabled"].astype(bool)].copy()
    if trade.empty:
        return trade
    trade["_priority"] = trade["strategy_slot"].map(STRATEGY_PRIORITY).fillna(50).astype(int)
    trade["_entry_time_dt"] = pd.to_datetime(trade["entry_time"], errors="coerce")
    trade = trade.sort_values(["_entry_time_dt", "_priority", "strategy_slot"]).drop(columns=["_priority", "_entry_time_dt"], errors="ignore")
    if max_payload_rows >= 0:
        trade = trade.head(int(max_payload_rows))
    return trade.reset_index(drop=True)


def build_payload_df(candidates: pd.DataFrame, *, magic: int) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=PAYLOAD_COLUMNS)
    rows: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        rows.append({
            "payload_key": row.get("payload_key", ""),
            "order_key": row.get("order_key", ""),
            "signal_key": row.get("signal_key", ""),
            "broker_symbol": row.get("broker_symbol", "BTCUSD#"),
            "symbol": row.get("symbol", "BTC"),
            "direction": row.get("direction", ""),
            "lot": row.get("lot", 0.0),
            "entry_price_reference": row.get("entry_price_reference", 0.0),
            "sl_price": row.get("sl_price", 0.0),
            "tp_price": row.get("tp_price", 0.0),
            "magic_number": int(magic),
            "strategy_key": row.get("strategy_slot", ""),
            "strategy_alias": row.get("strategy_alias", row.get("strategy_slot", "")),
            "strategy_id": row.get("strategy_id", ""),
            "condition_id": row.get("condition_id", row.get("strategy_id", "")),
            "router_strategy_slot": row.get("strategy_slot", ""),
            "router_strategy_id": row.get("strategy_id", ""),
            "candidate_rank": row.get("candidate_rank", ""),
            "source": "btc_multi_strategy_dry_run_cycle",
            "entry_time": row.get("entry_time", ""),
            "rr": row.get("rr", 2.0),
            "horizon_hours": row.get("horizon_hours", 72),
            "spread_cost_usd": row.get("spread_cost_usd", 22.5),
        })
    return pd.DataFrame(rows, columns=PAYLOAD_COLUMNS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one BTC multi-strategy dry-run scan cycle. No MT5 calls.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    p.add_argument("--btc-d1-csv")
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--symbol", default="BTC")
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--spread-cost-usd", type=float, default=22.5)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=int, default=72)
    p.add_argument("--magic", type=int, default=26050604)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--live-lookback-bars", type=int, default=1)
    p.add_argument("--max-payload-rows", type=int, default=1)
    p.add_argument("--cooldown-bars-m15", type=int, default=16, help="Per strategy/direction event cooldown. 16 M15 bars = 4 hours.")
    p.add_argument("--tail-m15", type=int, default=20000)
    p.add_argument("--tail-h1", type=int, default=5000)
    p.add_argument("--tail-h4", type=int, default=3000)
    p.add_argument("--tail-d1", type=int, default=1000)
    p.add_argument("--enable-sell-pullback-reject", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--enable-sell-d1-low-break", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--enable-buy-bull-stack-break", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--enable-sell-early-low-break-trade", action=argparse.BooleanOptionalAction, default=False)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    mkdir_path(args.out_dir)

    paths = {
        "m15_csv": resolve_csv(args.csv_dir, args.btc_m15_csv, "btcusdsharp_m15.csv"),
        "h1_csv": resolve_csv(args.csv_dir, args.btc_h1_csv, "btcusdsharp_h1.csv"),
        "h4_csv": resolve_csv(args.csv_dir, args.btc_h4_csv, "btcusdsharp_h4.csv"),
        "d1_csv": resolve_csv(args.csv_dir, args.btc_d1_csv, "btcusdsharp_d1.csv"),
        "all_candidates_csv": args.out_dir / "candidates" / "btc_multi_strategy_candidates_all.csv",
        "live_candidates_csv": args.out_dir / "candidates" / "btc_multi_strategy_candidates_live.csv",
        "selected_payload_candidates_csv": args.out_dir / "payload" / "btc_multi_strategy_selected_payload_candidates.csv",
        "order_payloads_csv": args.out_dir / "payload" / "order_payloads.csv",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
    }

    print("=" * 80, flush=True)
    print("BTC multi-strategy dry-run cycle", flush=True)
    print("No MT5 calls. No order_send. CSV/indicator calculation is shared across all BTC detectors.", flush=True)
    print(f"csv_dir={args.csv_dir}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"broker_symbol={args.broker_symbol} base_lot={args.base_lot} spread_cost_usd={args.spread_cost_usd}", flush=True)
    print("=" * 80, flush=True)

    try:
        joined, frames = build_joined_frame(
            m15_csv=paths["m15_csv"], h1_csv=paths["h1_csv"], h4_csv=paths["h4_csv"], d1_csv=paths["d1_csv"],
            csv_sep=args.csv_sep, tail_m15=args.tail_m15, tail_h1=args.tail_h1, tail_h4=args.tail_h4, tail_d1=args.tail_d1,
        )
        latest_time = latest_m15_time(frames["m15"], latest_confirmed_policy=args.latest_confirmed_policy)
        params = StrategyParams(
            base_lot=float(args.base_lot), spread_cost_usd=float(args.spread_cost_usd), rr=float(args.rr),
            horizon_hours=int(args.horizon_hours), broker_symbol=str(args.broker_symbol), symbol=str(args.symbol),
        )
        trade_enabled = parse_bool_strategy_overrides(args)
        raw_candidates = detect_candidates(joined, params=params, trade_enabled=trade_enabled)
        all_candidates = apply_cooldown(raw_candidates, cooldown_bars_m15=int(args.cooldown_bars_m15))
        live_candidates = filter_live_candidates(
            all_candidates, latest_time=latest_time, live_lookback_bars=max(1, int(args.live_lookback_bars)), m15=frames["m15"],
        )
        selected = select_payload_candidates(live_candidates, max_payload_rows=int(args.max_payload_rows))
        payload_df = build_payload_df(selected, magic=int(args.magic))
        cycle_ok = True
        reason = "BTC_MULTI_STRATEGY_DRY_RUN_CYCLE_PASS"
        error = ""
    except Exception as exc:
        joined = pd.DataFrame()
        frames = {"m15": pd.DataFrame(), "h1": pd.DataFrame(), "h4": pd.DataFrame(), "d1": pd.DataFrame()}
        latest_time = None
        raw_candidates = pd.DataFrame(columns=OUTPUT_COLUMNS)
        all_candidates = pd.DataFrame(columns=OUTPUT_COLUMNS)
        live_candidates = pd.DataFrame(columns=OUTPUT_COLUMNS)
        selected = pd.DataFrame(columns=OUTPUT_COLUMNS)
        payload_df = pd.DataFrame(columns=PAYLOAD_COLUMNS)
        cycle_ok = False
        reason = "BTC_MULTI_STRATEGY_DRY_RUN_CYCLE_FAILED"
        error = repr(exc)

    write_csv(ensure_output_columns(all_candidates), paths["all_candidates_csv"])
    write_csv(ensure_output_columns(live_candidates), paths["live_candidates_csv"])
    write_csv(ensure_output_columns(selected), paths["selected_payload_candidates_csv"])
    write_csv(payload_df, paths["order_payloads_csv"])

    summary = {
        "schema_version": "btc_multi_strategy_dry_run_cycle_v1",
        "cycle_at_utc": utc_now_text(),
        "cycle_ok": bool(cycle_ok),
        "reason": reason,
        "error": error,
        "broker_symbol": str(args.broker_symbol),
        "symbol": str(args.symbol),
        "base_lot": float(args.base_lot),
        "spread_cost_usd": float(args.spread_cost_usd),
        "rr": float(args.rr),
        "horizon_hours": int(args.horizon_hours),
        "latest_confirmed_policy": str(args.latest_confirmed_policy),
        "latest_m15_time": "" if latest_time is None else pd.Timestamp(latest_time).strftime("%Y-%m-%d %H:%M:%S"),
        "live_lookback_bars": int(args.live_lookback_bars),
        "max_payload_rows": int(args.max_payload_rows),
        "cooldown_bars_m15": int(args.cooldown_bars_m15),
        "rows": {
            "m15_rows": int(len(frames.get("m15", pd.DataFrame()))),
            "h1_rows": int(len(frames.get("h1", pd.DataFrame()))),
            "h4_rows": int(len(frames.get("h4", pd.DataFrame()))),
            "d1_rows": int(len(frames.get("d1", pd.DataFrame()))),
            "joined_rows": int(len(joined)),
            "raw_candidate_rows": int(len(raw_candidates)),
            "all_candidate_rows_after_cooldown": int(len(all_candidates)),
            "live_candidate_rows": int(len(live_candidates)),
            "selected_payload_candidate_rows": int(len(selected)),
            "payload_rows_out": int(len(payload_df)),
        },
        "raw_candidate_count_by_strategy": candidate_count_by_strategy(raw_candidates),
        "candidate_count_by_strategy": candidate_count_by_strategy(all_candidates),
        "live_candidate_count_by_strategy": candidate_count_by_strategy(live_candidates),
        "selected_strategy_slots": selected["strategy_slot"].astype(str).tolist() if not selected.empty else [],
        "trade_enabled": parse_bool_strategy_overrides(args),
        "safety": {
            "mt5_called": False, "order_send_called": False, "discord_called": False, "state_mutated": False,
            "early_low_break_trade_enabled": bool(args.enable_sell_early_low_break_trade),
            "payload_limited_to_max_payload_rows": True,
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "timing": {"total_seconds": round(time.perf_counter() - started_perf, 3)},
    }
    write_json(paths["summary_json"], summary)

    print(json.dumps({
        "cycle_ok": cycle_ok,
        "reason": reason,
        "latest_m15_time": summary["latest_m15_time"],
        "raw_candidate_rows": summary["rows"].get("raw_candidate_rows", 0),
        "all_candidate_rows_after_cooldown": summary["rows"].get("all_candidate_rows_after_cooldown", 0),
        "live_candidate_rows": summary["rows"]["live_candidate_rows"],
        "payload_rows_out": summary["rows"]["payload_rows_out"],
        "selected_strategy_slots": summary["selected_strategy_slots"],
        "summary_json": str(paths["summary_json"]),
        "order_payloads_csv": str(paths["order_payloads_csv"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
