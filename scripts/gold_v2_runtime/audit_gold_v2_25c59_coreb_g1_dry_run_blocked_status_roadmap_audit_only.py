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

STEP = "25C59_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_READY_AUDIT_ONLY_NO_EXECUTION_ALLOWED"
STOP_MISSING = "25C59_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C59_STOP_25C58_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_ROADMAP = "25C59_STOP_ROADMAP_UNSAFE_AUDIT_ONLY"
IN58 = "gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only"
OUT_DIR = "gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only"
EXPECTED_58_STEP = "25C58_COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_AUDIT_ONLY"
EXPECTED_58_STATUS = "COREB_G1_DRY_RUN_BLOCKED_STATUS_HANDOFF_READY_AUDIT_ONLY_ALL_EXECUTION_BLOCKED"
EXPECTED_NEXT_IN_58 = STEP
NEXT_STEP = "25C60_COREB_G1_DRY_RUN_BLOCKED_STATUS_FINAL_HANDOFF_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c58_coreb_g1_dry_run_blocked_status_handoff_audit_only/02_25c58_dry_run_blocked_status_handoff_summary.json",
        "FX_OUTPUTS/gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only/01_25c59_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only/02_25c59_dry_run_blocked_status_roadmap_summary.json",
        "FX_OUTPUTS/gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only/05_25c59_blocked_status_roadmap_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c59_coreb_g1_dry_run_blocked_status_roadmap_audit_only/10_25c59_handoff_notes.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary58: Optional[dict] = None) -> int:
    summary58 = summary58 or {}
    write_csv(out / "00_不要_25c59_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c59_input_audit.csv", input_audit)
    write_csv(out / "04_25c59_contract_audit.csv", diag)
    write_csv(out / "05_25c59_blocked_status_roadmap_matrix.csv", diag)
    write_csv(out / "06_25c59_future_precondition_matrix.csv", diag)
    write_csv(out / "07_25c59_blocked_execution_matrix.csv", diag)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C58 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "roadmap safe", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c59_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c59": False}])
    write_csv(out / "09_25c59_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C59 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No acceptance, approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c59_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocked_status_roadmap_only": True,
        "input_25c58_step": summary58.get("step"),
        "input_25c58_status": summary58.get("status"),
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
    write_json(out / "02_25c59_dry_run_blocked_status_roadmap_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C59 CoreB G1 dry-run blocked status roadmap audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run/external action was performed.",
    ])
    lp(out / "01_25c59_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary58: dict, contract58: pd.DataFrame, handoff58: pd.DataFrame, active58: pd.DataFrame, closed58: pd.DataFrame, gates58: pd.DataFrame, next58: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_58_STEP,
        "status": EXPECTED_58_STATUS,
        "audit_only": True,
        "blocked_status_handoff_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "handoff_rows": 9,
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
        "next_recommended_step": EXPECTED_NEXT_IN_58,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary58.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary58.get("representative_filters", [])
    rows.append({"contract_id": "C020", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary58.get(flag), "expected": False, "status": "PASS" if summary58.get(flag) is False else "STOP"})
    stop_count = int(contract58[contract58.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    handoff_ok = len(handoff58) == 9 and set(handoff58.get("handoff_status", pd.Series(dtype=str)).astype(str)).issubset({"CARRIED_FORWARD", "ACTIVE", "CLOSED", "BLOCKED", "DISABLED"})
    active_ok = len(active58) == 10 and active58.get("carry_forward_status", pd.Series(dtype=str)).astype(str).eq("CARRIED_FORWARD_ACTIVE").all()
    closed_ok = len(closed58) == 5 and closed58.get("carry_forward_status", pd.Series(dtype=str)).astype(str).eq("CARRIED_FORWARD_CLOSED").all()
    gates_ok = "EXECUTION_REMAINS_BLOCKED" in gates58.get("status", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in gates58.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next58.empty and str(next58.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_58 and as_bool(next58.iloc[0].get("allowed_now")) and not as_bool(next58.iloc[0].get("execution_allowed_in_25c58")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C58 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "handoff rows safe", "observed": handoff_ok, "expected": True, "status": "PASS" if handoff_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "active blockers carried forward", "observed": active_ok, "expected": True, "status": "PASS" if active_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "closed gates carried forward", "observed": closed_ok, "expected": True, "status": "PASS" if closed_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C58 gates show blocked", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C58 next plan allows 25C59 only", "observed": next58.iloc[0].to_dict() if not next58.empty else {}, "expected": "25C59 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_roadmap_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    roadmap_rows = [
        ("current_status_snapshot", "document current blocked state", False),
        ("blocked_source_confirmation_review", "source confirmation remains blocked", False),
        ("blocked_human_acceptance_review", "human acceptance remains absent", False),
        ("blocked_variant_approval_review", "A002 approval remains absent", False),
        ("blocked_dry_run_execution", "dry-run execution remains blocked", False),
        ("blocked_replay_execution", "replay execution remains blocked", False),
        ("blocked_source_recovery", "source recovery remains blocked", False),
        ("blocked_live_external_paths", "live/external paths remain blocked", False),
        ("blocked_no_signal_discord_notify", "NO_SIGNAL Discord notification remains disabled", False),
        ("final_blocked_status_handoff", "future final handoff documentation only", False),
    ]
    roadmap = pd.DataFrame([
        {"roadmap_id": f"RM{i+1:03d}", "roadmap_item": item, "description": desc, "execution_allowed_now": allowed, "status": "ROADMAP_ONLY_EXECUTION_BLOCKED"}
        for i, (item, desc, allowed) in enumerate(roadmap_rows)
    ])
    preconditions = pd.DataFrame([
        {"precondition_id": "P001", "precondition": "source confirmed for execution", "satisfied_now": False, "status": "NOT_SATISFIED"},
        {"precondition_id": "P002", "precondition": "human acceptance recorded", "satisfied_now": False, "status": "NOT_SATISFIED"},
        {"precondition_id": "P003", "precondition": "A002 approved", "satisfied_now": False, "status": "NOT_SATISFIED"},
        {"precondition_id": "P004", "precondition": "execution gate open", "satisfied_now": False, "status": "NOT_SATISFIED"},
        {"precondition_id": "P005", "precondition": "live/external explicit approval", "satisfied_now": False, "status": "NOT_SATISFIED"},
    ])
    blocked = pd.DataFrame([
        {"blocked_id": "B001", "execution_path": "dry_run_execution", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B002", "execution_path": "replay_execution", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B003", "execution_path": "source_recovery", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B004", "execution_path": "condition_change", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B005", "execution_path": "live_hook", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B006", "execution_path": "discord_notification", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B007", "execution_path": "mt5_order", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B008", "execution_path": "ai_api_call", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B009", "execution_path": "final_signal", "allowed_now": False, "status": "BLOCKED"},
        {"blocked_id": "B010", "execution_path": "no_signal_discord_notify", "allowed_now": False, "status": "BLOCKED"},
    ])
    return roadmap, preconditions, blocked


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN58
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary58": input_dir / "02_25c58_dry_run_blocked_status_handoff_summary.json",
        "contract58": input_dir / "04_25c58_contract_audit.csv",
        "handoff58": input_dir / "05_25c58_blocked_status_handoff_matrix.csv",
        "active58": input_dir / "06_25c58_active_blocker_carry_forward.csv",
        "closed58": input_dir / "07_25c58_closed_gate_carry_forward.csv",
        "gates58": input_dir / "08_25c58_gates.csv",
        "next58": input_dir / "09_25c58_next_step_plan.csv",
        "notes58": input_dir / "10_25c58_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c59_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary58 = read_json(req["summary58"])
    contract58 = read_csv(req["contract58"])
    handoff58 = read_csv(req["handoff58"])
    active58 = read_csv(req["active58"])
    closed58 = read_csv(req["closed58"])
    gates58 = read_csv(req["gates58"])
    next58 = read_csv(req["next58"])
    notes58 = read_csv(req["notes58"])

    contract = contract_audit(summary58, contract58, handoff58, active58, closed58, gates58, next58)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary58)

    roadmap, preconditions, blocked = build_roadmap_matrices()
    unsafe = roadmap["execution_allowed_now"].apply(as_bool).any() or preconditions["satisfied_now"].apply(as_bool).any() or blocked["allowed_now"].apply(as_bool).any()
    if unsafe:
        return stop_outputs(out, STOP_ROADMAP, input_audit, pd.concat([roadmap, preconditions, blocked], ignore_index=True), summary58)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C58 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "blocked-status roadmap complete", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "any execution allowed", "observed": False, "status": "NO_EXECUTION_ALLOWED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write final blocked-status handoff only; no execution", "execution_allowed_in_25c59": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked; roadmap keeps execution paths closed", "execution_allowed_in_25c59": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c59": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C59 used 25C58 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Roadmap was written with no execution allowed.", "status": "NO_EXECUTION_ALLOWED"},
        {"note_id": "N003", "note": "A002 remains not approved and source remains planning-only.", "status": "PASS"},
        {"note_id": "N004", "note": "No acceptance, replay, dry-run, source, live, external, AI, notification, order, or final signal action was executed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c59_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c59_input_audit.csv", input_audit)
    write_csv(out / "04_25c59_contract_audit.csv", contract)
    write_csv(out / "05_25c59_blocked_status_roadmap_matrix.csv", roadmap)
    write_csv(out / "06_25c59_future_precondition_matrix.csv", preconditions)
    write_csv(out / "07_25c59_blocked_execution_matrix.csv", blocked)
    write_csv(out / "08_25c59_gates.csv", gates)
    write_csv(out / "09_25c59_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c59_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "blocked_status_roadmap_only": True,
        "input_25c58_step": summary58.get("step"),
        "input_25c58_status": summary58.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "roadmap_rows": int(len(roadmap)),
        "future_precondition_rows": int(len(preconditions)),
        "blocked_execution_rows": int(len(blocked)),
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
    write_json(out / "02_25c59_dry_run_blocked_status_roadmap_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C59 CoreB G1 dry-run blocked status roadmap audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C59 writes blocked-status roadmap only. No acceptance is recorded and no dry-run/replay is executed.", "",
        "## 25C58 contract audit", "", md_table(contract), "",
        "## Blocked status roadmap matrix", "", md_table(roadmap), "",
        "## Future precondition matrix", "", md_table(preconditions), "",
        "## Blocked execution matrix", "", md_table(blocked), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "No execution is allowed. A002 remains NOT_APPROVED_REVIEW_ONLY. Source remains planning-only. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c59_GOLD_V2_COREB_G1_DRY_RUN_BLOCKED_STATUS_ROADMAP_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "execution_remains_blocked": True, "roadmap_rows": len(roadmap), "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
