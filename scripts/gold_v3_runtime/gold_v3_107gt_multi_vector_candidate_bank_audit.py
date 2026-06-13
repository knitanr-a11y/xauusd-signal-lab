#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY'
READY='GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[
 ('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),
 ('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),
 ('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),
 ('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),
 ('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv'),
]
TOP_NS=[3,5,10,20,30,50,100]
SPLITS=[
 ('TRAIN_2025_TEST_2026','2026-01-01','2027-01-01'),
 ('TRAIN_2025H1_TEST_2025H2','2025-07-01','2026-01-01'),
 ('TRAIN_TO_2026_02_TEST_2026_03_PLUS','2026-03-01','2027-01-01'),
 ('TRAIN_TO_2026_04_TEST_2026_05_06','2026-05-01','2027-01-01'),
]

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
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(pd.to_datetime(x.entry_dt).dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def density(df):
    m=metric(df)
    if df is None or df.empty:
        return m|dict(min_entry_dt='',max_entry_dt='',business_days=0,business_day_trade_rate=0.0,active_trade_days=0,active_trade_day_rate=0.0)
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
    x['source_name']=src
    x['global_candidate_key']=x.source_name+'::'+x.candidate_key
    return x

def candidate_metrics(ledger):
    rows=[]
    for key,g in ledger.groupby('global_candidate_key',sort=False):
        m=density(g); f=g.iloc[0]
        # period robustness
        periods={
            '2025': (g.entry_dt>=pd.Timestamp('2025-01-01'))&(g.entry_dt<pd.Timestamp('2026-01-01')),
            '2026': (g.entry_dt>=pd.Timestamp('2026-01-01')),
            '2025H2': (g.entry_dt>=pd.Timestamp('2025-07-01'))&(g.entry_dt<pd.Timestamp('2026-01-01')),
            '2026_03_PLUS': (g.entry_dt>=pd.Timestamp('2026-03-01')),
            '2026_05_06': (g.entry_dt>=pd.Timestamp('2026-05-01')),
        }
        for name,mask in periods.items():
            pm=metric(g[mask])
            for kk,v in pm.items(): m[f'{name}_{kk}']=v
        split_pass=0
        for sp,st,en in SPLITS:
            sm=metric(g[(g.entry_dt>=pd.Timestamp(st))&(g.entry_dt<pd.Timestamp(en))])
            if sm['trades']>=20 and sm['win_rate']>=0.55 and sm['profit_factor']>=1.5: split_pass+=1
        m.update(global_candidate_key=key,source_name=f.source_name,candidate_key=f.candidate_key,side=f.side,family=f.family,condition=f.condition,profile_id=f.profile_id,cooldown_bars=int(f.cooldown_bars),oos_like_split_pass_count=split_pass)
        m['bank_score']=m['win_rate']*3500 + cap(m['profit_factor'])*800 + min(m['trades'],300)*0.30 + m['sum_result_usd']*0.03 + split_pass*500 - m['negative_month_count']*300
        rows.append(m)
    return pd.DataFrame(rows).sort_values(['bank_score','win_rate','profit_factor'],ascending=[False,False,False])

def tier(row):
    if row.trades>=30 and row.win_rate>=0.60 and row.profit_factor>=1.80: return 'core_high_wr'
    if row.trades>=50 and row.win_rate>=0.58 and row.profit_factor>=1.60: return 'practical_quality'
    if row.trades>=80 and row.win_rate>=0.55 and row.profit_factor>=1.50: return 'density_safe'
    if row.trades>=100 and row.win_rate>=0.52 and row.profit_factor>=1.30: return 'exploratory'
    return 'reject'

def build_portfolio(ledger, keys):
    if not keys: return pd.DataFrame()
    order={k:i for i,k in enumerate(keys)}
    x=ledger[ledger.global_candidate_key.isin(keys)].copy()
    x['candidate_rank']=x.global_candidate_key.map(order).fillna(999999)
    x=x.sort_values(['entry_dt','candidate_rank']).drop_duplicates('entry_dt',keep='first')
    return x

def gate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    t0=datetime.now(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107gtc'; out.mkdir(parents=True,exist_ok=True)
    log(f'{STEP} START candidate-bank mode')
    blocks=[]; vals=[]; outs=[]; finds=[]; cov=[]; ledgers=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                lg=normalize(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(lg)
                if rows: ledgers.append(lg)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
        log(f'input {src}: exists={p.exists()} rows={rows}')
    save(pd.DataFrame(cov),out/'gold_v3_107gt_input_ledger_coverage.csv'); outs.append('gold_v3_107gt_input_ledger_coverage.csv')
    if not ledgers: blocks.append(dict(blocker_id='no_candidate_ledgers',reason='No exact candidate ledgers found.'))
    if not blocks:
        ledger=pd.concat(ledgers,ignore_index=True)
        cm=candidate_metrics(ledger)
        cm['tier']=cm.apply(tier,axis=1)
        save(cm,out/'gold_v3_107gt_candidate_bank_metrics.csv'); outs.append('gold_v3_107gt_candidate_bank_metrics.csv')
        tier_summary=cm.groupby(['side','tier']).agg(candidate_count=('global_candidate_key','nunique'),trades_sum=('trades','sum'),avg_wr=('win_rate','mean'),avg_pf=('profit_factor','mean')).reset_index()
        save(tier_summary,out/'gold_v3_107gt_candidate_bank_tiers.csv'); outs.append('gold_v3_107gt_candidate_bank_tiers.csv')
        accepted=cm[cm.tier!='reject'].copy()
        save(accepted.head(200),out/'gold_v3_107gt_top_candidate_bank.csv'); outs.append('gold_v3_107gt_top_candidate_bank.csv')
        fronts=[]; best_score=-1e18; best_port=pd.DataFrame(); best_n=0
        keys=accepted.global_candidate_key.tolist()
        for n in TOP_NS:
            ks=keys[:n]
            port=build_portfolio(ledger,ks); m=density(port)
            m.update(top_n=n,selected_candidate_count=len(ks))
            m['quality_density_gate']=bool(m['win_rate']>=0.58 and m['profit_factor']>=1.6 and m['business_day_trade_rate']>=1.0 and m['negative_month_count']<=3)
            m['density_2_gate']=bool(m['win_rate']>=0.55 and m['profit_factor']>=1.5 and m['business_day_trade_rate']>=2.0 and m['negative_month_count']<=4)
            fronts.append(m)
            sc=m['win_rate']*5000+cap(m['profit_factor'])*800+min(m['business_day_trade_rate'],2.0)*500-m['negative_month_count']*300
            if sc>best_score:
                best_score=sc; best_port=port; best_n=n
        front_df=pd.DataFrame(fronts)
        save(front_df,out/'gold_v3_107gt_portfolio_size_frontier.csv'); outs.append('gold_v3_107gt_portfolio_size_frontier.csv')
        save(best_port,out/'gold_v3_107gt_best_bank_portfolio_ledger.csv'); outs.append('gold_v3_107gt_best_bank_portfolio_ledger.csv')
        source_side=cm.groupby(['source_name','side']).agg(candidate_count=('global_candidate_key','nunique'),accepted_count=('tier',lambda s:int((s!='reject').sum())),best_wr=('win_rate','max'),best_pf=('profit_factor','max'),trades_sum=('trades','sum')).reset_index()
        save(source_side,out/'gold_v3_107gt_source_side_summary.csv'); outs.append('gold_v3_107gt_source_side_summary.csv')
        bestm=density(best_port)
        if bool(front_df.density_2_gate.any()): decision='MULTI_VECTOR_BANK_CAN_MEET_DENSITY2_WITH_ACCEPTABLE_QUALITY'
        elif bool(front_df.quality_density_gate.any()): decision='MULTI_VECTOR_BANK_HAS_QUALITY_BUT_DENSITY_BELOW_2'
        elif len(accepted)>0: decision='CANDIDATE_BANK_HAS_ACCEPTED_VECTORS_BUT_PORTFOLIO_NEEDS_MORE_HIGH_WR_CANDIDATES'
        else: decision='NO_ACCEPTED_CANDIDATE_BANK_REDESIGN_REQUIRED'
        dec=pd.DataFrame([dict(decision=decision,accepted_candidates=int(len(accepted)),best_top_n=best_n,best_trades=bestm['trades'],best_wr=bestm['win_rate'],best_pf=bestm['profit_factor'],best_business_day_trade_rate=bestm['business_day_trade_rate'],best_negative_month_count=bestm['negative_month_count'],next_stage='107GU_BANK_OOS_SELECTION' if 'CAN_MEET' in decision or 'QUALITY' in decision else '107GU_NEW_CANDIDATE_GENERATION')])
        save(dec,out/'gold_v3_107gt_next_action_decision.csv'); outs.append('gold_v3_107gt_next_action_decision.csv')
        finds.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
        finds.append('tier_summary='+json.dumps(tier_summary.to_dict(orient='records'),ensure_ascii=False,default=str))
        vals.append(dict(check_id='candidate_bank_rows_positive',result='PASS' if len(cm)>0 else 'FAIL',observed=len(cm),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_seconds_to_minutes_stop_if_over_1h')
    if not blocks:
        summary.update(candidate_bank_rows=int(len(cm)),accepted_candidate_count=int(len(accepted)),best_top_n=int(best_n),best_wr=float(bestm['win_rate']),best_pf=float(bestm['profit_factor']),best_business_day_trade_rate=float(bestm['business_day_trade_rate']),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107gt_blocker_matrix.csv'); save(val,out/'gold_v3_107gt_validation_matrix.csv')
    outs += ['gold_v3_107gt_blocker_matrix.csv','gold_v3_107gt_validation_matrix.csv','gold_v3_107gt_summary.json','GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gt_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GT report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GT PASTE_ME_MULTI_VECTOR_CANDIDATE_BANK',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: existing Stage107 candidate ledgers as multi-vector bank; no M5 re-evaluation; no runtime change','runtime_estimate: light_to_medium; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    log(f'DONE status={status} paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
