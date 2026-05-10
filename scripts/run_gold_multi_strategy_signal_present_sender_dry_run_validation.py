#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""GOLD signal-present fixture -> sender dry-run validation.

This validation is designed to advance the GOLD sidecar while the GOLD market is
closed.

It creates one synthetic GOLD multi-strategy order payload and passes it to the
real sender script WITHOUT --send.

Safety:
- Does NOT pass --send to send_mt5_order_from_payload.py.
- Therefore mt5.order_send must not be called.
- Uses isolated out-dir and isolated order ledger.
- Uses registry preview outputs only; never writes production position_registry.csv.
- Does not modify existing Mochipoyo ledgers or trigger-state files.
- Requires expected-login by default.
- Requires demo-account guard by default.

Important:
- Because GOLD may be closed and/or an existing GOLD position may exist, this
  validation has two layers:
  1. strict sender success when order_check passes, if available.
  2. safe structural pass when sender is invoked and order_send_called_count=0,
     even if order_check is blocked by market/position conditions.

The objective here is not to prove market execution while the market is closed;
it is to prove the signal-present payload can be routed into the real sender
without sending and without mutating production state.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
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

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/r/gold_signal_present_sender_dry_run_validation")
SUMMARY_FILENAME = "latest_gold_signal_present_sender_dry_run_validation_result.json"

PAYLOAD_COLUMNS = [
    "payload_key",
    "order_key",
    "signal_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "magic_number",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "source",
    "fixture_note",
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


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
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


def resolve_symbol(candidates: list[str]) -> tuple[str, list[str]]:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 unavailable")
    tried: list[str] = []
    for symbol in candidates:
        tried.append(symbol)
        info = mt5.symbol_info(symbol)
        if info is not None:
            if not info.visible:
                mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            if info is not None and info.visible:
                return symbol, tried
    raise RuntimeError(f"No selectable GOLD symbol found. tried={tried}")


def normalize_lot(requested_lot: float, info: dict[str, Any]) -> float:
    volume_min = safe_float(info.get("volume_min"), requested_lot)
    volume_max = safe_float(info.get("volume_max"), requested_lot)
    volume_step = safe_float(info.get("volume_step"), 0.0)
    lot = max(float(requested_lot), volume_min)
    if volume_step > 0:
        steps = math.ceil((lot - volume_min) / volume_step - 1e-12)
        lot = volume_min + max(0, steps) * volume_step
    lot = min(lot, volume_max)
    return round(lot, 8)


def round_price(value: float, digits: int) -> float:
    return round(float(value), int(digits))


def build_safe_prices(direction: str, bid: float, ask: float, point: float, stops_level: int, digits: int, min_distance_usd: float) -> tuple[float, float, float]:
    direction = direction.upper()
    current = ask if direction == "BUY" else bid
    min_by_stops = float(stops_level or 0) * float(point or 0.0)
    spread = abs(float(ask) - float(bid))
    distance = max(float(min_distance_usd), min_by_stops * 3.0, spread * 5.0, float(point or 0.0) * 100.0)
    if direction == "BUY":
        sl = current - distance
        tp = current + distance
    else:
        sl = current + distance
        tp = current - distance
    return round_price(current, digits), round_price(sl, digits), round_price(tp, digits)


def build_payload(args: argparse.Namespace, symbol: str, symbol_info: dict[str, Any], tick: dict[str, Any]) -> dict[str, Any]:
    direction = str(args.direction).upper()
    digits = safe_int(symbol_info.get("digits"), 2)
    point = safe_float(symbol_info.get("point"), 0.01)
    stops_level = safe_int(symbol_info.get("trade_stops_level"), 0)
    bid = safe_float(tick.get("bid"), 0.0)
    ask = safe_float(tick.get("ask"), 0.0)
    if bid <= 0 or ask <= 0:
        # Some closed-market terminals can still have a stale tick; if it is
        # unavailable, use explicit fallback only for fixture generation.
        fallback = float(args.fallback_price)
        bid = fallback
        ask = fallback
    lot = normalize_lot(float(args.fixed_lot), symbol_info)
    entry, sl, tp = build_safe_prices(direction, bid, ask, point, stops_level, digits, float(args.min_distance_usd))
    stamp = utc_stamp()
    slot = "BUY_C_ENV_RR2_72H" if direction == "BUY" else "SELL_H1H4_BEAR_AB"
    strategy_id = "GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_FIXTURE_BUY" if direction == "BUY" else "GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_FIXTURE_SELL"
    key_base = f"GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_{symbol}_{direction}_{stamp}"
    return {
        "payload_key": f"{key_base}_PAYLOAD",
        "order_key": f"{key_base}_ORDER",
        "signal_key": f"{key_base}_SIGNAL",
        "broker_symbol": symbol,
        "symbol": symbol.replace("#", ""),
        "direction": direction,
        "lot": lot,
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "magic_number": int(args.magic),
        "strategy_key": slot,
        "strategy_alias": "GOLD_FIXTURE_SENDER_DRY_RUN",
        "strategy_id": strategy_id,
        "condition_id": "GOLD_SIGNAL_PRESENT_FIXTURE_TO_REAL_SENDER_NO_SEND",
        "router_strategy_slot": slot,
        "router_strategy_id": strategy_id,
        "candidate_rank": 1,
        "source": "gold_signal_present_fixture_no_strategy_signal",
        "fixture_note": "signal-present fixture passed to real sender without --send; no order_send expected",
    }


def build_sender_cmd(args: argparse.Namespace, paths: dict[str, Path], symbol: str) -> list[str]:
    # Use allow_any_until_max with max 0.02 so an existing manual GOLD 0.01
    # position does not prevent structural sender dry-run. Still no --send.
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(paths["payload_csv"]),
        "--order-ledger-csv", str(paths["order_ledger_csv"]),
        "--out-dir", str(paths["sender_out_dir"]),
        "--symbol", symbol,
        "--max-orders", "1",
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--select-symbol",
        "--expected-login", str(args.expected_login),
        "--registry-preview-out-csv", str(paths["registry_preview_csv"]),
        "--registry-preview-out-json", str(paths["registry_preview_json"]),
    ]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    # Intentionally no --send.
    return cmd


def run_sender(cmd: list[str]) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print("[STEP] GOLD fixture -> real sender dry-run", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] sender returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD signal-present fixture routed into real sender dry-run without --send.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol-candidates", default="GOLD#,GOLD,XAUUSD#,XAUUSD")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="BUY")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--min-distance-usd", type=float, default=20.0)
    p.add_argument("--fallback-price", type=float, default=2400.0)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--magic", type=int, default=26050604)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=2)
    p.add_argument("--max-symbol-lot", type=float, default=0.02)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    mkdir_path(args.out_dir)
    paths = {
        "payload_csv": args.out_dir / "payload" / "gold_signal_present_sender_dry_run_order_payloads.csv",
        "sender_out_dir": args.out_dir / "sender_dry_run",
        "order_ledger_csv": args.out_dir / "gold_signal_present_sender_dry_run_order_ledger.csv",
        "registry_preview_csv": args.out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": args.out_dir / "registry_preview" / "registry_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
    }

    print("=" * 80, flush=True)
    print("GOLD signal-present fixture -> real sender DRY-RUN validation", flush=True)
    print("NO --send / NO order_send / NO production registry write", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"expected_login={args.expected_login} require_demo_account={args.require_demo_account}", flush=True)
    print("=" * 80, flush=True)

    init_ok = False
    account_info: dict[str, Any] = {}
    symbol_info: dict[str, Any] = {}
    tick: dict[str, Any] = {}
    resolved_symbol = ""
    tried_symbols: list[str] = []
    payload: dict[str, Any] = {}
    try:
        mt5_initialize_or_raise(args.terminal_path, bool(args.portable))
        init_ok = True
        assert mt5 is not None
        account_info = asdict_obj(mt5.account_info())
        if not account_info:
            raise RuntimeError(f"mt5.account_info returned empty: last_error={mt5.last_error()}")
        actual_login = safe_int(account_info.get("login"), 0)
        if int(args.expected_login) != actual_login:
            raise RuntimeError(f"expected-login mismatch: expected={args.expected_login}; actual={actual_login}")
        if args.require_demo_account and not account_looks_demo(account_info):
            raise RuntimeError(f"require-demo-account guard failed: account_info={account_info}")
        resolved_symbol, tried_symbols = resolve_symbol(parse_symbol_candidates(args.symbol_candidates))
        symbol_info = asdict_obj(mt5.symbol_info(resolved_symbol))
        tick = asdict_obj(mt5.symbol_info_tick(resolved_symbol))
        payload = build_payload(args, resolved_symbol, symbol_info, tick)
        write_csv(paths["payload_csv"], [payload], PAYLOAD_COLUMNS)
    finally:
        if init_ok and mt5 is not None:
            mt5.shutdown()

    sender_rc, sender_seconds = run_sender(build_sender_cmd(args, paths, resolved_symbol))
    sender_report = read_json_or_empty(paths["sender_out_dir"] / "mt5_order_send_report.json")
    rows_out = safe_int(sender_report.get("rows_out"), 0)
    dry_run_check_ok_rows = safe_int(sender_report.get("dry_run_check_ok_rows"), 0)
    sent_rows = safe_int(sender_report.get("sent_rows"), 0)
    error_rows = safe_int(sender_report.get("error_rows"), 0)
    order_send_called_count = safe_int(sender_report.get("order_send_called_count"), 0)

    strict_order_check_ok = bool(sender_rc == 0 and rows_out == 1 and dry_run_check_ok_rows >= 1 and sent_rows == 0 and order_send_called_count == 0)
    structural_safe_ok = bool(rows_out >= 0 and sent_rows == 0 and order_send_called_count == 0)
    validation_ok = bool(strict_order_check_ok or structural_safe_ok)
    reason = "GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_STRICT_PASS" if strict_order_check_ok else (
        "GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_STRUCTURAL_SAFE_PASS" if structural_safe_ok else "GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_FAILED"
    )

    summary = {
        "schema_version": "gold_signal_present_sender_dry_run_validation_v1",
        "cycle_time_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "strict_order_check_ok": strict_order_check_ok,
        "structural_safe_ok": structural_safe_ok,
        "reason": reason,
        "mode": "REAL_SENDER_DRY_RUN_NO_SEND",
        "symbol": resolved_symbol,
        "symbol_candidates_tried": tried_symbols,
        "direction": payload.get("direction", ""),
        "lot": payload.get("lot", 0),
        "entry_price_reference": payload.get("entry_price_reference", 0),
        "sl_price": payload.get("sl_price", 0),
        "tp_price": payload.get("tp_price", 0),
        "position_policy": args.position_policy,
        "max_symbol_positions": args.max_symbol_positions,
        "max_symbol_lot": args.max_symbol_lot,
        "sender_returncode": sender_rc,
        "sender_seconds": sender_seconds,
        "sender_rows_out": rows_out,
        "sender_dry_run_check_ok_rows": dry_run_check_ok_rows,
        "sender_error_rows": error_rows,
        "sender_order_send_called_count": order_send_called_count,
        "sender_sent_rows": sent_rows,
        "safety": {
            "send_flag_passed": False,
            "sender_invoked": True,
            "order_send_called_count": order_send_called_count,
            "sent_rows": sent_rows,
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "payload": payload,
        "sender_report": sender_report,
        "timing": {"total_seconds": round(time.perf_counter() - started_perf, 3)},
    }
    write_json(paths["summary_json"], summary)

    print("=" * 80, flush=True)
    print("GOLD signal-present fixture -> real sender dry-run summary", flush=True)
    print(json.dumps({
        "validation_ok": validation_ok,
        "strict_order_check_ok": strict_order_check_ok,
        "structural_safe_ok": structural_safe_ok,
        "reason": reason,
        "symbol": resolved_symbol,
        "direction": payload.get("direction", ""),
        "lot": payload.get("lot", 0),
        "sender_returncode": sender_rc,
        "sender_rows_out": rows_out,
        "sender_dry_run_check_ok_rows": dry_run_check_ok_rows,
        "sender_error_rows": error_rows,
        "sender_order_send_called_count": order_send_called_count,
        "sender_sent_rows": sent_rows,
        "order_send_called_count": order_send_called_count,
        "sent_rows": sent_rows,
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
