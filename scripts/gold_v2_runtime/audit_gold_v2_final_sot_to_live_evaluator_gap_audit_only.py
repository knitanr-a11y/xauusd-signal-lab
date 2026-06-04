#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit GOLD V2 final SOT ledger gaps before live evaluator implementation.

This 13A step treats the final CoreA/CoreB/MEDIUM SOT ledger as historical
source-of-truth and explicitly separates:
  - what is frozen/verified as historical SOT
  - what is still missing before a live evaluator may emit signals

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="13A audit final SOT -> live evaluator gaps")
    p.add_argument("--sot-ledger", default=None)
    p.add_argument("--coreb-definition", default="configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json")
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
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_13a_sot_to_live_evaluator_gap_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else (repo_root() / p).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0, "worst": math.nan, "maxdd": 0.0, "max_loss_streak": 0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    equity = np.cumsum(vals)
    prior_peak = np.maximum.accumulate(np.r_[0.0, equity[:-1]])
    drawdown = np.maximum(prior_peak - equity, 0.0)
    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": int(len(vals)),
        "win_rate_pct": float((vals > 0).mean() * 100.0),
        "pf": float(pf) if not math.isnan(pf) else math.nan,
        "total_r": float(vals.sum()),
        "worst": float(vals.min()),
        "maxdd": float(drawdown.max()) if len(drawdown) else 0.0,
        "max_loss_streak": int(max_streak),
    }


def fmt_cell(value: Any) -> str:
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


def markdown_table(df: pd.DataFrame, cols: Optional[Sequence[str]] = None) -> str:
    if cols is not None:
        df = df[[c for c in cols if c in df.columns]].copy()
    if df.empty:
        return "_No rows._"
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt_cell(row[c]) for c in df.columns) + " |")
    return "\n".join(lines)


def safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def extract_coreb_required_fields(coreb_definition: Path) -> list[str]:
    obj = safe_read_json(coreb_definition)
    for key in ["required_fields", "required_feature_fields", "required_field_names", "required_predicate_fields"]:
        value = obj.get(key)
        if isinstance(value, list):
            return [str(x) for x in value]
    return []


def make_input_audit(paths: list[tuple[str, Path]]) -> pd.DataFrame:
    rows = []
    for role, path in paths:
        row: dict[str, Any] = {"role": role, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() == ".csv":
                tmp = pd.read_csv(path)
                row["rows"] = int(len(tmp))
                row["columns"] = int(len(tmp.columns))
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    sot_ledger = Path(args.sot_ledger).expanduser().resolve() if args.sot_ledger else default_sot_ledger()
    coreb_definition = resolve_repo_path(args.coreb_definition)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not sot_ledger.exists():
        raise FileNotFoundError(f"SOT ledger not found: {sot_ledger}")

    df = pd.read_csv(sot_ledger)
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")

    input_audit = make_input_audit([
        ("final_portfolio_sot_ledger", sot_ledger),
        ("optional_coreb_combined_evaluator_definition", coreb_definition),
    ])
    input_audit.to_csv(output_dir / "gold_v2_13a_input_audit.csv", index=False, encoding="utf-8-sig")

    final_summary_rows = []
    for dataset, group in df.groupby("dataset"):
        row = metrics(group["profit_r"])
        row.update({"dataset": dataset, "view": "FINAL_SOT"})
        final_summary_rows.append(row)
    final_summary = pd.DataFrame(final_summary_rows)
    final_summary.to_csv(output_dir / "gold_v2_13a_final_sot_summary.csv", index=False, encoding="utf-8-sig")

    source_rows = []
    for (dataset, source), group in df.groupby(["dataset", "source"]):
        row = metrics(group["profit_r"])
        row.update({"dataset": dataset, "source": source})
        source_rows.append(row)
    source_breakdown = pd.DataFrame(source_rows).sort_values(["dataset", "source"])
    source_breakdown.to_csv(output_dir / "gold_v2_13a_source_breakdown.csv", index=False, encoding="utf-8-sig")

    feature_candidates = [
        "signal_ABC", "top_candidate_id", "top_variant", "same_direction_count", "unique_same_direction_origins",
        "range96", "trend_eff96", "ret96", "tr_mean_32", "regime", "same_count", "unique_origins",
        "rr_bucket", "source_rule_count", "refined_rule", "priority",
    ]
    field_rows = []
    for source, group in df.groupby("source"):
        for col in feature_candidates:
            if col in df.columns:
                nonnull = int(group[col].notna().sum())
                field_rows.append({"source": source, "field": col, "nonnull_rows": nonnull, "rows": int(len(group)), "coverage_pct": 100.0 * nonnull / len(group) if len(group) else 0.0})
    field_coverage = pd.DataFrame(field_rows)
    field_coverage.to_csv(output_dir / "gold_v2_13a_sot_field_coverage_by_source.csv", index=False, encoding="utf-8-sig")

    required_rows = []
    for field in extract_coreb_required_fields(coreb_definition):
        required_rows.append({"component": "CORE_B_RR125", "field": field, "source": str(coreb_definition), "live_requirement": "must calculate exactly at eval_time"})
    if not required_rows:
        for field in ["ret_144_atr", "donch_pos_144", "range_96_atr", "m5_ret_96_atr", "same_count_source_hit_count"]:
            required_rows.append({"component": "CORE_B_RR125", "field": field, "source": "fallback_known_coreb_fields", "live_requirement": "must calculate exactly at eval_time"})
    for field in ["range96", "trend_eff96", "ret96", "tr_mean_32", "regime", "top_direction", "CoreA_REJECT", "entry_time_arbitration"]:
        required_rows.append({"component": "MEDIUM", "field": field, "source": "coreb_refined_rule_ledgers/final_sot_ledger", "live_requirement": "must calculate or derive before MEDIUM eligibility"})
    for field in ["fold4_rules_explicit_conditions", "ABC_gate_A_tail_hard_top5_all_consensus_stack_KEEP", "ABC_gate_B_CoreA_rejected_regime_MID_MIXED_trend_eff96_RR", "ABC_gate_C_range96_band", "CAP5_CAP3_sizing_policy", "confirmed_entry_time_feature_snapshot"]:
        required_rows.append({"component": "CORE_A", "field": field, "source": "abc_stack_cap exploration ledgers/docs", "live_requirement": "must freeze executable rule/mapping; cannot use historical entry_time only"})
    required_live = pd.DataFrame(required_rows)
    required_live.to_csv(output_dir / "gold_v2_13a_required_live_fields_and_structures.csv", index=False, encoding="utf-8-sig")

    component_status = pd.DataFrame([
        {"component": "FINAL_PORTFOLIO_SOT", "sot_status": "READY", "row_count": int(len(df)), "live_evaluator_status": "NOT_A_LIVE_EVALUATOR", "blocking_level": "GLOBAL", "final_signal_allowed": False, "detail": "Historical final SOT ledger is verified and safe as source ledger."},
        {"component": "CORE_A", "sot_status": "ROW_LEDGER_READY", "row_count": int(df["source"].isin(["CORE_A_ONLY", "CORE_A_CORE_B_CONFLUENCE"]).sum()), "live_evaluator_status": "BLOCKED_MAPPING_REQUIRED", "blocking_level": "HARD", "final_signal_allowed": False, "detail": "Need executable fold4_rules + ABC gate + CAP5/CAP3 mapping. Historical top_entry_time/cluster hits cannot be used as live trigger."},
        {"component": "CORE_B_RR125", "sot_status": "SOURCE_RULES_AND_SOT_ROWS_READY", "row_count": int(df["source"].isin(["CORE_B_ONLY", "CORE_A_CORE_B_CONFLUENCE"]).sum()), "live_evaluator_status": "BLOCKED_FEATURE_AND_SAME_COUNT_PARITY_REQUIRED", "blocking_level": "HARD", "final_signal_allowed": False, "detail": "12 selected rules and same_count source universe exist, but live feature formula/time alignment and same_count replay parity must be proven."},
        {"component": "MEDIUM", "sot_status": "REFINED_RULE_ROWS_READY", "row_count": int(df["source"].astype(str).str.startswith("MEDIUM_").sum()), "live_evaluator_status": "BLOCKED_HIGH_ARBITRATION_AND_FEATURE_PARITY_REQUIRED", "blocking_level": "HARD", "final_signal_allowed": False, "detail": "Need exact range96/trend_eff96/ret96/tr_mean_32/regime computation, CoreA_REJECT, and high-priority arbitration."},
        {"component": "EXTERNAL_ACTIONS", "sot_status": "OFF", "row_count": 0, "live_evaluator_status": "DISABLED_BY_POLICY", "blocking_level": "SAFETY", "final_signal_allowed": False, "detail": "Discord, MT5, AI API, and live hook remain disabled."},
    ])
    component_status.to_csv(output_dir / "gold_v2_13a_component_live_evaluator_gap_status.csv", index=False, encoding="utf-8-sig")

    blockers = pd.DataFrame([
        {"blocker_id": "B001", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "live CoreA signal", "required_resolution": "Freeze executable fold4_rules and ABC gate mapping from source, not historical entry_time."},
        {"blocker_id": "B002", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "live CoreA sizing", "required_resolution": "Implement and audit A_CAP5_BC_CAP3 sizing using live-computable fields."},
        {"blocker_id": "B003", "component": "CORE_B_RR125", "status": "OPEN", "severity": "HARD", "blocked_item": "live CoreB same_count", "required_resolution": "Prove same_count_source_hit_count >= 15 reproduces rr125_top_ledgers/top-ledger clustering on historical data."},
        {"blocker_id": "B004", "component": "CORE_B_RR125", "status": "OPEN", "severity": "HARD", "blocked_item": "live CoreB predicates", "required_resolution": "Prove all *_atr, donch_pos, compression, m5_* feature formulas and M15/M5 asof timing."},
        {"blocker_id": "B005", "component": "MEDIUM", "status": "OPEN", "severity": "HARD", "blocked_item": "live MEDIUM direction and eligibility", "required_resolution": "Implement exact top_direction/PROBE-to-direction logic, TIER2_HVT regime, CoreA_REJECT, and high arbitration."},
        {"blocker_id": "B006", "component": "GLOBAL", "status": "OPEN", "severity": "HARD", "blocked_item": "final_signal_allowed", "required_resolution": "Run live evaluator dry-run parity and preflight before enabling any SIGNAL output."},
        {"blocker_id": "B007", "component": "SAFETY", "status": "OPEN", "severity": "SAFETY", "blocked_item": "external actions", "required_resolution": "Explicit user permission required after all audit gates pass."},
    ])
    blockers.to_csv(output_dir / "gold_v2_13a_live_evaluator_blockers.csv", index=False, encoding="utf-8-sig")

    examples = df.sort_values(["dataset", "entry_time"]).groupby("source", group_keys=False).head(5)
    examples.to_csv(output_dir / "gold_v2_13a_sot_examples_by_source.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FINAL_SOT_READY_LIVE_EVALUATOR_BLOCKED_BY_GAPS_AUDIT_ONLY",
        "audit_only": True,
        "sot_ledger": str(sot_ledger),
        "sot_ledger_sha256": sha256_file(sot_ledger),
        "sot_rows": int(len(df)),
        "dataset_counts": {str(k): int(v) for k, v in df.groupby("dataset").size().items()},
        "source_counts": {str(k): int(v) for k, v in df.groupby("source").size().items()},
        "component_status": component_status.to_dict(orient="records"),
        "blockers": blockers.to_dict(orient="records"),
        "external_actions": EXTERNAL_ACTIONS,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
    }
    (output_dir / "gold_v2_13a_sot_to_live_evaluator_gap_summary.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13A SOT to live evaluator gap audit-only report", "",
        f"Created UTC: {manifest['created_utc']}",
        f"Status: `{manifest['status']}`", "",
        "## Final SOT summary", markdown_table(final_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]), "",
        "## Component live evaluator status", markdown_table(component_status, ["component", "sot_status", "row_count", "live_evaluator_status", "blocking_level", "final_signal_allowed", "detail"]), "",
        "## Open blockers", markdown_table(blockers, ["blocker_id", "component", "severity", "blocked_item", "required_resolution"]), "",
        "## Source breakdown", markdown_table(source_breakdown, ["dataset", "source", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd"]), "",
        "## Required live fields and structures", markdown_table(required_live.head(160), ["component", "field", "source", "live_requirement"]), "",
        "## Safety", "- Audit-only: true", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
    ]
    (output_dir / "GOLD_V2_13A_SOT_TO_LIVE_EVALUATOR_GAP_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"status": manifest["status"], "output_dir": str(output_dir), "sot_rows": int(len(df))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
