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

STEP = "25C58_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_READY_AUDIT_ONLY_ALL_EXECUTION_BLOCKED"
STOP_MISSING = "25C58_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C58_STOP_25C57_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_HANDOFF = "25C58_STOP_HANDOFF_UNSAFE_AUDIT_ONLY"
IN57 = "gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only"
OUT_DIR = "gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only"
EXPECTED_57_STEP = "25C57_COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_AUDIT_ONLY"
EXPECTED_57_STATUS = "COREB_G1_DRY_RUN_EXECUTION_BLOCKER_FINALIZATION_READY_AUDIT_ONLY_EXECUTION_REMAINS_BLOCKED"
EXPECTED_NEXT_IN_57 = STEP
NEXT_STEP = "25C59_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c57_coreb_g1_dry_run_execution_blocker_finalization_audit_only/02_25c57_dry_run_execution_blocker_finalization_summary.json",
        "FX_OUTPUTS/gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only/01_25c58_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only/02_25c58_dry_run_blocked_status_handoff_summary.json",
        "FX_OUTPUTS/gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only/05_25c58_blocked_status_handoff_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only/10_25c58_handoff_notes.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary57: Optional[dict] = None) -> int:
    summary57 = summary57 or {}
    write_csv(out / "00_不要_25c58_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c58_input_audit.csv", input_audit)
    write_csv(out / "04_25c58_contract_audit.csv", diag)
    write_csv(out / "05_25c58_blocked_status_handoff_matrix.csv", diag)
    write_csv(out / "06_25c58_active_blocker_carry_forward.csv", diag)
    write_csv(out / "07_25c58_closed_gate_carry_forward.csv", diag)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C57 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "handoff safe", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c58_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c58": False}])
    write_csv(out / "09_25c58_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C58 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c58_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocked_status_handoff_only": True,
        "input_25c57_step": summary57.get("step"),
        "input_25c57_status": summary57.get("status"),
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
    write_json(out / "02_25c58_dry_run_blocked_status_handoff_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C58 CoreB G1 dry-run blocked status handoff audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run/external action was performed.",
    ])
    lp(out / "01_25c58_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary57: dict, contract57: pd.DataFrame, active57: pd.DataFrame, closed57: pd.DataFrame, audit57: pd.DataFrame, gates57: pd.DataFrame, next57: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_57_STEP,
        "status": EXPECTED_57_STATUS,
        "audit_only": True,
        "blocker_finalization_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "active_blocker_rows": 10,
        "closed_gate_rows": 5,
        "execution_remains_blocked": True,
        "acceptance_recorded": False,
        "required_literal_present": False,
        "execution_gate_open": False,
        "future_dry_run_execution_allowed": False,
        "source_confirmed_for_execution": False,
        "human_dry_run_execution_approval": False,
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_57,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary57.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary57.get("representative_filters", [])
    rows.append({"contract_id": "C019", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary57.get(flag), "expected": False, "status": "PASS" if summary57.get(flag) is False else "STOP"})
    stop_count = int(contract57[contract57.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    active_ok = len(active57) == 10 and active57.get("status", pd.Series(dtype=str)).astype(str).eq("ACTIVE_BLOCKER").all() and active57.get("active", pd.Series(dtype=bool)).apply(as_bool).all()
    closed_ok = len(closed57) == 5 and closed57.get("status", pd.Series(dtype=str)).astype(str).eq("CLOSED").all() and not closed57.get("open", pd.Series(dtype=bool)).apply(as_bool).any()
    audit_ok = "audit_only" in audit57.get("value", pd.Series(dtype=str)).astype(str).tolist() and "blocked" in audit57.get("value", pd.Series(dtype=str)).astype(str).tolist()
    gates_ok = "EXECUTION_REMAINS_BLOCKED" in gates57.get("status", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in gates57.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next57.empty and str(next57.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_57 and as_bool(next57.iloc[0].get("allowed_now")) and not as_bool(next57.iloc[0].get("execution_allowed_in_25c57")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C57 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "active blockers carry forward", "observed": active_ok, "expected": True, "status": "PASS" if active_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "closed gates carry forward", "observed": closed_ok, "expected": True, "status": "PASS" if closed_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "audit-only/blocked status present", "observed": audit_ok, "expected": True, "status": "PASS" if audit_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C57 gates show blocked", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C57 next plan allows 25C58 only", "observed": next57.iloc[0].to_dict() if not next57.empty else {}, "expected": "25C58 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_handoff_matrices(active57: pd.DataFrame, closed57: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    handoff = pd.DataFrame([
        {"handoff_id": "H001", "item": "GOLD_V2_mode", "value": "audit_only", "handoff_status": "CARRIED_FORWARD"},
        {"handoff_id": "H002", "item": "A002_approval", "value": "NOT_APPROVED_REVIEW_ONLY", "handoff_status": "CARRIED_FORWARD"},
        {"handoff_id": "H003", "item": "source_binding", "value": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY", "handoff_status": "CARRIED_FORWARD"},
        {"handoff_id": "H004", "item": "active_blockers", "value": "10", "handoff_status": "ACTIVE"},
        {"handoff_id": "H005", "item": "closed_gates", "value": "5", "handoff_status": "CLOSED"},
        {"handoff_id": "H006", "item": "future_dry_run_execution", "value": "blocked", "handoff_status": "BLOCKED"},
        {"handoff_id": "H007", "item": "source_recovery", "value": "blocked", "handoff_status": "BLOCKED"},
        {"handoff_id": "H008", "item": "live_external_paths", "value": "blocked", "handoff_status": "BLOCKED"},
        {"handoff_id": "H009", "item": "NO_SIGNAL_Discord_notification", "value": "disabled", "handoff_status": "DISABLED"},
    ])
    active_cf = active57.copy()
    active_cf["carry_forward_status"] = "CARRIED_FORWARD_ACTIVE"
    closed_cf = closed57.copy()
    closed_cf["carry_forward_status"] = "CARRIED_FORWARD_CLOSED"
    return handoff, active_cf, closed_cf


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN57
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary57": input_dir / "02_25c57_dry_run_execution_blocker_finalization_summary.json",
        "contract57": input_dir / "04_25c57_contract_audit.csv",
        "active57": input_dir / "05_25c57_active_blocker_matrix.csv",
        "closed57": input_dir / "06_25c57_closed_gate_matrix.csv",
        "audit57": input_dir / "07_25c57_audit_only_status_matrix.csv",
        "gates57": input_dir / "08_25c57_gates.csv",
        "next57": input_dir / "09_25c57_next_step_plan.csv",
        "notes57": input_dir / "10_25c57_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c58_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary57 = read_json(req["summary57"])
    contract57 = read_csv(req["contract57"])
    active57 = read_csv(req["active57"])
    closed57 = read_csv(req["closed57"])
    audit57 = read_csv(req["audit57"])
    gates57 = read_csv(req["gates57"])
    next57 = read_csv(req["next57"])
    notes57 = read_csv(req["notes57"])

    contract = contract_audit(summary57, contract57, active57, closed57, audit57, gates57, next57)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary57)

    handoff, active_cf, closed_cf = build_handoff_matrices(active57, closed57)
    unsafe = not handoff["handoff_status"].astype(str).isin(["CARRIED_FORWARD", "ACTIVE", "CLOSED", "BLOCKED", "DISABLED"]).all()
    if unsafe:
        return stop_outputs(out, STOP_HANDOFF, input_audit, handoff, summary57)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C57 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "blocked-status handoff complete", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "execution remains blocked", "observed": True, "status": "EXECUTION_REMAINS_BLOCKED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write blocked-status roadmap only; no execution", "execution_allowed_in_25c58": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked; status handoff records blockers", "execution_allowed_in_25c58": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c58": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C58 used 25C57 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Blocked status handoff is complete; execution remains blocked.", "status": "EXECUTION_REMAINS_BLOCKED"},
        {"note_id": "N003", "note": "A002 remains not approved and source remains planning-only.", "status": "PASS"},
        {"note_id": "N004", "note": "No acceptance, replay, dry-run, source, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c58_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c58_input_audit.csv", input_audit)
    write_csv(out / "04_25c58_contract_audit.csv", contract)
    write_csv(out / "05_25c58_blocked_status_handoff_matrix.csv", handoff)
    write_csv(out / "06_25c58_active_blocker_carry_forward.csv", active_cf)
    write_csv(out / "07_25c58_closed_gate_carry_forward.csv", closed_cf)
    write_csv(out / "08_25c58_gates.csv", gates)
    write_csv(out / "09_25c58_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c58_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "blocked_status_handoff_only": True,
        "input_25c57_step": summary57.get("step"),
        "input_25c57_status": summary57.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "handoff_rows": int(len(handoff)),
        "active_blocker_rows": int(len(active_cf)),
        "closed_gate_rows": int(len(closed_cf)),
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
    write_json(out / "02_25c58_dry_run_blocked_status_handoff_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C58 CoreB G1 dry-run blocked status handoff audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C58 writes blocked-status handoff only. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C57 contract audit", "", md_table(contract), "",
        "## Blocked status handoff matrix", "", md_table(handoff), "",
        "## Active blocker carry-forward", "", md_table(active_cf), "",
        "## Closed gate carry-forward", "", md_table(closed_cf), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "Execution remains blocked. A002 remains NOT_APPROVED_REVIEW_ONLY. Source remains planning-only. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c58_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "execution_remains_blocked": True, "handoff_rows": len(handoff), "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
