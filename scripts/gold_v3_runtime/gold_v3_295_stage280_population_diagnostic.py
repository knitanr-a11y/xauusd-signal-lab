#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from gold_v3_289_feature_core import load_gold, m1_arrays
from gold_v3_289_stage280_features import build_stage280_context

EXPECTED_FIT = 4974
EXPECTED_CAL = 1809
FIT_START = pd.Timestamp("2024-01-01")
FIT_END = pd.Timestamp("2025-07-01")
CAL_END = pd.Timestamp("2026-01-01")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def counts(mask: pd.Series, fit: pd.Series, cal: pd.Series) -> dict[str, int]:
    return {
        "fit_n": int((mask & fit).sum()),
        "cal_n": int((mask & cal).sum()),
    }


def error(value: dict[str, int]) -> int:
    return abs(value["fit_n"] - EXPECTED_FIT) + abs(value["cal_n"] - EXPECTED_CAL)


def valid_future_window(ctx: pd.DataFrame, candle_dir: Path) -> pd.Series:
    raw = load_gold(candle_dir, tail_only=False)
    mt, *_ = m1_arrays(raw["M1"])
    result = []
    for value in pd.to_datetime(ctx.time):
        timestamp = np.datetime64(value)
        start = np.searchsorted(mt, timestamp, side="left")
        end = np.searchsorted(mt, timestamp + np.timedelta64(240, "m"), side="left")
        result.append(
            start < len(mt)
            and mt[start] == timestamp
            and end > start
            and end - start >= 180
        )
    return pd.Series(result, index=ctx.index, dtype=bool)


def overlap_hours(hours: pd.Series, blocked: set[int], horizon_hours: int) -> pd.Series:
    result = []
    for hour in hours.astype(int):
        occupied = {(hour + offset) % 24 for offset in range(horizon_hours + 1)}
        result.append(not bool(occupied & blocked))
    return pd.Series(result, index=hours.index, dtype=bool)


def exact_hour_exclusions(
    base: pd.Series,
    fit: pd.Series,
    cal: pd.Series,
    hours: pd.Series,
    max_removed_hours: int = 8,
) -> list[dict[str, object]]:
    fit_by_hour = {
        hour: int((base & fit & hours.eq(hour)).sum()) for hour in range(24)
    }
    cal_by_hour = {
        hour: int((base & cal & hours.eq(hour)).sum()) for hour in range(24)
    }
    base_counts = counts(base, fit, cal)
    need_fit = base_counts["fit_n"] - EXPECTED_FIT
    need_cal = base_counts["cal_n"] - EXPECTED_CAL
    matches: list[dict[str, object]] = []
    if need_fit < 0 or need_cal < 0:
        return matches
    for size in range(1, max_removed_hours + 1):
        for subset in itertools.combinations(range(24), size):
            removed_fit = sum(fit_by_hour[h] for h in subset)
            removed_cal = sum(cal_by_hour[h] for h in subset)
            if removed_fit == need_fit and removed_cal == need_cal:
                matches.append(
                    {
                        "excluded_server_hours": list(subset),
                        "fit_n": EXPECTED_FIT,
                        "cal_n": EXPECTED_CAL,
                    }
                )
                if len(matches) >= 25:
                    return matches
    return matches


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage295_stage280_population_diagnostic.json"
    )

    ctx = build_stage280_context(
        candle_dir, include_next=False, tail_only=False
    ).sort_values("time").reset_index(drop=True)
    time = pd.to_datetime(ctx.time)
    fit = time.ge(FIT_START) & time.lt(FIT_END)
    cal = time.ge(FIT_END) & time.lt(CAL_END)
    h4 = pd.to_numeric(ctx.h4_trend, errors="coerce").fillna(0).astype(int)
    d1 = pd.to_numeric(ctx.d1_trend, errors="coerce").fillna(0).astype(int)
    hour = time.dt.hour
    weekday = time.dt.dayofweek
    future_valid = valid_future_window(ctx, candle_dir)

    raw_feature_columns = [
        column
        for column in ctx.columns
        if column
        not in {"time", "atr_prev", "h4_trend", "d1_trend"}
    ]
    all_raw_finite = (
        ctx[raw_feature_columns]
        .replace([np.inf, -np.inf], np.nan)
        .notna()
        .all(axis=1)
    )
    atr_valid = pd.to_numeric(ctx.atr_prev, errors="coerce").gt(0)

    masks: dict[str, pd.Series] = {
        "h4_non_neutral": h4.ne(0),
        "h4_down_only": h4.eq(-1),
        "h4_up_only": h4.eq(1),
        "h4_non_neutral_and_future_valid": h4.ne(0) & future_valid,
        "h4_non_neutral_and_all_raw_finite": h4.ne(0) & all_raw_finite,
        "h4_non_neutral_and_atr_valid": h4.ne(0) & atr_valid,
        "h4_non_neutral_and_d1_non_neutral": h4.ne(0) & d1.ne(0),
        "h4_non_neutral_and_d1_aligned": h4.ne(0) & d1.eq(h4),
        "h4_non_neutral_and_d1_opposed": h4.ne(0) & d1.eq(-h4),
        "h4_non_neutral_exclude_hours_0_1": h4.ne(0) & ~hour.isin([0, 1]),
        "h4_non_neutral_exclude_hours_0_1_2": h4.ne(0) & ~hour.isin([0, 1, 2]),
        "h4_non_neutral_exclude_hours_22_23_0": h4.ne(0) & ~hour.isin([22, 23, 0]),
        "h4_non_neutral_no_4h_overlap_0_1": h4.ne(0)
        & overlap_hours(hour, {0, 1}, 4),
        "h4_non_neutral_no_6h_overlap_0_1": h4.ne(0)
        & overlap_hours(hour, {0, 1}, 6),
        "h4_non_neutral_weekdays_only": h4.ne(0) & weekday.lt(5),
    }

    structural = {
        "future_valid": future_valid,
        "all_raw_finite": all_raw_finite,
        "atr_valid": atr_valid,
        "d1_non_neutral": d1.ne(0),
        "d1_aligned": d1.eq(h4),
        "d1_not_opposed": ~d1.eq(-h4),
        "weekdays_only": weekday.lt(5),
    }
    base = h4.ne(0)
    structural_names = list(structural)
    combination_rows: list[dict[str, object]] = []
    for size in range(1, min(5, len(structural_names)) + 1):
        for names in itertools.combinations(structural_names, size):
            mask = base.copy()
            for name in names:
                mask &= structural[name]
            value = counts(mask, fit, cal)
            combination_rows.append(
                {
                    "filters": list(names),
                    **value,
                    "distance": error(value),
                }
            )

    mask_counts = {
        name: {**counts(mask, fit, cal), "distance": error(counts(mask, fit, cal))}
        for name, mask in masks.items()
    }
    exact_masks = [
        {"filter": name, **value}
        for name, value in mask_counts.items()
        if value["fit_n"] == EXPECTED_FIT and value["cal_n"] == EXPECTED_CAL
    ]
    exact_combinations = [
        row
        for row in combination_rows
        if row["fit_n"] == EXPECTED_FIT and row["cal_n"] == EXPECTED_CAL
    ]
    nearest = sorted(
        [
            {"filter": name, **value}
            for name, value in mask_counts.items()
        ]
        + combination_rows,
        key=lambda row: (row["distance"], str(row)),
    )[:25]

    hour_counts = []
    for value in range(24):
        mask = base & hour.eq(value)
        hour_counts.append({"server_hour": value, **counts(mask, fit, cal)})
    weekday_counts = []
    for value in range(7):
        mask = base & weekday.eq(value)
        weekday_counts.append({"weekday": value, **counts(mask, fit, cal)})

    report = {
        "status": "GOLD_V3_295_STAGE280_POPULATION_DIAGNOSTIC_READY",
        "expected": {"fit_n": EXPECTED_FIT, "cal_n": EXPECTED_CAL},
        "current_h4_non_neutral": counts(base, fit, cal),
        "mask_counts": mask_counts,
        "exact_named_masks": exact_masks,
        "exact_structural_combinations": exact_combinations,
        "exact_hour_exclusions_from_h4_non_neutral": exact_hour_exclusions(
            base, fit, cal, hour
        ),
        "nearest_conditions": nearest,
        "counts_by_server_hour": hour_counts,
        "counts_by_weekday": weekday_counts,
        "notes": [
            "This diagnostic does not change thresholds or create model artifacts.",
            "An exact count match is necessary but not sufficient; threshold and fixture parity must still pass.",
            "All timestamps are treated as MT5 server time.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
