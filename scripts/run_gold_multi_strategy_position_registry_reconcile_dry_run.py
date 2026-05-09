#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run reconciliation for GOLD multi-strategy position_registry.csv.

This script is an isolated validation layer. It does not modify the real sender.

Purpose:
- Read a proposed position_registry.csv.
- Read current open positions from either:
    1. --positions-csv snapshot/mock CSV, or
    2. real MT5 positions when --positions-csv is omitted.
- Reconcile ACTIVE registry rows against open positions.
- Detect unregistered MT5/mock positions.
- Produce CSV/JSON reports for future sender policy design.

Safety:
- No mt5.order_send.
- No mt5.order_check.
- No registry mutation by default.
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
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as e:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(e)
else:  # pragma: no cover
    MT5_IMPORT_ERROR = ""

SCHEMA_VERSION = "gold_multi_strategy_position_registry_reconcile_dry_run_v1"
DEFAULT_REGISTRY_CSV = Path("data/research_results/gold_multi_strategy_position_registry/position_registry.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_registry")

RECONCILE_CSV_NAME = "position_registry_reconcile_dry_run.csv"
SUMMARY_JSON_NAME = "position_registry_reconcile_dry_run.json"
POSITIONS_SNAPSHOT_CSV_NAME = "position_registry_reconcile_positions_snapshot.csv"

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

RECONCILE_COLUMNS = [
    "reconcile_time_utc",
    "row_type",
    "position_source",
    "registry_row_index",
    "registry_position_status",
    "registry_position_ticket",
    "registry_broker_symbol",
    "registry_direction",
    "registry_lot",
    "registry_strategy_key",
    "registry_strategy_alias",
    "registry_signal_key",
    "registry_order_key",
    "position_ticket",
    "position_symbol",
    "position_direction",
    "position_lot",
    "position_magic",
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

POSITION_SNAPSHOT_COLUMNS = [
    "snapshot_time_utc",
    "position_source",
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

ACTIVE_STATUSES = {"ACTIVE", "OPEN", "SENT", "FILLED"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dry-run reconcile position_registry.csv with open positions. No order_send/order_check.")
    p.add_argument("--registry-csv", type=Path, default=DEFAULT_REGISTRY_CSV)
    p.add_argument("--positions-csv", type=Path, default=None, help="Optional mock/snapshot positions CSV. If omitted, read real MT5 positions.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--positions-snapshot-csv", type=Path, default=None)
    p.add_argument("--symbol", type=str, default=None, help="Optional broker symbol focus, e.g. GOLD#")
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--require-demo-account", action="store_true")
    p.add_argument("--allow-live-account", action="store_true")
    p.add_argument("--terminal-path", type=str, default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--select-symbol", action="store_true")
    p.add_argument("--lot-tolerance", type=float, default=1e-9)
    p.add_argument("--mock-account-login", type=int, default=75539039)
    p.add_argument("--mock-account-server", type=str, default="MOCK-MT5")
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


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


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
    return [asdict_obj(item) for item in list(items)]


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def mt5_position_direction(position: dict[str, Any]) -> str:
    explicit = clean_str(position.get("direction")).upper()
    if explicit in {"BUY", "SELL"}:
        return explicit
    try:
        t = int(position.get("type"))
    except Exception:
        return "UNKNOWN"
    if mt5 is not None:
        try:
            if t == int(mt5.POSITION_TYPE_BUY):
                return "BUY"
            if t == int(mt5.POSITION_TYPE_SELL):
                return "SELL"
        except Exception:
            pass
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


def read_registry(path: Path) -> tuple[pd.DataFrame, str, bool]:
    if not path_exists(path):
        return pd.DataFrame(columns=REGISTRY_COLUMNS), "REGISTRY_NOT_FOUND", False
    df = read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=REGISTRY_COLUMNS), "REGISTRY_EMPTY", True
    for col in REGISTRY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REGISTRY_COLUMNS].copy(), "REGISTRY_READ_OK", True


def read_positions_from_csv(path: Path) -> list[dict[str, Any]]:
    df = read_csv(path)
    if df.empty:
        return []
    return [{str(k): row.get(k) for k in df.columns} for _, row in df.iterrows()]


def get_real_mt5_positions(args: argparse.Namespace) -> tuple[bool, int, str, dict[str, Any], list[dict[str, Any]]]:
    report: dict[str, Any] = {
        "position_source": "MT5_REAL",
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
        return False, 2, "MT5_REAL", report, []

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
        return False, 3, "MT5_REAL", report, []

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
        return False, 4, "MT5_REAL", report, []

    if args.select_symbol and args.symbol:
        report["symbol_select"] = {str(args.symbol): bool(mt5.symbol_select(str(args.symbol), True))}
        report["last_error_after_symbol_select"] = str(mt5.last_error())

    positions = asdict_list(mt5.positions_get())
    add_position_report_summary(report, positions, args.symbol)
    return True, 0, "MT5_REAL", report, positions


def get_positions(args: argparse.Namespace) -> tuple[bool, int, str, dict[str, Any], list[dict[str, Any]]]:
    if args.positions_csv is not None:
        report: dict[str, Any] = {
            "position_source": "POSITIONS_CSV",
            "positions_csv": str(args.positions_csv),
            "mock_account_login": int(args.mock_account_login),
            "mock_account_server": str(args.mock_account_server),
            "mt5_initialize_skipped": True,
            "order_send_called_count": 0,
            "order_check_called_count": 0,
        }
        if not path_exists(args.positions_csv):
            report["fatal_error"] = "POSITIONS_CSV_NOT_FOUND"
            return False, 20, "POSITIONS_CSV", report, []
        try:
            positions = read_positions_from_csv(args.positions_csv)
        except Exception as e:
            report["fatal_error"] = "POSITIONS_CSV_READ_ERROR"
            report["positions_csv_read_error"] = repr(e)
            return False, 21, "POSITIONS_CSV", report, []
        add_position_report_summary(report, positions, args.symbol)
        return True, 0, "POSITIONS_CSV", report, positions
    return get_real_mt5_positions(args)


def add_position_report_summary(report: dict[str, Any], positions: list[dict[str, Any]], symbol: str | None) -> None:
    report["existing_total_positions"] = int(len(positions))
    if symbol:
        symbol_positions = [p for p in positions if clean_str(p.get("symbol")).upper() == str(symbol).upper()]
        report["snapshot_symbol"] = symbol
        report["existing_snapshot_symbol_positions"] = int(len(symbol_positions))
        report["existing_snapshot_symbol_lot"] = float(sum(position_volume(p) for p in symbol_positions))
        report["existing_snapshot_symbol_directions"] = ",".join(mt5_position_direction(p) for p in symbol_positions)


def positions_snapshot_dataframe(positions: list[dict[str, Any]], now: str, source: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for p in positions:
        row = {col: "" for col in POSITION_SNAPSHOT_COLUMNS}
        row.update({
            "snapshot_time_utc": now,
            "position_source": source,
            "ticket": clean_int_text(p.get("ticket")),
            "identifier": clean_int_text(p.get("identifier")),
            "symbol": clean_str(p.get("symbol")),
            "direction": mt5_position_direction(p),
            "type": clean_int_text(p.get("type")),
            "volume": position_volume(p),
            "price_open": clean_float(p.get("price_open")) if clean_float(p.get("price_open")) is not None else "",
            "sl": clean_float(p.get("sl")) if clean_float(p.get("sl")) is not None else "",
            "tp": clean_float(p.get("tp")) if clean_float(p.get("tp")) is not None else "",
            "magic": clean_int_text(p.get("magic")),
            "comment": clean_str(p.get("comment")),
            "external_id": clean_str(p.get("external_id")),
            "time": clean_str(p.get("time")),
            "time_msc": clean_str(p.get("time_msc")),
            "profit": clean_float(p.get("profit")) if clean_float(p.get("profit")) is not None else "",
            "swap": clean_float(p.get("swap")) if clean_float(p.get("swap")) is not None else "",
        })
        rows.append(row)
    return pd.DataFrame(rows, columns=POSITION_SNAPSHOT_COLUMNS)


def active_registry_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    return df["position_status"].astype(str).str.upper().isin(ACTIVE_STATUSES)


def build_position_lookup(positions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in positions:
        ticket = clean_int_text(p.get("ticket"))
        if ticket:
            out[ticket] = p
    return out


def build_registry_active_ticket_set(registry_df: pd.DataFrame) -> set[str]:
    if registry_df.empty:
        return set()
    active_df = registry_df[active_registry_mask(registry_df)]
    return {clean_int_text(v) for v in active_df["position_ticket"].tolist() if clean_int_text(v)}


def reconcile_registry_rows(now: str, registry_df: pd.DataFrame, positions: list[dict[str, Any]], source: str, lot_tolerance: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lookup = build_position_lookup(positions)
    if registry_df.empty:
        return rows

    for idx, reg in registry_df.iterrows():
        status = clean_str(reg.get("position_status")).upper()
        if status not in ACTIVE_STATUSES:
            continue
        registry_ticket = clean_int_text(reg.get("position_ticket"))
        position = lookup.get(registry_ticket)
        base = base_reconcile_row(now, source, idx, reg)
        if position is None:
            base.update({
                "reconcile_status": "REGISTRY_ACTIVE_MISSING_POSITION",
                "reconcile_reason": f"active registry ticket not found in current positions: ticket={registry_ticket}",
            })
            rows.append(base)
            continue

        registry_symbol = clean_str(reg.get("broker_symbol")).upper()
        registry_direction = clean_str(reg.get("direction")).upper()
        registry_lot = clean_float(reg.get("lot"))
        position_symbol = clean_str(position.get("symbol")).upper()
        position_direction = mt5_position_direction(position)
        position_lot = position_volume(position)
        symbol_match = registry_symbol == position_symbol
        direction_match = registry_direction == position_direction
        lot_match = bool(registry_lot is not None and abs(float(registry_lot) - float(position_lot)) <= float(lot_tolerance))
        strategy_detected = detect_strategy_in_position(position, clean_str(reg.get("strategy_key")), clean_str(reg.get("strategy_alias")))
        problems: list[str] = []
        if not symbol_match:
            problems.append(f"symbol mismatch: registry={registry_symbol}; position={position_symbol}")
        if not direction_match:
            problems.append(f"direction mismatch: registry={registry_direction}; position={position_direction}")
        if not lot_match:
            problems.append(f"lot mismatch: registry={registry_lot}; position={position_lot}")

        if problems:
            status_text = "REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH"
            reason = "; ".join(problems)
        else:
            status_text = "REGISTRY_ACTIVE_MATCHED"
            reason = "active registry row matched current open position"

        base.update(position_fields(position))
        base.update({
            "ticket_match": "true",
            "symbol_match": bool_text(symbol_match),
            "direction_match": bool_text(direction_match),
            "lot_match": bool_text(lot_match),
            "strategy_detected_in_position": bool_text(strategy_detected),
            "reconcile_status": status_text,
            "reconcile_reason": reason,
        })
        rows.append(base)
    return rows


def reconcile_unregistered_positions(now: str, registry_df: pd.DataFrame, positions: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active_tickets = build_registry_active_ticket_set(registry_df)
    for position in positions:
        ticket = clean_int_text(position.get("ticket"))
        if ticket and ticket in active_tickets:
            continue
        row = {col: "" for col in RECONCILE_COLUMNS}
        row.update({
            "reconcile_time_utc": now,
            "row_type": "POSITION_WITHOUT_ACTIVE_REGISTRY",
            "position_source": source,
            "position_ticket": ticket,
            "position_symbol": clean_str(position.get("symbol")),
            "position_direction": mt5_position_direction(position),
            "position_lot": position_volume(position),
            "position_magic": clean_int_text(position.get("magic")),
            "position_comment": clean_str(position.get("comment")),
            "position_external_id": clean_str(position.get("external_id")),
            "ticket_match": "false",
            "symbol_match": "",
            "direction_match": "",
            "lot_match": "",
            "strategy_detected_in_position": "",
            "reconcile_status": "POSITION_WITHOUT_ACTIVE_REGISTRY",
            "reconcile_reason": f"current position ticket is not present in ACTIVE registry rows: ticket={ticket}",
        })
        rows.append(row)
    return rows


def base_reconcile_row(now: str, source: str, idx: int, reg: pd.Series) -> dict[str, Any]:
    row = {col: "" for col in RECONCILE_COLUMNS}
    row.update({
        "reconcile_time_utc": now,
        "row_type": "ACTIVE_REGISTRY_ROW",
        "position_source": source,
        "registry_row_index": int(idx),
        "registry_position_status": clean_str(reg.get("position_status")),
        "registry_position_ticket": clean_int_text(reg.get("position_ticket")),
        "registry_broker_symbol": clean_str(reg.get("broker_symbol")),
        "registry_direction": clean_str(reg.get("direction")),
        "registry_lot": clean_float(reg.get("lot")) if clean_float(reg.get("lot")) is not None else "",
        "registry_strategy_key": clean_str(reg.get("strategy_key")),
        "registry_strategy_alias": clean_str(reg.get("strategy_alias")),
        "registry_signal_key": clean_str(reg.get("signal_key")),
        "registry_order_key": clean_str(reg.get("order_key")),
    })
    return row


def position_fields(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_ticket": clean_int_text(position.get("ticket")),
        "position_symbol": clean_str(position.get("symbol")),
        "position_direction": mt5_position_direction(position),
        "position_lot": position_volume(position),
        "position_magic": clean_int_text(position.get("magic")),
        "position_comment": clean_str(position.get("comment")),
        "position_external_id": clean_str(position.get("external_id")),
    }


def main() -> int:
    args = parse_args()
    Path(windows_long_path(args.out_dir)).mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / RECONCILE_CSV_NAME
    output_json = args.output_json if args.output_json is not None else args.out_dir / SUMMARY_JSON_NAME
    positions_snapshot_csv = args.positions_snapshot_csv if args.positions_snapshot_csv is not None else args.out_dir / POSITIONS_SNAPSHOT_CSV_NAME
    now = utc_now_text()

    registry_df, registry_status, registry_exists = read_registry(args.registry_csv)
    positions_ok, positions_rc, source, position_report, positions = get_positions(args)
    write_csv(positions_snapshot_dataframe(positions, now, source), positions_snapshot_csv)

    if not positions_ok:
        out = pd.DataFrame(columns=RECONCILE_COLUMNS)
        write_csv(out, output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "reconcile_ok": False,
            "reason": position_report.get("fatal_error", "POSITION_READ_FAILED"),
            "registry_csv": str(args.registry_csv),
            "registry_status": registry_status,
            "registry_exists": bool(registry_exists),
            "positions_source": source,
            "positions_csv": str(args.positions_csv) if args.positions_csv else "",
            "output_csv": str(output_csv),
            "output_json": str(output_json),
            "positions_snapshot_csv": str(positions_snapshot_csv),
            "registry_rows": int(len(registry_df)),
            "positions_rows": 0,
            "reconcile_rows": 0,
            "position_report": position_report,
        }
        write_json(output_json, summary)
        print("run_gold_multi_strategy_position_registry_reconcile_dry_run")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        if source == "MT5_REAL" and mt5 is not None:
            mt5.shutdown()
        return positions_rc

    rows: list[dict[str, Any]] = []
    rows.extend(reconcile_registry_rows(now, registry_df, positions, source, args.lot_tolerance))
    rows.extend(reconcile_unregistered_positions(now, registry_df, positions, source))
    out = pd.DataFrame([{col: row.get(col, "") for col in RECONCILE_COLUMNS} for row in rows], columns=RECONCILE_COLUMNS)
    write_csv(out, output_csv)

    active_registry_count = int(active_registry_mask(registry_df).sum()) if not registry_df.empty else 0
    status_counts = out["reconcile_status"].value_counts().to_dict() if not out.empty else {}
    summary = {
        "schema_version": SCHEMA_VERSION,
        "reconcile_ok": True,
        "reason": "RECONCILE_EVALUATED",
        "registry_csv": str(args.registry_csv),
        "registry_status": registry_status,
        "registry_exists": bool(registry_exists),
        "positions_source": source,
        "positions_csv": str(args.positions_csv) if args.positions_csv else "",
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "positions_snapshot_csv": str(positions_snapshot_csv),
        "registry_rows": int(len(registry_df)),
        "active_registry_rows": active_registry_count,
        "positions_rows": int(len(positions)),
        "reconcile_rows": int(len(out)),
        "matched_active_registry_rows": int((out["reconcile_status"] == "REGISTRY_ACTIVE_MATCHED").sum()) if not out.empty else 0,
        "matched_with_mismatch_rows": int((out["reconcile_status"] == "REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH").sum()) if not out.empty else 0,
        "missing_position_rows": int((out["reconcile_status"] == "REGISTRY_ACTIVE_MISSING_POSITION").sum()) if not out.empty else 0,
        "unregistered_position_rows": int((out["reconcile_status"] == "POSITION_WITHOUT_ACTIVE_REGISTRY").sum()) if not out.empty else 0,
        "status_counts": status_counts,
        "position_report": position_report,
        "safety": {
            "order_send_called_count": 0,
            "order_check_called_count": 0,
            "registry_mutated": False,
            "ledger_mutated": False,
            "trigger_state_mutated": False,
        },
        "records": out.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("run_gold_multi_strategy_position_registry_reconcile_dry_run")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if not out.empty:
        show_cols = [
            "row_type",
            "registry_position_ticket",
            "registry_strategy_key",
            "position_ticket",
            "position_symbol",
            "position_direction",
            "position_lot",
            "ticket_match",
            "symbol_match",
            "direction_match",
            "lot_match",
            "strategy_detected_in_position",
            "reconcile_status",
            "reconcile_reason",
        ]
        print(out[show_cols].to_string(index=False))
    else:
        print("[INFO] no active registry rows and no current positions")
    print(f"output_csv: {output_csv}")
    print(f"output_json: {output_json}")
    print(f"positions_snapshot_csv: {positions_snapshot_csv}")
    print("done")

    if source == "MT5_REAL" and mt5 is not None:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
