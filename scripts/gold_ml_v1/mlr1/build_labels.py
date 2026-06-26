from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

POINT = 0.01
ONE_MINUTE = pd.Timedelta(minutes=1)


@dataclass(frozen=True)
class DirectionResult:
    resolved: bool
    outcome: str
    exit_bar_open_time: pd.Timestamp | None
    exit_time: pd.Timestamp | None
    exit_bid_close: float | None
    exit_ask_close: float | None
    exit_spread_points: int | None
    fill_price: float | None
    base_r: float | None
    strong_r: float | None
    extreme_r: float | None
    same_m1_collision: bool
    holding_minutes: int | None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


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


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    required = [
        "m1_file",
        "m1_sha256",
        "feature_registry_sha256",
        "target_atr",
        "protective_atr",
        "horizon_hours",
        "strong_cost",
        "extreme_cost",
    ]
    missing = [key for key in required if key not in contract]
    if missing:
        raise ValueError(f"Label contract missing keys: {missing}")
    return contract


def read_m1(path: Path) -> pd.DataFrame:
    required = ["time", "open", "high", "low", "close", "spread"]
    df = pd.read_csv(path, usecols=required)
    if set(df.columns) != set(required):
        raise ValueError(f"Unexpected M1 columns in {path}")
    df["time"] = pd.to_datetime(
        df["time"], format="%Y.%m.%d %H:%M:%S", errors="raise"
    )
    if df["time"].duplicated().any():
        raise ValueError("M1 timestamps contain duplicates")
    if not df["time"].is_monotonic_increasing:
        raise ValueError("M1 timestamps are not increasing")
    return df


def read_features(path: Path) -> pd.DataFrame:
    required = [
        "decision_time",
        "entry_m1_bid_open",
        "entry_m1_spread_points",
        "label_m15_atr14_price",
    ]
    df = pd.read_csv(path, usecols=required)
    df["decision_time"] = pd.to_datetime(df["decision_time"], errors="raise")
    if df["decision_time"].duplicated().any():
        raise ValueError("Feature registry decision times contain duplicates")
    if not df["decision_time"].is_monotonic_increasing:
        raise ValueError("Feature registry decision times are not increasing")
    if not np.isfinite(
        df[["entry_m1_bid_open", "entry_m1_spread_points", "label_m15_atr14_price"]]
        .to_numpy(dtype=float)
    ).all():
        raise ValueError("Feature registry label metadata contains nonfinite values")
    return df


def scenario_r(
    *,
    base_r: float,
    atr: float,
    direction: str,
    entry_spread_price: float,
    exit_spread_price: float,
    spread_multiplier: float,
    entry_slippage: float,
    exit_slippage: float,
) -> float:
    if spread_multiplier < 1.0:
        raise ValueError("spread multiplier cannot be below one")
    incremental_spread = (
        (spread_multiplier - 1.0) * entry_spread_price
        if direction == "LONG"
        else (spread_multiplier - 1.0) * exit_spread_price
    )
    return base_r - (
        incremental_spread + entry_slippage + exit_slippage
    ) / atr


def evaluate_direction(
    *,
    direction: str,
    decision_time: pd.Timestamp,
    entry_bid_open: float,
    entry_spread_points: int,
    atr: float,
    target_atr: float,
    protective_atr: float,
    horizon_hours: int,
    m1_times: np.ndarray,
    m1_open: np.ndarray,
    m1_high: np.ndarray,
    m1_low: np.ndarray,
    m1_close: np.ndarray,
    m1_spread: np.ndarray,
    last_observed_close_time: pd.Timestamp,
    strong_cost: dict[str, float],
    extreme_cost: dict[str, float],
) -> DirectionResult:
    if direction not in {"LONG", "SHORT"}:
        raise ValueError(direction)
    if not np.isfinite(atr) or atr <= 0.0:
        raise ValueError("ATR must be positive and finite")

    decision_ns = np.datetime64(decision_time, "ns")
    start = int(np.searchsorted(m1_times, decision_ns, side="left"))
    if start >= len(m1_times) or m1_times[start] != decision_ns:
        raise ValueError(f"Missing exact M1 at {decision_time}")

    horizon_time = decision_time + pd.Timedelta(hours=horizon_hours)
    horizon_ns = np.datetime64(horizon_time, "ns")
    end = int(np.searchsorted(m1_times, horizon_ns, side="left"))
    if end <= start:
        raise ValueError("No eligible M1 bars inside label horizon")

    spread_price = m1_spread[start:end].astype(float) * POINT
    bid_open = m1_open[start:end]
    ask_open = bid_open + spread_price
    ask_high = m1_high[start:end] + spread_price
    ask_low = m1_low[start:end] + spread_price
    ask_close = m1_close[start:end] + spread_price

    entry_spread_price = float(entry_spread_points) * POINT
    if direction == "LONG":
        entry_price = float(entry_bid_open) + entry_spread_price
        target_price = entry_price + target_atr * atr
        protective_price = entry_price - protective_atr * atr
        gap_protective = bid_open <= protective_price
        gap_target = bid_open >= target_price
        target_hits = m1_high[start:end] >= target_price
        protective_hits = m1_low[start:end] <= protective_price
    else:
        entry_price = float(entry_bid_open)
        target_price = entry_price - target_atr * atr
        protective_price = entry_price + protective_atr * atr
        gap_protective = ask_open >= protective_price
        gap_target = ask_open <= target_price
        target_hits = ask_low <= target_price
        protective_hits = ask_high >= protective_price

    any_hits = target_hits | protective_hits
    hit_offsets = np.flatnonzero(any_hits)
    if len(hit_offsets):
        offset = int(hit_offsets[0])
        absolute_index = start + offset
        collision = bool(target_hits[offset] and protective_hits[offset])
        if gap_protective[offset]:
            outcome = "PROTECTIVE"
            fill_price = float(bid_open[offset] if direction == "LONG" else ask_open[offset])
            collision = False
        elif gap_target[offset]:
            outcome = "TARGET"
            fill_price = target_price
            collision = False
        elif protective_hits[offset]:
            outcome = "PROTECTIVE"
            fill_price = protective_price
        else:
            outcome = "TARGET"
            fill_price = target_price
        exit_bar_open_time = pd.Timestamp(m1_times[absolute_index])
        exit_time = exit_bar_open_time + ONE_MINUTE
    else:
        if horizon_time > last_observed_close_time:
            return DirectionResult(
                resolved=False,
                outcome="UNRESOLVED",
                exit_bar_open_time=None,
                exit_time=None,
                exit_bid_close=None,
                exit_ask_close=None,
                exit_spread_points=None,
                fill_price=None,
                base_r=None,
                strong_r=None,
                extreme_r=None,
                same_m1_collision=False,
                holding_minutes=None,
            )
        absolute_index = end - 1
        offset = absolute_index - start
        collision = False
        outcome = "TIME"
        exit_bar_open_time = pd.Timestamp(m1_times[absolute_index])
        exit_time = exit_bar_open_time + ONE_MINUTE
        fill_price = (
            float(m1_close[absolute_index])
            if direction == "LONG"
            else float(ask_close[offset])
        )

    exit_bid_close = float(m1_close[absolute_index])
    exit_spread_points = int(m1_spread[absolute_index])
    exit_ask_close = exit_bid_close + exit_spread_points * POINT
    base_r = (
        (float(fill_price) - entry_price) / atr
        if direction == "LONG"
        else (entry_price - float(fill_price)) / atr
    )
    exit_spread_price = exit_spread_points * POINT
    strong_r = scenario_r(
        base_r=base_r,
        atr=atr,
        direction=direction,
        entry_spread_price=entry_spread_price,
        exit_spread_price=exit_spread_price,
        spread_multiplier=float(strong_cost["spread_multiplier"]),
        entry_slippage=float(strong_cost["entry_slippage_price"]),
        exit_slippage=float(strong_cost["exit_slippage_price"]),
    )
    extreme_r = scenario_r(
        base_r=base_r,
        atr=atr,
        direction=direction,
        entry_spread_price=entry_spread_price,
        exit_spread_price=exit_spread_price,
        spread_multiplier=float(extreme_cost["spread_multiplier"]),
        entry_slippage=float(extreme_cost["entry_slippage_price"]),
        exit_slippage=float(extreme_cost["exit_slippage_price"]),
    )
    holding_minutes = int((exit_time - decision_time) / ONE_MINUTE)

    return DirectionResult(
        resolved=True,
        outcome=outcome,
        exit_bar_open_time=exit_bar_open_time,
        exit_time=exit_time,
        exit_bid_close=exit_bid_close,
        exit_ask_close=exit_ask_close,
        exit_spread_points=exit_spread_points,
        fill_price=float(fill_price),
        base_r=float(base_r),
        strong_r=float(strong_r),
        extreme_r=float(extreme_r),
        same_m1_collision=collision,
        holding_minutes=holding_minutes,
    )


def build_labels(
    features: pd.DataFrame,
    m1: pd.DataFrame,
    contract: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    m1_times = m1["time"].to_numpy(dtype="datetime64[ns]")
    m1_open = m1["open"].to_numpy(dtype=float)
    m1_high = m1["high"].to_numpy(dtype=float)
    m1_low = m1["low"].to_numpy(dtype=float)
    m1_close = m1["close"].to_numpy(dtype=float)
    m1_spread = m1["spread"].to_numpy(dtype=int)
    last_observed_close_time = pd.Timestamp(m1_times[-1]) + ONE_MINUTE

    rows: list[dict[str, Any]] = []
    unresolved = {"LONG": 0, "SHORT": 0}
    for item in features.itertuples(index=False):
        decision_time = pd.Timestamp(item.decision_time)
        entry_bid_open = float(item.entry_m1_bid_open)
        entry_spread_points = int(item.entry_m1_spread_points)
        atr = float(item.label_m15_atr14_price)
        for direction in ["LONG", "SHORT"]:
            result = evaluate_direction(
                direction=direction,
                decision_time=decision_time,
                entry_bid_open=entry_bid_open,
                entry_spread_points=entry_spread_points,
                atr=atr,
                target_atr=float(contract["target_atr"]),
                protective_atr=float(contract["protective_atr"]),
                horizon_hours=int(contract["horizon_hours"]),
                m1_times=m1_times,
                m1_open=m1_open,
                m1_high=m1_high,
                m1_low=m1_low,
                m1_close=m1_close,
                m1_spread=m1_spread,
                last_observed_close_time=last_observed_close_time,
                strong_cost=contract["strong_cost"],
                extreme_cost=contract["extreme_cost"],
            )
            if not result.resolved:
                unresolved[direction] += 1
                continue
            entry_spread_price = entry_spread_points * POINT
            entry_price = (
                entry_bid_open + entry_spread_price
                if direction == "LONG"
                else entry_bid_open
            )
            target_price = (
                entry_price + float(contract["target_atr"]) * atr
                if direction == "LONG"
                else entry_price - float(contract["target_atr"]) * atr
            )
            protective_price = (
                entry_price - float(contract["protective_atr"]) * atr
                if direction == "LONG"
                else entry_price + float(contract["protective_atr"]) * atr
            )
            rows.append({
                "decision_time": decision_time,
                "direction": direction,
                "entry_time": decision_time,
                "entry_bid_open": entry_bid_open,
                "entry_spread_points": entry_spread_points,
                "entry_price": entry_price,
                "label_atr14_price": atr,
                "target_price": target_price,
                "protective_price": protective_price,
                "outcome": result.outcome,
                "exit_bar_open_time": result.exit_bar_open_time,
                "exit_time": result.exit_time,
                "exit_bid_close": result.exit_bid_close,
                "exit_ask_close": result.exit_ask_close,
                "exit_spread_points": result.exit_spread_points,
                "fill_price": result.fill_price,
                "base_r": result.base_r,
                "strong_r": result.strong_r,
                "extreme_r": result.extreme_r,
                "same_m1_collision": result.same_m1_collision,
                "holding_minutes": result.holding_minutes,
            })

    labels = pd.DataFrame(rows)
    labels = labels.sort_values(
        ["decision_time", "direction"], kind="mergesort"
    ).reset_index(drop=True)
    summary: dict[str, Any] = {
        "feature_rows": int(len(features)),
        "potential_direction_rows": int(len(features) * 2),
        "resolved_rows": int(len(labels)),
        "unresolved": unresolved,
        "resolved_by_direction": labels["direction"].value_counts().sort_index().to_dict(),
        "outcomes_by_direction": {
            direction: labels.loc[labels["direction"] == direction, "outcome"]
            .value_counts()
            .sort_index()
            .to_dict()
            for direction in ["LONG", "SHORT"]
        },
        "same_m1_collisions": {
            direction: int(
                labels.loc[labels["direction"] == direction, "same_m1_collision"].sum()
            )
            for direction in ["LONG", "SHORT"]
        },
    }
    return labels, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GML1-MLR1 v1 exact-M1 labels")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument(
        "--feature-registry",
        type=Path,
        default=Path("outputs/gold_ml_v1/mlr1/ml02_features_v1/mlr1_features_v1.csv.gz"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/gold_ml_v1/mlr1_label_contract_v1_20260627.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/mlr1/ml03_labels_v1"),
    )
    args = parser.parse_args()

    contract = load_contract(args.contract)
    m1_path = args.raw_dir / contract["m1_file"]
    if sha256_file(m1_path) != contract["m1_sha256"]:
        raise ValueError("M1 SHA256 mismatch")
    if sha256_file(args.feature_registry) != contract["feature_registry_sha256"]:
        raise ValueError("Feature registry SHA256 mismatch")

    m1 = read_m1(m1_path)
    features = read_features(args.feature_registry)
    labels, summary = build_labels(features, m1, contract)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    label_path = args.output_dir / "mlr1_labels_v1.csv.gz"
    deterministic_csv_gzip(labels, label_path)
    manifest = {
        "system_id": "GML1-MLR1",
        "stage": "ML-03",
        "status": "LABEL_REGISTRY_BUILT_AUDIT_ONLY",
        "contract": str(args.contract),
        "contract_sha256": sha256_file(args.contract),
        "input": {
            "m1_sha256": contract["m1_sha256"],
            "feature_registry_sha256": contract["feature_registry_sha256"],
        },
        "output": {
            "label_registry": str(label_path),
            "label_registry_sha256": sha256_file(label_path),
            "rows": int(len(labels)),
            "first_decision": str(labels["decision_time"].iloc[0]),
            "last_decision": str(labels["decision_time"].iloc[-1]),
        },
        "summary": summary,
        "controls": {
            "audit_only": True,
            "model_trained": False,
            "live_ready": False,
        },
    }
    write_json(args.output_dir / "mlr1_label_manifest_v1.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
