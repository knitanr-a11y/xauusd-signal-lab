#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_161_CURRENT_BEST_PF_IDENTITY_AUDIT_ONLY'
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
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); return x
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def dedup(df):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def met(df,rc):
    if df.empty: return {'rows':0,'sum':0.0,'pf':0.0,'wr':0.0,'neg_rows':0,'unique_entry_dt':0,'months':0,'neg_months':0,'june_rows':0,'june_sum':0.0,'min_entry_dt':'','max_entry_dt':''}
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return {'rows':int(len(df)),'sum':float(r.sum()),'pf':pf(r),'wr':float((r>0).mean()),'neg_rows':int((r<0).sum()),'unique_entry_dt':int(df.entry_dt.nunique()),'months':int(len(m)),'neg_months':int((m<0).sum()),'june_rows':int((df.month=='2026-06').sum()),'june_sum':float(m.get('2026-06',0.0)),'min_entry_dt':str(df.entry_dt.min()),'max_entry_dt':str(df.entry_dt.max())}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'161'; out.mkdir(parents=True,exist_ok=True)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); s160=readj(root/'160'/'gold_v3_160_summary.json'); cur=str(s160.get('current_best_policy_key') or CUR)
    blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['worst_result_usd','result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; regime=[]; prog(out,0,1,'START',t0)
    if not blockers:
        x=prep(raw,pc,rc); c=x[x.policy_norm.eq(cur)].copy(); cut=pd.Timestamp(CUTOFF)
        rows.append({'metric_scope':'RAW_ALL_POLICY_ROWS',**met(c,rc)})
        rows.append({'metric_scope':'DEDUP_ONE_PER_ENTRY_DT',**met(dedup(c),rc)})
        rows.append({'metric_scope':'RAW_AFTER_CUTOFF',**met(c[c.entry_dt>=cut],rc)})
        rows.append({'metric_scope':'DEDUP_AFTER_CUTOFF',**met(dedup(c[c.entry_dt>=cut]),rc)})
        rows.append({'metric_scope':'RAW_BEFORE_CUTOFF',**met(c[c.entry_dt<cut],rc)})
        rows.append({'metric_scope':'DEDUP_BEFORE_CUTOFF',**met(dedup(c[c.entry_dt<cut]),rc)})
        # regime summary rows from small known dirs
        for d in ['107k2c','128','132']:
            for p in (root/d).glob('*.csv') if (root/d).exists() else []:
                try:
                    h=pd.read_csv(p,encoding='utf-8-sig',nrows=5,low_memory=False)
                except Exception:
                    continue
                if 'policy_key' in h.columns and 'oos_profit_factor' in h.columns:
                    df=load(p); z=df[df.policy_key.astype(str).eq(cur)].copy()
                    if not z.empty:
                        z.insert(0,'source_file',str(p)); regime.append(z)
        reg=pd.concat(regime,ignore_index=True) if regime else pd.DataFrame()
        save(pd.DataFrame(rows),out/'gold_v3_161_current_best_pf_modes.csv'); save(reg,out/'gold_v3_161_current_best_regime_rows.csv')
    else:
        prog(out,1,1,'BLOCKED',t0)
    modes=pd.DataFrame(rows); reg_count=0 if not regime else len(pd.concat(regime,ignore_index=True))
    status='READY' if not blockers else 'INPUT_MISSING'; decision='CURRENT_BEST_PF_IDENTITY_READY' if status=='READY' else 'CURRENT_BEST_PF_IDENTITY_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'result_column_used':rc,'policy_column_used':pc,'stage160_current_pf':s160.get('top_candidate','') and 'see_160_current_full_pf_in_ranking','mode_count':int(len(modes)),'regime_row_count':int(reg_count),'important_note':'Old PF 2.5+ is regime/OOS policy-row PF. Stage160 PF 1.45 is dedup one-entry-dt replay PF from 107k2 ledger. These are not the same metric.','source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_161_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_161_decision.csv')
    lines=['GOLD V3 161 PASTE_ME_CURRENT_BEST_PF_IDENTITY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','CURRENT_BEST_PF_MODES',modes.to_string(index=False) if not modes.empty else 'NO_MODES','','CURRENT_BEST_REGIME_ROWS',reg.to_string(index=False) if regime else 'NO_REGIME_ROWS','','INTERPRETATION','If regime rows show PF around 2.5 but dedup replay shows PF around 1.45, the difference is metric identity: raw/OOS policy rows vs one-entry-dt dedup event replay. Do not compare them as the same PF.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
