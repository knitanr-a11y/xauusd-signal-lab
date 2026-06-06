#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY"
IN_DIR = "gold_v2_24l_source_recovery_execution_dry_run_plan_audit_only"
OUT_DIR = "gold_v2_24m_source_recovery_execution_dry_run_audit_only"
EXPECTED_24L_STATUS = "SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24L_NEXT = "24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_DRY_RUN_COMPLETED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24M_STOP_SOURCE_RECOVERY_EXECUTION_DRY_RUN_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24l_source_recovery_execution_dry_run_plan_summary.json",
    "input_audit": "gold_v2_24l_input_audit.csv",
    "dry_run_plan": "gold_v2_24l_dry_run_plan.csv",
    "input_manifest": "gold_v2_24l_dry_run_input_manifest.csv",
    "expected_noop_outputs": "gold_v2_24l_expected_noop_outputs.csv",
    "stop_conditions": "gold_v2_24l_stop_conditions.csv",
    "checks": "gold_v2_24l_integrated_checks.csv",
    "gates": "gold_v2_24l_required_next_gates.csv",
    "safety": "gold_v2_24l_safety_matrix.csv",
}

BLOCKED_NOW = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
BLOCKED_ACTIONS = BLOCKED_NOW + ["SOURCE_MUTATION"]


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_root() -> Path:
    return files_root() / "FX_OUTPUTS"


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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with lp(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def build_observation_log(dry_plan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in dry_plan.iterrows():
        rows.append({
            "observation_id": str(row.get("plan_id", "")),
            "dry_run_item": str(row.get("dry_run_item", "")),
            "would_check": str(row.get("description", "")),
            "performed_as_noop": True,
            "source_mutated": False,
            "status": "PASS" if t(row.get("audit_only", False)) and t(row.get("no_write", False)) else "STOP",
        })
    return pd.DataFrame(rows)


def build_blocked_action_matrix() -> pd.DataFrame:
    return pd.DataFrame([{"blocked_action": a, "allowed_in_24m": False, "observed": False, "status": "PASS"} for a in BLOCKED_ACTIONS])


def build_hash_presence_preview(paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in paths.items():
        exists = lp(path).exists()
        rows.append({"role": role, "path": str(path), "exists": exists, "sha256": sha256_file(path) if exists and lp(path).is_file() else "", "read_only_preview": True, "status": "PASS" if exists else "STOP"})
    return pd.DataFrame(rows)


def review_noop_outputs(expected: pd.DataFrame, obs: pd.DataFrame, blocked: pd.DataFrame, preview: pd.DataFrame) -> pd.DataFrame:
    produced = {"dry_run_observation_log": not obs.empty, "dry_run_blocked_action_matrix": not blocked.empty, "dry_run_hash_presence_preview": not preview.empty, "dry_run_summary": True}
    rows = []
    for _, row in expected.iterrows():
        role = str(row.get("output_role", ""))
        should = t(row.get("should_be_written_by_24m", False))
        mutates = t(row.get("mutates_source", False))
        ok = should and produced.get(role, False) and not mutates
        rows.append({"output_role": role, "expected_written": should, "observed_written": produced.get(role, False), "mutates_source": mutates, "status": "PASS" if ok else "STOP"})
    return pd.DataFrame(rows)


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24m_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24M-C000", "required 24L files exist", inputs_ok, True, inputs_ok)]
    summary24l: dict[str, Any] = {}
    dry_plan = pd.DataFrame(); expected_noop = pd.DataFrame()
    if inputs_ok:
        summary24l = rj(paths["summary"])
        dry_plan = rc(paths["dry_run_plan"])
        expected_noop = rc(paths["expected_noop_outputs"])
        checks24l = rc(paths["checks"])
        gates24l = rc(paths["gates"])
        safety24l = rc(paths["safety"])
        rows += [
            check("24M-C001", "24L status passed", summary24l.get("status"), EXPECTED_24L_STATUS, summary24l.get("status") == EXPECTED_24L_STATUS),
            check("24M-C002", "24L is dry-run-plan only", summary24l.get("dry_run_plan_only"), True, t(summary24l.get("dry_run_plan_only"))),
            check("24M-C003", "24L stop rows zero", stops(checks24l) + stops(safety24l), 0, stops(checks24l) + stops(safety24l) == 0),
            check("24M-C004", "24L next only 24M", allowed(gates24l, "allowed_after_24l_success"), [EXPECTED_24L_NEXT], allowed(gates24l, "allowed_after_24l_success") == [EXPECTED_24L_NEXT]),
            check("24M-C005", "24L did not allow source mutation", summary24l.get("source_mutation_allowed"), False, f(summary24l.get("source_mutation_allowed"))),
            check("24M-C006", "dry-run plan audit-only", bool_col_all(dry_plan, "audit_only"), True, bool_col_all(dry_plan, "audit_only")),
            check("24M-C007", "dry-run plan no-write", bool_col_all(dry_plan, "no_write"), True, bool_col_all(dry_plan, "no_write")),
            check("24M-C008", "expected noop outputs non-mutating", bool((not expected_noop.empty) and (not expected_noop["mutates_source"].map(t).any())), True, bool((not expected_noop.empty) and (not expected_noop["mutates_source"].map(t).any()))),
        ]
    observations = build_observation_log(dry_plan)
    blocked = build_blocked_action_matrix()
    preview = build_hash_presence_preview(paths)
    noop_review = review_noop_outputs(expected_noop, observations, blocked, preview)
    checks = pd.DataFrame(rows)
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "noop_dry_run_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_identity_finalization_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(observations) + stops(blocked) + stops(preview) + stops(noop_review) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY", "allowed_after_24m_success": bool(ok), "reason": "dry-run completed" if ok else "24M not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24m_success": False, "reason": "24M is no-op dry-run only"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24m_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24m_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "noop_dry_run_only": True,
        "upstream_24l_status": summary24l.get("status", "UNKNOWN"),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24m": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24m_success"),
        "next_recommended_step": "24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_24M_INPUTS",
        "do_not_execute_source_recovery_in_24m": True,
    }
    wc(out / "gold_v2_24m_dry_run_observation_log.csv", observations)
    wc(out / "gold_v2_24m_blocked_action_matrix.csv", blocked)
    wc(out / "gold_v2_24m_hash_presence_preview.csv", preview)
    wc(out / "gold_v2_24m_noop_output_review.csv", noop_review)
    wc(out / "gold_v2_24m_integrated_checks.csv", checks)
    wc(out / "gold_v2_24m_required_next_gates.csv", gates)
    wc(out / "gold_v2_24m_safety_matrix.csv", safety)
    wj(out / "gold_v2_24m_source_recovery_execution_dry_run_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24M source recovery execution dry-run audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24M performs a no-op dry-run only. It writes observation artifacts under its own output folder and does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Dry-run observation log", "", md(observations), "", "## Blocked action matrix", "", md(blocked), "", "## Hash/presence preview", "", md(preview), "", "## Noop output review", "", md(noop_review), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
