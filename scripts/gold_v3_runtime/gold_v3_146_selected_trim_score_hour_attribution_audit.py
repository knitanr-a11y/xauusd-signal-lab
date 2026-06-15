#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP="GOLD_V3_146_SELECTED_TRIM_SCORE_HOUR_ATTRIBUTION_AUDIT_ONLY"
READY=STEP+"_READY"; BLOCKED=STEP+"_BLOCKED"

def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")

def load(p):
    return pd.read_csv(p,encoding="utf-8-sig",low_memory=False) if p.exists() else pd.DataFrame()

def readj(p):
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception: return {}

def pf(vals):
    a=pd.to_numeric(pd.Series(vals),errors="coerce").dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def prog(out,done,total,label,t0):
    pct=done/total*100 if total else 100
    msg=f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {label} elapsed={time.time()-t0:.1f}s"
    print(msg,flush=True)
    (out/"progress.txt").write_text(msg+"\n",encoding="utf-8")
    (out/"progress.json").write_text(json.dumps({"done":done,"total":total,"percent":pct,"label":label,"elapsed_seconds":round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding="utf-8")

def bucket_hour(h):
    try: h=int(h)
    except Exception: return "unknown"
    if h<6: return "00_05"
    if h<12: return "06_11"
    if h<18: return "12_17"
    return "18_23"

def qbucket(s):
    x=pd.to_numeric(s,errors="coerce")
    if x.notna().sum()<5: return pd.Series(["unknown"]*len(s),index=s.index)
    try:
        return pd.qcut(x.rank(method="first"),4,labels=["Q1_low","Q2_midlow","Q3_midhigh","Q4_high"])
    except Exception:
        return pd.Series(["unknown"]*len(s),index=s.index)

def group_metrics(df, cols, label):
    if df.empty: return pd.DataFrame()
    rows=[]
    for key,g in df.groupby(cols,dropna=False):
        if not isinstance(key,tuple): key=(key,)
        w=pd.to_numeric(g.worst_result_usd_trimmed,errors="coerce").fillna(0)
        r=pd.to_numeric(g.rep_result_usd_trimmed,errors="coerce").fillna(0)
        row={"group_label":label,"events":int(len(g)),"rep_sum_result_usd":float(r.sum()),"worst_sum_result_usd":float(w.sum()),"worst_pf":pf(w[w!=0]),"negative_events":int((w<0).sum())}
        for c,v in zip(cols,key): row[c]=v
        rows.append(row)
    out=pd.DataFrame(rows)
    if not out.empty: out=out.sort_values(["worst_sum_result_usd","events"],ascending=[True,False]).reset_index(drop=True)
    return out

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir",default=""); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/"FX_OUTPUTS"/"gold_v3"; out=root/"146"; out.mkdir(parents=True,exist_ok=True)
    prog(out,0,1,"START",t0)
    s145=readj(root/"145"/"gold_v3_145_summary.json")
    p=root/"145"/"gold_v3_145_selected_trim_reconstructed_events.csv"
    ev=load(p); blockers=[]
    if ev.empty: blockers.append({"blocker_id":"missing_145_reconstructed_events","path":str(p)})
    need={"chosen_route_score_trimmed","kept_after_score_trim","date","entry_dt","rep_result_usd_trimmed","worst_result_usd_trimmed"}
    if not ev.empty and not need.issubset(set(ev.columns)): blockers.append({"blocker_id":"events_missing_required_columns","missing":sorted(need-set(ev.columns))})
    monthly=route_totals=neg_events=factors=pd.DataFrame()
    if not blockers:
        x=ev.copy(); x["entry_dt"]=pd.to_datetime(x.entry_dt,errors="coerce"); x=x[x.entry_dt.notna()].copy()
        x["month"]=pd.to_datetime(x.date,errors="coerce").dt.to_period("M").astype(str)
        x["hour"]=x.entry_dt.dt.hour; x["hour_bucket"]=x.hour.map(bucket_hour)
        for c in ["rep_result_usd_trimmed","worst_result_usd_trimmed","feature_score","score","max_score"]:
            if c in x.columns: x[c]=pd.to_numeric(x[c],errors="coerce")
        if "feature_score" in x.columns: x["feature_score_bucket"]=qbucket(x.feature_score)
        if "score" in x.columns: x["score_bucket"]=qbucket(x.score)
        if "max_score" in x.columns: x["max_score_bucket"]=qbucket(x.max_score)
        kept=x[x.kept_after_score_trim.astype(str).str.lower().isin(["true","1"])].copy()
        monthly=group_metrics(kept,["month","chosen_route_score_trimmed"],"month_route")
        route_totals=group_metrics(kept,["chosen_route_score_trimmed"],"route_total")
        neg_events=kept[pd.to_numeric(kept.worst_result_usd_trimmed,errors="coerce").fillna(0)<0].copy().sort_values("worst_result_usd_trimmed")
        frames=[]
        for cols,label in [(["chosen_route_score_trimmed","hour_bucket"],"route_hour"),(["chosen_route_score_trimmed","feature_score_bucket"],"route_feature_score_bucket"),(["chosen_route_score_trimmed","score_bucket"],"route_score_bucket"),(["month","chosen_route_score_trimmed","hour_bucket"],"month_route_hour")]:
            cols=[c for c in cols if c in kept.columns]
            if cols: frames.append(group_metrics(kept,cols,label))
        factors=pd.concat([f for f in frames if not f.empty],ignore_index=True) if frames else pd.DataFrame()
        save(x,out/"gold_v3_146_events_with_score_hour_buckets.csv"); save(monthly,out/"gold_v3_146_monthly_route_attribution.csv"); save(route_totals,out/"gold_v3_146_route_totals.csv"); save(neg_events,out/"gold_v3_146_negative_kept_events.csv"); save(factors,out/"gold_v3_146_factor_summary.csv")
    status=BLOCKED if blockers else READY
    if blockers: decision="SCORE_HOUR_ATTRIBUTION_BLOCKED_INPUT_MISSING"
    elif not monthly.empty and (monthly.groupby("month").worst_sum_result_usd.sum()<0).sum()>0: decision="SCORE_HOUR_ATTRIBUTION_READY_NEGATIVE_MONTHS_REMAIN"
    else: decision="SCORE_HOUR_ATTRIBUTION_READY_NO_NEGATIVE_MONTHS"
    neg_months=int((monthly.groupby("month").worst_sum_result_usd.sum()<0).sum()) if not monthly.empty else 0
    summary={"step":STEP,"status":status,"ready":status==READY,"decision":decision,"created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"output_dir":str(out),"audit_only":True,"review_only":True,"source_145_decision":s145.get("decision",""),"progress_total_configs":1,"progress_completed_configs":1 if not blockers else 0,"progress_output":str(out/"progress.txt"),"kept_events":int(len(ev[ev.kept_after_score_trim.astype(str).str.lower().isin(["true","1"])])) if not ev.empty and "kept_after_score_trim" in ev.columns else 0,"negative_month_count":neg_months,"negative_kept_event_count":int(len(neg_events)) if not neg_events.empty else 0,"source_csv_mutated":False,"contract_mutated":False,"open_asof_allowed":False,"candidate_pool_removed":False,"f002_exclusion_bypassed":False,"blocker_count":len(blockers),"elapsed_seconds":round(time.time()-t0,2)}
    prog(out,1,1,"DONE",t0)
    (out/"gold_v3_146_summary.json").write_text(json.dumps(summary|{"blockers":blockers},ensure_ascii=False,indent=2,default=str),encoding="utf-8"); save(pd.DataFrame([summary]),out/"gold_v3_146_decision.csv")
    lines=["GOLD V3 146 PASTE_ME_SELECTED_TRIM_SCORE_HOUR_ATTRIBUTION_AUDIT"]+[f"{k}: {v}" for k,v in summary.items()]
    lines += ["","ROUTE_TOTALS", route_totals.to_string(index=False) if not route_totals.empty else "NO_ROUTE_TOTALS"]
    lines += ["","FACTOR_WORST_TOP50", factors.head(50).to_string(index=False) if not factors.empty else "NO_FACTOR_ROWS"]
    lines += ["","NEGATIVE_KEPT_EVENTS_TOP40", neg_events.head(40).to_string(index=False) if not neg_events.empty else "NO_NEGATIVE_EVENTS"]
    lines += ["","MONTHLY_ROUTE_ATTRIBUTION", monthly.to_string(index=False) if not monthly.empty else "NO_MONTHLY"]
    lines += ["","BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=="__main__":
    raise SystemExit(main())
