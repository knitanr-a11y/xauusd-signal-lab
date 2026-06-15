#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_148_VOLUME_REVIEW_AUDIT_ONLY'

def load(p):
    return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'148'; out.mkdir(parents=True,exist_ok=True); prog(out,0,1,'START',t0)
    rank=load(root/'147'/'gold_v3_147_hour_filter_ranking.csv'); mon=load(root/'147'/'gold_v3_147_hour_filter_monthly_all.csv'); notes=[]
    if rank.empty: notes.append('missing_147_ranking')
    review=pd.DataFrame(); selm=pd.DataFrame()
    if not rank.empty:
        x=rank.copy()
        for c in ['events','champion','challenger','removed','worst_sum','worst_pf','neg_months','june_events','june_challenger','june_worst']:
            x[c]=pd.to_numeric(x[c],errors='coerce').fillna(0)
        base=x[x.rule_name.astype(str)=='BASE'].head(1)
        base_worst=float(base.iloc[0].worst_sum) if not base.empty else 0.0
        x['volume_band']=pd.cut(x.events,bins=[0,90,110,120,9999],labels=['under90','90_109','110_119','120plus'])
        x['keeps_june']=x.june_events>=4
        x['better_than_base']=x.worst_sum>=base_worst
        x['quality_first_score']=x.worst_sum+x.worst_pf*100-x.neg_months*500+x.june_worst-x.removed*0.2
        review=x.sort_values(['neg_months','worst_sum','events'],ascending=[True,False,False]).reset_index(drop=True)
        key=str(review.iloc[0].rule_name) if not review.empty else ''
        if not mon.empty and key:
            selm=mon[mon.rule_name.astype(str)==key].copy()
    save(review,out/'gold_v3_148_volume_review.csv'); save(selm,out/'gold_v3_148_selected_monthly.csv')
    selected=review.head(1) if not review.empty else pd.DataFrame(); prog(out,1,1,'DONE',t0)
    summary={'step':STEP,'status':'READY' if not notes else 'INPUT_MISSING','ready':not notes,'decision':'VOLUME_REVIEW_READY','created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'selected_rule_name':str(selected.iloc[0].rule_name) if not selected.empty else '','selected_events':int(selected.iloc[0].events) if not selected.empty else 0,'selected_challenger_events':int(selected.iloc[0].challenger) if not selected.empty else 0,'selected_worst_sum':float(selected.iloc[0].worst_sum) if not selected.empty else 0.0,'selected_worst_pf':float(selected.iloc[0].worst_pf) if not selected.empty else 0.0,'selected_negative_months':int(selected.iloc[0].neg_months) if not selected.empty else 0,'selected_june_worst':float(selected.iloc[0].june_worst) if not selected.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'notes':notes,'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_148_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_148_decision.csv')
    lines=['GOLD V3 148 PASTE_ME_VOLUME_REVIEW_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','VOLUME_REVIEW',review.to_string(index=False) if not review.empty else 'NO_ROWS','','SELECTED_MONTHLY',selm.to_string(index=False) if not selm.empty else 'NO_MONTHLY']
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not notes,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not notes else 2
if __name__=='__main__': raise SystemExit(main())
