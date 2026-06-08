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

STEP = "25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY"
STATUS = "COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_READY_AUDIT_ONLY_HUMAN_DIRECTION_REQUIRED_NO_EXECUTION"
STOP_MISSING = "25C62_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C62_STOP_25C61_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_SCOPE = "25C62_STOP_FIXED_CONDITION_SCOPE_UNSAFE_AUDIT_ONLY"
IN61 = "gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only"
OUT_DIR = "gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only"
EXPECTED_61_STEP = "25C61_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY"
EXPECTED_61_STATUS = "COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_READY_AUDIT_ONLY_EXECUTION_BLOCKED_MINIMAL_GATES_IDENTIFIED"
NEXT_STEP = "WAIT_FOR_SINGLE_FIXED_CONDITION_DRY_RUN_DIRECTION_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]


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
        "FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json",
        "FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/01_25c62_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/02_25c62_a002_fixed_dry_run_direction_package_summary.json",
        "FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/06_25c62_human_direction_required_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/07_25c62_derived_gate_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary61: Optional[dict] = None) -> int:
    summary61 = summary61 or {}
    write_csv(out / "00_不要_25c62_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c62_input_audit.csv", input_audit)
    write_csv(out / "04_25c62_contract_audit.csv", diag)
    write_csv(out / "05_25c62_fixed_condition_scope_matrix.csv", diag)
    write_csv(out / "06_25c62_human_direction_required_matrix.csv", diag)
    write_csv(out / "07_25c62_derived_gate_matrix.csv", diag)
    write_csv(out / "08_25c62_execution_boundary_matrix.csv", diag)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c62": False}])
    write_csv(out / "09_25c62_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C62 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No condition change, replay, dry-run, source recovery, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c62_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "human_direction_package_only": True,
        "input_25c61_step": summary61.get("step"),
        "input_25c61_status": summary61.get("status"),
        "condition_changed": False,
        "future_dry_run_execution_allowed": False,
        "dry_run_executed": False,
        "replay_executed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": "STOP",
        "total_stop_rows": int((diag.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if isinstance(diag, pd.DataFrame) else 1,
    }
    write_json(out / "02_25c62_a002_fixed_dry_run_direction_package_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C62 CoreB G1 A002 fixed dry-run direction package audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No condition change or dry-run/external action was performed.",
    ])
    lp(out / "01_25c62_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "condition_changed": False, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary61: dict, contract61: pd.DataFrame, freeze61: pd.DataFrame, gate61: pd.DataFrame, decision61: pd.DataFrame, boundary61: pd.DataFrame, next61: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_61_STEP,
        "status": EXPECTED_61_STATUS,
        "audit_only": True,
        "integrated_minimal_gate_review_only": True,
        "representative_variant_code": "A002",
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "minimal_gate_rows": 5,
        "minimal_gates_blocking_future_dry_run": 5,
        "source_confirmed_for_execution": False,
        "a002_variant_approved": False,
        "human_dry_run_execution_approval": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "next_recommended_step": "WAIT_FOR_EXPLICIT_HUMAN_DIRECTION_FOR_FIXED_CONDITION_AUDIT_ONLY",
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary61.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary61.get("representative_filters", [])
    rows.append({"contract_id": "C018", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary61.get(flag), "expected": False, "status": "PASS" if summary61.get(flag) is False else "STOP"})
    stop_count = int(contract61[contract61.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    freeze_ok = len(freeze61) == 6 and freeze61.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").all()
    gate_ok = len(gate61) == 5 and gate61.get("status", pd.Series(dtype=str)).astype(str).eq("BLOCKED_NOT_STOP").all()
    decision_ok = len(decision61) == 5 and int(decision61.get("status", pd.Series(dtype=str)).astype(str).eq("NEEDS_HUMAN_DIRECTION").sum()) == 3
    boundary_ok = len(boundary61) == 6 and boundary61.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").all()
    next_ok = (not next61.empty and str(next61.iloc[0].get("next_step")) == "WAIT_FOR_EXPLICIT_HUMAN_DIRECTION_FOR_FIXED_CONDITION_AUDIT_ONLY" and as_bool(next61.iloc[0].get("allowed_now")) and not as_bool(next61.iloc[0].get("execution_allowed_in_25c61")) and not as_bool(next61.iloc[0].get("condition_change_allowed")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C61 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "condition freeze safe", "observed": freeze_ok, "expected": True, "status": "PASS" if freeze_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "five minimal gates blocked not stop", "observed": gate_ok, "expected": True, "status": "PASS" if gate_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "three human-direction decisions needed", "observed": decision_ok, "expected": True, "status": "PASS" if decision_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "execution boundaries safe", "observed": boundary_ok, "expected": True, "status": "PASS" if boundary_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C61 next plan waits for fixed-condition direction only", "observed": next61.iloc[0].to_dict() if not next61.empty else {}, "expected": "WAIT_FOR_EXPLICIT_HUMAN_DIRECTION... and execution/condition false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scope = pd.DataFrame([
        {"scope_id": "S001", "item": "variant", "value": "A002", "fixed": True, "status": "FIXED"},
        {"scope_id": "S002", "item": "filter_1", "value": EXPECTED_FILTERS[0], "fixed": True, "status": "FIXED"},
        {"scope_id": "S003", "item": "filter_2", "value": EXPECTED_FILTERS[1], "fixed": True, "status": "FIXED"},
        {"scope_id": "S004", "item": "condition_change", "value": "not allowed", "fixed": True, "status": "BLOCKED"},
        {"scope_id": "S005", "item": "source_recovery", "value": "not allowed", "fixed": True, "status": "BLOCKED"},
    ])
    direction = pd.DataFrame([
        {"direction_id": "HD001", "required_direction": "confirm_existing_bound_source_for_audit_only_dry_run_without_source_recovery", "met_now": False, "execution_effect_now": "none", "status": "HUMAN_DIRECTION_REQUIRED"},
        {"direction_id": "HD002", "required_direction": "approve_A002_fixed_filters_for_audit_only_dry_run", "met_now": False, "execution_effect_now": "none", "status": "HUMAN_DIRECTION_REQUIRED"},
        {"direction_id": "HD003", "required_direction": "permit_fixed_condition_audit_only_dry_run_execution_without_live_or_external_actions", "met_now": False, "execution_effect_now": "none", "status": "HUMAN_DIRECTION_REQUIRED"},
    ])
    derived = pd.DataFrame([
        {"derived_gate_id": "DG001", "derived_gate": "execution_gate_open", "open_now": False, "reason": "human directions not recorded in 25C62", "status": "CLOSED"},
        {"derived_gate_id": "DG002", "derived_gate": "future_dry_run_execution_allowed", "open_now": False, "reason": "execution gate remains closed", "status": "BLOCKED"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "replay_execution", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "dry_run_execution", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B006", "boundary": "no_signal_discord_notify", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    return scope, direction, derived, boundary


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN61
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary61": input_dir / "02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json",
        "contract61": input_dir / "04_25c61_contract_audit.csv",
        "freeze61": input_dir / "05_25c61_condition_freeze_matrix.csv",
        "gate61": input_dir / "06_25c61_minimal_gate_matrix.csv",
        "decision61": input_dir / "07_25c61_fixed_condition_next_decision_matrix.csv",
        "boundary61": input_dir / "08_25c61_execution_boundary_matrix.csv",
        "next61": input_dir / "09_25c61_next_step_plan.csv",
        "notes61": input_dir / "10_25c61_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c62_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary61 = read_json(req["summary61"])
    contract61 = read_csv(req["contract61"])
    freeze61 = read_csv(req["freeze61"])
    gate61 = read_csv(req["gate61"])
    decision61 = read_csv(req["decision61"])
    boundary61 = read_csv(req["boundary61"])
    next61 = read_csv(req["next61"])
    notes61 = read_csv(req["notes61"])

    contract = contract_audit(summary61, contract61, freeze61, gate61, decision61, boundary61, next61)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary61)

    scope, direction, derived, boundary = build_matrices()
    unsafe = not scope["fixed"].apply(as_bool).all() or direction["met_now"].apply(as_bool).any() or derived["open_now"].apply(as_bool).any() or boundary["allowed_now"].apply(as_bool).any()
    if unsafe:
        return stop_outputs(out, STOP_SCOPE, input_audit, pd.concat([scope, direction, derived, boundary], ignore_index=True), summary61)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "wait for one explicit fixed-condition dry-run direction; no execution", "execution_allowed_in_25c62": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "future fixed-condition dry-run", "allowed_now": False, "purpose": "blocked until direction is explicitly provided and separately reviewed", "execution_allowed_in_25c62": False, "condition_change_allowed": False},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c62": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C62 used 25C61 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed; no signal condition was changed.", "status": "PASS"},
        {"note_id": "N003", "note": "Five minimal gates were consolidated into three human-direction items.", "status": "PASS"},
        {"note_id": "N004", "note": "No acceptance, replay, dry-run, source recovery, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c62_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c62_input_audit.csv", input_audit)
    write_csv(out / "04_25c62_contract_audit.csv", contract)
    write_csv(out / "05_25c62_fixed_condition_scope_matrix.csv", scope)
    write_csv(out / "06_25c62_human_direction_required_matrix.csv", direction)
    write_csv(out / "07_25c62_derived_gate_matrix.csv", derived)
    write_csv(out / "08_25c62_execution_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c62_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c62_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "human_direction_package_only": True,
        "input_25c61_step": summary61.get("step"),
        "input_25c61_status": summary61.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "minimal_gate_rows_inherited": 5,
        "human_direction_required_rows": int(len(direction)),
        "derived_gate_rows": int(len(derived)),
        "source_confirmed_for_execution": False,
        "a002_variant_approved": False,
        "human_dry_run_execution_approval": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "variant_approved": False,
        "replay_executed": False,
        "dry_run_executed": False,
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
    write_json(out / "02_25c62_a002_fixed_dry_run_direction_package_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C62 CoreB G1 A002 fixed dry-run direction package audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C62 consolidates the fixed-condition dry-run gates into a human-direction package. No condition change, replay, or dry-run is executed.", "",
        "## 25C61 contract audit", "", md_table(contract), "",
        "## Fixed condition scope matrix", "", md_table(scope), "",
        "## Human direction required matrix", "", md_table(direction), "",
        "## Derived gate matrix", "", md_table(derived), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 and the retained filters remain fixed. No signal condition was changed. No dry-run/replay/source recovery/live/external action was executed. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c62_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "condition_changed": False, "human_direction_required_rows": int(len(direction)), "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
