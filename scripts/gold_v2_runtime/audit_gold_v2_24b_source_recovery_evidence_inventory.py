#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY"
OUT_DIR = "gold_v2_24b_source_recovery_evidence_inventory_audit_only"
IN24A = "gold_v2_24a_source_recovery_precheck_audit_only"
EXPECTED_24A_STATUS = "SOURCE_RECOVERY_PRECHECK_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
SUCCESS_STATUS = "SOURCE_RECOVERY_EVIDENCE_INVENTORY_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24B_STOP_REVIEW_SOURCE_RECOVERY_EVIDENCE_INVENTORY_INPUTS"

REPORT_FILE = "GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24b_source_recovery_evidence_inventory_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24b_input_audit.csv"
EVIDENCE_INVENTORY_FILE = "gold_v2_24b_evidence_inventory.csv"
EVIDENCE_GAP_FILE = "gold_v2_24b_evidence_gap_matrix.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24b_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24b_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24b_safety_matrix.csv"

FORBIDDEN_GATES = {
    "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL",
    "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK",
}
EXPECTED_STILL_BLOCKED = [
    "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL",
    "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK",
]
FALSE_SUMMARY_FLAGS = [
    "request_more_audit_is_source_recovery_approval", "source_recovery_approved",
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified", "ai_api_called",
    "discord_sent", "mt5_order_sent", "live_hook_enabled", "source_recovery_execution_performed",
    "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]

REQUIRED_24A_FILES = {
    "24a_report": "GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_REPORT.md",
    "24a_summary": "gold_v2_24a_source_recovery_precheck_summary.json",
    "24a_input_audit": "gold_v2_24a_input_audit.csv",
    "24a_precheck_matrix": "gold_v2_24a_source_recovery_precheck_matrix.csv",
    "24a_evidence_request_matrix": "gold_v2_24a_evidence_request_matrix.csv",
    "24a_integrated_checks": "gold_v2_24a_integrated_checks.csv",
    "24a_required_next_gates": "gold_v2_24a_required_next_gates.csv",
    "24a_safety_matrix": "gold_v2_24a_safety_matrix.csv",
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
    if isinstance(value, bool): return value
    if value is None: return False
    if isinstance(value, (int, float)) and not isinstance(value, bool): return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "allowed", "pass", "ready"}


def falsey(value: Any) -> bool:
    if isinstance(value, bool): return not value
    if value is None: return True
    if isinstance(value, (int, float)) and not isinstance(value, bool): return not bool(value)
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
    if df.empty: return "_No rows._"
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
    if sub.empty: return "no forbidden gate rows found"
    allowed = sub[sub[col].map(truthy)]
    return "all forbidden gates blocked" if allowed.empty else ",".join(allowed["next_step"].astype(str).tolist())


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    return int(sum(1 for k in FALSE_SUMMARY_FLAGS if truthy(summary.get(k, False))) + sum(1 for k in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, k))))


def build_input_audit(paths: dict[str, Path]) -> pd.DataFrame:
    return pd.DataFrame([{
        "role": role, "path": str(path), "required": True, "exists": long_path(path).exists(),
        "source_of_truth_role": "24A audited artifact",
        "notes": "24B reads this artifact only; no source recovery/live/AI/external execution.",
    } for role, path in paths.items()])


def classify_evidence(row: pd.Series, base: Path) -> dict[str, Any]:
    evidence_id = str(row.get("evidence_id", ""))
    name = str(row.get("evidence_name", ""))
    scope = str(row.get("requested_artifact_or_scope", ""))
    priority = str(row.get("priority", ""))
    source = str(row.get("expected_location_or_source", ""))
    concrete = False
    exists = False
    checked_path = ""
    availability = "NEEDS_EXPLICIT_ARTIFACT_LIST"

    known_24a_files = {
        "24A report": REPORT_FILE,
    }
    # The 24A evidence requests are mostly abstract scopes. Only concrete filename-like scopes are checked.
    if scope.endswith(".csv") or scope.endswith(".json") or scope.endswith(".md"):
        candidate = base / scope
        concrete = True
        checked_path = str(candidate)
        exists = long_path(candidate).exists()
        availability = "AVAILABLE_CONCRETE_PATH" if exists else "MISSING_CONCRETE_PATH"
    elif name in {"non-reconstruction declaration", "future approval policy", "live/external isolation proof", "next-step gate proof"}:
        # These are embedded in the already uploaded 24A report/safety/gates. Mark available as audited 24A-derived evidence, not external source evidence.
        concrete = False
        exists = True
        checked_path = "embedded_in_24a_outputs"
        availability = "AVAILABLE_AS_24A_AUDITED_OUTPUT"
    elif evidence_id in {"24A-E001", "24A-E002", "24A-E003"}:
        concrete = False
        exists = True
        checked_path = "upstream_audit_package_referenced_by_24a"
        availability = "AVAILABLE_AS_UPSTREAM_AUDITED_REFERENCE"
    else:
        availability = "NEEDS_EXPLICIT_ARTIFACT_LIST"

    gap = availability in {"NEEDS_EXPLICIT_ARTIFACT_LIST", "MISSING_CONCRETE_PATH"}
    return {
        "evidence_id": evidence_id,
        "evidence_name": name,
        "requested_artifact_or_scope": scope,
        "priority": priority,
        "expected_location_or_source": source,
        "concrete_path_checked": concrete,
        "checked_path": checked_path,
        "exists_or_available_in_audit_package": bool(exists),
        "availability_status": availability,
        "gap_detected": bool(gap),
        "next_inventory_action": "List exact artifact path/hash in 24C or later audit-only evidence package." if gap else "Retain as audited evidence reference; do not execute recovery.",
        "status": "INVENTORIED_AUDIT_ONLY",
    }


def build_gap_matrix(inventory: pd.DataFrame) -> pd.DataFrame:
    gaps = inventory[inventory["gap_detected"].map(truthy)].copy()
    if gaps.empty:
        return pd.DataFrame([{
            "gap_id": "24B-G000", "evidence_id": "NONE", "gap_type": "NO_GAPS_DETECTED",
            "gap_description": "No missing evidence gaps were detected in 24B inventory.",
            "required_next_action": "Proceed to package review audit-only.",
            "blocks_source_recovery_execution": True, "status": "NO_EXECUTION_ALLOWED",
        }])
    rows = []
    for i, (_, r) in enumerate(gaps.iterrows(), start=1):
        rows.append({
            "gap_id": f"24B-G{i:03d}",
            "evidence_id": r["evidence_id"],
            "gap_type": r["availability_status"],
            "gap_description": f"{r['evidence_name']} requires explicit concrete artifact/path/hash before recovery can be considered.",
            "required_next_action": r["next_inventory_action"],
            "blocks_source_recovery_execution": True,
            "status": "GAP_OPEN_AUDIT_ONLY",
        })
    return pd.DataFrame(rows)


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    rows = [
        ("24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY", "Review evidence package completeness", "Review available/gap evidence without executing recovery.", ok, "NONE_FOR_24C_REVIEW", "" if ok else "24B checks did not pass."),
        ("SOURCE_RECOVERY", "Execute source recovery", "Would run recovery actions rather than audit-only review.", False, "APPROVE_SOURCE_RECOVERY_EXECUTION", "24B is inventory only and does not grant recovery approval."),
        ("SOURCE_IDENTITY_FINALIZATION", "Finalize source identity", "Would finalize recovered/source identity state.", False, "APPROVE_SOURCE_IDENTITY_FINALIZATION", "24B does not grant finalization approval."),
        ("LIVE", "Enable live evaluator/use", "Would create or enable live behavior.", False, "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "GOLD V2 remains audit-only."),
        ("FINAL_SIGNAL", "Enable final signal", "Would produce final signal behavior.", False, "APPROVE_FINAL_SIGNAL", "Final signal remains blocked."),
        ("DISCORD_SEND", "Send Discord notification", "Would send notifications externally.", False, "APPROVE_DISCORD_SEND", "Discord remains blocked; NO_SIGNAL must not notify."),
        ("MT5_ORDER", "Place MT5 order", "Would place or prepare live orders.", False, "APPROVE_MT5_ORDER", "MT5 order path remains blocked."),
        ("AI_API", "Call AI API", "Would call an external AI review API.", False, "APPROVE_AI_API_REVIEW", "AI API remains blocked."),
        ("LIVE_HOOK", "Enable live hook", "Would connect audit logic to live runtime hooks.", False, "APPROVE_LIVE_HOOK", "Live hook remains blocked."),
    ]
    return pd.DataFrame([{"next_step": a, "name": b, "purpose": c, "allowed_after_24b_success": bool(d), "required_human_decision_value_later": e, "still_blocked_reason": f} for a,b,c,d,e,f in rows])


def build_safety_matrix(summary24a: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str):
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24B writes audit artifacts only.")
    add("evidence_inventory_only", True, True, True, "24B inventories evidence/gaps and never executes recovery.")
    add("required_24a_inputs_exist", inputs_ok, True, inputs_ok, "All 24A source-of-truth artifacts must exist.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24a.get(key, False) if inputs_ok else "UNKNOWN_MISSING_24A_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24a, key) if inputs_ok else "UNKNOWN_MISSING_24A_SUMMARY"
        add(key, obs, False, inputs_ok and falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "24B does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "24B never calls AI API.")
    add("discord_sent", False, False, True, "24B never sends Discord.")
    add("mt5_order_sent", False, False, True, "24B never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "24B never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "24B never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24B never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24B never finalizes source identity.")
    add("overall_24b_inventory_passed", ok, True, bool(ok), "Overall PASS is required before using 24B outputs.")
    return pd.DataFrame(rows)


def build_report(now: str, status: str, input_audit: pd.DataFrame, checks: pd.DataFrame, inventory: pd.DataFrame, gaps: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 24B source recovery evidence inventory audit-only report", "",
        f"Created UTC: {now}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Boundary", "", "- 24B is audit-only.", "- 24B reads 24A audited artifacts as the source of truth.",
        "- 24B inventories requested evidence and gaps only.", "- 24B does not approve or execute source recovery.",
        "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
        "- Old GOLD/DISC8 remain quarantined.", "", "## Outcome", "",
        f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
        f"- Evidence inventory rows: `{summary.get('evidence_inventory_rows')}`",
        f"- Evidence gaps open: `{summary.get('evidence_gaps_open')}`",
        f"- Next recommended step: `{summary.get('next_recommended_step')}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "",
        "## Evidence inventory", "", md_table(inventory), "", "## Evidence gap matrix", "", md_table(gaps), "",
        "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "",
        "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`",
        "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`",
        "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); out = base / OUT_DIR; source = base / IN24A
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    paths = {role: source / filename for role, filename in REQUIRED_24A_FILES.items()}
    input_audit = build_input_audit(paths); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()
    checks = [check_row("24B-C000", "Required 24A source-of-truth artifacts exist", ",".join(missing) if missing else "all present", "all present", inputs_ok)]
    summary24a: dict[str, Any] = {}; evidence24a = pd.DataFrame(); upstream_stop_rows = 1 if not inputs_ok else 0
    precheck_rows = 0; evidence_rows = 0
    if inputs_ok:
        summary24a = read_json(paths["24a_summary"])
        input24a = read_csv(paths["24a_input_audit"])
        precheck24a = read_csv(paths["24a_precheck_matrix"])
        evidence24a = read_csv(paths["24a_evidence_request_matrix"])
        checks24a = read_csv(paths["24a_integrated_checks"])
        gates24a = read_csv(paths["24a_required_next_gates"])
        safety24a = read_csv(paths["24a_safety_matrix"])
        upstream_stop_rows = int(summary24a.get("total_stop_rows", 999)) + stop_rows(checks24a) + stop_rows(safety24a)
        precheck_rows = len(precheck24a); evidence_rows = len(evidence24a)
        missing_required_24a_inputs = 0
        if {"required", "exists"}.issubset(input24a.columns):
            missing_required_24a_inputs = int((input24a["required"].map(truthy) & ~input24a["exists"].map(truthy)).sum())
        else:
            missing_required_24a_inputs = 999
        allowed_after_24a = allowed_next_steps(gates24a, "allowed_after_24a_success")
        forbidden_detail = forbidden_allowed_detail(gates24a, "allowed_after_24a_success")
        false_flags = count_true_forbidden_summary_flags(summary24a)
        checks.extend([
            check_row("24B-C001", "24A status matches expected", summary24a.get("status"), EXPECTED_24A_STATUS, summary24a.get("status") == EXPECTED_24A_STATUS),
            check_row("24B-C002", "24A audit_only remains true", summary24a.get("audit_only"), True, truthy(summary24a.get("audit_only", False))),
            check_row("24B-C003", "24A source_recovery_precheck_only remains true", summary24a.get("source_recovery_precheck_only"), True, truthy(summary24a.get("source_recovery_precheck_only", False))),
            check_row("24B-C004", "24A source recovery precheck ready", summary24a.get("source_recovery_precheck_ready"), True, truthy(summary24a.get("source_recovery_precheck_ready", False))),
            check_row("24B-C005", "24A total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
            check_row("24B-C006", "24A required inputs were complete", missing_required_24a_inputs, 0, missing_required_24a_inputs == 0),
            check_row("24B-C007", "24A required next allowed only 24B", allowed_after_24a, ["24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY"], allowed_after_24a == ["24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY"]),
            check_row("24B-C008", "24A forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24B-C009", "24A forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
            check_row("24B-C010", "24A precheck matrix row count meets minimum", precheck_rows, ">=10", precheck_rows >= 10),
            check_row("24B-C011", "24A evidence request row count meets minimum", evidence_rows, ">=8", evidence_rows >= 8),
            check_row("24B-C012", "24A says source recovery is not executed in 24A", summary24a.get("do_not_execute_source_recovery_in_24a"), True, truthy(summary24a.get("do_not_execute_source_recovery_in_24a", False))),
        ])
    checks_df = pd.DataFrame(checks)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    inventory_df = pd.DataFrame([classify_evidence(row, source) for _, row in evidence24a.iterrows()]) if preliminary_ok else pd.DataFrame()
    if inventory_df.empty:
        inventory_df = pd.DataFrame(columns=["evidence_id", "evidence_name", "requested_artifact_or_scope", "priority", "expected_location_or_source", "concrete_path_checked", "checked_path", "exists_or_available_in_audit_package", "availability_status", "gap_detected", "next_inventory_action", "status"])
    gap_df = build_gap_matrix(inventory_df) if preliminary_ok else pd.DataFrame([{"gap_id":"24B-GSTOP","evidence_id":"STOP","gap_type":"24B_STOP","gap_description":"24B prerequisite checks failed.","required_next_action":"Review 24B checks.","blocks_source_recovery_execution":True,"status":"STOP"}])
    safety_df = build_safety_matrix(summary24a, preliminary_ok, inputs_ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS
    gates_df = build_required_next_gates(ok)
    gaps_open = int(inventory_df["gap_detected"].map(truthy).sum()) if not inventory_df.empty and "gap_detected" in inventory_df.columns else 0
    outputs = {
        "input_audit": str(out / INPUT_AUDIT_FILE), "evidence_inventory": str(out / EVIDENCE_INVENTORY_FILE),
        "evidence_gap_matrix": str(out / EVIDENCE_GAP_FILE), "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE), "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE), "report": str(out / REPORT_FILE),
    }
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "source_recovery_evidence_inventory_only": True, "source_of_truth": "24A audited artifacts under FX_OUTPUTS/" + IN24A,
        "upstream_status": summary24a.get("status", "UNKNOWN_MISSING_24A_SUMMARY"),
        "source_recovery_approved": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False, "old_gold_disc8_quarantined": True, "approximate_reimplementation_used": False,
        "ai_api_called": False, "discord_sent": False, "mt5_order_sent": False, "live_hook_enabled": False,
        "source_recovery_execution_performed": False, "source_recovery_approval_granted": False, "source_identity_finalization_performed": False,
        "required_24a_inputs_ok": inputs_ok, "missing_inputs": missing, "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows), "evidence_inventory_rows": int(len(inventory_df)), "evidence_gaps_open": gaps_open,
        "precheck_matrix_rows_from_24a": precheck_rows, "evidence_request_rows_from_24a": evidence_rows,
        "required_next_allowed": ["24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_24b": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_24B_INPUTS_AND_24A_OUTPUTS",
        "do_not_execute_source_recovery_in_24b": True, "outputs": outputs,
    }
    write_csv(out / EVIDENCE_INVENTORY_FILE, inventory_df)
    write_csv(out / EVIDENCE_GAP_FILE, gap_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, inventory_df, gap_df, gates_df, safety_df, summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
