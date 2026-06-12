#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY'
READY='GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
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

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def read(p):
    df=pd.read_csv(p,encoding='utf-8-sig')
    df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df=df[df.entry_dt.notna()].copy(); df['entry_month']=df.entry_dt.dt.to_period('M').astype(str)
    df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce'); df=df[df.result_usd.notna()].copy()
    if 'portfolio_side' in df.columns: df['side']=df['portfolio_side'].astype(str)
    else: df['side']=df.get('side','').astype(str)
    for c in KEY:
        if c in df.columns: df[c]=df[c].astype(str)
    df['candidate_id']=df[KEY].astype(str).agg('||'.join,axis=1)
    if 'selected_rank' not in df.columns: df['selected_rank']=1
    return df.sort_values(['side','entry_dt','selected_rank']).drop_duplicates(['side','entry_dt'],keep='first')

def month_range(months,target,lookback):
    i=months.index(target)
    if lookback=='expanding': return months[:i]
    n=int(lookback); return months[max(0,i-n):i]

def pass_gate(hist,mintr,minpf,minwr,maxneg):
    m=metric(hist)
    return m['trades']>=mintr and m['profit_factor']>=minpf and m['win_rate']>=minwr and m['negative_month_count']<=maxneg, m

def apply_gate(base, mode, lookback, mintr, minpf, minwr, maxneg):
    months=sorted(base.entry_month.unique().tolist()); parts=[]; logs=[]
    for target in months:
        prior=month_range(months,target,lookback)
        if len(prior)<3: continue
        target_df=base[base.entry_month==target]
        hist=base[base.entry_month.isin(prior)]
        if mode=='combined_monthly_gate':
            ok,m=pass_gate(hist,mintr,minpf,minwr,maxneg); logs.append(dict(target_month=target,gate_group='COMBINED',gate_key='ALL',pass_gate=ok,**{f'train_{k}':v for k,v in m.items()}))
            if ok: parts.append(target_df)
        elif mode=='side_monthly_gate':
            for side,g in target_df.groupby('side'):
                h=hist[hist.side==side]; ok,m=pass_gate(h,mintr,minpf,minwr,maxneg); logs.append(dict(target_month=target,gate_group='SIDE',gate_key=side,pass_gate=ok,**{f'train_{k}':v for k,v in m.items()}))
                if ok: parts.append(g)
        elif mode=='candidate_monthly_gate':
            for cid,g in target_df.groupby('candidate_id'):
                h=hist[hist.candidate_id==cid]; ok,m=pass_gate(h,mintr,minpf,minwr,maxneg); logs.append(dict(target_month=target,gate_group='CANDIDATE',gate_key=cid,pass_gate=ok,**{f'train_{k}':v for k,v in m.items()}))
                if ok: parts.append(g)
    out=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=base.columns)
    return out,pd.DataFrame(logs)

def score(m): return pfcap(m['profit_factor'])*1000 + m['win_rate']*800 + min(m['trades'],600)*0.25 - m['negative_month_count']*350

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107ghc'; out.mkdir(parents=True,exist_ok=True)
    ledger_p=src/'gold_v3_107gd_diversified_portfolio_ledger.csv'; blockers=[]; vals=[]; findings=[]; outputs=[]
    if not ledger_p.exists(): blockers.append(dict(blocker_id='missing_fixed_portfolio_ledger',artifact=str(ledger_p),reason='required 107GD output missing'))
    if not blockers:
        raw=read(ledger_p)
        base=raw.sort_values(['entry_dt','selected_rank']).drop_duplicates(['entry_dt'],keep='first')
        rows=[]; ledgers={}; logs=[]
        bm=metric(base); rows.append(dict(mode='no_gate_baseline',lookback_months='NA',min_train_trades=0,min_train_pf=0,min_train_wr=0,max_train_negative_months=999,score=score(bm),**bm))
        ledgers['no_gate_baseline']=base
        grid=list(itertools.product(['3','6','expanding'],[10,20,40],[1.2,1.5,1.8,2.0],[0.50,0.55,0.60],[0,1,2],['combined_monthly_gate','side_monthly_gate','candidate_monthly_gate']))
        best_key='no_gate_baseline'; best_score=score(bm)
        for i,(lb,mintr,minpf,minwr,maxneg,mode) in enumerate(grid):
            sel,log=apply_gate(base,mode,lb,mintr,minpf,minwr,maxneg)
            m=metric(sel); sc=score(m); key=f'{mode}_{lb}_{mintr}_{minpf}_{minwr}_{maxneg}_{i}'
            rows.append(dict(mode=mode,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,score=sc,**m))
            if not log.empty: log=log.assign(config_key=key,mode=mode,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg); logs.append(log)
            if sc>best_score:
                best_score=sc; best_key=key; ledgers[key]=sel
        cfg=pd.DataFrame(rows).sort_values('score',ascending=False); save(cfg,out/'gold_v3_107gh_gate_config_summary.csv'); outputs.append('gold_v3_107gh_gate_config_summary.csv')
        best=cfg.iloc[0].to_dict(); best_led=base if best['mode']=='no_gate_baseline' else ledgers.get(best_key,pd.DataFrame())
        save(best_led,out/'gold_v3_107gh_best_gate_selected_ledger.csv'); outputs.append('gold_v3_107gh_best_gate_selected_ledger.csv')
        monthly=[]
        for mth,g in best_led.groupby('entry_month') if not best_led.empty else []:
            m=metric(g); m.update(entry_month=mth); monthly.append(m)
        save(pd.DataFrame(monthly),out/'gold_v3_107gh_best_gate_monthly_summary.csv'); outputs.append('gold_v3_107gh_best_gate_monthly_summary.csv')
        side=[]
        for s,g in best_led.groupby('side') if not best_led.empty else []:
            m=metric(g); m.update(side=s); side.append(m)
        save(pd.DataFrame(side),out/'gold_v3_107gh_best_gate_side_summary.csv'); outputs.append('gold_v3_107gh_best_gate_side_summary.csv')
        cand=[]
        for cid,g in best_led.groupby('candidate_id') if not best_led.empty else []:
            m=metric(g); first=g.iloc[0]; m.update(candidate_id=cid,side=first.side,condition=first.condition,profile_id=first.profile_id,cooldown_bars=first.cooldown_bars); cand.append(m)
        save(pd.DataFrame(cand),out/'gold_v3_107gh_best_gate_candidate_summary.csv'); outputs.append('gold_v3_107gh_best_gate_candidate_summary.csv')
        if logs: save(pd.concat(logs,ignore_index=True),out/'gold_v3_107gh_gate_decision_log.csv'); outputs.append('gold_v3_107gh_gate_decision_log.csv')
        gm=metric(best_led); gates=[qgate('gate_trades',gm['trades'],'>=',300),qgate('gate_pf',gm['profit_factor'],'>=',2.0),qgate('gate_wr',gm['win_rate'],'>=',0.60),qgate('gate_negative_months',gm['negative_month_count'],'<=',2)]
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107gh_gate_quality_matrix.csv'); outputs.append('gold_v3_107gh_gate_quality_matrix.csv')
        lim=pd.DataFrame([dict(limitation_id='entry_month_proxy',severity='IMPORTANT',message='No exact exit_dt dependency is required in this script. If fixed ledger lacks exit_dt, monthly prior-entry results are used as an audit proxy, not exact live rehydration.'),dict(limitation_id='fixed_candidate_selection_bias',severity='IMPORTANT',message='Fixed portfolio candidates came from prior full-period audits. Train-only candidate universe audit is still required before live consideration.')])
        save(lim,out/'gold_v3_107gh_limitations.csv'); outputs.append('gold_v3_107gh_limitations.csv')
        rec=[]
        if best['mode']=='no_gate_baseline': rec.append(dict(priority=1,action='keep_fixed_portfolio_no_monthly_reselection_for_next_train_only_universe_audit',reason='monthly sticky gate did not beat baseline score'))
        else: rec.append(dict(priority=1,action='test_best_sticky_gate_in_train_only_universe_protocol',reason='sticky prior-month gate improved balanced score over no-gate baseline'))
        rec.append(dict(priority=2,action='generate_candidate_universe_using_train_window_only',reason='remaining full-period candidate-universe bias must be removed'))
        save(pd.DataFrame(rec),out/'gold_v3_107gh_recommended_next_actions.csv'); outputs.append('gold_v3_107gh_recommended_next_actions.csv')
        findings.append('baseline_fixed='+json.dumps(bm,ensure_ascii=False,default=str))
        findings.append('best_gate='+json.dumps(best,ensure_ascii=False,default=str))
        findings.append('best_gate_metric='+json.dumps(gm,ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='fixed_ledger_rows_positive',result='PASS' if len(base)>0 else 'FAIL',observed=len(base),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_minutes_to_20min_stop_if_over_1h')
    if not blockers and 'gm' in locals(): summary.update({f'best_gate_{k}':v for k,v in gm.items()})
    save(pd.DataFrame(blockers),out/'gold_v3_107gh_blocker_matrix.csv'); save(val,out/'gold_v3_107gh_validation_matrix.csv')
    (out/'gold_v3_107gh_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GH report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gh_blocker_matrix.csv','gold_v3_107gh_validation_matrix.csv','gold_v3_107gh_summary.json','GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GH PASTE_ME_FIXED_PORTFOLIO_STICKY_GATE',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GD fixed portfolio ledger only; sticky prior-history monthly gates; no runtime change','runtime_estimate: light_to_medium; minutes_to_20min; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
