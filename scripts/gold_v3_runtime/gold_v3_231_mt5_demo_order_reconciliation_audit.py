#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage231 - MT5 Demo Order Reconciliation Audit

Read-only reconciliation for the single Stage230 demo order.
No new order, no close, no position modification.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


STAGE = "GOLD_V3_231_MT5_DEMO_ORDER_RECONCILIATION_AUDIT"
DECISION_READY = "STAGE231_MT5_DEMO_ORDER_RECONCILIATION_READY"
DECISION_BLOCKED = "STAGE231_MT5_DEMO_ORDER_RECONCILIATION_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
SYMBOL = "GOLD#"
MAGIC = 300230

OFF_FLAGS: Dict[str, bool] = {
    "new_order_called": False,
    "close_called": False,
    "modify_called": False,
    "order_send_called": False,
    "position_close_called": False,
    "position_modify_called": False,
    "autotrade_loop_enabled": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return Path.cwd().resolve()


def paths() -> Dict[str, Path]:
    files = mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "231"
    work = out / "mt5_demo_order_reconciliation"
    stage230 = files / "FX_OUTPUTS" / "gold_v3" / "230" / "mt5_demo_one_order_send_test"
    return {
        "out": out,
        "work": work,
        "stage230_summary": stage230 / "stage230_summary.json",
        "stage230_order_result": stage230 / "stage230_order_send_result.json",
        "stage230_ledger": stage230 / "stage230_demo_order_send_ledger.csv",
        "account_info": work / "stage231_account_info_redacted.json",
        "positions": work / "stage231_positions.json",
        "history_orders": work / "stage231_history_orders.json",
        "history_deals": work / "stage231_history_deals.json",
        "summary": work / "stage231_reconciliation_summary.json",
        "paste": out / "paste_me.txt",
    }


def nt_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        return dict(obj._asdict())
    if isinstance(obj, dict):
        return dict(obj)
    return {"value": str(obj)}


def list_to_dicts(values: Any) -> List[Dict[str, Any]]:
    if values is None:
        return []
    return [nt_to_dict(v) for v in values]


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


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_ledger_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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
    if real_const is not None and trade_mode == real_const:
        return False, f"trade_mode={trade_mode} REAL"
    if demo_const is not None and trade_mode == demo_const:
        return True, f"trade_mode={trade_mode} DEMO"
    text = " ".join([str(account.get("server", "")), str(account.get("name", "")), str(account.get("company", ""))]).lower()
    if "demo" in text:
        return True, "server/name/company contains demo"
    return False, f"cannot confirm demo: trade_mode={trade_mode}"


def filter_rows(rows: List[Dict[str, Any]], order_ticket: str, deal_ticket: str) -> List[Dict[str, Any]]:
    targets = {str(order_ticket), str(deal_ticket)} - {"", "None"}
    matched: List[Dict[str, Any]] = []
    for row in rows:
        if any(str(row.get(k, "")) in targets for k in ["ticket", "order", "position_id", "deal"]):
            matched.append(row)
    return matched


def position_matches_stage230(pos: Dict[str, Any], symbol: str, volume: float) -> bool:
    if str(pos.get("symbol", "")) != symbol:
        return False
    try:
        return abs(float(pos.get("volume") or 0) - volume) < 1e-9
    except Exception:
        return False


def position_has_tpsl(pos: Dict[str, Any]) -> bool:
    try:
        sl = float(pos.get("sl") or 0)
        tp = float(pos.get("tp") or 0)
        return sl > 0 and tp > 0
    except Exception:
        return False


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("R231001", summary.get("stage230_summary_exists") is True, "Stage230 summary exists")
    add("R231002", summary.get("stage230_order_placed") is True, "Stage230 order_placed=True")
    add("R231003", summary.get("mt5_initialize_ok") is True, str(summary.get("mt5_last_error")))
    add("R231004", summary.get("demo_account_confirmed") is True, str(summary.get("demo_account_evidence")))
    add("R231005", summary.get("stage230_symbol") == SYMBOL, str(summary.get("stage230_symbol")))
    add("R231006", abs(float(summary.get("stage230_volume") or 0) - 0.01) < 1e-9, str(summary.get("stage230_volume")))
    add("R231007", bool(summary.get("stage230_order_ticket")) and bool(summary.get("stage230_deal_ticket")), f"order={summary.get('stage230_order_ticket')} deal={summary.get('stage230_deal_ticket')}")
    add("R231008", summary.get("positions_query_executed") is True, "positions_get executed")
    add("R231009", summary.get("history_orders_query_executed") is True, "history_orders_get executed")
    add("R231010", summary.get("history_deals_query_executed") is True, "history_deals_get executed")
    add("R231011", summary.get("position_or_history_evidence_exists") is True, f"open_matches={summary.get('open_position_match_count')} history_orders={summary.get('matched_history_order_count')} history_deals={summary.get('matched_history_deal_count')}")
    add("R231012", summary.get("open_position_match_count") == 0 or summary.get("open_positions_tpsl_ok") is True, "if open position exists, TP/SL non-zero")
    add("R231013", summary.get("new_order_called") is False and summary.get("close_called") is False and summary.get("modify_called") is False and summary.get("order_send_called") is False, "no new order/close/modify")
    add("R231014", summary.get("autotrade_loop_enabled") is False and summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False and summary.get("no_signal_order_allowed") is False, "restricted modes OFF")
    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 231 PASTE_ME_MT5_DEMO_ORDER_RECONCILIATION_AUDIT")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "stage230_summary_exists", "stage230_order_result_exists", "stage230_ledger_exists", "stage230_order_placed",
        "stage230_symbol", "stage230_side", "stage230_volume", "stage230_order_ticket", "stage230_deal_ticket",
        "mt5_module_imported", "mt5_initialize_ok", "account_info_exists", "demo_account_confirmed", "demo_account_evidence",
        "positions_query_executed", "positions_total_count", "open_position_match_count", "open_positions_tpsl_ok",
        "history_orders_query_executed", "history_orders_total_count", "matched_history_order_count",
        "history_deals_query_executed", "history_deals_total_count", "matched_history_deal_count",
        "position_or_history_evidence_exists", "blocker_count",
    ] + list(OFF_FLAGS.keys())
    for key in keys:
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
    lines.append("Stage231 read MT5 positions and history to reconcile the Stage230 demo order. It did not send, close, or modify any order or position.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    created_at = utc_now_iso()
    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": created_at,
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "stage230_summary_exists": p["stage230_summary"].exists(),
        "stage230_order_result_exists": p["stage230_order_result"].exists(),
        "stage230_ledger_exists": p["stage230_ledger"].exists(),
        "stage230_order_placed": False,
        "stage230_symbol": "",
        "stage230_side": "",
        "stage230_volume": None,
        "stage230_order_ticket": "",
        "stage230_deal_ticket": "",
        "mt5_module_imported": False,
        "mt5_initialize_ok": False,
        "mt5_last_error": "",
        "account_info_exists": False,
        "demo_account_confirmed": False,
        "demo_account_evidence": "",
        "positions_query_executed": False,
        "positions_total_count": 0,
        "open_position_match_count": 0,
        "open_positions_tpsl_ok": False,
        "history_orders_query_executed": False,
        "history_orders_total_count": 0,
        "matched_history_order_count": 0,
        "history_deals_query_executed": False,
        "history_deals_total_count": 0,
        "matched_history_deal_count": 0,
        "position_or_history_evidence_exists": False,
        "output_files": {
            "account_info_redacted_json": str(p["account_info"]),
            "positions_json": str(p["positions"]),
            "history_orders_json": str(p["history_orders"]),
            "history_deals_json": str(p["history_deals"]),
            "summary_json": str(p["summary"]),
        },
    }
    summary.update(OFF_FLAGS)

    try:
        if not p["stage230_summary"].exists():
            raise RuntimeError(f"Stage230 summary missing: {p['stage230_summary']}")
        stage230_summary = read_json(p["stage230_summary"])
        ledger_rows = read_ledger_rows(p["stage230_ledger"])

        summary["stage230_order_placed"] = bool(stage230_summary.get("order_placed"))
        summary["stage230_symbol"] = str(stage230_summary.get("symbol", ""))
        summary["stage230_side"] = str(stage230_summary.get("side", ""))
        summary["stage230_volume"] = float(stage230_summary.get("volume") or 0)
        summary["stage230_order_ticket"] = str(stage230_summary.get("order_ticket", ""))
        summary["stage230_deal_ticket"] = str(stage230_summary.get("deal_ticket", ""))
        summary["stage230_ledger_rows"] = len(ledger_rows)

        import MetaTrader5 as mt5  # type: ignore
        summary["mt5_module_imported"] = True
        summary["mt5_initialize_ok"] = bool(mt5.initialize())
        try:
            summary["mt5_last_error"] = str(mt5.last_error())
        except Exception:
            summary["mt5_last_error"] = "last_error unavailable"
        if not summary["mt5_initialize_ok"]:
            raise RuntimeError(f"mt5.initialize failed: {summary['mt5_last_error']}")

        account = nt_to_dict(mt5.account_info())
        summary["account_info_exists"] = bool(account)
        demo_ok, demo_evidence = is_demo_account(mt5, account)
        summary["demo_account_confirmed"] = demo_ok
        summary["demo_account_evidence"] = demo_evidence
        write_json(p["account_info"], redact_account_info(account))
        if not demo_ok:
            raise RuntimeError(f"DEMO account not confirmed: {demo_evidence}")

        positions = list_to_dicts(mt5.positions_get(symbol=SYMBOL))
        summary["positions_query_executed"] = True
        summary["positions_total_count"] = len(positions)
        matching_positions = [pos for pos in positions if position_matches_stage230(pos, SYMBOL, 0.01)]
        summary["open_position_match_count"] = len(matching_positions)
        summary["open_positions_tpsl_ok"] = all(position_has_tpsl(pos) for pos in matching_positions) if matching_positions else False
        write_json(p["positions"], {"all_positions_for_symbol": positions, "matching_stage230_positions": matching_positions})

        now = datetime.now()
        date_from = now - timedelta(days=3)
        history_orders = list_to_dicts(mt5.history_orders_get(date_from, now))
        history_deals = list_to_dicts(mt5.history_deals_get(date_from, now))
        summary["history_orders_query_executed"] = True
        summary["history_deals_query_executed"] = True
        summary["history_orders_total_count"] = len(history_orders)
        summary["history_deals_total_count"] = len(history_deals)
        matched_orders = filter_rows(history_orders, summary["stage230_order_ticket"], summary["stage230_deal_ticket"])
        matched_deals = filter_rows(history_deals, summary["stage230_order_ticket"], summary["stage230_deal_ticket"])
        summary["matched_history_order_count"] = len(matched_orders)
        summary["matched_history_deal_count"] = len(matched_deals)
        summary["position_or_history_evidence_exists"] = bool(matching_positions or matched_orders or matched_deals)
        write_json(p["history_orders"], {"matched_orders": matched_orders, "all_orders_window": history_orders})
        write_json(p["history_deals"], {"matched_deals": matched_deals, "all_deals_window": history_deals})
        mt5.shutdown()

    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")
        try:
            if summary.get("mt5_module_imported"):
                mt5.shutdown()  # type: ignore[name-defined]
        except Exception:
            pass

    checks, validation_blockers = validate(summary)
    blockers = summary.get("blockers", []) + validation_blockers
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
    write_json(p["summary"], summary)
    write_paste_me(p["paste"], summary, checks)

    print(f"Stage231 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"open_position_match_count: {summary['open_position_match_count']}")
    print(f"matched_history_order_count: {summary['matched_history_order_count']}")
    print(f"matched_history_deal_count: {summary['matched_history_deal_count']}")
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
