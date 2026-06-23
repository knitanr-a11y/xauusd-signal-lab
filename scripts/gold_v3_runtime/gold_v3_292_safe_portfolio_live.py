#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from gold_v3_289_artifacts import validate_model_bundle
from gold_v3_289_candidates import model_dir
from gold_v3_289_live_features import GOLD_FILES, read_candles
from gold_v3_292_live_candidates import detect_all_candidates
from gold_v3_292_portfolio_state import (
    UPDATE_COLUMNS, apply_updates, evaluate_candidates,
    load_bootstrap, load_ledger, load_updates, state_at,
)

READY = "GOLD_V3_292_SAFE_PORTFOLIO_LIVE_READY"
NO_SIGNAL = "GOLD_V3_292_SAFE_PORTFOLIO_LIVE_NO_SIGNAL"
BLOCKED = "GOLD_V3_292_SAFE_PORTFOLIO_LIVE_BLOCKED"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_csv(path, frame):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp, index=False, encoding="utf-8-sig")
    os.replace(temp, path)


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--lookback-hours", type=int, default=96)
    parser.add_argument("--max-signal-lag-seconds", type=int, default=180)
    return parser.parse_args()


def main():
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output_dir).expanduser().resolve() if args.output_dir else candle_dir / "FX_OUTPUTS" / "gold_v3" / "292_safe_portfolio_live"
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "gold_v3_292_summary.json"
    final_path = output / "gold_v3_292_final_live_signal.csv"
    try:
        validate_model_bundle(model_dir())
        bootstrap_path = Path(__file__).resolve().parents[2] / "docs" / "gold_v3" / "gold_v3_stage292_safe_portfolio_bootstrap.json"
        bootstrap = load_bootstrap(bootstrap_path)
        for name in list(GOLD_FILES.values()) + ["us500cashsharp_m15.csv", "us100cashsharp_m15.csv"]:
            if not (candle_dir / name).exists():
                raise FileNotFoundError(name)
        stage69 = candle_dir / "FX_OUTPUTS" / "gold_v3" / "69_live_csv_condition_detector_audit_only" / "gold_v3_69_latest_closed_condition_candidates.csv"
        stage67 = candle_dir / "FX_OUTPUTS" / "gold_v3" / "67_health_gate_rehydration_audit_only" / "gold_v3_67_health_gate_event_ledger.csv"
        if not stage69.exists():
            raise FileNotFoundError("Stage69 latest conditions are missing")
        if not stage67.exists() or stage67.stat().st_size == 0:
            raise FileNotFoundError("Stage67 closed-outcome history is missing")
    except Exception as exc:
        write_csv(final_path, pd.DataFrame())
        write_json(summary_path, {"status":BLOCKED, "created_at_utc":utc_now(), "error":repr(exc)})
        return 2

    ledger_path = output / "gold_v3_292_live_signal_ledger.csv"
    updates_path = output / "gold_v3_292_execution_updates.csv"
    decisions_path = output / "gold_v3_292_decision_ledger.csv"
    runtime_path = output / "gold_v3_292_runtime_state.json"
    if not updates_path.exists():
        write_csv(updates_path, pd.DataFrame(columns=UPDATE_COLUMNS))

    m1 = read_candles(candle_dir / GOLD_FILES["M1"], 10, timeframe="M1", require_spread=True)
    m5 = read_candles(candle_dir / GOLD_FILES["M5"], 10, timeframe="M5", require_spread=True)
    m15 = read_candles(candle_dir / GOLD_FILES["M15"], 10, timeframe="M15", require_spread=True)
    latest_m1_close = pd.Timestamp(m1.time.max()) + pd.Timedelta(minutes=1)
    latest_m5_close = pd.Timestamp(m5.time.max()) + pd.Timedelta(minutes=5)
    latest_m15_close = pd.Timestamp(m15.time.max()) + pd.Timedelta(minutes=15)

    ledger = load_ledger(ledger_path)
    try:
        ledger, applied = apply_updates(ledger, load_updates(updates_path), latest_m1_close)
    except Exception as exc:
        write_json(summary_path, {"status":BLOCKED, "created_at_utc":utc_now(), "error":repr(exc)})
        return 2
    write_csv(ledger_path, ledger)
    write_csv(output / "gold_v3_292_applied_updates_latest.csv", applied)

    if runtime_path.exists():
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        first_run = False
    else:
        runtime = {
            "initialized_at_utc":utc_now(),
            "last_processed_entry_dt":str(max(latest_m5_close, latest_m15_close)),
        }
        write_json(runtime_path, runtime)
        first_run = True
    watermark = pd.to_datetime(runtime.get("last_processed_entry_dt"), errors="coerce")

    if first_run:
        write_csv(final_path, pd.DataFrame())
        write_json(summary_path, {
            "status":NO_SIGNAL, "reason":"INITIAL_WATERMARK_SET", "created_at_utc":utc_now(),
            "state":state_at(latest_m1_close, ledger, bootstrap),
            "final_signal_enabled":True, "mt5_order_enabled":False, "discord_enabled":False,
        })
        return 0

    try:
        candidates, meta, base_screen = detect_all_candidates(
            candle_dir, ledger, bootstrap, args.lookback_hours
        )
        write_csv(output / "gold_v3_292_latest_base_health_screen.csv", base_screen)
    except Exception as exc:
        write_csv(final_path, pd.DataFrame())
        write_json(summary_path, {"status":BLOCKED, "created_at_utc":utc_now(), "error":repr(exc)})
        return 2
    if len(candidates):
        candidates = candidates[candidates.entry_dt > watermark].copy()
        candidates["signal_lag_seconds"] = (latest_m1_close - candidates.entry_dt).dt.total_seconds()
        candidates = candidates[candidates.signal_lag_seconds.between(0, args.max_signal_lag_seconds)].copy()

    decisions, ledger = evaluate_candidates(candidates, ledger, bootstrap)
    old = pd.read_csv(decisions_path, encoding="utf-8-sig") if decisions_path.exists() and decisions_path.stat().st_size else pd.DataFrame()
    all_decisions = pd.concat([old, decisions], ignore_index=True, sort=False) if len(decisions) else old
    if len(all_decisions) and "candidate_id" in all_decisions:
        all_decisions = all_decisions.drop_duplicates("candidate_id", keep="last")
    write_csv(decisions_path, all_decisions)
    write_csv(ledger_path, ledger)
    final = decisions[decisions.final_signal.astype(bool)].tail(1) if len(decisions) and "final_signal" in decisions else pd.DataFrame()
    write_csv(final_path, final)

    runtime["last_processed_entry_dt"] = str(max(latest_m5_close, latest_m15_close))
    runtime["updated_at_utc"] = utc_now()
    write_json(runtime_path, runtime)
    current_state = state_at(latest_m1_close, ledger, bootstrap)
    write_json(summary_path, {
        "status":READY if len(final) else NO_SIGNAL,
        "created_at_utc":utc_now(),
        "latest_m1_close":latest_m1_close,
        "latest_m5_close":latest_m5_close,
        "latest_m15_close":latest_m15_close,
        "new_candidate_count":int(len(candidates)),
        "new_decision_count":int(len(decisions)),
        "final_signal_count":int(len(final)),
        "state":current_state,
        "candidate_meta":meta,
        "base_health_mode":"CUTOVER_CLOSED_HISTORY_PLUS_ACTUAL_LIVE_CLOSED",
        "final_signal_enabled":True,
        "actual_fill_close_updates_required":True,
        "mt5_order_enabled":False,
        "discord_enabled":False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
