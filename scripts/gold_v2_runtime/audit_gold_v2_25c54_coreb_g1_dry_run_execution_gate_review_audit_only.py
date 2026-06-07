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

STEP = "25C54_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_READY_AUDIT_ONLY_GATE_CLOSED_ACCEPTANCE_TEMPLATE_REQUIRED"
STOP_MISSING = "25C54_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C54_STOP_25C53_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_GATE = "25C54_STOP_EXECUTION_GATE_UNSAFE_AUDIT_ONLY"
IN53 = "gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only"
OUT_DIR = "gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only"
EXPECTED_53_STEP = "25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY"
EXPECTED_53_STATUS = "COREB_G1_DRY_RUN_PREFLIGHT_SPEC_READY_AUDIT_ONLY_EXECUTION_GATE_REVIEW_REQUIRED"
EXPECTED_NEXT_IN_53 = STEP
NEXT_STEP = "25C55_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
EXPECTED_CANDIDATE_RELATIVE_PATH = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv"


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
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/02_25c53_dry_run_preflight_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/06_25c53_preflight_check_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only/01_25c54_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only/02_25c54_dry_run_execution_gate_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only/05_25c54_execution_gate_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only/09_25c54_next_step_plan.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def execution_boundary_matrix() -> pd.DataFrame:
    rows = [
        ("source_confirmed_for_execution", False, False),
        ("human_dry_run_execution_approval", False, False),
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
    return pd.DataFrame([{"boundary_id": f"B{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary53: Optional[dict] = None) -> int:
    summary53 = summary53 or {}
    write_csv(out / "00_不要_25c54_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c54_input_audit.csv", input_audit)
    write_csv(out / "04_25c54_contract_audit.csv", diag)
    write_csv(out / "05_25c54_execution_gate_matrix.csv", diag)
    write_csv(out / "06_25c54_authorization_boundary_matrix.csv", diag)
    write_csv(out / "07_25c54_risk_and_blocker_matrix.csv", diag)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C53 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "dry-run execution gate", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c54_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c54": False}])
    write_csv(out / "09_25c54_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C54 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c54_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "execution_gate_review_only": True,
        "input_25c53_step": summary53.get("step"),
        "input_25c53_status": summary53.get("status"),
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
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
    write_json(out / "02_25c54_dry_run_execution_gate_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C54 CoreB G1 dry-run execution gate review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c54_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary53: dict, contract53: pd.DataFrame, preflight_inputs: pd.DataFrame, preflight_checks: pd.DataFrame, preflight_outputs: pd.DataFrame, boundary53: pd.DataFrame, gates53: pd.DataFrame, next53: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_53_STEP,
        "status": EXPECTED_53_STATUS,
        "audit_only": True,
        "preflight_spec_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "candidate_relative_path": EXPECTED_CANDIDATE_RELATIVE_PATH,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "preflight_input_rows": 5,
        "preflight_check_rows": 8,
        "preflight_output_spec_rows": 6,
        "next_recommended_step": EXPECTED_NEXT_IN_53,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary53.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary53.get("representative_filters", [])
    rows.append({"contract_id": "C016", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary53.get(flag), "expected": False, "status": "PASS" if summary53.get(flag) is False else "STOP"})
    stop_count = int(contract53[contract53.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    row_counts_ok = len(preflight_inputs) == 5 and len(preflight_checks) == 8 and len(preflight_outputs) == 6
    blocked_checks = "BLOCKED" in preflight_checks.get("status", pd.Series(dtype=str)).astype(str).tolist()
    boundary_ok = int(boundary53[boundary53.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gates_block_exec = "BLOCKED" in gates53.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next53.empty and str(next53.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_53 and as_bool(next53.iloc[0].get("allowed_now")) and not as_bool(next53.iloc[0].get("execution_allowed_in_25c53")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C53 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "preflight row counts", "observed": f"{len(preflight_inputs)}/{len(preflight_checks)}/{len(preflight_outputs)}", "expected": "5/8/6", "status": "PASS" if row_counts_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "preflight checks contain blocked future execution", "observed": blocked_checks, "expected": True, "status": "PASS" if blocked_checks else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C53 execution boundary has no STOP", "observed": boundary_ok, "expected": True, "status": "PASS" if boundary_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C53 gates block execution", "observed": gates_block_exec, "expected": True, "status": "PASS" if gates_block_exec else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C53 next plan allows 25C54 only", "observed": next53.iloc[0].to_dict() if not next53.empty else {}, "expected": "25C54 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_gate_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    execution_gate = pd.DataFrame([
        {"gate_id": "E001", "gate": "source confirmed for execution", "required_to_open": True, "observed": False, "gate_status": "CLOSED", "blocks_execution": True},
        {"gate_id": "E002", "gate": "human dry-run execution approval", "required_to_open": True, "observed": False, "gate_status": "CLOSED", "blocks_execution": True},
        {"gate_id": "E003", "gate": "A002 variant approved", "required_to_open": True, "observed": False, "gate_status": "CLOSED", "blocks_execution": True},
        {"gate_id": "E004", "gate": "replay execution permitted", "required_to_open": True, "observed": False, "gate_status": "CLOSED", "blocks_execution": True},
        {"gate_id": "E005", "gate": "dry-run execution permitted", "required_to_open": True, "observed": False, "gate_status": "CLOSED", "blocks_execution": True},
        {"gate_id": "E006", "gate": "live/external actions permitted", "required_to_open": False, "observed": False, "gate_status": "CLOSED", "blocks_execution": False},
    ])
    auth = execution_boundary_matrix()
    risks = pd.DataFrame([
        {"risk_id": "R001", "risk": "Source bound for planning only, not execution", "severity": "HIGH", "blocker": True, "status": "BLOCKED"},
        {"risk_id": "R002", "risk": "No explicit human dry-run approval", "severity": "HIGH", "blocker": True, "status": "BLOCKED"},
        {"risk_id": "R003", "risk": "A002 remains not approved", "severity": "HIGH", "blocker": True, "status": "BLOCKED"},
        {"risk_id": "R004", "risk": "Live/external actions must remain off", "severity": "HIGH", "blocker": True, "status": "BLOCKED"},
    ])
    return execution_gate, auth, risks


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN53
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary53": input_dir / "02_25c53_dry_run_preflight_spec_summary.json",
        "contract53": input_dir / "04_25c53_contract_audit.csv",
        "preflight_inputs53": input_dir / "05_25c53_preflight_input_matrix.csv",
        "preflight_checks53": input_dir / "06_25c53_preflight_check_matrix.csv",
        "preflight_outputs53": input_dir / "07_25c53_preflight_output_spec_matrix.csv",
        "boundary53": input_dir / "08_25c53_execution_boundary_matrix.csv",
        "gates53": input_dir / "09_25c53_gates.csv",
        "next53": input_dir / "10_25c53_next_step_plan.csv",
        "notes53": input_dir / "11_25c53_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c54_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary53 = read_json(req["summary53"])
    contract53 = read_csv(req["contract53"])
    preflight_inputs = read_csv(req["preflight_inputs53"])
    preflight_checks = read_csv(req["preflight_checks53"])
    preflight_outputs = read_csv(req["preflight_outputs53"])
    boundary53 = read_csv(req["boundary53"])
    gates53 = read_csv(req["gates53"])
    next53 = read_csv(req["next53"])
    notes53 = read_csv(req["notes53"])

    contract = contract_audit(summary53, contract53, preflight_inputs, preflight_checks, preflight_outputs, boundary53, gates53, next53)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary53)

    execution_gate, auth, risks = build_gate_matrices()
    if execution_gate["gate_status"].astype(str).ne("CLOSED").any() or auth["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_GATE, input_audit, pd.concat([execution_gate, auth], ignore_index=True), summary53)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C53 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "execution gate review complete", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "execution gate open", "observed": False, "status": "GATE_CLOSED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "acceptance template may be created", "observed": True, "status": "PASS"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write dry-run execution acceptance template only; no execution", "execution_allowed_in_25c54": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until explicit acceptance after template review", "execution_allowed_in_25c54": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c54": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C54 used 25C53 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Execution gate review completed with gate closed.", "status": "GATE_CLOSED"},
        {"note_id": "N003", "note": "No dry-run/replay/source/live/external action was executed.", "status": "PASS"},
        {"note_id": "N004", "note": "Next step can create acceptance template only.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c54_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c54_input_audit.csv", input_audit)
    write_csv(out / "04_25c54_contract_audit.csv", contract)
    write_csv(out / "05_25c54_execution_gate_matrix.csv", execution_gate)
    write_csv(out / "06_25c54_authorization_boundary_matrix.csv", auth)
    write_csv(out / "07_25c54_risk_and_blocker_matrix.csv", risks)
    write_csv(out / "08_25c54_gates.csv", gates)
    write_csv(out / "09_25c54_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c54_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "execution_gate_review_only": True,
        "input_25c53_step": summary53.get("step"),
        "input_25c53_status": summary53.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "gate_closed_reason": "source_not_confirmed_for_execution_and_no_explicit_human_execution_approval",
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
    write_json(out / "02_25c54_dry_run_execution_gate_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C54 CoreB G1 dry-run execution gate review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C54 reviews the execution gate only. The gate remains closed and no dry-run/replay is executed.", "",
        "## 25C53 contract audit", "", md_table(contract), "",
        "## Execution gate matrix", "", md_table(execution_gate), "",
        "## Authorization boundary matrix", "", md_table(auth), "",
        "## Risk and blocker matrix", "", md_table(risks), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "Execution gate is closed. A002 remains NOT_APPROVED_REVIEW_ONLY. Source is still planning-only, not confirmed for execution. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c54_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "execution_gate_open": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
