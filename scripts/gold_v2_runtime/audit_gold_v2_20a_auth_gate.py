#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY"
OUT_DIR = "gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only"
IN19N = "gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only"
REPORT = "GOLD_V2_20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19N = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
AUTH_TEXT = "USER_AUTHORIZED_PROCEED_AFTER_19N_TO_ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION"
AUTH_SCOPE = "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_AUTH_FLAGS = [
    "actual_decision_collection_allowed",
    "approval_allowed",
    "source_recovery_allowed",
    "source_identity_finalization_allowed",
    "source_identity_recovery_allowed",
    "ledger_source_of_truth_promotion_allowed",
    "oh_lc_replay_allowed",
    "live_evaluator_allowed",
    "final_signal_allowed",
    "discord_send_allowed",
    "no_signal_discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
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
        ["20B", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY", "Prepare an audit-only draft for later actual decision intake; no decision value is collected.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20A; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20A.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20A.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20a_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["authorization_gate_only", True, True, "PASS"],
        ["authorization_scope_preparation_only", True, True, "PASS"],
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
        ["next_gate_20b_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20A-S001", "required inputs missing", "STOP"],
        ["20A-S002", "19N status not passed", "STOP"],
        ["20A-S003", "decision collected or approval already made", "STOP"],
        ["20A-S004", "upstream STOP rows present", "STOP"],
        ["20A-S005", "authorization scope broader than audit-only preparation", "STOP"],
        ["20A-S006", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19n = base / IN19N
    inputs = {
        "summary_19n": p19n / "gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_summary.json",
        "checks_19n": p19n / "gold_v2_19n_handoff_checks.csv",
        "note_19n": p19n / "gold_v2_19n_final_handoff_note.md",
        "gates_19n": p19n / "gold_v2_19n_required_next_gates.csv",
        "safety_19n": p19n / "gold_v2_19n_safety_matrix.csv",
        "report_19n": p19n / "GOLD_V2_19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20a_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20a_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20A-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20a_authorization_checks.csv", checks)
        write_csv(out / "gold_v2_20a_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20a_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20A_STOP_MISSING_INPUTS",
            "audit_only": True,
            "authorization_gate_passed": False,
            "authorization_scope": AUTH_SCOPE,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
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
            "next_recommended_step": "STOP_REVIEW_20A_INPUTS",
        }
        write_json(out / "gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20A authorization gate audit-only report\n\nStatus: `20A_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19n = read_json(inputs["summary_19n"])
    checks19n = read_csv(inputs["checks_19n"])
    gates19n = read_csv(inputs["gates_19n"])
    safety19n = read_csv(inputs["safety_19n"])
    note19n = lp(inputs["note_19n"]).read_text(encoding="utf-8")

    auth_record = pd.DataFrame([{
        "authorization_id": "GOLD_V2_20A_AUTH_20260606",
        "created_utc": now,
        "authorization_text": AUTH_TEXT,
        "authorization_scope": AUTH_SCOPE,
        "source": "current_chat_user_explicit_permission",
        "allows_next_audit_only_preparation": True,
        "actual_decision_collection_allowed": False,
        "approval_allowed": False,
        "source_recovery_allowed": False,
        "source_identity_finalization_allowed": False,
        "source_identity_recovery_allowed": False,
        "ledger_source_of_truth_promotion_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "discord_send_allowed": False,
        "no_signal_discord_send_allowed": False,
        "mt5_order_allowed": False,
        "ai_api_allowed": False,
        "live_hook_allowed": False,
    }])
    write_csv(out / "gold_v2_20a_authorization_record.csv", auth_record)

    restricted_true = int(auth_record[RESTRICTED_AUTH_FLAGS].applymap(truthy).sum(axis=1).iloc[0])
    upstream_stop = stop_count(checks19n) + stop_count(safety19n)
    forbidden_gates = forbidden_gate_count(gates19n, "allowed_after_19n_success")
    forbidden_flags = forbidden_summary_count(s19n)
    handoff_mentions_auth = "explicit human authorization" in note19n.lower()
    manual_gate_allowed = False
    if {"next_step", "allowed_after_19n_success"}.issubset(gates19n.columns):
        mg = gates19n[gates19n["next_step"].astype(str) == "AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_INTAKE"]
        manual_gate_allowed = bool(not mg.empty and mg["allowed_after_19n_success"].map(truthy).all())

    checks = pd.DataFrame([
        check_row("20A-C001", "19N status", s19n.get("status"), EXPECTED_19N, s19n.get("status") == EXPECTED_19N),
        check_row("20A-C002", "19N handoff_ready", s19n.get("handoff_ready"), True, bool(s19n.get("handoff_ready", False))),
        check_row("20A-C003", "19N total_stop_rows", s19n.get("total_stop_rows"), 0, s19n.get("total_stop_rows") == 0),
        check_row("20A-C004", "19N decision_collected", s19n.get("decision_collected"), False, s19n.get("decision_collected") is False),
        check_row("20A-C005", "19N decision_made", s19n.get("decision_made"), False, s19n.get("decision_made") is False),
        check_row("20A-C006", "19N approval_granted", s19n.get("approval_granted"), False, s19n.get("approval_granted") is False),
        check_row("20A-C007", "19N manual auth gate allowed", manual_gate_allowed, True, manual_gate_allowed),
        check_row("20A-C008", "19N note mentions explicit authorization", handoff_mentions_auth, True, handoff_mentions_auth),
        check_row("20A-C009", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20A-C010", "authorization scope", AUTH_SCOPE, "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY", AUTH_SCOPE == "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY"),
        check_row("20A-C011", "restricted authorization true flags", restricted_true, 0, restricted_true == 0),
        check_row("20A-C012", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20A-C013", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20A_STOP_REVIEW_AUTHORIZATION_GATE_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20a_authorization_checks.csv", checks)
    write_csv(out / "gold_v2_20a_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20a_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "authorization_gate_passed": success,
        "authorization_text": AUTH_TEXT,
        "authorization_scope": AUTH_SCOPE,
        "upstream_19n_status": s19n.get("status"),
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
        "next_recommended_step": "20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY" if success else "STOP_REVIEW_20A_OUTPUTS",
    }
    write_json(out / "gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json", summary)
    report = [
        "# GOLD V2 20A TIER2 source identity human decision intake authorization gate audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20A records audit-only authorization to prepare the next actual decision intake audit-only draft step.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Authorization checks",
        md_table(checks),
        "",
        "## Authorization record",
        md_table(auth_record),
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
