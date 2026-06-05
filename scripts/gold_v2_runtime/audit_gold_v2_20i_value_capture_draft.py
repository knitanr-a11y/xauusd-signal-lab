#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY"
OUT_DIR = "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only"
IN20H = "gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only"
IN20B = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
REPORT = "GOLD_V2_20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20H = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP = "docs/gold_v2/GOLD_V2_20I_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"

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
FORBIDDEN_NEXT = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}


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
        ["20J", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke the still-UNSET value capture draft only.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20I.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20I.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20I.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked after 20I.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked after 20I.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20i_success"])


def safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"], ["value_capture_draft_only", True, True, "PASS"],
        ["decision_value", "UNSET", "UNSET", "PASS"], ["decision_value_collected", False, False, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"], ["actual_decision_collection_completed", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"], ["signal_conditions_changed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"], ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"], ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["next_gate_20j_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def main() -> int:
    root, base = repo_root(), fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20h, p20b = base / IN20H, base / IN20B
    inputs = {
        "backup_manifest": root / BACKUP,
        "summary_20h": p20h / "gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json",
        "auth_checks_20h": p20h / "gold_v2_20h_authorization_checks.csv",
        "gates_20h": p20h / "gold_v2_20h_required_next_gates.csv",
        "safety_20h": p20h / "gold_v2_20h_safety_matrix.csv",
        "report_20h": p20h / "GOLD_V2_20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md",
        "allowed_values_20b": p20b / "gold_v2_20b_allowed_decision_values.csv",
        "required_fields_20b": p20b / "gold_v2_20b_required_decision_fields.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20i_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        c = pd.DataFrame([check("20I-C000", "required inputs exist", False, True, False)])
        s = safety(False); g = next_gates(False)
        write_csv(out / "gold_v2_20i_draft_checks.csv", c); write_csv(out / "gold_v2_20i_safety_matrix.csv", s); write_csv(out / "gold_v2_20i_required_next_gates.csv", g)
        summary = {"created_utc": now, "step": STEP, "status": "20I_STOP_MISSING_INPUTS", "audit_only": True, "draft_ready": False, "decision_value": "UNSET", "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_20I_INPUTS"}
        write_json(out / "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s20h = read_json(inputs["summary_20h"])
    auth_checks = read_csv(inputs["auth_checks_20h"]); gates20h = read_csv(inputs["gates_20h"]); safety20h = read_csv(inputs["safety_20h"])
    allowed = read_csv(inputs["allowed_values_20b"]); fields = read_csv(inputs["required_fields_20b"])
    vcol = first_col(allowed, ("decision_value", "value", "name")); fcol = first_col(fields, ("field_name", "field", "name"))
    values = allowed[vcol].astype(str).str.strip().tolist() if vcol else []
    fvals = fields[fcol].astype(str).str.strip().tolist() if fcol else []
    action_col = "executes_action_in_18x" if "executes_action_in_18x" in allowed.columns else None
    action_rows = int(allowed[action_col].map(truthy).sum()) if action_col else 0
    false_summary = sum(int(bool(s20h.get(k, False))) for k in FALSE_SUMMARY_FLAGS)
    false_summary += sum(int(bool(v)) for v in s20h.get("external_actions", {}).values())
    draft = {
        "created_utc": now, "draft_status": "VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION", "authorization_scope": s20h.get("authorization_scope"),
        "decision_id": "UNSET", "decision_timestamp_utc": "UNSET", "decision_value": "UNSET", "human_reviewer": "UNSET", "explicit_phrase": "UNSET", "notes": "UNSET",
        "allowed_decision_values": values,
    }
    for k in FALSE_DRAFT_FLAGS:
        draft[k] = False
    write_json(out / "gold_v2_20i_value_capture_draft.json", draft)
    allowed2 = allowed.copy(); allowed2["audit_source"] = "20B_SOURCE_DEFINED_ALLOWED_VALUES"
    fields2 = fields.copy(); fields2["audit_source"] = "20B_SOURCE_DEFINED_REQUIRED_FIELDS"
    write_csv(out / "gold_v2_20i_allowed_decision_values_audit.csv", allowed2)
    write_csv(out / "gold_v2_20i_required_decision_fields_audit.csv", fields2)
    checks = pd.DataFrame([
        check("20I-C001", "20H status", s20h.get("status"), EXPECTED_20H, s20h.get("status") == EXPECTED_20H),
        check("20I-C002", "20H authorization_gate_passed", s20h.get("authorization_gate_passed"), True, bool(s20h.get("authorization_gate_passed", False))),
        check("20I-C003", "20H total_stop_rows", s20h.get("total_stop_rows"), 0, s20h.get("total_stop_rows") == 0),
        check("20I-C004", "20H decision_value", s20h.get("decision_value"), "UNSET", s20h.get("decision_value") == "UNSET"),
        check("20I-C005", "20H forbidden summary flags true", false_summary, 0, false_summary == 0),
        check("20I-C006", "20H artifact STOP rows", stop_count(auth_checks) + stop_count(safety20h), 0, stop_count(auth_checks) + stop_count(safety20h) == 0),
        check("20I-C007", "20H forbidden gates allowed", forbidden_gate_count(gates20h, "allowed_after_20h_success"), 0, forbidden_gate_count(gates20h, "allowed_after_20h_success") == 0),
        check("20I-C008", "backup manifest exists", lp(inputs["backup_manifest"]).exists(), True, lp(inputs["backup_manifest"]).exists()),
        check("20I-C009", "allowed value column present", bool(vcol), True, bool(vcol)),
        check("20I-C010", "allowed value rows", len(allowed), ">=4", len(allowed) >= 4),
        check("20I-C011", "allowed value duplicate rows", int(pd.Series(values).duplicated().sum()) if values else 999, 0, bool(values) and int(pd.Series(values).duplicated().sum()) == 0),
        check("20I-C012", "allowed value empty rows", int((pd.Series(values) == "").sum()) if values else 999, 0, bool(values) and int((pd.Series(values) == "").sum()) == 0),
        check("20I-C013", "allowed action-executing rows", action_rows, 0, action_rows == 0),
        check("20I-C014", "required field column present", bool(fcol), True, bool(fcol)),
        check("20I-C015", "required field rows", len(fields), ">=6", len(fields) >= 6),
        check("20I-C016", "required field duplicate rows", int(pd.Series(fvals).duplicated().sum()) if fvals else 999, 0, bool(fvals) and int(pd.Series(fvals).duplicated().sum()) == 0),
        check("20I-C017", "draft decision_value", draft["decision_value"], "UNSET", draft["decision_value"] == "UNSET"),
        check("20I-C018", "restricted draft true flags", sum(int(bool(draft.get(k, False))) for k in FALSE_DRAFT_FLAGS), 0, sum(int(bool(draft.get(k, False))) for k in FALSE_DRAFT_FLAGS) == 0),
    ])
    total_stop = stop_count(checks); success = total_stop == 0
    status = SUCCESS if success else "20I_STOP_REVIEW_VALUE_CAPTURE_DRAFT_OUTPUTS"
    s = safety(success); g = next_gates(success)
    write_csv(out / "gold_v2_20i_draft_checks.csv", checks); write_csv(out / "gold_v2_20i_safety_matrix.csv", s); write_csv(out / "gold_v2_20i_required_next_gates.csv", g)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True, "draft_ready": success,
        "draft_status": draft["draft_status"], "authorization_scope": draft["authorization_scope"], "decision_value": "UNSET",
        "decision_value_collected": False, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "actual_decision_collection_allowed": False, "actual_decision_collection_completed": False,
        "allowed_value_rows": int(len(allowed)), "required_field_rows": int(len(fields)), "total_stop_rows": int(total_stop),
        "signal_conditions_changed": False, "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_20I_OUTPUTS",
    }
    write_json(out / "gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_summary.json", summary)
    report = ["# GOLD V2 20I TIER2 source identity human decision value capture draft audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 20I prepared a still-UNSET actual decision value capture draft only.", "- No actual decision value was collected and no approval was made by this script.", "- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.", "", "## Draft checks", md_table(checks), "", "## Next gates", md_table(g), "", "## Safety", md_table(s)]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
