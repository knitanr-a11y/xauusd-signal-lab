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

STEP = "25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_PREFLIGHT_SPEC_READY_AUDIT_ONLY_EXECUTION_GATE_REVIEW_REQUIRED"
STOP_MISSING = "25C53_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C53_STOP_25C52_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_PREFLIGHT = "25C53_STOP_PREFLIGHT_SPEC_UNSAFE_AUDIT_ONLY"
IN52 = "gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only"
OUT_DIR = "gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only"
EXPECTED_52_STEP = "25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY"
EXPECTED_52_STATUS = "COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_READY_AUDIT_ONLY_SOURCE_BOUND_FOR_PLANNING_EXECUTION_BLOCKED"
EXPECTED_NEXT_IN_52 = STEP
NEXT_STEP = "25C54_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
EXPECTED_CANDIDATE_RELATIVE_PATH = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv"
EXPECTED_COLUMNS = [
    "dataset",
    "entry_time",
    "policy",
    "filter",
    "source_count_by_entry_time",
    "unique_origin_count_by_entry_time",
    "same_count_threshold",
    "unique_origins_threshold",
    "intersection_only",
    "full_coreb_parity",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
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


def as_bool(v: object) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in {"true", "1", "yes", "y"}


def as_int(v: object) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def md_table(df: pd.DataFrame, n: int = 120) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def file_request_df() -> pd.DataFrame:
    skip = ["raw OHLC", "old GOLD/DISC8", "24-series source recovery execution", "new replay/dry-run outputs", "AI ledgers", "Discord/MT5/live artifacts"]
    keep = [
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/02_25c52_dry_run_source_candidate_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/06_25c52_candidate_header_review.csv",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/07_25c52_source_binding_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/01_25c53_GOLD_V2_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/02_25c53_dry_run_preflight_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/05_25c53_preflight_input_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/06_25c53_preflight_check_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def execution_boundary_matrix() -> pd.DataFrame:
    rows = [
        ("variant_approval", False, False),
        ("replay_execution", False, False),
        ("dry_run_execution", False, False),
        ("condition_change", False, False),
        ("source_change_or_recovery", False, False),
        ("source_confirmed_for_execution", False, False),
        ("coreb_live_evaluator_unblock", False, False),
        ("discord_notification", False, False),
        ("mt5_order", False, False),
        ("ai_api_call", False, False),
        ("live_hook", False, False),
        ("final_signal", False, False),
        ("no_signal_discord_notify", False, False),
    ]
    return pd.DataFrame([{"boundary_id": f"X{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary52: Optional[dict] = None) -> int:
    summary52 = summary52 or {}
    write_csv(out / "00_不要_25c53_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c53_input_audit.csv", input_audit)
    write_csv(out / "04_25c53_contract_audit.csv", diag)
    write_csv(out / "05_25c53_preflight_input_matrix.csv", diag)
    write_csv(out / "06_25c53_preflight_check_matrix.csv", diag)
    write_csv(out / "07_25c53_preflight_output_spec_matrix.csv", diag)
    boundary = execution_boundary_matrix()
    write_csv(out / "08_25c53_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C52 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "preflight spec", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "09_25c53_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c53": False}])
    write_csv(out / "10_25c53_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C53 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "11_25c53_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "preflight_spec_only": True,
        "input_25c52_step": summary52.get("step"),
        "input_25c52_status": summary52.get("status"),
        "variant_approved": False,
        "replay_executed": False,
        "dry_run_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "source_confirmed_for_execution": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": "STOP",
        "total_stop_rows": int((diag.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if isinstance(diag, pd.DataFrame) else 1,
    }
    write_json(out / "02_25c53_dry_run_preflight_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C53 CoreB G1 dry-run preflight spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c53_GOLD_V2_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary52: dict, contract52: pd.DataFrame, metadata52: pd.DataFrame, header52: pd.DataFrame, binding52: pd.DataFrame, boundary52: pd.DataFrame, gates52: pd.DataFrame, next52: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_52_STEP,
        "status": EXPECTED_52_STATUS,
        "audit_only": True,
        "source_candidate_review_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "candidate_relative_path": EXPECTED_CANDIDATE_RELATIVE_PATH,
        "candidate_file_exists": True,
        "candidate_header_readable": True,
        "candidate_column_count": 10,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "source_bound_for_future_audit_planning": True,
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "next_recommended_step": EXPECTED_NEXT_IN_52,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary52.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary52.get("representative_filters", [])
    rows.append({"contract_id": "C017", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary52.get(flag), "expected": False, "status": "PASS" if summary52.get(flag) is False else "STOP"})
    stop_count = int(contract52[contract52.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    metadata_ok = (not metadata52.empty and str(metadata52.iloc[0].get("metadata_status")) == "PASS")
    header_cols = str(header52.iloc[0].get("columns_joined", "")).split(";") if not header52.empty else []
    header_ok = (not header52.empty and str(header52.iloc[0].get("header_status")) == "PASS" and header_cols == EXPECTED_COLUMNS)
    binding_ok = (not binding52.empty and str(binding52.iloc[0].get("source_binding_status")) == "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY" and not as_bool(binding52.iloc[0].get("source_confirmed_for_execution")) and not as_bool(binding52.iloc[0].get("future_dry_run_execution_allowed")))
    boundary_ok = int(boundary52[boundary52.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gate_ok = "EXECUTION_CONFIRMATION_BLOCKED" in gates52.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next52.empty and str(next52.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_52 and as_bool(next52.iloc[0].get("allowed_now")) and not as_bool(next52.iloc[0].get("execution_allowed_in_25c52")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C52 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "candidate metadata PASS", "observed": metadata52.iloc[0].to_dict() if not metadata52.empty else {}, "expected": "metadata_status PASS", "status": "PASS" if metadata_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "candidate header exact", "observed": ";".join(header_cols), "expected": ";".join(EXPECTED_COLUMNS), "status": "PASS" if header_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "source bound for planning only", "observed": binding52.iloc[0].to_dict() if not binding52.empty else {}, "expected": "planning only; execution false", "status": "PASS" if binding_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C52 execution boundary has no STOP", "observed": boundary_ok, "expected": True, "status": "PASS" if boundary_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C52 gates block execution confirmation", "observed": gate_ok, "expected": True, "status": "PASS" if gate_ok else "STOP"},
        {"contract_id": f"M{len(rows)+7:03d}", "check": "25C52 next plan allows 25C53 only", "observed": next52.iloc[0].to_dict() if not next52.empty else {}, "expected": "25C53 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_preflight_matrices(summary52: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inputs = pd.DataFrame([
        {"input_id": "I001", "input_name": "bound source candidate", "value": summary52.get("candidate_relative_path"), "required": True, "preflight_status": "SPEC_READY_AUDIT_ONLY"},
        {"input_id": "I002", "input_name": "candidate header columns", "value": ";".join(EXPECTED_COLUMNS), "required": True, "preflight_status": "SPEC_READY_AUDIT_ONLY"},
        {"input_id": "I003", "input_name": "representative variant", "value": "A002", "required": True, "preflight_status": "SPEC_READY_AUDIT_ONLY"},
        {"input_id": "I004", "input_name": "representative filters", "value": ";".join(EXPECTED_FILTERS), "required": True, "preflight_status": "SPEC_READY_AUDIT_ONLY"},
        {"input_id": "I005", "input_name": "unique key", "value": "variant+dataset+entry_time+policy", "required": True, "preflight_status": "SPEC_READY_AUDIT_ONLY"},
    ])
    checks = pd.DataFrame([
        {"check_id": "P001", "check": "source candidate bound for planning only", "expected": True, "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P002", "check": "source candidate header exact", "expected": ";".join(EXPECTED_COLUMNS), "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P003", "check": "A002 representative filters exact", "expected": ";".join(EXPECTED_FILTERS), "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P004", "check": "A002 approval status", "expected": "NOT_APPROVED_REVIEW_ONLY", "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P005", "check": "expected representative unique damage keys", "expected": 69, "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P006", "check": "expected representative open keys", "expected": 0, "execution_allowed_now": False, "status": "SPEC_READY_AUDIT_ONLY"},
        {"check_id": "P007", "check": "future dry-run execution", "expected": "blocked until later explicit acceptance", "execution_allowed_now": False, "status": "BLOCKED"},
        {"check_id": "P008", "check": "live/external actions", "expected": "blocked", "execution_allowed_now": False, "status": "BLOCKED"},
    ])
    outputs = pd.DataFrame([
        {"output_id": "O001", "future_output": "dry-run preflight summary json", "required": True, "execution_allowed_in_25c53": False},
        {"output_id": "O002", "future_output": "dry-run source load audit csv", "required": True, "execution_allowed_in_25c53": False},
        {"output_id": "O003", "future_output": "dry-run candidate row shape audit csv", "required": True, "execution_allowed_in_25c53": False},
        {"output_id": "O004", "future_output": "dry-run unique key coverage precheck csv", "required": True, "execution_allowed_in_25c53": False},
        {"output_id": "O005", "future_output": "dry-run execution gate matrix", "required": True, "execution_allowed_in_25c53": False},
        {"output_id": "O006", "future_output": "dry-run handoff notes", "required": True, "execution_allowed_in_25c53": False},
    ])
    return inputs, checks, outputs


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN52
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary52": input_dir / "02_25c52_dry_run_source_candidate_review_summary.json",
        "contract52": input_dir / "04_25c52_contract_audit.csv",
        "metadata52": input_dir / "05_25c52_candidate_file_metadata.csv",
        "header52": input_dir / "06_25c52_candidate_header_review.csv",
        "binding52": input_dir / "07_25c52_source_binding_matrix.csv",
        "boundary52": input_dir / "08_25c52_execution_boundary_matrix.csv",
        "gates52": input_dir / "09_25c52_gates.csv",
        "next52": input_dir / "10_25c52_next_step_plan.csv",
        "notes52": input_dir / "11_25c52_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c53_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary52 = read_json(req["summary52"])
    contract52 = read_csv(req["contract52"])
    metadata52 = read_csv(req["metadata52"])
    header52 = read_csv(req["header52"])
    binding52 = read_csv(req["binding52"])
    boundary52 = read_csv(req["boundary52"])
    gates52 = read_csv(req["gates52"])
    next52 = read_csv(req["next52"])
    notes52 = read_csv(req["notes52"])

    contract = contract_audit(summary52, contract52, metadata52, header52, binding52, boundary52, gates52, next52)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary52)

    preflight_inputs, preflight_checks, preflight_outputs = build_preflight_matrices(summary52)
    if preflight_checks["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_PREFLIGHT, input_audit, preflight_checks, summary52)

    boundary = execution_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C52 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "preflight spec ready", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "source confirmed for execution", "observed": False, "status": "EXECUTION_CONFIRMATION_BLOCKED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "review execution gate only; no dry-run execution", "execution_allowed_in_25c53": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until execution gate review and later explicit acceptance", "execution_allowed_in_25c53": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c53": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C53 used 25C52 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Dry-run preflight spec was created only; no dry-run was executed.", "status": "PASS"},
        {"note_id": "N003", "note": "Source remains bound for future planning only and is not confirmed for execution.", "status": "PASS"},
        {"note_id": "N004", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c53_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c53_input_audit.csv", input_audit)
    write_csv(out / "04_25c53_contract_audit.csv", contract)
    write_csv(out / "05_25c53_preflight_input_matrix.csv", preflight_inputs)
    write_csv(out / "06_25c53_preflight_check_matrix.csv", preflight_checks)
    write_csv(out / "07_25c53_preflight_output_spec_matrix.csv", preflight_outputs)
    write_csv(out / "08_25c53_execution_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c53_gates.csv", gates)
    write_csv(out / "10_25c53_next_step_plan.csv", next_plan)
    write_csv(out / "11_25c53_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "preflight_spec_only": True,
        "input_25c52_step": summary52.get("step"),
        "input_25c52_status": summary52.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "candidate_relative_path": EXPECTED_CANDIDATE_RELATIVE_PATH,
        "candidate_header_columns": EXPECTED_COLUMNS,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "preflight_input_rows": int(len(preflight_inputs)),
        "preflight_check_rows": int(len(preflight_checks)),
        "preflight_output_spec_rows": int(len(preflight_outputs)),
        "variant_approved": False,
        "replay_executed": False,
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
        "next_recommended_step": NEXT_STEP,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c53_dry_run_preflight_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C53 CoreB G1 dry-run preflight spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C53 writes the dry-run preflight specification package only. It does not confirm the source for execution and does not execute dry-run.", "",
        "## 25C52 contract audit", "", md_table(contract), "",
        "## Preflight input matrix", "", md_table(preflight_inputs), "",
        "## Preflight check matrix", "", md_table(preflight_checks), "",
        "## Preflight output spec matrix", "", md_table(preflight_outputs), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Source is still planning-only, not confirmed for execution. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c53_GOLD_V2_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "preflight_spec_only": True, "source_confirmed_for_execution": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
