#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AH_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ah_tier2_source_identity_human_decision_intake_readiness_package_final_audit_only"
IN18AG = "gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_audit_only"
REPORT = "GOLD_V2_18AH_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AG = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
EVIDENCE_DIRS = {
    "18X": "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only",
    "18Y": "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
    "18Z": "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only",
    "18AA": "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only",
    "18AB": "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only",
    "18AC": "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only",
    "18AD": "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only",
    "18AE": "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_only",
    "18AF": "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_audit_only",
    "18AG": IN18AG,
}
SUCCESS_KEYS = [
    "intake_planning_ready", "intake_load_smoke_passed", "intake_content_audit_passed", "intake_reconciliation_passed",
    "blocker_review_passed", "readiness_package_prepared", "package_load_smoke_passed", "package_content_audit_passed",
    "package_reconciliation_passed", "blocker_review_passed",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure_parent(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    lp(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    ensure_parent(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def check_row(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def forbidden_summary_count(s: dict[str, Any]) -> int:
    n = sum(int(bool(s.get(k, False))) for k in FORBIDDEN_FLAGS)
    ext = s.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def summary_success_flag(summary: dict[str, Any]) -> bool:
    return any(bool(summary.get(k, False)) for k in SUCCESS_KEYS)


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18AI", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY", "Prepare final handoff note for later explicit human decision intake only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AH.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AH.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18ah_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["final_audit_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_18ai_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AH-S001", "required inputs missing", "STOP"],
        ["18AH-S002", "18AG status not passed", "STOP"],
        ["18AH-S003", "decision collected or approval already made", "STOP"],
        ["18AH-S004", "upstream STOP rows present", "STOP"],
        ["18AH-S005", "evidence summary missing or failed", "STOP"],
        ["18AH-S006", "blockers not still in force", "STOP"],
        ["18AH-S007", "forbidden gate allowed", "STOP"],
        ["18AH-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ag = base / IN18AG
    inputs = {
        "summary_18ag": p18ag / "gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_summary.json",
        "checks_18ag": p18ag / "gold_v2_18ag_blocker_review_checks.csv",
        "blockers_18ag": p18ag / "gold_v2_18ag_blockers_still_in_force.csv",
        "gates_18ag": p18ag / "gold_v2_18ag_required_next_gates.csv",
        "safety_18ag": p18ag / "gold_v2_18ag_safety_matrix.csv",
        "report_18ag": p18ag / "GOLD_V2_18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_18ah_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AH-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18ah_final_checks.csv", checks)
        write_csv(out / "gold_v2_18ah_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "18AH_STOP_MISSING_INPUTS", "audit_only": True, "final_audit_ready": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_18AH_INPUTS"}
        write_json(out / "gold_v2_18ah_tier2_source_identity_human_decision_intake_readiness_package_final_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AH final audit-only report\n\nStatus: `18AH_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ag = read_json(inputs["summary_18ag"])
    checks18ag = read_csv(inputs["checks_18ag"])
    blockers = read_csv(inputs["blockers_18ag"])
    gates18ag = read_csv(inputs["gates_18ag"])
    safe18ag = read_csv(inputs["safety_18ag"])

    evidence_rows = []
    summaries = []
    for step, dirname in EVIDENCE_DIRS.items():
        folder = base / dirname
        found = None
        if lp(folder).exists():
            for f in folder.glob("*summary.json"):
                found = f
                break
        if found is None:
            evidence_rows.append([step, str(folder), False, "MISSING", False, "STOP"])
            continue
        summary = read_json(found)
        summaries.append(summary)
        ok = summary_success_flag(summary) and int(summary.get("total_stop_rows", 0)) == 0
        evidence_rows.append([step, str(found), True, summary.get("status"), ok, "PASS" if ok else "STOP"])
    evidence = pd.DataFrame(evidence_rows, columns=["step", "summary_path", "exists", "status", "success_flag_and_zero_stop", "status_check"])
    evidence["status"] = evidence["status_check"].astype(str).map(lambda s: "PASS" if s == "PASS" else "STOP")
    evidence = evidence.drop(columns=["status_check"])
    write_csv(out / "gold_v2_18ah_evidence_status.csv", evidence)

    blocker_status_bad = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    clear_bad = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    force_bad = int((~blockers.get("still_in_force_after_18ag", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    blocker_final = pd.DataFrame([
        check_row("18AH-B001", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        check_row("18AH-B002", "blocker status not BLOCKED", blocker_status_bad, 0, blocker_status_bad == 0),
        check_row("18AH-B003", "script_can_clear true rows", clear_bad, 0, clear_bad == 0),
        check_row("18AH-B004", "not still in force rows", force_bad, 0, force_bad == 0),
    ])
    write_csv(out / "gold_v2_18ah_blocker_final_status.csv", blocker_final)

    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in summaries + [s18ag])
    upstream_stop = stop_count(checks18ag) + stop_count(safe18ag)
    forbidden_gates = forbidden_gate_count(gates18ag, "allowed_after_18ag_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in summaries + [s18ag])
    checks = pd.DataFrame([
        check_row("18AH-C001", "18AG status", s18ag.get("status"), EXPECTED_18AG, s18ag.get("status") == EXPECTED_18AG),
        check_row("18AH-C002", "18AG blocker_review_passed", s18ag.get("blocker_review_passed"), True, bool(s18ag.get("blocker_review_passed", False))),
        check_row("18AH-C003", "18AG total_stop_rows", s18ag.get("total_stop_rows"), 0, s18ag.get("total_stop_rows") == 0),
        check_row("18AH-C004", "18X-18AG no decision/approval", no_decision, True, no_decision),
        check_row("18AH-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("18AH-C006", "evidence summary STOP rows", stop_count(evidence), 0, stop_count(evidence) == 0),
        check_row("18AH-C007", "blocker final STOP rows", stop_count(blocker_final), 0, stop_count(blocker_final) == 0),
        check_row("18AH-C008", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("18AH-C009", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AH_STOP_REVIEW_FINAL_AUDIT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18ah_final_checks.csv", checks)
    write_csv(out / "gold_v2_18ah_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18ah_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18ah_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "final_audit_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ag_status": s18ag.get("status"),
        "evidence_steps_checked": int(len(evidence)),
        "remaining_blockers": int(len(blockers)),
        "total_stop_rows": int(total_stop),
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AI_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY" if success else "STOP_REVIEW_18AH_OUTPUTS",
    }
    write_json(out / "gold_v2_18ah_tier2_source_identity_human_decision_intake_readiness_package_final_audit_summary.json", summary)
    report = [
        "# GOLD V2 18AH TIER2 source identity human decision intake readiness package final audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AH prepared a final audit-only readiness summary only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Final checks",
        md_table(checks),
        "",
        "## Evidence status",
        md_table(evidence),
        "",
        "## Blocker final status",
        md_table(blocker_final),
        "",
        "## Next gates",
        md_table(gates),
        "",
        "## Safety",
        md_table(sm),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
