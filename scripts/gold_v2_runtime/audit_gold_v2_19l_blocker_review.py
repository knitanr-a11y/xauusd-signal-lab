#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_audit_only"
IN19K = "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only"
IN19E = "gold_v2_19e_tier2_source_identity_human_decision_intake_actual_decision_plan_blocker_review_audit_only"
REPORT = "GOLD_V2_19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19K = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
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
        ["19M", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY", "Prepare final audit-only summary for the still-unset template.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19L.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19L.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19l_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["template_blocker_review_only", True, True, "PASS"],
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
        ["next_gate_19m_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19L-S001", "required inputs missing", "STOP"],
        ["19L-S002", "19K status not passed", "STOP"],
        ["19L-S003", "decision collected or approval already made", "STOP"],
        ["19L-S004", "upstream STOP rows present", "STOP"],
        ["19L-S005", "blockers missing or not blocked", "STOP"],
        ["19L-S006", "blocker script clearable", "STOP"],
        ["19L-S007", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19k = base / IN19K
    p19e = base / IN19E
    inputs = {
        "summary_19k": p19k / "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_summary.json",
        "checks_19k": p19k / "gold_v2_19k_reconciliation_checks.csv",
        "gates_19k": p19k / "gold_v2_19k_required_next_gates.csv",
        "safety_19k": p19k / "gold_v2_19k_safety_matrix.csv",
        "report_19k": p19k / "GOLD_V2_19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "blockers_19e": p19e / "gold_v2_19e_blockers_still_in_force.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19l_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19L-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19l_blocker_review_checks.csv", checks)
        write_csv(out / "gold_v2_19l_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19L_STOP_MISSING_INPUTS", "audit_only": True, "blocker_review_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19L_INPUTS"}
        write_json(out / "gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19L template blocker review audit-only report\n\nStatus: `19L_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19k = read_json(inputs["summary_19k"])
    checks19k = read_csv(inputs["checks_19k"])
    gates19k = read_csv(inputs["gates_19k"])
    safety19k = read_csv(inputs["safety_19k"])
    blockers = read_csv(inputs["blockers_19e"])
    reviewed = blockers.copy()
    reviewed["reviewed_by_19l"] = True
    reviewed["still_in_force_after_19l"] = True
    write_csv(out / "gold_v2_19l_blockers_still_in_force.csv", reviewed)

    status_bad = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    clear_bad = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    if "still_in_force_after_19e" in blockers.columns:
        force_bad = int((~blockers["still_in_force_after_19e"].map(truthy)).sum())
    else:
        force_bad = 999
    upstream_stop = stop_count(checks19k) + stop_count(safety19k)
    forbidden_gates = forbidden_gate_count(gates19k, "allowed_after_19k_success")
    forbidden_flags = forbidden_summary_count(s19k)
    checks = pd.DataFrame([
        check_row("19L-C001", "19K status", s19k.get("status"), EXPECTED_19K, s19k.get("status") == EXPECTED_19K),
        check_row("19L-C002", "19K template_reconciliation_passed", s19k.get("template_reconciliation_passed"), True, bool(s19k.get("template_reconciliation_passed", False))),
        check_row("19L-C003", "19K total_stop_rows", s19k.get("total_stop_rows"), 0, s19k.get("total_stop_rows") == 0),
        check_row("19L-C004", "19K decision_collected", s19k.get("decision_collected"), False, s19k.get("decision_collected") is False),
        check_row("19L-C005", "19K decision_made", s19k.get("decision_made"), False, s19k.get("decision_made") is False),
        check_row("19L-C006", "19K approval_granted", s19k.get("approval_granted"), False, s19k.get("approval_granted") is False),
        check_row("19L-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19L-C008", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        check_row("19L-C009", "blocker status not BLOCKED", status_bad, 0, status_bad == 0),
        check_row("19L-C010", "script_can_clear true rows", clear_bad, 0, clear_bad == 0),
        check_row("19L-C011", "not still in force after 19E rows", force_bad, 0, force_bad == 0),
        check_row("19L-C012", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("19L-C013", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19L_STOP_REVIEW_BLOCKER_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19l_blocker_review_checks.csv", checks)
    write_csv(out / "gold_v2_19l_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19l_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19l_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocker_review_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19k_status": s19k.get("status"),
        "remaining_blockers": int(len(blockers)),
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
        "next_recommended_step": "19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY" if success else "STOP_REVIEW_19L_OUTPUTS",
    }
    write_json(out / "gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_summary.json", summary)
    report = [
        "# GOLD V2 19L TIER2 source identity human decision intake actual decision template blocker review audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19L reviewed actual decision template blockers only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Blocker review checks",
        md_table(checks),
        "",
        "## Blockers still in force",
        md_table(reviewed),
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
