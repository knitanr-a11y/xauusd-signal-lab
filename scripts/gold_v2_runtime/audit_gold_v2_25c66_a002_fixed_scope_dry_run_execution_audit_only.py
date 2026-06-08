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

STEP = "25C66_A002_FIXED_SCOPE_DRY_RUN_EXECUTION_AUDIT_ONLY"
STATUS = "A002_FIXED_SCOPE_DRY_RUN_EXECUTED_AUDIT_ONLY_LEDGER_CREATED_NO_EXTERNAL_ACTION"
IN_DIR = "gold_v2_25c65_a002_fixed_scope_dry_review_audit_only"
OUT_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
NEXT_STEP = "25C67_A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"
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


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
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
        "summary65": input_dir / "02_25c65_a002_fixed_scope_dry_review_summary.json",
        "contract65": input_dir / "04_25c65_contract_audit.csv",
        "source_review65": input_dir / "05_25c65_source_row_review.csv",
        "filter_counts65": input_dir / "06_25c65_filter_row_counts.csv",
        "selected65": input_dir / "07_25c65_selected_source_rows.csv",
        "guard65": input_dir / "08_25c65_guardrail_matrix.csv",
        "next_pkg65": input_dir / "09_25c65_next_execution_review_package.csv",
        "boundary65": input_dir / "10_25c65_boundary_matrix.csv",
        "next65": input_dir / "11_25c65_next_step_plan.csv",
        "notes65": input_dir / "12_25c65_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c66_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C66_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c66_a002_fixed_scope_dry_run_execution_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s65 = read_json(req["summary65"])
    contract65 = read_csv(req["contract65"])
    source_review65 = read_csv(req["source_review65"])
    filter_counts65 = read_csv(req["filter_counts65"])
    selected65 = read_csv(req["selected65"])
    guard65 = read_csv(req["guard65"])
    next_pkg65 = read_csv(req["next_pkg65"])
    boundary65 = read_csv(req["boundary65"])
    next65 = read_csv(req["next65"])

    checks = [
        ("step", s65.get("step"), "25C65_A002_FIXED_SCOPE_DRY_REVIEW_AUDIT_ONLY"),
        ("status", s65.get("status"), "A002_FIXED_SCOPE_DRY_REVIEW_READY_AUDIT_ONLY_ROWS_SELECTED_NO_EXECUTION"),
        ("audit_only", s65.get("audit_only"), True),
        ("variant", s65.get("representative_variant_code"), "A002"),
        ("filters", s65.get("representative_filters"), EXPECTED_FILTERS),
        ("selected_rows", s65.get("selected_rows"), 1544),
        ("selected_unique_entry_times", s65.get("selected_unique_entry_times"), 772),
        ("next_execution_review_package_ready", s65.get("next_execution_review_package_ready"), True),
        ("condition_changed", s65.get("condition_changed"), False),
        ("source_recovery_executed", s65.get("source_recovery_executed"), False),
        ("source_mutation_executed", s65.get("source_mutation_executed"), False),
        ("dry_run_executed", s65.get("dry_run_executed"), False),
        ("replay_executed", s65.get("replay_executed"), False),
        ("ai_api_called", s65.get("ai_api_called"), False),
        ("discord_notification_sent", s65.get("discord_notification_sent"), False),
        ("mt5_order_sent", s65.get("mt5_order_sent"), False),
        ("final_signal_created", s65.get("final_signal_created"), False),
        ("next_recommended_step", s65.get("next_recommended_step"), "25C66_A002_FIXED_SCOPE_DRY_RUN_EXECUTION_AUDIT_ONLY"),
        ("total_stop_rows", s65.get("total_stop_rows"), 0),
    ]
    contract_rows = []
    for i, (name, obs, exp) in enumerate(checks, 1):
        ok = obs == exp
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    contract_rows += [
        {"contract_id": "M020", "check": "25C65 contract no STOP", "observed": int((contract65.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract65.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M021", "check": "source review pass", "observed": int(source_review65.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()), "expected": 4, "status": "PASS" if int(source_review65.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()) == 4 else "STOP"},
        {"contract_id": "M022", "check": "filter counts ready", "observed": int(filter_counts65.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()), "expected": 2, "status": "PASS" if int(filter_counts65.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()) == 2 else "STOP"},
        {"contract_id": "M023", "check": "selected rows count", "observed": int(len(selected65)), "expected": 1544, "status": "PASS" if int(len(selected65)) == 1544 else "STOP"},
        {"contract_id": "M024", "check": "guardrails pass", "observed": int(guard65.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()), "expected": 5, "status": "PASS" if int(guard65.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()) == 5 else "STOP"},
        {"contract_id": "M025", "check": "next package ready", "observed": int(next_pkg65.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()), "expected": 5, "status": "PASS" if int(next_pkg65.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()) == 5 else "STOP"},
        {"contract_id": "M026", "check": "boundaries safe", "observed": not boundary65.get("allowed_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not boundary65.get("allowed_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c66_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C66_STOP_25C65_CONTRACT_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c66_a002_fixed_scope_dry_run_execution_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    # One audit dry-run ledger row per dataset-entry_time-policy. The two fixed filters must be present for every event.
    group_cols = ["dataset", "entry_time", "policy"]
    grouped = selected65.groupby(group_cols, dropna=False)
    ledger = grouped.agg(
        selected_filter_rows=("filter", "size"),
        filter_count=("filter", "nunique"),
        filters_matched=("filter", lambda x: ";".join(sorted(map(str, x.unique())))),
        source_count_max=("source_count_by_entry_time", "max"),
        unique_origin_count_max=("unique_origin_count_by_entry_time", "max"),
        intersection_only_all=("intersection_only", lambda x: all(b(v) for v in x)),
        full_coreb_parity_any=("full_coreb_parity", lambda x: any(b(v) for v in x)),
    ).reset_index()
    ledger["a002_fixed_scope_event_id"] = [f"A002_DRY_{i+1:06d}" for i in range(len(ledger))]
    ledger["audit_only_dry_run_event_created"] = True
    ledger["external_action"] = False
    ledger["condition_changed"] = False
    ledger["source_recovery_executed"] = False
    ledger = ledger[["a002_fixed_scope_event_id"] + group_cols + [c for c in ledger.columns if c not in {"a002_fixed_scope_event_id", *group_cols}]]

    pair_ok = ledger["filters_matched"].eq(";".join(EXPECTED_FILTERS)) | ledger["filters_matched"].eq(";".join(sorted(EXPECTED_FILTERS)))
    integrity = pd.DataFrame([
        {"integrity_id": "I001", "item": "ledger_rows", "value": int(len(ledger)), "expected": 772, "status": "PASS" if len(ledger) == 772 else "STOP"},
        {"integrity_id": "I002", "item": "all_events_have_two_rows", "value": bool((ledger["selected_filter_rows"] == 2).all()), "expected": True, "status": "PASS" if bool((ledger["selected_filter_rows"] == 2).all()) else "STOP"},
        {"integrity_id": "I003", "item": "all_events_have_two_filters", "value": bool((ledger["filter_count"] == 2).all()), "expected": True, "status": "PASS" if bool((ledger["filter_count"] == 2).all()) else "STOP"},
        {"integrity_id": "I004", "item": "all_events_fixed_filter_pair", "value": bool(pair_ok.all()), "expected": True, "status": "PASS" if bool(pair_ok.all()) else "STOP"},
        {"integrity_id": "I005", "item": "all_events_intersection_only", "value": bool(ledger["intersection_only_all"].apply(b).all()), "expected": True, "status": "PASS" if bool(ledger["intersection_only_all"].apply(b).all()) else "STOP"},
        {"integrity_id": "I006", "item": "any_full_coreb_parity", "value": bool(ledger["full_coreb_parity_any"].apply(b).any()), "expected": False, "status": "PASS" if not bool(ledger["full_coreb_parity_any"].apply(b).any()) else "STOP"},
    ])
    dataset_counts = ledger.groupby("dataset", dropna=False).agg(events=("a002_fixed_scope_event_id", "size")).reset_index()
    dataset_counts["status"] = "PASS"
    guard = pd.DataFrame([
        {"guard_id": "G001", "item": "condition_change", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G002", "item": "source_recovery", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G003", "item": "source_mutation", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G004", "item": "external_actions", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G005", "item": "ai_discord_mt5_live_final", "allowed": False, "observed": False, "status": "PASS"},
    ])
    next_pkg = pd.DataFrame([
        {"package_id": "P001", "item": "audit_dry_run_ledger", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P002", "item": "integrity_review", "ready": not integrity["status"].eq("STOP").any(), "status": "READY_AUDIT_ONLY" if not integrity["status"].eq("STOP").any() else "BLOCKED"},
        {"package_id": "P003", "item": "result_review", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P004", "item": "no_external_actions", "ready": True, "status": "READY_AUDIT_ONLY"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "source_mutation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "external_actions", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "final_signal", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_allowed = not integrity["status"].eq("STOP").any()
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": bool(next_allowed), "purpose": "review audit-only dry-run ledger", "execution_allowed_in_25c66": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c66": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C66 used 25C65 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed.", "status": "PASS"},
        {"note_id": "N003", "note": "Audit-only dry-run ledger was created with no external action.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c66_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c66_a002_fixed_scope_dry_run_execution_summary.json"}]))
    write_csv(out / "05_25c66_dry_run_event_ledger.csv", ledger)
    write_csv(out / "06_25c66_pair_integrity_matrix.csv", integrity)
    write_csv(out / "07_25c66_dataset_event_counts.csv", dataset_counts)
    write_csv(out / "08_25c66_guardrail_matrix.csv", guard)
    write_csv(out / "09_25c66_result_review_package.csv", next_pkg)
    write_csv(out / "10_25c66_boundary_matrix.csv", boundary)
    write_csv(out / "11_25c66_next_step_plan.csv", next_plan)
    write_csv(out / "12_25c66_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS if next_allowed else "25C66_STOP_INTEGRITY_FAILED_AUDIT_ONLY",
        "audit_only": True,
        "input_25c65_step": s65.get("step"),
        "input_25c65_status": s65.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "source_selected_rows": int(len(selected65)),
        "audit_only_dry_run_events": int(len(ledger)),
        "audit_only_dry_run_ledger_created": True,
        "dry_run_executed": True,
        "dry_run_execution_type": "audit_only_ledger_creation_no_external_action",
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
        "next_recommended_step": NEXT_STEP if next_allowed else "STOP",
        "total_stop_rows": 0 if next_allowed else int((integrity["status"] == "STOP").sum()),
    }
    write_json(out / "02_25c66_a002_fixed_scope_dry_run_execution_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C66 A002 fixed scope dry-run execution audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Pair integrity", "", md_table(integrity), "",
        "## Dataset event counts", "", md_table(dataset_counts), "",
        "## Guardrails", "", md_table(guard), "",
        "## Result review package", "", md_table(next_pkg), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c66_GOLD_V2_A002_FIXED_SCOPE_DRY_RUN_EXECUTION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "audit_only_dry_run_events": summary["audit_only_dry_run_events"], "dry_run_executed": True, "condition_changed": False, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if next_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
