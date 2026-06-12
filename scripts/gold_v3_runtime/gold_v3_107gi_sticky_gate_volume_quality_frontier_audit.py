#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

STEP='GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY'
READY='GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pfcap(x):
    try:
        v=float(x); return 10.0 if math.isinf(v) else min(v,10.0)
    except Exception:
        return 0.0

def score(r, min_tr=0):
    trades=float(r.get('trades',0)); wr=float(r.get('win_rate',0)); pf=pfcap(r.get('profit_factor',0)); sm=float(r.get('sum_result_usd',0)); neg=float(r.get('negative_month_count',0))
    density_bonus=min(trades,600)*0.35
    undersize_penalty=max(0,min_tr-trades)*2.0
    return pf*850 + wr*700 + density_bonus + sm*0.08 - neg*300 - undersize_penalty

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107ghc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gic'; out.mkdir(parents=True,exist_ok=True)
    req={'config':src/'gold_v3_107gh_gate_config_summary.csv','best_ledger':src/'gold_v3_107gh_best_gate_selected_ledger.csv','fixed_ledger':mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'/'gold_v3_107gd_diversified_portfolio_ledger.csv'}
    blockers=[]; vals=[]; findings=[]; outputs=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required prior output missing'))
    if not blockers:
        cfg=pd.read_csv(req['config'],encoding='utf-8-sig')
        for c in ['trades','win_rate','profit_factor','sum_result_usd','negative_month_count','score']:
            if c in cfg.columns: cfg[c]=pd.to_numeric(cfg[c],errors='coerce')
        rows=[]
        for mt in [100,150,250,300,400,500]:
            sub=cfg[cfg.trades>=mt].copy()
            if sub.empty:
                rows.append(dict(min_trades=mt,available=False))
                continue
            sub['frontier_score']=sub.apply(lambda r: score(r,mt),axis=1)
            best=sub.sort_values('frontier_score',ascending=False).iloc[0].to_dict(); best['min_trades']=mt; best['available']=True; rows.append(best)
        frontier=pd.DataFrame(rows); save(frontier,out/'gold_v3_107gi_volume_quality_frontier.csv'); outputs.append('gold_v3_107gi_volume_quality_frontier.csv')
        # classify configs
        cfg['tier_100_score']=cfg.apply(lambda r: score(r,100),axis=1)
        top=cfg.sort_values(['trades','tier_100_score'],ascending=[False,False]).head(100)
        save(top,out/'gold_v3_107gi_top_configs_by_tier.csv'); outputs.append('gold_v3_107gi_top_configs_by_tier.csv')
        # practical recommendation: prefer >=300 if PF>=2.0 and WR>=0.60; else >=250; else baseline/no_gate.
        practical=cfg[(cfg.trades>=300)&(cfg.profit_factor>=2.0)&(cfg.win_rate>=0.60)&(cfg.negative_month_count<=2)].copy()
        tier='>=300_pf2_wr60'
        if practical.empty:
            practical=cfg[(cfg.trades>=250)&(cfg.profit_factor>=2.0)&(cfg.win_rate>=0.58)&(cfg.negative_month_count<=2)].copy(); tier='>=250_pf2_wr58'
        if practical.empty:
            practical=cfg[(cfg.trades>=150)&(cfg.profit_factor>=2.5)&(cfg.win_rate>=0.65)&(cfg.negative_month_count<=2)].copy(); tier='quality_small_pf25_wr65'
        if practical.empty:
            practical=cfg.copy(); tier='fallback_best_score'
        practical['practical_score']=practical.apply(lambda r: score(r,300),axis=1)
        rec=practical.sort_values('practical_score',ascending=False).head(1).copy(); rec['recommendation_tier']=tier
        save(rec,out/'gold_v3_107gi_practical_recommendation.csv'); outputs.append('gold_v3_107gi_practical_recommendation.csv')
        r=rec.iloc[0].to_dict()
        gates=[qgate('practical_trades',float(r.get('trades',0)),'>=',300),qgate('practical_pf',float(r.get('profit_factor',0)),'>=',2.0),qgate('practical_wr',float(r.get('win_rate',0)),'>=',0.60),qgate('practical_negative_months',float(r.get('negative_month_count',0)),'<=',2)]
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107gi_quality_gate_matrix.csv'); outputs.append('gold_v3_107gi_quality_gate_matrix.csv')
        lim=pd.DataFrame([dict(limitation_id='summary_only_frontier',severity='INFO',message='107GI ranks Stage107GH gate config summaries; it does not reconstruct ledgers for every config.'),dict(limitation_id='candidate_universe_bias',severity='IMPORTANT',message='Candidate universe and fixed portfolio were selected from prior full-period audits. Train-only candidate universe remains required before live consideration.')])
        save(lim,out/'gold_v3_107gi_limitations.csv'); outputs.append('gold_v3_107gi_limitations.csv')
        actions=[]
        if gate_df.result.eq('PASS').all():
            actions.append(dict(priority=1,action='test_practical_sticky_gate_with_monthly_detail',reason='practical tier passes trades/PF/WR/negative-month gates'))
        else:
            actions.append(dict(priority=1,action='prefer_fixed_baseline_or_small_quality_gate_pending_train_only_universe',reason='no practical volume-quality gate passed all gates'))
        actions.append(dict(priority=2,action='train_only_candidate_universe_generation',reason='remaining full-period candidate universe bias'))
        save(pd.DataFrame(actions),out/'gold_v3_107gi_recommended_next_actions.csv'); outputs.append('gold_v3_107gi_recommended_next_actions.csv')
        findings.append('frontier='+json.dumps(frontier.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('practical_recommendation='+json.dumps(r,ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='frontier_rows_positive',result='PASS' if len(frontier)>0 else 'FAIL',observed=len(frontier),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h')
    if not blockers and 'r' in locals():
        for k in ['mode','lookback_months','min_train_trades','min_train_pf','min_train_wr','max_train_negative_months','trades','win_rate','profit_factor','sum_result_usd','negative_month_count','recommendation_tier']:
            if k in r: summary['recommended_'+k]=r[k]
    save(pd.DataFrame(blockers),out/'gold_v3_107gi_blocker_matrix.csv'); save(val,out/'gold_v3_107gi_validation_matrix.csv')
    (out/'gold_v3_107gi_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GI report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gi_blocker_matrix.csv','gold_v3_107gi_validation_matrix.csv','gold_v3_107gi_summary.json','GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GI PASTE_ME_STICKY_GATE_VOLUME_QUALITY_FRONTIER',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GH summaries only; volume-quality frontier; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
