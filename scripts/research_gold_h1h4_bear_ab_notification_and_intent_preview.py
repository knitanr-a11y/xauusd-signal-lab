#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build notification and dry-run order-intent previews for GOLD bearish A/B classifier.

Input is normally:
    data/research_results/gold_h1h4_bear_m15_low_break_ab_classifier/trades_classified_cooldown.csv

This script is research/dry-run only.
It does not send Discord messages, place orders, write Mochipoyo ledgers,
or write existing autotrade order-intent files.
"""

from __future__ import annotations

import argparse
import json
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
    build_notification_text,
    build_payload,
    safe_float,
)

DEFAULT_RESULT_DIR = Path("data/research_results/gold_h1h4_bear_m15_low_break_ab_classifier")
DEFAULT_INPUT = DEFAULT_RESULT_DIR / "trades_classified_cooldown.csv"
DEFAULT_SIGNAL_REVIEW = DEFAULT_RESULT_DIR / "signal_review_trade_enabled.csv"
DEFAULT_NOTIFICATION_TXT = DEFAULT_RESULT_DIR / "notification_preview.txt"
DEFAULT_NOTIFICATION_CSV = DEFAULT_RESULT_DIR / "notification_preview.csv"
DEFAULT_INTENT_JSONL = DEFAULT_RESULT_DIR / "order_intent_preview.jsonl"
DEFAULT_INTENT_CSV = DEFAULT_RESULT_DIR / "order_intent_preview.csv"

MINIMUM_COLUMNS = [
    "condition_id",
    "symbol",
    "direction",
    "rank",
    "trade_enabled",
    "a_pass",
    "b_pass",
    "entry_time",
    "entry_price",
    "sl_price",
    "tp_price",
    "risk_price",
    "reward_price",
    "rr",
    "max_hold_hours",
    "lot_multiplier",
    "effective_lot",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GOLD bearish A/B notification and order-intent previews.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--signal-review-csv", type=Path, default=DEFAULT_SIGNAL_REVIEW)
    parser.add_argument("--notification-txt", type=Path, default=DEFAULT_NOTIFICATION_TXT)
    parser.add_argument("--notification-csv", type=Path, default=DEFAULT_NOTIFICATION_CSV)
    parser.add_argument("--intent-jsonl", type=Path, default=DEFAULT_INTENT_JSONL)
    parser.add_argument("--intent-csv", type=Path, default=DEFAULT_INTENT_CSV)
    parser.add_argument("--include-observe-only", action="store_true", help="Also include A_ONLY_OBSERVE rows.")
    parser.add_argument("--risk-mode", type=str, default="dry_run_fixed_lot_preview")
    return parser.parse_args()


def require_columns(df: pd.DataFrame, path: Path) -> None:
    missing = [c for c in MINIMUM_COLUMNS if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required columns in {path}: {missing}")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def as_str(row: pd.Series, col: str, default: str = "") -> str:
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return str(value)


def build_order_intent(row: pd.Series, *, risk_mode: str, dry_run: bool = True) -> dict[str, Any]:
    payload = build_payload(row)
    return {
        "schema_version": "gold_h1h4_bear_ab_classifier_order_intent_v1",
        "dry_run": bool(dry_run),
        "intent_type": "OPEN_POSITION" if payload["trade_enabled"] else "OBSERVE_ONLY",
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": payload["condition_id"],
        "strategy_id": payload["strategy_id"],
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "rank": payload["rank"],
        "a_pass": payload["a_pass"],
        "b_pass": payload["b_pass"],
        "trade_enabled": payload["trade_enabled"],
        "entry_type": "MARKET_ON_SIGNAL",
        "signal_time": payload["entry"]["signal_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "risk_price": payload["risk"]["risk_price"],
        "reward_price": payload["risk"].get("reward_price", math.nan),
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "time_exit_required": True,
        "risk_mode": risk_mode,
        "lot": payload["lot"].get("effective_lot"),
        "volume": payload["lot"].get("effective_lot"),
        "lot_status": "DRY_RUN_LOT_FROM_CLASSIFIER_MULTIPLIER",
        "source_signal": payload,
    }


def flatten(row: pd.Series, payload: dict[str, Any], intent: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": payload["condition_id"],
        "strategy_id": payload["strategy_id"],
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "rank": payload["rank"],
        "a_pass": payload["a_pass"],
        "b_pass": payload["b_pass"],
        "trade_enabled": payload["trade_enabled"],
        "signal_time": payload["entry"]["signal_time"],
        "entry_time": payload["entry"]["entry_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "risk_price": payload["risk"]["risk_price"],
        "reward_price": payload["risk"].get("reward_price"),
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "base_lot": payload["lot"].get("base_lot"),
        "lot_multiplier": payload["lot"].get("lot_multiplier"),
        "effective_lot": payload["lot"].get("effective_lot"),
        "outcome": as_str(row, "outcome"),
        "realized_r": safe_float(row.get("realized_r", 0.0), 0.0),
        "lot_weighted_r": safe_float(row.get("lot_weighted_r", 0.0), 0.0),
        "exit_time": as_str(row, "exit_time"),
        "exit_price": safe_float(row.get("exit_price", 0.0), 0.0),
        "hold_hours": safe_float(row.get("hold_hours", 0.0), 0.0),
        "risk_mode": intent["risk_mode"],
        "dry_run": intent["dry_run"],
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

    if args.include_observe_only:
        use = df[df["rank"].isin(["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE"])].copy()
    else:
        use = df[df["trade_enabled"].map(bool_value)].copy()

    use = use.sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    args.signal_review_csv.parent.mkdir(parents=True, exist_ok=True)
    use.to_csv(args.signal_review_csv, index=False, encoding="utf-8-sig")

    notification_blocks: list[str] = []
    notification_rows: list[dict[str, Any]] = []
    intent_flat_rows: list[dict[str, Any]] = []

    args.intent_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.intent_jsonl.open("w", encoding="utf-8") as f:
        for _, row in use.iterrows():
            payload = build_payload(row)
            intent = build_order_intent(row, risk_mode=args.risk_mode, dry_run=True)
            text = build_notification_text(payload)
            notification_blocks.append(text)
            flat = flatten(row, payload, intent, text)
            notification_rows.append(flat)
            intent_flat_rows.append({k: v for k, v in flat.items() if k != "notification_text"})
            f.write(json.dumps(intent, ensure_ascii=False, sort_keys=True) + "\n")

    args.notification_txt.parent.mkdir(parents=True, exist_ok=True)
    args.notification_txt.write_text("\n\n".join(notification_blocks) + ("\n" if notification_blocks else ""), encoding="utf-8")
    pd.DataFrame(notification_rows).to_csv(args.notification_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(intent_flat_rows).to_csv(args.intent_csv, index=False, encoding="utf-8-sig")

    print(f"[INFO] input={args.input_csv}")
    print(f"[INFO] rows={len(use)}")
    print(f"[INFO] signal_review_csv={args.signal_review_csv}")
    print(f"[INFO] notification_txt={args.notification_txt}")
    print(f"[INFO] notification_csv={args.notification_csv}")
    print(f"[INFO] intent_jsonl={args.intent_jsonl}")
    print(f"[INFO] intent_csv={args.intent_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
