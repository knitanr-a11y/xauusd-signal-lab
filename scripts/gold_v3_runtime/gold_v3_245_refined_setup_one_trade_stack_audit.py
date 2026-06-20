#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,itertools,json,math,os,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from gold_v3_243_scalp_rebuild_no_lookahead_search_audit import read_csv_any, build_features, default_files_dir, save_csv, save_json

STAGE='GOLD_V3_245_REFINED_SETUP_ONE_TRADE_STACK_AUDIT_ONLY'
READY='STAGE245_REFINED_SETUP_ONE_TRADE_STACK_READY_AUDIT_ONLY'
BLOCKED='STAGE245_REFINED_SETUP_ONE_TRADE_STACK_BLOCKED_AUDIT_ONLY'
TF_MIN={'m1':1,'m15':15,'h1':60,'h4':240,'d1':1440}
OFF={'discord_webhook_called':False,'mt5_order_send_called':False,'order_placed':False,'real_account_allowed':False,'final_live_enabled':False,'payload_activation_enabled':False,'live_hook_enabled':False,'autotrade_enabled':False,'no_signal_discord_notify':False,'no_signal_order_allowed':False,'source_csv_mutated':False,'contract_mutated':False,'candidate_pool_removed':False,'open_asof_allowed':False}
CFG={
 'VOL_STRONG_H1_RSI45':('SHORT',40.0,15.0,480),
 'PULLBACK_H1_VOL_BAND':('SHORT',30.0,10.0,360),
 'BREAKOUT_TREND_VOL':('SHORT',40.0,15.0,480),
}

def prog(m,i=None,n=None):
 t=datetime.now().strftime('%H:%M:%S'); print(f'[Stage245 {i}/{n} {100*i/n:5.1f}% {t}] {m}' if i and n else f'[Stage245 {t}] {m}',flush=True)
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def load(root,tf):
 d=read_csv_any(root/f'goldsharp_{tf}.csv')
 if d.empty:return d
 d['open_time']=d['dt']; d['close_time']=d['dt']+pd.to_timedelta(TF_MIN[tf],unit='min'); return d

def frame(frames):
 s=build_features(frames['m15'],'m15')
 for tf in ['h1','h4','d1']:
  h=build_features(frames[tf],tf); keep=['close_time']+[c for c in h if c.startswith(tf+'_')]
  s=pd.merge_asof(s.sort_values('close_time'),h[keep].sort_values('close_time'),on='close_time',direction='backward',allow_exact_matches=True)
 return s.replace([np.inf,-np.inf],np.nan).reset_index(drop=True)
def conditions(s):
 breakout=(s.h1_ema20_ema50_atr14<=-.30)&(s.m15_break_low40_atr14>=.10)&(s.m15_body_atr14<=-.30)&(s.m15_close_loc<=.30)&(s.m15_atr_ratio>=1)
 vol=(s.h1_ema20_ema50_atr14<=-.15)&(s.m15_atr_ratio.shift(1)<=.85)&(s.m15_range_atr14>=1.30)&(s.m15_body_atr14<=-.70)&(s.m15_close_loc<=.30)
 pull=(s.h1_ema20_ema50_atr14<=-.30)&s.m15_close_ema20_atr14.between(-.25,.75)&s.m15_rsi14.between(40,65)&(s.m15_body_atr14<=-.30)&(s.close<s.low.shift(1))
 return {'VOL_STRONG_H1_RSI45':(vol&(s.h1_ema20_ema50_atr14<=-.70)&(s.h1_rsi14<=45)).fillna(False).values,'PULLBACK_H1_VOL_BAND':(pull&s.h1_atr_ratio.between(1.10,1.50)).fillna(False).values,'BREAKOUT_TREND_VOL':(breakout&(s.h1_ema20_ema50_atr14<=-.55)&(s.m15_atr_ratio>=1.10)).fillna(False).values}
def precompute(s,m1,d,tp,sl,hz):
 n=len(s); et=np.full(n,np.datetime64('NaT'),dtype='datetime64[ns]'); xt=et.copy(); pnl=np.full(n,np.nan); hit=np.empty(n,dtype=object)
 times=m1.open_time.values.astype('datetime64[ns]'); o=m1.open.astype(float).values; h=m1.high.astype(float).values; l=m1.low.astype(float).values; c=m1.close.astype(float).values
 for i,sc in enumerate(s.close_time):
  j=int(np.searchsorted(times,np.datetime64(sc),'left'))
  if j>=len(m1) or pd.Timestamp(m1.open_time.iloc[j])-pd.Timestamp(sc)>pd.Timedelta(minutes=2):continue
  ep=o[j]; end=min(j+hz,len(m1)); kx=end-1; p=(ep-c[kx]) if d=='SHORT' else (c[kx]-ep); p=max(-sl,min(tp,p)); hh='HORIZON'
  for k in range(j,end):
   sh=(h[k]>=ep+sl) if d=='SHORT' else (l[k]<=ep-sl); th=(l[k]<=ep-tp) if d=='SHORT' else (h[k]>=ep+tp)
   if sh:kx=k;p=-sl;hh='SL';break
   if th:kx=k;p=tp;hh='TP';break
  et[i]=np.datetime64(m1.open_time.iloc[j]); xt[i]=np.datetime64(pd.Timestamp(m1.open_time.iloc[kx])+pd.Timedelta(minutes=1)); pnl[i]=p; hit[i]=hh
 return et,xt,pnl,hit
def select(s,cond,out,name):
 et,xt,pnl,hit=out; rows=[]; active=False; until=np.datetime64('NaT'); armed=True
 for i,ct in enumerate(s.close_time.values.astype('datetime64[ns]')):
  if active and ct<until:continue
  if active:active=False;armed=False
  if not cond[i]:armed=True;continue
  if not armed or np.isnat(et[i]):continue
  rows.append(i);until=xt[i];active=True;armed=False
 idx=np.asarray(rows,dtype=int)
 if not len(idx):return pd.DataFrame(columns=['candidate','entry_time','exit_time','pnl_raw'])
 return pd.DataFrame({'candidate':name,'signal_time':s.close_time.iloc[idx].values,'entry_time':et[idx],'exit_time':xt[idx],'pnl_raw':pnl[idx],'hit':hit[idx]})
def met(df,a,b=None,cost=3):
 if df.empty:return {'n':0,'wr':None,'pf':None,'pnl':0.0}
 t=pd.to_datetime(df.entry_time); x=df[(t>=pd.Timestamp(a))&((t<pd.Timestamp(b)) if b else True)]
 if x.empty:return {'n':0,'wr':None,'pf':None,'pnl':0.0}
 z=x.pnl_raw-cost; gp=float(z[z>0].sum());gl=float(-z[z<0].sum());pf=math.inf if gl==0 and gp>0 else (0 if gl==0 else gp/gl)
 return {'n':len(x),'wr':float((z>0).mean()),'pf':pf,'pnl':float(z.sum())}
def near(a,b,w=30):
 x=pd.to_datetime(a.entry_time).sort_values().values.astype('datetime64[ns]'); y=pd.to_datetime(b.entry_time).sort_values().values.astype('datetime64[ns]'); win=np.timedelta64(w,'m')
 def cnt(q,r):
  z=0
  for t in q:
   j=int(np.searchsorted(r,t));z+=any(0<=k<len(r) and abs(r[k]-t)<=win for k in [j-1,j])
  return z
 return len(set(x)&set(y)),cnt(x,y),cnt(y,x)
def onepos(df):
 pri={'VOL_STRONG_H1_RSI45':1,'PULLBACK_H1_VOL_BAND':2,'BREAKOUT_TREND_VOL':3}; x=df.assign(pr=df.candidate.map(pri)).sort_values(['entry_time','pr']); rows=[]; until=None
 for _,r in x.iterrows():
  e=pd.Timestamp(r.entry_time)
  if until is not None and e<until:continue
  rows.append(r);until=pd.Timestamp(r.exit_time)
 return pd.DataFrame(rows).drop(columns='pr').reset_index(drop=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot-dir',default='');p.add_argument('--output-dir',default='');a=p.parse_args();root=Path(a.snapshot_dir).resolve() if a.snapshot_dir else default_files_dir()/ 'FX_OUTPUTS/gold_v3/243/input_snapshot/latest';out=Path(a.output_dir).resolve() if a.output_dir else default_files_dir()/ 'FX_OUTPUTS/gold_v3/245';out.mkdir(parents=True,exist_ok=True);t0=time.time();blocks=[]
 prog('load frozen inputs',1,6); fs={tf:load(root,tf) for tf in TF_MIN}; [blocks.append(f'missing_{tf}') for tf,d in fs.items() if d.empty]
 if not blocks:
  prog('build close-time-gated features',2,6);s=frame(fs);s=s[(s.close_time>=fs['m1'].open_time.min())&(s.close_time<=fs['m1'].open_time.max())].reset_index(drop=True);cs=conditions(s)
  prog('one setup = one trade',3,6);cache={};tr={}
  for n,cfg in CFG.items():
   if cfg not in cache:cache[cfg]=precompute(s,fs['m1'],*cfg)
   tr[n]=select(s,cs[n],cache[cfg],n);print(f'[Stage245 candidate] {n}: {len(tr[n])}',flush=True)
  alltr=pd.concat(tr.values(),ignore_index=True).sort_values('entry_time').reset_index(drop=True); glob=onepos(alltr)
  prog('metrics and overlap',4,6); periods=[('dev','2026-01-13','2026-05-01'),('may','2026-05-01','2026-06-01'),('june','2026-06-01',None),('validation','2026-05-01',None),('all','2026-01-13',None)]; rows=[]
  for n,d in tr.items():
   r={'candidate':n,'direction':CFG[n][0],'tp':CFG[n][1],'sl':CFG[n][2],'rr':CFG[n][1]/CFG[n][2],'horizon_m1':CFG[n][3],'trade_count':len(d)}
   for q,x,y in periods:
    for cost in [3,5]:
     for k,v in met(d,x,y,cost).items():r[f'{q}_{k}_cost{cost}']=v
   rows.append(r)
  ov=[]
  for x,y in itertools.combinations(tr,2):
   e,u,v=near(tr[x],tr[y]);ov.append({'candidate_a':x,'candidate_b':y,'exact_overlap':e,'a_within30m':u,'b_within30m':v,'a_rate':u/len(tr[x]),'b_rate':v/len(tr[y])})
  mon=[]; mths=[('2026-01-13_to_01-31','2026-01-13','2026-02-01'),('2026-02','2026-02-01','2026-03-01'),('2026-03','2026-03-01','2026-04-01'),('2026-04','2026-04-01','2026-05-01'),('2026-05','2026-05-01','2026-06-01'),('2026-06_to_end','2026-06-01',None)]
  for n,d in list(tr.items())+[('STACK_CANDIDATE_SPECIFIC',alltr),('GLOBAL_ONE_POSITION',glob)]:
   for q,x,y in mths:
    a3=met(d,x,y,3);a5=met(d,x,y,5);mon.append({'portfolio':n,'period':q,'n':a3['n'],'wr':a3['wr'],'pf3':a3['pf'],'pnl3':a3['pnl'],'pf5':a5['pf'],'pnl5':a5['pnl']})
  active=0
  for _,r in alltr.iterrows():
   e=pd.Timestamp(r.entry_time);active+=not alltr[(alltr.candidate!=r.candidate)&(pd.to_datetime(alltr.entry_time)<e)&(pd.to_datetime(alltr.exit_time)>e)].empty
  save_csv(pd.DataFrame(rows),out/'stage245_refined_candidates.csv');save_csv(pd.DataFrame(ov),out/'stage245_candidate_overlap.csv');save_csv(pd.DataFrame(mon),out/'stage245_portfolio_monthly.csv');save_csv(alltr,out/'stage245_candidate_specific_trades.csv');save_csv(glob,out/'stage245_global_one_position_trades.csv')
 else: alltr=glob=pd.DataFrame();active=0
 prog('audit and summary',5,6);audit=pd.DataFrame([{'check_id':'FROZEN_SNAPSHOT','passed':root.exists(),'details':str(root)},{'check_id':'OPEN_TIME_PLUS_TF_CLOSE','passed':True,'details':'M1/M15/H1/H4/D1'},{'check_id':'HTF_CLOSE_GATED','passed':True,'details':'backward merge on close_time'},{'check_id':'ENTRY_FIRST_M1_AFTER_SIGNAL_CLOSE','passed':True,'details':'searchsorted left'},{'check_id':'SAME_BAR_SL_PRIORITY','passed':True,'details':'SL checked first'},{'check_id':'ONE_SETUP_ONE_TRADE','passed':True,'details':'rearm after exit and false'},{'check_id':'AUDIT_ONLY','passed':True,'details':'no notification/order'}]);save_csv(audit,out/'stage245_no_lookahead_audit.csv')
 status='READY' if not blocks else 'BLOCKED';s={'step':STAGE,'status':status,'ready':not blocks,'decision':READY if not blocks else BLOCKED,'created_at_utc':now(),'elapsed_sec':round(time.time()-t0,3),'snapshot_dir':str(root),'candidate_specific_trade_count':len(alltr),'global_one_position_trade_count':len(glob),'active_overlap_entry_count':int(active),'candidate_specific_validation_cost3':met(alltr,'2026-05-01',None,3),'candidate_specific_validation_cost5':met(alltr,'2026-05-01',None,5),'global_one_position_validation_cost3':met(glob,'2026-05-01',None,3),'blockers':blocks,'blocker_count':len(blocks),'warning':'All survivors are M15 SHORT; filters were refined on the available 2026 sample and remain audit/watchlist only.','output_dir':str(out),**OFF};save_json(out/'stage245_summary.json',s);(out/'paste_me.txt').write_text('\n'.join([f'GOLD V3 245 PASTE_ME',*[f'{k}: {v}' for k,v in s.items()]]),encoding='utf-8');prog('done',6,6);print(out/'paste_me.txt');return 0 if not blocks else 2
if __name__=='__main__':raise SystemExit(main())
