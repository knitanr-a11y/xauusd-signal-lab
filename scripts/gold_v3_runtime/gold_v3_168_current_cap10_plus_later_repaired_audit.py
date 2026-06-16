#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_168_CURRENT_CAP10_PLUS_LATER_REPAIRED_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def metric(df,rc):
    if df.empty: return dict(orders=0,entry_dt=0,sum=0.0,row_pf=0.0,wr=0.0,neg_orders=0,months=0,neg_months=0,june_orders=0,june_sum=0.0,max_orders_per_entry_dt=0,gt10_entry_dt=0)
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum(); cnt=df.groupby('entry_dt').size()
    return dict(orders=int(len(df)),entry_dt=int(df.entry_dt.nunique()),sum=float(r.sum()),row_pf=pf(r),wr=float((r>0).mean()),neg_orders=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_orders=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),max_orders_per_entry_dt=int(cnt.max()) if len(cnt) else 0,gt10_entry_dt=int((cnt>10).sum()) if len(cnt) else 0)
def stack_metric(df,rc):
    if df.empty: return dict(stack_count=0,stack_sum=0.0,stack_pf=0.0,stack_wr=0.0,stack_neg=0)
    s=df.groupby('entry_dt')[rc].sum()
    return dict(stack_count=int(len(s)),stack_sum=float(s.sum()),stack_pf=pf(s),stack_wr=float((s>0).mean()),stack_neg=int((s<0).sum()))
def pref(d,p): return {p+k:v for k,v in d.items()}
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def sort_score(df):
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values(sc,ascending=[False]*len(sc),kind='mergesort') if sc else x
def one_entry(df,rc):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    if sc: return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values(['entry_dt'],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def current_cap10(x,rc):
    out=[]
    for dt,g in x[x.policy_norm.eq(CUR)].groupby('entry_dt',sort=True):
        if 'side' in g.columns and g.side.nunique(dropna=True)>1: continue
        s=sort_score(g).head(10).copy(); out.append(s)
    c=pd.concat(out,ignore_index=True) if out else pd.DataFrame(columns=x.columns)
    c=c.copy(); c.insert(0,'system','CURRENT_CAP10'); c.insert(1,'exec_priority',1); c.insert(2,'candidate','CURRENT_CAP10_SCORE_DROP_MIXED')
    return c
def repaired_later(x,rc):
    base=~x.policy_norm.eq(CUR)
    def num(c): return pd.to_numeric(x[c],errors='coerce') if c in x.columns else pd.Series(False,index=x.index)
    h1up=x['h1_up'].astype(str).eq('True') if 'h1_up' in x.columns else pd.Series(False,index=x.index)
    specs=[
      (11,'P1_D1','D1 no prune',base & (num('d1_dist_atr')<=-1.641755654337)),
      (12,'P2_DEN','density q035 d1 strict',x.policy_norm.eq('density_safe||100||Q0.35') & (num('d1_dist_atr')<=-0.781481)),
      (13,'P3_RSI','m15 rsi high',base & (num('m15_rsi14')>=66.932872868553) & (num('m15_rsi14')>=73.861004)),
      (14,'P4_H1_D1_STRICT','h1 range d1 strict',base & (num('h1_range_atr')<=0.737217834712) & (num('d1_dist_atr')<=-0.781481)),
      (15,'P5_H1UP_CUR','h1 up repaired current',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978)),
    ]
    frames=[]
    for pr,lab,desc,mask in specs:
        oe=one_entry(x[mask].copy(),rc)
        if oe.empty: continue
        oe=oe.copy(); oe['later_priority']=pr; oe['candidate']=lab; oe['candidate_desc']=desc; frames.append(oe)
    if not frames: return pd.DataFrame(columns=x.columns)
    z=pd.concat(frames,ignore_index=True).sort_values(['entry_dt','later_priority'],kind='mergesort')
    u=z.groupby('entry_dt',as_index=False).head(1).copy(); u.insert(0,'system','LATER_REPAIRED_ONE_ENTRY'); u.insert(1,'exec_priority',2)
    return u
def make_variants(cur,later,rc):
    out={}
    out['CURRENT_ONLY_CAP10']=cur.copy()
    out['LATER_ONLY_REPAIRED']=later.copy()
    out['ADDITIVE_ALLOW_GT10']=pd.concat([cur,later],ignore_index=True)
    # current first global 10: later is added only when current has fewer than 10 at same timestamp.
    z=pd.concat([cur,later],ignore_index=True).sort_values(['entry_dt','exec_priority'],kind='mergesort')
    out['GLOBAL_CAP10_CURRENT_FIRST']=z.groupby('entry_dt',as_index=False).head(10).copy()
    z2=pd.concat([cur,later.assign(exec_priority=0)],ignore_index=True).sort_values(['entry_dt','exec_priority'],kind='mergesort')
    out['GLOBAL_CAP10_LATER_FIRST']=z2.groupby('entry_dt',as_index=False).head(10).copy()
    cur_dt=set(cur.entry_dt.unique()) if not cur.empty else set()
    out['SKIP_LATER_WHEN_CURRENT_PRESENT']=pd.concat([cur,later[~later.entry_dt.isin(cur_dt)]],ignore_index=True)
    return out
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'168'; out.mkdir(parents=True,exist_ok=True)
    s167=readj(root/'167'/'gold_v3_167_summary.json')
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; monthly=[]; overlap=pd.DataFrame()
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        cur=current_cap10(x,rc); later=repaired_later(x,rc)
        save(cur,out/'gold_v3_168_current_cap10_orders.csv'); save(later,out/'gold_v3_168_later_repaired_one_entry_orders.csv')
        o_dt=set(cur.entry_dt.unique()) & set(later.entry_dt.unique())
        overlap=pd.DataFrame([{'overlap_entry_dt_count':len(o_dt),'later_entry_dt_count':int(later.entry_dt.nunique()) if not later.empty else 0,'current_entry_dt_count':int(cur.entry_dt.nunique()) if not cur.empty else 0,'later_overlap_sum':float(later[later.entry_dt.isin(o_dt)][rc].sum()) if not later.empty else 0.0,'later_non_overlap_sum':float(later[~later.entry_dt.isin(o_dt)][rc].sum()) if not later.empty else 0.0}])
        save(overlap,out/'gold_v3_168_overlap_summary.csv')
        cut=pd.Timestamp(CUTOFF)
        for name,df in make_variants(cur,later,rc).items():
            rec={'variant':name}; rec.update(pref(metric(df,rc),'full_')); rec.update(pref(stack_metric(df,rc),'full_')); rec.update(pref(metric(df[df.entry_dt>=cut],rc),'after_')); rec.update(pref(stack_metric(df[df.entry_dt>=cut],rc),'after_'))
            rows.append(rec)
            mo=df.groupby('month')[rc].agg(['count','sum']).reset_index(); mo.insert(0,'variant',name); monthly.append(mo)
        rank=pd.DataFrame(rows).sort_values(['full_gt10_entry_dt','full_stack_pf','full_sum'],ascending=[True,False,False]); save(rank,out/'gold_v3_168_combined_variant_metrics.csv')
        save(pd.concat(monthly,ignore_index=True),out/'gold_v3_168_combined_variant_monthly.csv')
    else: rank=pd.DataFrame()
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='CURRENT_CAP10_PLUS_LATER_REPAIRED_READY' if status=='READY' else 'CURRENT_CAP10_PLUS_LATER_REPAIRED_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'evaluation_contract':'current best cap10 stack plus later repaired one-entry; variants compare overlap/risk cap behavior','current_best_contract':'score desc; drop mixed side; max 10 rows per entry_dt','later_contract':'REPLACE_P4_D1_STRICT repaired packet; one entry per entry_dt; priority dedup; no stacking','top_variant':str(top.iloc[0].variant) if not top.empty else '','top_full_orders':int(top.iloc[0].full_orders) if not top.empty else 0,'top_full_sum':float(top.iloc[0].full_sum) if not top.empty else 0.0,'top_full_stack_pf':float(top.iloc[0].full_stack_pf) if not top.empty else 0.0,'top_full_neg_months':int(top.iloc[0].full_neg_months) if not top.empty else 0,'top_full_max_orders_per_entry_dt':int(top.iloc[0].full_max_orders_per_entry_dt) if not top.empty else 0,'top_full_gt10_entry_dt':int(top.iloc[0].full_gt10_entry_dt) if not top.empty else 0,'source_167_decision':s167.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_168_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_168_decision.csv')
    lines=['GOLD V3 168 PASTE_ME_CURRENT_CAP10_PLUS_LATER_REPAIRED_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','OVERLAP_SUMMARY',overlap.to_string(index=False) if not overlap.empty else 'NO_OVERLAP_SUMMARY','','COMBINED_VARIANT_METRICS',rank.to_string(index=False) if not rank.empty else 'NO_VARIANTS','','INTERPRETATION','Compares old current-best cap10 stack with repaired later one-entry packet. ADDITIVE may exceed 10 orders at a timestamp; GLOBAL_CAP10 variants enforce a total cap of 10. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
