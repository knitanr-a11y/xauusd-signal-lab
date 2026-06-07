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

STEP = "25C1_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY"
PASS_STATUS = "COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_COMPLETED_AUDIT_ONLY_ALIGNMENT_REVIEW_REQUIRED"
STOP_STATUS = "25C1_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C0 = "gold_v2_25c0_coreb_feature_source_candidate_review_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_audit_only"
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
    p = argparse.ArgumentParser(description="25C1 CoreB feature source to raw ledger alignment plan audit-only")
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


def safety_problems(s25c0: dict[str, Any]) -> list[str]:
    problems = []
    if s25c0.get("status") != "COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_COMPLETED_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED":
        problems.append("25C0 status mismatch")
    if int(s25c0.get("total_stop_rows", -1)) != 0:
        problems.append("25C0 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25c0.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s25c0.get(k)):
            problems.append(f"unsafe prior state: {k}")
    if not bool(s25c0.get("candidate_feature_source_review_passed_for_later_alignment_plan")):
        problems.append("candidate not passed for alignment plan")
    return problems


def time_profile(df: pd.DataFrame, col: str, label: str) -> pd.DataFrame:
    t = pd.to_datetime(df[col], errors="coerce")
    return pd.DataFrame([{
        "role": label,
        "time_column": col,
        "rows": int(len(df)),
        "parsed_time_rows": int(t.notna().sum()),
        "min_time": str(t.min()) if t.notna().any() else "",
        "max_time": str(t.max()) if t.notna().any() else "",
        "unique_time_rows": int(df[col].nunique()),
        "duplicate_time_rows": int(df.duplicated(subset=[col]).sum()),
    }])


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    s25c0_path = fx_outputs() / IN25C0 / "09_25c0_coreb_feature_source_candidate_review_summary.json"
    file_audit_path = fx_outputs() / IN25B3 / "gold_v2_25b3_shortlist_file_content_audit.csv"
    inputs = pd.DataFrame([
        {"role": "25c0_summary", "path": str(s25c0_path), "required": True, "exists": lp(s25c0_path).exists(), "status": "PASS" if lp(s25c0_path).exists() else "STOP"},
        {"role": "25b3_file_audit", "path": str(file_audit_path), "required": True, "exists": lp(file_audit_path).exists(), "status": "PASS" if lp(file_audit_path).exists() else "STOP"},
    ])
    write_csv(out_dir / "03_25c1_input_audit.csv", inputs)
    if not bool(inputs["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((inputs["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json", summary)
        return 2

    s25c0 = read_json(s25c0_path)
    problems = safety_problems(s25c0)
    feature_path = Path(str(s25c0.get("candidate_path", "")))
    if not lp(feature_path).exists():
        problems.append("feature source candidate path missing")
    file_audit = read_csv(file_audit_path)
    raw_path = path_from_file_audit(file_audit, RAW_LEDGER_NAME)
    if not bool(str(raw_path)) or not lp(raw_path).exists():
        problems.append("raw signal ledger path missing")

    if problems:
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "status_problems": problems, "total_stop_rows": len(problems), **SAFETY_FLAGS}
        write_json(out_dir / "02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json", summary)
        return 2

    feature_time = read_csv(feature_path, usecols=["time"])
    raw_time = read_csv(raw_path, usecols=["dataset", "entry_time"])
    feature_time["time_norm"] = pd.to_datetime(feature_time["time"], errors="coerce")
    raw_time["time_norm"] = pd.to_datetime(raw_time["entry_time"], errors="coerce")
    feature_profile = time_profile(feature_time, "time", "feature_source")
    raw_profile = time_profile(raw_time, "entry_time", "raw_signal_ledger")
    write_csv(out_dir / "04_25c1_feature_source_time_profile.csv", feature_profile)
    write_csv(out_dir / "05_25c1_raw_ledger_time_profile.csv", raw_profile)

    feature_set = set(feature_time["time_norm"].dropna())
    raw_set = set(raw_time["time_norm"].dropna())
    matched = raw_time[raw_time["time_norm"].isin(feature_set)].copy()
    missing = raw_time[~raw_time["time_norm"].isin(feature_set)].copy()
    extra_feature = feature_time[~feature_time["time_norm"].isin(raw_set)].copy()
    overlap = pd.DataFrame([{
        "raw_rows": int(len(raw_time)),
        "feature_rows": int(len(feature_time)),
        "raw_unique_times": int(raw_time["time_norm"].nunique()),
        "feature_unique_times": int(feature_time["time_norm"].nunique()),
        "raw_times_found_in_feature": int(matched["time_norm"].nunique()),
        "raw_rows_found_in_feature": int(len(matched)),
        "raw_rows_missing_feature_time": int(len(missing)),
        "feature_times_not_in_raw": int(extra_feature["time_norm"].nunique()),
        "raw_time_coverage_ratio": float(len(matched) / len(raw_time)) if len(raw_time) else 0.0,
    }])
    write_csv(out_dir / "06_25c1_time_overlap_matrix.csv", overlap)
    miss_sample = missing[["dataset", "entry_time"]].head(200).copy()
    write_csv(out_dir / "07_25c1_missing_time_samples.csv", miss_sample)

    full_raw_coverage = int(len(missing)) == 0
    feature_has_unique_time = int(feature_profile.iloc[0]["duplicate_time_rows"]) == 0
    raw_parse_ok = int(raw_profile.iloc[0]["parsed_time_rows"]) == int(raw_profile.iloc[0]["rows"])
    feature_parse_ok = int(feature_profile.iloc[0]["parsed_time_rows"]) == int(feature_profile.iloc[0]["rows"])
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "feature candidate exists", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "raw ledger exists", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "feature time parse ok", "observed": feature_parse_ok, "required": True, "status": "PASS" if feature_parse_ok else "BLOCKED"},
        {"gate_id": "G004", "gate": "raw entry_time parse ok", "observed": raw_parse_ok, "required": True, "status": "PASS" if raw_parse_ok else "BLOCKED"},
        {"gate_id": "G005", "gate": "feature time unique", "observed": feature_has_unique_time, "required": True, "status": "PASS" if feature_has_unique_time else "REVIEW"},
        {"gate_id": "G006", "gate": "all raw entry_time values covered by feature source", "observed": full_raw_coverage, "required": True, "status": "PASS" if full_raw_coverage else "BLOCKED"},
        {"gate_id": "G007", "gate": "CoreB non-key dry-run allowed now", "observed": False, "required": False, "status": "BLOCKED"},
    ])
    write_csv(out_dir / "08_25c1_alignment_gate_matrix.csv", gates)

    next_allowed = bool(feature_parse_ok and raw_parse_ok and feature_has_unique_time and full_raw_coverage)
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C2_COREB_NON_KEY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY", "allowed_now": next_allowed, "purpose": "Plan non-key dry-run only if alignment gates pass and human accepts feature source"},
        {"rank": 2, "next_step": "Human acceptance of feature source and alignment", "allowed_now": True, "purpose": "Accept/reject feature source candidate and timestamp alignment"},
        {"rank": 3, "next_step": "CoreB non-key dry-run execution", "allowed_now": False, "purpose": "Still blocked until implementation plan"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "09_25c1_next_step_plan.csv", next_plan)

    unnecessary = [
        "25C0 input_audit/candidate_selection/schema_profile already processed",
        "25B9 and older report/summary files already processed",
        "text-only MD/JSON feature-name candidates",
        "rr125_top_ledgers.csv alone",
    ]
    necessary = [
        "01_25c1_GOLD_V2_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY_REPORT.md",
        "02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json",
        "06_25c1_time_overlap_matrix.csv",
        "08_25c1_alignment_gate_matrix.csv",
        "09_25c1_next_step_plan.csv",
    ]
    req = pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・貼ってほしい", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )
    write_csv(out_dir / "00_不要_25c1_file_request_list.csv", req)

    status = PASS_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "status_problems": [],
        "feature_source_path": str(feature_path),
        "raw_signal_ledger_path": str(raw_path),
        "raw_rows": int(len(raw_time)),
        "feature_rows": int(len(feature_time)),
        "raw_rows_found_in_feature": int(len(matched)),
        "raw_rows_missing_feature_time": int(len(missing)),
        "raw_time_coverage_ratio": float(len(matched) / len(raw_time)) if len(raw_time) else 0.0,
        "alignment_gates_passed_for_later_plan": next_allowed,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25C2_COREB_NON_KEY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY" if next_allowed else "25C1_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY",
        "total_stop_rows": 0,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json", summary)

    request_text = "\n".join(
        ["00_不要_貼らなくてOK"]
        + [f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)]
        + ["", "必要・貼ってほしい"]
        + [f"{i+1:02d}. {x}" for i, x in enumerate(necessary)]
    )
    report = "\n".join([
        "# GOLD V2 25C1 CoreB feature source to raw ledger alignment plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25C1 profiles timestamp alignment only. It does not run CoreB replay or unblock CoreB.",
        "",
        "## Feature source time profile",
        "",
        md_table(feature_profile),
        "",
        "## Raw ledger time profile",
        "",
        md_table(raw_profile),
        "",
        "## Time overlap matrix",
        "",
        md_table(overlap),
        "",
        "## Alignment gates",
        "",
        md_table(gates),
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
    lp(out_dir / "01_25c1_GOLD_V2_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "raw_rows": int(len(raw_time)), "raw_rows_found_in_feature": int(len(matched)), "raw_rows_missing_feature_time": int(len(missing)), "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
