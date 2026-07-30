from __future__ import annotations

import argparse, hashlib, json, shutil, zipfile
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

INPUT_SHA='5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8'
VERSION='1.0.0'


def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def as_bool(s:pd.Series)->pd.Series:
 if s.dtype==bool:return s
 return s.astype(str).str.lower().map({'true':True,'false':False}).eq(True)

def load(p:Path)->pd.DataFrame:
 if sha256(p)!=INPUT_SHA:raise RuntimeError('BCR04 SHA mismatch')
 with zipfile.ZipFile(p) as z:
  d=pd.read_csv(z.open('02_decision_window_ledger.csv')); i=json.loads(z.read('11_integrity_checks.json'))
 if i['outcomes_opened'] or i['outcome_fields_read']:raise RuntimeError('outcome boundary failed')
 if len(d)!=907 or d.decision_time_utc.nunique()!=907:raise RuntimeError('universe mismatch')
 for c in ['feature_eligible_core','rci9_turn_up','rci9_turn_down']:
  d[c]=as_bool(d[c])
 d['decision_date_utc']=pd.to_datetime(d.decision_time_utc,utc=True).dt.strftime('%Y-%m-%d')
 return d

def predicate(d:pd.DataFrame,direction:str,e:str,z:str,p:str)->pd.Series:
 long=direction=='LONG'
 anchor=d.rci9_turn_up if long else d.rci9_turn_down
 ema=pd.Series(True,index=d.index) if e=='E0' else (d.ema_alignment.eq('BULLISH_STACK') if long else d.ema_alignment.eq('BEARISH_STACK'))
 if z=='Z0':level=pd.Series(True,index=d.index)
 elif z=='Z1':level=d.rci9.le(0) if long else d.rci9.ge(0)
 else:level=d.rci9.le(-40) if long else d.rci9.ge(40)
 ret=pd.Series(True,index=d.index) if p=='P0' else (d.closed_return_1_bps.gt(0) if long else d.closed_return_1_bps.lt(0))
 return anchor&ema&level&ret

def metrics(pos:pd.DataFrame,ctl:pd.DataFrame,fire_pos:pd.Series,fire_ctl:pd.Series)->dict:
 a=int(fire_pos.sum()); b=len(pos)-a; c=int(fire_ctl.sum()); dd=len(ctl)-c
 recall=a/len(pos); rate=c/len(ctl); total=a+c
 return {'source_event_hits':a,'source_event_total':len(pos),'source_event_recall':recall,
         'control_hits':c,'control_total':len(ctl),'control_fire_rate':rate,'specificity':1-rate,
         'prevalence_difference':recall-rate,
         'corrected_odds_ratio':((a+.5)*(dd+.5))/((b+.5)*(c+.5)),
         'fisher_p_value_descriptive':float(fisher_exact([[a,b],[c,dd]]).pvalue),
         'source_event_density_among_fires':a/total if total else np.nan}

def pareto(t:pd.DataFrame)->pd.Series:
 out=[]
 for i,r in t.iterrows():
  dominated=False
  for j,s in t.iterrows():
   if i==j:continue
   if s.source_event_recall>=r.source_event_recall and s.control_fire_rate<=r.control_fire_rate and (s.source_event_recall>r.source_event_recall or s.control_fire_rate<r.control_fire_rate):
    dominated=True;break
  out.append(not dominated)
 return pd.Series(out,index=t.index)

def tier(recall:float)->str|None:
 if recall==1:return 'FULL_COVERAGE'
 if .9<=recall<1:return 'HIGH_COVERAGE'
 if .75<=recall<.9:return 'BALANCED_COVERAGE'
 return None

def stability(pos:pd.DataFrame,ctl:pd.DataFrame,mask_pos:pd.Series,mask_ctl:pd.Series)->dict:
 day_rec=[]
 for day in sorted(pos.decision_date_utc.unique()):
  keep=pos.decision_date_utc.ne(day); den=int(keep.sum()); day_rec.append(float(mask_pos[keep].mean()) if den else np.nan)
 evt_rec=[]
 for idx in pos.index:
  keep=pos.index!=idx; evt_rec.append(float(mask_pos.loc[keep].mean()))
 ctl_daily=ctl.assign(fire=mask_ctl).groupby('decision_date_utc').fire.mean()
 hit_days=pos.loc[mask_pos,'decision_date_utc'].nunique()
 return {'leave_one_event_day_recall_min':float(np.nanmin(day_rec)),'leave_one_event_day_recall_max':float(np.nanmax(day_rec)),
         'leave_one_event_out_recall_min':float(np.min(evt_rec)),'leave_one_event_out_recall_max':float(np.max(evt_rec)),
         'control_fire_rate_daily_min':float(ctl_daily.min()),'control_fire_rate_daily_max':float(ctl_daily.max()),
         'event_hit_day_count':int(hit_days),'single_day_dominance':bool(mask_pos.sum()>0 and hit_days<=1),
         'leave_one_day_recall_json':json.dumps(day_rec),'leave_one_event_recall_json':json.dumps(evt_rec)}

def build(inp:Path,outdir:Path)->Path:
 d=load(inp); rows=[]; masks={}
 ctl=d[d.event_class.eq('IDLE_NON_EVENT_CONTROL')&d.feature_eligible_core].copy()
 if len(ctl)!=438:raise RuntimeError('control count')
 for direction in ['LONG','SHORT']:
  ec='PRIMARY_LONG_EVENT' if direction=='LONG' else 'PRIMARY_SHORT_EVENT'; pos=d[d.event_class.eq(ec)].copy(); exp=16 if direction=='LONG' else 10
  if len(pos)!=exp:raise RuntimeError('event count')
  for e,z,p in product(['E0','E1'],['Z0','Z1','Z2'],['P0','P1']):
   gid=f'A_{direction}_{e}_{z}_{p}'; mp=predicate(pos,direction,e,z,p); mc=predicate(ctl,direction,e,z,p)
   pred={'anchor':'RCI9_TURN_UP' if direction=='LONG' else 'RCI9_TURN_DOWN','ema':e,'rci9_level':z,'previous_return':p}
   rows.append({'grammar_id':gid,'direction':direction,'ema_axis':e,'rci9_level_axis':z,'return_axis':p,
                'optional_gate_count':(e!='E0')+(z!='Z0')+(p!='P0'),'predicates_json':json.dumps(pred,sort_keys=True),**metrics(pos,ctl,mp,mc)})
   masks[gid]=(pos,ctl,mp,mc)
 t=pd.DataFrame(rows)
 if len(t)!=24 or t.grammar_id.nunique()!=24:raise RuntimeError('grammar count')
 t['pareto']=False
 for _,idx in t.groupby('direction').groups.items():t.loc[idx,'pareto']=pareto(t.loc[idx]).values
 t['recall_tier']=t.source_event_recall.map(tier)
 advanced=[]
 for direction in ['LONG','SHORT']:
  for tr in ['FULL_COVERAGE','HIGH_COVERAGE','BALANCED_COVERAGE']:
   x=t[(t.direction==direction)&t.pareto&t.recall_tier.eq(tr)].sort_values(['control_fire_rate','optional_gate_count','grammar_id'],kind='mergesort')
   if len(x):
    r=x.iloc[0]; pos,ctl,mp,mc=masks[r.grammar_id]
    advanced.append({'direction':direction,'recall_tier':tr,'grammar_id':r.grammar_id,**stability(pos,ctl,mp,mc)})
 a=pd.DataFrame(advanced)
 t['advanced']=t.grammar_id.isin(set(a.grammar_id) if len(a) else set())
 if (t.groupby('direction').advanced.sum()>3).any():raise RuntimeError('advance cap')
 if any('distance' in x or 'state_age' in x for x in t.predicates_json):raise RuntimeError('forbidden predicate')
 summary={'project':'BTC_CANDIDATE_RESEARCH_REDESIGN','stage':'BCR05B_OUTCOME_BLIND_FINITE_TRACK_A_ENTRY_GRAMMAR','version':VERSION,
  'status':'READY_OUTCOME_BLIND_FINITE_ENTRY_GRAMMAR_FIDELITY_RESULT','input_sha256':INPUT_SHA,
  'grammar_rows':24,'long_grammars':12,'short_grammars':12,'advanced':a.to_dict('records'),
  'outcomes_opened':False,'performance_interpretation_performed':False,'candidate_formula_designed':False,
  'integrated_candidate_frozen':False,'ff06_created':False,'runtime_modified':False}
 if outdir.exists():shutil.rmtree(outdir)
 outdir.mkdir(parents=True)
 files={'00_READ_ME_FIRST.txt':'BCR05B finite entry grammar fidelity only. No outcomes opened.\n','01_summary.json':json.dumps(summary,indent=2)+'\n',
  '02_all_grammar_metrics.csv':t.to_csv(index=False),'03_pareto_frontier.csv':t[t.pareto].to_csv(index=False),
  '04_advanced_by_recall_tier.csv':a.to_csv(index=False),'05_integrity_checks.json':json.dumps({'status':'PASS','grammar_rows':24,'unique_ids':24,'long':12,'short':12,'eligible_idle_controls':438,'event_distance_predicate_used':False,'source_state_age_predicate_used':False,'outcomes_opened':False,'performance_interpretation_performed':False,'candidate_formula_designed':False},indent=2)+'\n'}
 for n,x in files.items():(outdir/n).write_text(x,encoding='utf-8',newline='')
 mani=[{'file':n,'sha256':sha256(outdir/n),'bytes':(outdir/n).stat().st_size} for n in sorted(files)]
 (outdir/'06_file_sha256_manifest.json').write_text(json.dumps(mani,indent=2)+'\n',encoding='utf-8')
 members=sorted(files)+['06_file_sha256_manifest.json']; pkg=outdir/'99_UPLOAD_PACKAGE.zip'
 with zipfile.ZipFile(pkg,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
  for n in members:
   info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;zf.writestr(info,(outdir/n).read_bytes())
 return pkg

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--bcr04',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();pkg=build(a.bcr04,a.output_dir);print(json.dumps({'package':str(pkg),'sha256':sha256(pkg)},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
