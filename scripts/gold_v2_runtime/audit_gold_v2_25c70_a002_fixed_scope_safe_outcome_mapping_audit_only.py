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

STEP = "25C70_A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_AUDIT_ONLY"
STATUS_READY = "A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_READY_AUDIT_ONLY_ONE_TO_ONE_RESULT_MAPPED"
STATUS_BLOCKED = "A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_BLOCKED_AUDIT_ONLY_JOIN_NOT_ONE_TO_ONE"
IN_DIR = "gold_v2_25c69_a002_fixed_scope_full_result_source_scan_audit_only"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c70_a002_fixed_scope_safe_outcome_mapping_audit_only"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
OUTCOME_COLUMN = "rr"


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


def boolish(v: object) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def as_rel_path(root: Path, rel: str) -> Path:
    parts = rel.replace("\\", "/").split("/")
    return root.joinpath(*parts)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--ledger-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    root = fx_outputs()
    input_dir = Path(args.input_dir).resolve() if args.input_dir else root / IN_DIR
    ledger_dir = Path(args.ledger_dir).resolve() if args.ledger_dir else root / LEDGER_DIR
    out = Path(args.output_dir).resolve() if args.output_dir else root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary69": input_dir / "02_25c69_full_result_source_scan_summary.json",
        "contract69": input_dir / "04_25c69_contract_audit.csv",
        "safe69": input_dir / "06_25c69_safe_full_source_candidates.csv",
        "readiness69": input_dir / "10_25c69_readiness_matrix.csv",
        "boundary69": input_dir / "11_25c69_boundary_matrix.csv",
        "ledger66": ledger_dir / "05_25c66_dry_run_event_ledger.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c70_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C70_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c70_safe_outcome_mapping_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s69 = read_json(req["summary69"])
    contract69 = read_csv(req["contract69"])
    safe69 = read_csv(req["safe69"])
    readiness69 = read_csv(req["readiness69"])
    boundary69 = read_csv(req["boundary69"])
    ledger = read_csv(req["ledger66"])

    source_rel = str(s69.get("best_candidate_path", ""))
    source_path = as_rel_path(root, source_rel)
    source_exists = lp(source_path).exists()
    source = read_csv(source_path) if source_exists else pd.DataFrame()

    contract_rows = []
    checks = [
        ("step", s69.get("step"), "25C69_A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_AUDIT_ONLY"),
        ("status", s69.get("status"), "A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_READY_AUDIT_ONLY_SAFE_SOURCE_FOUND"),
        ("audit_only", s69.get("audit_only"), True),
        ("variant", s69.get("representative_variant_code"), "A002"),
        ("filters", s69.get("representative_filters"), EXPECTED_FILTERS),
        ("ledger_events", s69.get("ledger_events"), 772),
        ("safe_full_sources", s69.get("safe_full_sources"), 1),
        ("best_candidate_match_count", s69.get("best_candidate_match_count"), 772),
        ("trade_outcome_simulation_executed", s69.get("trade_outcome_simulation_executed"), False),
        ("condition_changed", s69.get("condition_changed"), False),
        ("source_recovery_executed", s69.get("source_recovery_executed"), False),
        ("source_mutation_executed", s69.get("source_mutation_executed"), False),
        ("ai_api_called", s69.get("ai_api_called"), False),
        ("discord_notification_sent", s69.get("discord_notification_sent"), False),
        ("mt5_order_sent", s69.get("mt5_order_sent"), False),
        ("final_signal_created", s69.get("final_signal_created"), False),
        ("total_stop_rows", s69.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    contract_rows += [
        {"contract_id": "M018", "check": "25C69 contract no STOP", "observed": int((contract69.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract69.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M019", "check": "safe source candidate rows", "observed": int(len(safe69)), "expected": 1, "status": "PASS" if len(safe69) == 1 else "STOP"},
        {"contract_id": "M020", "check": "source file exists", "observed": source_exists, "expected": True, "status": "PASS" if source_exists else "STOP"},
        {"contract_id": "M021", "check": "ledger rows", "observed": int(len(ledger)), "expected": 772, "status": "PASS" if len(ledger) == 772 else "STOP"},
        {"contract_id": "M022", "check": "source outcome column", "observed": OUTCOME_COLUMN in source.columns, "expected": True, "status": "PASS" if OUTCOME_COLUMN in source.columns else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c70_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C70_STOP_25C69_CONTRACT_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c70_safe_outcome_mapping_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    join_cols = ["entry_time"]
    for c in ("dataset", "policy"):
        if c in ledger.columns and c in source.columns:
            join_cols.append(c)

    source_subset_cols = join_cols + [OUTCOME_COLUMN]
    for optional in ("profit", "outcome", "result", "signal", "direction", "filter"):
        if optional in source.columns and optional not in source_subset_cols:
            source_subset_cols.append(optional)
    source_subset = source[source_subset_cols].copy()
    dup_counts = source_subset.groupby(join_cols, dropna=False).size().reset_index(name="source_rows_per_key")
    ledger_keys = ledger[join_cols + ["a002_fixed_scope_event_id"]].copy()
    mapped = ledger_keys.merge(source_subset, on=join_cols, how="left", indicator=True)
    mapped = mapped.merge(dup_counts, on=join_cols, how="left")
    mapped["mapping_status"] = mapped.apply(lambda r: "MATCH_ONE" if r["_merge"] == "both" and int(r.get("source_rows_per_key", 0)) == 1 else ("MISSING" if r["_merge"] != "both" else "AMBIGUOUS"), axis=1)
    mapped["rr_numeric"] = pd.to_numeric(mapped[OUTCOME_COLUMN], errors="coerce") if OUTCOME_COLUMN in mapped.columns else pd.NA

    match_one = int(mapped["mapping_status"].eq("MATCH_ONE").sum())
    missing = int(mapped["mapping_status"].eq("MISSING").sum())
    ambiguous = int(mapped["mapping_status"].eq("AMBIGUOUS").sum())
    numeric_ok = int(mapped["rr_numeric"].notna().sum())
    one_to_one_ready = match_one == 772 and missing == 0 and ambiguous == 0 and numeric_ok == 772

    mapping_integrity = pd.DataFrame([
        {"check_id": "MI001", "check": "join_columns", "observed": ";".join(join_cols), "expected": "entry_time plus available dataset/policy", "status": "PASS"},
        {"check_id": "MI002", "check": "mapped_rows", "observed": int(len(mapped)), "expected": 772, "status": "PASS" if len(mapped) == 772 else "STOP"},
        {"check_id": "MI003", "check": "match_one", "observed": match_one, "expected": 772, "status": "PASS" if match_one == 772 else "STOP"},
        {"check_id": "MI004", "check": "missing", "observed": missing, "expected": 0, "status": "PASS" if missing == 0 else "STOP"},
        {"check_id": "MI005", "check": "ambiguous", "observed": ambiguous, "expected": 0, "status": "PASS" if ambiguous == 0 else "STOP"},
        {"check_id": "MI006", "check": "rr_numeric", "observed": numeric_ok, "expected": 772, "status": "PASS" if numeric_ok == 772 else "STOP"},
    ])

    if one_to_one_ready:
        result_summary = pd.DataFrame([
            {"metric": "events", "value": int(len(mapped))},
            {"metric": "rr_sum", "value": float(mapped["rr_numeric"].sum())},
            {"metric": "rr_mean", "value": float(mapped["rr_numeric"].mean())},
            {"metric": "rr_median", "value": float(mapped["rr_numeric"].median())},
            {"metric": "wins_rr_gt_0", "value": int((mapped["rr_numeric"] > 0).sum())},
            {"metric": "losses_rr_lt_0", "value": int((mapped["rr_numeric"] < 0).sum())},
            {"metric": "flat_rr_eq_0", "value": int((mapped["rr_numeric"] == 0).sum())},
            {"metric": "win_rate_rr_gt_0", "value": float((mapped["rr_numeric"] > 0).mean())},
        ])
        dataset_summary = mapped.groupby("dataset", dropna=False).agg(events=("a002_fixed_scope_event_id", "size"), rr_sum=("rr_numeric", "sum"), rr_mean=("rr_numeric", "mean"), wins=("rr_numeric", lambda x: int((x > 0).sum())), losses=("rr_numeric", lambda x: int((x < 0).sum()))).reset_index() if "dataset" in mapped.columns else pd.DataFrame()
    else:
        result_summary = pd.DataFrame([
            {"metric": "events", "value": int(len(mapped))},
            {"metric": "one_to_one_ready", "value": False},
            {"metric": "match_one", "value": match_one},
            {"metric": "missing", "value": missing},
            {"metric": "ambiguous", "value": ambiguous},
        ])
        dataset_summary = pd.DataFrame()

    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "source_mutation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_step = "25C71_A002_FIXED_SCOPE_OUTCOME_RESULT_REVIEW_AUDIT_ONLY" if one_to_one_ready else "WAIT_FOR_OUTCOME_MAPPING_DISAMBIGUATION_AUDIT_ONLY"
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next_step, "allowed_now": True, "purpose": "review mapped results or disambiguate join", "condition_change_allowed": False, "external_action_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "condition_change_allowed": False, "external_action_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C70 used 25C69 safe source and 25C66 ledger as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Outcome column rr was mapped without changing A002 conditions.", "status": "PASS"},
        {"note_id": "N003", "note": "No live or external action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c70_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c70_safe_outcome_mapping_summary.json"}]))
    write_csv(out / "05_25c70_mapping_integrity_matrix.csv", mapping_integrity)
    write_csv(out / "06_25c70_mapped_outcome_rows.csv", mapped.drop(columns=["_merge"], errors="ignore"))
    write_csv(out / "07_25c70_result_summary.csv", result_summary)
    write_csv(out / "08_25c70_dataset_result_summary.csv", dataset_summary)
    write_csv(out / "09_25c70_boundary_matrix.csv", boundary)
    write_csv(out / "10_25c70_next_step_plan.csv", next_plan)
    write_csv(out / "11_25c70_handoff_notes.csv", notes)

    stop_rows = int((mapping_integrity["status"] == "STOP").sum())
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS_READY if one_to_one_ready else STATUS_BLOCKED,
        "audit_only": True,
        "input_25c69_step": s69.get("step"),
        "input_25c69_status": s69.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "safe_source_path": source_rel,
        "join_columns": join_cols,
        "ledger_events": int(len(ledger)),
        "mapped_rows": int(len(mapped)),
        "match_one_rows": match_one,
        "missing_rows": missing,
        "ambiguous_rows": ambiguous,
        "rr_numeric_rows": numeric_ok,
        "one_to_one_ready": bool(one_to_one_ready),
        "trade_outcome_mapping_created": bool(one_to_one_ready),
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": next_step,
        "total_stop_rows": stop_rows,
    }
    write_json(out / "02_25c70_safe_outcome_mapping_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C70 A002 fixed scope safe outcome mapping audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Mapping integrity", "", md_table(mapping_integrity), "",
        "## Result summary", "", md_table(result_summary), "",
        "## Dataset summary", "", md_table(dataset_summary), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c70_GOLD_V2_A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "one_to_one_ready": bool(one_to_one_ready), "mapped_rows": int(len(mapped)), "match_one_rows": match_one, "missing_rows": missing, "ambiguous_rows": ambiguous, "next_recommended_step": next_step}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
