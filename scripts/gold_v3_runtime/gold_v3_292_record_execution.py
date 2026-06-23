#!/usr/bin/env python3
from __future__ import annotations
import argparse, os
from pathlib import Path
import numpy as np
import pandas as pd

from gold_v3_289_live_features import GOLD_FILES, read_candles
from gold_v3_292_portfolio_state import UPDATE_COLUMNS, load_ledger, load_updates


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--event-type", required=True, choices=["FILLED","CANCELLED","CLOSED"])
    parser.add_argument("--event-dt", default="")
    parser.add_argument("--price", type=float, default=np.nan)
    parser.add_argument("--pnl", type=float, default=np.nan)
    parser.add_argument("--reason", default="")
    return parser.parse_args()


def atomic_csv(path: Path, frame: pd.DataFrame):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp, index=False, encoding="utf-8-sig")
    os.replace(temp, path)


def main():
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output_dir).expanduser().resolve() if args.output_dir else candle_dir / "FX_OUTPUTS" / "gold_v3" / "292_safe_portfolio_live"
    ledger_path = output / "gold_v3_292_live_signal_ledger.csv"
    updates_path = output / "gold_v3_292_execution_updates.csv"
    ledger = load_ledger(ledger_path)
    if ledger.empty:
        raise RuntimeError("Stage292 signal ledger is empty")
    required_status = "PENDING_FILL" if args.event_type in {"FILLED","CANCELLED"} else "OPEN"
    eligible = ledger[ledger.status.astype(str).eq(required_status)].copy()
    if args.candidate_id:
        eligible = eligible[eligible.candidate_id.astype(str).eq(args.candidate_id)]
    if eligible.empty:
        raise RuntimeError(f"no {required_status} candidate matches")
    selected = eligible.sort_values("entry_dt").iloc[-1]
    if args.event_type == "FILLED" and not np.isfinite(args.price):
        raise ValueError("FILLED requires --price")
    if args.event_type == "CLOSED" and (not np.isfinite(args.price) or not np.isfinite(args.pnl)):
        raise ValueError("CLOSED requires --price and --pnl")
    if args.event_dt:
        event_dt = pd.Timestamp(args.event_dt)
    else:
        m1 = read_candles(candle_dir / GOLD_FILES["M1"], 4, timeframe="M1", require_spread=True)
        event_dt = pd.Timestamp(m1.time.max()) + pd.Timedelta(minutes=1)
    updates = load_updates(updates_path)
    row = pd.DataFrame([{
        "candidate_id":str(selected.candidate_id),
        "event_type":args.event_type,
        "event_dt":event_dt,
        "price":args.price,
        "pnl":args.pnl,
        "reason":args.reason,
    }], columns=UPDATE_COLUMNS)
    combined = pd.concat([updates, row], ignore_index=True)
    combined = combined.drop_duplicates(["candidate_id","event_type","event_dt"], keep="last")
    atomic_csv(updates_path, combined)
    print(f"recorded {args.event_type}: {selected.candidate_id} at {event_dt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
