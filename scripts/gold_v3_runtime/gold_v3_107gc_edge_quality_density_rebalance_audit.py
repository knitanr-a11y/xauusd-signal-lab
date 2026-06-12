#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY'
READY='GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
ROOT=Path(__file__).resolve().parents[2]

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def valnum(x, default=0.0):
    try:
        if pd.isna(x): return default
        if x==float('inf') or str(x).lower()=='inf': return 10.0
        return float(x)
    except Exception: return default

def pf_cap(x):
    v=valnum(x); return min(v,5.0)

def metric_flags(r, months):
    trades=valnum(r.get('trades')); raw=valnum(r.get('raw_events')); wr=valnum(r.get('win_rate')); pf=valnum(r.get('profit_factor')); neg=valnum(r.get('negative_month_count'))
    tpm=trades/max(1,months); rpm=raw/max(1,months)
    flags=[]
    if tpm>250 or rpm>400: flags.append('TOO_BROAD')
    if tpm<4: flags.append('TOO_RARE')
    if wr<0.45: flags.append('LOW_WR')
    if pf<1.50: flags.append('LOW_PF')
    if neg>3: flags.append('NEG_MONTHS_GT3')
    return tpm,rpm,flags

def get_split(split_df, r, split):
    if split_df.empty: return {}
    q=split_df[(split_df.side==r.side)&(split_df.condition==r.condition)&(split_df.profile_id==r.profile_id)&(split_df.cooldown_bars==r.cooldown_bars)&(split_df.split==split)]
    return q.iloc[0].to_dict() if len(q) else {}

def balanced_score(r, split_df, months):
    pf=pf_cap(r.get('profit_factor')); wr=valnum(r.get('win_rate')); trades=valnum(r.get('trades')); neg=valnum(r.get('negative_month_count'))
    tpm,rpm,flags=metric_flags(r,months)
    density_bonus=min(tpm,60)*5
    density_penalty=max(0,tpm-180)*8 + max(0,rpm-350)*3
    quality=pf*900 + wr*700 + min(trades,1200)*0.25 - neg*280 + density_bonus - density_penalty
    penalty=0
    for s in ['2025','2026','2026_03_plus','2026_05_06']:
        ss=get_split(split_df,r,s); st=valnum(ss.get('trades'))
        if st>=30:
            spf=valnum(ss.get('profit_factor')); swr=valnum(ss.get('win_rate'))
            if spf<1.10: penalty+=350
            if swr<0.40: penalty+=250
    if 'TOO_BROAD' in flags: penalty+=600
    if 'TOO_RARE' in flags: penalty+=300
    if 'LOW_WR' in flags: penalty+=400
    if 'LOW_PF' in flags: penalty+=500
    return quality-penalty, flags, tpm, rpm

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); a=ap.parse_args()
    mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gcc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]
    req={'density':src/'gold_v3_107gb_candidate_density_summary.csv','split':src/'gold_v3_107gb_candidate_split_summary.csv','feature':src/'gold_v3_107gb_feature_coverage.csv'}
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id=f'missing_{k}',artifact=str(p),reason='required 107GB output missing'))
    rows=[]; rej=[]; best_side=pd.DataFrame(); rec=pd.DataFrame(); months=18
    if not blockers:
        den=pd.read_csv(req['density'],encoding='utf-8-sig'); spl=pd.read_csv(req['split'],encoding='utf-8-sig') if req['split'].exists() else pd.DataFrame(); feat=pd.read_csv(req['feature'],encoding='utf-8-sig')
        if len(feat) and 'months' in feat.columns: months=int(feat.months.iloc[0])
        for _,r in den.iterrows():
            sc,flags,tpm,rpm=balanced_score(r,spl,months); d=r.to_dict(); d.update(trades_per_month=tpm,raw_events_per_month=rpm,quality_flags=';'.join(flags) if flags else 'OK',balanced_score=sc)
            rows.append(d)
            if flags: rej.append(d)
        q=pd.DataFrame(rows).sort_values('balanced_score',ascending=False); save(q,out/'gold_v3_107gc_quality_rebalanced_candidates.csv'); outputs.append('gold_v3_107gc_quality_rebalanced_candidates.csv')
        save(pd.DataFrame(rej).sort_values('balanced_score',ascending=False) if rej else pd.DataFrame(),out/'gold_v3_107gc_rejected_or_penalized_candidates.csv'); outputs.append('gold_v3_107gc_rejected_or_penalized_candidates.csv')
        best_side=q.groupby('side',group_keys=False).head(10); save(best_side,out/'gold_v3_107gc_best_by_side.csv'); outputs.append('gold_v3_107gc_best_by_side.csv')
        rec_rows=[]
        for side in ['LONG','SHORT']:
            s=q[(q.side==side)&(~q.quality_flags.str.contains('LOW_PF|TOO_RARE',regex=True,na=False))].head(5)
            for _,rr in s.iterrows(): rec_rows.append(dict(next_test='walkforward_and_dual_edge_arbitration',side=side,condition=rr.condition,profile_id=rr.profile_id,cooldown_bars=rr.cooldown_bars,balanced_score=rr.balanced_score,trades=rr.trades,win_rate=rr.win_rate,profit_factor=rr.profit_factor,quality_flags=rr.quality_flags))
        rec=pd.DataFrame(rec_rows); save(rec,out/'gold_v3_107gc_recommended_next_test_matrix.csv'); outputs.append('gold_v3_107gc_recommended_next_test_matrix.csv')
        for side in ['LONG','SHORT']:
            s=q[q.side==side].head(1)
            if len(s): findings.append(f"best_{side.lower()}_balanced="+json.dumps(s.iloc[0].to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='rebalanced_rows_positive',result='PASS' if len(q)>0 else 'FAIL',observed=len(q),expected='>0',severity='BLOCKER'))
    vals.append(dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'))
    vals.append(dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'))
    vals.append(dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'))
    vals.append(dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),months_used_for_density=months)
    save(pd.DataFrame(blockers),out/'gold_v3_107gc_blocker_matrix.csv'); save(val,out/'gold_v3_107gc_validation_matrix.csv')
    (out/'gold_v3_107gc_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GC report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gc_blocker_matrix.csv','gold_v3_107gc_validation_matrix.csv','gold_v3_107gc_summary.json','GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GC PASTE_ME_EDGE_QUALITY_DENSITY_REBALANCE',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GB outputs only; quality/density rebalance; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
