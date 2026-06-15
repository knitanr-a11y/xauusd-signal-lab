#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_164_LATER_CANDIDATES_ONE_ENTRY_AUDIT_ONLY'
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
    if df.empty: return dict(events=0,sum=0.0,pf=0.0,wr=0.0,neg=0,months=0,neg_months=0,june_events=0,june_sum=0.0,min_entry_dt='',max_entry_dt='')
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return dict(events=int(len(df)),sum=float(r.sum()),pf=pf(r),wr=float((r>0).mean()),neg=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),min_entry_dt=str(df.entry_dt.min()),max_entry_dt=str(df.entry_dt.max()))
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def one_entry(df,rc,selector='SCORE_DESC'):
    if df.empty: return df.copy()
    x=df.copy()
    if selector=='SCORE_DESC':
        sc=score_cols(x)
        for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
        if sc: return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    if selector=='BEST_RESULT_DEBUG': return x.sort_values(['entry_dt',rc],ascending=[True,False],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values(['entry_dt'],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def masks(x,cur):
    base=~x.policy_norm.eq(cur); out=[]
    if 'h1_up' in x: out.append(('ANY_H1_UP_TRUE','ANY_NON_CURRENT + h1_up=True',base & x.h1_up.astype(str).eq('True'),'BROAD_HIGH_PF'))
    if 'side' in x: out.append(('ANY_LONG','ANY_NON_CURRENT + side=LONG',base & x.side.astype(str).eq('LONG'),'BROAD_HIGH_PF'))
    out.append(('ANY_18_23','ANY_NON_CURRENT + hour_bucket=18_23',base & x.hour_bucket.eq('18_23'),'BROAD_HIGH_PF'))
    out.append(('DENSITY_Q035','density_safe||100||Q0.35 policy only',x.policy_norm.eq('density_safe||100||Q0.35'),'POLICY_ONLY'))
    out.append(('PRACTICAL_30_Q035','practical_quality||30||Q0.35 policy only',x.policy_norm.eq('practical_quality||30||Q0.35'),'POLICY_ONLY'))
    out.append(('PRACTICAL_30_Q04','practical_quality||30||Q0.4 policy only',x.policy_norm.eq('practical_quality||30||Q0.4'),'POLICY_ONLY'))
    if 'd1_dist_atr' in x: out.append(('D1_DIST_LE_164','d1_dist_atr <= -1.641755654337',base & (pd.to_numeric(x.d1_dist_atr,errors='coerce')<=-1.641755654337),'JUNE_FEATURE'))
    if 'h1_range_atr' in x: out.append(('H1_RANGE_LE_0737','h1_range_atr <= 0.737217834712',base & (pd.to_numeric(x.h1_range_atr,errors='coerce')<=0.737217834712),'HIGH_PF_FEATURE'))
    if 'm15_rsi14' in x: out.append(('M15_RSI_GE_6693','m15_rsi14 >= 66.932872868553',base & (pd.to_numeric(x.m15_rsi14,errors='coerce')>=66.932872868553),'HIGH_PF_FEATURE'))
    return out
def pref(d,p): return {p+k:v for k,v in d.items()}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'164'; out.mkdir(parents=True,exist_ok=True)
    s163=readj(root/'163'/'gold_v3_163_summary.json'); cur=str(s163.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; monthly=[]; events=[]
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        cut=pd.Timestamp(CUTOFF); configs=masks(x,cur); total=len(configs); done=0
        for lab,desc,m,kind in configs:
            done+=1; print(f'[PROGRESS] config {done}/{total} {lab}',flush=True)
            rawc=x[m].copy(); oe=one_entry(rawc,rc,'SCORE_DESC')
            rec={'candidate':lab,'description':desc,'kind':kind,'selector':'SCORE_DESC','raw_rows':int(len(rawc)),'raw_unique_entry_dt':int(rawc.entry_dt.nunique())}
            rec.update(pref(metric(oe,rc),'one_full_')); rec.update(pref(metric(oe[oe.entry_dt>=cut],rc),'one_after_')); rec.update(pref(metric(oe[oe.entry_dt<cut],rc),'one_before_'))
            if 'side' in oe.columns: rec['one_mixed_side_entry_dt']=int(rawc.groupby('entry_dt')['side'].nunique().gt(1).sum())
            else: rec['one_mixed_side_entry_dt']=0
            rec['audit_note']='later candidates are evaluated as one entry per entry_dt; no stacking'
            rows.append(rec)
            mo=oe.groupby('month')[rc].agg(['count','sum']).reset_index(); mo.insert(0,'candidate',lab); monthly.append(mo)
            tmp=oe.copy(); tmp.insert(0,'candidate',lab); events.append(tmp)
        rank=pd.DataFrame(rows); rank['rank_after_score']=rank.one_after_sum + rank.one_after_pf*50 - rank.one_full_neg_months*30 + rank.one_after_events*2
        rank=rank.sort_values(['one_after_sum','one_after_pf','one_after_events'],ascending=[False,False,False]).reset_index(drop=True)
        save(rank,out/'gold_v3_164_later_candidates_one_entry_ranking.csv'); save(pd.concat(monthly,ignore_index=True),out/'gold_v3_164_later_candidates_one_entry_monthly.csv'); save(pd.concat(events,ignore_index=True),out/'gold_v3_164_later_candidates_one_entry_events.csv')
    else:
        rank=pd.DataFrame()
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='LATER_CANDIDATES_ONE_ENTRY_READY' if status=='READY' else 'LATER_CANDIDATES_ONE_ENTRY_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'evaluation_contract':'one entry per entry_dt; no stacking; SCORE_DESC selected row','top_candidate':str(top.iloc[0].candidate) if not top.empty else '','top_one_after_events':int(top.iloc[0].one_after_events) if not top.empty else 0,'top_one_after_sum':float(top.iloc[0].one_after_sum) if not top.empty else 0.0,'top_one_after_pf':float(top.iloc[0].one_after_pf) if not top.empty else 0.0,'candidate_count':int(len(rank)) if not rank.empty else 0,'source_163_decision':s163.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_164_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_164_decision.csv')
    lines=['GOLD V3 164 PASTE_ME_LATER_CANDIDATES_ONE_ENTRY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','LATER_CANDIDATES_ONE_ENTRY_RANKING',rank.to_string(index=False) if not rank.empty else 'NO_RANKING','','INTERPRETATION','Later candidates are evaluated as one entry per same timestamp. This is deliberately separated from old current best stacking/cap review. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
