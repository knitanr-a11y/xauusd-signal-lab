#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17D_VOL_TRMEAN32_REFINED_RECONCILIATION_AUDIT_ONLY"
COMPONENT = "VOL_TRMEAN32_REFINED"
OUT_DIR_NAME = "gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only"
REPORT_NAME = "GOLD_V2_17D_VOL_TRMEAN32_REFINED_RECONCILIATION_AUDIT_ONLY_REPORT.md"
EXPECTED_RULE_ROWS = 36
EXPECTED_COMBINED_ROWS = 104
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "rule_ledger": ("gold_v2_coreb_refined_probe_outputs", "coreb_refined_rule_ledgers.csv"),
    "combined_ledger": ("gold_v2_coreb_refined_probe_outputs", "coreb_refined_combined_ledgers.csv"),
    "matrix_17a": ("gold_v2_17a_medium_full_set_source_arbitration_audit_only", "gold_v2_17a_medium_arbitration_matrix.csv"),
    "matrix_17b": ("gold_v2_17b_medium_non_tier2_component_replay_planning_audit_only", "gold_v2_17b_replay_planning_matrix.csv"),
}
DATASET_MAP = {"2025_fold4": "2025", "2026_WF": "2026"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def input_path(role: str) -> Path:
    folder, name = INPUTS[role]
    return fx_outputs() / folder / name


def output_dir() -> Path:
    path = fx_outputs() / OUT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)):
            return None
        if math.isinf(float(value)):
            return "inf" if float(value) > 0 else "-inf"
        return float(value)
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_num(series: Any) -> pd.Series:
    return pd.to_numeric(series if isinstance(series, pd.Series) else pd.Series(series), errors="coerce")


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def component_col(df: pd.DataFrame) -> str | None:
    return first_col(df, ["component", "rule_component", "medium_component", "source_component", "refined_rule"])


def row_hash(row: pd.Series) -> str:
    payload = json.dumps(clean(row.to_dict()), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def markdown_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit() -> pd.DataFrame:
    rows = []
    for role in INPUTS:
        path = input_path(role)
        row: dict[str, Any] = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            df = read_csv(path)
            row["rows"] = len(df)
            row["columns"] = len(df.columns)
            row["column_names"] = "|".join(map(str, df.columns))
        rows.append(row)
    return pd.DataFrame(rows)


def standardize(df: pd.DataFrame, role: str, comp_col: str) -> pd.DataFrame:
    out = df.copy()
    out["source_role"] = role
    out["source_row_number_1based"] = np.arange(1, len(out) + 1)
    out["component_col_used"] = comp_col
    if comp_col != "component":
        out["component"] = out[comp_col]
    dataset_col = first_col(out, ["dataset_final", "dataset", "year", "source_dataset"])
    entry_col = first_col(out, ["entry_time", "top_entry_time", "signal_time", "time", "m15_time"])
    direction_col = first_col(out, ["direction", "top_direction", "side", "trade_direction"])
    profit_col = first_col(out, ["profit_r", "selected_profit_r", "profit", "r", "pnl_r"])
    out["dataset_final_std"] = out[dataset_col].map(DATASET_MAP).fillna(out[dataset_col].astype(str)) if dataset_col else ""
    out["entry_time_std"] = out[entry_col] if entry_col else ""
    out["entry_time_dt"] = pd.to_datetime(out["entry_time_std"], errors="coerce")
    out["direction_std"] = out[direction_col].astype(str) if direction_col else ""
    out["profit_r_std"] = to_num(out[profit_col]) if profit_col else np.nan
    out["outcome"] = np.select([to_num(out["profit_r_std"]) > 0, to_num(out["profit_r_std"]) < 0, to_num(out["profit_r_std"]).eq(0)], ["WIN", "LOSS", "BREAKEVEN"], default="UNKNOWN")
    out["strategy_id"] = COMPONENT
    out["key_available"] = bool(dataset_col and entry_col and direction_col)
    out["key_columns_used"] = json.dumps({"dataset": dataset_col, "entry_time": entry_col, "direction": direction_col, "profit_r": profit_col}, ensure_ascii=False)
    if bool(dataset_col and entry_col and direction_col):
        out["source_key"] = out["dataset_final_std"].astype(str) + "|" + out["entry_time_dt"].astype("int64").astype(str) + "|" + out["direction_std"].astype(str)
    else:
        out["source_key"] = ""
    out["source_row_hash"] = out.apply(row_hash, axis=1)
    return out


def extract_component(df: pd.DataFrame, role: str, expected_rows: int) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    comp_col = component_col(df)
    if comp_col is None:
        check = pd.DataFrame([{"source_role": role, "condition": "component column exists", "observed_rows": 0, "expected_rows": expected_rows, "status": "STOP", "component_col": ""}])
        return pd.DataFrame(), check, ""
    mask = df[comp_col].astype(str).eq(COMPONENT)
    observed = int(mask.sum())
    checks = pd.DataFrame([
        {"source_role": role, "condition": f"{comp_col} == {COMPONENT}", "observed_rows": observed, "expected_rows": expected_rows, "status": "PASS" if observed == expected_rows else "STOP", "component_col": comp_col},
        {"source_role": role, "condition": "other component rows excluded", "observed_rows": int((~mask).sum()), "expected_rows": "not constrained", "status": "INFO", "component_col": comp_col},
    ])
    return standardize(df[mask].copy(), role, comp_col), checks, comp_col


def matrix_checks(matrix_17a: pd.DataFrame, matrix_17b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    a = matrix_17a[matrix_17a["component"].astype(str).eq(COMPONENT)] if "component" in matrix_17a.columns else pd.DataFrame()
    b = matrix_17b[matrix_17b["component"].astype(str).eq(COMPONENT)] if "component" in matrix_17b.columns else pd.DataFrame()
    if a.empty:
        rows.append(["17D-17A-000", "17A component row exists", "missing", COMPONENT, "STOP"])
    else:
        row = a.iloc[0]
        expected = [("rule_ledger_rows", EXPECTED_RULE_ROWS), ("combined_ledger_rows", EXPECTED_COMBINED_ROWS), ("arbitration_status", "NEEDS_REPLAY_PARITY"), ("live_evaluator_allowed", False), ("final_signal_allowed", False)]
        for key, exp in expected:
            obs = bool_value(row.get(key, False)) if isinstance(exp, bool) else row.get(key, "")
            if isinstance(exp, int):
                obs = int(obs)
            rows.append([f"17D-17A-{key}", f"17A {key}", obs, exp, "PASS" if obs == exp else "STOP"])
    if b.empty:
        rows.append(["17D-17B-000", "17B component row exists", "missing", COMPONENT, "STOP"])
    else:
        row = b.iloc[0]
        expected = [("planned_step", "17D"), ("planning_status", "PLAN_READY"), ("rule_ledger_rows", EXPECTED_RULE_ROWS), ("combined_ledger_rows", EXPECTED_COMBINED_ROWS), ("live_evaluator_allowed", False), ("final_signal_allowed", False)]
        for key, exp in expected:
            obs = bool_value(row.get(key, False)) if isinstance(exp, bool) else row.get(key, "")
            if isinstance(exp, int):
                obs = int(obs)
            rows.append([f"17D-17B-{key}", f"17B {key}", obs, exp, "PASS" if obs == exp else "STOP"])
    return pd.DataFrame(rows, columns=["check_id", "check", "observed", "expected", "status"])


def key_reconciliation(rule_rows: pd.DataFrame, combined_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if rule_rows.empty or combined_rows.empty or not bool(rule_rows["key_available"].iloc[0]) or not bool(combined_rows["key_available"].iloc[0]):
        summary = pd.DataFrame([["shared_key_reconciliation_available", False, True, "STOP", "dataset/entry_time/direction columns are required"]], columns=["metric", "observed", "expected", "status", "note"])
        return summary, pd.DataFrame(), pd.DataFrame()
    rule_keys = set(rule_rows["source_key"].astype(str))
    combined_keys = set(combined_rows["source_key"].astype(str))
    missing = sorted(rule_keys - combined_keys)
    extra = sorted(combined_keys - rule_keys)
    summary = pd.DataFrame([
        ["rule_unique_keys", len(rule_keys), "<=36", "INFO", "duplicates audited"],
        ["combined_unique_keys", len(combined_keys), "<=104", "INFO", "combined extras allowed"],
        ["rule_keys_missing_in_combined", len(missing), 0, "PASS" if not missing else "STOP", "all rule keys must exist in combined"],
        ["combined_extra_keys_not_in_rule", len(extra), "allowed/audited", "INFO", "104-row source extras"],
    ], columns=["metric", "observed", "expected", "status", "note"])
    return summary, rule_rows[rule_rows["source_key"].astype(str).isin(missing)].copy(), combined_rows[combined_rows["source_key"].astype(str).isin(extra)].copy()


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17d_input_audit.csv")
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    if len(missing):
        status = "VOL_TRMEAN32_REFINED_RECONCILIATION_MISSING_INPUTS_AUDIT_ONLY"
        blockers = pd.DataFrame([["17D-BINPUT", COMPONENT, "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))], ["17D-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."]], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
        write_csv(blockers, out / "gold_v2_17d_vol_trmean32_blockers.csv")
        write_json(out / "gold_v2_17d_vol_trmean32_reconciliation_summary.json", {"created_utc": now, "step": STEP, "component": COMPONENT, "status": status, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
        (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17D VOL_TRMEAN32_REFINED reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
        print(json.dumps(clean({"status": status, "output_dir": str(out)}), ensure_ascii=False, indent=2))
        return 2
    rule_rows, rule_checks, rule_component_col = extract_component(read_csv(input_path("rule_ledger")), "rule_ledger", EXPECTED_RULE_ROWS)
    combined_rows, combined_checks, combined_component_col = extract_component(read_csv(input_path("combined_ledger")), "combined_ledger", EXPECTED_COMBINED_ROWS)
    source_checks = pd.concat([rule_checks, combined_checks], ignore_index=True)
    matrix = matrix_checks(read_csv(input_path("matrix_17a")), read_csv(input_path("matrix_17b")))
    key_summary, missing_keys, extra_keys = key_reconciliation(rule_rows, combined_rows)
    write_csv(rule_rows, out / "gold_v2_17d_vol_trmean32_rule_ledger_source_rows.csv")
    write_csv(combined_rows, out / "gold_v2_17d_vol_trmean32_combined_ledger_source_rows.csv")
    write_csv(source_checks, out / "gold_v2_17d_vol_trmean32_source_extraction_checks.csv")
    write_csv(matrix, out / "gold_v2_17d_17a_17b_consistency_checks.csv")
    write_csv(key_summary, out / "gold_v2_17d_vol_trmean32_key_reconciliation_summary.csv")
    write_csv(missing_keys, out / "gold_v2_17d_vol_trmean32_rule_keys_missing_in_combined.csv")
    write_csv(extra_keys, out / "gold_v2_17d_vol_trmean32_combined_extra_keys_not_in_rule.csv")
    safety = pd.DataFrame([["audit_only", True, True, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"]], columns=["safety_item", "observed", "expected", "status"])
    write_csv(safety, out / "gold_v2_17d_safety_matrix.csv")
    ok = source_checks[source_checks["status"].eq("STOP")].empty and matrix[matrix["status"].eq("STOP")].empty and key_summary[key_summary["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = "VOL_TRMEAN32_REFINED_SOURCE_RECONCILIATION_READY_FOR_CANDIDATE_SOURCE_FREEZE_AUDIT_ONLY" if ok else "VOL_TRMEAN32_REFINED_SOURCE_RECONCILIATION_STOPPED_AUDIT_ONLY"
    candidate_status = "SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE" if ok else "NOT_APPROVED_SOURCE_RECONCILIATION_FAILED"
    next_step = "17E_MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_AUDIT_ONLY" if ok else "STOP_REVIEW_17D_SOURCE_RECONCILIATION_OUTPUTS"
    decision = pd.DataFrame([["17D-C001", "rule ledger rows", len(rule_rows), EXPECTED_RULE_ROWS, "PASS" if len(rule_rows) == EXPECTED_RULE_ROWS else "STOP"], ["17D-C002", "combined ledger rows", len(combined_rows), EXPECTED_COMBINED_ROWS, "PASS" if len(combined_rows) == EXPECTED_COMBINED_ROWS else "STOP"], ["17D-C003", "17A/17B consistency", matrix[matrix["status"].eq("STOP")].empty, True, "PASS" if matrix[matrix["status"].eq("STOP")].empty else "STOP"], ["17D-C004", "rule keys present in combined", key_summary[key_summary["status"].eq("STOP")].empty, True, "PASS" if key_summary[key_summary["status"].eq("STOP")].empty else "STOP"], ["17D-C005", "candidate source freeze preview", candidate_status, "audit-only preview, not live", "PASS" if ok else "STOP"]], columns=["check_id", "check", "observed", "expected", "status"])
    write_csv(decision, out / "gold_v2_17d_vol_trmean32_decision_matrix.csv")
    freeze = {"created_utc": now, "step": STEP, "component": COMPONENT, "audit_only": True, "candidate_freeze_type": "SOURCE_ROW_IDENTITY_FREEZE_PREVIEW_ONLY", "candidate_status": candidate_status, "expected_counts": {"rule_ledger_rows": EXPECTED_RULE_ROWS, "combined_ledger_rows": EXPECTED_COMBINED_ROWS}, "observed_counts": {"rule_ledger_rows": len(rule_rows), "combined_ledger_rows": len(combined_rows)}, "component_filter": {"rule_component_col": rule_component_col, "combined_component_col": combined_component_col, "equals": COMPONENT}, "rule_source_row_hashes": rule_rows["source_row_hash"].astype(str).tolist() if "source_row_hash" in rule_rows.columns else [], "combined_source_row_hashes": combined_rows["source_row_hash"].astype(str).tolist() if "source_row_hash" in combined_rows.columns else [], "hard_warnings": ["Not executable live rule", "No OHLC rediscovery", "No approximate VOL_TRMEAN32_REFINED condition", "Feature/asof parity not proven", "External actions disabled"], "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS}
    write_json(out / "gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json", freeze)
    index_cols = ["source_role", "source_row_number_1based", "source_key", "strategy_id", "source_row_hash"]
    write_csv(pd.concat([rule_rows[[c for c in index_cols if c in rule_rows.columns]], combined_rows[[c for c in index_cols if c in combined_rows.columns]]], ignore_index=True), out / "gold_v2_17d_vol_trmean32_candidate_source_freeze_index.csv")
    blocks = []
    for _, row in source_checks[source_checks["status"].eq("STOP")].iterrows():
        blocks.append(["17D-B001", COMPONENT, "HARD", "OPEN", "source row extraction", f"{row['source_role']} observed={row['observed_rows']} expected={row['expected_rows']}"])
    for _, row in matrix[matrix["status"].eq("STOP")].iterrows():
        blocks.append(["17D-B17AB", COMPONENT, "HARD", "OPEN", "17A/17B consistency", f"{row['check']}: observed={row['observed']} expected={row['expected']}"])
    for _, row in key_summary[key_summary["status"].eq("STOP")].iterrows():
        blocks.append(["17D-BKEY", COMPONENT, "HARD", "OPEN", "key reconciliation", f"{row['metric']}: observed={row['observed']} expected={row['expected']}"])
    blocks += [["17D-B010", COMPONENT, "HARD", "OPEN", "executable rule freeze", "17D writes source-row freeze preview only; executable rule/load-smoke requires later audit."], ["17D-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "full MEDIUM set", "17C and 17D reconciliation outputs require post-consolidation before any later full-set candidate mapping."], ["17D-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."]]
    blockers = pd.DataFrame(blocks, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17d_vol_trmean32_blockers.csv")
    summary = {"created_utc": now, "step": STEP, "component": COMPONENT, "status": status, "audit_only": True, "source_of_truth": "coreb_refined_rule_ledgers.csv + coreb_refined_combined_ledgers.csv + 17A/17B matrices", "no_ohlc_rediscovery": True, "no_approximate_rule_created": True, "expected_counts": {"rule_ledger_rows": EXPECTED_RULE_ROWS, "combined_ledger_rows": EXPECTED_COMBINED_ROWS}, "observed_counts": {"rule_ledger_rows": len(rule_rows), "combined_ledger_rows": len(combined_rows)}, "source_counts_ok": source_checks[source_checks["status"].eq("STOP")].empty, "seventeen_a_b_consistency_ok": matrix[matrix["status"].eq("STOP")].empty, "rule_keys_missing_in_combined": len(missing_keys), "combined_extra_keys_not_in_rule": len(extra_keys), "key_reconciliation_ok": key_summary[key_summary["status"].eq("STOP")].empty, "candidate_source_freeze_preview_written": True, "candidate_status": candidate_status, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": next_step}
    write_json(out / "gold_v2_17d_vol_trmean32_reconciliation_summary.json", summary)
    report = ["# GOLD V2 17D VOL_TRMEAN32_REFINED reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- Source ledgers and 17A/17B matrices are the source of truth.", "- No OHLC rediscovery or approximate live rule was implemented.", "- Candidate output is source-row freeze preview only, not executable live logic.", f"- Next recommended step: `{next_step}`", "- Discord, MT5, AI API, final signal, and live hook remain disabled. NO_SIGNAL is not notified.", "", "## Input audit", markdown_table(audit), "", "## Source extraction checks", markdown_table(source_checks), "", "## 17A/17B consistency checks", markdown_table(matrix), "", "## Key reconciliation summary", markdown_table(key_summary), "", "## Decision matrix", markdown_table(decision), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": next_step}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
