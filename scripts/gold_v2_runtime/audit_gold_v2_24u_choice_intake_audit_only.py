#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY"
IN_DIR = "gold_v2_24t_source_recovery_readiness_final_decision_options_audit_only"
OUT_DIR = "gold_v2_24u_source_recovery_readiness_final_decision_intake_audit_only"
EXPECTED_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
WAIT_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
VALID_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24U_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_INPUTS_OR_SAFETY"
REQ = {
    "report": "GOLD_V2_24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24t_source_recovery_readiness_final_decision_options_summary.json",
    "input_audit": "gold_v2_24t_input_audit.csv",
    "options": "gold_v2_24t_decision_options.csv",
    "template": "gold_v2_24t_human_decision_input_template.json",
    "checks": "gold_v2_24t_integrated_checks.csv",
    "gates": "gold_v2_24t_required_next_gates.csv",
    "safety": "gold_v2_24t_safety_matrix.csv",
}
BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "SOURCE_MUTATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
BAD_TRUE = ["source_recovery_execution_allowed_now", "source_final_readiness_approved_by_24u", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "source_mutation_allowed", "live_enabled", "final_signal_allowed", "discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]

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
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows(): lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)

def chk(i: str, name: str, obs: Any, exp: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": i, "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"}

def alw(g: pd.DataFrame, col: str) -> list[str]:
    if g.empty or "next_step" not in g.columns or col not in g.columns: return []
    return g.loc[g[col].map(yes), "next_step"].astype(str).tolist()

def bad_count(o: dict[str, Any]) -> int:
    return sum(1 for k in BAD_TRUE if yes(o.get(k, False)))

def main() -> int:
    src, out = fx() / IN_DIR, fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    opt_input = out / "gold_v2_24u_human_decision_input.json"
    ia = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()] + [{"role": "24u_optional_human_decision_input", "path": str(opt_input), "required": False, "exists": lp(opt_input).exists()}])
    wc(out / "gold_v2_24u_input_audit.csv", ia)
    req_ok = bool(ia[ia["required"].map(yes)]["exists"].map(yes).all())
    rows = [chk("24U-C000", "required 24T files exist", req_ok, True, req_ok)]
    s24t: dict[str, Any] = {}; vals: list[str] = []
    if req_ok:
        s24t = rj(paths["summary"]); opt = rc(paths["options"]); c24t = rc(paths["checks"]); g24t = rc(paths["gates"]); sf24t = rc(paths["safety"])
        vals = opt["decision_value"].astype(str).tolist() if "decision_value" in opt.columns else []
        rows += [
            chk("24U-C001", "24T status ready", s24t.get("status"), EXPECTED_STATUS, s24t.get("status") == EXPECTED_STATUS),
            chk("24U-C002", "24T options only", s24t.get("decision_options_only"), True, yes(s24t.get("decision_options_only"))),
            chk("24U-C003", "option rows four", len(vals), 4, len(vals) == 4),
            chk("24U-C004", "24T stop rows zero", stops(c24t) + stops(sf24t), 0, stops(c24t) + stops(sf24t) == 0),
            chk("24U-C005", "24T next only 24U", alw(g24t, "allowed_after_24t_success"), [STEP], alw(g24t, "allowed_after_24t_success") == [STEP]),
            chk("24U-C006", "24T did not allow now", s24t.get("source_recovery_execution_allowed_now"), False, no(s24t.get("source_recovery_execution_allowed_now"))),
        ]
    wj(out / "gold_v2_24u_human_decision_input_template.json", {"template_name": "GOLD_V2_24U_SOURCE_RECOVERY_FINAL_READINESS_DECISION_INPUT", "created_by_step": STEP, "audit_only": True, "allowed_decision_values": vals, "selected_decision_value": "", "source_recovery_execution_allowed_now": False, "source_final_readiness_approved_by_24u": False, "still_blocked_after_template_creation": BLOCKED})
    if lp(opt_input).exists():
        obj = rj(opt_input); selected = str(obj.get("selected_decision_value", "")).strip(); supplied = bool(selected); value_ok = selected in vals; bc = bad_count(obj); valid = supplied and value_ok and bc == 0
        result = pd.DataFrame([{"selected_decision_value": selected, "decision_supplied": supplied, "decision_value_allowed": value_ok, "forbidden_flags_true_count": bc, "routes_to_later_audit": valid, "source_recovery_execution_allowed_now": False, "source_final_readiness_approved_by_24u": False, "status": "VALID_24U_DECISION_VALUE_FOR_ROUTING_AUDIT_ONLY" if valid else "STOP", "notes": "validated for later routing only" if valid else "invalid or unsafe input"}])
    else:
        selected = ""; supplied = False; valid = False; bc = 0
        result = pd.DataFrame([{"selected_decision_value": "", "decision_supplied": False, "decision_value_allowed": False, "forbidden_flags_true_count": 0, "routes_to_later_audit": False, "source_recovery_execution_allowed_now": False, "source_final_readiness_approved_by_24u": False, "status": "WAIT_FOR_24U_HUMAN_DECISION_INPUT", "notes": "No optional human decision input supplied."}])
    wc(out / "gold_v2_24u_human_decision_intake_result.csv", result)
    checks = pd.DataFrame(rows)
    safety = pd.DataFrame([{"safety_item": x, "observed": o, "expected": e, "status": "PASS"} for x, o, e in [("audit_only", True, True), ("decision_intake_only", True, True), ("source_recovery_execution_allowed_now", False, False), ("source_final_readiness_approved_by_24u", False, False), ("source_mutation_allowed", False, False), ("external_actions_allowed", False, False), ("old_gold_disc8_quarantined", True, True)]])
    total_stop = stops(checks) + stops(result) + stops(safety); ok_base = req_ok and stops(checks) == 0 and stops(safety) == 0
    status = VALID_STATUS if ok_base and valid else WAIT_STATUS if ok_base and not supplied else STOP_STATUS
    gates = pd.DataFrame([{"next_step": "WAIT_FOR_24U_HUMAN_DECISION_INPUT", "allowed_after_24u_success": bool(ok_base and not supplied), "reason": "decision not supplied" if ok_base and not supplied else "not waiting"}, {"next_step": "24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY", "allowed_after_24u_success": bool(ok_base and valid), "reason": "decision validated" if ok_base and valid else "decision not validated"}] + [{"next_step": x, "allowed_after_24u_success": False, "reason": "blocked"} for x in ["SOURCE_RECOVERY", "SOURCE_MUTATION", "SOURCE_IDENTITY_FINALIZATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]])
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "decision_intake_only": True, "upstream_24t_status": s24t.get("status", "UNKNOWN"), "allowed_decision_values": vals, "decision_supplied": supplied, "decision_validated": valid, "selected_decision_value": selected, "forbidden_flags_true_count": int(bc), "source_recovery_execution_allowed_now": False, "source_final_readiness_approved_by_24u": False, "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False, "source_mutation_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "old_gold_disc8_quarantined": True, "still_blocked_after_24u": BLOCKED, "total_stop_rows": int(total_stop), "required_next_allowed": alw(gates, "allowed_after_24u_success"), "next_recommended_step": "24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY" if valid and ok_base else "WAIT_FOR_24U_HUMAN_DECISION_INPUT" if ok_base and not supplied else "STOP_REVIEW_24U_INPUTS", "do_not_execute_source_recovery_in_24u": True}
    wc(out / "gold_v2_24u_integrated_checks.csv", checks); wc(out / "gold_v2_24u_required_next_gates.csv", gates); wc(out / "gold_v2_24u_safety_matrix.csv", safety); wj(out / "gold_v2_24u_source_recovery_readiness_final_decision_intake_summary.json", summary)
    report = "\n".join(["# GOLD V2 24U source recovery readiness final decision intake audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "", "## Boundary", "", "24U intakes one optional human readiness value only. It does not choose a value, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "", "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Decision supplied: `{summary['decision_supplied']}`", f"- Decision validated: `{summary['decision_validated']}`", f"- Selected decision value: `{summary['selected_decision_value']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "", "## Input audit", "", md(ia), "", "## Human decision intake result", "", md(result), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "", "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- final readiness approved by 24U: `false`", "- live/final signal/external actions: `false`"])
    wt(out / "GOLD_V2_24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)); return 0 if ok_base else 2

if __name__ == "__main__":
    raise SystemExit(main())
