#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY"
OUT_DIR_NAME="gold_v2_25c93_non_oracle_component_selector_audit_only"
INPUT_NAMES=["25c92_summary.json","rr125_raw_signal_ledger.csv","rr125_top_ledgers.csv","gold_v2_13c_coreb_rr125_selected_top_ledgers.csv"]
SELECTORS=["single_only","smallest_count","largest_count","smallest_ge15","largest_ge15","max_unique","min_unique","latest_start","earliest_start","latest_end","earliest_end","shortest_duration","longest_duration","closest_start","closest_center","contains_top_candidate_candidate","contains_top_candidate_origin","contains_top_candidate_any"]
EXTERNAL_ACTIONS={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}

def repo_root()->Path: return Path(__file__).resolve().parents[2]
def files_root()->Path:
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs()->Path: return files_root()/"FX_OUTPUTS"
def out_dir()->Path:
    p=fx_outputs()/OUT_DIR_NAME; p.mkdir(parents=True,exist_ok=True); return p

def find_file(name:str)->Path|None:
    for c in [repo_root()/name,fx_outputs()/name]:
        if c.exists(): return c
    for base in [fx_outputs(),repo_root()]:
        if base.exists():
            found=sorted(base.rglob(name))
            if found: return found[0]
    return None

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def read_csv(p): return pd.read_csv(p) if p and p.exists() else pd.DataFrame()
def read_json(p):
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
def clean(x:Any)->Any:
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,float):
        if math.isnan(x): return None
        if math.isinf(x): return "inf" if x>0 else "-inf"
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x
def write_json(p:Path,o:dict): p.write_text(json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def inventory(paths):
    rows=[]
    for n,p in paths.items():
        r={"filename":n,"exists":bool(p and p.exists()),"path":str(p) if p else ""}
        if p and p.exists():
            r["bytes"]=p.stat().st_size; r["sha256"]=sha256_file(p)
            if p.suffix.lower()==".csv":
                r["row_count"]=len(pd.read_csv(p)); r["columns"]=";".join(pd.read_csv(p,nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)

def prep_raw(raw):
    d=raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    d["entry_dt"]=pd.to_datetime(d["entry_time"],errors="coerce")
    d["exit_dt"]=pd.to_datetime(d["exit_time"],errors="coerce")
    d["profit_num"]=pd.to_numeric(d.get("profit_r"),errors="coerce")
    for c in ["dataset","direction","origin_id","candidate_id"]:
        if c in d.columns: d[c]=d[c].astype(str).str.strip()
    return d.sort_values(["dataset","direction","entry_dt","exit_dt"]).reset_index(drop=True)

def prep_top(top):
    d=top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()
    d["entry_dt"]=pd.to_datetime(d["entry_time"],errors="coerce")
    for col in ["same_count","source_rule_count","unique_origins","profit"]:
        d[col+"_num"]=pd.to_numeric(d.get(col),errors="coerce")
    for c in ["dataset","top_direction","top_candidate_id"]:
        if c in d.columns: d[c]=d[c].astype(str).str.strip()
    return d.sort_values(["dataset","entry_dt","cluster_id"]).reset_index(drop=True)

def assign_entry_gap_15(raw):
    frames=[]; gap=pd.Timedelta(minutes=15)
    for _,g0 in raw.groupby(["dataset","direction"],dropna=False):
        g=g0.sort_values(["entry_dt","exit_dt"]).copy(); cid=-1; prev=None; ids=[]
        for _,row in g.iterrows():
            ent=row["entry_dt"]
            if cid<0 or pd.isna(ent) or (ent-prev)>gap: cid+=1
            prev=ent; ids.append(cid)
        g["recon_cluster_id"]=ids; frames.append(g)
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()

def component_table(comp):
    if comp.empty: return pd.DataFrame()
    return comp.groupby(["dataset","direction","recon_cluster_id"],dropna=False).agg(
        component_count=("entry_time","size"), component_unique_origins=("origin_id","nunique"),
        component_min_entry=("entry_dt","min"), component_max_entry=("entry_dt","max"),
        component_max_exit=("exit_dt","max"), component_profit_sum=("profit_num","sum"),
        component_profit_mean=("profit_num","mean"), candidate_ids=("candidate_id",lambda s:";".join(sorted(set(map(str,s))))),
        origin_ids=("origin_id",lambda s:";".join(sorted(set(map(str,s))))) ).reset_index()

def cov_components(ct,tr):
    c=ct[(ct["dataset"].astype(str)==str(tr["dataset"])) & (ct["direction"].astype(str)==str(tr["top_direction"]))].copy()
    if c.empty: return c
    c=c[(c["component_min_entry"]<=tr["entry_dt"]) & (c["component_max_exit"]>=tr["entry_dt"])]
    if c.empty: return c
    c["duration_min"]=(c["component_max_exit"]-c["component_min_entry"]).dt.total_seconds()/60.0
    c["dist_start"]=(c["component_min_entry"]-tr["entry_dt"]).abs().dt.total_seconds()/60.0
    center=c["component_min_entry"]+(c["component_max_exit"]-c["component_min_entry"])/2
    c["dist_center"]=(center-tr["entry_dt"]).abs().dt.total_seconds()/60.0
    tid=str(tr.get("top_candidate_id"))
    c["has_tid_cand"]=c["candidate_ids"].astype(str).str.split(";").apply(lambda x: tid in x)
    c["has_tid_orig"]=c["origin_ids"].astype(str).str.split(";").apply(lambda x: tid in x)
    return c

def pick(c,sel):
    if c.empty: return None
    d=c.copy()
    if sel=="single_only": return d.iloc[0] if len(d)==1 else None
    specs={
      "smallest_count":(["component_count","dist_center"],[True,True]),"largest_count":(["component_count","dist_center"],[False,True]),
      "max_unique":(["component_unique_origins","dist_center"],[False,True]),"min_unique":(["component_unique_origins","dist_center"],[True,True]),
      "latest_start":(["component_min_entry"],[False]),"earliest_start":(["component_min_entry"],[True]),"latest_end":(["component_max_exit"],[False]),"earliest_end":(["component_max_exit"],[True]),
      "shortest_duration":(["duration_min","dist_center"],[True,True]),"longest_duration":(["duration_min","dist_center"],[False,True]),
      "closest_start":(["dist_start","component_count"],[True,True]),"closest_center":(["dist_center","component_count"],[True,True]),
    }
    if sel=="smallest_ge15": d=d[d.component_count>=15]; key,asc=["component_count","dist_center"],[True,True]
    elif sel=="largest_ge15": d=d[d.component_count>=15]; key,asc=["component_count","dist_center"],[False,True]
    elif sel=="contains_top_candidate_candidate": d=d[d.has_tid_cand]; key,asc=["dist_center","component_count"],[True,True]
    elif sel=="contains_top_candidate_origin": d=d[d.has_tid_orig]; key,asc=["dist_center","component_count"],[True,True]
    elif sel=="contains_top_candidate_any": d=d[d.has_tid_cand|d.has_tid_orig]; key,asc=["dist_center","component_count"],[True,True]
    else: key,asc=specs.get(sel,(["dist_center"],[True]))
    if d.empty: return None
    return d.sort_values(key,ascending=asc).iloc[0]

def eval_selector(ct,top,sel):
    rows=[]
    for _,tr in top.iterrows():
        c=cov_components(ct,tr); s=pick(c,sel)
        r={"selector":sel,"dataset":tr.get("dataset"),"entry_time":tr.get("entry_time"),"cluster_id":tr.get("cluster_id"),"covering_components":len(c),"selected":s is not None,"source_same_count":tr.get("same_count_num")}
        if s is None:
            r.update({"selected_count":None,"same_count_match":False,"source_rule_count_match":False,"unique_origins_match":False,"profit_sum_match":False})
        else:
            cnt=int(s.component_count); uniq=int(s.component_unique_origins)
            r.update({"selected_count":cnt,"selected_unique_origins":uniq,"same_count_match":cnt==int(tr.same_count_num),"source_rule_count_match":cnt==int(tr.source_rule_count_num),"unique_origins_match":uniq==int(tr.unique_origins_num),"profit_sum_match":abs(float(s.component_profit_sum)-float(tr.profit_num))<=1e-6})
        rows.append(r)
    df=pd.DataFrame(rows)
    sm={"selector":sel,"top_rows":len(top),"selected_rows":int(df.selected.sum()),"same_count_exact":int(df.same_count_match.sum()),"source_rule_count_exact":int(df.source_rule_count_match.sum()),"unique_origins_exact":int(df.unique_origins_match.sum()),"profit_sum_exact":int(df.profit_sum_match.sum())}
    sm["status"]="FULL" if sm["same_count_exact"]==len(top) or sm["source_rule_count_exact"]==len(top) else "PARTIAL_OR_FAIL"
    return sm,df

def md(df,n=40):
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("").copy(); lines=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(lines)

def main():
    out=out_dir(); created=datetime.now(timezone.utc).isoformat(); paths={n:find_file(n) for n in INPUT_NAMES}
    inv=inventory(paths); s92=read_json(paths["25c92_summary.json"])
    raw=prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"])); top=prep_top(read_csv(paths["rr125_top_ledgers.csv"])); ct=component_table(assign_entry_gap_15(raw))
    summaries=[]; details=[]
    for sel in SELECTORS:
        sm,df=eval_selector(ct,top,sel); summaries.append(sm); details.append(df)
    summary_df=pd.DataFrame(summaries).sort_values(["same_count_exact","source_rule_count_exact","unique_origins_exact"],ascending=False)
    detail_df=pd.concat(details,ignore_index=True); best=summary_df.head(1).copy(); full=bool((summary_df.status=="FULL").any())
    upstream_ok=s92.get("status")=="NEARBY_COMPONENT_ORACLE_FULL_COUNT_FOUND_AUDIT_ONLY_NOT_LIVE_LOGIC"; inputs_ok=bool(inv.exists.all()) if not inv.empty else False
    status="NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED" if full else "NON_ORACLE_COMPONENT_SELECTOR_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    next_step="HUMAN_REVIEW_NON_ORACLE_SELECTOR_CANDIDATE" if full else "REPRESENTATIVE_SELECTOR_NOT_DERIVED_KEEP_HISTORICAL_ONLY_OR_NEW_POLICY"
    if not upstream_ok or not inputs_ok: status="NON_ORACLE_COMPONENT_SELECTOR_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"; next_step="REVIEW_25C93_INPUTS"
    decision=pd.DataFrame([["upstream_25c92_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],["raw_rr125_rows",len(raw),">0","PASS" if len(raw)>0 else "FAIL"],["top125_rows",len(top),125,"PASS" if len(top)==125 else "FAIL"],["full_non_oracle_selector",full,True,"PASS" if full else "BLOCKED"],["coreb_live_evaluator_allowed",False,False,"PASS"],["a002_used",False,False,"PASS"]],columns=["decision_item","observed","required","status"])
    blockers=pd.DataFrame([["B93-001","non_oracle_selector","OPEN" if not full else "REVIEW","HARD","No complete non-oracle selector found" if not full else "Candidate requires human review"],["B93-002","CoreB live evaluator","OPEN","HARD","Live remains blocked"],["B93-003","A002","CLOSED_FOR_COREB_MAIN_PATH","INFO","A002 not used"]],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"upstream_25c92_ok":upstream_ok,"inputs_ok":inputs_ok,"raw_rr125_rows":int(len(raw)),"top125_rows":int(len(top)),"component_family":"entry_gap","gap_min":15,"best_selector":str(best.iloc[0].selector) if not best.empty else None,"best_same_count_exact":int(best.iloc[0].same_count_exact) if not best.empty else 0,"best_source_rule_count_exact":int(best.iloc[0].source_rule_count_exact) if not best.empty else 0,"full_match_found":full,"coreb_historical_sot_report_allowed":True,"coreb_live_evaluator_allowed":False,"final_signal_allowed":False,"a002_used":False,"source_recovery_approved":False,"external_actions":EXTERNAL_ACTIONS,"next_recommended_step":next_step}
    inv.to_csv(out/"25c93_input_inventory.csv",index=False,encoding="utf-8-sig"); summary_df.to_csv(out/"25c93_selector_summary.csv",index=False,encoding="utf-8-sig"); detail_df.to_csv(out/"25c93_selector_rows.csv",index=False,encoding="utf-8-sig"); best.to_csv(out/"25c93_best_candidate_matrix.csv",index=False,encoding="utf-8-sig"); decision.to_csv(out/"25c93_decision_matrix.csv",index=False,encoding="utf-8-sig"); blockers.to_csv(out/"25c93_blocker_matrix.csv",index=False,encoding="utf-8-sig"); write_json(out/"25c93_summary.json",summary)
    report="\n".join(["# GOLD V2 25C93 non-oracle component selector audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Selector summary",md(summary_df),"","## Decision matrix",md(decision),"","## Blockers",md(blockers),"","## Safety","- audit_only: true","- oracle matching is not used in selector logic","- A002 not used","- source recovery not approved","- live/final/external actions remain OFF"])
    (out/"GOLD_V2_25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    zip_path=fx_outputs()/"gold_v2_25c93_non_oracle_component_selector_audit_only.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p,arcname=p.name)
    print(json.dumps({"status":status,"output_dir":str(out),"zip":str(zip_path)},ensure_ascii=False,indent=2,allow_nan=False)); print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2
if __name__=="__main__": raise SystemExit(main())
