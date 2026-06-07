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

STEP = "25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY"
STATUS = "COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_READY_AUDIT_ONLY_NEXT_AUDIT_REQUIRED"
STOP = "25C39_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C39_STOP_25C38_CONTRACT_UNSAFE_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c39_coreb_g1_remaining_mismatch_route_plan_audit_only"
IN38 = "gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only"

EXPECTED_STEP_38 = "25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY"
EXPECTED_STATUS_38 = "COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED"
EXPECTED_NEXT_FROM_38 = "25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def default_fx_outputs() -> Path:
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


def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def numericize(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def status_from_exists(path: Path) -> str:
    return "PASS" if lp(path).exists() else "STOP"


def contract_rows_from_25c38(s38: dict, next_plan: pd.DataFrame) -> list[dict]:
    rows = []
    checks = [
        ("C001", "25C38 step matches expected", s38.get("step") == EXPECTED_STEP_38, s38.get("step")),
        ("C002", "25C38 status is next-plan-required", s38.get("status") == EXPECTED_STATUS_38, s38.get("status")),
        ("C003", "25C38 audit_only true", as_bool(s38.get("audit_only", False)) is True, s38.get("audit_only")),
        ("C004", "25C38 result_review_only true", as_bool(s38.get("result_review_only", False)) is True, s38.get("result_review_only")),
        ("C005", "25C38 dry_run_executed false", as_bool(s38.get("dry_run_executed", True)) is False, s38.get("dry_run_executed")),
        ("C006", "25C38 condition_changed false", as_bool(s38.get("condition_changed", True)) is False, s38.get("condition_changed")),
        ("C007", "25C38 any_exact_match false", as_bool(s38.get("any_exact_match", True)) is False, s38.get("any_exact_match")),
        ("C008", "25C38 best variant not approved", as_bool(s38.get("best_variant_approved", True)) is False, s38.get("best_variant_approved")),
        ("C009", "25C38 best variant not live-ready", as_bool(s38.get("best_variant_live_ready", True)) is False, s38.get("best_variant_live_ready")),
        ("C010", "25C38 best variant not source-of-truth replacement", as_bool(s38.get("best_variant_source_of_truth_replacement", True)) is False, s38.get("best_variant_source_of_truth_replacement")),
        ("C011", "25C38 source recovery false", as_bool(s38.get("source_recovery_executed", True)) is False, s38.get("source_recovery_executed")),
        ("C012", "25C38 source mutation false", as_bool(s38.get("source_mutation_executed", True)) is False, s38.get("source_mutation_executed")),
        ("C013", "25C38 CoreB live unblock false", as_bool(s38.get("coreb_live_evaluator_unblocked", True)) is False, s38.get("coreb_live_evaluator_unblocked")),
        ("C014", "25C38 AI API false", as_bool(s38.get("ai_api_called", True)) is False, s38.get("ai_api_called")),
        ("C015", "25C38 next recommended step is 25C39", s38.get("next_recommended_step") == EXPECTED_NEXT_FROM_38, s38.get("next_recommended_step")),
    ]
    for cid, check, passed, observed in checks:
        rows.append({"contract_id": cid, "check": check, "observed": observed, "status": "PASS" if passed else "STOP"})

    if not next_plan.empty and {"next_step", "allowed_now"}.issubset(next_plan.columns):
        m = next_plan[next_plan["next_step"].astype(str).eq(EXPECTED_NEXT_FROM_38)]
        passed = not m.empty and as_bool(m.iloc[0]["allowed_now"]) is True
        rows.append({
            "contract_id": "C016",
            "check": "25C38 next plan allows 25C39 planning now",
            "observed": "" if m.empty else str(m.iloc[0].to_dict()),
            "status": "PASS" if passed else "STOP",
        })
    else:
        rows.append({
            "contract_id": "C016",
            "check": "25C38 next plan allows 25C39 planning now",
            "observed": "next plan schema missing",
            "status": "STOP",
        })
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--fx-output-root", default=None)
    args = ap.parse_args(argv)

    fx_root = Path(args.fx_output_root).resolve() if args.fx_output_root else default_fx_outputs()
    out = Path(args.output_dir).resolve() if args.output_dir else fx_root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base = fx_root / IN38
    req = {
        "s38": base / "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json",
        "tradeoff": base / "04_25c38_adjusted_variant_tradeoff_matrix.csv",
        "best_review": base / "05_25c38_best_variant_review_matrix.csv",
        "decisions": base / "06_25c38_remaining_mismatch_decision_matrix.csv",
        "next_plan": base / "07_25c38_next_step_plan.csv",
    }

    input_audit = pd.DataFrame(
        [{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()]
    )
    write_csv(out / "03_25c39_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP,
            "audit_only": True,
            "plan_only": True,
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
            "total_stop_rows": int((input_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json", summary)
        return 2

    s38 = read_json(req["s38"])
    tradeoff = numericize(read_csv(req["tradeoff"]), [
        "replay_g1_rows", "both", "left_only", "right_only", "baseline_replay_g1_rows",
        "baseline_both", "baseline_left_only", "baseline_right_only", "left_only_reduction",
        "right_only_increase", "both_loss", "replay_row_reduction", "over_narrowing_score",
        "net_tradeoff_score",
    ])
    best_review = read_csv(req["best_review"])
    decisions_38 = read_csv(req["decisions"])
    next_plan_38 = read_csv(req["next_plan"])

    contract_rows = contract_rows_from_25c38(s38, next_plan_38)
    all_variants_not_exact = bool((tradeoff.get("exact_match", pd.Series(dtype=str)).astype(str).str.lower() == "false").all()) if not tradeoff.empty else False
    all_raise_right_only = bool((tradeoff["right_only_increase"] > 0).all()) if "right_only_increase" in tradeoff.columns and not tradeoff.empty else False
    all_lose_both = bool((tradeoff["both_loss"] > 0).all()) if "both_loss" in tradeoff.columns and not tradeoff.empty else False
    a002 = tradeoff[tradeoff["variant"].astype(str).str.startswith("A002_")] if "variant" in tradeoff.columns else pd.DataFrame()
    a004 = tradeoff[tradeoff["variant"].astype(str).str.startswith("A004_")] if "variant" in tradeoff.columns else pd.DataFrame()
    a002_a004_equivalent = False
    if not a002.empty and not a004.empty:
        metrics = ["replay_g1_rows", "both", "left_only", "right_only", "left_only_reduction", "right_only_increase", "both_loss"]
        a002_a004_equivalent = all(int(a002.iloc[0][m]) == int(a004.iloc[0][m]) for m in metrics if m in a002.columns and m in a004.columns)
    contract_rows.extend([
        {"contract_id": "C017", "check": "all adjusted variants remain non-exact", "observed": all_variants_not_exact, "status": "PASS" if all_variants_not_exact else "STOP"},
        {"contract_id": "C018", "check": "all adjusted variants increase right_only", "observed": all_raise_right_only, "status": "PASS" if all_raise_right_only else "REVIEW"},
        {"contract_id": "C019", "check": "all adjusted variants lose both rows", "observed": all_lose_both, "status": "PASS" if all_lose_both else "REVIEW"},
        {"contract_id": "C020", "check": "A002/A004 are equivalent on aggregate metrics", "observed": a002_a004_equivalent, "status": "PASS" if a002_a004_equivalent else "REVIEW"},
    ])
    contract_audit = pd.DataFrame(contract_rows)
    hard_stop = bool((contract_audit["status"] == "STOP").any())

    if hard_stop:
        write_csv(out / "04_25c39_route_option_matrix.csv", pd.DataFrame())
        write_csv(out / "05_25c39_route_recommendation_matrix.csv", pd.DataFrame())
        write_csv(out / "06_25c39_execution_boundary_matrix.csv", pd.DataFrame())
        write_csv(out / "07_25c39_acceptance_gate_matrix.csv", contract_audit)
        write_csv(out / "08_25c39_next_step_plan.csv", pd.DataFrame([
            {"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": "25C38 contract unsafe or inconsistent"},
        ]))
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP_CONTRACT,
            "audit_only": True,
            "plan_only": True,
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
            "total_stop_rows": int((contract_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json", summary)
        return 2

    best_variant = str(s38.get("best_variant", ""))
    best_too_destructive = (
        int(s38.get("best_right_only_increase", 0)) > 0
        or int(s38.get("best_both_loss", 0)) > 0
    )

    routes = pd.DataFrame([
        {
            "route_id": "R001",
            "route": "RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST",
            "rank": 1,
            "recommended": True,
            "allowed_now": True,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": True,
            "reason": "all adjusted variants increase right_only and lose both; check whether row-level right_only evidence exists before any new dry-run",
            "next_step": "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY",
        },
        {
            "route_id": "R002",
            "route": "HYBRID_VARIANT_PLAN_AFTER_RIGHT_ONLY_DRIVER_REVIEW",
            "rank": 2,
            "recommended": False,
            "allowed_now": False,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": True,
            "reason": "hybrid design should wait until right_only damage drivers are known",
            "next_step": "blocked until right_only recovery input/driver review",
        },
        {
            "route_id": "R003",
            "route": "LESS_DESTRUCTIVE_THRESHOLD_PLAN_ONLY",
            "rank": 3,
            "recommended": False,
            "allowed_now": False,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": True,
            "reason": "A002/A004 already show only moderate left_only reduction while still adding right_only; threshold-only route is insufficient without right_only context",
            "next_step": "optional later plan, not next",
        },
        {
            "route_id": "R004",
            "route": "STOP_ADJUSTED_NARROWING_AS_INSUFFICIENT",
            "rank": 4,
            "recommended": False,
            "allowed_now": True,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": False,
            "reason": "valid human decision if no further recovery audit is desired",
            "next_step": "human stop decision",
        },
        {
            "route_id": "R005",
            "route": "SOURCE_RECOVERY_OR_SOURCE_MUTATION",
            "rank": 5,
            "recommended": False,
            "allowed_now": False,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": True,
            "reason": "REQUEST_MORE_AUDIT is not source recovery approval; source mutation remains blocked",
            "next_step": "blocked",
        },
        {
            "route_id": "R006",
            "route": "COREB_LIVE_EVALUATOR_OR_EXTERNAL_ACTIONS",
            "rank": 6,
            "recommended": False,
            "allowed_now": False,
            "executes_dry_run": False,
            "changes_conditions": False,
            "requires_human_acceptance_before_dry_run": True,
            "reason": "no exact match; CoreB live evaluator, Discord, MT5, AI API, live hook, and final signal remain blocked",
            "next_step": "blocked",
        },
    ])
    write_csv(out / "04_25c39_route_option_matrix.csv", routes)

    recommendation = pd.DataFrame([
        {
            "recommendation_id": "REC001",
            "selected_route_id": "R001",
            "selected_route": "RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST",
            "best_variant": best_variant,
            "best_variant_too_destructive": best_too_destructive,
            "any_exact_match": bool(s38.get("any_exact_match", False)),
            "all_adjusted_variants_raise_right_only": all_raise_right_only,
            "all_adjusted_variants_lose_both": all_lose_both,
            "a002_a004_equivalent": a002_a004_equivalent,
            "reason": "before designing any new exclusion bundle, audit whether existing artifacts contain enough right_only row-level evidence to identify what the adjusted filters damaged",
            "next_recommended_step": "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY",
            "dry_run_allowed_next": False,
            "live_unblock_allowed_next": False,
        }
    ])
    write_csv(out / "05_25c39_route_recommendation_matrix.csv", recommendation)

    boundary = pd.DataFrame([
        {"boundary": "plan_remaining_mismatch_route", "allowed": True, "observed": True},
        {"boundary": "read_25c38_outputs_only", "allowed": True, "observed": True},
        {"boundary": "run_new_dry_run", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "06_25c39_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C38 completed audit-only next-plan-required", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "no exact match remains", "observed": not bool(s38.get("any_exact_match", False)), "status": "PASS" if not bool(s38.get("any_exact_match", False)) else "REVIEW"},
        {"gate_id": "G003", "gate": "A003 not approved/live-ready", "observed": not as_bool(s38.get("best_variant_approved", True)) and not as_bool(s38.get("best_variant_live_ready", True)), "status": "PASS"},
        {"gate_id": "G004", "gate": "right_only recovery input availability audit can be planned now", "observed": True, "status": "PASS"},
        {"gate_id": "G005", "gate": "future dry-run execution allowed now", "observed": False, "status": "BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G006", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G007", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "07_25c39_acceptance_gate_matrix.csv", gates)

    next_step = pd.DataFrame([
        {
            "rank": 1,
            "next_step": "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY",
            "allowed_now": True,
            "purpose": "check whether existing 25C37/25C38 artifacts contain enough right_only row-level evidence for recovery review; no dry-run",
            "requires_human_acceptance_before_execution": False,
            "execution_allowed_in_25c39": False,
        },
        {
            "rank": 2,
            "next_step": "RIGHT_ONLY_RECOVERY_DRIVER_REVIEW_AUDIT_ONLY",
            "allowed_now": False,
            "purpose": "depends on 25C40 confirming row-level evidence availability or a separately accepted export plan",
            "requires_human_acceptance_before_execution": False,
            "execution_allowed_in_25c39": False,
        },
        {
            "rank": 3,
            "next_step": "future adjusted narrowing dry-run",
            "allowed_now": False,
            "purpose": "requires a separate plan and explicit human acceptance gate",
            "requires_human_acceptance_before_execution": True,
            "execution_allowed_in_25c39": False,
        },
        {
            "rank": 4,
            "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API",
            "allowed_now": False,
            "purpose": "blocked because no exact match and no source recovery approval",
            "requires_human_acceptance_before_execution": True,
            "execution_allowed_in_25c39": False,
        },
    ])
    write_csv(out / "08_25c39_next_step_plan.csv", next_step)

    unnecessary = [
        "full replay rows",
        "full target rows",
        "old GOLD/DISC8 files",
        "raw OHLC",
        "25C37 dry-run rerun output",
    ]
    necessary = [
        "01_25c39_GOLD_V2_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY_REPORT.md",
        "02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json",
        "03_25c39_input_audit.csv",
        "04_25c39_route_option_matrix.csv",
        "05_25c39_route_recommendation_matrix.csv",
        "06_25c39_execution_boundary_matrix.csv",
        "07_25c39_acceptance_gate_matrix.csv",
        "08_25c39_next_step_plan.csv",
    ]
    write_csv(
        out / "00_不要_25c39_file_request_list.csv",
        pd.DataFrame(
            [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
            + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
        ),
    )

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "plan_only": True,
        "dry_run_executed": False,
        "condition_changed": False,
        "full_coreb_parity": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "best_variant": best_variant,
        "best_variant_approved": False,
        "best_variant_live_ready": False,
        "best_variant_source_of_truth_replacement": False,
        "best_variant_too_destructive": best_too_destructive,
        "all_adjusted_variants_raise_right_only": all_raise_right_only,
        "all_adjusted_variants_lose_both": all_lose_both,
        "a002_a004_equivalent": a002_a004_equivalent,
        "selected_route": "RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST",
        "next_recommended_step": "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY",
        "requires_human_acceptance_before_next_dry_run": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C39 CoreB G1 remaining mismatch route plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{STATUS}`",
        "",
        "## Scope",
        "",
        "This is a route plan only. It reads 25C38 outputs and does not run a new dry-run.",
        "",
        "## 25C38 contract audit",
        "",
        md_table(contract_audit),
        "",
        "## 25C38 tradeoff summary used as source-of-truth",
        "",
        md_table(tradeoff),
        "",
        "## Route option matrix",
        "",
        md_table(routes),
        "",
        "## Route recommendation matrix",
        "",
        md_table(recommendation),
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
        *[f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)],
        "",
        "必要・見るファイル",
        *[f"{i+1:02d}. {x}" for i, x in enumerate(necessary)],
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_step),
        "",
        "## Safety",
        "",
        "- A003 remains review-only: not approved, not live-ready, and not a source-of-truth replacement.",
        "- 25C39 does not execute dry-run, source recovery, source mutation, condition change, live evaluator, Discord, MT5, AI API, live hook, or final signal.",
        "- Future dry-run remains blocked until a separate explicit human acceptance gate.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c39_GOLD_V2_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "selected_route": summary["selected_route"],
        "next_recommended_step": summary["next_recommended_step"],
        "dry_run_executed": False,
        "ai_api_called": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
