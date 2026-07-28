from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10W24_PY = MR / "m10w24" / "python"
if str(M10W24_PY) not in sys.path:
    sys.path.insert(0, str(M10W24_PY))

import run_m10w24_preregistered_microstructure_entry_evaluation as base

STAGE = "M10W24B_NEITHER_COHORT_SCOPE_CORRECTION_AUDIT_ONLY"
CORRECTION = ROOT / "config" / "mochipoyo_alert_research" / "m10w24b_neither_cohort_scope_correction_contract_20260728.json"
POSTRUN_CORRECTION = ROOT / "config" / "mochipoyo_alert_research" / "m10w24b_postrun_audit_correction_contract_20260728.json"
M10W23 = ROOT / "config" / "mochipoyo_alert_research" / "m10w23_high_atr_bullish_microstructure_entry_preregistration_20260728.json"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def load_coverage_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"M10W14 coverage grid missing: {path}")
    coverage: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "decision_time" not in (reader.fieldnames or []) or "coverage_class" not in (reader.fieldnames or []):
            raise RuntimeError("M10W14 coverage grid missing decision_time/coverage_class")
        for row in reader:
            decision = str(row["decision_time"])
            if decision in coverage:
                raise RuntimeError(f"duplicate M10W14 decision_time: {decision}")
            coverage[decision] = str(row["coverage_class"])
    if not coverage:
        raise RuntimeError("M10W14 coverage grid empty")
    return coverage


def classify_frozen(blocks: dict[str, Any], gates: dict[str, Any]) -> str:
    split_names = ("TRAIN_2023_2024", "VALIDATION_2025", "TEST_2026")
    strong = gates["STRONG_CANDIDATE"]
    robust = gates["ROBUST_CANDIDATE"]
    strong_min_count = int(strong["minimum_count_each_split"])
    robust_min_count = int(robust["minimum_count_each_split"])
    if strong_min_count != robust_min_count:
        raise RuntimeError("M10W23 strong/robust minimum split counts differ unexpectedly")
    min_count = robust_min_count

    counts = [int(blocks[name]["actual"]["count"]) for name in split_names]
    split_pfs = [base.pf(blocks[name]["actual"]) for name in split_names]
    all_pf = base.pf(blocks["ALL"]["actual"])
    fixed_pf = base.pf(blocks["ALL"]["fixed0p20"])
    cost2_pf = base.pf(blocks["ALL"]["actual_plus2bps_cost"])
    nets = [float(blocks[name]["actual"]["net_bps"]) for name in split_names]

    # Frozen M10W23 REJECT rule: any adequately populated split PF <= 1.0,
    # or all-sample fixed-$0.20 / +2bps PF <= 1.0. A sparse different split
    # does not erase an already adequately populated losing split.
    if any(count >= min_count and split_pf <= 1.0 for count, split_pf in zip(counts, split_pfs)) or fixed_pf <= 1.0 or cost2_pf <= 1.0:
        return "REJECT"
    if min(counts) < min_count:
        return "INSUFFICIENT_DENSITY"

    if min(split_pfs) >= float(strong["minimum_pf_each_split"]) and all_pf >= float(strong["minimum_all_pf"]) and fixed_pf >= float(strong["minimum_fixed0p20_all_pf"]) and cost2_pf >= float(strong["minimum_extra2bps_all_pf"]) and all(net > 0 for net in nets):
        return "STRONG_CANDIDATE"
    if min(split_pfs) >= float(robust["minimum_pf_each_split"]) and all_pf >= float(robust["minimum_all_pf"]) and fixed_pf >= float(robust["minimum_fixed0p20_all_pf"]) and cost2_pf >= float(robust["minimum_extra2bps_all_pf"]) and all(net > 0 for net in nets):
        return "ROBUST_CANDIDATE"
    return "WEAK_OR_INCONSISTENT"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    base.write_csv(path, rows)


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W24B"
    try:
        correction = load_json(CORRECTION)
        if correction.get("stage") != STAGE or correction.get("status") != "CORRECTION_FROZEN_BEFORE_CORRECTED_OUTCOME_RERUN":
            raise RuntimeError("unexpected M10W24B correction contract")

        postrun = load_json(POSTRUN_CORRECTION)
        if postrun.get("stage") != STAGE or postrun.get("status") != "POSTRUN_AUDIT_CORRECTION_FROZEN_NO_SIGNAL_RULE_CHANGE":
            raise RuntimeError("unexpected M10W24B postrun audit correction contract")

        contract = load_json(M10W23)
        if contract.get("stage") != "M10W23_HIGH_ATR_BULLISH_MICROSTRUCTURE_ENTRY_PREREGISTRATION_AUDIT_ONLY" or contract.get("status") != "HYPOTHESES_FROZEN_BEFORE_OUTCOME_EVALUATION":
            raise RuntimeError("unexpected M10W23 frozen contract")

        feature_path = local_root / "outputs" / "M10W22" / "LATEST" / "02_target_regime_causal_feature_rows.csv"
        coverage_path = local_root / "outputs" / "M10W14" / "LATEST" / "02_m15_coverage_grid.csv"
        feature_rows = base.load_feature_rows(feature_path)
        coverage_map = load_coverage_map(coverage_path)

        broad_decisions = [str(row["decision_time"]) for row in feature_rows]
        broad_times = set(broad_decisions)
        if len(broad_times) != len(broad_decisions):
            raise RuntimeError("duplicate decision_time inside M10W22 feature rows")
        unmatched = sorted(decision for decision in broad_decisions if decision not in coverage_map)
        if unmatched:
            sample = ",".join(unmatched[:5])
            raise RuntimeError(f"M10W22 decision_time missing from M10W14 coverage grid: count={len(unmatched)} sample={sample}")

        coverage_class_counts: dict[str, int] = {}
        for decision in broad_decisions:
            cls = coverage_map[decision]
            coverage_class_counts[cls] = coverage_class_counts.get(cls, 0) + 1

        corrected_rows = [row for row in feature_rows if coverage_map[str(row["decision_time"])] == "NEITHER"]
        if not corrected_rows:
            raise RuntimeError("corrected NEITHER target cohort is empty")

        corrected_times = {str(row["decision_time"]) for row in corrected_rows}
        if len(corrected_times) != len(corrected_rows):
            raise RuntimeError("duplicate decision_time inside corrected feature rows")
        if not corrected_times.issubset(broad_times):
            raise RuntimeError("corrected cohort is not subset of M10W22 rows")

        data_root = base.resolve_data_root(local_root)
        m1 = base.verify_m1(data_root)
        gates = contract["frozen_evaluation"]["decision_tiers"]
        family_results: dict[str, Any] = {}
        all_trade_rows: list[dict[str, Any]] = []
        all_skip_rows: list[dict[str, Any]] = []

        for family in contract["families"]:
            candidates = base.build_candidates(corrected_rows, family)
            trades, skips = base.build_ledger(candidates, m1)
            blocks = base.metric_blocks(trades)
            classification = classify_frozen(blocks, gates)
            family_results[family] = {
                "classification": classification,
                "candidate_count": len(candidates),
                "accepted_count": sum(row.get("trade_id") is not None for row in trades),
                "resolved_count": sum(row.get("status") == "RESOLVED" for row in trades),
                "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
                "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in trades),
                "overlap_skip_count": len(skips),
                "metrics": blocks,
                "advance_to_fresh_shadow": classification in ("ROBUST_CANDIDATE", "STRONG_CANDIDATE"),
            }
            all_trade_rows.extend(trades)
            all_skip_rows.extend({"family": family, **row} for row in skips)

        advancing = [name for name, result in family_results.items() if result["advance_to_fresh_shadow"]]
        year_counts = {str(year): sum(int(row["year"]) == year for row in corrected_rows) for year in (2023, 2024, 2025, 2026)}
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_NEITHER_COHORT_SCOPE_CORRECTION_EVALUATION_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "source_feature_rows": str(feature_path),
            "source_coverage_grid": str(coverage_path),
            "broader_M10W22_row_count": len(feature_rows),
            "coverage_join_integrity": {
                "join_key": "decision_time exact string equality",
                "broad_decision_time_unique": True,
                "coverage_grid_decision_time_unique": True,
                "matched_broader_row_count": len(feature_rows),
                "unmatched_broader_row_count": 0,
                "coverage_class_counts_within_broader": coverage_class_counts,
            },
            "corrected_NEITHER_row_count": len(corrected_rows),
            "corrected_year_counts": year_counts,
            "required_coverage_class": "NEITHER",
            "formula_or_threshold_change": False,
            "classification_audit_correction": {
                "applied": True,
                "reason": "Apply frozen M10W23 REJECT rule to any adequately populated losing split before sparse-other-split density fallback.",
                "formula_change": False,
                "threshold_change": False,
                "cohort_change": False,
                "metric_change": False,
            },
            "families": family_results,
            "advancing_families": advancing,
            "interpretation": {
                "this_is_scope_correction_not_threshold_rescue": True,
                "M10W24_broader_result_can_reject_corrected_NEITHER": False,
                "corrected_historical_result_is_clean_independent_validation": False,
                "fresh_shadow_required_for_any_pass": True,
                "M10W19_modified": False,
            },
            "guardrails": correction["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W24B restores the original M10W17 NEITHER cohort by exact decision_time join. "
            "M10W23 formulas, thresholds, horizon, execution and decision tiers are unchanged. "
            "Postrun audit correction only adds exact-join completeness enforcement and frozen REJECT-rule classification precedence.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_corrected_neither_feature_rows.csv", corrected_rows)
        write_csv(archive / "03_trade_ledger_all_families.csv", all_trade_rows)
        write_csv(archive / "04_overlap_skip_ledger_all_families.csv", all_skip_rows)
        (archive / "05_audit.log").write_text("\n".join([
            "status=PASS_NEITHER_COHORT_SCOPE_CORRECTION_EVALUATION_AUDIT_ONLY",
            f"broader_rows={len(feature_rows)}",
            f"coverage_join_matched_rows={len(feature_rows)}",
            "coverage_join_unmatched_rows=0",
            f"corrected_neither_rows={len(corrected_rows)}",
            f"coverage_class_counts={json.dumps(coverage_class_counts, sort_keys=True)}",
            f"advancing_families={','.join(advancing) if advancing else 'NONE'}",
            "required_coverage_class=NEITHER",
            "formula_change=false",
            "threshold_change=false",
            "cohort_change=false",
            "metric_formula_change=false",
            "classification_audit_correction=true",
            "horizon_change=false",
            "M10W19_modified=false",
            "automatic_live_promotion=false",
            "",
        ]), encoding="utf-8")

        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_corrected_neither_feature_rows.csv", "03_trade_ledger_all_families.csv", "04_overlap_skip_ledger_all_families.csv", "05_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        print(f"[M10W24B PASS] broader={len(feature_rows)} matched={len(feature_rows)} unmatched=0 neither={len(corrected_rows)} advancing={advancing if advancing else 'NONE'}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W24B BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No current monitor, frozen start, formula, threshold, horizon, or decision tier was modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
