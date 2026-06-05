#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only"
IN18T = "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only"
IN18S = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18T = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
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


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18V", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY", "Summarize remaining blockers for human review only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18U.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18U.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18u_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["reconciliation_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18v_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18U-S001", "required inputs missing", "STOP"], ["18U-S002", "18T status not passed", "STOP"],
        ["18U-S003", "decision or approval already made", "STOP"], ["18U-S004", "upstream STOP rows present", "STOP"],
        ["18U-S005", "packet count reconciliation failed", "STOP"], ["18U-S006", "blocked action reconciliation failed", "STOP"],
        ["18U-S007", "manual question reconciliation failed", "STOP"], ["18U-S008", "forbidden gate allowed", "STOP"],
        ["18U-S009", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18t, p18s, p18r = fx() / IN18T, fx() / IN18S, fx() / IN18R
    refs = {"18K": fx()/IN18K, "18L": fx()/IN18L, "18M": fx()/IN18M, "18N": fx()/IN18N, "18O": fx()/IN18O, "18P": fx()/IN18P, "18Q": fx()/IN18Q, "18R": p18r, "18S": p18s, "18T": p18t}
    inputs = {
        "summary_18t": p18t / "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_summary.json",
        "content_checks_18t": p18t / "gold_v2_18t_content_checks.csv",
        "section_audit_18t": p18t / "gold_v2_18t_packet_section_audit.csv",
        "manual_audit_18t": p18t / "gold_v2_18t_manual_question_content_audit.csv",
        "blocked_audit_18t": p18t / "gold_v2_18t_blocked_action_content_audit.csv",
        "gates_18t": p18t / "gold_v2_18t_required_next_gates.csv",
        "safety_18t": p18t / "gold_v2_18t_safety_matrix.csv",
        "report_18t": p18t / "GOLD_V2_18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_18s": p18s / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json",
        "load_checks_18s": p18s / "gold_v2_18s_load_checks.csv",
        "gates_18s": p18s / "gold_v2_18s_required_next_gates.csv",
        "safety_18s": p18s / "gold_v2_18s_safety_matrix.csv",
        "summary_18r": p18r / "gold_v2_18r_tier2_source_identity_human_review_packet_summary.json",
        "packet_index_18r": p18r / "gold_v2_18r_human_review_packet_index.csv",
        "manual_questions_18r": p18r / "gold_v2_18r_manual_decision_questions.csv",
        "blocked_actions_18r": p18r / "gold_v2_18r_actions_still_blocked.csv",
        "gates_18r": p18r / "gold_v2_18r_required_next_gates.csv",
        "safety_18r": p18r / "gold_v2_18r_safety_matrix.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18u_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18U-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18u_reconciliation_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18u_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18U_STOP_MISSING_INPUTS", "audit_only": True, "reconciliation_passed": False, "next_recommended_step": "STOP_REVIEW_18U_INPUTS"}
        wjson(out / "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18U reconciliation audit-only report\n\nStatus: `18U_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18t, s18s, s18r = rjson(inputs["summary_18t"]), rjson(inputs["summary_18s"]), rjson(inputs["summary_18r"])
    t_tables = [rcsv(inputs[k]) for k in ["content_checks_18t", "section_audit_18t", "manual_audit_18t", "blocked_audit_18t", "safety_18t"]]
    s_tables = [rcsv(inputs[k]) for k in ["load_checks_18s", "safety_18s"]]
    r_safe = rcsv(inputs["safety_18r"])
    packet_index = rcsv(inputs["packet_index_18r"])
    manual = rcsv(inputs["manual_questions_18r"])
    blocked = rcsv(inputs["blocked_actions_18r"])
    t_blocked_audit = rcsv(inputs["blocked_audit_18t"])
    t_manual_audit = rcsv(inputs["manual_audit_18t"])
    gates18t, gates18s, gates18r = rcsv(inputs["gates_18t"]), rcsv(inputs["gates_18s"]), rcsv(inputs["gates_18r"])

    packet_count = int(len(packet_index))
    s_packet_files_checked = int(s18s.get("packet_files_checked", -1))
    packet_recon = pd.DataFrame([
        ["18U-P001", "18R packet index vs 18S packet files checked", packet_count, s_packet_files_checked, "PASS" if packet_count == s_packet_files_checked else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    blocked_count = int(len(blocked))
    t_blocked_stop = stop_count(t_blocked_audit)
    blocked_recon = pd.DataFrame([
        ["18U-A001", "18R blocked action rows", blocked_count, s18s.get("blocked_actions_checked", -1), "PASS" if blocked_count == int(s18s.get("blocked_actions_checked", -1)) else "STOP"],
        ["18U-A002", "18T blocked action audit STOP rows", t_blocked_stop, 0, "PASS" if t_blocked_stop == 0 else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    manual_count = int(len(manual))
    manual_recon = pd.DataFrame([
        ["18U-Q001", "18R manual questions vs 18S count", manual_count, s18s.get("manual_questions_checked", -1), "PASS" if manual_count == int(s18s.get("manual_questions_checked", -1)) else "STOP"],
        ["18U-Q002", "18T manual question audit STOP rows", stop_count(t_manual_audit), 0, "PASS" if stop_count(t_manual_audit) == 0 else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    upstream_stop = sum(stop_count(df) for df in t_tables + s_tables + [r_safe])
    forbidden_gates = forbidden_gate_count(gates18t, "allowed_after_18t_success") + forbidden_gate_count(gates18s, "allowed_after_18s_success") + forbidden_gate_count(gates18r, "allowed_after_18r_success")
    summaries = []
    for _, path in refs.items():
        if lp(path).exists():
            candidates = list(lp(path).glob("*summary.json"))
            if candidates:
                summaries.append(rjson(candidates[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    no_decision = all(s.get("decision_made") is False and s.get("approval_granted") is False for s in [s18r, s18s, s18t])
    rec_checks = pd.DataFrame([
        ck("18U-C001", "18T status", s18t.get("status"), EXPECTED_18T, s18t.get("status") == EXPECTED_18T),
        ck("18U-C002", "18T content_audit_passed", s18t.get("content_audit_passed"), True, bool(s18t.get("content_audit_passed", False))),
        ck("18U-C003", "18T total_stop_rows", s18t.get("total_stop_rows"), 0, s18t.get("total_stop_rows") == 0),
        ck("18U-C004", "18R/18S/18T no decision or approval", no_decision, True, no_decision),
        ck("18U-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18U-C006", "packet count reconciliation STOP rows", stop_count(packet_recon), 0, stop_count(packet_recon) == 0),
        ck("18U-C007", "blocked action reconciliation STOP rows", stop_count(blocked_recon), 0, stop_count(blocked_recon) == 0),
        ck("18U-C008", "manual question reconciliation STOP rows", stop_count(manual_recon), 0, stop_count(manual_recon) == 0),
        ck("18U-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18U-C010", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = sum(stop_count(df) for df in [rec_checks, packet_recon, blocked_recon, manual_recon])
    success = total_stop == 0
    status = SUCCESS if success else "18U_STOP_REVIEW_PACKET_RECONCILIATION_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18u_reconciliation_checks.csv", rec_checks),
        ("gold_v2_18u_packet_count_reconciliation.csv", packet_recon),
        ("gold_v2_18u_blocked_action_reconciliation.csv", blocked_recon),
        ("gold_v2_18u_manual_question_reconciliation.csv", manual_recon),
        ("gold_v2_18u_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18u_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18u_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "reconciliation_passed": success, "decision_made": False, "approval_granted": False,
        "upstream_18t_status": s18t.get("status"), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY" if success else "STOP_REVIEW_18U_OUTPUTS",
    }
    wjson(out / "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 18U TIER2 source identity human review packet reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18U reconciled 18R/18S/18T human-review packet evidence only.", "- No decision or approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Reconciliation checks", mdtable(rec_checks), "", "## Packet count reconciliation", mdtable(packet_recon), "", "## Blocked action reconciliation", mdtable(blocked_recon), "", "## Manual question reconciliation", mdtable(manual_recon), "", "## Next gates", mdtable(next_gates(success)), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
