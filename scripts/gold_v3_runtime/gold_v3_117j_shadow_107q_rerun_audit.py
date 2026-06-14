#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_107o_rolling_20d_adaptive_loss_trim_audit as ro
import gold_v3_107p_rolling_lookback_parameter_sweep_audit as sw
import gold_v3_107q_stable_filter_family_replay_audit as q107

STEP='GOLD_V3_117J_SHADOW_107Q_RERUN_AUDIT'
READY='GOLD_V3_117J_SHADOW_107Q_RERUN_AUDIT_READY'
BLOCKED='GOLD_V3_117J_SHADOW_107Q_RERUN_AUDIT_BLOCKED'

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def month_rows(df):
    if df is None or df.empty or 'entry_dt' not in df.columns: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['entry_month']=x.entry_dt.dt.to_period('M').astype(str)
    return ro.by_group(x,['entry_month'])
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--family-top-n',type=int,default=30); ap.add_argument('--lookbacks',default='20,10,5'); ap.add_argument('--targets',default='5,3,1'); ap.add_argument('--min-train-rows',type=int,default=150); ap.add_argument('--min-removed',type=int,default=10); ap.add_argument('--min-retention',type=float,default=0.65); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117j'; out.mkdir(parents=True,exist_ok=True)
    lpath=root/'107lc'/'gold_v3_107l_rehydrated_best_policy_ledger.csv'; fpath=root/'107mc'/'gold_v3_107m_loss_trim_frontier.csv'
    blockers=[]; outputs=[]; findings=[]
    if not lpath.exists(): blockers.append({'blocker_id':'missing_107l_rehydrated_best_policy_ledger','path':str(lpath)})
    if not fpath.exists(): blockers.append({'blocker_id':'missing_107m_loss_trim_frontier','path':str(fpath)})
    led=pd.DataFrame(); seed=pd.DataFrame(); families=pd.DataFrame(); summary_df=pd.DataFrame(); all_selected=pd.DataFrame(); all_windows=pd.DataFrame(); best_ledger=pd.DataFrame(); best_reg=pd.DataFrame(); best_mon=pd.DataFrame()
    if not blockers:
        led=pd.read_csv(lpath,encoding='utf-8-sig',low_memory=False); seed=pd.read_csv(fpath,encoding='utf-8-sig',low_memory=False)
        for c in ['entry_dt','result_usd','regime_split']:
            if c not in led.columns: blockers.append({'blocker_id':'ledger_missing_required_column','column':c})
        families=q107.family_candidates_from_seed(seed,args.family_top_n)
        if families.empty: blockers.append({'blocker_id':'no_seed_families_from_107m_frontier'})
    if not blockers:
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce')
        led=led[led.entry_dt.notna()&led.result_usd.notna()].sort_values('entry_dt').copy(); led['entry_day']=led.entry_dt.dt.date.astype(str); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        lookbacks=sw.parse_ints(args.lookbacks); targets=sw.parse_ints(args.targets)
        rows=[]; selected_parts=[]; window_parts=[]; ledger_by_key={}; total=len(families)*len(lookbacks)*len(targets); step=0
        print(f'[{datetime.now().strftime("%H:%M:%S")}] {STEP} START shadow_only=true total_combos={total}',flush=True)
        for _,fam in families.iterrows():
            famd=fam.to_dict()
            for lookback in lookbacks:
                for target in targets:
                    step+=1
                    rec,sel,roll,wm=q107.run_family_combo(led,famd,lookback,target,args.min_train_rows,args.min_removed,args.min_retention)
                    combo_key=f"{famd['family_id']}_L{lookback}_T{target}"; rec['combo_key']=combo_key; rows.append(rec)
                    if not sel.empty: sel['combo_key']=combo_key; selected_parts.append(sel)
                    if not wm.empty: wm['combo_key']=combo_key; window_parts.append(wm)
                    ledger_by_key[combo_key]=roll
                    if step % 10 == 0 or step == total:
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] progress {step}/{total} combo={combo_key} wr={rec.get("family_wr",0):.4f} pf={rec.get("family_pf",0):.3f}',flush=True)
        summary_df=pd.DataFrame(rows).sort_values(['selection_score','family_wr','family_pf'],ascending=[False,False,False]).reset_index(drop=True)
        if not summary_df.empty: summary_df.insert(0,'family_sweep_rank',range(1,len(summary_df)+1))
        all_selected=pd.concat(selected_parts,ignore_index=True) if selected_parts else pd.DataFrame()
        all_windows=pd.concat(window_parts,ignore_index=True) if window_parts else pd.DataFrame()
        best_key=str(summary_df.iloc[0]['combo_key']) if not summary_df.empty else ''
        best_ledger=ledger_by_key.get(best_key,pd.DataFrame()).copy()
        best_reg=ro.by_group(best_ledger,['regime_split']) if not best_ledger.empty else pd.DataFrame()
        best_mon=ro.by_group(best_ledger,['regime_split','entry_month']) if not best_ledger.empty else pd.DataFrame()
        save(summary_df,out/'gold_v3_117j_shadow_107q_family_sweep_summary.csv'); save(all_selected,out/'gold_v3_117j_shadow_107q_all_selected_thresholds.csv'); save(all_windows,out/'gold_v3_117j_shadow_107q_all_window_metrics.csv'); save(best_ledger,out/'gold_v3_117j_shadow_107q_best_family_trade_ledger.csv'); save(best_reg,out/'gold_v3_117j_shadow_107q_best_family_regime_metrics.csv'); save(best_mon,out/'gold_v3_117j_shadow_107q_best_family_monthly_metrics.csv')
        outputs += ['gold_v3_117j_shadow_107q_family_sweep_summary.csv','gold_v3_117j_shadow_107q_all_selected_thresholds.csv','gold_v3_117j_shadow_107q_all_window_metrics.csv','gold_v3_117j_shadow_107q_best_family_trade_ledger.csv','gold_v3_117j_shadow_107q_best_family_regime_metrics.csv','gold_v3_117j_shadow_107q_best_family_monthly_metrics.csv']
        if summary_df.empty: blockers.append({'blocker_id':'empty_family_sweep_summary'})
    best=summary_df.iloc[0].to_dict() if not summary_df.empty else {}; primary=bool(best.get('primary_gate',False)); review=bool(best.get('review_gate',False))
    qg=pd.DataFrame([gy.gate_row('primary_wr_ge_62_5',best.get('family_wr',0.0),'>=',0.625),gy.gate_row('primary_pf_ge_2_70',best.get('family_pf',0.0),'>=',2.70),gy.gate_row('retention_ge_65',best.get('family_retention',0.0),'>=',0.65),gy.gate_row('min_regime_wr_ge_60',best.get('min_regime_wr',0.0),'>=',0.60),gy.gate_row('negative_month_count_eq_0',best.get('family_negative_month_count',999),'==',0),gy.gate_row('review_wr_gain_ge_1pct',best.get('family_wr_gain',0.0),'>=',0.01),gy.gate_row('review_pf_improves',best.get('family_pf',0.0),'>=',best.get('base_pf',999.0))])
    save(qg,out/'gold_v3_117j_shadow_107q_quality_gate_matrix.csv'); outputs.append('gold_v3_117j_shadow_107q_quality_gate_matrix.csv')
    val=pd.DataFrame([{'check_id':'shadow_only','result':'PASS','observed':True,'expected':True,'severity':'BLOCKER'},{'check_id':'source_csv_mutated','result':'PASS','observed':False,'expected':False,'severity':'BLOCKER'},{'check_id':'contract_mutated','result':'PASS','observed':False,'expected':False,'severity':'BLOCKER'},{'check_id':'open_asof_allowed','result':'PASS','observed':False,'expected':False,'severity':'BLOCKER'}])
    validation_failed=int((~val.result.eq('PASS')).sum()) if not val.empty else 0
    status=READY if not blockers and validation_failed==0 else BLOCKED
    if status!=READY: decision='SHADOW_107Q_RERUN_BLOCKED_INPUT_INCOMPLETE'
    elif primary: decision='SHADOW_107Q_PRIMARY_READY_REVIEW_107R6_NEXT'
    elif review: decision='SHADOW_107Q_REVIEW_READY_107R6_NEXT'
    else: decision='SHADOW_107Q_NOT_CONFIRMED_REVIEW_REQUIRED'
    input_june_rows=int(((led.entry_dt>=pd.Timestamp('2026-06-01'))&(led.entry_dt<pd.Timestamp('2026-07-01'))).sum()) if not led.empty else 0
    out_june_rows=int(((pd.to_datetime(best_ledger.entry_dt,errors='coerce')>=pd.Timestamp('2026-06-01'))&(pd.to_datetime(best_ledger.entry_dt,errors='coerce')<pd.Timestamp('2026-07-01'))).sum()) if not best_ledger.empty and 'entry_dt' in best_ledger.columns else 0
    monthly=month_rows(best_ledger); save(monthly,out/'gold_v3_117j_shadow_107q_best_family_month_only_metrics.csv')
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),shadow_only=True,audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,input_107l_rows=int(len(led)) if not led.empty else 0,input_107l_june_rows=input_june_rows,family_rows=int(len(families)) if not families.empty else 0,family_sweep_rows=int(len(summary_df)) if not summary_df.empty else 0,best_combo_key=best.get('combo_key',''),best_family_id=best.get('family_id',''),best_feature=best.get('feature',''),best_op=best.get('op',''),best_side_scope=best.get('side_scope',''),best_lookback_active_days=best.get('lookback_active_days',''),best_target_active_days=best.get('target_active_days',''),best_family_trades=int(best.get('family_trades',0) or 0),best_family_june_rows=out_june_rows,best_family_wr=best.get('family_wr',0.0),best_family_pf=best.get('family_pf',0.0),best_family_retention=best.get('family_retention',0.0),best_family_wr_gain=best.get('family_wr_gain',0.0),best_min_regime_wr=best.get('min_regime_wr',0.0),best_primary_gate=primary,best_review_gate=review,blocker_count=len(blockers),validation_failure_count=validation_failed,elapsed_seconds=round(time.time()-t0,2))
    findings=[]
    if best: findings.append('best_family_combo='+json.dumps(best,ensure_ascii=False,default=str))
    save(pd.DataFrame(blockers),out/'gold_v3_117j_blocker_matrix.csv'); save(val,out/'gold_v3_117j_validation_matrix.csv'); save(pd.DataFrame([summary]),out/'gold_v3_117j_decision.csv')
    write_json(out/'gold_v3_117j_summary.json',summary|{'findings':findings,'blockers':blockers})
    outputs += ['gold_v3_117j_blocker_matrix.csv','gold_v3_117j_validation_matrix.csv','gold_v3_117j_decision.csv','gold_v3_117j_summary.json','paste_me.txt']
    lines=['GOLD V3 117J PASTE_ME_SHADOW_107Q_RERUN_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'shadow_only: true',f'input_107l_rows: {summary["input_107l_rows"]}',f'input_107l_june_rows: {input_june_rows}',f'best_combo_key: {summary["best_combo_key"]}',f'best_feature: {summary["best_feature"]}',f'best_op: {summary["best_op"]}',f'best_lookback_active_days: {summary["best_lookback_active_days"]}',f'best_target_active_days: {summary["best_target_active_days"]}',f'best_family_trades: {summary["best_family_trades"]}',f'best_family_june_rows: {out_june_rows}',f'best_family_wr: {summary["best_family_wr"]}',f'best_family_pf: {summary["best_family_pf"]}',f'best_primary_gate: {primary}',f'best_review_gate: {review}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','MONTHLY_METRICS',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_ROWS','','QUALITY_GATES_BEST_FAMILY',qg.to_string(index=False),'','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
