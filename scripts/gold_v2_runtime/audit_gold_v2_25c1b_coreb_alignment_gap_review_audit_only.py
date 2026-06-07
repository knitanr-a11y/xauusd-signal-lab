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

STEP = "25C1B_COREB_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY"
PASS_STATUS = "COREB_ALIGNMENT_GAP_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED"
STOP_STATUS = "25C1B_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C1 = "gold_v2_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c1b_coreb_alignment_gap_review_audit_only"
RAW_LEDGER_NAME = "rr125_raw_signal_ledger.csv"

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
    p = argparse.ArgumentParser(description="25C1B CoreB alignment gap review audit-only")
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


def read_csv(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False, usecols=usecols)
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


def path_from_file_audit(file_audit: pd.DataFrame, name: str) -> Path:
    m = file_audit[file_audit["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    if m.empty:
        return Path("")
    return Path(str(m.iloc[0]["absolute_path"]))


def safety_problems(s25c1: dict[str, Any]) -> list[str]:
    problems = []
    if s25c1.get("status") != "COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_COMPLETED_AUDIT_ONLY_ALIGNMENT_REVIEW_REQUIRED":
        problems.append("25C1 status mismatch")
    if int(s25c1.get("total_stop_rows", -1)) != 0:
        problems.append("25C1 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25c1.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s25c1.get(k)):
            problems.append(f"unsafe prior state: {k}")
    return problems


def classify_gap(t: pd.Timestamp, feature_min: pd.Timestamp, feature_max: pd.Timestamp, feature_set: set[pd.Timestamp]) -> str:
    if pd.isna(t):
        return "UNPARSED_RAW_TIME"
    if t < feature_min:
        return "BEFORE_FEATURE_START"
    if t > feature_max:
        return "AFTER_FEATURE_END"
    if t not in feature_set:
        return "WITHIN_FEATURE_RANGE_HOLE"
    return "COVERED"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    s25c1_path = fx_outputs() / IN25C1 / "02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json"
    file_audit_path = fx_outputs() / IN25B3 / "gold_v2_25b3_shortlist_file_content_audit.csv"
    inputs = pd.DataFrame([
        {"role": "25c1_summary", "path": str(s25c1_path), "required": True, "exists": lp(s25c1_path).exists(), "status": "PASS" if lp(s25c1_path).exists() else "STOP"},
        {"role": "25b3_file_audit", "path": str(file_audit_path), "required": True, "exists": lp(file_audit_path).exists(), "status": "PASS" if lp(file_audit_path).exists() else "STOP"},
    ])
    write_csv(out_dir / "03_25c1b_input_audit.csv", inputs)
    if not bool(inputs["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((inputs["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c1b_coreb_alignment_gap_review_summary.json", summary)
        return 2

    s25c1 = read_json(s25c1_path)
    problems = safety_problems(s25c1)
    feature_path = Path(str(s25c1.get("feature_source_path", "")))
    file_audit = read_csv(file_audit_path)
    raw_path = path_from_file_audit(file_audit, RAW_LEDGER_NAME)
    if not lp(feature_path).exists():
        problems.append("feature source path missing")
    if not str(raw_path) or not lp(raw_path).exists():
        problems.append("raw ledger path missing")
    if problems:
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "status_problems": problems, "total_stop_rows": len(problems), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c1b_coreb_alignment_gap_review_summary.json", summary)
        return 2

    feature_time = read_csv(feature_path, usecols=["time"])
    raw = read_csv(raw_path, usecols=["dataset", "entry_time", "policy", "candidate_id", "origin_id", "direction", "variant", "rr_bucket"])
    feature_time["time_norm"] = pd.to_datetime(feature_time["time"], errors="coerce")
    raw["time_norm"] = pd.to_datetime(raw["entry_time"], errors="coerce")
    feature_min = feature_time["time_norm"].min()
    feature_max = feature_time["time_norm"].max()
    feature_set = set(feature_time["time_norm"].dropna())
    raw["gap_class"] = raw["time_norm"].map(lambda x: classify_gap(x, feature_min, feature_max, feature_set))
    gaps = raw[raw["gap_class"] != "COVERED"].copy()

    gap_counts = raw.groupby("gap_class", dropna=False).size().reset_index(name="raw_rows").sort_values("raw_rows", ascending=False)
    write_csv(out_dir / "04_25c1b_gap_classification_counts.csv", gap_counts)

    by_dataset_policy = gaps.groupby(["gap_class", "dataset", "policy"], dropna=False).size().reset_index(name="raw_rows").sort_values(["gap_class", "raw_rows"], ascending=[True, False])
    write_csv(out_dir / "05_25c1b_gap_by_dataset_policy.csv", by_dataset_policy)

    bounds_rows = []
    for cls, g in gaps.groupby("gap_class", dropna=False):
        bounds_rows.append({
            "gap_class": cls,
            "rows": int(len(g)),
            "unique_times": int(g["time_norm"].nunique()),
            "min_entry_time": str(g["time_norm"].min()) if g["time_norm"].notna().any() else "",
            "max_entry_time": str(g["time_norm"].max()) if g["time_norm"].notna().any() else "",
        })
    bounds = pd.DataFrame(bounds_rows)
    write_csv(out_dir / "06_25c1b_gap_time_bounds.csv", bounds)

    samples = gaps[["gap_class", "dataset", "entry_time", "policy", "candidate_id", "origin_id", "direction", "variant", "rr_bucket"]].head(300).copy()
    write_csv(out_dir / "07_25c1b_gap_samples.csv", samples)

    before_rows = int((raw["gap_class"] == "BEFORE_FEATURE_START").sum())
    inside_rows = int((raw["gap_class"] == "WITHIN_FEATURE_RANGE_HOLE").sum())
    after_rows = int((raw["gap_class"] == "AFTER_FEATURE_END").sum())
    all_gap_outside_start = inside_rows == 0 and after_rows == 0 and before_rows > 0
    decision = pd.DataFrame([
        {"decision_id": "D001", "question": "Can current feature source cover every raw ledger row?", "decision": "NO", "reason": f"missing rows={len(gaps)}"},
        {"decision_id": "D002", "question": "Are gaps only before feature source start?", "decision": "YES" if all_gap_outside_start else "NO", "reason": f"before={before_rows}; inside={inside_rows}; after={after_rows}"},
        {"decision_id": "D003", "question": "Can later non-key dry-run use intersection subset only?", "decision": "REVIEW_REQUIRED", "reason": "subset would exclude source rows and must not be promoted as full CoreB parity"},
        {"decision_id": "D004", "question": "Can CoreB live evaluator be unblocked?", "decision": "NO", "reason": "alignment and parity are not proven"},
    ])
    write_csv(out_dir / "08_25c1b_alignment_decision_matrix.csv", decision)

    next_step = "25C2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY" if all_gap_outside_start else "25C2_COREB_FEATURE_SOURCE_EXTENSION_OR_ALIGNMENT_REPAIR_PLAN_AUDIT_ONLY"
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next_step, "allowed_now": True, "purpose": "Plan next audit-only path based on gap class; no replay execution yet"},
        {"rank": 2, "next_step": "Human decision: accept intersection-only limitation or require extended feature source", "allowed_now": True, "purpose": "Avoid silently dropping missing raw rows"},
        {"rank": 3, "next_step": "CoreB non-key dry-run execution", "allowed_now": False, "purpose": "Still blocked"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "09_25c1b_next_step_plan.csv", next_plan)

    unnecessary = [
        "25C1 input_audit/feature_time_profile/raw_time_profile already processed",
        "25C0 and older report/summary files already processed",
        "rr125_top_ledgers.csv alone",
        "text-only MD/JSON feature-name candidates",
    ]
    necessary = [
        "01_25c1b_GOLD_V2_COREB_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY_REPORT.md",
        "02_25c1b_coreb_alignment_gap_review_summary.json",
        "04_25c1b_gap_classification_counts.csv",
        "06_25c1b_gap_time_bounds.csv",
        "08_25c1b_alignment_decision_matrix.csv",
        "09_25c1b_next_step_plan.csv",
    ]
    req = pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・貼ってほしい", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )
    write_csv(out_dir / "00_不要_25c1b_file_request_list.csv", req)

    status = PASS_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "status_problems": [],
        "raw_rows": int(len(raw)),
        "covered_rows": int((raw["gap_class"] == "COVERED").sum()),
        "gap_rows": int(len(gaps)),
        "before_feature_start_rows": before_rows,
        "within_feature_range_hole_rows": inside_rows,
        "after_feature_end_rows": after_rows,
        "all_gap_rows_before_feature_start": bool(all_gap_outside_start),
        "feature_min_time": str(feature_min),
        "feature_max_time": str(feature_max),
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": next_step,
        "total_stop_rows": 0,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "02_25c1b_coreb_alignment_gap_review_summary.json", summary)

    request_text = "\n".join(
        ["00_不要_貼らなくてOK"]
        + [f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)]
        + ["", "必要・貼ってほしい"]
        + [f"{i+1:02d}. {x}" for i, x in enumerate(necessary)]
    )
    report = "\n".join([
        "# GOLD V2 25C1B CoreB alignment gap review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25C1B classifies alignment gaps only. It does not run CoreB replay or unblock CoreB.",
        "",
        "## Gap classification counts",
        "",
        md_table(gap_counts),
        "",
        "## Gap time bounds",
        "",
        md_table(bounds),
        "",
        "## Alignment decision matrix",
        "",
        md_table(decision),
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
    lp(out_dir / "01_25c1b_GOLD_V2_COREB_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "gap_rows": int(len(gaps)), "before_feature_start_rows": before_rows, "within_feature_range_hole_rows": inside_rows, "after_feature_end_rows": after_rows, "next_recommended_step": next_step}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
