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

STEP = "25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED"
STOP_MISSING = "25C43_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C43_STOP_25C42_CONTRACT_UNSAFE_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only"
IN42 = "gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only"
EXPECTED_STEP_42 = "25C42_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY"
EXPECTED_STATUS_42 = "COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY"
EXPECTED_NEXT_42 = "25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY"
KEY = ["dataset", "entry_time", "policy"]


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
    last = None
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


def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def status_from_exists(path: Path) -> str:
    return "PASS" if lp(path).exists() else "STOP"


def classify_driver(baseline_merge: object) -> str:
    bm = str(baseline_merge)
    if bm == "both":
        return "INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"
    if bm == "right_only":
        return "PERSISTENT_BASELINE_RIGHT_ONLY"
    return "UNKNOWN_BASELINE_DRIVER"


def file_request_df() -> pd.DataFrame:
    unnecessary = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "new dry-run outputs", "AI review ledgers", "full 25C42 full-row CSV if right_only CSV is already available"]
    necessary = [
        "01_25c43_GOLD_V2_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY_REPORT.md",
        "02_25c43_coreb_g1_right_only_driver_review_summary.json",
        "03_25c43_input_audit.csv",
        "04_25c43_right_only_driver_classification_matrix.csv",
        "05_25c43_incremental_damage_by_variant_dataset_policy.csv",
        "06_25c43_right_only_variant_overlap_matrix.csv",
        "07_25c43_incremental_damage_monthly_concentration_matrix.csv",
        "08_25c43_driver_review_findings_matrix.csv",
        "09_25c43_execution_boundary_matrix.csv",
        "10_25c43_acceptance_gate_matrix.csv",
        "11_25c43_next_step_plan.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )


def write_stop(out: Path, status: str, input_audit: pd.DataFrame, diagnostic: pd.DataFrame, stop_rows: int) -> None:
    empty = pd.DataFrame()
    write_csv(out / "00_不要_25c43_file_request_list.csv", file_request_df())
    write_csv(out / "04_25c43_right_only_driver_classification_matrix.csv", empty)
    write_csv(out / "05_25c43_incremental_damage_by_variant_dataset_policy.csv", empty)
    write_csv(out / "06_25c43_right_only_variant_overlap_matrix.csv", empty)
    write_csv(out / "07_25c43_incremental_damage_monthly_concentration_matrix.csv", empty)
    write_csv(out / "08_25c43_driver_review_findings_matrix.csv", diagnostic)
    boundary = pd.DataFrame([
        {"boundary": "right_only_driver_review", "allowed": False, "observed": False},
        {"boundary": "new_dry_run", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
    ])
    write_csv(out / "09_25c43_execution_boundary_matrix.csv", boundary)
    write_csv(out / "10_25c43_acceptance_gate_matrix.csv", diagnostic)
    write_csv(out / "11_25c43_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status}]))
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "driver_review_executed": False,
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
        "total_stop_rows": int(stop_rows),
    }
    write_json(out / "02_25c43_coreb_g1_right_only_driver_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C43 CoreB G1 right_only driver review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Diagnostic",
        "",
        md_table(diagnostic),
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Safety",
        "",
        "Stop status written. No dry-run, source recovery, live evaluator, Discord, MT5, AI API, live hook, or final signal executed.",
    ])
    lp(out / "01_25c43_GOLD_V2_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base = fx_outputs() / IN42
    req = {
        "s42": base / "02_25c42_coreb_g1_right_only_row_level_export_summary.json",
        "right_only_rows": base / "05_25c42_variant_right_only_row_level_compare_rows.csv",
        "by_policy42": base / "06_25c42_right_only_by_variant_dataset_policy.csv",
        "recon42": base / "07_25c42_right_only_export_reconciliation_matrix.csv",
        "gates42": base / "09_25c42_acceptance_gate_matrix.csv",
        "next42": base / "10_25c42_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()])
    write_csv(out / "03_25c43_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        write_stop(out, STOP_MISSING, input_audit, input_audit, int((input_audit["status"] == "STOP").sum()))
        return 2

    s42 = read_json(req["s42"])
    recon42 = read_csv(req["recon42"])
    gates42 = read_csv(req["gates42"])
    next42 = read_csv(req["next42"])
    contract_rows = [
        {"contract_id": "C001", "check": "25C42 step matches expected", "observed": s42.get("step"), "status": "PASS" if s42.get("step") == EXPECTED_STEP_42 else "STOP"},
        {"contract_id": "C002", "check": "25C42 status driver-review-ready", "observed": s42.get("status"), "status": "PASS" if s42.get("status") == EXPECTED_STATUS_42 else "STOP"},
        {"contract_id": "C003", "check": "25C42 audit_only true", "observed": s42.get("audit_only"), "status": "PASS" if as_bool(s42.get("audit_only", False)) else "STOP"},
        {"contract_id": "C004", "check": "25C42 reconciliation passed", "observed": s42.get("reconciliation_passed"), "status": "PASS" if as_bool(s42.get("reconciliation_passed", False)) else "STOP"},
        {"contract_id": "C005", "check": "25C42 right_only rows exported", "observed": s42.get("right_only_row_count"), "status": "PASS" if int(s42.get("right_only_row_count", 0)) > 0 else "STOP"},
        {"contract_id": "C006", "check": "25C42 dry_run_executed false", "observed": s42.get("dry_run_executed"), "status": "PASS" if not as_bool(s42.get("dry_run_executed", True)) else "STOP"},
        {"contract_id": "C007", "check": "25C42 external/live flags false", "observed": "ai_api/live/discord/mt5/final all false", "status": "PASS" if not any(as_bool(s42.get(k, True)) for k in ["coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created"]) else "STOP"},
        {"contract_id": "C008", "check": "25C42 next recommended step is 25C43", "observed": s42.get("next_recommended_step"), "status": "PASS" if s42.get("next_recommended_step") == EXPECTED_NEXT_42 else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    if bool((contract["status"] == "STOP").any()):
        write_stop(out, STOP_CONTRACT, input_audit, contract, int((contract["status"] == "STOP").sum()))
        return 2

    right = read_csv(req["right_only_rows"])
    right["driver_class"] = right["baseline_merge"].apply(classify_driver)
    right["entry_month"] = pd.to_datetime(right["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    write_csv(out / "04_25c43_right_only_driver_classification_matrix.csv", right)

    inc = right[right["driver_class"].eq("INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH")].copy()
    inc_by = inc.groupby(["variant", "dataset", "policy"], dropna=False).size().reset_index(name="incremental_damage_rows")
    base_persist_by = right[right["driver_class"].eq("PERSISTENT_BASELINE_RIGHT_ONLY")].groupby(["variant", "dataset", "policy"], dropna=False).size().reset_index(name="persistent_baseline_right_only_rows")
    inc_by = inc_by.merge(base_persist_by, on=["variant", "dataset", "policy"], how="outer").fillna(0)
    for c in ["incremental_damage_rows", "persistent_baseline_right_only_rows"]:
        inc_by[c] = inc_by[c].astype(int)
    write_csv(out / "05_25c43_incremental_damage_by_variant_dataset_policy.csv", inc_by.sort_values(["variant", "dataset", "policy"]))

    sets = {v: set(map(tuple, df[KEY].astype(str).values)) for v, df in right.groupby("variant")}
    overlap_rows = []
    variants = sorted(sets)
    for a in variants:
        for b in variants:
            overlap_rows.append({
                "variant_a": a,
                "variant_b": b,
                "a_count": len(sets[a]),
                "b_count": len(sets[b]),
                "intersection_count": len(sets[a] & sets[b]),
                "a_only_count": len(sets[a] - sets[b]),
                "b_only_count": len(sets[b] - sets[a]),
                "identical_set": sets[a] == sets[b],
            })
    overlap = pd.DataFrame(overlap_rows)
    write_csv(out / "06_25c43_right_only_variant_overlap_matrix.csv", overlap)

    monthly = inc.groupby(["entry_month", "variant"], dropna=False).size().reset_index(name="incremental_damage_rows")
    write_csv(out / "07_25c43_incremental_damage_monthly_concentration_matrix.csv", monthly.sort_values(["entry_month", "variant"]))

    driver_summary = right.groupby(["variant", "driver_class"], dropna=False).size().unstack(fill_value=0).reset_index()
    for col in ["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH", "PERSISTENT_BASELINE_RIGHT_ONLY", "UNKNOWN_BASELINE_DRIVER"]:
        if col not in driver_summary.columns:
            driver_summary[col] = 0
    driver_summary["total_right_only_rows"] = driver_summary[["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH", "PERSISTENT_BASELINE_RIGHT_ONLY", "UNKNOWN_BASELINE_DRIVER"]].sum(axis=1)
    driver_summary["incremental_damage_share_pct"] = (driver_summary["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"] / driver_summary["total_right_only_rows"].replace(0, pd.NA) * 100).round(2).fillna(0)

    a002_set = sets.get("A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U", set())
    a004_set = sets.get("A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR", set())
    findings = []
    for _, r in driver_summary.iterrows():
        v = r["variant"]
        findings.append({
            "finding_id": f"F_{v[:4]}",
            "variant": v,
            "total_right_only_rows": int(r["total_right_only_rows"]),
            "incremental_damage_rows": int(r["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"]),
            "persistent_baseline_right_only_rows": int(r["PERSISTENT_BASELINE_RIGHT_ONLY"]),
            "incremental_damage_share_pct": float(r["incremental_damage_share_pct"]),
            "interpretation": "target-matching baseline rows removed by adjusted narrowing" if int(r["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"]) > 0 else "no incremental damage detected",
            "approval_status": "NOT_APPROVED_REVIEW_ONLY",
            "live_ready": False,
        })
    findings.append({
        "finding_id": "F_EQUIV_A002_A004",
        "variant": "A002_vs_A004",
        "total_right_only_rows": len(a002_set),
        "incremental_damage_rows": int(driver_summary[driver_summary["variant"].eq("A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U")]["INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"].iloc[0]) if not driver_summary[driver_summary["variant"].eq("A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U")].empty else 0,
        "persistent_baseline_right_only_rows": int(driver_summary[driver_summary["variant"].eq("A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U")]["PERSISTENT_BASELINE_RIGHT_ONLY"].iloc[0]) if not driver_summary[driver_summary["variant"].eq("A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U")].empty else 0,
        "incremental_damage_share_pct": 0,
        "interpretation": "A002 and A004 right_only sets are identical" if a002_set == a004_set else "A002 and A004 differ; inspect overlap matrix",
        "approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "live_ready": False,
    })
    findings_df = pd.DataFrame(findings)
    write_csv(out / "08_25c43_driver_review_findings_matrix.csv", findings_df)

    boundary = pd.DataFrame([
        {"boundary": "right_only_driver_review", "allowed": True, "observed": True},
        {"boundary": "read_25c42_right_only_rows", "allowed": True, "observed": True},
        {"boundary": "new_dry_run", "allowed": False, "observed": False},
        {"boundary": "new_variant_search", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "approve_best_variant", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "09_25c43_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C42 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "right_only driver classification created", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "incremental damage rows found", "observed": len(inc) > 0, "status": "PASS" if len(inc) > 0 else "REVIEW"},
        {"gate_id": "G004", "gate": "future dry-run allowed now", "observed": False, "status": "BLOCKED_PLAN_AND_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G005", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "10_25c43_acceptance_gate_matrix.csv", gates)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY", "allowed_now": True, "purpose": "plan whether to stop, design retention-aware recovery, or request a later accepted dry-run; no execution", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c43": False},
        {"rank": 2, "next_step": "future adjusted narrowing dry-run", "allowed_now": False, "purpose": "blocked until 25C44 plan and explicit acceptance", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c43": False},
        {"rank": 3, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c43": False},
    ])
    write_csv(out / "11_25c43_next_step_plan.csv", next_plan)
    write_csv(out / "00_不要_25c43_file_request_list.csv", file_request_df())

    total_right = int(len(right))
    total_inc = int(len(inc))
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "driver_review_executed": True,
        "dry_run_executed": False,
        "condition_changed": False,
        "full_coreb_parity": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "best_variant_approved": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "right_only_row_count": total_right,
        "incremental_damage_row_count": total_inc,
        "persistent_baseline_right_only_row_count": int((right["driver_class"] == "PERSISTENT_BASELINE_RIGHT_ONLY").sum()),
        "a002_a004_right_only_sets_identical": bool(a002_set == a004_set),
        "next_recommended_step": "25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY",
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c43_coreb_g1_right_only_driver_review_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C43 CoreB G1 right_only driver review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{STATUS}`",
        "",
        "## Scope",
        "",
        "This step reviews exported 25C42 right_only rows only. It does not run a dry-run, change conditions, approve variants, or unblock live behavior.",
        "",
        "## 25C42 contract audit",
        "",
        md_table(contract),
        "",
        "## Driver summary by variant",
        "",
        md_table(driver_summary),
        "",
        "## Incremental damage by variant / dataset / policy",
        "",
        md_table(inc_by),
        "",
        "## Variant overlap matrix",
        "",
        md_table(overlap),
        "",
        "## Monthly incremental damage concentration",
        "",
        md_table(monthly),
        "",
        "## Findings",
        "",
        md_table(findings_df),
        "",
        "## Execution boundaries",
        "",
        md_table(boundary),
        "",
        "## Acceptance gates",
        "",
        md_table(gates),
        "",
        "## File request list",
        "",
        "```text",
        "00_不要_貼らなくてOK",
        *[f"00-{i+1}. {x}" for i, x in enumerate(file_request_df()[file_request_df()["section"].eq("00_不要_貼らなくてOK")]["item"].tolist())],
        "",
        "必要・見るファイル",
        *[f"{i+1:02d}. {x}" for i, x in enumerate(file_request_df()[file_request_df()["section"].eq("必要・見るファイル")]["item"].tolist())],
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- 25C43 is review-only and does not approve any variant.",
        "- CoreB live evaluator, Discord, MT5, AI API, live hook, and final signal remain blocked.",
        "- Future dry-run remains blocked until route plan and separate explicit human acceptance.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c43_GOLD_V2_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "right_only_row_count": total_right,
        "incremental_damage_row_count": total_inc,
        "a002_a004_right_only_sets_identical": bool(a002_set == a004_set),
        "next_recommended_step": summary["next_recommended_step"],
        "dry_run_executed": False,
        "ai_api_called": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
