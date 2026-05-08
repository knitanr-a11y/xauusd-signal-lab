#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run preflight v2 for future GOLD multi-strategy position policy.

This is a safer revision of run_gold_multi_strategy_position_policy_preflight.py.

Important v2 change:
- Even when order_payloads.csv is missing or empty, this script still initializes MT5,
  validates the account guard, reads current open positions, and writes a snapshot to
  strategy_position_policy_preflight.json.

This script intentionally does NOT call mt5.order_check or mt5.order_send.

Policy candidate:
    block_same_strategy_and_opposite_direction

Rules for payload rows:
1. same signal_key / order_key duplicate is blocked.
2. same strategy is limited to one open position.
3. same symbol opposite direction is blocked.
4. total open positions >= max_total_positions is blocked.
5. requested lot > max_lot_per_order is blocked.
6. otherwise allow.

Safety boundary:
- No order_send.
- No order_check.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from pandas.errors import EmptyDataError

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as e:  # pragma: no cover - depends on local MT5 install
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(e)
else:  # pragma: no cover - depends on local MT5 install
    MT5_IMPORT_ERROR = ""

POLICY_NAME = "block_same_strategy_and_opposite_direction"
SCHEMA_VERSION = "gold_multi_strategy_position_policy_preflight_v2"

DEFAULT_INPUT_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/order_payloads.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_policy_preflight")
DEFAULT_ORDER_LEDGER_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/dry_run_order_ledger.csv")

OUTPUT_CSV_NAME = "strategy_position_policy_preflight.csv"
OUTPUT_JSON_NAME = "strategy_position_policy_preflight.json"
POSITIONS_CSV_NAME = "strategy_position_policy_preflight_positions.csv"

OUTPUT_COLUMNS = [
    "preflight_time_utc",
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
    "existing_total_positions",
    "existing_symbol_positions",
    "existing_symbol_lot",
    "existing_symbol_directions",
    "existing_symbol_strategy_keys_detected",
    "existing_symbol_positions_detail",
    "duplicate_key_blocked",
    "duplicate_key_reason",
    "same_strategy_blocked",
    "same_strategy_reason",
    "opposite_direction_blocked",
    "opposite_direction_reason",
    "total_position_cap_blocked",
    "total_position_cap_reason",
    "per_order_lot_blocked",
    "per_order_lot_reason",
    "input_validation_blocked",
    "input_validation_reason",
    "strategy_detectability_warning",
    "final_policy_decision",
    "final_policy_reason",
]

POSITION_COLUMNS = [
    "snapshot_time_utc",
    "ticket",
    "identifier",
    "symbol",
    "direction",
    "type",
    "volume",
    "price_open",
    "sl",
    "tp",
    "magic",
    "comment",
    "external_id",
    "time",
    "time_msc",
    "profit",
    "swap",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Dry-run preflight v2 for GOLD multi-strategy MT5 position policy. No order_send/order_check."
    )
    p.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV, help="Mochipoyo-compatible order_payloads.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None, help=f"Default: <out-dir>/{OUTPUT_CSV_NAME}")
    p.add_argument("--output-json", type=Path, default=None, help=f"Default: <out-dir>/{OUTPUT_JSON_NAME}")
    p.add_argument("--positions-csv", type=Path, default=None, help=f"Default: <out-dir>/{POSITIONS_CSV_NAME}")
    p.add_argument(
        "--order-ledger-csv",
        type=Path,
        default=DEFAULT_ORDER_LEDGER_CSV,
        help="Existing order ledger used only for duplicate order_key/signal_key checks. Read-only.",
    )
    p.add_argument("--symbol", type=str, default=None, help="Broker symbol override / position snapshot focus, e.g. GOLD#")
    p.add_argument("--max-orders", type=int, default=5, help="Max payload rows to evaluate. Default 5.")
    p.add_argument("--max-total-positions", type=int, default=5)
    p.add_argument("--max-lot-per-order", type=float, default=0.02)
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--require-demo-account", action="store_true")
    p.add_argument("--allow-live-account", action="store_true")
    p.add_argument("--terminal-path", type=str, default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument(
        "--select-symbol",
        action="store_true",
        help="Call mt5.symbol_select(symbol, True) before reading positions. Does not place/check orders.",
    )
    p.add_argument(
        "--block-unknown-same-symbol-strategy",
        action="store_true",
        help=(
            "Conservative optional mode: if an existing same-symbol same-direction position has no detectable "
            "strategy key, block it as possibly the same strategy. Default false."
        ),
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


def bool_text(v: bool) -> str:
    return "true" if bool(v) else "false"


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        raw = obj._asdict()
    elif isinstance(obj, dict):
        raw = obj
    else:
        raw = {"value": str(obj)}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        try:
            json.dumps(v)
            out[str(k)] = v
        except TypeError:
            out[str(k)] = str(v)
    return out


def asdict_list(items: Any) -> list[dict[str, Any]]:
    if items is None:
        return []
    out: list[dict[str, Any]] = []
    for item in list(items):
        out.append(asdict_obj(item))
    return out


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def mt5_position_direction(position: dict[str, Any]) -> str:
    try:
        t = int(position.get("type"))
    except Exception:
        return "UNKNOWN"
    if mt5 is not None:
        if t == int(mt5.POSITION_TYPE_BUY):
            return "BUY"
        if t == int(mt5.POSITION_TYPE_SELL):
            return "SELL"
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


def position_text_for_strategy_detection(position: dict[str, Any]) -> str:
    keys = ["comment", "external_id", "symbol", "magic", "identifier", "ticket"]
    return " ".join(clean_str(position.get(k)) for k in keys).lower()


def requested_strategy_key(row: pd.Series) -> str:
    return clean_str(row.get("router_strategy_slot")) or clean_str(row.get("pair_name")) or clean_str(row.get("strategy_id"))


def strategy_match_keys(row: pd.Series) -> list[str]:
    keys = [
        requested_strategy_key(row),
        clean_str(row.get("router_strategy_id")),
        clean_str(row.get("strategy_id")),
        clean_str(row.get("pair_name")),
    ]
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        k = key.strip()
        if not k:
            continue
        low = k.lower()
        if low not in seen:
            out.append(k)
            seen.add(low)
    return out


def infer_position_strategy_keys(position: dict[str, Any], known_strategy_keys: Iterable[str]) -> list[str]:
    text = position_text_for_strategy_detection(position)
    detected: list[str] = []
    for key in known_strategy_keys:
        k = clean_str(key)
        if k and k.lower() in text:
            detected.append(k)
    return detected


def summarize_positions(positions: list[dict[str, Any]], known_strategy_keys: Iterable[str] = ()) -> str:
    if not positions:
        return ""
    parts: list[str] = []
    for p in positions:
        detected = infer_position_strategy_keys(p, known_strategy_keys)
        parts.append(
            "ticket={ticket},symbol={symbol},direction={direction},type={type},volume={volume},price_open={price_open},sl={sl},tp={tp},magic={magic},comment={comment},detected_strategy={detected}".format(
                ticket=p.get("ticket"),
                symbol=p.get("symbol"),
                direction=mt5_position_direction(p),
                type=p.get("type"),
                volume=p.get("volume"),
                price_open=p.get("price_open"),
                sl=p.get("sl"),
                tp=p.get("tp"),
                magic=p.get("magic"),
                comment=p.get("comment"),
                detected="|".join(detected) if detected else "",
            )
        )
    return " | ".join(parts)


def load_existing_keys(order_ledger_csv: Path) -> tuple[set[str], set[str], str]:
    if not order_ledger_csv.exists():
        return set(), set(), "ORDER_LEDGER_NOT_FOUND"
    try:
        df = read_csv(order_ledger_csv)
    except Exception as e:
        return set(), set(), f"ORDER_LEDGER_READ_ERROR: {repr(e)}"
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


def get_all_positions() -> list[dict[str, Any]]:
    if mt5 is None:
        return []
    return asdict_list(mt5.positions_get())


def same_symbol_positions(all_positions: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    s = clean_str(symbol).upper()
    return [p for p in all_positions if clean_str(p.get("symbol")).upper() == s]


def positions_dataframe(positions: list[dict[str, Any]], snapshot_time_utc: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for p in positions:
        row = {col: "" for col in POSITION_COLUMNS}
        row.update({
            "snapshot_time_utc": snapshot_time_utc,
            "ticket": p.get("ticket", ""),
            "identifier": p.get("identifier", ""),
            "symbol": p.get("symbol", ""),
            "direction": mt5_position_direction(p),
            "type": p.get("type", ""),
            "volume": p.get("volume", ""),
            "price_open": p.get("price_open", ""),
            "sl": p.get("sl", ""),
            "tp": p.get("tp", ""),
            "magic": p.get("magic", ""),
            "comment": p.get("comment", ""),
            "external_id": p.get("external_id", ""),
            "time": p.get("time", ""),
            "time_msc": p.get("time_msc", ""),
            "profit": p.get("profit", ""),
            "swap": p.get("swap", ""),
        })
        rows.append(row)
    return pd.DataFrame(rows, columns=POSITION_COLUMNS)


def read_payload_csv(input_csv: Path) -> tuple[pd.DataFrame, str, bool]:
    if not input_csv.exists():
        return pd.DataFrame(), "NO_INPUT_CSV", False
    df = read_csv(input_csv)
    if df.empty:
        return df, "NO_INPUT_ROWS", True
    return df, "INPUT_ROWS_FOUND", True


def initialize_mt5_and_snapshot(args: argparse.Namespace, output_csv: Path, output_json: Path) -> tuple[bool, int, dict[str, Any], list[dict[str, Any]]]:
    """Initialize MT5 and read account/positions without calling order_check/order_send.

    Returns (ok, return_code, mt5_report, positions).
    """
    report: dict[str, Any] = {
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "initialize_ok": False,
        "expected_login": args.expected_login,
        "require_demo_account": bool(args.require_demo_account),
        "allow_live_account": bool(args.allow_live_account),
        "order_send_called_count": 0,
        "order_check_called_count": 0,
    }
    if mt5 is None:
        report["fatal_error"] = "MT5_IMPORT_FAILED"
        return False, 2, report, []

    init_kwargs: dict[str, Any] = {}
    if args.terminal_path:
        init_kwargs["path"] = args.terminal_path
    if args.portable:
        init_kwargs["portable"] = True

    initialized = bool(mt5.initialize(**init_kwargs))
    report["initialize_ok"] = initialized
    report["last_error_after_initialize"] = str(mt5.last_error())
    if not initialized:
        report["fatal_error"] = "MT5_INITIALIZE_FAILED"
        return False, 3, report, []

    try:
        terminal_info = asdict_obj(mt5.terminal_info())
        account_info = asdict_obj(mt5.account_info())
        report["terminal_info"] = terminal_info
        report["account_info"] = account_info
        report["account_login"] = account_info.get("login")
        report["account_server"] = account_info.get("server")
        report["account_name"] = account_info.get("name")

        guard_errors: list[str] = []
        if args.expected_login is not None and int(account_info.get("login") or -1) != int(args.expected_login):
            guard_errors.append(f"expected_login mismatch: expected={args.expected_login}; actual={account_info.get('login')}")
        if args.require_demo_account and not args.allow_live_account and not account_looks_demo(account_info):
            guard_errors.append("require_demo_account is set but account/server/company does not look like demo")
        if guard_errors:
            report["fatal_error"] = "GLOBAL_ACCOUNT_GUARD_FAILED"
            report["global_errors"] = guard_errors
            return False, 4, report, []

        if args.select_symbol:
            symbols: list[str] = []
            if args.symbol:
                symbols.append(str(args.symbol))
            selected: dict[str, Any] = {}
            for symbol in sorted(set(s for s in symbols if s)):
                selected[symbol] = bool(mt5.symbol_select(symbol, True))
            report["symbol_select"] = selected
            report["last_error_after_symbol_select"] = str(mt5.last_error())

        positions = get_all_positions()
        report["existing_total_positions"] = int(len(positions))
        report["existing_positions_detail"] = summarize_positions(positions)
        if args.symbol:
            symbol_positions = same_symbol_positions(positions, args.symbol)
            report["snapshot_symbol"] = args.symbol
            report["existing_snapshot_symbol_positions"] = int(len(symbol_positions))
            report["existing_snapshot_symbol_lot"] = float(sum(position_volume(p) for p in symbol_positions))
            report["existing_snapshot_symbol_directions"] = ",".join(mt5_position_direction(p) for p in symbol_positions)
            report["existing_snapshot_symbol_positions_detail"] = summarize_positions(symbol_positions)
        return True, 0, report, positions
    except Exception as e:
        report["fatal_error"] = "MT5_SNAPSHOT_ERROR"
        report["snapshot_error"] = repr(e)
        return False, 5, report, []


def build_preflight_row(
    *,
    now: str,
    row_index: int,
    payload_row: pd.Series,
    args: argparse.Namespace,
    all_positions: list[dict[str, Any]],
    known_existing_order_keys: set[str],
    known_existing_signal_keys: set[str],
    seen_order_keys: set[str],
    seen_signal_keys: set[str],
) -> dict[str, Any]:
    requested_symbol = args.symbol or clean_str(payload_row.get("broker_symbol"), clean_str(payload_row.get("symbol")))
    requested_direction = clean_str(payload_row.get("direction")).upper()
    requested_lot = clean_float(payload_row.get("lot"))
    req_strategy_key = requested_strategy_key(payload_row)
    req_strategy_id = clean_str(payload_row.get("strategy_id"))
    req_router_slot = clean_str(payload_row.get("router_strategy_slot"))
    req_pair_name = clean_str(payload_row.get("pair_name"))
    req_condition_id = clean_str(payload_row.get("condition_id"))
    req_signal_key = clean_str(payload_row.get("signal_key"))
    req_order_key = clean_str(payload_row.get("order_key"), clean_str(payload_row.get("payload_key")))
    req_payload_key = clean_str(payload_row.get("payload_key"), req_order_key)

    input_errors: list[str] = []
    if not requested_symbol:
        input_errors.append("missing requested_symbol/broker_symbol")
    if requested_direction not in {"BUY", "SELL"}:
        input_errors.append(f"requested_direction must be BUY or SELL: {requested_direction}")
    if requested_lot is None:
        input_errors.append("requested_lot is missing or non-finite")
    if not req_strategy_key:
        input_errors.append("requested_strategy_key is missing: need router_strategy_slot, pair_name, or strategy_id")
    if not req_order_key:
        input_errors.append("requested_order_key is missing")
    if not req_signal_key:
        input_errors.append("requested_signal_key is missing")

    symbol_positions = same_symbol_positions(all_positions, requested_symbol) if requested_symbol else []
    symbol_directions = [mt5_position_direction(p) for p in symbol_positions]
    existing_symbol_lot = sum(position_volume(p) for p in symbol_positions)
    match_keys = strategy_match_keys(payload_row)

    detected_strategy_keys: list[str] = []
    for p in symbol_positions:
        detected_strategy_keys.extend(infer_position_strategy_keys(p, match_keys))
    detected_strategy_keys = sorted(set(detected_strategy_keys))

    duplicate_reasons: list[str] = []
    if req_order_key and req_order_key in known_existing_order_keys:
        duplicate_reasons.append(f"order_key already exists in order ledger: {req_order_key}")
    if req_payload_key and req_payload_key in known_existing_order_keys:
        duplicate_reasons.append(f"payload_key already exists in order ledger: {req_payload_key}")
    if req_signal_key and req_signal_key in known_existing_signal_keys:
        duplicate_reasons.append(f"signal_key already exists in order ledger: {req_signal_key}")
    if req_order_key and req_order_key in seen_order_keys:
        duplicate_reasons.append(f"duplicate order_key within input csv: {req_order_key}")
    if req_signal_key and req_signal_key in seen_signal_keys:
        duplicate_reasons.append(f"duplicate signal_key within input csv: {req_signal_key}")
    duplicate_blocked = bool(duplicate_reasons)

    same_strategy_positions: list[dict[str, Any]] = []
    unknown_same_symbol_same_direction_positions: list[dict[str, Any]] = []
    for p in symbol_positions:
        detected = infer_position_strategy_keys(p, match_keys)
        if detected:
            same_strategy_positions.append(p)
        elif mt5_position_direction(p) == requested_direction:
            unknown_same_symbol_same_direction_positions.append(p)

    same_strategy_reasons: list[str] = []
    if same_strategy_positions:
        same_strategy_reasons.append(f"existing same-strategy position(s) detected: count={len(same_strategy_positions)}; strategy_key={req_strategy_key}")
    if args.block_unknown_same_symbol_strategy and unknown_same_symbol_same_direction_positions:
        same_strategy_reasons.append(
            "unknown-strategy same-symbol same-direction position exists and --block-unknown-same-symbol-strategy is enabled: "
            f"count={len(unknown_same_symbol_same_direction_positions)}"
        )
    same_strategy_blocked = bool(same_strategy_reasons)

    opposite = [d for d in symbol_directions if d in {"BUY", "SELL"} and d != requested_direction]
    opposite_blocked = bool(opposite)
    opposite_reason = (
        f"existing same-symbol opposite direction position(s): requested={requested_direction}; existing_directions={symbol_directions}"
        if opposite_blocked
        else ""
    )

    total_position_cap_blocked = len(all_positions) >= int(args.max_total_positions)
    total_position_cap_reason = (
        f"total open positions cap reached: existing_total_positions={len(all_positions)}; max_total_positions={int(args.max_total_positions)}"
        if total_position_cap_blocked
        else ""
    )

    per_order_lot_blocked = bool(requested_lot is not None and requested_lot > float(args.max_lot_per_order) + 1e-12)
    per_order_lot_reason = (
        f"requested lot exceeds per-order cap: requested_lot={requested_lot}; max_lot_per_order={float(args.max_lot_per_order)}"
        if per_order_lot_blocked
        else ""
    )

    input_validation_blocked = bool(input_errors)
    warnings: list[str] = []
    if symbol_positions and not detected_strategy_keys:
        warnings.append(
            "No strategy key was detectable from existing same-symbol MT5 position comments/external_id. "
            "same_strategy_block can only be exact-match until sender stores strategy metadata."
        )

    block_reasons: list[str] = []
    if input_validation_blocked:
        block_reasons.append("input_validation: " + "; ".join(input_errors))
    if duplicate_blocked:
        block_reasons.append("duplicate: " + "; ".join(duplicate_reasons))
    if same_strategy_blocked:
        block_reasons.append("same_strategy: " + "; ".join(same_strategy_reasons))
    if opposite_blocked:
        block_reasons.append("opposite_direction: " + opposite_reason)
    if total_position_cap_blocked:
        block_reasons.append("total_position_cap: " + total_position_cap_reason)
    if per_order_lot_blocked:
        block_reasons.append("per_order_lot: " + per_order_lot_reason)

    final_decision = "BLOCK" if block_reasons else "ALLOW"
    final_reason = "; ".join(block_reasons) if block_reasons else "policy allow: no duplicate, no same-strategy position, no opposite same-symbol direction, total cap not reached, lot cap ok"

    return {
        "preflight_time_utc": now,
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
        "requested_symbol": requested_symbol,
        "requested_direction": requested_direction,
        "requested_lot": requested_lot if requested_lot is not None else "",
        "existing_total_positions": int(len(all_positions)),
        "existing_symbol_positions": int(len(symbol_positions)),
        "existing_symbol_lot": float(existing_symbol_lot),
        "existing_symbol_directions": ",".join(symbol_directions),
        "existing_symbol_strategy_keys_detected": ",".join(detected_strategy_keys),
        "existing_symbol_positions_detail": summarize_positions(symbol_positions, match_keys),
        "duplicate_key_blocked": bool_text(duplicate_blocked),
        "duplicate_key_reason": "; ".join(duplicate_reasons),
        "same_strategy_blocked": bool_text(same_strategy_blocked),
        "same_strategy_reason": "; ".join(same_strategy_reasons),
        "opposite_direction_blocked": bool_text(opposite_blocked),
        "opposite_direction_reason": opposite_reason,
        "total_position_cap_blocked": bool_text(total_position_cap_blocked),
        "total_position_cap_reason": total_position_cap_reason,
        "per_order_lot_blocked": bool_text(per_order_lot_blocked),
        "per_order_lot_reason": per_order_lot_reason,
        "input_validation_blocked": bool_text(input_validation_blocked),
        "input_validation_reason": "; ".join(input_errors),
        "strategy_detectability_warning": "; ".join(warnings),
        "final_policy_decision": final_decision,
        "final_policy_reason": final_reason,
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / OUTPUT_CSV_NAME
    output_json = args.output_json if args.output_json is not None else args.out_dir / OUTPUT_JSON_NAME
    positions_csv = args.positions_csv if args.positions_csv is not None else args.out_dir / POSITIONS_CSV_NAME
    now = utc_now_text()

    src, input_status, input_exists = read_payload_csv(args.input_csv)
    original_rows_in = int(len(src))
    if args.max_orders > 0 and not src.empty:
        src = src.head(int(args.max_orders)).copy()

    mt5_ok, mt5_rc, mt5_report, all_positions = initialize_mt5_and_snapshot(args, output_csv, output_json)
    positions_df = positions_dataframe(all_positions, now)
    write_csv(positions_df, positions_csv)

    if not mt5_ok:
        out = pd.DataFrame(columns=OUTPUT_COLUMNS)
        write_csv(out, output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "preflight_ok": False,
            "policy_name": POLICY_NAME,
            "reason": mt5_report.get("fatal_error", "MT5_PREFLIGHT_FAILED"),
            "input_status": input_status,
            "input_csv": str(args.input_csv),
            "input_exists": bool(input_exists),
            "order_ledger_csv": str(args.order_ledger_csv),
            "output_csv": str(output_csv),
            "output_json": str(output_json),
            "positions_csv": str(positions_csv),
            "rows_in": original_rows_in,
            "rows_out": 0,
            "allow_rows": 0,
            "blocked_rows": 0,
            "mt5": mt5_report,
        }
        write_json(output_json, summary)
        print("run_gold_multi_strategy_position_policy_preflight_v2")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        if mt5 is not None:
            mt5.shutdown()
        return mt5_rc

    existing_order_keys, existing_signal_keys, ledger_reason = load_existing_keys(args.order_ledger_csv)
    rows: list[dict[str, Any]] = []
    seen_order_keys: set[str] = set()
    seen_signal_keys: set[str] = set()

    if not src.empty:
        for i, (_, payload_row) in enumerate(src.iterrows(), start=1):
            result = build_preflight_row(
                now=now,
                row_index=i,
                payload_row=payload_row,
                args=args,
                all_positions=all_positions,
                known_existing_order_keys=existing_order_keys,
                known_existing_signal_keys=existing_signal_keys,
                seen_order_keys=seen_order_keys,
                seen_signal_keys=seen_signal_keys,
            )
            rows.append(result)
            if result.get("requested_order_key"):
                seen_order_keys.add(str(result["requested_order_key"]))
            if result.get("requested_signal_key"):
                seen_signal_keys.add(str(result["requested_signal_key"]))

    out = pd.DataFrame([{col: row.get(col, "") for col in OUTPUT_COLUMNS} for row in rows], columns=OUTPUT_COLUMNS)
    write_csv(out, output_csv)

    allow_rows = int((out["final_policy_decision"] == "ALLOW").sum()) if not out.empty else 0
    blocked_rows = int((out["final_policy_decision"] == "BLOCK").sum()) if not out.empty else 0
    no_payload_snapshot_ok = src.empty and mt5_ok
    reason = input_status if src.empty else "POLICY_ROWS_EVALUATED"

    summary = {
        "schema_version": SCHEMA_VERSION,
        "preflight_ok": True,
        "policy_name": POLICY_NAME,
        "reason": reason,
        "no_payload_snapshot_ok": bool(no_payload_snapshot_ok),
        "input_status": input_status,
        "input_csv": str(args.input_csv),
        "input_exists": bool(input_exists),
        "order_ledger_csv": str(args.order_ledger_csv),
        "order_ledger_status": ledger_reason,
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "positions_csv": str(positions_csv),
        "rows_in": int(len(src)),
        "original_rows_in": original_rows_in,
        "rows_out": int(len(out)),
        "allow_rows": allow_rows,
        "blocked_rows": blocked_rows,
        "duplicate_key_blocked_rows": int((out["duplicate_key_blocked"] == "true").sum()) if not out.empty else 0,
        "same_strategy_blocked_rows": int((out["same_strategy_blocked"] == "true").sum()) if not out.empty else 0,
        "opposite_direction_blocked_rows": int((out["opposite_direction_blocked"] == "true").sum()) if not out.empty else 0,
        "total_position_cap_blocked_rows": int((out["total_position_cap_blocked"] == "true").sum()) if not out.empty else 0,
        "per_order_lot_blocked_rows": int((out["per_order_lot_blocked"] == "true").sum()) if not out.empty else 0,
        "input_validation_blocked_rows": int((out["input_validation_blocked"] == "true").sum()) if not out.empty else 0,
        "max_total_positions": int(args.max_total_positions),
        "max_lot_per_order": float(args.max_lot_per_order),
        "block_unknown_same_symbol_strategy": bool(args.block_unknown_same_symbol_strategy),
        "mt5": mt5_report,
        "records": out.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("run_gold_multi_strategy_position_policy_preflight_v2")
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
            "duplicate_key_blocked",
            "same_strategy_blocked",
            "opposite_direction_blocked",
            "total_position_cap_blocked",
            "per_order_lot_blocked",
            "final_policy_decision",
            "final_policy_reason",
        ]
        print(out[show_cols].to_string(index=False))
    else:
        print(f"[INFO] no payload rows; MT5 position snapshot written: {positions_csv}")
    print(f"output_csv: {output_csv}")
    print(f"output_json: {output_json}")
    print(f"positions_csv: {positions_csv}")
    print("done")

    if mt5 is not None:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
