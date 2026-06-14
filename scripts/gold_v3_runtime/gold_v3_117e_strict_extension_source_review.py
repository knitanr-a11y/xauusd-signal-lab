#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_117d_upstream_june_regen_candidate_audit as d117

STEP='GOLD_V3_117E_STRICT_EXTENSION_SOURCE_REVIEW'
READY='GOLD_V3_117E_STRICT_EXTENSION_SOURCE_REVIEW_READY'
BLOCKED='GOLD_V3_117E_STRICT_EXTENSION_SOURCE_REVIEW_BLOCKED'

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pf_to_float(x):
    try:
        if str(x).lower()=='inf': return math.inf
        return float(x)
    except Exception:
        return 0.0
def norm_path(s): return str(s).replace('\\','/').strip().lower()
def load_selected_keys(root):
    p=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    if not p.exists(): return set()
    sel=pd.read_csv(p,encoding='utf-8-sig',low_memory=False)
    return d117.make_selected_keys(sel)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--chunksize',type=int,default=250000); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117e'; out.mkdir(parents=True,exist_ok=True)
    parity_path=root/'117d'/'gold_v3_117d_source_parity_matrix.csv'
    ext_path=root/'117d'/'gold_v3_117d_june_extension_candidates.csv'
    blockers=[]
    if not parity_path.exists(): blockers.append({'blocker_id':'missing_117d_parity_matrix','path':str(parity_path)})
    if not ext_path.exists(): blockers.append({'blocker_id':'missing_117d_extension_candidates','path':str(ext_path)})
    rank=pd.DataFrame(); review_ext=pd.DataFrame(); best={}; decision=''; extraction_note=''
    if not blockers:
        rank=pd.read_csv(parity_path,encoding='utf-8-sig',low_memory=False)
        if rank.empty:
            blockers.append({'blocker_id':'empty_117d_parity_matrix'})
    if not blockers:
        for c in ['selected_may_entry_overlap','projected_extra_may_entries','projected_may_unique_entries','projected_june_rows','selected_may_entry_recall','june_win_rate','june_profit_factor','june_sum_result_usd']:
            if c not in rank.columns: rank[c]=0
            rank[c]=pd.to_numeric(rank[c],errors='coerce').fillna(0)
        rank['selected_may_entry_precision']=rank['selected_may_entry_overlap']/(rank['selected_may_entry_overlap']+rank['projected_extra_may_entries']).replace(0,1)
        rank['extra_per_selected_row']=rank['projected_extra_may_entries']/pd.to_numeric(rank.get('selected_may_rows',0),errors='coerce').replace(0,1)
        rank['strict_auto_gate']=(rank['selected_may_entry_recall']>=0.999)&(rank['selected_may_entry_precision']>=0.95)&(rank['projected_extra_may_entries']<=0)&(rank['projected_june_rows']>0)
        rank['review_gate']=(rank['selected_may_entry_recall']>=0.999)&(rank['projected_extra_may_entries']<=5)&(rank['projected_june_rows']>0)
        rank['volume_reject_hint']=(rank['projected_extra_may_entries']>50)|(rank['projected_june_rows']>100)
        rank['strict_review_score']=rank['selected_may_entry_recall']*10000+rank['selected_may_entry_precision']*5000-rank['projected_extra_may_entries']*20-rank['projected_june_rows']*0.5+rank['june_sum_result_usd']*0.01
        rank=rank.sort_values(['strict_auto_gate','review_gate','strict_review_score','selected_may_entry_precision'],ascending=[False,False,False,False])
        save(rank,out/'gold_v3_117e_strict_source_ranking.csv')
        if rank['strict_auto_gate'].any():
            decision='STRICT_AUTO_EXTENSION_SOURCE_FOUND_BUT_REVIEW_REQUIRED'
            best=rank[rank.strict_auto_gate].iloc[0].to_dict()
        elif rank['review_gate'].any():
            decision='NO_STRICT_AUTO_SOURCE_REVIEW_CANDIDATE_ONLY'
            best=rank[rank.review_gate].iloc[0].to_dict()
        else:
            decision='NO_ACCEPTABLE_EXTENSION_SOURCE'
            best=rank.iloc[0].to_dict() if not rank.empty else {}
        if best and ext_path.exists():
            ext=pd.read_csv(ext_path,encoding='utf-8-sig',low_memory=False)
            src=str(best.get('rel_path',''))
            if '_source_rel_path' in ext.columns and src:
                srcn=norm_path(src)
                review_ext=ext[ext['_source_rel_path'].astype(str).map(norm_path)==srcn].copy()
                extraction_note='from_117d_extension_candidates_exact_source_path'
            if review_ext.empty and best.get('path'):
                selected_keys=load_selected_keys(root)
                p=Path(str(best.get('path')))
                if p.exists() and selected_keys:
                    june,info=d117.extract_source(p,selected_keys,pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01'),args.chunksize)
                    if not june.empty:
                        june=june.copy(); june['_source_rel_path']=src; june['_source_key_col']=info.get('key_col',''); june['_extraction_note']='direct_best_source_reextract'
                        review_ext=june
                        extraction_note='direct_best_source_reextract'
                    else:
                        extraction_note='direct_best_source_reextract_empty'
                else:
                    extraction_note='direct_best_source_reextract_blocked_missing_path_or_keys'
            save(review_ext,out/'gold_v3_117e_review_extension_candidates.csv')
    status=READY if not blockers else BLOCKED
    review_rows=int(len(review_ext)) if not review_ext.empty else 0
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision or ('BLOCKED_INPUT_INCOMPLETE' if blockers else ''),created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),best_rel_path=str(best.get('rel_path','')) if best else '',best_recall=float(best.get('selected_may_entry_recall',0)) if best else 0.0,best_precision=float(best.get('selected_may_entry_precision',0)) if best else 0.0,best_extra_may_entries=int(float(best.get('projected_extra_may_entries',0))) if best else 0,best_projected_june_rows=int(float(best.get('projected_june_rows',0))) if best else 0,review_extension_rows=review_rows,extraction_note=extraction_note,strict_auto_gate_count=int(rank['strict_auto_gate'].sum()) if not rank.empty and 'strict_auto_gate' in rank.columns else 0,review_gate_count=int(rank['review_gate'].sum()) if not rank.empty and 'review_gate' in rank.columns else 0,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    write_json(out/'gold_v3_117e_summary.json',summary|{'blockers':blockers})
    dec=pd.DataFrame([summary])
    save(dec,out/'gold_v3_117e_decision.csv')
    view_cols=['rel_path','selected_may_entry_recall','selected_may_entry_precision','projected_extra_may_entries','projected_june_rows','june_win_rate','june_profit_factor','june_sum_result_usd','strict_auto_gate','review_gate','volume_reject_hint']
    top=rank[view_cols].head(10) if not rank.empty else pd.DataFrame()
    lines=['GOLD V3 117E PASTE_ME_STRICT_EXTENSION_SOURCE_REVIEW',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {summary["decision"]}',f'best_rel_path: {summary["best_rel_path"]}',f'best_recall: {summary["best_recall"]}',f'best_precision: {summary["best_precision"]}',f'best_extra_may_entries: {summary["best_extra_may_entries"]}',f'best_projected_june_rows: {summary["best_projected_june_rows"]}',f'review_extension_rows: {review_rows}',f'extraction_note: {extraction_note}',f'strict_auto_gate_count: {summary["strict_auto_gate_count"]}',f'review_gate_count: {summary["review_gate_count"]}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP_STRICT_SOURCE_RANKING',top.to_string(index=False) if not top.empty else 'NO_RANKING_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':summary['decision'],'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
