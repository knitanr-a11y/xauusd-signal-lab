#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY'
READY='GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def split_df(df):
    out=[]
    splits={'ALL':df,'2025':df[df.entry_dt.dt.year==2025],'2026':df[df.entry_dt.dt.year==2026],'2026_03_plus':df[df.entry_dt>=pd.Timestamp('2026-03-01')],'2026_05_06':df[df.entry_month.isin(['2026-05','2026-06'])]}
    for k,g in splits.items():
        m=metric(g); m['split']=k; out.append(m)
    return out

def gate(name, obs, ok, exp, sev='AUDIT'):
    return dict(gate_id=name,result='PASS' if ok else 'FAIL',observed=obs,expected=exp,severity=sev)

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); a=ap.parse_args()
    mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gec'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]
    paths={
        'selection':src/'gold_v3_107gd_diversified_candidate_selection.csv',
        'ledger':src/'gold_v3_107gd_diversified_portfolio_ledger.csv',
        'summary':src/'gold_v3_107gd_diversified_portfolio_summary.csv',
        'conflict':src/'gold_v3_107gd_long_short_portfolio_conflict.csv'}
    for k,p in paths.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required 107GD output missing'))
    gates=[]; pack_status='BLOCKED'
    if not blockers:
        sel=pd.read_csv(paths['selection'],encoding='utf-8-sig'); led=pd.read_csv(paths['ledger'],encoding='utf-8-sig'); con=pd.read_csv(paths['conflict'],encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led=led[led.entry_dt.notna()].copy(); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        side_rows=[]
        for side,g in led.groupby('portfolio_side',dropna=False):
            for r in split_df(g): r.update(portfolio_side=side); side_rows.append(r)
        side_sum=pd.DataFrame(side_rows); save(side_sum,out/'gold_v3_107ge_side_portfolio_split_summary.csv'); outputs.append('gold_v3_107ge_side_portfolio_split_summary.csv')
        comb=led.sort_values(['entry_dt','portfolio_side','selected_rank']).drop_duplicates(['entry_dt'],keep='first')
        comb_rows=split_df(comb); comb_sum=pd.DataFrame(comb_rows); save(comb_sum,out/'gold_v3_107ge_combined_portfolio_split_summary.csv'); outputs.append('gold_v3_107ge_combined_portfolio_split_summary.csv')
        mon=[]
        for side,g in led.groupby('portfolio_side',dropna=False):
            for month,gg in g.groupby('entry_month'):
                m=metric(gg); m.update(portfolio_side=side,entry_month=month); mon.append(m)
        for month,gg in comb.groupby('entry_month'):
            m=metric(gg); m.update(portfolio_side='COMBINED',entry_month=month); mon.append(m)
        mon_df=pd.DataFrame(mon); save(mon_df,out/'gold_v3_107ge_portfolio_monthly_summary.csv'); outputs.append('gold_v3_107ge_portfolio_monthly_summary.csv')
        contrib=[]
        cols=['portfolio_side','side','condition','profile_id','cooldown_bars','selected_rank']
        for k,g in led.groupby(cols,dropna=False):
            m=metric(g); m.update({c:v for c,v in zip(cols,k)}); contrib.append(m)
        contrib_df=pd.DataFrame(contrib).sort_values(['portfolio_side','selected_rank']); save(contrib_df,out/'gold_v3_107ge_candidate_contribution_summary.csv'); outputs.append('gold_v3_107ge_candidate_contribution_summary.csv')
        ca=con.iloc[0].to_dict() if len(con) else {}; conflict=int(float(ca.get('conflict_events',999)))
        allc=comb_sum[comb_sum.split=='ALL'].iloc[0].to_dict(); gates.append(gate('conflict_events_zero',conflict,conflict==0,'0'))
        gates.append(gate('combined_all_pf_ge_1_80',allc.get('profit_factor'),float(allc.get('profit_factor',0))>=1.8,'>=1.80'))
        gates.append(gate('combined_all_wr_ge_0_55',allc.get('win_rate'),float(allc.get('win_rate',0))>=0.55,'>=0.55'))
        gates.append(gate('combined_negative_month_count_le_2',allc.get('negative_month_count'),float(allc.get('negative_month_count',99))<=2,'<=2'))
        for side in ['LONG','SHORT']:
            q=side_sum[(side_sum.portfolio_side==side)&(side_sum.split=='ALL')]
            if len(q): gates.append(gate(f'{side.lower()}_all_pf_ge_1_80',q.iloc[0].profit_factor,float(q.iloc[0].profit_factor)>=1.8,'>=1.80'))
        for split in ['2025','2026','2026_03_plus','2026_05_06']:
            q=comb_sum[comb_sum.split==split]
            if len(q):
                r=q.iloc[0]; obs=f"trades={r.trades}, pf={r.profit_factor}, wr={r.win_rate}"
                ok=(r.trades<30) or (float(r.profit_factor)>= (1.1 if split!='2025' and split!='2026' else 1.2))
                gates.append(gate(f'combined_{split}_pf_floor_when_trades_ge_30',obs,ok,'pf>=floor if trades>=30'))
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107ge_stability_gate_matrix.csv'); outputs.append('gold_v3_107ge_stability_gate_matrix.csv')
        pack_status='CANDIDATE_PACK_AUDIT_PASS' if gate_df.result.eq('PASS').all() else 'NEEDS_MORE_AUDIT'
        pack=dict(candidate_pack_status=pack_status,combined_all=allc,side_all=side_sum[side_sum.split=='ALL'].to_dict('records'),conflict=ca,candidate_count_by_side=sel.groupby('side').size().to_dict() if 'side' in sel else {})
        (out/'gold_v3_107ge_candidate_pack_audit.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2,default=str),encoding='utf-8'); outputs.append('gold_v3_107ge_candidate_pack_audit.json')
        findings.append('candidate_pack_status='+pack_status)
        findings.append('combined_all='+json.dumps(allc,ensure_ascii=False,default=str))
        findings.append('conflict='+json.dumps(ca,ensure_ascii=False,default=str))
        vals.append(dict(check_id='ledger_rows_positive',result='PASS' if len(led)>0 else 'FAIL',observed=len(led),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),candidate_pack_status=pack_status)
    save(pd.DataFrame(blockers),out/'gold_v3_107ge_blocker_matrix.csv'); save(val,out/'gold_v3_107ge_validation_matrix.csv')
    (out/'gold_v3_107ge_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GE report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107ge_blocker_matrix.csv','gold_v3_107ge_validation_matrix.csv','gold_v3_107ge_summary.json','GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GE PASTE_ME_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GD diversified portfolio outputs only; split/monthly/candidate-pack audit; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','STABILITY_GATES',pd.DataFrame(gates).to_string(index=False) if gates else 'NO_GATES','','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
