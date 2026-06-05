#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AI_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_audit_only"
IN18AH = "gold_v2_18ah_tier2_source_identity_human_decision_intake_readiness_package_final_audit_only"
REPORT = "GOLD_V2_18AI_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AH = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_PHRASES = [
    "no approval",
    "no source recovery",
    "no source identity finalization",
    "no live enablement",
    "no final signal",
    "no discord send",
    "no mt5 order",
    "no ai api",
    "no live hook",
    "no no_signal discord",
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


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["19A", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY", "Plan a later actual human decision intake process only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AI.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AI.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18ai_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["handoff_note_only", True, True, "PASS"],
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
        ["next_gate_19a_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AI-S001", "required inputs missing", "STOP"],
        ["18AI-S002", "18AH status not passed", "STOP"],
        ["18AI-S003", "decision collected or approval already made", "STOP"],
        ["18AI-S004", "upstream STOP rows present", "STOP"],
        ["18AI-S005", "handoff note missing required prohibitions", "STOP"],
        ["18AI-S006", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def build_handoff_note(now: str, s18ah: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 18AI final handoff note audit-only",
        "",
        f"Created UTC: {now}",
        "",
        "## Handoff purpose",
        "This note hands off the audit-only readiness package for a later explicit human decision-intake planning step.",
        "It does not collect a decision and does not approve any action.",
        "",
        "## Current upstream status",
        f"18AH status: `{s18ah.get('status')}`",
        "",
        "## Required prohibitions retained",
        "- no approval",
        "- no source recovery",
        "- no source identity finalization",
        "- no live enablement",
        "- no final signal",
        "- no discord send",
        "- no mt5 order",
        "- no ai api",
        "- no live hook",
        "- no no_signal discord",
        "",
        "## Next allowed audit-only step",
        "19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY",
    ])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ah = base / IN18AH
    inputs = {
        "summary_18ah": p18ah / "gold_v2_18ah_tier2_source_identity_human_decision_intake_readiness_package_final_audit_summary.json",
        "final_checks_18ah": p18ah / "gold_v2_18ah_final_checks.csv",
        "evidence_18ah": p18ah / "gold_v2_18ah_evidence_status.csv",
        "blocker_18ah": p18ah / "gold_v2_18ah_blocker_final_status.csv",
        "gates_18ah": p18ah / "gold_v2_18ah_required_next_gates.csv",
        "safety_18ah": p18ah / "gold_v2_18ah_safety_matrix.csv",
        "report_18ah": p18ah / "GOLD_V2_18AH_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_18ai_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AI-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18ai_handoff_checks.csv", checks)
        write_csv(out / "gold_v2_18ai_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "18AI_STOP_MISSING_INPUTS", "audit_only": True, "handoff_ready": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_18AI_INPUTS"}
        write_json(out / "gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AI final handoff audit-only report\n\nStatus: `18AI_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ah = read_json(inputs["summary_18ah"])
    final_checks = read_csv(inputs["final_checks_18ah"])
    evidence = read_csv(inputs["evidence_18ah"])
    blocker = read_csv(inputs["blocker_18ah"])
    gates18ah = read_csv(inputs["gates_18ah"])
    safety18ah = read_csv(inputs["safety_18ah"])
    note = build_handoff_note(now, s18ah)
    write_text(out / "gold_v2_18ai_handoff_note.md", note)
    note_lower = note.lower()
    missing_phrases = [p for p in FORBIDDEN_PHRASES if p not in note_lower]
    upstream_stop = stop_count(final_checks) + stop_count(evidence) + stop_count(blocker) + stop_count(safety18ah)
    forbidden_gates = forbidden_gate_count(gates18ah, "allowed_after_18ah_success")
    checks = pd.DataFrame([
        check_row("18AI-C001", "18AH status", s18ah.get("status"), EXPECTED_18AH, s18ah.get("status") == EXPECTED_18AH),
        check_row("18AI-C002", "18AH final_audit_ready", s18ah.get("final_audit_ready"), True, bool(s18ah.get("final_audit_ready", False))),
        check_row("18AI-C003", "18AH total_stop_rows", s18ah.get("total_stop_rows"), 0, s18ah.get("total_stop_rows") == 0),
        check_row("18AI-C004", "18AH decision_collected", s18ah.get("decision_collected"), False, s18ah.get("decision_collected") is False),
        check_row("18AI-C005", "18AH decision_made", s18ah.get("decision_made"), False, s18ah.get("decision_made") is False),
        check_row("18AI-C006", "18AH approval_granted", s18ah.get("approval_granted"), False, s18ah.get("approval_granted") is False),
        check_row("18AI-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("18AI-C008", "handoff required prohibitions missing", len(missing_phrases), 0, len(missing_phrases) == 0),
        check_row("18AI-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AI_STOP_REVIEW_HANDOFF_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18ai_handoff_checks.csv", checks)
    write_csv(out / "gold_v2_18ai_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18ai_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18ai_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "handoff_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ah_status": s18ah.get("status"),
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
        "next_recommended_step": "19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY" if success else "STOP_REVIEW_18AI_OUTPUTS",
    }
    write_json(out / "gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_summary.json", summary)
    report = [
        "# GOLD V2 18AI TIER2 source identity human decision intake final handoff audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AI prepared a final handoff note only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Handoff checks",
        md_table(checks),
        "",
        "## Handoff note",
        note,
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
