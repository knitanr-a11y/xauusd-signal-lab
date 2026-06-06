#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY"
IN_DIR = "gold_v2_24j_source_recovery_execution_plan_audit_only"
OUT_DIR = "gold_v2_24k_source_recovery_execution_preflight_audit_only"
EXPECTED_24J_STATUS = "SOURCE_RECOVERY_EXECUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24J_NEXT = "24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_PREFLIGHT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24K_STOP_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24j_source_recovery_execution_plan_summary.json",
    "input_audit": "gold_v2_24j_input_audit.csv",
    "plan": "gold_v2_24j_plan.csv",
    "preflight": "gold_v2_24j_preflight_checks.csv",
    "stop_conditions": "gold_v2_24j_stop_conditions.csv",
    "manifest": "gold_v2_24j_required_artifact_manifest.csv",
    "checks": "gold_v2_24j_integrated_checks.csv",
    "gates": "gold_v2_24j_required_next_gates.csv",
    "safety": "gold_v2_24j_safety_matrix.csv",
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


def bool_col_all(df: pd.DataFrame, col: str) -> bool:
    return (not df.empty) and col in df.columns and bool(df[col].map(t).all())


def review_preflight(preflight: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in preflight.iterrows():
        exp = str(row.get("expected", ""))
        obs = str(row.get("observed", ""))
        must = t(row.get("must_pass_before_later_step", True))
        ok = (exp == obs) or (exp == "False" and obs == "False")
        rows.append({"preflight_id": row.get("preflight_id", ""), "check": row.get("check", ""), "expected": exp, "observed": obs, "must_pass": must, "status": "PASS" if ok and must else "STOP"})
    return pd.DataFrame(rows)


def review_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if manifest.empty:
        return pd.DataFrame([{"artifact_role": "manifest_missing", "required_for_24k": True, "status": "STOP", "notes": "manifest empty"}])
    for _, row in manifest.iterrows():
        req = t(row.get("required_for_24k", False))
        role = str(row.get("artifact_role", ""))
        rows.append({"artifact_role": role, "required_for_24k": req, "status": "PASS" if req and role else "STOP", "notes": row.get("notes", "")})
    return pd.DataFrame(rows)


def review_stop_conditions(stop_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if stop_df.empty:
        return pd.DataFrame([{"stop_id": "missing", "condition": "stop condition file empty", "action": "STOP", "status": "STOP"}])
    for _, row in stop_df.iterrows():
        action = str(row.get("action", "")).strip().upper()
        rows.append({"stop_id": row.get("stop_id", ""), "condition": row.get("condition", ""), "action": action, "status": "PASS" if action == "STOP" else "STOP"})
    return pd.DataFrame(rows)


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24k_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24K-C000", "required 24J files exist", inputs_ok, True, inputs_ok)]
    summary24j: dict[str, Any] = {}
    plan = pd.DataFrame(); preflight = pd.DataFrame(); stop_df = pd.DataFrame(); manifest = pd.DataFrame()
    if inputs_ok:
        summary24j = rj(paths["summary"])
        plan = rc(paths["plan"])
        preflight = rc(paths["preflight"])
        stop_df = rc(paths["stop_conditions"])
        manifest = rc(paths["manifest"])
        checks24j = rc(paths["checks"])
        gates24j = rc(paths["gates"])
        safety24j = rc(paths["safety"])
        rows += [
            check("24K-C001", "24J status passed", summary24j.get("status"), EXPECTED_24J_STATUS, summary24j.get("status") == EXPECTED_24J_STATUS),
            check("24K-C002", "24J is plan only", summary24j.get("plan_only"), True, t(summary24j.get("plan_only"))),
            check("24K-C003", "24J stop rows zero", stops(checks24j) + stops(safety24j), 0, stops(checks24j) + stops(safety24j) == 0),
            check("24K-C004", "24J next only 24K", allowed(gates24j, "allowed_after_24j_success"), [EXPECTED_24J_NEXT], allowed(gates24j, "allowed_after_24j_success") == [EXPECTED_24J_NEXT]),
            check("24K-C005", "plan rows present", len(plan), ">=5", len(plan) >= 5),
            check("24K-C006", "plan rows required", bool_col_all(plan, "required"), True, bool_col_all(plan, "required")),
            check("24K-C007", "plan rows audit-only", bool_col_all(plan, "audit_only"), True, bool_col_all(plan, "audit_only")),
            check("24K-C008", "preflight rows present", len(preflight), ">=6", len(preflight) >= 6),
            check("24K-C009", "stop condition rows present", len(stop_df), ">=6", len(stop_df) >= 6),
            check("24K-C010", "manifest rows present", len(manifest), ">=5", len(manifest) >= 5),
            check("24K-C011", "24J did not allow run now", summary24j.get("source_recovery_execution_allowed_now"), False, f(summary24j.get("source_recovery_execution_allowed_now"))),
            check("24K-C012", "24J old quarantine preserved", summary24j.get("old_gold_disc8_quarantined"), True, t(summary24j.get("old_gold_disc8_quarantined"))),
        ]
    checks = pd.DataFrame(rows)
    preflight_review = review_preflight(preflight)
    manifest_review = review_manifest(manifest)
    stop_review = review_stop_conditions(stop_df)
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "preflight_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_identity_finalization_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(preflight_review) + stops(manifest_review) + stops(stop_review) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY", "allowed_after_24k_success": bool(ok), "reason": "preflight passed" if ok else "24K not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24k_success": False, "reason": "24K is preflight-only"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24k_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24k_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "preflight_only": True,
        "upstream_24j_status": summary24j.get("status", "UNKNOWN"),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24k": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24k_success"),
        "next_recommended_step": "24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_24K_INPUTS",
        "do_not_execute_source_recovery_in_24k": True,
    }
    wc(out / "gold_v2_24k_preflight_validation.csv", preflight_review)
    wc(out / "gold_v2_24k_artifact_manifest_review.csv", manifest_review)
    wc(out / "gold_v2_24k_stop_condition_review.csv", stop_review)
    wc(out / "gold_v2_24k_integrated_checks.csv", checks)
    wc(out / "gold_v2_24k_required_next_gates.csv", gates)
    wc(out / "gold_v2_24k_safety_matrix.csv", safety)
    wj(out / "gold_v2_24k_source_recovery_execution_preflight_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24K source recovery execution preflight audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24K verifies the 24J plan package only. It does not run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Preflight validation", "", md(preflight_review), "", "## Artifact manifest review", "", md(manifest_review), "", "## Stop condition review", "", md(stop_review), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
