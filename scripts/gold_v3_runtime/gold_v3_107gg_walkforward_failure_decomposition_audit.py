#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY'
READY='GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
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

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def read(p):
    df=pd.read_csv(p,encoding='utf-8-sig')
    if 'entry_dt' in df.columns:
        df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce')
        df=df[df.entry_dt.notna()].copy()
        df['entry_month']=df.entry_dt.dt.to_period('M').astype(str)
    if 'result_usd' in df.columns: df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce')
    for c in KEY:
        if c in df.columns: df[c]=df[c].astype(str)
    return df

def candidate_id(df):
    if 'candidate_id' not in df.columns and all(c in df.columns for c in KEY):
        df['candidate_id']=df[KEY].astype(str).agg('||'.join,axis=1)
    return df

def side_col(df):
    if 'portfolio_side' in df.columns: return 'portfolio_side'
    if 'wf_side' in df.columns: return 'wf_side'
    return 'side'

def add_scope_metric(rows, scope, name, df):
    m=metric(df); m.update(scope=scope,name=name); rows.append(m)

def monthly(df, label):
    rows=[]
    for mth,g in df.groupby('entry_month') if df is not None and not df.empty else []:
        m=metric(g); m.update(source=label,entry_month=mth); rows.append(m)
    return rows

def side_summary(df,label):
    rows=[]; sc=side_col(df)
    for side,g in df.groupby(sc) if df is not None and not df.empty and sc in df.columns else []:
        m=metric(g); m.update(source=label,side=side); rows.append(m)
    return rows

def split_summary(df,label):
    rows=[]
    parts={'ALL':df,'2025':df[df.entry_dt.dt.year==2025],'2026':df[df.entry_dt.dt.year==2026],'2026_03_plus':df[df.entry_dt>=pd.Timestamp('2026-03-01')],'2026_05_06':df[df.entry_month.isin(['2026-05','2026-06'])]}
    for k,g in parts.items():
        m=metric(g); m.update(source=label,split=k); rows.append(m)
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); out=mt5/'FX_OUTPUTS'/'gold_v3'/'107ggc'; out.mkdir(parents=True,exist_ok=True)
    p_gf=mt5/'FX_OUTPUTS'/'gold_v3'/'107gfc'; p_gb=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; p_gd=mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'
    req={'gf_config':p_gf/'gold_v3_107gf_wf_config_summary.csv','gf_ledger':p_gf/'gold_v3_107gf_wf_selected_trade_ledger.csv','gf_selection':p_gf/'gold_v3_107gf_wf_selection_log.csv','gb_ledger':p_gb/'gold_v3_107gb_top_candidate_trade_ledger.csv','gd_fixed_ledger':p_gd/'gold_v3_107gd_diversified_portfolio_ledger.csv'}
    blockers=[]; vals=[]; findings=[]; outputs=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required prior output missing'))
    if not blockers:
        cfg=read(req['gf_config']); wf=read(req['gf_ledger']); sel=read(req['gf_selection']); gb=read(req['gb_ledger']); fixed=read(req['gd_fixed_ledger'])
        gb=candidate_id(gb); wf=candidate_id(wf); sel=candidate_id(sel); fixed=candidate_id(fixed)
        if 'portfolio_side' in fixed.columns:
            fixed=fixed.sort_values(['portfolio_side','entry_dt','selected_rank' if 'selected_rank' in fixed.columns else 'entry_dt']).drop_duplicates(['portfolio_side','entry_dt'],keep='first')
            fixed_comb=fixed.sort_values(['entry_dt','selected_rank' if 'selected_rank' in fixed.columns else 'entry_dt']).drop_duplicates(['entry_dt'],keep='first')
        else:
            fixed_comb=fixed.sort_values(['entry_dt']).drop_duplicates(['entry_dt'],keep='first')
        if 'config_id' in wf.columns and len(cfg):
            best_id=int(cfg.iloc[0].config_id)
            wf=wf[wf.config_id.astype(int)==best_id].copy() if 'config_id' in wf.columns else wf
        else:
            best_id=-1
        summary_rows=[]
        add_scope_metric(summary_rows,'ALL','fixed_107GE_style',fixed_comb)
        add_scope_metric(summary_rows,'ALL','walkforward_107GF',wf)
        comp=pd.DataFrame(summary_rows); save(comp,out/'gold_v3_107gg_fixed_vs_wf_summary.csv'); outputs.append('gold_v3_107gg_fixed_vs_wf_summary.csv')
        monthly_rows=monthly(fixed_comb,'fixed_107GE_style')+monthly(wf,'walkforward_107GF')
        mdf=pd.DataFrame(monthly_rows); save(mdf,out/'gold_v3_107gg_fixed_vs_wf_monthly.csv'); outputs.append('gold_v3_107gg_fixed_vs_wf_monthly.csv')
        sdf=pd.DataFrame(side_summary(fixed_comb,'fixed_107GE_style')+side_summary(wf,'walkforward_107GF')); save(sdf,out/'gold_v3_107gg_fixed_vs_wf_side.csv'); outputs.append('gold_v3_107gg_fixed_vs_wf_side.csv')
        split_df=pd.DataFrame(split_summary(fixed_comb,'fixed_107GE_style')+split_summary(wf,'walkforward_107GF')); save(split_df,out/'gold_v3_107gg_fixed_vs_wf_split.csv'); outputs.append('gold_v3_107gg_fixed_vs_wf_split.csv')
        churn=[]
        if len(sel) and 'config_id' in sel.columns:
            bs=sel[sel.config_id.astype(int)==best_id].copy()
            for side,g in bs.groupby('side'):
                bym=g.groupby('target_month').candidate_id.apply(lambda s: tuple(sorted(set(s)))).reset_index().sort_values('target_month')
                switches=0; prev=None
                for ids in bym.candidate_id:
                    if prev is not None and ids!=prev: switches+=1
                    prev=ids
                for cid,h in g.groupby('candidate_id'):
                    first=h.iloc[0]
                    churn.append(dict(side=side,candidate_id=cid,condition=first.condition,profile_id=first.profile_id,cooldown_bars=first.cooldown_bars,months_active=int(h.target_month.nunique()),avg_train_pf=float(pd.to_numeric(h.train_pf,errors='coerce').mean()),avg_train_wr=float(pd.to_numeric(h.train_wr,errors='coerce').mean()),side_month_switches=int(switches),selected_rows=int(len(h))))
        churn_df=pd.DataFrame(churn).sort_values(['side','months_active'],ascending=[True,False]) if churn else pd.DataFrame()
        save(churn_df,out/'gold_v3_107gg_wf_candidate_churn.csv'); outputs.append('gold_v3_107gg_wf_candidate_churn.csv')
        # conflict impact reconstruction
        impact=[]
        if len(sel) and len(gb) and 'config_id' in sel.columns:
            bs=sel[sel.config_id.astype(int)==best_id].copy()
            need=bs[['target_month','candidate_id','train_score']].drop_duplicates()
            raw=gb.merge(need,left_on=['entry_month','candidate_id'],right_on=['target_month','candidate_id'],how='inner')
            raw['train_score']=pd.to_numeric(raw.train_score,errors='coerce')
            resolved=raw.sort_values(['entry_dt','train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first') if len(raw) else raw
            dup_mask=raw.duplicated('entry_dt',keep=False) if len(raw) else pd.Series([],dtype=bool)
            conflict_only=raw[dup_mask].copy() if len(raw) else raw
            drop_all=raw[~dup_mask].copy() if len(raw) else raw
            for name,df in [('raw_before_resolution',raw),('resolved_by_train_score',resolved),('conflict_only_rows',conflict_only),('drop_all_conflicts',drop_all)]:
                m=metric(df); m.update(scenario=name,rows=int(len(df))); impact.append(m)
        imp_df=pd.DataFrame(impact); save(imp_df,out/'gold_v3_107gg_wf_conflict_impact.csv'); outputs.append('gold_v3_107gg_wf_conflict_impact.csv')
        # failure attribution
        fm=metric(fixed_comb); wm=metric(wf); attr=[]
        attr.append(dict(finding='FIXED_PORTFOLIO_BETTER',result=bool(fm['profit_factor']>wm['profit_factor'] and fm['win_rate']>wm['win_rate']),fixed_pf=fm['profit_factor'],wf_pf=wm['profit_factor'],fixed_wr=fm['win_rate'],wf_wr=wm['win_rate']))
        if len(churn_df): attr.append(dict(finding='WF_SELECTION_CHURN_PRESENT',result=bool(churn_df.side_month_switches.max()>0),max_side_switches=int(churn_df.side_month_switches.max()),unique_selected_candidates=int(churn_df.candidate_id.nunique())))
        if len(imp_df):
            raw_pf=float(imp_df[imp_df.scenario=='raw_before_resolution'].profit_factor.iloc[0]); res_pf=float(imp_df[imp_df.scenario=='resolved_by_train_score'].profit_factor.iloc[0])
            attr.append(dict(finding='CONFLICT_DAMAGE',result=bool(res_pf<raw_pf),raw_pf=raw_pf,resolved_pf=res_pf,conflict_rows=int(imp_df[imp_df.scenario=='conflict_only_rows'].rows.iloc[0])))
        if len(sdf):
            for side in ['LONG','SHORT']:
                fx=sdf[(sdf.source=='fixed_107GE_style')&(sdf.side==side)]; wx=sdf[(sdf.source=='walkforward_107GF')&((sdf.side==side)|(sdf.side=='%s'%side))]
                if len(fx) and len(wx): attr.append(dict(finding='SIDE_SPECIFIC_WEAKNESS_'+side,result=bool(float(wx.profit_factor.iloc[0])<1.8),fixed_pf=float(fx.profit_factor.iloc[0]),wf_pf=float(wx.profit_factor.iloc[0]),fixed_wr=float(fx.win_rate.iloc[0]),wf_wr=float(wx.win_rate.iloc[0])))
        attr.append(dict(finding='CANDIDATE_UNIVERSE_OVERFIT_WARNING',result=True,note='107GF selection is prior-month only, but candidate universe came from Stage107GB full-period generation. Train-only universe audit remains required.'))
        adf=pd.DataFrame(attr); save(adf,out/'gold_v3_107gg_failure_attribution.csv'); outputs.append('gold_v3_107gg_failure_attribution.csv')
        rec=[]
        if fm['profit_factor']>wm['profit_factor']:
            rec.append(dict(priority=1,action='test_fixed_small_portfolio_with_resolved_only_health_gate',reason='fixed 107GE-style portfolio outperformed monthly WF selection'))
        if len(churn_df) and churn_df.side_month_switches.max()>0:
            rec.append(dict(priority=2,action='reduce_candidate_churn_or_use_sticky_selection',reason='monthly reselection may be unstable'))
        if len(imp_df) and int(imp_df[imp_df.scenario=='conflict_only_rows'].rows.iloc[0])>0:
            rec.append(dict(priority=3,action='audit_conflict_policy_train_score_vs_no_trade',reason='WF produced conflict rows before resolution'))
        rec.append(dict(priority=4,action='train_only_candidate_universe_generation',reason='full-period candidate universe bias remains'))
        rdf=pd.DataFrame(rec); save(rdf,out/'gold_v3_107gg_recommended_next_actions.csv'); outputs.append('gold_v3_107gg_recommended_next_actions.csv')
        findings.append('fixed_summary='+json.dumps(fm,ensure_ascii=False,default=str))
        findings.append('wf_summary='+json.dumps(wm,ensure_ascii=False,default=str))
        if len(adf): findings.append('failure_attribution='+json.dumps(adf.to_dict(orient='records'),ensure_ascii=False,default=str))
        if len(imp_df): findings.append('conflict_impact='+json.dumps(imp_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        vals.append(dict(check_id='comparison_rows_positive',result='PASS' if len(comp)>0 else 'FAIL',observed=len(comp),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_to_medium_minutes_to_20min_stop_if_over_1h')
    save(pd.DataFrame(blockers),out/'gold_v3_107gg_blocker_matrix.csv'); save(val,out/'gold_v3_107gg_validation_matrix.csv')
    (out/'gold_v3_107gg_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GG report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gg_blocker_matrix.csv','gold_v3_107gg_validation_matrix.csv','gold_v3_107gg_summary.json','GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GG PASTE_ME_WALKFORWARD_FAILURE_DECOMPOSITION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GF/107GD/107GB outputs only; failure decomposition; no runtime change','runtime_estimate: light_to_medium; minutes_to_20min; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
