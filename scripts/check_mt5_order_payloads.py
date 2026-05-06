#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Mochipoyo order payloads against MT5 without placing orders.

This script is intentionally safe:
- reads order_payloads.csv
- connects to MT5
- reads symbol_info and tick
- validates lot step/min/max
- validates BUY/SELL SL/TP direction
- optionally calls mt5.order_check for a pre-flight broker check
- NEVER calls mt5.order_send

Important:
- order_check may still depend on terminal/account trading permissions.
- If terminal Algo Trading is OFF, order_check can fail. That is not an order.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as e:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(e)
else:
    MT5_IMPORT_ERROR = ""


ORDER_TYPE_MAP = {
    "BUY": 0,   # mt5.ORDER_TYPE_BUY
    "SELL": 1,  # mt5.ORDER_TYPE_SELL
}


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


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding=encoding, newline="") as f:
        f.write(text)


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


def clean_float(x: Any) -> float | None:
    try:
        v = float(x)
    except Exception:
        return None
    if pd.isna(v) or not math.isfinite(v):
        return None
    return v


def clean_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    s = str(x)
    return s if s else default


def round_to_digits(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), int(digits))


def is_volume_step_ok(lot: float, volume_min: float, volume_max: float, volume_step: float, eps: float = 1e-9) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if lot < volume_min - eps:
        errors.append(f"lot below volume_min: lot={lot}; volume_min={volume_min}")
    if lot > volume_max + eps:
        errors.append(f"lot above volume_max: lot={lot}; volume_max={volume_max}")
    if volume_step <= 0:
        errors.append(f"invalid volume_step: {volume_step}")
    else:
        steps = round((lot - volume_min) / volume_step)
        normalized = volume_min + steps * volume_step
        if abs(normalized - lot) > max(eps, volume_step * 1e-6):
            errors.append(f"lot not aligned to volume_step: lot={lot}; volume_min={volume_min}; volume_step={volume_step}")
    return len(errors) == 0, errors


def validate_price_relation(direction: str, entry_reference: float | None, sl: float | None, tp: float | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    d = direction.upper()
    if d not in {"BUY", "SELL"}:
        errors.append(f"invalid direction: {direction}")
    if entry_reference is None:
        errors.append("missing entry_price_reference")
    if sl is None:
        errors.append("missing sl_price")
    if tp is None:
        errors.append("missing tp_price")
    if errors:
        return False, errors
    assert entry_reference is not None and sl is not None and tp is not None
    if d == "BUY":
        if not sl < entry_reference:
            errors.append(f"BUY requires sl < entry_reference: sl={sl}; entry={entry_reference}")
        if not tp > entry_reference:
            errors.append(f"BUY requires tp > entry_reference: tp={tp}; entry={entry_reference}")
    elif d == "SELL":
        if not sl > entry_reference:
            errors.append(f"SELL requires sl > entry_reference: sl={sl}; entry={entry_reference}")
        if not tp < entry_reference:
            errors.append(f"SELL requires tp < entry_reference: tp={tp}; entry={entry_reference}")
    return len(errors) == 0, errors


def validate_current_price_relation(direction: str, current_price: float | None, sl: float | None, tp: float | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    d = direction.upper()
    if current_price is None:
        errors.append("missing current execution price")
    if sl is None:
        errors.append("missing sl_price")
    if tp is None:
        errors.append("missing tp_price")
    if errors:
        return False, errors
    assert current_price is not None and sl is not None and tp is not None
    if d == "BUY":
        if not sl < current_price:
            errors.append(f"BUY requires sl < current ask: sl={sl}; ask={current_price}")
        if not tp > current_price:
            errors.append(f"BUY requires tp > current ask: tp={tp}; ask={current_price}")
    elif d == "SELL":
        if not sl > current_price:
            errors.append(f"SELL requires sl > current bid: sl={sl}; bid={current_price}")
        if not tp < current_price:
            errors.append(f"SELL requires tp < current bid: tp={tp}; bid={current_price}")
    else:
        errors.append(f"invalid direction for current price check: {direction}")
    return len(errors) == 0, errors


def check_stop_level(direction: str, current_price: float | None, sl: float | None, tp: float | None, point: float, stops_level: int) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if current_price is None or sl is None or tp is None:
        return False, ["missing price for stop-level validation"]
    min_distance = float(stops_level) * float(point)
    if min_distance <= 0:
        return True, []
    sl_dist = abs(float(current_price) - float(sl))
    tp_dist = abs(float(tp) - float(current_price))
    if sl_dist < min_distance:
        errors.append(f"SL distance below stops_level: distance={sl_dist}; min={min_distance}")
    if tp_dist < min_distance:
        errors.append(f"TP distance below stops_level: distance={tp_dist}; min={min_distance}")
    return len(errors) == 0, errors


def make_order_check_request(row: pd.Series, symbol: str, direction: str, lot: float, price: float, sl: float, tp: float, deviation: int, magic: int, comment: str) -> dict[str, Any]:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 is not imported")
    order_type = mt5.ORDER_TYPE_BUY if direction.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": float(price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate order payloads with MT5 order_check only; never order_send.")
    p.add_argument("--input-csv", required=True, help="order_payloads.csv from build_mochipoyo_order_payloads.py")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default=None, help="Optional broker symbol override, e.g. GOLD#")
    p.add_argument("--select-symbol", action="store_true")
    p.add_argument("--run-order-check", action="store_true", help="Call mt5.order_check. Still never sends orders.")
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "input_csv": args.input_csv,
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "initialize_ok": False,
        "run_order_check": bool(args.run_order_check),
        "order_send_called": False,
        "read_only": True,
    }

    if mt5 is None:
        write_text(out_dir / "mt5_order_payload_check_report.json", json.dumps(report, ensure_ascii=False, indent=2))
        print("check_mt5_order_payloads")
        print("ERROR: MetaTrader5 import failed")
        print(MT5_IMPORT_ERROR)
        return 2

    df = read_csv(args.input_csv)
    rows: list[dict[str, Any]] = []
    initialized = False
    try:
        init_kwargs: dict[str, Any] = {}
        if args.terminal_path:
            init_kwargs["path"] = args.terminal_path
        if args.portable:
            init_kwargs["portable"] = True
        initialized = bool(mt5.initialize(**init_kwargs))
        report["initialize_ok"] = initialized
        report["last_error_after_initialize"] = mt5.last_error()
        if not initialized:
            write_text(out_dir / "mt5_order_payload_check_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))
            print("check_mt5_order_payloads")
            print("ERROR: mt5.initialize failed")
            print(f"last_error: {report['last_error_after_initialize']}")
            return 3

        terminal_info = asdict_obj(mt5.terminal_info())
        account_info = asdict_obj(mt5.account_info())
        report["terminal_info"] = terminal_info
        report["account_info"] = account_info

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            broker_symbol = args.symbol or clean_str(row.get("broker_symbol"), clean_str(row.get("symbol"), ""))
            direction = clean_str(row.get("direction")).upper()
            lot = clean_float(row.get("lot"))
            entry_ref = clean_float(row.get("entry_price_reference"))
            sl_raw = clean_float(row.get("sl_price"))
            tp_raw = clean_float(row.get("tp_price"))
            magic = int(clean_float(row.get("magic_number")) or 26050601)
            comment = clean_str(row.get("comment"), f"mochipoyo {direction}")

            result: dict[str, Any] = {
                "row_index": i,
                "order_key": clean_str(row.get("order_key")),
                "payload_key": clean_str(row.get("payload_key")),
                "symbol_payload": clean_str(row.get("symbol")),
                "broker_symbol": broker_symbol,
                "direction": direction,
                "lot": lot,
                "entry_price_reference": entry_ref,
                "sl_price_payload": sl_raw,
                "tp_price_payload": tp_raw,
                "mt5_symbol_select_ok": None,
                "mt5_symbol_info_ok": False,
                "mt5_tick_ok": False,
                "local_validation_ok": False,
                "order_check_requested": bool(args.run_order_check),
                "order_check_ok": None,
                "order_check_retcode": None,
                "order_check_comment": None,
                "order_send_called": False,
            }

            errors: list[str] = []
            if not broker_symbol:
                errors.append("missing broker_symbol")
                result["validation_errors"] = "; ".join(errors)
                rows.append(result)
                continue

            if args.select_symbol:
                result["mt5_symbol_select_ok"] = bool(mt5.symbol_select(broker_symbol, True))
                result["last_error_after_symbol_select"] = str(mt5.last_error())

            info_obj = mt5.symbol_info(broker_symbol)
            tick_obj = mt5.symbol_info_tick(broker_symbol)
            info = asdict_obj(info_obj)
            tick = asdict_obj(tick_obj)
            result["mt5_symbol_info_ok"] = bool(info)
            result["mt5_tick_ok"] = bool(tick)
            result["last_error_after_symbol_read"] = str(mt5.last_error())
            if not info:
                errors.append(f"symbol_info not found: {broker_symbol}")
                result["validation_errors"] = "; ".join(errors)
                rows.append(result)
                continue
            if not tick:
                errors.append(f"symbol tick not found: {broker_symbol}")
                result["validation_errors"] = "; ".join(errors)
                rows.append(result)
                continue

            digits = int(info.get("digits", 0) or 0)
            point = float(info.get("point", 0.0) or 0.0)
            volume_min = float(info.get("volume_min", 0.0) or 0.0)
            volume_max = float(info.get("volume_max", 0.0) or 0.0)
            volume_step = float(info.get("volume_step", 0.0) or 0.0)
            stops_level = int(info.get("trade_stops_level", 0) or 0)
            bid = clean_float(tick.get("bid"))
            ask = clean_float(tick.get("ask"))
            current_price = ask if direction == "BUY" else bid if direction == "SELL" else None
            sl = round_to_digits(sl_raw, digits)
            tp = round_to_digits(tp_raw, digits)
            current_price = round_to_digits(current_price, digits)
            entry_ref = round_to_digits(entry_ref, digits)

            result.update({
                "digits": digits,
                "point": point,
                "volume_min": volume_min,
                "volume_max": volume_max,
                "volume_step": volume_step,
                "trade_stops_level": stops_level,
                "trade_freeze_level": info.get("trade_freeze_level"),
                "bid": bid,
                "ask": ask,
                "current_execution_price": current_price,
                "sl_price": sl,
                "tp_price": tp,
                "spread_price": (ask - bid) if ask is not None and bid is not None else None,
            })

            if lot is None:
                errors.append("missing lot")
            else:
                ok, e = is_volume_step_ok(lot, volume_min, volume_max, volume_step)
                errors.extend(e)
            ok, e = validate_price_relation(direction, entry_ref, sl, tp)
            errors.extend(e)
            ok, e = validate_current_price_relation(direction, current_price, sl, tp)
            errors.extend(e)
            ok, e = check_stop_level(direction, current_price, sl, tp, point, stops_level)
            errors.extend(e)

            local_ok = len(errors) == 0
            result["local_validation_ok"] = bool(local_ok)
            result["validation_errors"] = "; ".join(errors)

            if args.run_order_check and local_ok and lot is not None and current_price is not None and sl is not None and tp is not None:
                req = make_order_check_request(row, broker_symbol, direction, lot, current_price, sl, tp, args.deviation, magic, comment)
                result["order_check_request"] = json.dumps(req, ensure_ascii=False, default=str)
                check = mt5.order_check(req)
                check_d = asdict_obj(check)
                result["order_check_raw"] = json.dumps(check_d, ensure_ascii=False, default=str)
                result["order_check_retcode"] = check_d.get("retcode")
                result["order_check_comment"] = check_d.get("comment")
                # TRADE_RETCODE_DONE is commonly 10009, but order_check may also return other acceptable broker-specific retcodes.
                result["order_check_ok"] = bool(check is not None and int(check_d.get("retcode", -1)) == mt5.TRADE_RETCODE_DONE)
                result["last_error_after_order_check"] = str(mt5.last_error())
            rows.append(result)

        out = pd.DataFrame(rows)
        write_csv(out, out_dir / "mt5_order_payload_check_results.csv")
        report.update({
            "rows_in": int(len(df)),
            "rows_out": int(len(out)),
            "local_validation_ok_rows": int(out["local_validation_ok"].fillna(False).astype(bool).sum()) if not out.empty else 0,
            "local_validation_ng_rows": int((~out["local_validation_ok"].fillna(False).astype(bool)).sum()) if not out.empty else 0,
            "order_check_ok_rows": int(out["order_check_ok"].fillna(False).astype(bool).sum()) if "order_check_ok" in out.columns and not out.empty else 0,
            "order_check_ng_rows": int((~out["order_check_ok"].fillna(False).astype(bool)).sum()) if args.run_order_check and "order_check_ok" in out.columns and not out.empty else 0,
            "order_send_called": False,
            "results": rows,
        })
        write_text(out_dir / "mt5_order_payload_check_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))

        print("check_mt5_order_payloads")
        print(f"input_csv: {args.input_csv}")
        print(f"rows_in: {len(df)}")
        print(f"rows_out: {len(out)}")
        print(f"terminal_connected: {terminal_info.get('connected')}")
        print(f"account_login: {account_info.get('login')}")
        print(f"account_server: {account_info.get('server')}")
        print(f"trade_allowed_terminal: {terminal_info.get('trade_allowed')}")
        print(f"trade_allowed_account: {account_info.get('trade_allowed')}")
        print(f"local_validation_ok_rows: {report['local_validation_ok_rows']}")
        print(f"local_validation_ng_rows: {report['local_validation_ng_rows']}")
        print(f"run_order_check: {args.run_order_check}")
        print(f"order_check_ok_rows: {report['order_check_ok_rows']}")
        print(f"order_check_ng_rows: {report['order_check_ng_rows']}")
        print("order_send_called: False")
        cols = [
            "row_index",
            "broker_symbol",
            "direction",
            "lot",
            "current_execution_price",
            "sl_price",
            "tp_price",
            "local_validation_ok",
            "order_check_ok",
            "order_check_retcode",
            "order_check_comment",
            "validation_errors",
        ]
        cols = [c for c in cols if c in out.columns]
        if not out.empty:
            print(out[cols].to_string(index=False))
        print(f"out_dir: {out_dir}")
        print("done")
        return 0 if int(report["local_validation_ng_rows"]) == 0 and (not args.run_order_check or int(report["order_check_ng_rows"]) == 0) else 1
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
