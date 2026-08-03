from __future__ import annotations
import json,warnings
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import ks_2samp
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss
warnings.filterwarnings('ignore')
ROOT=Path('/mnt/data/btc_ai_v1_cycle2');PREP=ROOT/'prepared';OUT=ROOT/'stage11_outputs';OUT.mkdir(exist_ok=True);SEED=20260803
def ns(s):return np.datetime64(s).astype('datetime64[ns]').astype(np.int64)
def model(mid):
 if mid=='LOGIT_L2':lr=LogisticRegression(penalty='l2',C=.25,solver='lbfgs',max_iter=1000,class_weight='balanced',random_state=SEED)
 elif mid=='LOGIT_EN50':lr=LogisticRegression(penalty='elasticnet',l1_ratio=.5,C=.1,solver='saga',max_iter=1500,class_weight='balanced',random_state=SEED,n_jobs=1)
 else:raise ValueError(mid)
 return Pipeline([('imp',SimpleImputer(strategy='median')),('sc',StandardScaler()),('model',lr)])
def psi(a,b,bins=10):
 a=np.asarray(a);b=np.asarray(b);a=a[np.isfinite(a)];b=b[np.isfinite(b)]
 if len(a)<100 or len(b)<100:return np.nan
 edges=np.unique(np.quantile(a,np.linspace(0,1,bins+1)))
 if len(edges)<3:return 0.
 edges[0]=-np.inf;edges[-1]=np.inf;pa=np.histogram(a,edges)[0]/len(a);pb=np.histogram(b,edges)[0]/len(b);eps=1e-6;pa=np.clip(pa,eps,None);pb=np.clip(pb,eps,None);return float(np.sum((pb-pa)*np.log(pb/pa)))
def first(sc,t,prev):
 a=sc>=t;p=np.empty(len(sc),bool);p[0]=prev>=t;p[1:]=a[:-1];return a&~p
def cool(sc,t):
 ids=np.flatnonzero(sc>=t);k=[];last=-10
 for x in ids:
  if x-last>=4:k.append(x);last=x
 o=np.zeros(len(sc),bool)
 if k:o[np.array(k)]=1
 return o
def main():
 fs=json.loads((PREP/'feature_sets.json').read_text());full=fs['FULL_CAUSAL'];Xall=np.load(PREP/'features.npy',mmap_mode='r');m=np.load(PREP/'meta.npz');t=m['decision_ns'];yL=m['label_long'];yS=m['label_short'];mat=m['mature_ns'];dt=pd.to_datetime(t)
 periods=[('2023H1','2023-01-01','2023-07-01'),('2023H2','2023-07-01','2024-01-01'),('2024H1','2024-01-01','2024-07-01'),('2024H2','2024-07-01','2025-01-01'),('2025H1','2025-01-01','2025-07-01'),('2025H2','2025-07-01','2026-01-01'),('2026_7M','2026-01-01','2026-08-01')];rates=[]
 for name,a,b in periods:
  mask=(t>=ns(a))&(t<ns(b))
  for side,y in [('LONG',yL),('SHORT',yS)]:
   v=mask&(y>=0);rates.append({'period':name,'side':side,'valid_rows':int(v.sum()),'positive_rate':float(y[v].mean()),'calendar_months':7 if name=='2026_7M' else 6})
 pd.DataFrame(rates).to_csv(OUT/'label_rate_by_period.csv',index=False);dev=(t>=ns('2024-01-01'))&(t<ns('2026-01-01'));fin=(t>=ns('2026-01-01'))&(t<ns('2026-08-01'));drift=[]
 for j,c in enumerate(full):
  a=np.asarray(Xall[dev,j],float);b=np.asarray(Xall[fin,j],float);af=a[np.isfinite(a)];bf=b[np.isfinite(b)]
  if len(af)<100 or len(bf)<100:continue
  sd=np.std(af);ks=ks_2samp(af,bf,method='asymp');drift.append({'feature':c,'dev_mean':float(np.mean(af)),'final_mean':float(np.mean(bf)),'standardized_mean_shift':float((np.mean(bf)-np.mean(af))/(sd if sd>1e-12 else 1)),'psi':psi(af,bf),'ks_stat':float(ks.statistic),'ks_p':float(ks.pvalue)})
 drift_df=pd.DataFrame(drift).sort_values(['psi','ks_stat'],ascending=False);drift_df.to_csv(OUT/'feature_drift_2026_vs_2024_2025.csv',index=False);finalists=pd.read_csv(ROOT/'stage07_outputs/second_cycle_finalist_registry.csv');train=(t>=ns('2023-01-01'))&(t<ns('2025-07-01'))&(yS>=0)&(mat<ns('2025-07-01'));cal=(t>=ns('2025-07-01'))&(t<ns('2026-01-01'))&(yS>=0)&(mat<ns('2026-01-01'));test=(t>=ns('2026-01-01'))&(t<ns('2026-08-01'))&(yS>=0);cache={};rows=[]
 for _,r in finalists.iterrows():
  key=(r.model_id,r.feature_set);cols=fs[r.feature_set];idx=np.array([full.index(c) for c in cols]);X=Xall[:,idx]
  if key not in cache:
   md=model(r.model_id);md.fit(X[train],yS[train]);cache[key]=(md.predict_proba(X[cal])[:,1],md.predict_proba(X[test])[:,1],np.flatnonzero(test))
  cs,ts,gidx=cache[key];thr=float(np.quantile(cs,float(r.percentile)));em=first(ts,thr,float(cs[-1])) if r.event_policy=='FIRST_CROSS_FROM_BELOW' else cool(ts,thr);ev=gidx[em];labels=yS[ev]
  rows.append({'candidate_id':r.candidate_id,'model_id':r.model_id,'feature_set':r.feature_set,'calibration_auc':roc_auc_score(yS[cal],cs),'final_auc':roc_auc_score(yS[test],ts),'calibration_brier':brier_score_loss(yS[cal],cs),'final_brier':brier_score_loss(yS[test],ts),'frozen_events':len(ev),'event_label_hit_rate':float(labels.mean()),'baseline_final_short_label_rate':float(yS[test].mean())})
 pd.DataFrame(rows).to_csv(OUT/'finalist_score_and_label_drift.csv',index=False);(OUT/'stage11_summary.json').write_text(json.dumps({'stage':'BTC_AI_V1_11_SECOND_CYCLE_REGIME_SHIFT_FORENSIC_NO_RESCUE','status':'COMPLETE_DIAGNOSTIC_ONLY','label_rates':rates,'top_feature_drift':drift_df.head(15).to_dict('records'),'finalist_diagnostics':rows,'candidate_selection_performed':False,'rescue_performed':False},indent=2))
if __name__=='__main__':main()
