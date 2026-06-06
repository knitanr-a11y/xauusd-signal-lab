#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STEP = "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY"
OUT_DIR = "gold_v2_24a_source_recovery_precheck_audit_only"
IN23D = "gold_v2_23d_request_more_audit_decision_routing_audit_only"

EXPECTED_23D_STATUS = "REQUEST_MORE_AUDIT_DECISION_ROUTED_TO_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_ROUTE_TARGET = "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY"
SUCCESS_STATUS = "SOURCE_RECOVERY_PRECHECK_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24A_STOP_REVIEW_SOURCE_RECOVERY_PRECHECK_INPUTS"

REPORT_FILE = "GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24a_source_recovery_precheck_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24a_input_audit.csv"
PRECHECK_MATRIX_FILE = "gold_v2_24a_source_recovery_precheck_matrix.csv"
EVIDENCE_MATRIX_FILE = "gold_v2_24a_evidence_request_matrix.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24a_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24a_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24a_safety_matrix.csv"

FORBIDDEN_GATES = {
    "SOURCE_IDENTITY_FINALIZATION",
    "SOURCE_RECOVERY",
    "LIVE",
    "FINAL_SIGNAL",
    "DISCORD_SEND",
    "MT5_ORDER",
    "AI_API",
    "LIVE_HOOK",
}

EXPECTED_STILL_BLOCKED = [
    "SOURCE_IDENTITY_FINALIZATION",
    "SOURCE_RECOVERY",
    "LIVE",
    "FINAL_SIGNAL",
    "DISCORD_SEND",
    "MT5_ORDER",
    "AI_API",
    "LIVE_HOOK",
]

FALSE_SUMMARY_FLAGS = [
    "request_more_audit_is_source_recovery_approval",
    "source_recovery_approved",
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "ledger_is_source_of_truth",
    "live_or_final_implementation_allowed",
    "oh_lc_replay_allowed",
    "live_enabled",
    "final_signal_allowed",
    "no_signal_discord_notified",
    "ai_api_called",
    "discord_sent",
    "mt5_order_sent",
    "live_hook_enabled",
    "source_recovery_execution_performed",
    "source_identity_finalization_performed",
]

EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]

REQUIRED_23D_FILES = {
    "23d_report": "GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_REPORT.md",
    "23d_summary": "gold_v2_23d_request_more_audit_decision_routing_summary.json",
    "23d_input_audit": "gold_v2_23d_input_audit.csv",
    "23d_routing_matrix": "gold_v2_23d_decision_routing_matrix.csv",
    "23d_integrated_checks": "gold_v2_23d_integrated_checks.csv",
    "23d_required_next_gates": "gold_v2_23d_required_next_gates.csv",
    "23d_safety_matrix": "gold_v2_23d_safety_matrix.csv",
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
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=encoding, keep_default_na=False)
        except Exception as exc:
            errors.append(f"{encoding}: {exc}")
    raise RuntimeError(f"CSV read failed: {path} / {'; '.join(errors)}")


def stop_rows(frame: pd.DataFrame) -> int:
    if frame.empty or "status" not in frame.columns:
        return 0
    return int((frame["status"].astype(str).str.upper() == "STOP").sum())


def md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        vals = [str(row[c]).replace("|", "\\|").replace("\n", " ") for c in columns]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def check_row(check_id: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": check_id, "check": check, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def get_external(summary: dict[str, Any], key: str) -> Any:
    external = summary.get("external_actions", {})
    return external.get(key, False) if isinstance(external, dict) else False


def allowed_next_steps(gates: pd.DataFrame, allowed_column: str) -> list[str]:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return []
    return gates.loc[gates[allowed_column].map(truthy), "next_step"].astype(str).tolist()


def forbidden_allowed_detail(gates: pd.DataFrame, allowed_column: str) -> str:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return "missing next_step/allowed column"
    subset = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
    if subset.empty:
        return "no forbidden gate rows found"
    allowed = subset[subset[allowed_column].map(truthy)]
    if allowed.empty:
        return "all forbidden gates blocked"
    return ",".join(allowed["next_step"].astype(str).tolist())


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    return int(sum(1 for key in FALSE_SUMMARY_FLAGS if truthy(summary.get(key, False))) + sum(1 for key in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, key))))


def build_input_audit(input_paths: dict[str, Path]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "role": role,
            "path": str(path),
            "required": True,
            "exists": long_path(path).exists(),
            "source_of_truth_role": "23D audited artifact",
            "notes": "24A reads this artifact only; no source recovery/live/AI/external execution.",
        }
        for role, path in input_paths.items()
    ])


def build_precheck_matrix(ok: bool) -> pd.DataFrame:
    status = "READY_FOR_EVIDENCE_INVENTORY_AUDIT_ONLY" if ok else "BLOCKED_BY_24A_STOP"
    rows = [
        ("24A-P001", "Confirm recovery target scope", "Identify exact source identity/component/artifact family under recovery consideration.", "No target can be recovered implicitly.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY", "HIGH"),
        ("24A-P002", "Confirm audited source-of-truth lineage", "List upstream audited artifacts that justify any future recovery path.", "Unverified lineage can contaminate GOLD V2.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY", "HIGH"),
        ("24A-P003", "Confirm old GOLD/DISC8 quarantine remains active", "Ensure quarantined sources are not used as active source-of-truth.", "HTF open-time mismatch may leak into recovered logic.", "APPROVE_OLD_GOLD_DISC8_DEQUARANTINE", "OLD_GOLD_DISC8_ACTIVE_USE", "HIGH"),
        ("24A-P004", "Inventory required files", "List candidate source files, ledgers, configs, docs, and hashes needed for later inspection.", "Recovery may be based on incomplete evidence.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY", "HIGH"),
        ("24A-P005", "Define non-reconstruction rule", "Record that approximate reimplementation and OHLC replay cannot substitute missing source truth.", "Approximate logic may diverge from audited SOT.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "APPROXIMATE_REIMPLEMENTATION", "HIGH"),
        ("24A-P006", "Define dry-run-only boundary", "Any later recovery attempt must first be a dry-run plan, not execution.", "Execution can mutate audit boundary.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY", "HIGH"),
        ("24A-P007", "Define acceptance gates", "Future approval requires evidence package, identity review, and explicit value.", "Approval can be inferred from precheck wording.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY", "HIGH"),
        ("24A-P008", "Confirm live/final isolation", "Recovery precheck must not connect to live evaluator/final signal.", "Audit artifact can become runtime behavior.", "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION; APPROVE_FINAL_SIGNAL", "LIVE; FINAL_SIGNAL; LIVE_HOOK", "HIGH"),
        ("24A-P009", "Confirm external isolation", "No Discord, MT5, AI API, or live hook side effects.", "External notification/order/API cost can occur from audit-only step.", "APPROVE_DISCORD_SEND; APPROVE_MT5_ORDER; APPROVE_AI_API_REVIEW; APPROVE_LIVE_HOOK", "DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK", "HIGH"),
        ("24A-P010", "Define next safe step", "Proceed only to 24B evidence inventory audit-only if 24A passes.", "Workflow may skip evidence inventory and attempt execution.", "NONE_FOR_24B_PRECHECK", "SOURCE_RECOVERY", "MEDIUM"),
        ("24A-P011", "Confirm no trade evaluation", "Do not use trade ledger fields or outcomes in this precheck.", "Trade performance could be mistaken for source identity evidence.", "NONE_FOR_24B_PRECHECK", "STRATEGY_EVALUATION", "MEDIUM"),
        ("24A-P012", "Record unresolved blockers", "Execution/finalization/live remain blocked after precheck.", "Precheck could be misread as blocker removal.", "APPROVE_SOURCE_RECOVERY_EXECUTION", "SOURCE_RECOVERY; SOURCE_IDENTITY_FINALIZATION; LIVE", "HIGH"),
    ]
    return pd.DataFrame([
        {
            "precheck_id": rid,
            "precheck_item": item,
            "audit_only_requirement": req,
            "risk_if_missing": risk,
            "future_explicit_value_required_before_execution": future,
            "blocked_actions": blocked,
            "risk_level": level,
            "status": status,
        }
        for rid, item, req, risk, future, blocked, level in rows
    ])


def build_evidence_matrix(ok: bool) -> pd.DataFrame:
    status = "REQUESTED_FOR_24B_AUDIT_ONLY" if ok else "BLOCKED_BY_24A_STOP"
    rows = [
        ("24A-E001", "23D routed package", "23D summary/report/checks/routing/safety/gates", "Prove route target and blockers.", "required", "23D artifacts"),
        ("24A-E002", "23C validated intake package", "23C summary/intake result/allowed values/checks", "Prove user-selected precheck value was valid.", "required", "23C artifacts"),
        ("24A-E003", "23A-23B request-more-audit package", "Resolution/options outputs", "Preserve chain that REQUEST_MORE_AUDIT was not approval.", "required", "23A-23B artifacts"),
        ("24A-E004", "source identity lineage docs", "Known SOT reports and handoff docs", "Identify exact recovery candidate without guessing.", "required_later", "docs/gold_v2 and FX_OUTPUTS"),
        ("24A-E005", "candidate source files", "Scripts/configs/CSV/JSON/parquet hashes if available", "Confirm what source is recoverable and what is missing.", "required_later", "repo + FX_OUTPUTS"),
        ("24A-E006", "old GOLD/DISC8 quarantine evidence", "HTF open-time mismatch suspicion and quarantine docs", "Prevent quarantined source from becoming active truth.", "required_later", "docs and audit outputs"),
        ("24A-E007", "non-reconstruction declaration", "No approximate reimplementation / no OHLC replay substitution", "Avoid rebuilding logic from outputs.", "required", "24A report"),
        ("24A-E008", "future approval policy", "Explicit required values list", "Separate precheck from execution approval.", "required", "24A report"),
        ("24A-E009", "live/external isolation proof", "Safety matrix with all external/live false", "Ensure audit-only boundary.", "required", "24A safety matrix"),
        ("24A-E010", "next-step gate proof", "24B only allowed after 24A success", "Prevent automatic execution.", "required", "24A gates"),
    ]
    return pd.DataFrame([
        {
            "evidence_id": rid,
            "evidence_name": name,
            "requested_artifact_or_scope": scope,
            "purpose": purpose,
            "priority": priority,
            "expected_location_or_source": location,
            "status": status,
        }
        for rid, name, scope, purpose, priority, location in rows
    ])


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    gates = [
        ("24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY", "Inventory evidence for source recovery precheck", "Collect and verify source identity/recovery evidence without executing recovery.", ok, "NONE_FOR_24B_INVENTORY", "" if ok else "24A checks did not pass."),
        ("SOURCE_RECOVERY", "Execute source recovery", "Would run recovery actions rather than audit-only review.", False, "APPROVE_SOURCE_RECOVERY_EXECUTION", "24A is precheck only and does not grant recovery approval."),
        ("SOURCE_IDENTITY_FINALIZATION", "Finalize source identity", "Would finalize recovered/source identity state.", False, "APPROVE_SOURCE_IDENTITY_FINALIZATION", "24A is precheck only and does not grant finalization approval."),
        ("LIVE", "Enable live evaluator/use", "Would create or enable live behavior.", False, "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "GOLD V2 remains audit-only."),
        ("FINAL_SIGNAL", "Enable final signal", "Would produce final signal behavior.", False, "APPROVE_FINAL_SIGNAL", "Final signal remains blocked."),
        ("DISCORD_SEND", "Send Discord notification", "Would send notifications externally.", False, "APPROVE_DISCORD_SEND", "Discord remains blocked; NO_SIGNAL must not notify."),
        ("MT5_ORDER", "Place MT5 order", "Would place or prepare live orders.", False, "APPROVE_MT5_ORDER", "MT5 order path remains blocked."),
        ("AI_API", "Call AI API", "Would call an external AI review API.", False, "APPROVE_AI_API_REVIEW", "AI API remains blocked."),
        ("LIVE_HOOK", "Enable live hook", "Would connect audit logic to live runtime hooks.", False, "APPROVE_LIVE_HOOK", "Live hook remains blocked."),
    ]
    return pd.DataFrame([
        {"next_step": a, "name": b, "purpose": c, "allowed_after_24a_success": bool(d), "required_human_decision_value_later": e, "still_blocked_reason": f}
        for a, b, c, d, e, f in gates
    ])


def build_safety_matrix(summary23d: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, observed: Any, expected: Any, passed: bool, notes: str) -> None:
        rows.append({"safety_item": item, "observed": observed, "expected": expected, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24A writes audit artifacts only.")
    add("precheck_only", True, True, True, "24A inventories blockers/evidence; it does not execute or approve recovery.")
    add("required_23d_inputs_exist", inputs_ok, True, inputs_ok, "All 23D source-of-truth artifacts must exist.")
    add("route_target_is_24a", summary23d.get("route_target", "UNKNOWN"), EXPECTED_ROUTE_TARGET, inputs_ok and summary23d.get("route_target") == EXPECTED_ROUTE_TARGET, "23D must route to 24A.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        observed = summary23d.get(key, False) if inputs_ok else "UNKNOWN_MISSING_23D_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        observed = get_external(summary23d, key) if inputs_ok else "UNKNOWN_MISSING_23D_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "24A does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "24A never calls AI API.")
    add("discord_sent", False, False, True, "24A never sends Discord.")
    add("mt5_order_sent", False, False, True, "24A never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "24A never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "24A never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24A never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24A never finalizes source identity.")
    add("overall_24a_precheck_passed", ok, True, bool(ok), "Overall PASS is required before using 24A outputs.")
    return pd.DataFrame(rows)


def build_report(now: str, status: str, input_audit: pd.DataFrame, checks: pd.DataFrame, precheck: pd.DataFrame, evidence: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame, summary: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 24A source recovery precheck audit-only report",
        "", f"Created UTC: {now}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Boundary", "",
        "- 24A is audit-only.",
        "- 24A reads 23D routed artifacts as the source of truth.",
        "- 24A inventories source recovery prerequisites, evidence, blockers, and future approval values.",
        "- 24A does not approve or execute source recovery.",
        "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
        "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "",
        f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
        f"- Next recommended step: `{summary.get('next_recommended_step')}`", "",
        "## Input audit", "", md_table(input_audit), "",
        "## Integrated checks", "", md_table(checks), "",
        "## Source recovery precheck matrix", "", md_table(precheck), "",
        "## Evidence request matrix", "", md_table(evidence), "",
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
    source = base / IN23D
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    input_paths = {role: source / filename for role, filename in REQUIRED_23D_FILES.items()}
    input_audit = build_input_audit(input_paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing_inputs = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()

    checks = [check_row("24A-C000", "Required 23D source-of-truth artifacts exist", ",".join(missing_inputs) if missing_inputs else "all present", "all present", inputs_ok)]
    summary23d: dict[str, Any] = {}
    upstream_stop_rows = 1 if not inputs_ok else 0

    if inputs_ok:
        summary23d = read_json(input_paths["23d_summary"])
        input23d = read_csv(input_paths["23d_input_audit"])
        routing23d = read_csv(input_paths["23d_routing_matrix"])
        checks23d = read_csv(input_paths["23d_integrated_checks"])
        gates23d = read_csv(input_paths["23d_required_next_gates"])
        safety23d = read_csv(input_paths["23d_safety_matrix"])
        upstream_stop_rows = int(summary23d.get("total_stop_rows", 999)) + stop_rows(checks23d) + stop_rows(safety23d)
        missing_required_23d_inputs = 0
        if {"required", "exists"}.issubset(input23d.columns):
            missing_required_23d_inputs = int((input23d["required"].map(truthy) & ~input23d["exists"].map(truthy)).sum())
        else:
            missing_required_23d_inputs = 999
        route_ok = bool((routing23d.get("route_target", pd.Series(dtype=str)).astype(str) == EXPECTED_ROUTE_TARGET).any()) if not routing23d.empty else False
        route_not_execution = True
        for col in ["execution_approved", "source_recovery_approved", "source_recovery_executed"]:
            if col in routing23d.columns:
                route_not_execution = route_not_execution and not bool(routing23d[col].map(truthy).any())
        allowed_after_23d = allowed_next_steps(gates23d, "allowed_after_23d_success")
        forbidden_detail = forbidden_allowed_detail(gates23d, "allowed_after_23d_success")
        false_flags = count_true_forbidden_summary_flags(summary23d)
        checks.extend([
            check_row("24A-C001", "23D status matches expected", summary23d.get("status"), EXPECTED_23D_STATUS, summary23d.get("status") == EXPECTED_23D_STATUS),
            check_row("24A-C002", "23D audit_only remains true", summary23d.get("audit_only"), True, truthy(summary23d.get("audit_only", False))),
            check_row("24A-C003", "23D decision_routing_only remains true", summary23d.get("decision_routing_only"), True, truthy(summary23d.get("decision_routing_only", False))),
            check_row("24A-C004", "23D route target is 24A", summary23d.get("route_target"), EXPECTED_ROUTE_TARGET, summary23d.get("route_target") == EXPECTED_ROUTE_TARGET),
            check_row("24A-C005", "23D route target allowed", summary23d.get("route_target_allowed"), True, truthy(summary23d.get("route_target_allowed", False))),
            check_row("24A-C006", "23D routing matrix routes to 24A", route_ok, True, route_ok),
            check_row("24A-C007", "23D routing grants no execution approval", route_not_execution, True, route_not_execution),
            check_row("24A-C008", "23D total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
            check_row("24A-C009", "23D required inputs were complete", missing_required_23d_inputs, 0, missing_required_23d_inputs == 0),
            check_row("24A-C010", "23D required next allowed only 24A", allowed_after_23d, [EXPECTED_ROUTE_TARGET], allowed_after_23d == [EXPECTED_ROUTE_TARGET]),
            check_row("24A-C011", "23D forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24A-C012", "23D forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
            check_row("24A-C013", "23D says source recovery is not executed in 23D", summary23d.get("do_not_execute_source_recovery_in_23d"), True, truthy(summary23d.get("do_not_execute_source_recovery_in_23d", False))),
        ])

    checks_df = pd.DataFrame(checks)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    precheck_df = build_precheck_matrix(preliminary_ok)
    evidence_df = build_evidence_matrix(preliminary_ok)
    safety_df = build_safety_matrix(summary23d, preliminary_ok, inputs_ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS
    if not ok:
        precheck_df = build_precheck_matrix(False)
        evidence_df = build_evidence_matrix(False)
    gates_df = build_required_next_gates(ok)

    outputs = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "precheck_matrix": str(out / PRECHECK_MATRIX_FILE),
        "evidence_request_matrix": str(out / EVIDENCE_MATRIX_FILE),
        "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE),
        "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE),
        "report": str(out / REPORT_FILE),
    }
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_precheck_only": True,
        "source_of_truth": "23D routed artifacts under FX_OUTPUTS/" + IN23D,
        "upstream_status": summary23d.get("status", "UNKNOWN_MISSING_23D_SUMMARY"),
        "route_target": summary23d.get("route_target", "UNKNOWN_MISSING_23D_SUMMARY"),
        "source_recovery_precheck_ready": bool(ok),
        "request_more_audit_is_source_recovery_approval": False,
        "source_recovery_approved": False,
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
        "old_gold_disc8_quarantined": True,
        "approximate_reimplementation_used": False,
        "ai_api_called": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "live_hook_enabled": False,
        "source_recovery_execution_performed": False,
        "source_recovery_approval_granted": False,
        "source_identity_finalization_performed": False,
        "required_23d_inputs_ok": inputs_ok,
        "missing_inputs": missing_inputs,
        "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows),
        "precheck_matrix_rows": int(len(precheck_df)),
        "evidence_request_rows": int(len(evidence_df)),
        "required_next_allowed": ["24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_24a": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY" if ok else "STOP_REVIEW_24A_INPUTS_AND_23D_OUTPUTS",
        "do_not_execute_source_recovery_in_24a": True,
        "outputs": outputs,
    }
    write_csv(out / PRECHECK_MATRIX_FILE, precheck_df)
    write_csv(out / EVIDENCE_MATRIX_FILE, evidence_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, precheck_df, evidence_df, gates_df, safety_df, summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
