#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_151_LOSER_FEATURE_SIGNATURE_AUDIT_ONLY'
KEYWORDS=['atr','rsi','macd','ema','sma','bb','boll','adx','di','rci','stoch','ichimoku','kijun','tenkan','cloud','volume','vol','range','body','wick','slope','trend','h1','h4','d1','m15']

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8'); (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def group_name(c):
    s=c.lower()
    for k in KEYWORDS:
        if k in s: return k
    return 'other'
def yes(s): return s.astype(str).str.lower().isin(['true','1','yes'])
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','max_score'] if c in df.columns]
def choose_rep(df):
    sc=score_cols(df)
    if not sc: return df.head(1)
    for c in sc: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.sort_values(sc,ascending=[False]*len(sc)).head(1)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'151'; out.mkdir(parents=True,exist_ok=True); prog(out,0,1,'START',t0)
    s133=readj(root/'133'/'gold_v3_133_summary.json'); s150=readj(root/'150'/'gold_v3_150_summary.json')
    ev=load(root/'150'/'gold_v3_150_selected_score_tail_events.csv'); led=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    if ev.empty: blockers.append({'id':'missing_150_selected_score_tail_events'})
    if led.empty: blockers.append({'id':'missing_107k2c_ledger'})
    selected=pd.DataFrame(); reps=pd.DataFrame(); numsum=pd.DataFrame(); catsum=pd.DataFrame(); groups=pd.DataFrame()
    if not blockers:
        ev['entry_dt']=pd.to_datetime(ev.entry_dt,errors='coerce'); ev=ev[ev.entry_dt.notna()].copy()
        ev=ev[ev.route2.astype(str)!='NO_ROUTE'].copy() if 'route2' in ev.columns else ev
        ev['event_id']=range(len(ev)); ev['event_worst']=pd.to_numeric(ev.get('worst2',ev.get('worst_after_rule',ev.get('worst',0))),errors='coerce').fillna(0); ev['event_rep']=pd.to_numeric(ev.get('rep2',ev.get('rep_after_rule',ev.get('rep',0))),errors='coerce').fillna(0)
        ev['route_for_policy']=ev.get('route2',ev.get('route_after_rule',ev.get('route',''))).astype(str)
        pmap={'CHAMPION':str(s133.get('champion_policy_key','density_safe||100||Q0.6')),'CHALLENGER':str(s133.get('selected_challenger_policy_key','density_safe||100||Q0.35'))}
        ev['policy_key']=ev.route_for_policy.map(pmap)
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce')
        sel=ev[['event_id','entry_dt','policy_key','route_for_policy','event_worst','event_rep']].dropna(subset=['entry_dt','policy_key'])
        m=led.merge(sel,on=['entry_dt','policy_key'],how='inner')
        if m.empty:
            reps=ev.copy()
        else:
            reps=m.groupby('event_id',group_keys=False).apply(lambda g: choose_rep(g.copy())).reset_index(drop=True)
        reps['is_loser']=pd.to_numeric(reps.event_worst,errors='coerce').fillna(0)<0
        reps['month']=pd.to_datetime(reps.entry_dt,errors='coerce').dt.to_period('M').astype(str)
        selected=reps.copy(); save(selected,out/'gold_v3_151_selected_events_enriched.csv')
        exclude=re.compile(r'(result|profit|pnl|entry|exit|date|time|month|policy|event_|route|ticket|comment|symbol|id$)',re.I)
        numeric=[]
        for c in reps.columns:
            if exclude.search(c): continue
            s=pd.to_numeric(reps[c],errors='coerce')
            if s.notna().sum()>=10 and s.nunique(dropna=True)>=3: numeric.append(c)
        rows=[]
        for c in numeric[:400]:
            s=pd.to_numeric(reps[c],errors='coerce'); ok=s.notna(); tmp=reps[ok].copy(); vals=s[ok]
            if len(tmp)<10: continue
            q25=float(vals.quantile(.25)); q75=float(vals.quantile(.75)); los=tmp.is_loser; win=~los
            if los.sum()==0 or win.sum()==0: continue
            lh=float((vals[los]>=q75).mean()); wh=float((vals[win]>=q75).mean()); ll=float((vals[los]<=q25).mean()); wl=float((vals[win]<=q25).mean())
            hd=lh-wh; ld=ll-wl; tail='HIGH' if abs(hd)>=abs(ld) else 'LOW'; delta=hd if tail=='HIGH' else ld
            rows.append({'feature':c,'feature_group':group_name(c),'events':int(len(tmp)),'losers':int(los.sum()),'winners':int(win.sum()),'loser_median':float(vals[los].median()),'winner_median':float(vals[win].median()),'q25':q25,'q75':q75,'loser_high_share':lh,'winner_high_share':wh,'loser_low_share':ll,'winner_low_share':wl,'risk_tail':tail,'tail_delta':float(delta),'abs_tail_delta':float(abs(delta))})
        numsum=pd.DataFrame(rows).sort_values(['abs_tail_delta','losers'],ascending=[False,False]) if rows else pd.DataFrame(); save(numsum,out/'gold_v3_151_numeric_feature_loss_signature.csv')
        catcols=[]
        for c in reps.columns:
            if exclude.search(c): continue
            if reps[c].nunique(dropna=True)<=30 and reps[c].nunique(dropna=True)>=2: catcols.append(c)
        cr=[]
        for c in catcols[:200]:
            for v,g in reps.groupby(reps[c].fillna('MISSING').astype(str),dropna=False):
                if len(g)<3: continue
                w=pd.to_numeric(g.event_worst,errors='coerce').fillna(0)
                cr.append({'feature':c,'feature_group':group_name(c),'value':v,'events':int(len(g)),'losers':int((w<0).sum()),'loss_rate':float((w<0).mean()),'worst_sum':float(w.sum()),'worst_pf':pf(w)})
        catsum=pd.DataFrame(cr).sort_values(['loss_rate','events'],ascending=[False,False]) if cr else pd.DataFrame(); save(catsum,out/'gold_v3_151_categorical_loss_frequency.csv')
        if not numsum.empty:
            groups=numsum.groupby('feature_group',as_index=False).agg(features=('feature','count'),max_abs_tail_delta=('abs_tail_delta','max'),mean_abs_tail_delta=('abs_tail_delta','mean'),top_feature=('feature','first')).sort_values(['max_abs_tail_delta','features'],ascending=[False,False])
        save(groups,out/'gold_v3_151_indicator_group_summary.csv')
    prog(out,1,1,'DONE',t0)
    status='READY' if not blockers else 'INPUT_MISSING'; decision='LOSER_FEATURE_SIGNATURE_READY' if not blockers else 'LOSER_FEATURE_SIGNATURE_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_150_decision':s150.get('decision',''),'source_150_selected_rule':s150.get('selected_rule',''),'progress_total_configs':1,'progress_completed_configs':1 if not blockers else 0,'progress_output':str(out/'progress.txt'),'selected_event_count':int(len(selected)) if not selected.empty else 0,'loser_event_count':int(selected.is_loser.sum()) if not selected.empty and 'is_loser' in selected.columns else 0,'numeric_feature_count':int(len(numsum)) if not numsum.empty else 0,'categorical_signature_count':int(len(catsum)) if not catsum.empty else 0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_151_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_151_decision.csv')
    lines=['GOLD V3 151 PASTE_ME_LOSER_FEATURE_SIGNATURE_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['','INDICATOR_GROUP_SUMMARY_TOP30',groups.head(30).to_string(index=False) if not groups.empty else 'NO_GROUP_ROWS']
    lines += ['','NUMERIC_FEATURE_LOSS_SIGNATURE_TOP60',numsum.head(60).to_string(index=False) if not numsum.empty else 'NO_NUMERIC_ROWS']
    lines += ['','CATEGORICAL_LOSS_FREQUENCY_TOP60',catsum.head(60).to_string(index=False) if not catsum.empty else 'NO_CATEGORICAL_ROWS']
    lines += ['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
