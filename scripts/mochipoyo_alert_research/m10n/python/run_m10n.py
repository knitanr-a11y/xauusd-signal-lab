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
from itertools import combinations
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for rel in ("m10a/python", "m10i/python", "m10j/python", "m10l/python", "m10m/python"):
    path = MR / rel
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import frozen_core as c
import run_m10j as m10j
import run_m10l as m10l
import run_m10m as m10m

STAGE = "M10N_DOWNSIDE_REGIME_SPECIFIC_SHORT_RESEARCH"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10n_downside_regime_specific_short_contract_20260725.json"
POINT = c.POINT
QUANTILES = (0.10, 0.20, 0.30, 0.70, 0.80, 0.90)
TOP_SINGLES_FOR_PAIRS = 30
SHORTLIST = 100

REGIME_FEATURES = [
    "h1_rci9", "h1_rci9_delta", "h1_ret3_bps", "h1_ret5_bps", "h1_ema20_slope_atr",
    "h1_ema20_30_bps", "h1_ema30_40_bps", "h1_macd_hist_slope", "h1_volume_ratio20",
    "h4_ema30_40_bps", "h4_macd_hist_bps", "h4_macd_hist_slope", "h4_rci9", "h4_atr_pct100",
    "d1_ema20_30_bps", "d1_ema30_40_bps", "d1_macd_hist_bps", "d1_macd_hist_slope",
    "d1_rci9", "d1_atr_pct100",
]
EXCLUDED_SEED_FEATURES = {
    "h4_ema20_30_bps", "h1_atr_pct100", "h1_macd_hist_bps", "h1_macd_line_bps", "m5_ema30_40_bps"
}

SEEDS = {
    "M10J_C0212": {"horizon": 240, "min_train": 35},
    "M10L_H240_C056": {"horizon": 240, "min_train": 25},
    "M10M_H120_C021": {"horizon": 120, "min_train": 25},
}
RANKING_SEEDS = ("M10J_C0212", "M10L_H240_C056")


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def resolve_data_root(local: Path) -> Path:
    override = os.environ.get("M10N_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata = local / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata.is_file():
        raise AuditError("M8B symbol metadata unavailable; set M10N_GOLD_DATA_ROOT")
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    root = str(payload.get("mt5_files_root", "")).strip()
    if not root:
        raise AuditError("mt5_files_root missing in M8B metadata")
    return Path(root) / "gold_v3_2023_2026"


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


def build_seed_rows(bars: dict[str, list[c.Bar]]) -> dict[str, list[dict[str, Any]]]:
    rows15 = m10j.build_feature_rows(bars)
    c0212 = [
        {"decision": row["decision"], "year": int(row["year"])}
        for row in rows15
        if float(row["h4_ema20_30_bps"]) >= 37.61355979 and float(row["h1_atr_pct100"]) >= 0.8
    ]

    rows_h1 = m10l.build_feature_rows(bars)
    c056 = [
        {"decision": row["decision"], "year": int(row["year"])}
        for row in rows_h1
        if float(row["h1_macd_hist_bps"]) >= 3.637199446 and float(row["h1_macd_line_bps"]) <= -7.667425443
    ]

    rows_m5 = m10m.build_feature_rows(bars)
    m5_ref = [
        {"decision": row["decision"], "year": int(row["year"])}
        for row in rows_m5
        if float(row["m5_ema30_40_bps"]) <= -3.052275892 and float(row["h4_ema20_30_bps"]) >= 37.61355979
    ]

    out = {
        "M10J_C0212": c0212,
        "M10L_H240_C056": c056,
        "M10M_H120_C021": m5_ref,
    }
    for rows in out.values():
        rows.sort(key=lambda row: row["decision"])
    return out


def build_conditions(train_regime_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if EXCLUDED_SEED_FEATURES.intersection(REGIME_FEATURES):
        raise AuditError("exact seed feature leaked into regime feature list")
    conditions: list[dict[str, Any]] = []
    for feature in REGIME_FEATURES:
        values = [float(row[feature]) for row in train_regime_rows]
        thresholds = sorted({m10l.qtile(values, q) for q in QUANTILES})
        for threshold in thresholds:
            for op in ("<=", ">="):
                conditions.append({
                    "id": f"{feature}{op}{threshold:.10g}",
                    "feature": feature,
                    "op": op,
                    "threshold": threshold,
                })
    return conditions


def condition_match(row: dict[str, Any], condition: dict[str, Any]) -> bool:
    value = float(row[condition["feature"]])
    return value <= float(condition["threshold"]) if condition["op"] == "<=" else value >= float(condition["threshold"])


def attach_regime(seed_rows: list[dict[str, Any]], regime_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    regime_rows = sorted(regime_rows, key=lambda row: row["decision"])
    times = [row["decision"] for row in regime_rows]
    attached: list[dict[str, Any]] = []
    for seed in seed_rows:
        idx = bisect.bisect_right(times, seed["decision"]) - 1
        if idx < 0:
            continue
        snapshot = regime_rows[idx]
        if snapshot["decision"] > seed["decision"]:
            raise AuditError("future regime snapshot selected")
        attached.append({**seed, "regime": snapshot})
    return attached


def build_outcomes(seed_rows: list[dict[str, Any]], horizon: int, m1: list[c.Bar]) -> dict[int, tuple[float, float, datetime] | None]:
    by_time = {bar.time: bar for bar in m1}
    outcomes: dict[int, tuple[float, float, datetime] | None] = {}
    for idx, row in enumerate(seed_rows):
        entry = by_time.get(row["decision"])
        exit_time = row["decision"] + timedelta(minutes=horizon)
        exit_bar = by_time.get(exit_time)
        if entry is None or exit_bar is None:
            outcomes[idx] = None
            continue
        entry_bid = float(entry.open)
        actual_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
        fixed_ask = float(exit_bar.open) + 0.20
        outcomes[idx] = (
            c.directional_return("SHORT", entry_bid, actual_ask),
            c.directional_return("SHORT", entry_bid, fixed_ask),
            exit_time,
        )
    return outcomes


def gated_indices(seed_rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> set[int]:
    return {
        idx
        for idx, row in enumerate(seed_rows)
        if all(condition_match(row["regime"], condition) for condition in conditions)
    }


def selected_metrics(
    seed_rows: list[dict[str, Any]],
    outcomes: dict[int, tuple[float, float, datetime] | None],
    indices: set[int],
    years: set[int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    actual: list[float] = []
    fixed: list[float] = []
    blocked_until: datetime | None = None
    for idx in sorted(indices, key=lambda i: seed_rows[i]["decision"]):
        row = seed_rows[idx]
        if int(row["year"]) not in years:
            continue
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        item = outcomes.get(idx)
        if item is None:
            continue
        a, f, exit_time = item
        actual.append(float(a))
        fixed.append(float(f))
        blocked_until = exit_time
    return c.metrics_from_values(actual), c.metrics_from_values(fixed)


def baseline_table(seed_rows: dict[str, list[dict[str, Any]]], outcomes: dict[str, dict[int, tuple[float, float, datetime] | None]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    splits = {"train": {2023, 2024}, "val2025": {2025}, "test2026": {2026}, "all": {2023, 2024, 2025, 2026}}
    for seed_id, rows in seed_rows.items():
        indices = set(range(len(rows)))
        seed_result: dict[str, Any] = {}
        for split, years in splits.items():
            m, fm = selected_metrics(rows, outcomes[seed_id], indices, years)
            for key, value in m.items():
                seed_result[f"{split}_{key}"] = value
            for key, value in fm.items():
                seed_result[f"fixed0p20_{split}_{key}"] = value
        result[seed_id] = seed_result
    return result


def score_gate_train(
    conditions: list[dict[str, Any]],
    seed_rows: dict[str, list[dict[str, Any]]],
    outcomes: dict[str, dict[int, tuple[float, float, datetime] | None]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    details: dict[str, Any] = {}
    lifts: list[float] = []
    retain_counts: list[int] = []
    for seed_id in RANKING_SEEDS:
        rows = seed_rows[seed_id]
        indices = gated_indices(rows, conditions)
        m, _ = selected_metrics(rows, outcomes[seed_id], indices, {2023, 2024})
        count = int(m["count"])
        pf = m["profit_factor_bps"]
        baseline_count = int(baselines[seed_id]["train_count"])
        baseline_pf = baselines[seed_id]["train_profit_factor_bps"]
        retention = count / baseline_count if baseline_count else 0.0
        if count < int(SEEDS[seed_id]["min_train"]) or retention < 0.30 or pf is None or baseline_pf is None:
            return None
        lift = float(pf) / float(baseline_pf)
        if lift < 0.95:
            return None
        details[f"{seed_id}_train_count"] = count
        details[f"{seed_id}_train_pf"] = pf
        details[f"{seed_id}_train_retention"] = retention
        details[f"{seed_id}_train_pf_lift"] = lift
        lifts.append(lift)
        retain_counts.append(count)
    details["min_train_pf_lift"] = min(lifts)
    details["mean_train_pf_lift"] = sum(lifts) / len(lifts)
    details["min_train_count"] = min(retain_counts)
    return details


def evaluate_gate(
    gate_id: str,
    formula_type: str,
    conditions: list[dict[str, Any]],
    discovery_rank: int,
    seed_rows: dict[str, list[dict[str, Any]]],
    outcomes: dict[str, dict[int, tuple[float, float, datetime] | None]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "gate_id": gate_id,
        "formula_type": formula_type,
        "formula": " AND ".join(f"{cnd['feature']} {cnd['op']} {float(cnd['threshold']):.10g}" for cnd in conditions),
        "conditions_json": json.dumps(conditions, sort_keys=True, separators=(",", ":")),
        "discovery_rank": discovery_rank,
    }
    splits = {"train": {2023, 2024}, "val2025": {2025}, "test2026": {2026}, "all": {2023, 2024, 2025, 2026}}
    for seed_id, rows in seed_rows.items():
        indices = gated_indices(rows, conditions)
        for split, years in splits.items():
            m, fm = selected_metrics(rows, outcomes[seed_id], indices, years)
            prefix = f"{seed_id}_{split}"
            for key, value in m.items():
                result[f"{prefix}_{key}"] = value
            for key, value in fm.items():
                result[f"{seed_id}_fixed0p20_{split}_{key}"] = value
            base_count = int(baselines[seed_id].get(f"{split}_count") or 0)
            base_pf = baselines[seed_id].get(f"{split}_profit_factor_bps")
            result[f"{prefix}_retention"] = (int(m["count"]) / base_count) if base_count else None
            result[f"{prefix}_pf_lift"] = (float(m["profit_factor_bps"]) / float(base_pf)) if (m["profit_factor_bps"] is not None and base_pf not in (None, 0)) else None
    return result


def seed_gate_is_pf2(row: dict[str, Any], seed_id: str) -> bool:
    counts = [int(row.get(f"{seed_id}_{split}_count") or 0) for split in ("train", "val2025", "test2026")]
    pfs = [row.get(f"{seed_id}_{split}_profit_factor_bps") for split in ("train", "val2025", "test2026")]
    fixed_pf = row.get(f"{seed_id}_fixed0p20_all_profit_factor_bps")
    return counts[0] >= 25 and counts[1] >= 12 and counts[2] >= 8 and all(pf is not None and float(pf) >= 2.0 for pf in pfs) and fixed_pf is not None and float(fixed_pf) > 1.0


def common_holdout_supported(row: dict[str, Any], baselines: dict[str, dict[str, Any]]) -> bool:
    for seed_id in RANKING_SEEDS:
        for split in ("train", "val2025", "test2026"):
            pf = row.get(f"{seed_id}_{split}_profit_factor_bps")
            if pf is None or float(pf) <= 1.0:
                return False
        for split in ("val2025", "test2026"):
            pf = row.get(f"{seed_id}_{split}_profit_factor_bps")
            base = baselines[seed_id].get(f"{split}_profit_factor_bps")
            if pf is None or base is None or float(pf) < float(base):
                return False
    return True


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10N contract")
        if set(contract["regime_definition"]["explicitly_excluded_exact_seed_features"]) != EXCLUDED_SEED_FEATURES:
            raise AuditError("M10N excluded seed-feature contract mismatch")
        if list(contract["regime_definition"]["regime_features"]) != REGIME_FEATURES:
            raise AuditError("M10N regime feature contract mismatch")

        local = local_root()
        data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual = c.sha256(path)
            if actual != expected:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = path
            hashes[tf] = actual
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}

        regime_rows = m10l.build_feature_rows(bars)
        regime_rows.sort(key=lambda row: row["decision"])
        train_regime_rows = [row for row in regime_rows if int(row["year"]) in (2023, 2024)]
        conditions = build_conditions(train_regime_rows)

        raw_seed_rows = build_seed_rows(bars)
        seed_rows = {seed_id: attach_regime(rows, regime_rows) for seed_id, rows in raw_seed_rows.items()}
        outcomes = {seed_id: build_outcomes(rows, int(SEEDS[seed_id]["horizon"]), bars["M1"]) for seed_id, rows in seed_rows.items()}
        baselines = baseline_table(seed_rows, outcomes)

        single_rows: list[dict[str, Any]] = []
        scored_singles: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for condition in conditions:
            score = score_gate_train([condition], seed_rows, outcomes, baselines)
            row = {"condition_id": condition["id"], "feature": condition["feature"], "op": condition["op"], "threshold": condition["threshold"], "eligible_common_discovery": score is not None}
            if score:
                row.update(score)
                scored_singles.append((condition, score))
            single_rows.append(row)

        scored_singles.sort(key=lambda item: (float(item[1]["min_train_pf_lift"]), float(item[1]["mean_train_pf_lift"]), int(item[1]["min_train_count"])), reverse=True)
        top_singles = scored_singles[:TOP_SINGLES_FOR_PAIRS]

        candidates: list[tuple[str, list[dict[str, Any]], dict[str, Any]]] = []
        for condition, score in scored_singles:
            candidates.append(("SINGLE", [condition], score))
        for (a, _), (b, _) in combinations(top_singles, 2):
            if a["feature"] == b["feature"]:
                continue
            score = score_gate_train([a, b], seed_rows, outcomes, baselines)
            if score is not None:
                candidates.append(("AND2", [a, b], score))

        candidates.sort(key=lambda item: (float(item[2]["min_train_pf_lift"]), float(item[2]["mean_train_pf_lift"]), int(item[2]["min_train_count"])), reverse=True)
        frozen = candidates[:SHORTLIST]

        evaluated: list[dict[str, Any]] = []
        for rank, (formula_type, conds, _) in enumerate(frozen, start=1):
            evaluated.append(evaluate_gate(f"M10N_G{rank:03d}", formula_type, conds, rank, seed_rows, outcomes, baselines))

        pf2_pairs: list[dict[str, Any]] = []
        for row in evaluated:
            for seed_id in SEEDS:
                if seed_gate_is_pf2(row, seed_id):
                    pf2_pairs.append({
                        "gate_id": row["gate_id"],
                        "seed_id": seed_id,
                        "formula": row["formula"],
                        "train_count": row[f"{seed_id}_train_count"],
                        "train_pf": row[f"{seed_id}_train_profit_factor_bps"],
                        "val2025_count": row[f"{seed_id}_val2025_count"],
                        "val2025_pf": row[f"{seed_id}_val2025_profit_factor_bps"],
                        "test2026_count": row[f"{seed_id}_test2026_count"],
                        "test2026_pf": row[f"{seed_id}_test2026_profit_factor_bps"],
                        "all_pf": row[f"{seed_id}_all_profit_factor_bps"],
                        "fixed0p20_all_pf": row[f"{seed_id}_fixed0p20_all_profit_factor_bps"],
                    })

        common_supported = [row for row in evaluated if common_holdout_supported(row, baselines)]
        common_supported.sort(key=lambda row: min(
            float(row.get("M10J_C0212_val2025_pf_lift") or 0),
            float(row.get("M10J_C0212_test2026_pf_lift") or 0),
            float(row.get("M10L_H240_C056_val2025_pf_lift") or 0),
            float(row.get("M10L_H240_C056_test2026_pf_lift") or 0),
        ), reverse=True)

        best_descriptive = sorted(evaluated, key=lambda row: min(
            float(row.get("M10J_C0212_train_profit_factor_bps") or 0),
            float(row.get("M10J_C0212_val2025_profit_factor_bps") or 0),
            float(row.get("M10J_C0212_test2026_profit_factor_bps") or 0),
            float(row.get("M10L_H240_C056_train_profit_factor_bps") or 0),
            float(row.get("M10L_H240_C056_val2025_profit_factor_bps") or 0),
            float(row.get("M10L_H240_C056_test2026_profit_factor_bps") or 0),
        ), reverse=True)[:20]

        baseline_json: dict[str, Any] = {}
        for seed_id, metrics in baselines.items():
            baseline_json[seed_id] = {
                "horizon_minutes": SEEDS[seed_id]["horizon"],
                "train_count": metrics.get("train_count"),
                "train_pf": metrics.get("train_profit_factor_bps"),
                "val2025_count": metrics.get("val2025_count"),
                "val2025_pf": metrics.get("val2025_profit_factor_bps"),
                "test2026_count": metrics.get("test2026_count"),
                "test2026_pf": metrics.get("test2026_profit_factor_bps"),
                "all_count": metrics.get("all_count"),
                "all_pf": metrics.get("all_profit_factor_bps"),
                "fixed0p20_all_pf": metrics.get("fixed0p20_all_profit_factor_bps"),
            }

        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_HISTORICAL_DOWNSIDE_REGIME_SPECIFIC_SHORT_RESEARCH_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regime_snapshot_count": len(regime_rows),
            "train_regime_snapshot_count": len(train_regime_rows),
            "regime_feature_count": len(REGIME_FEATURES),
            "generated_regime_condition_count": len(conditions),
            "eligible_single_gate_count": len(scored_singles),
            "frozen_regime_gate_count": len(evaluated),
            "seed_baselines": baseline_json,
            "robust_pf2_seed_gate_pair_count": len(pf2_pairs),
            "common_holdout_supported_gate_count": len(common_supported),
            "robust_pf2_seed_gate_pairs": pf2_pairs[:20],
            "best_common_holdout_supported_gates": common_supported[:20],
            "best_descriptive_common_min_pf_gates": best_descriptive,
            "interpretation": "Regime gates were generated and ranked using 2023-2024 only. Exact adoption-seed formula features were excluded from regime-gate generation to avoid tautology. 2025/2026 are descriptive locked holdouts after gate freeze.",
            "guardrails": contract["safety"],
        }

        out_root = local / "outputs" / "M10N"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10N downside-opportunity regime research. Regime gates are generated/ranked on 2023-2024 only; exact seed entry features are excluded from regime generation. Audit-only.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_frozen_regime_gate_results.csv", evaluated)
        write_csv(archive / "03_robust_pf2_seed_gate_pairs.csv", pf2_pairs)
        write_csv(archive / "04_common_holdout_supported_gates.csv", common_supported)
        write_csv(archive / "05_discovery_single_regime_conditions.csv", single_rows)
        write_csv(archive / "06_best_descriptive_common_min_pf_gates.csv", best_descriptive)
        (archive / "07_data_quality.json").write_text(json.dumps({
            "frozen_hashes": hashes,
            "newest_row_contract": "CLOSED",
            "time_basis": "MT5 server time",
            "nearest_m1_fallback": False,
            "exact_m1_entry_and_exit_only": True,
            "actual_spread_at_short_exit": True,
            "fixed_spread_sensitivity_usd": 0.20,
            "regime_gate_generation_uses_2025": False,
            "regime_gate_generation_uses_2026": False,
            "exact_seed_features_excluded_from_regime_generation": sorted(EXCLUDED_SEED_FEATURES),
            "regime_features": REGIME_FEATURES,
            "m7c_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "m10e_modified_or_reset": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "08_audit.log").write_text("\n".join([
            "status=PASS_HISTORICAL_DOWNSIDE_REGIME_SPECIFIC_SHORT_RESEARCH_ONLY",
            f"regime_snapshots={len(regime_rows)}",
            f"train_regime_snapshots={len(train_regime_rows)}",
            f"regime_features={len(REGIME_FEATURES)}",
            f"regime_conditions={len(conditions)}",
            f"eligible_single_gates={len(scored_singles)}",
            f"frozen_gates={len(evaluated)}",
            f"robust_pf2_seed_gate_pairs={len(pf2_pairs)}",
            f"common_holdout_supported_gates={len(common_supported)}",
            "regime_gate_generation_uses_2025=false",
            "regime_gate_generation_uses_2026=false",
            "exact_seed_features_excluded=true",
            "m7c_modified_or_reset=false",
            "m10b_modified_or_reset=false",
            "m10e_modified_or_reset=false",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")

        latest = out_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = [
            "00_READ_ME_FIRST.txt", "01_summary.json", "02_frozen_regime_gate_results.csv",
            "03_robust_pf2_seed_gate_pairs.csv", "04_common_holdout_supported_gates.csv",
            "05_discovery_single_regime_conditions.csv", "06_best_descriptive_common_min_pf_gates.csv",
            "07_data_quality.json", "08_audit.log",
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        print("[M10N PASS] Downside-regime SHORT research completed")
        print(f"[RESULT] frozen_gates={len(evaluated)} common_holdout_supported={len(common_supported)} robust_pf2_pairs={len(pf2_pairs)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10N BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] Existing forward monitors and all frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
