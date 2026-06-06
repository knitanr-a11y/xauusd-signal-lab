#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY"
IN_DIR = "gold_v2_24s_source_recovery_readiness_plan_review_audit_only"
OUT_DIR = "gold_v2_24t_source_recovery_readiness_final_decision_options_audit_only"
EXPECTED_24S_STATUS = "SOURCE_RECOVERY_READINESS_PLAN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24S_NEXT = "24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24T_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24s_source_recovery_readiness_plan_review_summary.json",
    "input_audit": "gold_v2_24s_input_audit.csv",
    "plan_review": "gold_v2_24s_plan_review.csv",
    "evidence_review": "gold_v2_24s_evidence_manifest_review.csv",
    "boundary_review": "gold_v2_24s_execution_boundary_review.csv",
    "checks": "gold_v2_24s_integrated_checks.csv",
    "gates": "gold_v2_24s_required_next_gates.csv",
    "safety": "gold_v2_24s_safety_matrix.csv",
}

OPTIONS = [
    "KEEP_SOURCE_RECOVERY_READINESS_FINAL_BLOCKED",
    "REQUEST_MORE_READINESS_PLAN_REVIEW",
    "REJECT_SOURCE_RECOVERY_FINAL_READINESS",
    "APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY",
]
BLOCKED_NOW = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "SOURCE_MUTATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_root() -> Path:
    r = root()
    f = r.parents[1] if len(r.parents) >= 2 else r.parent
    return f / "FX_OUTPUTS"


def lp(p: Path) -> Path:
    p = p if p.is_absolute() else p.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def truth(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1", "true", "yes", "pass", "allowed", "ready"}


def falsey(v: Any) -> bool:
    if isinstance(v, bool):
        return not v
    if v is None:
        return True
    return str(v).strip().lower() in {"", "0", "false", "no", "blocked", "none", "null"}


def rj(p: Path) -> dict[str, Any]:
    return json.loads(lp(p).read_text(encoding="utf-8"))


def rc(p: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception:
            pass
    raise RuntimeError(f"csv read failed: {p}")


def wc(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(p), index=False, encoding="utf-8-sig")


def wj(p: Path, obj: dict[str, Any]) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def wt(p: Path, text: str) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(text, encoding="utf-8")


def stops(df: pd.DataFrame) -> int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper() == "STOP").sum())


def md(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def check(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def allowed(g: pd.DataFrame, col: str) -> list[str]:
    if g.empty or "next_step" not in g.columns or col not in g.columns:
        return []
    return g.loc[g[col].map(truth), "next_step"].astype(str).tolist()


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24t_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(truth).all())
    rows = [check("24T-C000", "required 24S files exist", inputs_ok, True, inputs_ok)]
    summary24s: dict[str, Any] = {}
    if inputs_ok:
        summary24s = rj(paths["summary"])
        plan_review = rc(paths["plan_review"])
        evidence_review = rc(paths["evidence_review"])
        boundary_review = rc(paths["boundary_review"])
        checks24s = rc(paths["checks"])
        gates24s = rc(paths["gates"])
        safety24s = rc(paths["safety"])
        rows += [
            check("24T-C001", "24S status passed", summary24s.get("status"), EXPECTED_24S_STATUS, summary24s.get("status") == EXPECTED_24S_STATUS),
            check("24T-C002", "24S is review only", summary24s.get("review_only"), True, truth(summary24s.get("review_only"))),
            check("24T-C003", "24S stop rows zero", stops(checks24s) + stops(safety24s) + stops(plan_review) + stops(evidence_review) + stops(boundary_review), 0, stops(checks24s) + stops(safety24s) + stops(plan_review) + stops(evidence_review) + stops(boundary_review) == 0),
            check("24T-C004", "24S next only 24T", allowed(gates24s, "allowed_after_24s_success"), [EXPECTED_24S_NEXT], allowed(gates24s, "allowed_after_24s_success") == [EXPECTED_24S_NEXT]),
            check("24T-C005", "24S did not allow source action", summary24s.get("source_recovery_execution_allowed_now"), False, falsey(summary24s.get("source_recovery_execution_allowed_now"))),
            check("24T-C006", "24S did not allow mutation", summary24s.get("source_mutation_allowed"), False, falsey(summary24s.get("source_mutation_allowed"))),
        ]
    checks = pd.DataFrame(rows)
    options = pd.DataFrame([{
        "decision_value": value,
        "allowed_for_later_24u_intake": True,
        "source_recovery_execution_allowed_in_24t": False,
        "source_final_readiness_approved_by_24t": False,
    } for value in OPTIONS])
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "decision_options_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_final_readiness_approved_by_24t", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(options) + stops(safety)
    ok = inputs_ok and total_stop == 0 and len(options) == 4
    gates = pd.DataFrame([
        {"next_step": "24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY", "allowed_after_24t_success": bool(ok), "reason": "decision options ready" if ok else "24T not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24t_success": False, "reason": "24T is options-only"},
        {"next_step": "SOURCE_MUTATION", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24t_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24t_success": False, "reason": "blocked"},
    ])
    template = {
        "template_name": "GOLD_V2_24T_SOURCE_RECOVERY_FINAL_READINESS_DECISION_INPUT",
        "created_by_step": STEP,
        "audit_only": True,
        "allowed_decision_values": OPTIONS,
        "selected_decision_value": "",
        "source_recovery_execution_allowed_now": False,
        "source_final_readiness_approved_by_24t": False,
        "still_blocked_after_template_creation": BLOCKED_NOW,
    }
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "decision_options_only": True,
        "upstream_24s_status": summary24s.get("status", "UNKNOWN"),
        "decision_options_rows": int(len(options)),
        "allowed_decision_values": OPTIONS,
        "source_recovery_execution_allowed_now": False,
        "source_final_readiness_approved_by_24t": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24t": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24t_success"),
        "next_recommended_step": "24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY" if ok else "STOP_REVIEW_24T_INPUTS",
        "do_not_execute_source_recovery_in_24t": True,
    }
    wc(out / "gold_v2_24t_decision_options.csv", options)
    wj(out / "gold_v2_24t_human_decision_input_template.json", template)
    wc(out / "gold_v2_24t_integrated_checks.csv", checks)
    wc(out / "gold_v2_24t_required_next_gates.csv", gates)
    wc(out / "gold_v2_24t_safety_matrix.csv", safety)
    wj(out / "gold_v2_24t_source_recovery_readiness_final_decision_options_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24T source recovery readiness final decision options audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24T prepares final readiness decision options only. It does not choose a decision, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Decision option rows: `{summary['decision_options_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Decision options", "", md(options), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- final readiness approved by 24T: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
