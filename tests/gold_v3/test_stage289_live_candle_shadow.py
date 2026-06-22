from pathlib import Path
import importlib.util
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
RT=ROOT/'scripts'/'gold_v3_runtime'
sys.path.insert(0,str(RT))

def load(name):
 p=RT/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

F=load('gold_v3_289_feature_core')
S=load('gold_v3_289_state')

def test_latest_csv_row_is_kept(tmp_path):
 p=tmp_path/'goldsharp_m15.csv'; d=pd.DataFrame({'time':pd.date_range('2026-01-01',periods=5,freq='15min'),'open':[1]*5,'high':[2]*5,'low':[0]*5,'close':[1]*5,'tick_volume':[10]*5,'spread':[20]*5})
 d.to_csv(p,index=False); got=F.read_candles(p,3,timeframe='M15',require_spread=True)
 assert len(got)==3 and got.time.max()==d.time.max()

def test_h4_is_available_only_after_nominal_close():
 base=pd.DataFrame({'time':pd.to_datetime(['2026-01-01 03:59','2026-01-01 04:00'])})
 src=pd.DataFrame({'time':pd.to_datetime(['2026-01-01 00:00']),'v':[10]})
 got=F.merge_closed(base,src,'h4',240,['v'])
 assert pd.isna(got.loc[0,'h4_v']) and got.loc[1,'h4_v']==10

def test_missing_base_state_rejects_candidate():
 c=pd.DataFrame([{'candidate_id':'x','source':'STAGE280','priority':10,'decision_dt':pd.Timestamp('2026-01-01 09:00'),'trigger_dt':pd.Timestamp('2026-01-01 09:55'),'entry_dt':pd.Timestamp('2026-01-01 10:00'),'entry_price':2000.0,'direction':'LONG','direction_num':1,'ml_score':0.8,'score_threshold':0.6,'atr_entry':10.0,'tp_atr':1.75,'sl_atr':1.0,'max_holding_minutes':360,'candidate_contract':'TEST'}])
 dec,led=S.evaluate_shadow_eligibility(c,S.empty_observation_ledger(),pd.DataFrame(columns=['entry_dt','exit_dt','pnl','source']),base_state_ready=False)
 assert not bool(dec.iloc[0].shadow_eligible)
 assert 'BASE_PORTFOLIO_STATE_NOT_CONNECTED' in dec.iloc[0].reject_reasons
 assert led.empty

def test_entry_point_is_read_only():
 text=(RT/'gold_v3_289_live_candle_ml_safe_shadow_audit.py').read_text(encoding='utf-8').lower()
 assert 'order_send' not in text and 'metatrader5' not in text and 'webhook' not in text

def test_training_contract_excludes_2026_fit():
 text=(RT/'gold_v3_289_train_live_models_audit.py').read_text(encoding='utf-8')
 assert 'z.time<"2025-07-01"' in text and 'z.time<"2026-01-01"' in text
 assert '"fit_uses_2026":False' in text
