#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY"
IN_DIR = "gold_v2_24q_source_recovery_readiness_decision_routing_audit_only"
OUT_DIR = "gold_v2_24r_source_recovery_readiness_plan_audit_only"
EXPECTED_24Q_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_ROUTE = "ROUTE_APPROVE_READINESS_TO_PLAN_AUDIT_ONLY"
EXPECTED_24Q_NEXT = "24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_READINESS_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24R_STOP_SOURCE_RECOVERY_READINESS_PLAN_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24q_source_recovery_readiness_decision_routing_summary.json",
    "input_audit": "gold_v2_24q_input_audit.csv",
    "route": "gold_v2_24q_decision_route.csv",
    "checks": "gold_v2_24q_integrated_checks.csv",
    "gates": "gold_v2_24q_required_next_gates.csv",
    "safety": "gold_v2_24q_safety_matrix.csv",
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


def readiness_plan() -> pd.DataFrame:
    return pd.DataFrame([
        {"plan_id": "24R-P001", "plan_item": "confirm_route_chain", "required": True, "audit_only": True, "description": "Confirm 24P/24Q readiness route chain before any later review."},
        {"plan_id": "24R-P002", "plan_item": "compile_readiness_evidence", "required": True, "audit_only": True, "description": "List required evidence from 24E through 24Q."},
        {"plan_id": "24R-P003", "plan_item": "define_execution_boundary", "required": True, "audit_only": True, "description": "Record that recovery, mutation, finalization, live, and external actions remain blocked."},
        {"plan_id": "24R-P004", "plan_item": "define_next_review_checks", "required": True, "audit_only": True, "description": "Prepare 24S review checks for readiness plan completeness."},
        {"plan_id": "24R-P005", "plan_item": "preserve_old_gold_disc8_quarantine", "required": True, "audit_only": True, "description": "Keep old GOLD/DISC8 quarantine as a hard boundary."},
    ])


def evidence_manifest() -> pd.DataFrame:
    return pd.DataFrame([
        {"evidence_role": "24E artifact list intake", "required_for_24s": True, "notes": "artifact list chain must remain available"},
        {"evidence_role": "24F artifact list review", "required_for_24s": True, "notes": "artifact review chain must remain available"},
        {"evidence_role": "24M no-op dry-run outputs", "required_for_24s": True, "notes": "dry-run observation and blocked action proofs"},
        {"evidence_role": "24N dry-run review", "required_for_24s": True, "notes": "dry-run review passed"},
        {"evidence_role": "24P validated readiness decision", "required_for_24s": True, "notes": "operator-selected readiness value"},
        {"evidence_role": "24Q readiness routing", "required_for_24s": True, "notes": "route to 24R plan"},
    ])


def boundary_matrix() -> pd.DataFrame:
    return pd.DataFrame([{
        "boundary_item": item,
        "allowed_after_24r_plan": False,
        "reason": "24R is readiness-plan-only; still blocked",
        "status": "PASS",
    } for item in BLOCKED_NOW])


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24r_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24R-C000", "required 24Q files exist", inputs_ok, True, inputs_ok)]
    summary24q: dict[str, Any] = {}
    if inputs_ok:
        summary24q = rj(paths["summary"])
        route24q = rc(paths["route"])
        checks24q = rc(paths["checks"])
        gates24q = rc(paths["gates"])
        safety24q = rc(paths["safety"])
        route_id = str(summary24q.get("route_id", ""))
        routed_next = str(summary24q.get("routed_next_audit_step", ""))
        rows += [
            check("24R-C001", "24Q status routed", summary24q.get("status"), EXPECTED_24Q_STATUS, summary24q.get("status") == EXPECTED_24Q_STATUS),
            check("24R-C002", "24Q is routing only", summary24q.get("routing_only"), True, t(summary24q.get("routing_only"))),
            check("24R-C003", "24Q route id approve-readiness", route_id, EXPECTED_ROUTE, route_id == EXPECTED_ROUTE),
            check("24R-C004", "24Q routed next 24R", routed_next, EXPECTED_24Q_NEXT, routed_next == EXPECTED_24Q_NEXT),
            check("24R-C005", "24Q route row passed", route24q.iloc[0].get("status", "") if not route24q.empty else "missing", "ROUTED_TO_NEXT_AUDIT_ONLY", (not route24q.empty and str(route24q.iloc[0].get("status", "")) == "ROUTED_TO_NEXT_AUDIT_ONLY")),
            check("24R-C006", "24Q stop rows zero", stops(checks24q) + stops(safety24q) + stops(route24q), 0, stops(checks24q) + stops(safety24q) + stops(route24q) == 0),
            check("24R-C007", "24Q next only 24R plan", allowed(gates24q, "allowed_after_24q_success"), [EXPECTED_24Q_NEXT], allowed(gates24q, "allowed_after_24q_success") == [EXPECTED_24Q_NEXT]),
            check("24R-C008", "24Q did not allow recovery now", summary24q.get("source_recovery_execution_allowed_now"), False, f(summary24q.get("source_recovery_execution_allowed_now"))),
            check("24R-C009", "24Q did not approve readiness by itself", summary24q.get("source_recovery_readiness_approved_by_24q"), False, f(summary24q.get("source_recovery_readiness_approved_by_24q"))),
            check("24R-C010", "24Q did not allow source mutation", summary24q.get("source_mutation_allowed"), False, f(summary24q.get("source_mutation_allowed"))),
        ]
    checks = pd.DataFrame(rows)
    plan = readiness_plan()
    evidence = evidence_manifest()
    boundary = boundary_matrix()
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "readiness_plan_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_readiness_final_approval_by_24r", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(plan) + stops(evidence) + stops(boundary) + stops(safety)
    ok = inputs_ok and total_stop == 0 and len(plan) >= 5 and len(evidence) >= 6
    gates = pd.DataFrame([
        {"next_step": "24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY", "allowed_after_24r_success": bool(ok), "reason": "readiness plan ready" if ok else "24R not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24r_success": False, "reason": "24R is plan-only"},
        {"next_step": "SOURCE_MUTATION", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24r_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24r_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "readiness_plan_only": True,
        "upstream_24q_status": summary24q.get("status", "UNKNOWN"),
        "upstream_route_id": summary24q.get("route_id", ""),
        "source_recovery_execution_allowed_now": False,
        "source_readiness_final_approval_by_24r": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24r": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24r_success"),
        "next_recommended_step": "24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_24R_INPUTS",
        "do_not_execute_source_recovery_in_24r": True,
    }
    wc(out / "gold_v2_24r_readiness_plan.csv", plan)
    wc(out / "gold_v2_24r_required_evidence_manifest.csv", evidence)
    wc(out / "gold_v2_24r_execution_boundary_matrix.csv", boundary)
    wc(out / "gold_v2_24r_integrated_checks.csv", checks)
    wc(out / "gold_v2_24r_required_next_gates.csv", gates)
    wc(out / "gold_v2_24r_safety_matrix.csv", safety)
    wj(out / "gold_v2_24r_source_recovery_readiness_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24R source recovery readiness plan audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24R writes a readiness plan only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Upstream route id: `{summary['upstream_route_id']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Readiness plan", "", md(plan), "", "## Required evidence manifest", "", md(evidence), "", "## Execution boundary matrix", "", md(boundary), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- final readiness approval by 24R: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
