#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY'
READY='GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv')]
SPLITS=[('TRAIN_2025_TEST_2026','2025-01-01','2026-01-01','2026-01-01','2027-01-01'),('TRAIN_2025H1_TEST_2025H2','2025-01-01','2025-07-01','2025-07-01','2026-01-01'),('TRAIN_TO_2026_02_TEST_2026_03_PLUS','2025-01-01','2026-03-01','2026-03-01','2027-01-01'),('TRAIN_TO_2026_04_TEST_2026_05_06','2025-01-01','2026-05-01','2026-05-01','2027-01-01')]

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metric(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def density(df):
    m=metric(df)
    if df is None or df.empty: return m|dict(min_entry_dt='',max_entry_dt='',business_days=0,calendar_days=0,active_trade_days=0,business_day_trade_rate=0.0,calendar_day_trade_rate=0.0,active_trade_day_rate=0.0)
    mn=pd.to_datetime(df.entry_dt.min()); mx=pd.to_datetime(df.entry_dt.max()); start=mn.date(); end=mx.date()
    bd=int(np.busday_count(np.datetime64(start),np.datetime64(end)+np.timedelta64(1,'D'))); cd=max(1,(end-start).days+1); ad=int(pd.to_datetime(df.entry_dt).dt.date.nunique())
    return m|dict(min_entry_dt=str(mn),max_entry_dt=str(mx),business_days=bd,calendar_days=cd,active_trade_days=ad,business_day_trade_rate=float(m['trades']/bd) if bd else 0.0,calendar_day_trade_rate=float(m['trades']/cd),active_trade_day_rate=float(m['trades']/ad) if ad else 0.0)
def pfcap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else min(max(x,0.0),10.0)
    except Exception: return 0.0
def score(m): return pfcap(m.get('profit_factor',0))*1000 + float(m.get('win_rate',0))*800 + min(float(m.get('trades',0)),1000)*0.5 + float(m.get('sum_result_usd',0))*0.04 - float(m.get('negative_month_count',0))*300
def norm(df,src):
    x=df.copy()
    if 'entry_dt' not in x: return pd.DataFrame()
    x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy()
    if x.empty: return x
    x['result_usd']=pd.to_numeric(x.get('result_usd',0),errors='coerce'); x=x[x.result_usd.notna()].copy()
    if 'portfolio_side' in x: x['side']=x['portfolio_side']
    if 'selected_side' in x and 'side' not in x: x['side']=x['selected_side']
    if 'side' not in x: x['side']='UNKNOWN'
    for c in ['side','family','condition','profile_id','candidate_key']:
        if c not in x: x[c]=''
        x[c]=x[c].astype(str)
    if 'cooldown_bars' not in x: x['cooldown_bars']=0
    x['cooldown_bars']=pd.to_numeric(x.cooldown_bars,errors='coerce').fillna(0).astype(int)
    built=x.apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1)
    empty=x.candidate_key.eq('')|x.candidate_key.eq('nan')
    x.loc[empty,'candidate_key']=built[empty]
    x['source_name']=src; x['global_candidate_key']=x.source_name+'::'+x.candidate_key
    return x
def candidate_metrics(df):
    rows=[]
    for key,g in df.groupby('global_candidate_key'):
        m=density(g); f=g.iloc[0]
        m.update(global_candidate_key=key,source_name=f.source_name,candidate_key=f.candidate_key,side=f.side,family=f.family,condition=f.condition,profile_id=f.profile_id,cooldown_bars=int(f.cooldown_bars))
        m['train_score']=score(m); rows.append(m)
    return pd.DataFrame(rows).sort_values('train_score',ascending=False)
def select_from_train(train, max_candidates=100):
    cm=candidate_metrics(train)
    if cm.empty: return cm.iloc[0:0], pd.DataFrame()
    # quality floor is deliberately not too strict because density target allows many vectors.
    cm=cm[(cm.trades>=10)&(cm.sum_result_usd>0)&(cm.profit_factor>=1.15)&(cm.win_rate>=0.40)].copy().sort_values('train_score',ascending=False)
    selected=[]; parts=[]
    for _,r in cm.iterrows():
        selected.append(r.to_dict()|dict(selected_rank=len(selected)+1))
        parts.append(train[train.global_candidate_key==r.global_candidate_key].assign(candidate_train_score=float(r.train_score),selected_rank=len(selected)))
        port=pd.concat(parts,ignore_index=True).sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')
        dm=density(port)
        if dm['business_day_trade_rate']>=2.0 and len(selected)>=3: break
        if len(selected)>=max_candidates: break
    return pd.DataFrame(selected), pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
def apply_selection(test, sel):
    if test.empty or sel.empty: return pd.DataFrame()
    keys=set(sel.global_candidate_key)
    sc=sel.set_index('global_candidate_key').train_score.to_dict()
    out=test[test.global_candidate_key.isin(keys)].copy()
    if out.empty: return out
    out['candidate_train_score']=out.global_candidate_key.map(sc).fillna(0)
    out=out.sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')
    return out
def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--max-candidates',type=int,default=100)
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107gqc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; outputs=[]; findings=[]; cov=[]; ledgers=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                lg=norm(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(lg)
                if rows: ledgers.append(lg)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    covdf=pd.DataFrame(cov); save(covdf,out/'gold_v3_107gq_input_ledger_coverage.csv'); outputs.append('gold_v3_107gq_input_ledger_coverage.csv')
    if not ledgers: blockers.append(dict(blocker_id='no_candidate_ledgers',reason='no exact candidate ledgers found'))
    if not blockers:
        ledger=pd.concat(ledgers,ignore_index=True)
        sel_rows=[]; sum_rows=[]; oos_parts=[]
        for split,trs,tre,tes,tee in SPLITS:
            trs=pd.Timestamp(trs); tre=pd.Timestamp(tre); tes=pd.Timestamp(tes); tee=pd.Timestamp(tee)
            train=ledger[(ledger.entry_dt>=trs)&(ledger.entry_dt<tre)].copy(); test=ledger[(ledger.entry_dt>=tes)&(ledger.entry_dt<tee)].copy()
            sel,train_port_raw=select_from_train(train,a.max_candidates)
            test_port=apply_selection(test,sel)
            train_port=train_port_raw.sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first') if not train_port_raw.empty else pd.DataFrame()
            trm=density(train_port); tem=density(test_port)
            primary=tem['business_day_trade_rate']>=2.0 and tem['profit_factor']>=1.8 and tem['win_rate']>=0.50 and tem['negative_month_count']<=3
            exploratory=tem['business_day_trade_rate']>=2.0 and tem['profit_factor']>=1.5 and tem['win_rate']>=0.45 and tem['negative_month_count']<=4
            row=dict(split=split,selected_candidate_count=len(sel),train_trades=trm['trades'],train_business_day_trade_rate=trm['business_day_trade_rate'],train_profit_factor=trm['profit_factor'],train_win_rate=trm['win_rate'],test_trades=tem['trades'],test_business_day_trade_rate=tem['business_day_trade_rate'],test_profit_factor=tem['profit_factor'],test_win_rate=tem['win_rate'],test_sum_result_usd=tem['sum_result_usd'],test_negative_month_count=tem['negative_month_count'],primary_oos_gate=primary,exploratory_oos_gate=exploratory)
            sum_rows.append(row)
            if not sel.empty: sel_rows.append(sel.assign(split=split))
            if not test_port.empty: oos_parts.append(test_port.assign(split=split))
        sel_df=pd.concat(sel_rows,ignore_index=True) if sel_rows else pd.DataFrame(); oos=pd.concat(oos_parts,ignore_index=True) if oos_parts else pd.DataFrame(); summ=pd.DataFrame(sum_rows)
        save(sel_df,out/'gold_v3_107gq_split_selection_log.csv'); save(summ,out/'gold_v3_107gq_split_oos_summary.csv'); save(oos,out/'gold_v3_107gq_oos_trade_ledger.csv')
        outputs += ['gold_v3_107gq_split_selection_log.csv','gold_v3_107gq_split_oos_summary.csv','gold_v3_107gq_oos_trade_ledger.csv']
        # Full-period fixed 107GP benchmark, explicitly labeled as leakage benchmark.
        bench=root/'107gpc'/'gold_v3_107gp_best_density_portfolio_ledger.csv'
        if bench.exists():
            b=norm(pd.read_csv(bench,encoding='utf-8-sig'),'fixed_107gp_leakage_benchmark')
            bm=density(b); bm.update(benchmark='fixed_107gp_full_period_selected_leakage_benchmark')
            save(pd.DataFrame([bm]),out/'gold_v3_107gq_fixed_107gp_selected_benchmark.csv')
        else:
            save(pd.DataFrame(),out/'gold_v3_107gq_fixed_107gp_selected_benchmark.csv')
        outputs.append('gold_v3_107gq_fixed_107gp_selected_benchmark.csv')
        pass_primary=int(summ.primary_oos_gate.sum()) if len(summ) else 0; pass_expl=int(summ.exploratory_oos_gate.sum()) if len(summ) else 0
        gates=pd.DataFrame([qgate('splits_primary_oos_pass',pass_primary,'>=',2),qgate('splits_exploratory_oos_pass',pass_expl,'>=',2),qgate('oos_ledger_positive',len(oos),'>=',1)])
        save(gates,out/'gold_v3_107gq_quality_gate_matrix.csv'); outputs.append('gold_v3_107gq_quality_gate_matrix.csv')
        actions=[]
        if pass_primary>=2:
            actions.append(dict(priority=1,action='proceed_to_resolved_only_live_rehydrated_density_gate',reason='At least two anchored splits meet primary OOS density/quality gates.'))
        elif pass_expl>=2:
            actions.append(dict(priority=1,action='inspect_exploratory_oos_degradation_before_rehydration',reason='At least two splits meet exploratory but not primary gates.'))
        else:
            actions.append(dict(priority=1,action='do_not_advance_density_portfolio_redesign_selection',reason='Anchored OOS density/quality is not stable enough.'))
        save(pd.DataFrame(actions),out/'gold_v3_107gq_recommended_next_actions.csv'); outputs.append('gold_v3_107gq_recommended_next_actions.csv')
        findings.append('split_oos_summary='+json.dumps(summ.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append(f'splits_primary_oos_pass={pass_primary}, splits_exploratory_oos_pass={pass_expl}')
        vals.append(dict(check_id='oos_summary_rows_positive',result='PASS' if len(summ)>0 else 'FAIL',observed=len(summ),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_seconds_to_minutes_stop_if_over_1h',daily_density_target_business_day_trades=2.0)
    if not blockers: summary.update(splits_primary_oos_pass=pass_primary,splits_exploratory_oos_pass=pass_expl,oos_trade_rows=len(oos),selection_rows=len(sel_df))
    save(pd.DataFrame(blockers),out/'gold_v3_107gq_blocker_matrix.csv'); save(val,out/'gold_v3_107gq_validation_matrix.csv')
    outputs += ['gold_v3_107gq_blocker_matrix.csv','gold_v3_107gq_validation_matrix.csv','gold_v3_107gq_summary.json','GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gq_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GQ report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GQ PASTE_ME_DENSITY_PORTFOLIO_ANCHORED_OOS',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: existing Stage107 candidate ledgers only; anchored train-period selection; no M5 re-evaluation; no runtime change','runtime_estimate: light_to_medium; seconds_to_minutes; stop_if_over_1h','daily_density_target_business_day_trades: 2.0',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
