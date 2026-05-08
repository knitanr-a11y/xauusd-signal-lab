#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build preview position_registry.csv rows from order payloads and synthetic send results.

This script is a dry-run / preview-only bridge for the future registry write flow.

Purpose:
- Read one or more order_payloads.csv rows.
- Combine them with a synthetic successful send result.
- Produce the exact registry row shape that the real sender should write *after* a confirmed successful order_send.
- Write only to a preview/test registry path.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.
- No production registry mutation unless the user explicitly points --output-csv there.

Typical use:
1. Build a controlled payload.
2. Run this script with synthetic ticket/order/deal ids.
3. Reconcile the output registry row against a matching mock position.
4. Run registry policy preview against it.

This script should remain separate from send_mt5_order_from_payload.py until the registry semantics are fully validated.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

DEFAULT_INPUT_CSV = Path("data/research_results/gold_multi_strategy_position_policy_preflight/order_payloads_policy_test_same_direction_buy.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_registry")
DEFAULT_ACCOUNT_LOGIN = 75539039
DEFAULT_ACCOUNT_SERVER = "XMTrading-MT5 3"
DEFAULT_POSITION_TICKET_START = 990001
DEFAULT_ORDER_TICKET_START = 880001
DEFAULT_DEAL_TICKET_START = 770001
DEFAULT_MAGIC = 26050601

REGISTRY_COLUMNS = [
    "created_at_utc",
    "updated_at_utc",
    "account_login",
    "account_server",
    "broker_symbol",
    "symbol",
    "position_ticket",
    "order_ticket",
    "deal_ticket",
    "magic_number",
    "direction",
    "lot",
    "entry_price",
    "sl_price",
    "tp_price",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "signal_key",
    "order_key",
    "payload_key",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "source_payload_csv",
    "sender_report_json",
    "position_status",
    "last_seen_utc",
    "close_status",
    "close_reason",
    "notes",
]

SCHEMA_VERSION = "gold_multi_strategy_position_registry_from_payload_preview_v1"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build preview position_registry rows from payload + synthetic send result. No MT5 calls.")
    p.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--max-rows", type=int, default=1)
    p.add_argument("--account-login", type=int, default=DEFAULT_ACCOUNT_LOGIN)
    p.add_argument("--account-server", default=DEFAULT_ACCOUNT_SERVER)
    p.add_argument("--position-ticket-start", type=int, default=DEFAULT_POSITION_TICKET_START)
    p.add_argument("--order-ticket-start", type=int, default=DEFAULT_ORDER_TICKET_START)
    p.add_argument("--deal-ticket-start", type=int, default=DEFAULT_DEAL_TICKET_START)
    p.add_argument("--magic", type=int, default=DEFAULT_MAGIC)
    p.add_argument("--position-status", default="ACTIVE")
    p.add_argument("--sender-report-json", default="SYNTHETIC_SEND_RESULT_PREVIEW")
    p.add_argument("--notes", default="registry row generated from payload preview; no real order_send")
    p.add_argument(
        "--append",
        action="store_true",
        help="Append to output CSV if it exists. Default overwrites preview output.",
    )
    return p.parse_args()


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value)
    return text if text else default


def clean_float(value: Any, default: float | None = None) -> float | None:
    try:
        v = float(value)
    except Exception:
        return default
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    return v


def clean_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def infer_symbol(payload_row: pd.Series) -> str:
    return clean_str(payload_row.get("symbol"), "GOLD") or "GOLD"


def infer_broker_symbol(payload_row: pd.Series) -> str:
    return clean_str(payload_row.get("broker_symbol"), clean_str(payload_row.get("symbol"), "GOLD#")) or "GOLD#"


def infer_strategy_key(payload_row: pd.Series) -> str:
    return (
        clean_str(payload_row.get("router_strategy_slot"))
        or clean_str(payload_row.get("pair_name"))
        or clean_str(payload_row.get("strategy_id"))
    )


def infer_strategy_id(payload_row: pd.Series) -> str:
    return clean_str(payload_row.get("strategy_id"), clean_str(payload_row.get("router_strategy_id")))


def infer_strategy_alias(strategy_key: str, strategy_id: str, direction: str) -> str:
    text = f"{strategy_key} {strategy_id}".upper()
    if "BUY_C" in text or "C_ENV" in text:
        return "BUY_C"
    if "SELL_H1H4_BEAR_AB" in text or "BEAR_AB" in text or "H1H4_BEAR" in text:
        return "SELL_AB"
    if "BTC" in text:
        return "BTC"
    return f"{direction.upper()}_UNK"


def infer_entry_price(payload_row: pd.Series) -> float:
    for col in ["entry_price", "entry_price_reference", "open_price", "price"]:
        v = clean_float(payload_row.get(col))
        if v is not None:
            return float(v)
    return 0.0


def infer_sl(payload_row: pd.Series) -> float:
    for col in ["sl_price", "sl", "stop_loss"]:
        v = clean_float(payload_row.get(col))
        if v is not None:
            return float(v)
    return 0.0


def infer_tp(payload_row: pd.Series) -> float:
    for col in ["tp_price", "tp", "take_profit"]:
        v = clean_float(payload_row.get(col))
        if v is not None:
            return float(v)
    return 0.0


def validate_payload_row(payload_row: pd.Series) -> list[str]:
    errors: list[str] = []
    direction = clean_str(payload_row.get("direction")).upper()
    lot = clean_float(payload_row.get("lot"))
    if direction not in {"BUY", "SELL"}:
        errors.append(f"direction must be BUY or SELL: {direction}")
    if lot is None or lot <= 0:
        errors.append(f"lot must be positive: {payload_row.get('lot')}")
    if not infer_strategy_key(payload_row):
        errors.append("strategy key missing: need router_strategy_slot, pair_name, or strategy_id")
    if not clean_str(payload_row.get("signal_key")):
        errors.append("signal_key missing")
    if not clean_str(payload_row.get("order_key"), clean_str(payload_row.get("payload_key"))):
        errors.append("order_key/payload_key missing")
    return errors


def build_registry_row(
    *,
    now: str,
    payload_row: pd.Series,
    input_csv: Path,
    account_login: int,
    account_server: str,
    magic: int,
    position_ticket: int,
    order_ticket: int,
    deal_ticket: int,
    position_status: str,
    sender_report_json: str,
    notes: str,
) -> dict[str, Any]:
    direction = clean_str(payload_row.get("direction")).upper()
    strategy_key = infer_strategy_key(payload_row)
    strategy_id = infer_strategy_id(payload_row)
    strategy_alias = infer_strategy_alias(strategy_key, strategy_id, direction)
    payload_key = clean_str(payload_row.get("payload_key"), clean_str(payload_row.get("order_key")))
    order_key = clean_str(payload_row.get("order_key"), payload_key)
    return {
        "created_at_utc": now,
        "updated_at_utc": now,
        "account_login": int(account_login),
        "account_server": account_server,
        "broker_symbol": infer_broker_symbol(payload_row),
        "symbol": infer_symbol(payload_row),
        "position_ticket": int(position_ticket),
        "order_ticket": int(order_ticket),
        "deal_ticket": int(deal_ticket),
        "magic_number": int(clean_int(payload_row.get("magic_number"), magic)),
        "direction": direction,
        "lot": float(clean_float(payload_row.get("lot"), 0.0) or 0.0),
        "entry_price": infer_entry_price(payload_row),
        "sl_price": infer_sl(payload_row),
        "tp_price": infer_tp(payload_row),
        "strategy_key": strategy_key,
        "strategy_alias": strategy_alias,
        "strategy_id": strategy_id,
        "condition_id": clean_str(payload_row.get("condition_id"), strategy_id),
        "signal_key": clean_str(payload_row.get("signal_key")),
        "order_key": order_key,
        "payload_key": payload_key,
        "router_strategy_slot": clean_str(payload_row.get("router_strategy_slot"), strategy_key),
        "router_strategy_id": clean_str(payload_row.get("router_strategy_id"), strategy_id),
        "candidate_rank": clean_str(payload_row.get("candidate_rank")),
        "source_payload_csv": str(input_csv),
        "sender_report_json": sender_report_json,
        "position_status": clean_str(position_status, "ACTIVE").upper(),
        "last_seen_utc": now,
        "close_status": "",
        "close_reason": "",
        "notes": notes,
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / "position_registry_from_payload_preview.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / "position_registry_from_payload_preview.json"
    now = utc_now_text()

    if not args.input_csv.exists():
        empty = pd.DataFrame(columns=REGISTRY_COLUMNS)
        write_csv(empty, output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "preview_ok": False,
            "reason": "INPUT_CSV_NOT_FOUND",
            "input_csv": str(args.input_csv),
            "output_csv": str(output_csv),
            "output_json": str(output_json),
            "rows_in": 0,
            "rows_out": 0,
            "safety": safety_summary(),
        }
        write_json(output_json, summary)
        print("build_gold_multi_strategy_position_registry_from_payload_preview")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    payload_df = read_csv(args.input_csv)
    if payload_df.empty:
        empty = pd.DataFrame(columns=REGISTRY_COLUMNS)
        write_csv(empty, output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "preview_ok": True,
            "reason": "NO_INPUT_ROWS",
            "input_csv": str(args.input_csv),
            "output_csv": str(output_csv),
            "output_json": str(output_json),
            "rows_in": 0,
            "rows_out": 0,
            "safety": safety_summary(),
        }
        write_json(output_json, summary)
        print("build_gold_multi_strategy_position_registry_from_payload_preview")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.max_rows > 0:
        payload_df = payload_df.head(args.max_rows).copy()

    rows: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []
    for i, (_, payload_row) in enumerate(payload_df.iterrows(), start=0):
        errors = validate_payload_row(payload_row)
        if errors:
            validation_errors.append({"row_index": i + 1, "errors": errors})
            continue
        rows.append(
            build_registry_row(
                now=now,
                payload_row=payload_row,
                input_csv=args.input_csv,
                account_login=args.account_login,
                account_server=args.account_server,
                magic=args.magic,
                position_ticket=int(args.position_ticket_start) + i,
                order_ticket=int(args.order_ticket_start) + i,
                deal_ticket=int(args.deal_ticket_start) + i,
                position_status=args.position_status,
                sender_report_json=args.sender_report_json,
                notes=args.notes,
            )
        )

    new_df = pd.DataFrame([{col: row.get(col, "") for col in REGISTRY_COLUMNS} for row in rows], columns=REGISTRY_COLUMNS)
    if args.append and output_csv.exists():
        old_df = read_csv(output_csv)
        for col in REGISTRY_COLUMNS:
            if col not in old_df.columns:
                old_df[col] = ""
        out_df = pd.concat([old_df[REGISTRY_COLUMNS], new_df], ignore_index=True)
    else:
        out_df = new_df
    write_csv(out_df, output_csv)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "preview_ok": len(validation_errors) == 0,
        "reason": "REGISTRY_PREVIEW_ROWS_BUILT" if len(validation_errors) == 0 else "PAYLOAD_VALIDATION_ERRORS",
        "input_csv": str(args.input_csv),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "rows_in": int(len(payload_df)),
        "rows_out_new": int(len(new_df)),
        "rows_out_total": int(len(out_df)),
        "validation_error_rows": int(len(validation_errors)),
        "validation_errors": validation_errors,
        "account_login": int(args.account_login),
        "account_server": args.account_server,
        "position_ticket_start": int(args.position_ticket_start),
        "order_ticket_start": int(args.order_ticket_start),
        "deal_ticket_start": int(args.deal_ticket_start),
        "position_status": clean_str(args.position_status, "ACTIVE").upper(),
        "append": bool(args.append),
        "safety": safety_summary(),
        "records": new_df.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("build_gold_multi_strategy_position_registry_from_payload_preview")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if new_df.empty:
        print("[INFO] no registry rows created")
    else:
        print(new_df[["position_ticket", "broker_symbol", "direction", "lot", "strategy_key", "strategy_alias", "position_status", "signal_key"]].to_string(index=False))
    print(f"output_csv: {output_csv}")
    print(f"output_json: {output_json}")
    print("done")
    return 0 if summary["preview_ok"] else 1


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called": False,
        "order_send_called": False,
        "existing_mochipoyo_ledger_mutated": False,
        "trigger_state_mutated": False,
        "production_registry_mutated_by_default": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
