#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_only"
IN20J = "gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_audit_only"
IN20I = "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only"
REPORT = "GOLD_V2_20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20J = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP = "docs/gold_v2/GOLD_V2_20K_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBIDDEN_NEXT = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FALSE_FLAGS = [
    "decision_value_collected", "decision_collected", "decision_made", "approval_granted",
    "actual_decision_collection_allowed", "actual_decision_collection_completed", "signal_conditions_changed",
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
FALSE_DRAFT_FLAGS = [
    "actual_decision_value_collected", "actual_decision_collection_completed", "approval_granted",
    "source_recovery_allowed", "source_identity_finalization_allowed", "source_identity_recovery_allowed",
    "ledger_source_of_truth_promotion_allowed", "oh_lc_replay_allowed", "live_evaluator_allowed",
    "final_signal_allowed", "discord_send_allowed", "no_signal_discord_send_allowed", "mt5_order_allowed",
    "ai_api_allowed", "live_hook_allowed", "signal_conditions_change_allowed", "script_executes_action",
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


def first_col(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((n for n in names if n in df.columns), None)


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_NEXT)][col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20L", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY", "Reconcile value capture draft content audit outputs.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20K.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20K.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20K.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked after 20K.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked after 20K.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20k_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["draft_content_audit_only", True, True, "PASS"],
        ["decision_value", "UNSET", "UNSET", "PASS"], ["decision_value_collected", False, False, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"], ["actual_decision_collection_completed", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"], ["signal_conditions_changed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"], ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"], ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["next_gate_20l_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def main() -> int:
    root, base = repo_root(), fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20j, p20i = base / IN20J, base / IN20I
    inputs = {
        "backup_manifest": root / BACKUP,
        "summary_20j": p20j / "gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_summary.json",
        "load_checks_20j": p20j / "gold_v2_20j_load_checks.csv",
        "load_audit_20j": p20j / "gold_v2_20j_draft_load_audit.csv",
        "gates_20j": p20j / "gold_v2_20j_required_next_gates.csv",
        "safety_20j": p20j / "gold_v2_20j_safety_matrix.csv",
        "report_20j": p20j / "GOLD_V2_20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "draft_20i": p20i / "gold_v2_20i_value_capture_draft.json",
        "allowed_values_20i": p20i / "gold_v2_20i_allowed_decision_values_audit.csv",
        "required_fields_20i": p20i / "gold_v2_20i_required_decision_fields_audit.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20k_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        c = pd.DataFrame([check("20K-C000", "required inputs exist", False, True, False)])
        s = safety(False); g = next_gates(False)
        write_csv(out / "gold_v2_20k_content_checks.csv", c); write_csv(out / "gold_v2_20k_safety_matrix.csv", s); write_csv(out / "gold_v2_20k_required_next_gates.csv", g)
        summary = {"created_utc": now, "step": STEP, "status": "20K_STOP_MISSING_INPUTS", "audit_only": True, "content_audit_passed": False, "decision_value": "UNSET", "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_20K_INPUTS"}
        write_json(out / "gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s20j = read_json(inputs["summary_20j"])
    draft = read_json(inputs["draft_20i"])
    checks20j = read_csv(inputs["load_checks_20j"]); gates20j = read_csv(inputs["gates_20j"]); safety20j = read_csv(inputs["safety_20j"])
    allowed = read_csv(inputs["allowed_values_20i"]); fields = read_csv(inputs["required_fields_20i"])
    vcol = first_col(allowed, ("decision_value", "value", "name")); fcol = first_col(fields, ("field_name", "field", "name"))
    values = allowed[vcol].astype(str).str.strip().tolist() if vcol else []
    fvals = fields[fcol].astype(str).str.strip().tolist() if fcol else []
    action_col = "executes_action_in_18x" if "executes_action_in_18x" in allowed.columns else None
    action_rows = int(allowed[action_col].map(truthy).sum()) if action_col else 0
    false_summary = sum(int(bool(s20j.get(k, False))) for k in FALSE_FLAGS)
    false_summary += sum(int(bool(v)) for v in s20j.get("external_actions", {}).values())
    false_draft = sum(int(bool(draft.get(k, False))) for k in FALSE_DRAFT_FLAGS)
    unset_bad = sum(int(draft.get(k) != "UNSET") for k in UNSET_FIELDS)

    allowed_audit = pd.DataFrame([
        ["value_column_present", bool(vcol), True, bool(vcol)],
        ["rows", len(allowed), ">=4", len(allowed) >= 4],
        ["empty_rows", int((pd.Series(values) == "").sum()) if values else 999, 0, bool(values) and int((pd.Series(values) == "").sum()) == 0],
        ["duplicate_rows", int(pd.Series(values).duplicated().sum()) if values else 999, 0, bool(values) and int(pd.Series(values).duplicated().sum()) == 0],
        ["action_rows", action_rows, 0, action_rows == 0],
    ], columns=["item", "observed", "expected", "pass"])
    field_audit = pd.DataFrame([
        ["field_column_present", bool(fcol), True, bool(fcol)],
        ["rows", len(fields), ">=6", len(fields) >= 6],
        ["duplicate_rows", int(pd.Series(fvals).duplicated().sum()) if fvals else 999, 0, bool(fvals) and int(pd.Series(fvals).duplicated().sum()) == 0],
    ], columns=["item", "observed", "expected", "pass"])
    write_csv(out / "gold_v2_20k_allowed_value_audit.csv", allowed_audit)
    write_csv(out / "gold_v2_20k_required_field_audit.csv", field_audit)

    checks = pd.DataFrame([
        check("20K-C001", "20J status", s20j.get("status"), EXPECTED_20J, s20j.get("status") == EXPECTED_20J),
        check("20K-C002", "20J draft_load_smoke_passed", s20j.get("draft_load_smoke_passed"), True, bool(s20j.get("draft_load_smoke_passed", False))),
        check("20K-C003", "20J total_stop_rows", s20j.get("total_stop_rows"), 0, s20j.get("total_stop_rows") == 0),
        check("20K-C004", "20J decision_value", s20j.get("decision_value"), "UNSET", s20j.get("decision_value") == "UNSET"),
        check("20K-C005", "20J forbidden summary flags true", false_summary, 0, false_summary == 0),
        check("20K-C006", "20J load/safety STOP rows", stop_count(checks20j) + stop_count(safety20j), 0, stop_count(checks20j) + stop_count(safety20j) == 0),
        check("20K-C007", "20J forbidden gates allowed", forbidden_gate_count(gates20j, "allowed_after_20j_success"), 0, forbidden_gate_count(gates20j, "allowed_after_20j_success") == 0),
        check("20K-C008", "backup manifest exists", lp(inputs["backup_manifest"]).exists(), True, lp(inputs["backup_manifest"]).exists()),
        check("20K-C009", "draft_status", draft.get("draft_status"), "VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION", draft.get("draft_status") == "VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION"),
        check("20K-C010", "draft unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check("20K-C011", "restricted draft true flags", false_draft, 0, false_draft == 0),
        check("20K-C012", "allowed audit failed rows", int((allowed_audit["pass"] == False).sum()), 0, int((allowed_audit["pass"] == False).sum()) == 0),
        check("20K-C013", "field audit failed rows", int((field_audit["pass"] == False).sum()), 0, int((field_audit["pass"] == False).sum()) == 0),
    ])
    total_stop = stop_count(checks); success = total_stop == 0
    status = SUCCESS if success else "20K_STOP_REVIEW_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_OUTPUTS"
    s = safety(success); g = next_gates(success)
    write_csv(out / "gold_v2_20k_content_checks.csv", checks); write_csv(out / "gold_v2_20k_safety_matrix.csv", s); write_csv(out / "gold_v2_20k_required_next_gates.csv", g)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True, "content_audit_passed": success,
        "draft_status": draft.get("draft_status"), "decision_value": "UNSET", "decision_value_collected": False,
        "decision_collected": False, "decision_made": False, "approval_granted": False,
        "actual_decision_collection_allowed": False, "actual_decision_collection_completed": False,
        "allowed_value_rows": int(len(allowed)), "required_field_rows": int(len(fields)), "total_stop_rows": int(total_stop),
        "signal_conditions_changed": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "20L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_20K_OUTPUTS",
    }
    write_json(out / "gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_summary.json", summary)
    report = ["# GOLD V2 20K TIER2 source identity human decision value capture draft content-audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 20K content-audited the still-UNSET actual decision value capture draft only.", "- No actual decision value was collected and no approval was made by this script.", "- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.", "", "## Content checks", md_table(checks), "", "## Allowed value audit", md_table(allowed_audit), "", "## Required field audit", md_table(field_audit), "", "## Next gates", md_table(g), "", "## Safety", md_table(s)]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
