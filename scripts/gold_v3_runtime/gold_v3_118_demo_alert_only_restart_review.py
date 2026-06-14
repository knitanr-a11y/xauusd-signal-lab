#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

STEP = "GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY"
READY = "GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_READY"
BLOCKED = "GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_BLOCKED"

TARGET_FILES = {
    "full_loop_bat": "scripts/gold_v3_runtime/bat/run_gold_v3_116_115_full_loop.bat",
    "stage116_exact_ledger_bridge": "scripts/gold_v3_runtime/gold_v3_116_exact_ledger_bridge.py",
    "stage115d_stale_data_watchdog": "scripts/gold_v3_runtime/gold_v3_115d_stale_data_watchdog.py",
    "stage115c_single_bat_loop": "scripts/gold_v3_runtime/gold_v3_115c_single_bat_loop.py",
    "stage115a_queue_loop": "scripts/gold_v3_runtime/gold_v3_115a_queue_loop.py",
    "stage115b_queue_sender": "scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py",
    "stage115x_bat_error_queue": "scripts/gold_v3_runtime/gold_v3_115x_bat_error_queue.py",
}

ALLOWED_BAT_PY_CALLS = {
    "scripts\\gold_v3_runtime\\gold_v3_116_exact_ledger_bridge.py",
    "scripts\\gold_v3_runtime\\gold_v3_115d_stale_data_watchdog.py",
    "scripts\\gold_v3_runtime\\gold_v3_115c_single_bat_loop.py",
    "scripts\\gold_v3_runtime\\gold_v3_115x_bat_error_queue.py",
    "scripts\\gold_v3_runtime\\gold_v3_115b_queue_sender.py",
}

# Built as fragments so this review file never imports or calls any trading/routing API.
RISK_TOKENS = [
    "Meta" + "Trader5",
    "mt" + "5.",
    "order" + "_send",
    "Order" + "Send",
    "TRADE" + "_ACTION" + "_DEAL",
    "C" + "Trade",
    "Position" + "Open",
    "Position" + "Close",
    "B" + "uy(",
    "S" + "ell(",
    "send" + "_order",
    "create" + "_order",
]


def jst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def find_mt5_files_dir(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    here = Path(__file__).resolve()
    for p in here.parents:
        if p.name.lower() == "files":
            return p
    return Path.cwd().resolve()


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["check_id", "target", "severity", "passed", "status", "detail", "evidence"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in keys})


def read_targets(root: Path) -> tuple[dict[str, str], list[dict]]:
    texts: dict[str, str] = {}
    blockers: list[dict] = []
    for key, rel in TARGET_FILES.items():
        path = root / rel
        if not path.exists():
            texts[key] = ""
            blockers.append({"blocker_id": "missing_target_file", "target": key, "path": str(path)})
            continue
        try:
            texts[key] = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            texts[key] = ""
            blockers.append({"blocker_id": "read_failed", "target": key, "path": str(path), "error": str(e)})
    return texts, blockers


def add(rows: list[dict], check_id: str, target: str, passed: bool, detail_ok: str, detail_ng: str, evidence: str, severity: str = "BLOCKER") -> None:
    rows.append({
        "check_id": check_id,
        "target": target,
        "severity": severity,
        "passed": bool(passed),
        "status": "PASS" if passed else severity,
        "detail": detail_ok if passed else detail_ng,
        "evidence": evidence,
    })


def all_in(text: str, needles: list[str]) -> tuple[bool, str]:
    missing = [needle for needle in needles if needle not in text]
    return not missing, "all needles found" if not missing else "missing: " + " | ".join(missing)


def run_checks(texts: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    bat = texts.get("full_loop_bat", "")
    s116 = texts.get("stage116_exact_ledger_bridge", "")
    s115a = texts.get("stage115a_queue_loop", "")
    s115b = texts.get("stage115b_queue_sender", "")
    s115c = texts.get("stage115c_single_bat_loop", "")
    s115d = texts.get("stage115d_stale_data_watchdog", "")

    add(rows, "C001_FULL_LOOP_BAT_MODE_TEXT", "full_loop_bat", "MODE: alert-only / no MT5 orders / NO_SIGNAL no Discord" in bat, "BAT declares alert-only, no MT5 routing, and NO_SIGNAL no Discord.", "BAT mode line is missing or changed.", "MODE line")

    ok, ev = all_in(bat, ["[1/5] Stage116 exact ledger bridge", "[2/5] Stage115D stale data watchdog --once", "[3/5] Stage115C single BAT loop --once", "[4/5] Waiting until next minute target-second 5", "[5/5] Loop completed, restarting"])
    add(rows, "C002_FULL_LOOP_PROGRESS_DISPLAY", "full_loop_bat", ok, "BAT has required progress display.", "BAT progress display is incomplete.", ev)

    ok, ev = all_in(bat, ["[STOP 1/2] Queue BAT error notice", "[STOP 2/2] Send queued notice via Stage115B"])
    add(rows, "C003_STOP_BRANCH_PROGRESS_DISPLAY", "full_loop_bat", ok, "STOP_BRANCH has visible progress display.", "STOP_BRANCH progress display is incomplete.", ev)

    ok, ev = all_in(s116, ["gold_v3_109_selected_base_policy_ledger.csv", "latest_closed_candle_not_in_selected_ledger", "NO_SIGNAL_EXACT_LEDGER_NO_MATCH", "source':'109_selected_base_policy_ledger"])
    add(rows, "C004_STAGE116_EXACT_LEDGER_ONLY", "stage116_exact_ledger_bridge", ok, "Stage116 emits from exact 109c selected ledger match only; ledger miss becomes NO_SIGNAL.", "Stage116 exact-ledger/NO_SIGNAL contract text is missing or changed.", ev)

    ok, ev = all_in(s116, ["source_csv_mutated':False", "contract_mutated':False", "open_asof_allowed':False", "approximate_reconstruction':False"])
    add(rows, "C005_STAGE116_CLOSED_CSV_CONTRACT_FLAGS", "stage116_exact_ledger_bridge", ok, "Stage116 keeps CSV mutation/open-asof/reconstruction disabled.", "Stage116 closed CSV contract flags are missing or changed.", ev)

    no_signal_guard = bool(re.search(r"side\s+not\s+in\s+\[\s*[\"']\s*[\"']\s*,\s*[\"']NO_SIGNAL[\"']\s*,\s*[\"']NONE[\"']\s*\]", s115a))
    add(rows, "C006_STAGE115A_NO_SIGNAL_NOT_QUEUED", "stage115a_queue_loop", no_signal_guard, "Stage115A suppresses empty/NO_SIGNAL/NONE before queueing.", "Stage115A NO_SIGNAL queue suppression guard is missing or changed.", "side not in empty/NO_SIGNAL/NONE")

    ok = "OPEN_TRACKING_ONLY" in s115a and "PENDING" in s115a and "gold_v3_115a_virtual_signal_ledger.csv" in s115a
    add(rows, "C007_STAGE115A_TRACKING_ONLY_LEDGER", "stage115a_queue_loop", ok, "Stage115A uses virtual tracking-only ledger wording.", "Stage115A tracking-only wording is missing or changed.", "OPEN_TRACKING_ONLY/PENDING/virtual_signal_ledger")

    ok, ev = all_in(s115b, ["def iter_queue(root):", "root/'115a'/'queue'", "urllib.request", "message_title(side)", "GOLD V3 DEMO LONG", "GOLD V3 DEMO SHORT"])
    add(rows, "C008_STAGE115B_QUEUE_SENDER_ONLY", "stage115b_queue_sender", ok, "Stage115B only formats/sends queued Discord messages.", "Stage115B queue sender structure is missing or changed.", ev)

    ok, ev = all_in(s115d, ["side = \"STOP_REVIEW\"", "WATCH_STALE", "STOP_REVIEW_STALE", "INPUT_PARSE_ERROR", "INPUT_MISSING"])
    add(rows, "C009_STAGE115D_STOP_REVIEW_ONLY", "stage115d_stale_data_watchdog", ok, "Stage115D queues stale/input notices as STOP_REVIEW only.", "Stage115D STOP_REVIEW watchdog contract is missing or changed.", ev)

    ok = "qloop.run_once" in s115c and "sender.run_once" in s115c and "market_stop_treated_as_error" in s115c and "open_asof_allowed" in s115c
    add(rows, "C010_STAGE115C_STORAGE_AND_SENDER_ONLY", "stage115c_single_bat_loop", ok, "Stage115C only chains storage queue and Discord sender.", "Stage115C chain contract is missing or changed.", "qloop.run_once/sender.run_once/market_stop_treated_as_error/open_asof_allowed")

    for target, text in texts.items():
        hits = [token for token in RISK_TOKENS if token in text]
        add(rows, "C011_NO_ORDER_PATH_STATIC_SCAN_" + target.upper(), target, not hits, "No routing/execution token found in this target.", "Forbidden routing/execution token found.", "none" if not hits else " | ".join(hits))

    calls: list[str] = []
    for line in bat.splitlines():
        m = re.search(r"\b(?:py\s+-3|python)\s+([^\s]+\.py)", line.strip(), flags=re.IGNORECASE)
        if m:
            calls.append(m.group(1))
    unexpected = [call for call in calls if call not in ALLOWED_BAT_PY_CALLS]
    add(rows, "C012_FULL_LOOP_BAT_ALLOWED_PY_CALLS_ONLY", "full_loop_bat", bool(calls) and not unexpected, "Full loop BAT calls only Stage116/115 alert-only scripts.", "Full loop BAT calls an unexpected Python target or no Python calls were found.", "calls=" + " | ".join(calls) + (" unexpected=" + " | ".join(unexpected) if unexpected else ""))
    return rows


def write_report(out: Path, summary: dict, rows: list[dict], blockers: list[dict]) -> None:
    lines = [
        "# GOLD V3 118 — Demo Alert-Only Restart Review (audit-only)",
        "",
        f"Created UTC: `{summary['created_at_utc']}`",
        "",
        "## Decision",
        "",
        f"`{summary['decision']}`",
        "",
        "## Scope",
        "",
        "Stage118 reviews only the Stage116/115 demo Discord alert-only restart path. It does not start the loop, send Discord messages, write orders, or promote any final signal.",
        "",
        "## Safety posture",
        "",
        f"- order_path_enabled: `{str(summary['order_path_enabled']).lower()}`",
        f"- no_signal_discord_allowed: `{str(summary['no_signal_discord_allowed']).lower()}`",
        f"- csv_latest_row_contract: `{summary['csv_latest_row_contract']}`",
        f"- discord_scope: `{summary['discord_scope']}`",
        f"- selected_policy: `{summary['selected_policy']}`",
        f"- mt5_order_execution_allowed: `{str(summary['mt5_order_execution_allowed']).lower()}`",
        f"- final_signal_promotion_allowed: `{str(summary['final_signal_promotion_allowed']).lower()}`",
        "",
        "## Check matrix",
        "",
        "| check_id | target | status | detail |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        safe_detail = str(row["detail"]).replace("|", "/")
        lines.append(f"| {row['check_id']} | {row['target']} | {row['status']} | {safe_detail} |")
    lines += ["", "## Blockers", "", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    rr = repo_root()
    mt5 = find_mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "118"
    out.mkdir(parents=True, exist_ok=True)

    texts, file_blockers = read_targets(rr)
    rows = run_checks(texts)
    blockers = list(file_blockers)
    blockers.extend({"blocker_id": "safety_check_failed", "check_id": row["check_id"], "target": row["target"], "detail": row["detail"], "evidence": row["evidence"]} for row in rows if not row.get("passed"))

    status = READY if not blockers else BLOCKED
    decision = "DEMO_ALERT_ONLY_RESTART_REVIEW_PASS_USER_MAY_START_116_115_FULL_LOOP" if status == READY else "DEMO_ALERT_ONLY_RESTART_REVIEW_BLOCKED_DO_NOT_START_LOOP"
    now = jst()
    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "checked_at_jst": now.isoformat(),
        "repo_root": str(rr),
        "output_dir": str(out),
        "target_files_checked": len(TARGET_FILES),
        "check_rows": len(rows),
        "passed_checks": sum(1 for row in rows if row.get("passed")),
        "failed_checks": sum(1 for row in rows if not row.get("passed")),
        "blocker_count": len(blockers),
        "order_path_enabled": False if status == READY else None,
        "mt5_order_execution_allowed": False,
        "real_account_allowed": False,
        "live_order_allowed": False,
        "final_signal_promotion_allowed": False,
        "no_signal_discord_allowed": False,
        "discord_scope": "DEMO_ALERT_ONLY_LONG_SHORT_AND_STOP_REVIEW_NOTICES_ONLY",
        "csv_latest_row_contract": "LATEST_ROW_IS_CLOSED_NO_OPEN_ASOF",
        "selected_policy": "KEEP_F002_EXCLUSION",
        "review_only_june_restore_auto_adopted": False,
        "candidate_pool_removed": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "approximate_reconstruction": False,
        "shadow_only": True,
        "loop_started_by_stage118": False,
        "discord_sent_by_stage118": False,
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    write_csv(out / "gold_v3_118_safety_check_matrix.csv", rows)
    write_json(out / "gold_v3_118_summary.json", summary | {"blockers": blockers})
    append_jsonl(out / "journal" / now.strftime("%Y-%m") / f"gold_v3_118_restart_review_{now.strftime('%Y-%m-%d')}.jsonl", summary | {"blockers": blockers})
    write_report(out, summary, rows, blockers)

    paste = [
        "GOLD V3 118 PASTE_ME_DEMO_ALERT_ONLY_RESTART_REVIEW",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        f"decision: {decision}",
        f"target_files_checked: {summary['target_files_checked']}",
        f"check_rows: {summary['check_rows']}",
        f"passed_checks: {summary['passed_checks']}",
        f"failed_checks: {summary['failed_checks']}",
        f"blocker_count: {summary['blocker_count']}",
        "order_path_enabled: false" if status == READY else "order_path_enabled: REVIEW_BLOCKED",
        "mt5_order_execution_allowed: false",
        "real_account_allowed: false",
        "live_order_allowed: false",
        "final_signal_promotion_allowed: false",
        "no_signal_discord_allowed: false",
        "csv_latest_row_contract: LATEST_ROW_IS_CLOSED_NO_OPEN_ASOF",
        "discord_scope: DEMO_ALERT_ONLY_LONG_SHORT_AND_STOP_REVIEW_NOTICES_ONLY",
        "selected_policy: KEEP_F002_EXCLUSION",
        "review_only_june_restore_auto_adopted: false",
        "candidate_pool_removed: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "approximate_reconstruction: false",
        "loop_started_by_stage118: false",
        "discord_sent_by_stage118: false",
        "",
        "NEXT_ALLOWED_MANUAL_ACTION",
        "If this review is READY and the user explicitly wants demo monitoring, manually start scripts/gold_v3_runtime/bat/run_gold_v3_116_115_full_loop.bat.",
        "",
        "BLOCKERS",
        "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2),
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
