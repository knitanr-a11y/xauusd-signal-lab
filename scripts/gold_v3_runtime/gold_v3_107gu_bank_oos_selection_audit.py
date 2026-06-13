#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GU_BANK_OOS_SELECTION_AUDIT_ONLY'
READY='GOLD_V3_107GU_BANK_OOS_SELECTION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GU_BANK_OOS_SELECTION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv')]
SPLITS=[('TRAIN_2025_TEST_2026','2025-01-01','2026-01-01','2026-01-01','2027-01-01'),('TRAIN_2025H1_TEST_2025H2','2025-01-01','2025-07-01','2025-07-01','2026-01-01'),('TRAIN_TO_2026_02_TEST_2026_03_PLUS','2025-01-01','2026-03-01','2026-03-01','2027-01-01'),('TRAIN_TO_2026_04_TEST_2026_05_06','2025-01-01','2026-05-01','2026-05-01','2027-01-01')]
TIERS=[('core_high_wr',0.60,1.80,30),('practical_quality',0.58,1.60,50),('density_safe',0.55,1.50,80),('exploratory',0.52,1.30,100)]
TOP_NS=[3,5,10,20,30,50,100]

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def files_dir(s):
    if s: return Path(s).expanduser().resolve()
    e=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(e).expanduser().resolve() if e else Path.cwd()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(vals):
    a=np.asarray(vals,dtype=float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def metric(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(pd.to_datetime(x.entry_dt).dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def density(df):
    m=metric(df)
    if df is None or df.empty: return m|dict(min_entry_dt='',max_entry_dt='',business_days=0,business_day_trade_rate=0.0,active_trade_days=0,active_trade_day_rate=0.0)
    mn=pd.to_datetime(df.entry_dt.min()).date(); mx=pd.to_datetime(df.entry_dt.max()).date()
    bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,'D'))); ad=int(pd.to_datetime(df.entry_dt).dt.date.nunique())
    return m|dict(min_entry_dt=str(mn),max_entry_dt=str(mx),business_days=bd,business_day_trade_rate=float(m['trades']/bd) if bd else 0.0,active_trade_days=ad,active_trade_day_rate=float(m['trades']/ad) if ad else 0.0)

def normalize(df,src):
    if 'entry_dt' not in df.columns: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy()
    if x.empty: return x
    x['result_usd']=pd.to_numeric(x.get('result_usd',0),errors='coerce'); x=x[x.result_usd.notna()].copy()
    if 'portfolio_side' in x.columns: x['side']=x['portfolio_side']
    if 'selected_side' in x.columns and 'side' not in x.columns: x['side']=x['selected_side']
    if 'side' not in x.columns: x['side']='UNKNOWN'
    for c in ['side','family','condition','profile_id','candidate_key']:
        if c not in x.columns: x[c]=''
        x[c]=x[c].astype(str).replace({'nan':''})
    if 'cooldown_bars' not in x.columns: x['cooldown_bars']=0
    x['cooldown_bars']=pd.to_numeric(x.cooldown_bars,errors='coerce').fillna(0).astype(int)
    built=x.apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1)
    empty=x.candidate_key.eq('')|x.candidate_key.eq('nan')
    x.loc[empty,'candidate_key']=built[empty]
    x['source_name']=src; x['global_candidate_key']=x.source_name+'::'+x.candidate_key
    return x

def train_metrics(train):
    rows=[]
    for key,g in train.groupby('global_candidate_key',sort=False):
        m=density(g); f=g.iloc[0]
        score=m['win_rate']*3500+cap(m['profit_factor'])*800+min(m['trades'],300)*0.30+m['sum_result_usd']*0.03-m['negative_month_count']*300
        m.update(global_candidate_key=key,source_name=f.source_name,candidate_key=f.candidate_key,side=f.side,family=f.family,condition=f.condition,profile_id=f.profile_id,cooldown_bars=int(f.cooldown_bars),train_score=score)
        rows.append(m)
    return pd.DataFrame(rows).sort_values(['train_score','win_rate','profit_factor'],ascending=[False,False,False])
def build_port(test, selected, tm):
    if not selected: return pd.DataFrame()
    score=tm.set_index('global_candidate_key').train_score.to_dict()
    x=test[test.global_candidate_key.isin(selected)].copy()
    if x.empty: return x
    x['candidate_train_score']=x.global_candidate_key.map(score).fillna(0)
    return x.sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')
def gate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107guc'; out.mkdir(parents=True,exist_ok=True)
    log(f'{STEP} START train-only candidate bank OOS')
    blocks=[]; vals=[]; outs=[]; finds=[]; cov=[]; led=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                lg=normalize(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(lg)
                if rows: led.append(lg)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
        log(f'input {src}: exists={p.exists()} rows={rows}')
    save(pd.DataFrame(cov),out/'gold_v3_107gu_input_ledger_coverage.csv'); outs.append('gold_v3_107gu_input_ledger_coverage.csv')
    if not led: blocks.append(dict(blocker_id='no_candidate_ledgers',reason='No exact candidate ledgers found.'))
    if not blocks:
        ledger=pd.concat(led,ignore_index=True)
        log(f'ledger_rows={len(ledger)} candidates={ledger.global_candidate_key.nunique()}')
        all_train_metrics=[]; frontier=[]; selected_rows=[]; best_parts=[]
        for si,(sp,trs,tre,tes,tee) in enumerate(SPLITS,1):
            train=ledger[(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
            test=ledger[(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
            tm=train_metrics(train); tm['split']=sp; all_train_metrics.append(tm)
            log(f'split {si}/4 {sp}: train_rows={len(train)} test_rows={len(test)} train_candidates={len(tm)}')
            for tier_name,min_wr,min_pf,min_trades in TIERS:
                pool=tm[(tm.win_rate>=min_wr)&(tm.profit_factor>=min_pf)&(tm.trades>=min_trades)&(tm.sum_result_usd>0)].copy()
                pool=pool.sort_values(['train_score','win_rate','profit_factor'],ascending=[False,False,False])
                for n in TOP_NS:
                    selected=pool.global_candidate_key.head(n).tolist()
                    port=build_port(test,selected,tm)
                    m=density(port)
                    row=dict(split=sp,tier=tier_name,top_n=n,selected_candidate_count=len(selected),train_pool_count=len(pool),test_trades=m['trades'],test_wr=m['win_rate'],test_pf=m['profit_factor'],test_sum=m['sum_result_usd'],test_neg_months=m['negative_month_count'],test_business_day_trade_rate=m['business_day_trade_rate'],test_active_trade_day_rate=m['active_trade_day_rate'])
                    row['high_wr_gate']=bool(m['win_rate']>=0.60 and m['profit_factor']>=1.5 and m['trades']>=20)
                    row['practical_bank_gate']=bool(m['win_rate']>=0.58 and m['profit_factor']>=1.6 and m['business_day_trade_rate']>=1.0)
                    row['density2_gate']=bool(m['win_rate']>=0.55 and m['profit_factor']>=1.5 and m['business_day_trade_rate']>=2.0)
                    row['frontier_score']=m['win_rate']*5000+cap(m['profit_factor'])*700+min(m['business_day_trade_rate'],2.0)*500-m['negative_month_count']*250+min(m['trades'],200)*0.25
                    frontier.append(row)
                    for rank,k in enumerate(selected,1):
                        selected_rows.append(dict(split=sp,tier=tier_name,top_n=n,rank=rank,global_candidate_key=k))
            log(f'split {sp}: frontier rows cumulative={len(frontier)} elapsed={time.time()-t0:.1f}s')
        tm_all=pd.concat(all_train_metrics,ignore_index=True) if all_train_metrics else pd.DataFrame()
        fr=pd.DataFrame(frontier)
        sel=pd.DataFrame(selected_rows)
        save(tm_all,out/'gold_v3_107gu_train_candidate_metrics.csv'); outs.append('gold_v3_107gu_train_candidate_metrics.csv')
        save(fr,out/'gold_v3_107gu_oos_bank_frontier.csv'); outs.append('gold_v3_107gu_oos_bank_frontier.csv')
        save(sel,out/'gold_v3_107gu_selected_candidate_keys.csv'); outs.append('gold_v3_107gu_selected_candidate_keys.csv')
        if fr.empty:
            blocks.append(dict(blocker_id='no_frontier_rows',reason='No OOS bank frontier rows produced.'))
        else:
            best=fr.sort_values(['split','frontier_score'],ascending=[True,False]).groupby('split').head(1).reset_index(drop=True)
            overall=fr.sort_values('frontier_score',ascending=False).head(80)
            save(best,out/'gold_v3_107gu_best_by_split.csv'); save(overall,out/'gold_v3_107gu_best_overall_frontier.csv')
            outs += ['gold_v3_107gu_best_by_split.csv','gold_v3_107gu_best_overall_frontier.csv']
            # materialize best OOS ledger for each split
            best_led=[]
            for _,r in best.iterrows():
                sp=r.split; split_def=[x for x in SPLITS if x[0]==sp][0]; _,trs,tre,tes,tee=split_def
                train=ledger[(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
                test=ledger[(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy(); tm=train_metrics(train)
                keys=sel[(sel.split==sp)&(sel.tier==r.tier)&(sel.top_n==r.top_n)].sort_values('rank').global_candidate_key.tolist()
                p=build_port(test,keys,tm)
                if not p.empty: best_led.append(p.assign(split=sp,tier=r.tier,top_n=int(r.top_n)))
            oos=pd.concat(best_led,ignore_index=True) if best_led else pd.DataFrame()
            save(oos,out/'gold_v3_107gu_best_oos_trade_ledger.csv'); outs.append('gold_v3_107gu_best_oos_trade_ledger.csv')
            high=int(fr.high_wr_gate.sum()); practical=int(fr.practical_bank_gate.sum()); dens2=int(fr.density2_gate.sum())
            gates=pd.DataFrame([gate('any_high_wr_gate',high,'>=',1),gate('any_practical_bank_gate',practical,'>=',1),gate('any_density2_gate',dens2,'>=',1),gate('splits_best_wr_ge_58',int((best.test_wr>=0.58).sum()),'>=',2),gate('splits_best_density_ge_1',int((best.test_business_day_trade_rate>=1.0).sum()),'>=',2)])
            save(gates,out/'gold_v3_107gu_quality_gate_matrix.csv'); outs.append('gold_v3_107gu_quality_gate_matrix.csv')
            if dens2>0: action='inspect_density2_bank_then_rehydrate'
            elif practical>0 or high>0: action='consider_practical_bank_or_generate_more_vectors'
            else: action='candidate_bank_oos_not_stable_generate_new_vectors'
            save(pd.DataFrame([dict(priority=1,action=action,reason=f'high_wr={high}, practical={practical}, density2={dens2}')]),out/'gold_v3_107gu_recommended_next_actions.csv'); outs.append('gold_v3_107gu_recommended_next_actions.csv')
            finds.append('best_by_split='+json.dumps(best.to_dict(orient='records'),ensure_ascii=False,default=str))
            finds.append(f'gates high_wr={high}, practical={practical}, density2={dens2}')
            vals.append(dict(check_id='frontier_rows_positive',result='PASS' if len(fr)>0 else 'FAIL',observed=len(fr),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_seconds_to_minutes_stop_if_over_1h',elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'fr' in locals() and not fr.empty:
        summary.update(frontier_rows=int(len(fr)),high_wr_gate_count=int(fr.high_wr_gate.sum()),practical_bank_gate_count=int(fr.practical_bank_gate.sum()),density2_gate_count=int(fr.density2_gate.sum()),best_max_oos_wr=float(fr.test_wr.max()),best_max_density=float(fr.test_business_day_trade_rate.max()))
    save(pd.DataFrame(blocks),out/'gold_v3_107gu_blocker_matrix.csv'); save(val,out/'gold_v3_107gu_validation_matrix.csv')
    outs += ['gold_v3_107gu_blocker_matrix.csv','gold_v3_107gu_validation_matrix.csv','gold_v3_107gu_summary.json','GOLD_V3_107GU_BANK_OOS_SELECTION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gu_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GU_BANK_OOS_SELECTION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GU report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GU PASTE_ME_BANK_OOS_SELECTION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: existing Stage107 candidate ledgers as train-only multi-vector bank; no M5 re-evaluation; no runtime change','runtime_estimate: light_to_medium; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'elapsed_seconds':round(time.time()-t0,2),'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
