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

ALLOWED_PY_CALLS = {
    "scripts\\gold_v3_runtime\\gold_v3_116_exact_ledger_bridge.py",
    "scripts\\gold_v3_runtime\\gold_v3_115d_stale_data_watchdog.py",
    "scripts\\gold_v3_runtime\\gold_v3_115c_single_bat_loop.py",
    "scripts\\gold_v3_runtime\\gold_v3_115x_bat_error_queue.py",
    "scripts\\gold_v3_runtime\\gold_v3_115b_queue_sender.py",
}

FORBIDDEN_ORDER_PATTERNS = [
    r"\bMetaTrader5\b",
    r"\bmt5\s*\.",
    r"\border_send\b",
    r"\bOrderSend\b",
    r"\bTRADE_ACTION_DEAL\b",
    r"\bCTrade\b",
    r"\bPositionOpen\b",
    r"\bPositionClose\b",
    r"\bBuy\s*\(",
    r"\bSell\s*\(",
    r"\bsend_order\b",
    r"\bcreate_order\b",
    r"\blive_order\b",
]

CHECKS = [
    {
        "check_id": "C001_FULL_LOOP_BAT_MODE_TEXT",
        "target": "full_loop_bat",
        "severity": "BLOCKER",
        "expect": "contains",
        "needle": "MODE: alert-only / no MT5 orders / NO_SIGNAL no Discord",
        "pass_detail": "BAT declares alert-only, no MT5 orders, and NO_SIGNAL no Discord.",
        "fail_detail": "BAT mode line is missing or changed.",
    },
    {
        "check_id": "C002_FULL_LOOP_PROGRESS_DISPLAY",
        "target": "full_loop_bat",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["[1/5] Stage116 exact ledger bridge", "[2/5] Stage115D stale data watchdog --once", "[3/5] Stage115C single BAT loop --once", "[4/5] Waiting until next minute target-second 5", "[5/5] Loop completed, restarting"],
        "pass_detail": "BAT has the required progress display.",
        "fail_detail": "BAT progress display is incomplete.",
    },
    {
        "check_id": "C003_STOP_BRANCH_PROGRESS_DISPLAY",
        "target": "full_loop_bat",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["[STOP 1/2] Queue BAT error notice", "[STOP 2/2] Send queued notice via Stage115B"],
        "pass_detail": "STOP_BRANCH has visible progress display.",
        "fail_detail": "STOP_BRANCH progress display is incomplete.",
    },
    {
        "check_id": "C004_STAGE116_EXACT_LEDGER_ONLY",
        "target": "stage116_exact_ledger_bridge",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["gold_v3_109_selected_base_policy_ledger.csv", "latest_closed_candle_not_in_selected_ledger", "NO_SIGNAL_EXACT_LEDGER_NO_MATCH", "source':'109_selected_base_policy_ledger"],
        "pass_detail": "Stage116 emits from exact 109c selected ledger match only; ledger miss becomes NO_SIGNAL.",
        "fail_detail": "Stage116 exact-ledger/NO_SIGNAL contract text is missing or changed.",
    },
    {
        "check_id": "C005_STAGE116_CLOSED_CSV_CONTRACT_FLAGS",
        "target": "stage116_exact_ledger_bridge",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["source_csv_mutated':False", "contract_mutated':False", "open_asof_allowed':False", "approximate_reconstruction':False"],
        "pass_detail": "Stage116 summary keeps CSV mutation/open-asof/reconstruction disabled.",
        "fail_detail": "Stage116 closed CSV contract flags are missing or changed.",
    },
    {
        "check_id": "C006_STAGE115A_NO_SIGNAL_NOT_QUEUED",
        "target": "stage115a_queue_loop",
        "severity": "BLOCKER",
        "expect": "contains_regex",
        "pattern": r"side\s+not\s+in\s+\[\s*[\"']\s*[\"']\s*,\s*[\"']NO_SIGNAL[\"']\s*,\s*[\"']NONE[\"']\s*\]",
        "pass_detail": "Stage115A suppresses empty/NO_SIGNAL/NONE before queueing.",
        "fail_detail": "Stage115A NO_SIGNAL queue suppression guard is missing or changed.",
    },
    {
        "check_id": "C007_STAGE115A_TRACKING_ONLY_LEDGER",
        "target": "stage115a_queue_loop",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["OPEN_TRACKING_ONLY", "PENDING", "source_csv_mutated": "ignored"],
        "pass_detail": "Stage115A uses virtual tracking-only ledger wording.",
        "fail_detail": "Stage115A tracking-only wording is missing or changed.",
        "custom": "tracking_only",
    },
    {
        "check_id": "C008_STAGE115B_QUEUE_SENDER_ONLY",
        "target": "stage115b_queue_sender",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["def iter_queue(root):", "root/'115a'/'queue'", "urllib.request", "message_title(side)", "GOLD V3 DEMO LONG", "GOLD V3 DEMO SHORT"],
        "pass_detail": "Stage115B only formats/sends queued Discord messages.",
        "fail_detail": "Stage115B queue sender structure is missing or changed.",
    },
    {
        "check_id": "C009_STAGE115D_STOP_REVIEW_ONLY",
        "target": "stage115d_stale_data_watchdog",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["side = \"STOP_REVIEW\"", "WATCH_STALE", "STOP_REVIEW_STALE", "INPUT_PARSE_ERROR", "INPUT_MISSING"],
        "pass_detail": "Stage115D queues stale/input notices as STOP_REVIEW only.",
        "fail_detail": "Stage115D STOP_REVIEW watchdog contract is missing or changed.",
    },
    {
        "check_id": "C010_STAGE115C_STORAGE_AND_SENDER_ONLY",
        "target": "stage115c_single_bat_loop",
        "severity": "BLOCKER",
        "expect": "all_contains",
        "needles": ["qloop.run_once", "sender.run_once", "market_stop_treated_as_error", "source_csv_mutated": "ignored"],
        "pass_detail": "Stage115C only chains storage queue and Discord sender.",
        "fail_detail": "Stage115C chain contract is missing or changed.",
        "custom": "stage115c",
    },
]


def jst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = [
        "check_id", "target", "severity", "passed", "status", "detail", "evidence",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in keys})


def find_mt5_files_dir(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    here = Path(__file__).resolve()
    for p in here.parents:
        if p.name.lower() == "files":
            return p
    return Path.cwd().resolve()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_targets(root: Path) -> tuple[dict[str, str], list[dict]]:
    texts: dict[str, str] = {}
    blockers: list[dict] = []
    for key, rel in TARGET_FILES.items():
        p = root / rel
        if not p.exists():
            blockers.append({"blocker_id": "missing_target_file", "target": key, "path": str(p)})
            texts[key] = ""
            continue
        try:
            texts[key] = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            blockers.append({"blocker_id": "read_failed", "target": key, "path": str(p), "error": str(e)})
            texts[key] = ""
    return texts, blockers


def pass_contains(text: str, needle: str) -> bool:
    return needle in text


def evaluate_check(check: dict, texts: dict[str, str]) -> dict:
    target = check["target"]
    text = texts.get(target, "")
    status = "PASS"
    evidence = ""

    if check.get("custom") == "tracking_only":
        passed = "OPEN_TRACKING_ONLY" in text and "PENDING" in text and "append_csv(history / \"gold_v3_115a_virtual_signal_ledger.csv\"" in text
        evidence = "OPEN_TRACKING_ONLY/PENDING/virtual_signal_ledger" if passed else "tracking-only evidence missing"
    elif check.get("custom") == "stage115c":
        passed = "qloop.run_once" in text and "sender.run_once" in text and "market_stop_treated_as_error" in text and "open_asof_allowed" in text
        evidence = "qloop.run_once/sender.run_once/market_stop_treated_as_error/open_asof_allowed" if passed else "Stage115C evidence missing"
    elif check["expect"] == "contains":
        passed = pass_contains(text, check["needle"])
        evidence = check["needle"] if passed else "missing: " + check["needle"]
    elif check["expect"] == "all_contains":
        missing = [n for n in check.get("needles", []) if n not in text]
        passed = not missing
        evidence = "all needles found" if passed else "missing: " + " | ".join(missing)
    elif check["expect"] == "contains_regex":
        passed = bool(re.search(check["pattern"], text))
        evidence = check["pattern"] if passed else "regex not matched"
    else:
        passed = False
        evidence = "unknown check type"

    if not passed:
        status = "BLOCKER" if check.get("severity") == "BLOCKER" else "WARN"

    return {
        "check_id": check["check_id"],
        "target": target,
        "severity": check.get("severity", "BLOCKER"),
        "passed": passed,
        "status": status,
        "detail": check["pass_detail"] if passed else check["fail_detail"],
        "evidence": evidence,
    }


def scan_for_order_path(texts: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for target, text in texts.items():
        hits = []
        for pat in FORBIDDEN_ORDER_PATTERNS:
            if re.search(pat, text):
                hits.append(pat)
        passed = not hits
        rows.append({
            "check_id": "C011_NO_ORDER_PATH_STATIC_SCAN_" + target.upper(),
            "target": target,
            "severity": "BLOCKER",
            "passed": passed,
            "status": "PASS" if passed else "BLOCKER",
            "detail": "No MT5/order-execution token found in this target." if passed else "Forbidden order-execution token found.",
            "evidence": "none" if passed else " | ".join(hits),
        })
    return rows


def scan_bat_python_calls(text: str) -> list[dict]:
    calls = []
    for line in text.splitlines():
        s = line.strip()
        m = re.search(r"\b(?:py\s+-3|python)\s+([^\s]+\.py)", s, flags=re.IGNORECASE)
        if m:
            calls.append(m.group(1))
    unexpected = [c for c in calls if c not in ALLOWED_PY_CALLS]
    passed = not unexpected and bool(calls)
    return [{
        "check_id": "C012_FULL_LOOP_BAT_ALLOWED_PY_CALLS_ONLY",
        "target": "full_loop_bat",
        "severity": "BLOCKER",
        "passed": passed,
        "status": "PASS" if passed else "BLOCKER",
        "detail": "Full loop BAT calls only the Stage116/115 alert-only scripts." if passed else "Full loop BAT calls an unexpected Python target or no Python calls were found.",
        "evidence": "calls=" + " | ".join(calls) + (" unexpected=" + " | ".join(unexpected) if unexpected else ""),
    }]


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
        "Stage118 reviews only the Stage116/115 demo Discord alert-only restart path. It does not start the loop, does not send Discord messages, does not write orders, and does not promote any final signal.",
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
    for r in rows:
        lines.append(f"| {r['check_id']} | {r['target']} | {r['status']} | {str(r['detail']).replace('|','/')} |")
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
    rows: list[dict] = []
    rows.extend(evaluate_check(c, texts) for c in CHECKS)
    rows.extend(scan_for_order_path(texts))
    rows.extend(scan_bat_python_calls(texts.get("full_loop_bat", "")))

    blockers = list(file_blockers)
    blockers.extend({"blocker_id": "safety_check_failed", "check_id": r["check_id"], "target": r["target"], "detail": r["detail"], "evidence": r["evidence"]} for r in rows if not r.get("passed"))

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
        "passed_checks": sum(1 for r in rows if r.get("passed")),
        "failed_checks": sum(1 for r in rows if not r.get("passed")),
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
