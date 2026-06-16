#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_167_AUG_NEGATIVE_SOURCE_REPAIR_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'
BAD_MONTH='2025-08'

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
def metric(df,rc):
    if df.empty: return dict(events=0,sum=0.0,pf=0.0,wr=0.0,neg=0,months=0,neg_months=0,bad_month_events=0,bad_month_sum=0.0,june_events=0,june_sum=0.0)
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return dict(events=int(len(df)),sum=float(r.sum()),pf=pf(r),wr=float((r>0).mean()),neg=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),bad_month_events=int((df.month==BAD_MONTH).sum()),bad_month_sum=float(m.get(BAD_MONTH,0.0)),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)))
def pref(d,p): return {p+k:v for k,v in d.items()}
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def one_entry(df,rc):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    if sc: return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values(['entry_dt'],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def priority_union(frames,rc):
    if not frames: return pd.DataFrame()
    z=pd.concat(frames,ignore_index=True)
    z=z.sort_values(['entry_dt','priority'],ascending=[True,True],kind='mergesort')
    return z.groupby('entry_dt',as_index=False).head(1).copy()
def candidate_frame(x,rc,priority,label,desc,mask):
    raw=x[mask].copy(); oe=one_entry(raw,rc); oe=oe.copy(); oe.insert(0,'priority',priority); oe.insert(1,'candidate',label); oe.insert(2,'candidate_desc',desc); return oe
def build_candidates(x,rc):
    base=~x.policy_norm.eq(CUR)
    def num(c): return pd.to_numeric(x[c],errors='coerce') if c in x.columns else pd.Series(False,index=x.index)
    h1up=x['h1_up'].astype(str).eq('True') if 'h1_up' in x.columns else pd.Series(False,index=x.index)
    cands={}
    cands['P1_D1']=candidate_frame(x,rc,1,'P1_D1','D1_DIST_LE_164 no prune',base & (num('d1_dist_atr')<=-1.641755654337))
    cands['P2_DEN']=candidate_frame(x,rc,2,'P2_DEN','DENSITY_Q035 + d1_dist_atr <= -0.781481',x.policy_norm.eq('density_safe||100||Q0.35') & (num('d1_dist_atr')<=-0.781481))
    cands['P3_RSI']=candidate_frame(x,rc,3,'P3_RSI','M15_RSI_GE_6693 high q09',base & (num('m15_rsi14')>=66.932872868553) & (num('m15_rsi14')>=73.861004))
    cands['P4_H1_CUR']=candidate_frame(x,rc,4,'P4_H1_CUR','H1_RANGE repair current',base & (num('h1_range_atr')<=0.737217834712) & (num('d1_dist_atr')<=-0.170649))
    cands['P5_H1UP_CUR']=candidate_frame(x,rc,5,'P5_H1UP_CUR','ANY_H1_UP repair current',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978))
    # Non-result repair alternatives for P4/P5.
    cands['P4_H1_D1_STRICT']=candidate_frame(x,rc,4,'P4_H1_D1_STRICT','H1_RANGE tighter d1_dist_atr <= -0.781481',base & (num('h1_range_atr')<=0.737217834712) & (num('d1_dist_atr')<=-0.781481))
    cands['P4_H1_RSI80']=candidate_frame(x,rc,4,'P4_H1_RSI80','H1_RANGE + m15_rsi14 >= 54.503286',base & (num('h1_range_atr')<=0.737217834712) & (num('m15_rsi14')>=54.503286))
    cands['P4_H1_HOUR1217']=candidate_frame(x,rc,4,'P4_H1_HOUR1217','H1_RANGE + hour 12_17',base & (num('h1_range_atr')<=0.737217834712) & x.hour_bucket.eq('12_17'))
    cands['P4_H1_HOUR0611']=candidate_frame(x,rc,4,'P4_H1_HOUR0611','H1_RANGE + hour 06_11',base & (num('h1_range_atr')<=0.737217834712) & x.hour_bucket.eq('06_11'))
    cands['P5_H1UP_RSI80']=candidate_frame(x,rc,5,'P5_H1UP_RSI80','ANY_H1_UP combo + m15_rsi14 >= 54.559329',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978) & (num('m15_rsi14')>=54.559329))
    cands['P5_H1UP_RSI90']=candidate_frame(x,rc,5,'P5_H1UP_RSI90','ANY_H1_UP combo + m15_rsi14 >= 57.790816',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978) & (num('m15_rsi14')>=57.790816))
    cands['P5_H1UP_HOUR1217']=candidate_frame(x,rc,5,'P5_H1UP_HOUR1217','ANY_H1_UP combo + hour 12_17',base & h1up & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978) & x.hour_bucket.eq('12_17'))
    return cands
def variant_rows(cands,rc):
    variants={
        'CURRENT_P1_P2_P3_P4_P5':['P1_D1','P2_DEN','P3_RSI','P4_H1_CUR','P5_H1UP_CUR'],
        'P1_P2_P3_ONLY':['P1_D1','P2_DEN','P3_RSI'],
        'DROP_P4':['P1_D1','P2_DEN','P3_RSI','P5_H1UP_CUR'],
        'DROP_P5':['P1_D1','P2_DEN','P3_RSI','P4_H1_CUR'],
        'DROP_P4_P5':['P1_D1','P2_DEN','P3_RSI'],
        'REPLACE_P4_D1_STRICT':['P1_D1','P2_DEN','P3_RSI','P4_H1_D1_STRICT','P5_H1UP_CUR'],
        'REPLACE_P4_RSI80':['P1_D1','P2_DEN','P3_RSI','P4_H1_RSI80','P5_H1UP_CUR'],
        'REPLACE_P5_RSI80':['P1_D1','P2_DEN','P3_RSI','P4_H1_CUR','P5_H1UP_RSI80'],
        'REPLACE_P5_RSI90':['P1_D1','P2_DEN','P3_RSI','P4_H1_CUR','P5_H1UP_RSI90'],
        'REPLACE_P4_D1_STRICT_P5_RSI90':['P1_D1','P2_DEN','P3_RSI','P4_H1_D1_STRICT','P5_H1UP_RSI90'],
        'REPLACE_P4_HOUR1217_DROP_P5':['P1_D1','P2_DEN','P3_RSI','P4_H1_HOUR1217'],
        'REPLACE_P4_HOUR0611_DROP_P5':['P1_D1','P2_DEN','P3_RSI','P4_H1_HOUR0611'],
    }
    rows=[]; monthly=[]; details={}
    cut=pd.Timestamp(CUTOFF)
    for name,keys in variants.items():
        u=priority_union([cands[k] for k in keys],rc); details[name]=u
        rec={'variant':name,'keys':'+'.join(keys)}; rec.update(pref(metric(u,rc),'full_')); rec.update(pref(metric(u[u.entry_dt>=cut],rc),'after_')); rec.update(pref(metric(u[u.entry_dt<cut],rc),'before_'))
        rec['pass_zero_neg_months']=bool(rec['full_neg_months']==0)
        rec['rank_score']=rec['full_sum'] + rec['after_sum'] + rec['full_pf']*100 - rec['full_neg_months']*500 - max(0,rec['full_events']-700)*0.4
        rows.append(rec)
        mo=u.groupby(['month','candidate'])[rc].agg(['count','sum']).reset_index() if not u.empty else pd.DataFrame()
        mo.insert(0,'variant',name); monthly.append(mo)
    return pd.DataFrame(rows).sort_values(['pass_zero_neg_months','rank_score'],ascending=[False,False]), pd.concat(monthly,ignore_index=True) if monthly else pd.DataFrame(), details
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'167'; out.mkdir(parents=True,exist_ok=True)
    s166=readj(root/'166'/'gold_v3_166_summary.json')
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        cands=build_candidates(x,rc)
        packet=[]
        cut=pd.Timestamp(CUTOFF)
        for k,v in cands.items():
            rec={'key':k,'candidate':v.candidate.iloc[0] if not v.empty else k,'priority':int(v.priority.iloc[0]) if not v.empty else 99}; rec.update(pref(metric(v,rc),'one_full_')); rec.update(pref(metric(v[v.entry_dt>=cut],rc),'one_after_')); packet.append(rec)
        packet_df=pd.DataFrame(packet).sort_values(['priority','key']); save(packet_df,out/'gold_v3_167_candidate_alternative_packet.csv')
        variant_df, monthly, details=variant_rows(cands,rc); save(variant_df,out/'gold_v3_167_union_variant_metrics.csv'); save(monthly,out/'gold_v3_167_union_variant_monthly_by_candidate.csv')
        cur_u=details.get('CURRENT_P1_P2_P3_P4_P5',pd.DataFrame())
        aug_by=cur_u[cur_u.month.eq(BAD_MONTH)].groupby('candidate')[rc].agg(['count','sum']).reset_index().sort_values('sum') if not cur_u.empty else pd.DataFrame()
        save(aug_by,out/'gold_v3_167_aug_source_by_candidate_current_union.csv')
    else:
        packet_df=pd.DataFrame(); variant_df=pd.DataFrame(); monthly=pd.DataFrame(); aug_by=pd.DataFrame()
    top=variant_df.head(1) if not variant_df.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='AUG_NEGATIVE_SOURCE_REPAIR_READY' if status=='READY' else 'AUG_NEGATIVE_SOURCE_REPAIR_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'bad_month':BAD_MONTH,'evaluation_contract':'later candidates only; one entry per entry_dt; priority-dedup union; no stacking','top_variant':str(top.iloc[0].variant) if not top.empty else '','top_full_events':int(top.iloc[0].full_events) if not top.empty else 0,'top_full_sum':float(top.iloc[0].full_sum) if not top.empty else 0.0,'top_full_pf':float(top.iloc[0].full_pf) if not top.empty else 0.0,'top_full_neg_months':int(top.iloc[0].full_neg_months) if not top.empty else 0,'top_after_events':int(top.iloc[0].after_events) if not top.empty else 0,'top_after_sum':float(top.iloc[0].after_sum) if not top.empty else 0.0,'source_166_decision':s166.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_167_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_167_decision.csv')
    lines=['GOLD V3 167 PASTE_ME_AUG_NEGATIVE_SOURCE_REPAIR_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','AUG_SOURCE_BY_CANDIDATE_CURRENT_UNION',aug_by.to_string(index=False) if not aug_by.empty else 'NO_AUG_SOURCE','','UNION_VARIANT_METRICS',variant_df.head(80).to_string(index=False) if not variant_df.empty else 'NO_VARIANTS','','CANDIDATE_ALTERNATIVE_PACKET',packet_df.to_string(index=False) if not packet_df.empty else 'NO_PACKET','','INTERPRETATION','Finds which candidate caused the 2025-08 negative month and compares non-result repair variants. Month exclusion is not used as a selection rule. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
