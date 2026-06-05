#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_only"
IN18AD = "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only"
IN18AC = "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only"
REPORT = "GOLD_V2_18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AD = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REQUIRED_INDEX_ROLES = {
    "summary_18ab", "checks_18ab", "blockers_18ab", "gates_18ab", "safety_18ab", "report_18ab",
    "summary_18aa", "summary_18z", "summary_18y", "summary_18x",
    "template_18x", "fields_18x", "values_18x", "checks_18aa", "checks_18z", "checks_18y", "checks_18x",
}
REQUIRED_BLOCKER_ITEMS = {"blocker_rows", "must_remain_blocked_false_rows", "script_can_clear_true_rows", "template_decision_value"}
REF_DIRS = [
    "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only",
    "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
    "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only",
    "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only",
    "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only",
    IN18AC,
    IN18AD,
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


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def check_row(check_id: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": check_id, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def markdown_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        vals = [str(row[col]).replace("|", "\\|").replace("\n", " ") for col in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def forbidden_summary_count(summary: dict[str, Any]) -> int:
    count = sum(int(bool(summary.get(key, False))) for key in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    if isinstance(ext, dict):
        count += sum(int(bool(v)) for v in ext.values())
    else:
        count += 1
    return count


def collect_reference_summaries() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    base = fx_outputs()
    for dirname in REF_DIRS:
        folder = base / dirname
        if not lp(folder).exists():
            continue
        for candidate in folder.glob("*summary.json"):
            try:
                summaries.append(read_json(candidate))
                break
            except Exception:
                pass
    return summaries


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["18AF", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY", "Reconcile 18AC/18AD/18AE package evidence only.", bool(success)],
            ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AE.", False],
            ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AE.", False],
            ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
            ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
        ],
        columns=["next_step", "name", "purpose", "allowed_after_18ae_success"],
    )


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["audit_only", True, True, "PASS"],
            ["package_content_audit_only", True, True, "PASS"],
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
            ["next_gate_18af_only_after_success", bool(success), bool(success), "PASS"],
        ],
        columns=["safety_item", "observed", "expected", "status"],
    )


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["18AE-S001", "required inputs missing", "STOP"],
            ["18AE-S002", "18AD status not passed", "STOP"],
            ["18AE-S003", "decision collected or approval already made", "STOP"],
            ["18AE-S004", "upstream STOP rows present", "STOP"],
            ["18AE-S005", "package index content invalid", "STOP"],
            ["18AE-S006", "blocker summary content invalid", "STOP"],
            ["18AE-S007", "forbidden gate allowed", "STOP"],
            ["18AE-S008", "forbidden safety flag true", "STOP"],
        ],
        columns=["stop_id", "condition", "action"],
    )


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ad = base / IN18AD
    p18ac = base / IN18AC
    inputs = {
        "summary_18ad": p18ad / "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json",
        "load_checks_18ad": p18ad / "gold_v2_18ad_load_checks.csv",
        "index_audit_18ad": p18ad / "gold_v2_18ad_package_index_load_audit.csv",
        "blocker_audit_18ad": p18ad / "gold_v2_18ad_blocker_summary_load_audit.csv",
        "gates_18ad": p18ad / "gold_v2_18ad_required_next_gates.csv",
        "safety_18ad": p18ad / "gold_v2_18ad_safety_matrix.csv",
        "report_18ad": p18ad / "GOLD_V2_18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "index_18ac": p18ac / "gold_v2_18ac_evidence_package_index.csv",
        "blocker_summary_18ac": p18ac / "gold_v2_18ac_blocker_package_summary.csv",
    }
    input_audit = pd.DataFrame([{ "role": role, "path": str(path), "required": True, "exists": lp(path).exists()} for role, path in inputs.items()])
    write_csv(out / "gold_v2_18ae_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AE-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18ae_content_checks.csv", checks)
        write_csv(out / "gold_v2_18ae_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "18AE_STOP_MISSING_INPUTS",
            "audit_only": True,
            "package_content_audit_passed": False,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "total_stop_rows": 1,
            "next_recommended_step": "STOP_REVIEW_18AE_INPUTS",
        }
        write_json(out / "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AE readiness package content audit-only report\n\nStatus: `18AE_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ad = read_json(inputs["summary_18ad"])
    load_checks = read_csv(inputs["load_checks_18ad"])
    idx_audit = read_csv(inputs["index_audit_18ad"])
    blocker_audit = read_csv(inputs["blocker_audit_18ad"])
    gates18ad = read_csv(inputs["gates_18ad"])
    safe18ad = read_csv(inputs["safety_18ad"])
    idx18ac = read_csv(inputs["index_18ac"])
    blocker18ac = read_csv(inputs["blocker_summary_18ac"])

    roles = idx18ac.get("evidence_role", pd.Series(dtype=str)).astype(str).tolist()
    missing_roles = sorted(REQUIRED_INDEX_ROLES - set(roles))
    duplicate_roles = len(roles) - len(set(roles))
    package_use_bad = int((idx18ac.get("package_use", pd.Series(dtype=str)).astype(str) != "READINESS_PACKAGE_EVIDENCE_ONLY").sum()) if not idx18ac.empty else 999
    idx_content = pd.DataFrame(
        [
            check_row("18AE-I001", "required package roles missing", len(missing_roles), 0, len(missing_roles) == 0),
            check_row("18AE-I002", "duplicate package roles", duplicate_roles, 0, duplicate_roles == 0),
            check_row("18AE-I003", "non evidence-only package_use rows", package_use_bad, 0, package_use_bad == 0),
            check_row("18AE-I004", "18AD index load STOP rows", stop_count(idx_audit), 0, stop_count(idx_audit) == 0),
        ]
    )
    write_csv(out / "gold_v2_18ae_package_index_content_audit.csv", idx_content)

    observed = {str(row.get("item", "")): str(row.get("observed", "")) for _, row in blocker18ac.iterrows()}
    blocker_items_missing = sorted(REQUIRED_BLOCKER_ITEMS - set(observed.keys()))
    blocker_rows_ok = observed.get("blocker_rows", "0").isdigit() and int(observed.get("blocker_rows", "0")) > 0
    remain_ok = observed.get("must_remain_blocked_false_rows") == "0"
    clear_ok = observed.get("script_can_clear_true_rows") == "0"
    template_ok = observed.get("template_decision_value") == "UNSET"
    blocker_content = pd.DataFrame(
        [
            check_row("18AE-B001", "required blocker summary items missing", len(blocker_items_missing), 0, len(blocker_items_missing) == 0),
            check_row("18AE-B002", "blocker rows present", blocker_rows_ok, True, blocker_rows_ok),
            check_row("18AE-B003", "blockers remain blocked", remain_ok, True, remain_ok),
            check_row("18AE-B004", "script cannot clear blockers", clear_ok, True, clear_ok),
            check_row("18AE-B005", "template remains unset", template_ok, True, template_ok),
            check_row("18AE-B006", "18AD blocker load rows present", len(blocker_audit), ">0", len(blocker_audit) > 0),
        ]
    )
    write_csv(out / "gold_v2_18ae_blocker_summary_content_audit.csv", blocker_content)

    upstream_stop = stop_count(load_checks) + stop_count(safe18ad)
    forbidden_gates = forbidden_gate_count(gates18ad, "allowed_after_18ad_success")
    forbidden_flags = sum(forbidden_summary_count(summary) for summary in collect_reference_summaries())
    checks = pd.DataFrame(
        [
            check_row("18AE-C001", "18AD status", s18ad.get("status"), EXPECTED_18AD, s18ad.get("status") == EXPECTED_18AD),
            check_row("18AE-C002", "18AD package_load_smoke_passed", s18ad.get("package_load_smoke_passed"), True, bool(s18ad.get("package_load_smoke_passed", False))),
            check_row("18AE-C003", "18AD total_stop_rows", s18ad.get("total_stop_rows"), 0, s18ad.get("total_stop_rows") == 0),
            check_row("18AE-C004", "18AD decision_collected", s18ad.get("decision_collected"), False, s18ad.get("decision_collected") is False),
            check_row("18AE-C005", "18AD decision_made", s18ad.get("decision_made"), False, s18ad.get("decision_made") is False),
            check_row("18AE-C006", "18AD approval_granted", s18ad.get("approval_granted"), False, s18ad.get("approval_granted") is False),
            check_row("18AE-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
            check_row("18AE-C008", "package index content STOP rows", stop_count(idx_content), 0, stop_count(idx_content) == 0),
            check_row("18AE-C009", "blocker summary content STOP rows", stop_count(blocker_content), 0, stop_count(blocker_content) == 0),
            check_row("18AE-C010", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
            check_row("18AE-C011", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
        ]
    )
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AE_STOP_REVIEW_PACKAGE_CONTENT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18ae_content_checks.csv", checks)
    write_csv(out / "gold_v2_18ae_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18ae_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18ae_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "package_content_audit_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ad_status": s18ad.get("status"),
        "package_index_rows": int(len(idx18ac)),
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
        "next_recommended_step": "18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_18AE_OUTPUTS",
    }
    write_json(out / "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_summary.json", summary)
    report = [
        "# GOLD V2 18AE TIER2 source identity human decision intake readiness package content audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AE content-audited the 18AC readiness package only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Content checks",
        markdown_table(checks),
        "",
        "## Package index content audit",
        markdown_table(idx_content),
        "",
        "## Blocker summary content audit",
        markdown_table(blocker_content),
        "",
        "## Next gates",
        markdown_table(gates),
        "",
        "## Safety",
        markdown_table(sm),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
