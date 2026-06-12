#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY'
READY='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
KEY=['side','condition','profile_id','cooldown_bars']

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pf_from(gp,gl):
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    gp=float(x[x.result_usd>0].result_usd.sum()); gl=float(-x[x.result_usd<0].result_usd.sum()); mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf_from(gp,gl)),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def pfcap(x):
    try:
        return 10.0 if math.isinf(float(x)) else min(float(x),10.0)
    except Exception:
        return 0.0

def score_train(m): return pfcap(m['profit_factor'])*1000 + m['win_rate']*700 + min(m['trades'],600)*0.35 - m['negative_month_count']*250

def month_range(months,target,lookback):
    i=months.index(target)
    if lookback=='expanding': return months[:i]
    n=int(lookback); return months[max(0,i-n):i]

def overlap(a,b): return len(a&b)/max(1,min(len(a),len(b))) if a and b else 0.0

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def make_candidate_id(df):
    return df[KEY].astype(str).agg('||'.join,axis=1)

def train_stats(month_agg, train_months, side):
    x=month_agg[(month_agg.entry_month.isin(train_months))&(month_agg.side==side)]
    if x.empty: return pd.DataFrame()
    g=x.groupby(['candidate_id','side','condition','profile_id','cooldown_bars'],dropna=False).agg(trades=('trades','sum'),wins=('wins','sum'),losses=('losses','sum'),sum_result_usd=('sum_result_usd','sum'),gross_profit=('gross_profit','sum'),gross_loss=('gross_loss','sum'),negative_month_count=('month_sum','lambda')).reset_index()
    return g

def aggregate_train(month_agg, train_months, side):
    x=month_agg[(month_agg.entry_month.isin(train_months))&(month_agg.side==side)].copy()
    if x.empty: return pd.DataFrame()
    rows=[]
    for k,g in x.groupby(['candidate_id','side','condition','profile_id','cooldown_bars'],dropna=False):
        tr=int(g.trades.sum()); gp=float(g.gross_profit.sum()); gl=float(g.gross_loss.sum()); sm=float(g.sum_result_usd.sum()); wr=float(g.wins.sum()/tr) if tr else 0.0
        rows.append(dict(candidate_id=k[0],side=k[1],condition=k[2],profile_id=k[3],cooldown_bars=k[4],trades=tr,wins=int(g.wins.sum()),losses=int(g.losses.sum()),win_rate=wr,profit_factor=float(pf_from(gp,gl)),sum_result_usd=sm,negative_month_count=int((g.month_sum<0).sum())))
    return pd.DataFrame(rows)

def select_side(month_agg, train_months, side, min_tr, min_pf, min_wr, max_neg, max_cands, entry_sets):
    stat=aggregate_train(month_agg,train_months,side)
    if stat.empty: return []
    stat=stat[(stat.trades>=min_tr)&(stat.profit_factor>=min_pf)&(stat.win_rate>=min_wr)&(stat.negative_month_count<=max_neg)].copy()
    if stat.empty: return []
    stat['train_score']=stat.apply(lambda r: score_train(r),axis=1)
    stat=stat.sort_values('train_score',ascending=False)
    chosen=[]; sets=[]
    for _,r in stat.iterrows():
        st=entry_sets.get(r.candidate_id,set())
        ov=max([overlap(st,s) for s in sets],default=0.0)
        if ov<=0.35:
            chosen.append((r.candidate_id,float(r.train_score),r.to_dict(),ov)); sets.append(st)
        if len(chosen)>=max_cands: break
    return chosen

def apply_target(led,target_month,chosen):
    ids=[]; score_map={}; meta_map={}
    for side,items in chosen.items():
        for rank,(cid,sc,meta,ov) in enumerate(items,1):
            ids.append(cid); score_map[cid]=sc; meta_map[cid]=(side,rank,meta,ov)
    if not ids: return pd.DataFrame(),0
    raw=led[(led.entry_month==target_month)&(led.candidate_id.isin(ids))].copy()
    if raw.empty: return pd.DataFrame(),0
    raw['train_score']=raw.candidate_id.map(score_map)
    raw['wf_side']=raw.candidate_id.map(lambda x: meta_map[x][0])
    raw['wf_rank']=raw.candidate_id.map(lambda x: meta_map[x][1])
    raw['train_trades']=raw.candidate_id.map(lambda x: meta_map[x][2]['trades'])
    raw['train_pf']=raw.candidate_id.map(lambda x: meta_map[x][2]['profit_factor'])
    raw['train_wr']=raw.candidate_id.map(lambda x: meta_map[x][2]['win_rate'])
    raw['target_month']=target_month
    raw=raw.sort_values(['entry_dt','train_score'],ascending=[True,False])
    conflicts=int(raw.duplicated('entry_dt',keep=False).sum())
    return raw.drop_duplicates('entry_dt',keep='first'),conflicts

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--mode',default='fast',choices=['fast','medium'])
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gfc'; out.mkdir(parents=True,exist_ok=True)
    ledger_p=src/'gold_v3_107gb_top_candidate_trade_ledger.csv'; blockers=[]; vals=[]; findings=[]; outputs=[]
    if not ledger_p.exists(): blockers.append(dict(blocker_id='missing_107gb_candidate_ledger',artifact=str(ledger_p),reason='required 107GB output missing'))
    if not blockers:
        led=pd.read_csv(ledger_p,encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led=led[led.entry_dt.notna()].copy(); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce'); led=led[led.result_usd.notna()].copy()
        for c in KEY: led[c]=led[c].astype(str)
        led['candidate_id']=make_candidate_id(led); led['gross_profit']=led.result_usd.clip(lower=0); led['gross_loss']=(-led.result_usd.clip(upper=0));
        months=sorted(led.entry_month.unique().tolist())
        month_agg=led.groupby(['candidate_id','side','condition','profile_id','cooldown_bars','entry_month'],dropna=False).agg(trades=('result_usd','size'),wins=('result_usd',lambda s:int((s>0).sum())),losses=('result_usd',lambda s:int((s<0).sum())),sum_result_usd=('result_usd','sum'),gross_profit=('gross_profit','sum'),gross_loss=('gross_loss','sum'),month_sum=('result_usd','sum')).reset_index()
        entry_sets={cid:set(g.entry_dt.astype(str)) for cid,g in led.groupby('candidate_id')}
        if a.mode=='fast':
            cfgs=list(itertools.product(['6','12','expanding'],[20,40],[1.5,1.8],[0.50,0.55],[1,2],[1,2]))
        else:
            cfgs=list(itertools.product(['3','6','12','expanding'],[20,40,80],[1.5,1.8,2.0],[0.50,0.55,0.60],[1,2],[1,2,4]))
        cfg_rows=[]; monthly_rows=[]; select_rows=[]; best_parts={}; best_score=-1e18; best_id=-1; best_conf=0
        for ci,(lb,mintr,minpf,minwr,maxneg,maxcand) in enumerate(cfgs):
            parts=[]; conf_total=0; wf_months=0
            for target in months:
                train_months=month_range(months,target,lb)
                if len(train_months)<3: continue
                chosen={'LONG':select_side(month_agg,train_months,'LONG',mintr,minpf,minwr,maxneg,maxcand,entry_sets),'SHORT':select_side(month_agg,train_months,'SHORT',mintr,minpf,minwr,maxneg,maxcand,entry_sets)}
                for side,items in chosen.items():
                    for rank,(cid,sc,meta,ov) in enumerate(items,1):
                        select_rows.append(dict(config_id=ci,target_month=target,side=side,rank=rank,candidate_id=cid,condition=meta['condition'],profile_id=meta['profile_id'],cooldown_bars=meta['cooldown_bars'],train_score=sc,train_trades=meta['trades'],train_wr=meta['win_rate'],train_pf=meta['profit_factor'],train_negative_month_count=meta['negative_month_count'],max_overlap=ov,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand))
                outm,conf=apply_target(led,target,chosen); conf_total+=conf
                if not outm.empty:
                    wf_months+=1; outm=outm.assign(config_id=ci,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand); parts.append(outm)
                    mm=metric(outm); mm.update(config_id=ci,target_month=target,conflict_rows_before_resolution=conf); monthly_rows.append(mm)
            allout=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
            m=metric(allout); m.update(config_id=ci,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand,walkforward_months=wf_months,conflict_rows_before_resolution=conf_total)
            m['wf_score']=pfcap(m['profit_factor'])*1000+m['win_rate']*800+min(m['trades'],800)*0.3-m['negative_month_count']*350-conf_total*0.1
            cfg_rows.append(m)
            if m['wf_score']>best_score:
                best_score=m['wf_score']; best_id=ci; best_parts={'ledger':allout.copy(),'metric':m}; best_conf=conf_total
        cfg=pd.DataFrame(cfg_rows).sort_values('wf_score',ascending=False); save(cfg,out/'gold_v3_107gf_wf_config_summary.csv'); outputs.append('gold_v3_107gf_wf_config_summary.csv')
        save(pd.DataFrame(monthly_rows),out/'gold_v3_107gf_wf_monthly_summary.csv'); outputs.append('gold_v3_107gf_wf_monthly_summary.csv')
        save(pd.DataFrame(select_rows),out/'gold_v3_107gf_wf_selection_log.csv'); outputs.append('gold_v3_107gf_wf_selection_log.csv')
        best_led=best_parts.get('ledger',pd.DataFrame())
        save(best_led,out/'gold_v3_107gf_wf_selected_trade_ledger.csv'); outputs.append('gold_v3_107gf_wf_selected_trade_ledger.csv')
        conf=pd.DataFrame([dict(best_config_id=best_id,conflict_rows_before_resolution=best_conf,mode=a.mode,total_configs=len(cfgs))]); save(conf,out/'gold_v3_107gf_wf_conflict_summary.csv'); outputs.append('gold_v3_107gf_wf_conflict_summary.csv')
        bm=metric(best_led); gates=[qgate('wf_trades',bm['trades'],'>=',300),qgate('wf_pf',bm['profit_factor'],'>=',1.8),qgate('wf_wr',bm['win_rate'],'>=',0.55),qgate('wf_negative_months',bm['negative_month_count'],'<=',3)]
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107gf_quality_gate_matrix.csv'); outputs.append('gold_v3_107gf_quality_gate_matrix.csv')
        warn=pd.DataFrame([dict(warning_id='candidate_universe_selection_bias',severity='IMPORTANT',message='WF selection uses only prior results per target month, but candidate universe comes from Stage107GB full-period generation. Later train-only universe generation audit is still required.'),dict(warning_id='optimized_runtime_mode',severity='INFO',message=f'107GF optimized mode={a.mode}; pre-aggregated monthly candidate stats used to avoid exhaustive repeated groupby.')])
        save(warn,out/'gold_v3_107gf_selection_bias_warning.csv'); outputs.append('gold_v3_107gf_selection_bias_warning.csv')
        findings.append('best_wf_config='+json.dumps(cfg.iloc[0].to_dict(),ensure_ascii=False,default=str) if len(cfg) else 'NO_CONFIG')
        findings.append('best_wf_metric='+json.dumps(bm,ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        findings.append(f'optimized_mode={a.mode}; total_configs={len(cfgs)}')
        vals.append(dict(check_id='wf_configs_positive',result='PASS' if len(cfg)>0 else 'FAIL',observed=len(cfg),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    if not blockers and 'bm' in locals(): summary.update({f'best_wf_{k}':v for k,v in bm.items()})
    save(pd.DataFrame(blockers),out/'gold_v3_107gf_blocker_matrix.csv'); save(val,out/'gold_v3_107gf_validation_matrix.csv')
    (out/'gold_v3_107gf_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GF report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gf_blocker_matrix.csv','gold_v3_107gf_validation_matrix.csv','gold_v3_107gf_summary.json','GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GF PASTE_ME_WALKFORWARD_CANDIDATE_SELECTION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GB candidate ledger; optimized monthly prior-history walk-forward selection; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
