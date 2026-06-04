#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13B audit: CoreA executable mapping freeze, audit-only.

This step treats the final SOT ledger and ABC stack-cap exploration ledgers as
historical source-of-truth, then separates:
  - CoreA rows/ABC/CAP policy that are verified in SOT
  - CoreA conditions that can already be checked from available source fields
  - CoreA conditions still blocked before a live evaluator may emit signals

No Discord, MT5, AI API, or live hook is used.
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

EXTERNAL_ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="13B audit CoreA executable mapping freeze")
    p.add_argument("--sot-ledger", default=None)
    p.add_argument("--core-dir", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_sot_ledger() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_final_portfolio_sot_freeze_audit_only" / "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"


def default_core_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_13b_corea_executable_mapping_freeze_audit_only"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {
            "count": 0,
            "win_rate_pct": math.nan,
            "pf": math.nan,
            "total_r": 0.0,
            "worst": math.nan,
            "maxdd": 0.0,
            "max_loss_streak": 0,
        }
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    equity = np.cumsum(vals)
    previous_peak = np.maximum.accumulate(np.r_[0.0, equity[:-1]])
    drawdown = np.maximum(previous_peak - equity, 0.0)
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


def normalize_source_ledger(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    d = df.copy()
    if "signal_ABC" not in d.columns:
        if "signal_fixed_ABC" in d.columns:
            d["signal_ABC"] = d["signal_fixed_ABC"]
        elif "signal" in d.columns:
            d["signal_ABC"] = d["signal"]
        else:
            d["signal_ABC"] = "REJECT"
    d["dataset"] = dataset
    d["entry_time"] = pd.to_datetime(d["top_entry_time"], errors="coerce")
    d["profit_corea"] = np.where(
        d["signal_ABC"].astype(str).eq("A"),
        to_number(d.get("profit_cap5_from_members", pd.Series([np.nan] * len(d), index=d.index))),
        to_number(d.get("profit_cap3_from_members", pd.Series([np.nan] * len(d), index=d.index))),
    )
    return d


def bool_true(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


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


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def input_audit(paths: list[tuple[str, Path]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role, path in paths:
        row: dict[str, Any] = {"role": role, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() == ".csv":
                tmp = pd.read_csv(path)
                row["rows"] = int(len(tmp))
                row["columns"] = int(len(tmp.columns))
            elif path.suffix.lower() == ".json":
                row["json_keys"] = ",".join(json.loads(path.read_text(encoding="utf-8")).keys())
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    sot_ledger = Path(args.sot_ledger).expanduser().resolve() if args.sot_ledger else default_sot_ledger()
    core_dir = Path(args.core_dir).expanduser().resolve() if args.core_dir else default_core_dir()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    core25_path = core_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv"
    core26_path = core_dir / "abc_stack_cap_2026_cluster_ledger.csv"
    portfolio_path = core_dir / "abc_stack_cap_2025_2026_portfolio_ledger.csv"
    breakdown_path = core_dir / "abc_stack_cap_2025_2026_signal_breakdown.csv"
    aggregate_path = core_dir / "abc_stack_cap_2025_2026_aggregate_summary.csv"
    top5_path = core_dir / "abc_stack_cap_2025_fold4_candidateA_top5_by_month.csv"
    manifest_path = repo_root() / "configs" / "gold_v2" / "frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"

    paths = [
        ("final_sot_ledger", sot_ledger),
        ("corea_2025_cluster_ledger", core25_path),
        ("corea_2026_cluster_ledger", core26_path),
        ("corea_portfolio_ledger", portfolio_path),
        ("corea_signal_breakdown", breakdown_path),
        ("corea_aggregate_summary", aggregate_path),
        ("corea_candidateA_top5_by_month", top5_path),
        ("frozen_corea_manifest", manifest_path),
    ]
    audit_df = input_audit(paths)
    write_csv(audit_df, output_dir / "gold_v2_13b_corea_input_audit.csv")

    final = read_csv_required(sot_ledger)
    final["entry_time"] = pd.to_datetime(final["entry_time"], errors="coerce")
    corea_final = final[final["source"].isin(["CORE_A_ONLY", "CORE_A_CORE_B_CONFLUENCE"])].copy()
    write_csv(corea_final, output_dir / "gold_v2_13b_corea_final_sot_rows.csv")

    core25 = read_csv_required(core25_path)
    core26 = read_csv_required(core26_path)
    source = pd.concat(
        [normalize_source_ledger(core25, "2025"), normalize_source_ledger(core26, "2026")],
        ignore_index=True,
    )
    selected = source[source["signal_ABC"].astype(str).ne("REJECT")].copy()
    write_csv(source, output_dir / "gold_v2_13b_corea_source_cluster_ledger_normalized.csv")
    write_csv(selected, output_dir / "gold_v2_13b_corea_selected_source_rows.csv")

    replay_rows: list[dict[str, Any]] = []
    for dataset, group in selected.groupby("dataset"):
        row = metrics(group["profit_corea"])
        row.update({"dataset": dataset, "view": "CoreA_selected_source_rows"})
        replay_rows.append(row)
    replay_summary = pd.DataFrame(replay_rows)
    write_csv(replay_summary, output_dir / "gold_v2_13b_corea_source_replay_summary.csv")

    abc_rows: list[dict[str, Any]] = []
    for signal_name in ["A", "B_rr15", "C_fixed", "REJECT"]:
        subset = source[source["signal_ABC"].astype(str).eq(signal_name)]
        for dataset, group in subset.groupby("dataset"):
            row: dict[str, Any] = {"dataset": dataset, "signal_ABC": signal_name, "rows": int(len(group))}
            for col in [
                "is_A",
                "is_B_rr15_fixed",
                "is_C_fixed",
                "regime",
                "rr",
                "range96",
                "trend_eff96",
                "ret96",
                "tr_mean_32",
                "same_direction_count",
                "unique_same_direction_origins",
                "has_opposite_conflict",
            ]:
                if col not in group.columns:
                    continue
                if col in ["regime", "has_opposite_conflict"]:
                    row[f"{col}_top_values"] = json.dumps(group[col].value_counts(dropna=False).head(5).to_dict(), ensure_ascii=False)
                else:
                    nums = to_number(group[col])
                    if nums.notna().any():
                        row[f"{col}_min"] = float(nums.min())
                        row[f"{col}_max"] = float(nums.max())
                        row[f"{col}_mean"] = float(nums.mean())
                    else:
                        row[f"{col}_non_null"] = int(group[col].notna().sum())
            if signal_name == "A" and "is_A" in group.columns:
                row["known_formula"] = "is_A ledger flag; underlying A gate not fully executable from available fields"
                row["known_formula_match_rows"] = int(bool_true(group["is_A"]).sum())
            elif signal_name == "B_rr15" and len(group):
                cond = (
                    group["regime"].astype(str).eq("MID_MIXED")
                    & (to_number(group["trend_eff96"]) >= 0.633155 - 1e-9)
                    & (to_number(group["rr"]) >= 1.5 - 1e-9)
                )
                row["known_formula"] = "regime==MID_MIXED AND trend_eff96>=0.633155 AND rr>=1.5"
                row["known_formula_match_rows"] = int(cond.sum())
            elif signal_name == "C_fixed" and len(group):
                range96 = to_number(group["range96"])
                cond = (range96 >= 100.43 - 1e-6) & (range96 <= 117.86 + 1e-6)
                row["known_formula"] = "100.43<=range96<=117.86"
                row["known_formula_match_rows"] = int(cond.sum())
            abc_rows.append(row)
    abc_inventory = pd.DataFrame(abc_rows)
    write_csv(abc_inventory, output_dir / "gold_v2_13b_corea_abc_gate_inventory.csv")

    cap_rows: list[dict[str, Any]] = []
    for dataset, group in selected.groupby("dataset"):
        for signal_name, subgroup in group.groupby("signal_ABC"):
            is_a = str(signal_name) == "A"
            profit_col = "profit_cap5_from_members" if is_a else "profit_cap3_from_members"
            row = metrics(to_number(subgroup[profit_col]))
            row.update(
                {
                    "dataset": dataset,
                    "signal_ABC": signal_name,
                    "sizing_policy": "CAP5" if is_a else "CAP3",
                    "profit_column": profit_col,
                }
            )
            cap_rows.append(row)
    cap_inventory = pd.DataFrame(cap_rows)
    write_csv(cap_inventory, output_dir / "gold_v2_13b_corea_cap_policy_inventory.csv")

    required_fields = pd.DataFrame(
        [
            {"component": "CORE_A", "scope": "cluster identity", "field": "ruleset=fold4_rules / 2026_WF_TOP2", "available_in_source": True, "live_mapping_status": "BLOCKED_EXPLICIT_RULESET_SOURCE_NEEDED", "reason": "ruleset label exists, but executable selected rule predicates behind fold4 need frozen mapping."},
            {"component": "CORE_A", "scope": "ABC A gate", "field": "is_A / signal_ABC=A", "available_in_source": True, "live_mapping_status": "BLOCKED_UNDERLYING_A_GATE_NEEDED", "reason": "Ledger has is_A flag and candidateA_top5_by_month has monthly chosen_names, but tail_hard/top5/all-consensus/stack KEEP predicates are not yet converted to live-computable conditions."},
            {"component": "CORE_A", "scope": "ABC B gate", "field": "regime, trend_eff96, rr, CoreA rejected", "available_in_source": True, "live_mapping_status": "PARTIALLY_EXECUTABLE_AFTER_FEATURE_PARITY", "reason": "Known B condition matches source rows; still requires exact regime/trend_eff96/rr calculation and CoreA rejected ordering."},
            {"component": "CORE_A", "scope": "ABC C gate", "field": "range96, CoreA rejected", "available_in_source": True, "live_mapping_status": "PARTIALLY_EXECUTABLE_AFTER_FEATURE_PARITY", "reason": "Known C range band matches source rows with tolerance; still requires exact range96 calculation and CoreA rejected ordering."},
            {"component": "CORE_A", "scope": "sizing", "field": "A uses CAP5; B/C use CAP3", "available_in_source": True, "live_mapping_status": "EXECUTABLE_POLICY_AFTER_ABC_MAPPING", "reason": "SOT sizing rule is clear; live risk conversion needs separate MT5-safe implementation later."},
            {"component": "CORE_A", "scope": "timing", "field": "entry_time = M15 open time + 15m close evaluation", "available_in_source": True, "live_mapping_status": "NEEDS_LIVE_FEATURE_SNAPSHOT_PARITY", "reason": "Historical entry_time exists, but live must compute from latest closed M15 and confirmed lower/feature bars."},
            {"component": "CORE_A", "scope": "direction", "field": "top_direction", "available_in_source": True, "live_mapping_status": "BLOCKED_SOURCE_RULE_DIRECTION_REPLAY", "reason": "Historical top_direction exists, but live needs selected rule hit direction from executable source predicates."},
        ]
    )
    write_csv(required_fields, output_dir / "gold_v2_13b_corea_required_fields.csv")

    unmapped = pd.DataFrame(
        [
            {"unmapped_id": "A001", "component": "CORE_A", "condition": "fold4_rules executable predicates", "status": "UNMAPPED", "severity": "HARD", "detail": "Only ruleset label and cluster ledger are present; underlying origin/filter rule predicates must be frozen before live evaluator."},
            {"unmapped_id": "A002", "component": "CORE_A", "condition": "ABC A tail_hard/top5/all-consensus/stack KEEP", "status": "UNMAPPED", "severity": "HARD", "detail": "is_A flag is present, but source formulas for A gate need explicit executable mapping. candidateA_top5_by_month is supportive, not enough alone."},
            {"unmapped_id": "A003", "component": "CORE_A", "condition": "CoreA rejected prerequisite for B/C", "status": "PARTIAL", "severity": "HARD", "detail": "B/C formula can be checked after CoreA rejected, but live ordering depends on full A/fold4 rule replay."},
            {"unmapped_id": "A004", "component": "CORE_A", "condition": "feature parity for range96/trend_eff96/regime/rr", "status": "PARTIAL", "severity": "HARD", "detail": "Fields exist in source ledger; live feature-builder parity must be proven from OHLC and confirmed candle timing."},
            {"unmapped_id": "A005", "component": "CORE_A", "condition": "historical cluster top_entry_time as trigger", "status": "FORBIDDEN", "severity": "HARD", "detail": "SOT row times may be used for audit replay only. They cannot be used as live signal trigger."},
        ]
    )
    write_csv(unmapped, output_dir / "gold_v2_13b_corea_unmapped_conditions.csv")

    blockers = pd.DataFrame(
        [
            {"blocker_id": "13B-B001", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "live CoreA signal", "required_resolution": "Freeze executable fold4_rules selected rule predicates from source exploration files."},
            {"blocker_id": "13B-B002", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "ABC A live mapping", "required_resolution": "Convert A gate tail_hard/top5/all-consensus/stack KEEP logic into explicit live-computable conditions and replay against 325 SOT CoreA rows."},
            {"blocker_id": "13B-B003", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "B/C replay parity", "required_resolution": "After A/fold4 mapping, prove B_rr15 and C_fixed formulas reproduce source rows using live feature snapshot."},
            {"blocker_id": "13B-B004", "component": "CORE_A", "status": "OPEN", "severity": "HARD", "blocked_item": "CAP5/CAP3 risk mapping", "required_resolution": "Map CAP5/CAP3 historical profit policy to live TP/SL/risk sizing without MT5 order calls."},
            {"blocker_id": "13B-B005", "component": "CORE_A", "status": "OPEN", "severity": "SAFETY", "blocked_item": "external actions", "required_resolution": "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false until all dry-run parity gates pass."},
        ]
    )
    write_csv(blockers, output_dir / "gold_v2_13b_corea_replay_blockers.csv")

    fields = [
        "ruleset",
        "scenario",
        "cluster_id",
        "top_entry_time",
        "top_direction",
        "top_candidate_id",
        "top_variant",
        "signal_ABC",
        "is_A",
        "is_B_rr15_fixed",
        "is_C_fixed",
        "profit_cap3_from_members",
        "profit_cap5_from_members",
        "range96",
        "trend_eff96",
        "ret96",
        "tr_mean_32",
        "regime",
        "rr",
        "same_direction_count",
        "unique_same_direction_origins",
        "same_direction_count_from_members",
        "unique_origins_from_members",
        "has_opposite_conflict",
    ]
    coverage_rows: list[dict[str, Any]] = []
    for dataset, group in source.groupby("dataset"):
        for field in fields:
            if field in group.columns:
                coverage_rows.append(
                    {
                        "dataset": dataset,
                        "field": field,
                        "rows": int(len(group)),
                        "nonnull_rows": int(group[field].notna().sum()),
                        "coverage_pct": float(100.0 * group[field].notna().mean()),
                    }
                )
            else:
                coverage_rows.append({"dataset": dataset, "field": field, "rows": int(len(group)), "nonnull_rows": 0, "coverage_pct": 0.0, "missing_column": True})
    coverage = pd.DataFrame(coverage_rows)
    write_csv(coverage, output_dir / "gold_v2_13b_corea_source_field_coverage.csv")

    if top5_path.exists():
        top5 = pd.read_csv(top5_path)
        write_csv(top5, output_dir / "gold_v2_13b_corea_candidateA_top5_by_month_copy.csv")
        top5_inventory = pd.DataFrame(
            {
                "test_month": top5["test_month"],
                "train_count": top5["train_count"],
                "chosen_name_count": top5["chosen_names"].astype(str).apply(lambda x: 0 if x == "INSUFFICIENT_TRAIN" else len([y for y in x.split("|") if y.strip()])),
                "has_insufficient_train": top5["chosen_names"].astype(str).eq("INSUFFICIENT_TRAIN"),
                "mapping_status": "SUPPORTIVE_NOT_EXECUTABLE_FULL_A_GATE",
            }
        )
        write_csv(top5_inventory, output_dir / "gold_v2_13b_corea_candidateA_top5_inventory.csv")

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COREA_SOT_READY_EXECUTABLE_MAPPING_BLOCKED_AUDIT_ONLY",
        "audit_only": True,
        "corea_sot_rows": int(len(corea_final)),
        "corea_source_selected_rows": int(len(selected)),
        "dataset_counts": {str(k): int(v) for k, v in corea_final.groupby("dataset").size().to_dict().items()},
        "signal_counts": {str(k): int(v) for k, v in corea_final["signal_ABC"].value_counts(dropna=False).to_dict().items()},
        "source_signal_counts": {f"{dataset}|{signal}": int(v) for (dataset, signal), v in selected.groupby(["dataset", "signal_ABC"]).size().to_dict().items()},
        "abc_gate_status": {
            "A": "BLOCKED_UNDERLYING_A_GATE_NEEDED",
            "B_rr15": "PARTIALLY_EXECUTABLE_AFTER_FEATURE_PARITY",
            "C_fixed": "PARTIALLY_EXECUTABLE_AFTER_FEATURE_PARITY",
        },
        "cap_policy_status": "EXECUTABLE_POLICY_AFTER_ABC_MAPPING",
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "blockers": blockers.to_dict(orient="records"),
    }
    (output_dir / "gold_v2_13b_corea_mapping_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13B CoreA executable mapping freeze audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Purpose",
        "13B audits whether CoreA = fold4_rules + ABC gate + A_CAP5_BC_CAP3 can be converted from historical SOT ledgers into a live evaluator mapping.",
        "",
        "## Final decision",
        "- CoreA historical SOT rows are ready.",
        "- CoreA live evaluator is still blocked.",
        "- Historical top_entry_time / cluster_id rows must not be used as live triggers.",
        "- Discord, MT5, AI API, and live hook remain disabled.",
        "",
        "## CoreA SOT summary",
        markdown_table(replay_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]),
        "",
        "## ABC gate inventory",
        markdown_table(abc_inventory, ["dataset", "signal_ABC", "rows", "known_formula", "known_formula_match_rows", "range96_min", "range96_max", "trend_eff96_min", "trend_eff96_max", "rr_min", "rr_max"]),
        "",
        "## CAP policy inventory",
        markdown_table(cap_inventory, ["dataset", "signal_ABC", "sizing_policy", "profit_column", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd"]),
        "",
        "## Required fields / structures",
        markdown_table(required_fields, ["component", "scope", "field", "available_in_source", "live_mapping_status", "reason"]),
        "",
        "## Unmapped / blocked conditions",
        markdown_table(unmapped, ["unmapped_id", "component", "condition", "status", "severity", "detail"]),
        "",
        "## Replay blockers",
        markdown_table(blockers, ["blocker_id", "component", "severity", "blocked_item", "required_resolution"]),
        "",
        "## Safety",
        "- final_signal_allowed: false",
        "- step13_allowed: false",
        "- Discord/MT5/AI/live_hook: false",
        "",
    ]
    (output_dir / "GOLD_V2_13B_COREA_EXECUTABLE_MAPPING_FREEZE_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"status": summary["status"], "output_dir": str(output_dir), "corea_sot_rows": summary["corea_sot_rows"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
