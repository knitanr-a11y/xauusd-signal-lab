from __future__ import annotations

import bisect
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
M10A_DIR = THIS.parents[2] / "m10a" / "python"
if str(M10A_DIR) not in sys.path:
    sys.path.insert(0, str(M10A_DIR))

import frozen_core as c
import payoff_rules as p

STAGE = "M10D_H1_COMPOUND_LOSS_FILTER_DETERMINISTIC_REPRODUCTION"
M5_MACD_SLOPE_LE = -0.1308
H1_EMA30_MINUS_EMA40_BPS_GE = 17.3333
FIXED_SPREAD_USD = 0.20
H1_RUNNER_SHARE = 0.50
M5_SLOPE_NEIGHBORHOOD = (-0.20, -0.16, -0.13, -0.10, -0.06)
H1_STACK_NEIGHBORHOOD = (12.5, 15.0, 17.5, 20.0, 22.5)
EXPECTED_BASELINE = {
    "count": 159,
    "win_rate": 0.6792452830188679,
    "pf": 2.8303858342555084,
    "avg_win": 40.12947532813278,
    "avg_loss": -30.024198246139303,
    "payoff": 1.3365710883984345,
}
EXPECTED_FILTERED = {
    "count": 130,
    "win_rate": 0.7384615384615385,
    "pf": 5.4011538832619195,
    "avg_win": 37.78959763996185,
    "avg_loss": -19.755045440539647,
    "payoff": 1.9129086669885966,
    "net": 2956.12982845799,
}
EXPECTED_YEARLY = {
    "2023": {"count": 31, "pf": 6.305704093248458, "payoff": 2.1932883802603333},
    "2024": {"count": 49, "pf": 5.002500062921975, "payoff": 1.1255625141574443},
    "2025": {"count": 40, "pf": 4.16184709325092, "payoff": 2.497108255950552},
    "2026": {"count": 10, "pf": 11.629177619564157, "payoff": 2.907294404891039},
}
EXPECTED_FIXED_SPREAD = {"count": 130, "pf": 5.3636874914829455, "payoff": 1.8996393199002097}
EXPECTED_NEIGHBORHOOD = {"cells": 25, "improve_2025_2026": 5, "improve_every_year": 5}


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10D_GOLD_DATA_ROOT")
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_metrics(label: str, actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if int(actual["count"]) != int(expected["count"]):
        raise RuntimeError(f"{label}.count mismatch actual={actual['count']} expected={expected['count']}")
    mapping = {
        "win_rate": "win_rate",
        "profit_factor_bps": "pf",
        "average_win_bps": "avg_win",
        "average_loss_bps": "avg_loss",
        "payoff_ratio": "payoff",
        "net_bps": "net",
    }
    for actual_key, expected_key in mapping.items():
        if expected_key in expected:
            c.assert_close(f"{label}.{actual_key}", float(actual[actual_key]), float(expected[expected_key]))


def annotate_entry_features(rows: list[dict[str, Any]], m5: list[c.Bar], h1: list[c.Bar], *, slope_le: float, stack_ge: float) -> list[dict[str, Any]]:
    m5_close_times = [bar.time + timedelta(minutes=5) for bar in m5]
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    m5_macd = c.macd_bps(m5)
    h1_closes = [bar.close for bar in h1]
    h1_ema30 = c.ema(h1_closes, 30)
    h1_ema40 = c.ema(h1_closes, 40)
    output: list[dict[str, Any]] = []
    for row in rows:
        decision = c.parse_time(str(row["actual_entry_time"]))
        i5 = bisect.bisect_right(m5_close_times, decision) - 1
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        if i5 <= 0 or ih1 < 0:
            raise RuntimeError(f"entry feature context unavailable at {row['actual_entry_time']}")
        slope = float(m5_macd[i5]) - float(m5_macd[i5 - 1])
        close = float(h1_closes[ih1])
        if close == 0.0:
            raise RuntimeError(f"zero H1 close at {row['actual_entry_time']}")
        stack_bps = (float(h1_ema30[ih1]) - float(h1_ema40[ih1])) / abs(close) * 10000.0
        excluded = slope <= slope_le and stack_bps >= stack_ge
        output.append({
            **row,
            "entry_feature_m5_closed_index": i5,
            "entry_feature_h1_closed_index": ih1,
            "m5_macd_bps_slope": slope,
            "h1_ema30_minus_ema40_bps": stack_bps,
            "compound_filter_m5_macd_slope_le": slope_le,
            "compound_filter_h1_stack_ge": stack_ge,
            "compound_filter_excluded": excluded,
        })
    return output


def apply_filter(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept = [row for row in rows if not bool(row["compound_filter_excluded"])]
    excluded = [row for row in rows if bool(row["compound_filter_excluded"])]
    return kept, excluded


def one_position_after_filter(rows: list[dict[str, Any]], m5: list[c.Bar], h1: list[c.Bar], *, slope_le: float, stack_ge: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    annotated = annotate_entry_features(rows, m5, h1, slope_le=slope_le, stack_ge=stack_ge)
    kept, excluded = apply_filter(annotated)
    accepted, overlap = p.one_position_runner(kept, runner_share=H1_RUNNER_SHARE)
    return accepted, overlap, excluded, annotated


def fixed_spread_rows(rows: list[dict[str, Any]], m1: list[c.Bar], spread_usd: float) -> list[dict[str, Any]]:
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    output: list[dict[str, Any]] = []
    for row in rows:
        entry_time = c.parse_time(str(row["actual_entry_time"]))
        native_exit_time = c.parse_time(str(row["exit_time"]))
        entry_index = m1_index.get(entry_time)
        exit_index = m1_index.get(native_exit_time)
        if entry_index is None or exit_index is None:
            raise RuntimeError(f"M1 fixed-spread context unavailable for {row['actual_entry_time']}")
        entry_exec = float(m1[entry_index].open) + spread_usd
        native_return = (float(m1[exit_index].open) - entry_exec) / abs(entry_exec) * 10000.0
        runner_return = native_return
        runner_exit_raw = row.get("runner_exit_time")
        if runner_exit_raw not in (None, ""):
            runner_time = c.parse_time(str(runner_exit_raw))
            runner_index = m1_index.get(runner_time)
            if runner_index is None:
                raise RuntimeError(f"M1 runner fixed-spread context unavailable for {runner_exit_raw}")
            runner_return = (float(m1[runner_index].open) - entry_exec) / abs(entry_exec) * 10000.0
        output.append({**row, "entry_exec": entry_exec, "native_return_bps": native_return, "runner_return_bps": runner_return, "fixed_spread_usd": spread_usd})
    return output


def yearly_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["year"]): row for row in p.group_metrics(rows, value_key="weighted_return_bps", time_key="actual_entry_time", mode="year")}


def strictly_improves(filtered: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return (
        filtered.get("profit_factor_bps") is not None
        and baseline.get("profit_factor_bps") is not None
        and filtered.get("payoff_ratio") is not None
        and baseline.get("payoff_ratio") is not None
        and float(filtered["profit_factor_bps"]) > float(baseline["profit_factor_bps"])
        and float(filtered["payoff_ratio"]) > float(baseline["payoff_ratio"])
    )


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    data_root = resolve_data_root(local_root)
    point = float(os.environ.get("M10D_POINT", str(c.POINT)))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M10D BLOCKED] data root or point unavailable: {data_root} point={point}")
        return 2

    try:
        paths: dict[str, Path] = {}
        for timeframe, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise RuntimeError(f"missing required GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise RuntimeError(f"SHA256 mismatch {filename}: {actual_hash}")
            paths[timeframe] = path
        bars = {timeframe: c.load_bars(path) for timeframe, path in paths.items()}

        close_times = {
            "H4": [bar.time + timedelta(hours=4) for bar in bars["H4"]],
            "D1": [bar.time + timedelta(days=1) for bar in bars["D1"]],
        }
        h1_turns = c.build_timeframe_turns(bars["H1"], bars["M1"], point, "M10D_H1")
        h1_longs = [row for row in h1_turns if row["direction"] == "LONG"]
        c.enrich_indices(h1_longs, close_times, ("H4", "D1"))
        macd_h4 = c.macd_bps(bars["H4"])
        macd_d1 = c.macd_bps(bars["D1"])
        h1_s3 = c.select_s3(h1_longs, macd_h4, macd_d1)
        raw_metrics = c.raw_metrics(h1_s3)
        if raw_metrics["count"] != 191:
            raise RuntimeError(f"H1_S3 count mismatch actual={raw_metrics['count']} expected=191")
        c.assert_close("H1_S3.pf", float(raw_metrics["profit_factor_bps"]), 1.7802349633701025)

        h1_entry = p.build_htf_reclaim(
            h1_s3,
            bars["M1"],
            bars["H1"],
            bars["M5"],
            signal_delta=timedelta(hours=1),
            confirm_delta=timedelta(minutes=5),
            offset_atr=p.H1_ENTRY_OFFSET_ATR,
            wait_minutes=p.H1_ENTRY_WAIT_MINUTES,
            point=point,
            confirm_name="M5",
        )
        if len(h1_entry) != 171:
            raise RuntimeError(f"H1 reclaim count mismatch actual={len(h1_entry)} expected=171")

        h1_meta = p.build_runner_meta(
            h1_entry,
            bars["M1"],
            bars["H1"],
            context_bars=(bars["H4"], bars["D1"]),
            context_deltas=(timedelta(hours=4), timedelta(days=1)),
        )
        baseline, baseline_overlap = p.one_position_runner(h1_meta, runner_share=H1_RUNNER_SHARE)
        baseline_metrics = p.metric_rows(baseline, value_key="weighted_return_bps", time_key="actual_entry_time")
        verify_metrics("baseline", baseline_metrics, EXPECTED_BASELINE)
        if len(baseline_overlap) != 12:
            raise RuntimeError(f"baseline overlap mismatch actual={len(baseline_overlap)} expected=12")

        filtered, filtered_overlap, excluded, annotated = one_position_after_filter(
            h1_meta,
            bars["M5"],
            bars["H1"],
            slope_le=M5_MACD_SLOPE_LE,
            stack_ge=H1_EMA30_MINUS_EMA40_BPS_GE,
        )
        filtered_metrics = p.metric_rows(filtered, value_key="weighted_return_bps", time_key="actual_entry_time")
        verify_metrics("filtered", filtered_metrics, EXPECTED_FILTERED)

        baseline_yearly = yearly_map(baseline)
        filtered_yearly = yearly_map(filtered)
        for year, expected in EXPECTED_YEARLY.items():
            actual = filtered_yearly.get(year)
            if actual is None:
                raise RuntimeError(f"filtered yearly missing {year}")
            if int(actual["count"]) != int(expected["count"]):
                raise RuntimeError(f"filtered {year} count mismatch actual={actual['count']} expected={expected['count']}")
            c.assert_close(f"filtered.{year}.pf", float(actual["profit_factor_bps"]), float(expected["pf"]))
            c.assert_close(f"filtered.{year}.payoff", float(actual["payoff_ratio"]), float(expected["payoff"]))

        fixed_annotated = fixed_spread_rows(annotated, bars["M1"], FIXED_SPREAD_USD)
        fixed_kept, _ = apply_filter(fixed_annotated)
        fixed_filtered, fixed_overlap = p.one_position_runner(fixed_kept, runner_share=H1_RUNNER_SHARE)
        fixed_metrics = p.metric_rows(fixed_filtered, value_key="weighted_return_bps", time_key="actual_entry_time")
        if fixed_metrics["count"] != EXPECTED_FIXED_SPREAD["count"]:
            raise RuntimeError(f"fixed spread count mismatch actual={fixed_metrics['count']}")
        c.assert_close("fixed_spread.pf", float(fixed_metrics["profit_factor_bps"]), EXPECTED_FIXED_SPREAD["pf"])
        c.assert_close("fixed_spread.payoff", float(fixed_metrics["payoff_ratio"]), EXPECTED_FIXED_SPREAD["payoff"])

        neighborhood_rows: list[dict[str, Any]] = []
        improve_2025_2026 = 0
        improve_every_year = 0
        for slope_le in M5_SLOPE_NEIGHBORHOOD:
            for stack_ge in H1_STACK_NEIGHBORHOOD:
                candidate, overlap, candidate_excluded, _ = one_position_after_filter(
                    h1_meta,
                    bars["M5"],
                    bars["H1"],
                    slope_le=slope_le,
                    stack_ge=stack_ge,
                )
                metrics = p.metric_rows(candidate, value_key="weighted_return_bps", time_key="actual_entry_time")
                candidate_yearly = yearly_map(candidate)
                pass_2025_2026 = all(
                    year in candidate_yearly and year in baseline_yearly and strictly_improves(candidate_yearly[year], baseline_yearly[year])
                    for year in ("2025", "2026")
                )
                pass_every_year = all(
                    year in candidate_yearly and year in baseline_yearly and strictly_improves(candidate_yearly[year], baseline_yearly[year])
                    for year in ("2023", "2024", "2025", "2026")
                )
                improve_2025_2026 += int(pass_2025_2026)
                improve_every_year += int(pass_every_year)
                neighborhood_rows.append({
                    "m5_macd_slope_le": slope_le,
                    "h1_ema30_minus_ema40_bps_ge": stack_ge,
                    "excluded_before_one_position": len(candidate_excluded),
                    "accepted_count": metrics["count"],
                    "overlap_skips": len(overlap),
                    "profit_factor_bps": metrics["profit_factor_bps"],
                    "payoff_ratio": metrics["payoff_ratio"],
                    "improves_pf_payoff_2025_and_2026": pass_2025_2026,
                    "improves_pf_payoff_every_year_2023_2026": pass_every_year,
                })
        if len(neighborhood_rows) != EXPECTED_NEIGHBORHOOD["cells"]:
            raise RuntimeError(f"neighborhood cell mismatch actual={len(neighborhood_rows)}")
        if improve_2025_2026 != EXPECTED_NEIGHBORHOOD["improve_2025_2026"]:
            raise RuntimeError(f"neighborhood 2025/2026 pass mismatch actual={improve_2025_2026} expected=5")
        if improve_every_year != EXPECTED_NEIGHBORHOOD["improve_every_year"]:
            raise RuntimeError(f"neighborhood every-year pass mismatch actual={improve_every_year} expected=5")

        extra_cost2 = p.metric_rows(filtered, value_key="weighted_return_bps", time_key="actual_entry_time", extra_cost_bps=2.0)

    except Exception as exc:
        print(f"[M10D BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample": "research-exposed frozen GOLD history 2023-01-03 through 2026-06-19; not fresh forward evidence",
        "fixed_rule": {
            "direction": "EXCLUDE_H1_LONG_ENTRY",
            "condition": "latest fully closed M5 MACD(6,13) bps slope <= threshold AND latest fully closed H1 EMA30-EMA40 distance bps >= threshold",
            "m5_macd_bps_slope_le": M5_MACD_SLOPE_LE,
            "h1_ema30_minus_ema40_bps_ge": H1_EMA30_MINUS_EMA40_BPS_GE,
            "feature_decision_time": "actual H1 reclaim entry time; closed bars at or before that time only",
        },
        "baseline": {**baseline_metrics, "overlap_skips": len(baseline_overlap)},
        "filtered": {**filtered_metrics, "excluded_before_one_position": len(excluded), "overlap_skips": len(filtered_overlap)},
        "filtered_yearly": filtered_yearly,
        "fixed_spread_0p20_usd": {**fixed_metrics, "overlap_skips": len(fixed_overlap)},
        "extra_2bps_after_historical_spread": extra_cost2,
        "neighborhood": {
            "cells": len(neighborhood_rows),
            "m5_macd_slope_thresholds": list(M5_SLOPE_NEIGHBORHOOD),
            "h1_stack_thresholds": list(H1_STACK_NEIGHBORHOOD),
            "cells_improving_both_pf_and_payoff_in_2025_and_2026": improve_2025_2026,
            "cells_improving_both_pf_and_payoff_in_every_calendar_year": improve_every_year,
        },
        "anti_leakage": {
            "future_outcome_used_in_entry_gate": False,
            "mae_mfe_exit_path_used_as_filter_feature": False,
            "outcome_used_only_for_scoring": True,
            "closed_bars_only": True,
            "one_position_recomputed_after_filter": True,
        },
        "guardrails": {
            "newest_csv_row_contract": "CLOSED",
            "time_basis": "MT5_SERVER_TIME",
            "historical_spread_used": True,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
            "historical_research_exposed": True,
            "fresh_forward_validated": False,
            "m9y_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "historical_backfill": False,
            "automatic_live_promotion": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "audit_only": True,
        },
        "next": "After user-local M10D PASS and package review, freeze a separate new fresh prospective H1 baseline-vs-filter comparison arm. Do not retrofit M10B or reuse any existing start.",
    }

    out_root = Path(os.environ.get("M10D_OUTPUT_ROOT", "")) if os.environ.get("M10D_OUTPUT_ROOT") else local_root / "outputs" / "M10D"
    archive = out_root / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10D deterministically reproduces the H1 compound-loss entry filter found in M10C.\n"
        "Historical audit only. M9Y/M10B are not changed/reset/backfilled.\n"
        "PASS is not fresh validation and does not authorize live promotion.\n"
        "Submit 99_UPLOAD_PACKAGE.zip only.\n",
        encoding="utf-8",
    )
    c.dump_json(archive / "01_summary.json", summary)
    c.write_csv(archive / "02_baseline_h1_runner50_ledger.csv", baseline)
    c.write_csv(archive / "03_filtered_h1_runner50_ledger.csv", filtered)
    c.write_csv(archive / "04_excluded_entry_candidates.csv", excluded)
    c.write_csv(archive / "05_filtered_overlap_skips.csv", filtered_overlap)
    c.write_csv(archive / "06_yearly.csv", [{"scope": "baseline", **row} for row in baseline_yearly.values()] + [{"scope": "filtered", **row} for row in filtered_yearly.values()])
    c.write_csv(archive / "07_neighborhood.csv", neighborhood_rows)
    c.dump_json(archive / "08_fixed_spread_0p20_summary.json", fixed_metrics)
    c.dump_json(archive / "09_data_quality.json", {
        "data_root": str(data_root),
        "point": point,
        "hashes": {tf: {"file": filename, "sha256": digest} for tf, (filename, digest) in c.EXPECTED_FILES.items()},
        "newest_csv_row_contract": "CLOSED",
        "nearest_m1_fallback": False,
    })
    (archive / "10_audit.log").write_text("\n".join([
        "status=PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY",
        f"baseline_count={baseline_metrics['count']} PF={baseline_metrics['profit_factor_bps']} payoff={baseline_metrics['payoff_ratio']}",
        f"filtered_count={filtered_metrics['count']} PF={filtered_metrics['profit_factor_bps']} payoff={filtered_metrics['payoff_ratio']}",
        f"fixed_spread_0p20_count={fixed_metrics['count']} PF={fixed_metrics['profit_factor_bps']} payoff={fixed_metrics['payoff_ratio']}",
        f"neighborhood_pass_2025_2026={improve_2025_2026}",
        f"neighborhood_pass_every_year={improve_every_year}",
        "future_outcome_used_in_entry_gate=false",
        "m9y_modified_or_reset=false",
        "m10b_modified_or_reset=false",
        "historical_backfill=false",
        "automatic_live_promotion=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")
    names = [
        "00_READ_ME_FIRST.txt",
        "01_summary.json",
        "02_baseline_h1_runner50_ledger.csv",
        "03_filtered_h1_runner50_ledger.csv",
        "04_excluded_entry_candidates.csv",
        "05_filtered_overlap_skips.csv",
        "06_yearly.csv",
        "07_neighborhood.csv",
        "08_fixed_spread_0p20_summary.json",
        "09_data_quality.json",
        "10_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(
        "[M10D PASS] "
        f"baseline={baseline_metrics['count']} PF={baseline_metrics['profit_factor_bps']:.12f} payoff={baseline_metrics['payoff_ratio']:.12f} "
        f"filtered={filtered_metrics['count']} PF={filtered_metrics['profit_factor_bps']:.12f} payoff={filtered_metrics['payoff_ratio']:.12f} "
        f"spread0.20PF={fixed_metrics['profit_factor_bps']:.12f} neighborhood_every_year={improve_every_year}"
    )
    print("[M10D OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
