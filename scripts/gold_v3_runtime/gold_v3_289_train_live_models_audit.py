#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Train exact Stage280/281 models from complete closed historical CSVs."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import lightgbm
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from gold_v3_289_feature_core import GOLD_FILES,load_gold,m1_arrays,read_candles
from gold_v3_289_stage280_features import build_stage280_context,stage280_model_frame
from gold_v3_289_stage281_features import build_stage281_context
EXP280=.5927349103795366; EXP281=.5525199124029727
SCORE280=.5949591748604749; SCORE281=.6586538142862226
TIME280="2026-06-19 08:00:00"; TIME281="2026-06-17 10:00:00"; TOL=1e-12
EXPECTED_STAGE280_FIT_N=4974; EXPECTED_STAGE280_CAL_N=1809; EXPECTED_STAGE280_POSITIVE_FIT=245

def args():
 p=argparse.ArgumentParser(); p.add_argument("--candle-dir",required=True); p.add_argument("--output-dir",default=""); p.add_argument("--force",action="store_true"); return p.parse_args()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def stage280(cdir):
 ctx=build_stage280_context(cdir,include_next=False,tail_only=False).sort_values("time").reset_index(drop=True); raw=load_gold(cdir,tail_only=False); mt,mo,mh,ml,mc,mv,ms=m1_arrays(raw["M1"]); dirs=[]; future_valid=[]
 for r in ctx.itertuples(index=False):
  a=float(r.atr_prev) if pd.notna(r.atr_prev) else np.nan; t=np.datetime64(r.time); s=np.searchsorted(mt,t,"left"); e=np.searchsorted(mt,t+np.timedelta64(240,"m"),"left")
  valid=bool(np.isfinite(a) and a>0 and s<len(mt) and mt[s]==t and e>s and e-s>=180)
  future_valid.append(valid)
  if not valid: dirs.append(0); continue
  ep=float(mo[s]); hi=float(mh[s:e].max()); lo=float(ml[s:e].min()); fin=float(mc[e-1]); lmfe=(hi-ep)/a; lmae=(ep-lo)/a; lfin=(fin-ep)/a; smfe=(ep-lo)/a; smae=(hi-ep)/a; sfin=(ep-fin)/a
  lq=lmfe>=2 and lfin>=.75 and lmae<=1.25 and lmfe>=1.5*max(lmae,.05); sq=smfe>=2 and sfin>=.75 and smae<=1.25 and smfe>=1.5*max(smae,.05)
  dirs.append(1 if lq and not sq else (-1 if sq and not lq else (1 if lq and sq and lmfe-lmae>smfe-smae else (-1 if lq and sq else 0))))
 ctx["future_valid"]=np.asarray(future_valid,dtype=bool); ctx["event_dir"]=np.asarray(dirs,dtype="int8"); ctx["event_onset"]=False
 for d in [1,-1]:
  m=ctx.event_dir.eq(d); prev=m.shift(1,fill_value=False)|m.shift(2,fill_value=False)|m.shift(3,fill_value=False); ctx.loc[m&~prev,"event_onset"]=True
 meta={"time","atr_prev","future_valid","event_dir","event_onset","h4_trend","d1_trend"}; rawf=[c for c in ctx.columns if c not in meta]; bad=("_open","_high","_low","_close","_ema20","_ema50","_atr14"); rawf=[c for c in rawf if not c.endswith(bad)]; eng=["countermove_60","countermove_120","turn_5","turn_15","turn_30","turn_accel_5v30","turn_accel_15v60","m5_turn_accel","m15_turn_accel","m1_reject_wick","m5_reject_wick","m15_reject_wick","h4_align","d1_align"]; features=list(dict.fromkeys(rawf+eng))
 # The audited REV model pools both H4 directions. The predicted reversal
 # direction is opposite the prior closed H4 trend. Features are normalized
 # into that predicted direction, and incomplete future windows are excluded.
 z=ctx[ctx.h4_trend.ne(0)&ctx.future_valid].copy(); rev_direction=(-z.h4_trend).astype("int8"); y=((z.event_onset)&z.event_dir.eq(rev_direction)).astype(int); X=stage280_model_frame(z,features,direction=rev_direction); fm=(z.time>="2024-01-01")&(z.time<"2025-07-01"); cm=(z.time>="2025-07-01")&(z.time<"2026-01-01"); pos=max(int(y[fm].sum()),1); spw=min(max((int(fm.sum())-pos)/pos,1),25)
 model=LGBMClassifier(objective="binary",n_estimators=220,learning_rate=.03,num_leaves=15,max_depth=5,min_child_samples=60,subsample=.85,colsample_bytree=.8,reg_alpha=1,reg_lambda=6,random_state=281,n_jobs=1,verbosity=-1,scale_pos_weight=spw); model.fit(X.loc[fm],y.loc[fm]); q=float(np.quantile(model.predict_proba(X.loc[cm])[:,1],.95)); fixture=z.time.eq(pd.Timestamp(TIME280)); score=float(model.predict_proba(X.loc[fixture])[:,1][0]) if fixture.any() else np.nan
 return model,features,q,score,{"fit_n":int(fm.sum()),"cal_n":int(cm.sum()),"positive_fit":int(y[fm].sum()),"fit_base_rate":float(y[fm].mean()),"future_valid_rows":int(z.future_valid.sum()),"fit_h4_up_n":int((fm&z.h4_trend.eq(1)).sum()),"fit_h4_down_n":int((fm&z.h4_trend.eq(-1)).sum())}
def stage281(cdir,feature_list_path):
 ctx=build_stage281_context(cdir,include_next=False,tail_only=False).sort_values("time").reset_index(drop=True); raw=load_gold(cdir,tail_only=False); mt,mo,mh,ml,mc,mv,ms=m1_arrays(raw["M1"]); target=[]
 for r in ctx.itertuples(index=False):
  t=np.datetime64(r.time); s=np.searchsorted(mt,t,"left"); a=float(r.h1_atr14) if pd.notna(r.h1_atr14) else np.nan; e=np.searchsorted(mt,t+np.timedelta64(240,"m"),"left")
  if not np.isfinite(a) or a<=0 or s>=len(mt) or mt[s]!=t or e<=s+120 or e>len(mt): target.append(0); continue
  ep=mo[s]; hi=mh[s:e].max(); lo=ml[s:e].min(); fin=mc[e-1]; mfe=(hi-ep)/a; mae=(ep-lo)/a; final=(fin-ep)/a; target.append(int(mfe>=1.75 and final>=.55 and mae<=1.25 and mfe>=1.4*max(mae,.05)))
 ctx["target"]=np.asarray(target,dtype="int8"); z=ctx[ctx.h4_trend.eq(1)].copy(); wanted=feature_list_path.read_text(encoding="utf-8").split(); base=[c for c in wanted if c in z.columns]; X=z[base].copy()
 for c in base:
  if any(k in c for k in ["ret","dist_ema","ema20_slope","ema50_slope","body_signed"]): X[c]=pd.to_numeric(X[c],errors="coerce")
  elif "_pos" in c: X[c]=2*pd.to_numeric(X[c],errors="coerce")-1
 X["countermove_30"]=-pd.to_numeric(X.get("m1_ret30",np.nan),errors="coerce"); X["countermove_60"]=-pd.to_numeric(X.get("m1_ret60",np.nan),errors="coerce"); X["countermove_120"]=-pd.to_numeric(X.get("m1_ret120",np.nan),errors="coerce"); X["turn_accel_m1"]=pd.to_numeric(X.get("m1_ret15",0),errors="coerce")-(pd.to_numeric(X.get("m1_ret60",0),errors="coerce")-pd.to_numeric(X.get("m1_ret15",0),errors="coerce"))/3; X["turn_accel_m5"]=pd.to_numeric(X.get("m5_ret3_atr",0),errors="coerce")-(pd.to_numeric(X.get("m5_ret12_atr",0),errors="coerce")-pd.to_numeric(X.get("m5_ret3_atr",0),errors="coerce"))/3; X["turn_accel_m15"]=pd.to_numeric(X.get("m15_ret1_atr",0),errors="coerce")-(pd.to_numeric(X.get("m15_ret4_atr",0),errors="coerce")-pd.to_numeric(X.get("m15_ret1_atr",0),errors="coerce"))/3; X["h4_align"]=z.h4_trend; X["d1_align"]=z.d1_trend; features=list(X.columns); X=X.replace([np.inf,-np.inf],np.nan).fillna(0).astype("float32"); y=z.target.astype(int)
 fm=(z.time>="2024-01-01")&(z.time<"2025-07-01"); cm=(z.time>="2025-07-01")&(z.time<"2026-01-01"); pos=max(int(y[fm].sum()),1); spw=min(max((int(fm.sum())-pos)/pos,1),30); model=LGBMClassifier(objective="binary",n_estimators=110,learning_rate=.045,num_leaves=15,max_depth=5,min_child_samples=120,subsample=.85,colsample_bytree=.75,reg_alpha=1.5,reg_lambda=8,random_state=281,n_jobs=1,verbosity=-1,scale_pos_weight=spw); model.fit(X.loc[fm],y.loc[fm]); q=float(np.quantile(model.predict_proba(X.loc[cm])[:,1],.85)); fixture=z.time.eq(pd.Timestamp(TIME281)); score=float(model.predict_proba(X.loc[fixture])[:,1][0]) if fixture.any() else np.nan
 return model,features,q,score,{"fit_n":int(fm.sum()),"cal_n":int(cm.sum()),"positive_fit":int(y[fm].sum())}
def close(a,b): return bool(np.isfinite(a) and abs(float(a)-float(b))<=TOL)
def main():
 a=args(); cdir=Path(a.candle_dir).expanduser().resolve(); out=Path(a.output_dir).expanduser().resolve() if a.output_dir else Path(__file__).resolve().with_name("models")/"gold_v3_289"; out.mkdir(parents=True,exist_ok=True)
 missing=[str(cdir/n) for n in GOLD_FILES.values() if not (cdir/n).exists()]
 if missing: raise FileNotFoundError(f"missing closed candle CSVs: {missing}")
 for tf,name in GOLD_FILES.items(): read_candles(cdir/name,4,timeframe=tf,require_spread=True)
 m280,f280,q280,s280,n280=stage280(cdir); m281,f281,q281,s281,n281=stage281(cdir,Path(__file__).resolve().with_name("gold_v3_stage281_live_feature_list.txt")); checks={"stage280_threshold":q280,"stage281_threshold":q281,"stage280_fixture_score":s280,"stage281_fixture_score":s281}; stage280_population_ok=n280["fit_n"]==EXPECTED_STAGE280_FIT_N and n280["cal_n"]==EXPECTED_STAGE280_CAL_N and n280["positive_fit"]==EXPECTED_STAGE280_POSITIVE_FIT; stage280_parity=stage280_population_ok and close(q280,EXP280) and close(s280,SCORE280); stage281_parity=close(q281,EXP281) and close(s281,SCORE281); ok=stage280_parity and stage281_parity
 expected={"stage280_threshold":EXP280,"stage281_threshold":EXP281,"stage280_fixture_score":SCORE280,"stage281_fixture_score":SCORE281,"stage280_fit_n":EXPECTED_STAGE280_FIT_N,"stage280_cal_n":EXPECTED_STAGE280_CAL_N,"stage280_positive_fit":EXPECTED_STAGE280_POSITIVE_FIT}
 if not ok:
  report={"status":"BLOCKED_PARITY_MISMATCH","checks":checks,"expected":expected,"parity":{"stage280_population":stage280_population_ok,"stage280":stage280_parity,"stage281":stage281_parity},"counts":{"stage280":n280,"stage281":n281},"closed_csv_contract":True,"fit_uses_2026":False,"lightgbm_version":lightgbm.__version__}; (out/"stage289_model_training_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2)); return 2
 hashes={}
 for stem,model,features,q,ftime,fscore,name,quant in [("stage280_rev_long_2026",m280,f280,q280,TIME280,s280,"STAGE280_REV_LONG_2026","q95"),("stage281_med4h_cont_long_2026",m281,f281,q281,TIME281,s281,"STAGE281_MED4H_CONT_LONG_2026","q85")]:
  mp=out/f"{stem}_model.txt"; cp=out/f"{stem}_contract.json"; mp.write_text(model.booster_.model_to_string(),encoding="utf-8"); mh=sha(mp); contract={"model":name,"features":features,"fit_start":"2024-01-01","fit_end_exclusive":"2025-07-01","cal_start":"2025-07-01","cal_end_exclusive":"2026-01-01","score_quantile":quant,"score_threshold":q,"fixture_time":ftime,"fixture_score":fscore,"model_sha256":mh}; cp.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8"); hashes[mp.name]=mh; hashes[cp.name]=sha(cp)
 report={"status":"PASS","checks":checks,"expected":expected,"parity":{"stage280_population":True,"stage280":True,"stage281":True},"counts":{"stage280":n280,"stage281":n281},"closed_csv_contract":True,"fit_uses_2026":False,"fit_start":"2024-01-01","fit_end_exclusive":"2025-07-01","cal_start":"2025-07-01","cal_end_exclusive":"2026-01-01","lightgbm_version":lightgbm.__version__,"artifact_sha256":hashes}; (out/"stage289_model_training_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
