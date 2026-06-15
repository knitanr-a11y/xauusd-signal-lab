#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,itertools
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_152_FEATURE_FILTER_VALIDATION_AUDIT_ONLY'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8'); (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def metric(df):
    if df.empty: return {'events':0,'challenger':0,'champion':0,'sum':0.0,'pf':0.0,'neg_months':0,'june_sum':0.0}
    w=pd.to_numeric(df.event_worst,errors='coerce').fillna(0); r=df.route_for_policy.astype(str)
    m=df.groupby('month').event_worst.sum() if 'month' in df.columns else pd.Series(dtype=float)
    j=float(m.get('2026-06',0.0)) if len(m) else 0.0
    return {'events':int(len(df)),'challenger':int((r=='CHALLENGER').sum()),'champion':int((r=='CHAMPION').sum()),'sum':float(w.sum()),'pf':pf(w),'neg_months':int((m<0).sum()) if len(m) else 0,'june_sum':j}
def add_pref(d,prefix): return {prefix+k:v for k,v in d.items()}
def rule_mask(df,rule):
    typ,col,op,val,scope=rule
    if col not in df.columns: return pd.Series(False,index=df.index)
    sscope=pd.Series(True,index=df.index) if scope=='ALL' else (df.route_for_policy.astype(str)==scope)
    if typ=='num':
        x=pd.to_numeric(df[col],errors='coerce')
        m=(x>=float(val)) if op=='GE' else (x<=float(val))
    else:
        m=df[col].fillna('MISSING').astype(str)==str(val)
    return sscope & m.fillna(False)
def name_rule(r): return '|'.join([str(x) for x in r])
def build_candidates(ev,numsig,catsig):
    out=[]
    if not numsig.empty:
        n=numsig.copy().sort_values('abs_tail_delta',ascending=False).head(14)
        for _,r in n.iterrows():
            f=str(r.feature)
            if f not in ev.columns: continue
            tail=str(r.risk_tail); val=float(r.q75 if tail=='HIGH' else r.q25); op='GE' if tail=='HIGH' else 'LE'
            for scope in ['ALL','CHALLENGER','CHAMPION']:
                out.append(('num',f,op,val,scope))
    if not catsig.empty:
        c=catsig.copy()
        bad_features={'is_loser','score','score_threshold','score_quantile'}
        c=c[~c.feature.astype(str).isin(bad_features)].copy()
        c['loss_rate']=pd.to_numeric(c.loss_rate,errors='coerce').fillna(0); c['events']=pd.to_numeric(c.events,errors='coerce').fillna(0)
        c=c[(c.events>=3)&(c.loss_rate>=0.60)].head(20)
        for _,r in c.iterrows():
            f=str(r.feature); v=str(r.value)
            if f not in ev.columns: continue
            for scope in ['ALL','CHALLENGER','CHAMPION']:
                out.append(('cat',f,'EQ',v,scope))
    seen=[]; uniq=[]
    for r in out:
        nm=name_rule(r)
        if nm not in seen: seen.append(nm); uniq.append(r)
    return uniq
def eval_rule(ev,rules,label):
    m=pd.Series(False,index=ev.index)
    for r in rules: m=m|rule_mask(ev,r)
    kept=ev[~m].copy(); train=kept[kept.month<='2026-01']; valid=kept[kept.month>='2026-02']
    base={'rule_label':label,'removed':int(m.sum())}
    base.update(add_pref(metric(kept),'full_')); base.update(add_pref(metric(train),'train_')); base.update(add_pref(metric(valid),'valid_'))
    return base, kept

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'152'; out.mkdir(parents=True,exist_ok=True)
    s151=readj(root/'151'/'gold_v3_151_summary.json'); ev=load(root/'151'/'gold_v3_151_selected_events_enriched.csv'); ns=load(root/'151'/'gold_v3_151_numeric_feature_loss_signature.csv'); cs=load(root/'151'/'gold_v3_151_categorical_loss_frequency.csv'); probs=[]
    if ev.empty: probs.append({'id':'missing_151_enriched'})
    if ns.empty and cs.empty: probs.append({'id':'missing_151_signatures'})
    rows=[]; best_events=pd.DataFrame(); done=0; total=1
    if not probs:
        ev['entry_dt']=pd.to_datetime(ev.entry_dt,errors='coerce'); ev=ev[ev.entry_dt.notna()].copy(); ev['month']=ev.entry_dt.dt.to_period('M').astype(str); ev['event_worst']=pd.to_numeric(ev.event_worst,errors='coerce').fillna(0)
        ev['route_for_policy']=ev.route_for_policy.astype(str)
        cands=build_candidates(ev,ns,cs)
        pairs=list(itertools.combinations(cands[:24],2))
        configs=[('BASE',[])]+[(name_rule(r),[r]) for r in cands]+[(name_rule(a)+' && '+name_rule(b),[a,b]) for a,b in pairs]
        total=len(configs); prog(out,0,total,'START',t0); cache={}
        for i,(label,rs) in enumerate(configs,1):
            rec,kept=eval_rule(ev,rs,label); rows.append(rec); cache[label]=kept; done=i
            if i%10==0 or i==total: prog(out,i,total,label[:80],t0)
        rank=pd.DataFrame(rows)
        base=rank[rank.rule_label=='BASE'].iloc[0]
        ok=(rank.rule_label!='BASE')&(rank.full_events>=70)&(rank.valid_events>=20)&(rank.full_sum>=float(base.full_sum))&(rank.valid_sum>=float(base.valid_sum))&(rank.valid_neg_months<=int(base.valid_neg_months))&(rank.full_neg_months<=int(base.full_neg_months))
        rank['tier']='REJECTED'; rank.loc[ok,'tier']='PASS'; rank['tier_order']=rank.tier.map({'PASS':0,'REJECTED':1}).fillna(9); rank['rank_score']=rank.valid_sum+rank.valid_pf*100-rank.valid_neg_months*500+rank.full_sum*0.2-rank.removed*0.1
        rank=rank.sort_values(['tier_order','valid_neg_months','valid_sum','full_sum','full_events'],ascending=[True,True,False,False,False]).reset_index(drop=True)
        key=str(rank.iloc[0].rule_label); best_events=cache.get(key,pd.DataFrame())
        save(rank,out/'gold_v3_152_feature_filter_validation_ranking.csv'); save(best_events,out/'gold_v3_152_selected_feature_filter_events.csv')
    else:
        rank=pd.DataFrame()
    selected=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not probs else 'INPUT_MISSING'
    if probs: dec='FEATURE_FILTER_VALIDATION_INPUT_MISSING'
    elif selected.empty: dec='FEATURE_FILTER_VALIDATION_NO_CONFIG'
    elif str(selected.iloc[0].tier)=='PASS': dec='FEATURE_FILTER_VALIDATION_PASS_REVIEW'
    else: dec='FEATURE_FILTER_VALIDATION_NO_PASS_FOUND'
    summary={'step':STEP,'status':status,'ready':not probs,'decision':dec,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_151_decision':s151.get('decision',''),'split':'train_month<=2026-01 validation_month>=2026-02','progress_total_configs':total,'progress_completed_configs':done,'progress_output':str(out/'progress.txt'),'selected_rule_label':str(selected.iloc[0].rule_label) if not selected.empty else '','selected_tier':str(selected.iloc[0].tier) if not selected.empty and 'tier' in selected else '','selected_removed':int(selected.iloc[0].removed) if not selected.empty else 0,'selected_full_events':int(selected.iloc[0].full_events) if not selected.empty else 0,'selected_full_sum':float(selected.iloc[0].full_sum) if not selected.empty else 0.0,'selected_full_pf':float(selected.iloc[0].full_pf) if not selected.empty else 0.0,'selected_full_neg_months':int(selected.iloc[0].full_neg_months) if not selected.empty else 0,'selected_valid_events':int(selected.iloc[0].valid_events) if not selected.empty else 0,'selected_valid_sum':float(selected.iloc[0].valid_sum) if not selected.empty else 0.0,'selected_valid_pf':float(selected.iloc[0].valid_pf) if not selected.empty else 0.0,'selected_valid_neg_months':int(selected.iloc[0].valid_neg_months) if not selected.empty else 0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(probs),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_152_summary.json').write_text(json.dumps(summary|{'blockers':probs},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_152_decision.csv')
    lines=['GOLD V3 152 PASTE_ME_FEATURE_FILTER_VALIDATION_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP60_FEATURE_FILTER_VALIDATION',rank.head(60).to_string(index=False) if not rank.empty else 'NO_RANKING','','BLOCKERS','NO_BLOCKERS' if not probs else json.dumps(probs,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not probs,'decision':dec,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not probs else 2
if __name__=='__main__': raise SystemExit(main())
