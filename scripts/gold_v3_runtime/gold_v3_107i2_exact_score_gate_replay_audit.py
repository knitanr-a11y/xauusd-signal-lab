#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,warnings
from datetime import datetime,timezone
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore', category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_107h_train_only_feature_score_gate_audit as h

STEP='GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_AUDIT_ONLY'
READY='GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f'progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}')
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def day_stats(df):
    if df is None or df.empty:
        return dict(unique_trade_days=0,date_span_days=0,max_day_trades=0,max_day_trade_share=0.0,max_day_win_rate=0.0)
    x=df.copy(); x['day']=pd.to_datetime(x.entry_dt).dt.date; x['is_win']=pd.to_numeric(x.result_usd,errors='coerce')>0
    g=x.groupby('day').agg(day_trades=('result_usd','size'),day_win_rate=('is_win','mean')).reset_index()
    maxrow=g.sort_values('day_trades',ascending=False).iloc[0]
    span=(pd.to_datetime(x.entry_dt.max()).date()-pd.to_datetime(x.entry_dt.min()).date()).days+1
    return dict(unique_trade_days=int(len(g)),date_span_days=int(span),max_day_trades=int(maxrow.day_trades),max_day_trade_share=float(maxrow.day_trades/len(x)),max_day_win_rate=float(maxrow.day_win_rate))

def config_keys(sel,sp,tier,topn):
    return sel[(sel.split.astype(str)==sp)&(sel.tier.astype(str)==tier)&(pd.to_numeric(sel.top_n,errors='coerce')==int(topn))].sort_values('rank')['global_candidate_key'].astype(str).tolist()

def replay_row(ledger,sel,row):
    sp,tier,topn=str(row.split),str(row.tier),int(row.base_top_n)
    trs,tre,tes,tee=gy.SPLITS[sp]
    keys=config_keys(sel,sp,tier,topn)
    train=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
    test=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
    if train.empty or test.empty:
        return pd.DataFrame(), pd.DataFrame()
    bins=h.build_bins(train).sort_values('score',ascending=False).head(int(getattr(row,'bin_count',80))).copy()
    train['feature_score']=h.score_rows(train,bins); test['feature_score']=h.score_rows(test,bins)
    passed=test[test.feature_score>=float(row.score_threshold)].copy()
    return passed,bins

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--candidate-top',type=int,default=16); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107i2c'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START')
    blocks=[]; outputs=[]; findings=[]; vals=[]
    fpath=root/'107hc'/'gold_v3_107h_score_frontier.csv'; spath=root/'107guc'/'gold_v3_107gu_selected_candidate_keys.csv'
    for name,p in [('107h_frontier',fpath),('107gu_selected',spath)]:
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+name,path=str(p)))
    ledger=h.load_augmented_ledger(mt5,root,out); outputs+=['gold_v3_107h_ohlc_coverage.csv','gold_v3_107h_input_ledger_coverage.csv','gold_v3_107h_feature_join_coverage.csv']
    if ledger.empty: blocks.append(dict(blocker_id='missing_augmented_ledger_or_ohlc'))
    if not blocks:
        fr=pd.read_csv(fpath,encoding='utf-8-sig'); sel=pd.read_csv(spath,encoding='utf-8-sig')
        cand=fr[fr.primary_65_gate.astype(str).str.lower().isin(['true','1'])].copy()
        if cand.empty: cand=fr[fr.small_65_gate.astype(str).str.lower().isin(['true','1'])].copy()
        cand=cand.sort_values(['oos_trades','oos_win_rate','oos_profit_factor'],ascending=[False,False,False]).head(args.candidate_top)
        rows=[]; ledgers=[]; bin_parts=[]
        total=len(cand); prog(0,total,'start')
        for i,(_,r) in enumerate(cand.iterrows(),1):
            passed,bins=replay_row(ledger,sel,r)
            m=gy.density_metrics(passed); d=day_stats(passed)
            rec=dict(candidate_rank=i,split=str(r.split),tier=str(r.tier),base_top_n=int(r.base_top_n),score_quantile=float(r.score_quantile),score_threshold=float(r.score_threshold),source_oos_trades=int(r.oos_trades),source_oos_wr=float(r.oos_win_rate),source_oos_pf=float(r.oos_profit_factor),source_primary_65_gate=bool(r.primary_65_gate),source_small_65_gate=bool(r.small_65_gate),rebuilt_bin_count=len(bins))
            rec.update({f'replayed_{k}':v for k,v in m.items()}); rec.update(d)
            rec['metric_match_trades']=int(m['trades'])==int(r.oos_trades)
            rec['metric_match_wr']=abs(float(m['win_rate'])-float(r.oos_win_rate))<1e-9
            rec['primary_65_replayed']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=30)
            rec['concentration_ok']=bool(d['unique_trade_days']>=4 and d['max_day_trade_share']<=0.45 and d['date_span_days']>=7)
            rec['exact_replay_ready']=bool(rec['metric_match_trades'] and rec['metric_match_wr'] and rec['primary_65_replayed'] and rec['concentration_ok'])
            rec['selection_score']=m['win_rate']*12000+cap(m['profit_factor'])*900+m['trades']*0.4+min(m['business_day_trade_rate'],30)*100-d['max_day_trade_share']*1500
            rows.append(rec)
            if not passed.empty:
                tmp=passed.copy(); tmp['candidate_rank']=i; tmp['score_threshold']=float(r.score_threshold); ledgers.append(tmp)
            if not bins.empty:
                bb=bins.copy(); bb['candidate_rank']=i; bb['split']=str(r.split); bb['tier']=str(r.tier); bb['base_top_n']=int(r.base_top_n); bin_parts.append(bb)
            prog(i,total,f'exact replay candidate {i}/{total}')
        mat=pd.DataFrame(rows).sort_values(['exact_replay_ready','primary_65_replayed','selection_score'],ascending=[False,False,False]) if rows else pd.DataFrame()
        all_led=pd.concat(ledgers,ignore_index=True) if ledgers else pd.DataFrame(); all_bins=pd.concat(bin_parts,ignore_index=True) if bin_parts else pd.DataFrame()
        save(mat,out/'gold_v3_107i2_exact_replay_candidates.csv'); save(all_led,out/'gold_v3_107i2_all_replayed_ledgers.csv'); save(all_bins,out/'gold_v3_107i2_rebuilt_bin_scores.csv')
        outputs+=['gold_v3_107i2_exact_replay_candidates.csv','gold_v3_107i2_all_replayed_ledgers.csv','gold_v3_107i2_rebuilt_bin_scores.csv']
        if mat.empty: blocks.append(dict(blocker_id='no_exact_replay_candidates'))
        else:
            best=mat.iloc[0]
            best_ledger=all_led[all_led.candidate_rank==int(best.candidate_rank)].copy() if not all_led.empty else pd.DataFrame()
            save(best_ledger,out/'gold_v3_107i2_best_replayed_ledger.csv'); outputs.append('gold_v3_107i2_best_replayed_ledger.csv')
            ready=int(mat.exact_replay_ready.sum()); p65=int(mat.primary_65_replayed.sum()); conc=int(mat.concentration_ok.sum()); match=int((mat.metric_match_trades & mat.metric_match_wr).sum())
            decision='EXACT_REPLAY_PRIMARY_65_READY_FOR_HEALTH_GATE_AUDIT' if ready else ('PRIMARY_65_REPLAYED_BUT_METRIC_MISMATCH_REVIEW' if p65 else 'NO_EXACT_REPLAY_PRIMARY_65')
            gates=pd.DataFrame([gy.gate_row('any_exact_replay_ready',ready,'>=',1),gy.gate_row('any_primary_65_replayed',p65,'>=',1),gy.gate_row('any_metric_match',match,'>=',1),gy.gate_row('best_concentration_ok',int(bool(best.concentration_ok)),'>=',1),gy.gate_row('best_wr_ge_65',float(best.replayed_win_rate),'>=',0.65)])
            dec=pd.DataFrame([dict(decision=decision,exact_replay_ready_count=ready,primary_65_replayed_count=p65,concentration_ok_count=conc,metric_match_count=match,best_candidate_rank=int(best.candidate_rank),best_split=str(best.split),best_tier=str(best.tier),best_base_top_n=int(best.base_top_n),best_score_quantile=float(best.score_quantile),best_score_threshold=float(best.score_threshold),best_trades=int(best.replayed_trades),best_wr=float(best.replayed_win_rate),best_pf=float(best.replayed_profit_factor),best_density=float(best.replayed_business_day_trade_rate),unique_trade_days=int(best.unique_trade_days),max_day_trade_share=float(best.max_day_trade_share),next_stage='107J_ROLLING_HEALTH_GATE_SIMULATION' if ready else '107J_SCORE_GATE_ROOT_CAUSE_OR_NEW_BASE_CANDIDATE')])
            save(gates,out/'gold_v3_107i2_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107i2_next_action_decision.csv'); outputs+=['gold_v3_107i2_quality_gate_matrix.csv','gold_v3_107i2_next_action_decision.csv']
            findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            findings.append('top_exact_replay_candidates='+json.dumps(mat.head(12).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='exact_replay_candidates_positive',result='PASS',observed=len(mat),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'mat' in locals() and not mat.empty:
        summary.update(exact_replay_candidates=len(mat),exact_replay_ready_count=int(mat.exact_replay_ready.sum()),primary_65_replayed_count=int(mat.primary_65_replayed.sum()),metric_match_count=int((mat.metric_match_trades & mat.metric_match_wr).sum()),best_wr=float(mat.iloc[0].replayed_win_rate),best_pf=float(mat.iloc[0].replayed_profit_factor),best_trades=int(mat.iloc[0].replayed_trades),best_density=float(mat.iloc[0].replayed_business_day_trade_rate),best_unique_trade_days=int(mat.iloc[0].unique_trade_days),best_max_day_trade_share=float(mat.iloc[0].max_day_trade_share),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107i2_blocker_matrix.csv'); save(val,out/'gold_v3_107i2_validation_matrix.csv'); outputs+=['gold_v3_107i2_blocker_matrix.csv','gold_v3_107i2_validation_matrix.csv','gold_v3_107i2_summary.json','GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107i2_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107I2 report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107I2 PASTE_ME_EXACT_SCORE_GATE_REPLAY',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+gy.POOL_POLICY,'source: Stage107H score frontier replayed by rebuilding train-only bins per row; no persisted bin duplication; no runtime change','blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    prog(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
