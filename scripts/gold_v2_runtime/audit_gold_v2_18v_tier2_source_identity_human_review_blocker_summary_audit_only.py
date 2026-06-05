#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY"
OUT_DIR = "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only"
IN18U = "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only"
IN18T = "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18U = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_BLOCKED_ACTIONS = {
    "SOURCE_RECOVERY", "SOURCE_IDENTITY_FINALIZATION", "LIVE_EVALUATOR", "FINAL_SIGNAL",
    "DISCORD_SEND", "NO_SIGNAL_DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK",
}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]


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
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def summary_forbidden_true(summary: dict[str, Any]) -> int:
    n = sum(int(bool(summary.get(k, False))) for k in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18W", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY", "Prepare final human-review decision packet only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18V.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18V.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18v_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["blocker_summary_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18w_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18V-S001", "required inputs missing", "STOP"], ["18V-S002", "18U status not passed", "STOP"],
        ["18V-S003", "decision or approval already made", "STOP"], ["18V-S004", "upstream STOP rows present", "STOP"],
        ["18V-S005", "blocked actions incomplete or not blocked", "STOP"], ["18V-S006", "manual questions not no-script-decision", "STOP"],
        ["18V-S007", "forbidden gate allowed", "STOP"], ["18V-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18u, p18t, p18r = fx()/IN18U, fx()/IN18T, fx()/IN18R
    refs = {"18K": fx()/IN18K, "18L": fx()/IN18L, "18M": fx()/IN18M, "18N": fx()/IN18N, "18O": fx()/IN18O, "18P": fx()/IN18P, "18Q": fx()/IN18Q, "18R": p18r, "18T": p18t, "18U": p18u}
    inputs = {
        "summary_18u": p18u / "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_summary.json",
        "checks_18u": p18u / "gold_v2_18u_reconciliation_checks.csv",
        "gates_18u": p18u / "gold_v2_18u_required_next_gates.csv",
        "safety_18u": p18u / "gold_v2_18u_safety_matrix.csv",
        "report_18u": p18u / "GOLD_V2_18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "blocked_actions_18r": p18r / "gold_v2_18r_actions_still_blocked.csv",
        "manual_questions_18r": p18r / "gold_v2_18r_manual_decision_questions.csv",
        "gates_18r": p18r / "gold_v2_18r_required_next_gates.csv",
        "blocked_audit_18t": p18t / "gold_v2_18t_blocked_action_content_audit.csv",
        "manual_audit_18t": p18t / "gold_v2_18t_manual_question_content_audit.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18v_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18V-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18v_blocker_summary_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18v_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18V_STOP_MISSING_INPUTS", "audit_only": True, "blocker_summary_prepared": False, "next_recommended_step": "STOP_REVIEW_18V_INPUTS"}
        wjson(out / "gold_v2_18v_tier2_source_identity_human_review_blocker_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18V blocker summary audit-only report\n\nStatus: `18V_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18u = rjson(inputs["summary_18u"])
    checks18u = rcsv(inputs["checks_18u"])
    gates18u, gates18r = rcsv(inputs["gates_18u"]), rcsv(inputs["gates_18r"])
    safe18u = rcsv(inputs["safety_18u"])
    blocked = rcsv(inputs["blocked_actions_18r"])
    manual = rcsv(inputs["manual_questions_18r"])
    blocked_audit_18t = rcsv(inputs["blocked_audit_18t"])
    manual_audit_18t = rcsv(inputs["manual_audit_18t"])

    action_col = "action" if "action" in blocked.columns else "blocked_action" if "blocked_action" in blocked.columns else None
    observed_actions = set(blocked[action_col].astype(str)) if action_col else set()
    missing_actions = sorted(REQUIRED_BLOCKED_ACTIONS - observed_actions)
    not_blocked = int((blocked.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blocked.empty else 999
    remaining_blockers = blocked.copy()
    if action_col:
        remaining_blockers["blocker_category"] = remaining_blockers[action_col].astype(str)
    else:
        remaining_blockers["blocker_category"] = "UNKNOWN_NO_ACTION_COLUMN"
    remaining_blockers["still_blocking_after_18v"] = True
    remaining_blockers["script_can_clear"] = False
    wcsv(remaining_blockers, out / "gold_v2_18v_remaining_blockers.csv")

    manual_bad = int((manual.get("script_decision_status", pd.Series(dtype=str)).astype(str) != "NO_SCRIPT_DECISION").sum()) if not manual.empty else 999
    manual_summary = pd.DataFrame([
        ["manual_question_rows", int(len(manual)), "informational_only"],
        ["non_no_script_decision_rows", manual_bad, "must_be_zero"],
        ["script_decision_made", False, "must_remain_false"],
        ["script_approval_granted", False, "must_remain_false"],
    ], columns=["item", "observed", "requirement"])
    wcsv(manual_summary, out / "gold_v2_18v_manual_decision_summary.csv")

    summaries = []
    for path in refs.values():
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    forbidden_gates = forbidden_gate_count(gates18u, "allowed_after_18u_success") + forbidden_gate_count(gates18r, "allowed_after_18r_success")
    upstream_stop = stop_count(checks18u) + stop_count(safe18u) + stop_count(blocked_audit_18t) + stop_count(manual_audit_18t)
    checks = pd.DataFrame([
        ck("18V-C001", "18U status", s18u.get("status"), "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED", s18u.get("status") == "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"),
        ck("18V-C002", "18U reconciliation_passed", s18u.get("reconciliation_passed"), True, bool(s18u.get("reconciliation_passed", False))),
        ck("18V-C003", "18U total_stop_rows", s18u.get("total_stop_rows"), 0, s18u.get("total_stop_rows") == 0),
        ck("18V-C004", "18U decision_made", s18u.get("decision_made"), False, s18u.get("decision_made") is False),
        ck("18V-C005", "18U approval_granted", s18u.get("approval_granted"), False, s18u.get("approval_granted") is False),
        ck("18V-C006", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18V-C007", "missing required blocked actions", len(missing_actions), 0, len(missing_actions) == 0),
        ck("18V-C008", "blocked actions not BLOCKED", not_blocked, 0, not_blocked == 0),
        ck("18V-C009", "manual questions not no-script-decision", manual_bad, 0, manual_bad == 0),
        ck("18V-C010", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18V-C011", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18V_STOP_REVIEW_BLOCKER_SUMMARY_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18v_blocker_summary_checks.csv", checks),
        ("gold_v2_18v_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18v_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18v_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "blocker_summary_prepared": success, "decision_made": False, "approval_granted": False,
        "upstream_18u_status": s18u.get("status"), "remaining_blockers": int(len(remaining_blockers)),
        "manual_question_rows": int(len(manual)), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY" if success else "STOP_REVIEW_18V_OUTPUTS",
    }
    wjson(out / "gold_v2_18v_tier2_source_identity_human_review_blocker_summary.json", summary)
    report = [
        "# GOLD V2 18V TIER2 source identity human review blocker summary audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18V summarized remaining blockers only.", "- No decision or approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Blocker summary checks", mdtable(checks), "", "## Remaining blockers", mdtable(remaining_blockers), "", "## Manual decision summary", mdtable(manual_summary), "", "## Next gates", mdtable(next_gates(success)), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
