#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY"
OUT_DIR = "gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only"
IN19H = "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only"
IN19I = "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only"
IN19J = "gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_only"
IN19K = "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only"
IN19L = "gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_audit_only"
REPORT = "GOLD_V2_19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19L = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_TEMPLATE_FLAGS = [
    "approval_granted",
    "source_recovery_requested",
    "source_recovery_allowed",
    "source_identity_finalization_allowed",
    "live_or_final_implementation_allowed",
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
    "no_signal_discord_notified",
    "script_executes_action",
]
UNSET_FIELDS = [
    "decision_id",
    "decision_timestamp_utc",
    "decision_value",
    "human_reviewer",
    "explicit_phrase",
    "notes",
]
EVIDENCE_DIRS = {
    "19H": IN19H,
    "19I": IN19I,
    "19J": IN19J,
    "19K": IN19K,
    "19L": IN19L,
}
SUCCESS_KEYS = [
    "template_prepared",
    "template_load_smoke_passed",
    "template_content_audit_passed",
    "template_reconciliation_passed",
    "blocker_review_passed",
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
        ["19N", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY", "Prepare final audit-only handoff for the still-unset actual decision template.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19M.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19M.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19m_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["template_final_audit_only", True, True, "PASS"],
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
        ["next_gate_19n_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19M-S001", "required inputs missing", "STOP"],
        ["19M-S002", "19L status not passed", "STOP"],
        ["19M-S003", "decision collected or approval already made", "STOP"],
        ["19M-S004", "upstream STOP rows present", "STOP"],
        ["19M-S005", "evidence summary missing or failed", "STOP"],
        ["19M-S006", "template no longer still-unset", "STOP"],
        ["19M-S007", "blockers not still in force after 19L", "STOP"],
        ["19M-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19h, p19l = base / IN19H, base / IN19L
    inputs = {
        "summary_19l": p19l / "gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_summary.json",
        "checks_19l": p19l / "gold_v2_19l_blocker_review_checks.csv",
        "blockers_19l": p19l / "gold_v2_19l_blockers_still_in_force.csv",
        "gates_19l": p19l / "gold_v2_19l_required_next_gates.csv",
        "safety_19l": p19l / "gold_v2_19l_safety_matrix.csv",
        "report_19l": p19l / "GOLD_V2_19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md",
        "template_19h": p19h / "gold_v2_19h_actual_decision_template.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19m_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_19m_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19M-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        evidence = pd.DataFrame(columns=["step", "summary_path", "exists", "summary_status", "success_flag_and_zero_stop", "status"])
        blocker_final = pd.DataFrame([check_row("19M-B000", "blocker inputs available", False, True, False)])
        write_csv(out / "gold_v2_19m_final_checks.csv", checks)
        write_csv(out / "gold_v2_19m_evidence_status.csv", evidence)
        write_csv(out / "gold_v2_19m_blocker_final_status.csv", blocker_final)
        write_csv(out / "gold_v2_19m_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_19m_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "19M_STOP_MISSING_INPUTS",
            "audit_only": True,
            "final_audit_ready": False,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "total_stop_rows": 1,
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
            "next_recommended_step": "STOP_REVIEW_19M_INPUTS",
        }
        write_json(out / "gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19M template final audit-only report\n\nStatus: `19M_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19l = read_json(inputs["summary_19l"])
    checks19l = read_csv(inputs["checks_19l"])
    blockers = read_csv(inputs["blockers_19l"])
    gates19l = read_csv(inputs["gates_19l"])
    safety19l = read_csv(inputs["safety_19l"])
    template = read_json(inputs["template_19h"])

    evidence_rows = []
    summaries: list[dict[str, Any]] = []
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
    evidence = pd.DataFrame(evidence_rows, columns=["step", "summary_path", "exists", "summary_status", "success_flag_and_zero_stop", "status"])
    write_csv(out / "gold_v2_19m_evidence_status.csv", evidence)

    status_bad = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    clear_bad = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    force_bad = int((~blockers.get("still_in_force_after_19l", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    blocker_final = pd.DataFrame([
        check_row("19M-B001", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        check_row("19M-B002", "blocker status not BLOCKED", status_bad, 0, status_bad == 0),
        check_row("19M-B003", "script_can_clear true rows", clear_bad, 0, clear_bad == 0),
        check_row("19M-B004", "not still in force after 19L rows", force_bad, 0, force_bad == 0),
    ])
    write_csv(out / "gold_v2_19m_blocker_final_status.csv", blocker_final)

    unset_bad = sum(int(template.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_template_true = sum(int(bool(template.get(k, False))) for k in RESTRICTED_TEMPLATE_FLAGS)
    evidence_ack = template.get("evidence_acknowledged")
    template_status = template.get("template_status")
    decision_value = template.get("decision_value")

    no_decision = all(
        s.get("decision_collected", False) is False
        and s.get("decision_made") is False
        and s.get("approval_granted") is False
        for s in summaries + [s19l]
    )
    upstream_stop = stop_count(checks19l) + stop_count(safety19l)
    forbidden_gates = forbidden_gate_count(gates19l, "allowed_after_19l_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in summaries + [s19l])

    checks = pd.DataFrame([
        check_row("19M-C001", "19L status", s19l.get("status"), EXPECTED_19L, s19l.get("status") == EXPECTED_19L),
        check_row("19M-C002", "19L blocker_review_passed", s19l.get("blocker_review_passed"), True, bool(s19l.get("blocker_review_passed", False))),
        check_row("19M-C003", "19L total_stop_rows", s19l.get("total_stop_rows"), 0, s19l.get("total_stop_rows") == 0),
        check_row("19M-C004", "19H-19L no decision/approval", no_decision, True, no_decision),
        check_row("19M-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19M-C006", "evidence summary STOP rows", stop_count(evidence), 0, stop_count(evidence) == 0),
        check_row("19M-C007", "blocker final STOP rows", stop_count(blocker_final), 0, stop_count(blocker_final) == 0),
        check_row("19M-C008", "template_status", template_status, "TEMPLATE_ONLY_NOT_A_DECISION", template_status == "TEMPLATE_ONLY_NOT_A_DECISION"),
        check_row("19M-C009", "template decision_value", decision_value, "UNSET", decision_value == "UNSET"),
        check_row("19M-C010", "template unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check_row("19M-C011", "template evidence_acknowledged", evidence_ack, False, evidence_ack is False),
        check_row("19M-C012", "restricted template true flags", restricted_template_true, 0, restricted_template_true == 0),
        check_row("19M-C013", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("19M-C014", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19M_STOP_REVIEW_TEMPLATE_FINAL_AUDIT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19m_final_checks.csv", checks)
    write_csv(out / "gold_v2_19m_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19m_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "final_audit_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "template_status": template_status,
        "decision_value": decision_value,
        "upstream_19l_status": s19l.get("status"),
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
        "next_recommended_step": "19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY" if success else "STOP_REVIEW_19M_OUTPUTS",
    }
    write_json(out / "gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_summary.json", summary)
    report = [
        "# GOLD V2 19M TIER2 source identity human decision intake actual decision template final audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19M prepared a final audit-only summary for the still-unset actual human decision template only.",
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
