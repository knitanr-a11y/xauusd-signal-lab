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

STEP = "25C55_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_READY_AUDIT_ONLY_NO_ACCEPTANCE_RECORDED"
STOP_MISSING = "25C55_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C55_STOP_25C54_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_TEMPLATE = "25C55_STOP_ACCEPTANCE_TEMPLATE_UNSAFE_AUDIT_ONLY"
IN54 = "gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only"
OUT_DIR = "gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only"
EXPECTED_54_STEP = "25C54_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY"
EXPECTED_54_STATUS = "COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_READY_AUDIT_ONLY_GATE_CLOSED_ACCEPTANCE_TEMPLATE_REQUIRED"
EXPECTED_NEXT_IN_54 = STEP
NEXT_STEP = "25C56_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_DECISION_REVIEW_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
GATE_CLOSED_REASON = "source_not_confirmed_for_execution_and_no_explicit_human_execution_approval"
TEMPLATE_ITEMS = [
    "source_confirmed_for_execution",
    "human_dry_run_execution_approval",
    "A002_variant_approval",
    "replay_execution_boundary",
    "dry_run_execution_boundary",
    "source_change_or_recovery_boundary",
    "live_external_boundary",
    "AI_Discord_MT5_live_hook_final_signal_boundary",
    "NO_SIGNAL_Discord_notification_boundary",
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
        "FX_OUTPUTS/gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only/02_25c54_dry_run_execution_gate_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/01_25c55_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/02_25c55_dry_run_execution_acceptance_template_summary.json",
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/05_25c55_acceptance_template.csv",
        "FX_OUTPUTS/gold_v2_25c55_coreb_g1_dry_run_execution_acceptance_template_audit_only/06_25c55_required_literal_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def authorization_boundary_matrix() -> pd.DataFrame:
    rows = [
        "source_confirmed_for_execution",
        "human_dry_run_execution_approval",
        "execution_gate_open",
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


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary54: Optional[dict] = None) -> int:
    summary54 = summary54 or {}
    write_csv(out / "00_不要_25c55_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c55_input_audit.csv", input_audit)
    write_csv(out / "04_25c55_contract_audit.csv", diag)
    write_csv(out / "05_25c55_acceptance_template.csv", diag)
    write_csv(out / "06_25c55_required_literal_matrix.csv", diag)
    auth = authorization_boundary_matrix()
    write_csv(out / "07_25c55_authorization_boundary_matrix.csv", auth)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C54 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "acceptance recorded", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c55_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c55": False}])
    write_csv(out / "09_25c55_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C55 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c55_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "acceptance_template_only": True,
        "input_25c54_step": summary54.get("step"),
        "input_25c54_status": summary54.get("status"),
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
    write_json(out / "02_25c55_dry_run_execution_acceptance_template_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C55 CoreB G1 dry-run execution acceptance template audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No acceptance or dry-run/external action was performed.",
    ])
    lp(out / "01_25c55_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary54: dict, contract54: pd.DataFrame, gate54: pd.DataFrame, auth54: pd.DataFrame, risk54: pd.DataFrame, gates54: pd.DataFrame, next54: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_54_STEP,
        "status": EXPECTED_54_STATUS,
        "audit_only": True,
        "execution_gate_review_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "gate_closed_reason": GATE_CLOSED_REASON,
        "next_recommended_step": EXPECTED_NEXT_IN_54,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary54.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary54.get("representative_filters", [])
    rows.append({"contract_id": "C015", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary54.get(flag), "expected": False, "status": "PASS" if summary54.get(flag) is False else "STOP"})
    stop_count = int(contract54[contract54.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    gate_all_closed = (not gate54.empty and gate54.get("gate_status", pd.Series(dtype=str)).astype(str).eq("CLOSED").all())
    auth_ok = int(auth54[auth54.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    blockers_ok = (not risk54.empty and risk54.get("status", pd.Series(dtype=str)).astype(str).eq("BLOCKED").all())
    gates_closed = "GATE_CLOSED" in gates54.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next54.empty and str(next54.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_54 and as_bool(next54.iloc[0].get("allowed_now")) and not as_bool(next54.iloc[0].get("execution_allowed_in_25c54")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C54 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C54 execution gates all closed", "observed": gate_all_closed, "expected": True, "status": "PASS" if gate_all_closed else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C54 authorization boundaries safe", "observed": auth_ok, "expected": True, "status": "PASS" if auth_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C54 risk blockers remain blocked", "observed": blockers_ok, "expected": True, "status": "PASS" if blockers_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C54 gates include gate closed", "observed": gates_closed, "expected": True, "status": "PASS" if gates_closed else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C54 next plan allows 25C55 only", "observed": next54.iloc[0].to_dict() if not next54.empty else {}, "expected": "25C55 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_template() -> tuple[pd.DataFrame, pd.DataFrame]:
    template = pd.DataFrame([
        {
            "template_id": f"A{i+1:03d}",
            "decision_item": item,
            "required_literal_if_later_accepted": f"ACCEPT_{item}",
            "accepted_now": False,
            "recorded_in_25c55": False,
            "default_status": "NOT_ACCEPTED_TEMPLATE_ONLY",
        }
        for i, item in enumerate(TEMPLATE_ITEMS)
    ])
    literals = pd.DataFrame([
        {"literal_id": f"L{i+1:03d}", "decision_item": item, "required_literal": f"ACCEPT_{item}", "present_now": False, "status": "TEMPLATE_ONLY_NOT_PRESENT"}
        for i, item in enumerate(TEMPLATE_ITEMS)
    ])
    return template, literals


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN54
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary54": input_dir / "02_25c54_dry_run_execution_gate_review_summary.json",
        "contract54": input_dir / "04_25c54_contract_audit.csv",
        "gate54": input_dir / "05_25c54_execution_gate_matrix.csv",
        "auth54": input_dir / "06_25c54_authorization_boundary_matrix.csv",
        "risk54": input_dir / "07_25c54_risk_and_blocker_matrix.csv",
        "gates54": input_dir / "08_25c54_gates.csv",
        "next54": input_dir / "09_25c54_next_step_plan.csv",
        "notes54": input_dir / "10_25c54_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c55_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary54 = read_json(req["summary54"])
    contract54 = read_csv(req["contract54"])
    gate54 = read_csv(req["gate54"])
    auth54 = read_csv(req["auth54"])
    risk54 = read_csv(req["risk54"])
    gates54 = read_csv(req["gates54"])
    next54 = read_csv(req["next54"])
    notes54 = read_csv(req["notes54"])

    contract = contract_audit(summary54, contract54, gate54, auth54, risk54, gates54, next54)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary54)

    template, literals = build_template()
    if template["accepted_now"].apply(as_bool).any() or literals["present_now"].apply(as_bool).any():
        return stop_outputs(out, STOP_TEMPLATE, input_audit, pd.concat([template, literals], ignore_index=True), summary54)

    auth = authorization_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C54 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "acceptance template created", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "acceptance recorded", "observed": False, "status": "NO_ACCEPTANCE_RECORDED"},
        {"gate_id": "G004", "gate": "execution gate open", "observed": False, "status": "GATE_CLOSED"},
        {"gate_id": "G005", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "review future acceptance decision only; no execution", "execution_allowed_in_25c55": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until explicit acceptance review and later execution boundary change", "execution_allowed_in_25c55": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c55": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C55 used 25C54 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Acceptance template was created only; no acceptance was recorded.", "status": "NO_ACCEPTANCE_RECORDED"},
        {"note_id": "N003", "note": "Execution gate remains closed and dry-run execution remains blocked.", "status": "GATE_CLOSED"},
        {"note_id": "N004", "note": "No live/external action was executed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c55_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c55_input_audit.csv", input_audit)
    write_csv(out / "04_25c55_contract_audit.csv", contract)
    write_csv(out / "05_25c55_acceptance_template.csv", template)
    write_csv(out / "06_25c55_required_literal_matrix.csv", literals)
    write_csv(out / "07_25c55_authorization_boundary_matrix.csv", auth)
    write_csv(out / "08_25c55_gates.csv", gates)
    write_csv(out / "09_25c55_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c55_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "acceptance_template_only": True,
        "input_25c54_step": summary54.get("step"),
        "input_25c54_status": summary54.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "acceptance_template_rows": int(len(template)),
        "required_literal_rows": int(len(literals)),
        "acceptance_recorded": False,
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
    write_json(out / "02_25c55_dry_run_execution_acceptance_template_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C55 CoreB G1 dry-run execution acceptance template audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C55 writes a future decision template only. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C54 contract audit", "", md_table(contract), "",
        "## Acceptance template", "", md_table(template), "",
        "## Required literal matrix", "", md_table(literals), "",
        "## Authorization boundary matrix", "", md_table(auth), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "No acceptance was recorded. Execution gate is closed. A002 remains NOT_APPROVED_REVIEW_ONLY. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c55_GOLD_V2_COREB_G1_DRY_RUN_EXECUTION_ACCEPTANCE_TEMPLATE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "acceptance_recorded": False, "execution_gate_open": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
