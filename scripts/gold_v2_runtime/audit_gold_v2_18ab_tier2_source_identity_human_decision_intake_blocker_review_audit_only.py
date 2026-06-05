#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only"
IN18AA = "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only"
IN18V = "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only"
IN18X = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
REFS = [
    "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only",
    "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only",
    "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only",
    "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only",
    "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only",
    "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only",
    "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only",
    "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only",
    "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only",
    "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only",
    "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only",
    "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only",
    "gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only",
    "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only",
    "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
    "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only",
    "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only",
]
REPORT = "GOLD_V2_18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AA = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
REQUIRED_BLOCKERS = {"SOURCE_RECOVERY", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_IDENTITY_RECOVERED", "OHLC_REPLAY_RECONSTRUCTION", "LIVE_EVALUATOR", "FINAL_SIGNAL", "DISCORD_SEND", "NO_SIGNAL_DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = ["source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


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


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path)
    lp(path).write_text(text, encoding="utf-8")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    wtxt(path, json.dumps(obj, ensure_ascii=False, indent=2))


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    return int((df["status"].astype(str) == "STOP").sum()) if "status" in df.columns else 999


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def mdtable(df: pd.DataFrame, limit: int = 100) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][col].map(truthy).sum())
    return 999


def summary_forbidden_true(summary: dict[str, Any]) -> int:
    n = sum(int(bool(summary.get(k, False))) for k in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18AC", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY", "Package 18X-18AB intake readiness evidence only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AB.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AB.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18ab_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["blocker_review_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18ac_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AB-S001", "required inputs missing", "STOP"], ["18AB-S002", "18AA status not passed", "STOP"],
        ["18AB-S003", "decision collected or approval already made", "STOP"], ["18AB-S004", "upstream STOP rows present", "STOP"],
        ["18AB-S005", "required blocker missing or not blocked", "STOP"], ["18AB-S006", "decision value/template unsafe", "STOP"],
        ["18AB-S007", "forbidden gate allowed", "STOP"], ["18AB-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18aa, p18v, p18x = fx()/IN18AA, fx()/IN18V, fx()/IN18X
    inputs = {
        "summary_18aa": p18aa / "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json",
        "checks_18aa": p18aa / "gold_v2_18aa_reconciliation_checks.csv",
        "gates_18aa": p18aa / "gold_v2_18aa_required_next_gates.csv",
        "safety_18aa": p18aa / "gold_v2_18aa_safety_matrix.csv",
        "report_18aa": p18aa / "GOLD_V2_18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "remaining_blockers_18v": p18v / "gold_v2_18v_remaining_blockers.csv",
        "manual_summary_18v": p18v / "gold_v2_18v_manual_decision_summary.csv",
        "values_18x": p18x / "gold_v2_18x_allowed_decision_values.csv",
        "template_18x": p18x / "gold_v2_18x_human_decision_template.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18ab_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18AB-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18ab_blocker_review_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18ab_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18AB_STOP_MISSING_INPUTS", "audit_only": True, "blocker_review_passed": False, "next_recommended_step": "STOP_REVIEW_18AB_INPUTS"}
        wjson(out / "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18AB blocker review audit-only report\n\nStatus: `18AB_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18aa = rjson(inputs["summary_18aa"])
    checks18aa, gates18aa, safe18aa = rcsv(inputs["checks_18aa"]), rcsv(inputs["gates_18aa"]), rcsv(inputs["safety_18aa"])
    blockers = rcsv(inputs["remaining_blockers_18v"])
    manual_summary = rcsv(inputs["manual_summary_18v"])
    values = rcsv(inputs["values_18x"])
    template = rjson(inputs["template_18x"])
    action_col = "action" if "action" in blockers.columns else "blocker_category" if "blocker_category" in blockers.columns else None
    observed = set(blockers[action_col].astype(str)) if action_col else set()
    missing = sorted(REQUIRED_BLOCKERS - observed)
    status_blocked = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    still_blocking = int((~blockers.get("still_blocking_after_18v", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    script_can_clear = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    blockers_review = blockers.copy()
    blockers_review["reviewed_by_18ab"] = True
    blockers_review["must_remain_blocked_before_human_intake"] = True
    wcsv(blockers_review, out / "gold_v2_18ab_blockers_still_in_force.csv")
    value_executes = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    template_unsafe = int(any(bool(template.get(k, False)) for k in ["source_recovery_executed", "source_identity_finalized", "live_enabled"]))
    template_unset = template.get("decision_value") == "UNSET" and template.get("script_validation_status") == "TEMPLATE_ONLY_NOT_A_DECISION"
    upstream_stop = stop_count(checks18aa) + stop_count(safe18aa)
    forbidden_gates = forbidden_gate_count(gates18aa, "allowed_after_18aa_success")
    summaries = []
    for name in REFS:
        path = fx()/name
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    checks = pd.DataFrame([
        ck("18AB-C001", "18AA status", s18aa.get("status"), EXPECTED_18AA, s18aa.get("status") == EXPECTED_18AA),
        ck("18AB-C002", "18AA intake_reconciliation_passed", s18aa.get("intake_reconciliation_passed"), True, bool(s18aa.get("intake_reconciliation_passed", False))),
        ck("18AB-C003", "18AA total_stop_rows", s18aa.get("total_stop_rows"), 0, s18aa.get("total_stop_rows") == 0),
        ck("18AB-C004", "18AA decision_collected", s18aa.get("decision_collected"), False, s18aa.get("decision_collected") is False),
        ck("18AB-C005", "18AA decision_made", s18aa.get("decision_made"), False, s18aa.get("decision_made") is False),
        ck("18AB-C006", "18AA approval_granted", s18aa.get("approval_granted"), False, s18aa.get("approval_granted") is False),
        ck("18AB-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18AB-C008", "missing required blockers", len(missing), 0, len(missing) == 0),
        ck("18AB-C009", "blocker status not BLOCKED", status_blocked, 0, status_blocked == 0),
        ck("18AB-C010", "blockers not still blocking", still_blocking, 0, still_blocking == 0),
        ck("18AB-C011", "script_can_clear true rows", script_can_clear, 0, script_can_clear == 0),
        ck("18AB-C012", "decision values execute no action", value_executes, 0, value_executes == 0),
        ck("18AB-C013", "template remains unset", template_unset, True, template_unset),
        ck("18AB-C014", "template restricted actions false", template_unsafe, 0, template_unsafe == 0),
        ck("18AB-C015", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18AB-C016", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AB_STOP_REVIEW_INTAKE_BLOCKER_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18ab_blocker_review_checks.csv", checks),
        ("gold_v2_18ab_required_next_gates.csv", gates),
        ("gold_v2_18ab_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18ab_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "blocker_review_passed": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18aa_status": s18aa.get("status"), "remaining_blockers": int(len(blockers)), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY" if success else "STOP_REVIEW_18AB_OUTPUTS",
    }
    wjson(out / "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_summary.json", summary)
    report = [
        "# GOLD V2 18AB TIER2 source identity human decision intake blocker review audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18AB reviewed intake blockers only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Blocker review checks", mdtable(checks), "", "## Blockers still in force", mdtable(blockers_review), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
