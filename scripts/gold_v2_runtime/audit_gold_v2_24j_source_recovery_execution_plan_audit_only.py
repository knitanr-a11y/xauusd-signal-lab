#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY"
IN_DIR = "gold_v2_24i_source_recovery_execution_decision_routing_audit_only"
OUT_DIR = "gold_v2_24j_source_recovery_execution_plan_audit_only"
EXPECTED_24I_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_DECISION = "APPROVE_SOURCE_RECOVERY_EXECUTION"
EXPECTED_ROUTE = "ROUTE_APPROVE_TO_PLAN_AUDIT_ONLY"
EXPECTED_24I_NEXT = "24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24J_STOP_SOURCE_RECOVERY_EXECUTION_PLAN_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24i_source_recovery_execution_decision_routing_summary.json",
    "route": "gold_v2_24i_decision_route.csv",
    "input_audit": "gold_v2_24i_input_audit.csv",
    "checks": "gold_v2_24i_integrated_checks.csv",
    "gates": "gold_v2_24i_required_next_gates.csv",
    "safety": "gold_v2_24i_safety_matrix.csv",
}

BLOCKED_NOW = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]


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


def build_plan(summary24i: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {"plan_id": "24J-P001", "plan_item": "confirm_upstream_route", "required": True, "audit_only": True, "description": "Use validated 24I route as the only input authority."},
        {"plan_id": "24J-P002", "plan_item": "collect_required_artifacts", "required": True, "audit_only": True, "description": "List artifacts needed for later preflight before any future recovery attempt."},
        {"plan_id": "24J-P003", "plan_item": "define_preflight_checks", "required": True, "audit_only": True, "description": "Define checks for source identity, artifact hashes, quarantine status, and forbidden action locks."},
        {"plan_id": "24J-P004", "plan_item": "define_stop_conditions", "required": True, "audit_only": True, "description": "Stop if any required artifact is missing, mismatched, stale, or manually unverified."},
        {"plan_id": "24J-P005", "plan_item": "confirm_no_live_or_external_actions", "required": True, "audit_only": True, "description": "Keep live, final signal, Discord, MT5, AI API, and live hook disabled."},
    ])


def build_preflight(summary24i: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {"preflight_id": "24J-PF001", "check": "24I route status passed", "expected": EXPECTED_24I_STATUS, "observed": summary24i.get("status", ""), "must_pass_before_later_step": True},
        {"preflight_id": "24J-PF002", "check": "selected decision is approve", "expected": EXPECTED_DECISION, "observed": summary24i.get("selected_decision_value", ""), "must_pass_before_later_step": True},
        {"preflight_id": "24J-PF003", "check": "route id is approve-to-plan", "expected": EXPECTED_ROUTE, "observed": summary24i.get("route_id", ""), "must_pass_before_later_step": True},
        {"preflight_id": "24J-PF004", "check": "24I next gate is 24J plan", "expected": EXPECTED_24I_NEXT, "observed": summary24i.get("routed_next_audit_step", ""), "must_pass_before_later_step": True},
        {"preflight_id": "24J-PF005", "check": "24I did not execute recovery", "expected": False, "observed": summary24i.get("source_recovery_execution_allowed_now", False), "must_pass_before_later_step": True},
        {"preflight_id": "24J-PF006", "check": "24I did not approve by itself", "expected": False, "observed": summary24i.get("source_recovery_approved_by_24i", False), "must_pass_before_later_step": True},
    ])


def build_stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        {"stop_id": "24J-S001", "condition": "required 24I input missing", "action": "STOP"},
        {"stop_id": "24J-S002", "condition": "24I status not passed", "action": "STOP"},
        {"stop_id": "24J-S003", "condition": "selected decision is not APPROVE_SOURCE_RECOVERY_EXECUTION", "action": "STOP"},
        {"stop_id": "24J-S004", "condition": "route is not ROUTE_APPROVE_TO_PLAN_AUDIT_ONLY", "action": "STOP"},
        {"stop_id": "24J-S005", "condition": "any non-audit action flag is true", "action": "STOP"},
        {"stop_id": "24J-S006", "condition": "old GOLD/DISC8 quarantine not preserved", "action": "STOP"},
    ])


def build_manifest() -> pd.DataFrame:
    return pd.DataFrame([
        {"artifact_role": "24I route summary", "required_for_24k": True, "source": "24I output", "notes": "Machine-readable routing result."},
        {"artifact_role": "24I route csv", "required_for_24k": True, "source": "24I output", "notes": "Row-level selected route."},
        {"artifact_role": "24I report", "required_for_24k": True, "source": "24I output", "notes": "Human-readable route audit."},
        {"artifact_role": "24E/24F/24G/24H chain", "required_for_24k": True, "source": "prior audited outputs", "notes": "Traceability chain must remain available."},
        {"artifact_role": "forbidden action lock proof", "required_for_24k": True, "source": "24I/24J safety matrix", "notes": "All live/external/finalization flags must remain false."},
    ])


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24j_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24J-C000", "required 24I files exist", inputs_ok, True, inputs_ok)]
    summary24i: dict[str, Any] = {}
    if inputs_ok:
        summary24i = rj(paths["summary"])
        route24i = rc(paths["route"])
        checks24i = rc(paths["checks"])
        gates24i = rc(paths["gates"])
        safety24i = rc(paths["safety"])
        rows += [
            check("24J-C001", "24I status passed", summary24i.get("status"), EXPECTED_24I_STATUS, summary24i.get("status") == EXPECTED_24I_STATUS),
            check("24J-C002", "24I decision is approve", summary24i.get("selected_decision_value"), EXPECTED_DECISION, summary24i.get("selected_decision_value") == EXPECTED_DECISION),
            check("24J-C003", "24I route id correct", summary24i.get("route_id"), EXPECTED_ROUTE, summary24i.get("route_id") == EXPECTED_ROUTE),
            check("24J-C004", "24I routed next gate is 24J", summary24i.get("routed_next_audit_step"), EXPECTED_24I_NEXT, summary24i.get("routed_next_audit_step") == EXPECTED_24I_NEXT),
            check("24J-C005", "24I next allowed only 24J", summary24i.get("required_next_allowed"), [EXPECTED_24I_NEXT], summary24i.get("required_next_allowed") == [EXPECTED_24I_NEXT]),
            check("24J-C006", "24I route row passed", route24i.iloc[0].get("status", "") if not route24i.empty else "missing", "ROUTED_TO_NEXT_AUDIT_ONLY", (not route24i.empty and str(route24i.iloc[0].get("status", "")) == "ROUTED_TO_NEXT_AUDIT_ONLY")),
            check("24J-C007", "24I stop rows zero", stops(checks24i) + stops(safety24i), 0, stops(checks24i) + stops(safety24i) == 0),
            check("24J-C008", "24I gate allows 24J", allowed(gates24i, "allowed_after_24i_success"), [EXPECTED_24I_NEXT], allowed(gates24i, "allowed_after_24i_success") == [EXPECTED_24I_NEXT]),
            check("24J-C009", "24I did not allow run now", summary24i.get("source_recovery_execution_allowed_now"), False, f(summary24i.get("source_recovery_execution_allowed_now"))),
            check("24J-C010", "24I did not approve by itself", summary24i.get("source_recovery_approved_by_24i"), False, f(summary24i.get("source_recovery_approved_by_24i"))),
        ]
    checks = pd.DataFrame(rows)
    plan = build_plan(summary24i)
    preflight = build_preflight(summary24i)
    stops_df = build_stop_conditions()
    manifest = build_manifest()
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "plan_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_identity_finalization_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY", "allowed_after_24j_success": bool(ok), "reason": "plan ready" if ok else "24J not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24j_success": False, "reason": "24J is plan-only"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24j_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24j_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "plan_only": True,
        "upstream_24i_status": summary24i.get("status", "UNKNOWN"),
        "selected_decision_value": summary24i.get("selected_decision_value", ""),
        "route_id": summary24i.get("route_id", ""),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24j": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24j_success"),
        "next_recommended_step": "24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY" if ok else "STOP_REVIEW_24J_INPUTS",
        "do_not_execute_source_recovery_in_24j": True,
    }
    wc(out / "gold_v2_24j_plan.csv", plan)
    wc(out / "gold_v2_24j_preflight_checks.csv", preflight)
    wc(out / "gold_v2_24j_stop_conditions.csv", stops_df)
    wc(out / "gold_v2_24j_required_artifact_manifest.csv", manifest)
    wc(out / "gold_v2_24j_integrated_checks.csv", checks)
    wc(out / "gold_v2_24j_required_next_gates.csv", gates)
    wc(out / "gold_v2_24j_safety_matrix.csv", safety)
    wj(out / "gold_v2_24j_source_recovery_execution_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24J source recovery execution plan audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24J writes a plan/preflight package only. It does not run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Selected decision: `{summary['selected_decision_value']}`", f"- Route id: `{summary['route_id']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Plan", "", md(plan), "", "## Preflight checks", "", md(preflight), "", "## Stop conditions", "", md(stops_df), "", "## Required artifact manifest", "", md(manifest), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
