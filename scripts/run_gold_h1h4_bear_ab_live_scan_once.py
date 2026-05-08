#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run live scan once for GOLD H1/H4 bearish M15 low-break A/B classifier.

This is intentionally separated from Mochipoyo live/demo/autotrade code and
from the existing GOLD C_ENV BUY candidate.

No Discord send.
No order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.

Strategy family:
    GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H

Final rank:
    CORE_AB_CONFIRM = A and B, trade_enabled=True, lot_multiplier=2.0
    B_ONLY_SAFE     = B and not A, trade_enabled=True, lot_multiplier=1.0
    A_ONLY_OBSERVE  = A and not B, trade_enabled=False, lot_multiplier=0.0

Important live detail:
    The latest confirmed M15 bar often has no next M15 open row yet.
    Therefore this script computes A/B conditions on the full historical M15
    context first, then uses the latest confirmed M15 close as the live entry
    reference when the next M15 open is unavailable.

Duplicate handling:
    If the same signal_key already exists in signal_ledger.csv, this script does
    not append the ledger row and writes order_intent_dry_run.json with
    intent_type=DUPLICATE_SKIP instead of OPEN_POSITION.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (  # noqa: E402
    CONDITION_FAMILY_ID,
    CONDITION_ID_A_ONLY,
    CONDITION_ID_B_ONLY,
    CONDITION_ID_CORE,
    DIRECTION,
    LEDGER_COLUMNS,
    SYMBOL,
    add_indicators,
    attach_context,
    build_data_coverage,
    build_notification_text,
    build_payload,
    build_signal_candidates,
    build_signal_key,
    load_frames,
    write_csv,
)

DEFAULT_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_scan")
LOG_COLUMNS = [
    "scan_time_utc",
    "condition_family_id",
    "condition_id",
    "csv_dir",
    "latest_m15_bar_time",
    "latest_m15_close_time",
    "signal_found",
    "rank",
    "a_pass",
    "b_pass",
    "trade_enabled",
    "duplicate",
    "signal_key",
    "reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run live scan once for GOLD bearish A/B classifier.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--sl-usd", type=float, default=10.0)
    parser.add_argument("--tp-usd", type=float, default=20.0)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--horizon-hours", type=float, default=12.0)
    parser.add_argument("--base-lot", type=float, default=0.10)
    parser.add_argument("--core-lot-multiplier", type=float, default=2.0)
    parser.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    parser.add_argument("--max-lot-per-trade", type=float, default=99.0)
    parser.add_argument(
        "--latest-confirmed-policy",
        choices=["last", "second_last"],
        default="last",
        help="Use last M15 row as latest confirmed by default. Use second_last if the live CSV includes a forming candle.",
    )
    parser.add_argument(
        "--observe-only-ledger",
        action="store_true",
        help="Also write A_ONLY_OBSERVE rows to ledger. By default only trade_enabled signals are ledgered.",
    )
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[LEDGER_COLUMNS].copy()


def latest_confirmed_m15_row(m15: pd.DataFrame, *, policy: str) -> pd.Series | None:
    if m15.empty:
        return None
    m15_sorted = m15.sort_values("time", kind="mergesort").reset_index(drop=True)
    if policy == "second_last" and len(m15_sorted) >= 2:
        return m15_sorted.iloc[-2]
    return m15_sorted.iloc[-1]


def compute_live_ab_flags(m15_ctx: pd.DataFrame) -> pd.DataFrame:
    out = m15_ctx.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["m15_prev_low16"] = out["low"].shift(1).rolling(16, min_periods=16).min()
    out["m15_prev_low6"] = out["low"].shift(1).rolling(6, min_periods=6).min()

    a_h1 = (
        (out["h1_close"] < out["h1_ema20"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_ema20_slope3"] < 0)
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    a_h4 = (out["h4_close"] < out["h4_ema20"]) & (out["h4_ema20"] < out["h4_ema50"])
    d1_bear = out["d1_close"] < out["d1_ema20"]
    a_m15 = (
        (out["low"] < out["m15_prev_low16"])
        & (out["close_pos"] <= 0.45)
        & (out["macd_hist_delta"] < 0)
        & (out["range_atr_ratio"] >= 0.90)
    )

    b_h1 = (
        (out["h1_close"] < out["h1_ema50"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    b_h4 = out["h4_ema20"] < out["h4_ema50"]
    b_m15 = (
        (out["low"] < out["m15_prev_low6"])
        & (out["close_pos"] <= 0.50)
        & (out["macd_hist"] < 0)
        & (out["macd_hist_delta"] < 0)
    )

    out["a_pass"] = (a_h1 & a_h4 & d1_bear & a_m15).fillna(False)
    out["b_pass"] = (b_h1 & b_h4 & d1_bear & b_m15).fillna(False)
    out["rank"] = np.select(
        [out["a_pass"] & out["b_pass"], out["b_pass"] & ~out["a_pass"], out["a_pass"] & ~out["b_pass"]],
        ["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE"],
        default="NO_SIGNAL",
    )
    out["trade_enabled"] = out["rank"].isin(["CORE_AB_CONFIRM", "B_ONLY_SAFE"])
    out["condition_id"] = np.select(
        [out["rank"].eq("CORE_AB_CONFIRM"), out["rank"].eq("B_ONLY_SAFE"), out["rank"].eq("A_ONLY_OBSERVE")],
        [CONDITION_ID_CORE, CONDITION_ID_B_ONLY, CONDITION_ID_A_ONLY],
        default="",
    )
    out["signal_group"] = out["rank"]
    out["symbol"] = SYMBOL
    out["direction"] = DIRECTION
    out["signal_time"] = out["time"]
    out["m15_close_time"] = out["close_time"]
    return out


def force_live_entry_fields(row: pd.Series, args: argparse.Namespace) -> pd.Series:
    out = row.copy()
    out["symbol"] = SYMBOL
    out["direction"] = DIRECTION
    out["signal_time"] = out.get("time", "")
    out["m15_close_time"] = out.get("close_time", "")
    out["entry_time"] = out.get("close_time", "")
    entry_price = out.get("entry_price", np.nan)
    if pd.isna(entry_price):
        entry_price = out.get("close", np.nan)
    if pd.isna(entry_price):
        raise RuntimeError("Cannot build live SELL entry reference because entry_price and close are NaN.")
    out["entry_price"] = float(entry_price)
    out["sl_price"] = float(entry_price) + float(args.sl_usd)
    out["tp_price"] = float(entry_price) - float(args.tp_usd)
    out["risk_price"] = float(args.sl_usd)
    out["reward_price"] = float(args.tp_usd)
    out["rr"] = float(args.rr)
    out["max_hold_hours"] = float(args.horizon_hours)
    out["base_lot"] = float(args.base_lot)
    if str(out.get("rank")) == "CORE_AB_CONFIRM":
        out["lot_multiplier"] = float(args.core_lot_multiplier)
    elif str(out.get("rank")) == "B_ONLY_SAFE":
        out["lot_multiplier"] = float(args.standard_lot_multiplier)
    else:
        out["lot_multiplier"] = 0.0
    out["effective_lot"] = min(float(out["base_lot"]) * float(out["lot_multiplier"]), float(args.max_lot_per_trade))
    if not bool(out.get("trade_enabled", False)):
        out["effective_lot"] = 0.0
    return out


def build_order_intent(
    row: pd.Series,
    *,
    dry_run: bool = True,
    duplicate: bool = False,
    signal_key: str = "",
    reason: str = "",
) -> dict[str, Any]:
    payload = build_payload(row)
    if duplicate:
        return {
            "schema_version": "gold_h1h4_bear_ab_classifier_order_intent_v1",
            "dry_run": bool(dry_run),
            "intent_type": "DUPLICATE_SKIP",
            "action": "NO_OPEN_POSITION_INTENT",
            "reason": reason or "DUPLICATE_SIGNAL_KEY",
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": payload["condition_id"],
            "strategy_id": payload["strategy_id"],
            "signal_key": signal_key,
            "symbol": payload["symbol"],
            "direction": payload["direction"],
            "rank": payload["rank"],
            "a_pass": payload["a_pass"],
            "b_pass": payload["b_pass"],
            "trade_enabled": False,
            "lot": {"base_lot": 0.0, "lot_multiplier": 0.0, "effective_lot": 0.0},
            "source_signal": payload,
        }
    return {
        "schema_version": "gold_h1h4_bear_ab_classifier_order_intent_v1",
        "dry_run": bool(dry_run),
        "intent_type": "OPEN_POSITION" if payload["trade_enabled"] else "OBSERVE_ONLY",
        "action": "DRY_RUN_ONLY_NO_MT5_ORDER" if payload["trade_enabled"] else "OBSERVE_ONLY_NO_ORDER",
        "reason": reason or ("NEW_DRY_RUN_SIGNAL_CREATED" if payload["trade_enabled"] else "OBSERVE_ONLY_SIGNAL"),
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": payload["condition_id"],
        "strategy_id": payload["strategy_id"],
        "signal_key": signal_key,
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "rank": payload["rank"],
        "a_pass": payload["a_pass"],
        "b_pass": payload["b_pass"],
        "trade_enabled": payload["trade_enabled"],
        "lot": payload["lot"],
        "entry_type": "MARKET_ON_SIGNAL",
        "signal_time": payload["entry"]["signal_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "risk_price": payload["risk"]["risk_price"],
        "reward_price": payload["risk"]["reward_price"],
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "time_exit_required": True,
        "source_signal": payload,
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scan_time = utc_now_text()

    result_path = args.out_dir / "latest_scan_result.json"
    ledger_path = args.out_dir / "signal_ledger.csv"
    log_path = args.out_dir / "live_scan_log.csv"

    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_frames(args.csv_dir)
    write_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")

    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")

    latest_row = latest_confirmed_m15_row(m15, policy=args.latest_confirmed_policy)
    if latest_row is None:
        result = {"scan_time_utc": scan_time, "condition_family_id": CONDITION_FAMILY_ID, "signal_found": False, "duplicate": False, "reason": "NO_M15_ROWS"}
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        append_csv_row(log_path, {**result, "csv_dir": str(args.csv_dir)}, LOG_COLUMNS)
        return 0

    latest_bar_time = pd.Timestamp(latest_row["time"])
    latest_close_time = pd.Timestamp(latest_row["close_time"])
    print(f"[INFO] latest_m15_bar_time={latest_bar_time}")
    print(f"[INFO] latest_m15_close_time={latest_close_time}")

    m15_ctx = attach_context(m15, h1, h4, d1)
    raw_backtest_style = build_signal_candidates(m15_ctx, args)
    write_csv(raw_backtest_style, args.out_dir / "latest_raw_candidates.csv")

    live_flags = compute_live_ab_flags(m15_ctx)
    write_csv(live_flags[live_flags["rank"] != "NO_SIGNAL"].copy(), args.out_dir / "latest_live_flag_candidates.csv")
    latest_candidates = live_flags[pd.to_datetime(live_flags["close_time"], errors="coerce") == latest_close_time].copy()
    latest_candidates = latest_candidates[latest_candidates["rank"] != "NO_SIGNAL"].copy()

    if latest_candidates.empty:
        result = {
            "scan_time_utc": scan_time,
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": "",
            "csv_dir": str(args.csv_dir),
            "latest_m15_bar_time": str(latest_bar_time),
            "latest_m15_close_time": str(latest_close_time),
            "signal_found": False,
            "rank": "",
            "a_pass": False,
            "b_pass": False,
            "trade_enabled": False,
            "duplicate": False,
            "signal_key": "",
            "reason": "NO_SIGNAL_ON_LATEST_CONFIRMED_M15",
        }
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        append_csv_row(log_path, result, LOG_COLUMNS)
        print("[INFO] no signal on latest confirmed M15")
        return 0

    priority = {"CORE_AB_CONFIRM": 100, "B_ONLY_SAFE": 50, "A_ONLY_OBSERVE": 10}
    latest_candidates["priority"] = latest_candidates["rank"].map(priority).fillna(0)
    signal_row = latest_candidates.sort_values(["priority", "close_time"], ascending=[False, True], kind="mergesort").iloc[0]
    signal_row = force_live_entry_fields(signal_row, args)

    signal_key = build_signal_key(signal_row)
    payload = build_payload(signal_row)
    text = build_notification_text(payload)
    duplicate = False

    should_ledger = bool(signal_row.get("trade_enabled", False)) or bool(args.observe_only_ledger)
    if should_ledger:
        ledger = read_ledger(ledger_path)
        duplicate = signal_key in set(ledger["signal_key"].astype(str)) if not ledger.empty else False
    reason = "DUPLICATE_SIGNAL_KEY" if duplicate else ("NEW_DRY_RUN_SIGNAL_CREATED" if should_ledger else "OBSERVE_ONLY_SIGNAL_NOT_LEDGERED")
    intent = build_order_intent(signal_row, dry_run=True, duplicate=duplicate, signal_key=signal_key, reason=reason)

    result = {
        "scan_time_utc": scan_time,
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": str(signal_row.get("condition_id", "")),
        "csv_dir": str(args.csv_dir),
        "latest_m15_bar_time": str(latest_bar_time),
        "latest_m15_close_time": str(latest_close_time),
        "signal_found": True,
        "rank": str(signal_row.get("rank", "")),
        "a_pass": bool(signal_row.get("a_pass", False)),
        "b_pass": bool(signal_row.get("b_pass", False)),
        "trade_enabled": bool(signal_row.get("trade_enabled", False)),
        "duplicate": bool(duplicate),
        "signal_key": signal_key,
        "reason": reason,
        "lot_multiplier": float(signal_row.get("lot_multiplier", 0.0)),
        "effective_lot": float(signal_row.get("effective_lot", 0.0)),
    }

    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (args.out_dir / "latest_signal_payload.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (args.out_dir / "order_intent_dry_run.json").write_text(json.dumps(intent, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (args.out_dir / "notification_preview_latest.txt").write_text(text + "\n", encoding="utf-8")
    append_csv_row(log_path, result, LOG_COLUMNS)

    if should_ledger and not duplicate:
        ledger_row = {
            "created_at_utc": scan_time,
            "signal_key": signal_key,
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": str(signal_row.get("condition_id", "")),
            "symbol": SYMBOL,
            "direction": DIRECTION,
            "rank": str(signal_row.get("rank", "")),
            "signal_group": str(signal_row.get("signal_group", "")),
            "signal_time": str(signal_row.get("signal_time", "")),
            "entry_time": str(signal_row.get("entry_time", "")),
            "entry_price_reference": float(signal_row.get("entry_price", 0.0)),
            "sl_price": float(signal_row.get("sl_price", 0.0)),
            "tp_price": float(signal_row.get("tp_price", 0.0)),
            "risk_price": float(signal_row.get("risk_price", 0.0)),
            "reward_price": float(signal_row.get("reward_price", 0.0)),
            "rr": float(signal_row.get("rr", 2.0)),
            "max_hold_hours": float(signal_row.get("max_hold_hours", 12.0)),
            "a_pass": bool(signal_row.get("a_pass", False)),
            "b_pass": bool(signal_row.get("b_pass", False)),
            "trade_enabled": bool(signal_row.get("trade_enabled", False)),
            "base_lot": float(signal_row.get("base_lot", 0.0)),
            "lot_multiplier": float(signal_row.get("lot_multiplier", 0.0)),
            "effective_lot": float(signal_row.get("effective_lot", 0.0)),
            "status": "DRY_RUN_SIGNAL_CREATED" if bool(signal_row.get("trade_enabled", False)) else "OBSERVE_ONLY_SIGNAL",
        }
        append_csv_row(ledger_path, ledger_row, LEDGER_COLUMNS)
        print("[INFO] ledger appended: new signal_key")
    elif duplicate:
        print("[INFO] duplicate signal_key detected; ledger append skipped; order intent is DUPLICATE_SKIP")

    print(f"[INFO] signal_found rank={result['rank']} duplicate={duplicate} trade_enabled={result['trade_enabled']}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
