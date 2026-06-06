#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_24e_source_recovery_artifact_list_intake_audit_only"
IN24D = "gold_v2_24d_source_recovery_gap_resolution_plan_audit_only"
EXPECTED_24D_STATUS = "SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
TEMPLATE_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_TEMPLATE_READY_AUDIT_ONLY_ARTIFACT_LIST_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
VALIDATED_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24E_STOP_REVIEW_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_INPUTS"

REPORT_FILE = "GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24e_source_recovery_artifact_list_intake_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24e_input_audit.csv"
TEMPLATE_FILE = "gold_v2_24e_artifact_list_input_template.csv"
USER_INPUT_FILE = "gold_v2_24e_artifact_list_input.csv"
INTAKE_RESULT_FILE = "gold_v2_24e_artifact_list_intake_result.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24e_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24e_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24e_safety_matrix.csv"

FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
EXPECTED_STILL_BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FALSE_SUMMARY_FLAGS = [
    "source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled",
    "final_signal_allowed", "no_signal_discord_notified", "ai_api_called", "discord_sent", "mt5_order_sent",
    "live_hook_enabled", "source_recovery_execution_performed", "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]
REQUIRED_24D_FILES = {
    "24d_report": "GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY_REPORT.md",
    "24d_summary": "gold_v2_24d_source_recovery_gap_resolution_plan_summary.json",
    "24d_input_audit": "gold_v2_24d_input_audit.csv",
    "24d_gap_resolution_plan": "gold_v2_24d_gap_resolution_plan.csv",
    "24d_artifact_request_template": "gold_v2_24d_artifact_request_template.csv",
    "24d_integrated_checks": "gold_v2_24d_integrated_checks.csv",
    "24d_required_next_gates": "gold_v2_24d_required_next_gates.csv",
    "24d_safety_matrix": "gold_v2_24d_safety_matrix.csv",
}
REQUIRED_VALUE_COLUMNS = ["artifact_path", "artifact_hash", "artifact_role", "source_identity_scope", "upstream_sot_reference"]


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


def blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return str(value).strip() == ""


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


def build_input_audit(paths: dict[str, Path], user_input_path: Path) -> pd.DataFrame:
    rows = []
    for role, path in paths.items():
        rows.append({"role": role, "path": str(path), "required": True, "exists": long_path(path).exists(), "source_of_truth_role": "24D audited artifact", "notes": "24E reads this artifact only; no source recovery/live/AI/external execution."})
    rows.append({"role": "24e_optional_user_artifact_list_input", "path": str(user_input_path), "required": False, "exists": long_path(user_input_path).exists(), "source_of_truth_role": "optional user/operator filled intake", "notes": "If missing, 24E stays in template/wait mode and does not allow 24F."})
    return pd.DataFrame(rows)


def normalize_template(template: pd.DataFrame) -> pd.DataFrame:
    out = template.copy()
    for col in ["artifact_path", "artifact_hash", "artifact_role", "source_identity_scope", "upstream_sot_reference", "quarantine_note"]:
        if col not in out.columns:
            out[col] = ""
    return out


def validate_artifact_input(template: pd.DataFrame, user_input: pd.DataFrame | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    template_ids = template["intake_id"].astype(str).tolist() if "intake_id" in template.columns else []
    rows = []
    stats = {"artifact_list_supplied": user_input is not None, "unknown_ids": [], "duplicate_ids": [], "missing_ids": [], "valid_rows": 0, "invalid_rows": 0, "forbidden_true_rows": 0}
    if user_input is None:
        for _, t in template.iterrows():
            rows.append({
                "intake_id": t.get("intake_id", ""), "source_gap_id": t.get("source_gap_id", ""), "source_evidence_id": t.get("source_evidence_id", ""),
                "artifact_category": t.get("artifact_category", ""), "artifact_path_present": False, "artifact_hash_present": False,
                "artifact_role_present": False, "source_identity_scope_present": False, "upstream_sot_reference_present": False,
                "quarantine_note_present_or_not_required": False if t.get("artifact_category") == "old_gold_disc8_quarantine_evidence" else True,
                "execution_approved": False, "source_recovery_approved": False, "valid_for_24f_review": False,
                "status": "WAITING_FOR_USER_FILLED_ARTIFACT_LIST",
            })
        stats["missing_ids"] = template_ids
        stats["invalid_rows"] = len(rows)
        return pd.DataFrame(rows), stats

    if "intake_id" not in user_input.columns:
        stats["missing_ids"] = template_ids
        for _, t in template.iterrows():
            rows.append({"intake_id": t.get("intake_id", ""), "source_gap_id": t.get("source_gap_id", ""), "source_evidence_id": t.get("source_evidence_id", ""), "artifact_category": t.get("artifact_category", ""), "artifact_path_present": False, "artifact_hash_present": False, "artifact_role_present": False, "source_identity_scope_present": False, "upstream_sot_reference_present": False, "quarantine_note_present_or_not_required": False, "execution_approved": False, "source_recovery_approved": False, "valid_for_24f_review": False, "status": "INVALID_INPUT_MISSING_INTAKE_ID_COLUMN"})
        stats["invalid_rows"] = len(rows)
        return pd.DataFrame(rows), stats

    input_ids = user_input["intake_id"].astype(str).tolist()
    stats["unknown_ids"] = sorted([x for x in set(input_ids) if x not in set(template_ids)])
    stats["duplicate_ids"] = sorted(user_input.loc[user_input["intake_id"].astype(str).duplicated(), "intake_id"].astype(str).unique().tolist())
    stats["missing_ids"] = sorted([x for x in template_ids if x not in set(input_ids)])
    by_id = {str(r["intake_id"]): r for _, r in user_input.iterrows() if str(r.get("intake_id", "")) in set(template_ids)}

    for _, t in template.iterrows():
        iid = str(t.get("intake_id", ""))
        r = by_id.get(iid)
        category = str(t.get("artifact_category", ""))
        if r is None:
            status = "MISSING_REQUIRED_INTAKE_ROW"
            present = {col: False for col in REQUIRED_VALUE_COLUMNS}
            q_ok = category != "old_gold_disc8_quarantine_evidence"
            ex = False; rec = False; valid = False
        else:
            present = {col: not blank(r.get(col, "")) for col in REQUIRED_VALUE_COLUMNS}
            q_ok = (category != "old_gold_disc8_quarantine_evidence") or (not blank(r.get("quarantine_note", "")))
            ex = truthy(r.get("execution_approved", False)) if "execution_approved" in user_input.columns else False
            rec = truthy(r.get("source_recovery_approved", False)) if "source_recovery_approved" in user_input.columns else False
            valid = all(present.values()) and q_ok and not ex and not rec
            status = "VALID_FOR_24F_AUDIT_ONLY_REVIEW" if valid else "INVALID_OR_INCOMPLETE_ARTIFACT_ROW"
        if ex or rec:
            stats["forbidden_true_rows"] += 1
        stats["valid_rows"] += int(valid)
        stats["invalid_rows"] += int(not valid)
        rows.append({
            "intake_id": iid, "source_gap_id": t.get("source_gap_id", ""), "source_evidence_id": t.get("source_evidence_id", ""),
            "artifact_category": category, "artifact_path_present": present.get("artifact_path", False), "artifact_hash_present": present.get("artifact_hash", False),
            "artifact_role_present": present.get("artifact_role", False), "source_identity_scope_present": present.get("source_identity_scope", False),
            "upstream_sot_reference_present": present.get("upstream_sot_reference", False), "quarantine_note_present_or_not_required": q_ok,
            "execution_approved": ex, "source_recovery_approved": rec, "valid_for_24f_review": valid, "status": status,
        })
    return pd.DataFrame(rows), stats


def build_required_next_gates(ok: bool, validated: bool) -> pd.DataFrame:
    return pd.DataFrame([
        {"next_step": "24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY", "name": "Review supplied artifact list", "purpose": "Review exact artifact/path/hash entries without executing recovery.", "allowed_after_24e_success": bool(ok and validated), "required_human_decision_value_later": "NONE_FOR_24F_REVIEW", "still_blocked_reason": "" if ok and validated else "Filled artifact list has not been validated."},
        {"next_step": "WAIT_FOR_FILLED_24E_ARTIFACT_LIST", "name": "Wait for filled artifact list", "purpose": "User/operator fills gold_v2_24e_artifact_list_input.csv from template.", "allowed_after_24e_success": bool(ok and not validated), "required_human_decision_value_later": "NONE", "still_blocked_reason": "" if ok and not validated else "Artifact list already validated or 24E failed."},
        {"next_step": "SOURCE_RECOVERY", "name": "Execute source recovery", "purpose": "Would run recovery actions rather than audit-only review.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION", "still_blocked_reason": "24E is intake only and does not grant recovery approval."},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "name": "Finalize source identity", "purpose": "Would finalize recovered/source identity state.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION", "still_blocked_reason": "24E does not grant finalization approval."},
        {"next_step": "LIVE", "name": "Enable live evaluator/use", "purpose": "Would create or enable live behavior.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "still_blocked_reason": "GOLD V2 remains audit-only."},
        {"next_step": "FINAL_SIGNAL", "name": "Enable final signal", "purpose": "Would produce final signal behavior.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL", "still_blocked_reason": "Final signal remains blocked."},
        {"next_step": "DISCORD_SEND", "name": "Send Discord notification", "purpose": "Would send notifications externally.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_DISCORD_SEND", "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify."},
        {"next_step": "MT5_ORDER", "name": "Place MT5 order", "purpose": "Would place or prepare live orders.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_MT5_ORDER", "still_blocked_reason": "MT5 order path remains blocked."},
        {"next_step": "AI_API", "name": "Call AI API", "purpose": "Would call an external AI review API.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_AI_API_REVIEW", "still_blocked_reason": "AI API remains blocked."},
        {"next_step": "LIVE_HOOK", "name": "Enable live hook", "purpose": "Would connect audit logic to live runtime hooks.", "allowed_after_24e_success": False, "required_human_decision_value_later": "APPROVE_LIVE_HOOK", "still_blocked_reason": "Live hook remains blocked."},
    ])


def build_safety_matrix(summary24d: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str):
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24E writes audit artifacts only.")
    add("artifact_list_intake_only", True, True, True, "24E intakes artifact rows and never executes recovery.")
    add("required_24d_inputs_exist", inputs_ok, True, inputs_ok, "All 24D source-of-truth artifacts must exist.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24d.get(key, False) if inputs_ok else "UNKNOWN_MISSING_24D_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24d, key) if inputs_ok else "UNKNOWN_MISSING_24D_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("ai_api_called", False, False, True, "24E never calls AI API.")
    add("discord_sent", False, False, True, "24E never sends Discord.")
    add("mt5_order_sent", False, False, True, "24E never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "24E never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "24E never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24E never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24E never finalizes source identity.")
    add("overall_24e_intake_passed", ok, True, bool(ok), "Overall PASS is required before using 24E outputs.")
    return pd.DataFrame(rows)


def build_report(now: str, status: str, input_audit: pd.DataFrame, checks: pd.DataFrame, template: pd.DataFrame, intake: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 24E source recovery artifact list intake audit-only report", "", f"Created UTC: {now}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Boundary", "", "- 24E is audit-only.", "- 24E reads 24D audited artifacts as the source of truth.", "- 24E writes/fills/validates artifact list intake only.", "- 24E does not approve or execute source recovery.", "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.", "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary.get('total_stop_rows')}`", f"- Artifact list supplied: `{summary.get('artifact_list_supplied')}`", f"- Artifact list validated: `{summary.get('artifact_list_validated')}`", f"- Next recommended step: `{summary.get('next_recommended_step')}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "", "## Artifact list input template", "", md_table(template), "", "## Artifact list intake result", "", md_table(intake), "", "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "", "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`", "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`", "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); out = base / OUT_DIR; source = base / IN24D
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    user_input_path = out / USER_INPUT_FILE
    paths = {role: source / filename for role, filename in REQUIRED_24D_FILES.items()}
    input_audit = build_input_audit(paths, user_input_path); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    required_mask = input_audit["required"].map(truthy)
    inputs_ok = bool(input_audit.loc[required_mask, "exists"].all()) if not input_audit.empty else False
    missing = input_audit.loc[required_mask & ~input_audit["exists"].map(truthy), "role"].astype(str).tolist()
    checks = [check_row("24E-C000", "Required 24D source-of-truth artifacts exist", ",".join(missing) if missing else "all present", "all present", inputs_ok)]
    summary24d: dict[str, Any] = {}; template = pd.DataFrame(); upstream_stop_rows = 1 if not inputs_ok else 0
    if inputs_ok:
        summary24d = read_json(paths["24d_summary"])
        input24d = read_csv(paths["24d_input_audit"])
        plan24d = read_csv(paths["24d_gap_resolution_plan"])
        template = normalize_template(read_csv(paths["24d_artifact_request_template"]))
        checks24d = read_csv(paths["24d_integrated_checks"])
        gates24d = read_csv(paths["24d_required_next_gates"])
        safety24d = read_csv(paths["24d_safety_matrix"])
        upstream_stop_rows = int(summary24d.get("total_stop_rows", 999)) + stop_rows(checks24d) + stop_rows(safety24d)
        missing_required_24d_inputs = int((input24d["required"].map(truthy) & ~input24d["exists"].map(truthy)).sum()) if {"required","exists"}.issubset(input24d.columns) else 999
        allowed_after_24d = allowed_next_steps(gates24d, "allowed_after_24d_success")
        forbidden_detail = forbidden_allowed_detail(gates24d, "allowed_after_24d_success")
        false_flags = count_true_forbidden_summary_flags(summary24d)
        checks.extend([
            check_row("24E-C001", "24D status matches expected", summary24d.get("status"), EXPECTED_24D_STATUS, summary24d.get("status") == EXPECTED_24D_STATUS),
            check_row("24E-C002", "24D audit_only remains true", summary24d.get("audit_only"), True, truthy(summary24d.get("audit_only", False))),
            check_row("24E-C003", "24D gap resolution plan only remains true", summary24d.get("source_recovery_gap_resolution_plan_only"), True, truthy(summary24d.get("source_recovery_gap_resolution_plan_only", False))),
            check_row("24E-C004", "24D total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
            check_row("24E-C005", "24D required inputs were complete", missing_required_24d_inputs, 0, missing_required_24d_inputs == 0),
            check_row("24E-C006", "24D required next allowed only 24E", allowed_after_24d, [STEP], allowed_after_24d == [STEP]),
            check_row("24E-C007", "24D forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24E-C008", "24D forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
            check_row("24E-C009", "24D gap plan row count is 3", len(plan24d), 3, len(plan24d) == 3),
            check_row("24E-C010", "24D artifact request template row count is 3", len(template), 3, len(template) == 3),
            check_row("24E-C011", "24D says source recovery is not executed in 24D", summary24d.get("do_not_execute_source_recovery_in_24d"), True, truthy(summary24d.get("do_not_execute_source_recovery_in_24d", False))),
        ])
    write_csv(out / TEMPLATE_FILE, template)
    user_df = read_csv(user_input_path) if long_path(user_input_path).exists() else None
    intake_df, stats = validate_artifact_input(template, user_df) if inputs_ok else (pd.DataFrame(), {"artifact_list_supplied": False, "valid_rows": 0, "invalid_rows": 0, "forbidden_true_rows": 0, "unknown_ids": [], "duplicate_ids": [], "missing_ids": []})
    if stats.get("artifact_list_supplied"):
        checks.extend([
            check_row("24E-C012", "Supplied artifact list has no unknown intake IDs", stats["unknown_ids"], [], len(stats["unknown_ids"]) == 0),
            check_row("24E-C013", "Supplied artifact list has no duplicate intake IDs", stats["duplicate_ids"], [], len(stats["duplicate_ids"]) == 0),
            check_row("24E-C014", "Supplied artifact list has no missing intake IDs", stats["missing_ids"], [], len(stats["missing_ids"]) == 0),
            check_row("24E-C015", "Supplied artifact list has no forbidden approval/execution true rows", stats["forbidden_true_rows"], 0, stats["forbidden_true_rows"] == 0),
        ])
    checks_df = pd.DataFrame(checks)
    validated = bool(inputs_ok and stats.get("artifact_list_supplied") and stats.get("valid_rows") == 3 and stats.get("invalid_rows") == 0 and stats.get("forbidden_true_rows") == 0 and len(stats.get("unknown_ids", [])) == 0 and len(stats.get("duplicate_ids", [])) == 0 and len(stats.get("missing_ids", [])) == 0)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    safety_df = build_safety_matrix(summary24d, preliminary_ok, inputs_ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = VALIDATED_STATUS if ok and validated else (TEMPLATE_STATUS if ok else STOP_STATUS)
    gates_df = build_required_next_gates(ok, validated)
    outputs = {
        "input_audit": str(out / INPUT_AUDIT_FILE), "artifact_list_input_template": str(out / TEMPLATE_FILE),
        "artifact_list_intake_result": str(out / INTAKE_RESULT_FILE), "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE), "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE), "report": str(out / REPORT_FILE),
    }
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "source_recovery_artifact_list_intake_only": True,
        "source_of_truth": "24D audited artifacts under FX_OUTPUTS/" + IN24D,
        "upstream_status": summary24d.get("status", "UNKNOWN_MISSING_24D_SUMMARY"),
        "artifact_list_supplied": bool(stats.get("artifact_list_supplied")), "artifact_list_validated": bool(validated),
        "valid_artifact_rows": int(stats.get("valid_rows", 0)), "invalid_artifact_rows": int(stats.get("invalid_rows", 0)),
        "source_recovery_approved": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False, "old_gold_disc8_quarantined": True,
        "ai_api_called": False, "discord_sent": False, "mt5_order_sent": False, "live_hook_enabled": False,
        "source_recovery_execution_performed": False, "source_recovery_approval_granted": False,
        "source_identity_finalization_performed": False, "required_24d_inputs_ok": inputs_ok,
        "missing_inputs": missing, "upstream_stop_rows": int(upstream_stop_rows), "total_stop_rows": int(total_stop_rows),
        "template_rows": int(len(template)), "intake_result_rows": int(len(intake_df)),
        "required_next_allowed": ["24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY"] if ok and validated else (["WAIT_FOR_FILLED_24E_ARTIFACT_LIST"] if ok else []),
        "still_blocked_after_24e": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY" if ok and validated else ("WAIT_FOR_FILLED_24E_ARTIFACT_LIST" if ok else "STOP_REVIEW_24E_INPUTS_AND_24D_OUTPUTS"),
        "do_not_execute_source_recovery_in_24e": True, "outputs": outputs,
    }
    write_csv(out / INTAKE_RESULT_FILE, intake_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, template, intake_df, gates_df, safety_df, summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
