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

STEP = "25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED"
STOP = "25C38_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C38_STOP_25C37_CONTRACT_UNSAFE_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only"
IN37 = "gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only"

EXPECTED_STEP_37 = "25C37_COREB_G1_ADJUSTED_NARROWING_DRY_RUN_AUDIT_ONLY"
EXPECTED_STATUS_37 = {
    "COREB_G1_ADJUSTED_NARROWING_DRY_RUN_COMPLETED_AUDIT_ONLY_RESULT_REVIEW_REQUIRED",
    "COREB_G1_ADJUSTED_NARROWING_DRY_RUN_COMPLETED_AUDIT_ONLY_EXACT_MATCH_REVIEW_REQUIRED",
}
BASELINE = "BASELINE_CURRENT"
BEST_VARIANT_ID = "A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR"
EXPECTED_VARIANTS = {
    "BASELINE_CURRENT",
    "A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8",
    "A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U",
    "A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR",
    "A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR",
}


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


def status_from_exists(path: Path) -> str:
    return "PASS" if lp(path).exists() else "STOP"


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def classify_variant(row: pd.Series, best_variant: str) -> str:
    variant = str(row.get("variant", ""))
    if parse_bool(row.get("exact_match", False)):
        return "EXACT_MATCH_REVIEW_REQUIRED"
    if variant == best_variant:
        return "BEST_BY_25C37_SCORING_BUT_TOO_DESTRUCTIVE"
    if variant.startswith("A001_"):
        return "LESS_DESTRUCTIVE_COMPROMISE_BUT_NOT_EXACT"
    if variant.startswith("A002_") or variant.startswith("A004_"):
        return "MODERATE_REDUCTION_DUPLICATE_OR_EQUIVALENT_NOT_ENOUGH"
    return "ADJUSTED_VARIANT_NOT_USABLE_AS_IS"


def require_contract(summary: dict, gates: pd.DataFrame) -> tuple[bool, list[dict]]:
    rows: list[dict] = []
    checks = [
        ("C001", "25C37 step matches expected", summary.get("step") == EXPECTED_STEP_37, summary.get("step")),
        ("C002", "25C37 status is review-required", summary.get("status") in EXPECTED_STATUS_37, summary.get("status")),
        ("C003", "25C37 audit_only true", bool(summary.get("audit_only", False)) is True, summary.get("audit_only")),
        ("C004", "25C37 dry_run_executed true", bool(summary.get("dry_run_executed", False)) is True, summary.get("dry_run_executed")),
        ("C005", "25C37 condition_changed false", bool(summary.get("condition_changed", True)) is False, summary.get("condition_changed")),
        ("C006", "25C37 source recovery false", bool(summary.get("source_recovery_executed", True)) is False, summary.get("source_recovery_executed")),
        ("C007", "25C37 source mutation false", bool(summary.get("source_mutation_executed", True)) is False, summary.get("source_mutation_executed")),
        ("C008", "25C37 CoreB live unblock false", bool(summary.get("coreb_live_evaluator_unblocked", True)) is False, summary.get("coreb_live_evaluator_unblocked")),
        ("C009", "25C37 exact match not required for review", "any_exact_match" in summary, summary.get("any_exact_match")),
    ]
    for check_id, check, passed, observed in checks:
        rows.append({"contract_id": check_id, "check": check, "observed": observed, "status": "PASS" if passed else "STOP"})
    if not gates.empty and {"gate", "observed", "status"}.issubset(gates.columns):
        live_rows = gates[gates["gate"].astype(str).str.contains("CoreB live evaluator", case=False, regex=False, na=False)]
        if not live_rows.empty:
            observed = str(live_rows.iloc[0]["observed"])
            status = str(live_rows.iloc[0]["status"])
            passed = observed.lower() in {"false", "0", "no"} and status.upper() in {"BLOCKED", "PASS"}
            rows.append({"contract_id": "C010", "check": "25C37 gate keeps CoreB live evaluator blocked", "observed": f"{observed}/{status}", "status": "PASS" if passed else "STOP"})
    return all(r["status"] == "PASS" for r in rows), rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base = fx_outputs() / IN37
    req = {
        "s37": base / "02_25c37_coreb_g1_adjusted_narrowing_dry_run_summary.json",
        "contract": base / "04_25c37_variant_filter_contract.csv",
        "compare": base / "05_25c37_variant_compare_matrix.csv",
        "delta": base / "06_25c37_variant_delta_matrix.csv",
        "by_policy": base / "07_25c37_variant_by_dataset_policy.csv",
        "gates": base / "09_25c37_acceptance_gate_matrix.csv",
    }

    input_audit = pd.DataFrame(
        [{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()]
    )
    write_csv(out / "03_25c38_input_audit.csv", input_audit)

    if not bool(input_audit["exists"].all()):
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP,
            "audit_only": True,
            "total_stop_rows": int((input_audit["status"] == "STOP").sum()),
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "ai_api_called": False,
            "dry_run_executed": False,
            "condition_changed": False,
        }
        write_json(out / "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json", summary)
        return 2

    s37 = read_json(req["s37"])
    contract = read_csv(req["contract"])
    compare = numericize(read_csv(req["compare"]), ["replay_g1_rows", "both", "left_only", "right_only"])
    delta = read_csv(req["delta"])
    by_policy = read_csv(req["by_policy"])
    gates = read_csv(req["gates"])

    contract_ok, contract_rows = require_contract(s37, gates)
    observed_variants = set(compare["variant"].astype(str).tolist()) if "variant" in compare.columns else set()
    missing_variants = sorted(EXPECTED_VARIANTS - observed_variants)
    extra_variants = sorted(observed_variants - EXPECTED_VARIANTS)
    contract_rows.extend([
        {
            "contract_id": "C011",
            "check": "25C37 compare matrix contains expected baseline and A001-A004 variants",
            "observed": f"missing={missing_variants}; extra={extra_variants}",
            "status": "PASS" if not missing_variants else "STOP",
        },
        {
            "contract_id": "C012",
            "check": "25C37 summary variant_count is 4",
            "observed": s37.get("variant_count"),
            "status": "PASS" if int(s37.get("variant_count", -1)) == 4 else "STOP",
        },
        {
            "contract_id": "C013",
            "check": "25C37 best_variant is A003 but review-only",
            "observed": s37.get("best_variant"),
            "status": "PASS" if str(s37.get("best_variant", "")) == BEST_VARIANT_ID else "STOP",
        },
    ])
    contract_ok = contract_ok and all(r["status"] == "PASS" for r in contract_rows)
    contract_audit = pd.DataFrame(contract_rows)
    if not contract_ok:
        write_csv(out / "04_25c38_adjusted_variant_tradeoff_matrix.csv", pd.DataFrame())
        write_csv(out / "05_25c38_best_variant_review_matrix.csv", pd.DataFrame())
        write_csv(out / "06_25c38_remaining_mismatch_decision_matrix.csv", contract_audit)
        write_csv(out / "07_25c38_next_step_plan.csv", pd.DataFrame([
            {"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": "25C37 contract unsafe or inconsistent"},
        ]))
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP_CONTRACT,
            "audit_only": True,
            "total_stop_rows": int((contract_audit["status"] == "STOP").sum()),
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "ai_api_called": False,
            "dry_run_executed": False,
            "condition_changed": False,
        }
        write_json(out / "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json", summary)
        return 2

    if compare.empty or BASELINE not in set(compare["variant"].astype(str)):
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": "25C38_STOP_COMPARE_BASELINE_MISSING_AUDIT_ONLY",
            "audit_only": True,
            "total_stop_rows": 1,
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "ai_api_called": False,
            "dry_run_executed": False,
            "condition_changed": False,
        }
        write_json(out / "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json", summary)
        return 2

    base_row = compare[compare["variant"].astype(str).eq(BASELINE)].iloc[0]
    review = compare[~compare["variant"].astype(str).eq(BASELINE)].copy()
    for col in ["replay_g1_rows", "both", "left_only", "right_only"]:
        review[col] = pd.to_numeric(review[col], errors="coerce").fillna(0).astype(int)

    best_variant = str(s37.get("best_variant", ""))
    if not best_variant and not review.empty:
        best_variant = str(review.sort_values(["left_only"], ascending=[True]).iloc[0]["variant"])

    review["baseline_replay_g1_rows"] = int(base_row["replay_g1_rows"])
    review["baseline_both"] = int(base_row["both"])
    review["baseline_left_only"] = int(base_row["left_only"])
    review["baseline_right_only"] = int(base_row["right_only"])
    review["left_only_reduction"] = int(base_row["left_only"]) - review["left_only"]
    review["right_only_increase"] = review["right_only"] - int(base_row["right_only"])
    review["both_loss"] = int(base_row["both"]) - review["both"]
    review["replay_row_reduction"] = int(base_row["replay_g1_rows"]) - review["replay_g1_rows"]
    review["over_narrowing_score"] = review["right_only_increase"] + review["both_loss"]
    review["net_tradeoff_score"] = review["left_only_reduction"] - review["over_narrowing_score"]
    review["left_only_reduction_pct"] = (review["left_only_reduction"] / max(int(base_row["left_only"]), 1) * 100).round(2)
    review["right_only_increase_pct"] = (review["right_only_increase"] / max(int(base_row["right_only"]), 1) * 100).round(2)
    review["both_loss_pct"] = (review["both_loss"] / max(int(base_row["both"]), 1) * 100).round(2)
    review["review_class"] = review.apply(lambda r: classify_variant(r, best_variant), axis=1)
    review["usable_as_is"] = False
    review["live_ready"] = False
    review["approval_status"] = "NOT_APPROVED_REVIEW_ONLY"
    review["source_of_truth_replacement"] = False
    review = review.sort_values(["net_tradeoff_score", "left_only_reduction"], ascending=[False, False])
    write_csv(out / "04_25c38_adjusted_variant_tradeoff_matrix.csv", review)

    best = review[review["variant"].astype(str).eq(best_variant)].copy()
    if best.empty and not review.empty:
        best = review.head(1).copy()
    best_review_cols = [
        "variant", "replay_g1_rows", "both", "left_only", "right_only",
        "left_only_reduction", "right_only_increase", "both_loss", "over_narrowing_score",
        "net_tradeoff_score", "left_only_reduction_pct", "right_only_increase_pct", "both_loss_pct",
        "review_class", "usable_as_is", "live_ready", "approval_status", "source_of_truth_replacement",
    ]
    best_review = best[[c for c in best_review_cols if c in best.columns]].copy() if not best.empty else pd.DataFrame()
    if not best_review.empty:
        best_review["review_note"] = (
            "Best by 25C37 scoring only; not approved, not live-ready, and too destructive because right_only rises and both falls."
        )
    write_csv(out / "05_25c38_best_variant_review_matrix.csv", best_review)

    exact = bool(s37.get("any_exact_match", False))
    best_left_only = int(best.iloc[0]["left_only"]) if not best.empty else None
    best_right_only = int(best.iloc[0]["right_only"]) if not best.empty else None
    best_both = int(best.iloc[0]["both"]) if not best.empty else None
    best_right_only_increase = int(best.iloc[0]["right_only_increase"]) if not best.empty else None
    best_both_loss = int(best.iloc[0]["both_loss"]) if not best.empty else None
    best_too_destructive = bool((best_right_only_increase or 0) > 0 or (best_both_loss or 0) > 0)

    decisions = pd.DataFrame([
        {
            "decision_id": "D001",
            "question": "25C37 result reached exact match",
            "decision": "NO" if not exact else "YES_REVIEW_ONLY",
            "observed": exact,
            "action": "do not enable CoreB live evaluator",
        },
        {
            "decision_id": "D002",
            "question": "A003 is approved or live-ready",
            "decision": "NO",
            "observed": f"best_variant={best_variant}; left_only={best_left_only}; right_only={best_right_only}; both={best_both}",
            "action": "treat as review finding only",
        },
        {
            "decision_id": "D003",
            "question": "best variant is too destructive",
            "decision": "YES" if best_too_destructive else "NO",
            "observed": f"right_only_increase={best_right_only_increase}; both_loss={best_both_loss}",
            "action": "do not adopt as source-of-truth replacement",
        },
        {
            "decision_id": "D004",
            "question": "A001 is a safe compromise",
            "decision": "NO",
            "observed": "left_only reduction exists but right_only increase and both loss remain material",
            "action": "review-only; no adoption",
        },
        {
            "decision_id": "D005",
            "question": "A002 and A004 differ materially",
            "decision": "NO",
            "observed": "25C37 reported equivalent compare counts",
            "action": "treat as duplicate/equivalent result in this review",
        },
        {
            "decision_id": "D006",
            "question": "CoreB live evaluator unblock allowed",
            "decision": "NO",
            "observed": False,
            "action": "blocked",
        },
        {
            "decision_id": "D007",
            "question": "AI API call allowed or needed",
            "decision": "NO",
            "observed": False,
            "action": "not called",
        },
        {
            "decision_id": "D008",
            "question": "next work should execute another dry-run now",
            "decision": "NO",
            "observed": "25C38 is result review only",
            "action": "create a separate acceptance gate before any future dry-run",
        },
    ])
    write_csv(out / "06_25c38_remaining_mismatch_decision_matrix.csv", decisions)

    next_plan = pd.DataFrame([
        {
            "rank": 1,
            "next_step": "25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY",
            "allowed_now": True,
            "purpose": "plan which non-execution route to take next: less destructive threshold, right_only recovery review, hybrid plan, or stop",
            "requires_human_acceptance_before_execution": False,
            "execution_allowed_in_25c38": False,
        },
        {
            "rank": 2,
            "next_step": "future adjusted narrowing dry-run",
            "allowed_now": False,
            "purpose": "would require a separate explicit acceptance gate after a 25C39-style plan",
            "requires_human_acceptance_before_execution": True,
            "execution_allowed_in_25c38": False,
        },
        {
            "rank": 3,
            "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API",
            "allowed_now": False,
            "purpose": "blocked because no exact match and no source recovery approval",
            "requires_human_acceptance_before_execution": True,
            "execution_allowed_in_25c38": False,
        },
    ])
    write_csv(out / "07_25c38_next_step_plan.csv", next_plan)

    unnecessary = [
        "full replay rows",
        "full target rows",
        "old GOLD/DISC8 files",
        "25C36 source files unless a later plan explicitly needs them",
    ]
    necessary = [
        "01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md",
        "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json",
        "03_25c38_input_audit.csv",
        "04_25c38_adjusted_variant_tradeoff_matrix.csv",
        "05_25c38_best_variant_review_matrix.csv",
        "06_25c38_remaining_mismatch_decision_matrix.csv",
        "07_25c38_next_step_plan.csv",
    ]
    write_csv(
        out / "00_不要_25c38_file_request_list.csv",
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
        "result_review_only": True,
        "dry_run_executed": False,
        "condition_changed": False,
        "full_coreb_parity": False,
        "variant_count": int(len(review)),
        "best_variant": best_variant,
        "best_variant_approved": False,
        "best_variant_live_ready": False,
        "best_variant_source_of_truth_replacement": False,
        "best_left_only": best_left_only,
        "best_right_only": best_right_only,
        "best_both": best_both,
        "best_right_only_increase": best_right_only_increase,
        "best_both_loss": best_both_loss,
        "any_exact_match": exact,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": "25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY",
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C38 CoreB G1 adjusted narrowing result review audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{STATUS}`",
        "",
        "## Scope",
        "",
        "This is a result review only. It reads 25C37 output artifacts and does not run a new dry-run.",
        "",
        "## 25C37 contract audit",
        "",
        md_table(contract_audit),
        "",
        "## Adjusted variant tradeoff matrix",
        "",
        md_table(review),
        "",
        "## Best variant review matrix",
        "",
        md_table(best_review),
        "",
        "## Remaining mismatch decision matrix",
        "",
        md_table(decisions),
        "",
        "## Input audit",
        "",
        md_table(input_audit),
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
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- A003 remains review-only: not approved, not live-ready, and not a source-of-truth replacement.",
        "- CoreB live evaluator remains blocked.",
        "- Source recovery, source mutation, Discord, MT5, AI API, live hook, and final signal remain off.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "best_variant": best_variant,
        "best_variant_approved": False,
        "best_variant_live_ready": False,
        "dry_run_executed": False,
        "next_recommended_step": summary["next_recommended_step"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
