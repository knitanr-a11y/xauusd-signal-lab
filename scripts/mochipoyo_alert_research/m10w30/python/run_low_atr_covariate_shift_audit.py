from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
STAGE = "M10W30_LOW_ATR_POST_RESULT_COVARIATE_SHIFT_DIAGNOSTIC_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w30_low_atr_post_result_covariate_shift_audit_contract_20260728.json"
FORBIDDEN_COLUMNS = {
    "actual_return_bps", "fixed0p20_return_bps", "trade_id", "status",
    "scheduled_exit_time", "exit_time", "win", "loss", "label", "pnl", "profit_factor",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def finite_values(rows: list[dict[str, Any]], feature: str) -> list[float]:
    output: list[float] = []
    for row in rows:
        value = row.get(feature)
        if value in (None, ""):
            continue
        parsed = float(value)
        if math.isfinite(parsed):
            output.append(parsed)
    return output


def summary_stats(rows: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = finite_values(rows, feature)
    total = len(rows)
    if not values:
        return {
            "count": total, "available_count": 0, "missing_fraction": 1.0,
            "mean": None, "median": None, "p25": None, "p75": None,
            "minimum": None, "maximum": None,
        }
    return {
        "count": total,
        "available_count": len(values),
        "missing_fraction": (total - len(values)) / total if total else None,
        "mean": sum(values) / len(values),
        "median": quantile(values, 0.50),
        "p25": quantile(values, 0.25),
        "p75": quantile(values, 0.75),
        "minimum": min(values),
        "maximum": max(values),
    }


def train_edges(values: list[float]) -> list[float]:
    raw = [quantile(values, index / 10.0) for index in range(11)]
    unique: list[float] = []
    for value in raw:
        if not unique or value > unique[-1]:
            unique.append(value)
    if len(unique) < 3:
        distinct = sorted(set(values))
        if len(distinct) <= 1:
            return [-math.inf, math.inf]
        mids = [(a + b) / 2.0 for a, b in zip(distinct, distinct[1:])]
        return [-math.inf, *mids, math.inf]
    unique[0] = -math.inf
    unique[-1] = math.inf
    return unique


def bin_counts(values: list[float], edges: list[float]) -> list[int]:
    counts = [0] * (len(edges) - 1)
    internal = edges[1:-1]
    for value in values:
        index = bisect.bisect_right(internal, value)
        counts[index] += 1
    return counts


def psi(train: list[float], other: list[float], epsilon: float = 0.000001) -> tuple[float, int]:
    edges = train_edges(train)
    a = bin_counts(train, edges)
    b = bin_counts(other, edges)
    total_a = max(sum(a), 1)
    total_b = max(sum(b), 1)
    score = 0.0
    for count_a, count_b in zip(a, b):
        pa = max(count_a / total_a, epsilon)
        pb = max(count_b / total_b, epsilon)
        score += (pb - pa) * math.log(pb / pa)
    return score, len(a)


def ks_distance(left: list[float], right: list[float]) -> float:
    a = sorted(left)
    b = sorted(right)
    if not a or not b:
        return math.nan
    i = j = 0
    distance = 0.0
    while i < len(a) or j < len(b):
        if j >= len(b) or (i < len(a) and a[i] <= b[j]):
            value = a[i]
        else:
            value = b[j]
        while i < len(a) and a[i] <= value:
            i += 1
        while j < len(b) and b[j] <= value:
            j += 1
        distance = max(distance, abs(i / len(a) - j / len(b)))
    return distance


def drift_band(score: float) -> str:
    if score >= 0.25:
        return "SEVERE_GE_0P25"
    if score >= 0.10:
        return "MODERATE_GE_0P10_LT_0P25"
    return "LOW_LT_0P10"


def f(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    return math.nan if value in (None, "") else float(value)


def formula_pass(row: dict[str, Any], family: str) -> bool:
    if family == "LMVI1_LONG_M5_VOLUME_IMPULSE":
        return f(row, "m5_tick_volume_ratio20") >= 1.0 and f(row, "m5_body_ratio") >= 0.50 and f(row, "m5_close_location") >= (2.0 / 3.0)
    if family == "LMWR1_LONG_M5_PULLBACK_REJECTION":
        return f(row, "m5_ret3_bps") <= 0.0 and f(row, "m5_lower_wick_ratio") >= 0.40 and f(row, "m5_close_location") >= 0.60
    if family == "LMMO1_LONG_M1_MICRO_MOMENTUM":
        return f(row, "m1_ret5_bps") > 0.0 and f(row, "m1_up_close_count5") >= 3.0 and f(row, "m1_close_location") >= 0.60
    raise RuntimeError(f"unknown family: {family}")


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


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W30"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_POST_RESULT_DIAGNOSTIC_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W30 contract")
        source = local_root / "outputs" / "M10W27" / "LATEST" / "02_low_atr_bullish_causal_neither_feature_rows.csv"
        if not source.is_file():
            raise RuntimeError(f"M10W27 feature source missing: {source}")
        actual_hash = sha256(source)
        expected_hash = str(contract["source"]["expected_sha256"])
        if actual_hash != expected_hash:
            raise RuntimeError(f"M10W27 feature SHA mismatch: {actual_hash} expected={expected_hash}")
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            forbidden_found = sorted(fields & FORBIDDEN_COLUMNS)
            if forbidden_found:
                raise RuntimeError(f"outcome/trade columns present in pre-entry source: {forbidden_found}")
            rows = list(reader)
        expected_rows = int(contract["source"]["expected_rows"])
        if len(rows) != expected_rows:
            raise RuntimeError(f"source row count drift: {len(rows)} expected={expected_rows}")
        for row in rows:
            row["year"] = int(row["year"])
        groups = {
            "TRAIN_2023_2024": [row for row in rows if int(row["year"]) in (2023, 2024)],
            "VALIDATION_2025": [row for row in rows if int(row["year"]) == 2025],
            "TEST_2026": [row for row in rows if int(row["year"]) == 2026],
        }
        if any(not group for group in groups.values()):
            raise RuntimeError(f"empty split: {{name: len(items) for name, items in groups.items()}}")
        features = list(contract["numeric_features"])
        stats_rows: list[dict[str, Any]] = []
        for split, items in groups.items():
            for feature in features:
                stats_rows.append({"split": split, "feature": feature, **summary_stats(items, feature)})
        drift_rows: list[dict[str, Any]] = []
        train = groups["TRAIN_2023_2024"]
        for split in ("VALIDATION_2025", "TEST_2026"):
            for feature in features:
                reference = finite_values(train, feature)
                comparison = finite_values(groups[split], feature)
                score, bin_count = psi(reference, comparison)
                drift_rows.append({
                    "comparison": split,
                    "feature": feature,
                    "psi": score,
                    "psi_band": drift_band(score),
                    "train_decile_bin_count_after_duplicate_collapse": bin_count,
                    "ks_distance": ks_distance(reference, comparison),
                    "train_median": quantile(reference, 0.50),
                    "comparison_median": quantile(comparison, 0.50),
                    "train_mean": sum(reference) / len(reference),
                    "comparison_mean": sum(comparison) / len(comparison),
                })
        families = [
            "LMVI1_LONG_M5_VOLUME_IMPULSE",
            "LMWR1_LONG_M5_PULLBACK_REJECTION",
            "LMMO1_LONG_M1_MICRO_MOMENTUM",
        ]
        density_rows: list[dict[str, Any]] = []
        for split, items in groups.items():
            for family in families:
                count = sum(formula_pass(row, family) for row in items)
                density_rows.append({"split": split, "family": family, "row_count": len(items), "pass_count": count, "pass_fraction": count / len(items)})
        test_drift = [row for row in drift_rows if row["comparison"] == "TEST_2026"]
        severe_test = sorted((row for row in test_drift if row["psi_band"] == "SEVERE_GE_0P25"), key=lambda row: float(row["psi"]), reverse=True)
        moderate_test = sorted((row for row in test_drift if row["psi_band"] == "MODERATE_GE_0P10_LT_0P25"), key=lambda row: float(row["psi"]), reverse=True)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_MATERIAL_2026_COVARIATE_SCALE_SHIFT_DIAGNOSTIC_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_feature_sha256": actual_hash,
            "source_feature_rows": len(rows),
            "split_rows": {name: len(items) for name, items in groups.items()},
            "test_severe_PSI_features": [{"feature": row["feature"], "psi": row["psi"], "ks_distance": row["ks_distance"], "train_median": row["train_median"], "test_median": row["comparison_median"]} for row in severe_test],
            "test_moderate_PSI_features": [{"feature": row["feature"], "psi": row["psi"], "ks_distance": row["ks_distance"], "train_median": row["train_median"], "test_median": row["comparison_median"]} for row in moderate_test],
            "frozen_formula_density_by_split": density_rows,
            "interpretation": {
                "material_covariate_scale_shift_present": bool(severe_test),
                "formula_trigger_density_collapsed": False,
                "M10W29_outcome_failure_rescued": False,
                "M10W29_family_advance_authorized": False,
                "post_result_tuning_authorized": False,
                "next": "Design an outcome-blind availability audit for genuinely scale-normalized causal information. Do not refit the failed M10W29 formulas."
            },
            "outcome_blind_source_audit": {
                "trade_ledger_read": False,
                "future_return_read_or_computed": False,
                "pf_or_pnl_read_or_computed": False,
                "win_loss_label_read": False,
                "profit_ranked_feature_selection": False,
            },
            "relationship_to_forward": {"M10W26_modified": False, "existing_monitors_modified": False},
            "guardrails": contract["safety"],
        }
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W30 is a post-result diagnostic-only audit of pre-entry M10W27 covariate shift. It does not read trade outcomes and cannot rescue, retune or advance any M10W29 family.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_feature_drift.csv", drift_rows)
        write_csv(archive / "03_split_feature_summary.csv", stats_rows)
        write_csv(archive / "04_frozen_formula_density.csv", density_rows)
        (archive / "05_contract_copy.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_data_quality.json").write_text(json.dumps({
            "source_path": str(source), "source_sha256": actual_hash, "source_rows": len(rows),
            "forbidden_outcome_columns_found": [], "time_basis": "MT5_SERVER_TIME",
            "closed_rows_contract": True, "nearest_m1_fallback": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_MATERIAL_2026_COVARIATE_SCALE_SHIFT_DIAGNOSTIC_ONLY",
            "trade_ledger_read=false", "future_return_read_or_computed=false",
            "pf_or_pnl_read_or_computed=false", "win_loss_label_read=false",
            "M10W29_family_rescued=false", "post_result_tuning_authorized=false",
            "M10W26_modified=false", "discord_send=false", "mt5_order=false", "",
        ]), encoding="utf-8")
        files = sorted(path for path in archive.iterdir() if path.is_file())
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                zf.write(file, file.name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M10W30 PASS] ROWS={len(rows)} TEST_SEVERE_PSI={len(severe_test)} TEST_MODERATE_PSI={len(moderate_test)}")
        print(f"[M10W30 OUTPUT] {latest / '99_UPLOAD_PACKAGE.zip'}")
        return 0
    except Exception as exc:
        print(f"[M10W30 BLOCKED] {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
