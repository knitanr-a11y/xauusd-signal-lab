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

STEP = "25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY"
STATUS = "COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_READY_AUDIT_ONLY_FILTER_ATTRIBUTION_REQUIRED"
STOP_MISSING = "25C44_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C44_STOP_25C43_CONTRACT_UNSAFE_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only"
IN43 = "gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only"
EXPECTED_STEP_43 = "25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY"
EXPECTED_STATUS_43 = "COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED"
EXPECTED_NEXT_43 = "25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY"
NEXT_STEP = "25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY"


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


def file_request_df() -> pd.DataFrame:
    unnecessary = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "new dry-run outputs", "AI review ledgers", "full 25C42 full-row CSV"]
    necessary = [
        "01_25c44_GOLD_V2_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY_REPORT.md",
        "02_25c44_coreb_g1_right_only_damage_route_plan_summary.json",
        "03_25c44_input_audit.csv",
        "04_25c44_route_evidence_matrix.csv",
        "05_25c44_route_option_matrix.csv",
        "06_25c44_route_recommendation_matrix.csv",
        "07_25c44_dry_run_blocker_matrix.csv",
        "08_25c44_execution_boundary_matrix.csv",
        "09_25c44_acceptance_gate_matrix.csv",
        "10_25c44_next_step_plan.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
    )


def write_stop(out: Path, status: str, input_audit: pd.DataFrame, diagnostic: pd.DataFrame, stop_rows: int) -> None:
    write_csv(out / "00_不要_25c44_file_request_list.csv", file_request_df())
    for name in [
        "04_25c44_route_evidence_matrix.csv",
        "05_25c44_route_option_matrix.csv",
        "06_25c44_route_recommendation_matrix.csv",
        "07_25c44_dry_run_blocker_matrix.csv",
        "08_25c44_execution_boundary_matrix.csv",
        "09_25c44_acceptance_gate_matrix.csv",
    ]:
        write_csv(out / name, diagnostic)
    write_csv(out / "10_25c44_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status}]))
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "route_plan_only": True,
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
    write_json(out / "02_25c44_coreb_g1_right_only_damage_route_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C44 CoreB G1 right_only damage route plan audit-only report",
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
    lp(out / "01_25c44_GOLD_V2_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base = fx_outputs() / IN43
    req = {
        "s43": base / "02_25c43_coreb_g1_right_only_driver_review_summary.json",
        "incremental_by_policy": base / "05_25c43_incremental_damage_by_variant_dataset_policy.csv",
        "overlap": base / "06_25c43_right_only_variant_overlap_matrix.csv",
        "findings": base / "08_25c43_driver_review_findings_matrix.csv",
        "boundary43": base / "09_25c43_execution_boundary_matrix.csv",
        "gates43": base / "10_25c43_acceptance_gate_matrix.csv",
        "next43": base / "11_25c43_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()])
    write_csv(out / "03_25c44_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        write_stop(out, STOP_MISSING, input_audit, input_audit, int((input_audit["status"] == "STOP").sum()))
        return 2

    s43 = read_json(req["s43"])
    inc = read_csv(req["incremental_by_policy"])
    overlap = read_csv(req["overlap"])
    findings = read_csv(req["findings"])
    next43 = read_csv(req["next43"])

    contract = pd.DataFrame([
        {"contract_id": "C001", "check": "25C43 step matches expected", "observed": s43.get("step"), "status": "PASS" if s43.get("step") == EXPECTED_STEP_43 else "STOP"},
        {"contract_id": "C002", "check": "25C43 status next-plan-required", "observed": s43.get("status"), "status": "PASS" if s43.get("status") == EXPECTED_STATUS_43 else "STOP"},
        {"contract_id": "C003", "check": "25C43 audit_only true", "observed": s43.get("audit_only"), "status": "PASS" if as_bool(s43.get("audit_only", False)) else "STOP"},
        {"contract_id": "C004", "check": "25C43 driver review executed", "observed": s43.get("driver_review_executed"), "status": "PASS" if as_bool(s43.get("driver_review_executed", False)) else "STOP"},
        {"contract_id": "C005", "check": "incremental damage rows found", "observed": s43.get("incremental_damage_row_count"), "status": "PASS" if int(s43.get("incremental_damage_row_count", 0)) > 0 else "STOP"},
        {"contract_id": "C006", "check": "25C43 dry_run false", "observed": s43.get("dry_run_executed"), "status": "PASS" if not as_bool(s43.get("dry_run_executed", True)) else "STOP"},
        {"contract_id": "C007", "check": "25C43 external/live flags false", "observed": "all false", "status": "PASS" if not any(as_bool(s43.get(k, True)) for k in ["coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created"]) else "STOP"},
        {"contract_id": "C008", "check": "25C43 next recommended step is 25C44", "observed": s43.get("next_recommended_step"), "status": "PASS" if s43.get("next_recommended_step") == EXPECTED_NEXT_43 else "STOP"},
    ])
    if bool((contract["status"] == "STOP").any()):
        write_stop(out, STOP_CONTRACT, input_audit, contract, int((contract["status"] == "STOP").sum()))
        return 2

    inc_total = int(pd.to_numeric(inc.get("incremental_damage_rows", pd.Series(dtype=int)), errors="coerce").fillna(0).sum())
    persistent_total = int(pd.to_numeric(inc.get("persistent_baseline_right_only_rows", pd.Series(dtype=int)), errors="coerce").fillna(0).sum())
    a002_a004_identical = bool(s43.get("a002_a004_right_only_sets_identical", False))

    route_evidence = pd.DataFrame([
        {"evidence_id": "E001", "evidence": "incremental damage exists", "observed": inc_total, "interpretation": "adjusted narrowing removes baseline target-matching rows"},
        {"evidence_id": "E002", "evidence": "persistent baseline right_only exists", "observed": persistent_total, "interpretation": "part of right_only is not caused by adjusted narrowing"},
        {"evidence_id": "E003", "evidence": "A002 and A004 identical", "observed": a002_a004_identical, "interpretation": "A004 adds no aggregate/right_only-set benefit over A002"},
        {"evidence_id": "E004", "evidence": "least damaging tested variants still damage target rows", "observed": "A002/A004 incremental_damage_rows=69", "interpretation": "do not adopt as-is; need filter attribution before recovery design"},
    ])
    write_csv(out / "04_25c44_route_evidence_matrix.csv", route_evidence)

    route_options = pd.DataFrame([
        {"route_id": "R001", "route": "INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST", "rank": 1, "recommended": True, "allowed_now": True, "executes_dry_run": False, "changes_conditions": False, "reason": "25C43 identifies damaged keys but not source filters; attribute damaged keys to baseline filters before recovery planning", "next_step": NEXT_STEP},
        {"route_id": "R002", "route": "RETENTION_AWARE_RECOVERY_PLAN_AFTER_ATTRIBUTION", "rank": 2, "recommended": False, "allowed_now": False, "executes_dry_run": False, "changes_conditions": False, "reason": "needs filter attribution first", "next_step": "blocked until 25C45"},
        {"route_id": "R003", "route": "ADOPT_A002_OR_A004_AS_LEAST_DAMAGING", "rank": 3, "recommended": False, "allowed_now": False, "executes_dry_run": False, "changes_conditions": False, "reason": "A002/A004 still create 69 incremental damaged target rows and are not exact", "next_step": "blocked"},
        {"route_id": "R004", "route": "NEW_DRY_RUN_NOW", "rank": 4, "recommended": False, "allowed_now": False, "executes_dry_run": True, "changes_conditions": False, "reason": "requires route plan, attribution, and explicit later acceptance", "next_step": "blocked"},
        {"route_id": "R005", "route": "COREB_LIVE_OR_EXTERNAL_ACTIONS", "rank": 5, "recommended": False, "allowed_now": False, "executes_dry_run": False, "changes_conditions": False, "reason": "no exact match and no source recovery approval", "next_step": "blocked"},
    ])
    write_csv(out / "05_25c44_route_option_matrix.csv", route_options)

    recommendation = pd.DataFrame([
        {"recommendation_id": "REC001", "selected_route_id": "R001", "selected_route": "INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST", "incremental_damage_rows": inc_total, "persistent_baseline_right_only_rows": persistent_total, "a002_a004_identical": a002_a004_identical, "reason": "before designing any retention-aware bundle, identify which baseline filters produce the target-matching rows damaged by adjusted exclusions", "next_recommended_step": NEXT_STEP, "dry_run_allowed_next": False, "live_unblock_allowed_next": False},
    ])
    write_csv(out / "06_25c44_route_recommendation_matrix.csv", recommendation)

    blockers = pd.DataFrame([
        {"blocker_id": "B001", "blocker": "least damaging variant still loses baseline both rows", "observed": "A002/A004 incremental_damage_rows=69", "blocks_dry_run_now": True},
        {"blocker_id": "B002", "blocker": "damaged rows not yet attributed to original filters", "observed": True, "blocks_dry_run_now": True},
        {"blocker_id": "B003", "blocker": "no exact match", "observed": True, "blocks_live_now": True},
        {"blocker_id": "B004", "blocker": "source recovery not approved", "observed": True, "blocks_live_now": True},
    ])
    write_csv(out / "07_25c44_dry_run_blocker_matrix.csv", blockers)

    boundary = pd.DataFrame([
        {"boundary": "route_plan_only", "allowed": True, "observed": True},
        {"boundary": "read_25c43_outputs", "allowed": True, "observed": True},
        {"boundary": "run_new_dry_run", "allowed": False, "observed": False},
        {"boundary": "new_variant_search", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "approve_variant", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "08_25c44_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C43 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "route selected", "observed": "INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST", "status": "PASS"},
        {"gate_id": "G003", "gate": "25C45 attribution can be planned now", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "future dry-run allowed now", "observed": False, "status": "BLOCKED_ATTRIBUTION_AND_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G005", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "09_25c44_acceptance_gate_matrix.csv", gates)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "attribute incremental damage keys to source replay filters; no dry-run", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c44": False},
        {"rank": 2, "next_step": "retention-aware recovery plan", "allowed_now": False, "purpose": "blocked until filter attribution", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c44": False},
        {"rank": 3, "next_step": "future adjusted narrowing dry-run", "allowed_now": False, "purpose": "blocked until attribution, plan, and explicit acceptance", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c44": False},
        {"rank": 4, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c44": False},
    ])
    write_csv(out / "10_25c44_next_step_plan.csv", next_plan)
    write_csv(out / "00_不要_25c44_file_request_list.csv", file_request_df())

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "route_plan_only": True,
        "dry_run_executed": False,
        "condition_changed": False,
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
        "incremental_damage_rows": inc_total,
        "persistent_baseline_right_only_rows": persistent_total,
        "a002_a004_right_only_sets_identical": a002_a004_identical,
        "selected_route": "INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST",
        "next_recommended_step": NEXT_STEP,
        "requires_human_acceptance_before_next_dry_run": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c44_coreb_g1_right_only_damage_route_plan_summary.json", summary)

    reqdf = file_request_df()
    report = "\n".join([
        "# GOLD V2 25C44 CoreB G1 right_only damage route plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{STATUS}`",
        "",
        "## Scope",
        "",
        "This is a route plan only. It does not run a dry-run, search variants, change conditions, approve variants, or unblock live behavior.",
        "",
        "## 25C43 contract audit",
        "",
        md_table(contract),
        "",
        "## Route evidence",
        "",
        md_table(route_evidence),
        "",
        "## Route options",
        "",
        md_table(route_options),
        "",
        "## Route recommendation",
        "",
        md_table(recommendation),
        "",
        "## Dry-run blockers",
        "",
        md_table(blockers),
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
        *[f"00-{i+1}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("00_不要_貼らなくてOK")]["item"].tolist())],
        "",
        "必要・見るファイル",
        *[f"{i+1:02d}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("必要・見るファイル")]["item"].tolist())],
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- 25C44 is plan-only and does not approve any variant.",
        "- CoreB live evaluator, Discord, MT5, AI API, live hook, and final signal remain blocked.",
        "- Future dry-run remains blocked until filter attribution, route plan, and separate explicit human acceptance.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c44_GOLD_V2_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "selected_route": summary["selected_route"],
        "incremental_damage_rows": inc_total,
        "next_recommended_step": NEXT_STEP,
        "dry_run_executed": False,
        "ai_api_called": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
