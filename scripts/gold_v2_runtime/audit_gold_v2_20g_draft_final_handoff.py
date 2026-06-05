#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY"
OUT_DIR = "gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only"
IN20F = "gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only"
REPORT = "GOLD_V2_20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20F = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REQUIRED_NOTE_PHRASES = [
    "draft package is still unset",
    "no actual decision value has been collected",
    "no approval has been granted",
    "actual decision collection is still blocked",
    "no source recovery",
    "no source identity finalization",
    "no live evaluator",
    "no final signal",
    "no discord send",
    "no mt5 order",
    "no ai api",
    "no live hook",
    "no no_signal discord",
    "explicit human authorization gate is required",
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
        ["AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE", "A later human authorization gate is required before any actual decision value capture.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "Still blocked after 20G; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "Blocked after 20G.", False],
        ["SOURCE_RECOVERY", "Blocked after 20G.", False],
        ["LIVE", "Blocked after 20G.", False],
        ["FINAL_SIGNAL", "Blocked after 20G.", False],
    ], columns=["next_step", "purpose", "allowed_after_20g_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["draft_final_handoff_only", True, True, "PASS"],
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
        ["await_explicit_human_authorization_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20G-S001", "required inputs missing", "STOP"],
        ["20G-S002", "20F status not passed", "STOP"],
        ["20G-S003", "20F STOP rows present", "STOP"],
        ["20G-S004", "decision value no longer UNSET or decision/approval collected", "STOP"],
        ["20G-S005", "actual decision collection allowed", "STOP"],
        ["20G-S006", "forbidden gate or summary flag allowed", "STOP"],
        ["20G-S007", "handoff note missing required prohibition phrase", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def build_note(now: str) -> str:
    return "\n".join([
        "# GOLD V2 20G final audit-only handoff note",
        "",
        f"Created UTC: {now}",
        "",
        "This draft package is still unset.",
        "No actual decision value has been collected.",
        "No approval has been granted.",
        "Actual decision collection is still blocked.",
        "",
        "Required prohibitions retained:",
        "- no source recovery",
        "- no source identity finalization",
        "- no live evaluator",
        "- no final signal",
        "- no discord send",
        "- no mt5 order",
        "- no ai api",
        "- no live hook",
        "- no no_signal discord",
        "",
        "An explicit human authorization gate is required before any later actual decision value capture step.",
        "",
        "Next state:",
        "AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE",
    ])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20f = base / IN20F
    inputs = {
        "summary_20f": p20f / "gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json",
        "final_checks_20f": p20f / "gold_v2_20f_final_checks.csv",
        "gates_20f": p20f / "gold_v2_20f_required_next_gates.csv",
        "safety_20f": p20f / "gold_v2_20f_safety_matrix.csv",
        "report_20f": p20f / "GOLD_V2_20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20g_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20g_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20G-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20g_handoff_checks.csv", checks)
        write_csv(out / "gold_v2_20g_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20g_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20G_STOP_MISSING_INPUTS",
            "audit_only": True,
            "handoff_ready": False,
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
            "next_recommended_step": "STOP_REVIEW_20G_INPUTS",
        }
        write_json(out / "gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20G draft final handoff audit-only report\n\nStatus: `20G_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20f = read_json(inputs["summary_20f"])
    final_checks = read_csv(inputs["final_checks_20f"])
    gates20f = read_csv(inputs["gates_20f"])
    safety20f = read_csv(inputs["safety_20f"])
    note = build_note(now)
    write_text(out / "gold_v2_20g_final_handoff_note.md", note)

    note_lower = note.lower()
    missing_phrases = [p for p in REQUIRED_NOTE_PHRASES if p.lower() not in note_lower]
    upstream_stop = stop_count(final_checks) + stop_count(safety20f)
    forbidden_gates = forbidden_gate_count(gates20f, "allowed_after_20f_success")
    forbidden_flags = forbidden_summary_count(s20f)
    decision_flags_true = sum(int(bool(s20f.get(k, False))) for k in ("decision_collected", "decision_made", "approval_granted", "actual_decision_collection_allowed"))

    checks = pd.DataFrame([
        check_row("20G-C001", "20F status", s20f.get("status"), EXPECTED_20F, s20f.get("status") == EXPECTED_20F),
        check_row("20G-C002", "20F final_audit_ready", s20f.get("final_audit_ready"), True, bool(s20f.get("final_audit_ready", False))),
        check_row("20G-C003", "20F total_stop_rows", s20f.get("total_stop_rows"), 0, s20f.get("total_stop_rows") == 0),
        check_row("20G-C004", "20F decision_value", s20f.get("decision_value"), "UNSET", s20f.get("decision_value") == "UNSET"),
        check_row("20G-C005", "20F decision/approval/collection flags true", decision_flags_true, 0, decision_flags_true == 0),
        check_row("20G-C006", "20F final/safety STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20G-C007", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20G-C008", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
        check_row("20G-C009", "handoff note missing required phrases", len(missing_phrases), 0, len(missing_phrases) == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20G_STOP_REVIEW_DRAFT_FINAL_HANDOFF_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20g_handoff_checks.csv", checks)
    write_csv(out / "gold_v2_20g_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20g_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "handoff_ready": success,
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
        "next_recommended_step": "AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE" if success else "STOP_REVIEW_20G_OUTPUTS",
    }
    write_json(out / "gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json", summary)
    report = [
        "# GOLD V2 20G TIER2 source identity human decision intake draft final handoff audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20G prepared the final audit-only handoff note for the unset actual decision intake draft package only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Handoff checks",
        md_table(checks),
        "",
        "## Handoff note",
        note,
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
