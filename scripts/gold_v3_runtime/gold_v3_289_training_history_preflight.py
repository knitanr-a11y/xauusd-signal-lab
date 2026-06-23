#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from gold_v3_289_feature_core import GOLD_FILES, read_candles

FIT_START = pd.Timestamp("2024-01-01 00:00:00")
FIT_END = pd.Timestamp("2026-01-01 00:00:00")
FIXTURE_END = pd.Timestamp("2026-06-19 12:00:00")
EARLIEST_ALLOWED = pd.Timestamp("2024-01-07 00:00:00")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--report", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    report_path = (
        Path(args.report).expanduser().resolve()
        if args.report
        else candle_dir / "stage289_training_history_preflight.json"
    )

    checks: dict[str, object] = {}
    frames: dict[str, pd.DataFrame] = {}
    blockers: list[str] = []

    for timeframe, filename in GOLD_FILES.items():
        path = candle_dir / filename
        if not path.exists():
            blockers.append(f"MISSING_{timeframe}:{path}")
            continue
        try:
            frame = read_candles(
                path,
                None,
                timeframe=timeframe,
                require_spread=True,
            )
        except Exception as exc:
            blockers.append(f"READ_FAILED_{timeframe}:{exc!r}")
            continue
        frames[timeframe] = frame
        checks[timeframe] = {
            "path": str(path),
            "rows": int(len(frame)),
            "first": str(frame.time.min()),
            "last": str(frame.time.max()),
        }
        if pd.Timestamp(frame.time.min()) > EARLIEST_ALLOWED:
            blockers.append(
                f"{timeframe}_START_TOO_LATE:{frame.time.min()} > {EARLIEST_ALLOWED}"
            )
        if pd.Timestamp(frame.time.max()) < FIXTURE_END.floor(
            {"M1":"min","M5":"5min","M15":"15min","H1":"h","H4":"4h","D1":"D"}[timeframe]
        ):
            blockers.append(
                f"{timeframe}_END_TOO_EARLY:{frame.time.max()} < {FIXTURE_END}"
            )

    if "M1" in frames and "H1" in frames:
        m1_times = frames["M1"].time.to_numpy("datetime64[ns]")
        h1 = frames["H1"]
        decisions = h1[(h1.time >= FIT_START) & (h1.time < FIT_END)].time
        valid = 0
        for value in decisions:
            start = np.searchsorted(m1_times, np.datetime64(value), side="left")
            end = np.searchsorted(
                m1_times,
                np.datetime64(value + pd.Timedelta(minutes=240)),
                side="left",
            )
            if (
                start < len(m1_times)
                and m1_times[start] == np.datetime64(value)
                and end - start >= 180
            ):
                valid += 1
        ratio = valid / max(int(len(decisions)), 1)
        checks["m1_h1_label_windows"] = {
            "h1_decisions_2024_2025": int(len(decisions)),
            "valid_m1_240m_windows": int(valid),
            "coverage_ratio": float(ratio),
        }
        if valid == 0 or ratio < 0.50:
            blockers.append(
                f"M1_LABEL_WINDOW_COVERAGE_TOO_LOW:{valid}/{len(decisions)}"
            )

    status = "PASS" if not blockers else "BLOCKED_TRAINING_HISTORY_INCOMPLETE"
    report = {
        "status": status,
        "candle_dir": str(candle_dir),
        "fit_start": str(FIT_START),
        "fit_end_exclusive": str(FIT_END),
        "fixture_required_through": str(FIXTURE_END),
        "checks": checks,
        "blockers": blockers,
        "closed_csv_contract": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
