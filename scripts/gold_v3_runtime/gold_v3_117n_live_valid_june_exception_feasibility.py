#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_117N_LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY'; READY=STEP+'_READY'; BLOCKED=STEP+'_BLOCKED'
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pf(s):
    x=pd.to_numeric(s,errors='coerce').dropna(); gp=x[x>0].sum(); gl=-x[x<0].sum(); return float(gp/gl) if gl>0 else (math.inf if gp>0 else 0.0)
def met(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.entry_dt.notna()&x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(x.entry_dt.dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def keyset(df,cols): return set(map(tuple,df[cols].astype(str).fillna('').to_numpy())) if all(c in df for c in cols) else set()
def match(df,cols,ks): return df[cols].astype(str).fillna('').apply(tuple,axis=1).isin(ks) if ks and all(c in df for c in cols) else pd.Series(False,index=df.index)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/'FX_OUTPUTS'/'gold_v3'; out=root/'117n'; out.mkdir(parents=True,exist_ok=True)
    p107l=root/'107lc'/'gold_v3_107l_rehydrated_best_policy_ledger.csv'; pjune=root/'117l'/'gold_v3_117l_june_filter_detail.csv'; pbest=root/'117j'/'gold_v3_117j_shadow_107q_best_family_trade_ledger.csv'
    blocks=[]
    for n,p in [('107l',p107l),('117l_june',pjune),('117j_best',pbest)]:
        if not p.exists(): blocks.append({'blocker_id':'missing_'+n,'path':str(p)})
    cand=pd.DataFrame(); review=pd.DataFrame(); decision='BLOCKED_INPUT_INCOMPLETE'
    if not blocks:
        allr=pd.read_csv(p107l,encoding='utf-8-sig',low_memory=False); allr['entry_dt']=pd.to_datetime(allr.entry_dt,errors='coerce'); allr['score_num']=pd.to_numeric(allr.get('score'),errors='coerce')
        june=pd.read_csv(pjune,encoding='utf-8-sig',low_memory=False); june['entry_dt']=pd.to_datetime(june.entry_dt,errors='coerce'); june['score_num']=pd.to_numeric(june.get('score'),errors='coerce')
        best=pd.read_csv(pbest,encoding='utf-8-sig',low_memory=False)
        thr=float(pd.to_numeric(june.f002_threshold,errors='coerce').dropna().iloc[0]) if 'f002_threshold' in june and len(june) else float('nan')
        removed_pool=allr[allr.score_num<=thr].copy(); hist=removed_pool[removed_pool.entry_dt<pd.Timestamp('2026-06-01')].copy()
        rules=[('GLOBAL_KEY',['global_candidate_key']),('SIDE_CONDITION_PROFILE_CD',['side','condition','profile_id','cooldown_bars']),('REGIME_SOURCE_SIDE',['regime_split','source_name','side']),('REGIME_POLICY_SOURCE_SIDE',['regime_split','policy_key','source_name','side'])]
        rows=[]; ledgers=[]
        for name,cols in rules:
            ks=keyset(june,cols); hm=match(hist,cols,ks); jm=match(june,cols,ks)
            h=hist[hm].copy(); j=june[jm].copy(); r={'rule':name,'columns':'+'.join(cols),'historical_removed_rows':len(h),'june_restore_rows':len(j)}; r.update({f'hist_{k}':v for k,v in met(h).items()}); r.update({f'june_{k}':v for k,v in met(j).items()})
            r['pretrade_only']=True; r['auto_adopt_allowed']=False; r['review_gate']=bool(r['historical_removed_rows']>=10 and r['hist_win_rate']>=0.60 and r['hist_profit_factor']>=2.5 and r['hist_negative_month_count']==0 and r['june_restore_rows']>0)
            rows.append(r)
            if r['review_gate']:
                x=j[[c for c in best.columns if c in j.columns]].copy(); x['stage117n_exception_rule']=name; ledgers.append(x)
        cand=pd.DataFrame(rows).sort_values(['review_gate','hist_profit_factor','hist_win_rate','historical_removed_rows'],ascending=[False,False,False,False]); save(cand,out/'gold_v3_117n_exception_rule_candidates.csv')
        if ledgers:
            add=pd.concat(ledgers,ignore_index=True).drop_duplicates([c for c in ['entry_dt','global_candidate_key','result_usd'] if c in ledgers[0].columns])
            review=pd.concat([best,add],ignore_index=True,sort=False); save(review,out/'gold_v3_117n_best_exception_review_ledger.csv')
        if not cand.empty and bool(cand.iloc[0].review_gate): decision='PRETRADE_EXCEPTION_REVIEW_CANDIDATE_FOUND_NOT_AUTO_ADOPTED'
        else: decision='NO_PRETRADE_EXCEPTION_REVIEW_GATE_PASS_KEEP_F002_EXCLUSION'
    status=READY if not blocks else BLOCKED
    summary={'step':STEP,'status':status,'ready':status==READY,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'candidate_rows':int(len(cand)),'review_gate_count':int(cand.review_gate.sum()) if not cand.empty else 0,'best_rule':str(cand.iloc[0].rule) if not cand.empty else '','best_rule_hist_rows':int(cand.iloc[0].historical_removed_rows) if not cand.empty else 0,'best_rule_hist_wr':float(cand.iloc[0].hist_win_rate) if not cand.empty else 0.0,'best_rule_hist_pf':float(cand.iloc[0].hist_profit_factor) if not cand.empty else 0.0,'best_rule_june_rows':int(cand.iloc[0].june_restore_rows) if not cand.empty else 0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'approximate_reconstruction':False,'shadow_only':True,'no_auto_adoption':True,'blocker_count':len(blocks),'elapsed_seconds':round(time.time()-t0,2)}
    write_json(out/'gold_v3_117n_summary.json',summary|{'blockers':blocks}); save(pd.DataFrame([summary]),out/'gold_v3_117n_decision.csv')
    lines=['GOLD V3 117N PASTE_ME_LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY']+[f'{k}: {v}' for k,v in summary.items()]+['','EXCEPTION_RULE_CANDIDATES',cand.to_string(index=False) if not cand.empty else 'NO_CANDIDATES','','BLOCKERS','NO_BLOCKERS' if not blocks else json.dumps(blocks,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
