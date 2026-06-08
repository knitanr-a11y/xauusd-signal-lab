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

STEP = "25C57_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_READY_AUDIT_ONLY_EXECUTION_REMAINS_BLOCKED"
STOP_MISSING = "25C57_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C57_STOP_25C56_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_BLOCKER = "25C57_STOP_BLOCKER_FINALIZATION_UNSAFE_AUDIT_ONLY"
IN56 = "gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only"
OUT_DIR = "gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only"
EXPECTED_56_STEP = "25C56_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY"
EXPECTED_56_STATUS = "COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_READY_AUDIT_ONLY_NO_ACCEPTANCE_GATE_CLOSED"
EXPECTED_NEXT_IN_56 = STEP
NEXT_STEP = "25C58_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only/02_25c56_dry_run_execution_acceptance_decision_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only/01_25c57_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only/02_25c57_dry_run_execution_blocker_finalization_summary.json",
        "FX_OUTPUTS/gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only/05_25c57_active_blocker_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only/09_25c57_next_step_plan.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary56: Optional[dict] = None) -> int:
    summary56 = summary56 or {}
    write_csv(out / "00_不要_25c57_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c57_input_audit.csv", input_audit)
    write_csv(out / "04_25c57_contract_audit.csv", diag)
    write_csv(out / "05_25c57_active_blocker_matrix.csv", diag)
    write_csv(out / "06_25c57_closed_gate_matrix.csv", diag)
    write_csv(out / "07_25c57_audit_only_status_matrix.csv", diag)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C56 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "blocker finalization", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c57_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c57": False}])
    write_csv(out / "09_25c57_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C57 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c57_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocker_finalization_only": True,
        "input_25c56_step": summary56.get("step"),
        "input_25c56_status": summary56.get("status"),
        "execution_remains_blocked": True,
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
    write_json(out / "02_25c57_dry_run_execution_blocker_finalization_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C57 CoreB G1 dry-run execution blocker finalization audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No acceptance or dry-run/external action was performed.",
    ])
    lp(out / "01_25c57_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary56: dict, contract56: pd.DataFrame, decision56: pd.DataFrame, literal56: pd.DataFrame, auth56: pd.DataFrame, gates56: pd.DataFrame, next56: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_56_STEP,
        "status": EXPECTED_56_STATUS,
        "audit_only": True,
        "decision_review_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "decision_review_rows": 9,
        "literal_review_rows": 9,
        "acceptance_recorded": False,
        "required_literal_present": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_56,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary56.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary56.get("representative_filters", [])
    rows.append({"contract_id": "C018", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary56.get(flag), "expected": False, "status": "PASS" if summary56.get(flag) is False else "STOP"})
    stop_count = int(contract56[contract56.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    decision_ok = len(decision56) == 9 and decision56.get("review_status", pd.Series(dtype=str)).astype(str).eq("NO_DECISION_MARKER_PRESENT").all()
    literal_ok = len(literal56) == 9 and literal56.get("review_status", pd.Series(dtype=str)).astype(str).eq("NO_LITERAL_PRESENT").all()
    auth_ok = int(auth56[auth56.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gates_ok = "NO_ACCEPTANCE_RECORDED" in gates56.get("status", pd.Series(dtype=str)).astype(str).tolist() and "GATE_CLOSED" in gates56.get("status", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in gates56.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next56.empty and str(next56.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_56 and as_bool(next56.iloc[0].get("allowed_now")) and not as_bool(next56.iloc[0].get("execution_allowed_in_25c56")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C56 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "decision review confirms no markers", "observed": decision_ok, "expected": True, "status": "PASS" if decision_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "literal review confirms no literals", "observed": literal_ok, "expected": True, "status": "PASS" if literal_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C56 authorization boundaries safe", "observed": auth_ok, "expected": True, "status": "PASS" if auth_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C56 gates keep no acceptance/gate closed/blocked", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C56 next plan allows 25C57 only", "observed": next56.iloc[0].to_dict() if not next56.empty else {}, "expected": "25C57 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_finalization_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    blockers = [
        ("source_not_confirmed_for_execution", "Source is still planning-only."),
        ("human_acceptance_not_recorded", "No acceptance marker or required literal is present."),
        ("required_literals_absent", "All required literal rows remain absent."),
        ("execution_gate_closed", "Execution gate remains closed."),
        ("a002_not_approved", "A002 remains NOT_APPROVED_REVIEW_ONLY."),
        ("future_dry_run_execution_blocked", "Future dry-run execution is blocked."),
        ("replay_execution_blocked", "Replay execution is blocked."),
        ("source_change_recovery_blocked", "Source change/recovery remains blocked."),
        ("live_external_actions_blocked", "Live/external/AI/notification/order/final paths remain blocked."),
        ("no_signal_discord_notify_blocked", "NO_SIGNAL Discord notification remains disabled."),
    ]
    active = pd.DataFrame([
        {"blocker_id": f"BK{i+1:03d}", "blocker": b, "description": d, "active": True, "status": "ACTIVE_BLOCKER"}
        for i, (b, d) in enumerate(blockers)
    ])
    gates = pd.DataFrame([
        {"closed_gate_id": "CG001", "gate": "acceptance_recorded", "open": False, "status": "CLOSED"},
        {"closed_gate_id": "CG002", "gate": "source_confirmed_for_execution", "open": False, "status": "CLOSED"},
        {"closed_gate_id": "CG003", "gate": "execution_gate_open", "open": False, "status": "CLOSED"},
        {"closed_gate_id": "CG004", "gate": "future_dry_run_execution", "open": False, "status": "CLOSED"},
        {"closed_gate_id": "CG005", "gate": "live_external_actions", "open": False, "status": "CLOSED"},
    ])
    audit_status = pd.DataFrame([
        {"status_id": "AS001", "item": "GOLD_V2_mode", "value": "audit_only", "status": "PASS"},
        {"status_id": "AS002", "item": "A002_approval", "value": "NOT_APPROVED_REVIEW_ONLY", "status": "PASS"},
        {"status_id": "AS003", "item": "source_binding", "value": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY", "status": "PASS"},
        {"status_id": "AS004", "item": "dry_run_execution", "value": "blocked", "status": "BLOCKED"},
        {"status_id": "AS005", "item": "live_external_actions", "value": "blocked", "status": "BLOCKED"},
    ])
    return active, gates, audit_status


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN56
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary56": input_dir / "02_25c56_dry_run_execution_acceptance_decision_review_summary.json",
        "contract56": input_dir / "04_25c56_contract_audit.csv",
        "decision56": input_dir / "05_25c56_decision_review_matrix.csv",
        "literal56": input_dir / "06_25c56_literal_presence_review.csv",
        "auth56": input_dir / "07_25c56_authorization_boundary_matrix.csv",
        "gates56": input_dir / "08_25c56_gates.csv",
        "next56": input_dir / "09_25c56_next_step_plan.csv",
        "notes56": input_dir / "10_25c56_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c57_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary56 = read_json(req["summary56"])
    contract56 = read_csv(req["contract56"])
    decision56 = read_csv(req["decision56"])
    literal56 = read_csv(req["literal56"])
    auth56 = read_csv(req["auth56"])
    gates56 = read_csv(req["gates56"])
    next56 = read_csv(req["next56"])
    notes56 = read_csv(req["notes56"])

    contract = contract_audit(summary56, contract56, decision56, literal56, auth56, gates56, next56)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary56)

    active_blockers, closed_gates, audit_status = build_finalization_matrices()
    if not active_blockers["active"].apply(as_bool).all() or not closed_gates["open"].apply(lambda x: not as_bool(x)).all():
        return stop_outputs(out, STOP_BLOCKER, input_audit, pd.concat([active_blockers, closed_gates], ignore_index=True), summary56)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C56 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "active blockers finalized", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "execution remains blocked", "observed": True, "status": "EXECUTION_REMAINS_BLOCKED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write blocked-status handoff only; no execution", "execution_allowed_in_25c57": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked; finalized blockers remain active", "execution_allowed_in_25c57": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c57": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C57 used 25C56 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "All current execution blockers remain active.", "status": "EXECUTION_REMAINS_BLOCKED"},
        {"note_id": "N003", "note": "No acceptance, replay, dry-run, source, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
        {"note_id": "N004", "note": "Next step can write blocked-status handoff only.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c57_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c57_input_audit.csv", input_audit)
    write_csv(out / "04_25c57_contract_audit.csv", contract)
    write_csv(out / "05_25c57_active_blocker_matrix.csv", active_blockers)
    write_csv(out / "06_25c57_closed_gate_matrix.csv", closed_gates)
    write_csv(out / "07_25c57_audit_only_status_matrix.csv", audit_status)
    write_csv(out / "08_25c57_gates.csv", gates)
    write_csv(out / "09_25c57_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c57_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "blocker_finalization_only": True,
        "input_25c56_step": summary56.get("step"),
        "input_25c56_status": summary56.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "active_blocker_rows": int(len(active_blockers)),
        "closed_gate_rows": int(len(closed_gates)),
        "execution_remains_blocked": True,
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
    write_json(out / "02_25c57_dry_run_execution_blocker_finalization_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C57 CoreB G1 dry-run execution blocker finalization audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C57 finalizes current blockers only. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C56 contract audit", "", md_table(contract), "",
        "## Active blocker matrix", "", md_table(active_blockers), "",
        "## Closed gate matrix", "", md_table(closed_gates), "",
        "## Audit-only status matrix", "", md_table(audit_status), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "Execution remains blocked. No acceptance or required literal is present. A002 remains NOT_APPROVED_REVIEW_ONLY. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c57_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "execution_remains_blocked": True, "active_blocker_rows": len(active_blockers), "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
