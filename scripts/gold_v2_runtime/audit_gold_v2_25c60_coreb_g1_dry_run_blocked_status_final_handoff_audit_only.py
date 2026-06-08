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

STEP = "25C60_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_READY_AUDIT_ONLY_ALL_EXECUTION_BLOCKED"
STOP_MISSING = "25C60_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C60_STOP_25C59_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_HANDOFF = "25C60_STOP_FINAL_HANDOFF_UNSAFE_AUDIT_ONLY"
IN59 = "gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only"
OUT_DIR = "gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only"
EXPECTED_59_STEP = "25C59_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY"
EXPECTED_59_STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_READY_AUDIT_ONLY_NO_EXECUTION_ALLOWED"
EXPECTED_NEXT_IN_59 = STEP
NEXT_STEP = "WAIT_FOR_EXPLICIT_HUMAN_INSTRUCTION_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only/02_25c59_dry_run_blocked_status_roadmap_summary.json",
        "FX_OUTPUTS/gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only/01_25c60_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only/02_25c60_dry_run_blocked_status_final_handoff_summary.json",
        "FX_OUTPUTS/gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only/05_25c60_final_handoff_status_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only/10_25c60_handoff_notes.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary59: Optional[dict] = None) -> int:
    summary59 = summary59 or {}
    write_csv(out / "00_不要_25c60_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c60_input_audit.csv", input_audit)
    write_csv(out / "04_25c60_contract_audit.csv", diag)
    write_csv(out / "05_25c60_final_handoff_status_matrix.csv", diag)
    write_csv(out / "06_25c60_final_blocked_execution_matrix.csv", diag)
    write_csv(out / "07_25c60_final_guardrail_matrix.csv", diag)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C59 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "final handoff safe", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c60_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c60": False}])
    write_csv(out / "09_25c60_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C60 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c60_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "final_handoff_only": True,
        "input_25c59_step": summary59.get("step"),
        "input_25c59_status": summary59.get("status"),
        "execution_remains_blocked": True,
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
    write_json(out / "02_25c60_dry_run_blocked_status_final_handoff_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C60 CoreB G1 dry-run blocked status final handoff audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run/external action was performed.",
    ])
    lp(out / "01_25c60_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary59: dict, contract59: pd.DataFrame, roadmap59: pd.DataFrame, precond59: pd.DataFrame, blocked59: pd.DataFrame, gates59: pd.DataFrame, next59: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_59_STEP,
        "status": EXPECTED_59_STATUS,
        "audit_only": True,
        "blocked_status_roadmap_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "roadmap_rows": 10,
        "future_precondition_rows": 5,
        "blocked_execution_rows": 10,
        "execution_remains_blocked": True,
        "acceptance_recorded": False,
        "required_literal_present": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_59,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary59.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary59.get("representative_filters", [])
    rows.append({"contract_id": "C020", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary59.get(flag), "expected": False, "status": "PASS" if summary59.get(flag) is False else "STOP"})
    stop_count = int(contract59[contract59.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    roadmap_ok = len(roadmap59) == 10 and not roadmap59.get("execution_allowed_now", pd.Series(dtype=bool)).apply(as_bool).any()
    precond_ok = len(precond59) == 5 and not precond59.get("satisfied_now", pd.Series(dtype=bool)).apply(as_bool).any()
    blocked_ok = len(blocked59) == 10 and not blocked59.get("allowed_now", pd.Series(dtype=bool)).apply(as_bool).any()
    gates_ok = "NO_EXECUTION_ALLOWED" in gates59.get("status", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in gates59.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next59.empty and str(next59.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_59 and as_bool(next59.iloc[0].get("allowed_now")) and not as_bool(next59.iloc[0].get("execution_allowed_in_25c59")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C59 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "roadmap has no executable rows", "observed": roadmap_ok, "expected": True, "status": "PASS" if roadmap_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "preconditions not satisfied", "observed": precond_ok, "expected": True, "status": "PASS" if precond_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "blocked execution rows not allowed", "observed": blocked_ok, "expected": True, "status": "PASS" if blocked_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C59 gates show no execution", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C59 next plan allows 25C60 only", "observed": next59.iloc[0].to_dict() if not next59.empty else {}, "expected": "25C60 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_final_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    status = pd.DataFrame([
        {"handoff_id": "FH001", "item": "GOLD_V2_mode", "value": "audit_only", "final_status": "FINAL_CARRIED_FORWARD"},
        {"handoff_id": "FH002", "item": "A002_approval", "value": "NOT_APPROVED_REVIEW_ONLY", "final_status": "FINAL_CARRIED_FORWARD"},
        {"handoff_id": "FH003", "item": "source_binding", "value": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY", "final_status": "FINAL_CARRIED_FORWARD"},
        {"handoff_id": "FH004", "item": "acceptance_recorded", "value": "false", "final_status": "NOT_RECORDED"},
        {"handoff_id": "FH005", "item": "execution_gate_open", "value": "false", "final_status": "CLOSED"},
        {"handoff_id": "FH006", "item": "future_dry_run_execution", "value": "blocked", "final_status": "BLOCKED"},
        {"handoff_id": "FH007", "item": "live_external_paths", "value": "blocked", "final_status": "BLOCKED"},
        {"handoff_id": "FH008", "item": "NO_SIGNAL_Discord_notification", "value": "disabled", "final_status": "DISABLED"},
    ])
    blocked = pd.DataFrame([
        {"blocked_id": "FB001", "execution_path": "dry_run_execution", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB002", "execution_path": "replay_execution", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB003", "execution_path": "source_recovery", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB004", "execution_path": "condition_change", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB005", "execution_path": "live_hook", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB006", "execution_path": "discord_notification", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB007", "execution_path": "mt5_order", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB008", "execution_path": "ai_api_call", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB009", "execution_path": "final_signal", "allowed_now": False, "final_status": "BLOCKED"},
        {"blocked_id": "FB010", "execution_path": "no_signal_discord_notify", "allowed_now": False, "final_status": "BLOCKED"},
    ])
    guard = pd.DataFrame([
        {"guardrail_id": "GR001", "guardrail": "REQUEST_MORE_AUDIT is not approval", "status": "ACTIVE"},
        {"guardrail_id": "GR002", "guardrail": "Old GOLD/DISC8 remains quarantined", "status": "ACTIVE"},
        {"guardrail_id": "GR003", "guardrail": "No approximate reimplementation", "status": "ACTIVE"},
        {"guardrail_id": "GR004", "guardrail": "Discord/MT5/AI/live/final signal remain off", "status": "ACTIVE"},
        {"guardrail_id": "GR005", "guardrail": "NO_SIGNAL does not notify Discord", "status": "ACTIVE"},
    ])
    return status, blocked, guard


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN59
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary59": input_dir / "02_25c59_dry_run_blocked_status_roadmap_summary.json",
        "contract59": input_dir / "04_25c59_contract_audit.csv",
        "roadmap59": input_dir / "05_25c59_blocked_status_roadmap_matrix.csv",
        "precond59": input_dir / "06_25c59_future_precondition_matrix.csv",
        "blocked59": input_dir / "07_25c59_blocked_execution_matrix.csv",
        "gates59": input_dir / "08_25c59_gates.csv",
        "next59": input_dir / "09_25c59_next_step_plan.csv",
        "notes59": input_dir / "10_25c59_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c60_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary59 = read_json(req["summary59"])
    contract59 = read_csv(req["contract59"])
    roadmap59 = read_csv(req["roadmap59"])
    precond59 = read_csv(req["precond59"])
    blocked59 = read_csv(req["blocked59"])
    gates59 = read_csv(req["gates59"])
    next59 = read_csv(req["next59"])
    notes59 = read_csv(req["notes59"])

    contract = contract_audit(summary59, contract59, roadmap59, precond59, blocked59, gates59, next59)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary59)

    final_status, final_blocked, guardrails = build_final_matrices()
    unsafe = final_blocked["allowed_now"].apply(as_bool).any() or not guardrails["status"].astype(str).eq("ACTIVE").all()
    if unsafe:
        return stop_outputs(out, STOP_HANDOFF, input_audit, pd.concat([final_status, final_blocked, guardrails], ignore_index=True), summary59)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C59 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "final handoff complete", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "any execution allowed", "observed": False, "status": "NO_EXECUTION_ALLOWED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "blocked branch completed; wait for explicit human instruction", "execution_allowed_in_25c60": False, "requires_human_acceptance_before_execution": True},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked by final handoff", "execution_allowed_in_25c60": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c60": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C60 used 25C59 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Final blocked-status handoff completed; execution remains blocked.", "status": "NO_EXECUTION_ALLOWED"},
        {"note_id": "N003", "note": "A002 remains not approved and source remains planning-only.", "status": "PASS"},
        {"note_id": "N004", "note": "No acceptance, replay, dry-run, source, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
        {"note_id": "N005", "note": "Wait for explicit human instruction before any new branch.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c60_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c60_input_audit.csv", input_audit)
    write_csv(out / "04_25c60_contract_audit.csv", contract)
    write_csv(out / "05_25c60_final_handoff_status_matrix.csv", final_status)
    write_csv(out / "06_25c60_final_blocked_execution_matrix.csv", final_blocked)
    write_csv(out / "07_25c60_final_guardrail_matrix.csv", guardrails)
    write_csv(out / "08_25c60_gates.csv", gates)
    write_csv(out / "09_25c60_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c60_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "final_handoff_only": True,
        "input_25c59_step": summary59.get("step"),
        "input_25c59_status": summary59.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "final_handoff_rows": int(len(final_status)),
        "final_blocked_execution_rows": int(len(final_blocked)),
        "final_guardrail_rows": int(len(guardrails)),
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
    write_json(out / "02_25c60_dry_run_blocked_status_final_handoff_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C60 CoreB G1 dry-run blocked status final handoff audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C60 writes final blocked-status handoff only. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C59 contract audit", "", md_table(contract), "",
        "## Final handoff status matrix", "", md_table(final_status), "",
        "## Final blocked execution matrix", "", md_table(final_blocked), "",
        "## Final guardrail matrix", "", md_table(guardrails), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "Final blocked-status handoff completed. No execution is allowed. A002 remains NOT_APPROVED_REVIEW_ONLY. Source remains planning-only. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c60_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "execution_remains_blocked": True, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
