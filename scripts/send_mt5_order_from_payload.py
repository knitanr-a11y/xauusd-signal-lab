#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Send MT5 orders from Mochipoyo order payloads with strong guards.

Default behavior is dry-run only. mt5.order_send is called only when --send is
explicitly provided.

Safety guards:
- max one order by default
- duplicate order_key prevention via order ledger
- position policy guard by default
- optional expected account login guard
- optional require demo-account guard based on account name/server/company heuristics
- local payload validation
- mt5.order_check must pass before order_send
- writes detailed CSV/JSON reports

Position policies:
- block_any: block if any open position exists for the broker symbol
- allow_same_direction: allow additional same-direction positions up to max count/lot; block opposite direction
- allow_any_until_max: allow any direction up to max count/lot

This script is intended for DEMO account order tests first, not production fully
automated trading.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
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

POSITION_POLICY_BLOCK_ANY = "block_any"
POSITION_POLICY_ALLOW_SAME_DIRECTION = "allow_same_direction"
POSITION_POLICY_ALLOW_ANY_UNTIL_MAX = "allow_any_until_max"


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


def asdict_list(items: Any) -> list[dict[str, Any]]:
    if items is None:
        return []
    out: list[dict[str, Any]] = []
    for item in list(items):
        out.append(asdict_obj(item))
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


def is_order_check_success(check_d: dict[str, Any]) -> bool:
    ret_raw = check_d.get("retcode")
    comment = str(check_d.get("comment", "")).strip().lower()
    try:
        retcode = int(ret_raw)
    except Exception:
        return False
    if retcode == 0 and comment == "done":
        return True
    if mt5 is not None and retcode == int(mt5.TRADE_RETCODE_DONE):
        return True
    return False


def is_order_send_success(send_d: dict[str, Any]) -> bool:
    ret_raw = send_d.get("retcode")
    try:
        retcode = int(ret_raw)
    except Exception:
        return False
    if mt5 is None:
        return False
    success_codes = {
        int(mt5.TRADE_RETCODE_DONE),
        int(mt5.TRADE_RETCODE_PLACED),
        int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", mt5.TRADE_RETCODE_DONE)),
    }
    return retcode in success_codes


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def volume_step_errors(lot: float, volume_min: float, volume_max: float, volume_step: float, eps: float = 1e-9) -> list[str]:
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
    return errors


def price_relation_errors(direction: str, current_price: float | None, sl: float | None, tp: float | None) -> list[str]:
    errors: list[str] = []
    d = direction.upper()
    if current_price is None:
        errors.append("missing current execution price")
    if sl is None:
        errors.append("missing sl_price")
    if tp is None:
        errors.append("missing tp_price")
    if errors:
        return errors
    assert current_price is not None and sl is not None and tp is not None
    if d == "BUY":
        if not sl < current_price:
            errors.append(f"BUY requires sl < ask: sl={sl}; ask={current_price}")
        if not tp > current_price:
            errors.append(f"BUY requires tp > ask: tp={tp}; ask={current_price}")
    elif d == "SELL":
        if not sl > current_price:
            errors.append(f"SELL requires sl > bid: sl={sl}; bid={current_price}")
        if not tp < current_price:
            errors.append(f"SELL requires tp < bid: tp={tp}; bid={current_price}")
    else:
        errors.append(f"invalid direction: {direction}")
    return errors


def stop_level_errors(current_price: float | None, sl: float | None, tp: float | None, point: float, stops_level: int) -> list[str]:
    if current_price is None or sl is None or tp is None:
        return ["missing price for stop-level validation"]
    min_distance = float(stops_level) * float(point)
    if min_distance <= 0:
        return []
    errors: list[str] = []
    if abs(float(current_price) - float(sl)) < min_distance:
        errors.append(f"SL distance below stops_level: min={min_distance}")
    if abs(float(tp) - float(current_price)) < min_distance:
        errors.append(f"TP distance below stops_level: min={min_distance}")
    return errors


def load_existing_order_keys(order_ledger_csv: Path) -> set[str]:
    if not order_ledger_csv.exists():
        return set()
    try:
        df = read_csv(order_ledger_csv)
    except Exception:
        return set()
    if "order_key" not in df.columns:
        return set()
    return set(df["order_key"].dropna().astype(str).tolist())


def append_order_ledger(rows: list[dict[str, Any]], order_ledger_csv: Path) -> None:
    if not rows:
        return
    new = pd.DataFrame(rows)
    if order_ledger_csv.exists():
        old = read_csv(order_ledger_csv)
        cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
        out = pd.concat([old.reindex(columns=cols), new.reindex(columns=cols)], ignore_index=True)
    else:
        out = new
    write_csv(out, order_ledger_csv)


def build_request(symbol: str, direction: str, lot: float, price: float, sl: float, tp: float, deviation: int, magic: int, comment: str) -> dict[str, Any]:
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


def get_symbol_positions(symbol: str) -> list[dict[str, Any]]:
    if mt5 is None:
        return []
    positions = mt5.positions_get(symbol=symbol)
    return asdict_list(positions)


def mt5_position_direction(position: dict[str, Any]) -> str:
    """Convert MT5 position type to BUY/SELL string.

    In MT5, POSITION_TYPE_BUY is 0 and POSITION_TYPE_SELL is 1.
    """
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


def summarize_positions(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return ""
    parts: list[str] = []
    for p in positions:
        parts.append(
            "ticket={ticket},symbol={symbol},direction={direction},type={type},volume={volume},price_open={price_open},sl={sl},tp={tp}".format(
                ticket=p.get("ticket"),
                symbol=p.get("symbol"),
                direction=mt5_position_direction(p),
                type=p.get("type"),
                volume=p.get("volume"),
                price_open=p.get("price_open"),
                sl=p.get("sl"),
                tp=p.get("tp"),
            )
        )
    return " | ".join(parts)


def position_policy_errors(
    *,
    policy: str,
    requested_direction: str,
    requested_lot: float,
    positions: list[dict[str, Any]],
    max_symbol_positions: int,
    max_symbol_lot: float,
) -> list[str]:
    errors: list[str] = []
    count = len(positions)
    existing_lot = sum(position_volume(p) for p in positions)
    after_count = count + 1
    after_lot = existing_lot + float(requested_lot)
    directions = [mt5_position_direction(p) for p in positions]
    opposite = [d for d in directions if d in {"BUY", "SELL"} and d != requested_direction.upper()]

    if policy == POSITION_POLICY_BLOCK_ANY:
        if count > 0:
            errors.append(
                f"position policy block_any blocked order: existing_positions={count}; existing_lot={existing_lot:.2f}"
            )
        return errors

    if policy == POSITION_POLICY_ALLOW_SAME_DIRECTION:
        if opposite:
            errors.append(
                f"position policy allow_same_direction blocked opposite position: requested={requested_direction}; existing_directions={directions}"
            )
        if after_count > int(max_symbol_positions):
            errors.append(
                f"position count limit exceeded: after_count={after_count}; max_symbol_positions={int(max_symbol_positions)}"
            )
        if after_lot > float(max_symbol_lot) + 1e-9:
            errors.append(
                f"position lot limit exceeded: after_lot={after_lot:.2f}; max_symbol_lot={float(max_symbol_lot):.2f}"
            )
        return errors

    if policy == POSITION_POLICY_ALLOW_ANY_UNTIL_MAX:
        if after_count > int(max_symbol_positions):
            errors.append(
                f"position count limit exceeded: after_count={after_count}; max_symbol_positions={int(max_symbol_positions)}"
            )
        if after_lot > float(max_symbol_lot) + 1e-9:
            errors.append(
                f"position lot limit exceeded: after_lot={after_lot:.2f}; max_symbol_lot={float(max_symbol_lot):.2f}"
            )
        return errors

    errors.append(f"unknown position policy: {policy}")
    return errors


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guarded MT5 order sender from order_payloads.csv. Default is dry-run only.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--order-ledger-csv", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default=None, help="Broker symbol override, e.g. GOLD#")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--send", action="store_true", help="Actually call mt5.order_send after all guards pass.")
    p.add_argument("--select-symbol", action="store_true")
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--require-demo-account", action="store_true", help="Refuse --send unless account name/server/company contains 'demo'.")
    p.add_argument("--allow-live-account", action="store_true", help="Override --require-demo-account guard. Not recommended.")
    p.add_argument(
        "--position-policy",
        choices=[POSITION_POLICY_BLOCK_ANY, POSITION_POLICY_ALLOW_SAME_DIRECTION, POSITION_POLICY_ALLOW_ANY_UNTIL_MAX],
        default=POSITION_POLICY_BLOCK_ANY,
        help="Open-position policy for the broker symbol. Default: block_any.",
    )
    p.add_argument("--max-symbol-positions", type=int, default=1, help="Max positions after the new order for allow_* policies. Default 1.")
    p.add_argument("--max-symbol-lot", type=float, default=0.01, help="Max total symbol lot after the new order for allow_* policies. Default 0.01.")
    p.add_argument("--block-if-symbol-position-exists", action=argparse.BooleanOptionalAction, default=None, help="Deprecated compatibility flag. If true, forces --position-policy block_any.")
    p.add_argument("--max-existing-symbol-positions", type=int, default=None, help="Deprecated compatibility flag mapped to --max-symbol-positions for allow_* policies.")
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--sleep-seconds", type=float, default=0.5)
    args = p.parse_args()
    if args.block_if_symbol_position_exists is True:
        args.position_policy = POSITION_POLICY_BLOCK_ANY
    elif args.block_if_symbol_position_exists is False and args.position_policy == POSITION_POLICY_BLOCK_ANY:
        args.position_policy = POSITION_POLICY_ALLOW_ANY_UNTIL_MAX
    if args.max_existing_symbol_positions is not None:
        args.max_symbol_positions = int(args.max_existing_symbol_positions) + 1
    return args


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    order_ledger_csv = Path(args.order_ledger_csv)

    report: dict[str, Any] = {
        "input_csv": args.input_csv,
        "order_ledger_csv": str(order_ledger_csv),
        "send_requested": bool(args.send),
        "order_send_called_count": 0,
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "initialize_ok": False,
        "position_policy": args.position_policy,
        "max_symbol_positions": int(args.max_symbol_positions),
        "max_symbol_lot": float(args.max_symbol_lot),
    }

    if mt5 is None:
        write_text(out_dir / "mt5_order_send_report.json", json.dumps(report, ensure_ascii=False, indent=2))
        print("send_mt5_order_from_payload")
        print("ERROR: MetaTrader5 import failed")
        print(MT5_IMPORT_ERROR)
        return 2

    df = read_csv(args.input_csv)
    if args.max_orders > 0:
        df = df.head(int(args.max_orders)).copy()
    existing_order_keys = load_existing_order_keys(order_ledger_csv)
    rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    initialized = False

    try:
        init_kwargs: dict[str, Any] = {}
        if args.terminal_path:
            init_kwargs["path"] = args.terminal_path
        if args.portable:
            init_kwargs["portable"] = True
        initialized = bool(mt5.initialize(**init_kwargs))
        report["initialize_ok"] = initialized
        report["last_error_after_initialize"] = str(mt5.last_error())
        if not initialized:
            write_text(out_dir / "mt5_order_send_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))
            print("send_mt5_order_from_payload")
            print("ERROR: mt5.initialize failed")
            print(f"last_error: {report['last_error_after_initialize']}")
            return 3

        terminal_info = asdict_obj(mt5.terminal_info())
        account_info = asdict_obj(mt5.account_info())
        report["terminal_info"] = terminal_info
        report["account_info"] = account_info
        current_login = account_info.get("login")

        global_errors: list[str] = []
        if args.expected_login is not None and int(current_login or -1) != int(args.expected_login):
            global_errors.append(f"expected_login mismatch: expected={args.expected_login}; actual={current_login}")
        if args.require_demo_account and not args.allow_live_account and not account_looks_demo(account_info):
            global_errors.append("require_demo_account is set but account/server/company does not look like demo")
        if args.send and not bool(terminal_info.get("trade_allowed")):
            global_errors.append("terminal trade_allowed is False")
        if args.send and not bool(account_info.get("trade_allowed")):
            global_errors.append("account trade_allowed is False")

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            broker_symbol = args.symbol or clean_str(row.get("broker_symbol"), clean_str(row.get("symbol"), ""))
            direction = clean_str(row.get("direction")).upper()
            lot = clean_float(row.get("lot"))
            sl_raw = clean_float(row.get("sl_price"))
            tp_raw = clean_float(row.get("tp_price"))
            magic = int(clean_float(row.get("magic_number")) or 26050601)
            comment = clean_str(row.get("comment"), f"mochipoyo {direction}")
            order_key = clean_str(row.get("order_key"), clean_str(row.get("payload_key"), ""))
            payload_key = clean_str(row.get("payload_key"), order_key)
            result: dict[str, Any] = {
                "row_index": i,
                "order_key": order_key,
                "payload_key": payload_key,
                "broker_symbol": broker_symbol,
                "direction": direction,
                "lot": lot,
                "send_requested": bool(args.send),
                "position_policy": args.position_policy,
                "max_symbol_positions": int(args.max_symbol_positions),
                "max_symbol_lot": float(args.max_symbol_lot),
                "order_send_called": False,
                "order_send_ok": False,
                "order_status": "PENDING",
            }
            errors = list(global_errors)
            if not broker_symbol:
                errors.append("missing broker_symbol")
            if not order_key:
                errors.append("missing order_key")
            if order_key in existing_order_keys:
                errors.append("duplicate order_key already exists in order ledger")

            if errors:
                result["order_status"] = "BLOCKED_PRECHECK"
                result["validation_errors"] = "; ".join(errors)
                rows.append(result)
                continue

            if args.select_symbol:
                result["symbol_select_ok"] = bool(mt5.symbol_select(broker_symbol, True))
                result["last_error_after_symbol_select"] = str(mt5.last_error())

            symbol_positions = get_symbol_positions(broker_symbol)
            existing_lot = sum(position_volume(p) for p in symbol_positions)
            existing_directions = [mt5_position_direction(p) for p in symbol_positions]
            result["existing_symbol_positions"] = len(symbol_positions)
            result["existing_symbol_lot"] = existing_lot
            result["existing_symbol_directions"] = ",".join(existing_directions)
            result["existing_symbol_positions_detail"] = summarize_positions(symbol_positions)
            if lot is not None:
                policy_errors = position_policy_errors(
                    policy=args.position_policy,
                    requested_direction=direction,
                    requested_lot=lot,
                    positions=symbol_positions,
                    max_symbol_positions=int(args.max_symbol_positions),
                    max_symbol_lot=float(args.max_symbol_lot),
                )
                if policy_errors:
                    errors.extend(policy_errors)
                    result["order_status"] = "BLOCKED_POSITION_POLICY"
                    result["validation_errors"] = "; ".join(errors)
                    rows.append(result)
                    continue

            info = asdict_obj(mt5.symbol_info(broker_symbol))
            tick = asdict_obj(mt5.symbol_info_tick(broker_symbol))
            if not info:
                errors.append(f"symbol_info not found: {broker_symbol}")
            if not tick:
                errors.append(f"symbol tick not found: {broker_symbol}")
            if errors:
                result["order_status"] = "BLOCKED_SYMBOL"
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
            current_price = round_to_digits(current_price, digits)
            sl = round_to_digits(sl_raw, digits)
            tp = round_to_digits(tp_raw, digits)
            result.update({
                "digits": digits,
                "point": point,
                "volume_min": volume_min,
                "volume_max": volume_max,
                "volume_step": volume_step,
                "trade_stops_level": stops_level,
                "bid": bid,
                "ask": ask,
                "current_execution_price": current_price,
                "sl_price": sl,
                "tp_price": tp,
            })

            if lot is None:
                errors.append("missing lot")
            else:
                errors.extend(volume_step_errors(lot, volume_min, volume_max, volume_step))
            errors.extend(price_relation_errors(direction, current_price, sl, tp))
            errors.extend(stop_level_errors(current_price, sl, tp, point, stops_level))
            if errors:
                result["order_status"] = "BLOCKED_LOCAL_VALIDATION"
                result["validation_errors"] = "; ".join(errors)
                rows.append(result)
                continue

            assert lot is not None and current_price is not None and sl is not None and tp is not None
            req = build_request(broker_symbol, direction, lot, current_price, sl, tp, args.deviation, magic, comment)
            result["order_check_request"] = json.dumps(req, ensure_ascii=False, default=str)
            check = mt5.order_check(req)
            check_d = asdict_obj(check)
            result["order_check_raw"] = json.dumps(check_d, ensure_ascii=False, default=str)
            result["order_check_retcode"] = check_d.get("retcode")
            result["order_check_comment"] = check_d.get("comment")
            order_check_ok = bool(check is not None and is_order_check_success(check_d))
            result["order_check_ok"] = order_check_ok
            if not order_check_ok:
                result["order_status"] = "BLOCKED_ORDER_CHECK"
                result["validation_errors"] = f"order_check failed: retcode={check_d.get('retcode')}; comment={check_d.get('comment')}"
                rows.append(result)
                continue

            if not args.send:
                result["order_status"] = "DRY_RUN_ORDER_CHECK_OK"
                result["validation_errors"] = ""
                rows.append(result)
                continue

            send_result = mt5.order_send(req)
            report["order_send_called_count"] = int(report.get("order_send_called_count", 0)) + 1
            result["order_send_called"] = True
            send_d = asdict_obj(send_result)
            result["order_send_raw"] = json.dumps(send_d, ensure_ascii=False, default=str)
            result["order_send_retcode"] = send_d.get("retcode")
            result["order_send_comment"] = send_d.get("comment")
            result["order_ticket"] = send_d.get("order")
            result["deal_ticket"] = send_d.get("deal")
            result["order_send_ok"] = is_order_send_success(send_d)
            result["order_status"] = "SENT" if result["order_send_ok"] else "ERROR_ORDER_SEND"
            result["validation_errors"] = "" if result["order_send_ok"] else f"order_send failed: retcode={send_d.get('retcode')}; comment={send_d.get('comment')}"
            rows.append(result)

            ledger_rows.append({
                "sent_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "account_login": current_login,
                "account_server": account_info.get("server"),
                "order_key": order_key,
                "payload_key": payload_key,
                "broker_symbol": broker_symbol,
                "direction": direction,
                "lot": lot,
                "price": current_price,
                "sl": sl,
                "tp": tp,
                "magic": magic,
                "position_policy": args.position_policy,
                "existing_symbol_positions_before_send": len(symbol_positions),
                "existing_symbol_lot_before_send": existing_lot,
                "order_status": result["order_status"],
                "order_send_ok": result["order_send_ok"],
                "order_send_retcode": result.get("order_send_retcode"),
                "order_send_comment": result.get("order_send_comment"),
                "order_ticket": result.get("order_ticket"),
                "deal_ticket": result.get("deal_ticket"),
            })
            existing_order_keys.add(order_key)
            time.sleep(max(0.0, float(args.sleep_seconds)))

        out = pd.DataFrame(rows)
        write_csv(out, out_dir / "mt5_order_send_results.csv")
        if args.send:
            append_order_ledger(ledger_rows, order_ledger_csv)
        report.update({
            "rows_in": int(len(df)),
            "rows_out": int(len(out)),
            "dry_run_check_ok_rows": int((out.get("order_status", pd.Series(dtype=str)) == "DRY_RUN_ORDER_CHECK_OK").sum()) if not out.empty else 0,
            "sent_rows": int((out.get("order_status", pd.Series(dtype=str)) == "SENT").sum()) if not out.empty else 0,
            "blocked_position_policy_rows": int((out.get("order_status", pd.Series(dtype=str)) == "BLOCKED_POSITION_POLICY").sum()) if not out.empty else 0,
            "blocked_existing_symbol_position_rows": int((out.get("order_status", pd.Series(dtype=str)).isin(["BLOCKED_EXISTING_SYMBOL_POSITION", "BLOCKED_POSITION_POLICY"])).sum()) if not out.empty else 0,
            "error_rows": int(out["order_status"].astype(str).str.startswith(("ERROR", "BLOCKED")).sum()) if "order_status" in out.columns and not out.empty else 0,
            "results": rows,
        })
        write_text(out_dir / "mt5_order_send_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))

        print("send_mt5_order_from_payload")
        print(f"input_csv: {args.input_csv}")
        print(f"rows_in: {len(df)}")
        print(f"rows_out: {len(out)}")
        print(f"send_requested: {args.send}")
        print(f"account_login: {current_login}")
        print(f"account_server: {account_info.get('server')}")
        print(f"account_name: {account_info.get('name')}")
        print(f"terminal_trade_allowed: {terminal_info.get('trade_allowed')}")
        print(f"account_trade_allowed: {account_info.get('trade_allowed')}")
        print(f"position_policy: {args.position_policy}")
        print(f"max_symbol_positions: {args.max_symbol_positions}")
        print(f"max_symbol_lot: {args.max_symbol_lot}")
        print(f"order_send_called_count: {report['order_send_called_count']}")
        print(f"dry_run_check_ok_rows: {report['dry_run_check_ok_rows']}")
        print(f"sent_rows: {report['sent_rows']}")
        print(f"blocked_position_policy_rows: {report['blocked_position_policy_rows']}")
        print(f"error_rows: {report['error_rows']}")
        cols = [
            "row_index",
            "order_status",
            "broker_symbol",
            "direction",
            "lot",
            "existing_symbol_positions",
            "existing_symbol_lot",
            "existing_symbol_directions",
            "current_execution_price",
            "sl_price",
            "tp_price",
            "order_check_ok",
            "order_send_called",
            "order_send_ok",
            "order_send_retcode",
            "order_send_comment",
            "order_ticket",
            "deal_ticket",
            "validation_errors",
        ]
        cols = [c for c in cols if c in out.columns]
        if not out.empty:
            print(out[cols].to_string(index=False))
        print(f"order_ledger_csv: {order_ledger_csv}")
        print(f"out_dir: {out_dir}")
        print("done")
        return 0 if int(report["error_rows"]) == 0 else 1
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
