#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117D_UPSTREAM_JUNE_REGEN_CANDIDATE_AUDIT'
READY='GOLD_V3_117D_UPSTREAM_JUNE_REGEN_CANDIDATE_AUDIT_READY'
BLOCKED='GOLD_V3_117D_UPSTREAM_JUNE_REGEN_CANDIDATE_AUDIT_BLOCKED'
KEY_CANDIDATES=['global_candidate_key','candidate_key','subfilter_key']

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
def detect_sep(p:Path):
    try:
        s=p.read_text(encoding='utf-8-sig',errors='ignore')[:4096]
        return ';' if s.count(';')>s.count(',') else ','
    except Exception:
        return ','
def read_header(p:Path): return pd.read_csv(p,sep=detect_sep(p),encoding='utf-8-sig',nrows=3,low_memory=False)
def make_selected_keys(sel: pd.DataFrame):
    keys=set()
    for c in KEY_CANDIDATES:
        if c in sel.columns:
            keys |= set(sel[c].dropna().astype(str).unique())
    return keys
def pf(s):
    r=pd.to_numeric(s,errors='coerce').dropna().to_numpy(dtype=float)
    gp=r[r>0].sum(); gl=-r[r<0].sum()
    if gl>0: return float(gp/gl)
    if gp>0: return math.inf
    return 0.0
def metrics(df):
    if df is None or df.empty or 'result_usd' not in df.columns:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0)
    r=pd.to_numeric(df['result_usd'],errors='coerce').dropna()
    if r.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0)
    return dict(trades=int(len(r)),wins=int((r>0).sum()),losses=int((r<0).sum()),win_rate=float((r>0).mean()),profit_factor=pf(r),sum_result_usd=float(r.sum()))
def normalize_columns(df: pd.DataFrame, entry_col, key_col, side_col, result_col):
    out=df.copy()
    out['entry_dt']=pd.to_datetime(out[entry_col],errors='coerce')
    out['match_key']=out[key_col].astype(str)
    if side_col: out['side']=out[side_col].astype(str)
    elif 'side' not in out.columns: out['side']=''
    if result_col: out['result_usd']=pd.to_numeric(out[result_col],errors='coerce')
    elif 'result_usd' not in out.columns: out['result_usd']=0.0
    return out[out['entry_dt'].notna()].copy()
def extract_source(path: Path, selected_keys:set, start:pd.Timestamp, end:pd.Timestamp, chunksize:int):
    head=read_header(path)
    entry_col=find_col(head.columns,['entrydt','entrytime','signalentrydt'])
    if not entry_col:
        entry_col=find_col(head.columns,['time','datetime'])
    key_col=None
    for names in [['globalcandidatekey'],['candidatekey'],['subfilterkey']]:
        key_col=find_col(head.columns,names)
        if key_col: break
    side_col=find_col(head.columns,['side','portfolioside','selectedside'])
    result_col=find_col(head.columns,['resultusd','pnl','profit'])
    if not entry_col or not key_col:
        return pd.DataFrame(), {'error':'missing_entry_or_key_column','entry_col':entry_col or '', 'key_col':key_col or ''}
    parts=[]; total=0; matched=0
    sep=detect_sep(path)
    for chunk in pd.read_csv(path,sep=sep,encoding='utf-8-sig',low_memory=False,chunksize=chunksize):
        total += len(chunk)
        if key_col not in chunk.columns or entry_col not in chunk.columns: continue
        m=chunk[chunk[key_col].astype(str).isin(selected_keys)].copy()
        if m.empty: continue
        x=normalize_columns(m,entry_col,key_col,side_col,result_col)
        x=x[(x.entry_dt>=start)&(x.entry_dt<end)].copy()
        if x.empty: continue
        matched += len(x)
        parts.append(x)
    out=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    return out, {'error':'','entry_col':entry_col,'key_col':key_col,'side_col':side_col or '', 'result_col':result_col or '', 'total_read_rows':total,'matched_period_rows':matched}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--max-sources',type=int,default=8); ap.add_argument('--chunksize',type=int,default=250000); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117d'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]
    sel_path=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    src_path=root/'117c'/'gold_v3_117c_june_capable_sources.csv'
    if not sel_path.exists(): blockers.append({'blocker_id':'missing_selected_ledger','path':str(sel_path)})
    if not src_path.exists(): blockers.append({'blocker_id':'missing_117c_june_capable_sources','path':str(src_path)})
    parity_rows=[]; ext_parts=[]
    if not blockers:
        sel=pd.read_csv(sel_path,encoding='utf-8-sig',low_memory=False)
        if 'entry_dt' not in sel.columns: blockers.append({'blocker_id':'selected_missing_entry_dt'})
        else:
            sel['entry_dt']=pd.to_datetime(sel['entry_dt'],errors='coerce')
            sel=sel[sel.entry_dt.notna()].copy()
        selected_keys=make_selected_keys(sel)
        if not selected_keys: blockers.append({'blocker_id':'selected_keys_empty'})
    if not blockers:
        sources=pd.read_csv(src_path,encoding='utf-8-sig',low_memory=False)
        sources=sources[(pd.to_numeric(sources.get('selected_key_overlap_count',0),errors='coerce').fillna(0)>0) & (sources.get('has_result_usd',False).astype(str).str.lower().isin(['true','1'])) & (sources.get('has_side',False).astype(str).str.lower().isin(['true','1']))].copy()
        sources=sources.sort_values(['selected_key_overlap_count','june_rows','rows'],ascending=[False,False,False]).head(args.max_sources)
        may_start=pd.Timestamp('2026-05-01'); june_start=pd.Timestamp('2026-06-01'); july_start=pd.Timestamp('2026-07-01')
        sel_may=sel[(sel.entry_dt>=may_start)&(sel.entry_dt<june_start)].copy()
        sel_may_entries=set(sel_may.entry_dt.dt.strftime('%Y-%m-%d %H:%M:%S'))
        for _,srow in sources.iterrows():
            p=Path(str(srow.path))
            rec={'rel_path':str(srow.rel_path),'path':str(p),'source_selected_key_overlap_count':int(float(srow.selected_key_overlap_count)),'source_june_rows':int(float(srow.june_rows))}
            may,info_m=extract_source(p,selected_keys,may_start,june_start,args.chunksize)
            june,info_j=extract_source(p,selected_keys,june_start,july_start,args.chunksize)
            rec.update({f'may_{k}':v for k,v in info_m.items()})
            rec.update({'projected_may_rows':int(len(may)),'projected_june_rows':int(len(june))})
            if not may.empty:
                may_entries=set(may.entry_dt.dt.strftime('%Y-%m-%d %H:%M:%S'))
                common=len(sel_may_entries & may_entries)
                rec['selected_may_rows']=int(len(sel_may))
                rec['selected_may_entry_overlap']=common
                rec['selected_may_entry_recall']=float(common/max(1,len(sel_may_entries)))
                rec['projected_extra_may_entries']=int(len(may_entries-sel_may_entries))
                rec['projected_may_unique_entries']=int(len(may_entries))
            else:
                rec['selected_may_rows']=int(len(sel_may)); rec['selected_may_entry_overlap']=0; rec['selected_may_entry_recall']=0.0; rec['projected_extra_may_entries']=0; rec['projected_may_unique_entries']=0
            rec.update({f'june_{k}':v for k,v in metrics(june).items()})
            rec['passes_recall_gate']=bool(rec['selected_may_entry_recall']>=0.95)
            rec['passes_june_presence_gate']=bool(len(june)>0)
            parity_rows.append(rec)
            if not june.empty:
                june=june.copy(); june['_source_rel_path']=rec['rel_path']; june['_source_key_col']=info_j.get('key_col','')
                ext_parts.append(june)
    parity=pd.DataFrame(parity_rows)
    if not parity.empty:
        parity=parity.sort_values(['passes_recall_gate','selected_may_entry_recall','projected_june_rows'],ascending=[False,False,False])
    save(parity,out/'gold_v3_117d_source_parity_matrix.csv')
    ext=pd.concat(ext_parts,ignore_index=True) if ext_parts else pd.DataFrame()
    if not ext.empty:
        ext=ext.sort_values(['entry_dt']).drop_duplicates(['entry_dt','match_key','side'],keep='first')
    save(ext,out/'gold_v3_117d_june_extension_candidates.csv')
    pass_sources=int(parity['passes_recall_gate'].sum()) if not parity.empty else 0
    june_candidate_rows=int(len(ext))
    if blockers: decision='BLOCKED_INPUT_INCOMPLETE'
    elif pass_sources>0 and june_candidate_rows>0: decision='REGEN_CANDIDATE_READY_REVIEW_REQUIRED'
    elif june_candidate_rows>0: decision='JUNE_ROWS_EXTRACTED_BUT_MAY_PARITY_WEAK'
    else: decision='NO_JUNE_EXTENSION_ROWS_EXTRACTED'
    dec=pd.DataFrame([dict(decision=decision,pass_sources=pass_sources,june_candidate_rows=june_candidate_rows,sources_reviewed=int(len(parity)) if not parity.empty else 0)])
    save(dec,out/'gold_v3_117d_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),sources_reviewed=int(len(parity)) if not parity.empty else 0,pass_sources=pass_sources,june_candidate_rows=june_candidate_rows,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    write_json(out/'gold_v3_117d_summary.json',summary|{'blockers':blockers})
    view_cols=['rel_path','projected_may_rows','selected_may_rows','selected_may_entry_overlap','selected_may_entry_recall','projected_extra_may_entries','projected_june_rows','june_trades','june_win_rate','june_profit_factor','june_sum_result_usd','passes_recall_gate']
    top=parity[view_cols].head(10) if not parity.empty else pd.DataFrame()
    lines=['GOLD V3 117D PASTE_ME_UPSTREAM_JUNE_REGEN_CANDIDATE_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'sources_reviewed: {summary["sources_reviewed"]}',f'pass_sources: {pass_sources}',f'june_candidate_rows: {june_candidate_rows}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP_PARITY_SOURCES',top.to_string(index=False) if not top.empty else 'NO_PARITY_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
