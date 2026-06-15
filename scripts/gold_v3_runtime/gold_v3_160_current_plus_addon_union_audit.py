#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_160_CURRENT_PLUS_ADDON_UNION_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} {label} elapsed={time.time()-t0:.1f}s'; print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def prep(df,pc,rc):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['hour']=x.entry_dt.dt.hour
    x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
    x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0)
    return x
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def dedup(df,cur):
    if df.empty: return df.copy()
    x=df.copy(); x['_cur']=x.policy_norm.eq(cur).astype(int); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values(['entry_dt','_cur']+sc,ascending=[True,False]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1).drop(columns=['_cur'],errors='ignore')
def met(df,rc):
    if df.empty: return {'events':0,'sum':0.0,'pf':0.0,'wr':0.0,'neg_events':0,'months':0,'neg_months':0,'june_events':0,'june_sum':0.0}
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return {'events':int(len(df)),'sum':float(r.sum()),'pf':pf(r),'wr':float((r>0).mean()),'neg_events':int((r<0).sum()),'months':int(len(m)),'neg_months':int((m<0).sum()),'june_events':int((df.month=='2026-06').sum()),'june_sum':float(m.get('2026-06',0.0))}
def addpref(d,p): return {p+k:v for k,v in d.items()}
def masks(df,cur):
    base=~df.policy_norm.eq(cur); out=[]
    if 'h1_up' in df: out.append(('ANY_H1_UP_TRUE','ANY_NON_CURRENT + h1_up=True',base & df.h1_up.astype(str).eq('True')))
    if 'side' in df: out.append(('ANY_LONG','ANY_NON_CURRENT + side=LONG',base & df.side.astype(str).eq('LONG')))
    out.append(('ANY_18_23','ANY_NON_CURRENT + hour_bucket=18_23',base & df.hour_bucket.eq('18_23')))
    out.append(('DENSITY_Q035','density_safe||100||Q0.35 policy only',df.policy_norm.eq('density_safe||100||Q0.35')))
    out.append(('PRACTICAL_30_Q035','practical_quality||30||Q0.35 policy only',df.policy_norm.eq('practical_quality||30||Q0.35')))
    if 'd1_dist_atr' in df: out.append(('D1_DIST_LE_164','d1_dist_atr <= -1.641755654337',base & (pd.to_numeric(df.d1_dist_atr,errors='coerce')<=-1.641755654337)))
    if 'h1_range_atr' in df: out.append(('H1_RANGE_LE_0737','h1_range_atr <= 0.737217834712',base & (pd.to_numeric(df.h1_range_atr,errors='coerce')<=0.737217834712)))
    if 'm15_rsi14' in df: out.append(('M15_RSI_GE_6693','m15_rsi14 >= 66.932872868553',base & (pd.to_numeric(df.m15_rsi14,errors='coerce')>=66.932872868553)))
    return out
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'160'; out.mkdir(parents=True,exist_ok=True)
    s159=readj(root/'159'/'gold_v3_159_summary.json'); cur=str(s159.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['worst_result_usd','result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    prog(out,0,1,'START',t0); rows=[]; monthly=[]; evout=[]
    if not blockers:
        x=prep(raw,pc,rc); curdf=x[x.policy_norm.eq(cur)].copy(); curded=dedup(curdf,cur); cut=pd.Timestamp(CUTOFF)
        for i,(lab,desc,m) in enumerate(masks(x,cur),1):
            prog(out,i,8,lab,t0); add=x[m].copy(); union=dedup(pd.concat([curdf,add],ignore_index=True),cur)
            rec={'candidate':lab,'description':desc}
            rec.update(addpref(met(curded,rc),'current_full_')); rec.update(addpref(met(dedup(add,cur),rc),'addon_full_')); rec.update(addpref(met(union,rc),'union_full_'))
            rec.update(addpref(met(union[union.entry_dt>=cut],rc),'union_after_')); rec.update(addpref(met(union[union.entry_dt<cut],rc),'union_before_'))
            rec['added_unique_events']=rec['union_full_events']-rec['current_full_events']; rec['after_added_unique_events']=rec['union_after_events']-met(curded[curded.entry_dt>=cut],rc)['events']
            rec['audit_note']='current best preserved; dedup resolves same timestamp but addon is not gated by current-best absence'
            rows.append(rec)
            mo=union.groupby('month')[rc].agg(['count','sum']).reset_index(); mo.insert(0,'candidate',lab); monthly.append(mo)
            tmp=union[union.entry_dt>=cut].copy(); tmp.insert(0,'candidate',lab); evout.append(tmp)
        rank=pd.DataFrame(rows); rank['rank_score']=rank.union_after_sum+rank.union_after_pf*80+rank.added_unique_events*.2-rank.union_full_neg_months*50
        rank=rank.sort_values(['union_after_sum','union_after_pf'],ascending=[False,False]).reset_index(drop=True)
        save(rank,out/'gold_v3_160_current_plus_addon_union_ranking.csv'); save(pd.concat(monthly,ignore_index=True),out/'gold_v3_160_union_monthly.csv'); save(pd.concat(evout,ignore_index=True),out/'gold_v3_160_union_after_events.csv')
    else:
        rank=pd.DataFrame(); prog(out,1,1,'BLOCKED',t0)
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='CURRENT_PLUS_ADDON_UNION_READY' if status=='READY' else 'CURRENT_PLUS_ADDON_UNION_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'current_best_preserved':True,'top_candidate':str(top.iloc[0].candidate) if not top.empty else '','top_union_after_events':int(top.iloc[0].union_after_events) if not top.empty else 0,'top_union_after_sum':float(top.iloc[0].union_after_sum) if not top.empty else 0.0,'top_union_after_pf':float(top.iloc[0].union_after_pf) if not top.empty else 0.0,'candidate_count':int(len(rank)) if not rank.empty else 0,'progress_total_configs':8,'progress_completed_configs':8 if not blockers else 0,'progress_output':str(out/'progress.txt'),'source_159_decision':s159.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_160_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_160_decision.csv')
    lines=['GOLD V3 160 PASTE_ME_CURRENT_PLUS_ADDON_UNION_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','CURRENT_PLUS_ADDON_UNION_RANKING',rank.to_string(index=False) if not rank.empty else 'NO_RANKING','','INTERPRETATION','This tests whether adding high-PF addon candidates damages or improves the preserved current-best route. It is not a final/live contract.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
