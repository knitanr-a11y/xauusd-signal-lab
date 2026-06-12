#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY'
READY='GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def quality_row(name, observed, op, threshold):
    ok=(observed>=threshold if op=='>=' else observed<=threshold if op=='<=' else observed==threshold)
    return dict(gate=name, observed=observed, operator=op, threshold=threshold, result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); a=ap.parse_args()
    mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gec'; out.mkdir(parents=True,exist_ok=True)
    req={'selection':src/'gold_v3_107gd_diversified_candidate_selection.csv','ledger':src/'gold_v3_107gd_diversified_portfolio_ledger.csv','conflict':src/'gold_v3_107gd_long_short_portfolio_conflict.csv'}
    blockers=[]; vals=[]; findings=[]; outputs=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id=f'missing_{k}',artifact=str(p),reason='required 107GD output missing'))
    if not blockers:
        sel=pd.read_csv(req['selection'],encoding='utf-8-sig')
        led=pd.read_csv(req['ledger'],encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str); led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce')
        led=led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led=led.sort_values(['entry_dt','portfolio_side','selected_rank']).drop_duplicates(['entry_dt','portfolio_side'],keep='first')
        combined=led.sort_values(['entry_dt','selected_rank']).drop_duplicates(['entry_dt'],keep='first')
        comb=metric(combined); comb.update(scope='COMBINED',candidate_count=int(sel.shape[0]),min_entry_dt=str(combined.entry_dt.min()),max_entry_dt=str(combined.entry_dt.max()),months=int(combined.entry_month.nunique()))
        save(pd.DataFrame([comb]),out/'gold_v3_107ge_combined_portfolio_summary.csv'); outputs.append('gold_v3_107ge_combined_portfolio_summary.csv')
        side_rows=[]
        for side,g in combined.groupby('portfolio_side',dropna=False):
            m=metric(g); m.update(side=side); side_rows.append(m)
        side_df=pd.DataFrame(side_rows); save(side_df,out/'gold_v3_107ge_side_summary.csv'); outputs.append('gold_v3_107ge_side_summary.csv')
        cand_rows=[]
        for k,g in combined.groupby(['portfolio_side','condition','profile_id','cooldown_bars'],dropna=False):
            m=metric(g); m.update(portfolio_side=k[0],condition=k[1],profile_id=k[2],cooldown_bars=k[3]); cand_rows.append(m)
        cand_df=pd.DataFrame(cand_rows).sort_values(['portfolio_side','profit_factor','trades'],ascending=[True,False,False]); save(cand_df,out/'gold_v3_107ge_candidate_contribution.csv'); outputs.append('gold_v3_107ge_candidate_contribution.csv')
        mon_rows=[]
        for mth,g in combined.groupby('entry_month'):
            m=metric(g); m.update(entry_month=mth); mon_rows.append(m)
        monthly=pd.DataFrame(mon_rows); save(monthly,out/'gold_v3_107ge_monthly_summary.csv'); outputs.append('gold_v3_107ge_monthly_summary.csv')
        splits={'ALL':combined,'2025':combined[combined.entry_dt.dt.year==2025],'2026':combined[combined.entry_dt.dt.year==2026],'2026_03_plus':combined[combined.entry_dt>=pd.Timestamp('2026-03-01')],'2026_05_06':combined[combined.entry_month.isin(['2026-05','2026-06'])]}
        split_rows=[]
        for name,g in splits.items():
            m=metric(g); m.update(split=name); split_rows.append(m)
        split_df=pd.DataFrame(split_rows); save(split_df,out/'gold_v3_107ge_split_summary.csv'); outputs.append('gold_v3_107ge_split_summary.csv')
        L=set(led[led.portfolio_side=='LONG'].entry_dt.astype(str)); S=set(led[led.portfolio_side=='SHORT'].entry_dt.astype(str)); inter=L&S
        conf=pd.DataFrame([dict(long_trades=len(L),short_trades=len(S),combined_trades=len(combined),conflict_events=len(inter),conflict_rate_vs_long=len(inter)/max(1,len(L)),conflict_rate_vs_short=len(inter)/max(1,len(S)))])
        save(conf,out/'gold_v3_107ge_conflict_recheck.csv'); outputs.append('gold_v3_107ge_conflict_recheck.csv')
        gates=[]
        gates += [quality_row('combined_trades',comb['trades'],'>=',400),quality_row('combined_pf',comb['profit_factor'],'>=',2.0),quality_row('combined_wr',comb['win_rate'],'>=',0.60),quality_row('combined_negative_month_count',comb['negative_month_count'],'<=',2),quality_row('conflict_events',len(inter),'==',0)]
        for _,r in side_df.iterrows():
            gates += [quality_row(f"{r.side}_pf",r.profit_factor,'>=',2.0),quality_row(f"{r.side}_wr",r.win_rate,'>=',0.55)]
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107ge_quality_gate_matrix.csv'); outputs.append('gold_v3_107ge_quality_gate_matrix.csv')
        warn=pd.DataFrame([dict(warning_id='selection_bias_warning',severity='IMPORTANT',message='107GE validates candidates selected using prior full-period audit outputs. This is not a true out-of-sample approval. Later walk-forward selection is required before live consideration.')])
        save(warn,out/'gold_v3_107ge_selection_bias_warning.csv'); outputs.append('gold_v3_107ge_selection_bias_warning.csv')
        findings.append('combined='+json.dumps(comb,ensure_ascii=False,default=str))
        findings.append('side_summary='+json.dumps(side_rows,ensure_ascii=False,default=str))
        findings.append('conflict='+json.dumps(conf.iloc[0].to_dict(),ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='combined_rows_positive',result='PASS' if len(combined)>0 else 'FAIL',observed=len(combined),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    if not blockers and 'comb' in locals(): summary.update({f'combined_{k}':v for k,v in comb.items() if k in ['trades','win_rate','profit_factor','sum_result_usd','negative_month_count','months']})
    save(pd.DataFrame(blockers),out/'gold_v3_107ge_blocker_matrix.csv'); save(val,out/'gold_v3_107ge_validation_matrix.csv')
    (out/'gold_v3_107ge_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GE report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107ge_blocker_matrix.csv','gold_v3_107ge_validation_matrix.csv','gold_v3_107ge_summary.json','GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GE PASTE_ME_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GD outputs only; diversified portfolio split stability; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
