#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registry-aware policy preview for GOLD multi-strategy order payloads.

This script is a non-executing bridge between:
- order_payloads.csv candidates
- current positions snapshot/mock CSV
- position_registry.csv ownership metadata

It produces sender-like ALLOW/BLOCK decisions without modifying the real sender.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No registry mutation.
- No Mochipoyo ledger mutation.
- No trigger-state mutation.

Policy candidate:
    block_same_strategy_and_opposite_direction

Rules:
1. Invalid payload => BLOCK
2. same signal_key / order_key duplicate => BLOCK
3. registry inconsistency => BLOCK by default
4. same strategy already has an ACTIVE matched registry position => BLOCK
5. same symbol opposite direction exists in current positions => BLOCK
6. total open positions >= max_total_positions => BLOCK
7. requested lot > max_lot_per_order => BLOCK
8. otherwise => ALLOW

This is still a preview layer. Do not use it as an order sender.
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

SCHEMA_VERSION = "gold_multi_strategy_registry_policy_preview_v1"
POLICY_NAME = "block_same_strategy_and_opposite_direction"

DEFAULT_INPUT_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/order_payloads.csv")
DEFAULT_REGISTRY_CSV = Path("data/research_results/gold_multi_strategy_position_registry/position_registry.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_registry")
DEFAULT_ORDER_LEDGER_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/dry_run_order_ledger.csv")

OUTPUT_CSV_NAME = "registry_policy_preview.csv"
OUTPUT_JSON_NAME = "registry_policy_preview.json"
RECONCILE_CSV_NAME = "registry_policy_preview_reconcile.csv"

ACTIVE_STATUSES = {"ACTIVE", "OPEN", "SENT", "FILLED"}

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

PREVIEW_COLUMNS = [
    "preview_time_utc",
    "row_index",
    "policy_name",
    "requested_strategy_key",
    "requested_strategy_id",
    "requested_router_strategy_slot",
    "requested_pair_name",
    "requested_condition_id",
    "requested_signal_key",
    "requested_order_key",
    "requested_payload_key",
    "requested_symbol",
    "requested_direction",
    "requested_lot",
    "positions_source",
    "existing_total_positions",
    "existing_symbol_positions",
    "existing_symbol_lot",
    "existing_symbol_directions",
    "registry_status",
    "registry_rows",
    "active_registry_rows",
    "registry_matched_rows",
    "registry_missing_position_rows",
    "registry_mismatch_rows",
    "unregistered_position_rows",
    "same_strategy_registry_tickets",
    "same_strategy_blocked",
    "same_strategy_reason",
    "opposite_direction_blocked",
    "opposite_direction_reason",
    "total_position_cap_blocked",
    "total_position_cap_reason",
    "per_order_lot_blocked",
    "per_order_lot_reason",
    "duplicate_key_blocked",
    "duplicate_key_reason",
    "registry_inconsistency_blocked",
    "registry_inconsistency_reason",
    "input_validation_blocked",
    "input_validation_reason",
    "final_policy_decision",
    "final_policy_reason",
]

RECONCILE_COLUMNS = [
    "reconcile_time_utc",
    "row_type",
    "registry_row_index",
    "registry_position_ticket",
    "registry_broker_symbol",
    "registry_direction",
    "registry_lot",
    "registry_strategy_key",
    "registry_strategy_alias",
    "registry_status",
    "position_ticket",
    "position_symbol",
    "position_direction",
    "position_lot",
    "position_comment",
    "position_external_id",
    "ticket_match",
    "symbol_match",
    "direction_match",
    "lot_match",
    "strategy_detected_in_position",
    "reconcile_status",
    "reconcile_reason",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Registry-aware policy preview. No MT5/order_send/order_check.")
    p.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV, help="order_payloads.csv candidate file")
    p.add_argument("--positions-csv", type=Path, required=True, help="Current positions snapshot/mock CSV")
    p.add_argument("--registry-csv", type=Path, default=DEFAULT_REGISTRY_CSV)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--reconcile-csv", type=Path, default=None)
    p.add_argument("--symbol", type=str, default=None, help="Optional broker symbol override/focus, e.g. GOLD#")
    p.add_argument("--max-orders", type=int, default=5)
    p.add_argument("--max-total-positions", type=int, default=5)
    p.add_argument("--max-lot-per-order", type=float, default=0.02)
    p.add_argument("--lot-tolerance", type=float, default=1e-9)
    p.add_argument(
        "--allow-registry-inconsistency",
        action="store_true",
        help="If set, registry missing/mismatch rows are reported but do not block preview decisions.",
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


def clean_float(value: Any) -> float | None:
    try:
        v = float(value)
    except Exception:
        return None
    if pd.isna(v) or not math.isfinite(v):
        return None
    return v


def clean_int_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def mt5_position_direction(position: dict[str, Any]) -> str:
    explicit = clean_str(position.get("direction")).upper()
    if explicit in {"BUY", "SELL"}:
        return explicit
    try:
        t = int(position.get("type"))
    except Exception:
        return "UNKNOWN"
    if t == 0:
        return "BUY"
    if t == 1:
        return "SELL"
    return "UNKNOWN"


def position_volume(position: dict[str, Any]) -> float:
    try:
        return float(position.get("volume", 0.0) or 0.0)
    except Exception:
        return 0.0


def position_text(position: dict[str, Any]) -> str:
    keys = ["comment", "external_id", "symbol", "magic", "identifier", "ticket"]
    return " ".join(clean_str(position.get(k)) for k in keys).lower()


def detect_strategy_in_position(position: dict[str, Any], strategy_key: str, strategy_alias: str = "") -> bool:
    text = position_text(position)
    for key in [strategy_key, strategy_alias]:
        k = clean_str(key)
        if k and k.lower() in text:
            return True
    return False


def read_positions(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "POSITIONS_CSV_NOT_FOUND"
    df = read_csv(path)
    if df.empty:
        return [], "POSITIONS_EMPTY"
    return [{str(k): row.get(k) for k in df.columns} for _, row in df.iterrows()], "POSITIONS_READ_OK"


def read_payloads(path: Path, max_orders: int) -> tuple[pd.DataFrame, str, bool]:
    if not path.exists():
        return pd.DataFrame(), "NO_INPUT_CSV", False
    df = read_csv(path)
    if df.empty:
        return df, "NO_INPUT_ROWS", True
    if max_orders > 0:
        df = df.head(max_orders).copy()
    return df, "INPUT_ROWS_FOUND", True


def read_registry(path: Path) -> tuple[pd.DataFrame, str, bool]:
    if not path.exists():
        return pd.DataFrame(columns=REGISTRY_COLUMNS), "REGISTRY_NOT_FOUND", False
    df = read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=REGISTRY_COLUMNS), "REGISTRY_EMPTY", True
    for col in REGISTRY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REGISTRY_COLUMNS].copy(), "REGISTRY_READ_OK", True


def active_registry_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    return df["position_status"].astype(str).str.upper().isin(ACTIVE_STATUSES)


def requested_strategy_key(row: pd.Series) -> str:
    return clean_str(row.get("router_strategy_slot")) or clean_str(row.get("pair_name")) or clean_str(row.get("strategy_id"))


def requested_symbol(row: pd.Series, symbol_override: str | None) -> str:
    return symbol_override or clean_str(row.get("broker_symbol"), clean_str(row.get("symbol")))


def position_lookup(positions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in positions:
        ticket = clean_int_text(p.get("ticket"))
        if ticket:
            out[ticket] = p
    return out


def active_registry_tickets(registry_df: pd.DataFrame) -> set[str]:
    if registry_df.empty:
        return set()
    active_df = registry_df[active_registry_mask(registry_df)]
    return {clean_int_text(v) for v in active_df["position_ticket"].tolist() if clean_int_text(v)}


def reconcile_registry(now: str, registry_df: pd.DataFrame, positions: list[dict[str, Any]], lot_tolerance: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    lookup = position_lookup(positions)

    if not registry_df.empty:
        for idx, reg in registry_df[active_registry_mask(registry_df)].iterrows():
            ticket = clean_int_text(reg.get("position_ticket"))
            pos = lookup.get(ticket)
            base = {col: "" for col in RECONCILE_COLUMNS}
            base.update({
                "reconcile_time_utc": now,
                "row_type": "ACTIVE_REGISTRY_ROW",
                "registry_row_index": int(idx),
                "registry_position_ticket": ticket,
                "registry_broker_symbol": clean_str(reg.get("broker_symbol")),
                "registry_direction": clean_str(reg.get("direction")).upper(),
                "registry_lot": clean_float(reg.get("lot")) if clean_float(reg.get("lot")) is not None else "",
                "registry_strategy_key": clean_str(reg.get("strategy_key")),
                "registry_strategy_alias": clean_str(reg.get("strategy_alias")),
                "registry_status": clean_str(reg.get("position_status")),
            })
            if pos is None:
                base.update({
                    "ticket_match": "false",
                    "reconcile_status": "REGISTRY_ACTIVE_MISSING_POSITION",
                    "reconcile_reason": f"active registry ticket not found in current positions: ticket={ticket}",
                })
                rows.append(base)
                continue

            reg_symbol = clean_str(reg.get("broker_symbol")).upper()
            reg_direction = clean_str(reg.get("direction")).upper()
            reg_lot = clean_float(reg.get("lot"))
            pos_symbol = clean_str(pos.get("symbol")).upper()
            pos_direction = mt5_position_direction(pos)
            pos_lot = position_volume(pos)
            symbol_match = reg_symbol == pos_symbol
            direction_match = reg_direction == pos_direction
            lot_match = bool(reg_lot is not None and abs(float(reg_lot) - float(pos_lot)) <= float(lot_tolerance))
            strategy_detected = detect_strategy_in_position(pos, clean_str(reg.get("strategy_key")), clean_str(reg.get("strategy_alias")))
            problems: list[str] = []
            if not symbol_match:
                problems.append(f"symbol mismatch: registry={reg_symbol}; position={pos_symbol}")
            if not direction_match:
                problems.append(f"direction mismatch: registry={reg_direction}; position={pos_direction}")
            if not lot_match:
                problems.append(f"lot mismatch: registry={reg_lot}; position={pos_lot}")
            base.update({
                "position_ticket": clean_int_text(pos.get("ticket")),
                "position_symbol": clean_str(pos.get("symbol")),
                "position_direction": pos_direction,
                "position_lot": pos_lot,
                "position_comment": clean_str(pos.get("comment")),
                "position_external_id": clean_str(pos.get("external_id")),
                "ticket_match": "true",
                "symbol_match": bool_text(symbol_match),
                "direction_match": bool_text(direction_match),
                "lot_match": bool_text(lot_match),
                "strategy_detected_in_position": bool_text(strategy_detected),
                "reconcile_status": "REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH" if problems else "REGISTRY_ACTIVE_MATCHED",
                "reconcile_reason": "; ".join(problems) if problems else "active registry row matched current open position",
            })
            rows.append(base)

    active_tickets = active_registry_tickets(registry_df)
    for pos in positions:
        ticket = clean_int_text(pos.get("ticket"))
        if ticket and ticket in active_tickets:
            continue
        row = {col: "" for col in RECONCILE_COLUMNS}
        row.update({
            "reconcile_time_utc": now,
            "row_type": "POSITION_WITHOUT_ACTIVE_REGISTRY",
            "position_ticket": ticket,
            "position_symbol": clean_str(pos.get("symbol")),
            "position_direction": mt5_position_direction(pos),
            "position_lot": position_volume(pos),
            "position_comment": clean_str(pos.get("comment")),
            "position_external_id": clean_str(pos.get("external_id")),
            "ticket_match": "false",
            "reconcile_status": "POSITION_WITHOUT_ACTIVE_REGISTRY",
            "reconcile_reason": f"current position ticket is not present in ACTIVE registry rows: ticket={ticket}",
        })
        rows.append(row)

    return pd.DataFrame([{col: row.get(col, "") for col in RECONCILE_COLUMNS} for row in rows], columns=RECONCILE_COLUMNS)


def read_existing_keys(order_ledger_csv: Path) -> tuple[set[str], set[str], str]:
    if not order_ledger_csv.exists():
        return set(), set(), "ORDER_LEDGER_NOT_FOUND"
    df = read_csv(order_ledger_csv)
    if df.empty:
        return set(), set(), "ORDER_LEDGER_EMPTY"
    order_keys: set[str] = set()
    signal_keys: set[str] = set()
    for col in ["order_key", "payload_key"]:
        if col in df.columns:
            order_keys.update(clean_str(v) for v in df[col].dropna().tolist() if clean_str(v))
    if "signal_key" in df.columns:
        signal_keys.update(clean_str(v) for v in df["signal_key"].dropna().tolist() if clean_str(v))
    return order_keys, signal_keys, "ORDER_LEDGER_READ_OK"


def same_symbol_positions(positions: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    s = symbol.upper()
    return [p for p in positions if clean_str(p.get("symbol")).upper() == s]


def active_matched_registry_for_strategy(registry_df: pd.DataFrame, reconcile_df: pd.DataFrame, strategy_key: str, symbol: str) -> list[str]:
    if registry_df.empty or reconcile_df.empty:
        return []
    matched = reconcile_df[reconcile_df["reconcile_status"].astype(str).eq("REGISTRY_ACTIVE_MATCHED")].copy()
    if matched.empty:
        return []
    tickets: list[str] = []
    for _, row in matched.iterrows():
        if clean_str(row.get("registry_strategy_key")) == strategy_key and clean_str(row.get("registry_broker_symbol")).upper() == symbol.upper():
            ticket = clean_int_text(row.get("registry_position_ticket"))
            if ticket:
                tickets.append(ticket)
    return sorted(set(tickets))


def preview_row(
    *,
    now: str,
    row_index: int,
    payload_row: pd.Series,
    args: argparse.Namespace,
    positions: list[dict[str, Any]],
    registry_df: pd.DataFrame,
    reconcile_df: pd.DataFrame,
    registry_status: str,
    order_keys: set[str],
    signal_keys: set[str],
    seen_order_keys: set[str],
    seen_signal_keys: set[str],
) -> dict[str, Any]:
    req_symbol = requested_symbol(payload_row, args.symbol)
    req_direction = clean_str(payload_row.get("direction")).upper()
    req_lot = clean_float(payload_row.get("lot"))
    req_strategy_key = requested_strategy_key(payload_row)
    req_strategy_id = clean_str(payload_row.get("strategy_id"))
    req_router_slot = clean_str(payload_row.get("router_strategy_slot"))
    req_pair_name = clean_str(payload_row.get("pair_name"))
    req_condition_id = clean_str(payload_row.get("condition_id"))
    req_signal_key = clean_str(payload_row.get("signal_key"))
    req_order_key = clean_str(payload_row.get("order_key"), clean_str(payload_row.get("payload_key")))
    req_payload_key = clean_str(payload_row.get("payload_key"), req_order_key)

    input_errors: list[str] = []
    if not req_symbol:
        input_errors.append("missing requested_symbol/broker_symbol")
    if req_direction not in {"BUY", "SELL"}:
        input_errors.append(f"requested_direction must be BUY or SELL: {req_direction}")
    if req_lot is None:
        input_errors.append("requested_lot is missing or non-finite")
    if not req_strategy_key:
        input_errors.append("requested_strategy_key is missing")
    if not req_order_key:
        input_errors.append("requested_order_key is missing")
    if not req_signal_key:
        input_errors.append("requested_signal_key is missing")

    symbol_positions = same_symbol_positions(positions, req_symbol) if req_symbol else []
    symbol_directions = [mt5_position_direction(p) for p in symbol_positions]
    symbol_lot = sum(position_volume(p) for p in symbol_positions)

    duplicate_reasons: list[str] = []
    if req_order_key and req_order_key in order_keys:
        duplicate_reasons.append(f"order_key already exists in order ledger: {req_order_key}")
    if req_payload_key and req_payload_key in order_keys:
        duplicate_reasons.append(f"payload_key already exists in order ledger: {req_payload_key}")
    if req_signal_key and req_signal_key in signal_keys:
        duplicate_reasons.append(f"signal_key already exists in order ledger: {req_signal_key}")
    if req_order_key and req_order_key in seen_order_keys:
        duplicate_reasons.append(f"duplicate order_key within input csv: {req_order_key}")
    if req_signal_key and req_signal_key in seen_signal_keys:
        duplicate_reasons.append(f"duplicate signal_key within input csv: {req_signal_key}")
    duplicate_blocked = bool(duplicate_reasons)

    registry_missing_rows = int((reconcile_df["reconcile_status"] == "REGISTRY_ACTIVE_MISSING_POSITION").sum()) if not reconcile_df.empty else 0
    registry_mismatch_rows = int((reconcile_df["reconcile_status"] == "REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH").sum()) if not reconcile_df.empty else 0
    unregistered_rows = int((reconcile_df["reconcile_status"] == "POSITION_WITHOUT_ACTIVE_REGISTRY").sum()) if not reconcile_df.empty else 0
    registry_matched_rows = int((reconcile_df["reconcile_status"] == "REGISTRY_ACTIVE_MATCHED").sum()) if not reconcile_df.empty else 0

    registry_inconsistency_reasons: list[str] = []
    if registry_missing_rows > 0:
        registry_inconsistency_reasons.append(f"registry has ACTIVE row(s) missing from current positions: count={registry_missing_rows}")
    if registry_mismatch_rows > 0:
        registry_inconsistency_reasons.append(f"registry ACTIVE row(s) matched with mismatch: count={registry_mismatch_rows}")
    registry_inconsistency_blocked = bool(registry_inconsistency_reasons) and not args.allow_registry_inconsistency

    same_strategy_tickets = active_matched_registry_for_strategy(registry_df, reconcile_df, req_strategy_key, req_symbol) if req_strategy_key and req_symbol else []
    same_strategy_blocked = bool(same_strategy_tickets)
    same_strategy_reason = f"ACTIVE matched registry position already exists for strategy={req_strategy_key}; tickets={same_strategy_tickets}" if same_strategy_blocked else ""

    opposite = [d for d in symbol_directions if d in {"BUY", "SELL"} and d != req_direction]
    opposite_blocked = bool(opposite)
    opposite_reason = f"existing same-symbol opposite direction position(s): requested={req_direction}; existing_directions={symbol_directions}" if opposite_blocked else ""

    total_cap_blocked = len(positions) >= int(args.max_total_positions)
    total_cap_reason = f"total open positions cap reached: existing_total_positions={len(positions)}; max_total_positions={int(args.max_total_positions)}" if total_cap_blocked else ""

    per_lot_blocked = bool(req_lot is not None and req_lot > float(args.max_lot_per_order) + 1e-12)
    per_lot_reason = f"requested lot exceeds per-order cap: requested_lot={req_lot}; max_lot_per_order={float(args.max_lot_per_order)}" if per_lot_blocked else ""

    input_validation_blocked = bool(input_errors)
    block_reasons: list[str] = []
    if input_validation_blocked:
        block_reasons.append("input_validation: " + "; ".join(input_errors))
    if duplicate_blocked:
        block_reasons.append("duplicate: " + "; ".join(duplicate_reasons))
    if registry_inconsistency_blocked:
        block_reasons.append("registry_inconsistency: " + "; ".join(registry_inconsistency_reasons))
    if same_strategy_blocked:
        block_reasons.append("same_strategy: " + same_strategy_reason)
    if opposite_blocked:
        block_reasons.append("opposite_direction: " + opposite_reason)
    if total_cap_blocked:
        block_reasons.append("total_position_cap: " + total_cap_reason)
    if per_lot_blocked:
        block_reasons.append("per_order_lot: " + per_lot_reason)

    final_decision = "BLOCK" if block_reasons else "ALLOW"
    final_reason = "; ".join(block_reasons) if block_reasons else "policy allow: registry consistent, no duplicate, no same-strategy registry position, no opposite same-symbol direction, total cap not reached, lot cap ok"

    active_registry_rows = int(active_registry_mask(registry_df).sum()) if not registry_df.empty else 0
    return {
        "preview_time_utc": now,
        "row_index": int(row_index),
        "policy_name": POLICY_NAME,
        "requested_strategy_key": req_strategy_key,
        "requested_strategy_id": req_strategy_id,
        "requested_router_strategy_slot": req_router_slot,
        "requested_pair_name": req_pair_name,
        "requested_condition_id": req_condition_id,
        "requested_signal_key": req_signal_key,
        "requested_order_key": req_order_key,
        "requested_payload_key": req_payload_key,
        "requested_symbol": req_symbol,
        "requested_direction": req_direction,
        "requested_lot": req_lot if req_lot is not None else "",
        "positions_source": "POSITIONS_CSV",
        "existing_total_positions": int(len(positions)),
        "existing_symbol_positions": int(len(symbol_positions)),
        "existing_symbol_lot": float(symbol_lot),
        "existing_symbol_directions": ",".join(symbol_directions),
        "registry_status": registry_status,
        "registry_rows": int(len(registry_df)),
        "active_registry_rows": active_registry_rows,
        "registry_matched_rows": registry_matched_rows,
        "registry_missing_position_rows": registry_missing_rows,
        "registry_mismatch_rows": registry_mismatch_rows,
        "unregistered_position_rows": unregistered_rows,
        "same_strategy_registry_tickets": ",".join(same_strategy_tickets),
        "same_strategy_blocked": bool_text(same_strategy_blocked),
        "same_strategy_reason": same_strategy_reason,
        "opposite_direction_blocked": bool_text(opposite_blocked),
        "opposite_direction_reason": opposite_reason,
        "total_position_cap_blocked": bool_text(total_cap_blocked),
        "total_position_cap_reason": total_cap_reason,
        "per_order_lot_blocked": bool_text(per_lot_blocked),
        "per_order_lot_reason": per_lot_reason,
        "duplicate_key_blocked": bool_text(duplicate_blocked),
        "duplicate_key_reason": "; ".join(duplicate_reasons),
        "registry_inconsistency_blocked": bool_text(registry_inconsistency_blocked),
        "registry_inconsistency_reason": "; ".join(registry_inconsistency_reasons),
        "input_validation_blocked": bool_text(input_validation_blocked),
        "input_validation_reason": "; ".join(input_errors),
        "final_policy_decision": final_decision,
        "final_policy_reason": final_reason,
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / OUTPUT_CSV_NAME
    output_json = args.output_json if args.output_json is not None else args.out_dir / OUTPUT_JSON_NAME
    reconcile_csv = args.reconcile_csv if args.reconcile_csv is not None else args.out_dir / RECONCILE_CSV_NAME
    now = utc_now_text()

    payload_df, input_status, input_exists = read_payloads(args.input_csv, args.max_orders)
    positions, positions_status = read_positions(args.positions_csv)
    registry_df, registry_status, registry_exists = read_registry(args.registry_csv)
    reconcile_df = reconcile_registry(now, registry_df, positions, args.lot_tolerance)
    write_csv(reconcile_df, reconcile_csv)

    order_keys, signal_keys, ledger_status = read_existing_keys(args.order_ledger_csv)

    rows: list[dict[str, Any]] = []
    seen_order_keys: set[str] = set()
    seen_signal_keys: set[str] = set()
    if not payload_df.empty:
        for i, (_, payload_row) in enumerate(payload_df.iterrows(), start=1):
            row = preview_row(
                now=now,
                row_index=i,
                payload_row=payload_row,
                args=args,
                positions=positions,
                registry_df=registry_df,
                reconcile_df=reconcile_df,
                registry_status=registry_status,
                order_keys=order_keys,
                signal_keys=signal_keys,
                seen_order_keys=seen_order_keys,
                seen_signal_keys=seen_signal_keys,
            )
            rows.append(row)
            if row.get("requested_order_key"):
                seen_order_keys.add(str(row["requested_order_key"]))
            if row.get("requested_signal_key"):
                seen_signal_keys.add(str(row["requested_signal_key"]))

    out = pd.DataFrame([{col: row.get(col, "") for col in PREVIEW_COLUMNS} for row in rows], columns=PREVIEW_COLUMNS)
    write_csv(out, output_csv)

    allow_rows = int((out["final_policy_decision"] == "ALLOW").sum()) if not out.empty else 0
    blocked_rows = int((out["final_policy_decision"] == "BLOCK").sum()) if not out.empty else 0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "preview_ok": positions_status != "POSITIONS_CSV_NOT_FOUND",
        "reason": "POLICY_PREVIEW_EVALUATED" if not payload_df.empty else input_status,
        "policy_name": POLICY_NAME,
        "input_csv": str(args.input_csv),
        "input_status": input_status,
        "input_exists": bool(input_exists),
        "positions_csv": str(args.positions_csv),
        "positions_status": positions_status,
        "positions_rows": int(len(positions)),
        "registry_csv": str(args.registry_csv),
        "registry_status": registry_status,
        "registry_exists": bool(registry_exists),
        "registry_rows": int(len(registry_df)),
        "active_registry_rows": int(active_registry_mask(registry_df).sum()) if not registry_df.empty else 0,
        "order_ledger_csv": str(args.order_ledger_csv),
        "order_ledger_status": ledger_status,
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "reconcile_csv": str(reconcile_csv),
        "rows_in": int(len(payload_df)),
        "rows_out": int(len(out)),
        "allow_rows": allow_rows,
        "blocked_rows": blocked_rows,
        "same_strategy_blocked_rows": int((out["same_strategy_blocked"] == "true").sum()) if not out.empty else 0,
        "opposite_direction_blocked_rows": int((out["opposite_direction_blocked"] == "true").sum()) if not out.empty else 0,
        "total_position_cap_blocked_rows": int((out["total_position_cap_blocked"] == "true").sum()) if not out.empty else 0,
        "per_order_lot_blocked_rows": int((out["per_order_lot_blocked"] == "true").sum()) if not out.empty else 0,
        "duplicate_key_blocked_rows": int((out["duplicate_key_blocked"] == "true").sum()) if not out.empty else 0,
        "registry_inconsistency_blocked_rows": int((out["registry_inconsistency_blocked"] == "true").sum()) if not out.empty else 0,
        "reconcile_status_counts": reconcile_df["reconcile_status"].value_counts().to_dict() if not reconcile_df.empty else {},
        "max_total_positions": int(args.max_total_positions),
        "max_lot_per_order": float(args.max_lot_per_order),
        "allow_registry_inconsistency": bool(args.allow_registry_inconsistency),
        "safety": {
            "mt5_imported": False,
            "order_check_called_count": 0,
            "order_send_called_count": 0,
            "registry_mutated": False,
            "ledger_mutated": False,
            "trigger_state_mutated": False,
        },
        "records": out.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("run_gold_multi_strategy_registry_policy_preview")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if not out.empty:
        show_cols = [
            "row_index",
            "requested_strategy_key",
            "requested_symbol",
            "requested_direction",
            "requested_lot",
            "existing_total_positions",
            "existing_symbol_positions",
            "existing_symbol_directions",
            "registry_matched_rows",
            "registry_missing_position_rows",
            "unregistered_position_rows",
            "same_strategy_blocked",
            "opposite_direction_blocked",
            "total_position_cap_blocked",
            "per_order_lot_blocked",
            "duplicate_key_blocked",
            "registry_inconsistency_blocked",
            "final_policy_decision",
            "final_policy_reason",
        ]
        print(out[show_cols].to_string(index=False))
    else:
        print("[INFO] no payload rows; reconciliation preview written only")
    print(f"output_csv: {output_csv}")
    print(f"output_json: {output_json}")
    print(f"reconcile_csv: {reconcile_csv}")
    print("done")
    return 0 if summary["preview_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
