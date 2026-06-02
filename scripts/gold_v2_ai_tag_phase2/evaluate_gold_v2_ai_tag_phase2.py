#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Iterable, List
import numpy as np, pandas as pd

def pf(vals: Iterable[float]) -> float:
    xs=[float(x) for x in vals]
    wins=sum(x for x in xs if x>0); losses=-sum(x for x in xs if x<0)
    if losses==0: return float('inf') if wins>0 else 0.0
    return wins/losses

def tags(v) -> List[str]:
    if pd.isna(v): return []
    s=str(v).strip()
    if not s: return []
    try:
        x=json.loads(s)
        if isinstance(x,list): return [str(i) for i in x]
    except Exception: pass
    return [p.strip().strip('"\'') for p in s.strip('[]').split(',') if p.strip()]

def summary(df, col, r_col):
    rows=[]
    for key,g in df.groupby(col, dropna=False):
        r=g[r_col].fillna(0).astype(float)
        rows.append({col:key,'count':len(g),'win_rate':float((r>0).mean()) if len(r) else 0,'pf':pf(r),'total_r':float(r.sum()),'avg_r':float(r.mean()) if len(r) else 0,'worst_r':float(r.min()) if len(r) else 0,'best_r':float(r.max()) if len(r) else 0})
    return pd.DataFrame(rows).sort_values(['count','total_r'], ascending=[False,False]) if rows else pd.DataFrame()

def stack_profit(row):
    sp=str(row.get('stack_permission',''))
    if sp=='BLOCK': return 0.0
    if sp in {'REPRESENTATIVE_ONLY','CAP_1'}: return row['cap1_profit_r']
    if sp=='CAP_2': return row['cap2_profit_r']
    if sp=='CAP_3': return row['cap3_profit_r']
    if sp=='ALLOW_STACKED_AUDIT_ONLY': return row['uncapped_profit_r']
    return row['cap3_profit_r']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--tags',required=True); ap.add_argument('--truth',required=True); ap.add_argument('--outdir',required=True); a=ap.parse_args()
    out=Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    tags_df=pd.read_csv(a.tags); truth=pd.read_csv(a.truth)
    df=tags_df.merge(truth,on='snapshot_id',how='left')
    df['ai_stack_profit_r']=df.apply(stack_profit, axis=1)
    df['ai_block_only_profit_r']=np.where(df['decision'].astype(str).eq('BLOCK'),0.0,df['uncapped_profit_r'])
    df.to_csv(out/'gold_v2_ai_phase2_joined_for_eval.csv', index=False, encoding='utf-8-sig')
    overall=[]
    for r_col in ['uncapped_profit_r','cap3_profit_r','cap2_profit_r','cap1_profit_r','ai_stack_profit_r','ai_block_only_profit_r']:
        overall.append({'profit_model':r_col,'count':len(df),'win_rate':float((df[r_col]>0).mean()),'pf':pf(df[r_col]),'total_r':float(df[r_col].sum()),'worst_r':float(df[r_col].min()),'best_r':float(df[r_col].max())})
    pd.DataFrame(overall).to_csv(out/'gold_v2_ai_phase2_overall_replay_summary.csv',index=False,encoding='utf-8-sig')
    for col in ['api_status','decision','stack_permission','risk_score','regime','top_direction','phase2_bucket','test_month']:
        if col in df.columns:
            summary(df,col,'uncapped_profit_r').to_csv(out/f'summary_by_{col}_uncapped.csv',index=False,encoding='utf-8-sig')
            summary(df,col,'ai_stack_profit_r').to_csv(out/f'summary_by_{col}_ai_stack.csv',index=False,encoding='utf-8-sig')
    for col in ['quality_tags','risk_tags','block_tags']:
        rows=[]
        for _,r in df.iterrows():
            for t in tags(r.get(col,'')):
                x=r.to_dict(); x['tag']=t; rows.append(x)
        ed=pd.DataFrame(rows)
        ed.to_csv(out/f'exploded_{col}.csv', index=False, encoding='utf-8-sig')
        if len(ed):
            summary(ed,'tag','uncapped_profit_r').to_csv(out/f'summary_by_{col}_uncapped.csv',index=False,encoding='utf-8-sig')
            summary(ed,'tag','ai_stack_profit_r').to_csv(out/f'summary_by_{col}_ai_stack.csv',index=False,encoding='utf-8-sig')
    print('wrote', out)
if __name__=='__main__': main()
