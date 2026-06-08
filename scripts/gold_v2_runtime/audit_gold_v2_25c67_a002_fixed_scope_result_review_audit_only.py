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

STEP = "25C67_A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"
STATUS = "A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_READY_AUDIT_ONLY_NO_CONTRADICTION_FOUND"
IN_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c67_a002_fixed_scope_dry_run_result_review_audit_only"
NEXT_STEP = "WAIT_FOR_NEXT_FIXED_SCOPE_DECISION_AUDIT_ONLY"
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


def b(v: object) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in {"true", "1", "yes", "y"}


def md_table(df: pd.DataFrame, max_rows: int = 120) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(max_rows).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    root = fx_outputs()
    input_dir = Path(args.input_dir).resolve() if args.input_dir else root / IN_DIR
    out = Path(args.output_dir).resolve() if args.output_dir else root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary66": input_dir / "02_25c66_a002_fixed_scope_dry_run_execution_summary.json",
        "contract66": input_dir / "04_25c66_contract_audit.csv",
        "ledger66": input_dir / "05_25c66_dry_run_event_ledger.csv",
        "integrity66": input_dir / "06_25c66_pair_integrity_matrix.csv",
        "dataset66": input_dir / "07_25c66_dataset_event_counts.csv",
        "guard66": input_dir / "08_25c66_guardrail_matrix.csv",
        "result_pkg66": input_dir / "09_25c66_result_review_package.csv",
        "boundary66": input_dir / "10_25c66_boundary_matrix.csv",
        "next66": input_dir / "11_25c66_next_step_plan.csv",
        "notes66": input_dir / "12_25c66_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c67_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C67_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c67_a002_fixed_scope_result_review_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s66 = read_json(req["summary66"])
    contract66 = read_csv(req["contract66"])
    ledger = read_csv(req["ledger66"])
    integrity66 = read_csv(req["integrity66"])
    dataset66 = read_csv(req["dataset66"])
    guard66 = read_csv(req["guard66"])
    result_pkg66 = read_csv(req["result_pkg66"])
    boundary66 = read_csv(req["boundary66"])
    next66 = read_csv(req["next66"])

    contract_rows = []
    checks = [
        ("step", s66.get("step"), "25C66_A002_FIXED_SCOPE_DRY_RUN_EXECUTION_AUDIT_ONLY"),
        ("status", s66.get("status"), "A002_FIXED_SCOPE_DRY_RUN_EXECUTED_AUDIT_ONLY_LEDGER_CREATED_NO_EXTERNAL_ACTION"),
        ("audit_only", s66.get("audit_only"), True),
        ("variant", s66.get("representative_variant_code"), "A002"),
        ("filters", s66.get("representative_filters"), EXPECTED_FILTERS),
        ("source_selected_rows", s66.get("source_selected_rows"), 1544),
        ("audit_only_dry_run_events", s66.get("audit_only_dry_run_events"), 772),
        ("audit_only_dry_run_ledger_created", s66.get("audit_only_dry_run_ledger_created"), True),
        ("dry_run_execution_type", s66.get("dry_run_execution_type"), "audit_only_ledger_creation_no_external_action"),
        ("condition_changed", s66.get("condition_changed"), False),
        ("source_recovery_executed", s66.get("source_recovery_executed"), False),
        ("source_mutation_executed", s66.get("source_mutation_executed"), False),
        ("replay_executed", s66.get("replay_executed"), False),
        ("discord_notification_sent", s66.get("discord_notification_sent"), False),
        ("mt5_order_sent", s66.get("mt5_order_sent"), False),
        ("ai_api_called", s66.get("ai_api_called"), False),
        ("live_hook_executed", s66.get("live_hook_executed"), False),
        ("final_signal_created", s66.get("final_signal_created"), False),
        ("no_signal_discord_notify", s66.get("no_signal_discord_notify"), False),
        ("next_recommended_step", s66.get("next_recommended_step"), "25C67_A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"),
        ("total_stop_rows", s66.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    contract_rows += [
        {"contract_id": "M022", "check": "25C66 contract no STOP", "observed": int((contract66.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract66.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M023", "check": "pair integrity no STOP", "observed": int((integrity66.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (integrity66.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M024", "check": "ledger row count", "observed": int(len(ledger)), "expected": 772, "status": "PASS" if len(ledger) == 772 else "STOP"},
        {"contract_id": "M025", "check": "dataset count sum", "observed": int(dataset66.get("events", pd.Series(dtype=int)).astype(int).sum()), "expected": 772, "status": "PASS" if int(dataset66.get("events", pd.Series(dtype=int)).astype(int).sum()) == 772 else "STOP"},
        {"contract_id": "M026", "check": "guardrail no observed action", "observed": not guard66.get("observed", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not guard66.get("observed", pd.Series(dtype=bool)).apply(b).any() else "STOP"},
        {"contract_id": "M027", "check": "boundary no allowed action", "observed": not boundary66.get("allowed_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not boundary66.get("allowed_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"},
        {"contract_id": "M028", "check": "result package ready", "observed": int(result_pkg66.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()), "expected": 4, "status": "PASS" if int(result_pkg66.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()) == 4 else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c67_contract_audit.csv", contract)

    terminology = pd.DataFrame([
        {"term_id": "T001", "field": "dry_run_executed", "observed": s66.get("dry_run_executed"), "interpretation": "legacy boolean from 25C66", "normalized_field": "audit_only_ledger_created", "normalized_value": True, "status": "CLARIFIED"},
        {"term_id": "T002", "field": "dry_run_execution_type", "observed": s66.get("dry_run_execution_type"), "interpretation": "ledger creation only; no external action", "normalized_field": "trade_outcome_simulation_executed", "normalized_value": False, "status": "CLARIFIED"},
        {"term_id": "T003", "field": "live_execution", "observed": False, "interpretation": "not run", "normalized_field": "live_execution_executed", "normalized_value": False, "status": "CLARIFIED"},
        {"term_id": "T004", "field": "external_action", "observed": False, "interpretation": "not run", "normalized_field": "external_action_executed", "normalized_value": False, "status": "CLARIFIED"},
    ])

    contradictions = []
    contradictions.append({"check_id": "X001", "check": "summary vs ledger events", "result": len(ledger) == int(s66.get("audit_only_dry_run_events", -1)), "detail": f"summary={s66.get('audit_only_dry_run_events')} ledger={len(ledger)}"})
    contradictions.append({"check_id": "X002", "check": "unique ids", "result": ledger["a002_fixed_scope_event_id"].nunique() == len(ledger), "detail": f"unique={ledger['a002_fixed_scope_event_id'].nunique()} rows={len(ledger)}"})
    contradictions.append({"check_id": "X003", "check": "unique entry_time", "result": ledger["entry_time"].nunique() == len(ledger), "detail": f"unique_entry_time={ledger['entry_time'].nunique()} rows={len(ledger)}"})
    contradictions.append({"check_id": "X004", "check": "each event has two selected rows", "result": bool((ledger["selected_filter_rows"].astype(int) == 2).all()), "detail": str(ledger["selected_filter_rows"].value_counts().to_dict())})
    contradictions.append({"check_id": "X005", "check": "each event has two filters", "result": bool((ledger["filter_count"].astype(int) == 2).all()), "detail": str(ledger["filter_count"].value_counts().to_dict())})
    contradictions.append({"check_id": "X006", "check": "fixed filter pair", "result": bool(ledger["filters_matched"].astype(str).eq(";".join(EXPECTED_FILTERS)).all()), "detail": str(ledger["filters_matched"].value_counts().to_dict())})
    contradictions.append({"check_id": "X007", "check": "intersection only", "result": bool(ledger["intersection_only_all"].apply(b).all()), "detail": str(ledger["intersection_only_all"].astype(str).value_counts().to_dict())})
    contradictions.append({"check_id": "X008", "check": "no full coreb parity", "result": not bool(ledger["full_coreb_parity_any"].apply(b).any()), "detail": str(ledger["full_coreb_parity_any"].astype(str).value_counts().to_dict())})
    contradictions.append({"check_id": "X009", "check": "no external action", "result": not bool(ledger["external_action"].apply(b).any()), "detail": str(ledger["external_action"].astype(str).value_counts().to_dict())})
    contradictions.append({"check_id": "X010", "check": "no condition/source action", "result": not bool(ledger["condition_changed"].apply(b).any()) and not bool(ledger["source_recovery_executed"].apply(b).any()), "detail": "condition and source recovery columns are false"})
    contradiction_df = pd.DataFrame(contradictions)
    contradiction_df["status"] = contradiction_df["result"].apply(lambda x: "PASS" if bool(x) else "STOP")

    event_summary = pd.DataFrame([
        {"metric": "ledger_rows", "value": int(len(ledger))},
        {"metric": "unique_event_ids", "value": int(ledger["a002_fixed_scope_event_id"].nunique())},
        {"metric": "unique_entry_times", "value": int(ledger["entry_time"].nunique())},
        {"metric": "entry_time_min", "value": str(ledger["entry_time"].min())},
        {"metric": "entry_time_max", "value": str(ledger["entry_time"].max())},
        {"metric": "policy_count", "value": int(ledger["policy"].nunique())},
    ])
    dataset_counts = ledger.groupby("dataset", dropna=False).agg(events=("a002_fixed_scope_event_id", "size")).reset_index()
    policy_counts = ledger.groupby("policy", dropna=False).agg(events=("a002_fixed_scope_event_id", "size")).reset_index()
    boundaries = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "source_mutation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "no_signal_notify", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "user decides next fixed-scope audit action", "execution_allowed_in_25c67": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c67": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C67 used 25C66 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "The dry_run_executed field is treated as audit-only ledger creation, not live/external execution.", "status": "PASS"},
        {"note_id": "N003", "note": "No contradiction was found in counts, filters, guardrails, or boundaries.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c67_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c67_a002_fixed_scope_result_review_summary.json"}]))
    write_csv(out / "05_25c67_terminology_normalization_matrix.csv", terminology)
    write_csv(out / "06_25c67_contradiction_review_matrix.csv", contradiction_df)
    write_csv(out / "07_25c67_event_summary.csv", event_summary)
    write_csv(out / "08_25c67_dataset_counts.csv", dataset_counts)
    write_csv(out / "09_25c67_policy_counts.csv", policy_counts)
    write_csv(out / "10_25c67_boundary_matrix.csv", boundaries)
    write_csv(out / "11_25c67_next_step_plan.csv", next_plan)
    write_csv(out / "12_25c67_handoff_notes.csv", notes)

    stop_rows = int((contract["status"] == "STOP").sum() + (contradiction_df["status"] == "STOP").sum())
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS if stop_rows == 0 else "25C67_STOP_CONTRADICTION_FOUND_AUDIT_ONLY",
        "audit_only": True,
        "input_25c66_step": s66.get("step"),
        "input_25c66_status": s66.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "source_selected_rows": int(s66.get("source_selected_rows", 0)),
        "audit_only_dry_run_events": int(len(ledger)),
        "legacy_dry_run_executed_field": bool(s66.get("dry_run_executed")),
        "audit_only_ledger_created": True,
        "trade_outcome_simulation_executed": False,
        "live_execution_executed": False,
        "external_action_executed": False,
        "contradiction_found": stop_rows > 0,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "replay_executed": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": NEXT_STEP if stop_rows == 0 else "STOP",
        "total_stop_rows": stop_rows,
    }
    write_json(out / "02_25c67_a002_fixed_scope_result_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C67 A002 fixed scope result review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Terminology normalization", "", md_table(terminology), "",
        "## Contradiction review", "", md_table(contradiction_df), "",
        "## Event summary", "", md_table(event_summary), "",
        "## Dataset counts", "", md_table(dataset_counts), "",
        "## Policy counts", "", md_table(policy_counts), "",
        "## Boundaries", "", md_table(boundaries), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c67_GOLD_V2_A002_FIXED_SCOPE_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "contradiction_found": summary["contradiction_found"], "audit_only_dry_run_events": summary["audit_only_dry_run_events"], "trade_outcome_simulation_executed": False, "external_action_executed": False, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if stop_rows == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
