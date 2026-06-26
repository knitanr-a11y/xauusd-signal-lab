from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

POINT = 0.01
REQUIRED_COLUMNS = [
    "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"
]
TF_DELTAS = {
    "m15": pd.Timedelta(minutes=15),
    "h1": pd.Timedelta(hours=1),
    "h4": pd.Timedelta(hours=4),
    "d1": pd.Timedelta(days=1),
}
DEFAULT_FILES = {
    "m1": "gold_v3_2023_2026_m1.csv",
    "m15": "gold_v3_2023_2026_m15.csv",
    "h1": "gold_v3_2023_2026_h1.csv",
    "h4": "gold_v3_2023_2026_h4.csv",
    "d1": "gold_v3_2023_2026_d1.csv",
}
EXPECTED_HASHES = {
    "m1": "dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2",
    "m15": "e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28",
    "h1": "fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a",
    "h4": "5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913",
    "d1": "58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6",
}

TF_PROFILES: dict[str, dict[str, Any]] = {
    "m15": {
        "return_lookbacks": [1, 2, 4, 8, 16, 32],
        "ema_periods": [20, 50, 200],
        "slow_slope_lookback": 12,
        "extrema_windows": [20, 50, 100],
        "percentile_window": 256,
    },
    "h1": {
        "return_lookbacks": [1, 3, 6, 12, 24],
        "ema_periods": [20, 50, 200],
        "slow_slope_lookback": 12,
        "extrema_windows": [20, 50],
        "percentile_window": 168,
    },
    "h4": {
        "return_lookbacks": [1, 3, 6, 12, 24],
        "ema_periods": [20, 50, 100],
        "slow_slope_lookback": 8,
        "extrema_windows": [20, 50],
        "percentile_window": 126,
    },
    "d1": {
        "return_lookbacks": [1, 3, 5, 10, 20],
        "ema_periods": [10, 20, 50],
        "slow_slope_lookback": 5,
        "extrema_windows": [10, 20, 50],
        "percentile_window": 60,
    },
}


@dataclass(frozen=True)
class BuildResult:
    features: pd.DataFrame
    model_feature_columns: list[str]
    metadata_columns: list[str]
    rejection_summary: dict[str, Any]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def read_raw_csv(path: Path, *, columns: Iterable[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=list(columns) if columns is not None else None)
    expected = set(columns) if columns is not None else set(REQUIRED_COLUMNS)
    if not expected.issubset(df.columns):
        missing = sorted(expected.difference(df.columns))
        raise ValueError(f"{path}: missing required columns {missing}")
    df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M:%S", errors="raise")
    if df["time"].duplicated().any():
        raise ValueError(f"{path}: duplicate timestamps")
    if not df["time"].is_monotonic_increasing:
        raise ValueError(f"{path}: timestamps are not increasing")
    return df


def wilder_rma(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    out = np.full(len(values), np.nan, dtype=float)
    if len(values) < period:
        return pd.Series(out, index=series.index, dtype=float)

    start: int | None = None
    for idx in range(period - 1, len(values)):
        window = values[idx - period + 1 : idx + 1]
        if np.isfinite(window).all():
            start = idx
            out[idx] = float(window.mean())
            break
    if start is None:
        return pd.Series(out, index=series.index, dtype=float)

    previous = out[start]
    for idx in range(start + 1, len(values)):
        current = values[idx]
        if not np.isfinite(current):
            previous = np.nan
            continue
        if not np.isfinite(previous):
            if idx >= period - 1:
                window = values[idx - period + 1 : idx + 1]
                if np.isfinite(window).all():
                    previous = float(window.mean())
                    out[idx] = previous
            continue
        previous = ((period - 1) * previous + current) / period
        out[idx] = previous
    return pd.Series(out, index=series.index, dtype=float)


def true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    values = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    result = values.max(axis=1, skipna=True)
    result.iloc[0] = float(df["high"].iloc[0] - df["low"].iloc[0])
    return result.astype(float)


def atr_wilder(df: pd.DataFrame, period: int) -> pd.Series:
    return wilder_rma(true_range(df), period)


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).fillna(0.0)
    loss = (-delta.clip(upper=0.0)).fillna(0.0)
    avg_gain = wilder_rma(gain, period)
    avg_loss = wilder_rma(loss, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return rsi.astype(float)


def adx_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0), index=df.index
    )
    atr = atr_wilder(df, period)
    plus_di = 100.0 * wilder_rma(plus_dm, period) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * wilder_rma(minus_dm, period) / atr.replace(0.0, np.nan)
    denominator = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denominator
    return wilder_rma(dx, period)


def safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.astype(float) / denominator.astype(float).replace(0.0, np.nan)


def lagged_percentile_rank(series: pd.Series, window: int) -> pd.Series:
    return series.shift(1).rolling(window=window, min_periods=window).rank(pct=True)


def build_timeframe_features(
    raw: pd.DataFrame,
    tf: str,
    profile: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    if tf not in TF_DELTAS:
        raise ValueError(f"Unsupported timeframe: {tf}")
    df = raw.copy()
    prefix = f"{tf}_"
    atr14 = atr_wilder(df, 14)
    atr50 = atr_wilder(df, 50)
    candle_range = df["high"] - df["low"]
    body = df["close"] - df["open"]
    body_abs = body.abs()
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]

    output = pd.DataFrame(index=df.index)
    output[f"{tf}_source_bar_open_time"] = df["time"]
    output[f"{tf}_source_bar_close_time"] = df["time"] + TF_DELTAS[tf]
    model_columns: list[str] = []

    def add(name: str, values: pd.Series) -> None:
        column = prefix + name
        output[column] = values.astype(float)
        model_columns.append(column)

    for lookback in profile["return_lookbacks"]:
        add(f"log_return_{lookback}", np.log(df["close"] / df["close"].shift(lookback)))

    add("range_atr14", safe_div(candle_range, atr14))
    add("body_atr14", safe_div(body_abs, atr14))
    add("signed_body_atr14", safe_div(body, atr14))
    add("body_fraction", safe_div(body_abs, candle_range))
    add("upper_wick_fraction", safe_div(upper_wick, candle_range))
    add("lower_wick_fraction", safe_div(lower_wick, candle_range))
    add("close_location", safe_div(df["close"] - df["low"], candle_range))
    add("atr14_close_ratio", safe_div(atr14, df["close"]))
    add("atr14_atr50_ratio", safe_div(atr14, atr50))
    add(
        f"atr14_percentile_lag1_{profile['percentile_window']}",
        lagged_percentile_rank(atr14, profile["percentile_window"]),
    )

    ema_values: dict[int, pd.Series] = {}
    for period in profile["ema_periods"]:
        ema_values[period] = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    periods = profile["ema_periods"]
    for fast, slow in zip(periods[:-1], periods[1:]):
        add(f"ema{fast}_ema{slow}_gap_atr14", safe_div(ema_values[fast] - ema_values[slow], atr14))
    for period in periods:
        add(f"ema{period}_slope4_atr14", safe_div(ema_values[period] - ema_values[period].shift(4), atr14))
    slowest = periods[-1]
    slow_lb = int(profile["slow_slope_lookback"])
    add(
        f"ema{slowest}_slope{slow_lb}_atr14",
        safe_div(ema_values[slowest] - ema_values[slowest].shift(slow_lb), atr14),
    )

    add("rsi14_centered", (rsi_wilder(df["close"], 14) - 50.0) / 50.0)
    add("adx14_scaled", adx_wilder(df, 14) / 100.0)

    ema12 = df["close"].ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = df["close"].ewm(span=26, adjust=False, min_periods=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
    add("macd_line_atr14", safe_div(macd, atr14))
    add("macd_signal_atr14", safe_div(macd_signal, atr14))
    add("macd_hist_atr14", safe_div(macd - macd_signal, atr14))

    bb_mid = df["close"].rolling(20, min_periods=20).mean()
    bb_std = df["close"].rolling(20, min_periods=20).std(ddof=0)
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    add("bb20_width_atr14", safe_div(bb_upper - bb_lower, atr14))
    add("bb20_close_location", safe_div(df["close"] - bb_lower, bb_upper - bb_lower))

    volume = df["tick_volume"].astype(float)
    volume_mean20 = volume.shift(1).rolling(20, min_periods=20).mean()
    volume_mean50 = volume.shift(1).rolling(50, min_periods=50).mean()
    add("tick_volume_ratio20_lagbase", safe_div(volume, volume_mean20))
    add("tick_volume_ratio50_lagbase", safe_div(volume, volume_mean50))
    add(
        f"tick_volume_percentile_lag1_{profile['percentile_window']}",
        lagged_percentile_rank(volume, profile["percentile_window"]),
    )

    spread_price = df["spread"].astype(float) * POINT
    add("spread_atr14", safe_div(spread_price, atr14))
    add(
        f"spread_percentile_lag1_{profile['percentile_window']}",
        lagged_percentile_rank(spread_price, profile["percentile_window"]),
    )

    for window in profile["extrema_windows"]:
        previous_high = df["high"].shift(1).rolling(window, min_periods=window).max()
        previous_low = df["low"].shift(1).rolling(window, min_periods=window).min()
        add(f"distance_from_prev_high_{window}_atr14", safe_div(df["close"] - previous_high, atr14))
        add(f"distance_from_prev_low_{window}_atr14", safe_div(df["close"] - previous_low, atr14))

    output[f"__{tf}_close"] = df["close"].astype(float)
    output[f"__{tf}_atr14"] = atr14.astype(float)
    if tf == "d1":
        output["__d1_completed_high"] = df["high"].astype(float)
        output["__d1_completed_low"] = df["low"].astype(float)
        output["__d1_completed_5bar_high"] = df["high"].rolling(5, min_periods=5).max().astype(float)
        output["__d1_completed_5bar_low"] = df["low"].rolling(5, min_periods=5).min().astype(float)

    return output, model_columns


def _asof_join(base: pd.DataFrame, other: pd.DataFrame, tf: str) -> pd.DataFrame:
    right_time = f"{tf}_source_bar_close_time"
    return pd.merge_asof(
        base.sort_values("decision_time"),
        other.sort_values(right_time),
        left_on="decision_time",
        right_on=right_time,
        direction="backward",
        allow_exact_matches=True,
    )


def build_dataset_from_frames(
    *,
    m1: pd.DataFrame,
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    h4: pd.DataFrame,
    d1: pd.DataFrame,
    profiles: dict[str, dict[str, Any]] | None = None,
) -> BuildResult:
    profiles = profiles or TF_PROFILES
    m15_features, m15_columns = build_timeframe_features(m15, "m15", profiles["m15"])
    h1_features, h1_columns = build_timeframe_features(h1, "h1", profiles["h1"])
    h4_features, h4_columns = build_timeframe_features(h4, "h4", profiles["h4"])
    d1_features, d1_columns = build_timeframe_features(d1, "d1", profiles["d1"])

    base = m15_features.copy()
    base = base.rename(columns={"m15_source_bar_close_time": "decision_time"})
    base["m15_source_bar_close_time"] = base["decision_time"]

    m1_entry = m1[["time", "open", "spread"]].rename(
        columns={
            "time": "decision_time",
            "open": "entry_m1_bid_open",
            "spread": "entry_m1_spread_points",
        }
    )
    base = base.merge(m1_entry, on="decision_time", how="left", validate="one_to_one")
    base["exact_m1_available"] = base["entry_m1_bid_open"].notna()

    joined = _asof_join(base, h1_features, "h1")
    joined = _asof_join(joined, h4_features, "h4")
    joined = _asof_join(joined, d1_features, "d1")

    cross_columns: list[str] = []
    m15_atr = joined["__m15_atr14"]
    m15_close = joined["__m15_close"]
    cross_values = {
        "cross_distance_from_completed_day_high_atr14": safe_div(
            m15_close - joined["__d1_completed_high"], m15_atr
        ),
        "cross_distance_from_completed_day_low_atr14": safe_div(
            m15_close - joined["__d1_completed_low"], m15_atr
        ),
        "cross_distance_from_completed_5d_high_atr14": safe_div(
            m15_close - joined["__d1_completed_5bar_high"], m15_atr
        ),
        "cross_distance_from_completed_5d_low_atr14": safe_div(
            m15_close - joined["__d1_completed_5bar_low"], m15_atr
        ),
    }
    for column, values in cross_values.items():
        joined[column] = values.astype(float)
        cross_columns.append(column)

    hour = joined["decision_time"].dt.hour + joined["decision_time"].dt.minute / 60.0
    weekday = joined["decision_time"].dt.dayofweek.astype(float)
    joined["time_server_hour_sin"] = np.sin(2.0 * math.pi * hour / 24.0)
    joined["time_server_hour_cos"] = np.cos(2.0 * math.pi * hour / 24.0)
    joined["time_weekday_sin"] = np.sin(2.0 * math.pi * weekday / 7.0)
    joined["time_weekday_cos"] = np.cos(2.0 * math.pi * weekday / 7.0)
    time_columns = [
        "time_server_hour_sin",
        "time_server_hour_cos",
        "time_weekday_sin",
        "time_weekday_cos",
    ]

    model_columns = m15_columns + h1_columns + h4_columns + d1_columns + cross_columns + time_columns
    metadata_columns = [
        "decision_time",
        "m15_source_bar_open_time",
        "m15_source_bar_close_time",
        "h1_source_bar_open_time",
        "h1_source_bar_close_time",
        "h4_source_bar_open_time",
        "h4_source_bar_close_time",
        "d1_source_bar_open_time",
        "d1_source_bar_close_time",
        "entry_m1_bid_open",
        "entry_m1_spread_points",
        "label_m15_atr14_price",
    ]
    joined["label_m15_atr14_price"] = joined["__m15_atr14"]

    rejection_summary: dict[str, Any] = {"m15_decisions": int(len(joined))}
    exact_mask = joined["exact_m1_available"].fillna(False)
    rejection_summary["missing_exact_m1"] = int((~exact_mask).sum())

    htf_mask = (
        joined["h1_source_bar_close_time"].notna()
        & joined["h4_source_bar_close_time"].notna()
        & joined["d1_source_bar_close_time"].notna()
    )
    rejection_summary["missing_closed_higher_timeframe"] = int((exact_mask & ~htf_mask).sum())

    finite_features = np.isfinite(joined[model_columns].to_numpy(dtype=float)).all(axis=1)
    warmup_mask = pd.Series(finite_features, index=joined.index)
    rejection_summary["feature_warmup_or_nonfinite"] = int((exact_mask & htf_mask & ~warmup_mask).sum())

    eligible = exact_mask & htf_mask & warmup_mask
    result = joined.loc[eligible, metadata_columns + model_columns].copy()
    result = result.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    rejection_summary["eligible_rows"] = int(len(result))
    rejection_summary["first_eligible_decision"] = str(result["decision_time"].iloc[0]) if len(result) else ""
    rejection_summary["last_eligible_decision"] = str(result["decision_time"].iloc[-1]) if len(result) else ""

    return BuildResult(
        features=result,
        model_feature_columns=model_columns,
        metadata_columns=metadata_columns,
        rejection_summary=rejection_summary,
    )


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    required = ["raw_files", "input_sha256", "timeframe_profiles", "model_feature_columns"]
    missing = [key for key in required if key not in contract]
    if missing:
        raise ValueError(f"Feature contract missing keys: {missing}")
    return contract


def validate_source_hashes(raw_dir: Path, contract: dict[str, Any]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for tf, filename in contract["raw_files"].items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        digest = sha256_file(path)
        actual[tf] = digest
        expected = contract["input_sha256"][tf]
        if digest != expected:
            raise ValueError(
                f"Input SHA256 mismatch for {tf}: expected {expected}, got {digest}"
            )
    return actual


def build_from_raw_dir(raw_dir: Path, contract: dict[str, Any]) -> BuildResult:
    validate_source_hashes(raw_dir, contract)
    raw_files = contract["raw_files"]
    m1 = read_raw_csv(raw_dir / raw_files["m1"], columns=["time", "open", "spread"])
    frames = {
        tf: read_raw_csv(raw_dir / raw_files[tf])
        for tf in ["m15", "h1", "h4", "d1"]
    }
    result = build_dataset_from_frames(
        m1=m1,
        profiles=contract["timeframe_profiles"],
        **frames,
    )
    expected_columns = contract["model_feature_columns"]
    if result.model_feature_columns != expected_columns:
        raise ValueError("Generated model feature columns do not match the frozen contract")
    return result


def deterministic_csv_gzip(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw_handle,
            compresslevel=9,
            mtime=0,
        ) as gzip_handle:
            with io.TextIOWrapper(gzip_handle, encoding="utf-8", newline="") as text_handle:
                df.to_csv(
                    text_handle,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GML1-MLR1 v1 causal feature registry")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/mlr1/ml02_features_v1"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"),
    )
    args = parser.parse_args()

    contract = load_contract(args.contract)
    result = build_from_raw_dir(args.raw_dir, contract)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    feature_path = args.output_dir / "mlr1_features_v1.csv.gz"
    deterministic_csv_gzip(result.features, feature_path)

    columns_path = args.output_dir / "mlr1_feature_columns_v1.json"
    write_json(
        columns_path,
        {
            "system_id": "GML1-MLR1",
            "version": "v1",
            "metadata_columns": result.metadata_columns,
            "model_feature_columns": result.model_feature_columns,
            "model_feature_count": len(result.model_feature_columns),
        },
    )
    manifest = {
        "system_id": "GML1-MLR1",
        "stage": "ML-02",
        "status": "FEATURE_REGISTRY_BUILT_AUDIT_ONLY",
        "feature_contract": str(args.contract),
        "feature_contract_sha256": sha256_file(args.contract),
        "input_sha256": contract["input_sha256"],
        "output": {
            "feature_registry": str(feature_path),
            "feature_registry_sha256": sha256_file(feature_path),
            "rows": len(result.features),
            "model_feature_count": len(result.model_feature_columns),
            "first_decision": str(result.features["decision_time"].iloc[0]),
            "last_decision": str(result.features["decision_time"].iloc[-1]),
            "feature_columns": str(columns_path),
            "feature_columns_sha256": sha256_file(columns_path),
        },
        "rejection_summary": result.rejection_summary,
        "controls": {
            "audit_only": True,
            "labels_built": False,
            "model_trained": False,
            "live_ready": False,
        },
    }
    write_json(args.output_dir / "mlr1_feature_manifest_v1.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
