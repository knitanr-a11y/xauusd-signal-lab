#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117C_SELECTED_LEDGER_LINEAGE_COVERAGE_AUDIT'
READY='GOLD_V3_117C_SELECTED_LEDGER_LINEAGE_COVERAGE_AUDIT_READY'
BLOCKED='GOLD_V3_117C_SELECTED_LEDGER_LINEAGE_COVERAGE_AUDIT_BLOCKED'
EXCLUDE_DIR_NAMES={'115a','115b','115c','115d','116c','117a','117b','117c'}

def norm(x): return re.sub(r'[^a-z0-9]+','',str(x).lower())
def find_col(cols,names):
    m={norm(c):c for c in cols}
    for n in names:
        if n in m: return m[n]
    for k,v in m.items():
        if any(n in k for n in names): return v
    return None
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def detect_sep(path: Path):
    try:
        s=path.read_text(encoding='utf-8-sig',errors='ignore')[:4096]
        return ';' if s.count(';')>s.count(',') else ','
    except Exception:
        return ','
def read_header(path: Path):
    return pd.read_csv(path,sep=detect_sep(path),encoding='utf-8-sig',nrows=3,low_memory=False)
def coverage_for_csv(path: Path, root: Path, june_start, july_start, selected_keys:set):
    rec={'rel_path':str(path.relative_to(root)),'path':str(path),'rows':0,'entry_dt_col':'','min_entry_dt':'','max_entry_dt':'','june_rows':0,'has_result_usd':False,'has_side':False,'has_candidate_key':False,'selected_key_overlap_count':0,'selected_key_overlap_sample':'','error':''}
    try:
        head=read_header(path)
        t=find_col(head.columns,['entrydt','entrytime','signalentrydt','time','datetime'])
        if not t:
            rec['error']='no_entry_dt_like_column'
            return rec, pd.DataFrame()
        usecols=list(head.columns)
        df=pd.read_csv(path,sep=detect_sep(path),encoding='utf-8-sig',usecols=usecols,low_memory=False)
        if t not in df.columns:
            rec['error']='entry_col_missing_after_read'
            return rec, pd.DataFrame()
        dt=pd.to_datetime(df[t],errors='coerce')
        x=pd.DataFrame({'entry_dt':dt}).dropna()
        rec['rows']=int(len(x))
        rec['entry_dt_col']=str(t)
        if not x.empty:
            rec['min_entry_dt']=str(x.entry_dt.min())
            rec['max_entry_dt']=str(x.entry_dt.max())
            rec['june_rows']=int(((x.entry_dt>=june_start)&(x.entry_dt<july_start)).sum())
        rec['has_result_usd']=find_col(df.columns,['resultusd','pnl','profit']) is not None
        rec['has_side']=find_col(df.columns,['side','portfolioside','selectedside']) is not None
        ck=find_col(df.columns,['globalcandidatekey','candidatekey','subfilterkey'])
        rec['has_candidate_key']=ck is not None
        overlap_df=pd.DataFrame()
        if ck and selected_keys:
            keys=set(df[ck].dropna().astype(str).unique())
            overlap=sorted(keys & selected_keys)
            rec['selected_key_overlap_count']=len(overlap)
            rec['selected_key_overlap_sample']=' | '.join(overlap[:5])
            if overlap:
                tmp=df[df[ck].astype(str).isin(overlap)].copy()
                tmp['_source_rel_path']=rec['rel_path']; tmp['_candidate_key_col']=ck
                overlap_df=tmp.head(1000)
        return rec, overlap_df
    except Exception as e:
        rec['error']=str(e)
        return rec, pd.DataFrame()
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117c'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]
    if not root.exists(): blockers.append({'blocker_id':'missing_gold_v3_root','path':str(root)})
    selected_path=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    selected_keys=set(); selected_max=''; selected_min=''; selected_june_rows=0
    if not selected_path.exists():
        blockers.append({'blocker_id':'missing_109c_selected_ledger','path':str(selected_path)})
    else:
        try:
            s=pd.read_csv(selected_path,encoding='utf-8-sig',low_memory=False)
            if 'entry_dt' in s.columns:
                sdt=pd.to_datetime(s['entry_dt'],errors='coerce').dropna()
                if len(sdt):
                    selected_min=str(sdt.min()); selected_max=str(sdt.max()); selected_june_rows=int(((sdt>=pd.Timestamp('2026-06-01'))&(sdt<pd.Timestamp('2026-07-01'))).sum())
            for col in ['global_candidate_key','candidate_key','subfilter_key']:
                if col in s.columns:
                    selected_keys |= set(s[col].dropna().astype(str).unique())
        except Exception as e:
            blockers.append({'blocker_id':'read_109c_selected_ledger_failed','error':str(e)})
    june_start=pd.Timestamp('2026-06-01'); july_start=pd.Timestamp('2026-07-01')
    rows=[]; overlaps=[]
    if not blockers:
        csvs=[]
        for p in root.rglob('*.csv'):
            rel=p.relative_to(root)
            if rel.parts and rel.parts[0] in EXCLUDE_DIR_NAMES: continue
            csvs.append(p)
        for p in sorted(csvs):
            rec, odf=coverage_for_csv(p,root,june_start,july_start,selected_keys)
            if rec.get('error')=='no_entry_dt_like_column':
                continue
            rows.append(rec)
            if not odf.empty: overlaps.append(odf)
    cov=pd.DataFrame(rows).sort_values(['june_rows','max_entry_dt','rows'],ascending=[False,False,False]) if rows else pd.DataFrame()
    save(cov,out/'gold_v3_117c_all_entrydt_csv_coverage.csv')
    june_capable=cov[cov['june_rows'].fillna(0).astype(int)>0].copy() if not cov.empty else pd.DataFrame()
    save(june_capable,out/'gold_v3_117c_june_capable_sources.csv')
    overlap=pd.concat(overlaps,ignore_index=True) if overlaps else pd.DataFrame()
    save(overlap,out/'gold_v3_117c_selected_key_overlap.csv')
    june_source_count=int(len(june_capable)) if not june_capable.empty else 0
    june_trade_like_count=int(june_capable[(june_capable['has_result_usd']==True) & (june_capable['has_side']==True)].shape[0]) if not june_capable.empty else 0
    june_overlap_count=int(june_capable[june_capable['selected_key_overlap_count'].fillna(0).astype(int)>0].shape[0]) if not june_capable.empty else 0
    if blockers:
        decision='BLOCKED_INPUT_INCOMPLETE'
    elif selected_june_rows>0:
        decision='SELECTED_LEDGER_HAS_JUNE_ROWS'
    elif june_overlap_count>0:
        decision='UPSTREAM_JUNE_WITH_SELECTED_KEY_OVERLAP_REGEN_CANDIDATE'
    elif june_trade_like_count>0:
        decision='UPSTREAM_TRADE_LEDGER_HAS_JUNE_BUT_NO_SELECTED_KEY_OVERLAP'
    elif june_source_count>0:
        decision='JUNE_ENTRYDT_FILES_EXIST_BUT_NOT_TRADE_LIKE'
    else:
        decision='NO_GOLD_V3_UPSTREAM_JUNE_ENTRYDT_SOURCE_FOUND'
    dec=pd.DataFrame([dict(decision=decision,selected_min_entry_dt=selected_min,selected_max_entry_dt=selected_max,selected_june_rows=selected_june_rows,june_source_file_count=june_source_count,june_trade_like_file_count=june_trade_like_count,june_selected_key_overlap_file_count=june_overlap_count,total_entrydt_csv_files=int(len(cov)) if not cov.empty else 0)])
    save(dec,out/'gold_v3_117c_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),selected_min_entry_dt=selected_min,selected_max_entry_dt=selected_max,selected_june_rows=selected_june_rows,june_source_file_count=june_source_count,june_trade_like_file_count=june_trade_like_count,june_selected_key_overlap_file_count=june_overlap_count,total_entrydt_csv_files=int(len(cov)) if not cov.empty else 0,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    write_json(out/'gold_v3_117c_summary.json',summary|{'blockers':blockers})
    top_cols=['rel_path','rows','min_entry_dt','max_entry_dt','june_rows','has_result_usd','has_side','has_candidate_key','selected_key_overlap_count','error']
    top_june=june_capable[top_cols].head(25) if not june_capable.empty else pd.DataFrame()
    lines=['GOLD V3 117C PASTE_ME_SELECTED_LEDGER_LINEAGE_COVERAGE_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'selected_min_entry_dt: {selected_min}',f'selected_max_entry_dt: {selected_max}',f'selected_june_rows: {selected_june_rows}',f'june_source_file_count: {june_source_count}',f'june_trade_like_file_count: {june_trade_like_count}',f'june_selected_key_overlap_file_count: {june_overlap_count}',f'total_entrydt_csv_files: {summary["total_entrydt_csv_files"]}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP_JUNE_CAPABLE_SOURCES',top_june.to_string(index=False) if not top_june.empty else 'NO_JUNE_CAPABLE_SOURCES','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
