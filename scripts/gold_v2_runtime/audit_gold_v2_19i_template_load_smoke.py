#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only"
IN19H = "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only"
REPORT = "GOLD_V2_19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19H = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
RESTRICTED_TEMPLATE_FLAGS = [
    "approval_granted",
    "source_recovery_requested",
    "source_recovery_allowed",
    "source_identity_finalization_allowed",
    "live_or_final_implementation_allowed",
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
    "no_signal_discord_notified",
    "script_executes_action",
]
UNSET_FIELDS = [
    "decision_id",
    "decision_timestamp_utc",
    "decision_value",
    "human_reviewer",
    "explicit_phrase",
    "notes",
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


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["19J", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY", "Content-audit the still-unset template only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19I.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19I.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19i_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["template_load_smoke_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
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
        ["next_gate_19j_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19I-S001", "required inputs missing", "STOP"],
        ["19I-S002", "19H status not passed", "STOP"],
        ["19I-S003", "decision collected or approval already made", "STOP"],
        ["19I-S004", "upstream STOP rows present", "STOP"],
        ["19I-S005", "template failed to load", "STOP"],
        ["19I-S006", "template contains decision or approval", "STOP"],
        ["19I-S007", "template restricted flag true", "STOP"],
        ["19I-S008", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19h = base / IN19H
    inputs = {
        "summary_19h": p19h / "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_summary.json",
        "checks_19h": p19h / "gold_v2_19h_template_checks.csv",
        "template_19h": p19h / "gold_v2_19h_actual_decision_template.json",
        "fields_19h": p19h / "gold_v2_19h_required_decision_fields.csv",
        "values_19h": p19h / "gold_v2_19h_allowed_decision_values.csv",
        "gates_19h": p19h / "gold_v2_19h_required_next_gates.csv",
        "safety_19h": p19h / "gold_v2_19h_safety_matrix.csv",
        "report_19h": p19h / "GOLD_V2_19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19i_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19I-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19i_template_load_checks.csv", checks)
        write_csv(out / "gold_v2_19i_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19I_STOP_MISSING_INPUTS", "audit_only": True, "template_load_smoke_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19I_INPUTS"}
        write_json(out / "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19I template load-smoke audit-only report\n\nStatus: `19I_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19h = read_json(inputs["summary_19h"])
    checks19h = read_csv(inputs["checks_19h"])
    template = read_json(inputs["template_19h"])
    fields = read_csv(inputs["fields_19h"])
    values = read_csv(inputs["values_19h"])
    gates19h = read_csv(inputs["gates_19h"])
    safety19h = read_csv(inputs["safety_19h"])

    unset_bad = sum(int(template.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_true = sum(int(bool(template.get(k, False))) for k in RESTRICTED_TEMPLATE_FLAGS)
    field_rows = int(len(fields))
    value_rows = int(len(values))
    action_values = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    template_audit = pd.DataFrame([
        check_row("19I-T001", "template loads", True, True, True),
        check_row("19I-T002", "template_status", template.get("template_status"), "TEMPLATE_ONLY_NOT_A_DECISION", template.get("template_status") == "TEMPLATE_ONLY_NOT_A_DECISION"),
        check_row("19I-T003", "unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check_row("19I-T004", "evidence_acknowledged", template.get("evidence_acknowledged"), False, template.get("evidence_acknowledged") is False),
        check_row("19I-T005", "restricted template true flags", restricted_true, 0, restricted_true == 0),
        check_row("19I-T006", "required field rows", field_rows, ">=6", field_rows >= 6),
        check_row("19I-T007", "allowed value rows", value_rows, ">=4", value_rows >= 4),
        check_row("19I-T008", "values execute no action", action_values, 0, action_values == 0),
    ])
    write_csv(out / "gold_v2_19i_template_load_audit.csv", template_audit)

    upstream_stop = stop_count(checks19h) + stop_count(safety19h)
    forbidden_gates = forbidden_gate_count(gates19h, "allowed_after_19h_success")
    checks = pd.DataFrame([
        check_row("19I-C001", "19H status", s19h.get("status"), EXPECTED_19H, s19h.get("status") == EXPECTED_19H),
        check_row("19I-C002", "19H template_prepared", s19h.get("template_prepared"), True, bool(s19h.get("template_prepared", False))),
        check_row("19I-C003", "19H total_stop_rows", s19h.get("total_stop_rows"), 0, s19h.get("total_stop_rows") == 0),
        check_row("19I-C004", "19H decision_collected", s19h.get("decision_collected"), False, s19h.get("decision_collected") is False),
        check_row("19I-C005", "19H decision_made", s19h.get("decision_made"), False, s19h.get("decision_made") is False),
        check_row("19I-C006", "19H approval_granted", s19h.get("approval_granted"), False, s19h.get("approval_granted") is False),
        check_row("19I-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19I-C008", "template load audit STOP rows", stop_count(template_audit), 0, stop_count(template_audit) == 0),
        check_row("19I-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19I_STOP_REVIEW_TEMPLATE_LOAD_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19i_template_load_checks.csv", checks)
    write_csv(out / "gold_v2_19i_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19i_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19i_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "template_load_smoke_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "template_status": template.get("template_status"),
        "decision_value": template.get("decision_value"),
        "upstream_19h_status": s19h.get("status"),
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
        "next_recommended_step": "19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_19I_OUTPUTS",
    }
    write_json(out / "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 19I TIER2 source identity human decision intake actual decision template load-smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19I load-smoked the still-unset actual human decision template only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks",
        md_table(checks),
        "",
        "## Template load audit",
        md_table(template_audit),
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
