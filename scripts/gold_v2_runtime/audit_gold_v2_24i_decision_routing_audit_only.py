#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY"
IN_DIR = "gold_v2_24h_source_recovery_execution_decision_intake_audit_only"
OUT_DIR = "gold_v2_24i_source_recovery_execution_decision_routing_audit_only"
EXPECTED_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24I_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_INPUTS_OR_SAFETY"

REQ = {
    "summary": "gold_v2_24h_source_recovery_execution_decision_intake_summary.json",
    "decision_input": "gold_v2_24h_human_decision_input.json",
    "intake_result": "gold_v2_24h_human_decision_intake_result.csv",
    "checks": "gold_v2_24h_integrated_checks.csv",
    "gates": "gold_v2_24h_required_next_gates.csv",
    "safety": "gold_v2_24h_safety_matrix.csv",
    "report": "GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY_REPORT.md",
}

ROUTES = {
    "KEEP_SOURCE_RECOVERY_BLOCKED": ("ROUTE_KEEP_BLOCKED", "24J_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY"),
    "REQUEST_MORE_SOURCE_RECOVERY_AUDIT": ("ROUTE_REQUEST_MORE_AUDIT", "24J_SOURCE_RECOVERY_REQUEST_MORE_AUDIT_RESOLUTION_AUDIT_ONLY"),
    "REJECT_SOURCE_RECOVERY_EXECUTION": ("ROUTE_REJECT_EXECUTION", "24J_SOURCE_RECOVERY_REJECTION_RECORD_AUDIT_ONLY"),
    "APPROVE_SOURCE_RECOVERY_EXECUTION": ("ROUTE_APPROVE_TO_PLAN_AUDIT_ONLY", "24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY"),
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


def wj(p: Path, obj: dict[str, Any]) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def wc(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(p), index=False, encoding="utf-8-sig")


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
    wc(out / "gold_v2_24i_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24I-C000", "required 24H files exist", inputs_ok, True, inputs_ok)]
    summary24h: dict[str, Any] = {}
    selected = ""
    intake_selected = ""
    if inputs_ok:
        summary24h = rj(paths["summary"])
        decision = rj(paths["decision_input"])
        intake = rc(paths["intake_result"])
        checks24h = rc(paths["checks"])
        gates24h = rc(paths["gates"])
        safety24h = rc(paths["safety"])
        selected = str(decision.get("selected_decision_value", "")).strip()
        intake_selected = str(intake.iloc[0]["selected_decision_value"]).strip() if not intake.empty and "selected_decision_value" in intake.columns else ""
        rows += [
            check("24I-C001", "24H status valid", summary24h.get("status"), EXPECTED_STATUS, summary24h.get("status") == EXPECTED_STATUS),
            check("24I-C002", "decision supplied", summary24h.get("decision_supplied"), True, t(summary24h.get("decision_supplied"))),
            check("24I-C003", "decision validated", summary24h.get("decision_validated"), True, t(summary24h.get("decision_validated"))),
            check("24I-C004", "decision matches summary", selected, summary24h.get("selected_decision_value"), selected == str(summary24h.get("selected_decision_value", "")).strip() and selected != ""),
            check("24I-C005", "decision matches intake", selected, intake_selected, selected == intake_selected and selected != ""),
            check("24I-C006", "decision has route", selected, "known route", selected in ROUTES),
            check("24I-C007", "24H stop rows zero", stops(checks24h) + stops(safety24h), 0, stops(checks24h) + stops(safety24h) == 0),
            check("24I-C008", "24H next only 24I", allowed(gates24h, "allowed_after_24h_success"), [STEP], allowed(gates24h, "allowed_after_24h_success") == [STEP]),
            check("24I-C009", "24H did not allow run now", summary24h.get("source_recovery_execution_allowed_now"), False, f(summary24h.get("source_recovery_execution_allowed_now"))),
            check("24I-C010", "24H did not approve in intake", summary24h.get("source_recovery_approved_by_24h"), False, f(summary24h.get("source_recovery_approved_by_24h"))),
        ]
    checks = pd.DataFrame(rows)
    upstream_ok = inputs_ok and stops(checks) == 0
    route_id, next_step = ROUTES.get(selected, ("ROUTE_UNKNOWN", "STOP_REVIEW_24I_DECISION"))
    route = pd.DataFrame([{
        "selected_decision_value": selected,
        "route_id": route_id,
        "routed_next_audit_step": next_step,
        "route_known": selected in ROUTES,
        "source_recovery_execution_allowed_in_24i": False,
        "source_recovery_approved_by_24i": False,
        "status": "ROUTED_TO_NEXT_AUDIT_ONLY" if upstream_ok and selected in ROUTES else "STOP",
    }])
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "routing_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_recovery_approved_by_24i", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(route) + stops(safety)
    ok = upstream_ok and total_stop == 0 and next_step != "STOP_REVIEW_24I_DECISION"
    gates = pd.DataFrame([
        {"next_step": step, "allowed_after_24i_success": bool(ok and step == next_step), "reason": "selected route" if ok and step == next_step else "not selected/blocked"}
        for step in list({v[1] for v in ROUTES.values()}) + BLOCKED_NOW
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "decision_routing_only": True,
        "selected_decision_value": selected,
        "route_id": route_id,
        "routed_next_audit_step": next_step,
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24i": False,
        "source_recovery_approved": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24i": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24i_success"),
        "next_recommended_step": next_step if ok else "STOP_REVIEW_24I_INPUTS",
        "do_not_execute_source_recovery_in_24i": True,
    }
    wc(out / "gold_v2_24i_decision_route.csv", route)
    wc(out / "gold_v2_24i_integrated_checks.csv", checks)
    wc(out / "gold_v2_24i_required_next_gates.csv", gates)
    wc(out / "gold_v2_24i_safety_matrix.csv", safety)
    wj(out / "gold_v2_24i_source_recovery_execution_decision_routing_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24I decision routing audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24I routes the validated 24H decision only. It does not run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Selected decision: `{selected}`", f"- Route id: `{route_id}`", f"- Routed next audit step: `{next_step}`", "",
        "## Input audit", "", md(input_audit), "", "## Integrated checks", "", md(checks), "", "## Decision route", "", md(route), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
