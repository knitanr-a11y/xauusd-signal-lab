from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

POINT = 0.01
LABEL_COLUMNS = [
    "decision_time", "direction", "entry_time", "entry_bid_open",
    "entry_spread_points", "entry_price", "label_atr14_price",
    "target_price", "protective_price", "outcome",
    "exit_bar_open_time", "exit_time", "exit_bid_close", "exit_ask_close",
    "exit_spread_points", "fill_price", "base_r", "strong_r", "extreme_r",
    "same_m1_collision", "holding_minutes",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def deterministic_csv_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(
                    text,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_m1(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"time", "open", "high", "low", "close", "spread"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"M1 missing columns: {missing}")
    frame["time"] = pd.to_datetime(
        frame["time"], format="%Y.%m.%d %H:%M:%S", errors="raise"
    )
    if frame["time"].duplicated().any() or not frame["time"].is_monotonic_increasing:
        raise ValueError("M1 timestamps must be unique and increasing")
    if not frame["time"].dt.second.eq(0).all():
        raise ValueError("M1 timestamps contain non-zero seconds")
    return frame


class ExactM1Labeler:
    def __init__(self, m1: pd.DataFrame, contract: dict[str, Any]):
        self.contract = contract
        self.times = m1["time"].to_numpy(dtype="datetime64[ns]")
        self.open = m1["open"].to_numpy(dtype=float)
        self.high = m1["high"].to_numpy(dtype=float)
        self.low = m1["low"].to_numpy(dtype=float)
        self.close = m1["close"].to_numpy(dtype=float)
        self.spread = m1["spread"].to_numpy(dtype=float)
        self.last_observed_close = pd.Timestamp(
            self.times[-1] + np.timedelta64(1, "m")
        )
        self.horizon = pd.Timedelta(hours=int(contract["horizon_hours"]))
        self.target_atr = float(contract["target_atr"])
        self.protective_atr = float(contract["protective_atr"])

    def label(
        self, decision_time: pd.Timestamp, direction: str, atr: float
    ) -> dict[str, Any] | None:
        decision_time = pd.Timestamp(decision_time)
        dt64 = np.datetime64(decision_time, "ns")
        index = int(np.searchsorted(self.times, dt64))
        if index >= len(self.times) or self.times[index] != dt64:
            return None
        if direction not in {"LONG", "SHORT"}:
            raise ValueError(f"Unexpected direction: {direction}")
        if not np.isfinite(atr) or atr <= 0.0:
            raise ValueError("ATR must be finite and positive")

        entry_bid = float(self.open[index])
        entry_spread = float(self.spread[index])
        entry_ask = entry_bid + entry_spread * POINT
        if direction == "LONG":
            entry_price = entry_ask
            target = entry_price + self.target_atr * atr
            protective = entry_price - self.protective_atr * atr
        else:
            entry_price = entry_bid
            target = entry_price - self.target_atr * atr
            protective = entry_price + self.protective_atr * atr

        horizon_time = np.datetime64(decision_time + self.horizon, "ns")
        stop = int(np.searchsorted(self.times, horizon_time, side="left"))
        outcome = None
        exit_index = None
        fill_price = None
        collision = False

        for row in range(index, stop):
            spread_price = self.spread[row] * POINT
            if direction == "LONG":
                bar_open = self.open[row]
                bar_high = self.high[row]
                bar_low = self.low[row]
                if bar_open <= protective:
                    outcome, exit_index, fill_price = "PROTECTIVE", row, float(bar_open)
                    break
                if bar_open >= target:
                    outcome, exit_index, fill_price = "TARGET", row, float(target)
                    break
                protective_hit = bar_low <= protective
                target_hit = bar_high >= target
            else:
                bar_open = self.open[row] + spread_price
                bar_high = self.high[row] + spread_price
                bar_low = self.low[row] + spread_price
                if bar_open >= protective:
                    outcome, exit_index, fill_price = "PROTECTIVE", row, float(bar_open)
                    break
                if bar_open <= target:
                    outcome, exit_index, fill_price = "TARGET", row, float(target)
                    break
                protective_hit = bar_high >= protective
                target_hit = bar_low <= target

            if protective_hit and target_hit:
                outcome, exit_index, fill_price = "PROTECTIVE", row, float(protective)
                collision = True
                break
            if protective_hit:
                outcome, exit_index, fill_price = "PROTECTIVE", row, float(protective)
                break
            if target_hit:
                outcome, exit_index, fill_price = "TARGET", row, float(target)
                break

        if outcome is None:
            if decision_time + self.horizon > self.last_observed_close or stop <= index:
                return {"resolved": False, "reason": "HORIZON_NOT_OBSERVED"}
            exit_index = stop - 1
            outcome = "TIME"
            fill_price = float(self.close[exit_index])
            if direction == "SHORT":
                fill_price += self.spread[exit_index] * POINT

        exit_bar_open = pd.Timestamp(self.times[exit_index])
        exit_time = exit_bar_open + pd.Timedelta(minutes=1)
        exit_bid_close = float(self.close[exit_index])
        exit_spread = float(self.spread[exit_index])
        exit_ask_close = exit_bid_close + exit_spread * POINT

        if direction == "LONG":
            base_r = (fill_price - entry_price) / atr
            stress_spread = entry_spread * POINT
        else:
            base_r = (entry_price - fill_price) / atr
            stress_spread = exit_spread * POINT

        strong = self.contract["strong_cost"]
        extreme = self.contract["extreme_cost"]
        strong_r = base_r - (
            (float(strong["spread_multiplier"]) - 1.0) * stress_spread
            + float(strong["entry_slippage_price"])
            + float(strong["exit_slippage_price"])
        ) / atr
        extreme_r = base_r - (
            (float(extreme["spread_multiplier"]) - 1.0) * stress_spread
            + float(extreme["entry_slippage_price"])
            + float(extreme["exit_slippage_price"])
        ) / atr

        return {
            "resolved": True,
            "decision_time": decision_time,
            "direction": direction,
            "entry_time": decision_time,
            "entry_bid_open": entry_bid,
            "entry_spread_points": entry_spread,
            "entry_price": entry_price,
            "label_atr14_price": float(atr),
            "target_price": float(target),
            "protective_price": float(protective),
            "outcome": outcome,
            "exit_bar_open_time": exit_bar_open,
            "exit_time": exit_time,
            "exit_bid_close": exit_bid_close,
            "exit_ask_close": exit_ask_close,
            "exit_spread_points": exit_spread,
            "fill_price": float(fill_price),
            "base_r": float(base_r),
            "strong_r": float(strong_r),
            "extreme_r": float(extreme_r),
            "same_m1_collision": bool(collision),
            "holding_minutes": int(
                (exit_time - decision_time).total_seconds() / 60.0
            ),
        }


def build_resolved_registry(
    features: pd.DataFrame,
    proposals: pd.DataFrame,
    labeler: ExactM1Labeler,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not {"decision_time", "label_m15_atr14_price"}.issubset(features.columns):
        raise ValueError("Prospective features missing decision_time or ATR")
    if not {"decision_time", "candidate_id", "direction"}.issubset(proposals.columns):
        raise ValueError("Prospective proposals missing required metadata")
    if proposals.duplicated(["decision_time", "candidate_id"]).any():
        raise ValueError("Duplicate prospective candidate event")

    feature_atr = features[["decision_time", "label_m15_atr14_price"]].copy()
    if feature_atr["decision_time"].duplicated().any():
        raise ValueError("Duplicate prospective feature decision_time")
    keys = proposals[["decision_time", "direction"]].drop_duplicates().merge(
        feature_atr, on="decision_time", how="left", validate="many_to_one"
    )
    if keys["label_m15_atr14_price"].isna().any():
        raise ValueError("Proposal decision missing feature ATR")

    resolved_rows: list[dict[str, Any]] = []
    unresolved_rows: list[dict[str, Any]] = []
    for row in keys.itertuples(index=False):
        result = labeler.label(
            row.decision_time, row.direction, float(row.label_m15_atr14_price)
        )
        if result is None:
            unresolved_rows.append({
                "decision_time": row.decision_time,
                "direction": row.direction,
                "reason": "EXACT_M1_MISSING",
            })
        elif not result["resolved"]:
            unresolved_rows.append({
                "decision_time": row.decision_time,
                "direction": row.direction,
                "reason": result["reason"],
            })
        else:
            resolved_rows.append({column: result[column] for column in LABEL_COLUMNS})

    labels = pd.DataFrame(resolved_rows, columns=LABEL_COLUMNS).sort_values(
        ["decision_time", "direction"], kind="mergesort"
    ).reset_index(drop=True)
    unresolved = pd.DataFrame(
        unresolved_rows, columns=["decision_time", "direction", "reason"]
    ).sort_values(["decision_time", "direction"], kind="mergesort").reset_index(drop=True)
    resolved_events = proposals.merge(
        labels, on=["decision_time", "direction"], how="inner", validate="many_to_one"
    ).sort_values(["decision_time", "candidate_id"], kind="mergesort").reset_index(drop=True)
    unresolved_events = proposals.merge(
        unresolved[["decision_time", "direction"]],
        on=["decision_time", "direction"], how="inner", validate="many_to_one"
    ).sort_values(["decision_time", "candidate_id"], kind="mergesort").reset_index(drop=True)
    if len(resolved_events) + len(unresolved_events) != len(proposals):
        raise AssertionError("Prospective proposal row retention failure")
    return labels, unresolved, resolved_events, unresolved_events


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build resolved-only prospective MLR1 labels and candidate events"
    )
    parser.add_argument("--prospective-features", type=Path, required=True)
    parser.add_argument("--prospective-proposals", type=Path, required=True)
    parser.add_argument("--m1", type=Path, required=True)
    parser.add_argument("--label-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.m1.name.lower().startswith("goldsharp_") or args.m1.suffix.lower() != ".csv":
        raise ValueError("Prospective M1 must be an explicit goldsharp_*.csv file")
    if "gold_v3_2023_2026" in {part.lower() for part in args.m1.resolve().parts}:
        raise ValueError("Historical M1 is forbidden for prospective capture")

    before_hash = sha256_file(args.m1)
    contract = json.loads(args.label_contract.read_text(encoding="utf-8"))
    if contract.get("resolved_only") is not True:
        raise ValueError("Label contract is not resolved-only")
    features = pd.read_csv(args.prospective_features, parse_dates=["decision_time"])
    proposals = pd.read_csv(args.prospective_proposals, parse_dates=["decision_time"])
    m1 = read_m1(args.m1)
    after_hash = sha256_file(args.m1)
    if before_hash != after_hash:
        raise RuntimeError("M1 source changed while being read")

    labeler = ExactM1Labeler(m1, contract)
    labels, unresolved, resolved_events, unresolved_events = build_resolved_registry(
        features, proposals, labeler
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "labels": args.output_dir / "mlr1_prospective_resolved_labels_v1.csv.gz",
        "unresolved_keys": args.output_dir / "mlr1_prospective_unresolved_label_keys_v1.csv.gz",
        "resolved_events": args.output_dir / "mlr1_prospective_resolved_candidate_events_v1.csv.gz",
        "unresolved_events": args.output_dir / "mlr1_prospective_unresolved_candidate_events_v1.csv.gz",
    }
    deterministic_csv_gzip(labels, paths["labels"])
    deterministic_csv_gzip(unresolved, paths["unresolved_keys"])
    deterministic_csv_gzip(resolved_events, paths["resolved_events"])
    deterministic_csv_gzip(unresolved_events, paths["unresolved_events"])

    summary = {
        "system_id": "GML1-MLR1",
        "stage": "PROSPECTIVE_CAPTURE",
        "status": "RESOLVED_ONLY_PROSPECTIVE_CANDIDATE_EVENTS_BUILT_AUDIT_ONLY",
        "m1_sha256": before_hash,
        "proposal_rows": int(len(proposals)),
        "unique_decision_direction_keys": int(
            proposals[["decision_time", "direction"]].drop_duplicates().shape[0]
        ),
        "resolved_label_keys": int(len(labels)),
        "unresolved_label_keys": int(len(unresolved)),
        "resolved_candidate_events": int(len(resolved_events)),
        "unresolved_candidate_events": int(len(unresolved_events)),
        "last_observed_m1_close": str(labeler.last_observed_close),
        "outputs": {
            key: {"path": str(path), "sha256": sha256_file(path)}
            for key, path in paths.items()
        },
        "candidate_performance_calculated": False,
        "candidate_definitions_changed": False,
        "model_loaded": False,
        "prediction_generated": False,
        "audit_only": True,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    }
    write_json(
        args.output_dir / "mlr1_prospective_capture_summary_v1.json", summary
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
