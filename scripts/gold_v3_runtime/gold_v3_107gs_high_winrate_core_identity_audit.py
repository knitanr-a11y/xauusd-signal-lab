#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY'
READY='GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(s):
    if s: return Path(s).expanduser().resolve()
    e=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(e).expanduser().resolve() if e else Path.cwd()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metric(df):
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107grc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gsc'; out.mkdir(parents=True,exist_ok=True)
    req={'best_by_split':src/'gold_v3_107gr_best_by_split.csv','best_oos_ledger':src/'gold_v3_107gr_best_oos_trade_ledger.csv','frontier':src/'gold_v3_107gr_frontier_config_results.csv'}
    blocks=[]; vals=[]; outs=[]; finds=[]
    for k,p in req.items():
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required Stage107GR output missing'))
    if not blocks:
        best=pd.read_csv(req['best_by_split'],encoding='utf-8-sig')
        led=pd.read_csv(req['best_oos_ledger'],encoding='utf-8-sig')
        front=pd.read_csv(req['frontier'],encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led=led[led.entry_dt.notna()].copy()
        if 'global_candidate_key' not in led.columns:
            if 'candidate_key' in led.columns:
                led['global_candidate_key']=led.get('source_name','unknown').astype(str)+'::'+led.candidate_key.astype(str)
            else:
                led['global_candidate_key']='unknown'
        id_rows=[]
        for key,g in led.groupby('global_candidate_key'):
            m=metric(g); first=g.iloc[0]
            m.update(global_candidate_key=key,split_count=int(g.split.nunique()) if 'split' in g.columns else 0,splits='|'.join(sorted(g.split.astype(str).unique())) if 'split' in g.columns else '',side=str(first.get('side','')),family=str(first.get('family','')),condition=str(first.get('condition','')),profile_id=str(first.get('profile_id','')),candidate_key=str(first.get('candidate_key','')),source_name=str(first.get('source_name','')))
            id_rows.append(m)
        ident=pd.DataFrame(id_rows).sort_values(['split_count','profit_factor','win_rate','trades'],ascending=[False,False,False,False])
        save(ident,out/'gold_v3_107gs_high_wr_core_candidate_identity.csv'); outs.append('gold_v3_107gs_high_wr_core_candidate_identity.csv')
        split_summary=best.copy()
        split_summary['density_gap_to_2_per_day']=2.0-pd.to_numeric(split_summary.get('test_density',0),errors='coerce').fillna(0)
        split_summary['is_too_few_oos_trades']=pd.to_numeric(split_summary.get('test_trades',0),errors='coerce').fillna(0)<30
        save(split_summary,out/'gold_v3_107gs_split_core_summary.csv'); outs.append('gold_v3_107gs_split_core_summary.csv')
        gates=pd.DataFrame([
            qgate('best_split_wr_ge_60_count',int((best.test_wr>=0.60).sum()),'>=',2),
            qgate('best_split_density_ge_1_count',int((best.test_density>=1.0).sum()),'>=',2),
            qgate('best_split_density_ge_2_count',int((best.test_density>=2.0).sum()),'>=',1),
            qgate('candidate_identity_rows_positive',len(ident),'>=',1),
        ])
        save(gates,out/'gold_v3_107gs_frontier_gate_summary.csv'); outs.append('gold_v3_107gs_frontier_gate_summary.csv')
        trade=[]
        for d,g in front.groupby('density'):
            r=g.sort_values('frontier_score',ascending=False).iloc[0].to_dict(); trade.append(r)
        trade_df=pd.DataFrame(trade).sort_values('density')
        save(trade_df,out/'gold_v3_107gs_density_tradeoff_summary.csv'); outs.append('gold_v3_107gs_density_tradeoff_summary.csv')
        stable_count=int((ident.split_count>=2).sum()) if len(ident) and 'split_count' in ident.columns else 0
        best_wr=float(best.test_wr.max()) if len(best) else 0.0
        max_density=float(best.test_density.max()) if len(best) else 0.0
        if stable_count>0 and best_wr>=0.60 and max_density<2.0:
            decision='EXPAND_AROUND_HIGH_WR_CORE_TO_RECOVER_DENSITY'
        elif best_wr>=0.60:
            decision='HIGH_WR_EXISTS_BUT_CORE_TOO_SPARSE_NEED_DENSITY_FEATURES'
        else:
            decision='HIGH_WR_CORE_NOT_STABLE_REDESIGN_REQUIRED'
        dec=pd.DataFrame([dict(decision=decision,stable_core_candidate_count=stable_count,best_oos_win_rate=best_wr,max_best_split_density=max_density,density_retained_gate_count=int(front.get('density_retained_gate',pd.Series(dtype=bool)).sum()) if 'density_retained_gate' in front.columns else 0,next_stage='107GT_DENSITY_RECOVERY_AROUND_HIGH_WR_CORE' if 'EXPAND' in decision else '107GT_REDESIGN_FOR_DENSITY_FEATURES')])
        save(dec,out/'gold_v3_107gs_next_design_decision.csv'); outs.append('gold_v3_107gs_next_design_decision.csv')
        finds.append('next_design_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
        finds.append('top_core_candidates='+json.dumps(ident.head(10).to_dict(orient='records'),ensure_ascii=False,default=str))
        vals.append(dict(check_id='identity_rows_positive',result='PASS' if len(ident)>0 else 'FAIL',observed=len(ident),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_stop_if_over_1h')
    if not blocks:
        summary.update(identity_rows=int(len(ident)),stable_core_candidate_count=stable_count,best_oos_win_rate=best_wr,max_best_split_density=max_density,decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107gs_blocker_matrix.csv'); save(val,out/'gold_v3_107gs_validation_matrix.csv')
    outs += ['gold_v3_107gs_blocker_matrix.csv','gold_v3_107gs_validation_matrix.csv','gold_v3_107gs_summary.json','GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gs_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GS report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GS PASTE_ME_HIGH_WINRATE_CORE_IDENTITY',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GR outputs only; no M5 re-evaluation; no runtime change','runtime_estimate: light; seconds; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
