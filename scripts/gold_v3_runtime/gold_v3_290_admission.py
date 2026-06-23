from __future__ import annotations
import pandas as pd
from gold_v3_290_state import state_at

PRIORITY={"BASE":0,"STAGE280":10,"STAGE281":20,"STAGE286":60}

def overlaps_rollover(entry,minutes):
    t=pd.Timestamp(entry); end=t+pd.Timedelta(minutes=int(minutes))
    while t<=end:
        if t.hour in {0,1}: return True
        t+=pd.Timedelta(minutes=1)
    return False

def reject_reasons(row,state,max_lag_seconds):
    t=pd.Timestamp(row.planned_entry_dt); reasons=[]
    lag=float(getattr(row,"intent_lag_seconds",0.0))
    if lag<0 or lag>max_lag_seconds: reasons.append("ENTRY_INTENT_NOT_FRESH")
    if state["active_count"]>0: reasons.append("PENDING_OR_OPEN_POSITION_ACTIVE")
    if row.source=="BASE" and overlaps_rollover(t,row.max_holding_minutes): reasons.append("BASE_HOLD_OVERLAPS_SERVER_00_01")
    if row.source in {"STAGE280","STAGE281"} and state["dd"]>30.0: reasons.append("RESOLVED_COMBINED_DD_ABOVE_30")
    if row.source!="BASE" and pd.notna(state["last_candidate_entry"]) and t<pd.Timestamp(state["last_candidate_entry"])+pd.Timedelta(hours=12): reasons.append("SHARED_CANDIDATE_COOLDOWN_12H")
    if row.source=="STAGE281":
        ok=state["last_base_pnl"]<0 and pd.notna(state["last_base_exit"]) and pd.Timestamp(state["last_base_exit"])<=t<=pd.Timestamp(state["last_base_exit"])+pd.Timedelta(hours=72)
        if not ok: reasons.append("NOT_AFTER_LATEST_RESOLVED_BASE_LOSS_WITHIN_72H")
    if row.source=="STAGE286":
        if state["dd"]>10.0: reasons.append("RESOLVED_COMBINED_DD_ABOVE_10")
        if pd.notna(state["last_candidate_loss_exit"]) and t<pd.Timestamp(state["last_candidate_loss_exit"])+pd.Timedelta(hours=24): reasons.append("RESOLVED_CANDIDATE_LOSS_LOCKOUT_24H")
    return reasons

def evaluate_intents(intents,ledger,bootstrap,max_lag_seconds=120):
    decisions=[]; current=ledger.copy(); existing=set(current.candidate_id.astype(str)) if len(current) else set()
    if intents.empty: return pd.DataFrame(),current
    for row in intents.sort_values(["planned_entry_dt","priority","candidate_id"],kind="mergesort").itertuples(index=False):
        if str(row.candidate_id) in existing: continue
        state=state_at(row.planned_entry_dt,current,bootstrap); reasons=reject_reasons(row,state,max_lag_seconds); accepted=not reasons
        record=row._asdict(); record.update({"final_signal":accepted,"reject_reasons":";".join(reasons),"state_equity":state["equity"],"state_peak":state["peak"],"state_dd":state["dd"],"status":"PENDING_FILL" if accepted else "REJECTED","fill_dt":pd.NaT,"fill_price":float("nan"),"exit_dt":pd.NaT,"exit_price":float("nan"),"pnl":float("nan"),"exit_reason":""})
        decisions.append(record); existing.add(str(row.candidate_id))
        if accepted: current=pd.concat([current,pd.DataFrame([record])],ignore_index=True)
    return pd.DataFrame(decisions),current
