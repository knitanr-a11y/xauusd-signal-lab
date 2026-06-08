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

STEP = "25C71_A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATION_AUDIT_ONLY"
STATUS_READY = "A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATED_AUDIT_ONLY_IDENTICAL_DUPLICATES_COLLAPSED"
STATUS_BLOCKED = "A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATION_BLOCKED_AUDIT_ONLY_CONFLICTING_DUPLICATES"
IN_DIR = "gold_v2_25c70_a002_fixed_scope_safe_outcome_mapping_audit_only"
OUT_DIR = "gold_v2_25c71_a002_fixed_scope_outcome_disambiguation_audit_only"
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
        "summary70": input_dir / "02_25c70_safe_outcome_mapping_summary.json",
        "contract70": input_dir / "04_25c70_contract_audit.csv",
        "integrity70": input_dir / "05_25c70_mapping_integrity_matrix.csv",
        "mapped70": input_dir / "06_25c70_mapped_outcome_rows.csv",
        "boundary70": input_dir / "09_25c70_boundary_matrix.csv",
        "next70": input_dir / "10_25c70_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c71_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C71_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c71_outcome_disambiguation_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s70 = read_json(req["summary70"])
    contract70 = read_csv(req["contract70"])
    integrity70 = read_csv(req["integrity70"])
    mapped = read_csv(req["mapped70"])
    boundary70 = read_csv(req["boundary70"])

    contract_rows = []
    checks = [
        ("step", s70.get("step"), "25C70_A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_AUDIT_ONLY"),
        ("status", s70.get("status"), "A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_BLOCKED_AUDIT_ONLY_JOIN_NOT_ONE_TO_ONE"),
        ("audit_only", s70.get("audit_only"), True),
        ("variant", s70.get("representative_variant_code"), "A002"),
        ("filters", s70.get("representative_filters"), EXPECTED_FILTERS),
        ("ledger_events", s70.get("ledger_events"), 772),
        ("mapped_rows", s70.get("mapped_rows"), 2828),
        ("missing_rows", s70.get("missing_rows"), 0),
        ("ambiguous_rows", s70.get("ambiguous_rows"), 2828),
        ("rr_numeric_rows", s70.get("rr_numeric_rows"), 2828),
        ("one_to_one_ready", s70.get("one_to_one_ready"), False),
        ("condition_changed", s70.get("condition_changed"), False),
        ("source_recovery_executed", s70.get("source_recovery_executed"), False),
        ("source_mutation_executed", s70.get("source_mutation_executed"), False),
        ("ai_api_called", s70.get("ai_api_called"), False),
        ("discord_notification_sent", s70.get("discord_notification_sent"), False),
        ("mt5_order_sent", s70.get("mt5_order_sent"), False),
        ("final_signal_created", s70.get("final_signal_created"), False),
        ("total_stop_rows", s70.get("total_stop_rows"), 4),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    contract_rows += [
        {"contract_id": "M020", "check": "mapped rows", "observed": int(len(mapped)), "expected": 2828, "status": "PASS" if len(mapped) == 2828 else "STOP"},
        {"contract_id": "M021", "check": "unique events", "observed": int(mapped["a002_fixed_scope_event_id"].nunique()), "expected": 772, "status": "PASS" if mapped["a002_fixed_scope_event_id"].nunique() == 772 else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c71_contract_audit.csv", contract)

    group = mapped.groupby("a002_fixed_scope_event_id", dropna=False)
    per_event = group.agg(
        entry_time=("entry_time", "first"),
        dataset=("dataset", "first"),
        policy=("policy", "first"),
        duplicate_rows=("a002_fixed_scope_event_id", "size"),
        rr_unique=("rr_numeric", "nunique"),
        direction_unique=("direction", "nunique"),
        rr_numeric=("rr_numeric", "first"),
        direction=("direction", "first"),
        min_source_rows_per_key=("source_rows_per_key", "min"),
        max_source_rows_per_key=("source_rows_per_key", "max"),
    ).reset_index()
    per_event["disambiguation_status"] = per_event.apply(lambda r: "COLLAPSE_OK" if int(r["rr_unique"]) == 1 and int(r["direction_unique"]) == 1 and int(r["min_source_rows_per_key"]) == int(r["max_source_rows_per_key"]) else "CONFLICT", axis=1)
    conflict_rows = int(per_event["disambiguation_status"].eq("CONFLICT").sum())
    collapsed_ready = conflict_rows == 0 and len(per_event) == 772

    duplicate_distribution = per_event.groupby("duplicate_rows", dropna=False).agg(events=("a002_fixed_scope_event_id", "size")).reset_index()
    disambiguation_integrity = pd.DataFrame([
        {"check_id": "DI001", "check": "events_after_grouping", "observed": int(len(per_event)), "expected": 772, "status": "PASS" if len(per_event) == 772 else "STOP"},
        {"check_id": "DI002", "check": "rr_unique_per_event", "observed": int((per_event["rr_unique"] == 1).sum()), "expected": 772, "status": "PASS" if int((per_event["rr_unique"] == 1).sum()) == 772 else "STOP"},
        {"check_id": "DI003", "check": "direction_unique_per_event", "observed": int((per_event["direction_unique"] == 1).sum()), "expected": 772, "status": "PASS" if int((per_event["direction_unique"] == 1).sum()) == 772 else "STOP"},
        {"check_id": "DI004", "check": "conflict_rows", "observed": conflict_rows, "expected": 0, "status": "PASS" if conflict_rows == 0 else "STOP"},
        {"check_id": "DI005", "check": "collapsed_ready", "observed": collapsed_ready, "expected": True, "status": "PASS" if collapsed_ready else "STOP"},
    ])

    collapsed = per_event[["a002_fixed_scope_event_id", "entry_time", "dataset", "policy", "rr_numeric", "direction", "duplicate_rows", "disambiguation_status"]].copy()
    collapsed = collapsed.rename(columns={"rr_numeric": "rr"})
    collapsed["outcome_source_interpretation"] = "identical_duplicate_rows_collapsed"
    collapsed["condition_changed"] = False
    collapsed["source_recovery_executed"] = False
    collapsed["external_action_executed"] = False

    if collapsed_ready:
        result_summary = pd.DataFrame([
            {"metric": "events", "value": int(len(collapsed))},
            {"metric": "rr_sum", "value": float(collapsed["rr"].sum())},
            {"metric": "rr_mean", "value": float(collapsed["rr"].mean())},
            {"metric": "rr_median", "value": float(collapsed["rr"].median())},
            {"metric": "wins_rr_gt_0", "value": int((collapsed["rr"] > 0).sum())},
            {"metric": "losses_rr_lt_0", "value": int((collapsed["rr"] < 0).sum())},
            {"metric": "flat_rr_eq_0", "value": int((collapsed["rr"] == 0).sum())},
            {"metric": "win_rate_rr_gt_0", "value": float((collapsed["rr"] > 0).mean())},
        ])
        dataset_summary = collapsed.groupby("dataset", dropna=False).agg(events=("a002_fixed_scope_event_id", "size"), rr_sum=("rr", "sum"), rr_mean=("rr", "mean"), wins=("rr", lambda x: int((x > 0).sum())), losses=("rr", lambda x: int((x < 0).sum()))).reset_index()
    else:
        result_summary = pd.DataFrame([{"metric": "collapsed_ready", "value": False}, {"metric": "conflict_rows", "value": conflict_rows}])
        dataset_summary = pd.DataFrame()

    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "source_mutation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_step = "25C72_A002_FIXED_SCOPE_OUTCOME_RESULT_FINAL_REVIEW_AUDIT_ONLY" if collapsed_ready else "WAIT_FOR_CONFLICT_RESOLUTION_AUDIT_ONLY"
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next_step, "allowed_now": True, "purpose": "review collapsed outcome results", "condition_change_allowed": False, "external_action_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "condition_change_allowed": False, "external_action_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C71 used 25C70 mapped rows as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Duplicate rows were collapsed only when rr and direction were identical per event.", "status": "PASS" if collapsed_ready else "STOP"},
        {"note_id": "N003", "note": "No condition/source/external action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c71_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c71_outcome_disambiguation_summary.json"}]))
    write_csv(out / "05_25c71_disambiguation_integrity_matrix.csv", disambiguation_integrity)
    write_csv(out / "06_25c71_duplicate_distribution.csv", duplicate_distribution)
    write_csv(out / "07_25c71_collapsed_outcome_rows.csv", collapsed)
    write_csv(out / "08_25c71_result_summary.csv", result_summary)
    write_csv(out / "09_25c71_dataset_result_summary.csv", dataset_summary)
    write_csv(out / "10_25c71_boundary_matrix.csv", boundary)
    write_csv(out / "11_25c71_next_step_plan.csv", next_plan)
    write_csv(out / "12_25c71_handoff_notes.csv", notes)

    stop_rows = int((contract["status"] == "STOP").sum() + (disambiguation_integrity["status"] == "STOP").sum())
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS_READY if collapsed_ready and stop_rows == 0 else STATUS_BLOCKED,
        "audit_only": True,
        "input_25c70_step": s70.get("step"),
        "input_25c70_status": s70.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "mapped_rows_in": int(len(mapped)),
        "events_out": int(len(collapsed)),
        "conflict_rows": conflict_rows,
        "collapsed_ready": bool(collapsed_ready),
        "rr_sum": float(collapsed["rr"].sum()) if collapsed_ready else None,
        "rr_mean": float(collapsed["rr"].mean()) if collapsed_ready else None,
        "wins_rr_gt_0": int((collapsed["rr"] > 0).sum()) if collapsed_ready else None,
        "losses_rr_lt_0": int((collapsed["rr"] < 0).sum()) if collapsed_ready else None,
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
    write_json(out / "02_25c71_outcome_disambiguation_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C71 A002 fixed scope outcome disambiguation audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Disambiguation integrity", "", md_table(disambiguation_integrity), "",
        "## Duplicate distribution", "", md_table(duplicate_distribution), "",
        "## Result summary", "", md_table(result_summary), "",
        "## Dataset summary", "", md_table(dataset_summary), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c71_GOLD_V2_A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "collapsed_ready": bool(collapsed_ready), "events_out": int(len(collapsed)), "rr_sum": summary["rr_sum"], "rr_mean": summary["rr_mean"], "next_recommended_step": next_step}, ensure_ascii=False, indent=2))
    return 0 if collapsed_ready and stop_rows == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
