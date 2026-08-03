from __future__ import annotations
import hashlib,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd
BASE=Path('/mnt/data/btc_ai_v1_stage02');sys.path.insert(0,str(BASE))
import stage02_capability as s
import stage03_development_value as d3
import stage04_robustness as r4
ROOT=Path('/mnt/data');HERE=Path('/mnt/data/btc_ai_v1_cycle3');IN5=HERE/'stage12_outputs';IN6=HERE/'stage13_outputs';OUT=HERE/'stage14_outputs';OUT.mkdir(exist_ok=True);M1=ROOT/'BTCUSD#_M1_20230101_20260803.csv';ITER=2000;SEED=20260803
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def pf(gp,gl):return gp/gl if gl>0 else (math.inf if gp>0 else 0.)
def ledger(ev,d,si,ri,hi,g2p,entry,atr,month,op,cl,cont,fsl,ftp):
 di=0 if d==1 else 1;hz=int(d3.HORIZONS[hi]);sm=float(d3.STOP_MULT[si]);rr=float(d3.R_MULT[ri]);ti=int(d3.TARGET_MAP[si,ri]);rows=[];last=-1
 for g in ev:
  u=g2p[g];e=entry[g]
  if u<0 or e<0 or e<=last:continue
  sl=int(fsl[di,si,u]);tp=int(ftp[di,ti,u])
  if sl<hz and sl<=tp:p=-sm*atr[g];ex=e+sl
  elif tp<hz:p=sm*rr*atr[g];ex=e+tp
  else:
   if cont[e]<hz:continue
   ex=e+hz-1;adj=op[e]+22.5 if d==1 else op[e]-22.5;p=(cl[ex]-adj)*d
  last=ex;rows.append((int(g),int(e),int(ex),int(month[g]),float(p)))
 return rows
def boot(led,rng):
 mr={m:[] for m in range(24)}
 for x in led:mr[x[3]].append(x[4])
 nets=np.empty(ITER);pfs=np.empty(ITER)
 for i in range(ITER):
  arr=[]
  for m in rng.choice(np.arange(24),24,replace=True):arr.extend(mr[int(m)])
  a=np.asarray(arr);gp=a[a>0].sum() if len(a) else 0.;gl=-a[a<0].sum() if len(a) else 0.;nets[i]=a.sum() if len(a) else 0.;pfs[i]=pf(gp,gl)
 return nets,pfs
def main():
 feat=s.build_feature_frame();short=pd.read_csv(IN6/'diverse_ai_development_shortlist.csv');grid=pd.read_csv(IN6/'diverse_ai_development_grid_all.csv');z=np.load(IN5/'candidate_events.npz');event={cid:z[cid].astype(np.int32) for cid in short.candidate_id};dev=(feat.decision_time>=pd.Timestamp('2024-01-01'))&(feat.decision_time<pd.Timestamp('2026-01-01'))
 m=pd.read_csv(M1,sep=';',usecols=['time','open','high','low','close']);mt=pd.to_datetime(m.time,format='%Y.%m.%d %H:%M:%S').values.astype('datetime64[ns]').astype(np.int64);op=m.open.to_numpy(float);h=m.high.to_numpy(float);l=m.low.to_numpy(float);cl=m.close.to_numpy(float);cont=d3.forward_contiguous_lengths(mt,1440)
 ens=feat.entry_time.values.astype('datetime64[ns]').astype(np.int64);pos=np.searchsorted(mt,ens);v=pos<len(mt);v[v]&=(mt[pos[v]]==ens[v]);entry=np.where(v,pos,-1).astype(np.int64);atr=feat.atr14.to_numpy(float);dns=feat.decision_time.values.astype('datetime64[ns]').astype(np.int64);month=((feat.decision_time.dt.year-2024)*12+(feat.decision_time.dt.month-1)).to_numpy(np.int16);ready=dev.to_numpy()&np.isfinite(atr)&(entry>=0);pool=np.flatnonzero(ready).astype(np.int32);g2p=np.full(len(feat),-1,np.int32);g2p[pool]=np.arange(len(pool),dtype=np.int32);fsl,ftp,_,_=d3.precompute_first_hits(pool,entry,atr,op,h,l,cont,d3.STOP_MULT,d3.TARGET_MULT);pbm={x:pool[month[pool]==x] for x in range(24)};rows=[]
 for _,sr in short.iterrows():
  cid=sr.candidate_id;ev=event[cid];d=1 if sr.direction=='LONG' else -1;si=int(np.where(np.isclose(d3.STOP_MULT,sr.stop_atr))[0][0]);ri=int(np.where(np.isclose(d3.R_MULT,sr.target_R))[0][0]);hi=int(np.where(d3.HORIZONS==sr.horizon_min)[0][0]);led=ledger(ev,d,si,ri,hi,g2p,entry,atr,month,op,cl,cont,fsl,ftp);rng=np.random.default_rng(SEED+int(hashlib.sha256(cid.encode()).hexdigest()[:8],16));bn,bp=boot(led,rng);ec=np.bincount(month[ev],minlength=24);posm={}
  for mm in range(24):
   poolm=pbm[mm];mp={int(g):i for i,g in enumerate(poolm)};posm[mm]=np.asarray([mp[int(g)] for g in ev[month[ev]==mm] if int(g) in mp],np.int32)
  rn=np.empty(ITER);rp=np.empty(ITER);pn=np.empty(ITER);pp=np.empty(ITER)
  for it in range(ITER):
   ra=[];pa=[]
   for mm in range(24):
    poolm=pbm[mm];k=int(ec[mm])
    if k<=0 or len(poolm)==0:continue
    ra.append(np.sort(rng.choice(poolm,size=min(k,len(poolm)),replace=False)).astype(np.int32));p0=posm[mm]
    if len(p0):off=int(rng.integers(1,len(poolm))) if len(poolm)>1 else 0;pa.append(np.sort(poolm[(p0+off)%len(poolm)]).astype(np.int32))
   rev=np.sort(np.concatenate(ra)).astype(np.int32) if ra else np.empty(0,np.int32);pev=np.sort(np.concatenate(pa)).astype(np.int32) if pa else np.empty(0,np.int32);rt=d3.simulate_config_v2(rev,d,si,ri,hi,g2p,entry,atr,dns,month,op,cl,cont,fsl,ftp,d3.TARGET_MAP);pt=d3.simulate_config_v2(pev,d,si,ri,hi,g2p,entry,atr,dns,month,op,cl,cont,fsl,ftp,d3.TARGET_MAP);rn[it]=rt[5];rp[it]=pf(rt[3],rt[4]);pn[it]=pt[5];pp[it]=pf(pt[3],pt[4])
  neigh=[]
  for name,vals,cur in [('stop_atr',list(d3.STOP_MULT),float(sr.stop_atr)),('target_R',list(d3.R_MULT),float(sr.target_R)),('horizon_min',list(d3.HORIZONS),int(sr.horizon_min))]:
   ix=next(i for i,x in enumerate(vals) if np.isclose(x,cur))
   for j in (ix-1,ix+1):
    if 0<=j<len(vals):
     cond=(grid.candidate_id==cid)&np.isclose(grid.stop_atr,vals[j] if name=='stop_atr' else sr.stop_atr)&np.isclose(grid.target_R,vals[j] if name=='target_R' else sr.target_R)&(grid.horizon_min==(int(vals[j]) if name=='horizon_min' else int(sr.horizon_min)));q=grid[cond]
     if len(q):neigh.append(q.iloc[0])
  npf=np.array([x.pf for x in neigh]);nnet=np.array([x.net for x in neigh]);nfrac=float(np.mean((npf>1)&(nnet>0)));nmpf=float(np.median(npf));nmnet=float(np.median(nnet));dm={}
  for delay in (1,5):
   x=r4.simulate_delay(ev,d,float(sr.stop_atr),float(sr.target_R),int(sr.horizon_min),delay,entry,atr,op,h,l,cl,cont);dm[delay]=(pf(x[3],x[4]),x[5])
  vals={'bootstrap_net_positive_probability':float(np.mean(bn>0)),'bootstrap_pf_p05':float(np.quantile(bp,.05)),'matched_random_net_percentile':float(np.mean(rn<=sr.net)),'matched_random_pf_percentile':float(np.mean(rp<=sr.pf)),'pseudo_state_net_percentile':float(np.mean(pn<=sr.net)),'pseudo_state_pf_percentile':float(np.mean(pp<=sr.pf)),'neighborhood_positive_fraction':nfrac,'neighborhood_median_pf':nmpf,'neighborhood_median_net':nmnet};gates={'bootstrap':vals['bootstrap_net_positive_probability']>=.95 and vals['bootstrap_pf_p05']>=.95,'matched_random':vals['matched_random_net_percentile']>=.95 and vals['matched_random_pf_percentile']>=.95,'pseudo_state':vals['pseudo_state_net_percentile']>=.95 and vals['pseudo_state_pf_percentile']>=.95,'parameter_neighborhood':nfrac>=.5 and nmpf>=1 and nmnet>0}
  rows.append({'candidate_id':cid,'model_id':sr.model_id,'feature_set':sr.feature_set,'direction':sr.direction,'percentile':sr.percentile,'event_policy':sr.event_policy,'development_rank':int(sr.shortlist_rank),'stop_atr':sr.stop_atr,'target_R':sr.target_R,'horizon_min':int(sr.horizon_min),'evaluation_calendar_months':24,'development_trades':int(sr.trades),'development_trades_per_calendar_month':sr.trades_per_calendar_month,'active_months':int(sr.active_months),'monthly_min':int(sr.monthly_min),'monthly_median':sr.monthly_median,'monthly_max':int(sr.monthly_max),'development_pf':sr.pf,'development_net':sr.net,'development_max_dd':sr.max_dd,**vals,'delay_1_pf':dm[1][0],'delay_1_net':dm[1][1],'delay_5_pf':dm[5][0],'delay_5_net':dm[5][1],**{f'gate_{k}':v for k,v in gates.items()},'all_robustness_gates_pass':all(gates.values())})
 res=pd.DataFrame(rows).sort_values('development_rank');res.to_csv(OUT/'diverse_ai_robustness_results.csv',index=False);passed=res[res.all_robustness_gates_pass].sort_values('development_rank');final=[]
 for _,r in passed.iterrows():
  ev=event[r.candidate_id];ok=True
  for fr in final:
   fe=event[fr['candidate_id']];inter=np.intersect1d(ev,fe,assume_unique=True).size;u=len(ev)+len(fe)-inter
   if inter/u>.8:ok=False;break
  if ok:q=r.to_dict();q['finalist_rank']=len(final)+1;final.append(q)
  if len(final)>=5:break
 fdf=pd.DataFrame(final);fdf.to_csv(OUT/'diverse_ai_exploratory_survivors.csv',index=False);summary={'stage':'BTC_AI_V1_14_DIVERSE_AI_ROBUSTNESS','status':'COMPLETE_EXPLORATORY_SURVIVORS_FROZEN','evaluation_calendar_months':24,'shortlist_count':len(res),'all_robustness_pass':int(res.all_robustness_gates_pass.sum()),'exploratory_survivors':fdf.candidate_id.tolist() if len(fdf) else [],'classification_ceiling':'EXPLORATORY_PROSPECTIVE_ONLY','results_sha256':sha(OUT/'diverse_ai_robustness_results.csv'),'survivor_sha256':sha(OUT/'diverse_ai_exploratory_survivors.csv')};(OUT/'stage14_summary.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()
