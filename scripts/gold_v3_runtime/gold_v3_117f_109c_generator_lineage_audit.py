#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117F_109C_GENERATOR_LINEAGE_AUDIT'
READY='GOLD_V3_117F_109C_GENERATOR_LINEAGE_AUDIT_READY'
BLOCKED='GOLD_V3_117F_109C_GENERATOR_LINEAGE_AUDIT_BLOCKED'
PATTERNS=['109c','109_selected_base_policy_ledger','gold_v3_109_selected_base_policy_ledger.csv','KEEP_107Q_BASE','107Q_BASE_RESOLVED_PASS_THROUGH']
TEXT_EXT={'.py','.md','.bat','.json','.txt','.csv'}
SKIP_DIRS={'.git','__pycache__','.venv','venv','node_modules'}

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def find_repo_root(start: Path):
    c=start.resolve()
    for p in [c,*c.parents]:
        if (p/'.git').exists() or (p/'scripts'/'gold_v3_runtime').exists(): return p
    return c
def safe_read(p: Path, limit=2_000_000):
    try:
        if p.stat().st_size>limit and p.suffix.lower()!='.csv': return ''
        return p.read_text(encoding='utf-8-sig',errors='ignore')
    except Exception:
        return ''
def scan_repo(repo: Path):
    rows=[]
    roots=[repo/'scripts',repo/'docs'/'gold_v3']
    for base in roots:
        if not base.exists(): continue
        for p in base.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXT: continue
            if any(part in SKIP_DIRS for part in p.parts): continue
            txt=safe_read(p)
            if not txt: continue
            for pat in PATTERNS:
                if pat.lower() in txt.lower():
                    lines=txt.splitlines()
                    hit_lines=[]
                    for i,l in enumerate(lines,1):
                        if pat.lower() in l.lower():
                            hit_lines.append(f'{i}:{l[:220]}')
                            if len(hit_lines)>=5: break
                    rows.append({'rel_path':str(p.relative_to(repo)),'path':str(p),'pattern':pat,'hit_count':txt.lower().count(pat.lower()),'sample':' || '.join(hit_lines)})
    return pd.DataFrame(rows)
def detect_sep(path: Path):
    try:
        s=path.read_text(encoding='utf-8-sig',errors='ignore')[:4096]
        return ';' if s.count(';')>s.count(',') else ','
    except Exception:
        return ','
def find_col(cols,names):
    m={re.sub(r'[^a-z0-9]+','',str(c).lower()):c for c in cols}
    for n in names:
        if n in m: return m[n]
    for k,v in m.items():
        if any(n in k for n in names): return v
    return None
def csv_inventory(path: Path):
    rec={'file':path.name,'path':str(path),'exists':path.exists(),'size_bytes':path.stat().st_size if path.exists() else 0,'mtime':datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds') if path.exists() else '','rows':0,'cols':0,'entry_dt_col':'','min_entry_dt':'','max_entry_dt':'','error':''}
    if not path.exists(): return rec
    try:
        df=pd.read_csv(path,sep=detect_sep(path),encoding='utf-8-sig',low_memory=False)
        rec['rows']=int(len(df)); rec['cols']=int(len(df.columns))
        t=find_col(df.columns,['entrydt','entrytime','time','datetime'])
        if t:
            rec['entry_dt_col']=str(t)
            dt=pd.to_datetime(df[t],errors='coerce').dropna()
            if len(dt): rec['min_entry_dt']=str(dt.min()); rec['max_entry_dt']=str(dt.max())
    except Exception as e:
        rec['error']=str(e)
    return rec
def inventory_109c(root: Path):
    outdir=root/'109c'
    rows=[]
    if outdir.exists():
        for p in sorted(outdir.iterdir()):
            if p.is_file() and p.suffix.lower()=='.csv': rows.append(csv_inventory(p))
            elif p.is_file():
                rows.append({'file':p.name,'path':str(p),'exists':True,'size_bytes':p.stat().st_size,'mtime':datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),'rows':0,'cols':0,'entry_dt_col':'','min_entry_dt':'','max_entry_dt':'','error':''})
    return pd.DataFrame(rows)
def summary_inventory(root: Path):
    rows=[]
    for p in root.rglob('*summary*.json'):
        try:
            if any(part in {'115a','115b','115c','115d','116c','117a','117b','117c','117d','117e','117f'} for part in p.relative_to(root).parts): continue
            obj=json.loads(p.read_text(encoding='utf-8'))
            txt=json.dumps(obj,ensure_ascii=False)
            score=sum(txt.lower().count(pat.lower()) for pat in PATTERNS)
            if score or '109' in str(p.relative_to(root)):
                rows.append({'rel_path':str(p.relative_to(root)),'path':str(p),'score':score,'status':obj.get('status',''),'decision':obj.get('decision',''),'selected_option':obj.get('selected_option',''),'selected_policy_key':obj.get('selected_policy_key',''),'output_dir':obj.get('output_dir',''),'keys_sample':' | '.join(list(obj.keys())[:30])})
        except Exception as e:
            rows.append({'rel_path':str(p.relative_to(root)),'path':str(p),'score':0,'status':'','decision':'','selected_option':'','selected_policy_key':'','output_dir':'','keys_sample':'','error':str(e)})
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--repo-root',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117f'; out.mkdir(parents=True,exist_ok=True)
    repo=find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    blockers=[]
    if not root.exists(): blockers.append({'blocker_id':'missing_gold_v3_outputs','path':str(root)})
    hits=scan_repo(repo) if repo.exists() else pd.DataFrame()
    inv=inventory_109c(root) if root.exists() else pd.DataFrame()
    summ=summary_inventory(root) if root.exists() else pd.DataFrame()
    if not hits.empty: hits=hits.sort_values(['pattern','hit_count'],ascending=[True,False])
    if not summ.empty: summ=summ.sort_values(['score','rel_path'],ascending=[False,True])
    save(hits,out/'gold_v3_117f_repo_reference_hits.csv')
    save(inv,out/'gold_v3_117f_109c_output_inventory.csv')
    save(summ,out/'gold_v3_117f_summary_json_inventory.csv')
    generator_like=hits[hits['rel_path'].str.contains('109',case=False,na=False) & hits['rel_path'].str.endswith('.py',na=False)] if not hits.empty else pd.DataFrame()
    direct_writer=hits[hits['sample'].str.contains('109c',case=False,na=False) & hits['sample'].str.contains('write|save|to_csv|out =|out=',case=False,regex=True,na=False)] if not hits.empty else pd.DataFrame()
    if len(direct_writer)>0:
        decision='DIRECT_109C_WRITER_REFERENCE_FOUND'
    elif len(generator_like)>0:
        decision='109_RELATED_SCRIPT_REFERENCES_FOUND_REVIEW_REQUIRED'
    elif not summ.empty and int((summ['score']>0).sum())>0:
        decision='SUMMARY_LINEAGE_HINTS_FOUND_REVIEW_REQUIRED'
    else:
        decision='109C_GENERATOR_NOT_FOUND_IN_LOCAL_TEXT_SCAN'
    dec=pd.DataFrame([{'decision':decision,'repo_root':str(repo),'repo_hits':int(len(hits)) if not hits.empty else 0,'generator_like_hits':int(len(generator_like)) if not generator_like.empty else 0,'direct_writer_hits':int(len(direct_writer)) if not direct_writer.empty else 0,'summary_hits':int((summ['score']>0).sum()) if not summ.empty and 'score' in summ.columns else 0,'output_inventory_rows':int(len(inv)) if not inv.empty else 0}])
    save(dec,out/'gold_v3_117f_decision.csv')
    status=READY if not blockers else BLOCKED
    selected_inv=inv[inv['file'].astype(str).eq('gold_v3_109_selected_base_policy_ledger.csv')] if not inv.empty else pd.DataFrame()
    selected_max=selected_inv.iloc[0]['max_entry_dt'] if not selected_inv.empty else ''
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),repo_root=str(repo),repo_hits=int(len(hits)) if not hits.empty else 0,generator_like_hits=int(len(generator_like)) if not generator_like.empty else 0,direct_writer_hits=int(len(direct_writer)) if not direct_writer.empty else 0,summary_hits=int((summ['score']>0).sum()) if not summ.empty and 'score' in summ.columns else 0,selected_109c_max_entry_dt=str(selected_max),source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    write_json(out/'gold_v3_117f_summary.json',summary|{'blockers':blockers})
    top_hits=hits.head(30) if not hits.empty else pd.DataFrame()
    top_sum=summ.head(20) if not summ.empty else pd.DataFrame()
    lines=['GOLD V3 117F PASTE_ME_109C_GENERATOR_LINEAGE_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'repo_root: {repo}',f'repo_hits: {summary["repo_hits"]}',f'generator_like_hits: {summary["generator_like_hits"]}',f'direct_writer_hits: {summary["direct_writer_hits"]}',f'summary_hits: {summary["summary_hits"]}',f'selected_109c_max_entry_dt: {summary["selected_109c_max_entry_dt"]}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','109C_OUTPUT_INVENTORY',inv.to_string(index=False) if not inv.empty else 'NO_109C_OUTPUT_INVENTORY','','TOP_REPO_REFERENCE_HITS',top_hits.to_string(index=False) if not top_hits.empty else 'NO_REPO_REFERENCE_HITS','','TOP_SUMMARY_HINTS',top_sum.to_string(index=False) if not top_sum.empty else 'NO_SUMMARY_HINTS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
