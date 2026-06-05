#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY"
OUT_DIR = "gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only"
IN18W = OUT_DIR
IN18V = "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18U = "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only"
IN18T = "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only"
IN18S = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18V = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
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
    ensure(path); df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path); lp(path).write_text(text, encoding="utf-8")


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
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


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
        ["18X", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY", "Plan intake of an explicit later human decision only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18W.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18W.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18w_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["decision_packet_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18x_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18W-S001", "required inputs missing", "STOP"], ["18W-S002", "18V status not passed", "STOP"],
        ["18W-S003", "decision or approval already made", "STOP"], ["18W-S004", "upstream STOP rows present", "STOP"],
        ["18W-S005", "remaining blockers missing or clearable by script", "STOP"], ["18W-S006", "manual questions unavailable", "STOP"],
        ["18W-S007", "forbidden gate allowed", "STOP"], ["18W-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18v, p18r = fx()/IN18V, fx()/IN18R
    refs = [fx()/x for x in [IN18K, IN18L, IN18M, IN18N, IN18O, IN18P, IN18Q, IN18R, IN18S, IN18T, IN18U, IN18V]]
    inputs = {
        "summary_18v": p18v / "gold_v2_18v_tier2_source_identity_human_review_blocker_summary.json",
        "checks_18v": p18v / "gold_v2_18v_blocker_summary_checks.csv",
        "remaining_blockers_18v": p18v / "gold_v2_18v_remaining_blockers.csv",
        "manual_summary_18v": p18v / "gold_v2_18v_manual_decision_summary.csv",
        "gates_18v": p18v / "gold_v2_18v_required_next_gates.csv",
        "safety_18v": p18v / "gold_v2_18v_safety_matrix.csv",
        "report_18v": p18v / "GOLD_V2_18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY_REPORT.md",
        "packet_markdown_18r": p18r / "gold_v2_18r_human_review_packet_markdown.md",
        "manual_questions_18r": p18r / "gold_v2_18r_manual_decision_questions.csv",
        "blocked_actions_18r": p18r / "gold_v2_18r_actions_still_blocked.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18w_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18W-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18w_decision_packet_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18w_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18W_STOP_MISSING_INPUTS", "audit_only": True, "decision_packet_prepared": False, "next_recommended_step": "STOP_REVIEW_18W_INPUTS"}
        wjson(out / "gold_v2_18w_tier2_source_identity_human_review_decision_packet_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18W decision packet audit-only report\n\nStatus: `18W_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18v = rjson(inputs["summary_18v"])
    checks18v, safe18v, gates18v = rcsv(inputs["checks_18v"]), rcsv(inputs["safety_18v"]), rcsv(inputs["gates_18v"])
    blockers, manual_questions = rcsv(inputs["remaining_blockers_18v"]), rcsv(inputs["manual_questions_18r"])
    manual_summary = rcsv(inputs["manual_summary_18v"])
    readme = lp(inputs["packet_markdown_18r"]).read_text(encoding="utf-8")

    human_options = pd.DataFrame([
        ["DEFER", "Keep all blockers and request more evidence.", "HUMAN_ONLY", False],
        ["REQUEST_MORE_AUDIT", "Ask for additional audit-only checks.", "HUMAN_ONLY", False],
        ["CONSIDER_APPROVAL_LATER", "Human may later consider explicit approval outside this script.", "HUMAN_ONLY", False],
        ["REJECT_SOURCE_RECOVERY", "Human may reject source recovery/finalization.", "HUMAN_ONLY", False],
    ], columns=["option", "meaning", "decision_owner", "script_executes_action"])
    wcsv(human_options, out / "gold_v2_18w_human_decision_options.csv")

    blockers_present = len(blockers) > 0
    still_blocking_ok = bool(blockers.get("still_blocking_after_18v", pd.Series(dtype=bool)).map(truthy).all()) if blockers_present else False
    script_can_clear_false = not bool(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).any()) if blockers_present else False
    manual_present = len(manual_questions) > 0
    manual_no_decision = int((manual_questions.get("script_decision_status", pd.Series(dtype=str)).astype(str) != "NO_SCRIPT_DECISION").sum()) if manual_present else 999
    upstream_stop = stop_count(checks18v) + stop_count(safe18v)
    forbidden_gates = forbidden_gate_count(gates18v, "allowed_after_18v_success")
    summaries = []
    for p in refs:
        if lp(p).exists():
            found = list(lp(p).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    checks = pd.DataFrame([
        ck("18W-C001", "18V status", s18v.get("status"), EXPECTED_18V, s18v.get("status") == EXPECTED_18V),
        ck("18W-C002", "18V blocker_summary_prepared", s18v.get("blocker_summary_prepared"), True, bool(s18v.get("blocker_summary_prepared", False))),
        ck("18W-C003", "18V total_stop_rows", s18v.get("total_stop_rows"), 0, s18v.get("total_stop_rows") == 0),
        ck("18W-C004", "18V decision_made", s18v.get("decision_made"), False, s18v.get("decision_made") is False),
        ck("18W-C005", "18V approval_granted", s18v.get("approval_granted"), False, s18v.get("approval_granted") is False),
        ck("18W-C006", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18W-C007", "remaining blockers present", len(blockers), ">0", blockers_present),
        ck("18W-C008", "all blockers still blocking", still_blocking_ok, True, still_blocking_ok),
        ck("18W-C009", "script cannot clear blockers", script_can_clear_false, True, script_can_clear_false),
        ck("18W-C010", "manual questions present", len(manual_questions), ">0", manual_present),
        ck("18W-C011", "manual questions no-script-decision", manual_no_decision, 0, manual_no_decision == 0),
        ck("18W-C012", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18W-C013", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18W_STOP_REVIEW_DECISION_PACKET_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18w_decision_packet_checks.csv", checks),
        ("gold_v2_18w_required_next_gates.csv", gates),
        ("gold_v2_18w_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18w_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    decision_packet = [
        "# GOLD V2 18W human-review decision packet", "", "## Scope",
        "This packet is for human review only. It is not approval, not a decision, and not source recovery.", "",
        "## Upstream basis", f"18V status: `{s18v.get('status')}`", "",
        "## Remaining blockers", mdtable(blockers), "", "## Human-only decision options", mdtable(human_options), "", "## Manual questions", mdtable(manual_questions), "", "## Original 18R packet excerpt/source", "18R markdown was loaded for packet context; no automated decision was made.", "",
    ]
    wtxt(out / "gold_v2_18w_decision_packet_markdown.md", "\n".join(decision_packet))
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "decision_packet_prepared": success, "decision_made": False, "approval_granted": False,
        "upstream_18v_status": s18v.get("status"), "remaining_blockers": int(len(blockers)),
        "human_decision_options": int(len(human_options)), "manual_question_rows": int(len(manual_questions)), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY" if success else "STOP_REVIEW_18W_OUTPUTS",
    }
    wjson(out / "gold_v2_18w_tier2_source_identity_human_review_decision_packet_summary.json", summary)
    report = [
        "# GOLD V2 18W TIER2 source identity human review decision packet audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18W prepared a human-review decision packet only.", "- No decision or approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Decision packet checks", mdtable(checks), "", "## Human-only options", mdtable(human_options), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
