#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only"
IN18S = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18S = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_BLOCKED_ACTIONS = {
    "SOURCE_RECOVERY", "SOURCE_IDENTITY_FINALIZATION", "LIVE_EVALUATOR", "FINAL_SIGNAL",
    "DISCORD_SEND", "NO_SIGNAL_DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK",
}
REQUIRED_MARKDOWN_SECTIONS = ["scope", "decision checklist", "required evidence", "manual questions", "actions still blocked"]
AFFIRMATIVE_APPROVAL_MARKERS = [
    "approval granted", "approval_granted: true", "approved by this script", "script approved",
    "decision made by this script", "decision_made: true", "source-of-truth accepted",
    "source of truth accepted", "source identity finalization approved", "source recovery approved",
    "live readiness granted", "final signal readiness granted", "ready for live trading",
    "live evaluator enabled", "final signal enabled",
]
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
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def summary_forbidden_true(summary: dict[str, Any]) -> int:
    n = sum(int(bool(summary.get(k, False))) for k in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18U", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY", "Reconcile 18R/18S/18T packet evidence only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18T.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18T.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18t_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["content_audit_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18u_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18T-S001", "required inputs missing", "STOP"], ["18T-S002", "18S status not passed", "STOP"],
        ["18T-S003", "decision or approval already made", "STOP"], ["18T-S004", "upstream STOP rows present", "STOP"],
        ["18T-S005", "required packet section missing", "STOP"], ["18T-S006", "blocked actions incomplete or not blocked", "STOP"],
        ["18T-S007", "affirmative approval or execution language detected", "STOP"], ["18T-S008", "forbidden gate allowed", "STOP"],
        ["18T-S009", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18s = fx() / IN18S
    p18r = fx() / IN18R
    refs = {"18K": fx() / IN18K, "18L": fx() / IN18L, "18M": fx() / IN18M, "18N": fx() / IN18N, "18O": fx() / IN18O, "18P": fx() / IN18P, "18Q": fx() / IN18Q, "18R": p18r, "18S": p18s}
    inputs = {
        "summary_18s": p18s / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json",
        "load_checks_18s": p18s / "gold_v2_18s_load_checks.csv",
        "packet_file_audit_18s": p18s / "gold_v2_18s_packet_file_audit.csv",
        "markdown_audit_18s": p18s / "gold_v2_18s_markdown_audit.csv",
        "manual_question_audit_18s": p18s / "gold_v2_18s_manual_question_audit.csv",
        "blocked_action_audit_18s": p18s / "gold_v2_18s_blocked_action_audit.csv",
        "next_gates_18s": p18s / "gold_v2_18s_required_next_gates.csv",
        "safety_18s": p18s / "gold_v2_18s_safety_matrix.csv",
        "report_18s": p18s / "GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "markdown_18r": p18r / "gold_v2_18r_human_review_packet_markdown.md",
        "manual_questions_18r": p18r / "gold_v2_18r_manual_decision_questions.csv",
        "blocked_actions_18r": p18r / "gold_v2_18r_actions_still_blocked.csv",
        "next_gates_18r": p18r / "gold_v2_18r_required_next_gates.csv",
        "safety_18r": p18r / "gold_v2_18r_safety_matrix.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18t_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18T_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18T-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18t_content_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18t_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "content_audit_passed": False, "next_recommended_step": "STOP_REVIEW_18T_INPUTS"}
        wjson(out / "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18T content audit-only report\n\nStatus: `18T_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18s = rjson(inputs["summary_18s"])
    load18s = rcsv(inputs["load_checks_18s"])
    pfile18s = rcsv(inputs["packet_file_audit_18s"])
    mda18s = rcsv(inputs["markdown_audit_18s"])
    q18s = rcsv(inputs["manual_question_audit_18s"])
    ba18s = rcsv(inputs["blocked_action_audit_18s"])
    gates18s = rcsv(inputs["next_gates_18s"])
    safe18s = rcsv(inputs["safety_18s"])
    markdown = lp(inputs["markdown_18r"]).read_text(encoding="utf-8")
    manual = rcsv(inputs["manual_questions_18r"])
    blocked = rcsv(inputs["blocked_actions_18r"])
    gates18r = rcsv(inputs["next_gates_18r"])
    safe18r = rcsv(inputs["safety_18r"])

    text = markdown.lower()
    section_audit = pd.DataFrame([
        [f"18T-SEC{i+1:03d}", sec, sec in text, True, "PASS" if sec in text else "STOP"]
        for i, sec in enumerate(REQUIRED_MARKDOWN_SECTIONS)
    ], columns=["section_check_id", "section", "observed", "expected", "status"])
    approval_hits = [m for m in AFFIRMATIVE_APPROVAL_MARKERS if m in text]
    section_audit = pd.concat([section_audit, pd.DataFrame([{
        "section_check_id": "18T-SEC999", "section": "affirmative approval/execution language", "observed": len(approval_hits), "expected": 0, "status": "PASS" if not approval_hits else "STOP"
    }])], ignore_index=True)

    manual_bad = int((manual.get("script_decision_status", pd.Series(dtype=str)).astype(str) != "NO_SCRIPT_DECISION").sum()) if not manual.empty else 999
    manual_audit = pd.DataFrame([["18T-Q001", "manual questions remain no-script-decision", manual_bad, 0, "PASS" if manual_bad == 0 else "STOP"]], columns=["question_check_id", "check", "observed", "expected", "status"])
    actions = set(blocked["action"].astype(str)) if "action" in blocked.columns else set()
    missing_actions = sorted(REQUIRED_BLOCKED_ACTIONS - actions)
    not_blocked = int((blocked.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blocked.empty else 999
    blocked_audit = pd.DataFrame([
        ["18T-A001", "missing required blocked actions", len(missing_actions), 0, "PASS" if not missing_actions else "STOP"],
        ["18T-A002", "actions remain BLOCKED", not_blocked, 0, "PASS" if not_blocked == 0 else "STOP"],
    ], columns=["action_check_id", "check", "observed", "expected", "status"])
    forbidden_gate_true = 0
    for df, col in [(gates18s, "allowed_after_18s_success"), (gates18r, "allowed_after_18r_success")]:
        if {"next_step", col}.issubset(df.columns):
            forbidden_gate_true += int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][col].map(truthy).sum())
        else:
            forbidden_gate_true += 999
    summary_forbidden = sum(summary_forbidden_true(rjson(path / f"gold_v2_{step.lower()}_tier2_source_identity_dry_run_implementation_summary.json")) for step, path in [] )
    ref_summaries = []
    for name, path in refs.items():
        candidates = list(lp(path).glob("*summary.json")) if lp(path).exists() else []
        if candidates:
            ref_summaries.append(rjson(candidates[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in ref_summaries)
    upstream_stop = sum(stop_count(df) for df in [load18s, pfile18s, mda18s, q18s, ba18s, safe18s, safe18r])
    content_checks = pd.DataFrame([
        ck("18T-C001", "18S status", s18s.get("status"), EXPECTED_18S, s18s.get("status") == EXPECTED_18S),
        ck("18T-C002", "18S packet_load_smoke_passed", s18s.get("packet_load_smoke_passed"), True, bool(s18s.get("packet_load_smoke_passed", False))),
        ck("18T-C003", "18S total_stop_rows", s18s.get("total_stop_rows"), 0, s18s.get("total_stop_rows") == 0),
        ck("18T-C004", "18S decision_made", s18s.get("decision_made"), False, s18s.get("decision_made") is False),
        ck("18T-C005", "18S approval_granted", s18s.get("approval_granted"), False, s18s.get("approval_granted") is False),
        ck("18T-C006", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18T-C007", "packet section STOP rows", stop_count(section_audit), 0, stop_count(section_audit) == 0),
        ck("18T-C008", "manual question STOP rows", stop_count(manual_audit), 0, stop_count(manual_audit) == 0),
        ck("18T-C009", "blocked action STOP rows", stop_count(blocked_audit), 0, stop_count(blocked_audit) == 0),
        ck("18T-C010", "forbidden gates allowed", forbidden_gate_true, 0, forbidden_gate_true == 0),
        ck("18T-C011", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = sum(stop_count(df) for df in [content_checks, section_audit, manual_audit, blocked_audit])
    success = total_stop == 0
    status = SUCCESS if success else "18T_STOP_REVIEW_PACKET_CONTENT_AUDIT_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18t_content_checks.csv", content_checks),
        ("gold_v2_18t_packet_section_audit.csv", section_audit),
        ("gold_v2_18t_manual_question_content_audit.csv", manual_audit),
        ("gold_v2_18t_blocked_action_content_audit.csv", blocked_audit),
        ("gold_v2_18t_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18t_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18t_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "content_audit_passed": success, "decision_made": False, "approval_granted": False,
        "upstream_18s_status": s18s.get("status"), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_18T_OUTPUTS",
    }
    wjson(out / "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_summary.json", summary)
    report = [
        "# GOLD V2 18T TIER2 source identity human review packet content audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18T audited human-review packet content only.", "- No decision or approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Content checks", mdtable(content_checks), "", "## Packet section audit", mdtable(section_audit), "", "## Manual question audit", mdtable(manual_audit), "", "## Blocked action audit", mdtable(blocked_audit), "", "## Next gates", mdtable(next_gates(success)), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
