#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY"
IN_DIR = "gold_v2_24p_source_recovery_readiness_decision_intake_audit_only"
OUT_DIR = "gold_v2_24q_source_recovery_readiness_decision_routing_audit_only"
EXPECTED_24P_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_DECISION = "APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE"
PASS_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24Q_STOP_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24p_source_recovery_readiness_decision_intake_summary.json",
    "decision_input": "gold_v2_24p_human_decision_input.json",
    "intake_result": "gold_v2_24p_human_decision_intake_result.csv",
    "input_audit": "gold_v2_24p_input_audit.csv",
    "checks": "gold_v2_24p_integrated_checks.csv",
    "gates": "gold_v2_24p_required_next_gates.csv",
    "safety": "gold_v2_24p_safety_matrix.csv",
}

ROUTES = {
    "KEEP_SOURCE_RECOVERY_BLOCKED_AFTER_DRY_RUN": ("ROUTE_KEEP_BLOCKED_AFTER_DRY_RUN", "24R_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY"),
    "REQUEST_MORE_DRY_RUN_AUDIT": ("ROUTE_REQUEST_MORE_DRY_RUN_AUDIT", "24R_SOURCE_RECOVERY_REQUEST_MORE_DRY_RUN_AUDIT_RESOLUTION_AUDIT_ONLY"),
    "REJECT_SOURCE_RECOVERY_READINESS": ("ROUTE_REJECT_READINESS", "24R_SOURCE_RECOVERY_READINESS_REJECTION_RECORD_AUDIT_ONLY"),
    "APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE": ("ROUTE_APPROVE_READINESS_TO_PLAN_AUDIT_ONLY", "24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY"),
}
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


def t(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1", "true", "yes", "pass", "allowed", "ready"}


def f(v: Any) -> bool:
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
    return g.loc[g[col].map(t), "next_step"].astype(str).tolist()


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24q_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24Q-C000", "required 24P files exist", inputs_ok, True, inputs_ok)]
    summary24p: dict[str, Any] = {}
    selected = ""
    route_id = "UNKNOWN"
    next_step = "UNKNOWN"
    if inputs_ok:
        summary24p = rj(paths["summary"])
        decision_input = rj(paths["decision_input"])
        intake = rc(paths["intake_result"])
        checks24p = rc(paths["checks"])
        gates24p = rc(paths["gates"])
        safety24p = rc(paths["safety"])
        selected = str(summary24p.get("selected_decision_value") or decision_input.get("selected_decision_value") or "").strip()
        route_id, next_step = ROUTES.get(selected, ("UNKNOWN", "UNKNOWN"))
        rows += [
            check("24Q-C001", "24P status validated", summary24p.get("status"), EXPECTED_24P_STATUS, summary24p.get("status") == EXPECTED_24P_STATUS),
            check("24Q-C002", "24P decision supplied", summary24p.get("decision_supplied"), True, t(summary24p.get("decision_supplied"))),
            check("24Q-C003", "24P decision validated", summary24p.get("decision_validated"), True, t(summary24p.get("decision_validated"))),
            check("24Q-C004", "decision matches approved readiness", selected, EXPECTED_DECISION, selected == EXPECTED_DECISION),
            check("24Q-C005", "decision has route", selected, "known route", selected in ROUTES),
            check("24Q-C006", "24P stop rows zero", stops(checks24p) + stops(safety24p) + stops(intake), 0, stops(checks24p) + stops(safety24p) + stops(intake) == 0),
            check("24Q-C007", "24P next only 24Q", allowed(gates24p, "allowed_after_24p_success"), [STEP], allowed(gates24p, "allowed_after_24p_success") == [STEP]),
            check("24Q-C008", "24P did not allow recovery now", summary24p.get("source_recovery_execution_allowed_now"), False, f(summary24p.get("source_recovery_execution_allowed_now"))),
            check("24Q-C009", "24P did not approve readiness by itself", summary24p.get("source_recovery_readiness_approved_by_24p"), False, f(summary24p.get("source_recovery_readiness_approved_by_24p"))),
            check("24Q-C010", "24P did not allow source mutation", summary24p.get("source_mutation_allowed"), False, f(summary24p.get("source_mutation_allowed"))),
        ]
    checks = pd.DataFrame(rows)
    route = pd.DataFrame([{
        "selected_decision_value": selected,
        "route_id": route_id,
        "routed_next_audit_step": next_step,
        "route_known": route_id != "UNKNOWN",
        "source_recovery_execution_allowed_in_24q": False,
        "source_recovery_readiness_approved_by_24q": False,
        "source_mutation_allowed_in_24q": False,
        "status": "ROUTED_TO_NEXT_AUDIT_ONLY" if route_id != "UNKNOWN" else "STOP",
    }])
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "routing_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_recovery_readiness_approved_by_24q", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(route) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY", "allowed_after_24q_success": bool(ok and next_step == "24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY"), "reason": "selected approve-readiness route" if ok else "24Q not passed"},
        {"next_step": "24R_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY", "allowed_after_24q_success": bool(ok and next_step == "24R_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY"), "reason": "not selected"},
        {"next_step": "24R_SOURCE_RECOVERY_REQUEST_MORE_DRY_RUN_AUDIT_RESOLUTION_AUDIT_ONLY", "allowed_after_24q_success": bool(ok and next_step == "24R_SOURCE_RECOVERY_REQUEST_MORE_DRY_RUN_AUDIT_RESOLUTION_AUDIT_ONLY"), "reason": "not selected"},
        {"next_step": "24R_SOURCE_RECOVERY_READINESS_REJECTION_RECORD_AUDIT_ONLY", "allowed_after_24q_success": bool(ok and next_step == "24R_SOURCE_RECOVERY_READINESS_REJECTION_RECORD_AUDIT_ONLY"), "reason": "not selected"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24q_success": False, "reason": "24Q is routing-only"},
        {"next_step": "SOURCE_MUTATION", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24q_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24q_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "routing_only": True,
        "upstream_24p_status": summary24p.get("status", "UNKNOWN"),
        "selected_decision_value": selected,
        "route_id": route_id,
        "routed_next_audit_step": next_step,
        "source_recovery_execution_allowed_now": False,
        "source_recovery_readiness_approved_by_24q": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24q": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24q_success"),
        "next_recommended_step": next_step if ok else "STOP_REVIEW_24Q_INPUTS",
        "do_not_execute_source_recovery_in_24q": True,
    }
    wc(out / "gold_v2_24q_decision_route.csv", route)
    wc(out / "gold_v2_24q_integrated_checks.csv", checks)
    wc(out / "gold_v2_24q_required_next_gates.csv", gates)
    wc(out / "gold_v2_24q_safety_matrix.csv", safety)
    wj(out / "gold_v2_24q_source_recovery_readiness_decision_routing_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24Q source recovery readiness decision routing audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24Q routes the validated 24P readiness decision only. It does not choose a decision, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Selected decision: `{selected}`", f"- Route id: `{route_id}`", f"- Routed next audit step: `{next_step}`", "",
        "## Input audit", "", md(input_audit), "", "## Decision route", "", md(route), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- readiness approved by 24Q: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
