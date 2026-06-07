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

STEP = "25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_READY_AUDIT_ONLY_SOURCE_CONCRETION_REQUIRED"
STOP_MISSING = "25C50_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C50_STOP_25C49_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_READINESS = "25C50_STOP_READINESS_REVIEW_UNSAFE_AUDIT_ONLY"
IN49 = "gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only"
OUT_DIR = "gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only"
EXPECTED_49_STEP = "25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY"
EXPECTED_49_STATUS = "COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_READY_AUDIT_ONLY"
EXPECTED_NEXT_IN_49 = STEP
NEXT_STEP = "25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
BASELINE_SOURCE_LABEL = "audited baseline replay signal source"


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


def md_table(df: pd.DataFrame, n: int = 100) -> str:
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
    skip = ["raw OHLC", "old GOLD/DISC8", "24-series source recovery", "new replay/dry-run outputs", "AI ledgers", "Discord/MT5/live artifacts"]
    keep = [
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/02_25c49_representative_filter_set_dry_run_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/05_25c49_dry_run_input_contract.csv",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/07_25c49_dry_run_acceptance_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/01_25c50_GOLD_V2_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/02_25c50_representative_dry_run_readiness_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/05_25c50_readiness_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/06_25c50_unresolved_source_matrix.csv",
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
        ("coreb_live_evaluator_unblock", False, False),
        ("discord_notification", False, False),
        ("mt5_order", False, False),
        ("ai_api_call", False, False),
        ("live_hook", False, False),
        ("final_signal", False, False),
        ("no_signal_discord_notify", False, False),
    ]
    return pd.DataFrame([{"boundary_id": f"X{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary49: Optional[dict] = None) -> int:
    summary49 = summary49 or {}
    write_csv(out / "00_不要_25c50_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c50_input_audit.csv", input_audit)
    write_csv(out / "04_25c50_contract_audit.csv", diag)
    write_csv(out / "05_25c50_readiness_matrix.csv", diag)
    write_csv(out / "06_25c50_unresolved_source_matrix.csv", diag)
    boundary = execution_boundary_matrix()
    write_csv(out / "07_25c50_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C49 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "source concretion required", "observed": True, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c50_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c50": False}])
    write_csv(out / "09_25c50_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C50 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c50_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "readiness_review_only": True,
        "input_25c49_step": summary49.get("step"),
        "input_25c49_status": summary49.get("status"),
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
        "next_recommended_step": "STOP",
        "total_stop_rows": int((diag.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if isinstance(diag, pd.DataFrame) else 1,
    }
    write_json(out / "02_25c50_representative_dry_run_readiness_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C50 CoreB G1 representative dry-run readiness review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c50_GOLD_V2_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary49: dict, contract49: pd.DataFrame, input_contract: pd.DataFrame, output_contract: pd.DataFrame, acceptance: pd.DataFrame, blocked49: pd.DataFrame, next49: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_49_STEP,
        "status": EXPECTED_49_STATUS,
        "audit_only": True,
        "dry_run_spec_only": True,
        "representative_variant_code": "A002",
        "representative_retention_priority_cutoff": 1,
        "representative_total_unique_damage_keys": 69,
        "representative_covered_unique_keys": 69,
        "representative_open_unique_keys": 0,
        "representative_retained_filter_count": 2,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "dry_run_input_contract_rows": 5,
        "dry_run_output_contract_rows": 6,
        "dry_run_acceptance_rows": 7,
        "next_recommended_step": EXPECTED_NEXT_IN_49,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary49.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary49.get("representative_filters", [])
    rows.append({"contract_id": "C017", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary49.get(flag), "expected": False, "status": "PASS" if summary49.get(flag) is False else "STOP"})
    matrix_checks = [
        ("25C49 contract has no STOP", contract49),
        ("25C49 blocked matrix has no STOP", blocked49),
    ]
    for name, df in matrix_checks:
        stop_count = int(df[df.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) if isinstance(df, pd.DataFrame) else -1
        rows.append({"contract_id": f"M{len(rows)+1:03d}", "check": name, "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"})
    row_counts = [("input contract rows", len(input_contract), 5), ("output contract rows", len(output_contract), 6), ("acceptance rows", len(acceptance), 7)]
    for name, obs, exp in row_counts:
        rows.append({"contract_id": f"M{len(rows)+1:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    all_inputs_sot = bool(input_contract.get("source_of_truth", pd.Series(dtype=object)).apply(as_bool).all()) if not input_contract.empty else False
    acceptance_blocks = ("source recovery implied" in acceptance.get("check", pd.Series(dtype=str)).astype(str).tolist() and "live/external/AI/notification/order/final signal enabled" in acceptance.get("check", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in acceptance.get("status", pd.Series(dtype=str)).astype(str).tolist())
    next_ok = (not next49.empty and str(next49.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_49 and as_bool(next49.iloc[0].get("allowed_now")) and not as_bool(next49.iloc[0].get("execution_allowed_in_25c49")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "all dry-run inputs marked source_of_truth", "observed": all_inputs_sot, "expected": True, "status": "PASS" if all_inputs_sot else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "acceptance matrix blocks source recovery and live/external", "observed": acceptance_blocks, "expected": True, "status": "PASS" if acceptance_blocks else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C49 next plan allows 25C50 readiness review only", "observed": next49.iloc[0].to_dict() if not next49.empty else {}, "expected": "25C50 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_readiness(input_contract: pd.DataFrame, output_contract: pd.DataFrame, acceptance: pd.DataFrame, blocked49: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    unresolved_mask = input_contract["required_input"].astype(str).eq(BASELINE_SOURCE_LABEL) if "required_input" in input_contract else pd.Series([False] * len(input_contract))
    unresolved = input_contract[unresolved_mask].copy()
    if unresolved.empty:
        unresolved_matrix = pd.DataFrame([{"source_id": "U001", "required_input": BASELINE_SOURCE_LABEL, "current_path_hint": "MISSING", "readiness_state": "STOP_SOURCE_LINE_MISSING", "blocks_future_execution": True, "status": "STOP"}])
    else:
        unresolved_matrix = pd.DataFrame([{
            "source_id": "U001",
            "required_input": BASELINE_SOURCE_LABEL,
            "current_path_hint": str(unresolved.iloc[0].get("path_hint", "")),
            "readiness_state": "SOURCE_CONCRETION_REQUIRED",
            "blocks_future_execution": True,
            "status": "BLOCKED_NOT_STOP",
            "required_next_action": "Identify exact audited baseline replay signal source file before any dry-run execution.",
        }])
    readiness = pd.DataFrame([
        {"readiness_id": "R001", "check": "25C49 contract safe", "observed": True, "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS"},
        {"readiness_id": "R002", "check": "A002 representative still unapproved", "observed": True, "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS"},
        {"readiness_id": "R003", "check": "filter set exactly matches two retained filters", "observed": True, "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS"},
        {"readiness_id": "R004", "check": "dry-run input contract complete", "observed": len(input_contract), "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS" if len(input_contract) == 5 else "STOP"},
        {"readiness_id": "R005", "check": "dry-run output contract complete", "observed": len(output_contract), "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS" if len(output_contract) == 6 else "STOP"},
        {"readiness_id": "R006", "check": "dry-run acceptance contract complete", "observed": len(acceptance), "readiness_state": "SPEC_READY_FOR_MANUAL_REVIEW", "blocks_future_execution": False, "status": "PASS" if len(acceptance) == 7 else "STOP"},
        {"readiness_id": "R007", "check": "all future execution boundaries remain blocked", "observed": int((blocked49.get("status", pd.Series(dtype=str)).astype(str) == "PASS").sum()), "readiness_state": "EXECUTION_BLOCKED", "blocks_future_execution": True, "status": "PASS"},
        {"readiness_id": "R008", "check": "exact baseline replay signal source confirmed", "observed": False, "readiness_state": "SOURCE_CONCRETION_REQUIRED", "blocks_future_execution": True, "status": "BLOCKED_NOT_STOP"},
    ])
    boundary = execution_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C49 dry-run spec safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "manual spec review may proceed", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "exact baseline replay signal source confirmed", "observed": False, "status": "SOURCE_CONCRETION_REQUIRED"},
        {"gate_id": "G004", "gate": "dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    return readiness, unresolved_matrix, boundary, gates


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN49
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary49": input_dir / "02_25c49_representative_filter_set_dry_run_spec_summary.json",
        "contract49": input_dir / "04_25c49_contract_audit.csv",
        "input_contract49": input_dir / "05_25c49_dry_run_input_contract.csv",
        "output_contract49": input_dir / "06_25c49_dry_run_output_contract.csv",
        "acceptance49": input_dir / "07_25c49_dry_run_acceptance_matrix.csv",
        "blocked49": input_dir / "08_25c49_blocked_execution_matrix.csv",
        "next49": input_dir / "09_25c49_next_step_plan.csv",
        "notes49": input_dir / "10_25c49_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c50_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary49 = read_json(req["summary49"])
    contract49 = read_csv(req["contract49"])
    input_contract = read_csv(req["input_contract49"])
    output_contract = read_csv(req["output_contract49"])
    acceptance = read_csv(req["acceptance49"])
    blocked49 = read_csv(req["blocked49"])
    next49 = read_csv(req["next49"])
    notes49 = read_csv(req["notes49"])

    contract = contract_audit(summary49, contract49, input_contract, output_contract, acceptance, blocked49, next49)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary49)

    readiness, unresolved, boundary, gates = build_readiness(input_contract, output_contract, acceptance, blocked49)
    if readiness["status"].astype(str).eq("STOP").any() or unresolved["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_READINESS, input_audit, pd.concat([readiness, unresolved], ignore_index=True), summary49)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "identify exact audited baseline replay signal source; no execution", "execution_allowed_in_25c50": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until exact source concretion and later explicit acceptance", "execution_allowed_in_25c50": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c50": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C50 used 25C49 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Dry-run specification is ready for manual review, but future execution remains blocked.", "status": "PASS"},
        {"note_id": "N003", "note": "Exact audited baseline replay signal source must be concreted before any dry-run execution.", "status": "SOURCE_CONCRETION_REQUIRED"},
        {"note_id": "N004", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c50_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c50_input_audit.csv", input_audit)
    write_csv(out / "04_25c50_contract_audit.csv", contract)
    write_csv(out / "05_25c50_readiness_matrix.csv", readiness)
    write_csv(out / "06_25c50_unresolved_source_matrix.csv", unresolved)
    write_csv(out / "07_25c50_execution_boundary_matrix.csv", boundary)
    write_csv(out / "08_25c50_gates.csv", gates)
    write_csv(out / "09_25c50_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c50_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "readiness_review_only": True,
        "input_25c49_step": summary49.get("step"),
        "input_25c49_status": summary49.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "dry_run_spec_ready_for_manual_review": True,
        "source_concretion_required": True,
        "exact_baseline_replay_signal_source_confirmed": False,
        "future_dry_run_execution_allowed": False,
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
    write_json(out / "02_25c50_representative_dry_run_readiness_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C50 CoreB G1 representative dry-run readiness review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C50 reviews the dry-run specification readiness only. It does not run replay or dry-run and does not approve A002.", "",
        "## 25C49 contract audit", "", md_table(contract), "",
        "## Readiness matrix", "", md_table(readiness), "",
        "## Unresolved source matrix", "", md_table(unresolved), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c50_GOLD_V2_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "dry_run_spec_ready_for_manual_review": True, "source_concretion_required": True, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
