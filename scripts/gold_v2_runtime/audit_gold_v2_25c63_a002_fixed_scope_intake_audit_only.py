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

STEP = "25C63_A002_FIXED_SCOPE_INTAKE_AUDIT_ONLY"
STATUS = "A002_FIXED_SCOPE_INTAKE_READY_AUDIT_ONLY_NEXT_REVIEW_ALLOWED"
IN_DIR = "gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only"
OUT_DIR = "gold_v2_25c63_a002_fixed_scope_intake_audit_only"
NEXT_STEP = "25C64_A002_FIXED_SCOPE_PACKAGE_AUDIT_ONLY"
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


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
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

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN_DIR
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary62": input_dir / "02_25c62_a002_fixed_dry_run_direction_package_summary.json",
        "contract62": input_dir / "04_25c62_contract_audit.csv",
        "scope62": input_dir / "05_25c62_fixed_condition_scope_matrix.csv",
        "direction62": input_dir / "06_25c62_human_direction_required_matrix.csv",
        "derived62": input_dir / "07_25c62_derived_gate_matrix.csv",
        "boundary62": input_dir / "08_25c62_execution_boundary_matrix.csv",
        "next62": input_dir / "09_25c62_next_step_plan.csv",
        "notes62": input_dir / "10_25c62_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c63_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C63_STOP_MISSING_INPUT_AUDIT_ONLY"
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())}
        write_json(out / "02_25c63_a002_fixed_scope_intake_summary.json", summary)
        return 2

    s62 = read_json(req["summary62"])
    contract62 = read_csv(req["contract62"])
    scope62 = read_csv(req["scope62"])
    direction62 = read_csv(req["direction62"])
    derived62 = read_csv(req["derived62"])
    boundary62 = read_csv(req["boundary62"])
    next62 = read_csv(req["next62"])

    contract_rows = []
    checks = [
        ("step", s62.get("step"), "25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY"),
        ("status", s62.get("status"), "COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_READY_AUDIT_ONLY_HUMAN_DIRECTION_REQUIRED_NO_EXECUTION"),
        ("audit_only", s62.get("audit_only"), True),
        ("variant", s62.get("representative_variant_code"), "A002"),
        ("filters", s62.get("representative_filters"), EXPECTED_FILTERS),
        ("condition_changed", s62.get("condition_changed"), False),
        ("source_recovery_executed", s62.get("source_recovery_executed"), False),
        ("source_mutation_executed", s62.get("source_mutation_executed"), False),
        ("dry_run_executed", s62.get("dry_run_executed"), False),
        ("replay_executed", s62.get("replay_executed"), False),
        ("ai_api_called", s62.get("ai_api_called"), False),
        ("discord_notification_sent", s62.get("discord_notification_sent"), False),
        ("mt5_order_sent", s62.get("mt5_order_sent"), False),
        ("final_signal_created", s62.get("final_signal_created"), False),
        ("total_stop_rows", s62.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        ok = obs == exp
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    contract_rows.append({"contract_id": "M016", "check": "25C62 contract has no STOP", "observed": int((contract62.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract62.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"})
    contract_rows.append({"contract_id": "M017", "check": "scope fixed", "observed": len(scope62), "expected": 5, "status": "PASS" if len(scope62) == 5 else "STOP"})
    contract_rows.append({"contract_id": "M018", "check": "direction rows", "observed": len(direction62), "expected": 3, "status": "PASS" if len(direction62) == 3 else "STOP"})
    contract_rows.append({"contract_id": "M019", "check": "derived gates closed", "observed": not derived62.get("open_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not derived62.get("open_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"})
    contract_rows.append({"contract_id": "M020", "check": "boundaries safe", "observed": not boundary62.get("allowed_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not boundary62.get("allowed_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"})
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c63_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C63_STOP_25C62_CONTRACT_UNSAFE_AUDIT_ONLY"
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())}
        write_json(out / "02_25c63_a002_fixed_scope_intake_summary.json", summary)
        return 2

    direction = pd.DataFrame([
        {"item_id": "DI001", "item": "existing_bound_source", "received": True, "effect_now": "audit_package_only", "status": "RECEIVED"},
        {"item_id": "DI002", "item": "A002_fixed_filters", "received": True, "effect_now": "audit_package_only", "status": "RECEIVED"},
        {"item_id": "DI003", "item": "fixed_scope_review_without_external_actions", "received": True, "effect_now": "audit_package_only", "status": "RECEIVED"},
    ])
    scope = pd.DataFrame([
        {"scope_id": "S001", "item": "variant", "value": "A002", "fixed": True, "status": "FIXED"},
        {"scope_id": "S002", "item": "filter_1", "value": EXPECTED_FILTERS[0], "fixed": True, "status": "FIXED"},
        {"scope_id": "S003", "item": "filter_2", "value": EXPECTED_FILTERS[1], "fixed": True, "status": "FIXED"},
        {"scope_id": "S004", "item": "source_recovery", "value": "disabled", "fixed": True, "status": "BLOCKED"},
        {"scope_id": "S005", "item": "external_actions", "value": "disabled", "fixed": True, "status": "BLOCKED"},
    ])
    package = pd.DataFrame([
        {"package_id": "P001", "item": "source", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P002", "item": "fixed_filters", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P003", "item": "no_external_actions", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P004", "item": "next_review", "ready": True, "status": "READY_AUDIT_ONLY"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "replay_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "dry_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "external_actions", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "prepare fixed-scope next review", "execution_allowed_in_25c63": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c63": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C63 used 25C62 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed.", "status": "PASS"},
        {"note_id": "N003", "note": "No condition/source/external action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c63_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c63_a002_fixed_scope_intake_summary.json"}]))
    write_csv(out / "05_25c63_direction_intake_matrix.csv", direction)
    write_csv(out / "06_25c63_fixed_scope_matrix.csv", scope)
    write_csv(out / "07_25c63_next_package_matrix.csv", package)
    write_csv(out / "08_25c63_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c63_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c63_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "input_25c62_step": s62.get("step"),
        "input_25c62_status": s62.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "direction_items_received": 3,
        "fixed_scope_package_ready": True,
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
        "next_recommended_step": NEXT_STEP,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c63_a002_fixed_scope_intake_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C63 A002 fixed scope intake audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Direction intake", "", md_table(direction), "",
        "## Fixed scope", "", md_table(scope), "",
        "## Next package", "", md_table(package), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c63_GOLD_V2_A002_FIXED_SCOPE_INTAKE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "fixed_scope_package_ready": True, "dry_run_executed": False, "condition_changed": False, "next_recommended_step": NEXT_STEP}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
