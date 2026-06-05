#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY"
OUT_DIR = "gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_only"
IN19E = "gold_v2_19e_tier2_source_identity_human_decision_intake_actual_decision_plan_blocker_review_audit_only"
REPORT = "GOLD_V2_19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19E = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
EVIDENCE_DIRS = {
    "19A": "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only",
    "19B": "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only",
    "19C": "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_only",
    "19D": "gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_audit_only",
    "19E": IN19E,
}
SUCCESS_KEYS = [
    "decision_planning_ready", "plan_load_smoke_passed", "plan_content_audit_passed",
    "plan_reconciliation_passed", "blocker_review_passed",
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
        ["19G", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY", "Prepare final audit-only handoff note for later actual decision intake workflow.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19F.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19F.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19f_success"])


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
        ["next_gate_19g_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19F-S001", "required inputs missing", "STOP"],
        ["19F-S002", "19E status not passed", "STOP"],
        ["19F-S003", "decision collected or approval already made", "STOP"],
        ["19F-S004", "upstream STOP rows present", "STOP"],
        ["19F-S005", "evidence summary missing or failed", "STOP"],
        ["19F-S006", "blockers not still in force", "STOP"],
        ["19F-S007", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19e = base / IN19E
    inputs = {
        "summary_19e": p19e / "gold_v2_19e_tier2_source_identity_human_decision_intake_actual_decision_plan_blocker_review_summary.json",
        "checks_19e": p19e / "gold_v2_19e_blocker_review_checks.csv",
        "blockers_19e": p19e / "gold_v2_19e_blockers_still_in_force.csv",
        "gates_19e": p19e / "gold_v2_19e_required_next_gates.csv",
        "safety_19e": p19e / "gold_v2_19e_safety_matrix.csv",
        "report_19e": p19e / "GOLD_V2_19E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19f_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19F-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19f_final_checks.csv", checks)
        write_csv(out / "gold_v2_19f_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19F_STOP_MISSING_INPUTS", "audit_only": True, "final_audit_ready": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19F_INPUTS"}
        write_json(out / "gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19F final audit-only report\n\nStatus: `19F_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19e = read_json(inputs["summary_19e"])
    checks19e = read_csv(inputs["checks_19e"])
    blockers = read_csv(inputs["blockers_19e"])
    gates19e = read_csv(inputs["gates_19e"])
    safety19e = read_csv(inputs["safety_19e"])

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
    evidence = pd.DataFrame(evidence_rows, columns=["step", "summary_path", "exists", "summary_status", "success_flag_and_zero_stop", "status"])
    write_csv(out / "gold_v2_19f_evidence_status.csv", evidence)

    status_bad = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    clear_bad = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    force_bad = int((~blockers.get("still_in_force_after_19e", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    blocker_final = pd.DataFrame([
        check_row("19F-B001", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        check_row("19F-B002", "blocker status not BLOCKED", status_bad, 0, status_bad == 0),
        check_row("19F-B003", "script_can_clear true rows", clear_bad, 0, clear_bad == 0),
        check_row("19F-B004", "not still in force rows", force_bad, 0, force_bad == 0),
    ])
    write_csv(out / "gold_v2_19f_blocker_final_status.csv", blocker_final)

    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in summaries + [s19e])
    upstream_stop = stop_count(checks19e) + stop_count(safety19e)
    forbidden_gates = forbidden_gate_count(gates19e, "allowed_after_19e_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in summaries + [s19e])
    checks = pd.DataFrame([
        check_row("19F-C001", "19E status", s19e.get("status"), EXPECTED_19E, s19e.get("status") == EXPECTED_19E),
        check_row("19F-C002", "19E blocker_review_passed", s19e.get("blocker_review_passed"), True, bool(s19e.get("blocker_review_passed", False))),
        check_row("19F-C003", "19E total_stop_rows", s19e.get("total_stop_rows"), 0, s19e.get("total_stop_rows") == 0),
        check_row("19F-C004", "19A-19E no decision/approval", no_decision, True, no_decision),
        check_row("19F-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19F-C006", "evidence summary STOP rows", stop_count(evidence), 0, stop_count(evidence) == 0),
        check_row("19F-C007", "blocker final STOP rows", stop_count(blocker_final), 0, stop_count(blocker_final) == 0),
        check_row("19F-C008", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("19F-C009", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19F_STOP_REVIEW_FINAL_AUDIT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19f_final_checks.csv", checks)
    write_csv(out / "gold_v2_19f_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19f_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19f_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "final_audit_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19e_status": s19e.get("status"),
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
        "next_recommended_step": "19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY" if success else "STOP_REVIEW_19F_OUTPUTS",
    }
    write_json(out / "gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_summary.json", summary)
    report = [
        "# GOLD V2 19F TIER2 source identity human decision intake actual decision plan final audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19F prepared a final audit-only summary for the actual human decision intake plan only.",
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
