#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY"
IN_DIR = "gold_v2_24r_source_recovery_readiness_plan_audit_only"
OUT_DIR = "gold_v2_24s_source_recovery_readiness_plan_review_audit_only"
EXPECTED_24R_STATUS = "SOURCE_RECOVERY_READINESS_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24R_NEXT = "24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_READINESS_PLAN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24S_STOP_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24r_source_recovery_readiness_plan_summary.json",
    "input_audit": "gold_v2_24r_input_audit.csv",
    "plan": "gold_v2_24r_readiness_plan.csv",
    "evidence": "gold_v2_24r_required_evidence_manifest.csv",
    "boundary": "gold_v2_24r_execution_boundary_matrix.csv",
    "checks": "gold_v2_24r_integrated_checks.csv",
    "gates": "gold_v2_24r_required_next_gates.csv",
    "safety": "gold_v2_24r_safety_matrix.csv",
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


def review_plan(plan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if plan.empty:
        return pd.DataFrame([{"plan_id": "missing", "review": "plan file empty", "required": True, "audit_only": False, "status": "STOP"}])
    for _, row in plan.iterrows():
        req = t(row.get("required", False))
        audit_only = t(row.get("audit_only", False))
        rows.append({"plan_id": row.get("plan_id", ""), "plan_item": row.get("plan_item", ""), "required": req, "audit_only": audit_only, "status": "PASS" if req and audit_only else "STOP"})
    return pd.DataFrame(rows)


def review_evidence(evidence: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if evidence.empty:
        return pd.DataFrame([{"evidence_role": "missing", "required_for_24s": True, "status": "STOP", "notes": "evidence manifest empty"}])
    for _, row in evidence.iterrows():
        required = t(row.get("required_for_24s", False))
        role = str(row.get("evidence_role", "")).strip()
        rows.append({"evidence_role": role, "required_for_24s": required, "status": "PASS" if required and role else "STOP", "notes": row.get("notes", "")})
    return pd.DataFrame(rows)


def review_boundary(boundary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if boundary.empty:
        return pd.DataFrame([{"boundary_item": "missing", "allowed_after_24r_plan": True, "status": "STOP", "notes": "boundary matrix empty"}])
    for _, row in boundary.iterrows():
        item = str(row.get("boundary_item", "")).strip()
        allowed_now = t(row.get("allowed_after_24r_plan", True))
        source_status = str(row.get("status", ""))
        ok = item in BLOCKED_NOW and (not allowed_now) and source_status == "PASS"
        rows.append({"boundary_item": item, "allowed_after_24r_plan": allowed_now, "source_status": source_status, "status": "PASS" if ok else "STOP"})
    return pd.DataFrame(rows)


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24s_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24S-C000", "required 24R files exist", inputs_ok, True, inputs_ok)]
    summary24r: dict[str, Any] = {}
    if inputs_ok:
        summary24r = rj(paths["summary"])
        plan = rc(paths["plan"])
        evidence = rc(paths["evidence"])
        boundary = rc(paths["boundary"])
        checks24r = rc(paths["checks"])
        gates24r = rc(paths["gates"])
        safety24r = rc(paths["safety"])
        rows += [
            check("24S-C001", "24R status ready", summary24r.get("status"), EXPECTED_24R_STATUS, summary24r.get("status") == EXPECTED_24R_STATUS),
            check("24S-C002", "24R is readiness plan only", summary24r.get("readiness_plan_only"), True, t(summary24r.get("readiness_plan_only"))),
            check("24S-C003", "24R stop rows zero", stops(checks24r) + stops(safety24r), 0, stops(checks24r) + stops(safety24r) == 0),
            check("24S-C004", "24R next only 24S", allowed(gates24r, "allowed_after_24r_success"), [EXPECTED_24R_NEXT], allowed(gates24r, "allowed_after_24r_success") == [EXPECTED_24R_NEXT]),
            check("24S-C005", "24R did not allow recovery now", summary24r.get("source_recovery_execution_allowed_now"), False, f(summary24r.get("source_recovery_execution_allowed_now"))),
            check("24S-C006", "24R did not grant final readiness", summary24r.get("source_readiness_final_approval_by_24r"), False, f(summary24r.get("source_readiness_final_approval_by_24r"))),
            check("24S-C007", "24R did not allow source mutation", summary24r.get("source_mutation_allowed"), False, f(summary24r.get("source_mutation_allowed"))),
        ]
    else:
        plan = evidence = boundary = pd.DataFrame()
    checks = pd.DataFrame(rows)
    plan_review = review_plan(plan)
    evidence_review = review_evidence(evidence)
    boundary_review = review_boundary(boundary)
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "review_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_readiness_final_approval_by_24s", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(plan_review) + stops(evidence_review) + stops(boundary_review) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY", "allowed_after_24s_success": bool(ok), "reason": "readiness plan review passed" if ok else "24S not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24s_success": False, "reason": "24S is review-only"},
        {"next_step": "SOURCE_MUTATION", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24s_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24s_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "review_only": True,
        "upstream_24r_status": summary24r.get("status", "UNKNOWN"),
        "source_recovery_execution_allowed_now": False,
        "source_readiness_final_approval_by_24s": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24s": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24s_success"),
        "next_recommended_step": "24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY" if ok else "STOP_REVIEW_24S_INPUTS",
        "do_not_execute_source_recovery_in_24s": True,
    }
    wc(out / "gold_v2_24s_plan_review.csv", plan_review)
    wc(out / "gold_v2_24s_evidence_manifest_review.csv", evidence_review)
    wc(out / "gold_v2_24s_execution_boundary_review.csv", boundary_review)
    wc(out / "gold_v2_24s_integrated_checks.csv", checks)
    wc(out / "gold_v2_24s_required_next_gates.csv", gates)
    wc(out / "gold_v2_24s_safety_matrix.csv", safety)
    wj(out / "gold_v2_24s_source_recovery_readiness_plan_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24S source recovery readiness plan review audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24S reviews the 24R readiness plan only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Plan review", "", md(plan_review), "", "## Evidence manifest review", "", md(evidence_review), "", "## Execution boundary review", "", md(boundary_review), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- final readiness approval by 24S: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
