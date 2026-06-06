#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY"
IN_DIR = "gold_v2_24m_source_recovery_execution_dry_run_audit_only"
OUT_DIR = "gold_v2_24n_source_recovery_dry_run_review_audit_only"
EXPECTED_24M_STATUS = "SOURCE_RECOVERY_EXECUTION_DRY_RUN_COMPLETED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_24M_NEXT = "24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_DRY_RUN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24N_STOP_SOURCE_RECOVERY_DRY_RUN_REVIEW_INPUTS_OR_SAFETY"

REQ = {
    "report": "GOLD_V2_24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY_REPORT.md",
    "summary": "gold_v2_24m_source_recovery_execution_dry_run_summary.json",
    "input_audit": "gold_v2_24m_input_audit.csv",
    "observation_log": "gold_v2_24m_dry_run_observation_log.csv",
    "blocked_action_matrix": "gold_v2_24m_blocked_action_matrix.csv",
    "hash_presence_preview": "gold_v2_24m_hash_presence_preview.csv",
    "noop_output_review": "gold_v2_24m_noop_output_review.csv",
    "checks": "gold_v2_24m_integrated_checks.csv",
    "gates": "gold_v2_24m_required_next_gates.csv",
    "safety": "gold_v2_24m_safety_matrix.csv",
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


def review_observations(obs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in obs.iterrows():
        ok = t(row.get("performed_as_noop", False)) and f(row.get("source_mutated", False)) and str(row.get("status", "")) == "PASS"
        rows.append({"observation_id": row.get("observation_id", ""), "dry_run_item": row.get("dry_run_item", ""), "performed_as_noop": row.get("performed_as_noop", ""), "source_mutated": row.get("source_mutated", ""), "status": "PASS" if ok else "STOP"})
    return pd.DataFrame(rows)


def review_blocked(blocked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in blocked.iterrows():
        ok = f(row.get("allowed_in_24m", False)) and f(row.get("observed", False)) and str(row.get("status", "")) == "PASS"
        rows.append({"blocked_action": row.get("blocked_action", ""), "allowed_in_24m": row.get("allowed_in_24m", ""), "observed": row.get("observed", ""), "status": "PASS" if ok else "STOP"})
    return pd.DataFrame(rows)


def review_noop(noop: pd.DataFrame, preview: pd.DataFrame) -> pd.DataFrame:
    rows = []
    source_mutating_outputs = int(noop["mutates_source"].map(t).sum()) if not noop.empty and "mutates_source" in noop.columns else 999
    missing_preview = int((~preview["exists"].map(t)).sum()) if not preview.empty and "exists" in preview.columns else 999
    rows.append({"review_id": "24N-NOOP-001", "review": "noop outputs do not mutate source", "observed": source_mutating_outputs, "expected": 0, "status": "PASS" if source_mutating_outputs == 0 else "STOP"})
    rows.append({"review_id": "24N-NOOP-002", "review": "hash presence preview all present", "observed": missing_preview, "expected": 0, "status": "PASS" if missing_preview == 0 else "STOP"})
    return pd.DataFrame(rows)


def main() -> int:
    src = fx_root() / IN_DIR
    out = fx_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    paths = {k: src / v for k, v in REQ.items()}
    input_audit = pd.DataFrame([{"role": k, "path": str(p), "required": True, "exists": lp(p).exists()} for k, p in paths.items()])
    wc(out / "gold_v2_24n_input_audit.csv", input_audit)
    inputs_ok = bool(input_audit["exists"].map(t).all())
    rows = [check("24N-C000", "required 24M files exist", inputs_ok, True, inputs_ok)]
    summary24m: dict[str, Any] = {}
    if inputs_ok:
        summary24m = rj(paths["summary"])
        obs = rc(paths["observation_log"])
        blocked = rc(paths["blocked_action_matrix"])
        preview = rc(paths["hash_presence_preview"])
        noop = rc(paths["noop_output_review"])
        checks24m = rc(paths["checks"])
        gates24m = rc(paths["gates"])
        safety24m = rc(paths["safety"])
        rows += [
            check("24N-C001", "24M status passed", summary24m.get("status"), EXPECTED_24M_STATUS, summary24m.get("status") == EXPECTED_24M_STATUS),
            check("24N-C002", "24M is noop dry-run only", summary24m.get("noop_dry_run_only"), True, t(summary24m.get("noop_dry_run_only"))),
            check("24N-C003", "24M stop rows zero", stops(checks24m) + stops(safety24m) + stops(obs) + stops(blocked) + stops(preview) + stops(noop), 0, stops(checks24m) + stops(safety24m) + stops(obs) + stops(blocked) + stops(preview) + stops(noop) == 0),
            check("24N-C004", "24M next only 24N", allowed(gates24m, "allowed_after_24m_success"), [EXPECTED_24M_NEXT], allowed(gates24m, "allowed_after_24m_success") == [EXPECTED_24M_NEXT]),
            check("24N-C005", "24M did not allow source mutation", summary24m.get("source_mutation_allowed"), False, f(summary24m.get("source_mutation_allowed"))),
            check("24N-C006", "24M did not allow recovery now", summary24m.get("source_recovery_execution_allowed_now"), False, f(summary24m.get("source_recovery_execution_allowed_now"))),
        ]
    else:
        obs = blocked = preview = noop = pd.DataFrame()
    checks = pd.DataFrame(rows)
    dry_review = review_observations(obs)
    blocked_review = review_blocked(blocked)
    noop_integrity = review_noop(noop, preview)
    safety = pd.DataFrame([
        {"safety_item": "audit_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "review_only", "observed": True, "expected": True, "status": "PASS"},
        {"safety_item": "source_mutation_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_recovery_execution_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "source_identity_finalization_allowed_now", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "external_actions_allowed", "observed": False, "expected": False, "status": "PASS"},
        {"safety_item": "old_gold_disc8_quarantined", "observed": True, "expected": True, "status": "PASS"},
    ])
    total_stop = stops(checks) + stops(dry_review) + stops(blocked_review) + stops(noop_integrity) + stops(safety)
    ok = inputs_ok and total_stop == 0
    gates = pd.DataFrame([
        {"next_step": "24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY", "allowed_after_24n_success": bool(ok), "reason": "dry-run review passed" if ok else "24N not passed"},
        {"next_step": "SOURCE_RECOVERY", "allowed_after_24n_success": False, "reason": "24N is review-only"},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "LIVE", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "FINAL_SIGNAL", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "DISCORD_SEND", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "MT5_ORDER", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "AI_API", "allowed_after_24n_success": False, "reason": "blocked"},
        {"next_step": "LIVE_HOOK", "allowed_after_24n_success": False, "reason": "blocked"},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS if ok else STOP_STATUS,
        "audit_only": True,
        "review_only": True,
        "upstream_24m_status": summary24m.get("status", "UNKNOWN"),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "source_mutation_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "old_gold_disc8_quarantined": True,
        "still_blocked_after_24n": BLOCKED_NOW,
        "total_stop_rows": int(total_stop),
        "required_next_allowed": allowed(gates, "allowed_after_24n_success"),
        "next_recommended_step": "24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY" if ok else "STOP_REVIEW_24N_INPUTS",
        "do_not_execute_source_recovery_in_24n": True,
    }
    wc(out / "gold_v2_24n_dry_run_review.csv", dry_review)
    wc(out / "gold_v2_24n_blocked_action_review.csv", blocked_review)
    wc(out / "gold_v2_24n_noop_integrity_review.csv", noop_integrity)
    wc(out / "gold_v2_24n_integrated_checks.csv", checks)
    wc(out / "gold_v2_24n_required_next_gates.csv", gates)
    wc(out / "gold_v2_24n_safety_matrix.csv", safety)
    wj(out / "gold_v2_24n_source_recovery_dry_run_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 24N source recovery dry-run review audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "24N reviews the 24M no-op dry-run only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md(input_audit), "", "## Dry-run review", "", md(dry_review), "", "## Blocked action review", "", md(blocked_review), "", "## Noop integrity review", "", md(noop_integrity), "", "## Integrated checks", "", md(checks), "", "## Required next gates", "", md(gates), "", "## Safety matrix", "", md(safety), "",
        "## Explicit non-actions", "", "- source recovery run: `false`", "- source mutation: `false`", "- source identity finalization: `false`", "- live/final signal/external actions: `false`",
    ])
    wt(out / "GOLD_V2_24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY_REPORT.md", report)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
