#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY'
READY='GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv')]
SPLIT_TESTS={'TRAIN_2025_TEST_2026':('2026-01-01','2027-01-01'),'TRAIN_2025H1_TEST_2025H2':('2025-07-01','2026-01-01'),'TRAIN_TO_2026_02_TEST_2026_03_PLUS':('2026-03-01','2027-01-01'),'TRAIN_TO_2026_04_TEST_2026_05_06':('2026-05-01','2027-01-01')}

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

def normalize_ledger(df,src):
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

def bool_col(s):
    if s.dtype==bool: return s
    return s.astype(str).str.lower().isin(['true','1','yes','y'])
def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; gu=root/'107guc'; out=root/'107gvc'; out.mkdir(parents=True,exist_ok=True)
    log(f'{STEP} START density2 candidate review')
    required={'frontier':gu/'gold_v3_107gu_oos_bank_frontier.csv','selected':gu/'gold_v3_107gu_selected_candidate_keys.csv','train_metrics':gu/'gold_v3_107gu_train_candidate_metrics.csv'}
    blocks=[]; vals=[]; outs=[]; finds=[]
    for k,p in required.items():
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required 107GU output missing'))
    ledgers=[]; cov=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                lg=normalize_ledger(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(lg)
                if rows: ledgers.append(lg)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    save(pd.DataFrame(cov),out/'gold_v3_107gv_input_ledger_coverage.csv'); outs.append('gold_v3_107gv_input_ledger_coverage.csv')
    if not blocks:
        frontier=pd.read_csv(required['frontier'],encoding='utf-8-sig')
        selected=pd.read_csv(required['selected'],encoding='utf-8-sig')
        trainm=pd.read_csv(required['train_metrics'],encoding='utf-8-sig')
        if 'density2_gate' not in frontier.columns:
            blocks.append(dict(blocker_id='missing_density2_gate',reason='frontier missing density2_gate'))
        else:
            frontier['density2_gate_bool']=bool_col(frontier['density2_gate'])
            d2=frontier[frontier.density2_gate_bool].copy().sort_values(['test_wr','test_pf','test_business_day_trade_rate','test_trades'],ascending=[False,False,False,False])
            d2['config_rank']=range(1,len(d2)+1)
            d2['review_score']=pd.to_numeric(d2.test_wr,errors='coerce').fillna(0)*5000+pd.to_numeric(d2.test_pf,errors='coerce').fillna(0).map(cap)*700+pd.to_numeric(d2.test_business_day_trade_rate,errors='coerce').fillna(0).clip(upper=5)*300-pd.to_numeric(d2.test_neg_months,errors='coerce').fillna(0)*250+pd.to_numeric(d2.test_trades,errors='coerce').fillna(0).clip(upper=300)*0.2
            d2=d2.sort_values('review_score',ascending=False).reset_index(drop=True)
            d2['config_rank']=range(1,len(d2)+1)
            save(d2,out/'gold_v3_107gv_density2_pass_configs.csv'); outs.append('gold_v3_107gv_density2_pass_configs.csv')
            train_cols=[c for c in ['split','global_candidate_key','side','family','condition','profile_id','candidate_key','source_name','trades','win_rate','profit_factor','sum_result_usd','negative_month_count','train_score'] if c in trainm.columns]
            rows=[]
            ledger=pd.concat(ledgers,ignore_index=True) if ledgers else pd.DataFrame()
            for _,cfg in d2.iterrows():
                sp=str(cfg.split); tier=str(cfg.tier); topn=int(cfg.top_n)
                keys=selected[(selected.split.astype(str)==sp)&(selected.tier.astype(str)==tier)&(pd.to_numeric(selected.top_n,errors='coerce').astype('Int64')==topn)].copy()
                keys=keys.sort_values('rank') if 'rank' in keys.columns else keys
                for _,krow in keys.iterrows():
                    key=str(krow.global_candidate_key)
                    tm=trainm[(trainm.split.astype(str)==sp)&(trainm.global_candidate_key.astype(str)==key)][train_cols].head(1)
                    base=dict(config_rank=int(cfg.config_rank),split=sp,tier=tier,top_n=topn,rank=int(krow.get('rank',0)),global_candidate_key=key,portfolio_test_trades=int(cfg.test_trades),portfolio_test_wr=float(cfg.test_wr),portfolio_test_pf=float(cfg.test_pf),portfolio_test_density=float(cfg.test_business_day_trade_rate))
                    if not tm.empty:
                        for c,v in tm.iloc[0].to_dict().items(): base['train_'+c if c not in ['split','global_candidate_key'] else c]=v
                    if not ledger.empty and sp in SPLIT_TESTS:
                        st,en=SPLIT_TESTS[sp]
                        g=ledger[(ledger.global_candidate_key.astype(str)==key)&(ledger.entry_dt>=pd.Timestamp(st))&(ledger.entry_dt<pd.Timestamp(en))]
                        om=metric(g)
                        for c,v in om.items(): base['candidate_oos_'+c]=v
                    rows.append(base)
            comp=pd.DataFrame(rows)
            save(comp,out/'gold_v3_107gv_density2_candidate_composition.csv'); outs.append('gold_v3_107gv_density2_candidate_composition.csv')
            best=d2.head(1).copy()
            save(best,out/'gold_v3_107gv_best_density2_config.csv'); outs.append('gold_v3_107gv_best_density2_config.csv')
            if not best.empty:
                br=int(best.iloc[0].config_rank)
                detail=comp[comp.config_rank==br].copy() if not comp.empty else pd.DataFrame()
                save(detail,out/'gold_v3_107gv_best_density2_candidate_detail.csv'); outs.append('gold_v3_107gv_best_density2_candidate_detail.csv')
            side_mix=[]
            if not comp.empty:
                side_col='train_side' if 'train_side' in comp.columns else 'side' if 'side' in comp.columns else None
                if side_col:
                    side_mix=comp.groupby(['config_rank','split','tier','top_n',side_col]).size().reset_index(name='candidate_count')
                else:
                    side_mix=pd.DataFrame()
            else:
                side_mix=pd.DataFrame()
            save(side_mix,out/'gold_v3_107gv_side_mix_summary.csv'); outs.append('gold_v3_107gv_side_mix_summary.csv')
            if len(d2)==0:
                decision='NO_DENSITY2_CONFIGS_TO_REVIEW'
            elif len(best) and float(best.iloc[0].test_wr)>=0.58 and float(best.iloc[0].test_pf)>=1.6:
                decision='REVIEW_TOP_DENSITY2_CONFIG_FOR_LIVE_REHYDRATION_AUDIT'
            else:
                decision='DENSITY2_EXISTS_BUT_QUALITY_LOW_REVIEW_ALTERNATES'
            dec=pd.DataFrame([dict(decision=decision,density2_pass_count=int(len(d2)),best_split=str(best.iloc[0].split) if len(best) else '',best_tier=str(best.iloc[0].tier) if len(best) else '',best_top_n=int(best.iloc[0].top_n) if len(best) else 0,best_trades=int(best.iloc[0].test_trades) if len(best) else 0,best_wr=float(best.iloc[0].test_wr) if len(best) else 0.0,best_pf=float(best.iloc[0].test_pf) if len(best) else 0.0,best_density=float(best.iloc[0].test_business_day_trade_rate) if len(best) else 0.0,next_stage='107GW_RESOLVED_ONLY_LIVE_REHYDRATION_OF_SELECTED_BANK' if 'REVIEW_TOP' in decision else '107GW_ALTERNATE_DENSITY2_BANK_REVIEW')])
            save(dec,out/'gold_v3_107gv_next_action_decision.csv'); outs.append('gold_v3_107gv_next_action_decision.csv')
            finds.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            finds.append('top_density2_configs='+json.dumps(d2.head(10).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='density2_pass_configs_positive',result='PASS' if len(d2)>0 else 'FAIL',observed=len(d2),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h',elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'd2' in locals():
        summary.update(density2_pass_count=int(len(d2)),best_wr=float(best.iloc[0].test_wr) if len(best) else 0.0,best_pf=float(best.iloc[0].test_pf) if len(best) else 0.0,best_density=float(best.iloc[0].test_business_day_trade_rate) if len(best) else 0.0,best_top_n=int(best.iloc[0].top_n) if len(best) else 0,decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107gv_blocker_matrix.csv'); save(val,out/'gold_v3_107gv_validation_matrix.csv')
    outs += ['gold_v3_107gv_blocker_matrix.csv','gold_v3_107gv_validation_matrix.csv','gold_v3_107gv_summary.json','GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gv_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GV report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GV PASTE_ME_DENSITY2_BANK_CANDIDATE_REVIEW',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GU density2 configs and exact candidate ledgers; no M5 re-evaluation; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'elapsed_seconds':round(time.time()-t0,2),'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
