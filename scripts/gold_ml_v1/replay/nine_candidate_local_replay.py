from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_REGISTRY = 2
EXIT_METRICS = 3
EXIT_ENV = 4
POINT = 0.01
REQUIRED_RAW_COLUMNS = [
    "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"
]
TF_DELTA = {
    "M1": pd.Timedelta(minutes=1),
    "M15": pd.Timedelta(minutes=15),
    "H1": pd.Timedelta(hours=1),
    "H4": pd.Timedelta(hours=4),
    "D1": pd.Timedelta(days=1),
}
EXPECTED_CANDIDATES = [
    "GML1-PROV-007", "GML1-PROV-008", "GML1-WATCH-022-B",
    "GML1-PROV-010", "GML1-PROV-015", "GML1-PROV-020",
    "GML1-WATCH-021-A", "GML1-WATCH-021-B", "GML1-WATCH-021-C",
]


@dataclass(frozen=True)
class RepoPaths:
    repo_root: Path
    config: Path
    expected_metrics: Path
    expected_sha256: Path
    registries: Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv_auto(path: Path) -> pd.DataFrame:
    first = pd.read_csv(path)
    if len(first.columns) == 1 and ";" in str(first.columns[0]):
        return pd.read_csv(path, sep=";")
    return first


def json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def stable_sort_registry(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    sort_cols = [c for c in ["decision_close_time", "entry_time", "exit_time"] if c in out.columns]
    for col in sort_cols:
        out[col] = pd.to_datetime(out[col])
    if sort_cols:
        out = out.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    return out


def compute_metrics(df: pd.DataFrame) -> dict[str, Any]:
    ordered = stable_sort_registry(df)
    r = pd.to_numeric(ordered["r_value"], errors="raise").astype(float)
    positive = float(r[r > 0].sum())
    negative = float(-r[r < 0].sum())
    pf = positive / negative if negative > 0 else None
    equity = r.cumsum().to_numpy(dtype=float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity
    return {
        "trades": int(len(ordered)),
        "wins": int((r > 0).sum()),
        "nonwins": int((r <= 0).sum()),
        "win_rate": float((r > 0).mean()) if len(r) else None,
        "gross_positive_r": positive,
        "gross_negative_r": negative,
        "profit_factor": pf,
        "total_r": float(r.sum()),
        "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "first_decision_close_time": str(ordered["decision_close_time"].iloc[0]) if len(ordered) else None,
        "last_decision_close_time": str(ordered["decision_close_time"].iloc[-1]) if len(ordered) else None,
    }


def close_enough(a: Any, b: Any, tolerance: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tolerance * max(1.0, abs(float(a)), abs(float(b)))
    return a == b


def resolve_repo_paths(repo_root: Path) -> RepoPaths:
    root = repo_root.resolve()
    config = root / "config/gold_ml_v1/replay/nine_candidate_replay_config_20260625.json"
    metrics = root / "config/gold_ml_v1/replay/nine_candidate_expected_metrics_20260625.json"
    hashes = root / "config/gold_ml_v1/replay/nine_candidate_expected_sha256_20260625.json"
    missing = [p for p in [config, metrics, hashes] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing repository replay files: {missing}")
    return RepoPaths(root, config, metrics, hashes, root / "config/gold_ml_v1/registries")


def registry_path(paths: RepoPaths, filename: str) -> Path:
    path = paths.registries / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing exact registry: {path}. Install the verified exact artifacts first."
        )
    return path


def registry_only(paths: RepoPaths, output_dir: Path) -> int:
    expected_hashes = json.loads(paths.expected_sha256.read_text(encoding="utf-8"))
    expected_metrics = json.loads(paths.expected_metrics.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    exit_code = EXIT_OK
    for candidate_id, item in expected_hashes["expected_registries"].items():
        path = registry_path(paths, item["filename"])
        actual_hash = sha256_file(path)
        df = read_csv_auto(path)
        actual_metrics = compute_metrics(df)
        hash_ok = actual_hash == item["sha256"]
        rows_ok = len(df) == item["rows"]
        metrics_ok = all(
            close_enough(actual_metrics[key], expected_metrics[candidate_id][key])
            for key in expected_metrics[candidate_id]
        )
        rows.append({
            "candidate_id": candidate_id,
            "rows": len(df),
            "sha256_ok": hash_ok,
            "rows_ok": rows_ok,
            "metrics_ok": metrics_ok,
            "profit_factor": actual_metrics["profit_factor"],
            "total_r": actual_metrics["total_r"],
            "max_drawdown_r": actual_metrics["max_drawdown_r"],
        })
        if not hash_ok or not rows_ok:
            exit_code = max(exit_code, EXIT_REGISTRY)
        if not metrics_ok:
            exit_code = max(exit_code, EXIT_METRICS)
    try:
        _append_derivative_checks(paths, rows)
        if any(row.get("rows_ok") is False for row in rows):
            exit_code = max(exit_code, EXIT_REGISTRY)
    except Exception as exc:
        rows.append({
            "candidate_id": "DERIVATION_AUDIT_ERROR",
            "rows": 0,
            "sha256_ok": False,
            "rows_ok": False,
            "metrics_ok": False,
            "error": repr(exc),
        })
        exit_code = max(exit_code, EXIT_ENV)
    report = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_dir / "registry_parity_report.csv", index=False)
    json_dump(output_dir / "registry_parity_summary.json", {
        "status": "PASS" if exit_code == EXIT_OK else "FAIL",
        "exit_code": exit_code,
        "rows": rows,
    })
    print(report.to_string(index=False))
    print("REGISTRY PARITY", "PASS" if exit_code == EXIT_OK else "FAIL")
    return exit_code


def _append_derivative_checks(paths: RepoPaths, rows: list[dict[str, Any]]) -> None:
    p15 = read_csv_auto(registry_path(paths, "GML1-PROV-015_exact_trade_registry.csv"))
    p20 = read_csv_auto(registry_path(paths, "GML1-PROV-020_exact_trade_registry.csv"))
    events = read_csv_auto(registry_path(paths, "GML1-PROV-015_parent_event_registry_all_available.csv"))
    for frame in (p15, p20, events):
        frame["decision_close_time"] = pd.to_datetime(frame["decision_close_time"])
    joined = p15.merge(
        events[["decision_close_time", "h1_decision_close_server_hour", "h1_spread_price_div_atr14"]],
        on="decision_close_time", how="left", validate="one_to_one",
    )
    if joined[["h1_decision_close_server_hour", "h1_spread_price_div_atr14"]].isna().any().any():
        raise ValueError("PROV-020 support event join contains missing values")
    keep = ~(
        joined["h1_decision_close_server_hour"].between(8, 16)
        & (joined["h1_spread_price_div_atr14"] >= 0.0308778597897866)
    )
    _append_set_check(rows, "GML1-PROV-020_DERIVATION", joined.loc[keep], p20)

    features = read_csv_auto(registry_path(paths, "GML1-WATCH-014-A_54_feature_registry.csv"))
    features["decision_close_time"] = pd.to_datetime(features["bar_close_time"])
    base = p15.merge(features, on="decision_close_time", how="left", suffixes=("", "_feature"), validate="one_to_one")
    required = ["range_atr_lag1", "span_atr_12", "close_pos_lag5", "range_atr_lag10"]
    if base[required].isna().any().any():
        raise ValueError("WATCH-021 feature join contains missing values")
    keep_a = ~(
        (base["range_atr_lag1"] <= 0.6571970935503249)
        & (base["span_atr_12"] >= 5.058013327710588)
    )
    keep_b = ~(
        (base["close_pos_lag5"] <= 0.424089068826)
        & (base["range_atr_lag10"] >= 1.17215632583)
    )
    for candidate_id, mask in {
        "GML1-WATCH-021-A": keep_a,
        "GML1-WATCH-021-B": keep_b,
        "GML1-WATCH-021-C": keep_a & keep_b,
    }.items():
        expected = read_csv_auto(registry_path(paths, f"{candidate_id}_exact_trade_registry.csv"))
        expected["decision_close_time"] = pd.to_datetime(expected["decision_close_time"])
        _append_set_check(rows, f"{candidate_id}_DERIVATION", base.loc[mask], expected)

    p7 = read_csv_auto(registry_path(paths, "GML1-PROV-007_exact_trade_registry.csv"))
    w22 = read_csv_auto(registry_path(paths, "GML1-WATCH-022-B_exact_trade_registry.csv"))
    for frame in (p7, w22):
        frame["decision_close_time"] = pd.to_datetime(frame["decision_close_time"])
    keep_22 = ~(
        (pd.to_numeric(p7["upper_wick_frac"]) <= 0.06526044468913629)
        & (pd.to_numeric(p7["ema40_slope6_atr"]) >= 0.8700779249713114)
    )
    _append_set_check(rows, "GML1-WATCH-022-B_DERIVATION", p7.loc[keep_22], w22)


def _append_set_check(rows: list[dict[str, Any]], name: str, derived: pd.DataFrame, expected: pd.DataFrame) -> None:
    derived_set = set(pd.to_datetime(derived["decision_close_time"]))
    expected_set = set(pd.to_datetime(expected["decision_close_time"]))
    ok = derived_set == expected_set
    rows.append({
        "candidate_id": name,
        "rows": len(derived_set),
        "sha256_ok": None,
        "rows_ok": ok,
        "metrics_ok": ok,
        "profit_factor": None,
        "total_r": None,
        "max_drawdown_r": None,
    })


def locate_case_insensitive(root: Path, filename: str) -> Path | None:
    direct = root / filename
    if direct.exists():
        return direct
    target = filename.lower()
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == target:
            return path
    return None


def load_raw_bars(historical: Path, live: Path | None, timeframe: str) -> pd.DataFrame:
    historical_df = read_csv_auto(historical)
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in historical_df.columns]
    if missing:
        raise ValueError(f"{historical}: missing columns {missing}")
    df = historical_df[REQUIRED_RAW_COLUMNS].copy()
    df["time"] = pd.to_datetime(df["time"])
    df["source"] = "historical"
    if live is not None and live.exists():
        live_df = read_csv_auto(live)
        missing = [c for c in REQUIRED_RAW_COLUMNS if c not in live_df.columns]
        if missing:
            raise ValueError(f"{live}: missing columns {missing}")
        live_df = live_df[REQUIRED_RAW_COLUMNS].copy()
        live_df["time"] = pd.to_datetime(live_df["time"])
        live_df = live_df[live_df["time"] > df["time"].max()].copy()
        live_df["source"] = "live"
        df = pd.concat([df, live_df], ignore_index=True)
    df = df.sort_values("time", kind="mergesort").reset_index(drop=True)
    if df["time"].duplicated().any():
        raise ValueError(f"{timeframe}: duplicate bar-open times")
    if not df["time"].is_monotonic_increasing:
        raise ValueError(f"{timeframe}: out-of-order bars")
    invalid = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    if invalid.any():
        raise ValueError(f"{timeframe}: invalid OHLC rows={int(invalid.sum())}")
    df["bar_open_time"] = df["time"]
    df["bar_close_time"] = df["time"] + TF_DELTA[timeframe]
    return df


def atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = df["close"].shift(1)
    true_range = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - previous_close).abs(),
        (df["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    if len(true_range) >= period:
        out.iloc[period - 1] = true_range.iloc[:period].mean()
        for i in range(period, len(true_range)):
            out.iloc[i] = (out.iloc[i - 1] * (period - 1) + true_range.iloc[i]) / period
    return out


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rci(series: pd.Series, period: int = 18) -> pd.Series:
    def calculate(values: np.ndarray) -> float:
        price_rank = pd.Series(values).rank(method="average").to_numpy(dtype=float)
        time_rank = np.arange(1, len(values) + 1, dtype=float)
        diff = time_rank - price_rank
        return float((1 - 6 * np.sum(diff * diff) / (len(values) * (len(values) ** 2 - 1))) * 100)
    return series.rolling(period, min_periods=period).apply(calculate, raw=True)


def percentile_rank_last(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    return float(np.mean(values <= values[-1]))


def prepare_features(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()
    out["atr14"] = atr_wilder(out, 14)
    out["ema40"] = ema(out["close"], 40)
    if timeframe in {"M15", "H1"}:
        for period in (20, 60):
            mean = out["close"].rolling(period, min_periods=period).mean()
            sd = out["close"].rolling(period, min_periods=period).std(ddof=0)
            out[f"bb{period}_mid"] = mean
            out[f"bb{period}_upper"] = mean + 2 * sd
            out[f"bb{period}_lower"] = mean - 2 * sd
            out[f"bb{period}_width_atr"] = 4 * sd / out["atr14"]
    if timeframe == "M15":
        out["bb60_width_pct100"] = out["bb60_width_atr"].rolling(100, min_periods=100).apply(
            percentile_rank_last, raw=True
        )
    if timeframe in {"H4", "D1"}:
        out["rci18"] = rci(out["close"], 18)
    if timeframe == "H4":
        candle_range = (out["high"] - out["low"]).replace(0, np.nan)
        out["upper_wick_frac"] = (out["high"] - out[["open", "close"]].max(axis=1)) / candle_range
        out["ema40_slope6_atr"] = (out["ema40"] - out["ema40"].shift(6)) / out["atr14"]
        out["spread_atr"] = out["spread"] * POINT / out["atr14"]
    if timeframe == "D1":
        out["tickvol_ratio50"] = out["tick_volume"] / out["tick_volume"].rolling(50, min_periods=50).mean()
        out["delta_atr_3"] = (out["close"] - out["close"].shift(3)) / out["atr14"]
    if timeframe == "H1":
        out["spread_atr"] = out["spread"] * POINT / out["atr14"]
    return out


def evaluate_trade(
    m1: pd.DataFrame,
    decision_close_time: pd.Timestamp,
    atr_at_decision: float,
    direction: str,
    horizon_hours: int,
) -> dict[str, Any] | None:
    entry_rows = m1.index[m1["bar_open_time"] == decision_close_time]
    if len(entry_rows) != 1 or not np.isfinite(atr_at_decision):
        return None
    entry_bar = m1.loc[int(entry_rows[0])]
    spread_price = float(entry_bar["spread"] * POINT)
    entry_price = float(entry_bar["open"] + (spread_price if direction == "LONG" else 0.0))
    stop_distance = float(atr_at_decision)
    sl_price = entry_price - stop_distance if direction == "LONG" else entry_price + stop_distance
    tp_price = entry_price + stop_distance if direction == "LONG" else entry_price - stop_distance
    horizon_end = decision_close_time + pd.Timedelta(hours=horizon_hours)
    path = m1[(m1["bar_open_time"] >= decision_close_time) & (m1["bar_open_time"] < horizon_end)]
    if path.empty:
        return None
    for _, bar in path.iterrows():
        if direction == "LONG":
            sl_hit = bar["low"] <= sl_price
            tp_hit = bar["high"] >= tp_price
        else:
            ask_low = bar["low"] + bar["spread"] * POINT
            ask_high = bar["high"] + bar["spread"] * POINT
            sl_hit = ask_high >= sl_price
            tp_hit = ask_low <= tp_price
        if sl_hit:
            return {
                "entry_time": decision_close_time,
                "entry_price": entry_price,
                "exit_time": bar["bar_open_time"],
                "exit_price": float(sl_price),
                "r_value": -1.0,
                "outcome": "SL",
            }
        if tp_hit:
            return {
                "entry_time": decision_close_time,
                "entry_price": entry_price,
                "exit_time": bar["bar_open_time"],
                "exit_price": float(tp_price),
                "r_value": 1.0,
                "outcome": "TP",
            }
    final_open = horizon_end - pd.Timedelta(minutes=1)
    final_rows = m1[m1["bar_open_time"] == final_open]
    if len(final_rows) != 1:
        return None
    final_bar = final_rows.iloc[0]
    exit_price = float(
        final_bar["close"] if direction == "LONG" else final_bar["close"] + final_bar["spread"] * POINT
    )
    r_value = (
        (exit_price - entry_price) / stop_distance
        if direction == "LONG"
        else (entry_price - exit_price) / stop_distance
    )
    return {
        "entry_time": decision_close_time,
        "entry_price": entry_price,
        "exit_time": horizon_end,
        "exit_price": exit_price,
        "r_value": float(r_value),
        "outcome": "TIME_POS" if r_value > 0 else ("TIME_NEG" if r_value < 0 else "TIME_ZERO"),
    }


def compare_candidate(
    candidate_id: str,
    got: pd.DataFrame,
    expected_path: Path,
    diff_dir: Path,
    tolerance: float = 1e-8,
) -> dict[str, Any]:
    expected_full = stable_sort_registry(read_csv_auto(expected_path))
    actual_full = stable_sort_registry(got)
    keys = ["decision_close_time", "entry_time", "exit_time"]
    comparable = [
        c for c in ["candidate_id", *keys, "direction", "outcome", "r_value", "entry_price", "exit_price"]
        if c in expected_full.columns and c in actual_full.columns
    ]
    expected = expected_full[comparable]
    actual = actual_full[comparable]
    merged = expected.merge(actual, on=keys, how="outer", suffixes=("_expected", "_actual"), indicator=True)
    missing_or_extra = merged[merged["_merge"] != "both"].copy()
    both = merged[merged["_merge"] == "both"].copy()
    value_diff_mask = pd.Series(False, index=both.index)
    diff_columns: list[str] = []
    for column in ["r_value", "entry_price", "exit_price"]:
        expected_col, actual_col = f"{column}_expected", f"{column}_actual"
        if expected_col in both.columns and actual_col in both.columns:
            diff = (pd.to_numeric(both[expected_col]) - pd.to_numeric(both[actual_col])).abs() > tolerance
            value_diff_mask |= diff
            if diff.any():
                diff_columns.append(column)
    for column in ["direction", "outcome", "candidate_id"]:
        expected_col, actual_col = f"{column}_expected", f"{column}_actual"
        if expected_col in both.columns and actual_col in both.columns:
            diff = both[expected_col].astype(str) != both[actual_col].astype(str)
            value_diff_mask |= diff
            if diff.any():
                diff_columns.append(column)
    value_diffs = both[value_diff_mask].copy()
    diff_dir.mkdir(parents=True, exist_ok=True)
    missing_or_extra.to_csv(diff_dir / f"{candidate_id}_missing_extra.csv", index=False)
    value_diffs.to_csv(diff_dir / f"{candidate_id}_value_diff.csv", index=False)
    expected_metrics = compute_metrics(expected_full)
    actual_metrics = compute_metrics(actual_full)
    metric_keys = ["trades", "wins", "win_rate", "profit_factor", "total_r", "max_drawdown_r"]
    metrics_match = all(close_enough(expected_metrics[k], actual_metrics[k], tolerance) for k in metric_keys)
    passed = len(missing_or_extra) == 0 and len(value_diffs) == 0 and metrics_match
    return {
        "candidate_id": candidate_id,
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "missing_or_extra": len(missing_or_extra),
        "value_diff_rows": len(value_diffs),
        "value_diff_columns": ",".join(diff_columns),
        "metrics_match": metrics_match,
        "pass": passed,
    }


def write_input_manifest(files: dict[str, tuple[Path, Path | None]], output_dir: Path) -> None:
    manifest: dict[str, Any] = {}
    for timeframe, (historical, live) in files.items():
        historical_df = read_csv_auto(historical)
        item: dict[str, Any] = {
            "historical_path": str(historical),
            "historical_sha256": sha256_file(historical),
            "historical_rows": int(len(historical_df)),
            "historical_first_time": str(historical_df["time"].iloc[0]) if len(historical_df) else None,
            "historical_last_time": str(historical_df["time"].iloc[-1]) if len(historical_df) else None,
        }
        if live is not None:
            live_df = read_csv_auto(live)
            item.update({
                "live_path": str(live),
                "live_sha256": sha256_file(live),
                "live_rows": int(len(live_df)),
                "live_first_time": str(live_df["time"].iloc[0]) if len(live_df) else None,
                "live_last_time": str(live_df["time"].iloc[-1]) if len(live_df) else None,
            })
        manifest[timeframe] = item
    json_dump(output_dir / "raw_input_manifest.json", manifest)


def raw_replay(paths: RepoPaths, raw_dir: Path, output_dir: Path) -> int:
    config = json.loads(paths.config.read_text(encoding="utf-8"))
    raw_files: dict[str, tuple[Path, Path | None]] = {}
    missing: list[str] = []
    for timeframe, names in config["raw_files"].items():
        historical = locate_case_insensitive(raw_dir, names["historical"])
        live = locate_case_insensitive(raw_dir, names["live"])
        if historical is None:
            missing.append(names["historical"])
        else:
            raw_files[timeframe] = (historical, live)
    if missing:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_dump(output_dir / "missing_raw_inputs.json", {
            "missing": missing,
            "searched_root": str(raw_dir.resolve()),
            "required_timeframes": list(config["raw_files"]),
        })
        print("MISSING RAW INPUTS:")
        for name in missing:
            print(f"- {name}")
        return EXIT_INPUT
    try:
        write_input_manifest(raw_files, output_dir)
        bars = {
            timeframe: prepare_features(load_raw_bars(hist, live, timeframe), timeframe)
            for timeframe, (hist, live) in raw_files.items()
        }
        generated = generate_candidates(bars)
        reports: list[dict[str, Any]] = []
        for candidate_id in EXPECTED_CANDIDATES:
            df = generated[candidate_id].copy()
            df["year"] = pd.to_datetime(df["decision_close_time"]).dt.year
            stable_sort_registry(df).to_csv(output_dir / f"{candidate_id}_local_trade_registry.csv", index=False)
            reports.append(compare_candidate(
                candidate_id,
                df,
                registry_path(paths, f"{candidate_id}_exact_trade_registry.csv"),
                output_dir / "diffs",
            ))
        report_df = pd.DataFrame(reports)
        report_df.to_csv(output_dir / "raw_replay_comparison.csv", index=False)
        passed = bool(report_df["pass"].all())
        json_dump(output_dir / "raw_replay_summary.json", {
            "status": "PASS" if passed else "FAIL",
            "reports": reports,
            "warning": "Frozen implementation. Mismatches are reported and never silently tuned.",
        })
        print(report_df.to_string(index=False))
        return EXIT_OK if passed else EXIT_REGISTRY
    except Exception:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "raw_replay_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        return EXIT_ENV


def generate_candidates(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    m1, m15, h1, h4, d1 = (bars[k] for k in ["M1", "M15", "H1", "H4", "D1"])
    h4_features = h4[[
        "bar_close_time", "rci18", "spread_atr", "upper_wick_frac", "ema40_slope6_atr"
    ]].dropna().sort_values("bar_close_time")
    m15_joined = pd.merge_asof(
        m15.sort_values("bar_close_time"), h4_features, on="bar_close_time",
        direction="backward", allow_exact_matches=True,
    )
    m15_joined["state"] = (
        (m15_joined["rci18"] >= 73.993808)
        & (m15_joined["spread_atr"] <= 0.012772)
    )
    m1_times = set(m1["bar_open_time"])
    m15_joined["eligible"] = (
        m15_joined["bar_close_time"].isin(m1_times)
        & (m15_joined["bar_close_time"] + pd.Timedelta(hours=6) - pd.Timedelta(minutes=1)).isin(m1_times)
    )
    eligible = m15_joined[m15_joined["eligible"]].copy()
    eligible["event"] = eligible["state"] & ~eligible["state"].shift(fill_value=False)
    base_trades = _evaluate_events(
        eligible[eligible["event"]], m1, "LONG", 6,
        ["upper_wick_frac", "ema40_slope6_atr", "bb20_width_atr", "bb60_width_pct100"],
    )
    if base_trades.empty:
        raise RuntimeError("No GML1-PROV-002 parent trades generated")
    p7 = base_trades[~(
        (base_trades["upper_wick_frac"] >= 0.27488556398168634)
        & (base_trades["ema40_slope6_atr"] >= 0.6863028800058267)
    )].copy()
    p7["candidate_id"] = "GML1-PROV-007"
    p8 = base_trades[~(
        (base_trades["bb20_width_atr"] <= 3.3719018700718184)
        & (base_trades["bb60_width_pct100"] <= 0.536)
    )].copy()
    p8["candidate_id"] = "GML1-PROV-008"
    w22 = p7[~(
        (p7["upper_wick_frac"] <= 0.06526044468913629)
        & (p7["ema40_slope6_atr"] >= 0.8700779249713114)
    )].copy()
    w22["candidate_id"] = "GML1-WATCH-022-B"

    d1_features = d1[["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]].dropna().sort_values("bar_close_time")
    h1_joined = pd.merge_asof(
        h1.sort_values("bar_close_time"), d1_features, on="bar_close_time",
        direction="backward", allow_exact_matches=True, suffixes=("", "_d1"),
    )
    h1_joined["event"] = (
        (h1_joined["close"].shift(1) <= h1_joined["bb60_upper"].shift(1))
        & (h1_joined["close"] > h1_joined["bb60_upper"])
        & (h1_joined["rci18"] >= 0)
    )
    h1_joined["decision_hour"] = h1_joined["bar_close_time"].dt.hour
    p10 = _evaluate_events(
        h1_joined[h1_joined["event"]], m1, "LONG", 48,
        ["tickvol_ratio50", "delta_atr_3", "decision_hour", "spread_atr"],
    ).rename(columns={
        "tickvol_ratio50": "htf_tickvol_ratio50",
        "delta_atr_3": "htf_delta_atr_3",
        "decision_hour": "ltf_hour",
        "spread_atr": "ltf_spread_atr",
    })
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
        left_on="decision_close_time", right_on="bar_close_time", how="left", validate="one_to_one",
    )
    keep_a = ~(
        (p15_path["range_atr_lag1"] <= 0.6571970935503249)
        & (p15_path["span_atr_12"] >= 5.058013327710588)
    )
    keep_b = ~(
        (p15_path["close_pos_lag5"] <= 0.424089068826)
        & (p15_path["range_atr_lag10"] >= 1.17215632583)
    )
    wa = p15_path.loc[keep_a].copy(); wa["candidate_id"] = "GML1-WATCH-021-A"
    wb = p15_path.loc[keep_b].copy(); wb["candidate_id"] = "GML1-WATCH-021-B"
    wc = p15_path.loc[keep_a & keep_b].copy(); wc["candidate_id"] = "GML1-WATCH-021-C"
    return {
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


def _evaluate_events(
    events: pd.DataFrame,
    m1: pd.DataFrame,
    direction: str,
    horizon_hours: int,
    extra_columns: list[str],
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min
    for _, event in events.iterrows():
        decision = event["bar_close_time"]
        if decision < open_until:
            continue
        trade = evaluate_trade(m1, decision, event["atr14"], direction, horizon_hours)
        if trade is None:
            continue
        trade.update({"decision_close_time": decision, "direction": direction})
        for column in extra_columns:
            trade[column] = event[column]
        trades.append(trade)
        open_until = pd.Timestamp(trade["exit_time"])
    return pd.DataFrame(trades)


def main() -> int:
    parser = argparse.ArgumentParser(description="GOLD_ML_V1 nine-candidate exact local replay")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--raw-dir", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=["registry-only", "raw", "auto"], default="auto")
    args = parser.parse_args()
    output_dir = args.output_dir or args.repo_root / "outputs/gold_ml_v1/batch023_local_replay"
    try:
        paths = resolve_repo_paths(args.repo_root)
        if args.mode == "registry-only":
            return registry_only(paths, output_dir)
        if args.mode == "raw":
            return raw_replay(paths, args.raw_dir, output_dir)
        registry_code = registry_only(paths, output_dir / "registry")
        if registry_code != EXIT_OK:
            return registry_code
        return raw_replay(paths, args.raw_dir, output_dir / "raw")
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
