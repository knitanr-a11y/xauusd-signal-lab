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

STEP = "25B6_COREB_DRY_RUN_PARITY_REVIEW_AUDIT_ONLY"
IN_DIR = "gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only"
OUT_DIR = "gold_v2_25b6_coreb_dry_run_parity_review_audit_only"
PASS_STATUS = "COREB_DRY_RUN_PARITY_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED"
STOP_STATUS = "25B6_STOP_MISSING_25B5_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"

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

REQUIRED_INPUTS = {
    "summary": "gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json",
    "rule_key_audit": "gold_v2_25b5_rule_key_audit.csv",
    "raw_match_summary": "gold_v2_25b5_raw_match_summary.csv",
    "parity_summary": "gold_v2_25b5_parity_summary.csv",
    "target_compare": "gold_v2_25b5_target_compare_same_count_ge15.csv",
    "dry_run_rows": "gold_v2_25b5_dry_run_candidate_rows.csv",
    "execution_blockers": "gold_v2_25b5_execution_blockers.csv",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B6 CoreB dry-run parity review audit-only")
    p.add_argument("--input-dir", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_input_dir() -> Path:
    return fx_outputs() / IN_DIR


def default_output_dir() -> Path:
    return fx_outputs() / OUT_DIR


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


def metric(df: pd.DataFrame, name: str, col_name: str = "check", value_col: str = "observed") -> str:
    if df.empty or col_name not in df.columns or value_col not in df.columns:
        return ""
    m = df[df[col_name].astype(str) == name]
    if m.empty:
        return ""
    return str(m.iloc[0][value_col])


def safety_problems(summary: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if summary.get("status") != "COREB_SAME_COUNT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_PARITY_REVIEW_REQUIRED":
        problems.append("25B5 status mismatch")
    if int(summary.get("total_stop_rows", -1)) != 0:
        problems.append("25B5 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if summary.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    if bool(summary.get("coreb_live_evaluator_unblocked")):
        problems.append("CoreB live unexpectedly unblocked")
    if bool(summary.get("source_mutation_executed")):
        problems.append("source mutation unexpectedly executed")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    in_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else default_input_dir()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(out_dir).mkdir(parents=True, exist_ok=True)

    input_rows = []
    for role, filename in REQUIRED_INPUTS.items():
        p = in_dir / filename
        input_rows.append({"role": role, "path": str(p), "required": True, "exists": lp(p).exists(), "status": "PASS" if lp(p).exists() else "STOP"})
    input_audit = pd.DataFrame(input_rows)
    write_csv(out_dir / "gold_v2_25b6_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b6_coreb_dry_run_parity_review_summary.json", summary)
        return 2

    s25b5 = read_json(in_dir / REQUIRED_INPUTS["summary"])
    rule = read_csv(in_dir / REQUIRED_INPUTS["rule_key_audit"])
    raw = read_csv(in_dir / REQUIRED_INPUTS["raw_match_summary"])
    parity = read_csv(in_dir / REQUIRED_INPUTS["parity_summary"])
    compare = read_csv(in_dir / REQUIRED_INPUTS["target_compare"])
    dry = read_csv(in_dir / REQUIRED_INPUTS["dry_run_rows"])
    blockers25b5 = read_csv(in_dir / REQUIRED_INPUTS["execution_blockers"])

    problems = safety_problems(s25b5)
    status = PASS_STATUS if not problems else STOP_STATUS

    target_ge15 = int(float(metric(parity, "target_ge15_unique_keys") or 0))
    dry_unique = int(float(metric(parity, "dry_run_unique_keys") or 0))
    matched = int(float(metric(parity, "matched_keys") or 0))
    missing = int(float(metric(parity, "missing_dry_run_keys") or 0))
    extra = int(float(metric(parity, "extra_dry_run_keys") or 0))
    selected_rows = int(float(metric(rule, "selected_rule_rows") or 0))
    selected_unique = int(float(metric(rule, "selected_unique_keys") or 0))
    source_rows = int(float(metric(rule, "same_count_source_rule_rows") or 0))
    source_unique = int(float(metric(rule, "source_unique_keys") or 0))
    raw_rows = int(float(metric(raw, "raw_rows", "metric", "value") or 0))
    source_hit_rows = int(float(metric(raw, "source_rule_hit_rows", "metric", "value") or 0))
    selected_hit_rows = int(float(metric(raw, "selected_rule_hit_rows", "metric", "value") or 0))
    dry_signal_rows = int(float(metric(raw, "dry_run_signal_rows", "metric", "value") or 0))

    filter_gap_counts = pd.DataFrame()
    if not compare.empty and "parity_status" in compare.columns:
        filter_gap_counts = (
            compare.groupby(["parity_status", "filter"], dropna=False)
            .size()
            .reset_index(name="rows")
            .sort_values(["parity_status", "rows"], ascending=[True, False])
        )
    write_csv(out_dir / "gold_v2_25b6_filter_gap_counts.csv", filter_gap_counts)

    entry_dist = pd.DataFrame()
    if not dry.empty and "entry_time" in dry.columns:
        group_cols = [c for c in ["entry_time", "dataset", "policy"] if c in dry.columns]
        entry_dist = dry.groupby(group_cols, dropna=False).size().reset_index(name="dry_rows").sort_values("dry_rows", ascending=False)
    write_csv(out_dir / "gold_v2_25b6_dry_run_entry_distribution.csv", entry_dist)

    review_rows = [
        {"review_id": "R001", "classification": "KEY_ONLY_RULE_COLLAPSE", "observed": f"selected {selected_rows}->{selected_unique}; source {source_rows}->{source_unique}", "impact": "frozen condition detail was lost in key-only probe", "blocks_unblock": True},
        {"review_id": "R002", "classification": "SOURCE_RULE_UNIVERSE_OVERBROAD_KEY_MATCH", "observed": f"source_hit_rows={source_hit_rows}; raw_rows={raw_rows}", "impact": "source universe key probe matched all raw rows, so it is not discriminating original same_count semantics", "blocks_unblock": True},
        {"review_id": "R003", "classification": "DRY_RUN_UNDER_GENERATION", "observed": f"dry_unique={dry_unique}; target_ge15={target_ge15}; missing={missing}", "impact": "dry-run generated too few unique keys", "blocks_unblock": True},
        {"review_id": "R004", "classification": "EXTRA_DRY_RUN_ROWS", "observed": f"extra={extra}", "impact": "dry-run also generated target-missing keys", "blocks_unblock": True},
        {"review_id": "R005", "classification": "TARGET_FILTER_CONTRACT_MISMATCH", "observed": "target includes many filter strings; dry-run used one synthetic filter", "impact": "key comparison denominator is not aligned with target filter contract", "blocks_unblock": True},
        {"review_id": "R006", "classification": "SAME_COUNT_VALUE_PARITY_NOT_CHECKED", "observed": "not checked in 25B5", "impact": "same_count value equality remains unproven", "blocks_unblock": True},
        {"review_id": "R007", "classification": "CLUSTER_MEMBERSHIP_NOT_CHECKED", "observed": "not checked in 25B5", "impact": "cluster/member source semantics remain unproven", "blocks_unblock": True},
        {"review_id": "R008", "classification": "COREB_UNBLOCK_FORBIDDEN", "observed": "CoreB live false; parity not proven", "impact": "CoreB remains blocked", "blocks_unblock": True},
        {"review_id": "R009", "classification": "DRY_RUN_PROBE_FLAG_REVIEW", "observed": str(s25b5.get("replay_execution_scope", "")), "impact": "25B5 must be interpreted as dry-run probe only, not source recovery or live replay", "blocks_unblock": True},
    ]
    review = pd.DataFrame(review_rows)
    write_csv(out_dir / "gold_v2_25b6_parity_review_matrix.csv", review)

    decision = pd.DataFrame([
        {"decision_id": "D001", "question": "Can CoreB live evaluator be unblocked?", "decision": "NO", "reason": "same_count and membership parity are not proven"},
        {"decision_id": "D002", "question": "Can 25B5 key-only output be promoted to source truth?", "decision": "NO", "reason": "key-only rule collapse and target-filter mismatch"},
        {"decision_id": "D003", "question": "Can target rows be used to fit missing dry-run rows?", "decision": "NO", "reason": "post-hoc fitting remains forbidden"},
        {"decision_id": "D004", "question": "Can next work inspect full frozen condition objects?", "decision": "YES_AUDIT_ONLY", "reason": "needed to see whether rules contain condition semantics not represented by key-only probe"},
    ])
    write_csv(out_dir / "gold_v2_25b6_review_decision_matrix.csv", decision)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY", "allowed_now": True, "purpose": "Inspect frozen condition objects and determine whether a non-key-only dry-run is possible without approximation"},
        {"rank": 2, "next_step": "CoreB source recovery execution", "allowed_now": False, "purpose": "Still blocked until original condition/membership semantics are proven"},
        {"rank": 3, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked until exact parity gates pass"},
    ])
    write_csv(out_dir / "gold_v2_25b6_next_step_plan.csv", next_plan)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "status_problems": problems,
        "target_ge15_unique_keys": target_ge15,
        "dry_run_unique_keys": dry_unique,
        "matched_keys": matched,
        "missing_dry_run_keys": missing,
        "extra_dry_run_keys": extra,
        "selected_rule_rows": selected_rows,
        "selected_unique_keys": selected_unique,
        "same_count_source_rule_rows": source_rows,
        "source_unique_keys": source_unique,
        "source_rule_hit_rows": source_hit_rows,
        "raw_rows": raw_rows,
        "dry_run_signal_rows": dry_signal_rows,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY",
        "total_stop_rows": int(len(problems)),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b6_coreb_dry_run_parity_review_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B6 CoreB dry-run parity review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B6 reviews 25B5 outputs only. It does not change source files or unblock CoreB.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Key findings",
        "",
        md_table(pd.DataFrame([{
            "target_ge15_unique_keys": target_ge15,
            "dry_run_unique_keys": dry_unique,
            "matched_keys": matched,
            "missing_dry_run_keys": missing,
            "extra_dry_run_keys": extra,
            "selected_rule_collapse": f"{selected_rows}->{selected_unique}",
            "source_rule_collapse": f"{source_rows}->{source_unique}",
        }])),
        "",
        "## Parity review matrix",
        "",
        md_table(review),
        "",
        "## Filter gap counts",
        "",
        md_table(filter_gap_counts, max_rows=40),
        "",
        "## Review decisions",
        "",
        md_table(decision),
        "",
        "## 25B5 blockers carried forward",
        "",
        md_table(blockers25b5),
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "CoreB remains blocked. Source recovery/live/final/external actions remain off.",
    ])
    lp(out_dir / "GOLD_V2_25B6_COREB_DRY_RUN_PARITY_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "matched_keys": matched, "missing_dry_run_keys": missing, "extra_dry_run_keys": extra, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
