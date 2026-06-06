#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY"
IN_DIR = "gold_v2_24o_source_recovery_readiness_decision_options_audit_only"
OUT_DIR = "gold_v2_24p_source_recovery_readiness_decision_intake_audit_only"
EXPECTED_24O_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
WAIT_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
VALID_STATUS = "SOURCE_RECOVERY_READINESS_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24P_STOP_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24o_source_recovery_readiness_decision_options_summary.json",
    "input_audit": "gold_v2_24o_input_audit.csv",
    "decision_options": "gold_v2_24o_decision_options.csv",
    "template": "gold_v2_24o_human_decision_input_template.json",
    "checks": "gold_v2_24o_integrated_checks.csv",
    "gates": "gold_v2_24o_required_next_gates.csv",
    "safety": "gold_v2_24o_safety_matrix.csv",
}

BLOCKED_NOW = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "SOURCE_MUTATION", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FORBIDDEN_TRUE_KEYS = [
    "source_recovery_execution_allowed_now",
    "source_recovery_readiness_approved_by_24p",
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "source_mutation_allowed",
    "live_enabled",
    "final_signal_allowed",
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
]


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


def build_template(allowed_values: list[str], summary24o: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_name": "GOLD_V2_24P_SOURCE_RECOVERY_READINESS_DECISION_INPUT",
        "created_by_step": STEP,
        "audit_only": True,
        "instructions": [
            "Copy this file to gold_v2_24p_human_decision_input.json after filling exactly one selected_decision_value.",
            "selected_decision_value must exactly match one allowed_decision_values entry.",
            "APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE is not source recovery execution.",
            "Do not set any forbidden *_allowed or *_approved flags to true.",
        ],
        "allowed_decision_values": allowed_values,
        "selected_decision_value": "",
        "human_operator_notes": "",
        "source_recovery_execution_allowed_now": False,
        "source_recovery_readiness_approved_by_24p": False,
        "upstream_24o_status": summary24o.get("status", ""),
        "still_blocked_after_template_creation": BLOCKED_NOW,
    }


def forbidden_true_count(obj: dict[str, Any]) -> int:
    return sum(1 for k in FORBIDDEN_TRUE_KEYS if t(obj.get(k, False)))


def intake_result(input_path: Path, allowed_values: list[str]) -> tuple[pd.DataFrame, bool, bool, str, int]:
    if not lp(input_path).exists():
        df = pd.DataFrame([{
            "selected_decision_value": "",
            "decision_supplied": False,
            "decision_value_allowed": False,
            "forbidden_flags_true_count": 0,
            "routes_to_later_audit": False,
            "source_recovery_execution_allowed_now": False,
            "source_recovery_readiness_approved_by_24p": False,
            "status": "WAIT_FOR_24P_HUMAN_DECISION_INPUT",
            "notes": "No optional human decision input supplied.",
        }])
        return df, False, False, "", 0
    obj = rj(input_path)
    selected = str(obj.get("selected_decision_value", "")).strip()
    supplied = bool(selected)
    value_allowed = selected in allowed_values
    true_count = forbidden_true_count(obj)
    validated = supplied and value_allowed and true_count == 0
    df = pd.DataFrame([{
        "selected_decision_value": selected,
        "decision_supplied": supplied,
        "decision_value_allowed": value_allowed,
        "forbidden_flags_true_count": true_count,
        "routes_to_later_audit": validated,
        "source_recovery_execution_allowed_now": False,
        "source_recovery_readiness_approved_by_24p": False,
        "status": "VALID_24P_DECISION_VALUE_FOR_ROUTING_AUDIT_ONLY" if validated else "STOP",
        "notes": "Validated for later routing only; 24P does not execute recovery." if validated else "Invalid or unsafe decision input.",
    }])
    return df, supplied, validated, selected, true_count


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    optional_input = out / "gold_v2_24p_human_decision_input.json"
    input_audit = pd.concat([input_audit, pd.DataFrame([{"role": "24p_optional_human_decision_input", "path": str(optional_input), "required": False, "exists": lp(optional_input).exists()}])], ignore_index=True)
    wc(out / "gold_v2_24p_input_audit.csv", input_audit)
    required_ok = bool(input_audit[input_audit["required"].map(t)]["exists"].map(t).all())
    rows = [check("24P-C000", "required 24O files exist", required_ok, True, required_ok)]
    summary24o: dict[str, Any] = {}
    allowed_values: list[str] = []
    if required_ok:
        summary24o = rj(paths["summary"])
        options = rc(paths["decision_options"])
        checks24o = rc(paths["checks"])
        gates24o = rc(paths["gates"])
        safety24o = rc(paths["safety"])
        allowed_values = options["decision_value"].astype(str).tolist() if "decision_value" in options.columns else []
        rows += [
            check("24P-C001", "24O status ready", summary24o.get("status"), EXPECTED_24O_STATUS, summary24o.get("status") == EXPECTED_24O_STATUS),
            check("24P-C002", "24O is options only", summary24o.get("decision_options_only"), True, t(summary24o.get("decision_options_only"))),
            check("24P-C003", "24O option rows four", len(allowed_values), 4, len(allowed_values) == 4),
            check("24P-C004", "24O stop rows zero", stops(checks24o) + stops(safety24o), 0, stops(checks24o) + stops(safety24o) == 0),
            check("24P-C005", "24O next only 24P", allowed(gates24o, "allowed_after_24o_success"), [STEP], allowed(gates24o, "allowed_after_24o_success") == [STEP]),
            check("24P-C006", "24O did not allow recovery now", summary24o.get("source_recovery_execution_allowed_now"), False, f(summary24o.get("source_recovery_execution_allowed_now"))),
            check("24P-C007", "24O did not approve readiness by itself", summary24o.get("source_recovery_readiness_approved_by_24o"), False, f(summary24o.get("source_recovery_readiness_approved_by_24o"))),
        ]
    template = build_template(allowed_values, summary24o)
    wj(out / "gold_v2_24p_human_decision_input_template.json", template)
    result, supplied, validated, selected, true_count = intake_result(optional_input, allowed_values)
    wc(out / "gold_v2_24p_human_decision_intake_result.csv", result)
    checks = pd.DataFrame(rows)
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "decision_intake_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_identity_finalization_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(result) + stops(safety)
    ok_base = required_ok and stops(checks) == 0 and stops(safety) == 0
    status = VALID_STATUS if ok_base and validated else WAIT_STATUS if ok_base and not supplied else STOP_STATUS
    gates = pd.DataFrame([
        {"next_step": "WAIT_FOR_24P_HUMAN_DECISION_INPUT", "allowed_after_24p_success": bool(ok_base and not supplied), "reason": "decision not supplied" if ok_base and not supplied else "not waiting"},
        {"next_step": "24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY", "allowed_after_24p_success": bool(ok_base and validated), "reason": "decision validated" if ok_base and validated else "decision not validated"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24p_success": False, "reason": "24P is intake-only"},
        {"next_step": "SOURCE_MUTATION", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24p_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24p_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "decision_intake_only": True,
        "upstream_24o_status": summary24o.get("status", "UNKNOWN"),
        "allowed_decision_values": allowed_values,
        "decision_supplied": supplied,
        "decision_validated": validated,
        "selected_decision_value": selected,
        "forbidden_flags_true_count": int(true_count),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_readiness_approved_by_24p": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24p": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24p_success"),
        "next_recommended_step": "24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY" if validated and ok_base else "WAIT_FOR_24P_HUMAN_DECISION_INPUT" if ok_base and not supplied else "STOP_REVIEW_24P_INPUTS",
        "do_not_execute_source_recovery_in_24p": True,
    }
    wc(out / "gold_v2_24p_integrated_checks.csv", checks)
    wc(out / "gold_v2_24p_required_next_gates.csv", gates)
    wc(out / "gold_v2_24p_safety_matrix.csv", safety)
    wj(out / "gold_v2_24p_source_recovery_readiness_decision_intake_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24P source recovery readiness decision intake audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24P intakes one optional human readiness decision value only. It does not choose a decision, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Decision supplied: `{summary['decision_supplied']}`", f"- Decision validated: `{summary['decision_validated']}`", f"- Selected decision value: `{summary['selected_decision_value']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Human decision intake result", "", md(result), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- readiness approved by 24P: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok_base else 2


if __name__ == "__main__":
    raise SystemExit(main())
