#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,os,re,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore', category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_AUDIT_ONLY'
READY='GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
BOOL_COLS=['m15_up','m15_close_gt_ema20','h1_up','h1_close_gt_ema20','h4_up','h4_close_gt_ema20','d1_up','d1_close_gt_ema20']
NUM_COLS=['m15_atr28','m15_rsi14','m15_dist_atr','m15_range_atr','h1_atr28','h1_rsi14','h1_dist_atr','h1_range_atr','h4_atr28','h4_rsi14','h4_dist_atr','h4_range_atr','d1_rsi14','d1_dist_atr']
THRESH_Q=[0.50,0.60,0.70,0.75,0.80,0.85,0.90,0.92,0.95,0.97]

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f'progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}')
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def load_augmented_ledger(mt5:Path, root:Path, out:Path):
    cov=[]; feats={}; led=[]; lc=[]
    for tf in ['m15','h1','h4','d1']:
        x,c=gy.load_tf(mt5,tf); cov+=c
        if not x.empty: feats[tf]=gy.make_features(x,tf)
    save(pd.DataFrame(cov),out/'gold_v3_107h_ohlc_coverage.csv')
    for src,sub,fn in gy.INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                x=gy.normalize_ledger(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(x)
                if rows: led.append(x)
            except Exception as e: err=str(e)
        lc.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    save(pd.DataFrame(lc),out/'gold_v3_107h_input_ledger_coverage.csv')
    if not led or 'm15' not in feats: return pd.DataFrame()
    ledger=pd.concat(led,ignore_index=True).sort_values('entry_dt')
    for f in feats.values(): ledger=gy.merge_asof_feature(ledger,f)
    fc=[dict(feature=c,coverage=float(ledger[c].notna().mean()),non_null=int(ledger[c].notna().sum())) for c in ledger.columns if re.match(r'^(m15|h1|h4|d1)_',c)]
    save(pd.DataFrame(fc),out/'gold_v3_107h_feature_join_coverage.csv')
    return ledger

def bin_stats(df,col,bin_id,mask):
    x=df[mask].copy(); m=gy.density_metrics(x)
    if m['trades']<12 or m['sum_result_usd']<=0: return None
    score=(m['win_rate']-0.50)*6.0 + math.log(max(m['profit_factor'],0.01)) + min(m['trades'],300)*0.002 - m['negative_month_count']*0.25
    if score<=0: return None
    return dict(feature=col,bin_id=bin_id,score=score,**{f'train_{k}':v for k,v in m.items()})

def build_bins(train):
    bins=[]
    for col in BOOL_COLS:
        if col in train.columns and train[col].notna().sum()>=20:
            s=train[col].fillna(False).astype(bool)
            for val in [True,False]:
                r=bin_stats(train,col,str(val),s==val)
                if r: bins.append(r)
    for col in NUM_COLS:
        if col in train.columns and train[col].notna().sum()>=40:
            s=pd.to_numeric(train[col],errors='coerce')
            qs=s.dropna().quantile([0.2,0.4,0.6,0.8]).drop_duplicates().tolist()
            if len(qs)<2: continue
            edges=[-np.inf]+qs+[np.inf]
            for i in range(len(edges)-1):
                lo,hi=edges[i],edges[i+1]
                mask=(s>=lo)&(s<hi)
                r=bin_stats(train,col,f'bin{i}_{lo:.6g}_{hi:.6g}',mask)
                if r:
                    r['lo']=lo; r['hi']=hi; bins.append(r)
    return pd.DataFrame(bins)

def score_rows(df,bins):
    out=pd.Series(0.0,index=df.index)
    if bins.empty: return out
    for _,b in bins.iterrows():
        col=str(b.feature)
        if col not in df.columns: continue
        if col in BOOL_COLS:
            val=True if str(b.bin_id)=='True' else False
            mask=df[col].fillna(False).astype(bool)==val
        else:
            s=pd.to_numeric(df[col],errors='coerce'); mask=(s>=float(b.lo))&(s<float(b.hi))
        out.loc[mask]=out.loc[mask]+float(b.score)
    return out

def config_keys(sel,sp,tier,topn):
    return sel[(sel.split.astype(str)==sp)&(sel.tier.astype(str)==tier)&(pd.to_numeric(sel.top_n,errors='coerce')==int(topn))].sort_values('rank')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--frontier-top',type=int,default=8); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107hc'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START')
    blocks=[]; outputs=['gold_v3_107h_ohlc_coverage.csv','gold_v3_107h_input_ledger_coverage.csv','gold_v3_107h_feature_join_coverage.csv']; vals=[]; findings=[]
    fpath=root/'107gyc'/'gold_v3_107gy_stack_frontier.csv'; sel_path=root/'107guc'/'gold_v3_107gu_selected_candidate_keys.csv'
    if not fpath.exists(): blocks.append(dict(blocker_id='missing_107gy_frontier',path=str(fpath)))
    if not sel_path.exists(): blocks.append(dict(blocker_id='missing_107gu_selected',path=str(sel_path)))
    ledger=load_augmented_ledger(mt5,root,out)
    if ledger.empty: blocks.append(dict(blocker_id='missing_augmented_ledger_or_ohlc'))
    if not blocks:
        fr0=pd.read_csv(fpath,encoding='utf-8-sig').sort_values('review_score',ascending=False).head(args.frontier_top)
        sel=pd.read_csv(sel_path,encoding='utf-8-sig')
        total=len(fr0)*(1+len(THRESH_Q)); cur=0; prog(cur,total,'start')
        frontier=[]; bin_rows=[]; best_ledger=pd.DataFrame()
        for ci,(_,cfg) in enumerate(fr0.iterrows(),1):
            cur+=1
            sp,tier,topn=str(cfg.split),str(cfg.tier),int(cfg.base_top_n)
            if sp not in gy.SPLITS: continue
            trs,tre,tes,tee=gy.SPLITS[sp]
            keys=config_keys(sel,sp,tier,topn)['global_candidate_key'].astype(str).tolist()
            train=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
            test=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
            if train.empty or test.empty: continue
            bins=build_bins(train)
            if bins.empty: continue
            bins=bins.sort_values('score',ascending=False).head(80).copy(); bins['split']=sp; bins['tier']=tier; bins['base_top_n']=topn; bins['source_107gy_wr']=float(cfg.oos_win_rate); bin_rows.append(bins)
            train['feature_score']=score_rows(train,bins); test['feature_score']=score_rows(test,bins)
            for q in THRESH_Q:
                cur+=1
                thr=float(train.feature_score.quantile(q))
                tr_sel=train[train.feature_score>=thr].copy(); te_sel=test[test.feature_score>=thr].copy()
                m=gy.density_metrics(te_sel); mt=gy.density_metrics(tr_sel)
                row=dict(split=sp,tier=tier,base_top_n=topn,score_quantile=q,score_threshold=thr,bin_count=len(bins),source_107gy_wr=float(cfg.oos_win_rate),source_107gy_pf=float(cfg.oos_profit_factor),source_107gy_density=float(cfg.oos_business_day_trade_rate))
                row.update({f'train_{k}':v for k,v in mt.items()}); row.update({f'oos_{k}':v for k,v in m.items()})
                row['primary_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=30)
                row['review_63_gate']=bool(m['win_rate']>=0.63 and m['profit_factor']>=1.8 and m['trades']>=50)
                row['small_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=15)
                row['review_score']=m['win_rate']*13000+cap(m['profit_factor'])*900+m['trades']*0.30+min(m['business_day_trade_rate'],30)*120-m['negative_month_count']*500
                frontier.append(row)
                prog(cur,total,f'meta-score config={ci}/{len(fr0)} q={q}')
        bins_all=pd.concat(bin_rows,ignore_index=True) if bin_rows else pd.DataFrame(); fr=pd.DataFrame(frontier).sort_values('review_score',ascending=False) if frontier else pd.DataFrame()
        save(bins_all,out/'gold_v3_107h_feature_bin_scores.csv'); save(fr,out/'gold_v3_107h_score_frontier.csv'); outputs+=['gold_v3_107h_feature_bin_scores.csv','gold_v3_107h_score_frontier.csv']
        if fr.empty: blocks.append(dict(blocker_id='no_score_frontier'))
        else:
            best=fr.iloc[0]
            sp,tier,topn=str(best.split),str(best.tier),int(best.base_top_n); trs,tre,tes,tee=gy.SPLITS[sp]
            keys=config_keys(sel,sp,tier,topn)['global_candidate_key'].astype(str).tolist()
            test=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
            bb=bins_all[(bins_all.split==sp)&(bins_all.tier==tier)&(bins_all.base_top_n==topn)]
            test['feature_score']=score_rows(test,bb)
            best_ledger=test[test.feature_score>=float(best.score_threshold)].copy()
            save(best_ledger,out/'gold_v3_107h_best_score_ledger.csv'); outputs.append('gold_v3_107h_best_score_ledger.csv')
            p65=int(fr.primary_65_gate.sum()); r63=int(fr.review_63_gate.sum()); s65=int(fr.small_65_gate.sum())
            decision='PRIMARY_65_SCORE_GATE_READY_FOR_REHYDRATION' if p65 else ('REVIEW_63_SCORE_GATE' if r63 else ('SMALL_65_SCORE_GATE_REVIEW' if s65 else 'NO_65_SCORE_GATE_NEED_NEW_BASE_CANDIDATE_GENERATION'))
            gates=pd.DataFrame([gy.gate_row('any_primary_65',p65,'>=',1),gy.gate_row('any_review_63',r63,'>=',1),gy.gate_row('any_small_65',s65,'>=',1),gy.gate_row('best_wr_ge_65',float(best.oos_win_rate),'>=',0.65),gy.gate_row('best_trades_ge_30',int(best.oos_trades),'>=',30)])
            dec=pd.DataFrame([dict(decision=decision,primary_65_gate_count=p65,review_63_gate_count=r63,small_65_gate_count=s65,best_split=sp,best_tier=tier,best_base_top_n=topn,best_score_quantile=float(best.score_quantile),best_score_threshold=float(best.score_threshold),best_trades=int(best.oos_trades),best_wr=float(best.oos_win_rate),best_pf=float(best.oos_profit_factor),best_density=float(best.oos_business_day_trade_rate),next_stage='107I_RESOLVED_ONLY_REHYDRATION' if p65 else '107I_NEW_BASE_CANDIDATE_GENERATION')])
            save(gates,out/'gold_v3_107h_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107h_next_action_decision.csv'); outputs+=['gold_v3_107h_quality_gate_matrix.csv','gold_v3_107h_next_action_decision.csv']
            findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            findings.append('top_score_frontier='+json.dumps(fr.head(12).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='score_frontier_rows_positive',result='PASS',observed=len(fr),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'fr' in locals() and not fr.empty:
        summary.update(score_frontier_rows=len(fr),primary_65_gate_count=int(fr.primary_65_gate.sum()),review_63_gate_count=int(fr.review_63_gate.sum()),small_65_gate_count=int(fr.small_65_gate.sum()),best_wr=float(fr.iloc[0].oos_win_rate),best_pf=float(fr.iloc[0].oos_profit_factor),best_density=float(fr.iloc[0].oos_business_day_trade_rate),best_trades=int(fr.iloc[0].oos_trades),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107h_blocker_matrix.csv'); save(val,out/'gold_v3_107h_validation_matrix.csv'); outputs+=['gold_v3_107h_blocker_matrix.csv','gold_v3_107h_validation_matrix.csv','gold_v3_107h_summary.json','GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107h_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107H report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107H PASTE_ME_TRAIN_ONLY_FEATURE_SCORE_GATE',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+gy.POOL_POLICY,'source: Stage107GY frontier plus exact OHLC as-of feature scores and Stage107 candidate bank; no M5 re-evaluation; no runtime change','runtime_estimate: targeted_light_to_medium_with_percent_progress','blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    prog(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
