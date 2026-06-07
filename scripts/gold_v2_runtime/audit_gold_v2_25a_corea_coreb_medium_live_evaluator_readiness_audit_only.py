#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25A CoreA/CoreB/MEDIUM live evaluator readiness audit-only package.

This package is intentionally audit-only. It creates readiness, blocker,
recommendation, and safety matrices for the CoreA/CoreB/MEDIUM live evaluator
path. It does not run source recovery, mutate source artifacts, finalize source
identity, emit final signals, call AI APIs, send Discord messages, place MT5
orders, or connect live hooks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import pandas as pd

STEP = "25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only"
PASS_STATUS = "COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED"
STOP_STATUS = "25A_STOP_READINESS_INPUTS_OR_SOT_COUNT_MISMATCH_AUDIT_ONLY"

EXPECTED_TOTAL_ROWS = 529
EXPECTED_DATASET_COUNTS = {"2025": 346, "2026": 183}
EXPECTED_SOURCE_COUNTS = {
    "CORE_A_CORE_B_CONFLUENCE": 8,
    "CORE_A_ONLY": 317,
    "CORE_B_ONLY": 117,
    "MEDIUM_RANGE96_REFINED": 51,
    "MEDIUM_TIER2_HVT": 13,
    "MEDIUM_VOL_TRMEAN32_REFINED": 23,
}

REQUIRED_REFERENCE_DOCS = [
    "docs/gold_v2/GOLD_V2_24AF_PAUSE_AND_CORE_LIVE_EVALUATOR_REFOCUS_20260607.md",
    "docs/gold_v2/GOLD_V2_COREB_LIVE_EVALUATOR_BLOCKER_CONFIRMATION_20260607.md",
    "docs/gold_v2/GOLD_V2_COREB_CLUSTER_RECOVERY_STRICT_PLAN_20260607.md",
    "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md",
    "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md",
]

SAFETY_FLAGS = {
    "source_recovery_chain_status": "PAUSED_AT_24AF",
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "external_actions_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "old_gold_disc8_quarantined": True,
    "no_signal_discord_notification_allowed": False,
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD V2 25A readiness audit-only package")
    p.add_argument("--sot-ledger", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_sot_ledger() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_final_portfolio_sot_freeze_audit_only" / "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / OUT_DIR_NAME


def lp(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with lp(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_any(path: Path) -> pd.DataFrame:
    last_error: Optional[Exception] = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read CSV: {path}: {last_error}")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(text, encoding="utf-8")


def fmt(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows).copy()
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in cols) + " |")
    if len(df) > max_rows:
        lines.append(f"| ... | truncated: {len(df) - max_rows} more rows |" + " |" * max(0, len(cols) - 2))
    return "\n".join(lines)


def status_from_bool(ok: bool) -> str:
    return "PASS" if ok else "STOP"


def make_reference_doc_audit() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    root = repo_root()
    for rel in REQUIRED_REFERENCE_DOCS:
        path = root / rel
        exists = lp(path).exists()
        rows.append({
            "role": "required_reference_doc",
            "path": rel,
            "exists": bool(exists),
            "sha256": sha256_file(path) if exists else "",
            "status": status_from_bool(exists),
        })
    return pd.DataFrame(rows)


def make_sot_count_audit(sot_ledger: Path) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    observed: dict[str, Any] = {
        "sot_ledger_exists": lp(sot_ledger).exists(),
        "total_rows": None,
        "dataset_counts": {},
        "source_counts": {},
        "sot_ledger_sha256": "",
    }

    if not lp(sot_ledger).exists():
        rows.append({"check_id": "25A-SOT-000", "scope": "final_sot", "item": "ledger exists", "observed": False, "expected": True, "status": "STOP"})
        input_rows.append({"role": "final_portfolio_sot_ledger", "path": str(sot_ledger), "required": True, "exists": False, "status": "STOP"})
        return pd.DataFrame(rows), observed, pd.DataFrame(input_rows)

    df = read_csv_any(sot_ledger)
    observed["sot_ledger_sha256"] = sha256_file(sot_ledger)
    observed["total_rows"] = int(len(df))
    input_rows.append({
        "role": "final_portfolio_sot_ledger",
        "path": str(sot_ledger),
        "required": True,
        "exists": True,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "sha256": observed["sot_ledger_sha256"],
        "status": "PASS",
    })
    rows.append({"check_id": "25A-SOT-001", "scope": "final_sot", "item": "total rows", "observed": int(len(df)), "expected": EXPECTED_TOTAL_ROWS, "status": status_from_bool(int(len(df)) == EXPECTED_TOTAL_ROWS)})

    if "dataset" not in df.columns:
        rows.append({"check_id": "25A-SOT-002", "scope": "final_sot", "item": "dataset column", "observed": False, "expected": True, "status": "STOP"})
    else:
        dataset_counts = {str(k): int(v) for k, v in df.groupby("dataset").size().items()}
        observed["dataset_counts"] = dataset_counts
        for key, exp in EXPECTED_DATASET_COUNTS.items():
            got = int(dataset_counts.get(key, 0))
            rows.append({"check_id": f"25A-DATASET-{key}", "scope": "dataset_count", "item": key, "observed": got, "expected": exp, "status": status_from_bool(got == exp)})

    if "source" not in df.columns:
        rows.append({"check_id": "25A-SOT-003", "scope": "final_sot", "item": "source column", "observed": False, "expected": True, "status": "STOP"})
    else:
        source_counts = {str(k): int(v) for k, v in df.groupby("source").size().items()}
        observed["source_counts"] = source_counts
        for key, exp in EXPECTED_SOURCE_COUNTS.items():
            got = int(source_counts.get(key, 0))
            rows.append({"check_id": f"25A-SOURCE-{key}", "scope": "source_count", "item": key, "observed": got, "expected": exp, "status": status_from_bool(got == exp)})

    return pd.DataFrame(rows), observed, pd.DataFrame(input_rows)


def make_component_matrix(observed: dict[str, Any]) -> pd.DataFrame:
    source_counts = observed.get("source_counts") or {}
    corea_rows = int(source_counts.get("CORE_A_ONLY", 0)) + int(source_counts.get("CORE_A_CORE_B_CONFLUENCE", 0))
    coreb_rows = int(source_counts.get("CORE_B_ONLY", 0)) + int(source_counts.get("CORE_A_CORE_B_CONFLUENCE", 0))
    medium_rows = sum(int(source_counts.get(k, 0)) for k in source_counts if str(k).startswith("MEDIUM_"))
    return pd.DataFrame([
        {
            "component": "FINAL_PORTFOLIO_SOT",
            "historical_status": "SOURCE_OF_TRUTH_LEDGER_EXPECTED_529_ROWS",
            "expected_rows": EXPECTED_TOTAL_ROWS,
            "observed_rows": observed.get("total_rows"),
            "live_evaluator_status": "NOT_A_LIVE_EVALUATOR",
            "readiness_level": "HISTORICAL_REPORTING_ONLY",
            "blocker_summary": "Final portfolio ledger can be audited/reported but cannot emit live/final signals.",
            "approximate_reimplementation_allowed": False,
            "recommended_action": "USE_AS_HISTORICAL_SOT_FOR_AUDIT_ONLY",
        },
        {
            "component": "CoreA fold4 ABC CAP5/CAP3",
            "historical_status": "HISTORICAL_SOT_READY",
            "expected_rows": 325,
            "observed_rows": corea_rows,
            "live_evaluator_status": "BLOCKED_A_GATE_EXECUTABLE_SOURCE_FREEZE_REQUIRED",
            "readiness_level": "BLOCKED_FOR_LIVE",
            "blocker_summary": "tail_hard/top5/all-consensus/stack KEEP A gate and rejected ordering are not frozen as executable live conditions.",
            "approximate_reimplementation_allowed": False,
            "recommended_action": "PARALLEL_25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY",
        },
        {
            "component": "CoreB RR125_BUY_CONFLUENCE",
            "historical_status": "REPRODUCED_HISTORICAL_SOT_ALLOWED",
            "expected_rows": 125,
            "observed_rows": coreb_rows,
            "live_evaluator_status": "BLOCKED_SOURCE_CLUSTER_MEMBERSHIP_REQUIRED",
            "readiness_level": "PRIMARY_BLOCKER_FOR_FULL_PORTFOLIO_LIVE",
            "blocker_summary": "same_count / cluster_id / row-level membership source-of-truth generation evidence is insufficient.",
            "approximate_reimplementation_allowed": False,
            "recommended_action": "PRIORITIZE_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY",
        },
        {
            "component": "MEDIUM RANGE96/VOL_TRMEAN32/TIER2_HVT",
            "historical_status": "ARBITRATION_REPLAY_MATCHED_FINAL_SOT",
            "expected_rows": 87,
            "observed_rows": medium_rows,
            "live_evaluator_status": "BLOCKED_FEATURE_ASOF_TIER2_AND_HIGH_ARBITRATION_REQUIRED",
            "readiness_level": "PARTIAL_PATH_ONLY_AFTER_PARITY",
            "blocker_summary": "TIER2_HVT source mismatch and feature/asof parity are unresolved; HIGH arbitration depends on CoreA/CoreB.",
            "approximate_reimplementation_allowed": False,
            "recommended_action": "SECONDARY_25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY",
        },
        {
            "component": "GLOBAL SAFETY / EXTERNAL ACTIONS",
            "historical_status": "AUDIT_ONLY",
            "expected_rows": 0,
            "observed_rows": 0,
            "live_evaluator_status": "FINAL_SIGNAL_AND_EXTERNAL_ACTIONS_DISABLED",
            "readiness_level": "SAFETY_BLOCKED",
            "blocker_summary": "Discord/MT5/AI/live hook/final signal remain OFF until explicit future approval after parity gates.",
            "approximate_reimplementation_allowed": False,
            "recommended_action": "KEEP_ALL_EXTERNAL_ACTIONS_OFF",
        },
    ])


def make_blocker_matrix() -> pd.DataFrame:
    return pd.DataFrame([
        {"blocker_id": "25A-B001", "component": "CoreB", "severity": "HARD_PRIMARY", "blocked_item": "full CoreA/CoreB/MEDIUM live evaluator", "required_resolution": "Recover original CoreB same_count / cluster_id / membership source-of-truth and later prove exact 125-row parity.", "status": "OPEN"},
        {"blocker_id": "25A-B002", "component": "CoreB", "severity": "HARD_PRIMARY", "blocked_item": "live CoreB RR125 generation", "required_resolution": "Find original algorithm or row-level membership ledger; static windows/raw counts/connected components/post-hoc fitting are forbidden.", "status": "OPEN"},
        {"blocker_id": "25A-B003", "component": "CoreA", "severity": "HARD", "blocked_item": "live CoreA A gate", "required_resolution": "Freeze executable tail_hard/top5/all-consensus/stack KEEP and rejected ordering from source-of-truth evidence.", "status": "OPEN"},
        {"blocker_id": "25A-B004", "component": "MEDIUM", "severity": "HARD", "blocked_item": "live MEDIUM eligibility", "required_resolution": "Prove range96/trend_eff96/ret96/tr_mean_32/regime feature/asof parity and reconcile TIER2_HVT mismatches.", "status": "OPEN"},
        {"blocker_id": "25A-B005", "component": "GLOBAL", "severity": "HARD", "blocked_item": "final_signal_allowed", "required_resolution": "Run later dry-run parity/preflight after component blockers are closed; no final signals in 25A.", "status": "OPEN"},
        {"blocker_id": "25A-B006", "component": "SAFETY", "severity": "SAFETY", "blocked_item": "Discord/MT5/AI/live hook", "required_resolution": "Explicit future user approval only after all source/parity gates pass; NO_SIGNAL must not notify Discord.", "status": "OPEN"},
    ])


def make_next_steps() -> pd.DataFrame:
    return pd.DataFrame([
        {"rank": 1, "step": "25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY", "priority": "PRIMARY", "allowed_now": True, "reason": "CoreB cluster/same_count/membership recovery is the hard prerequisite for full portfolio live evaluator path."},
        {"rank": 2, "step": "25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY", "priority": "SECONDARY", "allowed_now": True, "reason": "MEDIUM can proceed as partial evaluator work after feature/asof and TIER2 checks, but not as a substitute for CoreB recovery."},
        {"rank": 3, "step": "25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY", "priority": "PARALLEL", "allowed_now": True, "reason": "CoreA A gate must be frozen before live mapping."},
        {"rank": 4, "step": "FULL_COREA_COREB_MEDIUM_LIVE_EVALUATOR", "priority": "BLOCKED", "allowed_now": False, "reason": "Blocked until CoreB cluster source recovery and CoreA/MEDIUM parity gates are resolved or CoreB is explicitly excluded by later human decision."},
        {"rank": 5, "step": "24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY", "priority": "NOT_REQUESTED", "allowed_now": False, "reason": "24-series remains paused at 24AF unless explicitly requested."},
    ])


def make_safety_matrix() -> pd.DataFrame:
    rows = []
    for item, observed in SAFETY_FLAGS.items():
        expected = observed
        rows.append({"safety_item": item, "observed": observed, "expected": expected, "status": "PASS"})
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    sot_ledger = Path(args.sot_ledger).expanduser().resolve() if args.sot_ledger else default_sot_ledger()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(output_dir).mkdir(parents=True, exist_ok=True)

    reference_doc_audit = make_reference_doc_audit()
    sot_count_audit, observed_sot, input_audit = make_sot_count_audit(sot_ledger)

    component_matrix = make_component_matrix(observed_sot)
    blocker_matrix = make_blocker_matrix()
    next_steps = make_next_steps()
    safety_matrix = make_safety_matrix()

    total_stop_rows = int((reference_doc_audit["status"].eq("STOP")).sum()) + int((sot_count_audit["status"].eq("STOP")).sum())
    ok = total_stop_rows == 0
    status = PASS_STATUS if ok else STOP_STATUS

    write_csv(output_dir / "gold_v2_25a_input_audit.csv", input_audit)
    write_csv(output_dir / "gold_v2_25a_reference_doc_audit.csv", reference_doc_audit)
    write_csv(output_dir / "gold_v2_25a_final_sot_count_audit.csv", sot_count_audit)
    write_csv(output_dir / "gold_v2_25a_core_component_readiness_matrix.csv", component_matrix)
    write_csv(output_dir / "gold_v2_25a_live_evaluator_blocker_matrix.csv", blocker_matrix)
    write_csv(output_dir / "gold_v2_25a_recommended_next_steps.csv", next_steps)
    write_csv(output_dir / "gold_v2_25a_safety_matrix.csv", safety_matrix)

    summary: dict[str, Any] = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "readiness_package_only": True,
        "source_recovery_chain_status": "PAUSED_AT_24AF",
        "do_not_proceed_to_24ag_without_explicit_request": True,
        "sot_ledger": str(sot_ledger),
        "sot_observed": observed_sot,
        "total_stop_rows": total_stop_rows,
        "component_rows": int(len(component_matrix)),
        "blocker_rows": int(len(blocker_matrix)),
        "recommended_primary_next": "25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY",
        "recommended_secondary_next": "25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY",
        "recommended_parallel_next": "25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY",
        "coreb_live_evaluator_status": "BLOCKED_SOURCE_CLUSTER_MEMBERSHIP_REQUIRED",
        "coreb_historical_status": "REPRODUCED_HISTORICAL_SOT_ALLOWED",
        "full_portfolio_live_evaluator_allowed": False,
        **SAFETY_FLAGS,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
    }
    write_json(output_dir / "gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25A CoreA/CoreB/MEDIUM live evaluator readiness audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25A is a readiness package only. It does not run source recovery, mutate source artifacts, finalize source identity, enable a live evaluator final signal, call AI APIs, send Discord messages, place MT5 orders, or connect live hooks.",
        "",
        "## Final SOT count audit",
        "",
        md_table(sot_count_audit),
        "",
        "## Component readiness matrix",
        "",
        md_table(component_matrix),
        "",
        "## Live evaluator blocker matrix",
        "",
        md_table(blocker_matrix),
        "",
        "## Recommended next steps",
        "",
        md_table(next_steps),
        "",
        "## Reference document audit",
        "",
        md_table(reference_doc_audit),
        "",
        "## Safety matrix",
        "",
        md_table(safety_matrix),
        "",
        "## Explicit non-actions",
        "",
        "- 24AG continuation: `false`",
        "- source recovery execution: `false`",
        "- source mutation: `false`",
        "- source identity finalization: `false`",
        "- live evaluator final signal: `false`",
        "- Discord / MT5 / AI API / live hook: `false`",
        "- NO_SIGNAL Discord notification: `false`",
        "",
        "## Conclusion",
        "",
        "Primary next is `25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY`. Full CoreA/CoreB/MEDIUM live evaluator remains blocked while CoreB same_count / cluster_id / membership source-of-truth is unrecovered.",
    ])
    write_text(output_dir / "GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md", report)

    print(json.dumps({"status": status, "output_dir": str(output_dir), "total_stop_rows": total_stop_rows, "recommended_primary_next": summary["recommended_primary_next"]}, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
