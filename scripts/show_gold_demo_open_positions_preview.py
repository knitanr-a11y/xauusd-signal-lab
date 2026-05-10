#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Read-only preview of current GOLD demo open positions.

This script only reads MT5 account/symbol/position information.

Safety:
- Does NOT call order_send.
- Does NOT close positions.
- Does NOT write production position_registry.csv.
- Does NOT modify Mochipoyo ledgers or trigger-state files.
- Requires expected-login by default.
- Requires demo-account guard by default.

Purpose:
- Quickly inspect currently carried GOLD positions while GOLD market is closed.
- Produce CSV/JSON outputs that can be used for manual review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(exc)
else:
    MT5_IMPORT_ERROR = ""

DEFAULT_OUT_DIR = Path("data/r/gold_demo_open_positions_preview")
SUMMARY_FILENAME = "latest_gold_demo_open_positions_preview_result.json"

POSITIONS_COLUMNS = [
    "position_ticket",
    "time",
    "time_msc",
    "symbol",
    "type",
    "direction",
    "volume",
    "price_open",
    "price_current",
    "sl",
    "tp",
    "profit",
    "swap",
    "magic",
    "comment",
    "identifier",
    "reason",
]


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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        d = obj._asdict()
    elif isinstance(obj, dict):
        d = obj
    else:
        d = {"value": str(obj)}
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            json.dumps(v)
            out[k] = v
        except TypeError:
            out[k] = str(v)
    return out


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def parse_symbol_candidates(text: str) -> list[str]:
    out: list[str] = []
    for part in str(text).replace(";", ",").split(","):
        s = part.strip()
        if s and s not in out:
            out.append(s)
    return out


def mt5_initialize_or_raise(terminal_path: str | None, portable: bool) -> None:
    if mt5 is None:
        raise RuntimeError(f"MetaTrader5 import failed: {MT5_IMPORT_ERROR}")
    if terminal_path:
        ok = mt5.initialize(path=terminal_path, portable=portable)
    else:
        ok = mt5.initialize()
    if not ok:
        raise RuntimeError(f"mt5.initialize failed: last_error={mt5.last_error()}")


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def direction_from_position_type(pos_type: Any) -> str:
    t = safe_int(pos_type, -1)
    if mt5 is not None:
        if t == mt5.POSITION_TYPE_BUY:
            return "BUY"
        if t == mt5.POSITION_TYPE_SELL:
            return "SELL"
    if t == 0:
        return "BUY"
    if t == 1:
        return "SELL"
    return f"UNKNOWN_{t}"


def build_position_row(pos: Any) -> dict[str, Any]:
    d = asdict_obj(pos)
    return {
        "position_ticket": d.get("ticket", ""),
        "time": d.get("time", ""),
        "time_msc": d.get("time_msc", ""),
        "symbol": d.get("symbol", ""),
        "type": d.get("type", ""),
        "direction": direction_from_position_type(d.get("type")),
        "volume": d.get("volume", ""),
        "price_open": d.get("price_open", ""),
        "price_current": d.get("price_current", ""),
        "sl": d.get("sl", ""),
        "tp": d.get("tp", ""),
        "profit": d.get("profit", ""),
        "swap": d.get("swap", ""),
        "magic": d.get("magic", ""),
        "comment": d.get("comment", ""),
        "identifier": d.get("identifier", ""),
        "reason": d.get("reason", ""),
    }


def get_positions_for_candidates(candidates: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    assert mt5 is not None
    tried: list[str] = []
    rows: list[dict[str, Any]] = []
    seen_tickets: set[str] = set()
    for symbol in candidates:
        if not symbol:
            continue
        tried.append(symbol)
        raw = mt5.positions_get(symbol=symbol)
        if raw is None:
            raw = []
        for pos in raw:
            row = build_position_row(pos)
            ticket = str(row.get("position_ticket", ""))
            if ticket and ticket not in seen_tickets:
                seen_tickets.add(ticket)
                rows.append(row)
    return rows, tried


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read-only preview of current GOLD demo open positions.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol-candidates", default="GOLD#,GOLD,XAUUSD#,XAUUSD")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    positions_csv = args.out_dir / "gold_demo_open_positions_preview.csv"
    summary_json = args.out_dir / SUMMARY_FILENAME
    candidates = parse_symbol_candidates(args.symbol_candidates)

    print("=" * 80, flush=True)
    print("GOLD demo open positions READ-ONLY preview", flush=True)
    print("NO order_send / NO close / NO production registry write", flush=True)
    print(f"symbol_candidates={candidates}", flush=True)
    print(f"expected_login={args.expected_login} require_demo_account={args.require_demo_account}", flush=True)
    print("=" * 80, flush=True)

    init_ok = False
    account_info: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    tried: list[str] = []
    try:
        mt5_initialize_or_raise(args.terminal_path, bool(args.portable))
        init_ok = True
        assert mt5 is not None
        account_raw = mt5.account_info()
        account_info = asdict_obj(account_raw)
        if not account_info:
            raise RuntimeError(f"mt5.account_info returned empty: last_error={mt5.last_error()}")
        actual_login = safe_int(account_info.get("login"), 0)
        if int(args.expected_login) != actual_login:
            raise RuntimeError(f"expected-login mismatch: expected={args.expected_login}; actual={actual_login}")
        if args.require_demo_account and not account_looks_demo(account_info):
            raise RuntimeError(f"require-demo-account guard failed: account_info={account_info}")
        rows, tried = get_positions_for_candidates(candidates)
    finally:
        if init_ok and mt5 is not None:
            mt5.shutdown()

    write_csv(positions_csv, rows, POSITIONS_COLUMNS)
    total_volume = round(sum(safe_float(r.get("volume"), 0.0) for r in rows), 8)
    total_profit = round(sum(safe_float(r.get("profit"), 0.0) for r in rows), 2)
    directions: dict[str, int] = {}
    for row in rows:
        d = str(row.get("direction", ""))
        directions[d] = directions.get(d, 0) + 1

    summary = {
        "schema_version": "gold_demo_open_positions_preview_v1_read_only",
        "cycle_time_utc": utc_now_text(),
        "preview_ok": True,
        "reason": "GOLD_DEMO_OPEN_POSITIONS_PREVIEW_PASS",
        "mode": "READ_ONLY_NO_ORDER_SEND_NO_CLOSE",
        "symbol_candidates": candidates,
        "symbols_tried": tried,
        "account_info": account_info,
        "positions_count": len(rows),
        "total_volume": total_volume,
        "total_profit": total_profit,
        "directions": directions,
        "safety": {
            "order_send_called_count": 0,
            "close_executed_count": 0,
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {
            "positions_csv": str(positions_csv),
            "summary_json": str(summary_json),
        },
        "positions": rows,
    }
    write_json(summary_json, summary)

    print(json.dumps({
        "preview_ok": True,
        "reason": summary["reason"],
        "positions_count": len(rows),
        "total_volume": total_volume,
        "total_profit": total_profit,
        "directions": directions,
        "order_send_called_count": 0,
        "close_executed_count": 0,
        "positions_csv": str(positions_csv),
        "summary_json": str(summary_json),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
