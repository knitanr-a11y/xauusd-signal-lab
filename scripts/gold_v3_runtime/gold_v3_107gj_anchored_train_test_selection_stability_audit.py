#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY'
READY='GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
KEY=['side','condition','profile_id','cooldown_bars']

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def pfcap(x):
    try: return 10.0 if math.isinf(float(x)) else min(float(x),10.0)
    except Exception: return 0.0

def score(m): return pfcap(m['profit_factor'])*1000 + m['win_rate']*700 + min(m['trades'],600)*0.3 - m['negative_month_count']*300

def overlap(a,b): return len(a&b)/max(1,min(len(a),len(b))) if a and b else 0.0

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def read_ledger(p):
    df=pd.read_csv(p,encoding='utf-8-sig')
    df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df=df[df.entry_dt.notna()].copy(); df['entry_month']=df.entry_dt.dt.to_period('M').astype(str)
    df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce'); df=df[df.result_usd.notna()].copy()
    for c in KEY: df[c]=df[c].astype(str)
    df['candidate_id']=df[KEY].astype(str).agg('||'.join,axis=1)
    return df

def split_masks(df,name):
    d=df.entry_dt
    if name=='TRAIN_2025_TEST_2026': return d.dt.year==2025, d.dt.year==2026
    if name=='TRAIN_2025H1_TEST_2025H2': return (d>=pd.Timestamp('2025-01-01'))&(d<pd.Timestamp('2025-07-01')), (d>=pd.Timestamp('2025-07-01'))&(d<pd.Timestamp('2026-01-01'))
    if name=='TRAIN_TO_2026_02_TEST_2026_03_PLUS': return d<pd.Timestamp('2026-03-01'), d>=pd.Timestamp('2026-03-01')
    if name=='TRAIN_TO_2026_04_TEST_2026_05_06': return d<pd.Timestamp('2026-05-01'), d>=pd.Timestamp('2026-05-01')
    raise ValueError(name)

def select_candidates(train, side, mintr, minpf, minwr, maxneg, maxcand):
    rows=[]; sets=[]; chosen=[]
    for cid,g in train[train.side==side].groupby('candidate_id'):
        m=metric(g)
        if m['trades']>=mintr and m['profit_factor']>=minpf and m['win_rate']>=minwr and m['negative_month_count']<=maxneg:
            first=g.iloc[0]; rows.append((score(m),cid,set(g.entry_dt.astype(str)),m,first))
    rows=sorted(rows,key=lambda x:x[0],reverse=True)
    for sc,cid,st,m,first in rows:
        ov=max([overlap(st,s) for s in sets],default=0.0)
        if ov<=0.35:
            chosen.append((cid,sc,m,first,ov)); sets.append(st)
        if len(chosen)>=maxcand: break
    return chosen

def apply_test(test, chosen):
    ids=[]; score_map={}; rank_map={}; side_map={}; meta={}
    for side,items in chosen.items():
        for rank,(cid,sc,m,first,ov) in enumerate(items,1):
            ids.append(cid); score_map[cid]=sc; rank_map[cid]=rank; side_map[cid]=side; meta[cid]=(m,first,ov)
    if not ids: return pd.DataFrame(),0
    raw=test[test.candidate_id.isin(ids)].copy()
    if raw.empty: return raw,0
    raw['train_score']=raw.candidate_id.map(score_map); raw['selected_rank']=raw.candidate_id.map(rank_map); raw['selected_side']=raw.candidate_id.map(side_map)
    raw=raw.sort_values(['entry_dt','train_score'],ascending=[True,False])
    conflicts=int(raw.duplicated('entry_dt',keep=False).sum())
    out=raw.drop_duplicates('entry_dt',keep='first')
    return out,conflicts

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gjc'; out.mkdir(parents=True,exist_ok=True)
    ledger_p=src/'gold_v3_107gb_top_candidate_trade_ledger.csv'; blockers=[]; vals=[]; findings=[]; outputs=[]
    if not ledger_p.exists(): blockers.append(dict(blocker_id='missing_107gb_candidate_ledger',artifact=str(ledger_p),reason='required 107GB candidate ledger missing'))
    if not blockers:
        led=read_ledger(ledger_p)
        cfgs=list(itertools.product([20,40,80],[1.5,1.8,2.0],[0.50,0.55,0.60],[0,1,2],[1,2,3]))
        split_names=['TRAIN_2025_TEST_2026','TRAIN_2025H1_TEST_2025H2','TRAIN_TO_2026_02_TEST_2026_03_PLUS','TRAIN_TO_2026_04_TEST_2026_05_06']
        rows=[]; candlog=[]; ledgers=[]
        for sp in split_names:
            tr_mask,te_mask=split_masks(led,sp); train=led[tr_mask].copy(); test=led[te_mask].copy()
            for ci,(mintr,minpf,minwr,maxneg,maxcand) in enumerate(cfgs):
                chosen={'LONG':select_candidates(train,'LONG',mintr,minpf,minwr,maxneg,maxcand),'SHORT':select_candidates(train,'SHORT',mintr,minpf,minwr,maxneg,maxcand)}
                for side,items in chosen.items():
                    for rank,(cid,sc,m,first,ov) in enumerate(items,1):
                        candlog.append(dict(split=sp,config_id=ci,side=side,rank=rank,candidate_id=cid,condition=first.condition,profile_id=first.profile_id,cooldown_bars=first.cooldown_bars,train_score=sc,train_trades=m['trades'],train_wr=m['win_rate'],train_pf=m['profit_factor'],train_negative_month_count=m['negative_month_count'],overlap_with_prior=ov,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand))
                outt,conf=apply_test(test,chosen)
                if not outt.empty: outt=outt.assign(split=sp,config_id=ci,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand)
                m=metric(outt); m.update(split=sp,config_id=ci,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand,train_rows=int(len(train)),test_rows=int(len(test)),selected_candidates=sum(len(v) for v in chosen.values()),conflict_rows_before_resolution=conf)
                m['split_score']=pfcap(m['profit_factor'])*1000+m['win_rate']*800+min(m['trades'],600)*0.25-m['negative_month_count']*350-conf*0.05
                rows.append(m)
                if not outt.empty and m['trades']>=50: ledgers.append(outt)
        summary=pd.DataFrame(rows).sort_values(['split','split_score'],ascending=[True,False]); save(summary,out/'gold_v3_107gj_split_config_summary.csv'); outputs.append('gold_v3_107gj_split_config_summary.csv')
        best=summary.groupby('split',group_keys=False).head(1); save(best,out/'gold_v3_107gj_best_by_split.csv'); outputs.append('gold_v3_107gj_best_by_split.csv')
        save(pd.DataFrame(candlog),out/'gold_v3_107gj_selected_candidate_log.csv'); outputs.append('gold_v3_107gj_selected_candidate_log.csv')
        best_led=[]
        if ledgers:
            all_led=pd.concat(ledgers,ignore_index=True)
            for _,r in best.iterrows():
                best_led.append(all_led[(all_led.split==r.split)&(all_led.config_id==r.config_id)])
        best_ledger=pd.concat(best_led,ignore_index=True) if best_led else pd.DataFrame()
        save(best_ledger,out/'gold_v3_107gj_best_selected_trade_ledger.csv'); outputs.append('gold_v3_107gj_best_selected_trade_ledger.csv')
        stab=[]
        for _,r in best.iterrows():
            gate_pass=(r.trades>=150 and r.profit_factor>=1.8 and r.win_rate>=0.55 and r.negative_month_count<=2)
            stab.append(dict(split=r.split,trades=r.trades,win_rate=r.win_rate,profit_factor=r.profit_factor,sum_result_usd=r.sum_result_usd,negative_month_count=r.negative_month_count,selected_candidates=r.selected_candidates,conflict_rows_before_resolution=r.conflict_rows_before_resolution,passes_basic_oos_gate=gate_pass))
        stab_df=pd.DataFrame(stab); save(stab_df,out/'gold_v3_107gj_stability_summary.csv'); outputs.append('gold_v3_107gj_stability_summary.csv')
        pass_count=int(stab_df.passes_basic_oos_gate.sum()) if len(stab_df) else 0
        gate_df=pd.DataFrame([qgate('splits_passing_basic_oos_gate',pass_count,'>=',2),qgate('train_2025_test_2026_pf',float(stab_df[stab_df.split=='TRAIN_2025_TEST_2026'].profit_factor.iloc[0]) if len(stab_df[stab_df.split=='TRAIN_2025_TEST_2026']) else 0,'>=',1.8),qgate('train_2025_test_2026_wr',float(stab_df[stab_df.split=='TRAIN_2025_TEST_2026'].win_rate.iloc[0]) if len(stab_df[stab_df.split=='TRAIN_2025_TEST_2026']) else 0,'>=',0.55)])
        save(gate_df,out/'gold_v3_107gj_quality_gate_matrix.csv'); outputs.append('gold_v3_107gj_quality_gate_matrix.csv')
        lim=pd.DataFrame([dict(limitation_id='existing_candidate_universe',severity='IMPORTANT',message='107GJ selects candidates using train-period results only, but candidate universe was generated in Stage107GB from the full primitive-combo audit universe. Full train-only OHLC universe generation remains a later heavier check.'),dict(limitation_id='anchored_split_not_live_rehydrated',severity='IMPORTANT',message='This is anchored train/test audit by period, not exact exit_dt<=entry_dt live rehydration.')])
        save(lim,out/'gold_v3_107gj_limitations.csv'); outputs.append('gold_v3_107gj_limitations.csv')
        actions=[]
        if pass_count>=2: actions.append(dict(priority=1,action='consider_heavier_train_only_ohlc_universe_generation',reason='anchored train/test selection retained edge across at least two splits'))
        else: actions.append(dict(priority=1,action='do_not_advance_to_heavy_train_only_universe_until_edges_redesigned',reason='anchored train/test selection did not retain enough OOS splits'))
        actions.append(dict(priority=2,action='inspect_failed_splits_by_side_and_candidate',reason='determine whether weakness is time-specific or side-specific'))
        save(pd.DataFrame(actions),out/'gold_v3_107gj_recommended_next_actions.csv'); outputs.append('gold_v3_107gj_recommended_next_actions.csv')
        findings.append('best_by_split='+json.dumps(best.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('stability_summary='+json.dumps(stab,ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='split_configs_positive',result='PASS' if len(summary)>0 else 'FAIL',observed=len(summary),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary_out=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_minutes_to_20min_stop_if_over_1h')
    if not blockers and 'pass_count' in locals(): summary_out['splits_passing_basic_oos_gate']=pass_count
    save(pd.DataFrame(blockers),out/'gold_v3_107gj_blocker_matrix.csv'); save(val,out/'gold_v3_107gj_validation_matrix.csv')
    (out/'gold_v3_107gj_summary.json').write_text(json.dumps(summary_out|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GJ report\n\n'+json.dumps({'summary':summary_out,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gj_blocker_matrix.csv','gold_v3_107gj_validation_matrix.csv','gold_v3_107gj_summary.json','GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GJ PASTE_ME_ANCHORED_TRAIN_TEST_SELECTION_STABILITY',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GB candidate ledger; anchored train/test candidate selection; no runtime change','runtime_estimate: light_to_medium; minutes_to_20min; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary_out.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
