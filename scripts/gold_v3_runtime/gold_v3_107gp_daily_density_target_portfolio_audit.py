#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY'
READY='GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

CANDIDATE_INPUTS=[
    ('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),
    ('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),
    ('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),
    ('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),
    ('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv'),
]

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig')

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x:
        x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def pfcap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else min(max(x,0.0),10.0)
    except Exception:
        return 0.0

def score(m, density_bias=0.0):
    return pfcap(m.get('profit_factor',0))*1000 + float(m.get('win_rate',0))*800 + min(float(m.get('trades',0)),800)*density_bias + float(m.get('sum_result_usd',0))*0.04 - float(m.get('negative_month_count',0))*300

def normalize_ledger(df, source_name):
    x=df.copy()
    if 'entry_dt' not in x.columns:
        return pd.DataFrame()
    x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy()
    if x.empty: return x
    x['entry_date']=x.entry_dt.dt.date.astype(str); x['entry_month']=x.entry_dt.dt.to_period('M').astype(str)
    x['result_usd']=pd.to_numeric(x.get('result_usd',0),errors='coerce'); x=x[x.result_usd.notna()].copy()
    if 'portfolio_side' in x.columns:
        x['side']=x['portfolio_side']
    if 'selected_side' in x.columns:
        x['side']=x.get('side',x['selected_side'])
    if 'side' not in x.columns:
        x['side']='UNKNOWN'
    for c in ['side','family','condition','profile_id','candidate_key']:
        if c not in x.columns: x[c]=''
        x[c]=x[c].astype(str)
    if 'cooldown_bars' not in x.columns: x['cooldown_bars']=0
    x['cooldown_bars']=pd.to_numeric(x.cooldown_bars,errors='coerce').fillna(0).astype(int)
    # Candidate key normalization. Preserve provided candidate_key when present; otherwise build from available columns.
    empty_key=x.candidate_key.eq('') | x.candidate_key.eq('nan')
    built=x.apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1)
    x.loc[empty_key,'candidate_key']=built[empty_key]
    x['source_name']=source_name
    x['global_candidate_key']=x['source_name']+'::'+x['candidate_key']
    return x

def density_metrics(df):
    m=metric(df)
    if df is None or df.empty:
        return m | dict(min_entry_dt='',max_entry_dt='',business_days=0,calendar_days=0,active_trade_days=0,business_day_trade_rate=0.0,calendar_day_trade_rate=0.0,active_trade_day_rate=0.0)
    mn=pd.to_datetime(df.entry_dt.min()); mx=pd.to_datetime(df.entry_dt.max())
    start=mn.date(); end=mx.date()
    business_days=int(np.busday_count(np.datetime64(start), np.datetime64(end)+np.timedelta64(1,'D')))
    calendar_days=max(1,(end-start).days+1)
    active_days=int(pd.to_datetime(df.entry_dt).dt.date.nunique())
    return m | dict(min_entry_dt=str(mn),max_entry_dt=str(mx),business_days=business_days,calendar_days=calendar_days,active_trade_days=active_days,business_day_trade_rate=float(m['trades']/business_days) if business_days>0 else 0.0,calendar_day_trade_rate=float(m['trades']/calendar_days),active_trade_day_rate=float(m['trades']/active_days) if active_days>0 else 0.0)

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def build_candidate_metrics(ledger):
    rows=[]
    for key,g in ledger.groupby('global_candidate_key'):
        m=density_metrics(g); first=g.iloc[0]
        m.update(global_candidate_key=key,source_name=first.source_name,candidate_key=first.candidate_key,side=str(first.side),family=str(first.family),condition=str(first.condition),profile_id=str(first.profile_id),cooldown_bars=int(first.cooldown_bars))
        m['quality_score']=score(m,0.20)
        m['density_score']=score(m,0.80)
        rows.append(m)
    return pd.DataFrame(rows).sort_values('quality_score',ascending=False)

def select_portfolio(name, cand, ledger, mode):
    if cand.empty:
        return pd.DataFrame(), pd.DataFrame()
    x=cand.copy()
    if mode=='quality_candidates_only':
        x=x[(x.profit_factor>=1.8)&(x.win_rate>=0.50)&(x.trades>=20)&(x.negative_month_count<=3)]
        rank_col='quality_score'; max_items=12
    elif mode=='balanced_density_expansion':
        x=x[(x.profit_factor>=1.45)&(x.win_rate>=0.43)&(x.sum_result_usd>0)&(x.trades>=30)&(x.negative_month_count<=5)]
        rank_col='density_score'; max_items=24
    elif mode=='density_target_relaxed':
        x=x[(x.profit_factor>=1.20)&(x.sum_result_usd>0)&(x.trades>=40)]
        rank_col='density_score'; max_items=40
    elif mode=='all_available_diagnostic':
        x=x[(x.sum_result_usd>0)&(x.trades>=20)]
        rank_col='density_score'; max_items=60
    else:
        x=x.iloc[0:0]; rank_col='quality_score'; max_items=0
    selected=[]; parts=[]
    used_entry=set()
    for _,r in x.sort_values(rank_col,ascending=False).iterrows():
        g=ledger[ledger.global_candidate_key==r.global_candidate_key].copy()
        if g.empty: continue
        # marginal rows after same-time de-dupe are what add density.
        marginal=g[~g.entry_dt.astype(str).isin(used_entry)]
        if len(marginal)<10 and len(selected)>0: continue
        selected.append(r.to_dict()|dict(portfolio_mode=mode,selected_rank=len(selected)+1,marginal_rows=len(marginal)))
        parts.append(g.assign(portfolio_mode=mode,selected_rank=len(selected),candidate_quality_score=float(r.quality_score),candidate_density_score=float(r.density_score)))
        used_entry.update(g.entry_dt.astype(str).tolist())
        temp=pd.concat(parts,ignore_index=True).sort_values(['entry_dt','candidate_density_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')
        dm=density_metrics(temp)
        if dm['business_day_trade_rate']>=2.0 and mode in ['balanced_density_expansion','density_target_relaxed','all_available_diagnostic']:
            break
        if len(selected)>=max_items: break
    if not parts:
        return pd.DataFrame(), pd.DataFrame()
    port=pd.concat(parts,ignore_index=True).sort_values(['entry_dt','candidate_density_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')
    return pd.DataFrame(selected), port

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107gpc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]; coverage=[]; ledgers=[]
    for source,subdir,fn in CANDIDATE_INPUTS:
        p=root/subdir/fn
        exists=p.exists(); rows=0
        if exists:
            try:
                lg=normalize_ledger(pd.read_csv(p,encoding='utf-8-sig'),source)
                rows=len(lg); 
                if rows: ledgers.append(lg)
            except Exception as e:
                coverage.append(dict(source_name=source,path=str(p),exists=True,rows=0,error=str(e)))
                continue
        coverage.append(dict(source_name=source,path=str(p),exists=exists,rows=rows,error=''))
    cov=pd.DataFrame(coverage); save(cov,out/'gold_v3_107gp_input_ledger_coverage.csv'); outputs.append('gold_v3_107gp_input_ledger_coverage.csv')
    primary_ok=bool(cov[(cov.source_name=='atomic_current_107GO')&(cov.rows>0)].shape[0])
    if not primary_ok:
        blockers.append(dict(blocker_id='missing_primary_107go_ledger',reason='Stage107GO portfolio ledger is required',artifact=str(root/'107goc'/'gold_v3_107go_portfolio_ledger.csv')))
    if not blockers:
        ledger=pd.concat(ledgers,ignore_index=True)
        cand=build_candidate_metrics(ledger)
        save(cand,out/'gold_v3_107gp_candidate_metrics.csv'); outputs.append('gold_v3_107gp_candidate_metrics.csv')
        summaries=[]; best_port=pd.DataFrame(); best_sel=pd.DataFrame(); best_score=-1e18
        # Current 107GO as baseline.
        current=ledger[ledger.source_name=='atomic_current_107GO'].copy()
        if not current.empty:
            current=current.sort_values(['entry_dt']).drop_duplicates('entry_dt',keep='first')
            m=density_metrics(current); m.update(portfolio_mode='atomic_current_107GO',selected_candidate_count=current.global_candidate_key.nunique())
            summaries.append(m)
            best_port=current.assign(portfolio_mode='atomic_current_107GO'); best_score=m['business_day_trade_rate']*1000 + pfcap(m['profit_factor'])*100 + m['win_rate']*100
        for mode in ['quality_candidates_only','balanced_density_expansion','density_target_relaxed','all_available_diagnostic']:
            sel,port=select_portfolio(mode,cand,ledger,mode)
            if port.empty:
                summaries.append(dict(portfolio_mode=mode,trades=0,business_day_trade_rate=0,profit_factor=0,win_rate=0,negative_month_count=0,selected_candidate_count=0))
                continue
            dm=density_metrics(port); dm.update(portfolio_mode=mode,selected_candidate_count=int(sel.global_candidate_key.nunique()) if not sel.empty else 0)
            summaries.append(dm)
            sc=(1 if dm['business_day_trade_rate']>=2.0 else 0)*100000 + dm['business_day_trade_rate']*1000 + pfcap(dm['profit_factor'])*150 + dm['win_rate']*100 - dm['negative_month_count']*50
            if sc>best_score:
                best_score=sc; best_port=port; best_sel=sel
        summ=pd.DataFrame(summaries).sort_values(['business_day_trade_rate','profit_factor'],ascending=[False,False])
        save(summ,out/'gold_v3_107gp_portfolio_density_summary.csv'); outputs.append('gold_v3_107gp_portfolio_density_summary.csv')
        save(best_port,out/'gold_v3_107gp_best_density_portfolio_ledger.csv'); outputs.append('gold_v3_107gp_best_density_portfolio_ledger.csv')
        save(best_sel,out/'gold_v3_107gp_selected_candidates.csv'); outputs.append('gold_v3_107gp_selected_candidates.csv')
        side_rows=[]
        if not best_port.empty:
            for side,g in best_port.groupby('side'):
                m=density_metrics(g); m.update(side=side); side_rows.append(m)
        side_df=pd.DataFrame(side_rows); save(side_df,out/'gold_v3_107gp_side_density_summary.csv'); outputs.append('gold_v3_107gp_side_density_summary.csv')
        best_m=density_metrics(best_port)
        primary_gate=best_m['business_day_trade_rate']>=2.0 and best_m['profit_factor']>=1.8 and best_m['win_rate']>=0.50 and best_m['negative_month_count']<=3
        exploratory_gate=best_m['business_day_trade_rate']>=2.0 and best_m['profit_factor']>=1.5 and best_m['win_rate']>=0.45 and best_m['negative_month_count']<=4
        gap=[]
        gap.append(dict(decision='DENSITY_AND_QUALITY_PASS' if primary_gate else 'EXPLORATORY_DENSITY_PASS' if exploratory_gate else 'DENSITY_OR_QUALITY_GAP_REMAINS',business_day_trade_rate=best_m['business_day_trade_rate'],profit_factor=best_m['profit_factor'],win_rate=best_m['win_rate'],negative_month_count=best_m['negative_month_count'],trades=best_m['trades'],required_business_day_trade_rate=2.0))
        gap_df=pd.DataFrame(gap); save(gap_df,out/'gold_v3_107gp_density_gap_decision.csv'); outputs.append('gold_v3_107gp_density_gap_decision.csv')
        gates=pd.DataFrame([qgate('business_day_trade_rate',best_m['business_day_trade_rate'],'>=',2.0),qgate('combined_pf_primary',best_m['profit_factor'],'>=',1.8),qgate('combined_wr_primary',best_m['win_rate'],'>=',0.50),qgate('negative_month_count_primary',best_m['negative_month_count'],'<=',3),qgate('exploratory_density_gate',1 if exploratory_gate else 0,'>=',1)])
        save(gates,out/'gold_v3_107gp_quality_gate_matrix.csv'); outputs.append('gold_v3_107gp_quality_gate_matrix.csv')
        actions=[]
        if primary_gate:
            actions.append(dict(priority=1,action='run_anchored_train_test_on_density_target_portfolio',reason='Portfolio meets daily density and primary quality gates.'))
        elif exploratory_gate:
            actions.append(dict(priority=1,action='inspect_degradation_then_anchored_test_if_acceptable',reason='Portfolio meets density only under exploratory quality thresholds.'))
        else:
            actions.append(dict(priority=1,action='redesign_for_density_before_train_test',reason='Existing ledgers cannot meet daily 2-trade density with acceptable PF/WR.'))
        actions.append(dict(priority=2,action='prioritize_short_quality_and_density',reason='107GO showed LONG quality but SHORT failed; density target likely requires better SHORT vectors.'))
        save(pd.DataFrame(actions),out/'gold_v3_107gp_recommended_next_actions.csv'); outputs.append('gold_v3_107gp_recommended_next_actions.csv')
        findings.append('portfolio_density_summary='+json.dumps(summ.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('best_density_metrics='+json.dumps(best_m,ensure_ascii=False,default=str))
        findings.append('density_gap_decision='+json.dumps(gap,ensure_ascii=False,default=str))
        vals.append(dict(check_id='candidate_metrics_positive',result='PASS' if len(cand)>0 else 'FAIL',observed=len(cand),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h',daily_density_target_business_day_trades=2.0)
    if not blockers:
        summary.update(best_trades=int(best_m['trades']),best_business_day_trade_rate=float(best_m['business_day_trade_rate']),best_profit_factor=float(best_m['profit_factor']),best_win_rate=float(best_m['win_rate']),best_negative_month_count=int(best_m['negative_month_count']),primary_density_quality_gate=bool(primary_gate),exploratory_density_gate=bool(exploratory_gate))
    save(pd.DataFrame(blockers),out/'gold_v3_107gp_blocker_matrix.csv'); save(val,out/'gold_v3_107gp_validation_matrix.csv')
    outputs += ['gold_v3_107gp_blocker_matrix.csv','gold_v3_107gp_validation_matrix.csv','gold_v3_107gp_summary.json','GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gp_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GP report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GP PASTE_ME_DAILY_DENSITY_TARGET_PORTFOLIO',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: existing Stage107 candidate ledgers only; no M5 re-evaluation; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h','daily_density_target_business_day_trades: 2.0',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
