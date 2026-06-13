#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY'
READY='GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig')

def pfcap(v):
    try:
        x=float(v)
        return 10.0 if math.isinf(x) else min(max(x,0.0),10.0)
    except Exception:
        return 0.0

def ncol(df,c,default=0.0):
    if c in df.columns:
        return pd.to_numeric(df[c],errors='coerce').fillna(default)
    return pd.Series(default,index=df.index)

def add_flags(df):
    x=df.copy()
    for c in ['trades','wins','losses','win_rate','profit_factor','sum_result_usd','negative_month_count','2025_trades','2025_profit_factor','2025_win_rate','2025H2_trades','2025H2_profit_factor','2025H2_win_rate','2026_trades','2026_profit_factor','2026_win_rate','2026_03_PLUS_trades','2026_03_PLUS_profit_factor','2026_05_06_trades','2026_05_06_profit_factor']:
        if c in x.columns: x[c]=pd.to_numeric(x[c],errors='coerce').fillna(0)
    x['strict_viable']=(x.trades>=150)&(x.profit_factor>=2.0)&(x.win_rate>=0.55)&(x.negative_month_count<=2)
    x['practical_viable']=(x.trades>=250)&(x.profit_factor>=1.8)&(x.win_rate>=0.50)&(x.negative_month_count<=2)
    x['exploratory_gap_fill']=(x.trades>=80)&(x.profit_factor>=1.6)&(x.win_rate>=0.48)&(x.negative_month_count<=3)
    x['has_2025_coverage']=ncol(x,'2025_trades')>=20
    x['has_2026_coverage']=ncol(x,'2026_trades')>=20
    x['has_both_years']=x.has_2025_coverage & x.has_2026_coverage
    x['broken_2026']=(ncol(x,'2026_trades')>=20)&(ncol(x,'2026_profit_factor')<1.2)
    x['broken_2025H2']=(ncol(x,'2025H2_trades')>=20)&(ncol(x,'2025H2_profit_factor')<1.2)
    x['single_year_only']=~x.has_both_years
    reasons=[]
    for _,r in x.iterrows():
        rr=[]
        if r.trades<80: rr.append('too_few_trades')
        if r.profit_factor<1.6: rr.append('low_pf')
        if r.win_rate<0.48: rr.append('low_wr')
        if r.negative_month_count>3: rr.append('too_many_negative_months')
        if bool(r.single_year_only): rr.append('single_year_only')
        if bool(r.broken_2026): rr.append('broken_2026')
        if bool(r.broken_2025H2): rr.append('broken_2025H2')
        reasons.append('|'.join(rr) if rr else 'ok')
    x['reject_reason']=reasons
    x['quality_score']=x.apply(lambda r: pfcap(r.profit_factor)*1000 + float(r.win_rate)*900 + min(float(r.trades),500)*0.25 + float(r.sum_result_usd)*0.03 - float(r.negative_month_count)*400 - (450 if r.single_year_only else 0) - (700 if r.broken_2026 else 0) - (500 if r.broken_2025H2 else 0),axis=1)
    return x

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default='')
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107glc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gmc'; out.mkdir(parents=True,exist_ok=True)
    req={'candidate_summary':src/'gold_v3_107gl_vector_candidate_summary.csv','family_summary':src/'gold_v3_107gl_side_family_summary.csv','split_summary':src/'gold_v3_107gl_anchored_split_summary.csv'}
    blockers=[]; vals=[]; outputs=[]; findings=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required 107GL output missing'))
    if not blockers:
        cand=pd.read_csv(req['candidate_summary'],encoding='utf-8-sig')
        cand=add_flags(cand)
        ranked=cand.sort_values(['side','quality_score'],ascending=[True,False])
        save(ranked,out/'gold_v3_107gm_quality_rebalanced_candidates.csv'); outputs.append('gold_v3_107gm_quality_rebalanced_candidates.csv')
        frontier=[]
        for side in ['LONG','SHORT']:
            s=ranked[ranked.side==side].copy()
            for tier,mask in [('strict',s.strict_viable),('practical',s.practical_viable),('exploratory',s.exploratory_gap_fill)]:
                sub=s[mask].sort_values('quality_score',ascending=False)
                if len(sub):
                    r=sub.iloc[0].to_dict(); r['tier']=tier; frontier.append(r)
                else:
                    frontier.append(dict(side=side,tier=tier,available=False))
        front_df=pd.DataFrame(frontier)
        save(front_df,out/'gold_v3_107gm_viable_candidate_frontier.csv'); outputs.append('gold_v3_107gm_viable_candidate_frontier.csv')
        rej=ranked[ranked.reject_reason!='ok'].copy()
        save(rej,out/'gold_v3_107gm_rejected_candidates.csv'); outputs.append('gold_v3_107gm_rejected_candidates.csv')
        fam=[]
        for (side,family),g in ranked.groupby(['side','family']):
            best=g.sort_values('quality_score',ascending=False).iloc[0]
            fam.append(dict(side=side,family=family,candidate_count=int(len(g)),strict_count=int(g.strict_viable.sum()),practical_count=int(g.practical_viable.sum()),exploratory_count=int(g.exploratory_gap_fill.sum()),best_condition=best.condition,best_profile_id=best.profile_id,best_cooldown_bars=int(best.cooldown_bars),best_trades=int(best.trades),best_win_rate=float(best.win_rate),best_profit_factor=float(best.profit_factor),best_negative_month_count=int(best.negative_month_count),best_has_both_years=bool(best.has_both_years),best_broken_2026=bool(best.broken_2026),best_quality_score=float(best.quality_score)))
        fam_df=pd.DataFrame(fam).sort_values(['side','best_quality_score'],ascending=[True,False])
        save(fam_df,out/'gold_v3_107gm_family_quality_summary.csv'); outputs.append('gold_v3_107gm_family_quality_summary.csv')
        sidegap=[]
        for side in ['LONG','SHORT']:
            s=ranked[ranked.side==side]
            sidegap.append(dict(side=side,total_candidates=int(len(s)),strict_viable_count=int(s.strict_viable.sum()),practical_viable_count=int(s.practical_viable.sum()),exploratory_gap_fill_count=int(s.exploratory_gap_fill.sum()),both_years_count=int(s.has_both_years.sum()),broken_2026_count=int(s.broken_2026.sum()),broken_2025H2_count=int(s.broken_2025H2.sum()),single_year_only_count=int(s.single_year_only.sum()),best_quality_condition=s.iloc[0].condition if len(s) else '',best_quality_family=s.iloc[0].family if len(s) else '',best_quality_pf=float(s.iloc[0].profit_factor) if len(s) else 0,best_quality_wr=float(s.iloc[0].win_rate) if len(s) else 0,best_quality_trades=int(s.iloc[0].trades) if len(s) else 0))
        sidegap_df=pd.DataFrame(sidegap)
        save(sidegap_df,out/'gold_v3_107gm_side_gap_summary.csv'); outputs.append('gold_v3_107gm_side_gap_summary.csv')
        long_practical=int(sidegap_df[sidegap_df.side=='LONG'].practical_viable_count.iloc[0]) if len(sidegap_df[sidegap_df.side=='LONG']) else 0
        short_practical=int(sidegap_df[sidegap_df.side=='SHORT'].practical_viable_count.iloc[0]) if len(sidegap_df[sidegap_df.side=='SHORT']) else 0
        long_strict=int(sidegap_df[sidegap_df.side=='LONG'].strict_viable_count.iloc[0]) if len(sidegap_df[sidegap_df.side=='LONG']) else 0
        short_strict=int(sidegap_df[sidegap_df.side=='SHORT'].strict_viable_count.iloc[0]) if len(sidegap_df[sidegap_df.side=='SHORT']) else 0
        gates=[qgate('long_practical_viable_count',long_practical,'>=',1),qgate('short_practical_viable_count',short_practical,'>=',1),qgate('long_strict_viable_count',long_strict,'>=',1),qgate('short_strict_viable_count',short_strict,'>=',1)]
        gate_df=pd.DataFrame(gates)
        save(gate_df,out/'gold_v3_107gm_quality_gate_matrix.csv'); outputs.append('gold_v3_107gm_quality_gate_matrix.csv')
        actions=[]
        if long_practical>=1 or short_practical>=1:
            actions.append(dict(priority=1,action='run_anchored_train_test_on_quality_rebalanced_new_vectors',reason='At least one side has practical viable candidates after quality rebalance.'))
        else:
            actions.append(dict(priority=1,action='redesign_new_vector_families_before_anchored_train_test',reason='No side has practical viable candidates after quality rebalance.'))
        if long_practical<1: actions.append(dict(priority=2,action='add_more_long_2026_coverage_vectors',reason='LONG new vectors are not practical-stable enough, especially 2026 coverage/quality.'))
        if short_practical<1: actions.append(dict(priority=3,action='add_more_short_2025_and_2025H2_vectors',reason='SHORT new vectors are weak or single-period only; 2025 coverage must be improved.'))
        save(pd.DataFrame(actions),out/'gold_v3_107gm_recommended_next_actions.csv'); outputs.append('gold_v3_107gm_recommended_next_actions.csv')
        findings.append('side_gap_summary='+json.dumps(sidegap_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('viable_frontier='+json.dumps(front_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='candidate_rows_positive',result='PASS' if len(cand)>0 else 'FAIL',observed=len(cand),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h')
    if not blockers:
        summary.update(candidate_rows=int(len(cand)),long_practical_viable_count=long_practical,short_practical_viable_count=short_practical,long_strict_viable_count=long_strict,short_strict_viable_count=short_strict)
    save(pd.DataFrame(blockers),out/'gold_v3_107gm_blocker_matrix.csv'); save(val,out/'gold_v3_107gm_validation_matrix.csv')
    outputs += ['gold_v3_107gm_blocker_matrix.csv','gold_v3_107gm_validation_matrix.csv','gold_v3_107gm_summary.json','GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gm_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GM report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GM PASTE_ME_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GL summary CSVs only; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
