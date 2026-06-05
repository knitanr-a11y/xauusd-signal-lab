#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY"
OUT_DIR = "gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_audit_only"
IN19F = "gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_only"
REPORT = "GOLD_V2_19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19F = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_NOTE_PHRASES = [
    "no actual decision",
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
        ["19H", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY", "Prepare a still-unset actual decision template only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19G.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19G.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19g_success"])


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
        ["next_gate_19h_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19G-S001", "required inputs missing", "STOP"],
        ["19G-S002", "19F status not passed", "STOP"],
        ["19G-S003", "decision collected or approval already made", "STOP"],
        ["19G-S004", "upstream STOP rows present", "STOP"],
        ["19G-S005", "handoff note missing required prohibitions", "STOP"],
        ["19G-S006", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def build_note(now: str, s19f: dict[str, Any]) -> str:
    return "\n".join([
        "# GOLD V2 19G final actual human decision intake plan handoff audit-only",
        "",
        f"Created UTC: {now}",
        "",
        "## Handoff purpose",
        "This note hands off the final audit-only actual human decision intake plan to a later template-preparation step.",
        "It is no actual decision and does not approve any action.",
        "",
        "## Current upstream status",
        f"19F status: `{s19f.get('status')}`",
        "",
        "## Required prohibitions retained",
        "- no actual decision",
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
        "19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY",
    ])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19f = base / IN19F
    inputs = {
        "summary_19f": p19f / "gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_summary.json",
        "checks_19f": p19f / "gold_v2_19f_final_checks.csv",
        "evidence_19f": p19f / "gold_v2_19f_evidence_status.csv",
        "blocker_19f": p19f / "gold_v2_19f_blocker_final_status.csv",
        "gates_19f": p19f / "gold_v2_19f_required_next_gates.csv",
        "safety_19f": p19f / "gold_v2_19f_safety_matrix.csv",
        "report_19f": p19f / "GOLD_V2_19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19g_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19G-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19g_handoff_checks.csv", checks)
        write_csv(out / "gold_v2_19g_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19G_STOP_MISSING_INPUTS", "audit_only": True, "handoff_ready": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19G_INPUTS"}
        write_json(out / "gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19G final handoff audit-only report\n\nStatus: `19G_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19f = read_json(inputs["summary_19f"])
    final_checks = read_csv(inputs["checks_19f"])
    evidence = read_csv(inputs["evidence_19f"])
    blocker = read_csv(inputs["blocker_19f"])
    gates19f = read_csv(inputs["gates_19f"])
    safety19f = read_csv(inputs["safety_19f"])
    note = build_note(now, s19f)
    write_text(out / "gold_v2_19g_final_handoff_note.md", note)
    note_lower = note.lower()
    missing_phrases = [p for p in REQUIRED_NOTE_PHRASES if p not in note_lower]
    upstream_stop = stop_count(final_checks) + stop_count(evidence) + stop_count(blocker) + stop_count(safety19f)
    forbidden_gates = forbidden_gate_count(gates19f, "allowed_after_19f_success")
    checks = pd.DataFrame([
        check_row("19G-C001", "19F status", s19f.get("status"), EXPECTED_19F, s19f.get("status") == EXPECTED_19F),
        check_row("19G-C002", "19F final_audit_ready", s19f.get("final_audit_ready"), True, bool(s19f.get("final_audit_ready", False))),
        check_row("19G-C003", "19F total_stop_rows", s19f.get("total_stop_rows"), 0, s19f.get("total_stop_rows") == 0),
        check_row("19G-C004", "19F decision_collected", s19f.get("decision_collected"), False, s19f.get("decision_collected") is False),
        check_row("19G-C005", "19F decision_made", s19f.get("decision_made"), False, s19f.get("decision_made") is False),
        check_row("19G-C006", "19F approval_granted", s19f.get("approval_granted"), False, s19f.get("approval_granted") is False),
        check_row("19G-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19G-C008", "handoff required prohibitions missing", len(missing_phrases), 0, len(missing_phrases) == 0),
        check_row("19G-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19G_STOP_REVIEW_HANDOFF_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19g_handoff_checks.csv", checks)
    write_csv(out / "gold_v2_19g_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19g_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19g_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "handoff_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19f_status": s19f.get("status"),
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
        "next_recommended_step": "19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY" if success else "STOP_REVIEW_19G_OUTPUTS",
    }
    write_json(out / "gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_summary.json", summary)
    report = [
        "# GOLD V2 19G TIER2 source identity human decision intake actual decision plan final handoff audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19G prepared a final audit-only handoff note only.",
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
