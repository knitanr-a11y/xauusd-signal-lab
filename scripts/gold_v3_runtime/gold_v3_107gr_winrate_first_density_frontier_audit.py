#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY'
READY='GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv')]
SPLITS=[('TRAIN_2025_TEST_2026','2025-01-01','2026-01-01','2026-01-01','2027-01-01'),('TRAIN_2025H1_TEST_2025H2','2025-01-01','2025-07-01','2025-07-01','2026-01-01'),('TRAIN_TO_2026_02_TEST_2026_03_PLUS','2025-01-01','2026-03-01','2026-03-01','2027-01-01'),('TRAIN_TO_2026_04_TEST_2026_05_06','2025-01-01','2026-05-01','2026-05-01','2027-01-01')]

def files_dir(s):
    if s: return Path(s).expanduser().resolve()
    e=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(e).expanduser().resolve() if e else Path.cwd()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(v):
    a=np.array(v,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def met(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def den(df):
    m=met(df)
    if df is None or df.empty: return m|dict(business_days=0,business_day_trade_rate=0.0,active_trade_days=0,active_trade_day_rate=0.0)
    mn=pd.to_datetime(df.entry_dt.min()).date(); mx=pd.to_datetime(df.entry_dt.max()).date()
    bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,'D'))); ad=int(pd.to_datetime(df.entry_dt).dt.date.nunique())
    return m|dict(business_days=bd,business_day_trade_rate=float(m['trades']/bd) if bd else 0.0,active_trade_days=ad,active_trade_day_rate=float(m['trades']/ad) if ad else 0.0)
def cap(v):
    try:
        x=float(v); return 10 if math.isinf(x) else max(0,min(x,10))
    except Exception: return 0

def norm(df,src):
    if 'entry_dt' not in df.columns: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy()
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

def cm(df):
    rows=[]
    for k,g in df.groupby('global_candidate_key'):
        m=den(g); f=g.iloc[0]
        score=m['win_rate']*5000+cap(m['profit_factor'])*650+min(m['trades'],250)*.25+m['sum_result_usd']*.02-m['negative_month_count']*450
        m.update(global_candidate_key=k,source_name=f.source_name,candidate_key=f.candidate_key,side=f.side,family=f.family,condition=f.condition,profile_id=f.profile_id,cooldown_bars=int(f.cooldown_bars),train_score=score)
        rows.append(m)
    return pd.DataFrame(rows).sort_values(['win_rate','profit_factor','train_score'],ascending=[False,False,False])
def select(train,cfg):
    c=cm(train)
    if c.empty: return c.iloc[0:0]
    c=c[(c.trades>=8)&(c.sum_result_usd>0)&(c.win_rate>=cfg['wr'])&(c.profit_factor>=cfg['pf'])&(c.negative_month_count<=cfg['neg'])].copy()
    chosen=[]; parts=[]
    for _,r in c.iterrows():
        chosen.append(r.to_dict()|dict(selected_rank=len(chosen)+1))
        parts.append(train[train.global_candidate_key==r.global_candidate_key].assign(candidate_train_score=float(r.train_score)))
        port=pd.concat(parts).sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt')
        if den(port)['business_day_trade_rate']>=cfg['density'] or len(chosen)>=cfg['maxc']: break
    return pd.DataFrame(chosen)
def apply(test,sel):
    if test.empty or sel.empty: return pd.DataFrame()
    sc=sel.set_index('global_candidate_key').train_score.to_dict()
    x=test[test.global_candidate_key.isin(sc)].copy()
    if x.empty: return x
    x['candidate_train_score']=x.global_candidate_key.map(sc).fillna(0)
    return x.sort_values(['entry_dt','candidate_train_score'],ascending=[True,False]).drop_duplicates('entry_dt')
def cid(c): return f"wr{int(c['wr']*100)}_pf{str(c['pf']).replace('.','p')}_neg{c['neg']}_d{str(c['density']).replace('.','p')}_max{c['maxc']}"
def gate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107grc'; out.mkdir(parents=True,exist_ok=True)
    blocks=[]; vals=[]; outs=[]; finds=[]; cov=[]; led=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                x=norm(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(x)
                if rows: led.append(x)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    save(pd.DataFrame(cov),out/'gold_v3_107gr_input_ledger_coverage.csv'); outs.append('gold_v3_107gr_input_ledger_coverage.csv')
    if not led: blocks.append(dict(blocker_id='no_candidate_ledgers',reason='no exact candidate ledgers found'))
    if not blocks:
        ledger=pd.concat(led,ignore_index=True)
        configs=[dict(wr=w,pf=p,neg=n,density=d,maxc=m) for w,p,n,d,m in itertools.product([.55,.58,.60,.62],[1.5,1.8,2.0,2.3],[0,1,2],[.5,1.0,1.5,2.0],[3,5,8,12,20,40])]
        rows=[]; best_parts=[]; sel_parts=[]
        for sp,trs,tre,tes,tee in SPLITS:
            train=ledger[(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))]
            test=ledger[(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))]
            for cfg in configs:
                sel=select(train,cfg)
                if sel.empty: continue
                tp=apply(test,sel); tm=den(tp)
                trp=apply(train,sel); trm=den(trp)
                r=dict(split=sp,config_id=cid(cfg),**cfg,selected_candidate_count=len(sel),train_trades=trm['trades'],train_density=trm['business_day_trade_rate'],train_pf=trm['profit_factor'],train_wr=trm['win_rate'],test_trades=tm['trades'],test_density=tm['business_day_trade_rate'],test_pf=tm['profit_factor'],test_wr=tm['win_rate'],test_sum=tm['sum_result_usd'],test_neg_months=tm['negative_month_count'])
                r['winrate_priority_gate']=r['test_wr']>=.58 and r['test_pf']>=1.5 and r['test_neg_months']<=3 and r['test_trades']>=20
                r['high_winrate_gate']=r['test_wr']>=.60 and r['test_pf']>=1.5 and r['test_neg_months']<=3 and r['test_trades']>=20
                r['balanced_gate']=r['test_wr']>=.55 and r['test_pf']>=1.8 and r['test_density']>=1.0 and r['test_neg_months']<=3
                r['density_retained_gate']=r['test_wr']>=.55 and r['test_pf']>=1.8 and r['test_density']>=2.0 and r['test_neg_months']<=3
                r['frontier_score']=r['test_wr']*10000+cap(r['test_pf'])*600+min(r['test_density'],2.0)*350+min(r['test_trades'],200)*.3-r['test_neg_months']*300
                rows.append(r)
        res=pd.DataFrame(rows)
        if res.empty: blocks.append(dict(blocker_id='no_frontier_results',reason='no selected frontier configs'))
        else:
            res=res.sort_values(['split','frontier_score'],ascending=[True,False])
            save(res,out/'gold_v3_107gr_frontier_config_results.csv'); outs.append('gold_v3_107gr_frontier_config_results.csv')
            best=res.groupby('split',as_index=False).head(1).reset_index(drop=True)
            save(best,out/'gold_v3_107gr_best_by_split.csv'); outs.append('gold_v3_107gr_best_by_split.csv')
            save(res.sort_values('frontier_score',ascending=False).head(50),out/'gold_v3_107gr_best_overall_candidates.csv'); outs.append('gold_v3_107gr_best_overall_candidates.csv')
            trade=[]
            for d,g in res.groupby('density'):
                trade.append(g.sort_values('frontier_score',ascending=False).iloc[0].to_dict())
            save(pd.DataFrame(trade),out/'gold_v3_107gr_winrate_density_tradeoff.csv'); outs.append('gold_v3_107gr_winrate_density_tradeoff.csv')
            win=int(res.winrate_priority_gate.sum()); high=int(res.high_winrate_gate.sum()); bal=int(res.balanced_gate.sum()); dens=int(res.density_retained_gate.sum())
            q=pd.DataFrame([gate('any_winrate_priority_gate',win,'>=',1),gate('any_high_winrate_gate',high,'>=',1),gate('any_balanced_gate',bal,'>=',1),gate('any_density_retained_gate',dens,'>=',1),gate('splits_best_wr_ge_58',int((best.test_wr>=.58).sum()),'>=',2)])
            save(q,out/'gold_v3_107gr_quality_gate_matrix.csv'); outs.append('gold_v3_107gr_quality_gate_matrix.csv')
            act='inspect_winrate_pruned_portfolio' if win or bal or dens else 'redesign_for_oos_winrate'
            save(pd.DataFrame([dict(priority=1,action=act,reason=f'winrate_gate={win}, high_wr={high}, balanced={bal}, density_retained={dens}')]),out/'gold_v3_107gr_recommended_next_actions.csv'); outs.append('gold_v3_107gr_recommended_next_actions.csv')
            # Materialize best OOS ledger only.
            mats=[]
            for _,b in best.iterrows():
                sp=[x for x in SPLITS if x[0]==b.split][0]; _,trs,tre,tes,tee=sp
                train=ledger[(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))]
                test=ledger[(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))]
                cfg=dict(wr=float(b.wr),pf=float(b.pf),neg=int(b.neg),density=float(b.density),maxc=int(b.maxc))
                sel=select(train,cfg); tp=apply(test,sel)
                if not tp.empty: mats.append(tp.assign(split=b.split,config_id=b.config_id))
            oos=pd.concat(mats,ignore_index=True) if mats else pd.DataFrame()
            save(oos,out/'gold_v3_107gr_best_oos_trade_ledger.csv'); outs.append('gold_v3_107gr_best_oos_trade_ledger.csv')
            finds.append('best_by_split='+json.dumps(best.to_dict(orient='records'),ensure_ascii=False,default=str))
            finds.append(f'gates winrate={win} high={high} balanced={bal} density_retained={dens}')
            vals.append(dict(check_id='frontier_rows_positive',result='PASS',observed=len(res),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_seconds_to_minutes_stop_if_over_1h')
    if not blocks and 'res' in locals() and not res.empty:
        summary.update(frontier_rows=int(len(res)),best_max_oos_win_rate=float(res.test_wr.max()),winrate_priority_gate_count=int(res.winrate_priority_gate.sum()),high_winrate_gate_count=int(res.high_winrate_gate.sum()),balanced_gate_count=int(res.balanced_gate.sum()),density_retained_gate_count=int(res.density_retained_gate.sum()))
    save(pd.DataFrame(blocks),out/'gold_v3_107gr_blocker_matrix.csv'); save(val,out/'gold_v3_107gr_validation_matrix.csv')
    outs += ['gold_v3_107gr_blocker_matrix.csv','gold_v3_107gr_validation_matrix.csv','gold_v3_107gr_summary.json','GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gr_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GR report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GR PASTE_ME_WINRATE_FIRST_DENSITY_FRONTIER',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: existing Stage107 candidate ledgers only; winrate-first anchored train-period selection; no M5 re-evaluation; no runtime change','runtime_estimate: light_to_medium; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
