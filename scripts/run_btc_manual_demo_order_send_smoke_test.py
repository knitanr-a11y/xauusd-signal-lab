#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC manual demo order_send smoke test runner.

Default mode is NO-SEND.

Purpose:
- Test the MT5 sender/order_check path with a BTC manual fixture payload while
  GOLD market is closed.
- Keep this completely separate from GOLD multi-strategy signals.
- Keep this separate from existing Mochipoyo production/demo BATs and ledgers.

Safety defaults:
- Does not pass --send to send_mt5_order_from_payload.py by default.
- Requires expected-login by default.
- Requires demo-account guard by default.
- max-orders=1.
- position-policy=block_any.
- Uses isolated output directory and isolated order ledger.
- Does not write production position_registry.csv.

What this script does:
1. Initialize MT5.
2. Resolve/select a BTC broker symbol.
3. Read symbol_info and symbol_info_tick.
4. Build one conservative BTC fixture payload using current bid/ask.
5. Shutdown MT5 in this wrapper process.
6. Call scripts/send_mt5_order_from_payload.py WITHOUT --send.
7. Validate sender report says order_send_called_count=0 and sent_rows=0.

Important:
- This is NOT a strategy signal.
- This is NOT BTC strategy integration.
- This is only a manual MT5 order path smoke test.
- A send-once mode must be implemented separately and should require explicit
  user approval.
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
DEFAULT_OUT_DIR = Path("data/r/btc_manual_demo_order_send_smoke_test")
SUMMARY_FILENAME = "latest_btc_manual_demo_order_send_smoke_test_result.json"

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

SUMMARY_PRINT_KEYS = [
    "cycle_ok",
    "reason",
    "mode",
    "symbol",
    "direction",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "sender_returncode",
    "sender_rows_out",
    "sender_dry_run_check_ok_rows",
    "sender_sent_rows",
    "sender_error_rows",
    "sender_order_send_called_count",
    "summary_json",
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


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or default)
    except Exception:
        try:
            return int(float(obj.get(key, default)))
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


def resolve_btc_symbol(candidates: list[str]) -> tuple[str, list[str]]:
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
    all_symbols = mt5.symbols_get()
    btc_symbols: list[str] = []
    if all_symbols is not None:
        for item in all_symbols:
            name = str(getattr(item, "name", ""))
            if "BTC" in name.upper() and name not in btc_symbols:
                btc_symbols.append(name)
    for symbol in btc_symbols:
        if symbol not in tried:
            tried.append(symbol)
        info = mt5.symbol_info(symbol)
        if info is not None:
            if not info.visible:
                mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            if info is not None and info.visible:
                return symbol, tried
    raise RuntimeError(f"No selectable BTC symbol found. tried={tried}; discovered_btc_symbols={btc_symbols[:50]}")


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def normalize_lot(requested_lot: float, info: dict[str, Any]) -> float:
    volume_min = safe_float(info.get("volume_min"), requested_lot)
    volume_max = safe_float(info.get("volume_max"), requested_lot)
    volume_step = safe_float(info.get("volume_step"), 0.0)
    lot = max(float(requested_lot), volume_min)
    if volume_step > 0:
        steps = math.ceil((lot - volume_min) / volume_step - 1e-12)
        lot = volume_min + max(0, steps) * volume_step
    lot = min(lot, volume_max)
    digits = 8
    return round(lot, digits)


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


def build_payload(args: argparse.Namespace, symbol: str, account_info: dict[str, Any], symbol_info: dict[str, Any], tick: dict[str, Any]) -> dict[str, Any]:
    direction = str(args.direction).upper()
    digits = safe_int(symbol_info, "digits", 2)
    point = safe_float(symbol_info.get("point"), 0.01)
    stops_level = safe_int(symbol_info, "trade_stops_level", 0)
    bid = safe_float(tick.get("bid"), 0.0)
    ask = safe_float(tick.get("ask"), 0.0)
    if bid <= 0 or ask <= 0:
        raise RuntimeError(f"invalid BTC tick bid/ask: bid={bid}; ask={ask}")
    lot = normalize_lot(float(args.fixed_lot), symbol_info)
    entry, sl, tp = build_safe_prices(direction, bid, ask, point, stops_level, digits, float(args.min_distance_usd))
    stamp = utc_stamp()
    key_base = f"BTC_MANUAL_SMOKE_{symbol}_{direction}_{stamp}"
    return {
        "payload_key": f"{key_base}_PAYLOAD",
        "order_key": f"{key_base}_ORDER",
        "signal_key": f"{key_base}_SIGNAL",
        "broker_symbol": symbol,
        "symbol": symbol,
        "direction": direction,
        "lot": lot,
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "magic_number": int(args.magic),
        "strategy_key": "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST",
        "strategy_alias": "BTC_MANUAL_SMOKE",
        "strategy_id": "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND",
        "condition_id": "BTC_MANUAL_FIXTURE_ORDER_CHECK_ONLY",
        "router_strategy_slot": "BTC_MANUAL_SMOKE_TEST",
        "router_strategy_id": "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND",
        "candidate_rank": 1,
        "source": "manual_fixture_no_strategy_signal",
        "fixture_note": "BTC manual smoke test payload; not a strategy signal; default no-send",
    }


def build_sender_cmd(args: argparse.Namespace, paths: dict[str, Path], symbol: str) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(paths["payload_csv"]),
        "--order-ledger-csv", str(paths["order_ledger_csv"]),
        "--out-dir", str(paths["sender_out_dir"]),
        "--symbol", symbol,
        "--max-orders", "1",
        "--deviation", str(args.deviation),
        "--position-policy", "block_any",
        "--max-symbol-positions", "1",
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
    # Intentionally no --send in this script.
    return cmd


def run_sender(cmd: list[str]) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print("[STEP] sender no-send/order_check smoke test", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] sender returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC manual demo order_send smoke test. Default is no-send/order_check only.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="", help="Explicit BTC broker symbol. If omitted, --symbol-candidates and BTC symbol discovery are used.")
    p.add_argument("--symbol-candidates", default="BTCUSD#,BTCUSD,BTCUSD.,BTCUSDm,BTCUSDmicro")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="BUY")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--min-distance-usd", type=float, default=100.0, help="Minimum SL/TP distance from current BTC price.")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--magic", type=int, default=26050602)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    mkdir_path(args.out_dir)
    paths = {
        "payload_csv": args.out_dir / "payload" / "btc_manual_order_payloads.csv",
        "sender_out_dir": args.out_dir / "sender_no_send",
        "order_ledger_csv": args.out_dir / "btc_manual_demo_order_ledger.csv",
        "registry_preview_csv": args.out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": args.out_dir / "registry_preview" / "registry_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
    }

    print("=" * 80, flush=True)
    print("BTC manual demo order_send smoke test - NO SEND", flush=True)
    print("This is not a strategy signal. It validates BTC payload -> sender dry-run/order_check path.", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"expected_login={args.expected_login} require_demo_account={args.require_demo_account}", flush=True)
    print("=" * 80, flush=True)

    resolved_symbol = ""
    tried_symbols: list[str] = []
    account_info: dict[str, Any] = {}
    symbol_info: dict[str, Any] = {}
    tick: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    init_ok = False

    try:
        mt5_initialize_or_raise(args.terminal_path, bool(args.portable))
        init_ok = True
        assert mt5 is not None
        account_raw = mt5.account_info()
        account_info = asdict_obj(account_raw)
        if not account_info:
            raise RuntimeError(f"mt5.account_info returned empty: last_error={mt5.last_error()}")
        actual_login = int(account_info.get("login", 0) or 0)
        if int(args.expected_login) != actual_login:
            raise RuntimeError(f"expected-login mismatch: expected={args.expected_login}; actual={actual_login}")
        if args.require_demo_account and not account_looks_demo(account_info):
            raise RuntimeError(f"require-demo-account guard failed: account_info={account_info}")

        candidates = [args.symbol.strip()] if args.symbol.strip() else parse_symbol_candidates(args.symbol_candidates)
        resolved_symbol, tried_symbols = resolve_btc_symbol(candidates)
        info_raw = mt5.symbol_info(resolved_symbol)
        tick_raw = mt5.symbol_info_tick(resolved_symbol)
        symbol_info = asdict_obj(info_raw)
        tick = asdict_obj(tick_raw)
        if not symbol_info:
            raise RuntimeError(f"symbol_info empty for {resolved_symbol}")
        if not tick:
            raise RuntimeError(f"symbol_info_tick empty for {resolved_symbol}")
        payload = build_payload(args, resolved_symbol, account_info, symbol_info, tick)
        write_csv(paths["payload_csv"], [payload], PAYLOAD_COLUMNS)
    finally:
        if init_ok and mt5 is not None:
            mt5.shutdown()

    sender_rc, sender_seconds = run_sender(build_sender_cmd(args, paths, resolved_symbol))
    sender_report = read_json_or_empty(paths["sender_out_dir"] / "mt5_order_send_report.json")
    rows_out = safe_int(sender_report, "rows_out", 0)
    dry_run_check_ok_rows = safe_int(sender_report, "dry_run_check_ok_rows", 0)
    sent_rows = safe_int(sender_report, "sent_rows", 0)
    error_rows = safe_int(sender_report, "error_rows", 0)
    order_send_called_count = safe_int(sender_report, "order_send_called_count", 0)

    # no-send mode must never call order_send. order_check may fail due to broker
    # constraints, existing BTC position, or market condition; in that case the
    # script returns non-zero and the report explains why.
    cycle_ok = bool(sender_rc == 0 and rows_out == 1 and order_send_called_count == 0 and sent_rows == 0 and dry_run_check_ok_rows >= 1)
    reason = "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS" if cycle_ok else "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_FAILED"

    summary = {
        "schema_version": "btc_manual_demo_order_send_smoke_test_no_send_v1",
        "cycle_start_utc": utc_now_text(),
        "cycle_ok": cycle_ok,
        "reason": reason,
        "mode": "NO_SEND_ORDER_CHECK_ONLY",
        "symbol": resolved_symbol,
        "symbol_candidates_tried": tried_symbols,
        "direction": payload.get("direction", ""),
        "lot": payload.get("lot", 0),
        "entry_price_reference": payload.get("entry_price_reference", 0),
        "sl_price": payload.get("sl_price", 0),
        "tp_price": payload.get("tp_price", 0),
        "account_info": account_info,
        "symbol_info_subset": {
            "name": symbol_info.get("name"),
            "visible": symbol_info.get("visible"),
            "digits": symbol_info.get("digits"),
            "point": symbol_info.get("point"),
            "trade_stops_level": symbol_info.get("trade_stops_level"),
            "volume_min": symbol_info.get("volume_min"),
            "volume_max": symbol_info.get("volume_max"),
            "volume_step": symbol_info.get("volume_step"),
            "trade_mode": symbol_info.get("trade_mode"),
        },
        "tick": tick,
        "sender_returncode": sender_rc,
        "sender_seconds": sender_seconds,
        "sender_rows_out": rows_out,
        "sender_dry_run_check_ok_rows": dry_run_check_ok_rows,
        "sender_sent_rows": sent_rows,
        "sender_error_rows": error_rows,
        "sender_order_send_called_count": order_send_called_count,
        "safety": {
            "send_flag_passed": False,
            "order_send_called_count": order_send_called_count,
            "sent_rows": sent_rows,
            "production_registry_mutated": False,
            "gold_strategy_signal_used": False,
            "btc_strategy_integration_used": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "payload": payload,
        "sender_report": sender_report,
        "timing": {
            "total_seconds": round(time.perf_counter() - started_perf, 3),
        },
    }
    write_json(paths["summary_json"], summary)

    print("=" * 80, flush=True)
    print("BTC manual demo order_send smoke test summary - NO SEND", flush=True)
    printable = {k: summary.get(k) for k in SUMMARY_PRINT_KEYS}
    printable["safety"] = summary["safety"]
    printable["paths"] = summary["paths"]
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
