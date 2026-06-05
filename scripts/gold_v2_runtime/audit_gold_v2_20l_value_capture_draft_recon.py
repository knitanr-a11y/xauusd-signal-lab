#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_20l_tier2_source_identity_human_decision_value_capture_draft_reconciliation_audit_only"
IN20K = "gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_only"
REPORT = "GOLD_V2_20L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20K = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP = "docs/gold_v2/GOLD_V2_20L_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBIDDEN_NEXT = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FALSE_FLAGS = [
    "decision_value_collected", "decision_collected", "decision_made", "approval_granted",
    "actual_decision_collection_allowed", "actual_decision_collection_completed", "signal_conditions_changed",
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]


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


def truthy(v: Any) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in {"1", "true", "yes", "y"}


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
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception:
            pass
    raise RuntimeError(f"CSV read failed: {path}")


def stop_count(df: pd.DataFrame) -> int:
    return int((df.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if not df.empty else 0


def failed_bool_count(df: pd.DataFrame) -> int:
    if "pass" not in df.columns:
        return 999
    return int((df["pass"].map(truthy) == False).sum())


def check(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_NEXT)][col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20M", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_ONLY", "Final-audit the reconciled still-UNSET value capture draft.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20L.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20L.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20L.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked after 20L.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked after 20L.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20l_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["draft_reconciliation_only", True, True, "PASS"],
        ["decision_value", "UNSET", "UNSET", "PASS"], ["decision_value_collected", False, False, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"], ["actual_decision_collection_completed", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"], ["signal_conditions_changed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"], ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"], ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["next_gate_20m_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def main() -> int:
    root, base = repo_root(), fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20k = base / IN20K
    inputs = {
        "backup_manifest": root / BACKUP,
        "summary_20k": p20k / "gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_summary.json",
        "checks_20k": p20k / "gold_v2_20k_content_checks.csv",
        "allowed_audit_20k": p20k / "gold_v2_20k_allowed_value_audit.csv",
        "field_audit_20k": p20k / "gold_v2_20k_required_field_audit.csv",
        "gates_20k": p20k / "gold_v2_20k_required_next_gates.csv",
        "safety_20k": p20k / "gold_v2_20k_safety_matrix.csv",
        "report_20k": p20k / "GOLD_V2_20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20l_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        c = pd.DataFrame([check("20L-C000", "required inputs exist", False, True, False)])
        s = safety(False); g = next_gates(False)
        write_csv(out / "gold_v2_20l_reconciliation_checks.csv", c); write_csv(out / "gold_v2_20l_safety_matrix.csv", s); write_csv(out / "gold_v2_20l_required_next_gates.csv", g)
        summary = {"created_utc": now, "step": STEP, "status": "20L_STOP_MISSING_INPUTS", "audit_only": True, "reconciliation_passed": False, "decision_value": "UNSET", "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_20L_INPUTS"}
        write_json(out / "gold_v2_20l_tier2_source_identity_human_decision_value_capture_draft_reconciliation_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s20k = read_json(inputs["summary_20k"])
    checks20k = read_csv(inputs["checks_20k"]); allowed = read_csv(inputs["allowed_audit_20k"]); fields = read_csv(inputs["field_audit_20k"])
    gates20k = read_csv(inputs["gates_20k"]); safety20k = read_csv(inputs["safety_20k"])
    false_summary = sum(int(bool(s20k.get(k, False))) for k in FALSE_FLAGS)
    false_summary += sum(int(bool(v)) for v in s20k.get("external_actions", {}).values())
    stage = pd.DataFrame([
        ["20K", s20k.get("status"), s20k.get("content_audit_passed"), s20k.get("decision_value"), s20k.get("total_stop_rows"), s20k.get("allowed_value_rows"), s20k.get("required_field_rows")]
    ], columns=["stage", "status", "passed", "decision_value", "summary_stop_rows", "allowed_value_rows", "required_field_rows"])
    write_csv(out / "gold_v2_20l_stage_status_audit.csv", stage)
    checks = pd.DataFrame([
        check("20L-C001", "20K status", s20k.get("status"), EXPECTED_20K, s20k.get("status") == EXPECTED_20K),
        check("20L-C002", "20K content_audit_passed", s20k.get("content_audit_passed"), True, bool(s20k.get("content_audit_passed", False))),
        check("20L-C003", "20K total_stop_rows", s20k.get("total_stop_rows"), 0, s20k.get("total_stop_rows") == 0),
        check("20L-C004", "20K decision_value", s20k.get("decision_value"), "UNSET", s20k.get("decision_value") == "UNSET"),
        check("20L-C005", "20K forbidden summary flags true", false_summary, 0, false_summary == 0),
        check("20L-C006", "20K content/safety STOP rows", stop_count(checks20k) + stop_count(safety20k), 0, stop_count(checks20k) + stop_count(safety20k) == 0),
        check("20L-C007", "20K allowed audit failed rows", failed_bool_count(allowed), 0, failed_bool_count(allowed) == 0),
        check("20L-C008", "20K field audit failed rows", failed_bool_count(fields), 0, failed_bool_count(fields) == 0),
        check("20L-C009", "20K forbidden gates allowed", forbidden_gate_count(gates20k, "allowed_after_20k_success"), 0, forbidden_gate_count(gates20k, "allowed_after_20k_success") == 0),
        check("20L-C010", "backup manifest exists", lp(inputs["backup_manifest"]).exists(), True, lp(inputs["backup_manifest"]).exists()),
    ])
    total_stop = stop_count(checks); success = total_stop == 0
    status = SUCCESS if success else "20L_STOP_REVIEW_VALUE_CAPTURE_DRAFT_RECONCILIATION_OUTPUTS"
    s = safety(success); g = next_gates(success)
    write_csv(out / "gold_v2_20l_reconciliation_checks.csv", checks); write_csv(out / "gold_v2_20l_safety_matrix.csv", s); write_csv(out / "gold_v2_20l_required_next_gates.csv", g)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True, "reconciliation_passed": success,
        "decision_value": "UNSET", "decision_value_collected": False, "decision_collected": False, "decision_made": False,
        "approval_granted": False, "actual_decision_collection_allowed": False, "actual_decision_collection_completed": False,
        "allowed_value_rows": int(s20k.get("allowed_value_rows", 0)), "required_field_rows": int(s20k.get("required_field_rows", 0)),
        "total_stop_rows": int(total_stop), "signal_conditions_changed": False, "source_recovery_executed": False,
        "source_identity_finalized": False, "source_identity_recovered": False, "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False,
        "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "20M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_ONLY" if success else "STOP_REVIEW_20L_OUTPUTS",
    }
    write_json(out / "gold_v2_20l_tier2_source_identity_human_decision_value_capture_draft_reconciliation_summary.json", summary)
    report = ["# GOLD V2 20L TIER2 source identity human decision value capture draft reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 20L reconciled the still-UNSET actual decision value capture draft content-audit outputs only.", "- No actual decision value was collected and no approval was made by this script.", "- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.", "", "## Reconciliation checks", md_table(checks), "", "## Stage status audit", md_table(stage), "", "## Next gates", md_table(g), "", "## Safety", md_table(s)]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
