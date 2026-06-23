#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict, deque
from pathlib import Path
import math
import numpy as np
import pandas as pd

from gold_v3_67_health_gate_rehydration_audit import (
    KEY_COLS, build_candidate_key, normalize_candidate_key_string,
)

WINDOW = 30
MIN_HISTORY = 20
PF_THRESHOLD = 1.10
LOSS_STREAK_LT = 3


def profit_factor(values) -> float:
    data = np.asarray(list(values), dtype=float)
    gain = float(data[data > 0].sum())
    loss = float(-data[data < 0].sum())
    if loss > 0:
        return gain / loss
    return math.inf if gain > 0 else 0.0


def loss_streak(values) -> int:
    count = 0
    for value in reversed(list(values)):
        if float(value) < 0:
            count += 1
        else:
            break
    return count


def gate(values) -> tuple[bool, str, float, int]:
    history = list(values)
    if len(history) < MIN_HISTORY:
        return True, "INSUFFICIENT_HISTORY", np.nan, 0
    pf = profit_factor(history)
    streak = loss_streak(history)
    reasons = []
    if pf < PF_THRESHOLD:
        reasons.append("PF_BELOW_THRESHOLD")
    if streak >= LOSS_STREAK_LT:
        reasons.append("LOSS_STREAK_LIMIT")
    return not reasons, "+".join(reasons) if reasons else "PASS", pf, streak


def _event_ledger_path(candle_dir: Path) -> Path:
    return (
        Path(candle_dir)
        / "FX_OUTPUTS"
        / "gold_v3"
        / "67_health_gate_rehydration_audit_only"
        / "gold_v3_67_health_gate_event_ledger.csv"
    )


def load_cutover_histories(candle_dir: Path):
    path = _event_ledger_path(candle_dir)
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Stage67 event ledger missing: {path}")
    data = pd.read_csv(path, encoding="utf-8-sig")
    required = {"candidate_key", "result_usd_after_close"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Stage67 event ledger missing columns: {missing}")
    data["candidate_key"] = data.candidate_key.map(normalize_candidate_key_string)
    data["result_usd_after_close"] = pd.to_numeric(
        data.result_usd_after_close, errors="coerce"
    )
    data = data.dropna(subset=["candidate_key", "result_usd_after_close"]).copy()
    if "event_time" in data.columns:
        data["event_time"] = pd.to_datetime(data.event_time, errors="coerce")
        data = data.sort_values(["event_time", "candidate_key"], kind="mergesort")
    histories = defaultdict(lambda: deque(maxlen=WINDOW))
    counts = defaultdict(int)
    for row in data.itertuples(index=False):
        key = str(row.candidate_key)
        histories[key].append(float(row.result_usd_after_close))
        counts[key] += 1
    return histories, {
        "seed_path": str(path),
        "seed_rows": int(len(data)),
        "seed_candidate_count": int(len(histories)),
        "seed_contract": (
            "Stage67 closed outcomes are used only as the cutover history snapshot; "
            "their event_time is not treated as a live exit time"
        ),
        "observed_counts": dict(counts),
    }


def add_live_resolved_base(histories, ledger: pd.DataFrame, bootstrap: dict, asof):
    applied = []
    if ledger.empty:
        return applied
    exits = pd.to_datetime(ledger.get("exit_dt"), errors="coerce")
    closed = ledger[
        ledger.source.astype(str).eq("BASE")
        & ledger.status.astype(str).eq("CLOSED")
        & exits.gt(pd.Timestamp(bootstrap["asof"]))
        & exits.le(pd.Timestamp(asof))
    ].copy()
    if closed.empty:
        return applied
    closed["exit_dt"] = pd.to_datetime(closed.exit_dt, errors="coerce")
    closed["pnl"] = pd.to_numeric(closed.pnl, errors="coerce")
    closed = closed.dropna(subset=["candidate_key", "exit_dt", "pnl"])
    closed = closed.sort_values(["exit_dt", "entry_dt", "candidate_id"], kind="mergesort")
    for row in closed.itertuples(index=False):
        key = normalize_candidate_key_string(row.candidate_key)
        histories[key].append(float(row.pnl))
        applied.append({
            "candidate_id": row.candidate_id,
            "candidate_key": key,
            "exit_dt": row.exit_dt,
            "pnl": float(row.pnl),
        })
    return applied


def load_latest_stage69(candle_dir: Path) -> tuple[pd.DataFrame, dict]:
    root = (
        Path(candle_dir)
        / "FX_OUTPUTS"
        / "gold_v3"
        / "69_live_csv_condition_detector_audit_only"
    )
    summary_path = root / "gold_v3_69_live_csv_condition_detector_summary.json"
    candidate_path = root / "gold_v3_69_latest_closed_condition_candidates.csv"
    if not summary_path.exists() or not candidate_path.exists():
        raise FileNotFoundError("Stage69 latest condition output is missing")
    import json
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY"
    if summary.get("status") != expected:
        raise ValueError(f"Stage69 not ready: {summary.get('status')}")
    if candidate_path.stat().st_size == 0:
        return pd.DataFrame(), summary
    candidates = pd.read_csv(candidate_path, encoding="utf-8-sig")
    if candidates.empty:
        return candidates, summary
    if "candidate_key" not in candidates.columns:
        missing = sorted(set(KEY_COLS) - set(candidates.columns))
        if missing:
            raise ValueError(f"Stage69 candidate key columns missing: {missing}")
        candidates["candidate_key"] = build_candidate_key(candidates)
    candidates["candidate_key"] = candidates.candidate_key.map(
        normalize_candidate_key_string
    )
    return candidates, summary


def evaluate_latest_base(candle_dir: Path, ledger: pd.DataFrame, bootstrap: dict):
    candidates, summary = load_latest_stage69(candle_dir)
    histories, metadata = load_cutover_histories(candle_dir)
    latest_time = pd.Timestamp(summary["latest_closed_m15_time"])
    entry_time = latest_time + pd.Timedelta(minutes=15)
    live_applied = add_live_resolved_base(histories, ledger, bootstrap, entry_time)
    rows = []
    if not candidates.empty:
        candidates = candidates.sort_values(
            ["priority", "candidate_label", "candidate_key", "condition_id"],
            kind="mergesort",
        )
        for row in candidates.itertuples(index=False):
            key = normalize_candidate_key_string(row.candidate_key)
            history = list(histories[key])
            passed, reason, pf, streak = gate(history)
            record = row._asdict()
            record.update({
                "candidate_key": key,
                "planned_entry_dt": entry_time,
                "health_history_count": len(history),
                "health_rolling_pf": pf,
                "health_loss_streak": streak,
                "health_gate_pass": passed,
                "health_gate_reason": reason,
            })
            rows.append(record)
    screen = pd.DataFrame(rows)
    eligible = screen[screen.health_gate_pass.astype(bool)].head(1) if len(screen) else pd.DataFrame()
    metadata.update({
        "latest_closed_m15_time": str(latest_time),
        "planned_entry_dt": str(entry_time),
        "latest_condition_rows": int(len(candidates)),
        "eligible_rows": int(screen.health_gate_pass.astype(bool).sum()) if len(screen) else 0,
        "live_resolved_base_events_applied": int(len(live_applied)),
        "live_resolved_base_events": live_applied,
    })
    return eligible, screen, metadata
