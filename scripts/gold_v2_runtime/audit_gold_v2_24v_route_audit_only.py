#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY"
IN_DIR = "gold_v2_24u_source_recovery_readiness_final_decision_intake_audit_only"
OUT_DIR = "gold_v2_24v_source_recovery_readiness_final_decision_routing_audit_only"
EXPECTED_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_VALUE = "APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24V_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_INPUTS_OR_SAFETY"
REQ = {"report": "GOLD_V2_24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md", "summary": "gold_v2_24u_source_recovery_readiness_final_decision_intake_summary.json", "decision_input": "gold_v2_24u_human_decision_input.json", "template": "gold_v2_24u_human_decision_input_template.json", "intake_result": "gold_v2_24u_human_decision_intake_result.csv", "input_audit": "gold_v2_24u_input_audit.csv", "checks": "gold_v2_24u_integrated_checks.csv", "gates": "gold_v2_24u_required_next_gates.csv", "safety": "gold_v2_24u_safety_matrix.csv"}
ROUTES = {"KEEP_SOURCE_RECOVERY_READINESS_FINAL_BLOCKED": ("ROUTE_KEEP_FINAL_BLOCKED", "24W_SOURCE_RECOVERY_FINAL_BLOCKED_STATE_RECORD_AUDIT_ONLY"), "REQUEST_MORE_READINESS_PLAN_REVIEW": ("ROUTE_REQUEST_MORE_PLAN_REVIEW", "24W_SOURCE_RECOVERY_READINESS_MORE_REVIEW_RESOLUTION_AUDIT_ONLY"), "REJECT_SOURCE_RECOVERY_FINAL_READINESS": ("ROUTE_REJECT_FINAL_READINESS", "24W_SOURCE_RECOVERY_READINESS_FINAL_REJECTION_RECORD_AUDIT_ONLY"), "APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY": ("ROUTE_APPROVE_TO_EXECUTION_PLANNING_AUDIT_ONLY", "24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY")}
BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "SOURCE_MUTATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]

def root() -> Path:
    return Path(__file__).resolve().parents[2]

def fx() -> Path:
    r = root(); return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"

def lp(p: Path) -> Path:
    p = p if p.is_absolute() else p.resolve()
    if os.name != "nt": return p
    s = str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)

def yes(v: Any) -> bool:
    if isinstance(v, bool): return v
    if v is None: return False
    return str(v).strip().lower() in {"1", "true", "yes", "pass", "allowed", "ready"}

def no(v: Any) -> bool:
    if isinstance(v, bool): return not v
    if v is None: return True
    return str(v).strip().lower() in {"", "0", "false", "no", "blocked", "none", "null"}

def rj(p: Path) -> dict[str, Any]:
    return json.loads(lp(p).read_text(encoding="utf-8"))

def rc(p: Path) -> pd.DataFrame:
    for e in ("utf-8-sig", "utf-8", "cp932"):
        try: return pd.read_csv(lp(p), encoding=e, keep_default_na=False)
        except Exception: pass
    raise RuntimeError(str(p))

def wc(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")

def wj(p: Path, obj: dict[str, Any]) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def wt(p: Path, s: str) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(s, encoding="utf-8")

def stops(df: pd.DataFrame) -> int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper() == "STOP").sum())

def md(df: pd.DataFrame) -> str:
    if df.empty: return "_No rows._"
    cols = list(df.columns); lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows(): lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)

def chk(i: str, name: str, obs: Any, exp: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": i, "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"}

def alw(g: pd.DataFrame, col: str) -> list[str]:
    if g.empty or "next_step" not in g.columns or col not in g.columns: return []
    return g.loc[g[col].map(yes), "next_step"].astype(str).tolist()

def main() -> int:
    src, out = fx() / IN_DIR, fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    ia = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24v_input_audit.csv", ia)
    ok_inputs = bool(ia["exists"].map(yes).all())
    rows = [chk("24V-C000", "required 24U files exist", ok_inputs, True, ok_inputs)]
    s24u: dict[str, Any] = {}; selected = ""; rid = "UNKNOWN"; nxt = "UNKNOWN"
    if ok_inputs:
        s24u = rj(paths["summary"]); decision_input = rj(paths["decision_input"]); intake = rc(paths["intake_result"]); c24u = rc(paths["checks"]); g24u = rc(paths["gates"]); sf24u = rc(paths["safety"])
        selected = str(s24u.get("selected_decision_value") or decision_input.get("selected_decision_value") or "").strip()
        rid, nxt = ROUTES.get(selected, ("UNKNOWN", "UNKNOWN"))
        rows += [chk("24V-C001", "24U status validated", s24u.get("status"), EXPECTED_STATUS, s24u.get("status") == EXPECTED_STATUS), chk("24V-C002", "24U decision supplied", s24u.get("decision_supplied"), True, yes(s24u.get("decision_supplied"))), chk("24V-C003", "24U decision validated", s24u.get("decision_validated"), True, yes(s24u.get("decision_validated"))), chk("24V-C004", "selected approve planning", selected, EXPECTED_VALUE, selected == EXPECTED_VALUE), chk("24V-C005", "route known", selected, "known route", selected in ROUTES), chk("24V-C006", "24U stop rows zero", stops(c24u)+stops(sf24u)+stops(intake), 0, stops(c24u)+stops(sf24u)+stops(intake) == 0), chk("24V-C007", "24U next only 24V", alw(g24u, "allowed_after_24u_success"), [STEP], alw(g24u, "allowed_after_24u_success") == [STEP]), chk("24V-C008", "24U did not allow now", s24u.get("source_recovery_execution_allowed_now"), False, no(s24u.get("source_recovery_execution_allowed_now"))), chk("24V-C009", "24U did not approve final by itself", s24u.get("source_final_readiness_approved_by_24u"), False, no(s24u.get("source_final_readiness_approved_by_24u"))), chk("24V-C010", "24U did not allow mutation", s24u.get("source_mutation_allowed"), False, no(s24u.get("source_mutation_allowed")))]
    checks = pd.DataFrame(rows)
    route = pd.DataFrame([{"selected_decision_value": selected, "route_id": rid, "routed_next_audit_step": nxt, "route_known": rid != "UNKNOWN", "source_recovery_execution_allowed_in_24v": False, "source_mutation_allowed_in_24v": False, "status": "ROUTED_TO_NEXT_AUDIT_ONLY" if rid != "UNKNOWN" else "STOP"}])
    safety = pd.DataFrame([{"safety_item": x, "observed": o, "expected": e, "status": "PASS"} for x,o,e in [("audit_only", True, True), ("routing_only", True, True), ("source_recovery_execution_allowed_now", False, False), ("source_mutation_allowed", False, False), ("external_actions_allowed", False, False), ("old_gold_disc8_quarantined", True, True)]])
    total_stop = stops(checks) + stops(route) + stops(safety)
    ok = ok_inputs and total_stop == 0
    gates = pd.DataFrame([{"next_step": nxt if ok else "STOP_REVIEW_24V_INPUTS", "allowed_after_24v_success": bool(ok), "reason": "selected route" if ok else "24V not passed"}] + [{"next_step": x, "allowed_after_24v_success": False, "reason": "blocked"} for x in ["SOURCE_RECOVERY", "SOURCE_MUTATION", "SOURCE_IDENTITY_FINALIZATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]])
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": PASS_STATUS if ok else STOP_STATUS, "audit_only": True, "routing_only": True, "upstream_24u_status": s24u.get("status", "UNKNOWN"), "selected_decision_value": selected, "route_id": rid, "routed_next_audit_step": nxt, "source_recovery_execution_allowed_now": False, "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False, "source_mutation_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "old_gold_disc8_quarantined": True, "still_blocked_after_24v": BLOCKED, "total_stop_rows": int(total_stop), "required_next_allowed": alw(gates, "allowed_after_24v_success"), "next_recommended_step": nxt if ok else "STOP_REVIEW_24V_INPUTS", "do_not_execute_source_recovery_in_24v": True}
    wc(out / "gold_v2_24v_decision_route.csv", route); wc(out / "gold_v2_24v_integrated_checks.csv", checks); wc(out / "gold_v2_24v_required_next_gates.csv", gates); wc(out / "gold_v2_24v_safety_matrix.csv", safety); wj(out / "gold_v2_24v_source_recovery_readiness_final_decision_routing_summary.json", summary)
    report = "\n".join(["# GOLD V2 24V source recovery readiness final decision routing audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "", "## Boundary", "", "24V routes a validated readiness value only. It does not choose a value, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "", "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Selected decision: `{selected}`", f"- Route id: `{rid}`", f"- Routed next audit step: `{nxt}`", "", "## Input audit", "", md(ia), "", "## Decision route", "", md(route), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "", "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`"])
    wt(out / "GOLD_V2_24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)); return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
