#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY"
OUT_DIR = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18P = "TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
REQUIRED_EVIDENCE_STEPS = ["18K", "18L", "18M", "18N", "18O"]
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
        ["decision_planning_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"],
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
        ["next_gate_18r_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18R", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY", "Format human review packet for manual review; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18Q.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18Q.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18q_success"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18Q-S001", "required inputs missing", "STOP"],
        ["18Q-S002", "18P status not passed", "STOP"],
        ["18Q-S003", "any upstream STOP row present", "STOP"],
        ["18Q-S004", "evidence manifest incomplete", "STOP"],
        ["18Q-S005", "human review blocking items missing", "STOP"],
        ["18Q-S006", "forbidden gate allowed", "STOP"],
        ["18Q-S007", "forbidden safety flag true", "STOP"],
        ["18Q-S008", "decision or approval made by script", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18p = fx() / IN18P
    p18o = fx() / IN18O
    p18n = fx() / IN18N
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18p": p18p / "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json",
        "input_audit_18p": p18p / "gold_v2_18p_input_audit.csv",
        "readiness_checks_18p": p18p / "gold_v2_18p_readiness_checks.csv",
        "evidence_manifest_18p": p18p / "gold_v2_18p_evidence_manifest.csv",
        "open_blockers_18p": p18p / "gold_v2_18p_open_blockers_for_human_review.csv",
        "human_review_packet_18p": p18p / "gold_v2_18p_human_review_packet.csv",
        "next_gates_18p": p18p / "gold_v2_18p_required_next_gates.csv",
        "safety_18p": p18p / "gold_v2_18p_safety_matrix.csv",
        "report_18p": p18p / "GOLD_V2_18P_TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md",
        "summary_18o": p18o / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json",
        "summary_18n": p18n / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json",
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18q_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18Q_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18Q-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18q_planning_checks.csv")
        wcsv(safety(False), out / "gold_v2_18q_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "decision_planning_ready": False, "next_recommended_step": "STOP_REVIEW_18Q_INPUTS"}
        wjson(out / "gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18Q TIER2 source identity human review decision planning audit-only report\n\nStatus: `18Q_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18p = rjson(inputs["summary_18p"])
    summaries = {
        "18K": rjson(inputs["summary_18k"]),
        "18L": rjson(inputs["summary_18l"]),
        "18M": rjson(inputs["summary_18m"]),
        "18N": rjson(inputs["summary_18n"]),
        "18O": rjson(inputs["summary_18o"]),
        "18P": s18p,
    }
    readiness = rcsv(inputs["readiness_checks_18p"])
    evidence = rcsv(inputs["evidence_manifest_18p"])
    blockers = rcsv(inputs["open_blockers_18p"])
    packet = rcsv(inputs["human_review_packet_18p"])
    gates = rcsv(inputs["next_gates_18p"])
    safe18p = rcsv(inputs["safety_18p"])
    _ = lp(inputs["report_18p"]).read_text(encoding="utf-8")

    evidence_steps = set(evidence["step"].astype(str)) if "step" in evidence.columns else set()
    missing_evidence = [s for s in REQUIRED_EVIDENCE_STEPS if s not in evidence_steps]
    blocking_items = 0
    if "scope" in packet.columns:
        blocking_items = int((packet["scope"].astype(str) == "BLOCKING").sum())
    gates_forbidden_true = 999
    if {"next_step", "allowed_after_18p_success"}.issubset(gates.columns):
        forbidden = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
        gates_forbidden_true = int(forbidden["allowed_after_18p_success"].map(truthy).sum())
    forbidden_summary_total = sum(forbidden_summary_true(v) for v in summaries.values())
    upstream_stop = stop_count(readiness) + stop_count(safe18p)
    planning_checks = pd.DataFrame([
        ck("18Q-C001", "18P status", s18p.get("status"), EXPECTED_18P, s18p.get("status") == EXPECTED_18P),
        ck("18Q-C002", "18P readiness_package_prepared", s18p.get("readiness_package_prepared"), True, bool(s18p.get("readiness_package_prepared", False))),
        ck("18Q-C003", "18P total_stop_rows", s18p.get("total_stop_rows"), 0, s18p.get("total_stop_rows") == 0),
        ck("18Q-C004", "18P upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18Q-C005", "missing evidence steps", len(missing_evidence), 0, len(missing_evidence) == 0),
        ck("18Q-C006", "open blockers present", len(blockers), ">=1", len(blockers) >= 1),
        ck("18Q-C007", "blocking packet items", blocking_items, ">=3", blocking_items >= 3),
        ck("18Q-C008", "forbidden gates allowed", gates_forbidden_true, 0, gates_forbidden_true == 0),
        ck("18Q-C009", "forbidden summary flags true across 18K-18P", forbidden_summary_total, 0, forbidden_summary_total == 0),
    ])
    decision_checklist = pd.DataFrame([
        ["DC-001", "Confirm 18K-18P evidence package was reviewed", "HUMAN", "REQUIRED", "NO_DECISION_BY_SCRIPT"],
        ["DC-002", "Confirm dry-run candidate identity ledger remains not source-of-truth", "HUMAN", "BLOCKING", "NO_DECISION_BY_SCRIPT"],
        ["DC-003", "Confirm source recovery execution remains blocked", "HUMAN", "BLOCKING", "NO_DECISION_BY_SCRIPT"],
        ["DC-004", "Confirm source identity finalization remains blocked", "HUMAN", "BLOCKING", "NO_DECISION_BY_SCRIPT"],
        ["DC-005", "Confirm live/final evaluator and final signal remain blocked", "HUMAN", "BLOCKING", "NO_DECISION_BY_SCRIPT"],
        ["DC-006", "Confirm Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain blocked", "HUMAN", "BLOCKING", "NO_DECISION_BY_SCRIPT"],
        ["DC-007", "List additional evidence required before any future finalization planning", "HUMAN", "PLANNING_ONLY", "NO_DECISION_BY_SCRIPT"],
    ], columns=["decision_item_id", "decision_item", "owner", "importance", "script_decision_status"])
    required_evidence = evidence.copy()
    if not required_evidence.empty:
        required_evidence["required_for_human_decision"] = True
        required_evidence["script_accepts_as_source_of_truth"] = False
    blocked_actions = pd.DataFrame([
        ["SOURCE_RECOVERY", "BLOCKED", "Requires later explicit human approval; not granted by 18Q"],
        ["SOURCE_IDENTITY_FINALIZATION", "BLOCKED", "Requires later explicit human approval; not granted by 18Q"],
        ["SOURCE_IDENTITY_RECOVERED", "BLOCKED", "Must remain false"],
        ["OHLC_REPLAY_RECONSTRUCTION", "BLOCKED", "Still not allowed"],
        ["LIVE_EVALUATOR", "BLOCKED", "Still not allowed"],
        ["FINAL_SIGNAL", "BLOCKED", "Still not allowed"],
        ["DISCORD_SEND", "BLOCKED", "Still not allowed"],
        ["NO_SIGNAL_DISCORD_SEND", "BLOCKED", "Still not allowed"],
        ["MT5_ORDER", "BLOCKED", "Still not allowed"],
        ["AI_API", "BLOCKED", "Still not allowed"],
        ["LIVE_HOOK", "BLOCKED", "Still not allowed"],
    ], columns=["action", "status", "reason"])
    total_stop = stop_count(planning_checks)
    success = total_stop == 0
    status = SUCCESS if success else "18Q_STOP_REVIEW_DECISION_PLANNING_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18q_planning_checks.csv", planning_checks),
        ("gold_v2_18q_decision_checklist.csv", decision_checklist),
        ("gold_v2_18q_required_evidence_for_decision.csv", required_evidence),
        ("gold_v2_18q_actions_still_blocked.csv", blocked_actions),
        ("gold_v2_18q_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18q_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18q_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "decision_planning_ready": success,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18p_status": s18p.get("status"),
        "decision_checklist_items": int(len(decision_checklist)),
        "required_evidence_items": int(len(required_evidence)),
        "blocked_actions": int(len(blocked_actions)),
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
        "next_recommended_step": "18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY" if success else "STOP_REVIEW_18Q_OUTPUTS",
    }
    wjson(out / "gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json", summary)
    report = [
        "# GOLD V2 18Q TIER2 source identity human review decision planning audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18Q prepared a human-review decision checklist only.",
        "- No decision or approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Planning checks",
        mdtable(planning_checks),
        "",
        "## Decision checklist",
        mdtable(decision_checklist),
        "",
        "## Required evidence for decision",
        mdtable(required_evidence),
        "",
        "## Actions still blocked",
        mdtable(blocked_actions),
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
