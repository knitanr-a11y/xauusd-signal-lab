#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_audit_only"
IN18AF = "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_audit_only"
IN18AB = "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only"
IN18AC = "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only"
REPORT = "GOLD_V2_18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AF = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REF_DIRS = [IN18AF, IN18AB, IN18AC]


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


def reference_summaries() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = fx_outputs()
    for name in REF_DIRS:
        d = base / name
        if not lp(d).exists():
            continue
        for f in d.glob("*summary.json"):
            try:
                out.append(read_json(f))
                break
            except Exception:
                pass
    return out


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18AH", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY", "Prepare final audit-only readiness summary only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AG.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AG.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18ag_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["blocker_review_only", True, True, "PASS"],
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
        ["next_gate_18ah_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AG-S001", "required inputs missing", "STOP"],
        ["18AG-S002", "18AF status not passed", "STOP"],
        ["18AG-S003", "decision collected or approval already made", "STOP"],
        ["18AG-S004", "upstream STOP rows present", "STOP"],
        ["18AG-S005", "blockers missing or clearable", "STOP"],
        ["18AG-S006", "blocker package summary unsafe", "STOP"],
        ["18AG-S007", "forbidden gate allowed", "STOP"],
        ["18AG-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18af, p18ab, p18ac = base / IN18AF, base / IN18AB, base / IN18AC
    inputs = {
        "summary_18af": p18af / "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_summary.json",
        "checks_18af": p18af / "gold_v2_18af_reconciliation_checks.csv",
        "gates_18af": p18af / "gold_v2_18af_required_next_gates.csv",
        "safety_18af": p18af / "gold_v2_18af_safety_matrix.csv",
        "report_18af": p18af / "GOLD_V2_18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "blockers_18ab": p18ab / "gold_v2_18ab_blockers_still_in_force.csv",
        "blocker_summary_18ac": p18ac / "gold_v2_18ac_blocker_package_summary.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_18ag_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AG-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18ag_blocker_review_checks.csv", checks)
        write_csv(out / "gold_v2_18ag_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "18AG_STOP_MISSING_INPUTS", "audit_only": True, "blocker_review_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_18AG_INPUTS"}
        write_json(out / "gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AG blocker review audit-only report\n\nStatus: `18AG_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18af = read_json(inputs["summary_18af"])
    checks18af = read_csv(inputs["checks_18af"])
    gates18af = read_csv(inputs["gates_18af"])
    safe18af = read_csv(inputs["safety_18af"])
    blockers = read_csv(inputs["blockers_18ab"])
    blocker_summary = read_csv(inputs["blocker_summary_18ac"])

    reviewed = blockers.copy()
    reviewed["reviewed_by_18ag"] = True
    reviewed["still_in_force_after_18ag"] = True
    write_csv(out / "gold_v2_18ag_blockers_still_in_force.csv", reviewed)

    status_bad = int((blockers.get("status", pd.Series(dtype=str)).astype(str) != "BLOCKED").sum()) if not blockers.empty else 999
    must_bad = int((~blockers.get("must_remain_blocked_before_human_intake", pd.Series(dtype=bool)).map(truthy)).sum()) if not blockers.empty else 999
    clear_bad = int(blockers.get("script_can_clear", pd.Series(dtype=bool)).map(truthy).sum()) if not blockers.empty else 999
    observed = {str(row.get("item", "")): str(row.get("observed", "")) for _, row in blocker_summary.iterrows()}
    blocker_rows_ok = observed.get("blocker_rows", "0").isdigit() and int(observed.get("blocker_rows", "0")) > 0
    remain_ok = observed.get("must_remain_blocked_false_rows") == "0"
    clear_ok = observed.get("script_can_clear_true_rows") == "0"
    template_ok = observed.get("template_decision_value") == "UNSET"
    upstream_stop = stop_count(checks18af) + stop_count(safe18af)
    forbidden_gates = forbidden_gate_count(gates18af, "allowed_after_18af_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in reference_summaries())
    checks = pd.DataFrame([
        check_row("18AG-C001", "18AF status", s18af.get("status"), EXPECTED_18AF, s18af.get("status") == EXPECTED_18AF),
        check_row("18AG-C002", "18AF package_reconciliation_passed", s18af.get("package_reconciliation_passed"), True, bool(s18af.get("package_reconciliation_passed", False))),
        check_row("18AG-C003", "18AF total_stop_rows", s18af.get("total_stop_rows"), 0, s18af.get("total_stop_rows") == 0),
        check_row("18AG-C004", "18AF decision_collected", s18af.get("decision_collected"), False, s18af.get("decision_collected") is False),
        check_row("18AG-C005", "18AF decision_made", s18af.get("decision_made"), False, s18af.get("decision_made") is False),
        check_row("18AG-C006", "18AF approval_granted", s18af.get("approval_granted"), False, s18af.get("approval_granted") is False),
        check_row("18AG-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("18AG-C008", "blocker rows present", len(blockers), ">0", len(blockers) > 0),
        check_row("18AG-C009", "blocker status not BLOCKED", status_bad, 0, status_bad == 0),
        check_row("18AG-C010", "must remain blocked false rows", must_bad, 0, must_bad == 0),
        check_row("18AG-C011", "script_can_clear true rows", clear_bad, 0, clear_bad == 0),
        check_row("18AG-C012", "summary blocker rows present", blocker_rows_ok, True, blocker_rows_ok),
        check_row("18AG-C013", "summary blockers remain blocked", remain_ok, True, remain_ok),
        check_row("18AG-C014", "summary script cannot clear blockers", clear_ok, True, clear_ok),
        check_row("18AG-C015", "summary template remains unset", template_ok, True, template_ok),
        check_row("18AG-C016", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("18AG-C017", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AG_STOP_REVIEW_BLOCKER_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18ag_blocker_review_checks.csv", checks)
    write_csv(out / "gold_v2_18ag_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18ag_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18ag_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocker_review_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18af_status": s18af.get("status"),
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
        "next_recommended_step": "18AH_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY" if success else "STOP_REVIEW_18AG_OUTPUTS",
    }
    write_json(out / "gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_summary.json", summary)
    report = [
        "# GOLD V2 18AG TIER2 source identity human decision intake readiness package blocker review audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AG reviewed readiness-package blockers only.",
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
