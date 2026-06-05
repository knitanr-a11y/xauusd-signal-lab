#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY"
OUT_DIR = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18Q = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
REQUIRED_EVIDENCE_STEPS = ["18K", "18L", "18M", "18N", "18O"]
REQUIRED_BLOCKED_ACTIONS = ["SOURCE_RECOVERY", "SOURCE_IDENTITY_FINALIZATION", "LIVE_EVALUATOR", "FINAL_SIGNAL", "DISCORD_SEND", "NO_SIGNAL_DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FORBIDDEN_GATES = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"]
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "ledger_is_source_of_truth",
    "live_or_final_implementation_allowed",
    "oh_lc_replay_allowed",
    "live_enabled",
    "final_signal_allowed",
    "no_signal_discord_notified",
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
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > limit:
        out.append(f"\n_Showing first {limit} of {len(df)} rows._")
    return "\n".join(out)


def forbidden_summary_true(summary: dict[str, Any]) -> int:
    n = 0
    for key in FORBIDDEN_SUMMARY_FLAGS:
        n += int(bool(summary.get(key, False)))
    ext = summary.get("external_actions", {})
    if isinstance(ext, dict):
        n += sum(int(bool(v)) for v in ext.values())
    else:
        n += 1
    return n


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["human_review_packet_only", True, True, "PASS"],
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
        ["next_gate_18s_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18S", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY", "Validate that the human-review packet outputs load and still keep forbidden gates blocked.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18R.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18R.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18r_success"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18R-S001", "required inputs missing", "STOP"],
        ["18R-S002", "18Q status not passed", "STOP"],
        ["18R-S003", "18Q made decision or granted approval", "STOP"],
        ["18R-S004", "any upstream STOP row present", "STOP"],
        ["18R-S005", "packet items missing", "STOP"],
        ["18R-S006", "required evidence incomplete", "STOP"],
        ["18R-S007", "forbidden gate allowed", "STOP"],
        ["18R-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18q = fx() / IN18Q
    p18p = fx() / IN18P
    p18o = fx() / IN18O
    p18n = fx() / IN18N
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18q": p18q / "gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json",
        "input_audit_18q": p18q / "gold_v2_18q_input_audit.csv",
        "planning_checks_18q": p18q / "gold_v2_18q_planning_checks.csv",
        "decision_checklist_18q": p18q / "gold_v2_18q_decision_checklist.csv",
        "required_evidence_18q": p18q / "gold_v2_18q_required_evidence_for_decision.csv",
        "actions_blocked_18q": p18q / "gold_v2_18q_actions_still_blocked.csv",
        "next_gates_18q": p18q / "gold_v2_18q_required_next_gates.csv",
        "safety_18q": p18q / "gold_v2_18q_safety_matrix.csv",
        "report_18q": p18q / "GOLD_V2_18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY_REPORT.md",
        "summary_18p": p18p / "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json",
        "summary_18o": p18o / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json",
        "summary_18n": p18n / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json",
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18r_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18R_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18R-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18r_packet_checks.csv")
        wcsv(safety(False), out / "gold_v2_18r_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "human_review_packet_ready": False, "next_recommended_step": "STOP_REVIEW_18R_INPUTS"}
        wjson(out / "gold_v2_18r_tier2_source_identity_human_review_packet_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18R TIER2 source identity human review packet audit-only report\n\nStatus: `18R_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18q = rjson(inputs["summary_18q"])
    summaries = {"18K": rjson(inputs["summary_18k"]), "18L": rjson(inputs["summary_18l"]), "18M": rjson(inputs["summary_18m"]), "18N": rjson(inputs["summary_18n"]), "18O": rjson(inputs["summary_18o"]), "18P": rjson(inputs["summary_18p"]), "18Q": s18q}
    planning = rcsv(inputs["planning_checks_18q"])
    checklist = rcsv(inputs["decision_checklist_18q"])
    evidence = rcsv(inputs["required_evidence_18q"])
    blocked = rcsv(inputs["actions_blocked_18q"])
    gates = rcsv(inputs["next_gates_18q"])
    safe18q = rcsv(inputs["safety_18q"])
    _ = lp(inputs["report_18q"]).read_text(encoding="utf-8")

    evidence_steps = set(evidence["step"].astype(str)) if "step" in evidence.columns else set()
    missing_evidence = [s for s in REQUIRED_EVIDENCE_STEPS if s not in evidence_steps]
    blocking_items = int((checklist.get("importance", pd.Series(dtype=str)).astype(str) == "BLOCKING").sum()) if not checklist.empty else 0
    blocked_actions = set(blocked["action"].astype(str)) if "action" in blocked.columns else set()
    missing_blocked_actions = [a for a in REQUIRED_BLOCKED_ACTIONS if a not in blocked_actions]
    forbidden_gate_true = 999
    if {"next_step", "allowed_after_18q_success"}.issubset(gates.columns):
        forbidden = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
        forbidden_gate_true = int(forbidden["allowed_after_18q_success"].map(truthy).sum())
    forbidden_summary_total = sum(forbidden_summary_true(v) for v in summaries.values())
    upstream_stop = stop_count(planning) + stop_count(safe18q)
    packet_checks = pd.DataFrame([
        ck("18R-C001", "18Q status", s18q.get("status"), EXPECTED_18Q, s18q.get("status") == EXPECTED_18Q),
        ck("18R-C002", "18Q decision_planning_ready", s18q.get("decision_planning_ready"), True, bool(s18q.get("decision_planning_ready", False))),
        ck("18R-C003", "18Q decision_made", s18q.get("decision_made"), False, s18q.get("decision_made") is False),
        ck("18R-C004", "18Q approval_granted", s18q.get("approval_granted"), False, s18q.get("approval_granted") is False),
        ck("18R-C005", "18Q total_stop_rows", s18q.get("total_stop_rows"), 0, s18q.get("total_stop_rows") == 0),
        ck("18R-C006", "18Q upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18R-C007", "missing evidence steps", len(missing_evidence), 0, len(missing_evidence) == 0),
        ck("18R-C008", "blocking checklist items", blocking_items, ">=3", blocking_items >= 3),
        ck("18R-C009", "missing blocked actions", len(missing_blocked_actions), 0, len(missing_blocked_actions) == 0),
        ck("18R-C010", "forbidden gates allowed", forbidden_gate_true, 0, forbidden_gate_true == 0),
        ck("18R-C011", "forbidden summary flags true across 18K-18Q", forbidden_summary_total, 0, forbidden_summary_total == 0),
    ])
    packet_index = pd.DataFrame([
        ["PKT-001", "Summary status", "gold_v2_18r_tier2_source_identity_human_review_packet_summary.json", "GENERATED"],
        ["PKT-002", "Packet checks", "gold_v2_18r_packet_checks.csv", "GENERATED"],
        ["PKT-003", "Human review packet markdown", "gold_v2_18r_human_review_packet_markdown.md", "GENERATED"],
        ["PKT-004", "Manual decision questions", "gold_v2_18r_manual_decision_questions.csv", "GENERATED"],
        ["PKT-005", "Actions still blocked", "gold_v2_18r_actions_still_blocked.csv", "GENERATED"],
    ], columns=["packet_item_id", "packet_item", "file", "status"])
    manual_questions = pd.DataFrame([
        ["Q-001", "Has the human reviewer inspected 18K-18Q reports and summaries?", "MANUAL_REQUIRED", "NO_SCRIPT_DECISION"],
        ["Q-002", "Should the dry-run candidate ledger remain not source-of-truth?", "MANUAL_REQUIRED", "NO_SCRIPT_DECISION"],
        ["Q-003", "What evidence would be required before source recovery planning?", "MANUAL_REQUIRED", "NO_SCRIPT_DECISION"],
        ["Q-004", "What evidence would be required before source identity finalization planning?", "MANUAL_REQUIRED", "NO_SCRIPT_DECISION"],
        ["Q-005", "Should live/final/Discord/MT5/AI/live hook remain blocked?", "MANUAL_REQUIRED", "NO_SCRIPT_DECISION"],
    ], columns=["question_id", "question", "required", "script_decision_status"])
    total_stop = stop_count(packet_checks)
    success = total_stop == 0
    status = SUCCESS if success else "18R_STOP_REVIEW_HUMAN_REVIEW_PACKET_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18r_packet_checks.csv", packet_checks),
        ("gold_v2_18r_human_review_packet_index.csv", packet_index),
        ("gold_v2_18r_manual_decision_questions.csv", manual_questions),
        ("gold_v2_18r_actions_still_blocked.csv", blocked),
        ("gold_v2_18r_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18r_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18r_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    markdown = [
        "# GOLD V2 18R human review packet",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Scope",
        "This packet is audit-only. It is not approval, source recovery, source identity finalization, source-of-truth acceptance, live readiness, or final signal readiness.",
        "",
        "## Decision checklist from 18Q",
        mdtable(checklist),
        "",
        "## Required evidence from 18Q",
        mdtable(evidence),
        "",
        "## Manual questions",
        mdtable(manual_questions),
        "",
        "## Actions still blocked",
        mdtable(blocked),
    ]
    wtxt(out / "gold_v2_18r_human_review_packet_markdown.md", "\n".join(markdown))
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "human_review_packet_ready": success,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18q_status": s18q.get("status"),
        "packet_index_items": int(len(packet_index)),
        "manual_decision_questions": int(len(manual_questions)),
        "blocked_actions": int(len(blocked)),
        "total_stop_rows": total_stop,
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
        "next_recommended_step": "18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_18R_OUTPUTS",
    }
    wjson(out / "gold_v2_18r_tier2_source_identity_human_review_packet_summary.json", summary)
    report = [
        "# GOLD V2 18R TIER2 source identity human review packet audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18R formatted a human-review packet only.",
        "- No decision or approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Packet checks",
        mdtable(packet_checks),
        "",
        "## Packet index",
        mdtable(packet_index),
        "",
        "## Manual decision questions",
        mdtable(manual_questions),
        "",
        "## Next gates",
        mdtable(next_gates(success)),
        "",
        "## Safety",
        mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
