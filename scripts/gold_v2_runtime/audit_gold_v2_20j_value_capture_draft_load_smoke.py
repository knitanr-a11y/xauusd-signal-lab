#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_audit_only"
IN20I = "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only"
REPORT = "GOLD_V2_20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20I = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP = "docs/gold_v2/GOLD_V2_20J_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBIDDEN_NEXT = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FALSE_SUMMARY_FLAGS = [
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


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_NEXT)][col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20K", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY", "Content-audit the still-UNSET value capture draft only.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20J.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20J.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20J.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked after 20J.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked after 20J.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20j_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["draft_load_smoke_only", True, True, "PASS"],
        ["decision_value", "UNSET", "UNSET", "PASS"], ["decision_value_collected", False, False, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"], ["actual_decision_collection_completed", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"], ["signal_conditions_changed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"], ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"], ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["next_gate_20k_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def main() -> int:
    root, base = repo_root(), fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20i = base / IN20I
    inputs = {
        "backup_manifest": root / BACKUP,
        "summary_20i": p20i / "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_summary.json",
        "draft_20i": p20i / "gold_v2_20i_value_capture_draft.json",
        "draft_checks_20i": p20i / "gold_v2_20i_draft_checks.csv",
        "allowed_values_20i": p20i / "gold_v2_20i_allowed_decision_values_audit.csv",
        "required_fields_20i": p20i / "gold_v2_20i_required_decision_fields_audit.csv",
        "gates_20i": p20i / "gold_v2_20i_required_next_gates.csv",
        "safety_20i": p20i / "gold_v2_20i_safety_matrix.csv",
        "report_20i": p20i / "GOLD_V2_20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20j_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        c = pd.DataFrame([check("20J-C000", "required inputs exist", False, True, False)])
        s = safety(False); g = next_gates(False)
        write_csv(out / "gold_v2_20j_load_checks.csv", c); write_csv(out / "gold_v2_20j_safety_matrix.csv", s); write_csv(out / "gold_v2_20j_required_next_gates.csv", g)
        summary = {"created_utc": now, "step": STEP, "status": "20J_STOP_MISSING_INPUTS", "audit_only": True, "draft_load_smoke_passed": False, "decision_value": "UNSET", "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_20J_INPUTS"}
        write_json(out / "gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s20i = read_json(inputs["summary_20i"])
    draft = read_json(inputs["draft_20i"])
    draft_checks = read_csv(inputs["draft_checks_20i"]); gates20i = read_csv(inputs["gates_20i"]); safety20i = read_csv(inputs["safety_20i"])
    allowed = read_csv(inputs["allowed_values_20i"]); fields = read_csv(inputs["required_fields_20i"])
    false_summary = sum(int(bool(s20i.get(k, False))) for k in FALSE_SUMMARY_FLAGS)
    false_summary += sum(int(bool(v)) for v in s20i.get("external_actions", {}).values())
    false_draft = sum(int(bool(draft.get(k, False))) for k in FALSE_DRAFT_FLAGS)
    allowed_vals = draft.get("allowed_decision_values", [])
    load_audit = pd.DataFrame([
        ["summary_status", s20i.get("status")], ["draft_status", draft.get("draft_status")], ["decision_value", draft.get("decision_value")],
        ["allowed_values_in_draft", len(allowed_vals)], ["allowed_values_audit_rows", len(allowed)], ["required_fields_audit_rows", len(fields)],
    ], columns=["item", "observed"])
    write_csv(out / "gold_v2_20j_draft_load_audit.csv", load_audit)
    checks = pd.DataFrame([
        check("20J-C001", "20I status", s20i.get("status"), EXPECTED_20I, s20i.get("status") == EXPECTED_20I),
        check("20J-C002", "20I draft_ready", s20i.get("draft_ready"), True, bool(s20i.get("draft_ready", False))),
        check("20J-C003", "20I total_stop_rows", s20i.get("total_stop_rows"), 0, s20i.get("total_stop_rows") == 0),
        check("20J-C004", "20I decision_value", s20i.get("decision_value"), "UNSET", s20i.get("decision_value") == "UNSET"),
        check("20J-C005", "20I forbidden summary flags true", false_summary, 0, false_summary == 0),
        check("20J-C006", "20I draft/safety STOP rows", stop_count(draft_checks) + stop_count(safety20i), 0, stop_count(draft_checks) + stop_count(safety20i) == 0),
        check("20J-C007", "20I forbidden gates allowed", forbidden_gate_count(gates20i, "allowed_after_20i_success"), 0, forbidden_gate_count(gates20i, "allowed_after_20i_success") == 0),
        check("20J-C008", "backup manifest exists", lp(inputs["backup_manifest"]).exists(), True, lp(inputs["backup_manifest"]).exists()),
        check("20J-C009", "draft_status", draft.get("draft_status"), "VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION", draft.get("draft_status") == "VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION"),
        check("20J-C010", "draft decision_value", draft.get("decision_value"), "UNSET", draft.get("decision_value") == "UNSET"),
        check("20J-C011", "draft allowed value rows", len(allowed_vals), ">=4", len(allowed_vals) >= 4),
        check("20J-C012", "allowed values audit rows", len(allowed), ">=4", len(allowed) >= 4),
        check("20J-C013", "required fields audit rows", len(fields), ">=6", len(fields) >= 6),
        check("20J-C014", "restricted draft true flags", false_draft, 0, false_draft == 0),
    ])
    total_stop = stop_count(checks); success = total_stop == 0
    status = SUCCESS if success else "20J_STOP_REVIEW_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_OUTPUTS"
    s = safety(success); g = next_gates(success)
    write_csv(out / "gold_v2_20j_load_checks.csv", checks); write_csv(out / "gold_v2_20j_safety_matrix.csv", s); write_csv(out / "gold_v2_20j_required_next_gates.csv", g)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True, "draft_load_smoke_passed": success,
        "draft_status": draft.get("draft_status"), "decision_value": "UNSET", "decision_value_collected": False,
        "decision_collected": False, "decision_made": False, "approval_granted": False,
        "actual_decision_collection_allowed": False, "actual_decision_collection_completed": False,
        "allowed_value_rows": int(len(allowed)), "required_field_rows": int(len(fields)), "total_stop_rows": int(total_stop),
        "signal_conditions_changed": False, "source_recovery_executed": False, "source_identity_finalized": False,
        "source_identity_recovered": False, "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_20J_OUTPUTS",
    }
    write_json(out / "gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_summary.json", summary)
    report = ["# GOLD V2 20J TIER2 source identity human decision value capture draft load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 20J load-smoked the still-UNSET actual decision value capture draft only.", "- No actual decision value was collected and no approval was made by this script.", "- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.", "", "## Load checks", md_table(checks), "", "## Draft load audit", md_table(load_audit), "", "## Next gates", md_table(g), "", "## Safety", md_table(s)]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
