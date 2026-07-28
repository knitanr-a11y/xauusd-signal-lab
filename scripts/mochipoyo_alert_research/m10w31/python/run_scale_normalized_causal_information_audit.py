from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m10a" / "python", MR / "m10w22" / "python", MR / "m10w30" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import run_high_atr_bullish_new_causal_information_availability_audit as feature_core
import run_low_atr_covariate_shift_audit as drift_core

STAGE = "M10W31_LOW_ATR_SCALE_NORMALIZED_CAUSAL_INFORMATION_AVAILABILITY_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w31_scale_normalized_causal_information_availability_contract_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
FORBIDDEN_COLUMNS = {
    "actual_return_bps", "fixed0p20_return_bps", "trade_id", "status",
    "scheduled_exit_time", "exit_time", "win", "loss", "label", "pnl", "profit_factor",
}
FEATURES = [
    "h1_atr14_usd",
    "h1_atr14_bps",
    "m5_range3_over_h1_atr14",
    "m1_range5_over_h1_atr14",
    "m5_ret3_over_h1_atr14",
    "m1_ret5_over_h1_atr14",
    "last_closed_m1_spread_usd",
    "last_closed_m1_spread_over_h1_atr14",
    "m15_close_minus_ema20_over_h1_atr14",
    "h1_close_minus_ema20_over_h1_atr14",
    "m5_tick_volume_ratio20",
    "m5_body_ratio",
    "m5_close_location",
    "m5_lower_wick_ratio",
    "m5_upper_wick_ratio",
    "m1_close_location",
    "m1_up_close_count5",
]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def build_rows(parent_rows: list[dict[str, Any]], bars: dict[str, list[c.Bar]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    m1, m5, m15, h1 = (bars[key] for key in ("M1", "M5", "M15", "H1"))
    m1_ct = [bar.time + timedelta(minutes=1) for bar in m1]
    m5_ct = [bar.time + timedelta(minutes=5) for bar in m5]
    m15_ct = [bar.time + timedelta(minutes=15) for bar in m15]
    h1_ct = [bar.time + timedelta(hours=1) for bar in h1]
    h1_atr = feature_core.pay.wilder_atr14(h1)
    m15_ema20 = c.ema([float(bar.close) for bar in m15], 20)
    h1_ema20 = c.ema([float(bar.close) for bar in h1], 20)

    output: list[dict[str, Any]] = []
    source_timing_violations = 0
    missing_context = 0
    nonpositive_atr = 0

    for parent in parent_rows:
        decision = parse_time(str(parent["decision_time"]))
        i1 = bisect.bisect_right(m1_ct, decision) - 1
        i5 = bisect.bisect_right(m5_ct, decision) - 1
        i15 = bisect.bisect_right(m15_ct, decision) - 1
        ih1 = bisect.bisect_right(h1_ct, decision) - 1
        if min(i1, i5, i15, ih1) < 0 or i1 < 4 or i5 < 19 or i5 < 3:
            missing_context += 1
            continue
        if h1_atr[ih1] is None:
            missing_context += 1
            continue
        atr = float(h1_atr[ih1])
        if not math.isfinite(atr) or atr <= 0:
            nonpositive_atr += 1
            continue
        last1, last5, last15, last_h1 = m1[i1], m5[i5], m15[i15], h1[ih1]
        if (
            last1.time + timedelta(minutes=1) > decision
            or last5.time + timedelta(minutes=5) > decision
            or last15.time + timedelta(minutes=15) > decision
            or last_h1.time + timedelta(hours=1) > decision
        ):
            source_timing_violations += 1
            continue

        shape1 = feature_core.bar_shape(last1)
        shape5 = feature_core.bar_shape(last5)
        volume_mean = sum(float(m5[index].tick_volume) for index in range(i5 - 19, i5 + 1)) / 20.0
        m5_range3_usd = max(float(m5[index].high) for index in range(i5 - 2, i5 + 1)) - min(float(m5[index].low) for index in range(i5 - 2, i5 + 1))
        m1_range5_usd = max(float(m1[index].high) for index in range(i1 - 4, i1 + 1)) - min(float(m1[index].low) for index in range(i1 - 4, i1 + 1))
        m5_ret3_usd = float(m5[i5].close) - float(m5[i5 - 3].close)
        m1_ret5_usd = float(m1[i1].close) - float(m1[i1 - 4].open)
        spread_usd = int(last1.spread) * c.POINT
        h1_close = float(last_h1.close)

        output.append({
            "decision_time": decision.strftime(TIME_FORMAT),
            "year": int(parent["year"]),
            "causal_coverage_class": str(parent["causal_coverage_class"]),
            "h1_atr_pct100": float(parent["h1_atr_pct100"]),
            "h1_atr14_usd": atr,
            "h1_atr14_bps": atr / max(abs(h1_close), 1e-12) * 10000.0,
            "m5_range3_over_h1_atr14": m5_range3_usd / atr,
            "m1_range5_over_h1_atr14": m1_range5_usd / atr,
            "m5_ret3_over_h1_atr14": m5_ret3_usd / atr,
            "m1_ret5_over_h1_atr14": m1_ret5_usd / atr,
            "last_closed_m1_spread_usd": spread_usd,
            "last_closed_m1_spread_over_h1_atr14": spread_usd / atr,
            "m15_close_minus_ema20_over_h1_atr14": (float(last15.close) - float(m15_ema20[i15])) / atr,
            "h1_close_minus_ema20_over_h1_atr14": (h1_close - float(h1_ema20[ih1])) / atr,
            "m5_tick_volume_ratio20": feature_core.safe_ratio(float(last5.tick_volume), volume_mean),
            "m5_body_ratio": shape5["body_ratio"],
            "m5_close_location": shape5["close_location"],
            "m5_lower_wick_ratio": shape5["lower_wick_ratio"],
            "m5_upper_wick_ratio": shape5["upper_wick_ratio"],
            "m1_close_location": shape1["close_location"],
            "m1_up_close_count5": sum(float(m1[index].close) > float(m1[index].open) for index in range(i1 - 4, i1 + 1)),
            "m1_source_open": last1.time.strftime(TIME_FORMAT),
            "m5_source_open": last5.time.strftime(TIME_FORMAT),
            "m15_source_open": last15.time.strftime(TIME_FORMAT),
            "h1_source_open": last_h1.time.strftime(TIME_FORMAT),
        })

    diagnostics = {
        "parent_row_count": len(parent_rows),
        "output_row_count": len(output),
        "missing_context_count": missing_context,
        "nonpositive_h1_atr_count": nonpositive_atr,
        "source_timing_violation_count": source_timing_violations,
        "decision_time_set_match": {row["decision_time"] for row in output} == {str(row["decision_time"]) for row in parent_rows},
        "future_return_computed": False,
        "trade_outcome_read": False,
    }
    return output, diagnostics


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W31"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W31 contract")
        parent_path = local_root / "outputs" / "M10W27" / "LATEST" / "02_low_atr_bullish_causal_neither_feature_rows.csv"
        if not parent_path.is_file():
            raise RuntimeError(f"M10W27 parent feature file missing: {parent_path}")
        actual_parent_hash = drift_core.sha256(parent_path)
        expected_parent_hash = str(contract["exact_parent_cohort"]["expected_sha256"])
        if actual_parent_hash != expected_parent_hash:
            raise RuntimeError(f"M10W27 parent SHA mismatch: {actual_parent_hash} expected={expected_parent_hash}")
        with parent_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            forbidden = sorted(fields & drift_core.FORBIDDEN_COLUMNS)
            if forbidden:
                raise RuntimeError(f"outcome/trade columns present in parent source: {forbidden}")
            parent_rows = list(reader)
        expected_rows = int(contract["exact_parent_cohort"]["expected_rows"])
        if len(parent_rows) != expected_rows:
            raise RuntimeError(f"parent row count drift: {len(parent_rows)} expected={expected_rows}")
        parent_times = [str(row["decision_time"]) for row in parent_rows]
        if len(parent_times) != len(set(parent_times)):
            raise RuntimeError("duplicate parent decision_time")

        data_root = feature_core.resolve_data_root(local_root)
        bars, frozen_hashes, _ = feature_core.verify_and_load(data_root)
        rows, causal_diagnostics = build_rows(parent_rows, bars)
        if not causal_diagnostics["decision_time_set_match"] or len(rows) != expected_rows:
            raise RuntimeError(f"exact M10W27 decision-time parity failed: {causal_diagnostics}")
        if int(causal_diagnostics["source_timing_violation_count"]) != 0:
            raise RuntimeError(f"causal source timing violations: {causal_diagnostics}")

        groups: dict[str, list[dict[str, Any]]] = {
            "ALL": rows,
            "TRAIN_2023_2024": [row for row in rows if int(row["year"]) in (2023, 2024)],
            "VALIDATION_2025": [row for row in rows if int(row["year"]) == 2025],
            "TEST_2026": [row for row in rows if int(row["year"]) == 2026],
        }
        summary_rows: list[dict[str, Any]] = []
        degenerate_rows: list[dict[str, Any]] = []
        for split, items in groups.items():
            for feature in FEATURES:
                values = drift_core.finite_values(items, feature)
                stats = drift_core.summary_stats(items, feature)
                mean = sum(values) / len(values) if values else None
                variance = sum((value - mean) ** 2 for value in values) / len(values) if values and mean is not None else None
                row = {"split": split, "feature": feature, **stats, "unique_count": len(set(values)), "variance": variance}
                summary_rows.append(row)
                if split == "ALL" and (len(set(values)) <= 1 or variance == 0.0):
                    degenerate_rows.append(row)

        drift_rows: list[dict[str, Any]] = []
        train = groups["TRAIN_2023_2024"]
        for split in ("VALIDATION_2025", "TEST_2026"):
            for feature in FEATURES:
                reference = drift_core.finite_values(train, feature)
                comparison = drift_core.finite_values(groups[split], feature)
                score, bin_count = drift_core.psi(reference, comparison)
                drift_rows.append({
                    "comparison": split,
                    "feature": feature,
                    "psi": score,
                    "psi_band": drift_core.drift_band(score),
                    "ks_distance": drift_core.ks_distance(reference, comparison),
                    "train_decile_bin_count_after_duplicate_collapse": bin_count,
                    "train_median": drift_core.quantile(reference, 0.50),
                    "comparison_median": drift_core.quantile(comparison, 0.50),
                })

        test_severe = sorted(
            [row for row in drift_rows if row["comparison"] == "TEST_2026" and row["psi_band"] == "SEVERE_GE_0P25"],
            key=lambda row: float(row["psi"]), reverse=True,
        )
        all_available = all(float(row["missing_fraction"]) <= 0.001 for row in summary_rows if row["split"] == "ALL")
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_SCALE_NORMALIZED_CAUSAL_INFORMATION_AVAILABLE_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parent_feature_sha256": actual_parent_hash,
            "exact_parent_row_count": len(rows),
            "split_rows": {name: len(items) for name, items in groups.items()},
            "decision_time_set_match": True,
            "causal_diagnostics": causal_diagnostics,
            "all_features_available_at_least_99p9pct": all_available,
            "degenerate_feature_count": len(degenerate_rows),
            "test_severe_PSI_features": [{"feature": row["feature"], "psi": row["psi"], "ks_distance": row["ks_distance"]} for row in test_severe],
            "frozen_data_sha256": frozen_hashes,
            "outcome_blind_audit": {
                "trade_ledger_read": False,
                "future_return_read_or_computed": False,
                "pf_or_pnl_read_or_computed": False,
                "win_loss_label_read": False,
                "profit_ranked_feature_selection": False,
                "entry_formula_created": False,
                "threshold_selected": False,
            },
            "interpretation": {
                "this_stage_creates_candidate": False,
                "M10W29_family_rescued": False,
                "next": "Review availability and drift. At most three semantic scale-normalized families may then be preregistered, with historical results treated as exploratory and fresh prospective support required."
            },
            "relationship_to_forward": {"M10W26_modified": False, "existing_monitors_modified": False},
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W31 audits scale-normalized causal pre-entry information on the exact M10W27 7480-row cohort. It does not read outcomes or create an entry formula and does not modify M10W26 or any monitor.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_scale_normalized_feature_rows.csv", rows)
        write_csv(archive / "03_feature_availability_distribution.csv", summary_rows)
        write_csv(archive / "04_cross_split_drift.csv", drift_rows)
        write_csv(archive / "05_degenerate_features.csv", degenerate_rows)
        (archive / "06_causal_data_quality.json").write_text(json.dumps({
            "parent_path": str(parent_path), "parent_sha256": actual_parent_hash,
            "parent_rows": len(parent_rows), "output_rows": len(rows),
            "decision_time_set_match": True, "source_timing_violation_count": 0,
            "time_basis": "MT5_SERVER_TIME", "closed_rows_contract": True,
            "nearest_m1_fallback": False, "frozen_data_sha256": frozen_hashes,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_contract_copy.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "08_audit.log").write_text("\n".join([
            "status=PASS_SCALE_NORMALIZED_CAUSAL_INFORMATION_AVAILABLE_AUDIT_ONLY",
            "decision_time_set_match=true", "source_timing_violation_count=0",
            "trade_ledger_read=false", "future_return_read_or_computed=false",
            "pf_or_pnl_read_or_computed=false", "win_loss_label_read=false",
            "entry_formula_created=false", "threshold_selected=false",
            "M10W29_family_rescued=false", "M10W26_modified=false",
            "discord_send=false", "mt5_order=false", "",
        ]), encoding="utf-8")
        files = sorted(path for path in archive.iterdir() if path.is_file())
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                zf.write(file, file.name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M10W31 PASS] ROWS={len(rows)} FEATURES={len(FEATURES)} DEGENERATE={len(degenerate_rows)} TEST_SEVERE_PSI={len(test_severe)}")
        print(f"[M10W31 OUTPUT] {latest / '99_UPLOAD_PACKAGE.zip'}")
        return 0
    except Exception as exc:
        print(f"[M10W31 BLOCKED] {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
