#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

STEP = "25C42_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY"
STATUS = "COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY"
STOP_MISSING = "25C42_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_ACCEPT = "25C42_STOP_HUMAN_ACCEPTANCE_FLAG_MISSING_AUDIT_ONLY"
STOP_CONTRACT = "25C42_STOP_25C41_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_RECON = "25C42_STOP_RECONCILIATION_MISMATCH_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only"
IN41 = "gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only"
TARGET_NAME = "rr125_top_ledgers.csv"
KEY = ["dataset", "entry_time", "policy"]

EXPECTED_STEP_41 = "25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY"
EXPECTED_STATUS_41 = "COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_EXPORT"
EXPECTED_ACCEPT_NEXT = "HUMAN_ACCEPT_25C41_BEFORE_25C42_RIGHT_ONLY_ROW_LEVEL_EXPORT"
EXPECTED_VARIANTS = {
    "A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8",
    "A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U",
    "A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR",
    "A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def default_fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def lp(p: Path) -> Path:
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_json(p: Path) -> dict:
    return json.loads(lp(p).read_text(encoding="utf-8-sig"))


def read_csv(p: Path) -> pd.DataFrame:
    last: Optional[Exception] = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e:
            last = e
    raise RuntimeError(f"read failed {p}: {last}")


def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(p), index=False, encoding="utf-8-sig")


def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def norm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in KEY:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].astype(str)
    return out


def path_from_audit(df: pd.DataFrame, name: str) -> Path:
    if "normalized_path" in df.columns:
        m = df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
        if not m.empty and "absolute_path" in m.columns:
            return Path(str(m.iloc[0]["absolute_path"]))
    for col in df.columns:
        m = df[df[col].astype(str).str.contains(name, case=False, regex=False, na=False)]
        if not m.empty:
            for c in ["absolute_path", "path", col]:
                if c in df.columns:
                    return Path(str(m.iloc[0][c]))
    return Path("")


def status_from_exists(path: Path) -> str:
    return "PASS" if lp(path).exists() else "STOP"


def contract_rows_from_25c41(s41: dict, next_plan: pd.DataFrame) -> list[dict]:
    checks = [
        ("C001", "25C41 step matches expected", s41.get("step") == EXPECTED_STEP_41, s41.get("step")),
        ("C002", "25C41 status requires acceptance before export", s41.get("status") == EXPECTED_STATUS_41, s41.get("status")),
        ("C003", "25C41 audit_only true", as_bool(s41.get("audit_only", False)) is True, s41.get("audit_only")),
        ("C004", "25C41 plan_only true", as_bool(s41.get("plan_only", False)) is True, s41.get("plan_only")),
        ("C005", "25C41 export contract created", as_bool(s41.get("export_contract_created", False)) is True, s41.get("export_contract_created")),
        ("C006", "25C41 export_executed false", as_bool(s41.get("export_executed", True)) is False, s41.get("export_executed")),
        ("C007", "25C41 dry_run_executed false", as_bool(s41.get("dry_run_executed", True)) is False, s41.get("dry_run_executed")),
        ("C008", "25C41 condition_changed false", as_bool(s41.get("condition_changed", True)) is False, s41.get("condition_changed")),
        ("C009", "25C41 source recovery false", as_bool(s41.get("source_recovery_executed", True)) is False, s41.get("source_recovery_executed")),
        ("C010", "25C41 source mutation false", as_bool(s41.get("source_mutation_executed", True)) is False, s41.get("source_mutation_executed")),
        ("C011", "25C41 CoreB live unblock false", as_bool(s41.get("coreb_live_evaluator_unblocked", True)) is False, s41.get("coreb_live_evaluator_unblocked")),
        ("C012", "25C41 AI API false", as_bool(s41.get("ai_api_called", True)) is False, s41.get("ai_api_called")),
        ("C013", "25C41 requires acceptance before 25C42", as_bool(s41.get("requires_human_acceptance_before_25c42", False)) is True, s41.get("requires_human_acceptance_before_25c42")),
    ]
    rows = [{"contract_id": cid, "check": check, "observed": observed, "status": "PASS" if passed else "STOP"} for cid, check, passed, observed in checks]
    if not next_plan.empty and {"next_step", "allowed_now"}.issubset(next_plan.columns):
        m = next_plan[next_plan["next_step"].astype(str).eq(EXPECTED_ACCEPT_NEXT)]
        passed = not m.empty and as_bool(m.iloc[0].get("requires_human_acceptance_before_execution", False)) is True
        rows.append({
            "contract_id": "C014",
            "check": "25C41 next plan requires explicit human acceptance before 25C42",
            "observed": "" if m.empty else str(m.iloc[0].to_dict()),
            "status": "PASS" if passed else "STOP",
        })
    else:
        rows.append({"contract_id": "C014", "check": "25C41 next plan requires explicit human acceptance before 25C42", "observed": "schema missing", "status": "STOP"})
    return rows


def compare_variant(name: str, replay_df: pd.DataFrame, target_key: pd.DataFrame, baseline_map: Optional[pd.DataFrame], source_artifact: str) -> pd.DataFrame:
    rk = norm(replay_df)[KEY].drop_duplicates()
    cmp = rk.merge(target_key, on=KEY, how="outer", indicator=True)
    cmp["_merge"] = cmp["_merge"].astype(str)
    cmp["variant"] = name
    cmp["replay_present"] = cmp["_merge"].isin(["both", "left_only"])
    cmp["target_present"] = cmp["_merge"].isin(["both", "right_only"])
    if baseline_map is None:
        cmp["baseline_merge"] = cmp["_merge"]
        cmp["baseline_replay_present"] = cmp["replay_present"]
        cmp["baseline_target_present"] = cmp["target_present"]
    else:
        cmp = cmp.merge(baseline_map, on=KEY, how="left")
        cmp["baseline_merge"] = cmp["baseline_merge"].fillna("missing")
        cmp["baseline_replay_present"] = cmp["baseline_replay_present"].fillna(False).astype(bool)
        cmp["baseline_target_present"] = cmp["baseline_target_present"].fillna(False).astype(bool)
    cmp["adjusted_replay_present"] = cmp["replay_present"]
    cmp["adjusted_target_present"] = cmp["target_present"]
    cmp["right_only_reason"] = cmp.apply(lambda r: "target_present_replay_absent_after_variant_filter_exclusion" if r["_merge"] == "right_only" else "", axis=1)
    cmp["source_step"] = STEP
    cmp["source_artifact"] = source_artifact
    return cmp[[
        "variant", "dataset", "entry_time", "policy", "_merge", "replay_present", "target_present",
        "baseline_merge", "baseline_replay_present", "baseline_target_present", "adjusted_replay_present",
        "adjusted_target_present", "right_only_reason", "source_step", "source_artifact"
    ]]


def write_stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, contract_audit: pd.DataFrame, total_stop_rows: int) -> None:
    empty = pd.DataFrame()
    write_csv(out / "04_25c42_variant_full_row_level_compare_rows.csv", empty)
    write_csv(out / "05_25c42_variant_right_only_row_level_compare_rows.csv", empty)
    write_csv(out / "06_25c42_right_only_by_variant_dataset_policy.csv", empty)
    write_csv(out / "07_25c42_right_only_export_reconciliation_matrix.csv", contract_audit)
    write_csv(out / "08_25c42_execution_boundary_matrix.csv", pd.DataFrame([
        {"boundary": "row_level_export_execution", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
    ]))
    write_csv(out / "09_25c42_acceptance_gate_matrix.csv", contract_audit)
    write_csv(out / "10_25c42_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status}]))
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "row_level_export_executed": False,
        "dry_run_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "total_stop_rows": int(total_stop_rows),
    }
    write_json(out / "02_25c42_coreb_g1_right_only_row_level_export_summary.json", summary)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept-25c42-row-level-export", action="store_true")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--fx-output-root", default=None)
    args = ap.parse_args(argv)

    fx_root = Path(args.fx_output_root).resolve() if args.fx_output_root else default_fx_outputs()
    out = Path(args.output_dir).resolve() if args.output_dir else fx_root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base41 = fx_root / IN41
    control_req = {
        "s41": base41 / "02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json",
        "input_contract": base41 / "04_25c41_future_export_input_contract.csv",
        "schema_contract": base41 / "05_25c41_future_export_output_schema_contract.csv",
        "recon_contract": base41 / "06_25c41_future_export_reconciliation_contract.csv",
        "gates41": base41 / "08_25c41_acceptance_gate_matrix.csv",
        "next41": base41 / "09_25c41_next_step_plan.csv",
    }
    input_rows = [{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v), "source": "25C41 control"} for k, v in control_req.items()]
    input_audit = pd.DataFrame(input_rows)
    write_csv(out / "03_25c42_input_audit.csv", input_audit)

    if not bool(input_audit["exists"].all()):
        write_stop_outputs(out, STOP_MISSING, input_audit, input_audit, int((input_audit["status"] == "STOP").sum()))
        return 2

    if not args.accept_25c42_row_level_export:
        write_stop_outputs(out, STOP_ACCEPT, input_audit, pd.DataFrame([{"contract_id": "ACCEPT", "check": "--accept-25c42-row-level-export supplied", "observed": False, "status": "STOP"}]), 1)
        return 2

    s41 = read_json(control_req["s41"])
    future_inputs = read_csv(control_req["input_contract"])
    schema = read_csv(control_req["schema_contract"])
    recon_contract = read_csv(control_req["recon_contract"])
    next41 = read_csv(control_req["next41"])
    contract_audit = pd.DataFrame(contract_rows_from_25c41(s41, next41))
    if bool((contract_audit["status"] == "STOP").any()):
        write_stop_outputs(out, STOP_CONTRACT, input_audit, contract_audit, int((contract_audit["status"] == "STOP").sum()))
        return 2

    future_map = {str(r["role"]): Path(str(r["path"])) for _, r in future_inputs.iterrows()}
    req_paths = {
        "25C36 summary": fx_root / future_map["25C36 summary"],
        "25C36 adjusted bundles": fx_root / future_map["25C36 adjusted bundles"],
        "25C36 adjusted membership": fx_root / future_map["25C36 adjusted membership"],
        "25C10 filter replay rows": fx_root / future_map["25C10 filter replay rows"],
        "25C15 selected policy summary": fx_root / future_map["25C15 selected policy summary"],
        "25C7 target compare window summary": fx_root / future_map["25C7 target compare window summary"],
        "25B3 shortlist file audit": fx_root / future_map["25B3 shortlist file audit"],
    }
    extra_audit = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v), "source": "25C42 future export input"} for k, v in req_paths.items()])
    input_audit = pd.concat([input_audit, extra_audit], ignore_index=True)
    write_csv(out / "03_25c42_input_audit.csv", input_audit)
    if not bool(extra_audit["exists"].all()):
        write_stop_outputs(out, STOP_MISSING, input_audit, extra_audit, int((extra_audit["status"] == "STOP").sum()))
        return 2

    s36 = read_json(req_paths["25C36 summary"])
    if not as_bool(s36.get("requires_human_acceptance_before_25c37", False)):
        write_stop_outputs(out, STOP_CONTRACT, input_audit, pd.DataFrame([{"contract_id": "C015", "check": "25C36 accepted before 25C37", "observed": s36.get("requires_human_acceptance_before_25c37"), "status": "STOP"}]), 1)
        return 2

    bundles = read_csv(req_paths["25C36 adjusted bundles"])
    members = read_csv(req_paths["25C36 adjusted membership"])
    signals = norm(read_csv(req_paths["25C10 filter replay rows"]))
    s15 = read_json(req_paths["25C15 selected policy summary"])
    s7 = read_json(req_paths["25C7 target compare window summary"])
    audit = read_csv(req_paths["25B3 shortlist file audit"])

    signals["filter"] = signals.get("filter", pd.Series(dtype=str)).astype(str)
    selected = set(s15.get("selected_output_policies", []))
    fmin = pd.to_datetime(s7.get("feature_min_time"), errors="coerce")
    fmax = pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target_path = path_from_audit(audit, TARGET_NAME)
    if not str(target_path):
        write_stop_outputs(out, STOP_MISSING, input_audit, pd.DataFrame([{"contract_id": "TARGET", "check": "target rr125_top_ledgers.csv resolved from 25B3 audit", "observed": False, "status": "STOP"}]), 1)
        return 2
    target = norm(read_csv(target_path))
    target["time_norm"] = pd.to_datetime(target["entry_time"], errors="coerce")
    target = target[(target["time_norm"] >= fmin) & (target["time_norm"] <= fmax) & target["policy"].isin(selected)].copy()
    target_key = target[KEY].drop_duplicates()
    signals = signals[signals["policy"].isin(selected)].copy()

    baseline_cmp = compare_variant("BASELINE_CURRENT", signals, target_key, None, str(req_paths["25C10 filter replay rows"]))
    baseline_map = baseline_cmp[KEY + ["_merge", "replay_present", "target_present"]].rename(columns={
        "_merge": "baseline_merge",
        "replay_present": "baseline_replay_present",
        "target_present": "baseline_target_present",
    })

    frames = [baseline_cmp]
    id_col = "adjusted_bundle_id"
    for _, b in bundles.iterrows():
        bid = str(b[id_col])
        bname = str(b["bundle_name"])
        variant = bid + "_" + bname
        if variant not in EXPECTED_VARIANTS:
            continue
        filters = set(members[members[id_col].astype(str).eq(bid)]["filter"].astype(str).tolist())
        narrowed = signals[~signals["filter"].isin(filters)].copy()
        frames.append(compare_variant(variant, narrowed, target_key, baseline_map, str(req_paths["25C10 filter replay rows"])))

    full = pd.concat(frames, ignore_index=True)
    missing_variants = sorted(EXPECTED_VARIANTS - set(full["variant"].astype(str).unique()))
    if missing_variants:
        write_stop_outputs(out, STOP_CONTRACT, input_audit, pd.DataFrame([{"contract_id": "VARIANTS", "check": "all expected variants exported", "observed": ",".join(missing_variants), "status": "STOP"}]), len(missing_variants))
        return 2

    right_only = full[(full["variant"].ne("BASELINE_CURRENT")) & (full["_merge"].eq("right_only"))].copy()
    by_policy = right_only.groupby(["variant", "dataset", "policy"], dropna=False).size().reset_index(name="right_only_rows")

    actual_counts = full[full["variant"].ne("BASELINE_CURRENT")].groupby(["variant", "_merge"], dropna=False).size().unstack(fill_value=0).reset_index()
    for c in ["both", "left_only", "right_only"]:
        if c not in actual_counts.columns:
            actual_counts[c] = 0
    recon = recon_contract.copy()
    for c in ["expected_both", "expected_left_only", "expected_right_only"]:
        recon[c] = pd.to_numeric(recon[c], errors="coerce").fillna(-1).astype(int)
    actual = actual_counts[["variant", "both", "left_only", "right_only"]].rename(columns={
        "both": "exported_both",
        "left_only": "exported_left_only",
        "right_only": "exported_right_only",
    })
    recon = recon.merge(actual, on="variant", how="left")
    for c in ["exported_both", "exported_left_only", "exported_right_only"]:
        recon[c] = pd.to_numeric(recon[c], errors="coerce").fillna(-1).astype(int)
    recon["both_match"] = recon["expected_both"].eq(recon["exported_both"])
    recon["left_only_match"] = recon["expected_left_only"].eq(recon["exported_left_only"])
    recon["right_only_match"] = recon["expected_right_only"].eq(recon["exported_right_only"])
    recon["status"] = recon.apply(lambda r: "PASS" if r["both_match"] and r["left_only_match"] and r["right_only_match"] else "STOP", axis=1)

    write_csv(out / "04_25c42_variant_full_row_level_compare_rows.csv", full.sort_values(["variant"] + KEY))
    write_csv(out / "05_25c42_variant_right_only_row_level_compare_rows.csv", right_only.sort_values(["variant"] + KEY))
    write_csv(out / "06_25c42_right_only_by_variant_dataset_policy.csv", by_policy.sort_values(["variant", "dataset", "policy"]))
    write_csv(out / "07_25c42_right_only_export_reconciliation_matrix.csv", recon)

    recon_ok = bool((recon["status"] == "PASS").all())
    boundary = pd.DataFrame([
        {"boundary": "human_acceptance_flag_supplied", "allowed": True, "observed": True},
        {"boundary": "row_level_export_execution", "allowed": True, "observed": True},
        {"boundary": "recompute_coreb_compare_for_export_only", "allowed": True, "observed": True},
        {"boundary": "run_new_dry_run", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "approve_best_variant", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "08_25c42_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C41 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "human acceptance flag supplied", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "row-level export reconciles to 25C41 contract", "observed": recon_ok, "status": "PASS" if recon_ok else "STOP"},
        {"gate_id": "G004", "gate": "right_only rows exported", "observed": len(right_only) > 0, "status": "PASS" if len(right_only) > 0 else "STOP"},
        {"gate_id": "G005", "gate": "driver review can start", "observed": recon_ok and len(right_only) > 0, "status": "PASS" if recon_ok and len(right_only) > 0 else "BLOCKED"},
        {"gate_id": "G006", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G007", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "09_25c42_acceptance_gate_matrix.csv", gates)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY" if recon_ok else "STOP_RECONCILIATION_MISMATCH", "allowed_now": bool(recon_ok), "purpose": "review exported right_only rows to identify target-damaging drivers; no live unblock", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c42": False},
        {"rank": 2, "next_step": "future adjusted narrowing plan/dry-run", "allowed_now": False, "purpose": "blocked until driver review and separate human acceptance gate", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c42": False},
        {"rank": 3, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c42": False},
    ])
    write_csv(out / "10_25c42_next_step_plan.csv", next_plan)

    unnecessary = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "new dry-run outputs", "AI review ledgers"]
    necessary = [
        "01_25c42_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY_REPORT.md",
        "02_25c42_coreb_g1_right_only_row_level_export_summary.json",
        "03_25c42_input_audit.csv",
        "04_25c42_variant_full_row_level_compare_rows.csv",
        "05_25c42_variant_right_only_row_level_compare_rows.csv",
        "06_25c42_right_only_by_variant_dataset_policy.csv",
        "07_25c42_right_only_export_reconciliation_matrix.csv",
        "08_25c42_execution_boundary_matrix.csv",
        "09_25c42_acceptance_gate_matrix.csv",
        "10_25c42_next_step_plan.csv",
    ]
    write_csv(out / "00_不要_25c42_file_request_list.csv", pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)] +
        [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    ))

    if not recon_ok:
        status = STOP_RECON
        next_recommended = "STOP_RECONCILIATION_MISMATCH"
    else:
        status = STATUS
        next_recommended = "25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY"

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "human_acceptance_flag_supplied": True,
        "row_level_export_executed": True,
        "dry_run_executed": False,
        "condition_changed": False,
        "full_coreb_parity": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "best_variant_approved": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "full_row_count": int(len(full)),
        "right_only_row_count": int(len(right_only)),
        "reconciliation_passed": recon_ok,
        "next_recommended_step": next_recommended,
        "total_stop_rows": 0 if recon_ok else int((recon["status"] == "STOP").sum()),
    }
    write_json(out / "02_25c42_coreb_g1_right_only_row_level_export_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C42 CoreB G1 right_only row-level export audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Scope",
        "",
        "This step exports row-level compare evidence only after explicit 25C42 acceptance. It does not run a new dry-run, change conditions, approve variants, or unblock live behavior.",
        "",
        "## 25C41 contract audit",
        "",
        md_table(contract_audit),
        "",
        "## Reconciliation matrix",
        "",
        md_table(recon),
        "",
        "## Right-only by variant / dataset / policy",
        "",
        md_table(by_policy),
        "",
        "## Output row counts",
        "",
        md_table(pd.DataFrame([{"full_row_count": len(full), "right_only_row_count": len(right_only), "reconciliation_passed": recon_ok}])),
        "",
        "## Execution boundaries",
        "",
        md_table(boundary),
        "",
        "## Acceptance gates",
        "",
        md_table(gates),
        "",
        "## File request list",
        "",
        "```text",
        "00_不要_貼らなくてOK",
        *[f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)],
        "",
        "必要・見るファイル",
        *[f"{i+1:02d}. {x}" for i, x in enumerate(necessary)],
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- 25C42 exports audit evidence only and does not approve any variant.",
        "- CoreB live evaluator, Discord, MT5, AI API, live hook, and final signal remain blocked.",
        "- Future dry-run remains blocked until driver review and separate explicit human acceptance.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c42_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": status,
        "full_row_count": int(len(full)),
        "right_only_row_count": int(len(right_only)),
        "reconciliation_passed": recon_ok,
        "next_recommended_step": next_recommended,
        "dry_run_executed": False,
        "ai_api_called": False,
    }, ensure_ascii=False, indent=2))
    return 0 if recon_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
