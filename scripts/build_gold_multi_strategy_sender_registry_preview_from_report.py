#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build position-registry preview rows from send_mt5_order_from_payload outputs.

This is a sender-adjacent dry-run-only registry preview hook.

It intentionally does NOT modify `send_mt5_order_from_payload.py` yet.
Instead it consumes the existing sender outputs:

- mt5_order_send_report.json
- mt5_order_send_results.csv
- original order_payloads.csv

and emits the registry rows that would be written after successful sends.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No production position_registry.csv mutation by default.
- No order ledger mutation.
- No trigger-state mutation.

First intended mode:
- Sender was run without --send.
- Eligible sender rows are `DRY_RUN_ORDER_CHECK_OK`.
- Synthetic ticket/order/deal values are used.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

SCHEMA_VERSION = "gold_multi_strategy_sender_registry_preview_from_report_v1"

DEFAULT_SENDER_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_send/mt5_order_send")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_sender_registry_preview")
DEFAULT_POSITION_TICKET_START = 990001
DEFAULT_ORDER_TICKET_START = 880001
DEFAULT_DEAL_TICKET_START = 770001
DEFAULT_POSITION_STATUS = "ACTIVE"

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

ELIGIBLE_DRY_RUN_STATUSES = {"DRY_RUN_ORDER_CHECK_OK"}
ELIGIBLE_SENT_STATUSES = {"SENT"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build registry preview rows from sender report/results. No MT5 calls.")
    p.add_argument("--sender-out-dir", type=Path, default=DEFAULT_SENDER_OUT_DIR)
    p.add_argument("--sender-report-json", type=Path, default=None)
    p.add_argument("--sender-results-csv", type=Path, default=None)
    p.add_argument("--payload-csv", type=Path, default=None, help="Original order_payloads.csv. Defaults to sender report input_csv.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--position-status", default=DEFAULT_POSITION_STATUS)
    p.add_argument("--position-ticket-start", type=int, default=DEFAULT_POSITION_TICKET_START)
    p.add_argument("--order-ticket-start", type=int, default=DEFAULT_ORDER_TICKET_START)
    p.add_argument("--deal-ticket-start", type=int, default=DEFAULT_DEAL_TICKET_START)
    p.add_argument("--include-sent-rows", action="store_true", help="Also include SENT/order_send_ok rows when present. Still preview-only.")
    p.add_argument("--max-rows", type=int, default=0, help="Limit preview rows after eligibility filtering. 0 means no limit.")
    p.add_argument("--notes", default="sender-adjacent registry preview from mt5_order_send_report; no production registry mutation")
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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path_exists(path):
        return {}
    try:
        return json.loads(Path(windows_long_path(path)).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_read_error": repr(e), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


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
    if pd.isna(v) or not math.isfinite(v):
        return default
    return v


def clean_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return int(default)
        if pd.isna(value):
            return int(default)
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def clean_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = clean_str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def normalize_symbol_from_broker(broker_symbol: str) -> str:
    text = broker_symbol.strip()
    if not text:
        return ""
    for suffix in ["#", ".", "_"]:
        if suffix in text:
            text = text.split(suffix)[0]
    return text.upper()


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


def resolve_payload_csv(args: argparse.Namespace, report: dict[str, Any]) -> Path:
    if args.payload_csv is not None:
        return args.payload_csv
    input_csv = clean_str(report.get("input_csv"))
    if input_csv:
        return Path(input_csv)
    return Path("")


def resolve_sender_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    report_json = args.sender_report_json if args.sender_report_json is not None else args.sender_out_dir / "mt5_order_send_report.json"
    results_csv = args.sender_results_csv if args.sender_results_csv is not None else args.sender_out_dir / "mt5_order_send_results.csv"
    return report_json, results_csv


def payload_lookup(payload_df: pd.DataFrame) -> dict[tuple[str, str, int], pd.Series]:
    out: dict[tuple[str, str, int], pd.Series] = {}
    if payload_df.empty:
        return out
    for idx, row in payload_df.iterrows():
        row_index = int(idx) + 1
        order_key = clean_str(row.get("order_key"), clean_str(row.get("payload_key")))
        payload_key = clean_str(row.get("payload_key"), order_key)
        if order_key:
            out[("order_key", order_key, 0)] = row
        if payload_key:
            out[("payload_key", payload_key, 0)] = row
        out[("row_index", "", row_index)] = row
    return out


def find_payload_row(sender_row: pd.Series, lookup: dict[tuple[str, str, int], pd.Series]) -> pd.Series | None:
    order_key = clean_str(sender_row.get("order_key"))
    payload_key = clean_str(sender_row.get("payload_key"))
    row_index = clean_int(sender_row.get("row_index"), 0)
    if order_key and ("order_key", order_key, 0) in lookup:
        return lookup[("order_key", order_key, 0)]
    if payload_key and ("payload_key", payload_key, 0) in lookup:
        return lookup[("payload_key", payload_key, 0)]
    if row_index and ("row_index", "", row_index) in lookup:
        return lookup[("row_index", "", row_index)]
    return None


def eligible_sender_rows(sender_df: pd.DataFrame, include_sent_rows: bool) -> pd.DataFrame:
    if sender_df.empty or "order_status" not in sender_df.columns:
        return pd.DataFrame(columns=sender_df.columns)
    statuses = set(ELIGIBLE_DRY_RUN_STATUSES)
    if include_sent_rows:
        statuses.update(ELIGIBLE_SENT_STATUSES)
    mask = sender_df["order_status"].astype(str).isin(statuses)
    if include_sent_rows and "order_send_ok" in sender_df.columns:
        sent_mask = sender_df["order_status"].astype(str).eq("SENT") & sender_df["order_send_ok"].map(clean_bool)
        mask = sender_df["order_status"].astype(str).isin(ELIGIBLE_DRY_RUN_STATUSES) | sent_mask
    return sender_df[mask].copy()


def account_login(report: dict[str, Any]) -> int:
    account = report.get("account_info", {})
    if isinstance(account, dict):
        return clean_int(account.get("login"), 0)
    return 0


def account_server(report: dict[str, Any]) -> str:
    account = report.get("account_info", {})
    if isinstance(account, dict):
        return clean_str(account.get("server"))
    return ""


def ticket_from_sender_or_synthetic(sender_row: pd.Series, *, synthetic_start: int, row_offset: int, keys: list[str]) -> int:
    for key in keys:
        v = sender_row.get(key)
        if clean_int(v, 0) != 0:
            return clean_int(v, synthetic_start + row_offset)
    return int(synthetic_start) + int(row_offset)


def build_registry_row(
    *,
    now: str,
    sender_row: pd.Series,
    payload_row: pd.Series | None,
    row_offset: int,
    args: argparse.Namespace,
    report: dict[str, Any],
    payload_csv: Path,
    sender_report_json: Path,
) -> dict[str, Any]:
    pr = payload_row if payload_row is not None else sender_row
    direction = clean_str(sender_row.get("direction"), clean_str(pr.get("direction"))).upper()
    broker_symbol = clean_str(sender_row.get("broker_symbol"), clean_str(pr.get("broker_symbol"), clean_str(pr.get("symbol"))))
    symbol = clean_str(pr.get("symbol"), normalize_symbol_from_broker(broker_symbol))
    strategy_key = infer_strategy_key(pr)
    strategy_id = infer_strategy_id(pr)
    strategy_alias = infer_strategy_alias(strategy_key, strategy_id, direction)
    payload_key = clean_str(pr.get("payload_key"), clean_str(sender_row.get("payload_key"), clean_str(pr.get("order_key"), clean_str(sender_row.get("order_key")))))
    order_key = clean_str(pr.get("order_key"), clean_str(sender_row.get("order_key"), payload_key))
    signal_key = clean_str(pr.get("signal_key"), clean_str(sender_row.get("signal_key")))
    lot = clean_float(sender_row.get("lot"), clean_float(pr.get("lot"), 0.0)) or 0.0
    entry_price = clean_float(sender_row.get("current_execution_price"), clean_float(pr.get("entry_price"), clean_float(pr.get("entry_price_reference"), 0.0))) or 0.0
    sl_price = clean_float(sender_row.get("sl_price"), clean_float(pr.get("sl_price"), 0.0)) or 0.0
    tp_price = clean_float(sender_row.get("tp_price"), clean_float(pr.get("tp_price"), 0.0)) or 0.0
    magic_number = clean_int(pr.get("magic_number"), clean_int(sender_row.get("magic"), 26050601))

    order_status = clean_str(sender_row.get("order_status"))
    if order_status == "SENT" and clean_bool(sender_row.get("order_send_ok")):
        order_ticket = ticket_from_sender_or_synthetic(sender_row, synthetic_start=args.order_ticket_start, row_offset=row_offset, keys=["order_ticket", "order", "order_id"])
        deal_ticket = ticket_from_sender_or_synthetic(sender_row, synthetic_start=args.deal_ticket_start, row_offset=row_offset, keys=["deal_ticket", "deal", "deal_id"])
        position_ticket = ticket_from_sender_or_synthetic(sender_row, synthetic_start=args.position_ticket_start, row_offset=row_offset, keys=["position_ticket", "position", "ticket"])
        ticket_note = "SENT row; used sender tickets where available, synthetic fallback for missing ticket fields"
    else:
        position_ticket = int(args.position_ticket_start) + int(row_offset)
        order_ticket = int(args.order_ticket_start) + int(row_offset)
        deal_ticket = int(args.deal_ticket_start) + int(row_offset)
        ticket_note = "DRY_RUN_ORDER_CHECK_OK row; synthetic preview tickets"

    notes = f"{args.notes}; sender_order_status={order_status}; {ticket_note}"
    return {
        "created_at_utc": now,
        "updated_at_utc": now,
        "account_login": account_login(report),
        "account_server": account_server(report),
        "broker_symbol": broker_symbol,
        "symbol": symbol,
        "position_ticket": position_ticket,
        "order_ticket": order_ticket,
        "deal_ticket": deal_ticket,
        "magic_number": magic_number,
        "direction": direction,
        "lot": float(lot),
        "entry_price": float(entry_price),
        "sl_price": float(sl_price),
        "tp_price": float(tp_price),
        "strategy_key": strategy_key,
        "strategy_alias": strategy_alias,
        "strategy_id": strategy_id,
        "condition_id": clean_str(pr.get("condition_id"), strategy_id),
        "signal_key": signal_key,
        "order_key": order_key,
        "payload_key": payload_key,
        "router_strategy_slot": clean_str(pr.get("router_strategy_slot"), strategy_key),
        "router_strategy_id": clean_str(pr.get("router_strategy_id"), strategy_id),
        "candidate_rank": clean_str(pr.get("candidate_rank")),
        "source_payload_csv": str(payload_csv),
        "sender_report_json": str(sender_report_json),
        "position_status": clean_str(args.position_status, DEFAULT_POSITION_STATUS).upper(),
        "last_seen_utc": now,
        "close_status": "",
        "close_reason": "",
        "notes": notes,
    }


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called_count": 0,
        "order_send_called_count": 0,
        "production_registry_mutated": False,
        "order_ledger_mutated": False,
        "trigger_state_mutated": False,
    }


def main() -> int:
    args = parse_args()
    Path(windows_long_path(args.out_dir)).mkdir(parents=True, exist_ok=True)
    sender_report_json, sender_results_csv = resolve_sender_paths(args)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / "sender_registry_preview.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / "sender_registry_preview.json"
    now = utc_now_text()

    report = read_json(sender_report_json)
    payload_csv = resolve_payload_csv(args, report)

    sender_report_exists = path_exists(sender_report_json)
    sender_results_exists = path_exists(sender_results_csv)
    payload_exists = bool(str(payload_csv)) and path_exists(payload_csv)

    if not sender_report_exists or not sender_results_exists or not payload_exists:
        empty = pd.DataFrame(columns=REGISTRY_COLUMNS)
        write_csv(empty, output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "preview_ok": False,
            "reason": "MISSING_INPUT",
            "sender_report_json": str(sender_report_json),
            "sender_report_exists": sender_report_exists,
            "sender_results_csv": str(sender_results_csv),
            "sender_results_exists": sender_results_exists,
            "payload_csv": str(payload_csv),
            "payload_exists": payload_exists,
            "output_csv": str(output_csv),
            "output_json": str(output_json),
            "registry_preview_rows": 0,
            "safety": safety_summary(),
        }
        write_json(output_json, summary)
        print("build_gold_multi_strategy_sender_registry_preview_from_report")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 2

    sender_df = read_csv(sender_results_csv)
    payload_df = read_csv(payload_csv)
    eligible_df = eligible_sender_rows(sender_df, bool(args.include_sent_rows))
    if args.max_rows and args.max_rows > 0:
        eligible_df = eligible_df.head(int(args.max_rows)).copy()

    lookup = payload_lookup(payload_df)
    rows: list[dict[str, Any]] = []
    unmatched_sender_rows: list[dict[str, Any]] = []
    for offset, (_, sender_row) in enumerate(eligible_df.iterrows()):
        payload_row = find_payload_row(sender_row, lookup)
        if payload_row is None:
            unmatched_sender_rows.append({
                "row_index": clean_int(sender_row.get("row_index"), 0),
                "order_key": clean_str(sender_row.get("order_key")),
                "payload_key": clean_str(sender_row.get("payload_key")),
                "order_status": clean_str(sender_row.get("order_status")),
            })
        rows.append(
            build_registry_row(
                now=now,
                sender_row=sender_row,
                payload_row=payload_row,
                row_offset=offset,
                args=args,
                report=report,
                payload_csv=payload_csv,
                sender_report_json=sender_report_json,
            )
        )

    out_df = pd.DataFrame([{col: row.get(col, "") for col in REGISTRY_COLUMNS} for row in rows], columns=REGISTRY_COLUMNS)
    write_csv(out_df, output_csv)

    sender_status_counts = sender_df["order_status"].value_counts().to_dict() if "order_status" in sender_df.columns and not sender_df.empty else {}
    eligible_status_counts = eligible_df["order_status"].value_counts().to_dict() if "order_status" in eligible_df.columns and not eligible_df.empty else {}
    reason = "REGISTRY_PREVIEW_ROWS_BUILT" if rows else "NO_ELIGIBLE_SENDER_ROWS"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "preview_ok": True,
        "reason": reason,
        "sender_report_json": str(sender_report_json),
        "sender_results_csv": str(sender_results_csv),
        "payload_csv": str(payload_csv),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "sender_rows_in": int(len(sender_df)),
        "payload_rows_in": int(len(payload_df)),
        "eligible_sender_rows": int(len(eligible_df)),
        "registry_preview_rows": int(len(out_df)),
        "sender_status_counts": sender_status_counts,
        "eligible_status_counts": eligible_status_counts,
        "include_sent_rows": bool(args.include_sent_rows),
        "position_status": clean_str(args.position_status, DEFAULT_POSITION_STATUS).upper(),
        "position_ticket_start": int(args.position_ticket_start),
        "order_ticket_start": int(args.order_ticket_start),
        "deal_ticket_start": int(args.deal_ticket_start),
        "send_requested_in_report": bool(report.get("send_requested", False)),
        "sender_order_send_called_count": clean_int(report.get("order_send_called_count"), 0),
        "unmatched_sender_rows": unmatched_sender_rows,
        "safety": safety_summary(),
        "records": out_df.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("build_gold_multi_strategy_sender_registry_preview_from_report")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if out_df.empty:
        print("[INFO] no eligible sender rows for registry preview")
    else:
        show_cols = [
            "position_ticket",
            "order_ticket",
            "deal_ticket",
            "broker_symbol",
            "direction",
            "lot",
            "entry_price",
            "sl_price",
            "tp_price",
            "strategy_key",
            "strategy_alias",
            "position_status",
            "signal_key",
        ]
        print(out_df[show_cols].to_string(index=False))
    print(f"output_csv: {output_csv}")
    print(f"output_json: {output_json}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
