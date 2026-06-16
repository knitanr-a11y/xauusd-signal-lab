#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage232 - Demo Order Loop Dry-Run Audit

Reads Stage227/228 runtime queue and records planned demo orders only.
No mt5.order_send. No order placement. No close/modify.
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
from typing import Any, Dict, List, Tuple


STAGE = "GOLD_V3_232_DEMO_ORDER_LOOP_DRY_RUN_AUDIT"
DECISION_READY = "STAGE232_DEMO_ORDER_LOOP_DRY_RUN_READY"
DECISION_BLOCKED = "STAGE232_DEMO_ORDER_LOOP_DRY_RUN_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
SYMBOL = "GOLD#"
VOLUME = 0.01
FILLING = "ORDER_FILLING_IOC"
TP_USD = 15.0
SL_USD = 5.0

PLANNED_COLUMNS = [
    "created_at_utc",
    "stage",
    "cycle_index",
    "signal_id",
    "short_signal_id",
    "source_route",
    "candidate_id",
    "direction",
    "symbol",
    "side",
    "volume",
    "filling",
    "tp_usd",
    "sl_usd",
    "dry_run_action",
    "reason",
]

REJECT_COLUMNS = [
    "created_at_utc",
    "stage",
    "cycle_index",
    "signal_id",
    "short_signal_id",
    "reason",
    "row_json",
]

OFF_FLAGS: Dict[str, bool] = {
    "order_send_called": False,
    "order_placed": False,
    "new_order_called": False,
    "close_called": False,
    "modify_called": False,
    "position_close_called": False,
    "position_modify_called": False,
    "autotrade_live_enabled": False,
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
    out = files / "FX_OUTPUTS" / "gold_v3" / "232"
    work = out / "demo_order_loop_dry_run"
    runtime = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    return {
        "files": files,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "queue_snapshot": work / "stage232_runtime_queue_snapshot.csv",
        "planned_ledger": work / "stage232_planned_order_dry_run_ledger.csv",
        "rejected_rows": work / "stage232_rejected_rows.csv",
        "positions": work / "stage232_positions_snapshot.json",
        "summary": work / "stage232_summary.json",
        "paste": out / "paste_me.txt",
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


def write_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["empty"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    if not rows:
        if not path.exists():
            write_csv_rows(path, [], fieldnames)
        return
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def planned_signal_ids(path: Path) -> set[str]:
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


def is_no_signal_row(row: Dict[str, str]) -> bool:
    text = " ".join(str(v) for v in row.values()).upper()
    return "NO_SIGNAL" in text and not infer_signal_id(row)


def run_stage227_refresh(enabled: bool) -> Tuple[bool, int | None, str]:
    if not enabled:
        return False, None, "disabled"
    script = repo_root() / "scripts" / "gold_v3_runtime" / "gold_v3_227_alert_only_runtime_queue_binding_audit.py"
    if not script.exists():
        return False, None, f"missing: {script}"
    cmd = [sys.executable, str(script)]
    result = subprocess.run(cmd, cwd=str(repo_root()), capture_output=True, text=True)
    text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return True, result.returncode, text[-2000:]


def wait_until_boundary_plus_delay(delay_seconds: int) -> None:
    now = time.time()
    next_minute = int(now // 60) * 60 + 60
    target = next_minute + delay_seconds
    sleep_seconds = max(0, target - now)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)


def evaluate_rows(
    queue_rows: List[Dict[str, str]],
    existing_planned_ids: set[str],
    open_position_count: int,
    cycle_index: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    planned: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    no_signal_count = 0
    duplicate_count = 0

    for row in queue_rows:
        signal_id = infer_signal_id(row)
        short_signal_id = infer_short_signal_id(row)
        created = utc_now_iso()

        if is_no_signal_row(row) or not signal_id:
            no_signal_count += 1
            rejected.append({
                "created_at_utc": created,
                "stage": STAGE,
                "cycle_index": cycle_index,
                "signal_id": signal_id,
                "short_signal_id": short_signal_id,
                "reason": "NO_SIGNAL_OR_MISSING_SIGNAL_ID",
                "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            })
            continue

        if signal_id in existing_planned_ids:
            duplicate_count += 1
            rejected.append({
                "created_at_utc": created,
                "stage": STAGE,
                "cycle_index": cycle_index,
                "signal_id": signal_id,
                "short_signal_id": short_signal_id,
                "reason": "DUPLICATE_SIGNAL_ID_ALREADY_PLANNED",
                "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            })
            continue

        if open_position_count > 0:
            rejected.append({
                "created_at_utc": created,
                "stage": STAGE,
                "cycle_index": cycle_index,
                "signal_id": signal_id,
                "short_signal_id": short_signal_id,
                "reason": "EXISTING_GOLD_POSITION_BLOCKS_NEW_PLAN",
                "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            })
            continue

        direction = infer_direction(row)
        side = direction_to_side(direction)
        if side not in {"BUY", "SELL"}:
            rejected.append({
                "created_at_utc": created,
                "stage": STAGE,
                "cycle_index": cycle_index,
                "signal_id": signal_id,
                "short_signal_id": short_signal_id,
                "reason": "DIRECTION_NOT_BUY_SELL_LONG_SHORT",
                "row_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            })
            continue

        planned.append({
            "created_at_utc": created,
            "stage": STAGE,
            "cycle_index": cycle_index,
            "signal_id": signal_id,
            "short_signal_id": short_signal_id,
            "source_route": row.get("route") or row.get("final_route") or row.get("source_route") or "",
            "candidate_id": row.get("candidate_id") or "",
            "direction": direction,
            "symbol": SYMBOL,
            "side": side,
            "volume": VOLUME,
            "filling": FILLING,
            "tp_usd": TP_USD,
            "sl_usd": SL_USD,
            "dry_run_action": "WOULD_SEND_DEMO_ORDER_IN_STAGE233_NOT_NOW",
            "reason": "DRY_RUN_ONLY_ORDER_SEND_DISABLED",
        })
        existing_planned_ids.add(signal_id)

    return planned, rejected, no_signal_count, duplicate_count


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("D232001", summary.get("mt5_initialize_ok") is True, str(summary.get("mt5_last_error")))
    add("D232002", summary.get("demo_account_confirmed") is True, str(summary.get("demo_account_evidence")))
    add("D232003", summary.get("runtime_queue_exists") is True or summary.get("queue_empty_allowed") is True, "runtime queue exists or empty allowed")
    add("D232004", summary.get("positions_query_executed") is True, "positions_get executed")
    add("D232005", summary.get("symbol") == SYMBOL, str(summary.get("symbol")))
    add("D232006", abs(float(summary.get("volume") or 0) - 0.01) < 1e-9, str(summary.get("volume")))
    add("D232007", summary.get("filling") == FILLING, str(summary.get("filling")))
    add("D232008", summary.get("tp_sl_design_included") is True, "TP/SL design included")
    add("D232009", summary.get("order_send_called") is False and summary.get("order_placed") is False, "order_send disabled")
    add("D232010", summary.get("new_order_called") is False and summary.get("close_called") is False and summary.get("modify_called") is False, "no new/close/modify")
    add("D232011", summary.get("no_signal_order_allowed") is False, "NO_SIGNAL order disabled")
    add("D232012", summary.get("autotrade_live_enabled") is False and summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False, "restricted modes OFF")
    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 232 PASTE_ME_DEMO_ORDER_LOOP_DRY_RUN_AUDIT")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "refresh_stage227_attempted", "refresh_stage227_return_code",
        "mt5_module_imported", "mt5_initialize_ok", "account_info_exists", "demo_account_confirmed", "demo_account_evidence",
        "runtime_queue_exists", "runtime_queue_rows", "cycle_count", "rows_seen_total", "planned_rows_written", "rejected_rows_written",
        "no_signal_rows_seen", "duplicate_skipped_count", "positions_query_executed", "open_gold_position_count",
        "symbol", "volume", "filling", "tp_sl_design_included", "queue_empty_allowed", "blocker_count",
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
    lines.append("Stage232 evaluated the runtime queue for demo order-loop eligibility in dry-run mode only. It did not call order_send and did not place, close, or modify any order or position.")
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
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--refresh-stage227", action="store_true")
    parser.add_argument("--wait-boundary", action="store_true")
    args = parser.parse_args()

    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
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
        "runtime_queue_rows": 0,
        "cycle_count": max(1, args.cycles),
        "rows_seen_total": 0,
        "planned_rows_written": 0,
        "rejected_rows_written": 0,
        "no_signal_rows_seen": 0,
        "duplicate_skipped_count": 0,
        "positions_query_executed": False,
        "open_gold_position_count": 0,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "filling": FILLING,
        "tp_sl_design_included": True,
        "queue_empty_allowed": True,
        "output_files": {
            "runtime_queue_snapshot_csv": str(p["queue_snapshot"]),
            "planned_order_dry_run_ledger_csv": str(p["planned_ledger"]),
            "rejected_rows_csv": str(p["rejected_rows"]),
            "positions_snapshot_json": str(p["positions"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
        },
    }
    summary.update(OFF_FLAGS)

    try:
        refresh_attempted, refresh_code, refresh_tail = run_stage227_refresh(args.refresh_stage227)
        summary["refresh_stage227_attempted"] = refresh_attempted
        summary["refresh_stage227_return_code"] = refresh_code
        summary["refresh_stage227_tail"] = refresh_tail
        if refresh_attempted and refresh_code not in (0, None):
            raise RuntimeError(f"Stage227 refresh failed: return_code={refresh_code}")

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

        positions = list_to_dicts(mt5.positions_get(symbol=SYMBOL))
        summary["positions_query_executed"] = True
        summary["open_gold_position_count"] = len(positions)
        write_json(p["positions"], {"symbol": SYMBOL, "positions": positions})
        mt5.shutdown()

        existing_ids = planned_signal_ids(p["planned_ledger"])
        all_queue_rows: List[Dict[str, str]] = []
        for cycle_index in range(1, max(1, args.cycles) + 1):
            if args.wait_boundary:
                wait_until_boundary_plus_delay(args.delay_seconds)
            summary["runtime_queue_exists"] = p["runtime_queue"].exists()
            queue_rows = read_csv_rows(p["runtime_queue"])
            all_queue_rows.extend(queue_rows)
            summary["rows_seen_total"] += len(queue_rows)
            planned, rejected, no_signal_count, duplicate_count = evaluate_rows(
                queue_rows=queue_rows,
                existing_planned_ids=existing_ids,
                open_position_count=int(summary["open_gold_position_count"]),
                cycle_index=cycle_index,
            )
            append_csv_rows(p["planned_ledger"], planned, PLANNED_COLUMNS)
            append_csv_rows(p["rejected_rows"], rejected, REJECT_COLUMNS)
            summary["planned_rows_written"] += len(planned)
            summary["rejected_rows_written"] += len(rejected)
            summary["no_signal_rows_seen"] += no_signal_count
            summary["duplicate_skipped_count"] += duplicate_count

        summary["runtime_queue_rows"] = len(all_queue_rows)
        write_csv_rows(p["queue_snapshot"], all_queue_rows)

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

    print(f"Stage232 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"rows_seen_total: {summary['rows_seen_total']}")
    print(f"planned_rows_written: {summary['planned_rows_written']}")
    print(f"rejected_rows_written: {summary['rejected_rows_written']}")
    print(f"order_send_called: {summary['order_send_called']}")
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
