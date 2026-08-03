from __future__ import annotations
import argparse, json, time, warnings
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
warnings.filterwarnings('ignore')
SEED=20260803
ROOT=Path('/mnt/data/btc_ai_v1_cycle3'); PREP=Path('/mnt/data/btc_ai_v1_cycle2/prepared'); OUT=ROOT/'model_scores'; OUT.mkdir(exist_ok=True)
FOLDS=[
 ('2024H1','2023-01-01','2023-07-01','2023-07-01','2024-01-01','2024-01-01','2024-07-01'),
 ('2024H2','2023-01-01','2024-01-01','2024-01-01','2024-07-01','2024-07-01','2025-01-01'),
 ('2025H1','2023-01-01','2024-07-01','2024-07-01','2025-01-01','2025-01-01','2025-07-01'),
 ('2025H2','2023-01-01','2025-01-01','2025-01-01','2025-07-01','2025-07-01','2026-01-01')]
def ns(s): return np.datetime64(s).astype('datetime64[ns]').astype(np.int64)
def model_for(mid):
 if mid=='XGB_D3':
  return XGBClassifier(n_estimators=250,learning_rate=.03,max_depth=3,min_child_weight=50,subsample=.8,colsample_bytree=.8,reg_lambda=2.0,tree_method='hist',random_state=SEED,n_jobs=1,eval_metric='logloss')
 if mid=='CAT_D4':
  return CatBoostClassifier(iterations=250,learning_rate=.03,depth=4,l2_leaf_reg=5.0,random_seed=SEED,loss_function='Logloss',verbose=False,thread_count=1,allow_writing_files=False)
 if mid=='EXTRA_D8':
  m=ExtraTreesClassifier(n_estimators=300,max_depth=8,min_samples_leaf=100,max_features=.7,class_weight='balanced',random_state=SEED,n_jobs=6)
  return Pipeline([('imp',SimpleImputer(strategy='median')),('model',m)])
 if mid=='HGB_L15':
  return HistGradientBoostingClassifier(max_iter=250,learning_rate=.04,max_leaf_nodes=15,min_samples_leaf=200,l2_regularization=2.0,random_state=SEED)
 raise ValueError(mid)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);ap.add_argument('--feature-set',required=True);ap.add_argument('--direction',required=True,choices=['LONG','SHORT']);a=ap.parse_args()
 tag=f'{a.model}__{a.feature_set}__{a.direction}';out=OUT/f'{tag}.npz';diag=OUT/f'{tag}.json'
 if out.exists() and diag.exists():print('SKIP',tag);return
 fs=json.loads((PREP/'feature_sets.json').read_text());full=fs['FULL_CAUSAL'];cols=fs[a.feature_set];idx=np.array([full.index(c) for c in cols]);Xall=np.load(PREP/'features.npy',mmap_mode='r');X=Xall[:,idx]
 meta=np.load(PREP/'meta.npz');t=meta['decision_ns'];mature=meta['mature_ns'];y=meta['label_long'] if a.direction=='LONG' else meta['label_short']
 arrays={};ds=[]
 for fold,tr0,tr1,ca0,ca1,va0,va1 in FOLDS:
  train=(t>=ns(tr0))&(t<ns(tr1))&(y>=0)&(mature<ns(tr1));cal=(t>=ns(ca0))&(t<ns(ca1))&(y>=0)&(mature<ns(ca1));val=(t>=ns(va0))&(t<ns(va1))
  md=model_for(a.model);st=time.time();md.fit(X[train],y[train]);cs=md.predict_proba(X[cal])[:,1].astype(np.float32);vs=md.predict_proba(X[val])[:,1].astype(np.float32);sec=time.time()-st
  auc=float(roc_auc_score(y[cal],cs)) if len(np.unique(y[cal]))>1 else float('nan')
  arrays[f'{fold}_val_idx']=np.flatnonzero(val).astype(np.int32);arrays[f'{fold}_val_score']=vs;arrays[f'{fold}_cal_score']=cs
  ds.append({'fold':fold,'train_rows':int(train.sum()),'calibration_rows':int(cal.sum()),'validation_rows':int(val.sum()),'calibration_positive_rate':float(y[cal].mean()),'calibration_auc':auc,'seconds':sec})
 np.savez_compressed(out,**arrays);diag.write_text(json.dumps({'tag':tag,'model_id':a.model,'feature_set':a.feature_set,'direction':a.direction,'diagnostics':ds},indent=2),encoding='utf-8');print('DONE',tag,round(sum(x['seconds'] for x in ds),2))
if __name__=='__main__':main()
