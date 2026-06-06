#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_24h_source_recovery_execution_decision_intake_audit_only"
IN24G = "gold_v2_24g_source_recovery_execution_decision_options_audit_only"
EXPECTED_24G_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
WAIT_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
VALID_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
INVALID_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_INVALID_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24H_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_INPUTS_OR_SAFETY"

REPORT_FILE = "GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24h_source_recovery_execution_decision_intake_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24h_input_audit.csv"
TEMPLATE_FILE = "gold_v2_24h_human_decision_input_template.json"
USER_DECISION_FILE = "gold_v2_24h_human_decision_input.json"
INTAKE_RESULT_FILE = "gold_v2_24h_human_decision_intake_result.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24h_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24h_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24h_safety_matrix.csv"

REQUIRED_24G_FILES = {
    "24g_report": "GOLD_V2_24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md",
    "24g_summary": "gold_v2_24g_source_recovery_execution_decision_options_summary.json",
    "24g_input_audit": "gold_v2_24g_input_audit.csv",
    "24g_decision_options": "gold_v2_24g_decision_options.csv",
    "24g_human_decision_template": "gold_v2_24g_human_decision_input_template.json",
    "24g_integrated_checks": "gold_v2_24g_integrated_checks.csv",
    "24g_required_next_gates": "gold_v2_24g_required_next_gates.csv",
    "24g_safety_matrix": "gold_v2_24g_safety_matrix.csv",
}

FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
EXPECTED_STILL_BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FALSE_SUMMARY_FLAGS = [
    "source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled",
    "final_signal_allowed", "no_signal_discord_notified", "ai_api_called", "discord_sent", "mt5_order_sent",
    "live_hook_enabled", "source_recovery_execution_performed", "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


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
    return str(value).strip() == ""


def write_text(path: Path, text: str) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(long_path(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(long_path(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def stop_rows(df: pd.DataFrame) -> int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper() == "STOP").sum())


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(limit).copy()
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def check_row(cid: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": check, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def get_external(summary: dict[str, Any], key: str) -> Any:
    ext = summary.get("external_actions", {})
    return ext.get(key, False) if isinstance(ext, dict) else False


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    return int(sum(1 for k in FALSE_SUMMARY_FLAGS if truthy(summary.get(k, False))) + sum(1 for k in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, k))))


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


def build_input_audit(paths: dict[str, Path], decision_input_path: Path) -> pd.DataFrame:
    rows = []
    for role, path in paths.items():
        rows.append({"role": role, "path": str(path), "required": True, "exists": long_path(path).exists(), "source_of_truth_role": "24G audited artifact", "notes": "24H reads this artifact only; no source recovery/live/AI/external execution."})
    rows.append({"role": "24h_optional_human_decision_input", "path": str(decision_input_path), "required": False, "exists": long_path(decision_input_path).exists(), "source_of_truth_role": "optional human/operator decision input", "notes": "If missing, 24H stays in template/wait mode and does not allow routing."})
    return pd.DataFrame(rows)


def build_24h_template(template24g: dict[str, Any], options: list[str], summary24g: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_name": "GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_INPUT",
        "created_by_step": STEP,
        "audit_only": True,
        "instructions": [
            "Copy this file to gold_v2_24h_human_decision_input.json after filling exactly one selected_decision_value.",
            "selected_decision_value must exactly match one allowed_decision_values entry.",
            "REQUEST_MORE_SOURCE_RECOVERY_AUDIT is not approval.",
            "APPROVE_SOURCE_RECOVERY_EXECUTION does not execute recovery in 24H; later routing/audit is still required.",
            "Do not set any forbidden *_allowed or *_approved flags to true.",
        ],
        "allowed_decision_values": options,
        "selected_decision_value": template24g.get("selected_decision_value", ""),
        "human_operator_notes": template24g.get("human_operator_notes", ""),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24h": False,
        "upstream_24g_status": summary24g.get("status", ""),
        "still_blocked_after_template_creation": EXPECTED_STILL_BLOCKED,
    }


def validate_human_decision(user_decision: dict[str, Any] | None, allowed_values: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if user_decision is None:
        row = {
            "selected_decision_value": "",
            "decision_supplied": False,
            "decision_value_allowed": False,
            "forbidden_flags_true_count": 0,
            "routes_to_later_audit": False,
            "source_recovery_execution_allowed_now": False,
            "source_recovery_approved_by_24h": False,
            "status": "WAITING_FOR_24H_HUMAN_DECISION_INPUT",
            "notes": "No gold_v2_24h_human_decision_input.json supplied.",
        }
        return pd.DataFrame([row]), {"decision_supplied": False, "decision_validated": False, "selected_decision_value": "", "forbidden_flags_true_count": 0}
    selected = str(user_decision.get("selected_decision_value", "")).strip()
    supplied = not blank(selected)
    allowed = selected in allowed_values
    forbidden_keys = [
        "source_recovery_execution_allowed_now", "source_recovery_approved_by_24h", "source_recovery_approved", "source_recovery_executed",
        "source_identity_finalized", "source_identity_recovered", "live_enabled", "final_signal_allowed", "discord_sent", "mt5_order_sent",
        "ai_api_called", "live_hook_enabled", "discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed",
    ]
    true_count = sum(1 for k in forbidden_keys if truthy(user_decision.get(k, False)))
    validated = supplied and allowed and true_count == 0
    row = {
        "selected_decision_value": selected,
        "decision_supplied": supplied,
        "decision_value_allowed": allowed,
        "forbidden_flags_true_count": true_count,
        "routes_to_later_audit": validated,
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24h": False,
        "status": "VALID_24H_DECISION_VALUE_FOR_ROUTING_AUDIT_ONLY" if validated else "INVALID_24H_DECISION_VALUE_OR_FORBIDDEN_FLAGS",
        "notes": "Validated for later routing only; 24H does not execute recovery." if validated else "Decision missing/unknown or forbidden flag true.",
    }
    return pd.DataFrame([row]), {"decision_supplied": supplied, "decision_validated": validated, "selected_decision_value": selected, "forbidden_flags_true_count": true_count}


def build_required_next_gates(ok: bool, decision_supplied: bool, decision_validated: bool) -> pd.DataFrame:
    return pd.DataFrame([
        {"next_step": "WAIT_FOR_24H_HUMAN_DECISION_INPUT", "name": "Wait for human decision input", "purpose": "User/operator fills gold_v2_24h_human_decision_input.json.", "allowed_after_24h_success": bool(ok and not decision_supplied), "required_human_decision_value_later": "ONE_OF_24G_ALLOWED_VALUES", "still_blocked_reason": "" if ok and not decision_supplied else "Decision already supplied/invalid or 24H failed."},
        {"next_step": "24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY", "name": "Route validated decision", "purpose": "Route exact validated decision value to the next audit-only stage. Does not execute recovery.", "allowed_after_24h_success": bool(ok and decision_validated), "required_human_decision_value_later": "VALIDATED_BY_24H", "still_blocked_reason": "" if ok and decision_validated else "No valid human decision value available."},
        {"next_step": "SOURCE_RECOVERY", "name": "Execute source recovery", "purpose": "Would run recovery actions rather than audit-only decision intake.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION", "still_blocked_reason": "24H only intakes a decision and does not execute recovery."},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "name": "Finalize source identity", "purpose": "Would finalize source identity.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION", "still_blocked_reason": "24H does not grant finalization approval."},
        {"next_step": "LIVE", "name": "Enable live evaluator/use", "purpose": "Would create or enable live behavior.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "still_blocked_reason": "GOLD V2 remains audit-only."},
        {"next_step": "FINAL_SIGNAL", "name": "Enable final signal", "purpose": "Would produce final signal behavior.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL", "still_blocked_reason": "Final signal remains blocked."},
        {"next_step": "DISCORD_SEND", "name": "Send Discord notification", "purpose": "Would send externally.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_DISCORD_SEND", "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify."},
        {"next_step": "MT5_ORDER", "name": "Place MT5 order", "purpose": "Would place order.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_MT5_ORDER", "still_blocked_reason": "MT5 remains blocked."},
        {"next_step": "AI_API", "name": "Call AI API", "purpose": "Would call external AI API.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_AI_API_REVIEW", "still_blocked_reason": "AI API remains blocked."},
        {"next_step": "LIVE_HOOK", "name": "Enable live hook", "purpose": "Would enable live hook.", "allowed_after_24h_success": False, "required_human_decision_value_later": "APPROVE_LIVE_HOOK", "still_blocked_reason": "Live hook remains blocked."},
    ])


def build_safety_matrix(summary24g: dict[str, Any], ok: bool, decision_validated: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str) -> None:
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24H writes decision intake artifacts only.")
    add("decision_intake_only", True, True, True, "24H validates a selected decision value only.")
    add("decision_validated_is_not_execution", decision_validated, "may be true", True, "Even validated decisions only route to later audit, never execute in 24H.")
    add("source_recovery_execution_allowed_now", False, False, True, "24H never permits immediate source recovery execution.")
    add("source_recovery_approved_by_24h", False, False, True, "24H never grants approval by itself.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24g.get(key, False)
        add(key, obs, False, falsey(obs), "Forbidden upstream summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24g, key)
        add(key, obs, False, falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("source_recovery_execution_performed", False, False, True, "24H never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24H never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24H never finalizes source identity.")
    add("ai_api_called", False, False, True, "24H never calls AI API.")
    add("discord_sent", False, False, True, "24H never sends Discord.")
    add("mt5_order_sent", False, False, True, "24H never sends MT5 order.")
    add("live_hook_enabled", False, False, True, "24H never enables live hook.")
    add("overall_24h_inputs_safe", ok, True, bool(ok), "Upstream and 24H safety must pass.")
    return pd.DataFrame(rows)


def build_report(summary: dict[str, Any], input_audit: pd.DataFrame, checks: pd.DataFrame, intake: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 24H source recovery execution decision intake audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "- 24H is audit-only.", "- 24H validates one selected human decision value only.", "- 24H does not choose, apply, approve, or execute source recovery.", "- A valid APPROVE_SOURCE_RECOVERY_EXECUTION value still routes only to later audit.", "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.", "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Decision supplied: `{summary['decision_supplied']}`", f"- Decision validated: `{summary['decision_validated']}`", f"- Selected decision value: `{summary['selected_decision_value']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "", "## Human decision intake result", "", md_table(intake), "", "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "", "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`", "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`", "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); source = base / IN24G; out = base / OUT_DIR
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    user_input_path = out / USER_DECISION_FILE
    paths = {role: source / filename for role, filename in REQUIRED_24G_FILES.items()}
    input_audit = build_input_audit(paths, user_input_path); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    required_mask = input_audit["required"].map(truthy)
    inputs_ok = bool(input_audit.loc[required_mask, "exists"].map(truthy).all()) if not input_audit.empty else False
    missing_roles = input_audit.loc[required_mask & ~input_audit["exists"].map(truthy), "role"].astype(str).tolist() if not input_audit.empty else list(REQUIRED_24G_FILES.keys())
    checks = [check_row("24H-C000", "Required 24G artifacts exist", ",".join(missing_roles) if missing_roles else "all present", "all present", inputs_ok)]
    summary24g: dict[str, Any] = {}
    options_df = pd.DataFrame()
    template24g: dict[str, Any] = {}
    allowed_values: list[str] = []
    if inputs_ok:
        summary24g = read_json(paths["24g_summary"])
        input24g = read_csv(paths["24g_input_audit"])
        options_df = read_csv(paths["24g_decision_options"])
        template24g = read_json(paths["24g_human_decision_template"])
        checks24g = read_csv(paths["24g_integrated_checks"])
        gates24g = read_csv(paths["24g_required_next_gates"])
        safety24g = read_csv(paths["24g_safety_matrix"])
        allowed_values = options_df["decision_value"].astype(str).tolist() if "decision_value" in options_df.columns else []
        allowed_after_24g = allowed_next_steps(gates24g, "allowed_after_24g_success")
        forbidden_detail = forbidden_allowed_detail(gates24g, "allowed_after_24g_success")
        missing_required_24g_inputs = int((input24g["required"].map(truthy) & ~input24g["exists"].map(truthy)).sum()) if {"required", "exists"}.issubset(input24g.columns) else 999
        checks.extend([
            check_row("24H-C001", "24G status is ready", summary24g.get("status"), EXPECTED_24G_STATUS, summary24g.get("status") == EXPECTED_24G_STATUS),
            check_row("24H-C002", "24G options only flag true", summary24g.get("source_recovery_execution_decision_options_only"), True, truthy(summary24g.get("source_recovery_execution_decision_options_only", False))),
            check_row("24H-C003", "24G source recovery execution allowed now remains false", summary24g.get("source_recovery_execution_allowed_now"), False, falsey(summary24g.get("source_recovery_execution_allowed_now", False))),
            check_row("24H-C004", "24G source recovery approved by 24G remains false", summary24g.get("source_recovery_approved_by_24g"), False, falsey(summary24g.get("source_recovery_approved_by_24g", False))),
            check_row("24H-C005", "24G decision options rows", len(options_df), 4, len(options_df) == 4),
            check_row("24H-C006", "24G allowed decision values non-empty", allowed_values, "4 exact values", len(allowed_values) == 4),
            check_row("24H-C007", "24G integrated/safety STOP rows zero", stop_rows(checks24g) + stop_rows(safety24g), 0, stop_rows(checks24g) + stop_rows(safety24g) == 0),
            check_row("24H-C008", "24G required inputs complete", missing_required_24g_inputs, 0, missing_required_24g_inputs == 0),
            check_row("24H-C009", "24G allowed next only 24H", allowed_after_24g, ["24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY"], allowed_after_24g == ["24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY"]),
            check_row("24H-C010", "24G forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24H-C011", "24G forbidden summary/external flags remain false", count_true_forbidden_summary_flags(summary24g), 0, count_true_forbidden_summary_flags(summary24g) == 0),
        ])
    template = build_24h_template(template24g, allowed_values, summary24g)
    write_json(out / TEMPLATE_FILE, template)
    user_decision = read_json(user_input_path) if long_path(user_input_path).exists() else None
    intake_df, decision_stats = validate_human_decision(user_decision, allowed_values)
    checks_df = pd.DataFrame(checks)
    upstream_ok = bool(inputs_ok and stop_rows(checks_df) == 0)
    safety_df = build_safety_matrix(summary24g, upstream_ok, bool(decision_stats.get("decision_validated")))
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = bool(upstream_ok and total_stop_rows == 0)
    decision_supplied = bool(decision_stats.get("decision_supplied", False))
    decision_validated = bool(decision_stats.get("decision_validated", False))
    if not ok:
        status = STOP_STATUS
    elif not decision_supplied:
        status = WAIT_STATUS
    elif decision_validated:
        status = VALID_STATUS
    else:
        status = INVALID_STATUS
    gates_df = build_required_next_gates(ok, decision_supplied, decision_validated)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_execution_decision_intake_only": True,
        "source_of_truth": "24G audited artifacts under FX_OUTPUTS/" + IN24G,
        "upstream_status": summary24g.get("status", "UNKNOWN_MISSING_24G_SUMMARY"),
        "required_24g_inputs_ok": inputs_ok,
        "missing_inputs": missing_roles,
        "allowed_decision_values": allowed_values,
        "decision_supplied": decision_supplied,
        "decision_validated": decision_validated,
        "selected_decision_value": decision_stats.get("selected_decision_value", ""),
        "forbidden_flags_true_count": int(decision_stats.get("forbidden_flags_true_count", 0)),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24h": False,
        "source_recovery_approved": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "no_signal_discord_notified": False,
        "old_gold_disc8_quarantined": True,
        "ai_api_called": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "live_hook_enabled": False,
        "source_recovery_execution_performed": False,
        "source_recovery_approval_granted": False,
        "source_identity_finalization_performed": False,
        "still_blocked_after_24h": EXPECTED_STILL_BLOCKED,
        "total_stop_rows": int(total_stop_rows),
        "required_next_allowed": allowed_next_steps(gates_df, "allowed_after_24h_success"),
        "next_recommended_step": "24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY" if ok and decision_validated else ("WAIT_FOR_24H_HUMAN_DECISION_INPUT" if ok and not decision_supplied else "REVIEW_INVALID_24H_DECISION_INPUT" if ok else "STOP_REVIEW_24H_INPUTS_AND_24G_OUTPUTS"),
        "do_not_execute_source_recovery_in_24h": True,
        "outputs": {
            "input_audit": str(out / INPUT_AUDIT_FILE),
            "human_decision_template": str(out / TEMPLATE_FILE),
            "human_decision_intake_result": str(out / INTAKE_RESULT_FILE),
            "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
            "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
            "safety_matrix": str(out / SAFETY_MATRIX_FILE),
            "summary": str(out / SUMMARY_FILE),
            "report": str(out / REPORT_FILE),
        },
    }
    write_csv(out / INTAKE_RESULT_FILE, intake_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(summary, input_audit, checks_df, intake_df, gates_df, safety_df))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
