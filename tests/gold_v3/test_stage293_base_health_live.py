from __future__ import annotations
import sys
from collections import defaultdict, deque
from pathlib import Path
import pandas as pd

RUNTIME = Path(__file__).resolve().parents[2] / "scripts" / "gold_v3_runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from gold_v3_293_base_health_live import (
    WINDOW, add_live_resolved_base, gate, load_cutover_histories,
)


def test_cutover_history_uses_closed_results_as_snapshot(tmp_path):
    root = tmp_path / "FX_OUTPUTS" / "gold_v3" / "67_health_gate_rehydration_audit_only"
    root.mkdir(parents=True)
    rows = []
    for index in range(35):
        rows.append({
            "event_time": pd.Timestamp("2026-01-01") + pd.Timedelta(hours=index),
            "candidate_key": "A|B|C|D|E|10|5|8|24",
            "result_usd_after_close": 1.0 if index % 3 else -0.5,
        })
    pd.DataFrame(rows).to_csv(root / "gold_v3_67_health_gate_event_ledger.csv", index=False)
    histories, meta = load_cutover_histories(tmp_path)
    history = list(histories["A|B|C|D|E|10|5|8|24"])
    assert len(history) == WINDOW
    assert history == [row["result_usd_after_close"] for row in rows[-WINDOW:]]
    assert meta["seed_rows"] == 35


def test_live_base_history_uses_only_actual_closed_exit_by_asof():
    histories = defaultdict(lambda: deque(maxlen=WINDOW))
    histories["BASE_KEY"].extend([1.0] * 20)
    ledger = pd.DataFrame([
        {
            "candidate_id":"old","candidate_key":"BASE_KEY","source":"BASE",
            "status":"CLOSED","entry_dt":"2026-06-20 08:00","exit_dt":"2026-06-20 10:00","pnl":-2.0,
        },
        {
            "candidate_id":"future","candidate_key":"BASE_KEY","source":"BASE",
            "status":"CLOSED","entry_dt":"2026-06-23 08:00","exit_dt":"2026-06-23 12:00","pnl":-20.0,
        },
    ])
    bootstrap = {"asof":pd.Timestamp("2026-06-19 15:51")}
    applied = add_live_resolved_base(histories, ledger, bootstrap, pd.Timestamp("2026-06-23 09:00"))
    assert applied == [{
        "candidate_id":"old","candidate_key":"BASE_KEY",
        "exit_dt":pd.Timestamp("2026-06-20 10:00"),"pnl":-2.0,
    }]
    assert list(histories["BASE_KEY"])[-1] == -2.0
    assert -20.0 not in histories["BASE_KEY"]


def test_health_gate_updates_after_live_loss_streak():
    passed, reason, _, streak = gate([1.0] * 20 + [-1.0, -1.0, -1.0])
    assert not passed
    assert reason == "LOSS_STREAK_LIMIT"
    assert streak == 3
