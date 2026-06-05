#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY"
OUT_DIR = "gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only"
IN20E = "gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only"
IN20B = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
REPORT = "GOLD_V2_20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20E = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_DRAFT_FLAGS = [
    "approval_granted", "actual_decision_collection_allowed", "source_recovery_requested", "source_recovery_allowed",
    "source_identity_finalization_allowed", "source_identity_recovery_allowed", "ledger_source_of_truth_promotion_allowed",
    "oh_lc_replay_allowed", "live_evaluator_allowed", "live_or_final_implementation_allowed", "final_signal_allowed",
    "discord_send_allowed", "no_signal_discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed",
    "script_executes_action",
]
UNSET_FIELDS = ["decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "explicit_phrase", "notes"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure_parent(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    lp(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    ensure_parent(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def check_row(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def forbidden_summary_count(s: dict[str, Any]) -> int:
    n = sum(int(bool(s.get(k, False))) for k in FORBIDDEN_FLAGS)
    ext = s.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20G", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY", "Final handoff note for the still-unset draft package.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20F; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20F.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20F.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20f_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["draft_final_audit_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_20g_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20F-S001", "required inputs missing", "STOP"],
        ["20F-S002", "20E status not passed", "STOP"],
        ["20F-S003", "20E or upstream STOP rows present", "STOP"],
        ["20F-S004", "stage status audit failed", "STOP"],
        ["20F-S005", "decision value no longer UNSET or decision/approval collected", "STOP"],
        ["20F-S006", "actual decision collection allowed", "STOP"],
        ["20F-S007", "draft restricted flag true", "STOP"],
        ["20F-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20e, p20b = base / IN20E, base / IN20B
    inputs = {
        "summary_20e": p20e / "gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json",
        "recon_checks_20e": p20e / "gold_v2_20e_reconciliation_checks.csv",
        "stage_status_20e": p20e / "gold_v2_20e_stage_status_audit.csv",
        "gates_20e": p20e / "gold_v2_20e_required_next_gates.csv",
        "safety_20e": p20e / "gold_v2_20e_safety_matrix.csv",
        "report_20e": p20e / "GOLD_V2_20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "draft_20b": p20b / "gold_v2_20b_decision_intake_draft.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20f_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20f_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20F-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20f_final_checks.csv", checks)
        write_csv(out / "gold_v2_20f_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20f_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20F_STOP_MISSING_INPUTS",
            "audit_only": True,
            "final_audit_ready": False,
            "decision_value": "UNSET",
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "actual_decision_collection_allowed": False,
            "total_stop_rows": 1,
            "source_recovery_executed": False,
            "source_identity_finalized": False,
            "source_identity_recovered": False,
            "ledger_is_source_of_truth": False,
            "live_or_final_implementation_allowed": False,
            "oh_lc_replay_allowed": False,
            "live_enabled": False,
            "final_signal_allowed": False,
            "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
            "no_signal_discord_notified": False,
            "next_recommended_step": "STOP_REVIEW_20F_INPUTS",
        }
        write_json(out / "gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20F draft final audit-only report\n\nStatus: `20F_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20e = read_json(inputs["summary_20e"])
    recon_checks = read_csv(inputs["recon_checks_20e"])
    stage_status = read_csv(inputs["stage_status_20e"])
    gates20e = read_csv(inputs["gates_20e"])
    safety20e = read_csv(inputs["safety_20e"])
    draft = read_json(inputs["draft_20b"])

    stage_not_ok = int((stage_status.get("status_ok", pd.Series(dtype=bool)).map(lambda x: not truthy(x))).sum()) if not stage_status.empty else 999
    stage_decision_not_unset = int((stage_status.get("decision_value", pd.Series(dtype=str)).astype(str) != "UNSET").sum()) if not stage_status.empty else 999
    stage_stop_rows = int(pd.to_numeric(stage_status.get("summary_stop_rows", pd.Series(dtype=int)), errors="coerce").fillna(999).sum()) if not stage_status.empty else 999
    upstream_stop = stop_count(recon_checks) + stop_count(safety20e)
    forbidden_gates = forbidden_gate_count(gates20e, "allowed_after_20e_success")
    forbidden_flags = forbidden_summary_count(s20e)
    draft_unset_bad = sum(int(draft.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_draft_true = sum(int(bool(draft.get(k, False))) for k in RESTRICTED_DRAFT_FLAGS)
    decision_flags_true = sum(int(bool(s20e.get(k, False))) for k in ("decision_collected", "decision_made", "approval_granted", "actual_decision_collection_allowed"))

    checks = pd.DataFrame([
        check_row("20F-C001", "20E status", s20e.get("status"), EXPECTED_20E, s20e.get("status") == EXPECTED_20E),
        check_row("20F-C002", "20E reconciliation_passed", s20e.get("reconciliation_passed"), True, bool(s20e.get("reconciliation_passed", False))),
        check_row("20F-C003", "20E total_stop_rows", s20e.get("total_stop_rows"), 0, s20e.get("total_stop_rows") == 0),
        check_row("20F-C004", "20E decision_value", s20e.get("decision_value"), "UNSET", s20e.get("decision_value") == "UNSET"),
        check_row("20F-C005", "20E decision/approval/collection flags true", decision_flags_true, 0, decision_flags_true == 0),
        check_row("20F-C006", "20E recon/safety STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20F-C007", "stage statuses not ok", stage_not_ok, 0, stage_not_ok == 0),
        check_row("20F-C008", "stage decision values not UNSET", stage_decision_not_unset, 0, stage_decision_not_unset == 0),
        check_row("20F-C009", "stage summary STOP rows", stage_stop_rows, 0, stage_stop_rows == 0),
        check_row("20F-C010", "draft unset fields not UNSET", draft_unset_bad, 0, draft_unset_bad == 0),
        check_row("20F-C011", "draft restricted flags true", restricted_draft_true, 0, restricted_draft_true == 0),
        check_row("20F-C012", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20F-C013", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20F_STOP_REVIEW_DRAFT_FINAL_AUDIT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20f_final_checks.csv", checks)
    write_csv(out / "gold_v2_20f_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20f_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "final_audit_ready": success,
        "decision_value": "UNSET",
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "total_stop_rows": int(total_stop),
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY" if success else "STOP_REVIEW_20F_OUTPUTS",
    }
    write_json(out / "gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json", summary)
    report = [
        "# GOLD V2 20F TIER2 source identity human decision intake draft final audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20F final-audited the unset actual decision intake draft package only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Final checks",
        md_table(checks),
        "",
        "## Next gates",
        md_table(gates),
        "",
        "## Safety",
        md_table(sm),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
