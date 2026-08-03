#!/usr/bin/env python3
"""Frozen monthly prequential comparison for BTC AI V1 OHLC schedules.

No PnL, 2026 selection, Shadow, Discord, MT5 order, live-ready or final signal.
Training uses only decisions before each monthly refit and labels resolved by it.
"""
from __future__ import annotations
import argparse, hashlib, json, math, platform, sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score

CONTRACT_ID="BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_FORENSIC_20260803"
START=pd.Timestamp("2024-01-01"); END=pd.Timestamp("2026-01-01")
MONTHS=tuple(pd.date_range(START,END,freq="MS",inclusive="left"))
FORMAL_MONTHS=MONTHS
DIRECTIONS=("LONG","SHORT")
SCHEDULES={"EXPANDING":None,"ROLLING_3M":3,"ROLLING_6M":6,"ROLLING_12M":12}
SCHEDULE_MONTHS=SCHEDULES
BAD_TOKENS=("volume","funding","open_interest","orderbook","order_flow","future","target","label","outcome","pnl","profit","exit","mfe","mae")

@dataclass(frozen=True)
class FormalConfig:
 expanding_start:str="2023-01-01"; min_training_rows:int=6000; min_positive_labels:int=400
 p90_quantile:float=.90; psi_bins:int=10; seed:int=20260803; num_leaves:int=15; max_depth:int=4
 learning_rate:float=.03; n_estimators:int=250; min_child_samples:int=120; bagging_fraction:float=.8
 bagging_freq:int=1; feature_fraction:float=.8; lambda_l2:float=5.; n_jobs:int=1

@dataclass(frozen=True)
class SupportGates:
 available_months_min:int=20; mean_auc_improvement_min:float=.01; positive_auc_months_min:int=15
 mean_p90_lift_improvement_min:float=.02; positive_p90_lift_months_min:int=15; score_psi_median_max:float=.25

class ContractError(RuntimeError): pass

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def dump(path,obj):
 def conv(x):
  if isinstance(x,(pd.Timestamp,np.datetime64)): return str(pd.Timestamp(x))
  if isinstance(x,np.integer): return int(x)
  if isinstance(x,np.floating): return None if not np.isfinite(x) else float(x)
  if isinstance(x,np.ndarray): return x.tolist()
  raise TypeError(type(x))
 Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=conv),encoding="utf-8")

def stable_month_start(x): return pd.to_datetime(x,errors="raise").dt.to_period("M").dt.to_timestamp()
def d1_regime(x):
 v=pd.to_numeric(x,errors="coerce")
 return pd.Series(np.select([v>0,v<0,v==0],["UP","DOWN","NEUTRAL"],default="UNKNOWN"),index=x.index)
def half(month): return f"{month.year}H{1 if month.month<=6 else 2}"
def schedule_start(month,schedule,cfg):
 n=SCHEDULES[schedule]
 return pd.Timestamp(cfg.expanding_start) if n is None else month-pd.DateOffset(months=n)

def load_state_inputs(state_dir):
 state_dir=Path(state_dir); fp=state_dir/"features.npy"; mp=state_dir/"meta.csv"; jp=state_dir/"feature_sets.json"
 missing=[str(p) for p in (fp,mp,jp) if not p.exists()]
 if missing: raise ContractError("Missing required state inputs: "+", ".join(missing))
 X=np.load(fp,mmap_mode="r"); m=pd.read_csv(mp); cols=list(json.loads(jp.read_text(encoding="utf-8")).get("all_cols",[]))
 if X.ndim!=2 or X.shape[0]!=len(m) or X.shape[1]!=len(cols): raise ContractError(f"feature/meta/name shape mismatch: {X.shape}, {len(m)}, {len(cols)}")
 if X.shape[1]!=100: raise ContractError(f"Frozen universe requires exactly 100 features, got {X.shape[1]}")
 req={"decision_time","label_long","label_short","maturity_ns","d1_trend"}; absent=sorted(req-set(m.columns))
 if absent: raise ContractError(f"meta.csv missing {absent}")
 bad=sorted(c for c in cols if any(t in c.lower() for t in BAD_TOKENS))
 if bad: raise ContractError(f"Prohibited feature names: {bad}")
 if len(set(cols))!=len(cols): raise ContractError("Duplicate feature names")
 m=m.copy(); m["decision_time"]=pd.to_datetime(m.decision_time,errors="raise")
 m["maturity_ns"]=pd.to_numeric(m.maturity_ns,errors="raise").astype("int64")
 for c in ("label_long","label_short"): m[c]=pd.to_numeric(m[c],errors="raise").astype("int8")
 m["month"]=stable_month_start(m.decision_time); m["d1_regime"]=d1_regime(m.d1_trend)
 if not m.decision_time.is_monotonic_increasing or m.decision_time.duplicated().any(): raise ContractError("decision_time must be unique and monotonic")
 counts=m.loc[(m.decision_time>=START)&(m.decision_time<END),"month"].value_counts()
 miss=[x.strftime("%Y-%m") for x in MONTHS if counts.get(x,0)==0]
 if miss: raise ContractError(f"Formal evaluation months missing: {miss}")
 manifest={"features":{"sha256":sha256(fp),"shape":list(X.shape),"dtype":str(X.dtype)},"meta":{"sha256":sha256(mp),"rows":len(m)},"feature_sets":{"sha256":sha256(jp),"feature_count":len(cols)},"decision_first":str(m.decision_time.iloc[0]),"decision_last":str(m.decision_time.iloc[-1]),"formal_rows":int(((m.decision_time>=START)&(m.decision_time<END)).sum()),"rows_2026_or_later_present_but_selection_forbidden":int((m.decision_time>=END).sum())}
 return X,m,cols,manifest

def build_masks(m,month,schedule,direction,cfg):
 end=month+pd.DateOffset(months=1); calendar=(m.decision_time>=month)&(m.decision_time<end)
 refit=pd.Timestamp(m.loc[calendar,"decision_time"].min()) if calendar.any() else month
 known=m[f"label_{direction.lower()}"].isin([0,1]).to_numpy(); start=schedule_start(month,schedule,cfg)
 train=((m.decision_time>=start)&(m.decision_time<refit)&(m.maturity_ns<=refit.value)).to_numpy()&known
 cal=((m.decision_time>=month-pd.DateOffset(months=1))&(m.decision_time<month)).to_numpy()
 val=calendar.to_numpy()&known
 return {"train":train,"calibration":cal,"validation":val,"refit_time":refit}

def audit_masks(m,z,month):
 tr=z["train"]; ca=z["calibration"]; va=z["validation"]; ref=pd.Timestamp(z["refit_time"])
 return {"train_future_or_current_decision_count":int((m.loc[tr,"decision_time"]>=ref).sum()),"train_unresolved_at_refit_count":int((m.loc[tr,"maturity_ns"]>ref.value).sum()),"calibration_outside_previous_month_count":int(((m.loc[ca,"decision_time"]<month-pd.DateOffset(months=1))|(m.loc[ca,"decision_time"]>=month)).sum()),"train_validation_overlap_count":int((tr&va).sum()),"calibration_validation_overlap_count":int((ca&va).sum()),"validation_outside_target_month_count":int(((m.loc[va,"decision_time"]<month)|(m.loc[va,"decision_time"]>=month+pd.DateOffset(months=1))).sum()),"selection_rows_2026_or_later_count":int((m.loc[tr|ca,"decision_time"]>=END).sum())}

def fit(X,y,cfg):
 p=float(y.mean())
 if not 0<p<1: raise ContractError("Training labels need both classes")
 w=float(np.clip(1/p,.5,3)); sw=np.where(y==1,w,1.)
 model=lgb.LGBMClassifier(objective="binary",num_leaves=cfg.num_leaves,max_depth=cfg.max_depth,learning_rate=cfg.learning_rate,n_estimators=cfg.n_estimators,min_child_samples=cfg.min_child_samples,subsample=cfg.bagging_fraction,subsample_freq=cfg.bagging_freq,colsample_bytree=cfg.feature_fraction,reg_lambda=cfg.lambda_l2,random_state=cfg.seed,n_jobs=cfg.n_jobs,verbosity=-1,deterministic=True,force_col_wise=True)
 model.fit(X,y,sample_weight=sw); return model,p,w

def edges(ref,bins):
 x=np.asarray(ref,float); x=x[np.isfinite(x)]
 if not len(x): return np.array([-np.inf,np.inf])
 e=np.unique(np.quantile(x,np.linspace(0,1,bins+1)))
 if len(e)<2: return np.array([-np.inf,float(e[0]),np.inf])
 e=e.astype(float); e[0]=-np.inf; e[-1]=np.inf; return e

def psi(ref,tar,bins=10,eps=1e-6):
 a=np.asarray(ref,float); b=np.asarray(tar,float); a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
 if not len(a) or not len(b): return math.nan
 e=edges(a,bins); ac=np.histogram(a,e)[0]; bc=np.histogram(b,e)[0]
 ap=np.maximum(ac/max(ac.sum(),1),eps); bp=np.maximum(bc/max(bc.sum(),1),eps)
 return float(np.sum((bp-ap)*np.log(bp/ap)))

def slope(y,s):
 if len(np.unique(y))<2 or np.nanstd(s)<=1e-12: return math.nan
 q=np.clip(s,1e-6,1-1e-6); x=np.log(q/(1-q)).reshape(-1,1)
 try:
  z=LogisticRegression(C=1e6,solver="lbfgs",max_iter=2000).fit(x,y); return float(z.coef_[0,0])
 except Exception: return math.nan

def fpsi(Xc,Xv,cols,bins):
 rows=[]
 for i,c in enumerate(cols): rows.append({"feature":c,"psi":psi(Xc[:,i],Xv[:,i],bins)})
 a=np.array([r["psi"] for r in rows if np.isfinite(r["psi"])])
 summ={"feature_psi_median":float(np.median(a)) if len(a) else math.nan,"feature_psi_p90":float(np.quantile(a,.9)) if len(a) else math.nan,"feature_psi_max":float(a.max()) if len(a) else math.nan}
 return summ,rows

def one(X,m,cols,month,schedule,direction,cfg):
 z=build_masks(m,month,schedule,direction,cfg); audit=audit_masks(m,z,month)
 if any(audit.values()): raise ContractError(f"Leakage audit failed {month:%Y-%m} {schedule} {direction}: {audit}")
 ti=np.flatnonzero(z["train"]); ci=np.flatnonzero(z["calibration"]); vi=np.flatnonzero(z["validation"]); lc=f"label_{direction.lower()}"
 yt=m.iloc[ti][lc].to_numpy(np.int8); y=m.iloc[vi][lc].to_numpy(np.int8)
 base={"month":month.strftime("%Y-%m"),"year":month.year,"halfyear":half(month),"schedule":schedule,"direction":direction,"training_start":str(schedule_start(month,schedule,cfg)),"training_cutoff":str(z["refit_time"]),"train_rows":len(ti),"train_positive_labels":int(yt.sum()),"train_negative_labels":int(len(yt)-yt.sum()),"calibration_rows":len(ci),"validation_rows":len(vi),**{f"audit_{k}":v for k,v in audit.items()}}
 reasons=[]
 if len(ti)<cfg.min_training_rows: reasons.append("MIN_TRAINING_ROWS")
 if yt.sum()<cfg.min_positive_labels: reasons.append("MIN_POSITIVE_LABELS")
 if (yt==0).sum()<1: reasons.append("TRAINING_NO_NEGATIVE_LABEL")
 if not len(ci): reasons.append("PREVIOUS_MONTH_CALIBRATION_MISSING")
 if not len(vi): reasons.append("VALIDATION_MONTH_MISSING")
 if len(np.unique(yt))<2: reasons.append("TRAINING_SINGLE_CLASS")
 if len(np.unique(y))<2: reasons.append("VALIDATION_SINGLE_CLASS")
 if reasons: return {**base,"available":False,"unavailable_reasons":"|".join(reasons)},[],pd.DataFrame()
 Xt=np.asarray(X[ti],np.float32); Xc=np.asarray(X[ci],np.float32); Xv=np.asarray(X[vi],np.float32)
 model,prior,pw=fit(Xt,yt,cfg); cs=model.predict_proba(Xc)[:,1]; s=model.predict_proba(Xv)[:,1]; thr=float(np.quantile(cs,cfg.p90_quantile)); sel=s>=thr
 fs,fr=fpsi(Xc,Xv,cols,cfg.psi_bins); un=float(y.mean()); sr=float(y[sel].mean()) if sel.any() else math.nan
 row={**base,"available":True,"unavailable_reasons":"","training_positive_rate":prior,"positive_class_weight":pw,"max_train_decision_time":str(m.iloc[ti].decision_time.max()),"max_train_maturity_time":str(pd.Timestamp(int(m.iloc[ti].maturity_ns.max()))),"validation_positive_labels":int(y.sum()),"validation_negative_labels":int(len(y)-y.sum()),"auc":float(roc_auc_score(y,s)),"balanced_accuracy_at_training_prior":float(balanced_accuracy_score(y,s>=prior)),"brier":float(brier_score_loss(y,s)),"calibration_slope":slope(y,s),"score_psi_vs_previous_month":psi(cs,s,cfg.psi_bins),"unconditional_positive_rate":un,"p90_threshold_from_previous_month":thr,"p90_event_count":int(sel.sum()),"p90_positive_rate":sr,"p90_label_lift":sr-un if np.isfinite(sr) else math.nan,"score_mean":float(s.mean()),"score_p90":float(np.quantile(s,.9)),**fs}
 reg=m.iloc[vi].d1_regime.to_numpy()
 for r in ("UP","NEUTRAL","DOWN"):
  q=reg==r; qs=q&sel; br=float(y[q].mean()) if q.any() else math.nan; rr=float(y[qs].mean()) if qs.any() else math.nan
  row[f"d1_{r.lower()}_rows"]=int(q.sum()); row[f"d1_{r.lower()}_p90_count"]=int(qs.sum()); row[f"d1_{r.lower()}_p90_lift"]=rr-br if np.isfinite(br) and np.isfinite(rr) else math.nan
 for r in fr: r.update(month=month.strftime("%Y-%m"),schedule=schedule,direction=direction)
 pred=pd.DataFrame({"decision_time":m.iloc[vi].decision_time.to_numpy(),"month":month.strftime("%Y-%m"),"schedule":schedule,"direction":direction,"d1_regime":reg,"label":y,"score":s,"p90_threshold_from_previous_month":thr,"selected_p90":sel})
 return row,fr,pred

def mean(s):
 x=pd.to_numeric(s,errors="coerce").to_numpy(float); x=x[np.isfinite(x)]; return float(x.mean()) if len(x) else math.nan
def median(s):
 x=pd.to_numeric(s,errors="coerce").to_numpy(float); x=x[np.isfinite(x)]; return float(np.median(x)) if len(x) else math.nan

def side_support(monthly,schedule,direction,g):
 e=monthly[(monthly.schedule=="EXPANDING")&(monthly.direction==direction)&monthly.available]
 c=monthly[(monthly.schedule==schedule)&(monthly.direction==direction)&monthly.available]
 j=e.merge(c,on=["month","year","halfyear","direction"],suffixes=("_exp","_cur")); j["adi"]=j.auc_cur-j.auc_exp; j["ldi"]=j.p90_label_lift_cur-j.p90_label_lift_exp
 ym={str(y):mean(j.loc[j.year==y,"p90_label_lift_cur"]) for y in (2024,2025)}; dm={r:mean(j[f"d1_{r.lower()}_p90_lift_cur"]) for r in ("UP","NEUTRAL","DOWN")}
 ph=j.assign(v=j.ldi.clip(lower=0)).groupby("halfyear").v.sum(); total=float(ph.sum()); share=float(ph.max()/total) if total>0 else math.inf
 vals={"available_months":len(j)>=g.available_months_min,"mean_auc_improvement":mean(j.adi)>=g.mean_auc_improvement_min,"median_auc_improvement_positive":median(j.adi)>0,"positive_auc_months":int((j.adi>0).sum())>=g.positive_auc_months_min,"mean_p90_lift_improvement":mean(j.ldi)>=g.mean_p90_lift_improvement_min,"positive_p90_lift_months":int((j.ldi>0).sum())>=g.positive_p90_lift_months_min,"positive_2024_and_2025":all(np.isfinite(v) and v>0 for v in ym.values()),"positive_all_d1_regimes":all(np.isfinite(v) and v>0 for v in dm.values()),"max_single_halfyear_dependency":np.isfinite(share) and share<=.5,"score_psi_median":median(j.score_psi_vs_previous_month_cur)<=g.score_psi_median_max}
 return {"schedule":schedule,"direction":direction,"available_paired_months":len(j),"mean_auc_improvement":mean(j.adi),"median_auc_improvement":median(j.adi),"positive_auc_improvement_months":int((j.adi>0).sum()),"mean_p90_label_lift_improvement":mean(j.ldi),"positive_p90_lift_improvement_months":int((j.ldi>0).sum()),"mean_schedule_p90_lift_by_year":ym,"mean_schedule_p90_lift_by_d1":dm,"max_positive_lift_halfyear_share":share,"median_score_psi":median(j.score_psi_vs_previous_month_cur),"gate_results":{k:bool(v) for k,v in vals.items()},"pass":bool(all(vals.values()))}

def support(monthly,g):
 rec=[side_support(monthly,s,d,g) for s in list(SCHEDULES)[1:] for d in DIRECTIONS]; flat=[]
 for r in rec:
  z={k:v for k,v in r.items() if k not in ("gate_results","mean_schedule_p90_lift_by_year","mean_schedule_p90_lift_by_d1")}; z.update({f"gate_{k}":v for k,v in r["gate_results"].items()}); z.update({f"year_{k}_mean_p90_lift":v for k,v in r["mean_schedule_p90_lift_by_year"].items()}); z.update({f"d1_{k.lower()}_mean_p90_lift":v for k,v in r["mean_schedule_p90_lift_by_d1"].items()}); flat.append(z)
 ok=[s for s in list(SCHEDULES)[1:] if all(r["pass"] for r in rec if r["schedule"]==s)]
 return pd.DataFrame(flat),{"formal_supported_schedules":ok,"formal_supported_schedule_count":len(ok),"same_schedule_must_pass_long_and_short":True,"direction_specific_rescue":False,"candidate_pnl_opened":False,"2026_opened":False,"automatic_promotion":False,"shadow":False,"discord":False,"mt5_orders":False,"live_ready":False,"final_signal":False,"direction_records":rec}

def run(state_dir,out_dir,cfg=FormalConfig(),gates=SupportGates()):
 out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); X,m,cols,manifest=load_state_inputs(state_dir); dump(out/"input_manifest.json",manifest); dump(out/"frozen_execution_config.json",{"contract_id":CONTRACT_ID,"formal_config":asdict(cfg),"support_gates":asdict(gates),"formal_months":[x.strftime("%Y-%m") for x in MONTHS]})
 rows=[]; fps=[]; preds=[]
 for month in MONTHS:
  for s in SCHEDULES:
   for d in DIRECTIONS:
    r,f,p=one(X,m,cols,month,s,d,cfg); rows.append(r); fps+=f
    if not p.empty: preds.append(p)
    print(f"{month:%Y-%m} {s:11s} {d:5s} available={r['available']} train={r['train_rows']}",flush=True)
 monthly=pd.DataFrame(rows); monthly.to_csv(out/"monthly_metrics.csv",index=False); pd.DataFrame(fps).to_csv(out/"feature_psi.csv",index=False)
 if preds: pd.concat(preds,ignore_index=True).to_csv(out/"monthly_prediction_audit.csv.gz",index=False,compression="gzip")
 ac=[c for c in monthly if c.startswith("audit_")]; total=int(monthly[ac].fillna(0).to_numpy(float).sum())
 leak={"status":"PASS" if total==0 else "FAIL","total_violation_count":total,"columns":{c:int(monthly[c].fillna(0).sum()) for c in ac},"selection_uses_2026":False,"future_validation_label_used_in_training":False,"unresolved_label_used_in_training":False,"validation_month_used_for_calibration":False}; dump(out/"leakage_audit.json",leak)
 if total: raise ContractError(f"Aggregated leakage audit failed: {leak}")
 sdf,ss=support(monthly,gates); sdf.to_csv(out/"direction_schedule_support.csv",index=False); dump(out/"schedule_support.json",ss); ok=ss["formal_supported_schedules"]
 status="BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_SCHEDULE_SUPPORT_FOUND_NO_PNL" if ok else "BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_NO_SUPPORTED_SCHEDULE"
 decision=f"Supported schedule(s): {', '.join(ok)}. PnL and 2026 remain unopened pending a new contract." if ok else "No rolling schedule passed every frozen LONG and SHORT gate against EXPANDING. No rescue is authorized."
 result={"contract_id":CONTRACT_ID,"formal_status":status,"decision":decision,"formal_months":24,"monthly_schedule_direction_rows":len(monthly),"available_rows":int(monthly.available.sum()),"unavailable_rows":int((~monthly.available).sum()),"leakage_audit":leak,"support":ss,"candidate_pnl_opened":False,"2026_opened":False,"shadow":False,"discord":False,"mt5_orders":False,"live_ready":False,"final_signal":False,"environment":{"python":sys.version,"platform":platform.platform(),"lightgbm":lgb.__version__,"numpy":np.__version__,"pandas":pd.__version__}}; dump(out/"result.json",result)
 lines=["# BTC AI V1 — rolling adaptive recalibration result","",f"Formal status: **`{status}`**","",decision,"","No PnL or 2026 diagnostic was opened."]; (out/"BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_RESULT.md").write_text("\n".join(lines),encoding="utf-8")
 files=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name!="output_manifest.json": files.append({"file":p.name,"bytes":p.stat().st_size,"sha256":sha256(p)})
 dump(out/"output_manifest.json",{"contract_id":CONTRACT_ID,"files":files}); return result

def main(argv:Sequence[str]|None=None):
 p=argparse.ArgumentParser(); p.add_argument("--state-dir",type=Path,required=True); p.add_argument("--out-dir",type=Path,required=True); p.add_argument("--n-jobs",type=int,default=1); a=p.parse_args(argv)
 try: result=run(a.state_dir,a.out_dir,FormalConfig(n_jobs=a.n_jobs),SupportGates())
 except ContractError as e: print(f"[FAIL_CLOSED] {e}",file=sys.stderr); return 2
 print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
