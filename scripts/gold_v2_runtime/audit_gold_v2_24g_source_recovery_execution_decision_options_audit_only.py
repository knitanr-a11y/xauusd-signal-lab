#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY"
OUT_DIR = "gold_v2_24g_source_recovery_execution_decision_options_audit_only"
IN24F = "gold_v2_24f_source_recovery_artifact_list_review_audit_only"
EXPECTED_24F_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24G_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_INPUTS_OR_SAFETY"

REPORT_FILE = "GOLD_V2_24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24g_source_recovery_execution_decision_options_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24g_input_audit.csv"
DECISION_OPTIONS_FILE = "gold_v2_24g_decision_options.csv"
HUMAN_DECISION_TEMPLATE_FILE = "gold_v2_24g_human_decision_input_template.json"
INTEGRATED_CHECKS_FILE = "gold_v2_24g_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24g_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24g_safety_matrix.csv"

REQUIRED_24F_FILES = {
    "24f_report": "GOLD_V2_24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY_REPORT.md",
    "24f_summary": "gold_v2_24f_source_recovery_artifact_list_review_summary.json",
    "24f_input_audit": "gold_v2_24f_input_audit.csv",
    "24f_artifact_reference_review": "gold_v2_24f_artifact_reference_review.csv",
    "24f_content_review_checks": "gold_v2_24f_artifact_content_review_checks.csv",
    "24f_integrated_checks": "gold_v2_24f_integrated_checks.csv",
    "24f_required_next_gates": "gold_v2_24f_required_next_gates.csv",
    "24f_safety_matrix": "gold_v2_24f_safety_matrix.csv",
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


def build_input_audit(paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in paths.items():
        rows.append({"role": role, "path": str(path), "required": True, "exists": long_path(path).exists(), "source_of_truth_role": "24F audited artifact", "notes": "24G reads this artifact only; no source recovery/live/AI/external execution."})
    return pd.DataFrame(rows)


def build_decision_options() -> pd.DataFrame:
    rows = [
        {
            "decision_value": "KEEP_SOURCE_RECOVERY_BLOCKED",
            "decision_label": "Keep source recovery blocked",
            "meaning": "Continue audit-only workflow and do not execute source recovery.",
            "execution_allowed_in_24g": False,
            "requires_later_routing": False,
            "source_recovery_approved_by_this_row": False,
            "notes": "Default safest option. No recovery execution is permitted.",
        },
        {
            "decision_value": "REQUEST_MORE_SOURCE_RECOVERY_AUDIT",
            "decision_label": "Request more source recovery audit",
            "meaning": "Ask for more evidence/review before any source recovery execution decision.",
            "execution_allowed_in_24g": False,
            "requires_later_routing": False,
            "source_recovery_approved_by_this_row": False,
            "notes": "REQUEST_MORE is not approval.",
        },
        {
            "decision_value": "REJECT_SOURCE_RECOVERY_EXECUTION",
            "decision_label": "Reject source recovery execution",
            "meaning": "Explicitly reject source recovery execution and keep the system audit-only/blocked.",
            "execution_allowed_in_24g": False,
            "requires_later_routing": False,
            "source_recovery_approved_by_this_row": False,
            "notes": "No recovery execution is permitted.",
        },
        {
            "decision_value": "APPROVE_SOURCE_RECOVERY_EXECUTION",
            "decision_label": "Approve source recovery execution candidate value",
            "meaning": "Exact candidate value that a human may later place into 24H intake. 24G does not apply it.",
            "execution_allowed_in_24g": False,
            "requires_later_routing": True,
            "source_recovery_approved_by_this_row": False,
            "notes": "Not approval inside 24G. Requires later 24H intake and later routing/execution audit before anything can run.",
        },
    ]
    return pd.DataFrame(rows)


def build_human_decision_template(options: pd.DataFrame, summary24f: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_name": "GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_TEMPLATE",
        "created_by_step": STEP,
        "audit_only": True,
        "instructions": [
            "Fill exactly one decision_value from allowed_decision_values.",
            "Do not edit allowed_decision_values.",
            "REQUEST_MORE_SOURCE_RECOVERY_AUDIT is not approval.",
            "APPROVE_SOURCE_RECOVERY_EXECUTION is not applied by 24G; it must be independently supplied in 24H and routed later.",
            "No source recovery execution is allowed by this template.",
        ],
        "allowed_decision_values": options["decision_value"].astype(str).tolist(),
        "selected_decision_value": "",
        "human_operator_notes": "",
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24g": False,
        "upstream_24f_status": summary24f.get("status", ""),
        "still_blocked_after_template_creation": EXPECTED_STILL_BLOCKED,
    }


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    return pd.DataFrame([
        {"next_step": "24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY", "name": "Intake human decision", "purpose": "Read and validate exact human decision value. Does not execute recovery.", "allowed_after_24g_success": bool(ok), "required_human_decision_value_later": "ONE_OF_24G_ALLOWED_VALUES", "still_blocked_reason": "" if ok else "24G did not pass."},
        {"next_step": "SOURCE_RECOVERY", "name": "Execute source recovery", "purpose": "Would run recovery actions rather than audit-only decision intake.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION", "still_blocked_reason": "24G only prepares options and does not grant recovery approval."},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "name": "Finalize source identity", "purpose": "Would finalize source identity.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION", "still_blocked_reason": "24G does not grant finalization approval."},
        {"next_step": "LIVE", "name": "Enable live evaluator/use", "purpose": "Would create or enable live behavior.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "still_blocked_reason": "GOLD V2 remains audit-only."},
        {"next_step": "FINAL_SIGNAL", "name": "Enable final signal", "purpose": "Would produce final signal behavior.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL", "still_blocked_reason": "Final signal remains blocked."},
        {"next_step": "DISCORD_SEND", "name": "Send Discord notification", "purpose": "Would send externally.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_DISCORD_SEND", "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify."},
        {"next_step": "MT5_ORDER", "name": "Place MT5 order", "purpose": "Would place order.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_MT5_ORDER", "still_blocked_reason": "MT5 remains blocked."},
        {"next_step": "AI_API", "name": "Call AI API", "purpose": "Would call external AI API.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_AI_API_REVIEW", "still_blocked_reason": "AI API remains blocked."},
        {"next_step": "LIVE_HOOK", "name": "Enable live hook", "purpose": "Would enable live hook.", "allowed_after_24g_success": False, "required_human_decision_value_later": "APPROVE_LIVE_HOOK", "still_blocked_reason": "Live hook remains blocked."},
    ])


def build_safety_matrix(summary24f: dict[str, Any], ok: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str) -> None:
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24G writes decision option artifacts only.")
    add("decision_options_only", True, True, True, "24G does not choose or apply any decision value.")
    add("source_recovery_execution_allowed_now", False, False, True, "24G never permits immediate source recovery execution.")
    add("source_recovery_approved_by_24g", False, False, True, "24G never grants approval.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24f.get(key, False)
        add(key, obs, False, falsey(obs), "Forbidden upstream summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24f, key)
        add(key, obs, False, falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("source_recovery_execution_performed", False, False, True, "24G never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24G never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24G never finalizes source identity.")
    add("ai_api_called", False, False, True, "24G never calls AI API.")
    add("discord_sent", False, False, True, "24G never sends Discord.")
    add("mt5_order_sent", False, False, True, "24G never sends MT5 order.")
    add("live_hook_enabled", False, False, True, "24G never enables live hook.")
    add("overall_24g_inputs_safe", ok, True, bool(ok), "Upstream and 24G safety must pass.")
    return pd.DataFrame(rows)


def build_report(summary: dict[str, Any], input_audit: pd.DataFrame, checks: pd.DataFrame, options: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 24G source recovery execution decision options audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "- 24G is audit-only.", "- 24G prepares decision options only.", "- 24G does not choose, apply, approve, or execute any source recovery decision.", "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.", "- Old GOLD/DISC8 remain quarantined.", "- REQUEST_MORE_SOURCE_RECOVERY_AUDIT is not approval.", "- APPROVE_SOURCE_RECOVERY_EXECUTION in the options matrix is not applied by 24G.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Decision options written: `{summary['decision_options_rows']}`", f"- Human decision template written: `{summary['human_decision_template_written']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "", "## Decision options", "", md_table(options), "", "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "", "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`", "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`", "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); source = base / IN24F; out = base / OUT_DIR
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    paths = {role: source / filename for role, filename in REQUIRED_24F_FILES.items()}
    input_audit = build_input_audit(paths); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].map(truthy).all()) if not input_audit.empty else False
    missing_roles = input_audit.loc[~input_audit["exists"].map(truthy), "role"].astype(str).tolist() if not input_audit.empty else list(REQUIRED_24F_FILES.keys())
    checks = [check_row("24G-C000", "Required 24F artifacts exist", ",".join(missing_roles) if missing_roles else "all present", "all present", inputs_ok)]
    summary24f: dict[str, Any] = {}
    if inputs_ok:
        summary24f = read_json(paths["24f_summary"])
        input24f = read_csv(paths["24f_input_audit"])
        ref24f = read_csv(paths["24f_artifact_reference_review"])
        content24f = read_csv(paths["24f_content_review_checks"])
        checks24f = read_csv(paths["24f_integrated_checks"])
        gates24f = read_csv(paths["24f_required_next_gates"])
        safety24f = read_csv(paths["24f_safety_matrix"])
        allowed_after_24f = allowed_next_steps(gates24f, "allowed_after_24f_success")
        forbidden_detail = forbidden_allowed_detail(gates24f, "allowed_after_24f_success")
        missing_required_24f_inputs = int((input24f["required"].map(truthy) & ~input24f["exists"].map(truthy)).sum()) if {"required", "exists"}.issubset(input24f.columns) else 999
        reviewable_rows = int(ref24f["artifact_review_status"].astype(str).str.startswith("REVIEWABLE").sum()) if "artifact_review_status" in ref24f.columns else 0
        checks.extend([
            check_row("24G-C001", "24F status is passed", summary24f.get("status"), EXPECTED_24F_STATUS, summary24f.get("status") == EXPECTED_24F_STATUS),
            check_row("24G-C002", "24F artifact review passed", summary24f.get("artifact_review_passed"), True, truthy(summary24f.get("artifact_review_passed", False))),
            check_row("24G-C003", "24F reviewable artifact rows", reviewable_rows, 3, reviewable_rows == 3),
            check_row("24G-C004", "24F content review STOP rows", stop_rows(content24f), 0, stop_rows(content24f) == 0),
            check_row("24G-C005", "24F integrated/safety STOP rows zero", stop_rows(checks24f) + stop_rows(safety24f), 0, stop_rows(checks24f) + stop_rows(safety24f) == 0),
            check_row("24G-C006", "24F required inputs complete", missing_required_24f_inputs, 0, missing_required_24f_inputs == 0),
            check_row("24G-C007", "24F allowed next only 24G", allowed_after_24f, ["24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY"], allowed_after_24f == ["24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY"]),
            check_row("24G-C008", "24F forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24G-C009", "24F forbidden summary/external flags remain false", count_true_forbidden_summary_flags(summary24f), 0, count_true_forbidden_summary_flags(summary24f) == 0),
        ])
    checks_df = pd.DataFrame(checks)
    upstream_ok = bool(inputs_ok and stop_rows(checks_df) == 0)
    options_df = build_decision_options()
    template = build_human_decision_template(options_df, summary24f)
    safety_df = build_safety_matrix(summary24f, upstream_ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = bool(upstream_ok and total_stop_rows == 0)
    status = PASS_STATUS if ok else STOP_STATUS
    gates_df = build_required_next_gates(ok)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_execution_decision_options_only": True,
        "source_of_truth": "24F audited artifacts under FX_OUTPUTS/" + IN24F,
        "upstream_status": summary24f.get("status", "UNKNOWN_MISSING_24F_SUMMARY"),
        "required_24f_inputs_ok": inputs_ok,
        "missing_inputs": missing_roles,
        "decision_options_rows": int(len(options_df)),
        "allowed_decision_values_for_24h": options_df["decision_value"].astype(str).tolist(),
        "human_decision_template_written": True,
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24g": False,
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
        "still_blocked_after_24g": EXPECTED_STILL_BLOCKED,
        "total_stop_rows": int(total_stop_rows),
        "required_next_allowed": allowed_next_steps(gates_df, "allowed_after_24g_success"),
        "next_recommended_step": "24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY" if ok else "STOP_REVIEW_24G_INPUTS_AND_24F_OUTPUTS",
        "do_not_execute_source_recovery_in_24g": True,
        "outputs": {
            "input_audit": str(out / INPUT_AUDIT_FILE),
            "decision_options": str(out / DECISION_OPTIONS_FILE),
            "human_decision_template": str(out / HUMAN_DECISION_TEMPLATE_FILE),
            "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
            "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
            "safety_matrix": str(out / SAFETY_MATRIX_FILE),
            "summary": str(out / SUMMARY_FILE),
            "report": str(out / REPORT_FILE),
        },
    }
    write_csv(out / DECISION_OPTIONS_FILE, options_df)
    write_json(out / HUMAN_DECISION_TEMPLATE_FILE, template)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(summary, input_audit, checks_df, options_df, gates_df, safety_df))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
