#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only"
IN20B = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
REPORT = "GOLD_V2_20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20B = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
AUTH_SCOPE = "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_DRAFT_FLAGS = [
    "approval_granted",
    "actual_decision_collection_allowed",
    "source_recovery_requested",
    "source_recovery_allowed",
    "source_identity_finalization_allowed",
    "source_identity_recovery_allowed",
    "ledger_source_of_truth_promotion_allowed",
    "oh_lc_replay_allowed",
    "live_evaluator_allowed",
    "live_or_final_implementation_allowed",
    "final_signal_allowed",
    "discord_send_allowed",
    "no_signal_discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
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


def forbidden_summary_count(s: dict[str, Any]) -> int:
    n = sum(int(bool(s.get(k, False))) for k in FORBIDDEN_FLAGS)
    ext = s.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20D", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY", "Content-audit the unset decision intake draft only.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20C; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20C.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20C.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20c_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["draft_load_smoke_only", True, True, "PASS"],
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
        ["next_gate_20d_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20C-S001", "required inputs missing", "STOP"],
        ["20C-S002", "20B status not passed", "STOP"],
        ["20C-S003", "draft failed to load", "STOP"],
        ["20C-S004", "draft no longer unset", "STOP"],
        ["20C-S005", "decision collection or approval allowed", "STOP"],
        ["20C-S006", "upstream STOP rows present", "STOP"],
        ["20C-S007", "restricted draft flag true", "STOP"],
        ["20C-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20b = base / IN20B
    inputs = {
        "summary_20b": p20b / "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json",
        "draft_20b": p20b / "gold_v2_20b_decision_intake_draft.json",
        "fields_20b": p20b / "gold_v2_20b_required_decision_fields.csv",
        "values_20b": p20b / "gold_v2_20b_allowed_decision_values.csv",
        "checks_20b": p20b / "gold_v2_20b_draft_checks.csv",
        "gates_20b": p20b / "gold_v2_20b_required_next_gates.csv",
        "safety_20b": p20b / "gold_v2_20b_safety_matrix.csv",
        "report_20b": p20b / "GOLD_V2_20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20c_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20c_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20C-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20c_load_checks.csv", checks)
        write_csv(out / "gold_v2_20c_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20c_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20C_STOP_MISSING_INPUTS",
            "audit_only": True,
            "draft_load_smoke_passed": False,
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
            "next_recommended_step": "STOP_REVIEW_20C_INPUTS",
        }
        write_json(out / "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20C draft load-smoke audit-only report\n\nStatus: `20C_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20b = read_json(inputs["summary_20b"])
    draft = read_json(inputs["draft_20b"])
    fields = read_csv(inputs["fields_20b"])
    values = read_csv(inputs["values_20b"])
    checks20b = read_csv(inputs["checks_20b"])
    gates20b = read_csv(inputs["gates_20b"])
    safety20b = read_csv(inputs["safety_20b"])

    unset_bad = sum(int(draft.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_true = sum(int(bool(draft.get(k, False))) for k in RESTRICTED_DRAFT_FLAGS)
    action_values = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    upstream_stop = stop_count(checks20b) + stop_count(safety20b)
    forbidden_gates = forbidden_gate_count(gates20b, "allowed_after_20b_success")
    forbidden_flags = forbidden_summary_count(s20b)

    draft_load = pd.DataFrame([
        check_row("20C-L001", "draft loads", True, True, True),
        check_row("20C-L002", "draft_status", draft.get("draft_status"), "DRAFT_ONLY_NOT_A_DECISION", draft.get("draft_status") == "DRAFT_ONLY_NOT_A_DECISION"),
        check_row("20C-L003", "authorization_scope", draft.get("authorization_scope"), AUTH_SCOPE, draft.get("authorization_scope") == AUTH_SCOPE),
        check_row("20C-L004", "draft decision_value", draft.get("decision_value"), "UNSET", draft.get("decision_value") == "UNSET"),
        check_row("20C-L005", "unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check_row("20C-L006", "evidence_acknowledged", draft.get("evidence_acknowledged"), False, draft.get("evidence_acknowledged") is False),
        check_row("20C-L007", "actual_decision_collection_allowed", draft.get("actual_decision_collection_allowed"), False, draft.get("actual_decision_collection_allowed") is False),
        check_row("20C-L008", "approval_granted", draft.get("approval_granted"), False, draft.get("approval_granted") is False),
        check_row("20C-L009", "restricted draft true flags", restricted_true, 0, restricted_true == 0),
        check_row("20C-L010", "required field rows", len(fields), ">=6", len(fields) >= 6),
        check_row("20C-L011", "allowed value rows", len(values), ">=4", len(values) >= 4),
        check_row("20C-L012", "allowed values execute no action", action_values, 0, action_values == 0),
    ])
    write_csv(out / "gold_v2_20c_draft_load_audit.csv", draft_load)

    checks = pd.DataFrame([
        check_row("20C-C001", "20B status", s20b.get("status"), EXPECTED_20B, s20b.get("status") == EXPECTED_20B),
        check_row("20C-C002", "20B draft_ready", s20b.get("draft_ready"), True, bool(s20b.get("draft_ready", False))),
        check_row("20C-C003", "20B total_stop_rows", s20b.get("total_stop_rows"), 0, s20b.get("total_stop_rows") == 0),
        check_row("20C-C004", "20B decision_value", s20b.get("decision_value"), "UNSET", s20b.get("decision_value") == "UNSET"),
        check_row("20C-C005", "20B decision_collected", s20b.get("decision_collected"), False, s20b.get("decision_collected") is False),
        check_row("20C-C006", "20B decision_made", s20b.get("decision_made"), False, s20b.get("decision_made") is False),
        check_row("20C-C007", "20B approval_granted", s20b.get("approval_granted"), False, s20b.get("approval_granted") is False),
        check_row("20C-C008", "20B actual_decision_collection_allowed", s20b.get("actual_decision_collection_allowed"), False, s20b.get("actual_decision_collection_allowed") is False),
        check_row("20C-C009", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20C-C010", "draft load audit STOP rows", stop_count(draft_load), 0, stop_count(draft_load) == 0),
        check_row("20C-C011", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20C-C012", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20C_STOP_REVIEW_DRAFT_LOAD_SMOKE_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20c_load_checks.csv", checks)
    write_csv(out / "gold_v2_20c_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20c_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "draft_load_smoke_passed": success,
        "draft_status": draft.get("draft_status"),
        "authorization_scope": draft.get("authorization_scope"),
        "decision_value": draft.get("decision_value"),
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "field_rows": int(len(fields)),
        "value_rows": int(len(values)),
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
        "next_recommended_step": "20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_20C_OUTPUTS",
    }
    write_json(out / "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 20C TIER2 source identity human decision intake draft load-smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20C load-smoked the unset actual decision intake draft package only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks",
        md_table(checks),
        "",
        "## Draft load audit",
        md_table(draft_load),
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
