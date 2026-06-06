#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_24c_source_recovery_evidence_package_review_audit_only"
IN24B = "gold_v2_24b_source_recovery_evidence_inventory_audit_only"
EXPECTED_24B_STATUS = "SOURCE_RECOVERY_EVIDENCE_INVENTORY_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
SUCCESS_STATUS = "SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_READY_AUDIT_ONLY_GAPS_OPEN_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24C_STOP_REVIEW_SOURCE_RECOVERY_EVIDENCE_PACKAGE_INPUTS"

REPORT_FILE = "GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24c_source_recovery_evidence_package_review_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24c_input_audit.csv"
PACKAGE_REVIEW_FILE = "gold_v2_24c_evidence_package_review_matrix.csv"
GAP_PLAN_FILE = "gold_v2_24c_gap_resolution_planning_matrix.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24c_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24c_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24c_safety_matrix.csv"

FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
EXPECTED_STILL_BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FALSE_SUMMARY_FLAGS = [
    "source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled",
    "final_signal_allowed", "no_signal_discord_notified", "ai_api_called", "discord_sent", "mt5_order_sent",
    "live_hook_enabled", "source_recovery_execution_performed", "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]
REQUIRED_24B_FILES = {
    "24b_report": "GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY_REPORT.md",
    "24b_summary": "gold_v2_24b_source_recovery_evidence_inventory_summary.json",
    "24b_input_audit": "gold_v2_24b_input_audit.csv",
    "24b_evidence_inventory": "gold_v2_24b_evidence_inventory.csv",
    "24b_evidence_gap_matrix": "gold_v2_24b_evidence_gap_matrix.csv",
    "24b_integrated_checks": "gold_v2_24b_integrated_checks.csv",
    "24b_required_next_gates": "gold_v2_24b_required_next_gates.csv",
    "24b_safety_matrix": "gold_v2_24b_safety_matrix.csv",
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
        "source_of_truth_role": "24B audited artifact",
        "notes": "24C reads this artifact only; no source recovery/live/AI/external execution.",
    } for role, path in paths.items()])


def build_package_review(inventory: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in inventory.iterrows():
        gap = truthy(row.get("gap_detected", False))
        rows.append({
            "review_id": f"24C-R{len(rows)+1:03d}",
            "evidence_id": row.get("evidence_id", ""),
            "evidence_name": row.get("evidence_name", ""),
            "availability_status": row.get("availability_status", ""),
            "gap_detected": gap,
            "review_result": "OPEN_GAP_BLOCKS_RECOVERY_EXECUTION" if gap else "AVAILABLE_FOR_AUDIT_REFERENCE_ONLY",
            "source_recovery_execution_allowed": False,
            "required_next_action": "Resolve exact artifact/path/hash in 24D audit-only plan." if gap else "Retain as evidence reference; do not execute recovery.",
            "status": "REVIEWED_AUDIT_ONLY",
        })
    if gaps.empty:
        rows.append({
            "review_id": "24C-RGAPLESS", "evidence_id": "NO_GAP", "evidence_name": "No open gap rows from 24B",
            "availability_status": "NO_GAPS", "gap_detected": False, "review_result": "NO_GAPS_REPORTED_BUT_EXECUTION_STILL_BLOCKED",
            "source_recovery_execution_allowed": False, "required_next_action": "Continue audit-only package review; no execution.", "status": "REVIEWED_AUDIT_ONLY",
        })
    return pd.DataFrame(rows)


def build_gap_plan(gaps: pd.DataFrame) -> pd.DataFrame:
    if gaps.empty:
        return pd.DataFrame([{
            "plan_id": "24C-P000", "gap_id": "NONE", "evidence_id": "NONE", "gap_type": "NO_OPEN_GAPS",
            "resolution_plan": "No gap plan rows required, but source recovery execution remains blocked.",
            "required_artifact_detail": "N/A", "blocks_source_recovery_execution": True,
            "next_step": "24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY", "status": "PLAN_AUDIT_ONLY",
        }])
    rows = []
    for i, (_, g) in enumerate(gaps.iterrows(), start=1):
        rows.append({
            "plan_id": f"24C-P{i:03d}",
            "gap_id": g.get("gap_id", ""),
            "evidence_id": g.get("evidence_id", ""),
            "gap_type": g.get("gap_type", ""),
            "resolution_plan": "Create an explicit artifact/path/hash inventory entry; verify it in a later audit-only step before any recovery can be considered.",
            "required_artifact_detail": g.get("gap_description", ""),
            "blocks_source_recovery_execution": True,
            "next_step": "24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY",
            "status": "OPEN_GAP_PLAN_AUDIT_ONLY",
        })
    return pd.DataFrame(rows)


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    rows = [
        ("24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY", "Plan evidence gap resolution", "Plan how to supply exact artifact/path/hash evidence without executing recovery.", ok, "NONE_FOR_24D_PLAN", "" if ok else "24C checks did not pass."),
        ("SOURCE_RECOVERY", "Execute source recovery", "Would run recovery actions rather than audit-only review.", False, "APPROVE_SOURCE_RECOVERY_EXECUTION", "24C is package review only and open gaps still block recovery."),
        ("SOURCE_IDENTITY_FINALIZATION", "Finalize source identity", "Would finalize recovered/source identity state.", False, "APPROVE_SOURCE_IDENTITY_FINALIZATION", "24C does not grant finalization approval."),
        ("LIVE", "Enable live evaluator/use", "Would create or enable live behavior.", False, "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "GOLD V2 remains audit-only."),
        ("FINAL_SIGNAL", "Enable final signal", "Would produce final signal behavior.", False, "APPROVE_FINAL_SIGNAL", "Final signal remains blocked."),
        ("DISCORD_SEND", "Send Discord notification", "Would send notifications externally.", False, "APPROVE_DISCORD_SEND", "Discord remains blocked; NO_SIGNAL must not notify."),
        ("MT5_ORDER", "Place MT5 order", "Would place or prepare live orders.", False, "APPROVE_MT5_ORDER", "MT5 order path remains blocked."),
        ("AI_API", "Call AI API", "Would call an external AI review API.", False, "APPROVE_AI_API_REVIEW", "AI API remains blocked."),
        ("LIVE_HOOK", "Enable live hook", "Would connect audit logic to live runtime hooks.", False, "APPROVE_LIVE_HOOK", "Live hook remains blocked."),
    ]
    return pd.DataFrame([{"next_step": a, "name": b, "purpose": c, "allowed_after_24c_success": bool(d), "required_human_decision_value_later": e, "still_blocked_reason": f} for a,b,c,d,e,f in rows])


def build_safety_matrix(summary24b: dict[str, Any], ok: bool, inputs_ok: bool, gaps_open: int) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str):
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24C writes audit artifacts only.")
    add("package_review_only", True, True, True, "24C reviews evidence/gaps and never executes recovery.")
    add("open_gaps_continue_to_block_recovery", gaps_open, ">=0", True, "Open gaps are reviewed, not resolved by 24C.")
    add("required_24b_inputs_exist", inputs_ok, True, inputs_ok, "All 24B source-of-truth artifacts must exist.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24b.get(key, False) if inputs_ok else "UNKNOWN_MISSING_24B_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24b, key) if inputs_ok else "UNKNOWN_MISSING_24B_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "24C does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "24C never calls AI API.")
    add("discord_sent", False, False, True, "24C never sends Discord.")
    add("mt5_order_sent", False, False, True, "24C never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "24C never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "24C never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24C never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24C never finalizes source identity.")
    add("overall_24c_review_passed", ok, True, bool(ok), "Overall PASS is required before using 24C outputs.")
    return pd.DataFrame(rows)


def build_report(now: str, status: str, input_audit: pd.DataFrame, checks: pd.DataFrame, review: pd.DataFrame, plan: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 24C source recovery evidence package review audit-only report", "", f"Created UTC: {now}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Boundary", "", "- 24C is audit-only.", "- 24C reads 24B audited artifacts as the source of truth.", "- 24C reviews evidence package availability and open gaps only.", "- 24C does not approve or execute source recovery.", "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.", "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary.get('total_stop_rows')}`", f"- Open evidence gaps: `{summary.get('open_evidence_gaps')}`", f"- Next recommended step: `{summary.get('next_recommended_step')}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "", "## Evidence package review matrix", "", md_table(review), "", "## Gap resolution planning matrix", "", md_table(plan), "", "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "", "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`", "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`", "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); out = base / OUT_DIR; source = base / IN24B
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    paths = {role: source / filename for role, filename in REQUIRED_24B_FILES.items()}
    input_audit = build_input_audit(paths); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()
    checks = [check_row("24C-C000", "Required 24B source-of-truth artifacts exist", ",".join(missing) if missing else "all present", "all present", inputs_ok)]
    summary24b: dict[str, Any] = {}; inventory = pd.DataFrame(); gaps = pd.DataFrame(); upstream_stop_rows = 1 if not inputs_ok else 0
    if inputs_ok:
        summary24b = read_json(paths["24b_summary"])
        input24b = read_csv(paths["24b_input_audit"])
        inventory = read_csv(paths["24b_evidence_inventory"])
        gaps = read_csv(paths["24b_evidence_gap_matrix"])
        checks24b = read_csv(paths["24b_integrated_checks"])
        gates24b = read_csv(paths["24b_required_next_gates"])
        safety24b = read_csv(paths["24b_safety_matrix"])
        upstream_stop_rows = int(summary24b.get("total_stop_rows", 999)) + stop_rows(checks24b) + stop_rows(safety24b)
        missing_required_24b_inputs = int((input24b["required"].map(truthy) & ~input24b["exists"].map(truthy)).sum()) if {"required","exists"}.issubset(input24b.columns) else 999
        allowed_after_24b = allowed_next_steps(gates24b, "allowed_after_24b_success")
        forbidden_detail = forbidden_allowed_detail(gates24b, "allowed_after_24b_success")
        false_flags = count_true_forbidden_summary_flags(summary24b)
        open_gaps = int((gaps["status"].astype(str) == "GAP_OPEN_AUDIT_ONLY").sum()) if "status" in gaps.columns else len(gaps)
        checks.extend([
            check_row("24C-C001", "24B status matches expected", summary24b.get("status"), EXPECTED_24B_STATUS, summary24b.get("status") == EXPECTED_24B_STATUS),
            check_row("24C-C002", "24B audit_only remains true", summary24b.get("audit_only"), True, truthy(summary24b.get("audit_only", False))),
            check_row("24C-C003", "24B evidence inventory only remains true", summary24b.get("source_recovery_evidence_inventory_only"), True, truthy(summary24b.get("source_recovery_evidence_inventory_only", False))),
            check_row("24C-C004", "24B total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
            check_row("24C-C005", "24B required inputs were complete", missing_required_24b_inputs, 0, missing_required_24b_inputs == 0),
            check_row("24C-C006", "24B required next allowed only 24C", allowed_after_24b, ["24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY"], allowed_after_24b == ["24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY"]),
            check_row("24C-C007", "24B forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24C-C008", "24B forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
            check_row("24C-C009", "24B evidence inventory row count meets minimum", len(inventory), ">=10", len(inventory) >= 10),
            check_row("24C-C010", "24B evidence gap matrix exists", len(gaps), ">=0", True),
            check_row("24C-C011", "24B open gaps remain execution blockers", open_gaps, "3 expected from 24B", open_gaps == int(summary24b.get("evidence_gaps_open", open_gaps))),
            check_row("24C-C012", "24B says source recovery is not executed in 24B", summary24b.get("do_not_execute_source_recovery_in_24b"), True, truthy(summary24b.get("do_not_execute_source_recovery_in_24b", False))),
        ])
    checks_df = pd.DataFrame(checks)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    review_df = build_package_review(inventory, gaps) if preliminary_ok else pd.DataFrame()
    plan_df = build_gap_plan(gaps) if preliminary_ok else pd.DataFrame([{"plan_id":"24C-PSTOP","gap_id":"STOP","evidence_id":"STOP","gap_type":"24C_STOP","resolution_plan":"Review 24C checks.","required_artifact_detail":"24C prerequisite checks failed.","blocks_source_recovery_execution":True,"next_step":"STOP","status":"STOP"}])
    open_gaps_count = int((plan_df["status"].astype(str) == "OPEN_GAP_PLAN_AUDIT_ONLY").sum()) if "status" in plan_df.columns else 0
    safety_df = build_safety_matrix(summary24b, preliminary_ok, inputs_ok, open_gaps_count)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS
    gates_df = build_required_next_gates(ok)
    outputs = {
        "input_audit": str(out / INPUT_AUDIT_FILE), "package_review_matrix": str(out / PACKAGE_REVIEW_FILE),
        "gap_resolution_planning_matrix": str(out / GAP_PLAN_FILE), "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE), "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE), "report": str(out / REPORT_FILE),
    }
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "source_recovery_evidence_package_review_only": True, "source_of_truth": "24B audited artifacts under FX_OUTPUTS/" + IN24B,
        "upstream_status": summary24b.get("status", "UNKNOWN_MISSING_24B_SUMMARY"),
        "source_recovery_approved": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False, "old_gold_disc8_quarantined": True, "approximate_reimplementation_used": False,
        "ai_api_called": False, "discord_sent": False, "mt5_order_sent": False, "live_hook_enabled": False,
        "source_recovery_execution_performed": False, "source_recovery_approval_granted": False, "source_identity_finalization_performed": False,
        "required_24b_inputs_ok": inputs_ok, "missing_inputs": missing, "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows), "package_review_rows": int(len(review_df)), "open_evidence_gaps": open_gaps_count,
        "source_recovery_execution_blocked_by_open_gaps": True, "required_next_allowed": ["24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_24c": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_24C_INPUTS_AND_24B_OUTPUTS",
        "do_not_execute_source_recovery_in_24c": True, "outputs": outputs,
    }
    write_csv(out / PACKAGE_REVIEW_FILE, review_df)
    write_csv(out / GAP_PLAN_FILE, plan_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, review_df, plan_df, gates_df, safety_df, summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
