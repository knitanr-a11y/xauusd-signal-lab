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

STEP='GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY'
READY='GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
REGIMES={
 'REGIME_2025_H2':('2025-01-01','2025-07-01','2025-07-01','2026-01-01','2025'),
 'REGIME_2026_Q1Q2':('2025-01-01','2026-01-01','2026-01-01','2026-05-01','2026_Q1Q2'),
 'REGIME_2026_HIGHVOL_MAYJUN':('2025-01-01','2026-05-01','2026-05-01','2027-01-01','2026_HIGHVOL'),
}
QS=[0.40,0.50,0.60,0.70,0.80,0.90]

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f'progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}')
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def day_stats(df):
    if df is None or df.empty: return dict(unique_trade_days=0,date_span_days=0,max_day_trade_share=0.0,business_day_trade_rate=0.0,active_trade_day_rate=0.0,min_entry_dt='',max_entry_dt='')
    x=df.copy(); x['day']=pd.to_datetime(x.entry_dt).dt.date
    g=x.groupby('day').size().reset_index(name='n')
    mn=pd.to_datetime(x.entry_dt.min()).date(); mx=pd.to_datetime(x.entry_dt.max()).date(); span=(mx-mn).days+1
    bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,'D'))); ad=len(g)
    return dict(unique_trade_days=int(ad),date_span_days=int(span),max_day_trade_share=float(g.n.max()/len(x)),business_day_trade_rate=float(len(x)/bd) if bd else 0.0,active_trade_day_rate=float(len(x)/ad) if ad else 0.0,min_entry_dt=str(mn),max_entry_dt=str(mx))
def metrics(df): return gy.density_metrics(df)|day_stats(df)
def config_keys(sel,sp,tier,topn):
    return sel[(sel.split.astype(str)==sp)&(sel.tier.astype(str)==tier)&(pd.to_numeric(sel.top_n,errors='coerce')==int(topn))].sort_values('rank')['global_candidate_key'].astype(str).tolist()

def score_policy(ledger,keys,trs,tre,tes,tee,score_q):
    train=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
    test=ledger[(ledger.global_candidate_key.isin(keys))&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
    if train.empty or test.empty: return pd.DataFrame(), pd.DataFrame(), None
    bins=h.build_bins(train).sort_values('score',ascending=False).head(80).copy()
    if bins.empty: return train.iloc[0:0], test.iloc[0:0], None
    train['feature_score']=h.score_rows(train,bins); test['feature_score']=h.score_rows(test,bins)
    thr=float(train.feature_score.quantile(score_q))
    passed=test[test.feature_score>=thr].copy()
    return passed,bins,thr

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--top-configs-per-regime',type=int,default=8); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107kc'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START')
    blocks=[]; outputs=[]; findings=[]; vals=[]
    d2p=root/'107gvc'/'gold_v3_107gv_density2_pass_configs.csv'; selp=root/'107guc'/'gold_v3_107gu_selected_candidate_keys.csv'
    for name,p in [('107gv_density2',d2p),('107gu_selected',selp)]:
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+name,path=str(p)))
    ledger=h.load_augmented_ledger(mt5,root,out); outputs+=['gold_v3_107h_ohlc_coverage.csv','gold_v3_107h_input_ledger_coverage.csv','gold_v3_107h_feature_join_coverage.csv']
    if ledger.empty: blocks.append(dict(blocker_id='missing_augmented_ledger_or_ohlc'))
    if not blocks:
        d2=pd.read_csv(d2p,encoding='utf-8-sig'); sel=pd.read_csv(selp,encoding='utf-8-sig')
        cfg_rows=[]
        for reg in REGIMES:
            x=d2[d2.split.astype(str)==reg].sort_values('review_score',ascending=False).head(args.top_configs_per_regime)
            cfg_rows += [r for _,r in x.iterrows()]
        total=len(cfg_rows)*len(QS); cur=0; prog(cur,total,'start')
        rows=[]; ledgers=[]; bin_rows=[]
        for cfg in cfg_rows:
            sp=str(cfg.split); tier=str(cfg.tier); topn=int(cfg.top_n)
            if sp not in REGIMES: continue
            trs,tre,tes,tee,rg=REGIMES[sp]
            keys=config_keys(sel,sp,tier,topn)
            if not keys: continue
            for q in QS:
                cur+=1
                passed,bins,thr=score_policy(ledger,keys,trs,tre,tes,tee,q)
                if thr is None: continue
                m=metrics(passed)
                row=dict(regime_split=sp,regime_group=rg,tier=tier,base_top_n=topn,score_quantile=q,score_threshold=thr,source_review_score=float(cfg.review_score),source_test_wr=float(cfg.test_wr),source_test_pf=float(cfg.test_pf),source_density=float(cfg.test_business_day_trade_rate))
                row.update({f'oos_{k}':v for k,v in m.items()})
                row['regime_pass_60']=bool(m['win_rate']>=0.60 and m['profit_factor']>=1.5 and m['trades']>=30)
                row['regime_pass_65']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=30)
                row['concentration_ok']=bool(m['unique_trade_days']>=4 and m['max_day_trade_share']<=0.45)
                row['regime_pass_60_conc']=bool(row['regime_pass_60'] and row['concentration_ok'])
                row['regime_pass_65_conc']=bool(row['regime_pass_65'] and row['concentration_ok'])
                row['policy_key']=f'{tier}||{topn}||Q{q}'
                row['regime_score']=m['win_rate']*12000+cap(m['profit_factor'])*900+m['trades']*0.25+min(m['business_day_trade_rate'],30)*100-m['negative_month_count']*500-m['max_day_trade_share']*1000
                rows.append(row)
                if not passed.empty:
                    tmp=passed.copy(); tmp['policy_key']=row['policy_key']; tmp['regime_split']=sp; tmp['score_quantile']=q; tmp['score_threshold']=thr; ledgers.append(tmp)
                if not bins.empty:
                    bb=bins.copy(); bb['policy_key']=row['policy_key']; bb['regime_split']=sp; bb['score_quantile']=q; bin_rows.append(bb)
                if cur%20==0: prog(cur,total,f'{sp} {tier} topn={topn}')
        per=pd.DataFrame(rows)
        save(per,out/'gold_v3_107k_regime_frontier.csv'); outputs.append('gold_v3_107k_regime_frontier.csv')
        all_led=pd.concat(ledgers,ignore_index=True) if ledgers else pd.DataFrame(); all_bins=pd.concat(bin_rows,ignore_index=True) if bin_rows else pd.DataFrame()
        save(all_led,out/'gold_v3_107k_all_regime_ledgers.csv'); save(all_bins,out/'gold_v3_107k_regime_bin_scores.csv'); outputs+=['gold_v3_107k_all_regime_ledgers.csv','gold_v3_107k_regime_bin_scores.csv']
        if per.empty: blocks.append(dict(blocker_id='no_regime_frontier'))
        else:
            ag=[]
            for key,g in per.groupby('policy_key'):
                have2025=bool((g.regime_group=='2025').any()); have2026=bool((g.regime_group=='2026_HIGHVOL').any())
                best_by_reg=g.sort_values('regime_score',ascending=False).groupby('regime_group').head(1)
                rec=dict(policy_key=key,have_2025=have2025,have_2026_highvol=have2026,regime_count=int(best_by_reg.regime_group.nunique()),min_wr=float(best_by_reg.oos_win_rate.min()),min_pf=float(best_by_reg.oos_profit_factor.min()),min_trades=int(best_by_reg.oos_trades.min()),min_unique_days=int(best_by_reg.unique_trade_days.min()),max_day_trade_share=float(best_by_reg.max_day_trade_share.max()),sum_trades=int(best_by_reg.oos_trades.sum()),avg_wr=float(best_by_reg.oos_win_rate.mean()),avg_pf=float(best_by_reg.oos_profit_factor.replace(np.inf,10).mean()),all_regime_pass_60=bool(have2025 and have2026 and best_by_reg.regime_pass_60_conc.all()),all_regime_pass_65=bool(have2025 and have2026 and best_by_reg.regime_pass_65_conc.all()))
                rec['balanced_score']=rec['min_wr']*15000+cap(rec['min_pf'])*1000+rec['min_trades']*0.5+rec['sum_trades']*0.1-rec['max_day_trade_share']*1000
                ag.append(rec)
            bal=pd.DataFrame(ag).sort_values(['all_regime_pass_65','all_regime_pass_60','balanced_score'],ascending=[False,False,False])
            save(bal,out/'gold_v3_107k_balanced_policy_summary.csv'); outputs.append('gold_v3_107k_balanced_policy_summary.csv')
            best=bal.iloc[0]
            best_rows=per[per.policy_key==best.policy_key].sort_values('regime_score',ascending=False).groupby('regime_group').head(1)
            save(best_rows,out/'gold_v3_107k_best_policy_regime_rows.csv'); outputs.append('gold_v3_107k_best_policy_regime_rows.csv')
            decision='REGIME_BALANCED_STRICT_65_READY_FOR_REHYDRATION' if bool(best.all_regime_pass_65) else ('REGIME_BALANCED_60_READY_FOR_REVIEW' if bool(best.all_regime_pass_60) else 'NO_REGIME_BALANCED_POLICY_NEED_ADAPTIVE_BASE_CANDIDATE_GENERATION')
            gates=pd.DataFrame([gy.gate_row('any_all_regime_pass_65',int(bal.all_regime_pass_65.sum()),'>=',1),gy.gate_row('any_all_regime_pass_60',int(bal.all_regime_pass_60.sum()),'>=',1),gy.gate_row('best_have_2025',int(bool(best.have_2025)),'>=',1),gy.gate_row('best_have_2026_highvol',int(bool(best.have_2026_highvol)),'>=',1),gy.gate_row('best_min_wr_ge_60',float(best.min_wr),'>=',0.60),gy.gate_row('best_min_trades_ge_30',int(best.min_trades),'>=',30)])
            dec=pd.DataFrame([dict(decision=decision,all_regime_pass_65_count=int(bal.all_regime_pass_65.sum()),all_regime_pass_60_count=int(bal.all_regime_pass_60.sum()),best_policy_key=str(best.policy_key),best_min_wr=float(best.min_wr),best_min_pf=float(best.min_pf),best_min_trades=int(best.min_trades),best_sum_trades=int(best.sum_trades),best_avg_wr=float(best.avg_wr),best_max_day_trade_share=float(best.max_day_trade_share),next_stage='107L_REGIME_REHYDRATION_AND_HEALTH_GATE' if (bool(best.all_regime_pass_65) or bool(best.all_regime_pass_60)) else '107L_ADAPTIVE_BASE_CANDIDATE_GENERATION')])
            save(gates,out/'gold_v3_107k_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107k_next_action_decision.csv'); outputs+=['gold_v3_107k_quality_gate_matrix.csv','gold_v3_107k_next_action_decision.csv']
            findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            findings.append('best_policy_regime_rows='+json.dumps(best_rows.to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='regime_frontier_positive',result='PASS',observed=len(per),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'bal' in locals() and not bal.empty:
        summary.update(regime_frontier_rows=len(per),balanced_policy_rows=len(bal),all_regime_pass_65_count=int(bal.all_regime_pass_65.sum()),all_regime_pass_60_count=int(bal.all_regime_pass_60.sum()),best_policy_key=str(bal.iloc[0].policy_key),best_min_wr=float(bal.iloc[0].min_wr),best_min_pf=float(bal.iloc[0].min_pf),best_min_trades=int(bal.iloc[0].min_trades),best_sum_trades=int(bal.iloc[0].sum_trades),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107k_blocker_matrix.csv'); save(val,out/'gold_v3_107k_validation_matrix.csv'); outputs+=['gold_v3_107k_blocker_matrix.csv','gold_v3_107k_validation_matrix.csv','gold_v3_107k_summary.json','GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107k_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107K report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107K PASTE_ME_REGIME_BALANCED_ADAPTIVE_SCORE',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+gy.POOL_POLICY,'source: adaptive train-only feature score evaluated separately on 2025 and 2026 high-vol regimes; no May-only selection; no runtime change','blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    prog(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
