#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only"
IN18X = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
IN18Y = "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only"
IN18Z = "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only"
IN18AA = "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only"
IN18AB = "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only"
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
    IN18X, IN18Y, IN18Z, IN18AA, IN18AB,
]
REPORT = "GOLD_V2_18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AB = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
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
        ["18AD", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke 18AC readiness package only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AC.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AC.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18ac_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["readiness_package_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18ad_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AC-S001", "required inputs missing", "STOP"], ["18AC-S002", "18AB status not passed", "STOP"],
        ["18AC-S003", "decision collected or approval already made", "STOP"], ["18AC-S004", "upstream STOP rows present", "STOP"],
        ["18AC-S005", "package evidence incomplete", "STOP"], ["18AC-S006", "blocker package unsafe", "STOP"],
        ["18AC-S007", "forbidden gate allowed", "STOP"], ["18AC-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p = {"18X": fx()/IN18X, "18Y": fx()/IN18Y, "18Z": fx()/IN18Z, "18AA": fx()/IN18AA, "18AB": fx()/IN18AB}
    inputs = {
        "summary_18ab": p["18AB"] / "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_summary.json",
        "checks_18ab": p["18AB"] / "gold_v2_18ab_blocker_review_checks.csv",
        "blockers_18ab": p["18AB"] / "gold_v2_18ab_blockers_still_in_force.csv",
        "gates_18ab": p["18AB"] / "gold_v2_18ab_required_next_gates.csv",
        "safety_18ab": p["18AB"] / "gold_v2_18ab_safety_matrix.csv",
        "report_18ab": p["18AB"] / "GOLD_V2_18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md",
        "summary_18aa": p["18AA"] / "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json",
        "summary_18z": p["18Z"] / "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json",
        "summary_18y": p["18Y"] / "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json",
        "summary_18x": p["18X"] / "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json",
        "template_18x": p["18X"] / "gold_v2_18x_human_decision_template.json",
        "fields_18x": p["18X"] / "gold_v2_18x_required_intake_fields.csv",
        "values_18x": p["18X"] / "gold_v2_18x_allowed_decision_values.csv",
        "checks_18aa": p["18AA"] / "gold_v2_18aa_reconciliation_checks.csv",
        "checks_18z": p["18Z"] / "gold_v2_18z_content_checks.csv",
        "checks_18y": p["18Y"] / "gold_v2_18y_load_checks.csv",
        "checks_18x": p["18X"] / "gold_v2_18x_intake_planning_checks.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18ac_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18AC-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18ac_package_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18ac_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18AC_STOP_MISSING_INPUTS", "audit_only": True, "readiness_package_prepared": False, "next_recommended_step": "STOP_REVIEW_18AC_INPUTS"}
        wjson(out / "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18AC readiness package audit-only report\n\nStatus: `18AC_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18ab = rjson(inputs["summary_18ab"])
    summaries = {step: rjson(inputs[f"summary_{step.lower()}"]) for step in ["18X", "18Y", "18Z", "18AA"]}
    checks_tables = [rcsv(inputs[x]) for x in ["checks_18ab", "checks_18aa", "checks_18z", "checks_18y", "checks_18x"]]
    gates18ab, safe18ab = rcsv(inputs["gates_18ab"]), rcsv(inputs["safety_18ab"])
    blockers = rcsv(inputs["blockers_18ab"])
    fields, values = rcsv(inputs["fields_18x"]), rcsv(inputs["values_18x"])
    template = rjson(inputs["template_18x"])
    evidence_rows = []
    for role, path in inputs.items():
        evidence_rows.append([role, str(path), lp(path).exists(), "READINESS_PACKAGE_EVIDENCE_ONLY"])
    evidence_index = pd.DataFrame(evidence_rows, columns=["evidence_role", "path", "exists", "package_use"])
    wcsv(evidence_index, out / "gold_v2_18ac_evidence_package_index.csv")
    still_blocking_false = int((~blockers.get("must_remain_blocked_before_human_intake", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    script_can_clear = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    blocker_summary = pd.DataFrame([
        ["blocker_rows", int(len(blockers)), ">0"],
        ["must_remain_blocked_false_rows", still_blocking_false, "0"],
        ["script_can_clear_true_rows", script_can_clear, "0"],
        ["template_decision_value", template.get("decision_value"), "UNSET"],
    ], columns=["item", "observed", "expected"])
    wcsv(blocker_summary, out / "gold_v2_18ac_blocker_package_summary.csv")
    upstream_stop = sum(stop_count(df) for df in checks_tables + [safe18ab])
    forbidden_gates = forbidden_gate_count(gates18ab, "allowed_after_18ab_success")
    all_refs = []
    for name in REFS:
        path = fx()/name
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                all_refs.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in all_refs)
    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in list(summaries.values()) + [s18ab])
    checks = pd.DataFrame([
        ck("18AC-C001", "18AB status", s18ab.get("status"), EXPECTED_18AB, s18ab.get("status") == EXPECTED_18AB),
        ck("18AC-C002", "18AB blocker_review_passed", s18ab.get("blocker_review_passed"), True, bool(s18ab.get("blocker_review_passed", False))),
        ck("18AC-C003", "18AB total_stop_rows", s18ab.get("total_stop_rows"), 0, s18ab.get("total_stop_rows") == 0),
        ck("18AC-C004", "18X-18AB no collected decision/approval", no_decision, True, no_decision),
        ck("18AC-C005", "all package evidence exists", bool(evidence_index["exists"].all()), True, bool(evidence_index["exists"].all())),
        ck("18AC-C006", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18AC-C007", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        ck("18AC-C008", "blockers must remain blocked", still_blocking_false, 0, still_blocking_false == 0),
        ck("18AC-C009", "script_can_clear true rows", script_can_clear, 0, script_can_clear == 0),
        ck("18AC-C010", "fields present", len(fields), ">0", len(fields) > 0),
        ck("18AC-C011", "values present", len(values), ">0", len(values) > 0),
        ck("18AC-C012", "template remains unset", template.get("decision_value"), "UNSET", template.get("decision_value") == "UNSET"),
        ck("18AC-C013", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18AC-C014", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AC_STOP_REVIEW_READINESS_PACKAGE_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18ac_package_checks.csv", checks),
        ("gold_v2_18ac_required_next_gates.csv", gates),
        ("gold_v2_18ac_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18ac_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "readiness_package_prepared": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18ab_status": s18ab.get("status"), "evidence_items": int(len(evidence_index)), "remaining_blockers": int(len(blockers)),
        "total_stop_rows": int(total_stop), "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_18AC_OUTPUTS",
    }
    wjson(out / "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json", summary)
    report = [
        "# GOLD V2 18AC TIER2 source identity human decision intake readiness package audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18AC packaged 18X-18AB intake readiness evidence only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Package checks", mdtable(checks), "", "## Evidence package index", mdtable(evidence_index), "", "## Blocker package summary", mdtable(blocker_summary), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
