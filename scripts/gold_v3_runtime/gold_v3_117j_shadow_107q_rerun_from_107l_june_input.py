#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_107o_rolling_20d_adaptive_loss_trim_audit as ro
import gold_v3_107p_rolling_lookback_parameter_sweep_audit as sw
import gold_v3_107q_stable_filter_family_replay_audit as q

STEP='GOLD_V3_117J_SHADOW_107Q_RERUN_FROM_107L_JUNE_INPUT'
READY='GOLD_V3_117J_SHADOW_107Q_RERUN_READY'
BLOCKED='GOLD_V3_117J_SHADOW_107Q_RERUN_BLOCKED'

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def group_month(df):
    if df is None or df.empty: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str)
    rows=[]
    for m,g in x.groupby('month'):
        r={'month':m}; r.update(ro.metrics(g)); rows.append(r)
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir',default='')
    ap.add_argument('--family-top-n',type=int,default=30)
    ap.add_argument('--lookbacks',default='20,10,5')
    ap.add_argument('--targets',default='5,3,1')
    ap.add_argument('--min-train-rows',type=int,default=150)
    ap.add_argument('--min-removed',type=int,default=10)
    ap.add_argument('--min-retention',type=float,default=0.65)
    args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117j'; out.mkdir(parents=True,exist_ok=True)
    lpath=root/'107lc'/'gold_v3_107l_rehydrated_best_policy_ledger.csv'
    fpath=root/'107mc'/'gold_v3_107m_loss_trim_frontier.csv'
    blockers=[]
    if not lpath.exists(): blockers.append({'blocker_id':'missing_107l_rehydrated_best_policy_ledger','path':str(lpath)})
    if not fpath.exists(): blockers.append({'blocker_id':'missing_107m_loss_trim_frontier','path':str(fpath)})
    led=pd.DataFrame(); seed=pd.DataFrame(); families=pd.DataFrame(); summary_df=pd.DataFrame(); all_selected=[]; all_windows=[]; best_ledger=pd.DataFrame(); best_mon=pd.DataFrame(); best={}
    if not blockers:
        led=pd.read_csv(lpath,encoding='utf-8-sig',low_memory=False)
        seed=pd.read_csv(fpath,encoding='utf-8-sig',low_memory=False)
        for c in ['entry_dt','result_usd','regime_split']:
            if c not in led.columns: blockers.append({'blocker_id':'ledger_missing_required_column','column':c})
        families=q.family_candidates_from_seed(seed,args.family_top_n)
        if families.empty: blockers.append({'blocker_id':'no_seed_families_from_107m_frontier'})
    if not blockers:
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce')
        led=led[led.entry_dt.notna()&led.result_usd.notna()].sort_values('entry_dt').copy()
        led['entry_day']=led.entry_dt.dt.date.astype(str); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        lookbacks=sw.parse_ints(args.lookbacks); targets=sw.parse_ints(args.targets)
        recs=[]; ledgers=[]
        total=max(1,len(families)*len(lookbacks)*len(targets)); i=0
        for _,fam in families.iterrows():
            fd=fam.to_dict()
            for lb in lookbacks:
                for tg in targets:
                    i+=1
                    rec, selected, rolling, windows = q.run_family_combo(led,fd,lb,tg,args.min_train_rows,args.min_removed,args.min_retention)
                    recs.append(rec)
                    if not rolling.empty: ledgers.append(rolling)
                    if not selected.empty: all_selected.append(selected)
                    if not windows.empty: all_windows.append(windows)
        summary_df=pd.DataFrame(recs).sort_values(['primary_gate','review_gate','selection_score'],ascending=[False,False,False]) if recs else pd.DataFrame()
        save(summary_df,out/'gold_v3_117j_shadow_107q_summary.csv')
        if all_selected: save(pd.concat(all_selected,ignore_index=True),out/'gold_v3_117j_shadow_107q_selected_windows.csv')
        if all_windows: save(pd.concat(all_windows,ignore_index=True),out/'gold_v3_117j_shadow_107q_window_metrics.csv')
        if not summary_df.empty:
            best=summary_df.iloc[0].to_dict()
            # Recompute best only to avoid storing all candidate ledgers as a huge file.
            fam=summary_df.iloc[0]
            fd={'family_id':fam.family_id,'feature':fam.feature,'op':fam.op,'side_scope':fam.side_scope}
            _, _, best_ledger, _ = q.run_family_combo(led,fd,int(fam.lookback_active_days),int(fam.target_active_days),args.min_train_rows,args.min_removed,args.min_retention)
            best_ledger=best_ledger.copy(); best_ledger['shadow_stage']='117J'; best_ledger['shadow_only']=True; best_ledger['source_stage']='107Q_shadow_rerun_from_107L_input'
            save(best_ledger,out/'gold_v3_117j_shadow_107q_best_family_trade_ledger.csv')
            best_mon=group_month(best_ledger); save(best_mon,out/'gold_v3_117j_shadow_107q_best_family_monthly_metrics.csv')
            save(pd.DataFrame([best]),out/'gold_v3_117j_best_family_row.csv')
    status=READY if not blockers else BLOCKED
    june_rows=int(((pd.to_datetime(best_ledger.entry_dt,errors='coerce')>=pd.Timestamp('2026-06-01'))&(pd.to_datetime(best_ledger.entry_dt,errors='coerce')<pd.Timestamp('2026-07-01'))).sum()) if not best_ledger.empty and 'entry_dt' in best_ledger.columns else 0
    max_dt=str(pd.to_datetime(best_ledger.entry_dt,errors='coerce').max()) if not best_ledger.empty and 'entry_dt' in best_ledger.columns else ''
    decision='BLOCKED_INPUT_INCOMPLETE' if blockers else ('SHADOW_107Q_RERUN_HAS_JUNE_ROWS_REVIEW_107R6_NEXT' if june_rows>0 else 'SHADOW_107Q_RERUN_NO_JUNE_ROWS_REVIEW_REQUIRED')
    dec=pd.DataFrame([{'decision':decision,'best_family_id':best.get('family_id',''),'best_feature':best.get('feature',''),'best_op':best.get('op',''),'best_lookback_active_days':best.get('lookback_active_days',''),'best_target_active_days':best.get('target_active_days',''),'best_rows':len(best_ledger),'best_max_entry_dt':max_dt,'best_june_rows':june_rows}]); save(dec,out/'gold_v3_117j_decision.csv')
    m=ro.metrics(best_ledger) if not best_ledger.empty else ro.metrics(pd.DataFrame())
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),input_107l_path=str(lpath),input_107m_path=str(fpath),input_107l_rows=int(len(led)) if not led.empty else 0,input_107l_max_entry_dt=str(led.entry_dt.max()) if not led.empty else '',input_107l_june_rows=int(((led.entry_dt>=pd.Timestamp('2026-06-01'))&(led.entry_dt<pd.Timestamp('2026-07-01'))).sum()) if not led.empty else 0,families=len(families) if not families.empty else 0,combo_rows=len(summary_df) if not summary_df.empty else 0,best_family_id=best.get('family_id',''),best_feature=best.get('feature',''),best_op=best.get('op',''),best_side_scope=best.get('side_scope',''),best_lookback_active_days=best.get('lookback_active_days',''),best_target_active_days=best.get('target_active_days',''),best_rows=int(len(best_ledger)),best_max_entry_dt=max_dt,best_june_rows=june_rows,shadow_only=True,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    summary.update({f'best_{k}':v for k,v in m.items()})
    write_json(out/'gold_v3_117j_summary.json',summary|{'blockers':blockers})
    lines=['GOLD V3 117J PASTE_ME_SHADOW_107Q_RERUN_FROM_107L_JUNE_INPUT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'input_107l_rows: {summary["input_107l_rows"]}',f'input_107l_max_entry_dt: {summary["input_107l_max_entry_dt"]}',f'input_107l_june_rows: {summary["input_107l_june_rows"]}',f'families: {summary["families"]}',f'combo_rows: {summary["combo_rows"]}',f'best_family_id: {summary["best_family_id"]}',f'best_feature: {summary["best_feature"]}',f'best_op: {summary["best_op"]}',f'best_lookback_active_days: {summary["best_lookback_active_days"]}',f'best_target_active_days: {summary["best_target_active_days"]}',f'best_rows: {summary["best_rows"]}',f'best_max_entry_dt: {summary["best_max_entry_dt"]}',f'best_june_rows: {summary["best_june_rows"]}','shadow_only: true','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','BEST_MONTHLY_METRICS',best_mon.to_string(index=False) if not best_mon.empty else 'NO_MONTHLY_ROWS','','TOP_SUMMARY',summary_df.head(10).to_string(index=False) if not summary_df.empty else 'NO_SUMMARY_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
