from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from cost_stress_contract import Lineage, POINT, Scenario
TOL_R=1e-8; TOL_PRICE=1e-7
RISK_COLS=('risk_price','risk_unit','trade_atr','atr14','atr')
class M1Engine:
    def __init__(self,frame:pd.DataFrame)->None:
        required=['time','open','high','low','close','spread']; missing=[x for x in required if x not in frame.columns]
        if missing: raise ValueError(f'M1 missing columns: {missing}')
        data=frame[required].copy(); data['time']=pd.to_datetime(data['time'],format='%Y.%m.%d %H:%M:%S'); data=data.sort_values('time',kind='mergesort').reset_index(drop=True)
        if data['time'].duplicated().any(): raise ValueError('M1 contains duplicate times')
        self.times=pd.DatetimeIndex(data['time']).asi8; self.opens=data['open'].to_numpy(float); self.highs=data['high'].to_numpy(float); self.lows=data['low'].to_numpy(float); self.closes=data['close'].to_numpy(float); self.spreads=data['spread'].to_numpy(float); self.latest_close_ns=int(self.times[-1])+60_000_000_000
    def entry_index(self,timestamp:pd.Timestamp)->int:
        value=pd.Timestamp(timestamp).value; index=int(np.searchsorted(self.times,value,side='left'))
        if index>=len(self.times) or int(self.times[index])!=value: raise RuntimeError(f'Exact M1 entry missing: {timestamp}')
        return index
    def evaluate(self,entry_time:pd.Timestamp,risk:float,lineage:Lineage,spread_multiplier:float,slip_points:int)->dict[str,Any]:
        start=self.entry_index(entry_time); horizon_end=pd.Timestamp(entry_time)+pd.Timedelta(minutes=lineage.horizon_minutes)
        if horizon_end.value>self.latest_close_ns: raise RuntimeError(f'Horizon exceeds frozen M1 data: {entry_time}')
        end=int(np.searchsorted(self.times,horizon_end.value,side='left'))
        if end<=start: raise RuntimeError(f'Empty M1 horizon: {entry_time}')
        spread_price=float(self.spreads[start])*POINT; reference_entry=float(self.opens[start])+spread_multiplier*spread_price; slip_price=float(slip_points)*POINT; entry_fill=reference_entry+slip_price; stop=reference_entry-risk; target=reference_entry+risk
        stop_hits=np.flatnonzero(self.lows[start:end]<=stop); target_hits=np.flatnonzero(self.highs[start:end]>=target); has_stop=bool(len(stop_hits)); has_target=bool(len(target_hits))
        if has_stop and (not has_target or int(stop_hits[0])<=int(target_hits[0])): index=start+int(stop_hits[0]); raw_exit=stop; outcome='SL'
        elif has_target: index=start+int(target_hits[0]); raw_exit=target; outcome='TP'
        else: index=end-1; raw_exit=float(self.closes[index]); outcome='TIME'
        exit_fill=float(raw_exit)-slip_price; stored_exit=pd.Timestamp(self.times[index])
        if lineage.stored_exit_time=='M1_BAR_CLOSE': stored_exit+=pd.Timedelta(minutes=1)
        return {'entry_reference':reference_entry,'entry_fill':entry_fill,'exit_reference':float(raw_exit),'exit_fill':exit_fill,'exit_time_stressed':stored_exit,'r_value_stressed':float((exit_fill-entry_fill)/risk),'outcome_stressed':outcome,'risk_price':float(risk),'baseline_spread_price':spread_price,'slippage_price_per_side':slip_price}
def recover_risk(row:pd.Series)->float:
    entry=float(row['entry_price']); exit_price=float(row['exit_price']); r_value=float(row['r_value'])
    if abs(r_value)>TOL_R:
        risk=(exit_price-entry)/r_value
        if math.isfinite(risk) and risk>0: return float(risk)
    for column in RISK_COLS:
        if column in row.index and pd.notna(row[column]):
            risk=float(row[column])
            if math.isfinite(risk) and risk>0: return risk
    raise RuntimeError(f"Cannot recover risk: candidate={row['candidate_id']} entry={row['entry_time']} r={r_value}")
def replay(registry:pd.DataFrame,engine:M1Engine,config:dict[str,Any],lineage_by_candidate:dict[str,Lineage],scenarios:list[Scenario])->tuple[pd.DataFrame,int]:
    baseline_id=str(config['scenario_grid']['baseline_scenario_id']); output=[]; checks_done=0; ordered=registry.sort_values(['candidate_id','decision_close_time'],kind='mergesort')
    for _,row in ordered.iterrows():
        candidate_id=str(row['candidate_id']); lineage=lineage_by_candidate[candidate_id]; risk=recover_risk(row)
        for scenario in scenarios:
            result=engine.evaluate(pd.Timestamp(row['entry_time']),risk,lineage,scenario.spread_multiplier,scenario.slippage_points_per_side)
            if scenario.scenario_id==baseline_id:
                checks={'entry_price':abs(result['entry_fill']-float(row['entry_price']))<=TOL_PRICE,'exit_price':abs(result['exit_fill']-float(row['exit_price']))<=TOL_PRICE,'r_value':abs(result['r_value_stressed']-float(row['r_value']))<=TOL_R,'exit_time':pd.Timestamp(result['exit_time_stressed'])==pd.Timestamp(row['exit_time'])}
                if not all(checks.values()): raise RuntimeError(f"Baseline parity mismatch {candidate_id} {row['entry_time']}: {checks}; expected entry={row['entry_price']} exit={row['exit_price']} r={row['r_value']} time={row['exit_time']}; actual={result}")
                checks_done+=1
            output.append({'candidate_id':candidate_id,'lineage_id':lineage.lineage_id,'population':str(row['trade_core_source']),'decision_close_time':pd.Timestamp(row['decision_close_time']),'entry_time':pd.Timestamp(row['entry_time']),'baseline_exit_time':pd.Timestamp(row['exit_time']),'baseline_entry_price':float(row['entry_price']),'baseline_exit_price':float(row['exit_price']),'baseline_r':float(row['r_value']),'scenario_id':scenario.scenario_id,'spread_multiplier':scenario.spread_multiplier,'slippage_points_per_side':scenario.slippage_points_per_side,**result})
    if checks_done!=len(registry): raise RuntimeError(f'Baseline parity count mismatch: {checks_done}/{len(registry)}')
    return pd.DataFrame(output),checks_done
