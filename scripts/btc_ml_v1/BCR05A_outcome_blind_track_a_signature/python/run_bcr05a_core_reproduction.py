from __future__ import annotations

import argparse, hashlib, json, zipfile
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

INPUT_SHA='5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8'
INVALID_V100_SHA='838dc8cacdcb086302cfa48f3a5818fdbc7e2ac61c041337381be57df996dcdb'


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def bh(p:pd.Series)->pd.Series:
    a=p.astype(float).to_numpy(); n=len(a); order=np.argsort(a,kind='mergesort')
    q=a[order]*n/np.arange(1,n+1); q=np.minimum.accumulate(q[::-1])[::-1]; q=np.minimum(q,1)
    out=np.empty(n); out[order]=q; return pd.Series(out,index=p.index)


def as_bool(s:pd.Series)->pd.Series:
    if s.dtype==bool:return s
    return s.astype(str).str.lower().map({'true':True,'false':False}).eq(True)


def zone(x:float)->str:
    if x<=-80:return 'LE_NEG80'
    if x<=-40:return 'NEG80_NEG40'
    if x<=0:return 'NEG40_ZERO'
    if x<40:return 'ZERO_40'
    if x<80:return '40_80'
    return 'GE_80'


def binary(pos:pd.DataFrame,ctl:pd.DataFrame,getter:Callable[[pd.DataFrame],pd.Series])->dict:
    x=getter(pos).fillna(False).astype(bool); y=getter(ctl).fillna(False).astype(bool)
    a=int(x.sum()); b=len(x)-a; c=int(y.sum()); d=len(y)-c
    return {'event_prevalence':a/len(x),'control_prevalence':c/len(y),
            'prevalence_difference':a/len(x)-c/len(y),
            'corrected_odds_ratio':((a+.5)*(d+.5))/((b+.5)*(c+.5)),
            'p_value':float(fisher_exact([[a,b],[c,d]]).pvalue)}


def continuous(pos:pd.DataFrame,ctl:pd.DataFrame,col:str)->dict:
    x=pd.to_numeric(pos[col],errors='coerce').dropna().to_numpy(float)
    y=pd.to_numeric(ctl[col],errors='coerce').dropna().to_numpy(float)
    u=mannwhitneyu(x,y,alternative='two-sided',method='asymptotic')
    return {'event_median':float(np.median(x)),'control_median':float(np.median(y)),
            'median_difference':float(np.median(x)-np.median(y)),
            'cliffs_delta':2*float(u.statistic)/(len(x)*len(y))-1,'p_value':float(u.pvalue)}


def load(p:Path)->pd.DataFrame:
    if sha256(p)!=INPUT_SHA:raise RuntimeError('BCR04 SHA mismatch')
    with zipfile.ZipFile(p) as z:
        d=pd.read_csv(z.open('02_decision_window_ledger.csv'))
        integ=json.loads(z.read('11_integrity_checks.json'))
    if integ['outcomes_opened'] or integ['outcome_fields_read']:raise RuntimeError('outcome boundary failed')
    if len(d)!=907 or d.decision_time_utc.nunique()!=907:raise RuntimeError('universe mismatch')
    d['feature_eligible_core']=as_bool(d.feature_eligible_core)
    for c in ['rci9_turn_up','rci9_turn_down','rci14_turn_up','rci14_turn_down','rci18_turn_up','rci18_turn_down']:
        d[c]=as_bool(d[c])
    for n in (9,14,18):d[f'rci{n}_zone']=pd.to_numeric(d[f'rci{n}']).map(zone)
    return d


def direction_tables(d:pd.DataFrame,direction:str)->tuple[pd.DataFrame,pd.DataFrame]:
    pos=d[d.event_class.eq('PRIMARY_LONG_EVENT' if direction=='LONG' else 'PRIMARY_SHORT_EVENT')]
    ctl=d[d.event_class.eq('IDLE_NON_EVENT_CONTROL')&d.feature_eligible_core]
    up=direction=='LONG'; br=[]; cr=[]
    for name,getter in [
        ('rci9_direction_correct_turn',lambda x:x.rci9_turn_up if up else x.rci9_turn_down),
        ('rci14_direction_correct_turn',lambda x:x.rci14_turn_up if up else x.rci14_turn_down),
        ('rci18_direction_correct_turn',lambda x:x.rci18_turn_up if up else x.rci18_turn_down)]:
        br.append({'family':'A','feature':name,**binary(pos,ctl,getter)})
    for n in (9,14,18):
        for z in ['LE_NEG80','NEG80_NEG40','NEG40_ZERO','ZERO_40','40_80','GE_80']:
            br.append({'family':'A','feature':f'rci{n}_zone={z}',**binary(pos,ctl,lambda x,n=n,z=z:x[f'rci{n}_zone'].eq(z))})
    for z in ['BULLISH_STACK','MIXED','BEARISH_STACK']:
        br.append({'family':'B','feature':f'ema_alignment={z}',**binary(pos,ctl,lambda x,z=z:x.ema_alignment.eq(z))})
    good='BULLISH_STACK' if up else 'BEARISH_STACK'
    br.append({'family':'B','feature':'direction_correct_ema_stack',**binary(pos,ctl,lambda x,good=good:x.ema_alignment.eq(good))})
    b=pd.DataFrame(br); b['q_value']=np.nan
    for _,idx in b.groupby('family').groups.items():b.loc[idx,'q_value']=bh(b.loc[idx,'p_value']).values
    for col in ['rci9','rci9_delta1','rci14','rci14_delta1','rci18','rci18_delta1']:
        cr.append({'family':'A','feature':col,**continuous(pos,ctl,col)})
    for col in ['closed_return_1_bps','closed_return_4_bps','closed_return_16_bps','previous_body_ratio',
                'previous_upper_wick_ratio','previous_lower_wick_ratio','previous_range_bps',
                'current_open_gap_from_previous_close_bps','current_open_distance_to_20_high_bps',
                'current_open_distance_to_20_low_bps','current_open_distance_to_50_high_bps',
                'current_open_distance_to_50_low_bps']:
        cr.append({'family':'D','feature':col,**continuous(pos,ctl,col)})
    c=pd.DataFrame(cr); c['q_value']=np.nan
    for _,idx in c.groupby('family').groups.items():c.loc[idx,'q_value']=bh(c.loc[idx,'p_value']).values
    return b,c


def close(a:float,b:float,tol:float=1e-12)->bool:return abs(a-b)<=tol


def build(inp:Path,out:Path)->None:
    d=load(inp); lb,lc=direction_tables(d,'LONG'); sb,sc=direction_tables(d,'SHORT')
    def row(t:pd.DataFrame,name:str)->pd.Series:return t[t.feature.eq(name)].iloc[0]
    result={
      'status':'PASS_BCR05A_CORE_REPRODUCTION','input_sha256':INPUT_SHA,
      'long_events':int(d.event_class.eq('PRIMARY_LONG_EVENT').sum()),
      'short_events':int(d.event_class.eq('PRIMARY_SHORT_EVENT').sum()),
      'eligible_idle_controls':int((d.event_class.eq('IDLE_NON_EVENT_CONTROL')&d.feature_eligible_core).sum()),
      'long_anchor':row(lb,'rci9_direction_correct_turn').to_dict(),
      'short_anchor':row(sb,'rci9_direction_correct_turn').to_dict(),
      'long_correct_ema_stack':row(lb,'direction_correct_ema_stack').to_dict(),
      'short_correct_ema_stack':row(sb,'direction_correct_ema_stack').to_dict(),
      'long_rci9_delta1':row(lc,'rci9_delta1').to_dict(),
      'short_rci9':row(sc,'rci9').to_dict(),
      'long_closed_return_1':row(lc,'closed_return_1_bps').to_dict(),
      'short_closed_return_1':row(sc,'closed_return_1_bps').to_dict(),
      'label_derived_event_distance_tested':False,'outcomes_opened':False,
      'performance_interpretation_performed':False,'candidate_formula_designed':False,
      'invalid_v100_package_sha256':INVALID_V100_SHA}
    checks=[result['long_events']==16,result['short_events']==10,result['eligible_idle_controls']==438,
      close(result['long_anchor']['event_prevalence'],1),close(result['long_anchor']['control_prevalence'],.11643835616438356),
      close(result['short_anchor']['event_prevalence'],1),close(result['short_anchor']['control_prevalence'],.1461187214611872),
      close(result['long_correct_ema_stack']['event_prevalence'],.875),close(result['short_correct_ema_stack']['event_prevalence'],.9),
      close(result['long_rci9_delta1']['cliffs_delta'],.6091609589041096),
      close(result['short_rci9']['cliffs_delta'],.49520547945205484),
      close(result['long_closed_return_1']['cliffs_delta'],.40496575342465757),
      close(result['short_closed_return_1']['cliffs_delta'],-.6762557077625571)]
    if not all(checks):raise RuntimeError('accepted BCR05A core metrics mismatch')
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2,default=float)+'\n',encoding='utf-8')


def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--bcr04',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.bcr04,a.output);return 0

if __name__=='__main__':raise SystemExit(main())
