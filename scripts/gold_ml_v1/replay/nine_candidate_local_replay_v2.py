from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_PATH = Path(__file__).with_name("nine_candidate_local_replay.py")
SPEC = importlib.util.spec_from_file_location("gml1_batch023_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load base replay module: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)

EXIT_OK = base.EXIT_OK
EXIT_INPUT = base.EXIT_INPUT
EXIT_REGISTRY = base.EXIT_REGISTRY
EXIT_METRICS = base.EXIT_METRICS
EXIT_ENV = base.EXIT_ENV
POINT = base.POINT
EXPECTED_CANDIDATES = base.EXPECTED_CANDIDATES

EXPECTED_PROV002 = {
    "trades": 193,
    "wins": 111,
    "profit_factor": 1.3372021510,
    "total_r": 27.3654253218,
    "max_drawdown_r": 6.9816100582,
}


def atr_simple_rolling(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Exact research ATR: arithmetic mean of the latest period true ranges."""
    previous_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(period, min_periods=period).mean()


# The original Batch023 base module called this global from prepare_features.
base.atr_wilder = atr_simple_rolling


def _read_raw(path: Path) -> pd.DataFrame:
    frame = base.read_csv_auto(path)
    missing = [c for c in base.REQUIRED_RAW_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    frame = frame[base.REQUIRED_RAW_COLUMNS].copy()
    frame["time"] = pd.to_datetime(frame["time"])
    return frame


def _validate_raw(frame: pd.DataFrame, label: str) -> None:
    if frame["time"].duplicated().any():
        raise ValueError(f"{label}: duplicate timestamps")
    if not frame["time"].is_monotonic_increasing:
        raise ValueError(f"{label}: timestamps are not ascending")
    invalid = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    )
    if invalid.any():
        raise ValueError(f"{label}: invalid OHLC rows={int(invalid.sum())}")


def load_historical_with_live_prehistory(
    historical_path: Path,
    live_path: Path | None,
    timeframe: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Reproduce the frozen research dataset.

    Historical rows are the only decision/evaluation window. Goldsharp may supply rows
    strictly before the historical first timestamp as indicator warmup. Every overlap
    row must match exactly. Goldsharp rows after the historical maximum are excluded
    from the historical replay.
    """
    historical = _read_raw(historical_path).sort_values("time", kind="mergesort").reset_index(drop=True)
    _validate_raw(historical, f"{timeframe} historical")
    historical_min = historical["time"].min()
    historical_max = historical["time"].max()
    historical["source"] = "historical"

    warmup = historical.iloc[0:0].copy()
    overlap_rows = 0
    live_rows = 0
    live_first = None
    live_last = None
    if live_path is not None and live_path.exists():
        live = _read_raw(live_path).sort_values("time", kind="mergesort").reset_index(drop=True)
        _validate_raw(live, f"{timeframe} goldsharp")
        live_rows = int(len(live))
        live_first = str(live["time"].min()) if len(live) else None
        live_last = str(live["time"].max()) if len(live) else None

        overlap = historical.merge(live, on="time", suffixes=("_historical", "_live"), how="inner")
        overlap_rows = int(len(overlap))
        for column in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
            left = overlap[f"{column}_historical"]
            right = overlap[f"{column}_live"]
            if pd.api.types.is_numeric_dtype(left):
                mismatch = ~np.isclose(left.astype(float), right.astype(float), rtol=0.0, atol=1e-12, equal_nan=True)
            else:
                mismatch = left.astype(str) != right.astype(str)
            if mismatch.any():
                raise ValueError(
                    f"{timeframe}: historical/goldsharp overlap mismatch in {column}, rows={int(mismatch.sum())}"
                )

        warmup = live[live["time"] < historical_min].copy()
        warmup["source"] = "goldsharp_warmup"

    combined = pd.concat([warmup, historical], ignore_index=True)
    combined = combined.sort_values("time", kind="mergesort").reset_index(drop=True)
    if combined["time"].duplicated().any():
        raise ValueError(f"{timeframe}: duplicate timestamp after warmup merge")
    combined["bar_open_time"] = combined["time"]
    combined["bar_close_time"] = combined["time"] + base.TF_DELTA[timeframe]

    audit = {
        "timeframe": timeframe,
        "historical_path": str(historical_path),
        "historical_sha256": base.sha256_file(historical_path),
        "historical_rows": int(len(historical)),
        "historical_first_open": str(historical_min),
        "historical_last_open": str(historical_max),
        "goldsharp_path": str(live_path) if live_path is not None else None,
        "goldsharp_rows": live_rows,
        "goldsharp_first_open": live_first,
        "goldsharp_last_open": live_last,
        "overlap_rows_verified": overlap_rows,
        "goldsharp_prehistory_rows_used_for_warmup": int(len(warmup)),
        "goldsharp_post_historical_rows_used": 0,
        "decision_source": "historical only",
    }
    return combined, audit


def _complete_horizon_mask(
    decision_times: pd.Series,
    m1_times: set[pd.Timestamp],
    horizon_hours: int,
) -> pd.Series:
    final_times = decision_times + pd.Timedelta(hours=horizon_hours) - pd.Timedelta(minutes=1)
    return decision_times.isin(m1_times) & final_times.isin(m1_times)


def _evaluate_events(
    events: pd.DataFrame,
    m1: pd.DataFrame,
    horizon_hours: int,
    extra_columns: list[str],
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min
    for _, event in events.iterrows():
        decision = pd.Timestamp(event["bar_close_time"])
        if decision < open_until:
            continue
        trade = base.evaluate_trade(m1, decision, float(event["atr14"]), "LONG", horizon_hours)
        if trade is None:
            continue
        trade.update({"decision_close_time": decision, "direction": "LONG"})
        for column in extra_columns:
            trade[column] = event[column]
        trades.append(trade)
        open_until = pd.Timestamp(trade["exit_time"])
    return pd.DataFrame(trades)


def generate_candidates_v2(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    m1, m15, h1, h4, d1 = (bars[key] for key in ["M1", "M15", "H1", "H4", "D1"])
    m1_historical = m1[m1["source"] == "historical"].copy()
    m1_times = set(pd.to_datetime(m1_historical["bar_open_time"]))

    # M15-H4: exact-entry and complete-horizon eligibility are applied BEFORE onset.
    h4_features = h4[
        ["bar_close_time", "rci18", "spread_atr", "upper_wick_frac", "ema40_slope6_atr"]
    ].dropna(subset=["rci18", "spread_atr"]).sort_values("bar_close_time")
    m15_joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4_features,
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    m15_joined["condition"] = (
        (m15_joined["rci18"] >= 73.993808)
        & (m15_joined["spread_atr"] <= 0.012772)
    )
    m15_joined["eligible"] = (
        (m15_joined["source"] == "historical")
        & _complete_horizon_mask(m15_joined["bar_close_time"], m1_times, 6)
    )
    eligible_m15 = m15_joined[m15_joined["eligible"]].copy()
    eligible_m15["event"] = eligible_m15["condition"] & ~eligible_m15["condition"].shift(fill_value=False)
    parent002 = _evaluate_events(
        eligible_m15[eligible_m15["event"]],
        m1_historical,
        6,
        ["upper_wick_frac", "ema40_slope6_atr", "bb20_width_atr", "bb60_width_pct100"],
    )
    if parent002.empty:
        raise RuntimeError("No GML1-PROV-002 parent trades generated")
    parent002["candidate_id"] = "GML1-PROV-002-DIAGNOSTIC"

    p7 = parent002[~(
        (parent002["upper_wick_frac"] >= 0.27488556398168634)
        & (parent002["ema40_slope6_atr"] >= 0.6863028800058267)
    )].copy()
    p7["candidate_id"] = "GML1-PROV-007"

    p8 = parent002[~(
        (parent002["bb20_width_atr"] <= 3.3719018700718184)
        & (parent002["bb60_width_pct100"] <= 0.536)
    )].copy()
    p8["candidate_id"] = "GML1-PROV-008"

    w22 = p7[~(
        (p7["upper_wick_frac"] <= 0.06526044468913629)
        & (p7["ema40_slope6_atr"] >= 0.8700779249713114)
    )].copy()
    w22["candidate_id"] = "GML1-WATCH-022-B"

    # H1-D1: eligibility is applied BEFORE the H1 breakout event comparison.
    d1_features = d1[
        ["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]
    ].dropna(subset=["rci18"]).sort_values("bar_close_time")
    h1_joined = pd.merge_asof(
        h1.sort_values("bar_close_time"),
        d1_features,
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
        suffixes=("", "_d1"),
    )
    h1_joined["eligible"] = (
        (h1_joined["source"] == "historical")
        & _complete_horizon_mask(h1_joined["bar_close_time"], m1_times, 48)
        & h1_joined["bb60_upper"].notna()
        & h1_joined["rci18"].notna()
    )
    eligible_h1 = h1_joined[h1_joined["eligible"]].copy()
    eligible_h1["event"] = (
        (eligible_h1["close"].shift(1) <= eligible_h1["bb60_upper"].shift(1))
        & (eligible_h1["close"] > eligible_h1["bb60_upper"])
        & (eligible_h1["rci18"] >= 0)
    )
    eligible_h1["decision_hour"] = eligible_h1["bar_close_time"].dt.hour
    p10 = _evaluate_events(
        eligible_h1[eligible_h1["event"]],
        m1_historical,
        48,
        ["tickvol_ratio50", "delta_atr_3", "decision_hour", "spread_atr"],
    ).rename(
        columns={
            "tickvol_ratio50": "htf_tickvol_ratio50",
            "delta_atr_3": "htf_delta_atr_3",
            "decision_hour": "ltf_hour",
            "spread_atr": "ltf_spread_atr",
        }
    )
    p10["candidate_id"] = "GML1-PROV-010"

    p15 = p10[~(
        (p10["htf_tickvol_ratio50"] <= 0.876789995391398)
        & (p10["htf_delta_atr_3"] <= 0.2256991669382677)
    )].copy()
    p15["candidate_id"] = "GML1-PROV-015"

    p20 = p15[~(
        p15["ltf_hour"].between(8, 16)
        & (p15["ltf_spread_atr"] >= 0.0308778597897866)
    )].copy()
    p20["candidate_id"] = "GML1-PROV-020"

    path = h1[["bar_close_time", "open", "high", "low", "close", "atr14"]].copy()
    path["range_atr"] = (path["high"] - path["low"]) / path["atr14"]
    path["close_pos"] = (path["close"] - path["low"]) / (path["high"] - path["low"]).replace(0, np.nan)
    path["range_atr_lag1"] = path["range_atr"].shift(1)
    path["close_pos_lag5"] = path["close_pos"].shift(5)
    path["range_atr_lag10"] = path["range_atr"].shift(10)
    path["span_atr_12"] = (
        path["high"].rolling(12).max() - path["low"].rolling(12).min()
    ) / path["atr14"]
    p15_path = p15.merge(
        path[["bar_close_time", "range_atr_lag1", "span_atr_12", "close_pos_lag5", "range_atr_lag10"]],
        left_on="decision_close_time",
        right_on="bar_close_time",
        how="left",
        validate="one_to_one",
    )
    keep_a = ~(
        (p15_path["range_atr_lag1"] <= 0.6571970935503249)
        & (p15_path["span_atr_12"] >= 5.058013327710588)
    )
    keep_b = ~(
        (p15_path["close_pos_lag5"] <= 0.424089068826)
        & (p15_path["range_atr_lag10"] >= 1.17215632583)
    )
    wa = p15_path.loc[keep_a].copy()
    wa["candidate_id"] = "GML1-WATCH-021-A"
    wb = p15_path.loc[keep_b].copy()
    wb["candidate_id"] = "GML1-WATCH-021-B"
    wc = p15_path.loc[keep_a & keep_b].copy()
    wc["candidate_id"] = "GML1-WATCH-021-C"

    return {
        "GML1-PROV-002-DIAGNOSTIC": parent002,
        "GML1-PROV-007": p7,
        "GML1-PROV-008": p8,
        "GML1-WATCH-022-B": w22,
        "GML1-PROV-010": p10,
        "GML1-PROV-015": p15,
        "GML1-PROV-020": p20,
        "GML1-WATCH-021-A": wa,
        "GML1-WATCH-021-B": wb,
        "GML1-WATCH-021-C": wc,
    }


def _metric_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(base.close_enough(actual[key], value, 1e-8) for key, value in expected.items())


def historical_replay(
    paths: Any,
    historical_dir: Path,
    warmup_dir: Path,
    output_dir: Path,
) -> int:
    config = json.loads(paths.config.read_text(encoding="utf-8"))
    input_audit: dict[str, Any] = {}
    bars: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for timeframe, names in config["raw_files"].items():
        historical_path = base.locate_case_insensitive(historical_dir, names["historical"])
        live_path = base.locate_case_insensitive(warmup_dir, names["live"])
        if historical_path is None:
            missing.append(names["historical"])
            continue
        combined, audit = load_historical_with_live_prehistory(historical_path, live_path, timeframe)
        bars[timeframe] = base.prepare_features(combined, timeframe)
        input_audit[timeframe] = audit

    output_dir.mkdir(parents=True, exist_ok=True)
    if missing:
        base.json_dump(
            output_dir / "missing_raw_inputs.json",
            {"missing": missing, "historical_root": str(historical_dir), "warmup_root": str(warmup_dir)},
        )
        return EXIT_INPUT

    base.json_dump(output_dir / "historical_replay_input_audit.json", input_audit)
    generated = generate_candidates_v2(bars)

    parent002 = generated["GML1-PROV-002-DIAGNOSTIC"].copy()
    parent002["year"] = pd.to_datetime(parent002["decision_close_time"]).dt.year
    base.stable_sort_registry(parent002).to_csv(
        output_dir / "GML1-PROV-002_DIAGNOSTIC_local_trade_registry.csv", index=False
    )
    parent_metrics = base.compute_metrics(parent002)
    parent_ok = _metric_match(parent_metrics, EXPECTED_PROV002)

    reports: list[dict[str, Any]] = []
    for candidate_id in EXPECTED_CANDIDATES:
        frame = generated[candidate_id].copy()
        frame["year"] = pd.to_datetime(frame["decision_close_time"]).dt.year
        base.stable_sort_registry(frame).to_csv(
            output_dir / f"{candidate_id}_local_trade_registry.csv", index=False
        )
        reports.append(
            base.compare_candidate(
                candidate_id,
                frame,
                base.registry_path(paths, f"{candidate_id}_exact_trade_registry.csv"),
                output_dir / "diffs",
            )
        )

    report_frame = pd.DataFrame(reports)
    report_frame.to_csv(output_dir / "raw_replay_comparison.csv", index=False)
    all_candidates_ok = bool(report_frame["pass"].all())
    summary = {
        "status": "PASS" if all_candidates_ok and parent_ok else "FAIL",
        "implementation": {
            "atr14": "simple rolling arithmetic mean of 14 true ranges",
            "historical_decision_source": "gold_v3_2023_2026 only",
            "goldsharp_role": "pre-historical indicator warmup only",
            "goldsharp_post_historical_rows_used": 0,
            "event_order": "exact M1 entry and complete horizon eligibility before event/onset detection",
        },
        "GML1-PROV-002-diagnostic": {
            "metrics": parent_metrics,
            "expected": EXPECTED_PROV002,
            "metrics_match": parent_ok,
        },
        "reports": reports,
    }
    base.json_dump(output_dir / "raw_replay_summary.json", summary)
    print("GML1-PROV-002 diagnostic:", json.dumps(summary["GML1-PROV-002-diagnostic"], ensure_ascii=False))
    print(report_frame.to_string(index=False))
    return EXIT_OK if all_candidates_ok and parent_ok else EXIT_REGISTRY


def main() -> int:
    parser = argparse.ArgumentParser(description="GOLD_ML_V1 Batch023 corrected historical replay")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--historical-dir", type=Path)
    parser.add_argument("--warmup-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=["registry-only", "raw", "auto"], default="auto")
    args = parser.parse_args()
    output_dir = args.output_dir or args.repo_root / "outputs/gold_ml_v1/batch023_historical_replay_v2"
    try:
        paths = base.resolve_repo_paths(args.repo_root)
        if args.mode == "registry-only":
            return base.registry_only(paths, output_dir)
        if args.historical_dir is None or args.warmup_dir is None:
            raise ValueError("--historical-dir and --warmup-dir are required for raw/auto mode")
        if args.mode == "auto":
            registry_code = base.registry_only(paths, output_dir / "registry")
            if registry_code != EXIT_OK:
                return registry_code
            return historical_replay(paths, args.historical_dir.resolve(), args.warmup_dir.resolve(), output_dir / "raw")
        return historical_replay(paths, args.historical_dir.resolve(), args.warmup_dir.resolve(), output_dir)
    except (FileNotFoundError, ValueError) as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "input_error.txt").write_text(str(exc), encoding="utf-8")
        print(exc, file=sys.stderr)
        return EXIT_INPUT
    except Exception:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "unexpected_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        return EXIT_ENV


if __name__ == "__main__":
    sys.exit(main())
