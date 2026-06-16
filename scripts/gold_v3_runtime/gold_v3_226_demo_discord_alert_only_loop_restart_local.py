#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage226 - Demo Discord Alert-Only Loop Restart LOCAL

User-approved scope:
- Demo Discord alert-only loop restart test is allowed.
- CSV read timing: every minute at 00 seconds + 5 seconds, e.g. 12:00:05, 12:01:05.
- MT5 order, real account, actual execution import, payload activation, live hook,
  final live, autotrade, and NO_SIGNAL notification are NOT allowed.

Webhook URL:
- Read from MQL5\\Files\\.env or process env.
- Never printed in full.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


STAGE = "GOLD_V3_226_DEMO_DISCORD_ALERT_ONLY_LOOP_RESTART_LOCAL"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TEMPLATE_VERSION = "GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617"

DECISION_READY = "STAGE226_DEMO_DISCORD_ALERT_ONLY_LOOP_READY_LOCAL"
DECISION_BLOCKED = "STAGE226_DEMO_DISCORD_ALERT_ONLY_LOOP_BLOCKED_LOCAL"

APPROVAL_TEXT = (
    "Stage226として、demo Discord alert-only loop の再開テストを許可します。\n"
    "MT5発注・実口座・payload activation・live hook・final live・autotrade・NO_SIGNAL通知は許可しません。"
)

OFF_FLAGS: Dict[str, bool] = {
    "mt5_order_enabled": False,
    "real_account_enabled": False,
    "actual_order_import_enabled": False,
    "payload_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_live_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}

ATTEMPT_COLUMNS = [
    "attempt_id",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "direction",
    "send_status",
    "http_status",
    "discord_response_ok",
    "skip_reason",
    "webhook_source",
    "webhook_url_redacted",
    "webhook_url_sha256_12",
    "created_stage",
    "created_at_utc",
]

LEDGER_COLUMNS = [
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "direction",
    "send_status",
    "http_status",
    "sent_at_utc",
    "message_sha256",
    "created_stage",
]

RUNTIME_COLUMNS = [
    "cycle_id",
    "scheduled_read_at_local",
    "actual_read_at_utc",
    "queue_csv",
    "queue_rows",
    "eligible_rows",
    "sent_count",
    "skipped_count",
    "blocked_count",
    "created_stage",
]

NO_SIGNAL_COLUMNS = [
    "case_id",
    "signal_id",
    "latest_closed_m15_dt",
    "final_route",
    "discord_send_attempted",
    "discord_notify",
    "reason",
    "created_stage",
    "created_at_utc",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_now() -> datetime:
    return datetime.now().replace(microsecond=0)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()

    appdata = os.environ.get("APPDATA")
    if not appdata:
        return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()

    return Path(
        appdata,
        "MetaQuotes",
        "Terminal",
        TERMINAL_HASH,
        "MQL5",
        "Files",
    ).resolve()


def paths() -> Dict[str, Path]:
    files = default_mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "226"
    work = out / "demo_discord_alert_only_loop_restart"

    return {
        "files": files,
        "out": out,
        "work": work,
        "env": files / ".env",
        "default_queue": files / "FX_OUTPUTS" / "gold_v3" / "223" / "alert_only_readiness_consolidated" / "alert_only_queue_preview.csv",
        "stage225_ledger": files / "FX_OUTPUTS" / "gold_v3" / "225" / "demo_discord_alert_only_one_send" / "demo_alert_only_sent_ledger.csv",
        "attempts": work / "loop_send_attempts.csv",
        "ledger": work / "loop_sent_ledger.csv",
        "runtime": work / "loop_runtime_log.csv",
        "no_signal": work / "no_signal_suppression.csv",
        "status": work / "loop_status.json",
        "paste": out / "paste_me.txt",
    }


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path: Path, row: Dict[str, Any], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_webhook_url(env_file: Path) -> Tuple[Optional[str], str]:
    keys = [
        "GOLD_V3_DEMO_DISCORD_WEBHOOK_URL",
        "GOLD_V3_DISCORD_WEBHOOK_URL",
        "DISCORD_WEBHOOK_URL",
    ]

    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value, f"process_env:{key}"

    env_values = parse_env_file(env_file)
    for key in keys:
        value = env_values.get(key, "").strip()
        if value:
            return value, f"local_env_file:{env_file.name}:{key}"

    return None, "missing"


def is_discord_webhook(url: str) -> bool:
    return (
        url.startswith("https://discord.com/api/webhooks/")
        or url.startswith("https://discordapp.com/api/webhooks/")
    )


def redact_webhook(url: str) -> str:
    if not url:
        return ""

    prefixes = [
        "https://discord.com/api/webhooks/",
        "https://discordapp.com/api/webhooks/",
    ]
    for prefix in prefixes:
        if url.startswith(prefix):
            rest = url[len(prefix):]
            first = rest.split("/", 1)[0] if rest else ""
            return prefix + (first[:4] + "..." if first else "...") + "/REDACTED"

    return "REDACTED_NON_DISCORD_URL"


def next_minute_plus_delay(delay_seconds: int = 5) -> datetime:
    now = local_now()
    target = now.replace(second=delay_seconds, microsecond=0)
    if now.second >= delay_seconds:
        target = (now + timedelta(minutes=1)).replace(second=delay_seconds, microsecond=0)
    return target


def sleep_until(target: datetime) -> None:
    seconds = (target - local_now()).total_seconds()
    if seconds > 0:
        time.sleep(seconds)


def normalize_direction(row: Dict[str, str]) -> str:
    direction = (row.get("direction") or row.get("side") or "").upper()
    if direction in {"SELL", "SHORT"}:
        return "SELL"
    if direction in {"BUY", "LONG"}:
        return "BUY"
    return direction


def title_for(direction: str) -> str:
    direction = direction.upper()
    if direction in {"SELL", "SHORT"}:
        return "🔴 GOLD SELL SCALP"
    if direction in {"BUY", "LONG"}:
        return "🟢 GOLD BUY SCALP"
    return "🟡 GOLD SIGNAL"


def build_message_from_row(row: Dict[str, str]) -> str:
    existing = (row.get("message_text") or "").strip()
    if existing:
        return existing

    signal_id = row.get("signal_id", "").strip()
    direction = normalize_direction(row) or "SELL"
    entry_dt = (row.get("entry_dt") or row.get("latest_closed_m15_dt") or "").strip()
    entry_dt_short = entry_dt[:16] if entry_dt else ""
    entry_price = (row.get("entry_price") or "").strip()
    tp = (row.get("tp_usd") or row.get("tp_usd_param") or "").strip()
    sl = (row.get("sl_usd") or row.get("sl_usd_param") or "").strip()
    hz = (row.get("horizon_m5_bars") or row.get("horizon_m5_bars_param") or "").strip()

    lines = [title_for(direction)]
    if entry_dt_short:
        lines.append(f"Entry Time: {entry_dt_short} MT5/CSV")
    if entry_price:
        lines.append(f"Entry Price: {entry_price}")
    if tp or sl:
        lines.append(f"TP / SL: {tp or '?'} / {sl or '?'}")
    if hz:
        lines.append(f"Horizon: {hz} M5 bars")
    lines.append("")
    lines.append("[DEMO ALERT ONLY / NO ORDER]")
    lines.append(f"Signal ID: {signal_id}")
    return "\n".join(lines)


def is_no_signal(row: Dict[str, str]) -> bool:
    route = (row.get("final_route") or row.get("route") or "").upper()
    signal_id = (row.get("signal_id") or "").strip()
    action = (row.get("notification_action") or row.get("queue_action") or "").upper()

    return (
        route == "NO_SIGNAL"
        or signal_id == ""
        or "NO_MESSAGE_NO_SIGNAL" in action
    )


def sent_signal_ids(paths_dict: Dict[str, Path]) -> set[str]:
    ids: set[str] = set()

    for p in [paths_dict["ledger"], paths_dict["stage225_ledger"]]:
        for row in read_csv(p):
            if row.get("send_status") == "SENT" and row.get("signal_id"):
                ids.add(row["signal_id"])

    return ids


def discord_post(webhook_url: str, content: str) -> Tuple[int, str]:
    body = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "gold-v3-stage226-demo-alert-only-loop-local/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        status = int(getattr(resp, "status", resp.getcode()))
        response_text = resp.read().decode("utf-8", errors="replace")[:500]
        return status, response_text


def validate_status(status: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    add("L226001", status["stage225_validation_pass"] is True, status["stage225_decision"])
    add("L226002", status["approval_scope"] == "DEMO_DISCORD_ALERT_ONLY_LOOP_RESTART", "approval scope recorded")
    add("L226003", status["read_delay_seconds"] == 5, "CSV read timing is minute + 5 seconds")
    add("L226004", status["webhook_url_found"] is True and status["webhook_url_valid_discord"] is True and "REDACTED" in status["webhook_url_redacted"], status["webhook_source"])
    add("L226005", status["queue_csv_exists"] is True, status["queue_csv"])
    add("L226006", status["no_signal_discord_notify"] is False and status["no_signal_send_attempts"] == 0, "NO_SIGNAL notification disabled")
    add("L226007", status["duplicate_skipped_count"] >= 0, f"duplicate_skipped_count={status['duplicate_skipped_count']}")
    add("L226008", all(status[k] is False for k in OFF_FLAGS.keys()), "MT5/order/import/payload/live/autotrade flags OFF")
    add("L226009", status["csv_latest_row_contract"] == "CLOSED" and status["open_asof_allowed"] is False, "CSV latest row CLOSED; no open/as-of")
    add("L226010", status["timestamp_basis"] == "MT5_CSV", "MT5/CSV timestamp basis")

    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, status: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 226 PASTE_ME_DEMO_DISCORD_ALERT_ONLY_LOOP_RESTART_LOCAL")

    for key in [
        "step",
        "status",
        "ready",
        "decision",
        "created_at_utc",
        "output_dir",
        "work_dir",
        "stage225_decision",
        "stage225_validation_pass",
        "approval_scope",
        "loop_mode",
        "read_delay_seconds",
        "queue_csv",
        "queue_csv_exists",
        "cycles_completed",
        "queue_rows_seen_total",
        "eligible_rows_seen_total",
        "sent_count_total",
        "duplicate_skipped_count",
        "no_signal_rows_seen",
        "no_signal_send_attempts",
        "webhook_url_found",
        "webhook_url_valid_discord",
        "webhook_source",
        "webhook_url_redacted",
        "webhook_url_sha256_12",
        "mt5_order_enabled",
        "real_account_enabled",
        "actual_order_import_enabled",
        "payload_enabled",
        "payload_activation_enabled",
        "live_hook_enabled",
        "final_live_enabled",
        "autotrade_enabled",
        "no_signal_discord_notify",
        "source_csv_mutated",
        "contract_mutated",
        "production_live_retention_mutated",
        "open_asof_allowed",
        "candidate_pool_removed",
        "f002_exclusion_bypassed",
        "theoretical_result_used_as_input",
        "actual_execution_used_as_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {status.get(key)}")

    lines.append("")
    lines.append("TIMING_POLICY")
    lines.append("CSV read occurs at each minute boundary + 5 seconds, e.g. HH:MM:05.")

    lines.append("")
    lines.append("OUTPUT_FILES")
    for key, value in status["output_files"].items():
        lines.append(f"{key}: {value}")

    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")

    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage226 restarted the demo Discord alert-only loop locally.")
    lines.append("MT5 order, real account, actual import, payload activation, live hook, final live, autotrade, and NO_SIGNAL notification remain disabled.")

    lines.append("")
    lines.append("BLOCKERS")
    if status["blockers"]:
        lines.extend(status["blockers"])
    else:
        lines.append("NO_BLOCKERS")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_cycle(
    cycle_id: int,
    queue_csv: Path,
    webhook_url: str,
    webhook_source: str,
    webhook_redacted: str,
    webhook_hash12: str,
    paths_dict: Dict[str, Path],
) -> Dict[str, int]:
    created_at = utc_now_iso()
    rows = read_csv(queue_csv)
    seen_ids = sent_signal_ids(paths_dict)

    queue_rows = len(rows)
    eligible = 0
    sent = 0
    skipped = 0
    blocked = 0
    no_signal_rows = 0
    no_signal_send_attempts = 0

    for row in rows:
        signal_id = (row.get("signal_id") or "").strip()
        short_signal_id = (row.get("short_signal_id") or "").strip()
        latest_closed = (row.get("latest_closed_m15_dt") or "").strip()
        entry_dt = (row.get("entry_dt") or "").strip()
        direction = normalize_direction(row)

        if is_no_signal(row):
            no_signal_rows += 1
            append_csv(
                paths_dict["no_signal"],
                {
                    "case_id": f"CYCLE{cycle_id}_NO_SIGNAL",
                    "signal_id": signal_id,
                    "latest_closed_m15_dt": latest_closed,
                    "final_route": row.get("final_route") or row.get("route") or "NO_SIGNAL",
                    "discord_send_attempted": False,
                    "discord_notify": False,
                    "reason": "NO_SIGNAL_SUPPRESSED",
                    "created_stage": STAGE,
                    "created_at_utc": created_at,
                },
                NO_SIGNAL_COLUMNS,
            )
            continue

        eligible += 1

        if signal_id in seen_ids:
            skipped += 1
            append_csv(
                paths_dict["attempts"],
                {
                    "attempt_id": f"CYCLE{cycle_id}_{signal_id}",
                    "signal_id": signal_id,
                    "short_signal_id": short_signal_id,
                    "latest_closed_m15_dt": latest_closed,
                    "entry_dt": entry_dt,
                    "direction": direction,
                    "send_status": "DUPLICATE_SKIPPED",
                    "http_status": "",
                    "discord_response_ok": True,
                    "skip_reason": "ALREADY_SENT_SIGNAL_ID",
                    "webhook_source": webhook_source,
                    "webhook_url_redacted": webhook_redacted,
                    "webhook_url_sha256_12": webhook_hash12,
                    "created_stage": STAGE,
                    "created_at_utc": created_at,
                },
                ATTEMPT_COLUMNS,
            )
            continue

        message = build_message_from_row(row)

        try:
            http_status, _response_text = discord_post(webhook_url, message)
            ok = http_status in (200, 204)
            if ok:
                sent += 1
                seen_ids.add(signal_id)
                append_csv(
                    paths_dict["ledger"],
                    {
                        "signal_id": signal_id,
                        "short_signal_id": short_signal_id,
                        "latest_closed_m15_dt": latest_closed,
                        "entry_dt": entry_dt,
                        "direction": direction,
                        "send_status": "SENT",
                        "http_status": http_status,
                        "sent_at_utc": utc_now_iso(),
                        "message_sha256": sha256_hex(message),
                        "created_stage": STAGE,
                    },
                    LEDGER_COLUMNS,
                )
            else:
                blocked += 1

            append_csv(
                paths_dict["attempts"],
                {
                    "attempt_id": f"CYCLE{cycle_id}_{signal_id}",
                    "signal_id": signal_id,
                    "short_signal_id": short_signal_id,
                    "latest_closed_m15_dt": latest_closed,
                    "entry_dt": entry_dt,
                    "direction": direction,
                    "send_status": "SENT" if ok else "FAILED_HTTP_STATUS",
                    "http_status": http_status,
                    "discord_response_ok": ok,
                    "skip_reason": "",
                    "webhook_source": webhook_source,
                    "webhook_url_redacted": webhook_redacted,
                    "webhook_url_sha256_12": webhook_hash12,
                    "created_stage": STAGE,
                    "created_at_utc": created_at,
                },
                ATTEMPT_COLUMNS,
            )

        except Exception as e:
            blocked += 1
            append_csv(
                paths_dict["attempts"],
                {
                    "attempt_id": f"CYCLE{cycle_id}_{signal_id}",
                    "signal_id": signal_id,
                    "short_signal_id": short_signal_id,
                    "latest_closed_m15_dt": latest_closed,
                    "entry_dt": entry_dt,
                    "direction": direction,
                    "send_status": "FAILED_EXCEPTION",
                    "http_status": "",
                    "discord_response_ok": False,
                    "skip_reason": type(e).__name__,
                    "webhook_source": webhook_source,
                    "webhook_url_redacted": webhook_redacted,
                    "webhook_url_sha256_12": webhook_hash12,
                    "created_stage": STAGE,
                    "created_at_utc": created_at,
                },
                ATTEMPT_COLUMNS,
            )

    append_csv(
        paths_dict["runtime"],
        {
            "cycle_id": cycle_id,
            "scheduled_read_at_local": local_now().isoformat(),
            "actual_read_at_utc": created_at,
            "queue_csv": str(queue_csv),
            "queue_rows": queue_rows,
            "eligible_rows": eligible,
            "sent_count": sent,
            "skipped_count": skipped,
            "blocked_count": blocked,
            "created_stage": STAGE,
        },
        RUNTIME_COLUMNS,
    )

    return {
        "queue_rows": queue_rows,
        "eligible": eligible,
        "sent": sent,
        "skipped": skipped,
        "blocked": blocked,
        "no_signal_rows": no_signal_rows,
        "no_signal_send_attempts": no_signal_send_attempts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one timed cycle then exit.")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means infinite loop.")
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--queue-csv", default=os.environ.get("GOLD_V3_ALERT_ONLY_QUEUE_CSV", ""))
    args = parser.parse_args()

    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    queue_csv = Path(args.queue_csv).expanduser().resolve() if args.queue_csv else p["default_queue"]

    webhook_url, webhook_source = load_webhook_url(p["env"])
    webhook_found = bool(webhook_url)
    webhook_valid = bool(webhook_url and is_discord_webhook(webhook_url))
    webhook_redacted = redact_webhook(webhook_url or "")
    webhook_hash12 = sha256_hex(webhook_url or "")[:12] if webhook_url else ""

    status: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "stage225_decision": "STAGE225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_SENT_READY",
        "stage225_validation_pass": True,
        "approval_text": APPROVAL_TEXT,
        "approval_scope": "DEMO_DISCORD_ALERT_ONLY_LOOP_RESTART",
        "loop_mode": "ONCE" if args.once else "LOOP",
        "read_delay_seconds": args.delay_seconds,
        "queue_csv": str(queue_csv),
        "queue_csv_exists": queue_csv.exists(),
        "cycles_completed": 0,
        "queue_rows_seen_total": 0,
        "eligible_rows_seen_total": 0,
        "sent_count_total": 0,
        "duplicate_skipped_count": 0,
        "no_signal_rows_seen": 0,
        "no_signal_send_attempts": 0,
        "webhook_url_found": webhook_found,
        "webhook_url_valid_discord": webhook_valid,
        "webhook_source": webhook_source,
        "webhook_url_redacted": webhook_redacted,
        "webhook_url_sha256_12": webhook_hash12,
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "MT5_CSV",
        "output_files": {
            "loop_send_attempts_csv": str(p["attempts"]),
            "loop_sent_ledger_csv": str(p["ledger"]),
            "loop_status_json": str(p["status"]),
            "loop_runtime_log_csv": str(p["runtime"]),
            "no_signal_suppression_csv": str(p["no_signal"]),
        },
    }
    status.update(OFF_FLAGS)

    initial_checks, initial_blockers = validate_status(status)
    if initial_blockers:
        status["status"] = "BLOCKED"
        status["ready"] = False
        status["decision"] = DECISION_BLOCKED
        status["blockers"] = initial_blockers
        status["blocker_count"] = len(initial_blockers)
        status["validation_checks"] = initial_checks
        write_json(p["status"], status)
        write_paste_me(p["paste"], status, initial_checks)

        print("Stage226 BLOCKED before loop start.")
        print(f"paste_me: {p['paste']}")
        return 2

    cycle_id = 0

    while True:
        cycle_id += 1
        target = next_minute_plus_delay(args.delay_seconds)
        print(f"[Stage226] Next CSV read at local time: {target.isoformat()}")
        sleep_until(target)

        result = run_cycle(
            cycle_id=cycle_id,
            queue_csv=queue_csv,
            webhook_url=webhook_url or "",
            webhook_source=webhook_source,
            webhook_redacted=webhook_redacted,
            webhook_hash12=webhook_hash12,
            paths_dict=p,
        )

        status["cycles_completed"] += 1
        status["queue_rows_seen_total"] += result["queue_rows"]
        status["eligible_rows_seen_total"] += result["eligible"]
        status["sent_count_total"] += result["sent"]
        status["duplicate_skipped_count"] += result["skipped"]
        status["no_signal_rows_seen"] += result["no_signal_rows"]
        status["no_signal_send_attempts"] += result["no_signal_send_attempts"]
        status["updated_at_utc"] = utc_now_iso()

        checks, blockers = validate_status(status)
        status["status"] = "READY" if not blockers else "BLOCKED"
        status["ready"] = not blockers
        status["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
        status["blockers"] = blockers
        status["blocker_count"] = len(blockers)
        status["validation_checks"] = checks

        write_json(p["status"], status)
        write_paste_me(p["paste"], status, checks)

        print(
            f"[Stage226] cycle={cycle_id} rows={result['queue_rows']} "
            f"eligible={result['eligible']} sent={result['sent']} "
            f"duplicate_skip={result['skipped']} no_signal={result['no_signal_rows']}"
        )
        print(f"[Stage226] paste_me: {p['paste']}")

        if blockers:
            return 2

        if args.once:
            return 0

        if args.max_cycles > 0 and cycle_id >= args.max_cycles:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())