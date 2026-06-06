#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY"
IN_DIR = "gold_v2_24k_source_recovery_execution_preflight_audit_only"
OUT_DIR = "gold_v2_24l_source_recovery_execution_dry_run_plan_audit_only"
EXPECTED_24K_STATUS = "SOURCE_RECOVERY_EXECUTION_PREFLIGHT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24K_NEXT = "24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24L_STOP_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24k_source_recovery_execution_preflight_summary.json",
    "input_audit": "gold_v2_24k_input_audit.csv",
    "preflight_validation": "gold_v2_24k_preflight_validation.csv",
    "artifact_manifest_review": "gold_v2_24k_artifact_manifest_review.csv",
    "stop_condition_review": "gold_v2_24k_stop_condition_review.csv",
    "checks": "gold_v2_24k_integrated_checks.csv",
    "gates": "gold_v2_24k_required_next_gates.csv",
    "safety": "gold_v2_24k_safety_matrix.csv",
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


def build_dry_run_plan() -> pd.DataFrame:
    return pd.DataFrame([
        {"plan_id": "24L-DR001", "dry_run_item": "read_only_source_artifact_scan", "audit_only": True, "no_write": True, "description": "Dry-run may read listed artifacts only and record what would be checked."},
        {"plan_id": "24L-DR002", "dry_run_item": "no_op_route_replay", "audit_only": True, "no_write": True, "description": "Dry-run may replay the approved route as metadata only."},
        {"plan_id": "24L-DR003", "dry_run_item": "hash_and_presence_preview", "audit_only": True, "no_write": True, "description": "Dry-run may verify presence/hash metadata without changing files."},
        {"plan_id": "24L-DR004", "dry_run_item": "forbidden_action_lock_preview", "audit_only": True, "no_write": True, "description": "Dry-run must confirm all blocked actions remain disabled."},
        {"plan_id": "24L-DR005", "dry_run_item": "no_source_identity_mutation", "audit_only": True, "no_write": True, "description": "Dry-run must not modify or finalize source identity."},
    ])


def build_input_manifest() -> pd.DataFrame:
    return pd.DataFrame([
        {"input_role": "24K summary", "required_for_24m": True, "read_only": True, "source_folder": IN_DIR},
        {"input_role": "24K report", "required_for_24m": True, "read_only": True, "source_folder": IN_DIR},
        {"input_role": "24K preflight validation", "required_for_24m": True, "read_only": True, "source_folder": IN_DIR},
        {"input_role": "24K manifest review", "required_for_24m": True, "read_only": True, "source_folder": IN_DIR},
        {"input_role": "24E-24J audit chain", "required_for_24m": True, "read_only": True, "source_folder": "prior FX_OUTPUTS"},
    ])


def build_expected_noop_outputs() -> pd.DataFrame:
    return pd.DataFrame([
        {"output_role": "dry_run_observation_log", "should_be_written_by_24m": True, "mutates_source": False},
        {"output_role": "dry_run_blocked_action_matrix", "should_be_written_by_24m": True, "mutates_source": False},
        {"output_role": "dry_run_hash_presence_preview", "should_be_written_by_24m": True, "mutates_source": False},
        {"output_role": "dry_run_summary", "should_be_written_by_24m": True, "mutates_source": False},
    ])


def build_stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        {"stop_id": "24L-S001", "condition": "required 24K input missing", "action": "STOP"},
        {"stop_id": "24L-S002", "condition": "24K status not passed", "action": "STOP"},
        {"stop_id": "24L-S003", "condition": "24K did not allow only 24L", "action": "STOP"},
        {"stop_id": "24L-S004", "condition": "any source mutation would be required", "action": "STOP"},
        {"stop_id": "24L-S005", "condition": "any external/live/finalization flag is true", "action": "STOP"},
        {"stop_id": "24L-S006", "condition": "old GOLD/DISC8 quarantine not preserved", "action": "STOP"},
    ])


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24l_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24L-C000", "required 24K files exist", inputs_ok, True, inputs_ok)]
    summary24k: dict[str, Any] = {}
    if inputs_ok:
        summary24k = rj(paths["summary"])
        checks24k = rc(paths["checks"])
        gates24k = rc(paths["gates"])
        safety24k = rc(paths["safety"])
        preflight24k = rc(paths["preflight_validation"])
        manifest24k = rc(paths["artifact_manifest_review"])
        stop24k = rc(paths["stop_condition_review"])
        rows += [
            check("24L-C001", "24K status passed", summary24k.get("status"), EXPECTED_24K_STATUS, summary24k.get("status") == EXPECTED_24K_STATUS),
            check("24L-C002", "24K is preflight only", summary24k.get("preflight_only"), True, t(summary24k.get("preflight_only"))),
            check("24L-C003", "24K stop rows zero", stops(checks24k) + stops(safety24k) + stops(preflight24k) + stops(manifest24k) + stops(stop24k), 0, stops(checks24k) + stops(safety24k) + stops(preflight24k) + stops(manifest24k) + stops(stop24k) == 0),
            check("24L-C004", "24K next only 24L", allowed(gates24k, "allowed_after_24k_success"), [EXPECTED_24K_NEXT], allowed(gates24k, "allowed_after_24k_success") == [EXPECTED_24K_NEXT]),
            check("24L-C005", "24K did not allow run now", summary24k.get("source_recovery_execution_allowed_now"), False, f(summary24k.get("source_recovery_execution_allowed_now"))),
            check("24L-C006", "24K old quarantine preserved", summary24k.get("old_gold_disc8_quarantined"), True, t(summary24k.get("old_gold_disc8_quarantined"))),
        ]
    checks = pd.DataFrame(rows)
    dry_plan = build_dry_run_plan()
    input_manifest = build_input_manifest()
    noop_outputs = build_expected_noop_outputs()
    stop_conditions = build_stop_conditions()
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "dry_run_plan_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY", "allowed_after_24l_success": bool(ok), "reason": "dry-run plan ready" if ok else "24L not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24l_success": False, "reason": "24L is dry-run-plan-only"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24l_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24l_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "dry_run_plan_only": True,
        "upstream_24k_status": summary24k.get("status", "UNKNOWN"),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24l": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24l_success"),
        "next_recommended_step": "24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY" if ok else "STOP_REVIEW_24L_INPUTS",
        "do_not_execute_source_recovery_in_24l": True,
    }
    wc(out / "gold_v2_24l_dry_run_plan.csv", dry_plan)
    wc(out / "gold_v2_24l_dry_run_input_manifest.csv", input_manifest)
    wc(out / "gold_v2_24l_expected_noop_outputs.csv", noop_outputs)
    wc(out / "gold_v2_24l_stop_conditions.csv", stop_conditions)
    wc(out / "gold_v2_24l_integrated_checks.csv", checks)
    wc(out / "gold_v2_24l_required_next_gates.csv", gates)
    wc(out / "gold_v2_24l_safety_matrix.csv", safety)
    wj(out / "gold_v2_24l_source_recovery_execution_dry_run_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24L source recovery execution dry-run plan audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24L writes a dry-run plan only. It does not run recovery, mutate sources, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Dry-run plan", "", md(dry_plan), "", "## Dry-run input manifest", "", md(input_manifest), "", "## Expected noop outputs", "", md(noop_outputs), "", "## Stop conditions", "", md(stop_conditions), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
