from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_FEATURE_SHA256 = "81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b"
EXPECTED_PROPOSAL_SHA256 = "7886b519d7adf3b4127599478e1f56271701667865dfcaac3b99ad833ac093e6"
ONE_M15 = pd.Timedelta(minutes=15)

PRIORITY = [
    "GML1-DISC-EXH-L", "GML1-DISC-EXH-S",
    "GML1-DISC-RECL-L", "GML1-DISC-RECL-S",
    "GML1-DISC-CMP-L", "GML1-DISC-CMP-S",
    "GML1-DISC-BRK-L", "GML1-DISC-BRK-S",
    "GML1-DISC-BBR-L", "GML1-DISC-BBR-S",
    "GML1-DISC-MOM-L", "GML1-DISC-MOM-S",
    "GML1-DISC-RSI-L", "GML1-DISC-RSI-S",
]

FAMILIES = {
    "GML1-DISC-EXH-L": "VOLATILITY_EXHAUSTION",
    "GML1-DISC-EXH-S": "VOLATILITY_EXHAUSTION",
    "GML1-DISC-RECL-L": "FAILED_BREAKOUT_RECLAIM",
    "GML1-DISC-RECL-S": "FAILED_BREAKOUT_RECLAIM",
    "GML1-DISC-CMP-L": "COMPRESSION_RELEASE",
    "GML1-DISC-CMP-S": "COMPRESSION_RELEASE",
    "GML1-DISC-BRK-L": "ROLLING_BREAKOUT",
    "GML1-DISC-BRK-S": "ROLLING_BREAKOUT",
    "GML1-DISC-BBR-L": "BOLLINGER_REENTRY",
    "GML1-DISC-BBR-S": "BOLLINGER_REENTRY",
    "GML1-DISC-MOM-L": "MOMENTUM_IGNITION",
    "GML1-DISC-MOM-S": "MOMENTUM_IGNITION",
    "GML1-DISC-RSI-L": "RSI_TURN",
    "GML1-DISC-RSI-S": "RSI_TURN",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_deterministic_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
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


def previous_exact(frame: pd.DataFrame, column: str, bars: int = 1) -> pd.Series:
    exact = frame["decision_time"].diff(bars).eq(ONE_M15 * bars)
    return frame[column].shift(bars).where(exact)


def cross_up(frame: pd.DataFrame, column: str, level: float) -> pd.Series:
    return (previous_exact(frame, column) <= level) & (frame[column] > level)


def cross_down(frame: pd.DataFrame, column: str, level: float) -> pd.Series:
    return (previous_exact(frame, column) >= level) & (frame[column] < level)


def onset(frame: pd.DataFrame, state: pd.Series) -> pd.Series:
    exact = frame["decision_time"].diff().eq(ONE_M15)
    prior = state.shift(1).where(exact, False).fillna(False).astype(bool)
    return state.fillna(False).astype(bool) & ~prior


def event_states(frame: pd.DataFrame) -> dict[str, pd.Series]:
    f = frame
    p = lambda column: previous_exact(f, column)
    states = {
        "GML1-DISC-EXH-L": (
            (f.m15_atr14_percentile_lag1_256 >= 0.65)
            & (f.m15_rsi14_centered <= -0.25)
            & (f.m15_range_atr14 >= 1.0)
            & (f.m15_lower_wick_fraction >= 0.40)
        ),
        "GML1-DISC-EXH-S": (
            (f.m15_atr14_percentile_lag1_256 >= 0.65)
            & (f.m15_rsi14_centered >= 0.25)
            & (f.m15_range_atr14 >= 1.0)
            & (f.m15_upper_wick_fraction >= 0.40)
        ),
        "GML1-DISC-RECL-L": (
            (p("m15_distance_from_prev_low_50_atr14") < 0)
            & (f.m15_distance_from_prev_low_50_atr14 >= 0)
            & (f.m15_lower_wick_fraction >= 0.20)
            & (f.m15_close_location >= 0.55)
        ),
        "GML1-DISC-RECL-S": (
            (p("m15_distance_from_prev_high_50_atr14") > 0)
            & (f.m15_distance_from_prev_high_50_atr14 <= 0)
            & (f.m15_upper_wick_fraction >= 0.20)
            & (f.m15_close_location <= 0.45)
        ),
        "GML1-DISC-CMP-L": (
            (p("m15_atr14_percentile_lag1_256") <= 0.40)
            & (f.m15_range_atr14 >= 1.0)
            & (f.m15_bb20_close_location > 1.0)
            & (f.m15_signed_body_atr14 > 0)
            & (f.m15_body_fraction >= 0.50)
        ),
        "GML1-DISC-CMP-S": (
            (p("m15_atr14_percentile_lag1_256") <= 0.40)
            & (f.m15_range_atr14 >= 1.0)
            & (f.m15_bb20_close_location < 0.0)
            & (f.m15_signed_body_atr14 < 0)
            & (f.m15_body_fraction >= 0.50)
        ),
        "GML1-DISC-BRK-L": (
            (p("m15_distance_from_prev_high_50_atr14") < 0)
            & (f.m15_distance_from_prev_high_50_atr14 >= 0)
            & (f.m15_signed_body_atr14 > 0)
            & (f.m15_body_fraction >= 0.55)
            & (f.m15_tick_volume_ratio20_lagbase >= 1.10)
        ),
        "GML1-DISC-BRK-S": (
            (p("m15_distance_from_prev_low_50_atr14") > 0)
            & (f.m15_distance_from_prev_low_50_atr14 <= 0)
            & (f.m15_signed_body_atr14 < 0)
            & (f.m15_body_fraction >= 0.55)
            & (f.m15_tick_volume_ratio20_lagbase >= 1.10)
        ),
        "GML1-DISC-BBR-L": (
            (p("m15_bb20_close_location") < 0)
            & (f.m15_bb20_close_location >= 0)
            & (f.m15_lower_wick_fraction >= 0.25)
            & (f.m15_close_location >= 0.50)
        ),
        "GML1-DISC-BBR-S": (
            (p("m15_bb20_close_location") > 1)
            & (f.m15_bb20_close_location <= 1)
            & (f.m15_upper_wick_fraction >= 0.25)
            & (f.m15_close_location <= 0.50)
        ),
        "GML1-DISC-MOM-L": (
            cross_up(f, "m15_macd_hist_atr14", 0.0)
            & (f.m15_signed_body_atr14 >= 0.05)
            & (f.m15_close_location >= 0.55)
            & (f.m15_tick_volume_ratio20_lagbase >= 1.10)
        ),
        "GML1-DISC-MOM-S": (
            cross_down(f, "m15_macd_hist_atr14", 0.0)
            & (f.m15_signed_body_atr14 <= -0.05)
            & (f.m15_close_location <= 0.45)
            & (f.m15_tick_volume_ratio20_lagbase >= 1.10)
        ),
        "GML1-DISC-RSI-L": (
            cross_up(f, "m15_rsi14_centered", -0.35)
            & (f.m15_macd_hist_atr14 > p("m15_macd_hist_atr14"))
        ),
        "GML1-DISC-RSI-S": (
            cross_down(f, "m15_rsi14_centered", 0.35)
            & (f.m15_macd_hist_atr14 < p("m15_macd_hist_atr14"))
        ),
    }
    return {candidate_id: onset(f, state) for candidate_id, state in states.items()}


def build(frame: pd.DataFrame, model_columns: list[str]) -> tuple[pd.DataFrame, int]:
    states = event_states(frame)
    matrix = pd.DataFrame(states, index=frame.index).astype(bool)
    long_columns = [column for column in PRIORITY if column.endswith("-L")]
    short_columns = [column for column in PRIORITY if column.endswith("-S")]
    conflict = matrix[long_columns].any(axis=1) & matrix[short_columns].any(axis=1)
    assigned = pd.Series(pd.NA, index=frame.index, dtype="object")
    for candidate_id in PRIORITY:
        selected = matrix[candidate_id] & assigned.isna() & ~conflict
        assigned.loc[selected] = candidate_id

    rows: list[dict[str, object]] = []
    for index, candidate_id in assigned.dropna().items():
        direction = "LONG" if str(candidate_id).endswith("-L") else "SHORT"
        row = frame.loc[index, ["decision_time"] + model_columns].to_dict()
        row.update(
            {
                "candidate_id": candidate_id,
                "candidate_definition_version": "event-discovery-v2",
                "candidate_family": FAMILIES[str(candidate_id)],
                "direction": direction,
                "proposal_strength": 1.0,
            }
        )
        rows.append(row)
    proposals = pd.DataFrame(rows)
    proposals = proposals[
        [
            "decision_time", "candidate_id", "candidate_definition_version",
            "candidate_family", "direction", "proposal_strength",
        ]
        + model_columns
    ]
    proposals = proposals.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)
    if proposals["decision_time"].duplicated().any():
        raise AssertionError("Event Discovery v2 must emit at most one row per decision")
    return proposals, int(conflict.sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.feature_registry) != EXPECTED_FEATURE_SHA256:
        raise ValueError("Feature registry SHA256 mismatch")
    contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    model_columns = list(contract["model_feature_columns"])
    if len(model_columns) != 161 or len(model_columns) != len(set(model_columns)):
        raise ValueError("Frozen 161-feature contract mismatch")

    frame = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    if frame["decision_time"].duplicated().any() or not frame["decision_time"].is_monotonic_increasing:
        raise ValueError("Feature decision_time contract mismatch")
    if not np.isfinite(frame[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite model features")

    proposals, conflicts = build(frame, model_columns)
    output_path = args.output_dir / "gml1_event_discovery_v2_proposals.csv.gz"
    summary_path = args.output_dir / "gml1_event_discovery_v2_summary.json"
    write_deterministic_gzip_csv(proposals, output_path)
    output_sha = sha256_file(output_path)
    if output_sha != EXPECTED_PROPOSAL_SHA256:
        raise AssertionError(f"Frozen proposal SHA mismatch: {output_sha}")
    summary = {
        "system_id": "GML1-EVENT-DISCOVERY",
        "version": "v2",
        "status": "LABEL_FREE_PROPOSALS_FROZEN",
        "proposal_rows": int(len(proposals)),
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "direction_counts": {
            str(key): int(value)
            for key, value in proposals["direction"].value_counts().sort_index().items()
        },
        "candidate_counts": {
            str(key): int(value)
            for key, value in proposals["candidate_id"].value_counts().sort_index().items()
        },
        "raw_direction_conflicts_excluded": conflicts,
        "proposal_registry_sha256": output_sha,
        "labels_read": False,
        "performance_read": False,
        "deployment_allowed": False,
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
