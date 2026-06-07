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

STEP = "25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY"
STATUS = "COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_READY_AUDIT_ONLY"
STOP_MISSING = "25C49_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C49_STOP_25C48_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_SPEC = "25C49_STOP_DRY_RUN_SPEC_UNSAFE_AUDIT_ONLY"
IN48 = "gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only"
OUT_DIR = "gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only"
EXPECTED_48_STEP = "25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY"
EXPECTED_48_STATUS = "COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_READY_AUDIT_ONLY"
EXPECTED_NEXT_IN_48 = STEP
NEXT_STEP = "25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY"
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


def md_table(df: pd.DataFrame, n: int = 80) -> str:
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
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/02_25c48_representative_filter_set_review_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/05_25c48_representative_filter_set.csv",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/09_25c48_next_step_plan.csv",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/01_25c49_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/02_25c49_representative_filter_set_dry_run_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/05_25c49_dry_run_input_contract.csv",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/06_25c49_dry_run_output_contract.csv",
        "FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/07_25c49_dry_run_acceptance_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def blocked_execution_matrix() -> pd.DataFrame:
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


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary48: Optional[dict] = None) -> int:
    summary48 = summary48 or {}
    write_csv(out / "00_不要_25c49_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c49_input_audit.csv", input_audit)
    write_csv(out / "04_25c49_contract_audit.csv", diag)
    write_csv(out / "05_25c49_dry_run_input_contract.csv", diag)
    write_csv(out / "06_25c49_dry_run_output_contract.csv", diag)
    write_csv(out / "07_25c49_dry_run_acceptance_matrix.csv", diag)
    blocked = blocked_execution_matrix()
    write_csv(out / "08_25c49_blocked_execution_matrix.csv", blocked)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c49": False}])
    write_csv(out / "09_25c49_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C49 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c49_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "dry_run_spec_only": True,
        "input_25c48_step": summary48.get("step"),
        "input_25c48_status": summary48.get("status"),
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
    write_json(out / "02_25c49_representative_filter_set_dry_run_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C49 CoreB G1 representative filter set dry-run spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c49_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary48: dict, contract48: pd.DataFrame, filter_set48: pd.DataFrame, review48: pd.DataFrame, blocked48: pd.DataFrame, gates48: pd.DataFrame, next48: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_48_STEP,
        "status": EXPECTED_48_STATUS,
        "audit_only": True,
        "spec_only": True,
        "representative_variant_code": "A002",
        "representative_retention_priority_cutoff": 1,
        "representative_total_unique_damage_keys": 69,
        "representative_covered_unique_keys": 69,
        "representative_open_unique_keys": 0,
        "representative_retained_filter_count": 2,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_48,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary48.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary48.get("representative_filters", [])
    rows.append({"contract_id": "C014", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary48.get(flag), "expected": False, "status": "PASS" if summary48.get(flag) is False else "STOP"})
    matrices = [("25C48 contract has no STOP", contract48), ("25C48 blocked matrix has no STOP", blocked48)]
    for name, df in matrices:
        stop_count = int(df[df.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) if isinstance(df, pd.DataFrame) else -1
        rows.append({"contract_id": f"M{len(rows)+1:03d}", "check": name, "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"})
    filter_ok = len(filter_set48) == 2 and filter_set48.get("filter", pd.Series(dtype=str)).astype(str).tolist() == EXPECTED_FILTERS and all(filter_set48.get("approval_status", pd.Series(dtype=str)).astype(str).eq("NOT_APPROVED_REVIEW_ONLY"))
    review_ok = "future dry-run" in review48.get("spec_item", pd.Series(dtype=str)).astype(str).tolist() and "BLOCKED" in review48.get("status", pd.Series(dtype=str)).astype(str).tolist()
    gates_ok = "25C49 dry-run spec may be created" in gates48.get("gate", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next48.empty and str(next48.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_48 and as_bool(next48.iloc[0].get("allowed_now")) and not as_bool(next48.iloc[0].get("execution_allowed_in_25c48")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C48 filter set exact and unapproved", "observed": filter_ok, "expected": True, "status": "PASS" if filter_ok else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C48 review spec keeps future dry-run blocked", "observed": review_ok, "expected": True, "status": "PASS" if review_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C48 gates allow 25C49 spec only", "observed": gates_ok, "expected": True, "status": "PASS" if gates_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C48 next plan allows 25C49 spec only", "observed": next48.iloc[0].to_dict() if not next48.empty else {}, "expected": "25C49 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_dry_run_spec() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    input_contract = pd.DataFrame([
        {"input_id": "I001", "required_input": "25C48 summary", "path_hint": "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/02_25c48_representative_filter_set_review_spec_summary.json", "required_before_execution": True, "source_of_truth": True, "notes": "Carries A002 representative facts and no-execution flags."},
        {"input_id": "I002", "required_input": "25C48 representative filter set", "path_hint": "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/05_25c48_representative_filter_set.csv", "required_before_execution": True, "source_of_truth": True, "notes": "Two retained filters only."},
        {"input_id": "I003", "required_input": "25C46 selected coverage plan", "path_hint": "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/05_25c46_selected_coverage_plan.csv", "required_before_execution": True, "source_of_truth": True, "notes": "Original selected representative row."},
        {"input_id": "I004", "required_input": "25C45 corrected attribution rows", "path_hint": "FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/04_25c45_incremental_damage_key_filter_attribution_rows.csv", "required_before_execution": True, "source_of_truth": True, "notes": "Must preserve 360 unique / 1260 attribution semantics."},
        {"input_id": "I005", "required_input": "audited baseline replay signal source", "path_hint": "Prior audited chain, expected 25C10 replay signal rows unless later handoff updates source", "required_before_execution": True, "source_of_truth": True, "notes": "Must be audited artifact only; no approximate reimplementation."},
    ])
    output_contract = pd.DataFrame([
        {"output_id": "O001", "future_output": "dry-run summary json", "required": True, "execution_allowed_in_25c49": False},
        {"output_id": "O002", "future_output": "dry-run candidate signal rows csv", "required": True, "execution_allowed_in_25c49": False},
        {"output_id": "O003", "future_output": "dry-run key coverage audit csv", "required": True, "execution_allowed_in_25c49": False},
        {"output_id": "O004", "future_output": "dry-run filter application audit csv", "required": True, "execution_allowed_in_25c49": False},
        {"output_id": "O005", "future_output": "dry-run comparison against 25C48 expected keys", "required": True, "execution_allowed_in_25c49": False},
        {"output_id": "O006", "future_output": "dry-run boundary and gate matrices", "required": True, "execution_allowed_in_25c49": False},
    ])
    acceptance = pd.DataFrame([
        {"accept_id": "A001", "check": "target candidate remains A002", "expected": "A002", "required_before_execution": True, "status": "SPEC_READY_AUDIT_ONLY"},
        {"accept_id": "A002", "check": "filter set exactly matches 25C48", "expected": ";".join(EXPECTED_FILTERS), "required_before_execution": True, "status": "SPEC_READY_AUDIT_ONLY"},
        {"accept_id": "A003", "check": "expected unique damage keys", "expected": 69, "required_before_execution": True, "status": "SPEC_READY_AUDIT_ONLY"},
        {"accept_id": "A004", "check": "expected open keys before dry-run", "expected": 0, "required_before_execution": True, "status": "SPEC_READY_AUDIT_ONLY"},
        {"accept_id": "A005", "check": "source recovery implied", "expected": False, "required_before_execution": True, "status": "BLOCKED"},
        {"accept_id": "A006", "check": "live/external/AI/notification/order/final signal enabled", "expected": False, "required_before_execution": True, "status": "BLOCKED"},
        {"accept_id": "A007", "check": "manual review before execution", "expected": True, "required_before_execution": True, "status": "SPEC_READY_AUDIT_ONLY"},
    ])
    return input_contract, output_contract, acceptance


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN48
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary48": input_dir / "02_25c48_representative_filter_set_review_spec_summary.json",
        "contract48": input_dir / "04_25c48_contract_audit.csv",
        "filter_set48": input_dir / "05_25c48_representative_filter_set.csv",
        "review_spec48": input_dir / "06_25c48_review_spec_matrix.csv",
        "blocked48": input_dir / "07_25c48_blocked_execution_matrix.csv",
        "gates48": input_dir / "08_25c48_gates.csv",
        "next48": input_dir / "09_25c48_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c49_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary48 = read_json(req["summary48"])
    contract48 = read_csv(req["contract48"])
    filter_set48 = read_csv(req["filter_set48"])
    review48 = read_csv(req["review_spec48"])
    blocked48 = read_csv(req["blocked48"])
    gates48 = read_csv(req["gates48"])
    next48 = read_csv(req["next48"])

    contract = contract_audit(summary48, contract48, filter_set48, review48, blocked48, gates48, next48)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary48)

    input_contract, output_contract, acceptance = build_dry_run_spec()
    unsafe = acceptance[acceptance["status"].astype(str).eq("STOP")]
    if not unsafe.empty:
        return stop_outputs(out, STOP_SPEC, input_audit, acceptance, summary48)

    blocked = blocked_execution_matrix()
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "review dry-run specification readiness only; no execution", "execution_allowed_in_25c49": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until readiness review and explicit acceptance", "execution_allowed_in_25c49": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c49": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C49 used 25C48 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Dry-run input and output contracts were specified only; no dry-run was executed.", "status": "PASS"},
        {"note_id": "N003", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
        {"note_id": "N004", "note": "Next recommended step is a readiness review audit-only step, not execution.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c49_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c49_input_audit.csv", input_audit)
    write_csv(out / "04_25c49_contract_audit.csv", contract)
    write_csv(out / "05_25c49_dry_run_input_contract.csv", input_contract)
    write_csv(out / "06_25c49_dry_run_output_contract.csv", output_contract)
    write_csv(out / "07_25c49_dry_run_acceptance_matrix.csv", acceptance)
    write_csv(out / "08_25c49_blocked_execution_matrix.csv", blocked)
    write_csv(out / "09_25c49_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c49_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "dry_run_spec_only": True,
        "input_25c48_step": summary48.get("step"),
        "input_25c48_status": summary48.get("status"),
        "representative_variant_code": "A002",
        "representative_retention_priority_cutoff": 1,
        "representative_total_unique_damage_keys": 69,
        "representative_covered_unique_keys": 69,
        "representative_open_unique_keys": 0,
        "representative_retained_filter_count": 2,
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "dry_run_input_contract_rows": int(len(input_contract)),
        "dry_run_output_contract_rows": int(len(output_contract)),
        "dry_run_acceptance_rows": int(len(acceptance)),
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
    write_json(out / "02_25c49_representative_filter_set_dry_run_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C49 CoreB G1 representative filter set dry-run spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C49 writes the dry-run specification package only. It does not run replay or dry-run and does not approve A002.", "",
        "## 25C48 contract audit", "", md_table(contract), "",
        "## Dry-run input contract", "", md_table(input_contract), "",
        "## Dry-run output contract", "", md_table(output_contract), "",
        "## Dry-run acceptance matrix", "", md_table(acceptance), "",
        "## Blocked execution matrix", "", md_table(blocked), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c49_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "representative_variant_code": "A002", "dry_run_spec_only": True, "dry_run_executed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
