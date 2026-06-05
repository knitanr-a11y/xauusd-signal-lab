#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only"
IN18AC = "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only"
REPORT = "GOLD_V2_18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AC = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REF_DIRS = [
    "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only",
    "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only",
    "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only",
    "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only",
    "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only",
    "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only",
    "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only",
    "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only",
    "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only",
    "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only",
    "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only",
    "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only",
    "gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only",
    "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only",
    "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
    "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only",
    "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only",
    "gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only",
    IN18AC,
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
    return {
        "check_id": check_id,
        "check": name,
        "observed": observed,
        "expected": expected,
        "status": "PASS" if ok else "STOP",
    }


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
            ["18AE", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY", "Content-audit 18AC readiness package only.", bool(success)],
            ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AD.", False],
            ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AD.", False],
            ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
            ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
        ],
        columns=["next_step", "name", "purpose", "allowed_after_18ad_success"],
    )


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["audit_only", True, True, "PASS"],
            ["package_load_smoke_only", True, True, "PASS"],
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
            ["next_gate_18ae_only_after_success", bool(success), bool(success), "PASS"],
        ],
        columns=["safety_item", "observed", "expected", "status"],
    )


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["18AD-S001", "required inputs missing", "STOP"],
            ["18AD-S002", "18AC status not passed", "STOP"],
            ["18AD-S003", "decision collected or approval already made", "STOP"],
            ["18AD-S004", "upstream STOP rows present", "STOP"],
            ["18AD-S005", "package index missing entries or non-evidence use", "STOP"],
            ["18AD-S006", "blocker summary unsafe", "STOP"],
            ["18AD-S007", "forbidden gate allowed", "STOP"],
            ["18AD-S008", "forbidden safety flag true", "STOP"],
        ],
        columns=["stop_id", "condition", "action"],
    )


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ac = base / IN18AC
    inputs = {
        "summary_18ac": p18ac / "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json",
        "checks_18ac": p18ac / "gold_v2_18ac_package_checks.csv",
        "index_18ac": p18ac / "gold_v2_18ac_evidence_package_index.csv",
        "blocker_summary_18ac": p18ac / "gold_v2_18ac_blocker_package_summary.csv",
        "gates_18ac": p18ac / "gold_v2_18ac_required_next_gates.csv",
        "safety_18ac": p18ac / "gold_v2_18ac_safety_matrix.csv",
        "report_18ac": p18ac / "GOLD_V2_18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame(
        [{"role": role, "path": str(path), "required": True, "exists": lp(path).exists()} for role, path in inputs.items()]
    )
    write_csv(out / "gold_v2_18ad_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AD-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18ad_load_checks.csv", checks)
        write_csv(out / "gold_v2_18ad_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "18AD_STOP_MISSING_INPUTS",
            "audit_only": True,
            "package_load_smoke_passed": False,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "total_stop_rows": 1,
            "next_recommended_step": "STOP_REVIEW_18AD_INPUTS",
        }
        write_json(out / "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AD readiness package load-smoke audit-only report\n\nStatus: `18AD_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ac = read_json(inputs["summary_18ac"])
    checks18ac = read_csv(inputs["checks_18ac"])
    idx = read_csv(inputs["index_18ac"])
    blocker_summary = read_csv(inputs["blocker_summary_18ac"])
    gates18ac = read_csv(inputs["gates_18ac"])
    safe18ac = read_csv(inputs["safety_18ac"])

    idx_audit = idx.copy()
    if "path" in idx_audit.columns:
        idx_audit["path_exists_now"] = idx_audit["path"].astype(str).map(lambda value: lp(Path(value)).exists())
    else:
        idx_audit["path_exists_now"] = False
    idx_audit["package_use_ok"] = idx_audit.get("package_use", pd.Series(dtype=str)).astype(str).eq("READINESS_PACKAGE_EVIDENCE_ONLY")
    idx_audit["status"] = (idx_audit["path_exists_now"] & idx_audit["package_use_ok"]).map(lambda ok: "PASS" if bool(ok) else "STOP")
    write_csv(out / "gold_v2_18ad_package_index_load_audit.csv", idx_audit)

    observed = {str(row.get("item", "")): str(row.get("observed", "")) for _, row in blocker_summary.iterrows()}
    blocker_rows_ok = observed.get("blocker_rows", "0").isdigit() and int(observed.get("blocker_rows", "0")) > 0
    remain_ok = observed.get("must_remain_blocked_false_rows") == "0"
    clear_ok = observed.get("script_can_clear_true_rows") == "0"
    template_ok = observed.get("template_decision_value") == "UNSET"
    blocker_audit = blocker_summary.copy()
    blocker_audit["load_smoke_checked"] = True
    write_csv(out / "gold_v2_18ad_blocker_summary_load_audit.csv", blocker_audit)

    upstream_stop = stop_count(checks18ac) + stop_count(safe18ac)
    forbidden_gates = forbidden_gate_count(gates18ac, "allowed_after_18ac_success")
    forbidden_flags = sum(forbidden_summary_count(summary) for summary in collect_reference_summaries())
    checks = pd.DataFrame(
        [
            check_row("18AD-C001", "18AC status", s18ac.get("status"), EXPECTED_18AC, s18ac.get("status") == EXPECTED_18AC),
            check_row("18AD-C002", "18AC readiness_package_prepared", s18ac.get("readiness_package_prepared"), True, bool(s18ac.get("readiness_package_prepared", False))),
            check_row("18AD-C003", "18AC total_stop_rows", s18ac.get("total_stop_rows"), 0, s18ac.get("total_stop_rows") == 0),
            check_row("18AD-C004", "18AC decision_collected", s18ac.get("decision_collected"), False, s18ac.get("decision_collected") is False),
            check_row("18AD-C005", "18AC decision_made", s18ac.get("decision_made"), False, s18ac.get("decision_made") is False),
            check_row("18AD-C006", "18AC approval_granted", s18ac.get("approval_granted"), False, s18ac.get("approval_granted") is False),
            check_row("18AD-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
            check_row("18AD-C008", "package index STOP rows", stop_count(idx_audit), 0, stop_count(idx_audit) == 0),
            check_row("18AD-C009", "blocker rows present", blocker_rows_ok, True, blocker_rows_ok),
            check_row("18AD-C010", "blockers remain blocked", remain_ok, True, remain_ok),
            check_row("18AD-C011", "script cannot clear blockers", clear_ok, True, clear_ok),
            check_row("18AD-C012", "template remains unset", template_ok, True, template_ok),
            check_row("18AD-C013", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
            check_row("18AD-C014", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
        ]
    )
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AD_STOP_REVIEW_PACKAGE_LOAD_SMOKE_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18ad_load_checks.csv", checks)
    write_csv(out / "gold_v2_18ad_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18ad_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18ad_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "package_load_smoke_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ac_status": s18ac.get("status"),
        "package_index_rows": int(len(idx)),
        "total_stop_rows": int(total_stop),
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_18AD_OUTPUTS",
    }
    write_json(out / "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 18AD TIER2 source identity human decision intake readiness package load-smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AD load-smoked the 18AC readiness package only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks",
        markdown_table(checks),
        "",
        "## Package index load audit",
        markdown_table(idx_audit),
        "",
        "## Blocker summary load audit",
        markdown_table(blocker_audit),
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
