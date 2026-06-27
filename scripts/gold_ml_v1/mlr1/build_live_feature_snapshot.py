from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_features as feature_engine

TIMEFRAMES = ("m1", "m15", "h1", "h4", "d1")
FORBIDDEN_PATH_SEGMENT = "gold_v3_2023_2026"


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
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an audit-only causal live feature snapshot from explicit Files-root goldsharp CSV paths"
    )
    for timeframe in TIMEFRAMES:
        parser.add_argument(f"--{timeframe}", type=Path, required=True)
    parser.add_argument(
        "--feature-contract",
        type=Path,
        default=Path("config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"),
    )
    parser.add_argument(
        "--adapter-contract",
        type=Path,
        default=Path("config/gold_ml_v1/mlr1_live_source_adapter_contract_v1_20260627.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/gml1/live_features"))
    return parser


def validate_explicit_paths(paths: dict[str, Path]) -> dict[str, Path]:
    if set(paths) != set(TIMEFRAMES):
        raise ValueError("Exactly one explicit path is required for every frozen timeframe")

    resolved: dict[str, Path] = {}
    for timeframe, supplied in paths.items():
        path = supplied.expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"{timeframe}: not a file: {path}")
        if not path.name.lower().startswith("goldsharp_") or path.suffix.lower() != ".csv":
            raise ValueError(f"{timeframe}: live filename must match goldsharp_*.csv: {path.name}")
        if FORBIDDEN_PATH_SEGMENT.lower() in {part.lower() for part in path.parts}:
            raise ValueError(f"{timeframe}: historical directory is forbidden for live input: {path}")
        resolved[timeframe] = path

    if len(set(resolved.values())) != len(TIMEFRAMES):
        raise ValueError("Each timeframe must use a distinct explicit file")
    parents = {path.parent for path in resolved.values()}
    if len(parents) != 1:
        raise ValueError("All live input files must be in the same explicit Files-root directory")
    return resolved


def validate_time_alignment(frame: pd.DataFrame, timeframe: str, path: Path) -> None:
    time = frame["time"]
    if not time.dt.second.eq(0).all():
        raise ValueError(f"{timeframe}: non-zero seconds in {path}")
    if timeframe == "m15" and not time.dt.minute.mod(15).eq(0).all():
        raise ValueError(f"m15 timestamps are not aligned to 15-minute bar opens: {path}")
    if timeframe in {"h1", "h4", "d1"} and not time.dt.minute.eq(0).all():
        raise ValueError(f"{timeframe} timestamps are not aligned to hourly bar opens: {path}")
    if timeframe == "h4" and not time.dt.hour.mod(4).eq(0).all():
        raise ValueError(f"h4 timestamps are not aligned to four-hour bar opens: {path}")
    if timeframe == "d1" and not time.dt.hour.eq(0).all():
        raise ValueError(f"d1 timestamps are not aligned to daily bar opens: {path}")


def read_stable_live_frames(paths: dict[str, Path]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    before = {timeframe: sha256_file(path) for timeframe, path in paths.items()}
    frames: dict[str, pd.DataFrame] = {
        "m1": feature_engine.read_raw_csv(paths["m1"], columns=["time", "open", "spread"]),
        "m15": feature_engine.read_raw_csv(paths["m15"]),
        "h1": feature_engine.read_raw_csv(paths["h1"]),
        "h4": feature_engine.read_raw_csv(paths["h4"]),
        "d1": feature_engine.read_raw_csv(paths["d1"]),
    }
    for timeframe, frame in frames.items():
        validate_time_alignment(frame, timeframe, paths[timeframe])
    after = {timeframe: sha256_file(path) for timeframe, path in paths.items()}
    changed = [timeframe for timeframe in TIMEFRAMES if before[timeframe] != after[timeframe]]
    if changed:
        raise RuntimeError(f"Live source changed while being read; retry a later stable snapshot: {changed}")
    return frames, before


def build_live_features(
    frames: dict[str, pd.DataFrame],
    feature_contract: dict[str, Any],
) -> feature_engine.BuildResult:
    result = feature_engine.build_dataset_from_frames(
        m1=frames["m1"],
        m15=frames["m15"],
        h1=frames["h1"],
        h4=frames["h4"],
        d1=frames["d1"],
        profiles=feature_contract["timeframe_profiles"],
    )
    if result.model_feature_columns != feature_contract["model_feature_columns"]:
        raise ValueError("Live generated model-feature columns differ from the frozen feature contract")
    features = result.features
    if len(features):
        if not (features["m15_source_bar_close_time"] == features["decision_time"]).all():
            raise AssertionError("M15 decision-time contract failure")
        for timeframe in ("h1", "h4", "d1"):
            if not (features[f"{timeframe}_source_bar_close_time"] <= features["decision_time"]).all():
                raise AssertionError(f"Future {timeframe} bar joined into live features")
        if not np.isfinite(features[result.model_feature_columns].to_numpy(dtype=float)).all():
            raise AssertionError("Nonfinite live model feature")
    return result


def main() -> int:
    args = build_parser().parse_args()
    explicit = {timeframe: getattr(args, timeframe) for timeframe in TIMEFRAMES}
    paths = validate_explicit_paths(explicit)

    feature_contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    adapter_contract = json.loads(args.adapter_contract.read_text(encoding="utf-8"))
    frames, source_hashes = read_stable_live_frames(paths)
    result = build_live_features(frames, feature_contract)

    snapshot_end = pd.Timestamp(adapter_contract["historical_snapshot_last_decision"])
    all_features = result.features.copy()
    prospective = all_features.loc[all_features["decision_time"] > snapshot_end].copy()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_path = args.output_dir / "mlr1_live_features_all_available_v1.csv.gz"
    prospective_path = args.output_dir / "mlr1_prospective_features_v1.csv.gz"
    manifest_path = args.output_dir / "mlr1_live_feature_manifest_v1.json"
    deterministic_csv_gzip(all_features, all_path)
    deterministic_csv_gzip(prospective, prospective_path)

    source_manifest = {}
    for timeframe in TIMEFRAMES:
        frame = frames[timeframe]
        source_manifest[timeframe] = {
            "resolved_path": str(paths[timeframe]),
            "sha256": source_hashes[timeframe],
            "rows": int(len(frame)),
            "first_bar_open": None if frame.empty else str(frame["time"].iloc[0]),
            "last_bar_open": None if frame.empty else str(frame["time"].iloc[-1]),
            "latest_row_closed_by_csv_contract": True,
        }

    manifest = {
        "system_id": "GML1-MLR1",
        "stage": "PROSPECTIVE_INFRASTRUCTURE",
        "version": "v1",
        "status": "LIVE_FEATURE_SNAPSHOT_BUILT_AUDIT_ONLY",
        "source_role": "FUTURE_SHADOW_AND_LIVE_CLOSED_BAR_INPUT_ONLY",
        "source_root": str(next(iter(paths.values())).parent),
        "sources": source_manifest,
        "feature_contract_sha256": sha256_file(args.feature_contract),
        "adapter_contract_sha256": sha256_file(args.adapter_contract),
        "historical_snapshot_last_decision": str(snapshot_end),
        "rejection_summary": result.rejection_summary,
        "all_available": {
            "path": str(all_path),
            "sha256": sha256_file(all_path),
            "rows": int(len(all_features)),
            "first_decision": None if all_features.empty else str(all_features["decision_time"].iloc[0]),
            "last_decision": None if all_features.empty else str(all_features["decision_time"].iloc[-1]),
        },
        "prospective": {
            "rule": "decision_time > historical_snapshot_last_decision",
            "path": str(prospective_path),
            "sha256": sha256_file(prospective_path),
            "rows": int(len(prospective)),
            "first_decision": None if prospective.empty else str(prospective["decision_time"].iloc[0]),
            "last_decision": None if prospective.empty else str(prospective["decision_time"].iloc[-1]),
        },
        "controls": {
            "audit_only": True,
            "historical_bridge_used": False,
            "cross_source_concatenation": False,
            "model_loaded": False,
            "prediction_generated": False,
            "shadow_ready": False,
            "live_ready": False,
            "final_signal": False,
            "mt5_order": False,
            "discord": False,
        },
    }
    write_json(manifest_path, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
