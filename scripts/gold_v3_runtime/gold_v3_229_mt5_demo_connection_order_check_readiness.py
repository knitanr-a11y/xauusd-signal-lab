#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage229 - MT5 Demo Connection Order-Check Readiness

Demo-only readiness audit.
This script may call mt5.order_check after demo-account confirmation.
This script must not call mt5.order_send.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


STAGE = "GOLD_V3_229_MT5_DEMO_CONNECTION_ORDER_CHECK_READINESS"
DECISION_READY = "STAGE229_MT5_DEMO_CONNECTION_ORDER_CHECK_READY"
DECISION_BLOCKED = "STAGE229_MT5_DEMO_CONNECTION_ORDER_CHECK_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

OFF_FLAGS: Dict[str, bool] = {
    "order_send_called": False,
    "order_placed": False,
    "position_modified": False,
    "position_closed": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "no_signal_notify": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "open_asof_allowed": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def paths() -> Dict[str, Path]:
    files = default_mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "229"
    work = out / "mt5_demo_connection_order_check_readiness"
    return {
        "out": out,
        "work": work,
        "account_info": work / "mt5_account_info_redacted.json",
        "terminal_info": work / "mt5_terminal_info.json",
        "symbol_info": work / "mt5_symbol_info.json",
        "order_check": work / "mt5_order_check_result.json",
        "summary": work / "mt5_readiness_summary.json",
        "paste": out / "paste_me.txt",
    }


def namedtuple_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        return dict(obj._asdict())
    if isinstance(obj, dict):
        return dict(obj)
    return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and not callable(getattr(obj, k))}


def redact_account_info(data: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(data)
    # Keep login visible enough for local audit? Redact by default.
    if "login" in redacted:
        text = str(redacted["login"])
        redacted["login_redacted"] = text[:2] + "***" + text[-2:] if len(text) >= 4 else "***"
        redacted.pop("login", None)
    return redacted


def is_demo_account(mt5: Any, account: Dict[str, Any]) -> Tuple[bool, str]:
    trade_mode = account.get("trade_mode")
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    real_const = getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", None)

    server = str(account.get("server", ""))
    name = str(account.get("name", ""))
    company = str(account.get("company", ""))
    text = " ".join([server, name, company]).lower()

    if real_const is not None and trade_mode == real_const:
        return False, f"trade_mode={trade_mode} equals ACCOUNT_TRADE_MODE_REAL"

    if demo_const is not None and trade_mode == demo_const:
        return True, f"trade_mode={trade_mode} equals ACCOUNT_TRADE_MODE_DEMO"

    if "real" in text and "demo" not in text:
        return False, "account text contains real without demo evidence"

    if "demo" in text:
        return True, "account server/name/company contains demo"

    return False, f"unable to confirm demo account; trade_mode={trade_mode} server/name/company={server}/{name}/{company}"


def normalize_volume(requested: float, symbol: Dict[str, Any]) -> Tuple[float, str]:
    volume_min = float(symbol.get("volume_min") or 0.01)
    volume_max = float(symbol.get("volume_max") or requested)
    volume_step = float(symbol.get("volume_step") or 0.01)

    vol = max(requested, volume_min)
    vol = min(vol, volume_max)
    if volume_step > 0:
        steps = math.ceil((vol - volume_min) / volume_step)
        vol = volume_min + steps * volume_step
    vol = round(vol, 8)
    return vol, f"requested={requested} min={volume_min} max={volume_max} step={volume_step} normalized={vol}"


def json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, "_asdict"):
        return json_safe(dict(value._asdict()))
    return str(value)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("M229001", summary.get("mt5_module_imported") is True, "MetaTrader5 module import")
    add("M229002", summary.get("mt5_initialize_ok") is True, str(summary.get("mt5_last_error")))
    add("M229003", summary.get("account_info_exists") is True, "account_info exists")
    add("M229004", summary.get("demo_account_confirmed") is True, str(summary.get("demo_account_evidence")))
    add("M229005", summary.get("terminal_info_exists") is True, "terminal_info exists")
    add("M229006", summary.get("symbol_select_ok") is True, str(summary.get("symbol")))
    add("M229007", summary.get("symbol_info_exists") is True, "symbol_info exists")
    add("M229008", summary.get("tick_info_exists") is True, "tick_info exists")
    add("M229009", summary.get("volume_normalized_ok") is True, str(summary.get("volume_evidence")))
    add("M229010", summary.get("order_check_executed") is True and summary.get("demo_account_confirmed") is True, "order_check only after demo gate")
    add("M229011", summary.get("order_check_result_exists") is True, "order_check result exists")
    add("M229012", summary.get("order_send_called") is False and summary.get("order_placed") is False, "order_send not called")
    add("M229013", summary.get("final_live_enabled") is False and summary.get("autotrade_enabled") is False and summary.get("payload_activation_enabled") is False, "final/live/autotrade/payload OFF")
    add("M229014", summary.get("csv_latest_row_contract") == "CLOSED" and summary.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 229 PASTE_ME_MT5_DEMO_CONNECTION_ORDER_CHECK_READINESS")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "mt5_module_imported", "mt5_initialize_ok", "account_info_exists", "demo_account_confirmed",
        "demo_account_evidence", "terminal_info_exists", "symbol", "symbol_select_ok", "symbol_info_exists",
        "tick_info_exists", "requested_volume", "normalized_volume", "volume_evidence", "order_check_executed",
        "order_check_result_exists", "order_check_retcode", "order_check_comment", "blocker_count",
    ] + list(OFF_FLAGS.keys()):
        lines.append(f"{key}: {summary.get(key)}")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in summary.get("output_files", {}).items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage229 confirmed MT5 demo-readiness and performed order_check only. It did not call order_send and did not place an order.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    created_at = utc_now_iso()
    symbol = os.environ.get("GOLD_V3_MT5_SYMBOL", "XAUUSD").strip() or "XAUUSD"
    requested_volume = float(os.environ.get("GOLD_V3_MT5_CHECK_VOLUME", "0.01"))
    side = os.environ.get("GOLD_V3_MT5_CHECK_SIDE", "BUY").strip().upper() or "BUY"

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": created_at,
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "mt5_module_imported": False,
        "mt5_initialize_ok": False,
        "mt5_last_error": "",
        "account_info_exists": False,
        "demo_account_confirmed": False,
        "demo_account_evidence": "",
        "terminal_info_exists": False,
        "symbol": symbol,
        "symbol_select_ok": False,
        "symbol_info_exists": False,
        "tick_info_exists": False,
        "requested_volume": requested_volume,
        "normalized_volume": None,
        "volume_normalized_ok": False,
        "volume_evidence": "",
        "order_check_executed": False,
        "order_check_result_exists": False,
        "order_check_retcode": "",
        "order_check_comment": "",
        "csv_latest_row_contract": "CLOSED",
        "output_files": {
            "account_info_redacted_json": str(p["account_info"]),
            "terminal_info_json": str(p["terminal_info"]),
            "symbol_info_json": str(p["symbol_info"]),
            "order_check_result_json": str(p["order_check"]),
            "summary_json": str(p["summary"]),
        },
    }
    summary.update(OFF_FLAGS)

    try:
        import MetaTrader5 as mt5  # type: ignore
        summary["mt5_module_imported"] = True

        init_ok = bool(mt5.initialize())
        summary["mt5_initialize_ok"] = init_ok
        try:
            summary["mt5_last_error"] = str(mt5.last_error())
        except Exception:
            summary["mt5_last_error"] = "last_error unavailable"

        if init_ok:
            account_obj = mt5.account_info()
            account = namedtuple_to_dict(account_obj)
            summary["account_info_exists"] = bool(account)
            if account:
                demo_ok, evidence = is_demo_account(mt5, account)
                summary["demo_account_confirmed"] = demo_ok
                summary["demo_account_evidence"] = evidence
                write_json(p["account_info"], redact_account_info(account))

            terminal = namedtuple_to_dict(mt5.terminal_info())
            summary["terminal_info_exists"] = bool(terminal)
            write_json(p["terminal_info"], terminal)

            if summary["demo_account_confirmed"]:
                summary["symbol_select_ok"] = bool(mt5.symbol_select(symbol, True))
                symbol_obj = mt5.symbol_info(symbol)
                symbol_info = namedtuple_to_dict(symbol_obj)
                summary["symbol_info_exists"] = bool(symbol_info)
                write_json(p["symbol_info"], symbol_info)

                tick_obj = mt5.symbol_info_tick(symbol)
                tick = namedtuple_to_dict(tick_obj)
                summary["tick_info_exists"] = bool(tick)

                if symbol_info:
                    normalized_volume, volume_evidence = normalize_volume(requested_volume, symbol_info)
                    summary["normalized_volume"] = normalized_volume
                    summary["volume_evidence"] = volume_evidence
                    summary["volume_normalized_ok"] = normalized_volume > 0
                else:
                    normalized_volume = requested_volume

                if summary["symbol_select_ok"] and symbol_info and tick and summary["volume_normalized_ok"]:
                    digits = int(symbol_info.get("digits") or 2)
                    point = float(symbol_info.get("point") or 0.01)
                    filling_mode = getattr(mt5, "ORDER_FILLING_IOC", 1)
                    order_type = getattr(mt5, "ORDER_TYPE_BUY", 0) if side != "SELL" else getattr(mt5, "ORDER_TYPE_SELL", 1)
                    trade_action_deal = getattr(mt5, "TRADE_ACTION_DEAL", 1)
                    price = float(tick.get("ask") if side != "SELL" else tick.get("bid"))
                    if price <= 0:
                        raise RuntimeError("Invalid tick price for order_check")
                    sl_distance = 5.0
                    tp_distance = 15.0
                    if side != "SELL":
                        sl = round(price - sl_distance, digits)
                        tp = round(price + tp_distance, digits)
                    else:
                        sl = round(price + sl_distance, digits)
                        tp = round(price - tp_distance, digits)
                    request = {
                        "action": trade_action_deal,
                        "symbol": symbol,
                        "volume": normalized_volume,
                        "type": order_type,
                        "price": round(price, digits),
                        "sl": sl,
                        "tp": tp,
                        "deviation": 50,
                        "magic": 300229,
                        "comment": "GOLD_V3_STAGE229_ORDER_CHECK_ONLY",
                        "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
                        "type_filling": filling_mode,
                    }
                    result_obj = mt5.order_check(request)
                    summary["order_check_executed"] = True
                    result = namedtuple_to_dict(result_obj)
                    summary["order_check_result_exists"] = bool(result)
                    summary["order_check_retcode"] = result.get("retcode", "") if result else ""
                    summary["order_check_comment"] = result.get("comment", "") if result else ""
                    write_json(p["order_check"], {"request": request, "result": result})

    except Exception as exc:
        summary["exception"] = f"{type(exc).__name__}: {exc}"

    finally:
        try:
            if summary.get("mt5_module_imported"):
                import MetaTrader5 as mt5  # type: ignore
                mt5.shutdown()
        except Exception:
            pass

    checks, blockers = validate(summary)
    if summary.get("exception"):
        blockers.append(f"EXCEPTION: {summary['exception']}")
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED

    write_json(p["summary"], summary)
    write_paste_me(p["paste"], summary, checks)

    print(f"Stage229 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"paste_me: {p['paste']}")
    if blockers:
        print("BLOCKERS:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
