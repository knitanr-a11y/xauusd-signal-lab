#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_169_PARALLEL_BUCKET_CAP_AUDIT_ONLY'
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
    if df.empty: return dict(orders=0,entry_dt=0,sum=0.0,row_pf=0.0,wr=0.0,neg_orders=0,months=0,neg_months=0,june_orders=0,june_sum=0.0,max_orders_per_entry_dt=0,gt15_entry_dt=0,gt10_entry_dt=0)
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum(); cnt=df.groupby('entry_dt').size()
    return dict(orders=int(len(df)),entry_dt=int(df.entry_dt.nunique()),sum=float(r.sum()),row_pf=pf(r),wr=float((r>0).mean()),neg_orders=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_orders=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),max_orders_per_entry_dt=int(cnt.max()) if len(cnt) else 0,gt15_entry_dt=int((cnt>15).sum()) if len(cnt) else 0,gt10_entry_dt=int((cnt>10).sum()) if len(cnt) else 0)
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
def side_set(g):
    if 'side' not in g.columns: return set()
    return set([str(x) for x in g['side'].dropna().unique() if str(x)!='nan'])
def current_cap10(x,rc):
    out=[]; mixed=0
    for dt,g in x[x.policy_norm.eq(CUR)].groupby('entry_dt',sort=True):
        ss=side_set(g)
        if len(ss)>1: mixed+=1; continue
        out.append(sort_score(g).head(10).copy())
    c=pd.concat(out,ignore_index=True) if out else pd.DataFrame(columns=x.columns)
    c=c.copy(); c.insert(0,'bucket','CURRENT'); c.insert(1,'candidate','CURRENT_CAP10'); c.insert(2,'lot_units',1)
    return c,mixed
def build_later_candidates(x,rc):
    base=~x.policy_norm.eq(CUR)
    def num(c): return pd.to_numeric(x[c],errors='coerce') if c in x.columns else pd.Series(False,index=x.index)
    h1up=x['h1_up'].astype(str).eq('True') if 'h1_up' in x.columns else pd.Series(False,index=x.index)
    specs=[
      ('P1_D1','D1_DIST_LE_164 no prune',base & (num('d1_dist_atr')<=-1.641755654337)),
      ('P2_DEN','density Q0.35 + d1_dist_atr <= -0.781481',x.policy_norm.eq('density_safe||100||Q0.35') & (num('d1_dist_atr')<=-0.781481)),
      ('P3_RSI','M15_RSI_GE_6693 high q09',base & (num('m15_rsi14')>=66.932872868553) & (num('m15_rsi14')>=73.861004)),
      ('P4_H1_D1_STRICT','H1_RANGE repaired d1 strict',base & (num('h1_range_atr')<=0.737217834712) & (num('d1_dist_atr')<=-0.781481)),
      ('P5_H1UP_CUR','ANY_H1_UP repaired combo',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978)),
    ]
    frames=[]; packet=[]
    cut=pd.Timestamp(CUTOFF)
    for i,(lab,desc,mask) in enumerate(specs,1):
        oe=one_entry(x[mask].copy(),rc)
        if oe.empty: continue
        oe=oe.copy(); oe.insert(0,'bucket','LATER'); oe.insert(1,'candidate',lab); oe.insert(2,'lot_units',1); oe['candidate_desc']=desc
        frames.append(oe)
        rec={'candidate':lab,'desc':desc}; rec.update(pref(metric(oe,rc),'one_full_')); rec.update(pref(metric(oe[oe.entry_dt>=cut],rc),'one_after_')); packet.append(rec)
    z=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=x.columns)
    return z,pd.DataFrame(packet)
def skip_later_internal_mixed(later):
    if later.empty: return later.copy(),0
    keep=[]; mixed=0
    for dt,g in later.groupby('entry_dt',sort=True):
        ss=side_set(g)
        if len(ss)>1: mixed+=1; continue
        keep.append(g)
    return (pd.concat(keep,ignore_index=True) if keep else pd.DataFrame(columns=later.columns)), mixed
def combine(cur,later,mode):
    if mode=='CURRENT_ONLY': return cur.copy(),0
    if mode=='LATER_ONLY_SKIP_INTERNAL_MIXED': return later.copy(),0
    dropped=0; frames=[]
    all_dt=sorted(set(cur.entry_dt.unique()) | set(later.entry_dt.unique()))
    for dt in all_dt:
        cg=cur[cur.entry_dt.eq(dt)]; lg=later[later.entry_dt.eq(dt)]
        cs=side_set(cg); ls=side_set(lg)
        conflict=bool(cs and ls and cs!=ls)
        if conflict and mode=='PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT':
            dropped+=1; continue
        if conflict and mode=='PARALLEL_SKIP_LATER_ON_BUCKET_CONFLICT':
            dropped+=1; frames.append(cg); continue
        frames.extend([cg,lg])
    return (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=cur.columns)), dropped
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'169'; out.mkdir(parents=True,exist_ok=True)
    s168=readj(root/'168'/'gold_v3_168_summary.json')
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; monthly=[]; packet=pd.DataFrame(); conflict_summary=pd.DataFrame()
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        cur,cur_mixed=current_cap10(x,rc); later_raw,packet=build_later_candidates(x,rc); later,later_mixed=skip_later_internal_mixed(later_raw)
        save(cur,out/'gold_v3_169_current_cap10_orders.csv'); save(later,out/'gold_v3_169_later_cap5_internal_mixed_skipped_orders.csv'); save(packet,out/'gold_v3_169_later_candidate_packet.csv')
        current_dt=set(cur.entry_dt.unique()) if not cur.empty else set(); later_dt=set(later.entry_dt.unique()) if not later.empty else set(); overlap_dt=current_dt & later_dt
        bucket_conflict=0; same_side_overlap=0
        for dt in overlap_dt:
            cs=side_set(cur[cur.entry_dt.eq(dt)]); ls=side_set(later[later.entry_dt.eq(dt)])
            if cs and ls and cs!=ls: bucket_conflict+=1
            else: same_side_overlap+=1
        conflict_summary=pd.DataFrame([{'current_internal_mixed_skipped':cur_mixed,'later_internal_mixed_skipped':later_mixed,'current_entry_dt':len(current_dt),'later_entry_dt':len(later_dt),'overlap_entry_dt':len(overlap_dt),'bucket_conflict_entry_dt':bucket_conflict,'same_side_overlap_entry_dt':same_side_overlap}])
        save(conflict_summary,out/'gold_v3_169_conflict_summary.csv')
        modes=['CURRENT_ONLY','LATER_ONLY_SKIP_INTERNAL_MIXED','PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT','PARALLEL_SKIP_LATER_ON_BUCKET_CONFLICT','PARALLEL_ALLOW_BUCKET_HEDGE']
        cut=pd.Timestamp(CUTOFF)
        for mode in modes:
            df,dropped=combine(cur,later,mode)
            rec={'variant':mode,'bucket_conflict_dropped_entry_dt':dropped}; rec.update(pref(metric(df,rc),'full_')); rec.update(pref(stack_metric(df,rc),'full_')); rec.update(pref(metric(df[df.entry_dt>=cut],rc),'after_')); rec.update(pref(stack_metric(df[df.entry_dt>=cut],rc),'after_'))
            rec['max_lot_if_001_per_order']=round(rec['full_max_orders_per_entry_dt']*0.01,2)
            rows.append(rec)
            mo=df.groupby('month')[rc].agg(['count','sum']).reset_index(); mo.insert(0,'variant',mode); monthly.append(mo)
        rank=pd.DataFrame(rows).sort_values(['full_gt15_entry_dt','bucket_conflict_dropped_entry_dt','full_stack_pf','full_sum'],ascending=[True,True,False,False]); save(rank,out/'gold_v3_169_parallel_bucket_variant_metrics.csv')
        save(pd.concat(monthly,ignore_index=True),out/'gold_v3_169_parallel_bucket_monthly.csv')
    else: rank=pd.DataFrame()
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='PARALLEL_BUCKET_CAP_READY' if status=='READY' else 'PARALLEL_BUCKET_CAP_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'evaluation_contract':'current best max10 orders + later candidates max5 one-per-candidate; no priority between buckets; later internal mixed side skipped','lot_assumption':'0.01 lot per order; max 15 orders means max 0.15 lot if current and later same timestamp both fire','conflict_policy_under_review':'later internal LONG/SHORT conflict skipped; bucket conflict variants compared','top_variant':str(top.iloc[0].variant) if not top.empty else '','top_full_orders':int(top.iloc[0].full_orders) if not top.empty else 0,'top_full_sum':float(top.iloc[0].full_sum) if not top.empty else 0.0,'top_full_stack_pf':float(top.iloc[0].full_stack_pf) if not top.empty else 0.0,'top_full_neg_months':int(top.iloc[0].full_neg_months) if not top.empty else 0,'top_full_max_orders_per_entry_dt':int(top.iloc[0].full_max_orders_per_entry_dt) if not top.empty else 0,'top_max_lot_if_001_per_order':float(top.iloc[0].max_lot_if_001_per_order) if not top.empty else 0.0,'source_168_decision':s168.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_169_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_169_decision.csv')
    lines=['GOLD V3 169 PASTE_ME_PARALLEL_BUCKET_CAP_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','CONFLICT_SUMMARY',conflict_summary.to_string(index=False) if not conflict_summary.empty else 'NO_CONFLICT_SUMMARY','','PARALLEL_BUCKET_VARIANT_METRICS',rank.to_string(index=False) if not rank.empty else 'NO_VARIANTS','','LATER_CANDIDATE_PACKET',packet.to_string(index=False) if not packet.empty else 'NO_PACKET','','INTERPRETATION','Tests the user proposal: current best can emit up to 10 x 0.01 lots, later candidates can emit up to 5 x 0.01 lots. Later internal mixed-side timestamps are skipped. Bucket-level conflicts are compared as variants. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
