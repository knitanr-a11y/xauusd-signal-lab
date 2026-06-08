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

STEP = "25C65_A002_FIXED_SCOPE_DRY_REVIEW_AUDIT_ONLY"
STATUS = "A002_FIXED_SCOPE_DRY_REVIEW_READY_AUDIT_ONLY_ROWS_SELECTED_NO_EXECUTION"
IN_DIR = "gold_v2_25c64_a002_fixed_scope_package_audit_only"
OUT_DIR = "gold_v2_25c65_a002_fixed_scope_dry_review_audit_only"
NEXT_STEP = "25C66_A002_FIXED_SCOPE_DRY_RUN_EXECUTION_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
EXPECTED_SOURCE_COLUMNS = [
    "dataset",
    "entry_time",
    "policy",
    "filter",
    "source_count_by_entry_time",
    "unique_origin_count_by_entry_time",
    "same_count_threshold",
    "unique_origins_threshold",
    "intersection_only",
    "full_coreb_parity",
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
        "summary64": input_dir / "02_25c64_a002_fixed_scope_package_summary.json",
        "contract64": input_dir / "04_25c64_contract_audit.csv",
        "source_package64": input_dir / "05_25c64_source_package_matrix.csv",
        "fixed_filter64": input_dir / "06_25c64_fixed_filter_matrix.csv",
        "guard64": input_dir / "07_25c64_guardrail_matrix.csv",
        "next_review64": input_dir / "08_25c64_next_review_package_matrix.csv",
        "boundary64": input_dir / "09_25c64_boundary_matrix.csv",
        "next64": input_dir / "10_25c64_next_step_plan.csv",
        "notes64": input_dir / "11_25c64_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c65_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C65_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c65_a002_fixed_scope_dry_review_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s64 = read_json(req["summary64"])
    contract64 = read_csv(req["contract64"])
    source_package64 = read_csv(req["source_package64"])
    fixed_filter64 = read_csv(req["fixed_filter64"])
    guard64 = read_csv(req["guard64"])
    next_review64 = read_csv(req["next_review64"])
    boundary64 = read_csv(req["boundary64"])
    next64 = read_csv(req["next64"])

    source_rel = str(s64.get("source_relative_path", ""))
    source_path = root / source_rel
    source_exists = lp(source_path).exists()
    source_df = read_csv(source_path) if source_exists else pd.DataFrame()
    header_ok = list(source_df.columns) == EXPECTED_SOURCE_COLUMNS if source_exists else False

    checks = [
        ("step", s64.get("step"), "25C64_A002_FIXED_SCOPE_PACKAGE_AUDIT_ONLY"),
        ("status", s64.get("status"), "A002_FIXED_SCOPE_PACKAGE_READY_AUDIT_ONLY_NEXT_DRY_REVIEW_ALLOWED"),
        ("audit_only", s64.get("audit_only"), True),
        ("variant", s64.get("representative_variant_code"), "A002"),
        ("filters", s64.get("representative_filters"), EXPECTED_FILTERS),
        ("source_exists", s64.get("source_exists"), True),
        ("source_header_ok", s64.get("source_header_ok"), True),
        ("next_review_package_ready", s64.get("next_review_package_ready"), True),
        ("condition_changed", s64.get("condition_changed"), False),
        ("source_recovery_executed", s64.get("source_recovery_executed"), False),
        ("source_mutation_executed", s64.get("source_mutation_executed"), False),
        ("dry_run_executed", s64.get("dry_run_executed"), False),
        ("replay_executed", s64.get("replay_executed"), False),
        ("ai_api_called", s64.get("ai_api_called"), False),
        ("discord_notification_sent", s64.get("discord_notification_sent"), False),
        ("mt5_order_sent", s64.get("mt5_order_sent"), False),
        ("final_signal_created", s64.get("final_signal_created"), False),
        ("next_recommended_step", s64.get("next_recommended_step"), "25C65_A002_FIXED_SCOPE_DRY_REVIEW_AUDIT_ONLY"),
        ("total_stop_rows", s64.get("total_stop_rows"), 0),
    ]
    contract_rows = []
    for i, (name, obs, exp) in enumerate(checks, 1):
        ok = obs == exp
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    contract_rows += [
        {"contract_id": "M020", "check": "25C64 contract no STOP", "observed": int((contract64.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract64.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M021", "check": "source package safe", "observed": int(source_package64.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()), "expected": 4, "status": "PASS" if int(source_package64.get("status", pd.Series(dtype=str)).astype(str).eq("PASS").sum()) == 4 else "STOP"},
        {"contract_id": "M022", "check": "fixed filters safe", "observed": int(fixed_filter64.get("status", pd.Series(dtype=str)).astype(str).eq("FIXED").sum()), "expected": 2, "status": "PASS" if int(fixed_filter64.get("status", pd.Series(dtype=str)).astype(str).eq("FIXED").sum()) == 2 else "STOP"},
        {"contract_id": "M023", "check": "guardrails blocked", "observed": int(guard64.get("status", pd.Series(dtype=str)).astype(str).eq("BLOCKED").sum()), "expected": 5, "status": "PASS" if int(guard64.get("status", pd.Series(dtype=str)).astype(str).eq("BLOCKED").sum()) == 5 else "STOP"},
        {"contract_id": "M024", "check": "next review ready", "observed": int(next_review64.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()), "expected": 4, "status": "PASS" if int(next_review64.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()) == 4 else "STOP"},
        {"contract_id": "M025", "check": "boundaries safe", "observed": not boundary64.get("allowed_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not boundary64.get("allowed_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"},
        {"contract_id": "M026", "check": "source file loaded", "observed": bool(source_exists and header_ok), "expected": True, "status": "PASS" if bool(source_exists and header_ok) else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c65_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C65_STOP_PACKAGE_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c65_a002_fixed_scope_dry_review_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    selected = source_df[source_df["filter"].isin(EXPECTED_FILTERS)].copy()
    selected["a002_fixed_scope_selected"] = True
    selected["condition_changed"] = False
    selected["source_recovery_executed"] = False
    selected["dry_review_only"] = True

    row_counts = selected.groupby("filter", dropna=False).agg(
        selected_rows=("filter", "size"),
        unique_entry_times=("entry_time", "nunique"),
        unique_datasets=("dataset", "nunique"),
    ).reset_index()
    for f in EXPECTED_FILTERS:
        if f not in set(row_counts["filter"].astype(str)):
            row_counts = pd.concat([row_counts, pd.DataFrame([{"filter": f, "selected_rows": 0, "unique_entry_times": 0, "unique_datasets": 0}])], ignore_index=True)
    row_counts["status"] = row_counts["selected_rows"].apply(lambda x: "READY_AUDIT_ONLY" if int(x) > 0 else "EMPTY")

    source_review = pd.DataFrame([
        {"review_id": "SR001", "item": "source_total_rows", "value": int(len(source_df)), "status": "PASS"},
        {"review_id": "SR002", "item": "selected_rows", "value": int(len(selected)), "status": "PASS" if len(selected) > 0 else "STOP"},
        {"review_id": "SR003", "item": "selected_unique_entry_times", "value": int(selected["entry_time"].nunique()) if not selected.empty else 0, "status": "PASS" if len(selected) > 0 else "STOP"},
        {"review_id": "SR004", "item": "filters_selected", "value": ";".join(EXPECTED_FILTERS), "status": "PASS"},
    ])
    guard = pd.DataFrame([
        {"guard_id": "G001", "item": "condition_change", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G002", "item": "source_recovery", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G003", "item": "source_mutation", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G004", "item": "replay_run", "allowed": False, "observed": False, "status": "PASS"},
        {"guard_id": "G005", "item": "external_actions", "allowed": False, "observed": False, "status": "PASS"},
    ])
    next_pkg = pd.DataFrame([
        {"package_id": "P001", "item": "selected_rows", "ready": len(selected) > 0, "status": "READY_AUDIT_ONLY" if len(selected) > 0 else "BLOCKED"},
        {"package_id": "P002", "item": "row_count_review", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P003", "item": "fixed_filter_review", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P004", "item": "no_external_actions", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P005", "item": "next_execution_review", "ready": len(selected) > 0, "status": "READY_AUDIT_ONLY" if len(selected) > 0 else "BLOCKED"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "replay_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "dry_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "external_actions", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_allowed = len(selected) > 0
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": bool(next_allowed), "purpose": "fixed-scope dry-run execution review", "execution_allowed_in_25c65": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c65": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C65 used 25C64 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed.", "status": "PASS"},
        {"note_id": "N003", "note": "Selected rows were copied to an audit-only output; no run action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c65_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c65_a002_fixed_scope_dry_review_summary.json"}]))
    write_csv(out / "05_25c65_source_row_review.csv", source_review)
    write_csv(out / "06_25c65_filter_row_counts.csv", row_counts)
    write_csv(out / "07_25c65_selected_source_rows.csv", selected)
    write_csv(out / "08_25c65_guardrail_matrix.csv", guard)
    write_csv(out / "09_25c65_next_execution_review_package.csv", next_pkg)
    write_csv(out / "10_25c65_boundary_matrix.csv", boundary)
    write_csv(out / "11_25c65_next_step_plan.csv", next_plan)
    write_csv(out / "12_25c65_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS if next_allowed else "25C65_STOP_SELECTED_ROWS_EMPTY_AUDIT_ONLY",
        "audit_only": True,
        "input_25c64_step": s64.get("step"),
        "input_25c64_status": s64.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "source_relative_path": source_rel,
        "source_total_rows": int(len(source_df)),
        "selected_rows": int(len(selected)),
        "selected_unique_entry_times": int(selected["entry_time"].nunique()) if not selected.empty else 0,
        "next_execution_review_package_ready": bool(next_allowed),
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "replay_executed": False,
        "dry_run_executed": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": NEXT_STEP if next_allowed else "STOP",
        "total_stop_rows": 0 if next_allowed else 1,
    }
    write_json(out / "02_25c65_a002_fixed_scope_dry_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C65 A002 fixed scope dry review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Source row review", "", md_table(source_review), "",
        "## Filter row counts", "", md_table(row_counts), "",
        "## Guardrails", "", md_table(guard), "",
        "## Next package", "", md_table(next_pkg), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c65_GOLD_V2_A002_FIXED_SCOPE_DRY_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "selected_rows": summary["selected_rows"], "selected_unique_entry_times": summary["selected_unique_entry_times"], "dry_run_executed": False, "condition_changed": False, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if next_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
