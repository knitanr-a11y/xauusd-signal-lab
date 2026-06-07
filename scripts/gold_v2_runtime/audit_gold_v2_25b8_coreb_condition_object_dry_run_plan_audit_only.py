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

STEP = "25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY"
PASS_STATUS = "COREB_CONDITION_OBJECT_DRY_RUN_PLAN_COMPLETED_AUDIT_ONLY_FEATURE_SOURCE_REQUIRED"
STOP_STATUS = "25B8_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25B7 = "gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only"

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
RAW_LEDGER_NAME = "rr125_raw_signal_ledger.csv"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B8 CoreB condition object dry-run plan audit-only")
    p.add_argument("--input-25b7-dir", default=None)
    p.add_argument("--input-25b3-dir", default=None)
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


def parse_column_names(text: str) -> list[str]:
    return [c for c in str(text).split(";") if c]


def field_family(field: str) -> str:
    f = field.lower()
    if f.startswith("m5_"):
        return "M5_FEATURE"
    if "donch" in f:
        return "DONCHIAN_FEATURE"
    if "ret" in f:
        return "RETURN_ATR_FEATURE"
    if "range" in f or "compression" in f:
        return "RANGE_COMPRESSION_FEATURE"
    if "dist_high" in f or "dist_low" in f:
        return "DISTANCE_ATR_FEATURE"
    if "ema" in f:
        return "EMA_FEATURE"
    if "wick" in f:
        return "CANDLE_WICK_FEATURE"
    return "OTHER_FEATURE"


def safety_problems(s25b7: dict[str, Any]) -> list[str]:
    problems = []
    if s25b7.get("status") != "COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED":
        problems.append("25B7 status mismatch")
    if int(s25b7.get("total_stop_rows", -1)) != 0:
        problems.append("25B7 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25b7.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s25b7.get(k)):
            problems.append(f"unsafe prior state: {k}")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    in25b7 = Path(args.input_25b7_dir).expanduser().resolve() if args.input_25b7_dir else fx_outputs() / IN25B7
    in25b3 = Path(args.input_25b3_dir).expanduser().resolve() if args.input_25b3_dir else fx_outputs() / IN25B3
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)

    required = {
        "25b7_summary": in25b7 / "gold_v2_25b7_coreb_frozen_condition_object_semantics_summary.json",
        "condition_inventory": in25b7 / "gold_v2_25b7_condition_object_inventory.csv",
        "key_only_loss": in25b7 / "gold_v2_25b7_key_only_loss_matrix.csv",
        "feasibility": in25b7 / "gold_v2_25b7_semantics_feasibility_matrix.csv",
        "25b3_csv_profile": in25b3 / "gold_v2_25b3_csv_profile.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in required.items()])
    write_csv(out_dir / "gold_v2_25b8_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b8_coreb_condition_object_dry_run_plan_summary.json", summary)
        return 2

    s25b7 = read_json(required["25b7_summary"])
    problems = safety_problems(s25b7)
    inv = read_csv(required["condition_inventory"])
    key_loss = read_csv(required["key_only_loss"])
    feasibility25b7 = read_csv(required["feasibility"])
    csv_profile = read_csv(required["25b3_csv_profile"])

    raw_profile = csv_profile[csv_profile["normalized_path"].astype(str).str.contains(RAW_LEDGER_NAME, case=False, regex=False, na=False)]
    raw_cols = []
    raw_rows = ""
    if raw_profile.empty:
        problems.append("raw ledger csv_profile missing")
    else:
        raw_cols = parse_column_names(raw_profile.iloc[0].get("column_names", ""))
        raw_rows = str(raw_profile.iloc[0].get("rows", ""))

    field_df = inv.copy()
    field_df["field"] = field_df.get("field", pd.Series(dtype=str)).astype(str)
    field_df = field_df[field_df["field"].str.strip() != ""].copy()
    manifest = (
        field_df.groupby("field", dropna=False)
        .agg(
            condition_object_rows=("field", "size"),
            config_roles=("config_role", lambda s: ";".join(sorted(set(map(str, s))))),
            operators=("operator", lambda s: ";".join(sorted(set(map(str, s))))),
            sample_values=("value_preview", lambda s: ";".join(list(dict.fromkeys(map(str, s)))[:10])),
        )
        .reset_index()
    )
    manifest["field_family"] = manifest["field"].map(field_family)
    manifest["present_in_raw_ledger"] = manifest["field"].isin(raw_cols)
    manifest = manifest.sort_values(["present_in_raw_ledger", "condition_object_rows", "field"], ascending=[True, False, True])
    write_csv(out_dir / "gold_v2_25b8_required_feature_manifest.csv", manifest)

    raw_coverage = pd.DataFrame([{
        "raw_ledger_rows": raw_rows,
        "raw_ledger_column_count": len(raw_cols),
        "raw_ledger_columns": ";".join(raw_cols),
        "required_feature_count": int(len(manifest)),
        "features_present_in_raw_ledger": int(manifest["present_in_raw_ledger"].sum()) if not manifest.empty else 0,
        "features_missing_from_raw_ledger": int((~manifest["present_in_raw_ledger"]).sum()) if not manifest.empty else 0,
        "raw_ledger_sufficient_for_condition_object_dry_run": bool(not manifest.empty and manifest["present_in_raw_ledger"].all()),
    }])
    write_csv(out_dir / "gold_v2_25b8_raw_ledger_field_coverage.csv", raw_coverage)

    missing_manifest = manifest[~manifest["present_in_raw_ledger"]].copy() if not manifest.empty else pd.DataFrame()
    source_requirements = pd.DataFrame([{
        "requirement_id": "25B8-FSRC-001",
        "required_artifact": "feature source or verified feature builder containing condition fields at raw-ledger entry_time granularity",
        "missing_feature_count": int(len(missing_manifest)),
        "examples": ";".join(missing_manifest["field"].head(20).astype(str).tolist()) if not missing_manifest.empty else "",
        "required_before_non_key_dry_run_implementation": True,
    }])
    write_csv(out_dir / "gold_v2_25b8_missing_feature_source_requirements.csv", source_requirements)

    can_plan_non_key = bool(not manifest.empty and len(missing_manifest) == 0)
    dry_run_feasibility = pd.DataFrame([
        {"check": "25B7 condition objects available", "observed": int(s25b7.get("condition_object_rows", 0)), "required": ">0", "status": "PASS" if int(s25b7.get("condition_object_rows", 0)) > 0 else "STOP"},
        {"check": "key-only loss groups exist", "observed": int(s25b7.get("key_only_loss_groups", 0)), "required": ">0", "status": "PASS" if int(s25b7.get("key_only_loss_groups", 0)) > 0 else "REVIEW"},
        {"check": "required fields present in raw ledger", "observed": int(manifest["present_in_raw_ledger"].sum()) if not manifest.empty else 0, "required": int(len(manifest)), "status": "PASS" if can_plan_non_key else "BLOCKED_FEATURE_SOURCE_REQUIRED"},
        {"check": "non-key dry-run implementation allowed now", "observed": False, "required": "feature source accepted first", "status": "BLOCKED"},
        {"check": "CoreB unblock allowed now", "observed": False, "required": "exact parity first", "status": "BLOCKED"},
    ])
    write_csv(out_dir / "gold_v2_25b8_condition_object_dry_run_feasibility.csv", dry_run_feasibility)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY", "allowed_now": True, "purpose": "Find audited feature source or builder covering required condition fields"},
        {"rank": 2, "next_step": "25B9_ALT_COREB_NON_KEY_DRY_RUN_IMPLEMENTATION", "allowed_now": can_plan_non_key, "purpose": "Only if all condition fields are available from source-of-truth features"},
        {"rank": 3, "next_step": "CoreB source recovery execution", "allowed_now": False, "purpose": "Still blocked"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "gold_v2_25b8_next_step_plan.csv", next_plan)

    status = PASS_STATUS if not problems else STOP_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_only": True,
        "status_problems": problems,
        "raw_ledger_rows": str(raw_rows),
        "raw_ledger_column_count": int(len(raw_cols)),
        "required_feature_count": int(len(manifest)),
        "features_present_in_raw_ledger": int(manifest["present_in_raw_ledger"].sum()) if not manifest.empty else 0,
        "features_missing_from_raw_ledger": int((~manifest["present_in_raw_ledger"]).sum()) if not manifest.empty else 0,
        "raw_ledger_sufficient_for_condition_object_dry_run": can_plan_non_key,
        "missing_feature_examples": missing_manifest["field"].head(20).astype(str).tolist() if not missing_manifest.empty else [],
        "key_only_loss_groups_from_25b7": int(s25b7.get("key_only_loss_groups", 0)),
        "condition_object_rows_from_25b7": int(s25b7.get("condition_object_rows", 0)),
        "non_key_dry_run_execution_allowed_now": False,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY",
        "total_stop_rows": int(len(problems)),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b8_coreb_condition_object_dry_run_plan_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B8 CoreB condition object dry-run plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B8 plans only. It checks whether condition-object fields are available in the raw ledger and does not execute a new dry-run.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Raw ledger field coverage",
        "",
        md_table(raw_coverage),
        "",
        "## Required feature manifest",
        "",
        md_table(manifest, max_rows=60),
        "",
        "## Missing feature source requirements",
        "",
        md_table(source_requirements),
        "",
        "## Dry-run feasibility",
        "",
        md_table(dry_run_feasibility),
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "CoreB remains blocked. No source recovery, mutation, live/final/external action is enabled.",
    ])
    lp(out_dir / "GOLD_V2_25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "required_feature_count": int(len(manifest)), "features_missing_from_raw_ledger": int((~manifest["present_in_raw_ledger"]).sum()) if not manifest.empty else 0, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
