#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

STEP = "25C64_A002_FIXED_SCOPE_PACKAGE_AUDIT_ONLY"
STATUS = "A002_FIXED_SCOPE_PACKAGE_READY_AUDIT_ONLY_NEXT_DRY_REVIEW_ALLOWED"
IN_DIR = "gold_v2_25c63_a002_fixed_scope_intake_audit_only"
OUT_DIR = "gold_v2_25c64_a002_fixed_scope_package_audit_only"
NEXT_STEP = "25C65_A002_FIXED_SCOPE_DRY_REVIEW_AUDIT_ONLY"
SOURCE_REL = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv"
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


def read_header(p: Path) -> list[str]:
    with lp(p).open("r", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


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
        "summary63": input_dir / "02_25c63_a002_fixed_scope_intake_summary.json",
        "contract63": input_dir / "04_25c63_contract_audit.csv",
        "direction63": input_dir / "05_25c63_direction_intake_matrix.csv",
        "scope63": input_dir / "06_25c63_fixed_scope_matrix.csv",
        "package63": input_dir / "07_25c63_next_package_matrix.csv",
        "boundary63": input_dir / "08_25c63_boundary_matrix.csv",
        "next63": input_dir / "09_25c63_next_step_plan.csv",
        "notes63": input_dir / "10_25c63_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c64_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C64_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c64_a002_fixed_scope_package_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s63 = read_json(req["summary63"])
    contract63 = read_csv(req["contract63"])
    direction63 = read_csv(req["direction63"])
    scope63 = read_csv(req["scope63"])
    package63 = read_csv(req["package63"])
    boundary63 = read_csv(req["boundary63"])
    next63 = read_csv(req["next63"])
    notes63 = read_csv(req["notes63"])

    contract_rows = []
    checks = [
        ("step", s63.get("step"), "25C63_A002_FIXED_SCOPE_INTAKE_AUDIT_ONLY"),
        ("status", s63.get("status"), "A002_FIXED_SCOPE_INTAKE_READY_AUDIT_ONLY_NEXT_REVIEW_ALLOWED"),
        ("audit_only", s63.get("audit_only"), True),
        ("variant", s63.get("representative_variant_code"), "A002"),
        ("filters", s63.get("representative_filters"), EXPECTED_FILTERS),
        ("direction_items_received", s63.get("direction_items_received"), 3),
        ("fixed_scope_package_ready", s63.get("fixed_scope_package_ready"), True),
        ("condition_changed", s63.get("condition_changed"), False),
        ("source_recovery_executed", s63.get("source_recovery_executed"), False),
        ("source_mutation_executed", s63.get("source_mutation_executed"), False),
        ("dry_run_executed", s63.get("dry_run_executed"), False),
        ("replay_executed", s63.get("replay_executed"), False),
        ("ai_api_called", s63.get("ai_api_called"), False),
        ("discord_notification_sent", s63.get("discord_notification_sent"), False),
        ("mt5_order_sent", s63.get("mt5_order_sent"), False),
        ("final_signal_created", s63.get("final_signal_created"), False),
        ("next_recommended_step", s63.get("next_recommended_step"), "25C64_A002_FIXED_SCOPE_PACKAGE_AUDIT_ONLY"),
        ("total_stop_rows", s63.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        ok = obs == exp
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    contract_rows += [
        {"contract_id": "M019", "check": "25C63 contract no STOP", "observed": int((contract63.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract63.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M020", "check": "direction received", "observed": int(direction63.get("status", pd.Series(dtype=str)).astype(str).eq("RECEIVED").sum()), "expected": 3, "status": "PASS" if int(direction63.get("status", pd.Series(dtype=str)).astype(str).eq("RECEIVED").sum()) == 3 else "STOP"},
        {"contract_id": "M021", "check": "scope fixed", "observed": len(scope63), "expected": 5, "status": "PASS" if len(scope63) == 5 else "STOP"},
        {"contract_id": "M022", "check": "package ready", "observed": int(package63.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()), "expected": 4, "status": "PASS" if int(package63.get("status", pd.Series(dtype=str)).astype(str).eq("READY_AUDIT_ONLY").sum()) == 4 else "STOP"},
        {"contract_id": "M023", "check": "boundaries safe", "observed": not boundary63.get("allowed_now", pd.Series(dtype=bool)).apply(b).any(), "expected": True, "status": "PASS" if not boundary63.get("allowed_now", pd.Series(dtype=bool)).apply(b).any() else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c64_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C64_STOP_25C63_CONTRACT_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c64_a002_fixed_scope_package_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    source_path = root / SOURCE_REL
    source_exists = lp(source_path).exists()
    try:
        header = read_header(source_path) if source_exists else []
    except Exception:
        header = []
    header_ok = header == EXPECTED_SOURCE_COLUMNS
    source_matrix = pd.DataFrame([
        {"source_id": "SRC001", "item": "relative_path", "value": SOURCE_REL, "status": "PASS"},
        {"source_id": "SRC002", "item": "exists", "value": source_exists, "status": "PASS" if source_exists else "STOP"},
        {"source_id": "SRC003", "item": "header_ok", "value": header_ok, "status": "PASS" if header_ok else "STOP"},
        {"source_id": "SRC004", "item": "source_recovery", "value": "disabled", "status": "PASS"},
    ])
    fixed_filter = pd.DataFrame([
        {"filter_id": "F001", "filter": EXPECTED_FILTERS[0], "fixed": True, "status": "FIXED"},
        {"filter_id": "F002", "filter": EXPECTED_FILTERS[1], "fixed": True, "status": "FIXED"},
    ])
    guard = pd.DataFrame([
        {"guard_id": "G001", "item": "condition_change", "allowed": False, "status": "BLOCKED"},
        {"guard_id": "G002", "item": "source_recovery", "allowed": False, "status": "BLOCKED"},
        {"guard_id": "G003", "item": "external_actions", "allowed": False, "status": "BLOCKED"},
        {"guard_id": "G004", "item": "ai_discord_mt5_live_final", "allowed": False, "status": "BLOCKED"},
        {"guard_id": "G005", "item": "no_signal_notify", "allowed": False, "status": "BLOCKED"},
    ])
    next_review = pd.DataFrame([
        {"package_id": "P001", "item": "source_file", "ready": bool(source_exists and header_ok), "status": "READY_AUDIT_ONLY" if source_exists and header_ok else "BLOCKED"},
        {"package_id": "P002", "item": "fixed_filters", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P003", "item": "guardrails", "ready": True, "status": "READY_AUDIT_ONLY"},
        {"package_id": "P004", "item": "next_review", "ready": bool(source_exists and header_ok), "status": "READY_AUDIT_ONLY" if source_exists and header_ok else "BLOCKED"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "replay_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "dry_run", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B005", "boundary": "external_actions", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    next_allowed = bool(source_exists and header_ok)
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": next_allowed, "purpose": "run next fixed-scope audit review", "execution_allowed_in_25c64": False, "condition_change_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c64": False, "condition_change_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C64 used 25C63 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 and retained filters remain fixed.", "status": "PASS"},
        {"note_id": "N003", "note": "No condition/source/external action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c64_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c64_a002_fixed_scope_package_summary.json"}]))
    write_csv(out / "05_25c64_source_package_matrix.csv", source_matrix)
    write_csv(out / "06_25c64_fixed_filter_matrix.csv", fixed_filter)
    write_csv(out / "07_25c64_guardrail_matrix.csv", guard)
    write_csv(out / "08_25c64_next_review_package_matrix.csv", next_review)
    write_csv(out / "09_25c64_boundary_matrix.csv", boundary)
    write_csv(out / "10_25c64_next_step_plan.csv", next_plan)
    write_csv(out / "11_25c64_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS if next_allowed else "25C64_STOP_SOURCE_PACKAGE_UNREADY_AUDIT_ONLY",
        "audit_only": True,
        "input_25c63_step": s63.get("step"),
        "input_25c63_status": s63.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "source_relative_path": SOURCE_REL,
        "source_exists": source_exists,
        "source_header_ok": header_ok,
        "next_review_package_ready": next_allowed,
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
        "total_stop_rows": 0 if next_allowed else int((source_matrix["status"] == "STOP").sum()),
    }
    write_json(out / "02_25c64_a002_fixed_scope_package_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C64 A002 fixed scope package audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Source package", "", md_table(source_matrix), "",
        "## Fixed filters", "", md_table(fixed_filter), "",
        "## Guardrails", "", md_table(guard), "",
        "## Next review package", "", md_table(next_review), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c64_GOLD_V2_A002_FIXED_SCOPE_PACKAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "next_review_package_ready": next_allowed, "dry_run_executed": False, "condition_changed": False, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if next_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
