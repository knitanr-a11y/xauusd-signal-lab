from __future__ import annotations
import hashlib,json,math,sys,warnings
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score
BASE=Path('/mnt/data/btc_ai_v1_stage02');sys.path.insert(0,str(BASE))
import stage02_capability as s
import stage03_development_value as d3
warnings.filterwarnings('ignore')
ROOT=Path('/mnt/data/btc_ai_v1_cycle3');PREP=Path('/mnt/data/btc_ai_v1_cycle2/prepared');IN=ROOT/'stage14_outputs';OUT=ROOT/'stage15_outputs';OUT.mkdir(exist_ok=True);M1=Path('/mnt/data/BTCUSD#_M1_20230101_20260803.csv');SEED=20260803
def ns(x):return np.datetime64(x).astype('datetime64[ns]').astype(np.int64)
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def model(mid):
 if mid=='XGB_D3':return XGBClassifier(n_estimators=250,learning_rate=.03,max_depth=3,min_child_weight=50,subsample=.8,colsample_bytree=.8,reg_lambda=2.,tree_method='hist',random_state=SEED,n_jobs=4,eval_metric='logloss')
 if mid=='EXTRA_D8':return Pipeline([('imp',SimpleImputer(strategy='median')),('model',ExtraTreesClassifier(n_estimators=300,max_depth=8,min_samples_leaf=100,max_features=.7,class_weight='balanced',random_state=SEED,n_jobs=6))])
 raise ValueError(mid)
def first(sc,t,prev):
 a=sc>=t;p=np.empty(len(sc),bool);p[0]=prev>=t;p[1:]=a[:-1];return a&~p
def cool(sc,t):
 ids=np.flatnonzero(sc>=t);keep=[];last=-10
 for x in ids:
  if x-last>=4:keep.append(x);last=x
 o=np.zeros(len(sc),bool)
 if keep:o[np.array(keep)]=1
 return o
def pf(gp,gl):return gp/gl if gl>0 else (math.inf if gp>0 else 0.)
def replay(ev,d,stop,target,horizon,feat,m1):
 mt=pd.to_datetime(m1.time,format='%Y.%m.%d %H:%M:%S').values.astype('datetime64[ns]').astype(np.int64);op=m1.open.to_numpy(float);hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float);cont=d3.forward_contiguous_lengths(mt,1440)
 ens=feat.entry_time.values.astype('datetime64[ns]').astype(np.int64);pos=np.searchsorted(mt,ens);v=pos<len(mt);v[v]&=(mt[pos[v]]==ens[v]);entry=np.where(v,pos,-1);atr=feat.atr14.to_numpy(float);last=-1;rows=[]
 for g in ev:
  e=entry[g]
  if e<0 or e<=last or not np.isfinite(atr[g]):continue
  adj=op[e]+22.5 if d==1 else op[e]-22.5;sl=adj-d*stop*atr[g];tp=adj+d*stop*target*atr[g];p=None;ex=None
  lim=min(int(horizon),int(cont[e]))
  for k in range(lim):
   hs=(lo[e+k]<=sl) if d==1 else (hi[e+k]>=sl);ht=(hi[e+k]>=tp) if d==1 else (lo[e+k]<=tp)
   if hs:p=-stop*atr[g];ex=e+k;break
   if ht:p=stop*target*atr[g];ex=e+k;break
  if p is None:
   if cont[e]<horizon:continue
   ex=e+horizon-1;p=(cl[ex]-adj)*d
  last=ex;rows.append((g,e,ex,p))
 return rows
def main():
 fs=json.loads((PREP/'feature_sets.json').read_text());full=fs['FULL_CAUSAL'];Xall=np.load(PREP/'features.npy',mmap_mode='r');m=np.load(PREP/'meta.npz');t=m['decision_ns'];y=m['label_short'];mat=m['mature_ns'];dt=pd.to_datetime(t)
 final=pd.read_csv(IN/'diverse_ai_exploratory_survivors.csv');train=(t>=ns('2023-01-01'))&(t<ns('2025-07-01'))&(y>=0)&(mat<ns('2025-07-01'));cal=(t>=ns('2025-07-01'))&(t<ns('2026-01-01'))&(y>=0)&(mat<ns('2026-01-01'));test=(t>=ns('2026-01-01'))&(t<ns('2026-08-01'))&(y>=0);m1=pd.read_csv(M1,sep=';',usecols=['time','open','high','low','close'])
 frozen=[];summary=[];monthly=[]
 for _,r in final.iterrows():
  cols=fs[r.feature_set];idx=np.array([full.index(c) for c in cols]);X=Xall[:,idx];md=model(r.model_id);md.fit(X[train],y[train]);cs=md.predict_proba(X[cal])[:,1];ts=md.predict_proba(X[test])[:,1];thr=float(np.quantile(cs,r.percentile));em=first(ts,thr,float(cs[-1])) if r.event_policy=='FIRST_CROSS_FROM_BELOW' else cool(ts,thr);gidx=np.flatnonzero(test);ev=gidx[em];
  for g,sc in zip(ev,ts[em]):frozen.append({'candidate_id':r.candidate_id,'decision_time':pd.Timestamp(dt[g]).strftime('%Y-%m-%d %H:%M:%S'),'global_index':int(g),'score':float(sc),'threshold':thr})
  led=replay(ev,-1,float(r.stop_atr),float(r.target_R),int(r.horizon_min),s.build_feature_frame(),m1);p=np.array([x[3] for x in led]);gp=p[p>0].sum();gl=-p[p<0].sum();net=p.sum();eq=np.cumsum(p);peak=np.maximum.accumulate(np.r_[0,eq]);dd=float(np.max(peak[1:]-eq)) if len(eq) else 0.;months=pd.to_datetime([dt[x[0]] for x in led]).strftime('%Y-%m');cnt=pd.Series(months).value_counts().reindex(pd.period_range('2026-01','2026-07',freq='M').astype(str),fill_value=0)
  summary.append({'candidate_id':r.candidate_id,'model_id':r.model_id,'feature_set':r.feature_set,'evaluation_calendar_months':7,'raw_events':len(ev),'completed_trades':len(led),'trades_per_calendar_month':len(led)/7,'active_months':int((cnt>0).sum()),'monthly_min':int(cnt.min()),'monthly_median':float(cnt.median()),'monthly_max':int(cnt.max()),'calibration_auc':float(roc_auc_score(y[cal],cs)),'diagnostic_2026_auc':float(roc_auc_score(y[test],ts)),'event_label_hit_rate':float(y[ev].mean()),'baseline_short_label_rate':float(y[test].mean()),'pf':pf(gp,gl),'net':float(net),'max_dd':dd})
  for mm,n in cnt.items():monthly.append({'candidate_id':r.candidate_id,'month':mm,'completed_trades':int(n)})
 f=pd.DataFrame(frozen).sort_values(['candidate_id','decision_time']);res=pd.DataFrame(summary);f.to_csv(OUT/'diverse_ai_2026_frozen_events_diagnostic.csv',index=False);res.to_csv(OUT/'diverse_ai_2026_diagnostic_result.csv',index=False);pd.DataFrame(monthly).to_csv(OUT/'diverse_ai_2026_diagnostic_monthly_counts.csv',index=False)
 manifest={'stage':'BTC_AI_V1_15_DIVERSE_AI_2026_CONSUMED_PERIOD_DIAGNOSTIC','status':'COMPLETE_DIAGNOSTIC_ONLY','calendar_months':7,'candidate_count':len(res),'events_sha256':sha(OUT/'diverse_ai_2026_frozen_events_diagnostic.csv'),'results_sha256':sha(OUT/'diverse_ai_2026_diagnostic_result.csv'),'support_claim':False,'selection_use':False}
 (OUT/'stage15_summary.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));print(res.to_string(index=False))
if __name__=='__main__':main()
