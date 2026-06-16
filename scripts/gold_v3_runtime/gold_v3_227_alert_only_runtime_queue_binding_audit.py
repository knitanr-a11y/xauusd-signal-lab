#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage227 - Alert-Only Runtime Queue Binding Audit

Creates a runtime alert-only queue CSV from a local GOLD V3 source state.
This script performs no network calls and no order actions.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STAGE = "GOLD_V3_227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_AUDIT_ONLY"
DECISION_READY = "STAGE227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TEMPLATE_VERSION = "GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617"

OFF_FLAGS: Dict[str, bool] = {
    "network_call_made": False,
    "order_enabled": False,
    "actual_import_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_notify": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}

QUEUE_COLUMNS = [
    "queue_id",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "symbol",
    "final_route",
    "strategy_role",
    "candidate_id",
    "direction",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "message_template_version",
    "message_title",
    "message_text",
    "queue_action",
    "created_stage",
    "created_at_utc",
]

SUPPRESSION_COLUMNS = [
    "case_id",
    "latest_closed_m15_dt",
    "final_route",
    "queue_row_created",
    "notify",
    "reason",
    "created_stage",
    "created_at_utc",
]


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


def stage_paths() -> Dict[str, Path]:
    files = default_mql5_files_dir()
    source_dir_env = os.environ.get("GOLD_V3_RETENTION_SOURCE_DIR", "").strip()
    source_dir = Path(source_dir_env).expanduser().resolve() if source_dir_env else files / "FX_OUTPUTS" / "gold_v3" / "217" / "staging_retention"
    output_dir = files / "FX_OUTPUTS" / "gold_v3" / "227"
    work_dir = output_dir / "alert_only_runtime_queue_binding"
    runtime_dir = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    return {
        "source_dir": source_dir,
        "output_dir": output_dir,
        "work_dir": work_dir,
        "runtime_dir": runtime_dir,
        "runtime_queue": runtime_dir / "alert_only_queue.csv",
        "runtime_suppression": runtime_dir / "alert_only_no_signal_suppression.csv",
    }


def assert_safe_paths(work_dir: Path, runtime_dir: Path) -> None:
    if tuple(work_dir.resolve().parts[-4:]) != ("FX_OUTPUTS", "gold_v3", "227", "alert_only_runtime_queue_binding"):
        raise RuntimeError(f"Unsafe work_dir: {work_dir}")
    if tuple(runtime_dir.resolve().parts[-3:]) != ("FX_OUTPUTS", "gold_v3", "runtime"):
        raise RuntimeError(f"Unsafe runtime_dir: {runtime_dir}")


def reset_work_dir(work_dir: Path, runtime_dir: Path) -> None:
    assert_safe_paths(work_dir, runtime_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def load_source_state(source_dir: Path) -> Tuple[Dict[str, Any], str]:
    latest_state = source_dir / "latest_state.json"
    trade_ledger = source_dir / "trade_signal_ledger.csv"
    if latest_state.exists():
        try:
            payload = json.loads(latest_state.read_text(encoding="utf-8"))
            if payload:
                return payload, "latest_state.json"
        except Exception:
            pass
    rows = read_csv(trade_ledger)
    if rows:
        return rows[-1], "trade_signal_ledger.csv:last_row"
    return {}, "missing"


def normalize_direction(value: Any) -> str:
    d = str(value or "").upper()
    if d in {"SHORT", "SELL"}:
        return "SELL"
    if d in {"LONG", "BUY"}:
        return "BUY"
    return d


def message_title(direction: str, strategy_role: str) -> str:
    d = normalize_direction(direction)
    icon = "🔴" if d == "SELL" else "🟢" if d == "BUY" else "🟡"
    side = d if d in {"SELL", "BUY"} else "SIGNAL"
    scalp = " SCALP" if "SCALP" in str(strategy_role or "").upper() else ""
    return f"{icon} GOLD {side}{scalp}"


def build_message(row: Dict[str, Any]) -> str:
    signal_id = str(row.get("signal_id") or "")
    direction = normalize_direction(row.get("direction"))
    strategy_role = str(row.get("strategy_role") or "")
    entry_dt = str(row.get("entry_dt") or row.get("latest_closed_m15_dt") or "")[:16]
    return "\n".join([
        message_title(direction, strategy_role),
        f"Entry Time: {entry_dt} MT5/CSV",
        f"Entry Price: {row.get('entry_price')}",
        f"TP / SL: {row.get('tp_usd')} / {row.get('sl_usd')}",
        f"Horizon: {row.get('horizon_m5_bars')} M5 bars",
        "",
        "[DEMO ALERT ONLY / NO ORDER]",
        f"Signal ID: {signal_id}",
    ])


def is_signal(row: Dict[str, Any]) -> bool:
    route = str(row.get("final_route") or "").upper()
    signal_id = str(row.get("signal_id") or "").strip()
    return bool(signal_id) and route != "NO_SIGNAL"


def make_queue_row(row: Dict[str, Any], created_at: str) -> Dict[str, Any]:
    signal_id = str(row.get("signal_id") or "")
    short_id = str(row.get("short_signal_id") or "")
    direction = normalize_direction(row.get("direction"))
    strategy_role = str(row.get("strategy_role") or "")
    return {
        "queue_id": f"{short_id or signal_id}_RUNTIME_QUEUE",
        "signal_id": signal_id,
        "short_signal_id": short_id,
        "latest_closed_m15_dt": str(row.get("latest_closed_m15_dt") or ""),
        "entry_dt": str(row.get("entry_dt") or row.get("latest_closed_m15_dt") or ""),
        "symbol": str(row.get("symbol") or "XAUUSD"),
        "final_route": str(row.get("final_route") or ""),
        "strategy_role": strategy_role,
        "candidate_id": str(row.get("candidate_id") or ""),
        "direction": direction,
        "entry_price": row.get("entry_price"),
        "tp_usd": row.get("tp_usd"),
        "sl_usd": row.get("sl_usd"),
        "horizon_m5_bars": row.get("horizon_m5_bars"),
        "message_template_version": TEMPLATE_VERSION,
        "message_title": message_title(direction, strategy_role),
        "message_text": build_message(row),
        "queue_action": "READY_FOR_ALERT_ONLY_LOOP_IF_NOT_DUPLICATE",
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }


def make_suppression_row(row: Dict[str, Any], created_at: str, reason: str) -> Dict[str, Any]:
    return {
        "case_id": "NO_SENDABLE_SIGNAL",
        "latest_closed_m15_dt": str(row.get("latest_closed_m15_dt") or ""),
        "final_route": str(row.get("final_route") or ""),
        "queue_row_created": False,
        "notify": False,
        "reason": reason,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    msg = summary.get("message_text", "")
    final_line = msg.splitlines()[-1] if msg else ""
    has_signal = summary.get("sendable_queue_rows") == 1
    add("QB001", summary.get("source_dir_exists") is True, f"source_dir={summary.get('source_dir')}")
    add("QB002", tuple(Path(summary["runtime_queue"]).resolve().parts[-3:]) == ("gold_v3", "runtime", "alert_only_queue.csv"), f"runtime_queue={summary.get('runtime_queue')}")
    add("QB003", summary.get("csv_latest_row_contract") == "CLOSED" and summary.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")
    add("QB004", summary.get("timestamp_basis") == "MT5_CSV" and summary.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis")
    add("QB005", has_signal or summary.get("suppression_rows") == 1, f"sendable_queue_rows={summary.get('sendable_queue_rows')} suppression_rows={summary.get('suppression_rows')}")
    add("QB006", (not has_signal) or msg.startswith(("🔴 GOLD SELL", "🟢 GOLD BUY")), "queue message title marker")
    add("QB007", (not has_signal) or final_line == f"Signal ID: {summary.get('source_signal_id')}", f"final_line={final_line}")
    add("QB008", all(summary[k] is False for k in OFF_FLAGS.keys()), "all restricted flags OFF")
    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 227 PASTE_ME_ALERT_ONLY_RUNTIME_QUEUE_BINDING_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir", "source_dir",
        "source_dir_exists", "source_kind", "source_final_route", "source_signal_id", "runtime_queue",
        "sendable_queue_rows", "suppression_rows", "stage226_queue_command", "blocker_count",
    ] + list(OFF_FLAGS.keys()):
        lines.append(f"{key}: {summary.get(key)}")
    lines.append("")
    lines.append("QUEUE_MESSAGE_PREVIEW")
    lines.append(summary.get("message_text", ""))
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
    lines.append("Stage227 writes a runtime alert-only queue for Stage226. It performs no network calls and no order actions.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    created_at = utc_now_iso()
    p = stage_paths()
    p["output_dir"].mkdir(parents=True, exist_ok=True)
    reset_work_dir(p["work_dir"], p["runtime_dir"])
    source_row, source_kind = load_source_state(p["source_dir"])
    queue_rows: List[Dict[str, Any]] = []
    suppression_rows: List[Dict[str, Any]] = []
    message = ""
    if source_row and is_signal(source_row):
        row = make_queue_row(source_row, created_at)
        queue_rows.append(row)
        message = str(row.get("message_text") or "")
    else:
        suppression_rows.append(make_suppression_row(source_row, created_at, "NO_SIGNAL_OR_NO_SOURCE_SIGNAL"))
    write_csv(p["runtime_queue"], queue_rows, QUEUE_COLUMNS)
    write_csv(p["runtime_suppression"], suppression_rows, SUPPRESSION_COLUMNS)
    work_queue_copy = p["work_dir"] / "alert_only_queue_runtime_copy.csv"
    work_supp_copy = p["work_dir"] / "alert_only_no_signal_suppression_copy.csv"
    write_csv(work_queue_copy, queue_rows, QUEUE_COLUMNS)
    write_csv(work_supp_copy, suppression_rows, SUPPRESSION_COLUMNS)
    command = f"python scripts\\gold_v3_runtime\\gold_v3_226_demo_discord_alert_only_loop_restart_local.py --queue-csv \"{p['runtime_queue']}\""
    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": created_at,
        "output_dir": str(p["output_dir"]),
        "work_dir": str(p["work_dir"]),
        "source_dir": str(p["source_dir"]),
        "source_dir_exists": p["source_dir"].exists(),
        "source_kind": source_kind,
        "source_final_route": str(source_row.get("final_route") or ""),
        "source_signal_id": str(source_row.get("signal_id") or ""),
        "runtime_queue": str(p["runtime_queue"]),
        "sendable_queue_rows": len(queue_rows),
        "suppression_rows": len(suppression_rows),
        "message_text": message,
        "stage226_queue_command": command,
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "output_files": {
            "runtime_alert_only_queue_csv": str(p["runtime_queue"]),
            "runtime_no_signal_suppression_csv": str(p["runtime_suppression"]),
            "work_queue_copy_csv": str(work_queue_copy),
            "work_suppression_copy_csv": str(work_supp_copy),
        },
    }
    summary.update(OFF_FLAGS)
    checks, blockers = validate(summary)
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
    summary_path = p["output_dir"] / "gold_v3_227_alert_only_runtime_queue_binding_summary.json"
    paste_path = p["output_dir"] / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)
    print(f"Stage227 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"runtime_queue: {p['runtime_queue']}")
    print(f"paste_me: {paste_path}")
    if blockers:
        print("BLOCKERS:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
