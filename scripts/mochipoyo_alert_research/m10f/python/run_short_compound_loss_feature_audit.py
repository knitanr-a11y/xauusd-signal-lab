from __future__ import annotations

import bisect
import csv
import itertools
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
MR = THIS.parents[2]
M10A_DIR = MR / "m10a" / "python"
if str(M10A_DIR) not in sys.path:
    sys.path.insert(0, str(M10A_DIR))

import frozen_core as c
import payoff_rules as pay

STAGE = "M10F_SHORT_COMPOUND_LOSS_FEATURE_AUDIT"
CONTRACT = THIS.parents[4] / "config" / "mochipoyo_alert_research" / "m10f_short_compound_loss_feature_audit_contract_20260725.json"
TIMEFRAMES = ("M5", "M15", "H1", "H4")
CONTEXT_TFS = ("M5", "M15", "H1", "H4", "D1")
TF_DELTA = {
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}
TRAIN_QUANTILES = (0.20, 0.35, 0.65, 0.80)
RETENTION_BANDS = (0.25, 0.50, 0.75)
MAX_SINGLE_PREDICATES = 24
TRIPLE_PREDICATES = 12
TOP_RULES_PER_BAND = 20
FIXED_SPREAD_USD = 0.20


class AuditError(RuntimeError):
    pass


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10F_GOLD_DATA_ROOT")
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def ratio20(bars: list[c.Bar]) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    rolling = 0
    for index, bar in enumerate(bars):
        rolling += bar.tick_volume
        if index >= 20:
            rolling -= bars[index - 20].tick_volume
        if index >= 19:
            mean = rolling / 20.0
            out[index] = None if mean == 0 else bar.tick_volume / mean
    return out


def returns_bps(bars: list[c.Bar], lookback: int) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    for index in range(lookback, len(bars)):
        previous = bars[index - lookback].close
        if previous != 0:
            out[index] = (bars[index].close - previous) / abs(previous) * 10000.0
    return out


def precompute_features(bars: dict[str, list[c.Bar]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for tf in CONTEXT_TFS:
        items = bars[tf]
        closes = [bar.close for bar in items]
        macd = c.macd_bps(items)
        rci9 = c.rci_series(closes, 9)
        ema20 = c.ema(closes, 20)
        ema30 = c.ema(closes, 30)
        ema40 = c.ema(closes, 40)
        atr14 = pay.wilder_atr14(items)
        vol20 = ratio20(items)
        ret1 = returns_bps(items, 1)
        ret3 = returns_bps(items, 3)
        feature_rows: list[dict[str, float | None]] = []
        for index, bar in enumerate(items):
            close = float(bar.close)
            denom = abs(close) if close != 0 else math.nan
            candle_range = float(bar.high - bar.low)
            close_pos = None if candle_range <= 0 else (float(bar.close) - float(bar.low)) / candle_range
            feature_rows.append({
                "macd_bps": float(macd[index]),
                "macd_slope": None if index == 0 else float(macd[index]) - float(macd[index - 1]),
                "rci9": None if rci9[index] is None else float(rci9[index]),
                "ema20_40_bps": None if not math.isfinite(denom) else (float(ema20[index]) - float(ema40[index])) / denom * 10000.0,
                "ema30_40_bps": None if not math.isfinite(denom) else (float(ema30[index]) - float(ema40[index])) / denom * 10000.0,
                "atr14_bps": None if atr14[index] is None or not math.isfinite(denom) else float(atr14[index]) / denom * 10000.0,
                "ret1_bps": ret1[index],
                "ret3_bps": ret3[index],
                "volume_ratio20": vol20[index],
                "body_bps": None if not math.isfinite(denom) else (float(bar.close) - float(bar.open)) / denom * 10000.0,
                "range_bps": None if not math.isfinite(denom) else candle_range / denom * 10000.0,
                "close_position": close_pos,
            })
        output[tf] = {
            "close_times": [bar.time + TF_DELTA[tf] for bar in items],
            "rows": feature_rows,
        }
    return output


def finite_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def annotate_short_rows(
    rows: list[dict[str, Any]],
    bars: dict[str, list[c.Bar]],
    features: dict[str, dict[str, Any]],
    *,
    point: float,
) -> list[dict[str, Any]]:
    m1_index = {bar.time: index for index, bar in enumerate(bars["M1"])}
    output: list[dict[str, Any]] = []
    for row in rows:
        decision = c.parse_time(str(row["turn_entry_time"]))
        exit_time = c.parse_time(str(row["exit_time"]))
        entry_index = m1_index.get(decision)
        exit_index = m1_index.get(exit_time)
        if entry_index is None or exit_index is None or exit_index <= entry_index:
            continue
        annotated: dict[str, Any] = dict(row)
        annotated["entry_year"] = decision.year
        annotated["mt5_server_hour"] = decision.hour
        annotated["entry_spread_usd"] = float(bars["M1"][entry_index].spread) * point
        entry_bid = float(bars["M1"][entry_index].open)
        fixed_exit_ask = float(bars["M1"][exit_index].open) + FIXED_SPREAD_USD
        annotated["fixed_spread_0p20_return_bps"] = (entry_bid - fixed_exit_ask) / abs(entry_bid) * 10000.0
        complete = True
        for tf in CONTEXT_TFS:
            close_times = features[tf]["close_times"]
            selected = bisect.bisect_right(close_times, decision) - 1
            if selected < 0:
                complete = False
                break
            feature_row = features[tf]["rows"][selected]
            for key, value in feature_row.items():
                annotated[f"{tf}_{key}"] = value
        if complete:
            output.append(annotated)
    return output


def period_rows(rows: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    if period == "train_2023_2024":
        return [row for row in rows if int(row["entry_year"]) in (2023, 2024)]
    if period == "validation_2025":
        return [row for row in rows if int(row["entry_year"]) == 2025]
    if period == "test_2026":
        return [row for row in rows if int(row["entry_year"]) == 2026]
    if period == "all":
        return list(rows)
    raise ValueError(period)


def metrics(rows: list[dict[str, Any]], value_key: str = "return_bps") -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: str(row["turn_entry_time"]))
    values = [float(row[value_key]) for row in ordered]
    return c.metrics_from_values(values)


def predicate_match(row: dict[str, Any], predicate: dict[str, Any]) -> bool:
    value = finite_number(row.get(str(predicate["feature"])))
    if value is None:
        return False
    threshold = float(predicate["threshold"])
    return value <= threshold if predicate["op"] == "<=" else value >= threshold


def clause_match(row: dict[str, Any], clause: list[dict[str, Any]]) -> bool:
    return all(predicate_match(row, predicate) for predicate in clause)


def rule_match(row: dict[str, Any], clauses: list[list[dict[str, Any]]]) -> bool:
    return any(clause_match(row, clause) for clause in clauses)


def format_clause(clause: list[dict[str, Any]]) -> str:
    return " AND ".join(f"{item['feature']} {item['op']} {float(item['threshold']):.8g}" for item in clause)


def format_rule(clauses: list[list[dict[str, Any]]]) -> str:
    return " OR ".join(f"({format_clause(clause)})" for clause in clauses)


def feature_names(rows: list[dict[str, Any]]) -> list[str]:
    excluded = {
        "trade_id", "direction", "proxy_entry_time", "turn_entry_time", "exit_time", "return_bps",
        "entry_year", "fixed_spread_0p20_return_bps",
    }
    names: list[str] = []
    if not rows:
        return names
    for key in rows[0].keys():
        if key in excluded:
            continue
        if any(finite_number(row.get(key)) is not None for row in rows):
            names.append(key)
    return names


def build_predicates(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predicates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, float]] = set()
    for feature in feature_names(train_rows):
        values = sorted(value for row in train_rows if (value := finite_number(row.get(feature))) is not None)
        if len(values) < 20:
            continue
        specs = ((0.20, "<="), (0.35, "<="), (0.65, ">="), (0.80, ">="))
        for q, op in specs:
            threshold = c.quantile_sorted(values, q)
            key = (feature, op, round(float(threshold), 10))
            if key in seen:
                continue
            seen.add(key)
            predicates.append({"feature": feature, "op": op, "threshold": float(threshold), "train_quantile": q})
    return predicates


def exclusion_stats(rows: list[dict[str, Any]], clauses: list[list[dict[str, Any]]]) -> dict[str, Any] | None:
    if not rows:
        return None
    matched = [row for row in rows if rule_match(row, clauses)]
    if len(matched) < max(12, int(math.ceil(len(rows) * 0.03))) or len(matched) > int(math.floor(len(rows) * 0.70)):
        return None
    baseline_values = [float(row["return_bps"]) for row in rows]
    matched_values = [float(row["return_bps"]) for row in matched]
    baseline_loss = abs(sum(value for value in baseline_values if value < 0))
    inside_loss = abs(sum(value for value in matched_values if value < 0))
    support = len(matched) / len(rows)
    loss_share = 0.0 if baseline_loss == 0 else inside_loss / baseline_loss
    loss_concentration = loss_share - support
    if loss_concentration <= 0:
        return None
    kept = [row for row in rows if not rule_match(row, clauses)]
    if len(kept) < max(20, int(math.ceil(len(rows) * 0.20))):
        return None
    inside_loss_rate = sum(value < 0 for value in matched_values) / len(matched_values)
    return {
        "excluded_count": len(matched),
        "retained_count": len(kept),
        "retention": len(kept) / len(rows),
        "excluded_support": support,
        "excluded_gross_loss_share": loss_share,
        "excluded_loss_concentration": loss_concentration,
        "excluded_loss_rate": inside_loss_rate,
        "kept_metrics": metrics(kept),
    }


def shortlist_predicates(train_rows: list[dict[str, Any]], predicates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for predicate in predicates:
        stats = exclusion_stats(train_rows, [[predicate]])
        if stats is None:
            continue
        scored.append({**predicate, **stats})
    scored.sort(key=lambda item: (float(item["excluded_loss_concentration"]), float(item["excluded_gross_loss_share"])), reverse=True)
    output: list[dict[str, Any]] = []
    per_feature: dict[str, int] = {}
    for item in scored:
        feature = str(item["feature"])
        if per_feature.get(feature, 0) >= 2:
            continue
        output.append({key: item[key] for key in ("feature", "op", "threshold", "train_quantile")})
        per_feature[feature] = per_feature.get(feature, 0) + 1
        if len(output) >= MAX_SINGLE_PREDICATES:
            break
    return output


def build_clause_candidates(train_rows: list[dict[str, Any]], shortlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for size, pool in ((2, shortlist), (3, shortlist[:TRIPLE_PREDICATES])):
        for combo in itertools.combinations(pool, size):
            if len({str(item["feature"]) for item in combo}) != size:
                continue
            clauses = [[dict(item) for item in combo]]
            stats = exclusion_stats(train_rows, clauses)
            if stats is None:
                continue
            candidates.append({
                "kind": f"AND{size}",
                "clauses": clauses,
                "formula": format_rule(clauses),
                **stats,
            })
    return candidates


def top_by_retention(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for floor in RETENTION_BANDS:
        eligible = [item for item in candidates if float(item["retention"]) >= floor]
        eligible.sort(
            key=lambda item: (
                float(item["kept_metrics"].get("profit_factor_bps") or -math.inf),
                float(item["kept_metrics"].get("net_bps") or -math.inf),
                int(item["retained_count"]),
            ),
            reverse=True,
        )
        for item in eligible[:TOP_RULES_PER_BAND]:
            copy = dict(item)
            copy.setdefault("retention_bands_selected", [])
            selected.setdefault(str(item["formula"]), copy)
            selected[str(item["formula"])].setdefault("retention_bands_selected", []).append(floor)
    return list(selected.values())


def build_union_candidates(train_rows: list[dict[str, Any]], base_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        base_candidates,
        key=lambda item: (
            float(item["kept_metrics"].get("profit_factor_bps") or -math.inf),
            float(item["kept_metrics"].get("net_bps") or -math.inf),
        ),
        reverse=True,
    )[:15]
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for left, right in itertools.combinations(ranked, 2):
        clauses = [list(map(dict, clause)) for clause in left["clauses"]] + [list(map(dict, clause)) for clause in right["clauses"]]
        formula = format_rule(clauses)
        if formula in seen:
            continue
        seen.add(formula)
        stats = exclusion_stats(train_rows, clauses)
        if stats is None:
            continue
        output.append({"kind": "OR2_COMPOUND", "clauses": clauses, "formula": formula, **stats})
    return output


def prefixed_metrics(prefix: str, rows: list[dict[str, Any]], clauses: list[list[dict[str, Any]]] | None, value_key: str) -> dict[str, Any]:
    kept = rows if clauses is None else [row for row in rows if not rule_match(row, clauses)]
    result = metrics(kept, value_key=value_key)
    return {f"{prefix}_{key}": value for key, value in result.items()}


def evaluate_candidate(all_rows: list[dict[str, Any]], candidate: dict[str, Any]) -> dict[str, Any]:
    clauses = candidate["clauses"]
    result: dict[str, Any] = {
        "kind": candidate["kind"],
        "formula": candidate["formula"],
        "clauses_json": json.dumps(clauses, ensure_ascii=False, separators=(",", ":")),
        "train_excluded_count": candidate["excluded_count"],
        "train_retention": candidate["retention"],
        "train_excluded_gross_loss_share": candidate["excluded_gross_loss_share"],
        "train_excluded_loss_concentration": candidate["excluded_loss_concentration"],
        "retention_bands_selected": ",".join(str(x) for x in sorted(set(candidate.get("retention_bands_selected", [])))),
    }
    for period, prefix in (
        ("train_2023_2024", "train"),
        ("validation_2025", "val2025"),
        ("test_2026", "test2026"),
        ("all", "all"),
    ):
        rows = period_rows(all_rows, period)
        result.update(prefixed_metrics(prefix, rows, clauses, "return_bps"))
        result.update(prefixed_metrics(f"fixed0p20_{prefix}", rows, clauses, "fixed_spread_0p20_return_bps"))
    result["pf2_all"] = (result.get("all_profit_factor_bps") or 0) >= 2.0
    result["pf2_validation_2025"] = (result.get("val2025_profit_factor_bps") or 0) >= 2.0
    result["pf2_final_test_2026"] = (result.get("test2026_profit_factor_bps") or 0) >= 2.0
    result["pf2_train_val_test_all"] = bool(result["pf2_all"] and result["pf2_validation_2025"] and result["pf2_final_test_2026"] and (result.get("train_profit_factor_bps") or 0) >= 2.0)
    return result


def baseline_row(tf: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"timeframe": tf}
    for period, prefix in (
        ("train_2023_2024", "train"),
        ("validation_2025", "val2025"),
        ("test_2026", "test2026"),
        ("all", "all"),
    ):
        selected = period_rows(rows, period)
        result.update(prefixed_metrics(prefix, selected, None, "return_bps"))
        result.update(prefixed_metrics(f"fixed0p20_{prefix}", selected, None, "fixed_spread_0p20_return_bps"))
    return result


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
    data_root = resolve_data_root(local_root)
    point = float(os.environ.get("M10F_POINT", str(c.POINT)))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M10F BLOCKED] data root or point unavailable: {data_root} point={point}")
        return 2

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10F contract")

        paths: dict[str, Path] = {}
        for tf, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing required GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise AuditError(f"SHA256 mismatch {filename}: {actual_hash}")
            paths[tf] = path
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        features = precompute_features(bars)

        ledgers: dict[str, list[dict[str, Any]]] = {}
        baselines: list[dict[str, Any]] = []
        candidate_rows: list[dict[str, Any]] = []
        summary_by_tf: dict[str, Any] = {}

        for tf in TIMEFRAMES:
            turns = c.build_timeframe_turns(bars[tf], bars["M1"], point, f"M10F_{tf}")
            short_rows = [row for row in turns if row["direction"] == "SHORT"]
            annotated = annotate_short_rows(short_rows, bars, features, point=point)
            ledgers[tf] = annotated
            baseline = baseline_row(tf, annotated)
            baselines.append(baseline)

            train = period_rows(annotated, "train_2023_2024")
            predicates = build_predicates(train)
            shortlist = shortlist_predicates(train, predicates)
            clause_candidates = build_clause_candidates(train, shortlist)
            selected_base = top_by_retention(clause_candidates)
            union_candidates = build_union_candidates(train, selected_base)
            selected_union = top_by_retention(union_candidates)

            unique: dict[str, dict[str, Any]] = {}
            for item in selected_base + selected_union:
                formula = str(item["formula"])
                if formula not in unique:
                    unique[formula] = item
                else:
                    bands = set(unique[formula].get("retention_bands_selected", [])) | set(item.get("retention_bands_selected", []))
                    unique[formula]["retention_bands_selected"] = sorted(bands)

            evaluated: list[dict[str, Any]] = []
            for number, item in enumerate(unique.values(), start=1):
                row = {"timeframe": tf, "candidate_id": f"M10F_{tf}_C{number:04d}", **evaluate_candidate(annotated, item)}
                evaluated.append(row)
                candidate_rows.append(row)

            train_ranked = sorted(
                evaluated,
                key=lambda row: (
                    float(row.get("train_profit_factor_bps") or -math.inf),
                    float(row.get("train_net_bps") or -math.inf),
                ),
                reverse=True,
            )
            summary_by_tf[tf] = {
                "raw_short_count": len(annotated),
                "baseline": baseline,
                "train_predicates_generated": len(predicates),
                "train_predicates_shortlisted": len(shortlist),
                "train_compound_rules_generated": len(clause_candidates),
                "train_selected_base_rules": len(selected_base),
                "train_union_rules_generated": len(union_candidates),
                "train_selected_union_rules": len(selected_union),
                "reported_candidate_rules": len(evaluated),
                "pf2_all_count": sum(bool(row["pf2_all"]) for row in evaluated),
                "pf2_validation_2025_count": sum(bool(row["pf2_validation_2025"]) for row in evaluated),
                "pf2_final_test_2026_count": sum(bool(row["pf2_final_test_2026"]) for row in evaluated),
                "pf2_train_val_test_all_count": sum(bool(row["pf2_train_val_test_all"]) for row in evaluated),
                "top_train_only_candidates": train_ranked[:5],
            }

    except Exception as exc:
        print(f"[M10F BLOCKED] {type(exc).__name__}: {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_HISTORICAL_SHORT_COMPOUND_LOSS_AUDIT_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample": "research-exposed frozen GOLD history 2023-01-03 through 2026-06-19; not fresh forward evidence",
        "target_pf": 2.0,
        "target_pf_is_descriptive_not_auto_adoption": True,
        "timeframes": summary_by_tf,
        "search_contract": {
            "discovery": "2023-2024 only",
            "validation": "2025 only",
            "final_test": "2026 through 2026-06-19 only",
            "formula_generation_uses_2025": False,
            "formula_generation_uses_2026": False,
            "long_rule_mirroring": False,
            "retention_bands": list(RETENTION_BANDS),
            "fixed_spread_usd": FIXED_SPREAD_USD,
        },
        "guardrails": {
            "historical_research_exposed": True,
            "fresh_forward_validated": False,
            "m9v_modified_or_reset": False,
            "m9y_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "m10e_modified_or_reset": False,
            "historical_backfill": False,
            "automatic_live_promotion": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "audit_only": True,
        },
        "next": "Review holdout robustness manually. Any promising SHORT rule must pass a separate deterministic reproduction before any independently frozen fresh prospective SHORT arm is considered.",
    }

    output_root = Path(os.environ.get("M10F_OUTPUT_ROOT", "")) if os.environ.get("M10F_OUTPUT_ROOT") else local_root / "outputs" / "M10F"
    archive = output_root / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10F audits SHORT-side entry-time compound loss regions on frozen historical GOLD data.\n"
        "Rules are generated from 2023-2024 only. 2025 is validation and 2026 is final test.\n"
        "PF2 markers are descriptive only; no forward monitor is modified or promoted.\n"
        "Submit 99_UPLOAD_PACKAGE.zip only.\n",
        encoding="utf-8",
    )
    c.dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_short_baselines.csv", baselines)
    write_csv(archive / "03_short_compound_candidates.csv", candidate_rows)
    for index, tf in enumerate(TIMEFRAMES, start=4):
        write_csv(archive / f"{index:02d}_{tf.lower()}_short_feature_ledger.csv", ledgers[tf])
    c.dump_json(archive / "08_data_quality.json", {
        "data_root": str(data_root),
        "point": point,
        "hashes": {tf: {"file": filename, "sha256": digest} for tf, (filename, digest) in c.EXPECTED_FILES.items()},
        "newest_csv_row_contract": "CLOSED",
        "nearest_m1_fallback": False,
    })
    (archive / "09_audit.log").write_text("\n".join([
        "status=PASS_HISTORICAL_SHORT_COMPOUND_LOSS_AUDIT_ONLY",
        "discovery=2023-2024_only",
        "validation=2025_only",
        "final_test=2026_through_0619_only",
        "long_rule_mirroring=false",
        "future_outcome_used_as_feature=false",
        "m9v_modified_or_reset=false",
        "m9y_modified_or_reset=false",
        "m10b_modified_or_reset=false",
        "m10e_modified_or_reset=false",
        "historical_backfill=false",
        "automatic_live_promotion=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")
    names = [path.name for path in archive.iterdir() if path.is_file()]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(names):
            zf.write(archive / name, name)
    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print("[M10F PASS] historical SHORT compound-loss audit complete")
    for tf in TIMEFRAMES:
        info = summary_by_tf[tf]
        base_pf = info["baseline"].get("all_profit_factor_bps")
        print(
            f"[M10F {tf}] baseline_count={info['raw_short_count']} PF={base_pf} "
            f"candidates={info['reported_candidate_rules']} PF2_all={info['pf2_all_count']} "
            f"PF2_train_val_test_all={info['pf2_train_val_test_all_count']}"
        )
    print("[M10F OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
