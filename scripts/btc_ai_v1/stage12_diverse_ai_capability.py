from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path('/mnt/data/btc_ai_v1_cycle3');PREP=Path('/mnt/data/btc_ai_v1_cycle2/prepared');SCORES=ROOT/'model_scores';OUT=ROOT/'stage12_outputs';OUT.mkdir(exist_ok=True)
MODELS=['XGB_D3','CAT_D4','EXTRA_D8','HGB_L15','RANK_ENSEMBLE'];FSETS=['MTF_CONTEXT','FULL_CAUSAL'];SIDES=['LONG','SHORT'];PCTS=[.9,.95,.975];POL=['FIRST_CROSS_FROM_BELOW','FOUR_M15_BAR_COOLDOWN'];FOLDS=['2024H1','2024H2','2025H1','2025H2']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
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
 m=np.load(PREP/'meta.npz');t=pd.to_datetime(m['decision_ns']);entry=m['entry_idx'];month=t.strftime('%Y-%m');rows=[];events={};cidn=0;model_diag=[]
 for mid in MODELS:
  for fs in FSETS:
   for side in SIDES:
    z=np.load(SCORES/f'{mid}__{fs}__{side}.npz');fold_data={}
    jpath=SCORES/f'{mid}__{fs}__{side}.json'
    if jpath.exists():
     j=json.loads(jpath.read_text())
     for d in j.get('diagnostics',[]):model_diag.append({'model_id':mid,'feature_set':fs,'direction':side,**d})
    for fold in FOLDS:
     sc=z[f'{fold}_val_score'];cs=z[f'{fold}_cal_score'];idx=z[f'{fold}_val_idx'];fold_data[fold]=(idx,sc,float(cs[-1]),{p:float(np.quantile(cs,p)) for p in PCTS})
    for p in PCTS:
     for policy in POL:
      cid=f'ML3_{cidn:03d}';cidn+=1;parts=[];fc={}
      for fold in FOLDS:
       idx,sc,prev,thr=fold_data[fold];em=first(sc,thr[p],prev) if policy==POL[0] else cool(sc,thr[p]);ev=idx[em].astype(np.int32);parts.append(ev);fc[fold]=len(ev)
      ev=np.sort(np.concatenate(parts)).astype(np.int32);events[cid]=ev;cnt=pd.Series(month[ev]).value_counts().reindex(pd.period_range('2024-01','2025-12',freq='M').astype(str),fill_value=0);invalid=int((entry[ev]<0).sum());ir=invalid/len(ev) if len(ev) else 1.;active=int((cnt>0).sum());share=float(cnt.max()/len(ev)) if len(ev) else 1.;ok=min(fc.values())>=20 and active>=18 and share<=.25 and ir<=.01
      rows.append({'candidate_id':cid,'family':'DIVERSE_AI_DIRECTIONAL_RANK','model_id':mid,'feature_set':fs,'direction':side,'percentile':p,'event_policy':policy,**{f'events_{k}':v for k,v in fc.items()},'events_total':len(ev),'evaluation_calendar_months':24,'active_months':active,'events_per_calendar_month':len(ev)/24,'zero_event_months':int((cnt==0).sum()),'monthly_min':int(cnt.min()),'monthly_median':float(cnt.median()),'monthly_max':int(cnt.max()),'max_month_event_share':share,'invalid_entry_m1':invalid,'invalid_entry_rate':ir,'explicit_capability_pass':ok})
 assert cidn==120
 reg=pd.DataFrame(rows);passed=reg[reg.explicit_capability_pass].copy();passed['min_fold_events']=passed[[f'events_{f}' for f in FOLDS]].min(axis=1);passed['fold_balance_ratio']=passed[[f'events_{f}' for f in FOLDS]].min(axis=1)/passed[[f'events_{f}' for f in FOLDS]].max(axis=1);passed=passed.sort_values(['active_months','fold_balance_ratio','min_fold_events','max_month_event_share','candidate_id'],ascending=[False,False,False,True,True])
 sel=[];rej=[]
 for _,r in passed.iterrows():
  ev=events[r.candidate_id];mx=0.;dup=''
  for sid in sel:
   sev=events[sid];inter=np.intersect1d(ev,sev,assume_unique=True).size;union=len(ev)+len(sev)-inter;j=inter/union if union else 1.
   if j>mx:mx=j;dup=sid
  if mx>.95:rej.append({'candidate_id':r.candidate_id,'near_duplicate_of':dup,'jaccard':mx});continue
  sel.append(r.candidate_id)
  if len(sel)>=60:break
 surv=reg[reg.candidate_id.isin(sel)].copy();surv['selection_rank']=surv.candidate_id.map({x:i+1 for i,x in enumerate(sel)});surv=surv.sort_values('selection_rank')
 reg.to_csv(OUT/'diverse_ai_candidate_registry.csv',index=False);surv.to_csv(OUT/'diverse_ai_capability_survivors.csv',index=False);pd.DataFrame(rej).to_csv(OUT/'near_duplicate_rejections.csv',index=False);pd.DataFrame(model_diag).to_csv(OUT/'model_calibration_diagnostics.csv',index=False);np.savez_compressed(OUT/'candidate_events.npz',**events)
 summary={'stage':'BTC_AI_V1_12_DIVERSE_AI_CAPABILITY','status':'COMPLETE_OUTCOME_BLIND','evaluation_calendar_months':24,'raw_candidates':120,'explicit_pass':int(reg.explicit_capability_pass.sum()),'survivors':len(surv),'survivor_models':surv.model_id.value_counts().to_dict(),'survivor_directions':surv.direction.value_counts().to_dict(),'events_range':[int(surv.events_total.min()),int(surv.events_total.max())],'events_per_month_range':[float(surv.events_per_calendar_month.min()),float(surv.events_per_calendar_month.max())],'registry_sha256':sha(OUT/'diverse_ai_candidate_registry.csv'),'survivors_sha256':sha(OUT/'diverse_ai_capability_survivors.csv'),'2026_used_for_selection':False}
 (OUT/'stage12_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
