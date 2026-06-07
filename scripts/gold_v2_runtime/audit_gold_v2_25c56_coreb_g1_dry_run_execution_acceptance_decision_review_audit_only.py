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

STEP = "25C56_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_READY_AUDIT_ONLY_NO_ACCEPTANCE_GATE_CLOSED"
STOP_MISSING = "25C56_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C56_STOP_25C55_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_REVIEW = "25C56_STOP_DECISION_REVIEW_UNSAFE_AUDIT_ONLY"
IN55 = "gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only"
OUT_DIR = "gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only"
EXPECTED_55_STEP = "25C55_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY"
EXPECTED_55_STATUS = "COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_READY_AUDIT_ONLY_NO_ACCEPTANCE_RECORDED"
EXPECTED_NEXT_IN_55 = STEP
NEXT_STEP = "25C57_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/02_25c55_dry_run_execution_acceptance_template_summary.json",
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/05_25c55_acceptance_template.csv",
        "FX_OUTPUTS/gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only/01_25c56_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only/02_25c56_dry_run_execution_acceptance_decision_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only/05_25c56_decision_review_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def authorization_boundary_matrix() -> pd.DataFrame:
    rows = [
        "acceptance_recorded",
        "execution_gate_open",
        "source_confirmed_for_execution",
        "human_dry_run_execution_approval",
        "variant_approval",
        "replay_execution",
        "dry_run_execution",
        "condition_change",
        "source_change_or_recovery",
        "coreb_live_evaluator_unblock",
        "discord_notification",
        "mt5_order",
        "ai_api_call",
        "live_hook",
        "final_signal",
        "no_signal_discord_notify",
    ]
    return pd.DataFrame([{"boundary_id": f"B{i+1:03d}", "boundary": b, "allowed": False, "observed": False, "status": "PASS"} for i, b in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary55: Optional[dict] = None) -> int:
    summary55 = summary55 or {}
    write_csv(out / "00_不要_25c56_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c56_input_audit.csv", input_audit)
    write_csv(out / "04_25c56_contract_audit.csv", diag)
    write_csv(out / "05_25c56_decision_review_matrix.csv", diag)
    write_csv(out / "06_25c56_literal_presence_review.csv", diag)
    auth = authorization_boundary_matrix()
    write_csv(out / "07_25c56_authorization_boundary_matrix.csv", auth)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C55 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "decision marker review", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c56_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c56": False}])
    write_csv(out / "09_25c56_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C56 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c56_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "decision_review_only": True,
        "input_25c55_step": summary55.get("step"),
        "input_25c55_status": summary55.get("status"),
        "acceptance_recorded": False,
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
    write_json(out / "02_25c56_dry_run_execution_acceptance_decision_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C56 CoreB G1 dry-run execution acceptance decision review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No acceptance or dry-run/external action was performed.",
    ])
    lp(out / "01_25c56_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary55: dict, contract55: pd.DataFrame, template55: pd.DataFrame, literals55: pd.DataFrame, auth55: pd.DataFrame, gates55: pd.DataFrame, next55: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_55_STEP,
        "status": EXPECTED_55_STATUS,
        "audit_only": True,
        "acceptance_template_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "acceptance_template_rows": 9,
        "required_literal_rows": 9,
        "acceptance_recorded": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_55,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary55.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary55.get("representative_filters", [])
    rows.append({"contract_id": "C017", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary55.get(flag), "expected": False, "status": "PASS" if summary55.get(flag) is False else "STOP"})
    stop_count = int(contract55[contract55.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    template_ok = len(template55) == 9 and not template55.get("accepted_now", pd.Series(dtype=bool)).apply(as_bool).any() and not template55.get("recorded_in_25c55", pd.Series(dtype=bool)).apply(as_bool).any()
    literals_ok = len(literals55) == 9 and not literals55.get("present_now", pd.Series(dtype=bool)).apply(as_bool).any()
    auth_ok = int(auth55[auth55.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gates_ok = "NO_ACCEPTANCE_RECORDED" in gates55.get("status", pd.Series(dtype=str)).astype(str).tolist() and "GATE_CLOSED" in gates55.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next55.empty and str(next55.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_55 and as_bool(next55.iloc[0].get("allowed_now")) and not as_bool(next55.iloc[0].get("execution_allowed_in_25c55")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C55 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "template has no accepted or recorded rows", "observed": template_ok, "expected": True, "status": "PASS" if template_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "literal matrix has no present rows", "observed": literals_ok, "expected": True, "status": "PASS" if literals_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C55 authorization boundaries safe", "observed": auth_ok, "expected": True, "status": "PASS" if auth_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C55 gates keep no acceptance/gate closed", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C55 next plan allows 25C56 only", "observed": next55.iloc[0].to_dict() if not next55.empty else {}, "expected": "25C56 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_reviews(template: pd.DataFrame, literals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    decision = template.copy()
    decision["accepted_now_bool"] = decision["accepted_now"].apply(as_bool)
    decision["recorded_now_bool"] = decision["recorded_in_25c55"].apply(as_bool)
    decision["review_status"] = decision.apply(lambda r: "NO_DECISION_MARKER_PRESENT" if not r["accepted_now_bool"] and not r["recorded_now_bool"] else "STOP", axis=1)
    literal = literals.copy()
    literal["present_now_bool"] = literal["present_now"].apply(as_bool)
    literal["review_status"] = literal["present_now_bool"].apply(lambda x: "NO_LITERAL_PRESENT" if not x else "STOP")
    return decision, literal


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN55
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary55": input_dir / "02_25c55_dry_run_execution_acceptance_template_summary.json",
        "contract55": input_dir / "04_25c55_contract_audit.csv",
        "template55": input_dir / "05_25c55_acceptance_template.csv",
        "literals55": input_dir / "06_25c55_required_literal_matrix.csv",
        "auth55": input_dir / "07_25c55_authorization_boundary_matrix.csv",
        "gates55": input_dir / "08_25c55_gates.csv",
        "next55": input_dir / "09_25c55_next_step_plan.csv",
        "notes55": input_dir / "10_25c55_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c56_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary55 = read_json(req["summary55"])
    contract55 = read_csv(req["contract55"])
    template55 = read_csv(req["template55"])
    literals55 = read_csv(req["literals55"])
    auth55 = read_csv(req["auth55"])
    gates55 = read_csv(req["gates55"])
    next55 = read_csv(req["next55"])
    notes55 = read_csv(req["notes55"])

    contract = contract_audit(summary55, contract55, template55, literals55, auth55, gates55, next55)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary55)

    decision_review, literal_review = build_reviews(template55, literals55)
    unsafe = decision_review["review_status"].astype(str).eq("STOP").any() or literal_review["review_status"].astype(str).eq("STOP").any()
    if unsafe:
        return stop_outputs(out, STOP_REVIEW, input_audit, pd.concat([decision_review, literal_review], ignore_index=True), summary55)

    auth = authorization_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C55 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "decision markers present", "observed": False, "status": "NO_ACCEPTANCE_RECORDED"},
        {"gate_id": "G003", "gate": "execution gate open", "observed": False, "status": "GATE_CLOSED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "finalize current blockers only; no execution", "execution_allowed_in_25c56": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked; no acceptance marker found", "execution_allowed_in_25c56": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c56": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C56 used 25C55 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "No decision marker or required literal is present.", "status": "NO_ACCEPTANCE_RECORDED"},
        {"note_id": "N003", "note": "Execution gate remains closed and dry-run execution remains blocked.", "status": "GATE_CLOSED"},
        {"note_id": "N004", "note": "No live/external action was executed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c56_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c56_input_audit.csv", input_audit)
    write_csv(out / "04_25c56_contract_audit.csv", contract)
    write_csv(out / "05_25c56_decision_review_matrix.csv", decision_review)
    write_csv(out / "06_25c56_literal_presence_review.csv", literal_review)
    write_csv(out / "07_25c56_authorization_boundary_matrix.csv", auth)
    write_csv(out / "08_25c56_gates.csv", gates)
    write_csv(out / "09_25c56_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c56_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "decision_review_only": True,
        "input_25c55_step": summary55.get("step"),
        "input_25c55_status": summary55.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "decision_review_rows": int(len(decision_review)),
        "literal_review_rows": int(len(literal_review)),
        "acceptance_recorded": False,
        "required_literal_present": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
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
    write_json(out / "02_25c56_dry_run_execution_acceptance_decision_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C56 CoreB G1 dry-run execution acceptance decision review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C56 reviews whether any decision marker is present. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C55 contract audit", "", md_table(contract), "",
        "## Decision review matrix", "", md_table(decision_review), "",
        "## Literal presence review", "", md_table(literal_review), "",
        "## Authorization boundary matrix", "", md_table(auth), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "No acceptance or required literal is present. Execution gate is closed. A002 remains NOT_APPROVED_REVIEW_ONLY. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c56_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "acceptance_recorded": False, "required_literal_present": False, "execution_gate_open": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
