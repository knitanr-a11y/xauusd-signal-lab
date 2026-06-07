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

STEP = "25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY"
STATUS = "COREB_G1_FILTER_COVERAGE_NEXT_PLAN_READY_AUDIT_ONLY"
STOP_MISSING = "25C47_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C47_STOP_25C46_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_REP = "25C47_STOP_REPRESENTATIVE_CANDIDATE_UNSAFE_AUDIT_ONLY"
IN46 = "gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only"
OUT_DIR = "gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only"
EXPECTED_46_STEP = "25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY"
EXPECTED_46_ALIAS = "25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY"
EXPECTED_46_STATUS = "COREB_G1_FILTER_COVERAGE_REVIEW_READY_AUDIT_ONLY"
NEXT_STEP = "25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY"


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
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/02_25c46_filter_coverage_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/04_25c46_coverage_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/05_25c46_selected_coverage_plan.csv",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/01_25c47_GOLD_V2_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/02_25c47_filter_coverage_next_plan_summary.json",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/05_25c47_representative_candidate_review.csv",
        "FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/06_25c47_next_option_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def safety_boundaries() -> pd.DataFrame:
    rows = [
        ("read_25c46_outputs", True, True),
        ("write_25c47_plan_artifacts", True, True),
        ("approve_variant", False, False),
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
    return pd.DataFrame([{"boundary_id": f"B{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary46: Optional[dict] = None) -> int:
    summary46 = summary46 or {}
    write_csv(out / "00_不要_25c47_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c47_input_audit.csv", input_audit)
    write_csv(out / "04_25c47_contract_audit.csv", diag)
    write_csv(out / "05_25c47_representative_candidate_review.csv", diag)
    write_csv(out / "06_25c47_next_option_matrix.csv", diag)
    boundary = safety_boundaries()
    write_csv(out / "07_25c47_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C46 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "representative candidate safe", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "25C48 spec may start", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c47_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c47": False}])
    write_csv(out / "09_25c47_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C47 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "10_25c47_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "next_plan_only": True,
        "input_25c46_step": summary46.get("step"),
        "input_25c46_status": summary46.get("status"),
        "variant_approved": False,
        "replay_executed": False,
        "dry_run_executed": False,
        "source_recovery_executed": False,
        "condition_changed": False,
        "ai_api_called": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": "STOP",
        "total_stop_rows": int((diag.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if isinstance(diag, pd.DataFrame) else 1,
    }
    write_json(out / "02_25c47_filter_coverage_next_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C47 CoreB G1 filter coverage next plan audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No execution or external action was performed.",
    ])
    lp(out / "01_25c47_GOLD_V2_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "replay_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary46: dict, coverage: pd.DataFrame, selected: pd.DataFrame, limits: pd.DataFrame, gates: pd.DataFrame, next_plan46: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_46_STEP,
        "logical_step_alias": EXPECTED_46_ALIAS,
        "status": EXPECTED_46_STATUS,
        "audit_only": True,
        "review_plan_only": True,
        "known_unique_damage_keys": 360,
        "unique_incremental_damage_keys": 360,
        "filter_attribution_rows": 1260,
        "unique_cleanly_attributed_damage_keys": 360,
        "unique_not_cleanly_attributed_damage_keys": 0,
        "coverage_rows": 11,
        "full_coverage_candidate_rows": 7,
        "selected_variant_code": "A002",
        "selected_retention_priority_cutoff": 1,
        "selected_total_unique_damage_keys": 69,
        "selected_covered_unique_keys": 69,
        "selected_open_unique_keys": 0,
        "selected_retained_filter_count": 2,
        "selected_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "a002_a004_approval_status": "NOT_APPROVED_REVIEW_ONLY",
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary46.get(k)
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    false_flags = ["replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "variant_approved", "best_variant_approved", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary46.get(flag), "expected": False, "status": "PASS" if summary46.get(flag) is False else "STOP"})
    rows += [
        {"contract_id": "M001", "check": "coverage row count matches summary", "observed": len(coverage), "expected": summary46.get("coverage_rows"), "status": "PASS" if len(coverage) == int(summary46.get("coverage_rows", -1)) else "STOP"},
        {"contract_id": "M002", "check": "selected row count matches full coverage candidates", "observed": len(selected), "expected": summary46.get("full_coverage_candidate_rows"), "status": "PASS" if len(selected) == int(summary46.get("full_coverage_candidate_rows", -1)) else "STOP"},
        {"contract_id": "M003", "check": "limits matrix has no STOP", "observed": int(limits[limits["status"].astype(str).eq("STOP")].shape[0]) if "status" in limits else -1, "expected": 0, "status": "PASS" if "status" in limits and not limits["status"].astype(str).eq("STOP").any() else "STOP"},
        {"contract_id": "M004", "check": "25C47 blocked until 25C46 review in gates", "observed": ";".join(gates.get("status", pd.Series(dtype=str)).astype(str).tolist()), "expected": "BLOCKED_UNTIL_25C46_ARTIFACT_REVIEW", "status": "PASS" if "BLOCKED_UNTIL_25C46_ARTIFACT_REVIEW" in gates.get("status", pd.Series(dtype=str)).astype(str).tolist() else "STOP"},
        {"contract_id": "M005", "check": "25C46 next plan points to 25C47 but not allowed_now", "observed": next_plan46.iloc[0].to_dict() if not next_plan46.empty else {}, "expected": "25C47 allowed_now False", "status": "PASS" if (not next_plan46.empty and str(next_plan46.iloc[0].get("next_step")) == STEP and str(next_plan46.iloc[0].get("allowed_now")).lower() == "false") else "STOP"},
    ]
    return pd.DataFrame(rows)


def representative_review(summary46: dict, selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty or "selected_representative" not in selected.columns:
        return pd.DataFrame([{"check": "selected representative exists", "status": "STOP"}])
    rep_mask = selected["selected_representative"].astype(str).str.lower().isin(["true", "1", "yes"])
    rows = []
    rows.append({"review_id": "R001", "check": "one selected representative", "observed": int(rep_mask.sum()), "expected": 1, "status": "PASS" if int(rep_mask.sum()) == 1 else "STOP"})
    if int(rep_mask.sum()) == 1:
        rep = selected[rep_mask].iloc[0]
        checks = {
            "variant_code": "A002",
            "retention_priority_cutoff": 1,
            "total_unique_damage_keys": 69,
            "covered_unique_keys": 69,
            "open_unique_keys": 0,
            "retained_filter_count": 2,
            "approval_status": "NOT_APPROVED_REVIEW_ONLY",
            "execution_allowed_now": False,
            "requires_artifact_review_before_25c47": True,
        }
        for i, (k, exp) in enumerate(checks.items(), 2):
            obs = rep.get(k)
            if isinstance(exp, bool):
                ok = as_bool(obs) == exp
            elif isinstance(exp, int):
                try:
                    ok = int(obs) == exp
                except Exception:
                    ok = False
            else:
                ok = str(obs) == exp
            rows.append({"review_id": f"R{i:003d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    return pd.DataFrame(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN46
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary46": input_dir / "02_25c46_filter_coverage_review_summary.json",
        "coverage46": input_dir / "04_25c46_coverage_matrix.csv",
        "selected46": input_dir / "05_25c46_selected_coverage_plan.csv",
        "limits46": input_dir / "07_25c46_limits.csv",
        "gates46": input_dir / "08_25c46_gates.csv",
        "next_plan46": input_dir / "09_25c46_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c47_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary46 = read_json(req["summary46"])
    coverage = read_csv(req["coverage46"])
    selected = read_csv(req["selected46"])
    limits = read_csv(req["limits46"])
    gates46 = read_csv(req["gates46"])
    next_plan46 = read_csv(req["next_plan46"])

    contract = contract_audit(summary46, coverage, selected, limits, gates46, next_plan46)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary46)

    rep = representative_review(summary46, selected)
    if rep["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_REP, input_audit, rep, summary46)

    option = pd.DataFrame([
        {"option_rank": 1, "option": NEXT_STEP, "category": "audit_only_spec_review", "allowed_now": True, "execution_allowed_in_25c47": False, "approval_effect": "none", "notes": "Create only the next representative filter set review specification."},
        {"option_rank": 2, "option": "representative candidate approval", "category": "approval", "allowed_now": False, "execution_allowed_in_25c47": False, "approval_effect": "blocked", "notes": "A002 remains NOT_APPROVED_REVIEW_ONLY."},
        {"option_rank": 3, "option": "replay or dry-run execution", "category": "execution", "allowed_now": False, "execution_allowed_in_25c47": False, "approval_effect": "blocked", "notes": "Requires a later explicit approval after specs."},
        {"option_rank": 4, "option": "source or condition change", "category": "mutation", "allowed_now": False, "execution_allowed_in_25c47": False, "approval_effect": "blocked", "notes": "No source or condition mutation in 25C47."},
        {"option_rank": 5, "option": "live/external/AI/notification/order/final signal", "category": "external_live", "allowed_now": False, "execution_allowed_in_25c47": False, "approval_effect": "blocked", "notes": "Discord, MT5, AI API, live hook and final signal remain OFF."},
    ])
    boundary = safety_boundaries()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C46 artifact contract reviewed", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "representative candidate remains not approved", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "25C48 spec review can be created", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "replay/dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write representative filter set review specification only", "execution_allowed_in_25c47": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run/replay", "allowed_now": False, "purpose": "blocked until later spec review and explicit acceptance", "execution_allowed_in_25c47": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "live/external/AI/notification/order/final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c47": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C46 artifacts were reviewed as the source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "A002 is only a representative candidate and remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
        {"note_id": "N003", "note": "25C47 creates a next-plan package only and does not execute replay/dry-run/source/live/external actions.", "status": "PASS"},
        {"note_id": "N004", "note": "Next recommended step is a 25C48 specification/review step only.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c47_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c47_input_audit.csv", input_audit)
    write_csv(out / "04_25c47_contract_audit.csv", contract)
    write_csv(out / "05_25c47_representative_candidate_review.csv", rep)
    write_csv(out / "06_25c47_next_option_matrix.csv", option)
    write_csv(out / "07_25c47_execution_boundary_matrix.csv", boundary)
    write_csv(out / "08_25c47_gates.csv", gates)
    write_csv(out / "09_25c47_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c47_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "next_plan_only": True,
        "input_25c46_step": summary46.get("step"),
        "input_25c46_status": summary46.get("status"),
        "input_25c46_known_unique_damage_keys": summary46.get("known_unique_damage_keys"),
        "input_25c46_filter_attribution_rows": summary46.get("filter_attribution_rows"),
        "representative_variant": summary46.get("selected_variant"),
        "representative_variant_code": summary46.get("selected_variant_code"),
        "representative_retention_priority_cutoff": summary46.get("selected_retention_priority_cutoff"),
        "representative_total_unique_damage_keys": summary46.get("selected_total_unique_damage_keys"),
        "representative_covered_unique_keys": summary46.get("selected_covered_unique_keys"),
        "representative_open_unique_keys": summary46.get("selected_open_unique_keys"),
        "representative_retained_filter_count": summary46.get("selected_retained_filter_count"),
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
    write_json(out / "02_25c47_filter_coverage_next_plan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C47 CoreB G1 filter coverage next plan audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C47 reviews 25C46 artifacts and writes the next plan package only. It does not approve candidates or execute replay/dry-run/source/live/external actions.", "",
        "## 25C46 contract audit", "", md_table(contract), "",
        "## Representative candidate review", "", md_table(rep), "",
        "## Next option matrix", "", md_table(option), "",
        "## Execution boundaries", "", md_table(boundary), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Discord, MT5, AI API, live hook, live evaluator unblock, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c47_GOLD_V2_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "representative_variant_code": summary["representative_variant_code"], "representative_approval_status": summary["representative_approval_status"], "next_recommended_step": NEXT_STEP, "ai_api_called": False, "replay_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
