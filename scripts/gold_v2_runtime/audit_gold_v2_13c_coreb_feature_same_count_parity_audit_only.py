#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13C audit: CoreB feature / same_count parity, audit-only.

This step audits the frozen CoreB RR1.25 BUY confluence definition against the
historical SOT ledgers and existing feature/replay artifacts. It intentionally
separates source readiness from live-evaluator parity.

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

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="13C audit CoreB feature/same_count parity")
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_output_dir() -> Path:
    return fx_outputs() / "gold_v2_13c_coreb_feature_same_count_parity_audit_only"


def first_existing(candidates: Sequence[Path], filename: Optional[str] = None) -> Path:
    for p in candidates:
        if p.exists():
            return p
    if filename:
        matches = list(fx_outputs().rglob(filename))
        if matches:
            return matches[0]
    return candidates[0]


def paths() -> dict[str, Path]:
    rr = fx_outputs() / "gold_v2_rr125_second_core_probe_outputs"
    feature = fx_outputs() / "gold_v2_coreb_combined_required_feature_snapshot_audit_only"
    feature_alt = fx_outputs() / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_audit_only"
    replay = fx_outputs() / "gold_v2_coreb_combined_evaluator_replay_audit_only"
    final = fx_outputs() / "gold_v2_final_portfolio_sot_freeze_audit_only"
    return {
        "final_sot_ledger": first_existing([final / "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"], "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"),
        "coreb_definition": repo_root() / "configs" / "gold_v2" / "frozen_coreB_combined_evaluator_definition_20260604.json",
        "rr125_top_ledgers": first_existing([rr / "rr125_top_ledgers.csv"], "rr125_top_ledgers.csv"),
        "rr125_raw_signal_ledger": first_existing([rr / "rr125_raw_signal_ledger.csv"], "rr125_raw_signal_ledger.csv"),
        "rr125_filter_results": first_existing([rr / "rr125_filter_results.csv"], "rr125_filter_results.csv"),
        "rr125_recommended_filters": first_existing([rr / "rr125_recommended_filters.csv"], "rr125_recommended_filters.csv"),
        "required_feature_snapshot": first_existing([feature / "gold_v2_coreb_combined_required_feature_snapshot.csv", feature_alt / "gold_v2_coreb_combined_required_feature_snapshot.csv"], "gold_v2_coreb_combined_required_feature_snapshot.csv"),
        "required_feature_schema": first_existing([feature / "gold_v2_coreb_combined_required_feature_schema.csv", feature_alt / "gold_v2_coreb_combined_required_feature_schema.csv"], "gold_v2_coreb_combined_required_feature_schema.csv"),
        "feature_coverage_audit_checks": first_existing([feature_alt / "gold_v2_coreb_combined_feature_coverage_audit_checks.csv", feature / "gold_v2_coreb_combined_feature_coverage_audit_checks.csv"], "gold_v2_coreb_combined_feature_coverage_audit_checks.csv"),
        "selected_conditions": first_existing([feature / "gold_v2_coreb_combined_selected_conditions.csv"], "gold_v2_coreb_combined_selected_conditions.csv"),
        "same_count_conditions": first_existing([feature / "gold_v2_coreb_combined_same_count_conditions.csv"], "gold_v2_coreb_combined_same_count_conditions.csv"),
        "combined_replay_summary": first_existing([replay / "gold_v2_coreb_combined_evaluator_replay_summary.json"], "gold_v2_coreb_combined_evaluator_replay_summary.json"),
        "combined_replay_rows": first_existing([replay / "gold_v2_coreb_combined_evaluator_replay_rows.csv"], "gold_v2_coreb_combined_evaluator_replay_rows.csv"),
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0, "worst": math.nan, "maxdd": 0.0, "max_loss_streak": 0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    equity = np.cumsum(vals)
    prior_peak = np.maximum.accumulate(np.r_[0.0, equity[:-1]])
    dd = np.maximum(prior_peak - equity, 0.0)
    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {"count": int(len(vals)), "win_rate_pct": float((vals > 0).mean() * 100.0), "pf": float(pf) if not math.isnan(pf) else math.nan, "total_r": float(vals.sum()), "worst": float(vals.min()), "maxdd": float(dd.max()), "max_loss_streak": int(max_streak)}


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


def input_audit(path_map: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role, path in path_map.items():
        row: dict[str, Any] = {"role": role, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() == ".csv":
                tmp = pd.read_csv(path)
                row["rows"] = int(len(tmp))
                row["columns"] = int(len(tmp.columns))
            elif path.suffix.lower() == ".json":
                obj = read_json(path)
                row["json_keys"] = ",".join(obj.keys()) if isinstance(obj, dict) else ""
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    pm = paths()

    audit = input_audit(pm)
    write_csv(audit, output_dir / "gold_v2_13c_coreb_input_audit.csv")

    definition = read_json(pm["coreb_definition"])
    rr_top = read_csv(pm["rr125_top_ledgers"])
    final = read_csv(pm["final_sot_ledger"])
    raw = read_csv(pm["rr125_raw_signal_ledger"])
    feature_snapshot = read_csv(pm["required_feature_snapshot"])
    feature_schema = read_csv(pm["required_feature_schema"])
    replay_summary = read_json(pm["combined_replay_summary"])
    replay_rows = read_csv(pm["combined_replay_rows"])

    selected_rules = definition.get("selected_rules", [])
    same_rules = definition.get("same_count_source_rules", [])
    required_fields = definition.get("required_fields", [])
    condition_rows: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    for rule_set, rules in [("selected", selected_rules), ("same_count_source", same_rules)]:
        for rule in rules:
            conds = rule.get("base_condition_objects", []) + rule.get("added_filter_condition_objects", [])
            rule_rows.append({"rule_set": rule_set, "rule_id": rule.get("rule_id"), "candidate_id": rule.get("candidate_id"), "origin_id": rule.get("origin_id"), "direction": rule.get("direction"), "variant": rule.get("variant"), "condition_count": len(conds), "source_row_count": rule.get("source_row_count"), "base_condition": rule.get("base_condition"), "added_filter_text": rule.get("added_filter_text")})
            for c in conds:
                row = dict(c)
                row.update({"rule_set": rule_set, "candidate_id": rule.get("candidate_id"), "origin_id": rule.get("origin_id"), "variant": rule.get("variant")})
                condition_rows.append(row)
    rule_inventory = pd.DataFrame(rule_rows)
    condition_inventory = pd.DataFrame(condition_rows)
    write_csv(rule_inventory, output_dir / "gold_v2_13c_coreb_rule_inventory.csv")
    write_csv(condition_inventory, output_dir / "gold_v2_13c_coreb_condition_inventory.csv")

    required_set = set(map(str, required_fields))
    cond_fields = set(condition_inventory["field"].dropna().astype(str)) if not condition_inventory.empty else set()
    field_inventory = pd.DataFrame([{"field": f, "in_required_fields": f in required_set, "used_in_conditions": f in cond_fields, "condition_count": int((condition_inventory["field"].astype(str) == f).sum()) if not condition_inventory.empty else 0} for f in sorted(required_set | cond_fields)])
    write_csv(field_inventory, output_dir / "gold_v2_13c_coreb_required_field_inventory.csv")

    selected_top = rr_top[(rr_top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (rr_top["filter"].astype(str).eq("same_count>=15"))].copy()
    write_csv(selected_top, output_dir / "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv")
    standalone_rows = []
    for dataset, group in selected_top.groupby("dataset"):
        row = metrics(group["profit"])
        row.update({"dataset": dataset, "view": "CoreB_RR125_from_RR1_rules_same_count_ge_15_standalone"})
        standalone_rows.append(row)
    standalone_summary = pd.DataFrame(standalone_rows)
    write_csv(standalone_summary, output_dir / "gold_v2_13c_coreb_standalone_summary.csv")

    coreb_final = final[final["source"].isin(["CORE_B_ONLY", "CORE_A_CORE_B_CONFLUENCE"])].copy()
    write_csv(coreb_final, output_dir / "gold_v2_13c_coreb_final_sot_rows.csv")
    final_rows = []
    for dataset, group in coreb_final.groupby("dataset"):
        vals = group["coreb_profit_r"].fillna(group["profit_r"]) if "coreb_profit_r" in group.columns else group["profit_r"]
        row = metrics(vals)
        row.update({"dataset": dataset, "view": "CoreB_rows_in_final_sot_coreb_contribution"})
        final_rows.append(row)
    final_coreb_summary = pd.DataFrame(final_rows)
    write_csv(final_coreb_summary, output_dir / "gold_v2_13c_coreb_final_sot_contribution_summary.csv")

    raw_rr1 = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    entry_counts = raw_rr1.groupby(["dataset", "entry_time"]).agg(raw_same_entry_count=("candidate_id", "size"), raw_unique_origins_at_entry=("origin_id", "nunique")).reset_index()
    sc = selected_top.merge(entry_counts, on=["dataset", "entry_time"], how="left")
    sc["same_count_equals_raw_same_entry_count"] = sc["same_count"] == sc["raw_same_entry_count"]
    sc["unique_origins_equals_raw_unique_origins_at_entry"] = sc["unique_origins"] == sc["raw_unique_origins_at_entry"]
    write_csv(sc, output_dir / "gold_v2_13c_coreb_same_count_sanity_against_raw_entry_time.csv")
    same_count_summary = pd.DataFrame([
        {"check": "selected_top_rows", "value": len(sc), "detail": "CoreB standalone selected top-ledger rows"},
        {"check": "same_count_equals_raw_same_entry_count_rows", "value": int(sc["same_count_equals_raw_same_entry_count"].sum()), "detail": "Expected 0 if same_count is source-universe cluster count, not exact entry_time row count"},
        {"check": "unique_origins_entry_time_match_rows", "value": int(sc["unique_origins_equals_raw_unique_origins_at_entry"].sum()), "detail": "Diagnostic only"},
        {"check": "min_same_count", "value": int(sc["same_count"].min()), "detail": "must be >=15 for selected CoreB"},
        {"check": "max_same_count", "value": int(sc["same_count"].max()), "detail": "diagnostic"},
    ])
    write_csv(same_count_summary, output_dir / "gold_v2_13c_coreb_same_count_sanity_summary.csv")

    complete_rows = int(feature_snapshot.get("coreb_combined_required_fields_complete", pd.Series(dtype=bool)).astype(bool).sum())
    parity_checks = pd.DataFrame([
        {"check": "definition_selected_rule_count", "observed": len(selected_rules), "expected": 12, "ok": len(selected_rules) == 12},
        {"check": "definition_same_count_source_rule_count", "observed": len(same_rules), "expected": 33, "ok": len(same_rules) == 33},
        {"check": "definition_selected_condition_count", "observed": int((condition_inventory.rule_set == "selected").sum()), "expected": 65, "ok": int((condition_inventory.rule_set == "selected").sum()) == 65},
        {"check": "definition_same_count_condition_count", "observed": int((condition_inventory.rule_set == "same_count_source").sum()), "expected": 181, "ok": int((condition_inventory.rule_set == "same_count_source").sum()) == 181},
        {"check": "definition_required_field_count", "observed": len(required_fields), "expected": 38, "ok": len(required_fields) == 38},
        {"check": "all_condition_fields_in_required_fields", "observed": len(cond_fields - required_set), "expected": 0, "ok": len(cond_fields - required_set) == 0},
        {"check": "feature_snapshot_rows", "observed": len(feature_snapshot), "expected": 30273, "ok": len(feature_snapshot) == 30273},
        {"check": "feature_complete_rows", "observed": complete_rows, "expected": 30129, "ok": complete_rows == 30129},
        {"check": "candidate_replay_coreb_signal_rows", "observed": replay_summary.get("coreb_candidate_signal_rows"), "expected": replay_summary.get("expected_user_backtest_coreb_2025_trades", 0) + replay_summary.get("expected_user_backtest_coreb_2026_trades", 0), "ok": False},
        {"check": "candidate_formula_parity_status", "observed": replay_summary.get("parity_status"), "expected": "PROVEN_PARITY", "ok": replay_summary.get("parity_status") == "PROVEN_PARITY"},
    ])
    write_csv(parity_checks, output_dir / "gold_v2_13c_coreb_parity_checks.csv")
    write_csv(feature_schema, output_dir / "gold_v2_13c_coreb_required_feature_schema_copy.csv")

    replay_signals = replay_rows[replay_rows["coreb_combined_candidate_signal"].astype(bool)].copy()
    write_csv(replay_signals, output_dir / "gold_v2_13c_coreb_candidate_replay_signal_rows.csv")
    monthly_rows = []
    for ym, group in replay_rows.groupby("year_month"):
        monthly_rows.append({"year_month": ym, "rows": len(group), "complete_rows": int(group["required_fields_complete"].sum()), "selected_hit_rows": int((group["selected_rule_hit_count"] > 0).sum()), "same_count_pass_rows": int((group["same_count_source_hit_count"] >= 15).sum()), "candidate_signal_rows": int(group["coreb_combined_candidate_signal"].astype(bool).sum()), "max_selected_hit_count": int(group["selected_rule_hit_count"].max()), "max_same_count_source_hit_count": int(group["same_count_source_hit_count"].max())})
    candidate_monthly = pd.DataFrame(monthly_rows)
    write_csv(candidate_monthly, output_dir / "gold_v2_13c_coreb_candidate_replay_monthly.csv")

    blockers = pd.DataFrame([
        {"blocker_id": "13C-B001", "component": "CORE_B_RR125", "severity": "HARD", "status": "OPEN", "blocked_item": "live CoreB parity", "required_resolution": "Candidate replay currently produces 7 signal rows vs expected 125 standalone historical CoreB trades; formula is not source-validated."},
        {"blocker_id": "13C-B002", "component": "CORE_B_RR125", "severity": "HARD", "status": "OPEN", "blocked_item": "same_count live reproduction", "required_resolution": "Prove same_count_source_hit_count>=15 reproduces rr125_top_ledgers cluster universe, not just exact entry_time raw count."},
        {"blocker_id": "13C-B003", "component": "CORE_B_RR125", "severity": "HARD", "status": "OPEN", "blocked_item": "feature formula/asof parity", "required_resolution": "Prove 38 required fields from M15/M5 OHLC match frozen source feature semantics at eval_time."},
        {"blocker_id": "13C-B004", "component": "CORE_B_RR125", "severity": "HARD", "status": "OPEN", "blocked_item": "selected 12 rule replay", "required_resolution": "Replay 12 selected rules and 33 same_count source rules against historical feature snapshots and compare to rr125_top_ledgers."},
        {"blocker_id": "13C-B005", "component": "SAFETY", "severity": "SAFETY", "status": "OPEN", "blocked_item": "external actions", "required_resolution": "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false until dry-run parity passes."},
    ])
    write_csv(blockers, output_dir / "gold_v2_13c_coreb_replay_blockers.csv")

    component_status = pd.DataFrame([
        {"component": "CORE_B_DEFINITION", "sot_status": "READY", "live_evaluator_status": "MAPPING_PRESENT_BUT_PARITY_NOT_PROVEN", "final_signal_allowed": False, "detail": definition.get("status")},
        {"component": "CORE_B_REQUIRED_FEATURES", "sot_status": "READY", "live_evaluator_status": "FEATURE_FORMULA_ASOF_PARITY_REQUIRED", "final_signal_allowed": False, "detail": f"38 required fields present in snapshot; {complete_rows} complete rows / {len(feature_snapshot)} total rows"},
        {"component": "CORE_B_SELECTED_RULES", "sot_status": "READY", "live_evaluator_status": "REPLAY_PARITY_REQUIRED", "final_signal_allowed": False, "detail": "12 selected rules / 65 conditions; all condition fields covered by required fields"},
        {"component": "CORE_B_SAME_COUNT_SOURCE", "sot_status": "READY", "live_evaluator_status": "SAME_COUNT_CLUSTER_PARITY_REQUIRED", "final_signal_allowed": False, "detail": "33 same-count source rules / 181 conditions; same_count>=15 target exists in rr125_top_ledgers"},
        {"component": "CORE_B_CANDIDATE_REPLAY", "sot_status": "NOT_PROVEN", "live_evaluator_status": "BLOCKED", "final_signal_allowed": False, "detail": f"candidate replay signal rows={replay_summary.get('coreb_candidate_signal_rows')} vs expected standalone={replay_summary.get('expected_user_backtest_coreb_2025_trades', 0) + replay_summary.get('expected_user_backtest_coreb_2026_trades', 0)}; parity_status={replay_summary.get('parity_status')}"},
        {"component": "EXTERNAL_ACTIONS", "sot_status": "OFF", "live_evaluator_status": "DISABLED_BY_POLICY", "final_signal_allowed": False, "detail": "Discord/MT5/AI/live_hook disabled"},
    ])
    write_csv(component_status, output_dir / "gold_v2_13c_coreb_component_status.csv")

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COREB_SOURCE_READY_FEATURE_SAME_COUNT_PARITY_NOT_PROVEN_AUDIT_ONLY",
        "audit_only": True,
        "coreb_definition_status": definition.get("status"),
        "selected_rule_count": len(selected_rules),
        "same_count_source_rule_count": len(same_rules),
        "selected_condition_count": int((condition_inventory.rule_set == "selected").sum()),
        "same_count_source_condition_count": int((condition_inventory.rule_set == "same_count_source").sum()),
        "required_field_count": len(required_fields),
        "condition_fields_missing_from_required_fields": sorted(list(cond_fields - required_set)),
        "standalone_coreb_counts": {str(k): int(v) for k, v in selected_top.groupby("dataset").size().items()},
        "final_sot_coreb_rows": int(len(coreb_final)),
        "feature_snapshot_rows": int(len(feature_snapshot)),
        "feature_complete_rows": int(complete_rows),
        "candidate_replay_summary": replay_summary,
        "parity_status": "NOT_PROVEN",
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "blockers": blockers.to_dict(orient="records"),
    }
    (output_dir / "gold_v2_13c_coreb_parity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13C CoreB feature / same_count parity audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Final decision",
        "- CoreB source definition is ready as a frozen candidate definition.",
        "- CoreB live evaluator parity is **not proven**.",
        "- Candidate formula replay currently does not reproduce the 104 + 21 standalone CoreB historical trades.",
        "- Historical same_count/top-ledger rows must not be reused as live signal triggers.",
        "- Discord, MT5, AI API, and live hook remain disabled.",
        "",
        "## CoreB standalone source summary",
        markdown_table(standalone_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]),
        "",
        "## CoreB rows in final SOT ledger",
        markdown_table(final_coreb_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]),
        "",
        "## Component status",
        markdown_table(component_status, ["component", "sot_status", "live_evaluator_status", "final_signal_allowed", "detail"]),
        "",
        "## Parity checks",
        markdown_table(parity_checks, ["check", "observed", "expected", "ok"]),
        "",
        "## Same-count sanity summary",
        markdown_table(same_count_summary, ["check", "value", "detail"]),
        "",
        "## Rule inventory",
        markdown_table(rule_inventory.head(80), ["rule_set", "rule_id", "candidate_id", "origin_id", "direction", "variant", "condition_count", "source_row_count"]),
        "",
        "## Required field inventory",
        markdown_table(field_inventory, ["field", "in_required_fields", "used_in_conditions", "condition_count"]),
        "",
        "## Open blockers",
        markdown_table(blockers, ["blocker_id", "component", "severity", "blocked_item", "required_resolution"]),
        "",
        "## Safety",
        "- final_signal_allowed: false",
        "- step13_allowed: false",
        "- Discord/MT5/AI/live_hook: false",
        "",
    ]
    (output_dir / "GOLD_V2_13C_COREB_FEATURE_SAME_COUNT_PARITY_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"status": summary["status"], "output_dir": str(output_dir), "selected_rule_count": summary["selected_rule_count"], "same_count_source_rule_count": summary["same_count_source_rule_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
