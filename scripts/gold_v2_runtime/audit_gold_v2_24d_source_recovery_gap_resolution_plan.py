#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY"
OUT_DIR = "gold_v2_24d_source_recovery_gap_resolution_plan_audit_only"
IN24C = "gold_v2_24c_source_recovery_evidence_package_review_audit_only"

EXPECTED_24C_STATUS = "SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_READY_AUDIT_ONLY_GAPS_OPEN_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
SUCCESS_STATUS = "SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24D_STOP_REVIEW_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_INPUTS"

REPORT_FILE = "GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24d_source_recovery_gap_resolution_plan_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24d_input_audit.csv"
GAP_RESOLUTION_PLAN_FILE = "gold_v2_24d_gap_resolution_plan.csv"
ARTIFACT_REQUEST_TEMPLATE_FILE = "gold_v2_24d_artifact_request_template.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24d_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24d_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24d_safety_matrix.csv"

FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
EXPECTED_STILL_BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FALSE_SUMMARY_FLAGS = [
    "source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled",
    "final_signal_allowed", "no_signal_discord_notified", "ai_api_called", "discord_sent", "mt5_order_sent",
    "live_hook_enabled", "source_recovery_execution_performed", "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]

REQUIRED_24C_FILES = {
    "24c_report": "GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY_REPORT.md",
    "24c_summary": "gold_v2_24c_source_recovery_evidence_package_review_summary.json",
    "24c_input_audit": "gold_v2_24c_input_audit.csv",
    "24c_package_review_matrix": "gold_v2_24c_evidence_package_review_matrix.csv",
    "24c_gap_resolution_planning_matrix": "gold_v2_24c_gap_resolution_planning_matrix.csv",
    "24c_integrated_checks": "gold_v2_24c_integrated_checks.csv",
    "24c_required_next_gates": "gold_v2_24c_required_next_gates.csv",
    "24c_safety_matrix": "gold_v2_24c_safety_matrix.csv",
}

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def fx_outputs_root() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"

def long_path(path: Path) -> Path:
    path = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)

def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "allowed", "pass", "ready"}

def falsey(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not bool(value)
    return str(value).strip().lower() in {"", "0", "false", "no", "n", "blocked", "none", "null"}

def write_text(path: Path, text: str) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(text, encoding="utf-8")

def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))

def write_csv(path: Path, frame: pd.DataFrame) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    frame.to_csv(long_path(path), index=False, encoding="utf-8-sig")

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(long_path(path).read_text(encoding="utf-8"))

def read_csv(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            errors.append(f"{enc}: {exc}")
    raise RuntimeError(f"CSV read failed: {path} / {'; '.join(errors)}")

def stop_rows(df: pd.DataFrame) -> int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper() == "STOP").sum())

def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)

def check_row(cid: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": check, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}

def get_external(summary: dict[str, Any], key: str) -> Any:
    ext = summary.get("external_actions", {})
    return ext.get(key, False) if isinstance(ext, dict) else False

def allowed_next_steps(gates: pd.DataFrame, col: str) -> list[str]:
    if gates.empty or "next_step" not in gates.columns or col not in gates.columns:
        return []
    return gates.loc[gates[col].map(truthy), "next_step"].astype(str).tolist()

def forbidden_allowed_detail(gates: pd.DataFrame, col: str) -> str:
    if gates.empty or "next_step" not in gates.columns or col not in gates.columns:
        return "missing next_step/allowed column"
    sub = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
    if sub.empty:
        return "no forbidden gate rows found"
    allowed = sub[sub[col].map(truthy)]
    return "all forbidden gates blocked" if allowed.empty else ",".join(allowed["next_step"].astype(str).tolist())

def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    return int(sum(1 for k in FALSE_SUMMARY_FLAGS if truthy(summary.get(k, False))) + sum(1 for k in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, k))))

def build_input_audit(paths: dict[str, Path]) -> pd.DataFrame:
    return pd.DataFrame([{
        "role": role, "path": str(path), "required": True, "exists": long_path(path).exists(),
        "source_of_truth_role": "24C audited artifact",
        "notes": "24D reads this artifact only; no source recovery/live/AI/external execution.",
    } for role, path in paths.items()])

def build_gap_resolution_plan(gap_plan_24c: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for idx, (_, g) in enumerate(gap_plan_24c.iterrows(), start=1):
        evidence_id = str(g.get("evidence_id", ""))
        gap_id = str(g.get("gap_id", ""))
        required_detail = str(g.get("required_artifact_detail", ""))
        if evidence_id == "24A-E004":
            artifact_category = "source_identity_lineage_docs"
            required_fields = "document_path; document_sha256_or_blob_sha; source_identity_scope; upstream_sot_reference"
        elif evidence_id == "24A-E005":
            artifact_category = "candidate_source_files"
            required_fields = "repo_path_or_fx_output_path; file_sha256_or_blob_sha; role; why_candidate_source"
        elif evidence_id == "24A-E006":
            artifact_category = "old_gold_disc8_quarantine_evidence"
            required_fields = "quarantine_doc_path; doc_sha256_or_blob_sha; htf_open_time_mismatch_note; blocked_use_scope"
        else:
            artifact_category = "other_source_recovery_evidence"
            required_fields = "artifact_path; artifact_hash; evidence_role; notes"
        rows.append({
            "resolution_id": f"24D-GR{idx:03d}",
            "source_gap_id": gap_id,
            "source_evidence_id": evidence_id,
            "gap_type": g.get("gap_type", ""),
            "artifact_category": artifact_category,
            "required_artifact_detail": required_detail,
            "required_fields_for_24e_intake": required_fields,
            "resolution_action": "Prepare exact artifact/path/hash entry for 24E intake audit-only.",
            "blocks_source_recovery_execution": True,
            "source_recovery_execution_allowed_after_this_plan": False,
            "status": "PLAN_READY_AUDIT_ONLY",
        })
    if not rows:
        rows.append({
            "resolution_id": "24D-GR000", "source_gap_id": "NO_GAP", "source_evidence_id": "NO_GAP",
            "gap_type": "NO_OPEN_GAPS", "artifact_category": "none", "required_artifact_detail": "No gap rows supplied by 24C.",
            "required_fields_for_24e_intake": "N/A", "resolution_action": "No gap action; source recovery execution remains blocked.",
            "blocks_source_recovery_execution": True, "source_recovery_execution_allowed_after_this_plan": False,
            "status": "PLAN_READY_AUDIT_ONLY",
        })
    return pd.DataFrame(rows)

def build_artifact_template(plan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in plan.iterrows():
        rows.append({
            "intake_id": f"24E-{p.get('resolution_id', '')}",
            "source_gap_id": p.get("source_gap_id", ""),
            "source_evidence_id": p.get("source_evidence_id", ""),
            "artifact_category": p.get("artifact_category", ""),
            "artifact_path": "",
            "artifact_hash": "",
            "artifact_role": "",
            "source_identity_scope": "",
            "upstream_sot_reference": "",
            "quarantine_note": "",
            "required_fields_hint": p.get("required_fields_for_24e_intake", ""),
            "user_or_operator_must_fill": True,
            "execution_approved": False,
            "source_recovery_approved": False,
            "status": "TEMPLATE_ROW_AUDIT_ONLY_NOT_FILLED",
        })
    return pd.DataFrame(rows)

def build_required_next_gates(ok: bool) -> pd.DataFrame:
    rows = [
        ("24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY", "Intake exact artifact/path/hash list", "User/operator supplies concrete artifact entries for the 3 open gaps; no recovery execution.", ok, "NONE_FOR_24E_INTAKE", "" if ok else "24D checks did not pass."),
        ("SOURCE_RECOVERY", "Execute source recovery", "Would run recovery actions rather than audit-only review.", False, "APPROVE_SOURCE_RECOVERY_EXECUTION", "24D is gap planning only and does not grant recovery approval."),
        ("SOURCE_IDENTITY_FINALIZATION", "Finalize source identity", "Would finalize recovered/source identity state.", False, "APPROVE_SOURCE_IDENTITY_FINALIZATION", "24D does not grant finalization approval."),
        ("LIVE", "Enable live evaluator/use", "Would create or enable live behavior.", False, "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "GOLD V2 remains audit-only."),
        ("FINAL_SIGNAL", "Enable final signal", "Would produce final signal behavior.", False, "APPROVE_FINAL_SIGNAL", "Final signal remains blocked."),
        ("DISCORD_SEND", "Send Discord notification", "Would send notifications externally.", False, "APPROVE_DISCORD_SEND", "Discord remains blocked; NO_SIGNAL must not notify."),
        ("MT5_ORDER", "Place MT5 order", "Would place or prepare live orders.", False, "APPROVE_MT5_ORDER", "MT5 order path remains blocked."),
        ("AI_API", "Call AI API", "Would call an external AI review API.", False, "APPROVE_AI_API_REVIEW", "AI API remains blocked."),
        ("LIVE_HOOK", "Enable live hook", "Would connect audit logic to live runtime hooks.", False, "APPROVE_LIVE_HOOK", "Live hook remains blocked."),
    ]
    return pd.DataFrame([{"next_step": a, "name": b, "purpose": c, "allowed_after_24d_success": bool(d), "required_human_decision_value_later": e, "still_blocked_reason": f} for a,b,c,d,e,f in rows])

def build_safety_matrix(summary24c: dict[str, Any], ok: bool, inputs_ok: bool, open_gaps: int) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str) -> None:
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24D writes audit artifacts only.")
    add("gap_resolution_plan_only", True, True, True, "24D plans artifact intake and never executes recovery.")
    add("open_gaps_continue_to_block_recovery", open_gaps, ">=0", True, "Open gaps are planned, not resolved by 24D.")
    add("required_24c_inputs_exist", inputs_ok, True, inputs_ok, "All 24C source-of-truth artifacts must exist.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24c.get(key, False) if inputs_ok else "UNKNOWN_MISSING_24C_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24c, key) if inputs_ok else "UNKNOWN_MISSING_24C_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "24D does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "24D never calls AI API.")
    add("discord_sent", False, False, True, "24D never sends Discord.")
    add("mt5_order_sent", False, False, True, "24D never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "24D never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "24D never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24D never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24D never finalizes source identity.")
    add("overall_24d_plan_passed", ok, True, bool(ok), "Overall PASS is required before using 24D outputs.")
    return pd.DataFrame(rows)

def build_report(now: str, status: str, input_audit: pd.DataFrame, checks: pd.DataFrame, plan: pd.DataFrame, template: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 24D source recovery gap resolution plan audit-only report", "",
        f"Created UTC: {now}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Boundary", "",
        "- 24D is audit-only.",
        "- 24D reads 24C audited artifacts as the source of truth.",
        "- 24D plans how exact artifact/path/hash evidence should be supplied for open gaps.",
        "- 24D does not approve, prepare, or execute source recovery.",
        "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
        "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "",
        f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
        f"- Open evidence gaps carried forward: `{summary.get('open_evidence_gaps_carried_forward')}`",
        f"- Artifact intake template rows: `{summary.get('artifact_request_template_rows')}`",
        f"- Next recommended step: `{summary.get('next_recommended_step')}`", "",
        "## Input audit", "", md_table(input_audit), "",
        "## Integrated checks", "", md_table(checks), "",
        "## Gap resolution plan", "", md_table(plan), "",
        "## Artifact request template", "", md_table(template), "",
        "## Required next gates", "", md_table(gates), "",
        "## Safety matrix", "", md_table(safety), "",
        "## Explicit non-actions", "",
        "- Source recovery approved: `false`",
        "- Source recovery executed: `false`",
        "- Source identity finalized/recovered: `false`",
        "- AI API called: `false`",
        "- Discord notification sent: `false`",
        "- MT5 order sent: `false`",
        "- Live hook enabled: `false`",
    ])

def main() -> int:
    base = fx_outputs_root()
    out = base / OUT_DIR
    source = base / IN24C
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    paths = {role: source / filename for role, filename in REQUIRED_24C_FILES.items()}
    input_audit = build_input_audit(paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()
    checks = [check_row("24D-C000", "Required 24C source-of-truth artifacts exist", ",".join(missing) if missing else "all present", "all present", inputs_ok)]

    summary24c: dict[str, Any] = {}
    gap_plan_24c = pd.DataFrame()
    upstream_stop_rows = 1 if not inputs_ok else 0
    open_gaps = 0
    package_review_rows = 0

    if inputs_ok:
        summary24c = read_json(paths["24c_summary"])
        input24c = read_csv(paths["24c_input_audit"])
        package_review_24c = read_csv(paths["24c_package_review_matrix"])
        gap_plan_24c = read_csv(paths["24c_gap_resolution_planning_matrix"])
        checks24c = read_csv(paths["24c_integrated_checks"])
        gates24c = read_csv(paths["24c_required_next_gates"])
        safety24c = read_csv(paths["24c_safety_matrix"])
        upstream_stop_rows = int(summary24c.get("total_stop_rows", 999)) + stop_rows(checks24c) + stop_rows(safety24c)
        package_review_rows = len(package_review_24c)
        open_gaps = int((gap_plan_24c["status"].astype(str) == "OPEN_GAP_PLAN_AUDIT_ONLY").sum()) if "status" in gap_plan_24c.columns else int(summary24c.get("open_evidence_gaps", 0))
        missing_required_24c_inputs = int((input24c["required"].map(truthy) & ~input24c["exists"].map(truthy)).sum()) if {"required", "exists"}.issubset(input24c.columns) else 999
        allowed_after_24c = allowed_next_steps(gates24c, "allowed_after_24c_success")
        forbidden_detail = forbidden_allowed_detail(gates24c, "allowed_after_24c_success")
        false_flags = count_true_forbidden_summary_flags(summary24c)
        checks.extend([
            check_row("24D-C001", "24C status matches expected", summary24c.get("status"), EXPECTED_24C_STATUS, summary24c.get("status") == EXPECTED_24C_STATUS),
            check_row("24D-C002", "24C audit_only remains true", summary24c.get("audit_only"), True, truthy(summary24c.get("audit_only", False))),
            check_row("24D-C003", "24C evidence package review only remains true", summary24c.get("source_recovery_evidence_package_review_only"), True, truthy(summary24c.get("source_recovery_evidence_package_review_only", False))),
            check_row("24D-C004", "24C total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
            check_row("24D-C005", "24C required inputs were complete", missing_required_24c_inputs, 0, missing_required_24c_inputs == 0),
            check_row("24D-C006", "24C required next allowed only 24D", allowed_after_24c, [STEP], allowed_after_24c == [STEP]),
            check_row("24D-C007", "24C forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24D-C008", "24C forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
            check_row("24D-C009", "24C package review row count meets minimum", package_review_rows, ">=10", package_review_rows >= 10),
            check_row("24D-C010", "24C open evidence gaps are carried forward", open_gaps, ">=1", open_gaps >= 1),
            check_row("24D-C011", "24C says source recovery is not executed in 24C", summary24c.get("do_not_execute_source_recovery_in_24c"), True, truthy(summary24c.get("do_not_execute_source_recovery_in_24c", False))),
            check_row("24D-C012", "24C source recovery execution blocked by open gaps", summary24c.get("source_recovery_execution_blocked_by_open_gaps"), True, truthy(summary24c.get("source_recovery_execution_blocked_by_open_gaps", False))),
        ])

    checks_df = pd.DataFrame(checks)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    plan_df = build_gap_resolution_plan(gap_plan_24c) if preliminary_ok else pd.DataFrame([{
        "resolution_id": "24D-GRSTOP", "source_gap_id": "STOP", "source_evidence_id": "STOP", "gap_type": "24D_STOP",
        "artifact_category": "STOP", "required_artifact_detail": "24D prerequisite checks failed.",
        "required_fields_for_24e_intake": "Review 24D checks.", "resolution_action": "Review 24D checks.",
        "blocks_source_recovery_execution": True, "source_recovery_execution_allowed_after_this_plan": False,
        "status": "STOP",
    }])
    template_df = build_artifact_template(plan_df)
    safety_df = build_safety_matrix(summary24c, preliminary_ok, inputs_ok, open_gaps)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS
    gates_df = build_required_next_gates(ok)

    outputs = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "gap_resolution_plan": str(out / GAP_RESOLUTION_PLAN_FILE),
        "artifact_request_template": str(out / ARTIFACT_REQUEST_TEMPLATE_FILE),
        "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE),
        "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE),
        "report": str(out / REPORT_FILE),
    }
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "source_recovery_gap_resolution_plan_only": True,
        "source_of_truth": "24C audited artifacts under FX_OUTPUTS/" + IN24C,
        "upstream_status": summary24c.get("status", "UNKNOWN_MISSING_24C_SUMMARY"),
        "source_recovery_approved": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False, "old_gold_disc8_quarantined": True,
        "approximate_reimplementation_used": False, "ai_api_called": False, "discord_sent": False,
        "mt5_order_sent": False, "live_hook_enabled": False,
        "source_recovery_execution_performed": False, "source_recovery_approval_granted": False,
        "source_identity_finalization_performed": False,
        "required_24c_inputs_ok": inputs_ok, "missing_inputs": missing,
        "upstream_stop_rows": int(upstream_stop_rows), "total_stop_rows": int(total_stop_rows),
        "open_evidence_gaps_carried_forward": int(open_gaps),
        "gap_resolution_plan_rows": int(len(plan_df)),
        "artifact_request_template_rows": int(len(template_df)),
        "source_recovery_execution_blocked_by_open_gaps": True,
        "required_next_allowed": ["24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_24d": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY" if ok else "STOP_REVIEW_24D_INPUTS_AND_24C_OUTPUTS",
        "do_not_execute_source_recovery_in_24d": True,
        "outputs": outputs,
    }
    write_csv(out / GAP_RESOLUTION_PLAN_FILE, plan_df)
    write_csv(out / ARTIFACT_REQUEST_TEMPLATE_FILE, template_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, plan_df, template_df, gates_df, safety_df, summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
