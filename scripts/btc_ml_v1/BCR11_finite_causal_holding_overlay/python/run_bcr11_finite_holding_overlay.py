from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

M15_SHA='b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148'
BCR09_SHA='92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa'
BCR10_SHA='99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0'
CONTRACT_COMMIT='b837d02914743bdec87d46cfbdc60683fdf511b0'
RECORDED_AT='2026-07-30T20:39:00+09:00'
SCENARIOS={'C0_OBSERVED_SPREAD':0.0,'C2_25PCT_SPREAD_PER_FILL':0.25}
OVERLAYS={
'O0_BASELINE':(None,False),'O1_MAX_HOLD_16':(16,False),'O2_MAX_HOLD_32':(32,False),
'O3_MAX_HOLD_64':(64,False),'O4_SERVER_DAY_FLAT_2345':(None,True),
'O5_MAX_HOLD_16_AND_SERVER_DAY_FLAT_2345':(16,True)}
B4={'TRACK_B_B4_E0_EMA20_TOUCH':'E0','TRACK_B_B4_E1_EXTENSION_CONTRACT':'E1'}


def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()


def load_b9():
 env_path=os.environ.get('BCR09_REPRODUCER_PATH')
 if env_path:
  path=Path(env_path)
 else:
  path=Path(__file__).resolve().parents[4]/'scripts/btc_ml_v1/BCR09_shared_retrospective_value_gate/python/run_bcr09_shared_value_gate.py'
 spec=importlib.util.spec_from_file_location('bcr09_reproducer',path)
 if not spec or not spec.loader: raise RuntimeError(f'Cannot import BCR09 reproducer: {path}')
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def b4_entry(r)->str|None:
 if not r.common_eligible:return None
 le=r.p_close<=r.p_ema20-1.5*r.p_atr14 and r.p_ret1_bps>0
 se=r.p_close>=r.p_ema20+1.0*r.p_atr14 and r.p_ret1_bps<0
 return 'LONG' if le and not se else ('SHORT' if se and not le else None)


def b4_exit(r,d:str,code:str)->bool:
 if not r.common_eligible:return False
 if code=='E0':return r.p_close>=r.p_ema20 if d=='LONG' else r.p_close<=r.p_ema20
 ext=(r.p_close-r.p_ema20)/r.p_atr14
 return ext>=-0.25 if d=='LONG' else ext<=0.25


def entry_direction(b9,r,mid:str)->tuple[str|None,bool]:
 if mid in b9.TRACK_A:
  s=b9.TRACK_A[mid]; le=b9.long_entry(r,s['long_entry']); se=b9.short_entry(r,s['short_entry'])
  return ('LONG' if le and not se else ('SHORT' if se and not le else None)),bool(le and se)
 return b4_entry(r),False


def base_exit(b9,r,mid:str,d:str)->bool:
 if mid in b9.TRACK_A:
  return b9.long_exit(r,b9.TRACK_A[mid]['long_exit']) if d=='LONG' else bool(r.common_eligible and r.p_rci9<=-70)
 return b4_exit(r,d,B4[mid])


def age(entry:pd.Timestamp,now:pd.Timestamp)->int:
 x=float((now-entry)/pd.Timedelta(minutes=15)); n=int(round(x))
 if abs(x-n)>1e-9 or n<0: raise RuntimeError('Non-M15 age')
 return n


def missing_2345(entry,end,available:set[pd.Timestamp])->int:
 ds=pd.date_range(entry.normalize(),end.normalize(),freq='D')
 return sum(entry<(d+pd.Timedelta(hours=23,minutes=45))<=end and (d+pd.Timedelta(hours=23,minutes=45)) not in available for d in ds)


def replay(b9,f:pd.DataFrame,mid:str,oid:str)->tuple[pd.DataFrame,dict]:
 maxhold,dayflat=OVERLAYS[oid]; state='IDLE'; ent=None; eps=[]; conflicts=suppressed=0
 available=set(f.server_open); endpoint=f.server_open.iloc[-1]
 for r in f.itertuples(index=False):
  exited=False
  if state!='IDLE':
   d='LONG' if state=='ACTIVE_LONG' else 'SHORT'; a=age(ent,r.server_open)
   mh=maxhold is not None and a>=maxhold; df=dayflat and r.server_open.hour==23 and r.server_open.minute==45; be=base_exit(b9,r,mid,d)
   if mh or df or be:
    reason='OVERLAY_MAX_HOLD_AND_DAY_FLAT' if mh and df else ('OVERLAY_MAX_HOLD' if mh else ('OVERLAY_SERVER_DAY_FLAT_2345' if df else 'BASE_EXIT'))
    eps.append(dict(machine_id=mid,overlay_id=oid,direction=d,entry_server_open=ent,exit_server_open=r.server_open,closed=True,exit_reason=reason,base_exit_flag=bool(be),max_hold_flag=bool(mh),day_flat_flag=bool(df),max_hold_overdue_after_gap=bool(mh and a>maxhold),day_flat_boundary_unavailable_count=missing_2345(ent,r.server_open,available) if dayflat else 0))
    state='IDLE';ent=None;exited=True
  suppress=dayflat and r.server_open.hour==23 and r.server_open.minute==45
  if state=='IDLE' and not exited:
   d,conf=entry_direction(b9,r,mid);conflicts+=int(conf)
   if d and suppress:suppressed+=1
   elif d:state='ACTIVE_'+d;ent=r.server_open
 if state!='IDLE':
  d='LONG' if state=='ACTIVE_LONG' else 'SHORT'
  eps.append(dict(machine_id=mid,overlay_id=oid,direction=d,entry_server_open=ent,exit_server_open=pd.NaT,closed=False,exit_reason='ENDPOINT_OPEN',base_exit_flag=False,max_hold_flag=False,day_flat_flag=False,max_hold_overdue_after_gap=False,day_flat_boundary_unavailable_count=missing_2345(ent,endpoint,available) if dayflat else 0))
 return pd.DataFrame(eps),{'machine_id':mid,'overlay_id':oid,'entry_conflicts':conflicts,'entry_suppressed_2345':suppressed}


def enrich(eps:pd.DataFrame,f:pd.DataFrame)->pd.DataFrame:
 px=f.set_index('server_open');t=eps[eps.closed].copy()
 for side in ('entry','exit'):
  key=side+'_server_open';t[side+'_open']=t[key].map(px.open);t[side+'_spread']=t[key].map(px.spread)
 if t[['entry_open','entry_spread','exit_open','exit_spread']].isna().any().any():raise RuntimeError('Missing exact execution row')
 t['entry_spread_price']=t.entry_spread*.01;t['exit_spread_price']=t.exit_spread*.01
 t['holding_bars']=((t.exit_server_open-t.entry_server_open)/pd.Timedelta(minutes=15)).astype(int)
 t['same_server_date']=t.entry_server_open.dt.date==t.exit_server_open.dt.date;t['rollover_exposed']=~t.same_server_date
 t['exit_month']=t.exit_server_open.dt.to_period('M').astype(str)
 for sc,frac in SCENARIOS.items():
  es=frac*t.entry_spread_price;xs=frac*t.exit_spread_price
  lp=(t.exit_open-xs)-(t.entry_open+t.entry_spread_price+es);sp=(t.entry_open-es)-(t.exit_open+t.exit_spread_price+xs)
  t['pnl_'+sc]=np.where(t.direction.eq('LONG'),lp,sp)
  t['cost_'+sc]=np.where(t.direction.eq('LONG'),t.entry_spread_price+es+xs,t.exit_spread_price+es+xs)
 return t


def metric(b9,g:pd.DataFrame,sc:str)->dict:
 m=b9.metrics(g,sc);m['rollover_exposed_episodes']=m.pop('rollover_exposed_trades');h=g.holding_bars.to_numpy(float)
 return {**m,'holding_median':float(np.median(h)),'holding_p90':float(np.quantile(h,.9)),'holding_max':int(h.max())}


def baseline_change(eps:pd.DataFrame,machines:list[str])->pd.DataFrame:
 out=[]
 for mid in machines:
  b=eps[(eps.machine_id==mid)&(eps.overlay_id=='O0_BASELINE')].set_index(['direction','entry_server_open'])
  for oid in OVERLAYS:
   o=eps[(eps.machine_id==mid)&(eps.overlay_id==oid)].set_index(['direction','entry_server_open'])
   match=b.index.intersection(o.index);missing=b.index.difference(o.index);new=o.index.difference(b.index);same=changed=0
   for k in match:
    br,orr=b.loc[k],o.loc[k]
    eq=bool(br.closed==orr.closed) and ((pd.isna(br.exit_server_open) and pd.isna(orr.exit_server_open)) or br.exit_server_open==orr.exit_server_open)
    same+=int(eq);changed+=int(not eq)
   total=len(missing)+changed
   out.append(dict(machine_id=mid,overlay_id=oid,base_entries=len(b),overlay_entries=len(o),matched_base_entries=len(match),base_entries_missing_after_path_divergence=len(missing),new_overlay_entries_after_path_divergence=len(new),matched_same_exit=same,matched_changed_exit=changed,base_episodes_with_changed_exit_or_missing=total,base_episode_changed_share=total/len(b)))
 return pd.DataFrame(out)


def decomposition(trades:pd.DataFrame,machines:list[str])->pd.DataFrame:
 out=[]
 for mid in machines:
  mg=trades[trades.machine_id==mid];base=mg[mg.overlay_id=='O0_BASELINE'].set_index(['direction','entry_server_open'])
  for oid,og0 in mg.groupby('overlay_id'):
   og=og0.copy();idx=pd.MultiIndex.from_frame(og[['direction','entry_server_open']]);og['entry_origin']=np.where(idx.isin(base.index),'MATCHED_BASE_ENTRY','NEW_AFTER_PATH_DIVERGENCE')
   for sc in SCENARIOS:
    og['basep']=idx.map(base['pnl_'+sc]);og['delta']=og['pnl_'+sc]-og.basep
    for origin,g in og.groupby('entry_origin'):
     v=g['pnl_'+sc].to_numpy(float);gp=v[v>0].sum();gl=-v[v<0].sum()
     out.append(dict(machine_id=mid,overlay_id=oid,scenario=sc,entry_origin=origin,closed_episodes=len(g),pf=gp/gl if gl else np.nan,net_usd_per_1lot=v.sum(),expectancy=v.mean(),pnl_delta_vs_baseline_same_entries=g.delta.sum(skipna=True)))
 return pd.DataFrame(out)


def pareto(mm:pd.DataFrame,ch:pd.DataFrame)->pd.DataFrame:
 c0=mm[mm.scenario=='C0_OBSERVED_SPREAD'][['machine_id','overlay_id','pf','max_drawdown','rollover_exposed_episodes','net_usd_per_1lot']]
 c2=mm[mm.scenario=='C2_25PCT_SPREAD_PER_FILL'][['machine_id','overlay_id','pf','max_drawdown','net_usd_per_1lot']]
 x=c0.merge(c2,on=['machine_id','overlay_id'],suffixes=('_c0','_c2')).merge(ch[['machine_id','overlay_id','base_episode_changed_share']],on=['machine_id','overlay_id'])
 x=x.rename(columns={'pf_c0':'c0_pf','pf_c2':'c2_pf','max_drawdown_c0':'c0_max_drawdown','max_drawdown_c2':'c2_max_drawdown','net_usd_per_1lot_c0':'c0_net','net_usd_per_1lot_c2':'c2_net'})
 flags=[]
 for i,r in x.iterrows():
  o=x[(x.machine_id==r.machine_id)&(x.index!=i)];dom=((o.c0_pf>=r.c0_pf)&(o.c2_pf>=r.c2_pf)&(o.c0_max_drawdown<=r.c0_max_drawdown)&(o.rollover_exposed_episodes<=r.rollover_exposed_episodes)&(o.base_episode_changed_share<=r.base_episode_changed_share)&((o.c0_pf>r.c0_pf)|(o.c2_pf>r.c2_pf)|(o.c0_max_drawdown<r.c0_max_drawdown)|(o.rollover_exposed_episodes<r.rollover_exposed_episodes)|(o.base_episode_changed_share<r.base_episode_changed_share))).any();flags.append(not dom)
 x['pareto_within_machine']=flags;return x


def dzip(folder:Path,target:Path):
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.iterdir()):
   i=zipfile.ZipInfo(p.name,(2026,7,30,11,39,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=(0o644&0xffff)<<16;z.writestr(i,p.read_bytes())


def run(m15:Path,bcr09:Path,bcr10:Path,out:Path)->Path:
 if sha(m15)!=M15_SHA or sha(bcr09)!=BCR09_SHA or sha(bcr10)!=BCR10_SHA:raise RuntimeError('Input SHA mismatch')
 b9=load_b9();raw=pd.read_csv(m15,encoding='utf-8-sig');raw['server_open']=pd.to_datetime(raw.time)
 for c in ('open','high','low','close','spread'):raw[c]=pd.to_numeric(raw[c],errors='raise')
 f=b9.build_features(raw);machines=list(b9.TRACK_A)+list(B4)
 with zipfile.ZipFile(bcr09) as z:expected=pd.read_csv(z.open('02_common_episode_ledger.csv'))
 expected=expected[expected.machine_id.isin(machines)].copy();expected.entry_server_open=pd.to_datetime(expected.entry_server_open);expected.exit_server_open=pd.to_datetime(expected.exit_server_open);expected.closed=expected.closed.astype(bool)
 parts=[];aud=[]
 for mid in machines:
  for oid in OVERLAYS:
   e,a=replay(b9,f,mid,oid);parts.append(e);aud.append(a)
 eps=pd.concat(parts,ignore_index=True);eps.entry_server_open=pd.to_datetime(eps.entry_server_open);eps.exit_server_open=pd.to_datetime(eps.exit_server_open);eps.closed=eps.closed.astype(bool)
 parity={}
 for mid in machines:
  cols=['direction','entry_server_open','exit_server_open','closed'];a=eps[(eps.machine_id==mid)&(eps.overlay_id=='O0_BASELINE')][cols].sort_values(['entry_server_open','direction']).reset_index(drop=True);b=expected[expected.machine_id==mid][cols].sort_values(['entry_server_open','direction']).reset_index(drop=True);parity[mid]=a.equals(b)
 if not all(parity.values()):raise RuntimeError(parity)
 trades=enrich(eps,f);ch=baseline_change(eps,machines);dec=decomposition(trades,machines);audit=pd.DataFrame(aud)
 mrows=[];drows=[];months=[]
 for (mid,oid),g in trades.groupby(['machine_id','overlay_id']):
  ar=audit[(audit.machine_id==mid)&(audit.overlay_id==oid)].iloc[0];entries=len(eps[(eps.machine_id==mid)&(eps.overlay_id==oid)]);opens=len(eps[(eps.machine_id==mid)&(eps.overlay_id==oid)&(~eps.closed)])
  for sc in SCENARIOS:
   mrows.append(dict(machine_id=mid,overlay_id=oid,scenario=sc,entries=entries,endpoint_open_episodes=opens,entry_conflicts=int(ar.entry_conflicts),entry_suppressed_2345=int(ar.entry_suppressed_2345),gap_overdue_exits=int(g.max_hold_overdue_after_gap.sum()),day_flat_boundary_unavailable_count=int(g.day_flat_boundary_unavailable_count.sum()),**metric(b9,g,sc)))
   for d,dg in g.groupby('direction'):drows.append(dict(machine_id=mid,overlay_id=oid,direction=d,scenario=sc,**metric(b9,dg,sc)))
   mo=g.groupby(g.exit_server_open.dt.to_period('M').astype(str))['pnl_'+sc].agg(['size','sum']).reset_index();mo.columns=['exit_month','closed_episodes','net_usd_per_1lot']
   for r in mo.itertuples(index=False):months.append(dict(machine_id=mid,overlay_id=oid,scenario=sc,exit_month=r.exit_month,closed_episodes=int(r.closed_episodes),net_usd_per_1lot=float(r.net_usd_per_1lot),positive=bool(r.net_usd_per_1lot>0)))
 mm=pd.DataFrame(mrows);dm=pd.DataFrame(drows);monthly=pd.DataFrame(months);er=eps.groupby(['machine_id','overlay_id','exit_reason'],as_index=False).agg(episodes=('exit_reason','size'),base_exit_flag=('base_exit_flag','sum'),max_hold_flag=('max_hold_flag','sum'),day_flat_flag=('day_flat_flag','sum'),max_hold_overdue_after_gap=('max_hold_overdue_after_gap','sum'),day_flat_boundary_unavailable_count=('day_flat_boundary_unavailable_count','sum'));pa=pareto(mm,ch)
 c0=mm[mm.scenario=='C0_OBSERVED_SPREAD'];c2=mm[mm.scenario=='C2_25PCT_SPREAD_PER_FILL'];bc0=c0.loc[c0.pf.idxmax()];bc2=c2.loc[c2.pf.idxmax()]
 summary=dict(stage='BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_REPLAY',recorded_at=RECORDED_AT,status='READY_RETROSPECTIVE_EXPOSED_FINITE_OVERLAY_COMPARISON_NO_PROMOTION',exposure='RETROSPECTIVE_FULL_HISTORY_EXPOSED_DEVELOPMENT',m15_sha256=M15_SHA,bcr09_sha256=BCR09_SHA,bcr10_sha256=BCR10_SHA,contract_commit=CONTRACT_COMMIT,machines=6,overlays=6,trials=36,best_c0_descriptive=dict(machine_id=bc0.machine_id,overlay_id=bc0.overlay_id,pf=float(bc0.pf),net_usd_per_1lot=float(bc0.net_usd_per_1lot)),best_c2_descriptive=dict(machine_id=bc2.machine_id,overlay_id=bc2.overlay_id,pf=float(bc2.pf),net_usd_per_1lot=float(bc2.net_usd_per_1lot)),nonbaseline_positive_c0_trials=int(((c0.overlay_id!='O0_BASELINE')&(c0.net_usd_per_1lot>0)).sum()),nonbaseline_pf_ge_1_c0_trials=int(((c0.overlay_id!='O0_BASELINE')&(c0.pf>=1)).sum()),nonbaseline_positive_c2_trials=int(((c2.overlay_id!='O0_BASELINE')&(c2.net_usd_per_1lot>0)).sum()),nonbaseline_pf_ge_1_c2_trials=int(((c2.overlay_id!='O0_BASELINE')&(c2.pf>=1)).sum()),candidate_promoted=False,portfolio_selected=False,prospective_start_set=False,shadow_started=False,swap_included=False)
 integrity=dict(m15_sha256=sha(m15),bcr09_sha256=sha(bcr09),bcr10_sha256=sha(bcr10),contract_commit=CONTRACT_COMMIT,machine_count=6,overlay_count=6,trial_count=36,baseline_exact_episode_parity=parity,baseline_all_six_match=all(parity.values()),exact_execution_rows_missing=0,current_bar_high_low_close_used_for_signal=False,nearest_next_or_interpolation_used=False,base_formula_changed=False,tp_sl_trailing_added=False,custom_overlay_per_machine=False,commission=0.0,swap_included=False,candidate_promoted=False,portfolio_selected=False,shadow_started=False)
 run=out/'BCR11_20260730T113900Z';shutil.rmtree(run,ignore_errors=True);run.mkdir(parents=True)
 (run/'00_READ_ME_FIRST.txt').write_text('BCR11 FINITE CAUSAL HOLDING OVERLAY\nRetrospective exposed development only. No promotion.\n',encoding='utf-8');(run/'01_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 eo=eps.copy();eo.entry_server_open=eo.entry_server_open.dt.strftime('%Y-%m-%d %H:%M:%S');eo.exit_server_open=eo.exit_server_open.dt.strftime('%Y-%m-%d %H:%M:%S');eo.to_csv(run/'02_overlay_episode_ledger.csv',index=False,encoding='utf-8-sig')
 to=trades.copy();to.entry_server_open=to.entry_server_open.dt.strftime('%Y-%m-%d %H:%M:%S');to.exit_server_open=to.exit_server_open.dt.strftime('%Y-%m-%d %H:%M:%S');to.to_csv(run/'03_overlay_trade_ledger_cost_enriched.csv',index=False,encoding='utf-8-sig')
 mm.to_csv(run/'04_machine_overlay_metrics.csv',index=False,encoding='utf-8-sig');dm.to_csv(run/'05_direction_metrics.csv',index=False,encoding='utf-8-sig');er.to_csv(run/'06_exit_reason_counts.csv',index=False,encoding='utf-8-sig');monthly.to_csv(run/'07_monthly_metrics.csv',index=False,encoding='utf-8-sig');ch.to_csv(run/'08_baseline_change_audit.csv',index=False,encoding='utf-8-sig');pa.to_csv(run/'09_pareto_by_machine.csv',index=False,encoding='utf-8-sig');dec.to_csv(run/'10_path_divergence_decomposition.csv',index=False,encoding='utf-8-sig');audit.to_csv(run/'11_replay_gap_and_entry_audit.csv',index=False,encoding='utf-8-sig');(run/'12_integrity_checks.json').write_text(json.dumps(integrity,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 manifest={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(run.iterdir())};(run/'13_file_sha256_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 pkg=out/'BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_20260730.zip';pkg.unlink(missing_ok=True);dzip(run,pkg);return pkg


def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--m15',type=Path,required=True);p.add_argument('--bcr09',type=Path,required=True);p.add_argument('--bcr10',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();pkg=run(a.m15,a.bcr09,a.bcr10,a.output_root);print(pkg);print(sha(pkg));return 0
if __name__=='__main__':raise SystemExit(main())
