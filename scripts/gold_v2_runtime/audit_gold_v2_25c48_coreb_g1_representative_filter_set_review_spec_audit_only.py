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

STEP = "25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY"
STATUS = "COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_READY_AUDIT_ONLY"
STOP_MISSING = "25C48_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C48_STOP_25C47_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_FILTER = "25C48_STOP_REPRESENTATIVE_FILTER_SET_UNSAFE_AUDIT_ONLY"
IN47 = "gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only"
IN46 = "gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only"
OUT_DIR = "gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only"
EXPECTED_47_STEP = "25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY"
EXPECTED_47_STATUS = "COREB_G1_FILTER_COVERAGE_NEXT_PLAN_READY_AUDIT_ONLY"
EXPECTED_NEXT_IN_47 = STEP
NEXT_STEP = "25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY"
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
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/02_25c47_filter_coverage_next_plan_summary.json",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/04_25c47_contract_audit.csv",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/05_25c47_representative_candidate_review.csv",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/09_25c47_next_step_plan.csv",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/05_25c46_selected_coverage_plan.csv",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/01_25c48_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/02_25c48_representative_filter_set_review_spec_summary.json",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/05_25c48_representative_filter_set.csv",
        "FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/06_25c48_review_spec_matrix.csv",
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


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary47: Optional[dict] = None) -> int:
    summary47 = summary47 or {}
    write_csv(out / "00_不要_25c48_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c48_input_audit.csv", input_audit)
    write_csv(out / "04_25c48_contract_audit.csv", diag)
    write_csv(out / "05_25c48_representative_filter_set.csv", diag)
    write_csv(out / "06_25c48_review_spec_matrix.csv", diag)
    blocked = blocked_execution_matrix()
    write_csv(out / "07_25c48_blocked_execution_matrix.csv", blocked)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C47 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "representative filter set safe", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "25C49 spec may start", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c48_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c48": False}])
    write_csv(out / "09_25c48_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C48 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c48_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "spec_only": True,
        "input_25c47_step": summary47.get("step"),
        "input_25c47_status": summary47.get("status"),
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
    write_json(out / "02_25c48_representative_filter_set_review_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C48 CoreB G1 representative filter set review spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No execution or external action was performed.",
    ])
    lp(out / "01_25c48_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "replay_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary47: dict, contract47: pd.DataFrame, rep47: pd.DataFrame, option47: pd.DataFrame, boundary47: pd.DataFrame, gates47: pd.DataFrame, next47: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_47_STEP,
        "status": EXPECTED_47_STATUS,
        "audit_only": True,
        "next_plan_only": True,
        "representative_variant_code": "A002",
        "representative_retention_priority_cutoff": 1,
        "representative_total_unique_damage_keys": 69,
        "representative_covered_unique_keys": 69,
        "representative_open_unique_keys": 0,
        "representative_retained_filter_count": 2,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "next_recommended_step": EXPECTED_NEXT_IN_47,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary47.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary47.get(flag), "expected": False, "status": "PASS" if summary47.get(flag) is False else "STOP"})
    matrix_checks = [
        ("contract47 has no STOP", contract47),
        ("representative review has no STOP", rep47),
        ("25C47 boundary matrix has no STOP", boundary47),
    ]
    for name, df in matrix_checks:
        stop_count = int(df[df.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) if isinstance(df, pd.DataFrame) else -1
        rows.append({"contract_id": f"M{len(rows)+1:03d}", "check": name, "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"})
    opt_ok = "25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY" in option47.get("option", pd.Series(dtype=str)).astype(str).tolist()
    gate_ok = "PASS" in gates47.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next47.empty and str(next47.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_47 and as_bool(next47.iloc[0].get("allowed_now")) and not as_bool(next47.iloc[0].get("execution_allowed_in_25c47")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C47 option matrix contains 25C48 spec", "observed": opt_ok, "expected": True, "status": "PASS" if opt_ok else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C47 gates include PASS rows", "observed": gate_ok, "expected": True, "status": "PASS" if gate_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C47 next plan allows 25C48 spec only", "observed": next47.iloc[0].to_dict() if not next47.empty else {}, "expected": "25C48 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def representative_filter_set(selected46: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if selected46.empty or "selected_representative" not in selected46.columns:
        diag = pd.DataFrame([{"check": "25C46 selected representative exists", "observed": False, "expected": True, "status": "STOP"}])
        return pd.DataFrame(), diag
    mask = selected46["selected_representative"].astype(str).str.lower().isin(["true", "1", "yes"])
    if int(mask.sum()) != 1:
        diag = pd.DataFrame([{"check": "one selected representative", "observed": int(mask.sum()), "expected": 1, "status": "STOP"}])
        return pd.DataFrame(), diag
    row = selected46[mask].iloc[0]
    checks = {
        "variant_code": "A002",
        "retention_priority_cutoff": 1,
        "total_unique_damage_keys": 69,
        "covered_unique_keys": 69,
        "open_unique_keys": 0,
        "retained_filter_count": 2,
        "approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "execution_allowed_now": False,
    }
    diag_rows = []
    for i, (k, exp) in enumerate(checks.items(), 1):
        obs = row.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = str(obs) == exp
        diag_rows.append({"check_id": f"R{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    retained = str(row.get("retained_filters", ""))
    filters = [x.strip() for x in retained.split(";") if x.strip()]
    diag_rows.append({"check_id": "R009", "check": "retained filters exact set", "observed": ";".join(filters), "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    filter_rows = []
    for i, filt in enumerate(filters, 1):
        filter_rows.append({
            "filter_rank": i,
            "variant": row.get("variant"),
            "variant_code": row.get("variant_code"),
            "retention_priority_cutoff": row.get("retention_priority_cutoff"),
            "filter": filt,
            "filter_source": "25C46_selected_coverage_plan.retained_filters",
            "candidate_status": "REPRESENTATIVE_REVIEW_SPEC_ONLY",
            "approval_status": "NOT_APPROVED_REVIEW_ONLY",
            "execution_allowed_now": False,
        })
    return pd.DataFrame(filter_rows), pd.DataFrame(diag_rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-25c47-dir", default=None)
    ap.add_argument("--input-25c46-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    in47 = Path(args.input_25c47_dir).resolve() if args.input_25c47_dir else fx_outputs() / IN47
    in46 = Path(args.input_25c46_dir).resolve() if args.input_25c46_dir else fx_outputs() / IN46
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary47": in47 / "02_25c47_filter_coverage_next_plan_summary.json",
        "contract47": in47 / "04_25c47_contract_audit.csv",
        "representative47": in47 / "05_25c47_representative_candidate_review.csv",
        "option47": in47 / "06_25c47_next_option_matrix.csv",
        "boundary47": in47 / "07_25c47_execution_boundary_matrix.csv",
        "gates47": in47 / "08_25c47_gates.csv",
        "next47": in47 / "09_25c47_next_step_plan.csv",
        "selected46": in46 / "05_25c46_selected_coverage_plan.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c48_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary47 = read_json(req["summary47"])
    contract47 = read_csv(req["contract47"])
    rep47 = read_csv(req["representative47"])
    option47 = read_csv(req["option47"])
    boundary47 = read_csv(req["boundary47"])
    gates47 = read_csv(req["gates47"])
    next47 = read_csv(req["next47"])
    selected46 = read_csv(req["selected46"])

    contract = contract_audit(summary47, contract47, rep47, option47, boundary47, gates47, next47)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary47)

    filter_set, filter_diag = representative_filter_set(selected46)
    if filter_diag["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_FILTER, input_audit, filter_diag, summary47)

    review_spec = pd.DataFrame([
        {"spec_id": "S001", "spec_item": "filter set identity", "expected": "A002 retained filter set from 25C46 selected representative", "status": "SPEC_READY_AUDIT_ONLY", "execution_allowed_now": False},
        {"spec_id": "S002", "spec_item": "coverage basis", "expected": "unique key only: variant+dataset+entry_time+policy", "status": "SPEC_READY_AUDIT_ONLY", "execution_allowed_now": False},
        {"spec_id": "S003", "spec_item": "expected unique damage keys", "expected": 69, "status": "SPEC_READY_AUDIT_ONLY", "execution_allowed_now": False},
        {"spec_id": "S004", "spec_item": "expected open keys", "expected": 0, "status": "SPEC_READY_AUDIT_ONLY", "execution_allowed_now": False},
        {"spec_id": "S005", "spec_item": "candidate approval status", "expected": "NOT_APPROVED_REVIEW_ONLY", "status": "SPEC_READY_AUDIT_ONLY", "execution_allowed_now": False},
        {"spec_id": "S006", "spec_item": "future dry-run", "expected": "blocked until later explicit approval", "status": "BLOCKED", "execution_allowed_now": False},
        {"spec_id": "S007", "spec_item": "source recovery", "expected": "blocked", "status": "BLOCKED", "execution_allowed_now": False},
        {"spec_id": "S008", "spec_item": "live/external/AI actions", "expected": "blocked", "status": "BLOCKED", "execution_allowed_now": False},
    ])
    blocked = blocked_execution_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C47 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "A002 representative filter set exact", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "A002 remains not approved", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "25C49 dry-run spec may be created", "observed": True, "status": "PASS"},
        {"gate_id": "G005", "gate": "replay/dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write dry-run specification only; no dry-run execution", "execution_allowed_in_25c48": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future replay/dry-run execution", "allowed_now": False, "purpose": "blocked until later explicit acceptance", "execution_allowed_in_25c48": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c48": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C48 used 25C47 and 25C46 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Representative filter set is exactly same_count>=2&unique_origins>=2 plus unique_origins>=2.", "status": "PASS"},
        {"note_id": "N003", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
        {"note_id": "N004", "note": "Next recommended step is a dry-run specification step only, not dry-run execution.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c48_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c48_input_audit.csv", input_audit)
    write_csv(out / "04_25c48_contract_audit.csv", contract)
    write_csv(out / "05_25c48_representative_filter_set.csv", filter_set)
    write_csv(out / "06_25c48_review_spec_matrix.csv", review_spec)
    write_csv(out / "07_25c48_blocked_execution_matrix.csv", blocked)
    write_csv(out / "08_25c48_gates.csv", gates)
    write_csv(out / "09_25c48_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c48_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "spec_only": True,
        "input_25c47_step": summary47.get("step"),
        "input_25c47_status": summary47.get("status"),
        "representative_variant_code": "A002",
        "representative_retention_priority_cutoff": 1,
        "representative_total_unique_damage_keys": 69,
        "representative_covered_unique_keys": 69,
        "representative_open_unique_keys": 0,
        "representative_retained_filter_count": 2,
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
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
    write_json(out / "02_25c48_representative_filter_set_review_spec_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C48 CoreB G1 representative filter set review spec audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C48 writes a representative filter set review specification only. It does not approve A002 or execute replay/dry-run/source/live/external actions.", "",
        "## 25C47 contract audit", "", md_table(contract), "",
        "## Representative filter set", "", md_table(filter_set), "",
        "## Filter set diagnostic", "", md_table(filter_diag), "",
        "## Review spec matrix", "", md_table(review_spec), "",
        "## Blocked execution matrix", "", md_table(blocked), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Discord, MT5, AI API, live hook, live evaluator unblock, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c48_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "representative_variant_code": "A002", "representative_filters": EXPECTED_FILTERS, "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY", "next_recommended_step": NEXT_STEP, "ai_api_called": False, "replay_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
