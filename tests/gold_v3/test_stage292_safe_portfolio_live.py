from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd

RUNTIME = Path(__file__).resolve().parents[2] / "scripts" / "gold_v3_runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from gold_v3_292_live_candidates import find_live_trigger
from gold_v3_292_portfolio_state import evaluate_candidates, state_at


def bootstrap():
    return {
        "asof":pd.Timestamp("2026-06-19 15:51"),
        "equity":965.6008808154019,
        "peak":985.2064859116765,
        "last_candidate_entry_dt":pd.Timestamp("2026-06-19 08:30"),
        "last_candidate_loss_exit_dt":pd.Timestamp("2026-04-29 21:45"),
        "last_base_exit_dt":pd.Timestamp("2026-06-19 15:51"),
        "last_base_pnl":-19.605605096274644,
    }


def candidate(source, entry):
    return pd.DataFrame([{
        "candidate_id":f"{source}|{entry}","source":source,
        "priority":{"BASE":0,"STAGE280":10,"STAGE281":20,"STAGE286":60}[source],
        "decision_dt":pd.Timestamp(entry),"trigger_dt":pd.Timestamp(entry),
        "entry_dt":pd.Timestamp(entry),"reference_price":3000.0,
        "direction":"SHORT" if source=="STAGE286" else "LONG",
        "direction_num":-1 if source=="STAGE286" else 1,
        "atr_entry":10.0,"tp_atr":2.25,"sl_atr":1.25,
        "tp_distance":22.5,"sl_distance":12.5,
        "max_holding_minutes":480,"candidate_contract":"TEST","candidate_key":"",
    }])


def test_cutover_dd_blocks_stage286_but_not_stage280():
    short_decisions, _ = evaluate_candidates(candidate("STAGE286","2026-06-23 08:00"), pd.DataFrame(), bootstrap())
    long_decisions, _ = evaluate_candidates(candidate("STAGE280","2026-06-23 08:00"), pd.DataFrame(), bootstrap())
    assert not bool(short_decisions.iloc[0].final_signal)
    assert "SHORT_DD_ABOVE_10" in short_decisions.iloc[0].reject_reasons
    assert bool(long_decisions.iloc[0].final_signal)


def test_stage281_requires_recent_resolved_base_loss():
    decisions, _ = evaluate_candidates(candidate("STAGE281","2026-06-23 08:00"), pd.DataFrame(), bootstrap())
    assert not bool(decisions.iloc[0].final_signal)
    assert "NOT_AFTER_RESOLVED_BASE_LOSS_WITHIN_72H" in decisions.iloc[0].reject_reasons


def test_live_trigger_uses_trigger_close_without_future_open():
    times = pd.date_range("2026-06-23 10:00", periods=8, freq="5min")
    frame = pd.DataFrame({
        "time":times,"open":[100]*8,"high":[101,101,101,101,101,101,102,104],
        "low":[99]*8,"close":[100,100,100,100,100,100,101,104],
        "body_signed":[0,0,0,0,0,0,0.2,0.8],"ema20":[100]*8,
    })
    trigger, entry, price = find_live_trigger(frame, times[6], 1, "BRK6", 60)
    assert trigger == times[7]
    assert entry == times[7] + pd.Timedelta(minutes=5)
    assert price == 104


def test_base_rollover_is_blocked():
    decisions, _ = evaluate_candidates(candidate("BASE","2026-06-23 23:30"), pd.DataFrame(), bootstrap())
    assert not bool(decisions.iloc[0].final_signal)
    assert "BASE_HOLD_OVERLAPS_SERVER_00_01" in decisions.iloc[0].reject_reasons
