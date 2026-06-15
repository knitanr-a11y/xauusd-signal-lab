#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_154_FILTER_ORDER_AUDIT_ONLY'
RULE_COOLDOWN=('num','cooldown_bars','GE','4.0','CHALLENGER')
RULE_CHAMP_D1R=('num','d1_range_atr','LE','0.721925170969071','CHAMPION')

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
def hb(h):
    h=int(h); return '00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23'))
def yes(s): return s.astype(str).str.lower().isin(['true','1','yes'])
def choose_rep(df):
    sc=[c for c in ['feature_score','score','ledger_score','max_score'] if c in df.columns]
    for c in sc: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.sort_values(sc,ascending=[False]*len(sc)).head(1) if sc else df.head(1)
def prep_stage145(df):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=pd.to_datetime(x.date,errors='coerce').dt.to_period('M').astype(str); x['hour_bucket']=x.entry_dt.dt.hour.map(hb)
    x=x[yes(x.kept_after_score_trim)&(x.chosen_route_score_trimmed.astype(str)!='NO_ROUTE')].copy()
    x['route_for_policy']=x.chosen_route_score_trimmed.astype(str)
    x['event_worst']=pd.to_numeric(x.worst_result_usd_trimmed,errors='coerce').fillna(0); x['event_rep']=pd.to_numeric(x.rep_result_usd_trimmed,errors='coerce').fillna(0); x['base_event_id']=range(len(x))
    return x
def enrich(ev,ledger,s133):
    pmap={'CHAMPION':str(s133.get('champion_policy_key','density_safe||100||Q0.6')),'CHALLENGER':str(s133.get('selected_challenger_policy_key','density_safe||100||Q0.35'))}
    ev=ev.copy(); ev['policy_key']=ev.route_for_policy.map(pmap); ledger=ledger.copy(); ledger['entry_dt']=pd.to_datetime(ledger.entry_dt,errors='coerce')
    m=ledger.merge(ev[['base_event_id','entry_dt','policy_key','route_for_policy','event_worst','event_rep','month','hour_bucket']],on=['entry_dt','policy_key'],how='inner')
    if m.empty: return ev
    return m.groupby('base_event_id',group_keys=False).apply(lambda g: choose_rep(g.copy())).reset_index(drop=True)
def metric(df):
    if df.empty: return dict(events=0,champion=0,challenger=0,sum=0.0,pf=0.0,neg_months=0,june_events=0,june_sum=0.0)
    w=pd.to_numeric(df.event_worst,errors='coerce').fillna(0); r=df.route_for_policy.astype(str); m=df.groupby('month').event_worst.sum()
    return dict(events=int(len(df)),champion=int((r=='CHAMPION').sum()),challenger=int((r=='CHALLENGER').sum()),sum=float(w.sum()),pf=pf(w),neg_months=int((m<0).sum()),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)))
def mask_hour(df):
    r=df.route_for_policy.astype(str); h=df.hour_bucket.astype(str)
    return ((r=='CHAMPION')&(h=='00_05')) | ((r=='CHALLENGER')&(h=='06_11'))
def mask_score_tail(df):
    r=df.route_for_policy.astype(str); x=pd.to_numeric(df.get('score',pd.Series([math.nan]*len(df))),errors='coerce')
    ch=df[(r=='CHALLENGER')&x.notna()].copy().sort_values('entry_dt')
    if ch.empty: return pd.Series(False,index=df.index)
    rem=pd.Series(False,index=df.index); hist=[]
    for idx,row in ch.iterrows():
        h=pd.Series(hist).dropna(); th=float(h.quantile(.8)) if len(h)>=30 else math.nan; sc=x.loc[idx]
        if not math.isnan(th) and pd.notna(sc) and float(sc)>=th: rem.loc[idx]=True
        hist.append(sc)
    return rem
def mask_feature(df,rules):
    rem=pd.Series(False,index=df.index)
    for typ,col,op,val,scope in rules:
        if col not in df.columns: continue
        sm=pd.Series(True,index=df.index) if scope=='ALL' else (df.route_for_policy.astype(str)==scope)
        if typ=='num':
            x=pd.to_numeric(df[col],errors='coerce'); v=float(val); m=(x>=v) if op=='GE' else (x<=v)
        else: m=df[col].fillna('MISSING').astype(str)==str(val)
        rem=rem|(sm&m.fillna(False))
    return rem
def apply_order(base,steps,label):
    x=base.copy(); rem_total=pd.Series(False,index=x.index); detail=[]
    for st in steps:
        cur=x[~rem_total].copy()
        if st=='HOUR': m=mask_hour(cur)
        elif st=='SCORE_TAIL': m=mask_score_tail(cur)
        elif st=='FEATURE_COOLDOWN': m=mask_feature(cur,[RULE_COOLDOWN])
        elif st=='FEATURE_COMBO': m=mask_feature(cur,[RULE_COOLDOWN,RULE_CHAMP_D1R])
        else: m=pd.Series(False,index=cur.index)
        rem_total.loc[m.index]=rem_total.loc[m.index]|m
        detail.append({'rule_label':label,'step':st,'removed_in_step':int(m.sum()),'remaining_after_step':int((~rem_total).sum())})
    kept=x[~rem_total].copy(); return kept,pd.DataFrame(detail),int(rem_total.sum())
def month(df,label):
    rows=[]
    for mo,g in df.groupby('month'):
        w=pd.to_numeric(g.event_worst,errors='coerce').fillna(0); r=g.route_for_policy.astype(str)
        rows.append(dict(rule_label=label,month=mo,events=int(len(g)),champion=int((r=='CHAMPION').sum()),challenger=int((r=='CHALLENGER').sum()),sum=float(w.sum()),pf=pf(w),neg_events=int((w<0).sum())))
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'154'; out.mkdir(parents=True,exist_ok=True)
    s133=readj(root/'133'/'gold_v3_133_summary.json'); src145=load(root/'145'/'gold_v3_145_selected_trim_reconstructed_events.csv'); ledger=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    if src145.empty: blockers.append({'id':'missing_145_reconstructed_events'})
    if ledger.empty: blockers.append({'id':'missing_107k2c_ledger'})
    configs=[('BASE_145_AFTER_SCORE_TRIM',[]),('FEATURE_FIRST_COOLDOWN_ONLY',['FEATURE_COOLDOWN']),('FEATURE_FIRST_COMBO',['FEATURE_COMBO']),('HOUR_FIRST',['HOUR']),('HOUR_THEN_SCORE_THEN_FEATURE_COMBO',['HOUR','SCORE_TAIL','FEATURE_COMBO']),('FEATURE_COMBO_THEN_HOUR_THEN_SCORE',['FEATURE_COMBO','HOUR','SCORE_TAIL']),('FEATURE_COOLDOWN_THEN_HOUR_THEN_SCORE',['FEATURE_COOLDOWN','HOUR','SCORE_TAIL']),('HOUR_THEN_FEATURE_COMBO_NO_SCORE',['HOUR','FEATURE_COMBO'])]
    prog(out,0,len(configs),'START',t0); rows=[]; months=[]; steps=[]; best=pd.DataFrame(); done=0
    if not blockers:
        base=prep_stage145(src145); enr=enrich(base,ledger,s133); enr['entry_dt']=pd.to_datetime(enr.entry_dt,errors='coerce'); enr['month']=enr.month.astype(str); enr['hour_bucket']=enr.hour_bucket.astype(str); enr['route_for_policy']=enr.route_for_policy.astype(str); enr['event_worst']=pd.to_numeric(enr.event_worst,errors='coerce').fillna(0); save(enr,out/'gold_v3_154_enriched_stage145_events.csv')
        for i,(label,seq) in enumerate(configs,1):
            kept,det,removed=apply_order(enr,seq,label); mt=metric(kept); rows.append({'rule_label':label,'order_sequence':' > '.join(seq) if seq else 'NONE','removed':removed,**mt}); months.append(month(kept,label)); steps.append(det); done=i; prog(out,i,len(configs),label,t0)
        rank=pd.DataFrame(rows); mon=pd.concat(months,ignore_index=True); stepdf=pd.concat(steps,ignore_index=True) if steps else pd.DataFrame()
        rank['tier']='REVIEW'; rank['rank_score']=rank['sum']+rank['pf']*100-rank['neg_months']*500+rank['june_sum']-rank['removed']*.1
        rank=rank.sort_values(['neg_months','sum','pf','events'],ascending=[True,False,False,False]).reset_index(drop=True); best_label=str(rank.iloc[0].rule_label); best=mon[mon.rule_label==best_label].copy()
        save(rank,out/'gold_v3_154_filter_order_ranking.csv'); save(mon,out/'gold_v3_154_filter_order_monthly.csv'); save(stepdf,out/'gold_v3_154_filter_order_step_detail.csv'); save(best,out/'gold_v3_154_selected_order_monthly.csv')
    else:
        rank=pd.DataFrame(); best=pd.DataFrame()
    selected=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'
    dec='FILTER_ORDER_REVIEW_READY' if not blockers else 'FILTER_ORDER_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':dec,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'purpose':'compare whether feature filters should be applied before hour/score filters from Stage145 base','progress_total_configs':len(configs),'progress_completed_configs':done,'progress_output':str(out/'progress.txt'),'selected_rule_label':str(selected.iloc[0].rule_label) if not selected.empty else '','selected_order_sequence':str(selected.iloc[0].order_sequence) if not selected.empty else '','selected_removed':int(selected.iloc[0].removed) if not selected.empty else 0,'selected_events':int(selected.iloc[0].events) if not selected.empty else 0,'selected_challenger':int(selected.iloc[0].challenger) if not selected.empty else 0,'selected_sum':float(selected.iloc[0]['sum']) if not selected.empty else 0.0,'selected_pf':float(selected.iloc[0].pf) if not selected.empty else 0.0,'selected_neg_months':int(selected.iloc[0].neg_months) if not selected.empty else 0,'selected_june_events':int(selected.iloc[0].june_events) if not selected.empty else 0,'selected_june_sum':float(selected.iloc[0].june_sum) if not selected.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_154_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_154_decision.csv')
    lines=['GOLD V3 154 PASTE_ME_FILTER_ORDER_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','FILTER_ORDER_RANKING',rank.to_string(index=False) if not rank.empty else 'NO_RANKING','','SELECTED_ORDER_MONTHLY',best.to_string(index=False) if not best.empty else 'NO_SELECTED_MONTHLY','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
