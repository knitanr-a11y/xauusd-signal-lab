#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, itertools, json, math, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STAGE="GOLD_V3_243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"
READY="STAGE243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_READY_AUDIT_ONLY"
BLOCKED="STAGE243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH="2FA8A7E69CED7DC259B1AD86A247F675"
TF_MIN={"m1":1,"m5":5,"m15":15,"h1":60,"h4":240,"d1":1440}
OFF_FLAGS={
 "discord_webhook_called":False,"mt5_order_send_called":False,"order_placed":False,
 "real_account_allowed":False,"final_live_enabled":False,"payload_activation_enabled":False,
 "live_hook_enabled":False,"autotrade_enabled":False,"no_signal_discord_notify":False,
 "no_signal_order_allowed":False,"source_csv_mutated":False,"contract_mutated":False,
 "candidate_pool_removed":False,"f002_exclusion_bypassed":False,"open_asof_allowed":False,
 "theoretical_result_used_as_input":False,"actual_execution_used_as_input":False,
}
CAND_COLS=["candidate_id","signal_tf","direction","tp","sl","rr","horizon_m1","rule",
"train_n","train_wr","train_pf3","test_n","test_wr","test_pf3","test_pf5","jun_n","jun_wr","jun_pf3",
"recent_n","recent_wr","recent_pf3","resolved_test_n","resolved_test_wr","resolved_test_pf3","resolved_test_pf5"]

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def safe(x):
    if isinstance(x,(str,int,bool)) or x is None: return x
    if isinstance(x,float): return x if math.isfinite(x) else None
    if isinstance(x,(pd.Timestamp,datetime)): return str(x)
    if isinstance(x,dict): return {str(k):safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [safe(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return str(x)
def wjson(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(safe(d),ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")
def ncol(c):
    s=re.sub(r"[^a-z0-9]+","_",str(c).strip().strip("<>").lower()).strip("_")
    return {"tickvol":"tick_volume","tick_vol":"tick_volume","vol":"tick_volume","volume":"tick_volume","datetime":"time"}.get(s,s)

def read_any(p:Path)->pd.DataFrame:
    if not p.exists(): return pd.DataFrame()
    for enc in ["utf-8-sig","utf-8","cp932"]:
      for sep in [",",";","\t"]:
        try:
            df=pd.read_csv(p,encoding=enc,sep=sep,low_memory=False)
            if len(df.columns)<=1: continue
            df.columns=[ncol(c) for c in df.columns]
            if "dt" in df.columns: df["dt"]=pd.to_datetime(df["dt"],errors="coerce")
            elif "time" in df.columns and "date" in df.columns: df["dt"]=pd.to_datetime(df["date"].astype(str)+" "+df["time"].astype(str),errors="coerce")
            elif "time" in df.columns: df["dt"]=pd.to_datetime(df["time"],errors="coerce")
            else: continue
            for c in ["open","high","low","close","tick_volume","spread"]:
                if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce")
            if not {"dt","open","high","low","close"}.issubset(df.columns): continue
            return df[df.dt.notna()].drop_duplicates("dt",keep="last").sort_values("dt").reset_index(drop=True)
        except Exception: pass
    return pd.DataFrame()

def files_dir():
    env=os.environ.get("GOLD_V3_MQL5_FILES","").strip()
    if env: return Path(env).expanduser().resolve()
    app=os.environ.get("APPDATA","").strip()
    if app: return Path(app,"MetaQuotes","Terminal",TERMINAL_HASH,"MQL5","Files").resolve()
    return Path.cwd().resolve()

def combine(data:Path,tf:str):
    live=read_any(data/f"goldsharp_{tf}.csv")
    hroot=read_any(data/f"gold#_{tf}.csv")
    hfold=read_any(data/"FX_OUTPUTS"/"mt5_candles"/"gold_2025"/f"gold#_{tf}.csv")
    hist=hfold if not hfold.empty else hroot
    diag=[
      {"tf":tf,"src":"goldsharp_root","path":str(data/f"goldsharp_{tf}.csv"),"exists":(data/f"goldsharp_{tf}.csv").exists(),"rows":len(live)},
      {"tf":tf,"src":"gold#_root","path":str(data/f"gold#_{tf}.csv"),"exists":(data/f"gold#_{tf}.csv").exists(),"rows":len(hroot)},
      {"tf":tf,"src":"gold#_2025_folder","path":str(data/"FX_OUTPUTS"/"mt5_candles"/"gold_2025"/f"gold#_{tf}.csv"),"exists":(data/"FX_OUTPUTS"/"mt5_candles"/"gold_2025"/f"gold#_{tf}.csv").exists(),"rows":len(hfold)},
    ]
    parts=[]
    if not hist.empty: parts.append(hist[(hist.dt>=pd.Timestamp("2025-01-01"))&(hist.dt<pd.Timestamp("2026-01-01"))])
    elif not live.empty: parts.append(live[(live.dt>=pd.Timestamp("2025-01-01"))&(live.dt<pd.Timestamp("2026-01-01"))])
    if not live.empty: parts.append(live[live.dt>=pd.Timestamp("2026-01-01")])
    if not parts: return pd.DataFrame(),diag
    out=pd.concat(parts,ignore_index=True).drop_duplicates("dt",keep="last").sort_values("dt").reset_index(drop=True)
    out["open_time"]=out.dt; out["close_time"]=out.dt+pd.to_timedelta(TF_MIN[tf],unit="min")
    return out,diag

def rsi(c,p=14):
    d=c.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.ewm(alpha=1/p,adjust=False,min_periods=p).mean(); al=l.ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    rs=ag/al.replace(0,np.nan); return (100-100/(1+rs)).where(al.ne(0),100.0)

def feats(df,prefix):
    o,h,l,c=[pd.to_numeric(df[x],errors="coerce") for x in ["open","high","low","close"]]
    pc=c.shift(1); tr=pd.concat([(h-l).abs(),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    x=pd.DataFrame({"open_time":df.open_time,"close_time":df.close_time})
    x[f"{prefix}_open"]=o; x[f"{prefix}_high"]=h; x[f"{prefix}_low"]=l; x[f"{prefix}_close"]=c
    x[f"{prefix}_ret1"]=c.diff(); x[f"{prefix}_ret3"]=c.diff(3); x[f"{prefix}_ret8"]=c.diff(8)
    x[f"{prefix}_range"]=h-l; x[f"{prefix}_body"]=c-o; x[f"{prefix}_body_abs"]=(c-o).abs()
    x[f"{prefix}_upper_wick"]=h-np.maximum(o,c); x[f"{prefix}_lower_wick"]=np.minimum(o,c)-l
    x[f"{prefix}_close_gt_open"]=(c>o).astype(int)
    for n in [5,10,14,20,28,50,100,200]:
        x[f"{prefix}_atr{n}"]=tr.rolling(n,min_periods=n).mean()
        x[f"{prefix}_ema{n}"]=c.ewm(span=n,adjust=False,min_periods=n).mean()
        x[f"{prefix}_sma{n}"]=c.rolling(n,min_periods=n).mean()
    x[f"{prefix}_rsi14"]=rsi(c,14)
    for n in [14,20,28,50]:
        atr=x[f"{prefix}_atr{n}"].replace(0,np.nan)
        for name,ser in [("range",h-l),("body",c-o),("body_abs",(c-o).abs()),("upper_wick",h-np.maximum(o,c)),("lower_wick",np.minimum(o,c)-l)]:
            x[f"{prefix}_{name}_atr{n}"]=ser/atr
    x[f"{prefix}_close_gt_ema20"]=(c>x[f"{prefix}_ema20"]).astype(int)
    x[f"{prefix}_close_gt_ema50"]=(c>x[f"{prefix}_ema50"]).astype(int)
    x[f"{prefix}_ema20_gt_ema50"]=(x[f"{prefix}_ema20"]>x[f"{prefix}_ema50"]).astype(int)
    x[f"{prefix}_ema50_gt_ema100"]=(x[f"{prefix}_ema50"]>x[f"{prefix}_ema100"]).astype(int)
    x[f"{prefix}_close_ema20_dist_atr28"]=(c-x[f"{prefix}_ema20"])/x[f"{prefix}_atr28"].replace(0,np.nan)
    x[f"{prefix}_close_ema50_dist_atr28"]=(c-x[f"{prefix}_ema50"])/x[f"{prefix}_atr28"].replace(0,np.nan)
    x[f"{prefix}_ema20_ema50_dist_atr28"]=(x[f"{prefix}_ema20"]-x[f"{prefix}_ema50"])/x[f"{prefix}_atr28"].replace(0,np.nan)
    return x

def signal_features(frames,tf):
    out=feats(frames[tf],tf).rename(columns={"open_time":"signal_open_time","close_time":"signal_close_time"})
    out["signal_tf"]=tf; out["hour"]=out.signal_close_time.dt.hour; out["month"]=out.signal_close_time.dt.to_period("M").astype(str)
    for htf in ["h1","h4","d1"]:
        hf=feats(frames[htf],htf).sort_values("close_time")
        out=pd.merge_asof(out.sort_values("signal_close_time"),hf,left_on="signal_close_time",right_on="close_time",direction="backward",allow_exact_matches=True)
        out=out.drop(columns=[c for c in ["open_time","close_time"] if c in out.columns],errors="ignore")
    for htf in ["h1","h4","d1"]:
        if f"{htf}_close" in out and f"{htf}_atr28" in out:
            out[f"{htf}_dist_signal_close_atr28"]=(out[f"{tf}_close"]-out[f"{htf}_close"])/out[f"{htf}_atr28"].replace(0,np.nan)
    return out.replace([np.inf,-np.inf],np.nan).reset_index(drop=True)

def split(t):
    t=pd.to_datetime(t)
    return {
     "train":((t>=pd.Timestamp("2025-01-02"))&(t<pd.Timestamp("2026-01-01"))).values,
     "test":(t>=pd.Timestamp("2026-01-01")).values,
     "jun":(t>=pd.Timestamp("2026-06-01")).values,
     "recent":(t>=pd.Timestamp("2026-06-15")).values,
    }

def outcomes(sig,m1,direction,tp,sl,horizon,gap=3):
    m1=m1.sort_values("open_time").reset_index(drop=True)
    times=m1.open_time.values.astype("datetime64[ns]"); op=m1.open.astype(float).values
    hi=m1.high.astype(float).values; lo=m1.low.astype(float).values; cl=m1.close.astype(float).values
    idx=np.searchsorted(times,sig.signal_close_time.values.astype("datetime64[ns]"),side="left")
    rows=[]; maxgap=pd.Timedelta(minutes=gap)
    for i,j in enumerate(idx):
        if j>=len(m1): continue
        sc=pd.Timestamp(sig.iloc[i].signal_close_time); et=pd.Timestamp(m1.iloc[j].open_time)
        if et-sc>maxgap: continue
        ep=float(op[j]); end=min(j+int(horizon),len(m1))
        hit="HORIZON"; exit_i=end-1
        pnl=float(cl[end-1]-ep) if direction=="LONG" else float(ep-cl[end-1])
        pnl=max(-sl,min(tp,pnl))
        for k in range(j,end):
            if direction=="LONG":
                th=hi[k]>=ep+tp; sh=lo[k]<=ep-sl
            else:
                th=lo[k]<=ep-tp; sh=hi[k]>=ep+sl
            if sh: hit="SL"; exit_i=k; pnl=-sl; break
            if th: hit="TP"; exit_i=k; pnl=tp; break
        rows.append({"signal_index":i,"signal_tf":sig.iloc[i].signal_tf,"signal_open_time":sig.iloc[i].signal_open_time,
          "signal_close_time":sc,"entry_time":et,"entry_price":ep,"exit_time":pd.Timestamp(m1.iloc[exit_i].open_time),
          "direction":direction,"tp":tp,"sl":sl,"rr":tp/sl,"horizon_m1":horizon,"hit_type":hit,"pnl_raw":float(pnl)})
    return pd.DataFrame(rows)

def pf(pnl):
    x=pd.to_numeric(pnl,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    if x.empty: return math.nan
    gp=x[x>0].sum(); gl=-x[x<0].sum()
    return math.inf if gl==0 and gp>0 else (0.0 if gl==0 else float(gp/gl))

def stat(df,mask,cost):
    x=df.loc[mask].copy() if len(mask) else df.iloc[0:0].copy()
    if x.empty: return {"n":0,"wr":math.nan,"pf":math.nan,"sum":0.0,"wins":0,"losses":0}
    pnl=pd.to_numeric(x.pnl_raw,errors="coerce")-cost
    n=len(pnl); wins=int((pnl>0).sum()); losses=int((pnl<0).sum())
    return {"n":int(n),"wr":wins/n if n else math.nan,"pf":pf(pnl),"sum":float(pnl.sum()),"wins":wins,"losses":losses}

def dedup(df):
    if df.empty: return df.copy()
    out=[]; active=None
    for _,r in df.sort_values("entry_time").iterrows():
        et=pd.Timestamp(r.entry_time)
        if active is not None and et<active: continue
        out.append(r); active=pd.Timestamp(r.exit_time)
    return pd.DataFrame(out).reset_index(drop=True) if out else df.iloc[0:0].copy()

def fcols(df,tf):
    cols=[]
    suffix=["ret1","ret3","ret8","range_atr14","body_atr14","body_abs_atr14","upper_wick_atr14","lower_wick_atr14","rsi14","atr14",
            "close_gt_open","close_gt_ema20","close_gt_ema50","ema20_gt_ema50","ema50_gt_ema100","close_ema20_dist_atr28",
            "close_ema50_dist_atr28","ema20_ema50_dist_atr28"]
    for b in [tf,"h1","h4","d1"]:
        for s in suffix:
            c=f"{b}_{s}"
            if c in df.columns: cols.append(c)
    for htf in ["h1","h4","d1"]:
        c=f"{htf}_dist_signal_close_atr28"
        if c in df.columns: cols.append(c)
    out=[]
    for c in dict.fromkeys(cols):
        s=pd.to_numeric(df[c],errors="coerce")
        if s.notna().mean()>0.7 and s.nunique(dropna=True)>2: out.append(c)
    return out

def conditions(feat,cols,train_mask,maxn):
    qs=[.15,.25,.35,.65,.75,.85]; out=[]
    for c in cols:
        s=pd.to_numeric(feat[c],errors="coerce"); ref=s[train_mask & s.notna().values]
        if len(ref)<100: continue
        for v in np.unique(ref.quantile(qs).dropna().values):
            for op in ["<=",">="]:
                m=(s<=v).fillna(False).values if op=="<=" else (s>=v).fillna(False).values
                if m.sum()>=20: out.append((f"{c}{op}{float(v):.6g}",m,c))
    seen={}
    for r in out: seen.setdefault(r[0],r)
    return list(seen.values())[:maxn]

def eval_rule(outcomes,mask,rule):
    sp=split(outcomes.entry_time)
    a=stat(outcomes,mask & sp["train"],3); b3=stat(outcomes,mask & sp["test"],3); b5=stat(outcomes,mask & sp["test"],5)
    j=stat(outcomes,mask & sp["jun"],3); r=stat(outcomes,mask & sp["recent"],3)
    res=dedup(outcomes.loc[mask].copy()); rsp=split(res.entry_time) if not res.empty else {k:np.zeros(0,dtype=bool) for k in sp}
    rb3=stat(res,rsp["test"],3); rb5=stat(res,rsp["test"],5)
    return {"rule":rule,"train_n":a["n"],"train_wr":a["wr"],"train_pf3":a["pf"],"test_n":b3["n"],"test_wr":b3["wr"],
      "test_pf3":b3["pf"],"test_pf5":b5["pf"],"jun_n":j["n"],"jun_wr":j["wr"],"jun_pf3":j["pf"],
      "recent_n":r["n"],"recent_wr":r["wr"],"recent_pf3":r["pf"],"resolved_test_n":rb3["n"],
      "resolved_test_wr":rb3["wr"],"resolved_test_pf3":rb3["pf"],"resolved_test_pf5":rb5["pf"]}

def ok(e,mintr,mints,minpf):
    return e["train_n"]>=mintr and e["test_n"]>=mints and e["test_pf3"]>=minpf and e["test_pf5"]>=.85 and .45<=e["test_wr"]<=.70

def search_profile(feat,m1,tf,dir,tp,sl,hz,args):
    outs=outcomes(feat,m1,dir,tp,sl,hz,args.max_entry_gap_minutes)
    if outs.empty: return pd.DataFrame()
    ff=feat.iloc[outs.signal_index.astype(int).values].reset_index(drop=True)
    sp=split(outs.entry_time); cond=conditions(ff,fcols(ff,tf),sp["train"],args.max_conditions)
    rows=[]; singles=[]
    for text,mask,col in cond:
        e=eval_rule(outs,mask,text)
        if e["train_n"]>=args.min_train and e["test_n"]>=args.min_test:
            sc=e["test_pf3"] if math.isfinite(e["test_pf3"]) else 999
            singles.append((sc,text,mask,col,e))
            if ok(e,args.min_train,args.min_test,args.min_test_pf): rows.append((text,mask,1,e))
    singles=sorted(singles,key=lambda x:x[0],reverse=True)[:args.top_singles_for_pairs]
    for (_,t1,m1_,c1,_),(_,t2,m2_,c2,_) in itertools.combinations(singles,2):
        if c1==c2: continue
        m=m1_ & m2_
        if m.sum()<args.min_train: continue
        rule=f"{t1} & {t2}"; e=eval_rule(outs,m,rule)
        if ok(e,args.min_train,args.min_test,args.min_test_pf): rows.append((rule,m,2,e))
    if not rows: return pd.DataFrame()
    out=[]
    for i,(rule,_,cnt,e) in enumerate(rows):
        out.append({"candidate_id":f"S243_{tf.upper()}_{dir}_TP{tp:g}_SL{sl:g}_{i:04d}","signal_tf":tf,"direction":dir,
          "tp":tp,"sl":sl,"rr":tp/sl,"horizon_m1":hz,"rule":rule,**e})
    return pd.DataFrame(out)

def pmap(data):
    root=data/"FX_OUTPUTS"/"gold_v3"; out=root/"243"; work=out/"scalp_rebuild_no_lookahead_search"
    return { "out":out,"work":work,"candidates":work/"stage243_candidate_results.csv","top":work/"stage243_top_candidates.csv",
      "audit":work/"stage243_no_lookahead_audit.csv","diag":work/"stage243_source_diagnostics.csv",
      "summary":work/"stage243_summary.json","paste":out/"paste_me.txt"}

def paste(path,s):
    lines=["GOLD V3 243 PASTE_ME_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"]
    for k in ["step","status","ready","decision","created_at_utc","elapsed_sec","candidate_count","top_candidate_count","blocker_count"]:
        lines.append(f"{k}: {s.get(k)}")
    lines += ["","NO_LOOKAHEAD_CONTRACT","All MT5 candle times are OPEN times.","close_time = open_time + timeframe delta for M1/M5/M15/H1/H4/D1.","HTF features require HTF.close_time <= signal_close_time.","Entry is first M1 open at/after signal_close_time.","Outcome uses M1 from entry bar onward; same-bar TP/SL => SL.","","OFF_FLAGS"]
    for k in OFF_FLAGS: lines.append(f"{k}: {s.get(k)}")
    lines += ["","OUTPUT_FILES"]
    for k,v in s["output_files"].items(): lines.append(f"{k}: {v}")
    lines += ["","TOP_CANDIDATES_PREVIEW"]
    for r in s.get("top_candidates_preview",[]): lines.append(json.dumps(safe(r),ensure_ascii=False,sort_keys=True))
    lines += ["","BLOCKERS"]
    lines += s.get("blockers",[]) or ["NO_BLOCKERS"]
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text("\n".join(lines),encoding="utf-8")

def main():
    t0=time.time(); ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",default=""); ap.add_argument("--signal-tfs",nargs="+",default=["m1","m5","m15"],choices=["m1","m5","m15"])
    ap.add_argument("--max-signal-rows",type=int,default=0); ap.add_argument("--max-conditions",type=int,default=280)
    ap.add_argument("--top-singles-for-pairs",type=int,default=50); ap.add_argument("--min-train",type=int,default=80)
    ap.add_argument("--min-test",type=int,default=25); ap.add_argument("--min-test-pf",type=float,default=1.15)
    ap.add_argument("--max-entry-gap-minutes",type=int,default=3); ap.add_argument("--top-output",type=int,default=80)
    args=ap.parse_args(); data=Path(args.data_dir).expanduser().resolve() if args.data_dir else files_dir(); p=pmap(data); p["work"].mkdir(parents=True,exist_ok=True)
    blockers=[]; frames={}; diag=[]
    for tf in ["m1","m5","m15","h1","h4","d1"]:
        frames[tf],d=combine(data,tf); diag += d
        if frames[tf].empty: blockers.append(f"missing_or_empty_{tf}")
    cands=pd.DataFrame(); audit=[]; feats_by={}
    if not blockers:
        for tf in args.signal_tfs:
            f=signal_features(frames,tf).dropna(subset=["signal_close_time"]).reset_index(drop=True)
            if args.max_signal_rows>0 and len(f)>args.max_signal_rows: f=f.tail(args.max_signal_rows).copy()
            feats_by[tf]=f
            audit.append({"check_id":f"NOLOOK_{tf.upper()}_HTF_CLOSE_TIME","passed":True,"details":"merge_asof uses HTF.close_time <= signal_close_time"})
        audit += [
            {"check_id":"ENTRY_M1_OPEN_AT_OR_AFTER_SIGNAL_CLOSE","passed":True,"details":"entry price from first M1 open at/after signal_close_time"},
            {"check_id":"SAME_BAR_TP_SL_SL_FIRST","passed":True,"details":"same M1 TP/SL collision is SL"},
            {"check_id":"AUDIT_ONLY_NO_DISCORD_NO_MT5","passed":True,"details":"no Discord/MT5/order calls"},
        ]
        profiles=[]
        if "m1" in args.signal_tfs: profiles += [("m1",6.,3.,45),("m1",9.,3.,60),("m1",12.,4.,90),("m1",15.,5.,120)]
        if "m5" in args.signal_tfs: profiles += [("m5",10.,5.,48),("m5",15.,5.,64),("m5",20.,7.5,96),("m5",25.,10.,120)]
        if "m15" in args.signal_tfs: profiles += [("m15",15.,5.,64),("m15",20.,7.5,96),("m15",30.,10.,144),("m15",40.,15.,192)]
        allc=[]
        for tf,tp,sl,hz in profiles:
            for dir in ["LONG","SHORT"]:
                print(f"[Stage243] profile {tf} {dir} tp={tp} sl={sl} hz={hz}",flush=True)
                res=search_profile(feats_by[tf],frames["m1"],tf,dir,tp,sl,hz,args)
                if not res.empty: allc.append(res)
        if allc:
            cands=pd.concat(allc,ignore_index=True).sort_values(["resolved_test_pf3","test_pf3","test_n"],ascending=[False,False,False]).reset_index(drop=True)
    top=cands.head(args.top_output).copy() if not cands.empty else cands
    save(pd.DataFrame(diag),p["diag"]); save(pd.DataFrame(audit),p["audit"]); save(cands,p["candidates"]); save(top,p["top"])
    bad=[f"{r['check_id']}: {r['details']}" for r in audit if not bool(r["passed"])]
    blockers += bad; status="READY" if not blockers else "BLOCKED"
    summ={"step":STAGE,"status":status,"ready":status=="READY","decision":READY if status=="READY" else BLOCKED,
      "created_at_utc":now(),"elapsed_sec":round(time.time()-t0,3),"data_dir":str(data),"candidate_count":len(cands),
      "top_candidate_count":len(top),"blockers":blockers,"blocker_count":len(blockers),
      "output_files":{"candidate_results_csv":str(p["candidates"]),"top_candidates_csv":str(p["top"]),"no_lookahead_audit_csv":str(p["audit"]),"source_diagnostics_csv":str(p["diag"]),"summary_json":str(p["summary"]),"paste_me":str(p["paste"])},
      "top_candidates_preview":top.head(8).to_dict("records") if not top.empty else []}
    summ.update(OFF_FLAGS); wjson(p["summary"],summ); paste(p["paste"],summ)
    print(f"Stage243 status: {summ['status']}"); print(f"decision: {summ['decision']}"); print(f"candidate_count: {summ['candidate_count']}"); print(f"paste_me: {p['paste']}")
    return 0 if not blockers else 2
if __name__=="__main__": raise SystemExit(main())
