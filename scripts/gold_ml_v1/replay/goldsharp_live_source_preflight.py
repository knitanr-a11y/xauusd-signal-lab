from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"
]
TIMEFRAMES = ["m1", "m15", "h1", "h4", "d1"]
HISTORICAL_NAMES = {tf: f"gold_v3_2023_2026_{tf}.csv" for tf in TIMEFRAMES}
LIVE_NAMES = {tf: f"goldsharp_{tf}.csv" for tf in TIMEFRAMES}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv_auto(path: Path) -> pd.DataFrame:
    first = pd.read_csv(path)
    if len(first.columns) == 1 and ";" in str(first.columns[0]):
        return pd.read_csv(path, sep=";")
    return first


def validate_frame(path: Path, source: str) -> tuple[pd.DataFrame, list[str]]:
    errors: list[str] = []
    df = read_csv_auto(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return df, [f"missing columns: {missing}"]
    df = df[REQUIRED_COLUMNS].copy()
    try:
        df["time"] = pd.to_datetime(df["time"])
    except Exception as exc:  # pragma: no cover - surfaced to report
        return df, [f"time parse failed: {exc}"]
    if df["time"].duplicated().any():
        errors.append(f"duplicate times: {int(df['time'].duplicated().sum())}")
    if not df["time"].is_monotonic_increasing:
        errors.append("time not ascending")
    invalid_ohlc = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    if invalid_ohlc.any():
        errors.append(f"invalid OHLC rows: {int(invalid_ohlc.sum())}")
    if (pd.to_numeric(df["spread"], errors="coerce") < 0).any():
        errors.append("negative spread found")
    df["source"] = source
    return df, errors


def locate(root: Path, filename: str) -> Path | None:
    direct = root / filename
    if direct.exists():
        return direct
    target = filename.lower()
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == target:
            return path
    return None


def partition_live_rows(historical: pd.DataFrame, live: pd.DataFrame) -> dict[str, Any]:
    historical_max = historical["time"].max()
    overlap = live[live["time"] <= historical_max]
    operational = live[live["time"] > historical_max]
    return {
        "historical_max_time": str(historical_max),
        "live_first_time": str(live["time"].min()) if len(live) else None,
        "live_last_time": str(live["time"].max()) if len(live) else None,
        "live_rows_total": int(len(live)),
        "live_overlap_or_backfill_rows": int(len(overlap)),
        "live_operational_rows_after_historical_max": int(len(operational)),
        "operational_first_time": str(operational["time"].min()) if len(operational) else None,
        "operational_last_time": str(operational["time"].max()) if len(operational) else None,
        "historical_rows_eligible_for_new_live_signal": 0,
        "live_rows_eligible_for_new_live_signal": int(len(operational)),
    }


def run(historical_dir: Path, live_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "contract": {
            "historical_replay_source": "gold_v3_2023_2026 only",
            "live_decision_source": "goldsharp only",
            "historical_live_use": "historical is warmup/continuity only during live mode",
            "latest_row_contract": "closed",
            "time_basis": "MT5 server naive time",
        },
        "timeframes": {},
    }
    failed = False
    for timeframe in TIMEFRAMES:
        historical_path = locate(historical_dir, HISTORICAL_NAMES[timeframe])
        live_path = locate(live_dir, LIVE_NAMES[timeframe])
        item: dict[str, Any] = {
            "historical_filename": HISTORICAL_NAMES[timeframe],
            "live_filename": LIVE_NAMES[timeframe],
        }
        if historical_path is None:
            item["historical_error"] = "not found"
            failed = True
        if live_path is None:
            item["live_error"] = "not found"
            failed = True
        if historical_path is not None and live_path is not None:
            historical, historical_errors = validate_frame(historical_path, "historical")
            live, live_errors = validate_frame(live_path, "goldsharp")
            item.update({
                "historical_path": str(historical_path),
                "historical_sha256": sha256_file(historical_path),
                "historical_rows": int(len(historical)),
                "historical_errors": historical_errors,
                "live_path": str(live_path),
                "live_sha256": sha256_file(live_path),
                "live_rows": int(len(live)),
                "live_errors": live_errors,
            })
            if historical_errors or live_errors:
                failed = True
            elif len(historical) == 0 or len(live) == 0:
                item["partition_error"] = "historical or live file is empty"
                failed = True
            else:
                partition = partition_live_rows(historical, live)
                item["partition"] = partition
                if partition["live_operational_rows_after_historical_max"] == 0:
                    item["warning"] = "no goldsharp rows strictly after historical maximum"
        report["timeframes"][timeframe.upper()] = item

    report["summary"] = {
        "status": "FAIL" if failed else "PASS",
        "historical_replay_must_ignore_goldsharp": True,
        "live_new_signal_source": "goldsharp only",
        "historical_backlog_signal_forbidden": True,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    }
    (output_dir / "goldsharp_live_source_preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rows = []
    for tf, item in report["timeframes"].items():
        partition = item.get("partition", {})
        rows.append({
            "timeframe": tf,
            "historical_rows": item.get("historical_rows"),
            "live_rows": item.get("live_rows"),
            "live_overlap_or_backfill_rows": partition.get("live_overlap_or_backfill_rows"),
            "live_operational_rows_after_historical_max": partition.get("live_operational_rows_after_historical_max"),
            "historical_errors": "; ".join(item.get("historical_errors", [])),
            "live_errors": "; ".join(item.get("live_errors", [])),
            "warning": item.get("warning", ""),
        })
    pd.DataFrame(rows).to_csv(output_dir / "goldsharp_live_source_preflight.csv", index=False)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit historical versus goldsharp live source separation")
    parser.add_argument("--historical-dir", type=Path, required=True)
    parser.add_argument("--live-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/goldsharp_live_source_preflight"),
    )
    args = parser.parse_args()
    try:
        return run(args.historical_dir.resolve(), args.live_dir.resolve(), args.output_dir.resolve())
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "preflight_exception.txt").write_text(repr(exc), encoding="utf-8")
        print(f"PREFLIGHT FAILED: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
