#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25C2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY"
PASS_STATUS = "COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP_STATUS = "25C2_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C1B = "gold_v2_25c1b_coreb_alignment_gap_review_audit_only"
OUT_DIR = "gold_v2_25c2_coreb_intersection_only_dry_run_plan_audit_only"

SAFETY_FLAGS = {
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "no_signal_discord_notification_allowed": False,
    "old_gold_disc8_quarantined": True,
    "source_recovery_chain_status": "PAUSED_AT_24AF",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25C2 CoreB intersection-only dry-run plan audit-only")
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not read CSV {path}: {last}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8-sig"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in view.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > max_rows:
        lines.append(f"| ... | truncated {len(df)-max_rows} more rows |" + " |" * max(0, len(cols)-2))
    return "\n".join(lines)


def safety_problems(s: dict[str, Any]) -> list[str]:
    problems = []
    if s.get("status") != "COREB_ALIGNMENT_GAP_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED":
        problems.append("25C1B status mismatch")
    if int(s.get("total_stop_rows", -1)) != 0:
        problems.append("25C1B stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s.get(k)):
            problems.append(f"unsafe prior state: {k}")
    if not bool(s.get("all_gap_rows_before_feature_start")):
        problems.append("not all gap rows are before feature start")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    in_dir = fx_outputs() / IN25C1B
    required = {
        "25c1b_summary": in_dir / "02_25c1b_coreb_alignment_gap_review_summary.json",
        "gap_counts": in_dir / "04_25c1b_gap_classification_counts.csv",
        "decision_matrix": in_dir / "08_25c1b_alignment_decision_matrix.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in required.items()])
    write_csv(out_dir / "03_25c2_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c2_coreb_intersection_only_dry_run_plan_summary.json", summary)
        return 2

    s = read_json(required["25c1b_summary"])
    problems = safety_problems(s)
    gap_counts = read_csv(required["gap_counts"])
    decision_matrix = read_csv(required["decision_matrix"])
    if problems:
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "status_problems": problems, "total_stop_rows": len(problems), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c2_coreb_intersection_only_dry_run_plan_summary.json", summary)
        return 2

    raw_rows = int(s.get("raw_rows", 0))
    covered_rows = int(s.get("covered_rows", 0))
    excluded_rows = int(s.get("gap_rows", 0))
    scope = pd.DataFrame([{
        "scope_id": "25C2-SCOPE-001",
        "intersection_only": True,
        "full_coreb_parity": False,
        "raw_rows_total": raw_rows,
        "covered_rows_eligible_for_later_dry_run": covered_rows,
        "excluded_raw_rows": excluded_rows,
        "excluded_reason": "BEFORE_FEATURE_START",
        "feature_min_time": s.get("feature_min_time", ""),
        "feature_max_time": s.get("feature_max_time", ""),
        "coverage_ratio": float(covered_rows / raw_rows) if raw_rows else 0.0,
    }])
    write_csv(out_dir / "04_25c2_intersection_scope_contract.csv", scope)

    exclusion = pd.DataFrame([
        {"impact_id": "EX001", "item": "raw rows excluded", "value": excluded_rows, "impact": "Full CoreB parity cannot be claimed"},
        {"impact_id": "EX002", "item": "excluded class", "value": "BEFORE_FEATURE_START", "impact": "Feature source starts after earliest raw ledger rows"},
        {"impact_id": "EX003", "item": "covered rows", "value": covered_rows, "impact": "Only this subset may be evaluated in next audit-only dry-run"},
        {"impact_id": "EX004", "item": "target/cluster parity", "value": "NOT_PROVEN", "impact": "CoreB remains blocked"},
    ])
    write_csv(out_dir / "05_25c2_exclusion_impact_matrix.csv", exclusion)

    algorithm = pd.DataFrame([
        {"step_no": 1, "algorithm_step": "load frozen CoreB selected/source condition objects", "execution_now": False, "future_scope": "audit-only implementation"},
        {"step_no": 2, "algorithm_step": "load raw_signal_ledger and feature source", "execution_now": False, "future_scope": "covered raw rows only"},
        {"step_no": 3, "algorithm_step": "inner join raw.entry_time == feature.time", "execution_now": False, "future_scope": "intersection only"},
        {"step_no": 4, "algorithm_step": "evaluate full condition objects, not KEY_COLS only", "execution_now": False, "future_scope": "non-key condition semantics"},
        {"step_no": 5, "algorithm_step": "compute source_universe_hit_count for covered subset", "execution_now": False, "future_scope": "no target fitting"},
        {"step_no": 6, "algorithm_step": "apply selected_rule_hit AND same_count_source_hit_count >= 15", "execution_now": False, "future_scope": "covered subset only"},
        {"step_no": 7, "algorithm_step": "compare to target with explicit intersection-only disclaimer", "execution_now": False, "future_scope": "not full parity"},
    ])
    write_csv(out_dir / "06_25c2_dry_run_algorithm_contract.csv", algorithm)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C1B status clean", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "all gaps before feature start", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "intersection-only disclaimer required", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "full CoreB parity allowed", "observed": False, "required": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "CoreB live evaluator allowed", "observed": False, "required": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "dry-run execution allowed now", "observed": False, "required": False, "status": "BLOCKED_UNTIL_HUMAN_ACCEPTANCE"},
    ])
    write_csv(out_dir / "07_25c2_acceptance_gate_matrix.csv", gates)

    forbidden = pd.DataFrame([
        {"method": "promote_intersection_to_full_parity", "forbidden": True, "reason": "excluded rows exist"},
        {"method": "fill_missing_pre_feature_rows", "forbidden": True, "reason": "would approximate unavailable feature values"},
        {"method": "use_target_rows_to_backfill_features", "forbidden": True, "reason": "post-hoc fitting"},
        {"method": "static_KEY_COLS_only_replay", "forbidden": True, "reason": "25B5/25B7 proved key-only loss"},
        {"method": "source_recovery_execution", "forbidden": True, "reason": "not approved"},
        {"method": "live_or_final_signal", "forbidden": True, "reason": "CoreB remains blocked"},
    ])
    write_csv(out_dir / "08_25c2_forbidden_methods.csv", forbidden)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "Human decision: accept intersection-only dry-run limitation", "allowed_now": True, "purpose": "Confirm excluded rows are acceptable for diagnostic dry-run only"},
        {"rank": 2, "next_step": "25C3_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY", "allowed_now": False, "purpose": "Blocked until explicit human acceptance"},
        {"rank": 3, "next_step": "CoreB full parity recovery", "allowed_now": False, "purpose": "Requires feature source extension or separate full-coverage source"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "09_25c2_next_step_plan.csv", next_plan)

    unnecessary = [
        "25C1B input_audit/gap_samples/gap_by_dataset_policy already optional",
        "25C1 and older report/summary files already processed",
        "rr125_top_ledgers.csv alone",
        "text-only MD/JSON feature-name candidates",
    ]
    necessary = [
        "01_25c2_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md",
        "02_25c2_coreb_intersection_only_dry_run_plan_summary.json",
        "04_25c2_intersection_scope_contract.csv",
        "05_25c2_exclusion_impact_matrix.csv",
        "07_25c2_acceptance_gate_matrix.csv",
        "08_25c2_forbidden_methods.csv",
        "09_25c2_next_step_plan.csv",
    ]
    req = pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・貼ってほしい", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )
    write_csv(out_dir / "00_不要_25c2_file_request_list.csv", req)

    status = PASS_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_only": True,
        "intersection_only": True,
        "full_coreb_parity": False,
        "status_problems": [],
        "raw_rows_total": raw_rows,
        "covered_rows_eligible_for_later_dry_run": covered_rows,
        "excluded_raw_rows": excluded_rows,
        "excluded_reason": "BEFORE_FEATURE_START",
        "feature_min_time": s.get("feature_min_time", ""),
        "feature_max_time": s.get("feature_max_time", ""),
        "dry_run_execution_allowed_now": False,
        "human_acceptance_required_before_25c3": True,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "HUMAN_DECISION_ACCEPT_INTERSECTION_ONLY_LIMITATION_BEFORE_25C3",
        "total_stop_rows": 0,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "02_25c2_coreb_intersection_only_dry_run_plan_summary.json", summary)

    request_text = "\n".join(
        ["00_不要_貼らなくてOK"]
        + [f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)]
        + ["", "必要・貼ってほしい"]
        + [f"{i+1:02d}. {x}" for i, x in enumerate(necessary)]
    )
    report = "\n".join([
        "# GOLD V2 25C2 CoreB intersection-only dry-run plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25C2 creates a plan only. It does not execute CoreB dry-run or unblock CoreB.",
        "",
        "## Intersection scope contract",
        "",
        md_table(scope),
        "",
        "## Exclusion impact matrix",
        "",
        md_table(exclusion),
        "",
        "## Dry-run algorithm contract",
        "",
        md_table(algorithm),
        "",
        "## Acceptance gates",
        "",
        md_table(gates),
        "",
        "## Forbidden methods",
        "",
        md_table(forbidden),
        "",
        "## File request list",
        "",
        "```text",
        request_text,
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "CoreB remains blocked. Source recovery/live/final/external actions remain off.",
    ])
    lp(out_dir / "01_25c2_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "intersection_only": True, "covered_rows": covered_rows, "excluded_raw_rows": excluded_rows, "dry_run_execution_allowed_now": False, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
