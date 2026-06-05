#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18J = "TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED"
IN18J = "gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_audit_only"
IN18I = "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only"
LEDGER_LABEL = "DRY_RUN_CANDIDATE_IDENTITY_LEDGER_NOT_SOURCE_OF_TRUTH"
REQ_FIELDS = [
    "manifest_row_id",
    "component",
    "source_identity_type",
    "source_role",
    "source_row_number_1based",
    "source_key",
    "source_row_hash",
    "strategy_id",
    "source_status",
]
AUX_ALIASES = {
    "entry_time": ["entry_time", "signal_time", "time", "timestamp", "open_time", "entry_open_time"],
    "direction": ["direction", "side", "trade_direction"],
    "tp": ["tp", "TP", "take_profit", "take_profit_price", "tp_price"],
    "sl": ["sl", "SL", "stop_loss", "stop_loss_price", "sl_price"],
    "outcome": ["outcome", "result", "final_status", "source_status"],
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path)
    lp(path).write_text(text, encoding="utf-8")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    wtxt(path, json.dumps(obj, ensure_ascii=False, indent=2))


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv read failed: {path}: {last}")


def cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def rel_under_fx(relative_path: str) -> Path:
    parts = [p for p in cell(relative_path).replace("\\", "/").split("/") if p]
    return fx().joinpath(*parts)


def split_cols(value: Any) -> list[str]:
    text = cell(value)
    if not text:
        return []
    return [c.strip() for c in text.replace(",", ";").split(";") if c.strip()]


def cmap(columns: list[str]) -> dict[str, str]:
    return {c.lower(): c for c in columns}


def resolve(candidates: list[str], columns: list[str]) -> tuple[list[str], list[str]]:
    m = cmap(columns)
    present, missing = [], []
    for cand in candidates:
        actual = m.get(cand.lower())
        if actual is None:
            missing.append(cand)
        else:
            present.append(actual)
    return present, missing


def pick_aux(row: pd.Series, aliases: list[str], columns: list[str]) -> str:
    m = cmap(columns)
    for alias in aliases:
        actual = m.get(alias.lower())
        if actual is not None:
            val = cell(row.get(actual, ""))
            if val:
                return val
    return ""


def pairs(row: pd.Series, cols: list[str]) -> list[tuple[str, str]]:
    return [(c, cell(row.get(c, ""))) for c in cols]


def render_pairs(items: list[tuple[str, str]]) -> str:
    return ";".join(f"{k}={v}" for k, v in items)


def dry_hash(relative_path: str, row_number: int, field: str, items: list[tuple[str, str]]) -> str:
    payload = {
        "scope": "dry_run_candidate_identity_only_not_final_source_identity",
        "relative_path": relative_path,
        "row_number_1based": row_number,
        "field": field,
        "candidate_pairs": items,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "dryrun_sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > limit:
        out.append(f"\n_Showing first {limit} of {len(df)} rows._")
    return "\n".join(out)


def build_safety(source_rows_read: bool, row_hash_computed: bool, success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"],
        ["dry_run_candidate_identity_ledger_only", True, True, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_rows_read", bool(source_rows_read), bool(source_rows_read), "PASS"],
        ["row_hash_computed", bool(row_hash_computed), bool(row_hash_computed), "PASS"],
        ["row_hash_scope_is_dry_run_candidate_only", bool(row_hash_computed), bool(row_hash_computed), "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_18l_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def build_next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18L", "TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY", "Validate that 18K dry-run outputs load and remain audit-only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18K; candidate ledger is not source-of-truth.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18K.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18k_success"])


def build_blockers() -> pd.DataFrame:
    return pd.DataFrame([
        ["18K-B001", "source identity finalization remains blocked", "SOURCE_IDENTITY_FINALIZED_FALSE_REQUIRED"],
        ["18K-B002", "source recovery execution remains blocked", "SOURCE_RECOVERY_EXECUTED_FALSE_REQUIRED"],
        ["18K-B003", "source identity recovered flag remains blocked", "SOURCE_IDENTITY_RECOVERED_FALSE_REQUIRED"],
        ["18K-B004", "OHLC replay/reconstruction remains blocked", "OHLC_REPLAY_ALLOWED_FALSE_REQUIRED"],
        ["18K-B005", "live/final evaluator/signal remains blocked", "LIVE_FINAL_FALSE_REQUIRED"],
        ["18K-B006", "Discord/MT5/AI API/live hook remain blocked", "EXTERNAL_ACTIONS_FALSE_REQUIRED"],
        ["18K-B007", "NO_SIGNAL Discord notification remains blocked", "NO_SIGNAL_DISCORD_FALSE_REQUIRED"],
    ], columns=["blocker_id", "blocker", "required_condition"])


def summary_base(now: str, status: str, ok: bool, source_rows_read: bool, row_hash_computed: bool) -> dict[str, Any]:
    return {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "dry_run_implemented": bool(ok),
        "dry_run_executed": bool(ok and source_rows_read),
        "source_rows_read": bool(source_rows_read),
        "row_hash_computed": bool(row_hash_computed),
        "row_hash_scope": "dry_run_candidate_identity_only_not_final_source_identity" if row_hash_computed else "not_computed",
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "live_or_final_implementation_allowed": False,
        "implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "no_signal_discord_notified": False,
        "ledger_name": LEDGER_LABEL,
        "ledger_is_source_of_truth": False,
    }


def write_stop(out: Path, now: str, status: str, audit: pd.DataFrame, checks: pd.DataFrame | None = None) -> None:
    checks = checks if checks is not None else pd.DataFrame(columns=["check_id", "check", "observed", "expected", "status"])
    ledger = pd.DataFrame(columns=[
        "ledger_label", "artifact_role", "relative_path", "source_filename", "source_row_index0", *REQ_FIELDS,
        "entry_time", "direction", "tp", "sl", "outcome", "dry_run_status",
        "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    ])
    row_counts = pd.DataFrame(columns=["relative_path", "selection_role", "expected_row_count", "actual_row_count", "row_count_match", "source_rows_read"])
    deriv = pd.DataFrame(columns=["relative_path", "selection_role", "field", "action", "candidate_columns", "present_columns", "missing_columns", "derivation_status"])
    validation = pd.DataFrame([["18K-V000", "stopped before dry-run candidate ledger creation", status, "PASS_STATUS", "STOP"]], columns=["validation_id", "validation", "observed", "expected", "status"])
    safety = build_safety(False, False, False)
    for name, df in [
        ("gold_v2_18k_implementation_checks.csv", checks),
        ("gold_v2_18k_dry_run_candidate_identity_rows.csv", ledger),
        ("gold_v2_18k_artifact_row_counts.csv", row_counts),
        ("gold_v2_18k_dry_run_field_derivation_audit.csv", deriv),
        ("gold_v2_18k_dry_run_validation_checks.csv", validation),
        ("gold_v2_18k_required_next_gates.csv", build_next_gates(False)),
        ("gold_v2_18k_blockers.csv", build_blockers()),
        ("gold_v2_18k_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = summary_base(now, status, False, False, False)
    summary.update({"candidate_identity_rows": 0, "validation_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_18K_INPUTS"})
    wjson(out / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json", summary)
    report = [
        "# GOLD V2 18K TIER2 source identity dry-run implementation audit-only report", "",
        f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision",
        "- 18K stopped before creating the dry-run candidate identity ledger.",
        "- Source recovery, source identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord notification remained disabled.",
        "", "## Input audit", mdtable(audit), "", "## Implementation checks", mdtable(checks), "", "## Validation checks", mdtable(validation), "", "## Safety", mdtable(safety),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def derive_field(field: str, action: str, present: list[str], src: pd.Series, rel: str, row_number: int) -> tuple[str, bool]:
    ps = pairs(src, present)
    if field == "component":
        direct_value = cell(src.get(present[0], "")) if action.startswith("COPY_DIRECT") and present else ""
        return direct_value or "TIER2_MEDIUM", False
    if field == "source_row_number_1based":
        return str(row_number), False
    if field == "source_row_hash":
        return dry_hash(rel, row_number, field, ps), True
    if action.startswith("COPY_DIRECT"):
        return (cell(src.get(present[0], "")) if present else ""), False
    if action.startswith("DERIVE"):
        return render_pairs(ps), False
    return "", False


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    base18j, base18i = fx() / IN18J, fx() / IN18I
    inputs = {
        "summary_18j": base18j / "gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json",
        "checks_18j": base18j / "gold_v2_18j_plan_checks.csv",
        "planned_artifacts_18j": base18j / "gold_v2_18j_planned_artifacts.csv",
        "planned_processing_steps_18j": base18j / "gold_v2_18j_planned_processing_steps.csv",
        "planned_output_contract_18j": base18j / "gold_v2_18j_planned_output_contract.csv",
        "planned_stop_conditions_18j": base18j / "gold_v2_18j_planned_stop_conditions.csv",
        "next_gates_18j": base18j / "gold_v2_18j_required_next_gates.csv",
        "blockers_18j": base18j / "gold_v2_18j_blockers.csv",
        "safety_18j": base18j / "gold_v2_18j_safety_matrix.csv",
        "recipe_18i": base18i / "gold_v2_18i_dry_run_field_recipe.csv",
    }
    audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(audit, out / "gold_v2_18k_input_audit.csv")
    if not audit["exists"].all():
        write_stop(out, now, "18K_STOP_MISSING_INPUTS", audit)
        return 2

    s18j = rjson(inputs["summary_18j"])
    checks18j = rcsv(inputs["checks_18j"])
    planned_artifacts = rcsv(inputs["planned_artifacts_18j"])
    planned_steps = rcsv(inputs["planned_processing_steps_18j"])
    planned_contract = rcsv(inputs["planned_output_contract_18j"])
    safety18j = rcsv(inputs["safety_18j"])
    recipe = rcsv(inputs["recipe_18i"])

    stop_checks_18j = int((checks18j["status"].astype(str) == "STOP").sum()) if "status" in checks18j.columns else 999
    stop_safety_18j = int((safety18j["status"].astype(str) == "STOP").sum()) if "status" in safety18j.columns else 999
    plan_reads = int((planned_steps["reads_source_rows"].map(truthy)).sum()) if "reads_source_rows" in planned_steps.columns else 0
    empty_candidates = int(((recipe["future_dry_run_action"].astype(str).str.contains("DERIVE", na=False)) & (recipe["candidate_columns"].astype(str).str.strip().eq(""))).sum()) if {"future_dry_run_action", "candidate_columns"}.issubset(recipe.columns) else 999
    contract_fields = set(planned_contract["field"].astype(str)) if "field" in planned_contract.columns else set()
    missing_contract = [f for f in REQ_FIELDS if f not in contract_fields]
    selected_count = int(len(planned_artifacts))
    role_series = planned_artifacts.get("future_dry_run_input_role", planned_artifacts.get("selection_role", pd.Series(dtype=str)))
    primary_count = int((role_series.astype(str) == "PRIMARY").sum()) if selected_count else 0
    external_any = bool(any(bool(v) for v in s18j.get("external_actions", {}).values()))
    live_final_any = bool(s18j.get("live_enabled", False) or s18j.get("final_signal_allowed", False) or s18j.get("no_signal_discord_notified", False) or external_any)
    checks = pd.DataFrame([
        ["18K-C001", "18J status", s18j.get("status"), EXPECTED_18J, "PASS" if s18j.get("status") == EXPECTED_18J else "STOP"],
        ["18K-C002", "18J checks STOP rows", stop_checks_18j, 0, "PASS" if stop_checks_18j == 0 else "STOP"],
        ["18K-C003", "18J safety STOP rows", stop_safety_18j, 0, "PASS" if stop_safety_18j == 0 else "STOP"],
        ["18K-C004", "18J dry-run implemented before 18K", bool(s18j.get("dry_run_implemented", False)), False, "PASS" if not bool(s18j.get("dry_run_implemented", False)) else "STOP"],
        ["18K-C005", "18J source rows read before 18K", bool(s18j.get("source_rows_read", False)), False, "PASS" if not bool(s18j.get("source_rows_read", False)) else "STOP"],
        ["18K-C006", "18J source recovery executed", bool(s18j.get("source_recovery_executed", False)), False, "PASS" if not bool(s18j.get("source_recovery_executed", False)) else "STOP"],
        ["18K-C007", "18J live/final/external actions disabled", live_final_any, False, "PASS" if not live_final_any else "STOP"],
        ["18K-C008", "18J planned source-row reads", plan_reads, 0, "PASS" if plan_reads == 0 else "STOP"],
        ["18K-C009", "18I derived recipe rows with empty candidate columns", empty_candidates, 0, "PASS" if empty_candidates == 0 else "STOP"],
        ["18K-C010", "18J planned output contract missing required fields", ";".join(missing_contract), "", "PASS" if not missing_contract else "STOP"],
        ["18K-C011", "18J planned artifacts", selected_count, ">=1", "PASS" if selected_count >= 1 else "STOP"],
        ["18K-C012", "18J PRIMARY artifact count", primary_count, 1, "PASS" if primary_count == 1 else "STOP"],
    ], columns=["check_id", "check", "observed", "expected", "status"])
    wcsv(checks, out / "gold_v2_18k_implementation_checks.csv")
    if int((checks["status"].astype(str) == "STOP").sum()) > 0:
        write_stop(out, now, "18K_STOP_UPSTREAM_PLAN_NOT_SAFE", audit, checks)
        return 2

    artifact_rows: list[dict[str, Any]] = []
    deriv_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    source_rows_read = False
    any_hash = False

    for _, art in planned_artifacts.iterrows():
        rel = cell(art.get("relative_path", ""))
        role = cell(art.get("future_dry_run_input_role", art.get("selection_role", "")))
        filename = cell(art.get("filename", Path(rel).name))
        try:
            expected_rows = int(float(cell(art.get("row_count", ""))))
        except ValueError:
            expected_rows = -1
        path = rel_under_fx(rel)
        if not lp(path).exists():
            artifact_rows.append({"relative_path": rel, "selection_role": role, "expected_row_count": expected_rows, "actual_row_count": -1, "row_count_match": False, "source_rows_read": False, "path": str(path)})
            continue
        df = rcsv(path)
        source_rows_read = True
        cols = list(df.columns)
        artifact_rows.append({"relative_path": rel, "selection_role": role, "expected_row_count": expected_rows, "actual_row_count": int(len(df)), "row_count_match": expected_rows == int(len(df)), "source_rows_read": True, "path": str(path)})
        sub_recipe = recipe[recipe["relative_path"].astype(str).eq(rel)].copy() if "relative_path" in recipe.columns else pd.DataFrame()
        field_defs: dict[str, tuple[str, list[str]]] = {}
        for field in REQ_FIELDS:
            rf = sub_recipe[sub_recipe["field"].astype(str).eq(field)] if not sub_recipe.empty and "field" in sub_recipe.columns else pd.DataFrame()
            if rf.empty:
                deriv_rows.append({"relative_path": rel, "selection_role": role, "field": field, "action": "MISSING_RECIPE", "candidate_columns": "", "present_columns": "", "missing_columns": "", "derivation_status": "STOP_MISSING_RECIPE_FIELD", "source_row_count": int(len(df)), "non_empty_output_values": 0})
                continue
            rr = rf.iloc[0]
            action = cell(rr.get("future_dry_run_action", ""))
            candidates = split_cols(rr.get("candidate_columns", ""))
            present, missing = resolve(candidates, cols)
            if action.startswith("COPY_DIRECT") and not present:
                status = "STOP_DIRECT_COLUMN_MISSING"
            elif action.startswith("DERIVE") and candidates and not present:
                status = "STOP_ALL_CANDIDATE_COLUMNS_MISSING"
            else:
                status = "PASS"
                field_defs[field] = (action, present)
            deriv_rows.append({"relative_path": rel, "selection_role": role, "field": field, "action": action, "candidate_columns": ";".join(candidates), "present_columns": ";".join(present), "missing_columns": ";".join(missing), "derivation_status": status, "source_row_count": int(len(df)), "non_empty_output_values": "computed_after_row_derivation"})
        for row_index0, src in df.iterrows():
            row_number = int(row_index0) + 1
            derived: dict[str, str] = {}
            for field in REQ_FIELDS:
                action, present = field_defs.get(field, ("", []))
                value, hash_flag = derive_field(field, action, present, src, rel, row_number)
                derived[field] = value
                any_hash = any_hash or hash_flag
            ledger_rows.append({
                "ledger_label": LEDGER_LABEL,
                "artifact_role": role,
                "relative_path": rel,
                "source_filename": filename,
                "source_row_index0": int(row_index0),
                "source_row_number_1based": derived.get("source_row_number_1based", str(row_number)),
                "manifest_row_id": derived.get("manifest_row_id", ""),
                "component": derived.get("component", ""),
                "source_identity_type": derived.get("source_identity_type", ""),
                "source_role": derived.get("source_role", ""),
                "source_key": derived.get("source_key", ""),
                "source_row_hash": derived.get("source_row_hash", ""),
                "source_row_hash_scope": "DRY_RUN_CANDIDATE_ONLY_NOT_FINAL_SOURCE_IDENTITY",
                "strategy_id": derived.get("strategy_id", ""),
                "source_status": derived.get("source_status", ""),
                "entry_time": pick_aux(src, AUX_ALIASES["entry_time"], cols),
                "direction": pick_aux(src, AUX_ALIASES["direction"], cols),
                "tp": pick_aux(src, AUX_ALIASES["tp"], cols),
                "sl": pick_aux(src, AUX_ALIASES["sl"], cols),
                "outcome": pick_aux(src, AUX_ALIASES["outcome"], cols),
                "dry_run_status": "DRY_RUN_CANDIDATE_ONLY_NOT_SOURCE_OF_TRUTH",
                "source_recovery_executed": False,
                "source_identity_finalized": False,
                "source_identity_recovered": False,
                "live_or_final_implementation_allowed": False,
                "oh_lc_replay_allowed": False,
                "discord_send_allowed": False,
                "mt5_order_allowed": False,
                "ai_api_allowed": False,
                "live_hook_allowed": False,
                "no_signal_discord_notified": False,
            })

    row_counts = pd.DataFrame(artifact_rows)
    deriv = pd.DataFrame(deriv_rows)
    ledger = pd.DataFrame(ledger_rows)
    if not deriv.empty and not ledger.empty:
        counts = ledger.groupby("relative_path", dropna=False).agg(**{f: (f, lambda s: int(s.astype(str).str.strip().ne("").sum())) for f in REQ_FIELDS if f in ledger.columns}).reset_index()
        for i, drow in deriv.iterrows():
            rel = str(drow["relative_path"])
            field = str(drow["field"])
            sub = counts[counts["relative_path"].astype(str).eq(rel)]
            if not sub.empty and field in sub.columns:
                deriv.at[i, "non_empty_output_values"] = int(sub.iloc[0][field])

    expected_total = int(row_counts["expected_row_count"].sum()) if not row_counts.empty else 0
    actual_total = int(row_counts["actual_row_count"].clip(lower=0).sum()) if not row_counts.empty else 0
    missing_artifacts = int((row_counts["source_rows_read"].astype(str) != "True").sum()) if not row_counts.empty else selected_count
    row_mismatches = int((row_counts["row_count_match"].astype(str) != "True").sum()) if not row_counts.empty else selected_count
    deriv_stops = int((deriv["derivation_status"].astype(str).str.startswith("STOP")).sum()) if not deriv.empty else len(REQ_FIELDS) * selected_count
    ledger_len = int(len(ledger))
    false_recovery = int((ledger["source_recovery_executed"].astype(str) == "False").sum()) if ledger_len else 0
    false_finalized = int((ledger["source_identity_finalized"].astype(str) == "False").sum()) if ledger_len else 0
    false_recovered = int((ledger["source_identity_recovered"].astype(str) == "False").sum()) if ledger_len else 0
    label_ok = int((ledger["ledger_label"].astype(str) == LEDGER_LABEL).sum()) if ledger_len else 0
    missing_req = [c for c in REQ_FIELDS if c not in ledger.columns]
    validation = pd.DataFrame([
        ["18K-V001", "source artifacts missing", missing_artifacts, 0, "PASS" if missing_artifacts == 0 else "STOP"],
        ["18K-V002", "source artifact row-count mismatches vs 18J plan", row_mismatches, 0, "PASS" if row_mismatches == 0 else "STOP"],
        ["18K-V003", "ledger rows equal actual source rows read", ledger_len, actual_total, "PASS" if ledger_len == actual_total and actual_total > 0 else "STOP"],
        ["18K-V004", "field derivation STOP rows", deriv_stops, 0, "PASS" if deriv_stops == 0 else "STOP"],
        ["18K-V005", "source_recovery_executed false for every ledger row", false_recovery, ledger_len, "PASS" if false_recovery == ledger_len and ledger_len > 0 else "STOP"],
        ["18K-V006", "source_identity_finalized false for every ledger row", false_finalized, ledger_len, "PASS" if false_finalized == ledger_len and ledger_len > 0 else "STOP"],
        ["18K-V007", "source_identity_recovered false for every ledger row", false_recovered, ledger_len, "PASS" if false_recovered == ledger_len and ledger_len > 0 else "STOP"],
        ["18K-V008", "ledger label marks candidate dry-run and not source-of-truth", label_ok, ledger_len, "PASS" if label_ok == ledger_len and ledger_len > 0 else "STOP"],
        ["18K-V009", "required candidate identity columns present", ";".join([c for c in REQ_FIELDS if c in ledger.columns]), ";".join(REQ_FIELDS), "PASS" if not missing_req else "STOP"],
        ["18K-V010", "AI API calls", False, False, "PASS"],
        ["18K-V011", "Discord/MT5/live hook calls", False, False, "PASS"],
        ["18K-V012", "NO_SIGNAL Discord notification", False, False, "PASS"],
        ["18K-V013", "OHLC replay/reconstruction", False, False, "PASS"],
    ], columns=["validation_id", "validation", "observed", "expected", "status"])
    success = int((checks["status"].astype(str) == "STOP").sum()) + int((validation["status"].astype(str) == "STOP").sum()) == 0
    status = SUCCESS if success else "18K_STOP_REVIEW_DRY_RUN_OUTPUTS"
    safety = build_safety(source_rows_read, any_hash, success)
    for name, df_out in [
        ("gold_v2_18k_implementation_checks.csv", checks),
        ("gold_v2_18k_dry_run_candidate_identity_rows.csv", ledger),
        ("gold_v2_18k_artifact_row_counts.csv", row_counts),
        ("gold_v2_18k_dry_run_field_derivation_audit.csv", deriv),
        ("gold_v2_18k_dry_run_validation_checks.csv", validation),
        ("gold_v2_18k_required_next_gates.csv", build_next_gates(success)),
        ("gold_v2_18k_blockers.csv", build_blockers()),
        ("gold_v2_18k_safety_matrix.csv", safety),
    ]:
        wcsv(df_out, out / name)
    summary = summary_base(now, status, success, source_rows_read, any_hash)
    summary.update({
        "source_artifacts_planned": selected_count,
        "source_artifacts_read": int((row_counts["source_rows_read"].astype(str) == "True").sum()) if not row_counts.empty else 0,
        "expected_source_rows_from_18j_plan": expected_total,
        "actual_source_rows_read": actual_total,
        "candidate_identity_rows": ledger_len,
        "field_derivation_audit_rows": int(len(deriv)),
        "implementation_checks_stop_rows": int((checks["status"].astype(str) == "STOP").sum()),
        "validation_stop_rows": int((validation["status"].astype(str) == "STOP").sum()),
        "next_recommended_step": "18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_18K_OUTPUTS",
    })
    wjson(out / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json", summary)
    report = [
        "# GOLD V2 18K TIER2 source identity dry-run implementation audit-only report", "",
        f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision",
        "- 18K creates a dry-run candidate identity ledger only when every check passes.",
        "- The ledger is not source-of-truth and must not be used for final MEDIUM signals or live parity claims.",
        "- source_recovery_executed, source_identity_finalized, and source_identity_recovered remain false.",
        "- OHLC replay/reconstruction, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord notification remain disabled.",
        "", "## Input audit", mdtable(audit), "", "## Implementation checks", mdtable(checks), "", "## Artifact row counts", mdtable(row_counts),
        "", "## Field derivation audit", mdtable(deriv), "", "## Validation checks", mdtable(validation), "", "## Candidate identity ledger preview", mdtable(ledger, limit=20),
        "", "## Next gates", mdtable(build_next_gates(success)), "", "## Blockers", mdtable(build_blockers()), "", "## Safety", mdtable(safety),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
