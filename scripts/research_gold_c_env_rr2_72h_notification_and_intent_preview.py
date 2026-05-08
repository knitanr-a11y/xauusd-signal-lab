#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build notification and dry-run order-intent previews for GOLD C_ENV RR2 72h.

Research-only utility.

Input:
    data/research_results/gold_c_env_rr2_best_hold_horizon_compare/signal_review_72h.csv

Outputs:
    notification_preview_72h.txt
    notification_preview_72h.csv
    order_intent_preview_72h.jsonl
    order_intent_preview_72h.csv

Purpose:
    Freeze a common signal payload shape that can later be reused by:
      1. Discord notification preview
      2. live scanner dry-run
      3. autotrade order-intent dry-run

This script does NOT send Discord messages, place orders, write live ledgers,
write trigger state, or touch Mochipoyo live/demo/autotrade files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"
STRATEGY_ID = CONDITION_ID
SETUP_NAME = "GOLD C_ENV H1 regular bullish M15 BO8 RR2 hold72h"
DEFAULT_RESULT_DIR = Path("data/research_results/gold_c_env_rr2_best_hold_horizon_compare")
DEFAULT_INPUT = DEFAULT_RESULT_DIR / "signal_review_72h.csv"
DEFAULT_NOTIFICATION_TXT = DEFAULT_RESULT_DIR / "notification_preview_72h.txt"
DEFAULT_NOTIFICATION_CSV = DEFAULT_RESULT_DIR / "notification_preview_72h.csv"
DEFAULT_INTENT_JSONL = DEFAULT_RESULT_DIR / "order_intent_preview_72h.jsonl"
DEFAULT_INTENT_CSV = DEFAULT_RESULT_DIR / "order_intent_preview_72h.csv"

REQUIRED_COLUMNS = [
    "symbol",
    "direction",
    "entry_time",
    "entry_price",
    "sl_price",
    "tp_price",
    "risk_price",
    "rr",
    "max_hold_hours",
    "h4_env_close_time",
    "h4_env_close",
    "h4_env_ema20",
    "h4_env_ema50",
    "h1_pivot_confirm_time",
    "h1_pivot_low",
    "h1_prev_pivot_low",
    "h1_pivot_macd",
    "h1_prev_pivot_macd",
    "m15_close_time",
    "m15_close",
    "m15_ema20",
    "m15_macd",
    "m15_macd_signal",
    "m15_macd_hist",
    "m15_rolling_high_prev",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build notification and dry-run order intent previews.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--notification-txt", type=Path, default=DEFAULT_NOTIFICATION_TXT)
    parser.add_argument("--notification-csv", type=Path, default=DEFAULT_NOTIFICATION_CSV)
    parser.add_argument("--intent-jsonl", type=Path, default=DEFAULT_INTENT_JSONL)
    parser.add_argument("--intent-csv", type=Path, default=DEFAULT_INTENT_CSV)
    parser.add_argument("--risk-mode", type=str, default="dry_run_no_lot")
    parser.add_argument("--dry-run", action="store_true", default=True)
    return parser.parse_args()


def require_columns(df: pd.DataFrame, path: Path) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required columns in {path}: {missing}")


def as_float(row: pd.Series, col: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(col, default))
    except Exception:
        return default
    if pd.isna(value):
        return default
    return value


def as_str(row: pd.Series, col: str, default: str = "") -> str:
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return str(value)


def fmt_price(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def fmt_num(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def build_signal_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "schema_version": "gold_c_env_rr2_72h_signal_v1",
        "condition_id": CONDITION_ID,
        "strategy_id": STRATEGY_ID,
        "setup_name": SETUP_NAME,
        "symbol": as_str(row, "symbol", "GOLD"),
        "direction": as_str(row, "direction", "BUY"),
        "entry": {
            "entry_type": "MARKET_ON_SIGNAL",
            "signal_time": as_str(row, "entry_time"),
            "entry_time": as_str(row, "entry_time"),
            "entry_price_reference": as_float(row, "entry_price"),
        },
        "risk": {
            "sl_price": as_float(row, "sl_price"),
            "tp_price": as_float(row, "tp_price"),
            "risk_price": as_float(row, "risk_price"),
            "rr": as_float(row, "rr", 2.0),
            "max_hold_hours": int(as_float(row, "max_hold_hours", 72)),
            "exit_rule": "TP/SL first-touch; if unresolved, time exit around 72h",
        },
        "context": {
            "h4": {
                "env_close_time": as_str(row, "h4_env_close_time"),
                "close": as_float(row, "h4_env_close"),
                "ema20": as_float(row, "h4_env_ema20"),
                "ema50": as_float(row, "h4_env_ema50"),
                "env_rule": "ema20 > ema50 and close > ema50",
            },
            "h1": {
                "divergence_type": "regular_bullish",
                "pivot_confirm_time": as_str(row, "h1_pivot_confirm_time"),
                "pivot_low": as_float(row, "h1_pivot_low"),
                "prev_pivot_low": as_float(row, "h1_prev_pivot_low"),
                "pivot_macd": as_float(row, "h1_pivot_macd"),
                "prev_pivot_macd": as_float(row, "h1_prev_pivot_macd"),
                "exhaustion_rule": "close < ema50 or ema20 < ema50",
            },
            "m15": {
                "close_time": as_str(row, "m15_close_time"),
                "close": as_float(row, "m15_close"),
                "ema20": as_float(row, "m15_ema20"),
                "rolling_high_prev": as_float(row, "m15_rolling_high_prev"),
                "macd": as_float(row, "m15_macd"),
                "macd_signal": as_float(row, "m15_macd_signal"),
                "macd_hist": as_float(row, "m15_macd_hist"),
                "trigger_rule": "close > previous rolling high 8, close > ema20, macd > signal, hist increasing",
            },
        },
        "research_outcome": {
            "outcome": as_str(row, "outcome"),
            "realized_r": as_float(row, "realized_r"),
            "exit_time": as_str(row, "exit_time"),
            "exit_price": as_float(row, "exit_price"),
            "hold_hours": as_float(row, "hold_hours"),
        },
    }


def build_order_intent(row: pd.Series, *, risk_mode: str, dry_run: bool) -> dict[str, Any]:
    payload = build_signal_payload(row)
    return {
        "schema_version": "gold_c_env_rr2_72h_order_intent_v1",
        "dry_run": bool(dry_run),
        "intent_type": "OPEN_POSITION",
        "strategy_id": STRATEGY_ID,
        "condition_id": CONDITION_ID,
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "entry_type": "MARKET_ON_SIGNAL",
        "signal_time": payload["entry"]["signal_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "risk_price": payload["risk"]["risk_price"],
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "time_exit_required": True,
        "risk_mode": risk_mode,
        "lot": None,
        "volume": None,
        "lot_status": "NOT_CALCULATED_RESEARCH_PREVIEW",
        "source_signal": payload,
    }


def notification_text(payload: dict[str, Any]) -> str:
    entry = payload["entry"]
    risk = payload["risk"]
    h4 = payload["context"]["h4"]
    h1 = payload["context"]["h1"]
    m15 = payload["context"]["m15"]
    outcome = payload["research_outcome"]

    return "\n".join(
        [
            "━━━━━━━━━━━━━━━━━━━━",
            f"【{payload['symbol']} {payload['direction']}候補】",
            f"condition: {payload['condition_id']}",
            f"signal_time: {entry['signal_time']}",
            "",
            f"Entry ref: {fmt_price(entry['entry_price_reference'])}",
            f"SL: {fmt_price(risk['sl_price'])}",
            f"TP: {fmt_price(risk['tp_price'])}",
            f"RR: {fmt_num(risk['rr'], 2)}",
            f"Max hold: {risk['max_hold_hours']}h",
            "",
            f"H4 env: close={fmt_price(h4['close'])} ema20={fmt_price(h4['ema20'])} ema50={fmt_price(h4['ema50'])}",
            f"H4 close_time: {h4['env_close_time']}",
            f"H1 regular bullish: low {fmt_price(h1['prev_pivot_low'])} -> {fmt_price(h1['pivot_low'])}, MACD {fmt_num(h1['prev_pivot_macd'])} -> {fmt_num(h1['pivot_macd'])}",
            f"H1 confirm: {h1['pivot_confirm_time']}",
            f"M15 break: close={fmt_price(m15['close'])} prev_high8={fmt_price(m15['rolling_high_prev'])} ema20={fmt_price(m15['ema20'])}",
            f"M15 MACD: {fmt_num(m15['macd'])} / signal {fmt_num(m15['macd_signal'])} / hist {fmt_num(m15['macd_hist'])}",
            "",
            f"[research] outcome={outcome['outcome']} R={fmt_num(outcome['realized_r'])} exit={outcome['exit_time']} hold_h={fmt_num(outcome['hold_hours'], 2)}",
        ]
    )


def flatten_for_csv(payload: dict[str, Any], intent: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "condition_id": payload["condition_id"],
        "strategy_id": payload["strategy_id"],
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "signal_time": payload["entry"]["signal_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "risk_price": payload["risk"]["risk_price"],
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "time_exit_required": intent["time_exit_required"],
        "risk_mode": intent["risk_mode"],
        "dry_run": intent["dry_run"],
        "lot_status": intent["lot_status"],
        "h4_env_close_time": payload["context"]["h4"]["env_close_time"],
        "h1_pivot_confirm_time": payload["context"]["h1"]["pivot_confirm_time"],
        "m15_close_time": payload["context"]["m15"]["close_time"],
        "research_outcome": payload["research_outcome"]["outcome"],
        "research_realized_r": payload["research_outcome"]["realized_r"],
        "research_exit_time": payload["research_outcome"]["exit_time"],
        "research_hold_hours": payload["research_outcome"]["hold_hours"],
        "notification_text": text,
        "signal_payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "order_intent_json": json.dumps(intent, ensure_ascii=False, sort_keys=True),
    }


def main() -> int:
    args = parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {args.input_csv}")

    df = pd.read_csv(args.input_csv, encoding="utf-8-sig")
    require_columns(df, args.input_csv)

    notification_blocks: list[str] = []
    notification_rows: list[dict[str, Any]] = []
    intent_rows: list[dict[str, Any]] = []
    intent_flat_rows: list[dict[str, Any]] = []

    for _, row in df.sort_values("entry_time", kind="mergesort").iterrows():
        payload = build_signal_payload(row)
        intent = build_order_intent(row, risk_mode=args.risk_mode, dry_run=args.dry_run)
        text = notification_text(payload)
        notification_blocks.append(text)
        flat = flatten_for_csv(payload, intent, text)
        notification_rows.append(flat)
        intent_rows.append(intent)
        intent_flat_rows.append({k: v for k, v in flat.items() if k != "notification_text"})

    args.notification_txt.parent.mkdir(parents=True, exist_ok=True)
    args.notification_txt.write_text("\n\n".join(notification_blocks) + "\n", encoding="utf-8")
    pd.DataFrame(notification_rows).to_csv(args.notification_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(intent_flat_rows).to_csv(args.intent_csv, index=False, encoding="utf-8-sig")
    with args.intent_jsonl.open("w", encoding="utf-8") as f:
        for intent in intent_rows:
            f.write(json.dumps(intent, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"[INFO] input={args.input_csv}")
    print(f"[INFO] notification_txt={args.notification_txt}")
    print(f"[INFO] notification_csv={args.notification_csv}")
    print(f"[INFO] intent_jsonl={args.intent_jsonl}")
    print(f"[INFO] intent_csv={args.intent_csv}")
    print(f"[INFO] rows={len(notification_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
