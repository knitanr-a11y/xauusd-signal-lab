#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_117L_JUNE_REMOVED_8_DETAIL_REVIEW'; READY=STEP+'_READY'; BLOCKED=STEP+'_BLOCKED'
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pf(s):
    x=pd.to_numeric(s,errors='coerce').dropna(); gp=x[x>0].sum(); gl=-x[x<0].sum(); return float(gp/gl) if gl>0 else (math.inf if gp>0 else 0.0)
def met(df):
    if df is None or df.empty or 'result_usd' not in df: return {'trades':0,'wins':0,'losses':0,'win_rate':0.0,'profit_factor':0.0,'sum_result_usd':0.0}
    x=pd.to_numeric(df.result_usd,errors='coerce').dropna(); n=len(x)
    return {'trades':int(n),'wins':int((x>0).sum()),'losses':int((x<0).sum()),'win_rate':float((x>0).mean()) if n else 0.0,'profit_factor':pf(x),'sum_result_usd':float(x.sum()) if n else 0.0}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/'FX_OUTPUTS'/'gold_v3'; out=root/'117l'; out.mkdir(parents=True,exist_ok=True)
    p107l=root/'107lc'/'gold_v3_107l_rehydrated_best_policy_ledger.csv'; pwin=root/'117j'/'gold_v3_117j_shadow_107q_selected_windows.csv'; pbest=root/'117j'/'gold_v3_117j_shadow_107q_best_family_trade_ledger.csv'
    blocks=[]
    for n,p in [('107l',p107l),('117j_windows',pwin),('117j_best',pbest)]:
        if not p.exists(): blocks.append({'blocker_id':'missing_'+n,'path':str(p)})
    june=pd.DataFrame(); detail=pd.DataFrame(); threshold=None; decision='BLOCKED_INPUT_INCOMPLETE'
    if not blocks:
        led=pd.read_csv(p107l,encoding='utf-8-sig',low_memory=False); led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce')
        june=led[(led.entry_dt>=pd.Timestamp('2026-06-01'))&(led.entry_dt<pd.Timestamp('2026-07-01'))].copy(); save(june,out/'gold_v3_117l_june_107l_rows.csv')
        win=pd.read_csv(pwin,encoding='utf-8-sig',low_memory=False)
        w=win[(win.family_id.astype(str)=='F002')&(pd.to_numeric(win.lookback_active_days,errors='coerce')==20)&(pd.to_numeric(win.target_active_days,errors='coerce')==5)].copy()
        for c in ['target_start','target_end']: w[c]=pd.to_datetime(w[c],errors='coerce')
        jw=w[(w.target_start<pd.Timestamp('2026-07-01'))&(w.target_end>=pd.Timestamp('2026-06-01'))].copy()
        if jw.empty: blocks.append({'blocker_id':'missing_f002_june_window'})
        else:
            threshold=float(pd.to_numeric(jw.iloc[-1].get('threshold'),errors='coerce'))
            detail=june.copy(); detail['f002_threshold']=threshold
            detail['score_num']=pd.to_numeric(detail.get('score'),errors='coerce')
            detail['filter_condition']='score <= threshold'
            detail['filter_removed']=detail.score_num<=threshold
            cols=[c for c in ['entry_dt','side','portfolio_side','score','score_num','f002_threshold','filter_condition','filter_removed','result_usd','profile_id','candidate_key','family','condition'] if c in detail.columns]
            save(detail[cols],out/'gold_v3_117l_june_filter_detail.csv')
            removed=int(detail.filter_removed.sum()); kept=int((~detail.filter_removed).sum())
            if len(detail)==0: decision='NO_JUNE_107L_ROWS'
            elif removed==len(detail): decision='ALL_JUNE_107L_ROWS_REMOVED_BY_F002_SCORE_FILTER'
            elif kept>0: decision='SOME_JUNE_107L_ROWS_SURVIVE_FILTER_REVIEW'
            else: decision='JUNE_FILTER_DIAGNOSIS_REVIEW'
    status=READY if not blocks else BLOCKED
    mm=met(june); rm=met(detail[detail.filter_removed]) if not detail.empty and 'filter_removed' in detail else met(pd.DataFrame()); km=met(detail[~detail.filter_removed]) if not detail.empty and 'filter_removed' in detail else met(pd.DataFrame())
    summary={'step':STEP,'status':status,'ready':status==READY,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'june_rows':int(len(june)),'june_min_entry_dt':str(june.entry_dt.min()) if not june.empty else '','june_max_entry_dt':str(june.entry_dt.max()) if not june.empty else '','f002_threshold':threshold,'removed_rows':int(detail.filter_removed.sum()) if not detail.empty and 'filter_removed' in detail else 0,'kept_rows':int((~detail.filter_removed).sum()) if not detail.empty and 'filter_removed' in detail else 0,'june_win_rate':mm['win_rate'],'june_profit_factor':mm['profit_factor'],'june_sum_result_usd':mm['sum_result_usd'],'removed_win_rate':rm['win_rate'],'removed_profit_factor':rm['profit_factor'],'removed_sum_result_usd':rm['sum_result_usd'],'kept_win_rate':km['win_rate'],'kept_profit_factor':km['profit_factor'],'kept_sum_result_usd':km['sum_result_usd'],'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'approximate_reconstruction':False,'blocker_count':len(blocks),'elapsed_seconds':round(time.time()-t0,2)}
    write_json(out/'gold_v3_117l_summary.json',summary|{'blockers':blocks}); save(pd.DataFrame([summary]),out/'gold_v3_117l_decision.csv')
    lines=['GOLD V3 117L PASTE_ME_JUNE_REMOVED_8_DETAIL_REVIEW']+[f'{k}: {v}' for k,v in summary.items()]+['','JUNE_FILTER_DETAIL',detail.to_string(index=False) if not detail.empty else 'NO_DETAIL_ROWS','','BLOCKERS','NO_BLOCKERS' if not blocks else json.dumps(blocks,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
