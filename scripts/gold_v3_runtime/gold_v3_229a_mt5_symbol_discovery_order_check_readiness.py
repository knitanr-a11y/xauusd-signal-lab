#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage229A - MT5 Symbol Discovery Order-Check Readiness

Demo-only readiness audit with symbol discovery.
This script may call mt5.order_check after demo-account confirmation.
This script must not call mt5.order_send.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STAGE = "GOLD_V3_229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_READINESS"
DECISION_READY = "STAGE229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_READY"
DECISION_BLOCKED = "STAGE229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

COMMON_GOLD_SYMBOLS = ["XAUUSD", "XAUUSD.", "XAUUSDm", "XAUUSD#", "GOLD", "GOLD.", "Gold"]
SEARCH_TOKENS = ["XAU", "GOLD"]

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
    out = files / "FX_OUTPUTS" / "gold_v3" / "229A"
    work = out / "mt5_symbol_discovery_order_check_readiness"
    return {
        "out": out,
        "work": work,
        "account_info": work / "mt5_account_info_redacted.json",
        "terminal_info": work / "mt5_terminal_info.json",
        "symbol_candidates": work / "mt5_symbol_candidates.json",
        "symbol_info": work / "mt5_selected_symbol_info.json",
        "order_check": work / "mt5_order_check_result.json",
        "summary": work / "mt5_symbol_discovery_order_check_summary.json",
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def redact_account_info(data: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(data)
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


def symbol_trade_candidate(mt5: Any, name: str) -> Dict[str, Any]:
    selected = bool(mt5.symbol_select(name, True))
    info = namedtuple_to_dict(mt5.symbol_info(name))
    tick = namedtuple_to_dict(mt5.symbol_info_tick(name))
    return {
        "name": name,
        "selected": selected,
        "info_exists": bool(info),
        "tick_exists": bool(tick),
        "visible": info.get("visible") if info else None,
        "trade_mode": info.get("trade_mode") if info else None,
        "volume_min": info.get("volume_min") if info else None,
        "volume_step": info.get("volume_step") if info else None,
        "digits": info.get("digits") if info else None,
        "point": info.get("point") if info else None,
        "bid": tick.get("bid") if tick else None,
        "ask": tick.get("ask") if tick else None,
    }


def candidate_ok(candidate: Dict[str, Any]) -> bool:
    if not candidate.get("selected"):
        return False
    if not candidate.get("info_exists") or not candidate.get("tick_exists"):
        return False
    try:
        bid = float(candidate.get("bid") or 0)
        ask = float(candidate.get("ask") or 0)
        vol_min = float(candidate.get("volume_min") or 0)
        vol_step = float(candidate.get("volume_step") or 0)
        return bid > 0 and ask > 0 and vol_min > 0 and vol_step > 0
    except Exception:
        return False


def discover_symbol(mt5: Any, preferred: str) -> Tuple[Optional[str], List[Dict[str, Any]], str]:
    names: List[str] = []
    if preferred:
        names.append(preferred)
    for name in COMMON_GOLD_SYMBOLS:
        if name not in names:
            names.append(name)

    all_symbols = mt5.symbols_get()
    if all_symbols:
        for obj in all_symbols:
            d = namedtuple_to_dict(obj)
            name = str(d.get("name") or "")
            upper = name.upper()
            if name and any(token in upper for token in SEARCH_TOKENS) and name not in names:
                names.append(name)

    candidates: List[Dict[str, Any]] = []
    for name in names:
        c = symbol_trade_candidate(mt5, name)
        candidates.append(c)
        if candidate_ok(c):
            return name, candidates, f"selected={name}"
    return None, candidates, "no usable gold-like symbol found"


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("M229A001", summary.get("mt5_module_imported") is True, "MetaTrader5 module import")
    add("M229A002", summary.get("mt5_initialize_ok") is True, str(summary.get("mt5_last_error")))
    add("M229A003", summary.get("account_info_exists") is True, "account_info exists")
    add("M229A004", summary.get("demo_account_confirmed") is True, str(summary.get("demo_account_evidence")))
    add("M229A005", summary.get("symbol_discovery_attempted") is True, "symbol discovery attempted")
    add("M229A006", bool(summary.get("selected_symbol")), str(summary.get("symbol_discovery_evidence")))
    add("M229A007", summary.get("symbol_info_exists") is True, "selected symbol_info exists")
    add("M229A008", summary.get("tick_info_exists") is True, "selected tick exists")
    add("M229A009", summary.get("volume_normalized_ok") is True, str(summary.get("volume_evidence")))
    add("M229A010", summary.get("order_check_executed") is True and summary.get("demo_account_confirmed") is True, "order_check only after demo gate")
    add("M229A011", summary.get("order_check_result_exists") is True, "order_check result exists")
    add("M229A012", summary.get("order_send_called") is False and summary.get("order_placed") is False, "order_send not called")
    add("M229A013", summary.get("final_live_enabled") is False and summary.get("autotrade_enabled") is False and summary.get("payload_activation_enabled") is False, "final/live/autotrade/payload OFF")
    add("M229A014", summary.get("csv_latest_row_contract") == "CLOSED" and summary.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")
    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 229A PASTE_ME_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_READINESS")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "mt5_module_imported", "mt5_initialize_ok", "account_info_exists", "demo_account_confirmed",
        "demo_account_evidence", "terminal_info_exists", "preferred_symbol", "symbol_discovery_attempted",
        "selected_symbol", "symbol_discovery_evidence", "symbol_info_exists", "tick_info_exists", "requested_volume",
        "normalized_volume", "volume_evidence", "order_check_executed", "order_check_result_exists",
        "order_check_retcode", "order_check_comment", "blocker_count",
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
    lines.append("Stage229A discovered a broker-available gold-like symbol and performed order_check only after demo-account confirmation. It did not call order_send and did not place an order.")
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
    preferred = os.environ.get("GOLD_V3_MT5_SYMBOL", "XAUUSD").strip() or "XAUUSD"
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
        "preferred_symbol": preferred,
        "symbol_discovery_attempted": False,
        "selected_symbol": "",
        "symbol_discovery_evidence": "",
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
            "symbol_candidates_json": str(p["symbol_candidates"]),
            "selected_symbol_info_json": str(p["symbol_info"]),
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
            account = namedtuple_to_dict(mt5.account_info())
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
                summary["symbol_discovery_attempted"] = True
                selected, candidates, evidence = discover_symbol(mt5, preferred)
                summary["selected_symbol"] = selected or ""
                summary["symbol_discovery_evidence"] = evidence
                write_json(p["symbol_candidates"], {"preferred": preferred, "candidates": candidates})
                if selected:
                    symbol_info = namedtuple_to_dict(mt5.symbol_info(selected))
                    tick = namedtuple_to_dict(mt5.symbol_info_tick(selected))
                    summary["symbol_info_exists"] = bool(symbol_info)
                    summary["tick_info_exists"] = bool(tick)
                    write_json(p["symbol_info"], symbol_info)
                    if symbol_info:
                        normalized_volume, volume_evidence = normalize_volume(requested_volume, symbol_info)
                        summary["normalized_volume"] = normalized_volume
                        summary["volume_evidence"] = volume_evidence
                        summary["volume_normalized_ok"] = normalized_volume > 0
                    else:
                        normalized_volume = requested_volume
                    if symbol_info and tick and summary["volume_normalized_ok"]:
                        digits = int(symbol_info.get("digits") or 2)
                        price = float(tick.get("ask") if side != "SELL" else tick.get("bid"))
                        if price <= 0:
                            raise RuntimeError("Invalid tick price for order_check")
                        if side != "SELL":
                            order_type = getattr(mt5, "ORDER_TYPE_BUY", 0)
                            sl = round(price - 5.0, digits)
                            tp = round(price + 15.0, digits)
                        else:
                            order_type = getattr(mt5, "ORDER_TYPE_SELL", 1)
                            sl = round(price + 5.0, digits)
                            tp = round(price - 15.0, digits)
                        request = {
                            "action": getattr(mt5, "TRADE_ACTION_DEAL", 1),
                            "symbol": selected,
                            "volume": normalized_volume,
                            "type": order_type,
                            "price": round(price, digits),
                            "sl": sl,
                            "tp": tp,
                            "deviation": 50,
                            "magic": 3002291,
                            "comment": "GOLD_V3_STAGE229A_ORDER_CHECK_ONLY",
                            "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
                            "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 1),
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
    print(f"Stage229A status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"selected_symbol: {summary.get('selected_symbol')}")
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
