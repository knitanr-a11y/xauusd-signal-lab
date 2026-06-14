#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_117M_JUNE_RESTORE_POLICY_COMPARISON'; READY=STEP+'_READY'; BLOCKED=STEP+'_BLOCKED'
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pf(x):
    s=pd.to_numeric(x,errors='coerce').dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum(); return float(gp/gl) if gl>0 else (math.inf if gp>0 else 0.0)
def met(df):
    if df is None or df.empty or 'result_usd' not in df: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.entry_dt.notna()&x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(x.entry_dt.dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def mrow(name,df,valid=True,note=''):
    r={'policy':name,'valid_for_live':bool(valid),'note':note}; r.update(met(df));
    j=df.copy() if df is not None and not df.empty else pd.DataFrame()
    if not j.empty and 'entry_dt' in j:
        j['entry_dt']=pd.to_datetime(j.entry_dt,errors='coerce'); jj=j[(j.entry_dt>=pd.Timestamp('2026-06-01'))&(j.entry_dt<pd.Timestamp('2026-07-01'))]
    else: jj=pd.DataFrame()
    jm=met(jj); r.update({f'june_{k}':v for k,v in jm.items()}); return r
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/'FX_OUTPUTS'/'gold_v3'; out=root/'117m'; out.mkdir(parents=True,exist_ok=True)
    pbest=root/'117j'/'gold_v3_117j_shadow_107q_best_family_trade_ledger.csv'; pjune=root/'117l'/'gold_v3_117l_june_filter_detail.csv'
    blocks=[]
    for n,p in [('117j_best',pbest),('117l_june_detail',pjune)]:
        if not p.exists(): blocks.append({'blocker_id':'missing_'+n,'path':str(p)})
    comp=pd.DataFrame(); restore=pd.DataFrame(); decision='BLOCKED_INPUT_INCOMPLETE'
    if not blocks:
        best=pd.read_csv(pbest,encoding='utf-8-sig',low_memory=False); best['entry_dt']=pd.to_datetime(best.entry_dt,errors='coerce')
        june=pd.read_csv(pjune,encoding='utf-8-sig',low_memory=False); june['entry_dt']=pd.to_datetime(june.entry_dt,errors='coerce')
        common=[c for c in best.columns if c in june.columns]
        add=june[common].copy(); add['stage117m_policy_source']='RESTORE_ALL_8_JUNE_REVIEW_ONLY'
        restore=pd.concat([best,add],ignore_index=True,sort=False)
        save(restore,out/'gold_v3_117m_restore_all_8_review_ledger.csv')
        winners=june[pd.to_numeric(june.result_usd,errors='coerce')>0][common].copy()
        rows=[mrow('KEEP_F002_EXCLUSION',best,True,'current selected F002 output'),mrow('RESTORE_ALL_8_JUNE_REVIEW_ONLY',restore,False,'manual restore of all 8 removed June rows; review only'),mrow('RESTORE_WINNERS_ONLY_POSTHOC_INVALID_REFERENCE_ONLY',pd.concat([best,winners],ignore_index=True,sort=False),False,'uses known outcomes; invalid live; upper-bound reference')]
        comp=pd.DataFrame(rows); save(comp,out/'gold_v3_117m_policy_comparison.csv')
        base=comp[comp.policy.eq('KEEP_F002_EXCLUSION')].iloc[0]; rest=comp[comp.policy.eq('RESTORE_ALL_8_JUNE_REVIEW_ONLY')].iloc[0]
        if rest['june_trades']>0 and rest['june_profit_factor']>=2.0 and rest['june_win_rate']>=0.5:
            decision='RESTORE_ALL_8_IS_POSITIVE_BUT_REVIEW_ONLY_NOT_AUTO_ADOPTED'
        else:
            decision='KEEP_F002_EXCLUSION_REMAINS_PREFERRED'
    status=READY if not blocks else BLOCKED
    summary={'step':STEP,'status':status,'ready':status==READY,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'approximate_reconstruction':False,'shadow_only':True,'blocker_count':len(blocks),'elapsed_seconds':round(time.time()-t0,2)}
    if not comp.empty:
        for _,r in comp.iterrows():
            if r.policy=='RESTORE_ALL_8_JUNE_REVIEW_ONLY': summary.update({'restore_all_8_total_trades':int(r.trades),'restore_all_8_june_trades':int(r.june_trades),'restore_all_8_june_win_rate':float(r.june_win_rate),'restore_all_8_june_profit_factor':float(r.june_profit_factor),'restore_all_8_june_sum_result_usd':float(r.june_sum_result_usd)})
    write_json(out/'gold_v3_117m_summary.json',summary|{'blockers':blocks}); save(pd.DataFrame([summary]),out/'gold_v3_117m_decision.csv')
    lines=['GOLD V3 117M PASTE_ME_JUNE_RESTORE_POLICY_COMPARISON']+[f'{k}: {v}' for k,v in summary.items()]+['','POLICY_COMPARISON',comp.to_string(index=False) if not comp.empty else 'NO_COMPARISON_ROWS','','BLOCKERS','NO_BLOCKERS' if not blocks else json.dumps(blocks,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
