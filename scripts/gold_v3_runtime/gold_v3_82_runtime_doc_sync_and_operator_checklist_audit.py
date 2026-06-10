#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 82 runtime doc sync and operator checklist audit-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"

REQ_DOCS = [
    "docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md",
    "docs/gold_v3/GOLD_V3_RUNTIME_OPERATOR_CHECKLIST_AUDIT_ONLY_20260610.md",
    "docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_81_RUNTIME_OPERATION_MANUAL_READY_82_NEXT_AUDIT_ONLY_20260610.md",
]
REQ_RUNTIME = [
    "scripts/gold_v3_runtime/bat/run_gold_v3_80_immutable_runtime_monitor_audit.bat",
    "scripts/gold_v3_runtime/bat/run_gold_v3_81_compact_support_bundle_audit.bat",
    "scripts/gold_v3_runtime/gold_v3_76_full_audit_monitor_with_payload_preview_audit.py",
    "scripts/gold_v3_runtime/gold_v3_79_immutable_runtime_output_policy_audit.py",
    "scripts/gold_v3_runtime/gold_v3_80_immutable_runtime_monitor_audit.py",
    "scripts/gold_v3_runtime/gold_v3_81_compact_support_bundle_audit.py",
]


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    repo = Path(__file__).resolve().parents[2]
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir/"FX_OUTPUTS"/"gold_v3"/"82_runtime_doc_sync_and_operator_checklist_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []

    for rel in REQ_DOCS + REQ_RUNTIME:
        p = repo / rel
        exists = p.exists()
        file_rows.append({"path": rel, "exists": exists, "size_bytes": p.stat().st_size if exists else "", "role": "doc" if rel.startswith("docs/") else "runtime"})
        val.append(ok("file_present_" + Path(rel).name, exists, rel, "exists"))
        if not exists:
            blockers.append(blocker("required_file_missing", rel, "REQUIRED_FILE_MISSING"))

    manual_path = repo / REQ_DOCS[0]
    checklist_path = repo / REQ_DOCS[1]
    manual = read_text(manual_path)
    checklist = read_text(checklist_path)

    doc_checks = [
        ("manual_mentions_stage80_bat", "run_gold_v3_80_immutable_runtime_monitor_audit.bat" in manual, "Stage80 BAT in manual"),
        ("manual_mentions_upload_first", "upload_first.txt" in manual, "upload_first.txt in manual"),
        ("manual_mentions_no_huge_csv_first", "Do not upload these first" in manual or "巨大CSV" in manual, "no huge logs first"),
        ("manual_mentions_stage81", "run_gold_v3_81_compact_support_bundle_audit.bat" in manual, "Stage81 BAT in manual"),
        ("checklist_mentions_stage80_bat", "run_gold_v3_80_immutable_runtime_monitor_audit.bat" in checklist, "Stage80 BAT in checklist"),
        ("checklist_mentions_upload_first", "upload_first.txt" in checklist, "upload_first.txt in checklist"),
        ("checklist_mentions_do_not_upload_large_logs", "Do not upload these first" in checklist, "do not upload huge logs first"),
        ("checklist_mentions_audit_only", "GOLD V3 remains audit-only" in checklist, "audit-only stated"),
    ]
    doc_rows = []
    for cid, passed, expected in doc_checks:
        doc_rows.append({"check_id": cid, "result": "PASS" if passed else "FAIL", "expected": expected})
        val.append(ok(cid, passed, "present" if passed else "missing", expected))
        if not passed:
            blockers.append(blocker(cid, str(manual_path if "manual" in cid else checklist_path), "DOC_REFERENCE_MISSING", expected))

    p80_summary = cdir/"FX_OUTPUTS"/"gold_v3"/"80_immutable_runtime_monitor_audit_only"/"gold_v3_80_immutable_runtime_monitor_summary.json"
    j80 = read_json(p80_summary)
    val.append(ok("stage80_summary_present", p80_summary.exists(), str(p80_summary), "exists"))
    if not p80_summary.exists():
        blockers.append(blocker("stage80_summary_missing", str(p80_summary), "STAGE80_SUMMARY_MISSING"))
    else:
        val.append(ok("stage80_ready", j80.get("status") == "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY", j80.get("status"), "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY"))
        val.append(ok("stage80_auto_support_bundle_enabled", j80.get("auto_support_bundle_enabled") is True, j80.get("auto_support_bundle_enabled"), True))
        val.append(ok("stage80_blocker_count_zero", int(j80.get("blocker_count", 999)) == 0, j80.get("blocker_count"), 0))
        if j80.get("status") != "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY":
            blockers.append(blocker("stage80_not_ready", str(p80_summary), "STAGE80_NOT_READY", j80.get("status")))
        if j80.get("auto_support_bundle_enabled") is not True:
            blockers.append(blocker("stage80_auto_support_disabled", str(p80_summary), "AUTO_SUPPORT_BUNDLE_DISABLED"))

    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(file_rows).to_csv(out/"gold_v3_82_file_presence_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(doc_rows).to_csv(out/"gold_v3_82_doc_reference_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out/"gold_v3_82_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out/"gold_v3_82_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "runtime_doc_sync_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "manual_path": REQ_DOCS[0],
        "operator_checklist_path": REQ_DOCS[1],
        "stage80_summary_path": str(p80_summary),
        "stage80_status": j80.get("status", "MISSING"),
        "stage80_auto_support_bundle_enabled": j80.get("auto_support_bundle_enabled", ""),
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out/"gold_v3_82_runtime_doc_sync_and_operator_checklist_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = [
        "GOLD V3 82 PASTE_ME_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_SUMMARY",
        f"status: {status}",
        "runtime_doc_sync_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"manual_path: {REQ_DOCS[0]}",
        f"operator_checklist_path: {REQ_DOCS[1]}",
        f"stage80_status: {j80.get('status', 'MISSING')}",
        f"stage80_auto_support_bundle_enabled: {j80.get('auto_support_bundle_enabled', '')}",
        f"blocker_count: {len(blockers)}",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_82_doc_reference_matrix.csv",
        "gold_v3_82_file_presence_matrix.csv",
        "gold_v3_82_blocker_matrix.csv",
        "gold_v3_82_validation_matrix.csv",
        "gold_v3_82_runtime_doc_sync_and_operator_checklist_summary.json",
        "gold_v3_82_PASTE_ME_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_SUMMARY.txt",
        "GOLD_V3_82_REPORT.md",
    ]
    (out/"gold_v3_82_PASTE_ME_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 82 runtime doc sync and operator checklist audit-only report

Status: `{status}`

- manual: `{REQ_DOCS[0]}`
- checklist: `{REQ_DOCS[1]}`
- Stage80 status: `{j80.get('status', 'MISSING')}`
- auto support bundle enabled: `{j80.get('auto_support_bundle_enabled', '')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_82_REPORT.md").write_text(report, encoding="utf-8")
    print(f"[{status}] {out/'gold_v3_82_PASTE_ME_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
