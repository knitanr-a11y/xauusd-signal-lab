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

STEP = "25C61_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY"
STATUS = "COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_READY_AUDIT_ONLY_EXECUTION_BLOCKED_MINIMAL_GATES_IDENTIFIED"
STOP_MISSING = "25C61_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C61_STOP_25C60_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_FREEZE = "25C61_STOP_CONDITION_FREEZE_UNSAFE_AUDIT_ONLY"
IN60 = "gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only"
OUT_DIR = "gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only"
EXPECTED_60_STEP = "25C60_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY"
EXPECTED_60_STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_READY_AUDIT_ONLY_ALL_EXECUTION_BLOCKED"
NEXT_STEP = "WAIT_FOR_EXPLICIT_HUMAN_DIRECTION_FOR_FIXED_CONDITION_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only/02_25c60_dry_run_blocked_status_final_handoff_summary.json",
        "FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/01_25c61_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json",
        "FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/06_25c61_minimal_gate_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/07_25c61_fixed_condition_next_decision_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary60: Optional[dict] = None) -> int:
    summary60 = summary60 or {}
    write_csv(out / "00_不要_25c61_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c61_input_audit.csv", input_audit)
    write_csv(out / "04_25c61_contract_audit.csv", diag)
    write_csv(out / "05_25c61_condition_freeze_matrix.csv", diag)
    write_csv(out / "06_25c61_minimal_gate_matrix.csv", diag)
    write_csv(out / "07_25c61_fixed_condition_next_decision_matrix.csv", diag)
    write_csv(out / "08_25c61_execution_boundary_matrix.csv", diag)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c61": False}])
    write_csv(out / "09_25c61_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C61 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No condition change, replay, dry-run, source recovery, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c61_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "integrated_minimal_gate_review_only": True,
        "input_25c60_step": summary60.get("step"),
        "input_25c60_status": summary60.get("status"),
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
    write_json(out / "02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C61 CoreB G1 A002 fixed dry-run minimal gate integrated audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No condition change or dry-run/external action was performed.",
    ])
    lp(out / "01_25c61_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "condition_changed": False, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary60: dict, contract60: pd.DataFrame, final_status60: pd.DataFrame, blocked60: pd.DataFrame, guard60: pd.DataFrame, gates60: pd.DataFrame, next60: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_60_STEP,
        "status": EXPECTED_60_STATUS,
        "audit_only": True,
        "final_handoff_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "execution_remains_blocked": True,
        "acceptance_recorded": False,
        "required_literal_present": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "next_recommended_step": "WAIT_FOR_EXPLICIT_HUMAN_INSTRUCTION_AUDIT_ONLY",
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary60.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary60.get("representative_filters", [])
    rows.append({"contract_id": "C017", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary60.get(flag), "expected": False, "status": "PASS" if summary60.get(flag) is False else "STOP"})
    stop_count = int(contract60[contract60.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    final_status_ok = len(final_status60) == 8 and "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY" in final_status60.get("value", pd.Series(dtype=str)).astype(str).tolist()
    blocked_ok = len(blocked60) == 10 and not blocked60.get("allowed_now", pd.Series(dtype=bool)).apply(as_bool).any()
    guard_ok = len(guard60) == 5 and guard60.get("status", pd.Series(dtype=str)).astype(str).eq("ACTIVE").all()
    gates_ok = "NO_EXECUTION_ALLOWED" in gates60.get("status", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in gates60.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next60.empty and str(next60.iloc[0].get("next_step")) == "WAIT_FOR_EXPLICIT_HUMAN_INSTRUCTION_AUDIT_ONLY" and as_bool(next60.iloc[0].get("allowed_now")) and not as_bool(next60.iloc[0].get("execution_allowed_in_25c60")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C60 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C60 final status safe", "observed": final_status_ok, "expected": True, "status": "PASS" if final_status_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C60 blocked execution rows not allowed", "observed": blocked_ok, "expected": True, "status": "PASS" if blocked_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C60 guardrails active", "observed": guard_ok, "expected": True, "status": "PASS" if guard_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C60 gates show no execution", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C60 next plan waits for human instruction only", "observed": next60.iloc[0].to_dict() if not next60.empty else {}, "expected": "WAIT_FOR_EXPLICIT_HUMAN_INSTRUCTION_AUDIT_ONLY and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_condition_freeze(summary60: dict) -> pd.DataFrame:
    rows = [
        ("variant_code_fixed", summary60.get("representative_variant_code"), "A002", True),
        ("filter_1_fixed", EXPECTED_FILTERS[0], EXPECTED_FILTERS[0], True),
        ("filter_2_fixed", EXPECTED_FILTERS[1], EXPECTED_FILTERS[1], True),
        ("condition_changed", summary60.get("condition_changed"), False, summary60.get("condition_changed") is False),
        ("source_recovery_executed", summary60.get("source_recovery_executed"), False, summary60.get("source_recovery_executed") is False),
        ("source_mutation_executed", summary60.get("source_mutation_executed"), False, summary60.get("source_mutation_executed") is False),
    ]
    return pd.DataFrame([{"freeze_id": f"CF{i+1:03d}", "check": c, "observed": o, "expected": e, "status": "PASS" if ok else "STOP"} for i, (c, o, e, ok) in enumerate(rows)])


def build_gate_and_decision_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    minimal_gate = pd.DataFrame([
        {"gate_id": "MG001", "gate": "source_confirmed_for_execution", "satisfied_now": False, "blocks_future_dry_run": True, "status": "BLOCKED_NOT_STOP"},
        {"gate_id": "MG002", "gate": "A002_variant_approval", "satisfied_now": False, "blocks_future_dry_run": True, "status": "BLOCKED_NOT_STOP"},
        {"gate_id": "MG003", "gate": "human_dry_run_execution_approval", "satisfied_now": False, "blocks_future_dry_run": True, "status": "BLOCKED_NOT_STOP"},
        {"gate_id": "MG004", "gate": "execution_gate_open", "satisfied_now": False, "blocks_future_dry_run": True, "status": "BLOCKED_NOT_STOP"},
        {"gate_id": "MG005", "gate": "future_dry_run_execution_allowed", "satisfied_now": False, "blocks_future_dry_run": True, "status": "BLOCKED_NOT_STOP"},
    ])
    next_decision = pd.DataFrame([
        {"decision_id": "D001", "decision": "keep_A002_filters_fixed", "required": True, "met_now": True, "status": "READY_AUDIT_ONLY"},
        {"decision_id": "D002", "decision": "review_source_confirmation_without_recovery", "required": True, "met_now": False, "status": "NEEDS_HUMAN_DIRECTION"},
        {"decision_id": "D003", "decision": "review_A002_approval_scope", "required": True, "met_now": False, "status": "NEEDS_HUMAN_DIRECTION"},
        {"decision_id": "D004", "decision": "review_audit_only_dry_run_permission", "required": True, "met_now": False, "status": "NEEDS_HUMAN_DIRECTION"},
        {"decision_id": "D005", "decision": "do_not_change_signal_conditions", "required": True, "met_now": True, "status": "READY_AUDIT_ONLY"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "replay_execution", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "dry_run_execution", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B006", "boundary": "no_signal_discord_notify", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    return minimal_gate, next_decision, boundary


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN60
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary60": input_dir / "02_25c60_dry_run_blocked_status_final_handoff_summary.json",
        "contract60": input_dir / "04_25c60_contract_audit.csv",
        "final_status60": input_dir / "05_25c60_final_handoff_status_matrix.csv",
        "blocked60": input_dir / "06_25c60_final_blocked_execution_matrix.csv",
        "guard60": input_dir / "07_25c60_final_guardrail_matrix.csv",
        "gates60": input_dir / "08_25c60_gates.csv",
        "next60": input_dir / "09_25c60_next_step_plan.csv",
        "notes60": input_dir / "10_25c60_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c61_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary60 = read_json(req["summary60"])
    contract60 = read_csv(req["contract60"])
    final_status60 = read_csv(req["final_status60"])
    blocked60 = read_csv(req["blocked60"])
    guard60 = read_csv(req["guard60"])
    gates60 = read_csv(req["gates60"])
    next60 = read_csv(req["next60"])
    notes60 = read_csv(req["notes60"])

    contract = contract_audit(summary60, contract60, final_status60, blocked60, guard60, gates60, next60)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary60)

    freeze = build_condition_freeze(summary60)
    if freeze["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_FREEZE, input_audit, freeze, summary60)

    minimal_gate, next_decision, boundary = build_gate_and_decision_matrices()
    write_csv(out / "00_不要_25c61_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c61_input_audit.csv", input_audit)
    write_csv(out / "04_25c61_contract_audit.csv", contract)
    write_csv(out / "05_25c61_condition_freeze_matrix.csv", freeze)
    write_csv(out / "06_25c61_minimal_gate_matrix.csv", minimal_gate)
    write_csv(out / "07_25c61_fixed_condition_next_decision_matrix.csv", next_decision)
    write_csv(out / "08_25c61_execution_boundary_matrix.csv", boundary)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "human chooses next fixed-condition audit-only branch; no execution", "execution_allowed_in_25c61": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "future fixed-condition dry-run", "allowed_now": False, "purpose": "blocked by minimal gates; conditions must remain fixed", "execution_allowed_in_25c61": False, "condition_change_allowed": False},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c61": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C61 used 25C60 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed; no signal condition was changed.", "status": "PASS"},
        {"note_id": "N003", "note": "Minimal gates for any future audit-only dry-run were identified in one integrated step.", "status": "PASS"},
        {"note_id": "N004", "note": "No acceptance, replay, dry-run, source recovery, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
    ])
    write_csv(out / "09_25c61_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c61_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "integrated_minimal_gate_review_only": True,
        "input_25c60_step": summary60.get("step"),
        "input_25c60_status": summary60.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "minimal_gate_rows": int(len(minimal_gate)),
        "minimal_gates_blocking_future_dry_run": int(minimal_gate["blocks_future_dry_run"].apply(as_bool).sum()),
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
    write_json(out / "02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C61 CoreB G1 A002 fixed dry-run minimal gate integrated audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C61 identifies the minimal gates for a future fixed-condition audit-only dry-run. No condition change, replay, or dry-run is executed.", "",
        "## 25C60 contract audit", "", md_table(contract), "",
        "## Condition freeze matrix", "", md_table(freeze), "",
        "## Minimal gate matrix", "", md_table(minimal_gate), "",
        "## Fixed-condition next decision matrix", "", md_table(next_decision), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 and the retained filters remain fixed. No signal condition was changed. No dry-run/replay/source recovery/live/external action was executed. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c61_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "condition_changed": False, "minimal_gates_blocking_future_dry_run": int(minimal_gate["blocks_future_dry_run"].apply(as_bool).sum()), "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
