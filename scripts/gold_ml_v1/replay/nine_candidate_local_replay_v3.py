from __future__ import annotations

import argparse
import importlib.util
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

V2_PATH = Path(__file__).with_name("nine_candidate_local_replay_v2.py")
SPEC = importlib.util.spec_from_file_location("gml1_batch023_v2", V2_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load replay v2 module: {V2_PATH}")
v2 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v2
SPEC.loader.exec_module(v2)

base = v2.base


def complete_horizon_mask_v3(
    decision_times: pd.Series,
    m1_times: set[pd.Timestamp],
    horizon_hours: int,
) -> pd.Series:
    """
    A decision is eligible when the exact M1 entry exists and the dataset extends
    beyond the requested wall-clock horizon. The exact final minute need not exist:
    weekends and broker maintenance gaps are valid and use the last available M1
    close inside the horizon.
    """
    if not m1_times:
        return pd.Series(False, index=decision_times.index)
    latest_m1_close = max(m1_times) + pd.Timedelta(minutes=1)
    horizon_end = decision_times + pd.Timedelta(hours=horizon_hours)
    return decision_times.isin(m1_times) & (horizon_end <= latest_m1_close)


def evaluate_trade_v3(
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
    spread_price = float(entry_bar["spread"] * base.POINT)
    entry_price = float(entry_bar["open"] + (spread_price if direction == "LONG" else 0.0))
    stop_distance = float(atr_at_decision)
    sl_price = entry_price - stop_distance if direction == "LONG" else entry_price + stop_distance
    tp_price = entry_price + stop_distance if direction == "LONG" else entry_price - stop_distance
    horizon_end = decision_close_time + pd.Timedelta(hours=horizon_hours)
    path = m1[
        (m1["bar_open_time"] >= decision_close_time)
        & (m1["bar_open_time"] < horizon_end)
    ]
    if path.empty:
        return None

    for _, bar in path.iterrows():
        if direction == "LONG":
            sl_hit = bar["low"] <= sl_price
            tp_hit = bar["high"] >= tp_price
        else:
            ask_low = bar["low"] + bar["spread"] * base.POINT
            ask_high = bar["high"] + bar["spread"] * base.POINT
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

    # Time exit uses the last actually available M1 bar within the wall-clock
    # horizon. This intentionally supports weekends and broker maintenance gaps.
    final_bar = path.iloc[-1]
    exit_price = float(
        final_bar["close"]
        if direction == "LONG"
        else final_bar["close"] + final_bar["spread"] * base.POINT
    )
    r_value = (
        (exit_price - entry_price) / stop_distance
        if direction == "LONG"
        else (entry_price - exit_price) / stop_distance
    )
    return {
        "entry_time": decision_close_time,
        "entry_price": entry_price,
        "exit_time": final_bar["bar_close_time"],
        "exit_price": exit_price,
        "r_value": float(r_value),
        "outcome": "TIME_POS" if r_value > 0 else ("TIME_NEG" if r_value < 0 else "TIME_ZERO"),
    }


# Patch only the two remaining evaluator-contract mismatches.
v2._complete_horizon_mask = complete_horizon_mask_v3
v2.base.evaluate_trade = evaluate_trade_v3


def main() -> int:
    parser = argparse.ArgumentParser(description="GOLD_ML_V1 Batch023 corrected historical replay v3")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--historical-dir", type=Path)
    parser.add_argument("--warmup-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=["registry-only", "raw", "auto"], default="auto")
    args = parser.parse_args()
    output_dir = args.output_dir or args.repo_root / "outputs/gold_ml_v1/batch023_historical_replay_v3"
    try:
        paths = base.resolve_repo_paths(args.repo_root)
        if args.mode == "registry-only":
            return base.registry_only(paths, output_dir)
        if args.historical_dir is None or args.warmup_dir is None:
            raise ValueError("--historical-dir and --warmup-dir are required for raw/auto mode")
        if args.mode == "auto":
            registry_code = base.registry_only(paths, output_dir / "registry")
            if registry_code != base.EXIT_OK:
                return registry_code
            return v2.historical_replay(
                paths,
                args.historical_dir.resolve(),
                args.warmup_dir.resolve(),
                output_dir / "raw",
            )
        return v2.historical_replay(
            paths,
            args.historical_dir.resolve(),
            args.warmup_dir.resolve(),
            output_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "input_error.txt").write_text(str(exc), encoding="utf-8")
        print(exc, file=sys.stderr)
        return base.EXIT_INPUT
    except Exception:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "unexpected_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        return base.EXIT_ENV


if __name__ == "__main__":
    sys.exit(main())
