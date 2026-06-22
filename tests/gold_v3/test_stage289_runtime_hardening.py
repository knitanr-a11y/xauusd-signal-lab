from __future__ import annotations
import hashlib,importlib.util,json,sys
from pathlib import Path
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[2]; RT=ROOT/"scripts"/"gold_v3_runtime"; sys.path.insert(0,str(RT))
def load(name):
 p=RT/f"{name}.py"; spec=importlib.util.spec_from_file_location(name,p); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
F=load("gold_v3_289_feature_core"); A=load("gold_v3_289_artifacts"); S=load("gold_v3_289_state")
def write_candles(path,sep=",",out_of_order=False,partial=False):
 times=list(pd.date_range("2026-01-01",periods=5,freq="15min"))
 if out_of_order: times[3],times[4]=times[4],times[3]
 text=sep.join(["time","open","high","low","close","tick_volume","spread"])+"\n"
 for i,t in enumerate(times): text+=sep.join([t.strftime("%Y.%m.%d %H:%M"),str(100+i),str(102+i),str(99+i),str(101+i),str(1000+i),"25"])+"\n"
 if partial: text+=sep.join(["2026.01.01 01:15","106","107"])
 path.write_text(text,encoding="utf-8")
def candidate(source,entry,cid="x"):
 return pd.DataFrame([{"candidate_id":cid,"source":source,"priority":{"STAGE280":10,"STAGE281":20,"STAGE286":60}[source],"decision_dt":pd.Timestamp(entry)-pd.Timedelta(hours=1),"trigger_dt":pd.Timestamp(entry)-pd.Timedelta(minutes=5),"entry_dt":pd.Timestamp(entry),"entry_price":2000.0,"direction":"SHORT" if source=="STAGE286" else "LONG","direction_num":-1 if source=="STAGE286" else 1,"ml_score":.8,"score_threshold":.6,"atr_entry":10.0,"tp_atr":2.25,"sl_atr":1.25,"max_holding_minutes":480,"candidate_contract":"TEST"}])
def test_semicolon_and_partial_append_keep_latest_complete(tmp_path):
 p=tmp_path/"goldsharp_m15.csv"; write_candles(p,sep=";",partial=True); got=F.read_candles(p,3,timeframe="M15",require_spread=True); assert len(got)==3; assert got.time.max()==pd.Timestamp("2026-01-01 01:00"); assert got.attrs["separator"]==";"; assert got.attrs["rows_dropped_incomplete"]==1
def test_out_of_order_is_blocked(tmp_path):
 p=tmp_path/"goldsharp_m15.csv"; write_candles(p,out_of_order=True)
 with pytest.raises(ValueError,match="TIME_NOT_ASCENDING"): F.read_candles(p,timeframe="M15",require_spread=True)
def make_bundle(path):
 hashes={}
 for key,spec in A.EXPECTED.items():
  mp=path/spec["model_file"]; cp=path/spec["contract_file"]; mp.write_text(f"dummy {key}\n"); mh=hashlib.sha256(mp.read_bytes()).hexdigest(); contract={"model":spec["model_name"],"features":["f1","f2"],"fit_start":"2024-01-01","fit_end_exclusive":"2025-07-01","cal_start":"2025-07-01","cal_end_exclusive":"2026-01-01","score_threshold":spec["threshold"],"fixture_time":spec["fixture_time"],"fixture_score":spec["fixture_score"],"model_sha256":mh}; cp.write_text(json.dumps(contract)); hashes[mp.name]=mh; hashes[cp.name]=hashlib.sha256(cp.read_bytes()).hexdigest()
 report={"status":"PASS","fit_uses_2026":False,"checks":{"stage280_threshold":A.EXPECTED["stage280"]["threshold"],"stage281_threshold":A.EXPECTED["stage281"]["threshold"],"stage280_fixture_score":A.EXPECTED["stage280"]["fixture_score"],"stage281_fixture_score":A.EXPECTED["stage281"]["fixture_score"]},"artifact_sha256":hashes}; (path/A.REPORT_FILE).write_text(json.dumps(report))
def test_bundle_hash_tamper_is_blocked(tmp_path):
 make_bundle(tmp_path); assert A.validate_model_bundle(tmp_path)["status"]=="PASS"; p=tmp_path/A.EXPECTED["stage280"]["model_file"]; p.write_text("tampered")
 with pytest.raises(A.ArtifactValidationError,match="SHA256"): A.validate_model_bundle(tmp_path)
def test_future_entry_does_not_leak_into_prior_state():
 future=candidate("STAGE280","2026-01-02 10:00","future").iloc[0].to_dict(); future.update({"tp_price":2020.0,"sl_price":1990.0,"status":"OPEN","exit_dt":pd.NaT,"exit_price":float("nan"),"exit_reason":"","gross_pnl":float("nan"),"pnl":float("nan")}); ledger=pd.DataFrame([future]); state=S.state_at(pd.Timestamp("2026-01-01 10:00"),ledger,pd.DataFrame(columns=["entry_dt","exit_dt","pnl","source"])); assert pd.isna(state["last_candidate_entry"]); assert state["pending_candidate_count"]==0
def test_stage281_requires_resolved_base_loss_within_72h():
 base=pd.DataFrame([{"entry_dt":pd.Timestamp("2026-01-01 00:00"),"exit_dt":pd.Timestamp("2026-01-01 01:00"),"pnl":-5.0,"source":"BASE"}]); ok,_=S.evaluate_shadow_eligibility(candidate("STAGE281","2026-01-03 00:00","ok"),S.empty_observation_ledger(),base,True); assert bool(ok.iloc[0].shadow_eligible); ng,_=S.evaluate_shadow_eligibility(candidate("STAGE281","2026-01-05 02:00","ng"),S.empty_observation_ledger(),base,True); assert "NOT_AFTER_BASE_LOSS_WITHIN_72H" in ng.iloc[0].reject_reasons
def test_stage286_dd10_gate():
 base=pd.DataFrame([{"entry_dt":pd.Timestamp("2026-01-01 00:00"),"exit_dt":pd.Timestamp("2026-01-01 01:00"),"pnl":20.0,"source":"BASE"},{"entry_dt":pd.Timestamp("2026-01-01 02:00"),"exit_dt":pd.Timestamp("2026-01-01 03:00"),"pnl":-15.0,"source":"BASE"}]); ng,_=S.evaluate_shadow_eligibility(candidate("STAGE286","2026-01-01 10:00","dd"),S.empty_observation_ledger(),base,True); assert "SHORT_DD_ABOVE_10" in ng.iloc[0].reject_reasons
def test_training_code_excludes_2026_fit_and_writes_hashes():
 text=(RT/"gold_v3_289_train_live_models_audit.py").read_text(encoding="utf-8"); assert 'z.time<"2025-07-01"' in text; assert 'z.time<"2026-01-01"' in text; assert '"fit_uses_2026":False' in text; assert '"artifact_sha256":hashes' in text
