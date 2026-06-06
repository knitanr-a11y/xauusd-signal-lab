#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STEP = "23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY"
OUT_DIR = "gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only"
IN22G = "gold_v2_22g_additional_audit_read_only_final_handoff_audit_only"

SELECTED = "REQUEST_MORE_AUDIT"
EXPECTED_22G_STATUS = (
    "ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_"
    "AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
)
SUCCESS_STATUS = "REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
STOP_STATUS = "23A_STOP_REVIEW_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INPUTS"

REPORT_FILE = "GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_23a_request_more_audit_resolution_matrix_summary.json"
INPUT_AUDIT_FILE = "gold_v2_23a_input_audit.csv"
RESOLUTION_MATRIX_FILE = "gold_v2_23a_resolution_matrix.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_23a_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_23a_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_23a_safety_matrix.csv"

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

FALSE_SUMMARY_FLAGS = [
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
]

EXTERNAL_ACTION_KEYS = [
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
]

REQUIRED_22G_FILES = {
    "22g_report": "GOLD_V2_22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md",
    "22g_final_handoff": "GOLD_V2_22G_FINAL_HANDOFF_REQUEST_MORE_AUDIT_AUDIT_ONLY.md",
    "22g_summary": "gold_v2_22g_additional_audit_read_only_final_handoff_summary.json",
    "22g_input_audit": "gold_v2_22g_input_audit.csv",
    "22g_handoff_checks": "gold_v2_22g_handoff_checks.csv",
    "22g_required_next_gates": "gold_v2_22g_required_next_gates.csv",
    "22g_safety_matrix": "gold_v2_22g_safety_matrix.csv",
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
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "allowed", "pass", "ready"}


def falsey(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not bool(value)
    text = str(value).strip().lower()
    return text in {"", "0", "false", "no", "n", "blocked", "none", "null"}


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
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            values.append(str(row[column]).replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def check_row(check_id: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "check": check,
        "observed": observed,
        "expected": expected,
        "status": "PASS" if ok else "STOP",
    }


def get_external(summary: dict[str, Any], key: str) -> Any:
    external = summary.get("external_actions", {})
    if isinstance(external, dict):
        return external.get(key, False)
    return False


def count_forbidden_allowed_gates(gates: pd.DataFrame, allowed_column: str) -> int:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return 999
    subset = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
    return int(subset[allowed_column].map(truthy).sum())


def forbidden_gate_detail(gates: pd.DataFrame, allowed_column: str) -> str:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return "missing next_step/allowed column"
    subset = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)].copy()
    if subset.empty:
        return "no forbidden gate rows found"
    allowed = subset[subset[allowed_column].map(truthy)]
    if allowed.empty:
        return "all forbidden gates blocked"
    return ",".join(allowed["next_step"].astype(str).tolist())


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    flag_count = sum(1 for key in FALSE_SUMMARY_FLAGS if truthy(summary.get(key, False)))
    external_count = sum(1 for key in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, key)))
    return int(flag_count + external_count)


def build_input_audit(input_paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in input_paths.items():
        rows.append(
            {
                "role": role,
                "path": str(path),
                "required": True,
                "exists": long_path(path).exists(),
                "source_of_truth_role": "22G audited artifact",
                "notes": "23A reads this artifact only; no source recovery/live/AI execution.",
            }
        )
    return pd.DataFrame(rows)


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "next_step": "23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY",
                "name": "Prepare explicit human decision options after 23A review",
                "purpose": "Convert remaining uncertainty into exact human-review options without executing recovery.",
                "allowed_after_23a_success": bool(ok),
                "required_human_decision_value_later": "REQUEST_MORE_AUDIT_DECISION_OPTIONS_AUDIT_ONLY",
                "still_blocked_reason": "" if ok else "23A checks did not pass.",
            },
            {
                "next_step": "SOURCE_IDENTITY_FINALIZATION",
                "name": "Finalize source identity",
                "purpose": "Would finalize recovered/source identity state.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
                "still_blocked_reason": "REQUEST_MORE_AUDIT is not finalization approval.",
            },
            {
                "next_step": "SOURCE_RECOVERY",
                "name": "Execute source recovery",
                "purpose": "Would run recovery actions rather than audit-only review.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION",
                "still_blocked_reason": "REQUEST_MORE_AUDIT is not source recovery approval.",
            },
            {
                "next_step": "LIVE",
                "name": "Enable live evaluator/use",
                "purpose": "Would create or enable live behavior.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
                "still_blocked_reason": "GOLD V2 remains audit-only.",
            },
            {
                "next_step": "FINAL_SIGNAL",
                "name": "Enable final signal",
                "purpose": "Would produce final signal behavior.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL",
                "still_blocked_reason": "Final signal remains explicitly blocked.",
            },
            {
                "next_step": "DISCORD_SEND",
                "name": "Send Discord notification",
                "purpose": "Would send notifications externally.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_DISCORD_SEND",
                "still_blocked_reason": "Discord notification remains explicitly blocked; NO_SIGNAL must not notify.",
            },
            {
                "next_step": "MT5_ORDER",
                "name": "Place MT5 order",
                "purpose": "Would place or prepare live orders.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_MT5_ORDER",
                "still_blocked_reason": "MT5 order path remains explicitly blocked.",
            },
            {
                "next_step": "AI_API",
                "name": "Call AI API",
                "purpose": "Would call an external AI review API.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_AI_API_REVIEW",
                "still_blocked_reason": "AI API remains explicitly blocked for 23A.",
            },
            {
                "next_step": "LIVE_HOOK",
                "name": "Enable live hook",
                "purpose": "Would connect audit logic to live runtime hooks.",
                "allowed_after_23a_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_HOOK",
                "still_blocked_reason": "Live hook remains explicitly blocked.",
            },
        ]
    )


def build_safety_matrix(summary: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(item: str, observed: Any, expected: Any, passed: bool, notes: str) -> None:
        rows.append(
            {
                "safety_item": item,
                "observed": observed,
                "expected": expected,
                "status": "PASS" if passed else "STOP",
                "notes": notes,
            }
        )

    add("audit_only", True, True, True, "23A writes audit artifacts only.")
    add("integrated_audit_only_script", True, True, True, "23A uses one integrated audit-only script.")
    add("required_22g_inputs_exist", inputs_ok, True, inputs_ok, "All 22G source-of-truth artifacts must exist.")
    add(
        "request_more_audit_is_not_source_recovery_approval",
        SELECTED,
        "NOT_APPROVAL",
        True,
        "REQUEST_MORE_AUDIT is interpreted only as a request for more audit.",
    )
    for key in [
        "source_recovery_approved",
        "source_recovery_executed",
        "source_identity_finalized",
        "source_identity_recovered",
        "live_or_final_implementation_allowed",
        "live_enabled",
        "final_signal_allowed",
        "no_signal_discord_notified",
    ]:
        observed = summary.get(key, False) if inputs_ok else "UNKNOWN_MISSING_22G_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        observed = get_external(summary, key) if inputs_ok else "UNKNOWN_MISSING_22G_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "23A does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "23A never calls AI API.")
    add("source_recovery_execution_performed", False, False, True, "23A never executes source recovery.")
    add("source_identity_finalization_performed", False, False, True, "23A never finalizes source identity.")
    add("overall_23a_integrated_checks_passed", ok, True, bool(ok), "Overall PASS is required before using 23A outputs.")
    return pd.DataFrame(rows)


def build_resolution_matrix(
    ok: bool,
    inputs_ok: bool,
    summary: dict[str, Any],
    missing_inputs: list[str],
    upstream_stop_rows: int,
) -> pd.DataFrame:
    upstream_status = summary.get("status", "UNKNOWN_MISSING_22G_SUMMARY")
    selected_value = summary.get("selected_value", "UNKNOWN_MISSING_22G_SUMMARY")
    decision_value = summary.get("decision_value", "UNKNOWN_MISSING_22G_SUMMARY")
    common_status = "READY_AUDIT_ONLY" if ok else "BLOCKED_BY_23A_STOP"

    rows = [
        {
            "item_id": "23A-R001",
            "question": "REQUEST_MORE_AUDIT means what?",
            "current_answer": (
                "REQUEST_MORE_AUDIT means more audit only; it is not source recovery approval."
                if inputs_ok
                else "Cannot verify because required 22G artifacts are missing."
            ),
            "evidence_available": f"22G selected_value={selected_value}; decision_value={decision_value}; status={upstream_status}",
            "evidence_missing": "Explicit approval value for recovery/finalization/live/external action.",
            "risk_if_ignored": "A read-only review value could be misread as permission to execute recovery or live paths.",
            "allowed_current_action": "Produce and review this audit-only resolution matrix.",
            "blocked_actions": "SOURCE_RECOVERY; SOURCE_IDENTITY_FINALIZATION; LIVE; FINAL_SIGNAL; DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK",
            "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION only if recovery is intentionally approved later.",
            "recommended_next_step": "Review 23A outputs, then use 23B decision-options audit-only if needed.",
            "status": common_status,
        },
        {
            "item_id": "23A-R002",
            "question": "Is source recovery approved?",
            "current_answer": f"No. source_recovery_approved={summary.get('source_recovery_approved', 'UNKNOWN')}",
            "evidence_available": "22G summary and 23A safety checks.",
            "evidence_missing": "No explicit APPROVE_SOURCE_RECOVERY_EXECUTION human decision value exists.",
            "risk_if_ignored": "Unapproved source recovery could mutate the audit boundary.",
            "allowed_current_action": "Audit-only explanation of missing approval.",
            "blocked_actions": "SOURCE_RECOVERY",
            "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION",
            "recommended_next_step": "Keep recovery blocked; clarify decision values in 23B if the user wants options.",
            "status": common_status,
        },
        {
            "item_id": "23A-R003",
            "question": "Is source identity finalization approved?",
            "current_answer": f"No. source_identity_finalized={summary.get('source_identity_finalized', 'UNKNOWN')}; source_identity_recovered={summary.get('source_identity_recovered', 'UNKNOWN')}",
            "evidence_available": "22G summary and 23A safety checks.",
            "evidence_missing": "No explicit APPROVE_SOURCE_IDENTITY_FINALIZATION value exists.",
            "risk_if_ignored": "Identity could be finalized before the evidence package is accepted.",
            "allowed_current_action": "Audit-only explanation of finalization blocker.",
            "blocked_actions": "SOURCE_IDENTITY_FINALIZATION",
            "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
            "recommended_next_step": "Do not finalize identity in 23A.",
            "status": common_status,
        },
        {
            "item_id": "23A-R004",
            "question": "Are live evaluator/final signal paths allowed?",
            "current_answer": f"No. live_enabled={summary.get('live_enabled', 'UNKNOWN')}; final_signal_allowed={summary.get('final_signal_allowed', 'UNKNOWN')}",
            "evidence_available": "22G summary, 22G gates, and 23A required next gates.",
            "evidence_missing": "No explicit live/final approval values and no live parity approval.",
            "risk_if_ignored": "Audit-only artifacts could be connected to trading/runtime by mistake.",
            "allowed_current_action": "Audit-only reporting only.",
            "blocked_actions": "LIVE; FINAL_SIGNAL; LIVE_HOOK",
            "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION; APPROVE_FINAL_SIGNAL; APPROVE_LIVE_HOOK",
            "recommended_next_step": "Keep live/final blocked.",
            "status": common_status,
        },
        {
            "item_id": "23A-R005",
            "question": "Are external actions allowed?",
            "current_answer": (
                "No. Discord, MT5, AI API, and live hook remain disabled. NO_SIGNAL must not notify."
            ),
            "evidence_available": f"external_actions={summary.get('external_actions', 'UNKNOWN_MISSING_22G_SUMMARY')}",
            "evidence_missing": "No explicit external-action approval values.",
            "risk_if_ignored": "External notifications, orders, or API cost/actions could occur from an audit-only step.",
            "allowed_current_action": "Write CSV/JSON/Markdown outputs locally only.",
            "blocked_actions": "DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK",
            "required_human_decision_value_later": "APPROVE_DISCORD_SEND; APPROVE_MT5_ORDER; APPROVE_AI_API_REVIEW; APPROVE_LIVE_HOOK",
            "recommended_next_step": "Do not add or run external integrations.",
            "status": common_status,
        },
        {
            "item_id": "23A-R006",
            "question": "What is the old GOLD/DISC8 state?",
            "current_answer": "Old GOLD/DISC8 remain quarantined because of suspected HTF open-time mismatch.",
            "evidence_available": "22G handoff policy and 23A safety matrix.",
            "evidence_missing": "No de-quarantine approval or HTF mismatch resolution package.",
            "risk_if_ignored": "A quarantined source could contaminate GOLD V2 evidence.",
            "allowed_current_action": "Mention quarantine state in audit outputs.",
            "blocked_actions": "Using old GOLD/DISC8 as active source-of-truth for live/final behavior.",
            "required_human_decision_value_later": "APPROVE_OLD_GOLD_DISC8_DEQUARANTINE after a separate HTF audit.",
            "recommended_next_step": "Keep old GOLD/DISC8 out of 23A.",
            "status": common_status,
        },
        {
            "item_id": "23A-R007",
            "question": "What uncertainty remains?",
            "current_answer": "Whether the user later wants recovery, identity finalization, live/final enablement, or only more audit remains undecided.",
            "evidence_available": "REQUEST_MORE_AUDIT chain reached read-only completion; upstream_stop_rows=%s." % upstream_stop_rows,
            "evidence_missing": "The next explicit human decision value selecting one allowed path.",
            "risk_if_ignored": "The next step could drift back into fragmented meta-audits or unsafe execution.",
            "allowed_current_action": "Summarize uncertainty in one matrix.",
            "blocked_actions": "Any execution or finalization action.",
            "required_human_decision_value_later": "REQUEST_MORE_AUDIT_DECISION_OPTIONS_AUDIT_ONLY or a specific approval value.",
            "recommended_next_step": "23B should present a compact decision menu, not execute any action.",
            "status": common_status,
        },
        {
            "item_id": "23A-R008",
            "question": "What evidence is missing?",
            "current_answer": "Explicit approval values and any separate evidence required to lift recovery/finalization/live blockers are missing.",
            "evidence_available": "22G source-of-truth artifacts exist=%s; missing_inputs=%s." % (inputs_ok, ",".join(missing_inputs) or "none"),
            "evidence_missing": "Approval value; recovery package acceptance; identity finalization acceptance; live/final approval.",
            "risk_if_ignored": "The audit chain could be mistaken for substantive source recovery.",
            "allowed_current_action": "List missing evidence.",
            "blocked_actions": "Treating REQUEST_MORE_AUDIT as approval.",
            "required_human_decision_value_later": "Exact explicit approval value matching the requested action.",
            "recommended_next_step": "Resolve via human decision options after reviewing 23A outputs.",
            "status": common_status,
        },
        {
            "item_id": "23A-R009",
            "question": "What can be closed as complete from REQUEST_MORE_AUDIT chain?",
            "current_answer": "The 21A-22G read-only additional-audit handoff can be considered complete if 23A passes.",
            "evidence_available": f"22G final_handoff_ready={summary.get('final_handoff_ready', 'UNKNOWN')}; 23A ok={ok}.",
            "evidence_missing": "No execution approval is included in this closure.",
            "risk_if_ignored": "Repeated meta-audit chains may continue without resolving the user's decision need.",
            "allowed_current_action": "Close only the read-only REQUEST_MORE_AUDIT audit package.",
            "blocked_actions": "Closing recovery/finalization/live blockers.",
            "required_human_decision_value_later": "REQUEST_MORE_AUDIT_DECISION_OPTIONS_AUDIT_ONLY for the next audit-only decision menu.",
            "recommended_next_step": "Use 23B only after user reviews 23A outputs.",
            "status": common_status,
        },
        {
            "item_id": "23A-R010",
            "question": "What is the fastest safe next move?",
            "current_answer": "After 23A passes, prepare 23B human decision options audit-only; do not proceed automatically.",
            "evidence_available": "22G handoff says do not proceed to 23B automatically; 23A gates allow only 23B after success.",
            "evidence_missing": "User's next explicit decision after reviewing 23A outputs.",
            "risk_if_ignored": "The workflow may again split into low-value meta-audit or accidentally execute blocked actions.",
            "allowed_current_action": "Stop after generating 23A outputs.",
            "blocked_actions": "Automatic 23B execution; source recovery; finalization; live/final/external actions.",
            "required_human_decision_value_later": "User instruction to run 23B audit-only, or a separate explicit approval gate later.",
            "recommended_next_step": "Run BAT, inspect outputs, then decide.",
            "status": common_status,
        },
    ]

    if not inputs_ok:
        for row in rows:
            row["status"] = "STOP_MISSING_22G_INPUTS"
            row["recommended_next_step"] = "Restore or rerun 22G outputs before 23A can be trusted."

    return pd.DataFrame(rows)


def build_report(
    now: str,
    status: str,
    input_audit: pd.DataFrame,
    checks: pd.DataFrame,
    resolution: pd.DataFrame,
    gates: pd.DataFrame,
    safety: pd.DataFrame,
    summary: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# GOLD V2 23A request more audit resolution matrix integrated audit-only report",
            "",
            f"Created UTC: {now}",
            f"Step: `{STEP}`",
            f"Status: `{status}`",
            "",
            "## Boundary",
            "",
            "- 23A is audit-only.",
            "- 23A reads 22G audited artifacts as the source of truth.",
            "- 23A does not execute source recovery, source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, or live hook.",
            "- `REQUEST_MORE_AUDIT` remains a request for more audit and is not source recovery approval.",
            "- Old GOLD/DISC8 remain quarantined.",
            "",
            "## Outcome",
            "",
            f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
            f"- Next recommended step: `{summary.get('next_recommended_step')}`",
            "",
            "## Input audit",
            "",
            md_table(input_audit),
            "",
            "## Integrated checks",
            "",
            md_table(checks),
            "",
            "## Resolution matrix",
            "",
            md_table(resolution),
            "",
            "## Required next gates",
            "",
            md_table(gates),
            "",
            "## Safety matrix",
            "",
            md_table(safety),
            "",
            "## Explicit non-actions",
            "",
            "- AI API called: `false`",
            "- Discord notification sent: `false`",
            "- MT5 order sent: `false`",
            "- Live hook enabled: `false`",
            "- Source recovery executed: `false`",
            "- Source identity finalized/recovered: `false`",
        ]
    )


def main() -> int:
    base = fx_outputs_root()
    out = base / OUT_DIR
    source = base / IN22G
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    input_paths = {role: source / filename for role, filename in REQUIRED_22G_FILES.items()}
    input_audit = build_input_audit(input_paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)

    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing_inputs = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()

    checks: list[dict[str, Any]] = [
        check_row(
            "23A-C000",
            "Required 22G source-of-truth artifacts exist",
            ",".join(missing_inputs) if missing_inputs else "all present",
            "all present",
            inputs_ok,
        )
    ]

    summary22: dict[str, Any] = {}
    checks22 = pd.DataFrame()
    gates22 = pd.DataFrame()
    safety22 = pd.DataFrame()
    upstream_stop_rows = 1 if not inputs_ok else 0

    if inputs_ok:
        summary22 = read_json(input_paths["22g_summary"])
        checks22 = read_csv(input_paths["22g_handoff_checks"])
        gates22 = read_csv(input_paths["22g_required_next_gates"])
        safety22 = read_csv(input_paths["22g_safety_matrix"])
        input22 = read_csv(input_paths["22g_input_audit"])
        missing_required_22g_inputs = 0
        if {"required", "exists"}.issubset(input22.columns):
            required_mask = input22["required"].map(truthy)
            exists_mask = input22["exists"].map(truthy)
            missing_required_22g_inputs = int((required_mask & ~exists_mask).sum())
        else:
            missing_required_22g_inputs = 999

        upstream_stop_rows = int(summary22.get("total_stop_rows", 999)) + stop_rows(checks22) + stop_rows(safety22)
        false_flags = count_true_forbidden_summary_flags(summary22)
        forbidden_allowed = count_forbidden_allowed_gates(gates22, "allowed_after_22g_success")
        forbidden_detail = forbidden_gate_detail(gates22, "allowed_after_22g_success")

        checks.extend(
            [
                check_row(
                    "23A-C001",
                    "22G status matches expected",
                    summary22.get("status"),
                    EXPECTED_22G_STATUS,
                    summary22.get("status") == EXPECTED_22G_STATUS,
                ),
                check_row(
                    "23A-C002",
                    "22G audit_only remains true",
                    summary22.get("audit_only"),
                    True,
                    truthy(summary22.get("audit_only", False)),
                ),
                check_row(
                    "23A-C003",
                    "22G selected_value remains REQUEST_MORE_AUDIT",
                    summary22.get("selected_value"),
                    SELECTED,
                    summary22.get("selected_value") == SELECTED,
                ),
                check_row(
                    "23A-C004",
                    "22G decision_value remains REQUEST_MORE_AUDIT",
                    summary22.get("decision_value"),
                    SELECTED,
                    summary22.get("decision_value") == SELECTED,
                ),
                check_row(
                    "23A-C005",
                    "22G final_handoff_ready is true",
                    summary22.get("final_handoff_ready"),
                    True,
                    truthy(summary22.get("final_handoff_ready", False)),
                ),
                check_row(
                    "23A-C006",
                    "Total upstream STOP rows are zero",
                    upstream_stop_rows,
                    0,
                    upstream_stop_rows == 0,
                ),
                check_row(
                    "23A-C007",
                    "Forbidden 22G gates remain blocked",
                    forbidden_detail,
                    "all forbidden gates blocked",
                    forbidden_allowed == 0,
                ),
                check_row(
                    "23A-C008",
                    "Forbidden 22G summary/external flags remain false",
                    false_flags,
                    0,
                    false_flags == 0,
                ),
                check_row(
                    "23A-C009",
                    "22G source recovery approval remains false",
                    summary22.get("source_recovery_approved"),
                    False,
                    falsey(summary22.get("source_recovery_approved", False)),
                ),
                check_row(
                    "23A-C010",
                    "22G source recovery execution remains false",
                    summary22.get("source_recovery_executed"),
                    False,
                    falsey(summary22.get("source_recovery_executed", False)),
                ),
                check_row(
                    "23A-C011",
                    "22G source identity finalization/recovery remain false",
                    f"finalized={summary22.get('source_identity_finalized')}; recovered={summary22.get('source_identity_recovered')}",
                    "finalized=False; recovered=False",
                    falsey(summary22.get("source_identity_finalized", False))
                    and falsey(summary22.get("source_identity_recovered", False)),
                ),
                check_row(
                    "23A-C012",
                    "22G live/final implementation flags remain false",
                    f"live_or_final={summary22.get('live_or_final_implementation_allowed')}; live={summary22.get('live_enabled')}; final={summary22.get('final_signal_allowed')}",
                    "all false",
                    falsey(summary22.get("live_or_final_implementation_allowed", False))
                    and falsey(summary22.get("live_enabled", False))
                    and falsey(summary22.get("final_signal_allowed", False)),
                ),
                check_row(
                    "23A-C013",
                    "22G external actions remain false",
                    summary22.get("external_actions"),
                    "all false",
                    all(falsey(get_external(summary22, key)) for key in EXTERNAL_ACTION_KEYS),
                ),
                check_row(
                    "23A-C014",
                    "22G input audit did not report missing required upstream inputs",
                    missing_required_22g_inputs,
                    0,
                    missing_required_22g_inputs == 0,
                ),
            ]
        )

    checks_df = pd.DataFrame(checks)
    total_stop_rows = stop_rows(checks_df)
    ok = inputs_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS

    safety_df = build_safety_matrix(summary22, ok, inputs_ok)
    safety_stop_rows = stop_rows(safety_df)

    if safety_stop_rows:
        ok = False
        status = STOP_STATUS
    gates_df = build_required_next_gates(ok)
    resolution_df = build_resolution_matrix(ok, inputs_ok, summary22, missing_inputs, upstream_stop_rows)

    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)

    output_paths = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "resolution_matrix": str(out / RESOLUTION_MATRIX_FILE),
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
        "integrated_audit_only": True,
        "source_of_truth": "22G audited artifacts under FX_OUTPUTS/" + IN22G,
        "selected_value": summary22.get("selected_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_22G_SUMMARY"),
        "decision_value": summary22.get("decision_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_22G_SUMMARY"),
        "upstream_status": summary22.get("status", "UNKNOWN_MISSING_22G_SUMMARY"),
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
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "no_signal_discord_notified": False,
        "old_gold_disc8_quarantined": True,
        "approximate_reimplementation_used": False,
        "ai_api_called": False,
        "source_recovery_execution_performed": False,
        "source_identity_finalization_performed": False,
        "required_22g_inputs_ok": inputs_ok,
        "missing_inputs": missing_inputs,
        "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows),
        "resolution_matrix_rows": int(len(resolution_df)),
        "expected_min_resolution_matrix_rows": 9,
        "required_next_allowed": ["23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_23a": [
            "SOURCE_IDENTITY_FINALIZATION",
            "SOURCE_RECOVERY",
            "LIVE",
            "FINAL_SIGNAL",
            "DISCORD_SEND",
            "MT5_ORDER",
            "AI_API",
            "LIVE_HOOK",
        ],
        "next_recommended_step": (
            "23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_AFTER_USER_REVIEWS_23A_OUTPUTS"
            if ok
            else "STOP_REVIEW_23A_INPUTS_AND_22G_OUTPUTS"
        ),
        "do_not_proceed_automatically_to_23b": True,
        "outputs": output_paths,
    }

    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_csv(out / RESOLUTION_MATRIX_FILE, resolution_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, resolution_df, gates_df, safety_df, summary))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
