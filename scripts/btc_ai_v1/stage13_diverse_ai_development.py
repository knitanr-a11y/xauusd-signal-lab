from __future__ import annotations
import hashlib,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd
from numba import njit
BASE=Path('/mnt/data/btc_ai_v1_stage02');sys.path.insert(0,str(BASE))
import stage02_capability as s
import stage03_development_value as d3
ROOT=Path('/mnt/data');HERE=Path('/mnt/data/btc_ai_v1_cycle3');IN=HERE/'stage12_outputs';OUT=HERE/'stage13_outputs';OUT.mkdir(exist_ok=True);M1=ROOT/'BTCUSD#_M1_20230101_20260803.csv'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def pf(gp,gl):return gp/gl if gl>0 else (math.inf if gp>0 else 0.)
@njit(cache=True)
def sim(ev,direction,si,ri,hi,g2u,entry,atr,decision_ns,month_id,m1open,m1close,contig,fsl,ftp):
 di=0 if direction==1 else 1;hz=d3.HORIZONS[hi];sm=d3.STOP_MULT[si];rr=d3.R_MULT[ri];ti=d3.TARGET_MAP[si,ri]
 total=invalid=supp=0;gp=gl=net=peak=ddmax=0.;fn=np.zeros(4,np.int32);fgp=np.zeros(4);fgl=np.zeros(4);fnet=np.zeros(4);mgp=np.zeros(24);mn=np.zeros(24,np.int32);last=-1
 for g in ev:
  u=g2u[g]
  if u<0:continue
  e=entry[g]
  if e<0:invalid+=1;continue
  if e<=last:supp+=1;continue
  sl=int(fsl[di,si,u]);tp=int(ftp[di,ti,u]);pnl=0.;ex=-1
  if sl<hz and sl<=tp:pnl=-sm*atr[g];ex=e+sl
  elif tp<hz:pnl=sm*rr*atr[g];ex=e+tp
  else:
   if contig[e]<hz:invalid+=1;continue
   ex=e+hz-1;adj=m1open[e]+22.5 if direction==1 else m1open[e]-22.5;pnl=(m1close[ex]-adj)*direction
  total+=1;last=ex;fi=d3.fold_id_from_ns(decision_ns[g]);mi=month_id[g];fn[fi]+=1;mn[mi]+=1
  if pnl>0:gp+=pnl;fgp[fi]+=pnl;mgp[mi]+=pnl
  elif pnl<0:gl+=-pnl;fgl[fi]+=-pnl
  net+=pnl;fnet[fi]+=pnl;peak=max(peak,net);ddmax=max(ddmax,peak-net)
 return total,invalid,supp,gp,gl,net,ddmax,fn,fgp,fgl,fnet,mgp,mn
def main():
 feat=s.build_feature_frame();surv=pd.read_csv(IN/'diverse_ai_capability_survivors.csv');z=np.load(IN/'candidate_events.npz');events={cid:z[cid].astype(np.int32) for cid in surv.candidate_id};union=np.unique(np.concatenate(list(events.values()))).astype(np.int32);g2u=np.full(len(feat),-1,np.int32);g2u[union]=np.arange(len(union),dtype=np.int32)
 m=pd.read_csv(M1,sep=';',usecols=['time','open','high','low','close']);mt=pd.to_datetime(m.time,format='%Y.%m.%d %H:%M:%S').values.astype('datetime64[ns]').astype(np.int64);op=m.open.to_numpy(float);hi0=m.high.to_numpy(float);lo0=m.low.to_numpy(float);cl=m.close.to_numpy(float);cont=d3.forward_contiguous_lengths(mt,1440)
 ens=feat.entry_time.values.astype('datetime64[ns]').astype(np.int64);pos=np.searchsorted(mt,ens);v=pos<len(mt);v[v]&=(mt[pos[v]]==ens[v]);entry=np.where(v,pos,-1).astype(np.int64);atr=feat.atr14.to_numpy(float);dns=feat.decision_time.values.astype('datetime64[ns]').astype(np.int64);month=((feat.decision_time.dt.year-2024)*12+(feat.decision_time.dt.month-1)).to_numpy(np.int16);fsl,ftp,_,_=d3.precompute_first_hits(union,entry,atr,op,hi0,lo0,cont,d3.STOP_MULT,d3.TARGET_MULT);rows=[];monthly=[]
 for _,c in surv.iterrows():
  ev=events[c.candidate_id];direction=1 if c.direction=='LONG' else -1
  for si,sm in enumerate(d3.STOP_MULT):
   for ri,rr in enumerate(d3.R_MULT):
    for hi,hz in enumerate(d3.HORIZONS):
     total,invalid,supp,gp,gl,net,dd,fn,fgp,fgl,fnet,mgp,mn=sim(ev,direction,si,ri,hi,g2u,entry,atr,dns,month,op,cl,cont,fsl,ftp);fp=np.array([pf(fgp[i],fgl[i]) for i in range(4)]);agg=pf(gp,gl);posf=int(np.sum((fp>1)&(fnet>0)));worst=float(fp.min());nd=net/dd if dd>0 else (math.inf if net>0 else 0.);share=float(mgp.max()/gp) if gp>0 else 1.;ir=invalid/(len(ev)-supp) if len(ev)>supp else 1.;active=int((mn>0).sum());gates={'min_total':total>=120,'min_each_fold':bool(np.all(fn>=20)),'pf':agg>=1.15,'net':net>0,'positive_folds':posf>=3,'worst_fold_pf':worst>=.8,'net_dd':nd>=.25,'month_share':share<=.5}
     rows.append({'candidate_id':c.candidate_id,'family':c.family,'model_id':c.model_id,'feature_set':c.feature_set,'direction':c.direction,'percentile':c.percentile,'event_policy':c.event_policy,'stop_atr':sm,'target_R':rr,'horizon_min':int(hz),'raw_events':len(ev),'trades':int(total),'evaluation_calendar_months':24,'active_months':active,'trades_per_calendar_month':total/24,'zero_trade_months':int((mn==0).sum()),'monthly_min':int(mn.min()),'monthly_median':float(np.median(mn)),'monthly_max':int(mn.max()),'invalid':int(invalid),'suppressed_overlap':int(supp),'invalid_rate':ir,'gross_profit':gp,'gross_loss':gl,'pf':agg,'net':net,'max_dd':dd,'net_to_dd':nd,'positive_folds':posf,'worst_fold_pf':worst,'single_month_gp_share':share,**{f'{nm}_trades':int(fn[i]) for i,nm in enumerate(['2024H1','2024H2','2025H1','2025H2'])},**{f'{nm}_pf':fp[i] for i,nm in enumerate(['2024H1','2024H2','2025H1','2025H2'])},**{f'{nm}_net':fnet[i] for i,nm in enumerate(['2024H1','2024H2','2025H1','2025H2'])},**{f'gate_{k}':x for k,x in gates.items()},'all_development_gates_pass':all(gates.values())})
 res=pd.DataFrame(rows);res.to_csv(OUT/'diverse_ai_development_grid_all.csv',index=False);pas=res[res.all_development_gates_pass].copy();pas=pas.sort_values(['candidate_id','positive_folds','worst_fold_pf','pf','net_to_dd','net'],ascending=[True,False,False,False,False,False]);best=pas.groupby('candidate_id',as_index=False).first() if len(pas) else pas;short=best.sort_values(['positive_folds','worst_fold_pf','pf','net_to_dd','net','candidate_id'],ascending=[False,False,False,False,False,True]).head(20).copy()
 if len(short):short.insert(0,'shortlist_rank',np.arange(1,len(short)+1))
 short.to_csv(OUT/'diverse_ai_development_shortlist.csv',index=False);summary={'stage':'BTC_AI_V1_13_DIVERSE_AI_DEVELOPMENT_VALUE','status':'COMPLETE_DEVELOPMENT_ONLY','evaluation_calendar_months':24,'capability_survivors':len(surv),'execution_configs_evaluated':len(res),'configs_passing_all_development_gates':int(res.all_development_gates_pass.sum()),'development_shortlist_count':len(short),'grid_sha256':sha(OUT/'diverse_ai_development_grid_all.csv'),'shortlist_sha256':sha(OUT/'diverse_ai_development_shortlist.csv')};(OUT/'stage13_summary.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()
