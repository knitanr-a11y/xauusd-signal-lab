#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPORT_NAME = "mt5_order_send_report.json"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")


def normalize_volume(requested: float, *, minimum: float, maximum: float, step: float) -> float:
    if not all(math.isfinite(v) for v in [requested, minimum, maximum, step]):
        raise ValueError("non-finite volume contract")
    if requested < minimum - 1e-12 or requested > maximum + 1e-12:
        raise ValueError(f"volume outside broker range: requested={requested}; min={minimum}; max={maximum}")
    if step <= 0:
        raise ValueError("volume step must be positive")
    units = round((requested - minimum) / step)
    normalized = minimum + units * step
    if abs(normalized - requested) > max(1e-9, step * 1e-6):
        raise ValueError(f"volume not aligned to step: requested={requested}; step={step}")
    decimals = max(0, min(8, int(round(-math.log10(step))) if step < 1 else 0))
    return round(normalized, decimals)


def position_guard_errors(
    positions: list[dict[str, Any]], *, requested_magic: int, requested_lot: float,
    max_positions: int, max_lot: float,
) -> list[str]:
    errors: list[str] = []
    if any(int(p.get("magic", 0) or 0) == int(requested_magic) for p in positions):
        errors.append(f"same active magic already exists: {requested_magic}")
    if len(positions) + 1 > int(max_positions):
        errors.append(f"position count limit exceeded: after={len(positions)+1}; max={max_positions}")
    current_lot = sum(float(p.get("volume", 0.0) or 0.0) for p in positions)
    if current_lot + float(requested_lot) > float(max_lot) + 1e-9:
        errors.append(f"position lot limit exceeded: after={current_lot + requested_lot:.2f}; max={max_lot:.2f}")
    return errors


def _load_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"MetaTrader5 import failed: {exc}") from exc
    return mt5


def _asdict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {name: getattr(value, name) for name in dir(value) if not name.startswith("_")}


def _account_guard(mt5: Any, *, expected_login: int) -> dict[str, Any]:
    if not mt5.initialize():
        return {"ok": False, "reason": f"MT5_INITIALIZE_FAILED: {mt5.last_error()}"}
    account = mt5.account_info()
    if account is None:
        return {"ok": False, "reason": f"ACCOUNT_INFO_FAILED: {mt5.last_error()}"}
    login = int(getattr(account, "login", 0))
    trade_mode = int(getattr(account, "trade_mode", -1))
    margin_mode = int(getattr(account, "margin_mode", -1))
    demo_mode = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
    hedge_mode = int(getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2))
    errors: list[str] = []
    if expected_login and login != int(expected_login):
        errors.append(f"login mismatch actual={login} expected={expected_login}")
    if trade_mode != demo_mode:
        errors.append(f"not demo account trade_mode={trade_mode}")
    if margin_mode != hedge_mode:
        errors.append(f"not hedging account margin_mode={margin_mode}")
    return {
        "ok": not errors,
        "reason": "PASS" if not errors else "; ".join(errors),
        "login": login,
        "demo": trade_mode == demo_mode,
        "hedging": margin_mode == hedge_mode,
    }


def _select_fill_mode(mt5: Any, request: dict[str, Any], info: Any) -> tuple[int | None, dict[str, Any]]:
    candidates: list[int] = []
    for value in [
        int(getattr(info, "filling_mode", -1)),
        int(getattr(mt5, "ORDER_FILLING_IOC", 1)),
        int(getattr(mt5, "ORDER_FILLING_FOK", 0)),
        int(getattr(mt5, "ORDER_FILLING_RETURN", 2)),
    ]:
        if value >= 0 and value not in candidates:
            candidates.append(value)
    checks: list[dict[str, Any]] = []
    for fill in candidates:
        candidate = {**request, "type_filling": fill}
        check = mt5.order_check(candidate)
        item = _asdict(check)
        item["type_filling"] = fill
        checks.append(item)
        if check is not None and int(getattr(check, "retcode", -1)) == 0:
            return fill, {"checks": checks}
    return None, {"checks": checks}


def send(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / REPORT_NAME
    frame = pd.read_csv(args.input_csv, encoding="utf-8-sig")
    report: dict[str, Any] = {
        "schema_version": "btc_youtube_mt5_sender_v1",
        "started_at_utc": utc_text(),
        "rows_in": int(len(frame)),
        "rows_out": 0,
        "dry_run_check_ok_rows": 0,
        "sent_rows": 0,
        "duplicate_rows": 0,
        "error_rows": 0,
        "order_send_called_count": 0,
        "send_requested": bool(args.send),
        "records": [],
    }
    if len(frame) > int(args.max_orders):
        report["error_rows"] = len(frame)
        report["error"] = f"rows exceed max-orders: {len(frame)} > {args.max_orders}"
        write_json(report_path, report)
        return report

    ledger = read_ledger(args.order_ledger_csv)
    if not ledger.empty and {"order_key", "status"}.issubset(ledger.columns):
        sent_keys = set(ledger.loc[ledger["status"].astype(str) == "SENT", "order_key"].astype(str))
    else:
        sent_keys = set()
    mt5 = _load_mt5()
    account = _account_guard(mt5, expected_login=int(args.expected_login))
    report["account"] = account
    if not account.get("ok"):
        report["error_rows"] = len(frame)
        report["error"] = account.get("reason")
        write_json(report_path, report)
        mt5.shutdown()
        return report

    symbol = str(args.symbol)
    if not mt5.symbol_select(symbol, True):
        report["error_rows"] = len(frame)
        report["error"] = f"symbol_select failed: {symbol}; {mt5.last_error()}"
        write_json(report_path, report)
        mt5.shutdown()
        return report
    info = mt5.symbol_info(symbol)
    if info is None:
        report["error_rows"] = len(frame)
        report["error"] = f"symbol_info failed: {symbol}"
        write_json(report_path, report)
        mt5.shutdown()
        return report

    for _, row in frame.iterrows():
        order_key = str(row.get("order_key", row.get("payload_key", "")))
        record: dict[str, Any] = {"order_key": order_key, "strategy_id": row.get("strategy_id", ""), "status": ""}
        if order_key in sent_keys:
            record["status"] = "DUPLICATE_SKIPPED"
            report["duplicate_rows"] += 1
            report["records"].append(record)
            continue
        try:
            direction = str(row["direction"]).upper()
            if direction not in {"LONG", "SHORT", "BUY", "SELL"}:
                raise ValueError(f"invalid direction: {direction}")
            lot = normalize_volume(
                float(row["lot"]),
                minimum=float(getattr(info, "volume_min", 0.01)),
                maximum=float(getattr(info, "volume_max", 100.0)),
                step=float(getattr(info, "volume_step", 0.01)),
            )
            magic = int(row["magic_number"])
            positions = [_asdict(p) for p in (mt5.positions_get(symbol=symbol) or [])]
            errors = position_guard_errors(
                positions, requested_magic=magic, requested_lot=lot,
                max_positions=int(args.max_symbol_positions), max_lot=float(args.max_symbol_lot),
            )
            if errors:
                raise ValueError("; ".join(errors))
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")
            is_buy = direction in {"LONG", "BUY"}
            price = float(tick.ask if is_buy else tick.bid)
            sl = float(row["sl_price"])
            tp = float(row["tp_price"])
            if is_buy and not (sl < price < tp):
                raise ValueError(f"invalid BUY prices sl={sl} price={price} tp={tp}")
            if not is_buy and not (tp < price < sl):
                raise ValueError(f"invalid SELL prices tp={tp} price={price} sl={sl}")
            base_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": int(args.deviation),
                "magic": magic,
                "comment": f"YT {str(row.get('order_role', ''))} {str(row.get('strategy_id', ''))[:12]}",
                "type_time": mt5.ORDER_TIME_GTC,
            }
            fill_mode, check_report = _select_fill_mode(mt5, base_request, info)
            record["order_checks"] = check_report
            if fill_mode is None:
                raise RuntimeError("no broker-supported filling mode passed order_check")
            request = {**base_request, "type_filling": fill_mode}
            report["dry_run_check_ok_rows"] += 1
            if not args.send:
                record["status"] = "DRY_RUN_CHECK_OK"
            else:
                result = mt5.order_send(request)
                report["order_send_called_count"] += 1
                record["order_result"] = _asdict(result)
                retcode = -1 if result is None else int(getattr(result, "retcode", -1))
                success_codes = {
                    int(getattr(mt5, "TRADE_RETCODE_DONE", 10009)),
                    int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
                }
                if retcode not in success_codes:
                    raise RuntimeError(f"order_send failed retcode={retcode}; last_error={mt5.last_error()}")
                record["status"] = "SENT"
                record["sent_at_utc"] = utc_text()
                report["sent_rows"] += 1
                sent_keys.add(order_key)
                append_ledger(args.order_ledger_csv, {
                    "sent_at_utc": record["sent_at_utc"],
                    "order_key": order_key,
                    "strategy_id": row.get("strategy_id", ""),
                    "order_role": row.get("order_role", ""),
                    "direction": direction,
                    "lot": lot,
                    "magic_number": magic,
                    "status": "SENT",
                    "retcode": retcode,
                })
        except Exception as exc:
            record["status"] = "ERROR"
            record["error"] = repr(exc)
            report["error_rows"] += 1
            append_ledger(args.order_ledger_csv, {
                "sent_at_utc": utc_text(), "order_key": order_key,
                "strategy_id": row.get("strategy_id", ""), "order_role": row.get("order_role", ""),
                "direction": row.get("direction", ""), "lot": row.get("lot", ""),
                "magic_number": row.get("magic_number", ""), "status": "ERROR", "error": repr(exc),
            })
        report["records"].append(record)

    report["rows_out"] = len(report["records"])
    report["cycle_ok"] = report["error_rows"] == 0 and (
        (not args.send and report["dry_run_check_ok_rows"] + report["duplicate_rows"] == len(frame))
        or (args.send and report["sent_rows"] + report["duplicate_rows"] == len(frame))
    )
    report["completed_at_utc"] = utc_text()
    write_json(report_path, report)
    mt5.shutdown()
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fail-closed MT5 demo sender for BTC YouTube candidates.")
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--order-ledger-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="BTCUSD#")
    parser.add_argument("--expected-login", type=int, default=75539039)
    parser.add_argument("--max-orders", type=int, default=3)
    parser.add_argument("--max-symbol-positions", type=int, default=6)
    parser.add_argument("--max-symbol-lot", type=float, default=0.10)
    parser.add_argument("--deviation", type=int, default=100)
    parser.add_argument("--send", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = send(args)
    except Exception as exc:
        report = {
            "schema_version": "btc_youtube_mt5_sender_v1",
            "cycle_ok": False,
            "rows_out": 0,
            "dry_run_check_ok_rows": 0,
            "sent_rows": 0,
            "duplicate_rows": 0,
            "error_rows": 1,
            "order_send_called_count": 0,
            "error": repr(exc),
        }
        write_json(args.out_dir / REPORT_NAME, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if report.get("cycle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
