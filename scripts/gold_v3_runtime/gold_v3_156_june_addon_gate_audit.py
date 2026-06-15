#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_156_JUNE_ADDON_GATE_AUDIT_ONLY'
DEFAULT_CURRENT='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
    (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metric(df,result_col):
    if df.empty or result_col not in df.columns:
        return dict(rows=0,sum=0.0,pf=0.0,win_rate=0.0,neg_rows=0)
    r=pd.to_numeric(df[result_col],errors='coerce').fillna(0)
    return dict(rows=int(len(df)),sum=float(r.sum()),pf=pf(r),win_rate=float((r>0).mean()) if len(r) else 0.0,neg_rows=int((r<0).sum()))
def choose_result_col(df):
    prefs=['worst_result_usd','worst2','event_worst','result_usd','pnl_usd','profit_usd','rep_result_usd','rep2']
    for c in prefs:
        if c in df.columns: return c
    nums=[]
    for c in df.columns:
        if re.search(r'(result|profit|pnl)',c,re.I):
            s=pd.to_numeric(df[c],errors='coerce')
            if s.notna().sum()>0: nums.append(c)
    return nums[0] if nums else ''
def clean_policy_col(df):
    for c in ['policy_key','k2_policy_key','rule_key','policy','config_key']:
        if c in df.columns: return c
    return ''
def gate_rows(df, cols, max_values=20):
    rows=[]
    for c in cols:
        if c not in df.columns: continue
        vc=df[c].fillna('MISSING').astype(str).value_counts().head(max_values)
        for v,n in vc.items(): rows.append((c,v,int(n)))
    return rows
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--min-after-rows',type=int,default=3); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'156'; out.mkdir(parents=True,exist_ok=True)
    s132=readj(root/'132'/'gold_v3_132_summary.json'); s131=readj(root/'131'/'gold_v3_131_summary.json'); s155=readj(root/'155'/'gold_v3_155_summary.json')
    cur=str(s132.get('current_best_policy_key') or s131.get('current_best_policy_key') or DEFAULT_CURRENT)
    ledger=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv')
    blockers=[]
    if ledger.empty: blockers.append({'id':'missing_107k2c_ledger'})
    policy_col=clean_policy_col(ledger) if not ledger.empty else ''
    result_col=choose_result_col(ledger) if not ledger.empty else ''
    if not blockers and not policy_col: blockers.append({'id':'missing_policy_key_column'})
    if not blockers and not result_col: blockers.append({'id':'missing_result_column'})
    prog(out,0,1,'START',t0)
    policy_rank=pd.DataFrame(); gate_rank=pd.DataFrame(); selected=pd.DataFrame(); after_current_rows=0; after_all_rows=0
    if not blockers:
        x=ledger.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce') if 'entry_dt' in x.columns else pd.to_datetime(x.get('time',''),errors='coerce')
        x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        x['policy_key_norm']=x[policy_col].astype(str); x[result_col]=pd.to_numeric(x[result_col],errors='coerce').fillna(0)
        cutoff=pd.Timestamp(CUTOFF); x['after_cutoff']=x.entry_dt>=cutoff
        after=x[x.after_cutoff].copy(); before=x[~x.after_cutoff].copy(); after_all_rows=int(len(after)); after_current_rows=int((after.policy_key_norm==cur).sum())
        addon=after[after.policy_key_norm!=cur].copy(); before_addon=before[before.policy_key_norm!=cur].copy()
        pr=[]
        for pol,g in addon.groupby('policy_key_norm'):
            ma=metric(g,result_col); bp=before_addon[before_addon.policy_key_norm==pol]; mb=metric(bp,result_col)
            if ma['rows']>=args.min_after_rows:
                pr.append({'gate_type':'POLICY_ONLY','policy_key':pol,'gate_col':'','gate_value':'','after_rows':ma['rows'],'after_sum':ma['sum'],'after_pf':ma['pf'],'after_win_rate':ma['win_rate'],'after_neg_rows':ma['neg_rows'],'before_rows':mb['rows'],'before_sum':mb['sum'],'before_pf':mb['pf'],'before_win_rate':mb['win_rate'],'june_specificity':ma['rows']/(mb['rows']+1),'risk_note':'policy-only addon candidate; not final/live'})
        policy_rank=pd.DataFrame(pr)
        cat_cols=[]
        for c in ['condition','side','source_name','regime_split','portfolio_side','hour_bucket','score_quantile','score_threshold','m15_up','h1_up','h4_up','d1_up','h1_close_gt_ema20','h4_close_gt_ema20','d1_close_gt_ema20','m15_close_gt_ema20']:
            if c in x.columns: cat_cols.append(c)
        gr=[]; total=max(1,len(cat_cols)); done=0
        for c in cat_cols:
            done+=1; prog(out,done,total,f'GATE {c}',t0)
            vals=gate_rows(addon,[c],max_values=25)
            for _,v,_ in vals:
                ga=addon[addon[c].fillna('MISSING').astype(str)==str(v)].copy(); ma=metric(ga,result_col)
                if ma['rows']<args.min_after_rows: continue
                gb=before_addon[before_addon[c].fillna('MISSING').astype(str)==str(v)].copy(); mb=metric(gb,result_col)
                pols=';'.join(ga.policy_key_norm.value_counts().head(5).index.astype(str).tolist())
                gr.append({'gate_type':'CATEGORICAL','policy_key':'ANY_NON_CURRENT','gate_col':c,'gate_value':v,'top_policies':pols,'after_rows':ma['rows'],'after_sum':ma['sum'],'after_pf':ma['pf'],'after_win_rate':ma['win_rate'],'after_neg_rows':ma['neg_rows'],'before_rows':mb['rows'],'before_sum':mb['sum'],'before_pf':mb['pf'],'before_win_rate':mb['win_rate'],'june_specificity':ma['rows']/(mb['rows']+1),'risk_note':'June addon gate candidate; current best remains primary'})
                # policy + gate rows
                for pol,pg in ga.groupby('policy_key_norm'):
                    mp=metric(pg,result_col)
                    if mp['rows']<args.min_after_rows: continue
                    bp=before_addon[(before_addon.policy_key_norm==pol)&(before_addon[c].fillna('MISSING').astype(str)==str(v))]
                    mbp=metric(bp,result_col)
                    gr.append({'gate_type':'POLICY_AND_CATEGORICAL','policy_key':pol,'gate_col':c,'gate_value':v,'top_policies':pol,'after_rows':mp['rows'],'after_sum':mp['sum'],'after_pf':mp['pf'],'after_win_rate':mp['win_rate'],'after_neg_rows':mp['neg_rows'],'before_rows':mbp['rows'],'before_sum':mbp['sum'],'before_pf':mbp['pf'],'before_win_rate':mbp['win_rate'],'june_specificity':mp['rows']/(mbp['rows']+1),'risk_note':'narrower addon candidate; check overfit risk'})
        if policy_rank.empty: policy_rank=pd.DataFrame(pr)
        gate_rank=pd.concat([policy_rank,pd.DataFrame(gr)],ignore_index=True) if gr or not policy_rank.empty else pd.DataFrame()
        if not gate_rank.empty:
            gate_rank['pass_flag']=(gate_rank.after_rows>=args.min_after_rows)&(gate_rank.after_sum>0)&(gate_rank.after_pf>=1.2)&(gate_rank.after_neg_rows<=gate_rank.after_rows/2)
            gate_rank['rank_score']=gate_rank.after_sum+gate_rank.after_pf*25+gate_rank.after_win_rate*20-gate_rank.after_neg_rows*5+gate_rank.june_specificity*10
            gate_rank=gate_rank.sort_values(['pass_flag','after_sum','after_pf','after_rows'],ascending=[False,False,False,False]).reset_index(drop=True)
            selected=gate_rank[gate_rank.pass_flag].head(20).copy()
        save(policy_rank,out/'gold_v3_156_policy_only_addon_candidates.csv'); save(gate_rank,out/'gold_v3_156_june_addon_gate_ranking.csv'); save(selected,out/'gold_v3_156_selected_addon_gate_candidates.csv')
    prog(out,1,1,'DONE',t0)
    status='READY' if not blockers else 'INPUT_MISSING'
    decision='JUNE_ADDON_GATE_CANDIDATES_READY_KEEP_CURRENT_BEST_PRIMARY' if status=='READY' and not selected.empty else ('JUNE_ADDON_GATE_NO_PASS_FOUND' if status=='READY' else 'JUNE_ADDON_GATE_INPUT_MISSING')
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'current_best_preserved':True,'addon_scope':'non-current-best K2 rows after cutoff only; current best remains primary','cutoff':CUTOFF,'after_cutoff_all_rows':after_all_rows,'after_cutoff_current_best_rows':after_current_rows,'after_cutoff_non_current_rows':after_all_rows-after_current_rows,'selected_addon_candidate_count':int(len(selected)) if not selected.empty else 0,'source_155_decision':s155.get('decision',''),'progress_total_configs':1,'progress_completed_configs':1 if not blockers else 0,'progress_output':str(out/'progress.txt'),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_156_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_156_decision.csv')
    lines=['GOLD V3 156 PASTE_ME_JUNE_ADDON_GATE_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['','SELECTED_ADDON_GATE_CANDIDATES_TOP20',selected.head(20).to_string(index=False) if not selected.empty else 'NO_SELECTED_ADDON_GATE_CANDIDATES']
    lines += ['','JUNE_ADDON_GATE_RANKING_TOP80',gate_rank.head(80).to_string(index=False) if not gate_rank.empty else 'NO_GATE_RANKING']
    lines += ['','POLICY_ONLY_ADDON_CANDIDATES',policy_rank.head(60).to_string(index=False) if not policy_rank.empty else 'NO_POLICY_ONLY_ROWS']
    lines += ['','INTERPRETATION','Keep old current best as primary. Use selected addon candidates only as audit-only June/after-cutoff fallback candidates when current best has no rows. Do not treat as final/live.']
    lines += ['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
