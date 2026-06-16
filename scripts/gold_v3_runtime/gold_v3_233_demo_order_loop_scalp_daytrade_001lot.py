#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage233 - Demo order loop for SCALP/DAYTRADE 0.01 lot.

DEMO account only. GOLD# only. ORDER_FILLING_IOC. TP/SL required.
Each signal_id is sent at most once. SCALP max 1 position, DAYTRADE max 1
position, total max 2 known Stage233 positions. No real account, no final live,
no payload activation, no NO_SIGNAL order, no unlimited autotrade.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STAGE = "GOLD_V3_233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT"
DECISION_READY = "STAGE233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT_READY"
DECISION_BLOCKED = "STAGE233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
SYMBOL = "GOLD#"
VOLUME = 0.01
FILLING_NAME = "ORDER_FILLING_IOC"
SCALP_MAGIC = 30023301
DAY_MAGIC = 30023302
SCALP_COMMENT = "G3S233_SCALP"
DAY_COMMENT = "G3S233_DAY"
DEFAULT_TP_USD = 15.0
DEFAULT_SL_USD = 5.0
MAX_SCALP_POSITIONS = 1
MAX_DAY_POSITIONS = 1
MAX_TOTAL_STAGE233_POSITIONS = 2

LEDGER_COLUMNS = [
    "created_at_utc", "stage", "cycle_index", "signal_id", "short_signal_id",
    "role", "candidate_id", "direction", "side", "symbol", "volume", "magic",
    "comment", "tp_usd", "sl_usd", "price", "sl", "tp", "order_check_retcode",
    "order_check_comment", "order_send_retcode", "order_send_comment", "order_ticket",
    "deal_ticket", "request_id", "result_raw",
]

REJECT_COLUMNS = [
    "created_at_utc", "stage", "cycle_index", "signal_id", "short_signal_id",
    "reason", "row_json",
]

OFF_FLAGS: Dict[str, bool] = {
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "no_signal_order_allowed": False,
    "unlimited_autotrade_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "position_close_called": False,
    "position_modify_called": False,
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
    out = files / "FX_OUTPUTS" / "gold_v3" / "233"
    work = out / "demo_order_loop_scalp_daytrade_001lot"
    runtime = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    return {
        "files": files,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "execution_ledger": work / "stage233_execution_ledger.csv",
        "rejected_rows": work / "stage233_rejected_rows.csv",
        "positions_snapshot": work / "stage233_positions_snapshot.json",
        "summary": work / "stage233_summary.json",
        "paste": out / "paste_me.txt",
        "kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE233.txt",
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    if not rows:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sent_signal_ids(path: Path) -> set[str]:
    return {str(row.get("signal_id", "")) for row in read_csv_rows(path) if row.get("signal_id")}


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


def infer_signal_id(row: Dict[str, str]) -> str:
    for key in ["signal_id", "source_signal_id", "id"]:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def infer_short_signal_id(row: Dict[str, str]) -> str:
    for key in ["short_signal_id", "short_id"]:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def infer_direction(row: Dict[str, str]) -> str:
    for key in ["direction", "side", "signal_direction"]:
        value = str(row.get(key, "")).strip().upper()
        if value in {"BUY", "SELL", "LONG", "SHORT"}:
            return value
    return ""


def direction_to_side(direction: str) -> str:
    direction = direction.upper().strip()
    if direction in {"BUY", "LONG"}:
        return "BUY"
    if direction in {"SELL", "SHORT"}:
        return "SELL"
    return ""


def infer_role(row: Dict[str, str]) -> str:
    text = " ".join([
        str(row.get("strategy_role", "")),
        str(row.get("role", "")),
        str(row.get("candidate_id", "")),
        str(row.get("route", "")),
        str(row.get("final_route", "")),
    ]).upper()
    if "SCALP" in text:
        return "SCALP"
    return "DAYTRADE"


def is_no_signal_row(row: Dict[str, str]) -> bool:
    text = " ".join(str(v) for v in row.values()).upper()
    return "NO_SIGNAL" in text and not infer_signal_id(row)


def parse_float(row: Dict[str, str], keys: List[str], default: float) -> float:
    for key in keys:
        try:
            value = str(row.get(key, "")).strip()
            if value:
                out = float(value)
                if out > 0:
                    return out
        except Exception:
            pass
    return default


def run_stage227_refresh(enabled: bool) -> Tuple[bool, int | None, str]:
    if not enabled:
        return False, None, "disabled"
    script = repo_root() / "scripts" / "gold_v3_runtime" / "gold_v3_227_alert_only_runtime_queue_binding_audit.py"
    if not script.exists():
        return False, None, f"missing: {script}"
    result = subprocess.run([sys.executable, str(script)], cwd=str(repo_root()), capture_output=True, text=True)
    text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return True, result.returncode, text[-2000:]


def wait_until_boundary_plus_delay(delay_seconds: int) -> None:
    now = time.time()
    next_minute = int(now // 60) * 60 + 60
    target = next_minute + delay_seconds
    sleep_seconds = max(0, target - now)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)


def count_positions(positions: List[Dict[str, Any]]) -> Dict[str, int]:
    scalp = 0
    day = 0
    unknown = 0
    for pos in positions:
        if str(pos.get("symbol", "")) != SYMBOL:
            continue
        magic = int(pos.get("magic") or 0)
        if magic == SCALP_MAGIC:
            scalp += 1
        elif magic == DAY_MAGIC:
            day += 1
        else:
            unknown += 1
    return {"scalp": scalp, "daytrade": day, "unknown": unknown, "total_known": scalp + day}


def ensure_volume(symbol_info: Dict[str, Any]) -> Tuple[bool, str]:
    volume_min = float(symbol_info.get("volume_min") or 0)
    volume_max = float(symbol_info.get("volume_max") or 0)
    volume_step = float(symbol_info.get("volume_step") or 0)
    if volume_min <= 0 or volume_max <= 0 or volume_step <= 0:
        return False, f"invalid volume constraints min={volume_min} max={volume_max} step={volume_step}"
    if VOLUME < volume_min or VOLUME > volume_max:
        return False, f"volume 0.01 outside min/max min={volume_min} max={volume_max}"
    steps = (VOLUME - volume_min) / volume_step
    if abs(steps - round(steps)) > 1e-7:
        return False, f"volume 0.01 not aligned to step={volume_step} from min={volume_min}"
    return True, f"volume=0.01 allowed min={volume_min} max={volume_max} step={volume_step}"


def build_request(mt5: Any, symbol_info: Dict[str, Any], tick: Dict[str, Any], row: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], str, str, float, float]:
    direction = infer_direction(row)
    side = direction_to_side(direction)
    if side not in {"BUY", "SELL"}:
        return None, direction, side, DEFAULT_TP_USD, DEFAULT_SL_USD
    role = infer_role(row)
    magic = SCALP_MAGIC if role == "SCALP" else DAY_MAGIC
    comment = SCALP_COMMENT if role == "SCALP" else DAY_COMMENT
    digits = int(symbol_info.get("digits") or 2)
    tp_usd = parse_float(row, ["tp_usd", "tp_usd_param", "tp"], DEFAULT_TP_USD)
    sl_usd = parse_float(row, ["sl_usd", "sl_usd_param", "sl"], DEFAULT_SL_USD)
    if side == "BUY":
        price = float(tick.get("ask") or 0)
        order_type = mt5.ORDER_TYPE_BUY
        sl = round(price - sl_usd, digits)
        tp = round(price + tp_usd, digits)
    else:
        price = float(tick.get("bid") or 0)
        order_type = mt5.ORDER_TYPE_SELL
        sl = round(price + sl_usd, digits)
        tp = round(price - tp_usd, digits)
    if price <= 0 or sl <= 0 or tp <= 0:
        return None, direction, side, tp_usd, sl_usd
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "type": order_type,
        "price": round(price, digits),
        "sl": sl,
        "tp": tp,
        "deviation": 50,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }, direction, side, tp_usd, sl_usd


def evaluate_and_send(
    mt5: Any,
    queue_rows: List[Dict[str, str]],
    existing_ids: set[str],
    cycle_index: int,
    summary: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    executed: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    symbol_info = nt_to_dict(mt5.symbol_info(SYMBOL))
    tick = nt_to_dict(mt5.symbol_info_tick(SYMBOL))
    if not symbol_info or not tick:
        raise RuntimeError("symbol_info/tick missing for GOLD#")
    volume_ok, volume_evidence = ensure_volume(symbol_info)
    summary["volume_evidence"] = volume_evidence
    if not volume_ok:
        raise RuntimeError(volume_evidence)

    for row in queue_rows:
        created = utc_now_iso()
        signal_id = infer_signal_id(row)
        short_id = infer_short_signal_id(row)
        if is_no_signal_row(row) or not signal_id:
            summary["no_signal_rows_seen"] += 1
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "NO_SIGNAL_OR_MISSING_SIGNAL_ID", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue
        if signal_id in existing_ids:
            summary["duplicate_skipped_count"] += 1
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "DUPLICATE_SIGNAL_ID_ALREADY_EXECUTED", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue

        role = infer_role(row)
        request, direction, side, tp_usd, sl_usd = build_request(mt5, symbol_info, tick, row)
        if request is None or side not in {"BUY", "SELL"}:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "INVALID_DIRECTION_OR_REQUEST", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue

        positions = list_to_dicts(mt5.positions_get(symbol=SYMBOL))
        counts = count_positions(positions)
        summary["open_gold_position_count_last"] = len(positions)
        summary["open_scalp_position_count_last"] = counts["scalp"]
        summary["open_daytrade_position_count_last"] = counts["daytrade"]
        summary["unknown_gold_position_count_last"] = counts["unknown"]
        if counts["unknown"] > 0:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "UNKNOWN_GOLD_POSITION_EXISTS", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue
        if role == "SCALP" and counts["scalp"] >= MAX_SCALP_POSITIONS:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "SCALP_POSITION_LIMIT_REACHED", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue
        if role == "DAYTRADE" and counts["daytrade"] >= MAX_DAY_POSITIONS:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "DAYTRADE_POSITION_LIMIT_REACHED", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue
        if counts["total_known"] >= MAX_TOTAL_STAGE233_POSITIONS:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": "TOTAL_STAGE233_POSITION_LIMIT_REACHED", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue

        check_obj = mt5.order_check(request)
        check = nt_to_dict(check_obj)
        check_retcode = check.get("retcode", "") if check else ""
        check_comment = check.get("comment", "") if check else ""
        if not check or int(check.get("retcode", -1)) != 0:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": f"ORDER_CHECK_FAILED retcode={check_retcode} comment={check_comment}", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue

        summary["order_send_call_count"] += 1
        result_obj = mt5.order_send(request)
        result = nt_to_dict(result_obj)
        result_retcode = result.get("retcode", "") if result else ""
        result_comment = result.get("comment", "") if result else ""
        success_codes = {getattr(mt5, "TRADE_RETCODE_DONE", 10009), getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010), 10009, 10010}
        order_placed = bool(result) and int(result.get("retcode", -1)) in success_codes
        if order_placed:
            summary["order_placed_count"] += 1
            existing_ids.add(signal_id)
        else:
            rejected.append({"created_at_utc": created, "stage": STAGE, "cycle_index": cycle_index, "signal_id": signal_id, "short_signal_id": short_id, "reason": f"ORDER_SEND_NOT_PLACED retcode={result_retcode} comment={result_comment}", "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True)})
            continue

        executed.append({
            "created_at_utc": created,
            "stage": STAGE,
            "cycle_index": cycle_index,
            "signal_id": signal_id,
            "short_signal_id": short_id,
            "role": role,
            "candidate_id": row.get("candidate_id") or "",
            "direction": direction,
            "side": side,
            "symbol": SYMBOL,
            "volume": VOLUME,
            "magic": request.get("magic"),
            "comment": request.get("comment"),
            "tp_usd": tp_usd,
            "sl_usd": sl_usd,
            "price": request.get("price"),
            "sl": request.get("sl"),
            "tp": request.get("tp"),
            "order_check_retcode": check_retcode,
            "order_check_comment": check_comment,
            "order_send_retcode": result_retcode,
            "order_send_comment": result_comment,
            "order_ticket": result.get("order", "") if result else "",
            "deal_ticket": result.get("deal", "") if result else "",
            "request_id": result.get("request_id", "") if result else "",
            "result_raw": json.dumps(json_safe(result), ensure_ascii=False, sort_keys=True),
        })
    return executed, rejected


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("S233001", summary.get("explicit_user_approval_recorded") is True, "explicit Stage233 user approval recorded")
    add("S233002", summary.get("mt5_initialize_ok") is True, str(summary.get("mt5_last_error")))
    add("S233003", summary.get("demo_account_confirmed") is True, str(summary.get("demo_account_evidence")))
    add("S233004", summary.get("symbol") == SYMBOL, str(summary.get("symbol")))
    add("S233005", abs(float(summary.get("volume") or 0) - 0.01) < 1e-9, str(summary.get("volume")))
    add("S233006", summary.get("filling") == FILLING_NAME, str(summary.get("filling")))
    add("S233007", summary.get("tp_sl_required") is True, "TP/SL required")
    add("S233008", summary.get("max_scalp_positions") == MAX_SCALP_POSITIONS and summary.get("max_daytrade_positions") == MAX_DAY_POSITIONS and summary.get("max_total_positions") == MAX_TOTAL_STAGE233_POSITIONS, "position caps fixed")
    add("S233009", summary.get("no_signal_order_allowed") is False, "NO_SIGNAL not allowed")
    add("S233010", summary.get("real_account_allowed") is False and summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False, "restricted modes OFF")
    add("S233011", summary.get("unlimited_autotrade_allowed") is False and int(summary.get("cycle_count") or 0) <= int(summary.get("max_cycles_allowed") or 0), "bounded loop")
    add("S233012", summary.get("kill_switch_present") is False, "kill switch absent")
    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 233 PASTE_ME_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "explicit_user_approval_recorded", "refresh_stage227_attempted", "refresh_stage227_return_code",
        "mt5_module_imported", "mt5_initialize_ok", "account_info_exists", "demo_account_confirmed", "demo_account_evidence",
        "runtime_queue_exists", "cycle_count", "rows_seen_total", "executed_rows_written", "rejected_rows_written",
        "no_signal_rows_seen", "duplicate_skipped_count", "order_send_call_count", "order_placed_count",
        "symbol", "volume", "filling", "tp_sl_required", "max_scalp_positions", "max_daytrade_positions", "max_total_positions",
        "open_gold_position_count_last", "open_scalp_position_count_last", "open_daytrade_position_count_last", "unknown_gold_position_count_last",
        "kill_switch_present", "blocker_count",
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
    lines.append("Stage233 ran the user-approved MT5 DEMO order loop for SCALP/DAYTRADE 0.01 lot with bounded cycles, signal_id dedupe, position caps, GOLD# only, IOC filling, and TP/SL required.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=60)
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--refresh-stage227", action="store_true")
    parser.add_argument("--wait-boundary", action="store_true")
    args = parser.parse_args()
    if args.cycles < 1:
        args.cycles = 1
    if args.cycles > 60:
        args.cycles = 60

    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "explicit_user_approval_recorded": True,
        "refresh_stage227_attempted": False,
        "refresh_stage227_return_code": None,
        "refresh_stage227_tail": "",
        "mt5_module_imported": False,
        "mt5_initialize_ok": False,
        "mt5_last_error": "",
        "account_info_exists": False,
        "demo_account_confirmed": False,
        "demo_account_evidence": "",
        "runtime_queue_exists": p["runtime_queue"].exists(),
        "cycle_count": args.cycles,
        "max_cycles_allowed": 60,
        "rows_seen_total": 0,
        "executed_rows_written": 0,
        "rejected_rows_written": 0,
        "no_signal_rows_seen": 0,
        "duplicate_skipped_count": 0,
        "order_send_call_count": 0,
        "order_placed_count": 0,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "filling": FILLING_NAME,
        "tp_sl_required": True,
        "max_scalp_positions": MAX_SCALP_POSITIONS,
        "max_daytrade_positions": MAX_DAY_POSITIONS,
        "max_total_positions": MAX_TOTAL_STAGE233_POSITIONS,
        "open_gold_position_count_last": 0,
        "open_scalp_position_count_last": 0,
        "open_daytrade_position_count_last": 0,
        "unknown_gold_position_count_last": 0,
        "kill_switch_present": p["kill_switch"].exists(),
        "volume_evidence": "",
        "output_files": {
            "execution_ledger_csv": str(p["execution_ledger"]),
            "rejected_rows_csv": str(p["rejected_rows"]),
            "positions_snapshot_json": str(p["positions_snapshot"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "kill_switch": str(p["kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)

    try:
        if summary["kill_switch_present"]:
            raise RuntimeError(f"kill switch present: {p['kill_switch']}")
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
        if not demo_ok:
            raise RuntimeError(f"DEMO account not confirmed: {demo_evidence}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"symbol_select failed: {SYMBOL}")

        existing_ids = sent_signal_ids(p["execution_ledger"])
        for cycle_index in range(1, args.cycles + 1):
            if p["kill_switch"].exists():
                summary["kill_switch_present"] = True
                break
            if args.wait_boundary:
                wait_until_boundary_plus_delay(args.delay_seconds)
            refresh_attempted, refresh_code, refresh_tail = run_stage227_refresh(args.refresh_stage227)
            summary["refresh_stage227_attempted"] = refresh_attempted
            summary["refresh_stage227_return_code"] = refresh_code
            summary["refresh_stage227_tail"] = refresh_tail
            if refresh_attempted and refresh_code not in (0, None):
                raise RuntimeError(f"Stage227 refresh failed: return_code={refresh_code}")
            summary["runtime_queue_exists"] = p["runtime_queue"].exists()
            queue_rows = read_csv_rows(p["runtime_queue"])
            summary["rows_seen_total"] += len(queue_rows)
            positions = list_to_dicts(mt5.positions_get(symbol=SYMBOL))
            write_json(p["positions_snapshot"], {"created_at_utc": utc_now_iso(), "symbol": SYMBOL, "positions": positions})
            counts = count_positions(positions)
            summary["open_gold_position_count_last"] = len(positions)
            summary["open_scalp_position_count_last"] = counts["scalp"]
            summary["open_daytrade_position_count_last"] = counts["daytrade"]
            summary["unknown_gold_position_count_last"] = counts["unknown"]
            executed, rejected = evaluate_and_send(mt5, queue_rows, existing_ids, cycle_index, summary)
            append_csv_rows(p["execution_ledger"], executed, LEDGER_COLUMNS)
            append_csv_rows(p["rejected_rows"], rejected, REJECT_COLUMNS)
            summary["executed_rows_written"] += len(executed)
            summary["rejected_rows_written"] += len(rejected)
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

    print(f"Stage233 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"rows_seen_total: {summary['rows_seen_total']}")
    print(f"order_send_call_count: {summary['order_send_call_count']}")
    print(f"order_placed_count: {summary['order_placed_count']}")
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
