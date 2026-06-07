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

STEP = "25C0_COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY"
PASS_STATUS = "COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_COMPLETED_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED"
STOP_STATUS = "25C0_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25B9 = "gold_v2_25b9_coreb_feature_source_discovery_audit_only"
IN25B8 = "gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only"
OUT_DIR = "gold_v2_25c0_coreb_feature_source_candidate_review_audit_only"

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
    p = argparse.ArgumentParser(description="25C0 CoreB feature source candidate review audit-only")
    p.add_argument("--candidate-path", default=None, help="Optional explicit candidate CSV path")
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


def read_csv(path: Path, nrows: int | None = None) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False, nrows=nrows)
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


def safety_problems(s25b9: dict[str, Any]) -> list[str]:
    problems = []
    if s25b9.get("status") not in {
        "COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_CANDIDATE_REVIEW_REQUIRED",
        "COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_SOURCE_NOT_ACCEPTED",
    }:
        problems.append("25B9 status mismatch")
    if int(s25b9.get("total_stop_rows", -1)) != 0:
        problems.append("25B9 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25b9.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s25b9.get(k)):
            problems.append(f"unsafe prior state: {k}")
    return problems


def required_features(manifest: pd.DataFrame) -> list[str]:
    if "field" not in manifest.columns:
        return []
    return sorted(set(str(x) for x in manifest["field"].dropna().tolist() if str(x)))


def select_candidate(coverage: pd.DataFrame, explicit: str | None) -> pd.DataFrame:
    if explicit:
        return pd.DataFrame([{
            "path": explicit,
            "kind": "explicit_candidate",
            "required_feature_hits": "unknown",
            "required_feature_count": "unknown",
            "missing_feature_count": "unknown",
            "complete_coverage": "unknown",
            "selection_reason": "explicit --candidate-path",
        }])
    if coverage.empty:
        return pd.DataFrame()
    df = coverage.copy()
    if "complete_coverage" in df.columns:
        df["complete_bool"] = df["complete_coverage"].astype(str).str.lower().isin(["true", "1"])
    else:
        df["complete_bool"] = False
    if "kind" not in df.columns:
        df["kind"] = ""
    table = df[df["complete_bool"] & df["kind"].astype(str).eq("table_candidate")].copy()
    if table.empty:
        table = df[df["complete_bool"]].copy()
    if table.empty:
        table = df.sort_values("required_feature_hits", ascending=False).head(1).copy()
    else:
        table = table.sort_values("required_feature_hits", ascending=False).head(1).copy()
    table["selection_reason"] = "best_complete_table_candidate_preferred"
    return table


def profile_feature_values(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for f in features:
        if f not in df.columns:
            rows.append({"field": f, "present": False, "non_empty_rows": 0, "numeric_rows": 0, "nan_rows_after_numeric": 0, "min": "", "max": "", "mean": ""})
            continue
        s = df[f]
        non_empty = s.astype(str).str.len() > 0
        num = pd.to_numeric(s, errors="coerce")
        numeric_rows = int(num.notna().sum())
        rows.append({
            "field": f,
            "present": True,
            "non_empty_rows": int(non_empty.sum()),
            "numeric_rows": numeric_rows,
            "nan_rows_after_numeric": int(num.isna().sum()),
            "min": float(num.min()) if numeric_rows else "",
            "max": float(num.max()) if numeric_rows else "",
            "mean": float(num.mean()) if numeric_rows else "",
        })
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    in25b9 = fx_outputs() / IN25B9
    in25b8 = fx_outputs() / IN25B8
    required = {
        "25b9_summary": in25b9 / "gold_v2_25b9_coreb_feature_source_discovery_summary.json",
        "25b9_coverage": in25b9 / "gold_v2_25b9_feature_coverage_by_candidate.csv",
        "25b9_inventory": in25b9 / "gold_v2_25b9_feature_source_candidate_inventory.csv",
        "25b8_required_feature_manifest": in25b8 / "gold_v2_25b8_required_feature_manifest.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in required.items()])
    write_csv(out_dir / "01_25c0_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "09_25c0_coreb_feature_source_candidate_review_summary.json", summary)
        return 2

    s25b9 = read_json(required["25b9_summary"])
    problems = safety_problems(s25b9)
    coverage = read_csv(required["25b9_coverage"])
    manifest = read_csv(required["25b8_required_feature_manifest"])
    features = required_features(manifest)
    selection = select_candidate(coverage, args.candidate_path)
    write_csv(out_dir / "02_25c0_candidate_selection.csv", selection)

    if selection.empty:
        problems.append("no candidate selected")
        candidate_path = Path("")
    else:
        candidate_path = Path(str(selection.iloc[0].get("path", "")))
        if not lp(candidate_path).exists():
            problems.append("selected candidate path does not exist")

    if problems:
        status = STOP_STATUS
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "status_problems": problems, "total_stop_rows": int(len(problems)), **SAFETY_FLAGS}
        write_json(out_dir / "09_25c0_coreb_feature_source_candidate_review_summary.json", summary)
        return 2

    head = read_csv(candidate_path)
    rows = int(len(head))
    cols = list(head.columns)
    missing = sorted(set(features) - set(cols))
    present = sorted(set(features) & set(cols))
    schema_profile = pd.DataFrame([{
        "candidate_path": str(candidate_path),
        "exists": True,
        "bytes": int(lp(candidate_path).stat().st_size),
        "rows": rows,
        "column_count": len(cols),
        "required_feature_count": len(features),
        "required_features_present": len(present),
        "required_features_missing": len(missing),
        "complete_feature_coverage": len(missing) == 0,
        "columns": ";".join(cols),
    }])
    write_csv(out_dir / "03_25c0_candidate_schema_profile.csv", schema_profile)

    value_profile = profile_feature_values(head, features)
    write_csv(out_dir / "04_25c0_required_feature_value_profile.csv", value_profile)

    time_col = "time" if "time" in head.columns else ("entry_time" if "entry_time" in head.columns else "")
    time_profile_rows = []
    if time_col:
        t = pd.to_datetime(head[time_col], errors="coerce")
        time_profile_rows.append({
            "time_column": time_col,
            "rows": rows,
            "parsed_time_rows": int(t.notna().sum()),
            "min_time": str(t.min()) if t.notna().any() else "",
            "max_time": str(t.max()) if t.notna().any() else "",
            "duplicate_time_rows": int(head.duplicated(subset=[time_col]).sum()),
            "unique_time_rows": int(head[time_col].nunique()),
        })
    else:
        time_profile_rows.append({"time_column": "", "rows": rows, "parsed_time_rows": 0, "min_time": "", "max_time": "", "duplicate_time_rows": "", "unique_time_rows": ""})
    time_profile = pd.DataFrame(time_profile_rows)
    write_csv(out_dir / "05_25c0_time_key_profile.csv", time_profile)

    all_numeric = bool(value_profile["present"].all() and (value_profile["numeric_rows"] == rows).all()) if rows > 0 else False
    has_time = bool(time_col)
    no_dup_time = bool(has_time and int(time_profile.iloc[0]["duplicate_time_rows"] or 0) == 0)
    gate = pd.DataFrame([
        {"gate_id": "G001", "gate": "candidate exists", "observed": True, "required": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "complete 38-field coverage", "observed": len(missing) == 0, "required": True, "status": "PASS" if len(missing) == 0 else "BLOCKED"},
        {"gate_id": "G003", "gate": "time column exists", "observed": has_time, "required": True, "status": "PASS" if has_time else "BLOCKED"},
        {"gate_id": "G004", "gate": "time column has no duplicate rows", "observed": no_dup_time, "required": True, "status": "PASS" if no_dup_time else "REVIEW"},
        {"gate_id": "G005", "gate": "required feature values numeric for all rows", "observed": all_numeric, "required": True, "status": "PASS" if all_numeric else "REVIEW"},
        {"gate_id": "G006", "gate": "CoreB unblock allowed now", "observed": False, "required": False, "status": "BLOCKED"},
    ])
    write_csv(out_dir / "06_25c0_source_acceptance_gate_matrix.csv", gate)

    unnecessary = [
        "25B9 report/summary/input_audit/scan_root_audit already processed",
        "25B8 and older report/summary files already processed",
        "text-only MD/JSON candidates that only mention feature names",
        "rr125_raw_signal_ledger.csv alone",
        "rr125_top_ledgers.csv alone",
    ]
    necessary = [
        f"01_feature_source_candidate_csv: {candidate_path}",
        "02_if_available_builder_script: build_coreb_combined_required_feature_snapshot_audit_only.py",
        "03_if_available_prior_parity_report: GOLD_V2_13C2_COREB_SOURCE_LEDGER_TO_FEATURE_SNAPSHOT_PARITY_AUDIT_ONLY_REPORT.md",
    ]
    file_request = pd.DataFrame(
        [{"section": "不要・貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・貼ってほしい", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )
    write_csv(out_dir / "07_25c0_file_request_list.csv", file_request)

    accept_candidate_for_later_plan = bool(len(missing) == 0 and has_time and rows > 0)
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C1_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY", "allowed_now": accept_candidate_for_later_plan, "purpose": "Plan timestamp alignment between feature source and raw signal ledger"},
        {"rank": 2, "next_step": "Human acceptance of feature source candidate", "allowed_now": True, "purpose": "Accept/reject candidate source before non-key dry-run"},
        {"rank": 3, "next_step": "CoreB non-key dry-run implementation", "allowed_now": False, "purpose": "Still blocked until alignment plan and acceptance"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "08_25c0_next_step_plan.csv", next_plan)

    status = PASS_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "status_problems": [],
        "candidate_path": str(candidate_path),
        "candidate_rows": rows,
        "candidate_column_count": len(cols),
        "required_feature_count": len(features),
        "required_features_present": len(present),
        "required_features_missing": len(missing),
        "time_column": time_col,
        "duplicate_time_rows": int(time_profile.iloc[0]["duplicate_time_rows"] or 0) if time_col else None,
        "candidate_feature_source_review_passed_for_later_alignment_plan": accept_candidate_for_later_plan,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25C1_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY",
        "total_stop_rows": 0,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "09_25c0_coreb_feature_source_candidate_review_summary.json", summary)

    request_text = "\n".join(
        ["【不要・貼らなくてOK】"]
        + [f"{i+1}. {x}" for i, x in enumerate(unnecessary)]
        + ["", "【必要・貼ってほしい】"]
        + [f"{i+1}. {x}" for i, x in enumerate(necessary)]
    )
    report = "\n".join([
        "# GOLD V2 25C0 CoreB feature source candidate review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25C0 profiles a candidate feature source only. It does not run CoreB replay or unblock CoreB.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Candidate selection",
        "",
        md_table(selection),
        "",
        "## Candidate schema profile",
        "",
        md_table(schema_profile),
        "",
        "## Time key profile",
        "",
        md_table(time_profile),
        "",
        "## Acceptance gates",
        "",
        md_table(gate),
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
    lp(out_dir / "00_GOLD_V2_25C0_COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "candidate_rows": rows, "required_features_missing": len(missing), "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
