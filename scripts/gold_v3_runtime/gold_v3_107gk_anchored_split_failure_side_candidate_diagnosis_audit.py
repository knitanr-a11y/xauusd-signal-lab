#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY'
READY='GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
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
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x:
        x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def read_csv(p):
    return pd.read_csv(p,encoding='utf-8-sig')

def prep_ledger(df):
    if 'entry_dt' in df.columns:
        df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df=df[df.entry_dt.notna()].copy(); df['entry_month']=df.entry_dt.dt.to_period('M').astype(str)
    if 'result_usd' in df.columns:
        df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce')
    if 'selected_side' in df.columns and 'side' not in df.columns:
        df['side']=df['selected_side']
    if 'wf_side' in df.columns and 'side' not in df.columns:
        df['side']=df['wf_side']
    if 'side' in df.columns:
        df['side']=df.side.astype(str)
    if 'candidate_id' not in df.columns and all(c in df.columns for c in KEY):
        for c in KEY: df[c]=df[c].astype(str)
        df['candidate_id']=df[KEY].astype(str).agg('||'.join,axis=1)
    return df

def norm_col(df, names):
    for n in names:
        if n in df.columns: return n
    return None

def score_quality(row):
    pfv=float(row.get('profit_factor',row.get('test_profit_factor',0)) or 0)
    if math.isinf(pfv): pfv=10.0
    wr=float(row.get('win_rate',row.get('test_win_rate',0)) or 0)
    tr=float(row.get('trades',row.get('test_trades',0)) or 0)
    neg=float(row.get('negative_month_count',row.get('test_negative_month_count',0)) or 0)
    return min(pfv,10)*1000+wr*700+min(tr,400)*.3-neg*250

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); gj=mt5/'FX_OUTPUTS'/'gold_v3'/'107gjc'; gb=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gkc'; out.mkdir(parents=True,exist_ok=True)
    req={'best_by_split':gj/'gold_v3_107gj_best_by_split.csv','selected_candidate_log':gj/'gold_v3_107gj_selected_candidate_log.csv','best_selected_trade_ledger':gj/'gold_v3_107gj_best_selected_trade_ledger.csv','stability_summary':gj/'gold_v3_107gj_stability_summary.csv'}
    blockers=[]; vals=[]; outputs=[]; findings=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required 107GJ output missing'))
    if not blockers:
        best=read_csv(req['best_by_split']); sel=read_csv(req['selected_candidate_log']); led=prep_ledger(read_csv(req['best_selected_trade_ledger'])); stab=read_csv(req['stability_summary'])
        if 'selected_side' in led.columns: led['side']=led['selected_side'].astype(str)
        side_rows=[]
        for (sp,side),g in led.groupby(['split','side']) if len(led) and 'split' in led.columns and 'side' in led.columns else []:
            m=metric(g); m.update(split=sp,side=side); side_rows.append(m)
        side_df=pd.DataFrame(side_rows).sort_values(['split','side']) if side_rows else pd.DataFrame()
        save(side_df,out/'gold_v3_107gk_split_side_test_summary.csv'); outputs.append('gold_v3_107gk_split_side_test_summary.csv')
        cand_rows=[]
        for (sp,cid),g in led.groupby(['split','candidate_id']) if len(led) and 'candidate_id' in led.columns else []:
            m=metric(g); first=g.iloc[0]
            srow=sel[(sel.split==sp)&(sel.candidate_id==cid)] if 'split' in sel.columns and 'candidate_id' in sel.columns else pd.DataFrame()
            train={}
            if not srow.empty:
                r=srow.iloc[0]
                train=dict(train_trades=int(r.get('train_trades',0)),train_wr=float(r.get('train_wr',0)),train_pf=float(r.get('train_pf',0)),train_negative_month_count=int(r.get('train_negative_month_count',0)),selected_rank=int(r.get('rank',0)))
            m.update(split=sp,candidate_id=cid,side=str(first.get('side','')),condition=str(first.get('condition','')),profile_id=str(first.get('profile_id','')),cooldown_bars=str(first.get('cooldown_bars','')),**train)
            m['train_good_test_bad']=bool(m.get('train_pf',0)>=1.8 and m.get('train_wr',0)>=0.55 and (m['profit_factor']<1.8 or m['win_rate']<0.55))
            cand_rows.append(m)
        cand_df=pd.DataFrame(cand_rows).sort_values(['split','side','profit_factor'],ascending=[True,True,False]) if cand_rows else pd.DataFrame()
        save(cand_df,out/'gold_v3_107gk_selected_candidate_train_test_diagnosis.csv'); outputs.append('gold_v3_107gk_selected_candidate_train_test_diagnosis.csv')
        fail_rows=[]
        if len(stab):
            failed=stab[stab.get('passes_basic_oos_gate',False).astype(str).str.lower().isin(['false','0'])]
            for _,r in failed.iterrows():
                sp=r['split']; ss=side_df[side_df.split==sp] if len(side_df) else pd.DataFrame()
                if ss.empty:
                    fail_rows.append(dict(split=sp,weak_side='UNKNOWN',reason='no_side_summary'))
                else:
                    for _,s in ss.iterrows():
                        weak=bool(float(s.profit_factor)<1.8 or float(s.win_rate)<0.55 or int(s.trades)<80)
                        reason=[]
                        if float(s.profit_factor)<1.8: reason.append('low_pf')
                        if float(s.win_rate)<0.55: reason.append('low_wr')
                        if int(s.trades)<80: reason.append('low_trades')
                        fail_rows.append(dict(split=sp,side=s.side,trades=int(s.trades),win_rate=float(s.win_rate),profit_factor=float(s.profit_factor),sum_result_usd=float(s.sum_result_usd),negative_month_count=int(s.negative_month_count),weak_side=weak,reason='|'.join(reason) if reason else 'ok'))
        fail_df=pd.DataFrame(fail_rows)
        save(fail_df,out/'gold_v3_107gk_failed_split_side_attribution.csv'); outputs.append('gold_v3_107gk_failed_split_side_attribution.csv')
        # Post-hoc lightweight alternative hints from optional summaries only.
        hints=[]
        optional_files=[gb/'gold_v3_107gb_candidate_split_summary.csv', gb/'gold_v3_107gb_candidate_monthly_summary.csv']
        for p in optional_files:
            if not p.exists(): continue
            try:
                odf=read_csv(p)
                sidec=norm_col(odf,['side','portfolio_side','selected_side'])
                condc=norm_col(odf,['condition','candidate_condition'])
                profc=norm_col(odf,['profile_id','profile'])
                splitc=norm_col(odf,['split','period','scope'])
                trc=norm_col(odf,['trades','trade_count','count'])
                pfc=norm_col(odf,['profit_factor','pf'])
                wrc=norm_col(odf,['win_rate','wr'])
                negc=norm_col(odf,['negative_month_count','neg_months'])
                if sidec and condc and trc and pfc and wrc:
                    x=odf.copy()
                    x['trades_n']=pd.to_numeric(x[trc],errors='coerce').fillna(0)
                    x['pf_n']=pd.to_numeric(x[pfc],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(999)
                    x['wr_n']=pd.to_numeric(x[wrc],errors='coerce').fillna(0)
                    if negc: x['neg_n']=pd.to_numeric(x[negc],errors='coerce').fillna(0)
                    else: x['neg_n']=0
                    x=x[(x.trades_n>=50)&(x.pf_n>=1.8)&(x.wr_n>=0.55)&(x.neg_n<=2)].copy()
                    x['hint_score']=x.apply(score_quality,axis=1)
                    for _,r in x.sort_values('hint_score',ascending=False).head(30).iterrows():
                        hints.append(dict(source_file=p.name,side=str(r[sidec]),condition=str(r[condc]),profile_id=str(r[profc]) if profc else '',split=str(r[splitc]) if splitc else '',trades=float(r.trades_n),win_rate=float(r.wr_n),profit_factor=float(r.pf_n),negative_month_count=float(r.neg_n),posthoc_hint_only=True))
            except Exception as e:
                hints.append(dict(source_file=p.name,error=str(e),posthoc_hint_only=True))
        hint_df=pd.DataFrame(hints)
        save(hint_df,out/'gold_v3_107gk_posthoc_alternative_vector_hints.csv'); outputs.append('gold_v3_107gk_posthoc_alternative_vector_hints.csv')
        # Recommendations by side/vector gap.
        rec=[]
        for side in ['LONG','SHORT']:
            s=fail_df[(fail_df.side==side)&(fail_df.weak_side==True)] if len(fail_df) and 'side' in fail_df.columns else pd.DataFrame()
            cg=cand_df[(cand_df.side==side)&(cand_df.train_good_test_bad==True)] if len(cand_df) and 'side' in cand_df.columns else pd.DataFrame()
            needs=bool(len(s)>0 or len(cg)>0)
            rec.append(dict(side=side,needs_new_vector=needs,weak_failed_split_count=int(len(s)),train_good_test_bad_candidate_count=int(len(cg)),recommendation='ADD_INDEPENDENT_'+side+'_VECTORS' if needs else 'CURRENT_SELECTED_'+side+'_VECTORS_NOT_PRIMARY_FAILURE'))
        # global recommendation
        rec.append(dict(side='BOTH',needs_new_vector=True,weak_failed_split_count=int(len(fail_df[fail_df.weak_side==True])) if len(fail_df) and 'weak_side' in fail_df.columns else 0,train_good_test_bad_candidate_count=int(len(cand_df[cand_df.train_good_test_bad==True])) if len(cand_df) and 'train_good_test_bad' in cand_df.columns else 0,recommendation='NEXT_STAGE_SHOULD_GENERATE_NEW_LONG_AND_SHORT_VECTOR_FAMILIES_NOT_ONLY_RETUNE_GATES'))
        rec_df=pd.DataFrame(rec)
        save(rec_df,out/'gold_v3_107gk_vector_gap_recommendations.csv'); outputs.append('gold_v3_107gk_vector_gap_recommendations.csv')
        gates=[dict(gate='diagnosis_rows_positive',observed=len(cand_df),operator='>=',threshold=1,result='PASS' if len(cand_df)>=1 else 'FAIL'),dict(gate='side_summary_positive',observed=len(side_df),operator='>=',threshold=1,result='PASS' if len(side_df)>=1 else 'FAIL'),dict(gate='vector_recommendations_positive',observed=len(rec_df),operator='>=',threshold=1,result='PASS' if len(rec_df)>=1 else 'FAIL')]
        gate_df=pd.DataFrame(gates)
        save(gate_df,out/'gold_v3_107gk_quality_gate_matrix.csv'); outputs.append('gold_v3_107gk_quality_gate_matrix.csv')
        lim=pd.DataFrame([dict(limitation_id='selected_candidates_only_primary',severity='INFO',message='Primary diagnosis uses selected 107GJ candidates and their test ledger; it does not re-run full grid search.'),dict(limitation_id='posthoc_hints_not_selection',severity='IMPORTANT',message='Alternative vector hints from 107GB summaries are post-hoc diagnostic hints only, not approved selections.'),dict(limitation_id='full_train_only_universe_still_required',severity='IMPORTANT',message='New vector families must still be evaluated in audit-only train/test protocol before live consideration.')])
        save(lim,out/'gold_v3_107gk_limitations.csv'); outputs.append('gold_v3_107gk_limitations.csv')
        next_actions=pd.DataFrame([dict(priority=1,action='create_new_long_short_vector_family_audit',reason='Both LONG and SHORT need independent vectors if current selected candidates fail by split/side.'),dict(priority=2,action='separate_trend_pullback_breakout_reversal_session_vectors',reason='Avoid relying on one fixed vector family across all periods.'),dict(priority=3,action='evaluate_new_vectors_with_anchored_train_test_before_heavy_train_only_ohlc_universe',reason='107GJ basic OOS gate passed only one split.')])
        save(next_actions,out/'gold_v3_107gk_recommended_next_actions.csv'); outputs.append('gold_v3_107gk_recommended_next_actions.csv')
        findings.append('side_test_summary='+json.dumps(side_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('failed_split_side_attribution='+json.dumps(fail_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('vector_gap_recommendations='+json.dumps(rec_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('posthoc_hint_rows='+str(len(hint_df)))
        vals.append(dict(check_id='diagnosis_outputs_positive',result='PASS' if len(cand_df)>0 and len(side_df)>0 else 'FAIL',observed=f'candidate_rows={len(cand_df)},side_rows={len(side_df)}',expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]:
        vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(gj),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h')
    if not blockers:
        summary['side_summary_rows']=len(side_df); summary['candidate_diagnosis_rows']=len(cand_df); summary['posthoc_hint_rows']=len(hint_df) if 'hint_df' in locals() else 0
    save(pd.DataFrame(blockers),out/'gold_v3_107gk_blocker_matrix.csv'); save(val,out/'gold_v3_107gk_validation_matrix.csv')
    (out/'gold_v3_107gk_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GK report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gk_blocker_matrix.csv','gold_v3_107gk_validation_matrix.csv','gold_v3_107gk_summary.json','GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GK PASTE_ME_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GJ outputs primarily; optional Stage107GB lightweight summaries; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
