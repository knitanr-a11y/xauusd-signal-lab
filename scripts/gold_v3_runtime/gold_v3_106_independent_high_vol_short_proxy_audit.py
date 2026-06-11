#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
READY="GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY"
BLOCKED="GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT="open/in-progress candles are not written to CSV"
POOL_POLICY="poolから外さない。rolling health gateに判断させる。"
HV_PROFILES=[("HV_SHORT_TP180_SL70_H128",180.0,70.0,128),("HV_SHORT_TP200_SL80_H128",200.0,80.0,128),("HV_SHORT_TP220_SL90_H128",220.0,90.0,128)]

def find_files_dir()->Path:
    root=Path(__file__).resolve().parents[2]
    for d in [Path.cwd(),root,root.parent,root.parent.parent,root/"Files",root.parent/"Files"]:
        d=d.resolve()
        if (d/"goldsharp_m15.csv").exists() and (d/"goldsharp_m5.csv").exists() and (d/"FX_OUTPUTS"/"gold_v3").exists(): return d
    raise SystemExit("Files dir not found")

def read_csv(path:Path)->pd.DataFrame:
    if not path.exists() or path.stat().st_size==0: return pd.DataFrame()
    return pd.read_csv(path,encoding="utf-8-sig")

def load_stage45(path:Path):
    spec=importlib.util.spec_from_file_location("gold_v3_stage45",path)
    if spec is None or spec.loader is None: raise ImportError(str(path))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def ok(cid:str,passed:bool,obs:Any,exp:Any,sev:str="BLOCKER")->dict[str,Any]:
    return {"check_id":cid,"result":"PASS" if passed else "FAIL","observed":obs,"expected":exp,"severity":sev}

def metrics(df:pd.DataFrame,by:list[str])->pd.DataFrame:
    if df.empty: return pd.DataFrame(columns=by+["trades","wins","losses","win_rate","gross_profit","gross_loss","profit_factor","sum_result_usd","avg_result_usd"])
    rows=[]
    for key,x in df.groupby(by,dropna=False):
        if not isinstance(key,tuple): key=(key,)
        gp=float(x.loc[x.result_usd>0,"result_usd"].sum()); gl=float(-x.loc[x.result_usd<0,"result_usd"].sum())
        pf=gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
        r={k:v for k,v in zip(by,key)}
        r.update(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()) if len(x) else 0.0,gross_profit=gp,gross_loss=gl,profit_factor=pf,sum_result_usd=float(x.result_usd.sum()),avg_result_usd=float(x.result_usd.mean()) if len(x) else 0.0)
        rows.append(r)
    return pd.DataFrame(rows).sort_values(["profit_factor","trades"],ascending=[False,False])

def evaluate_short(opps:pd.DataFrame,m5:pd.DataFrame)->pd.DataFrame:
    if opps.empty: return opps
    m5=m5.sort_values("time").reset_index(drop=True); times=m5.time.values; lo=m5.low.to_numpy(float); hi=m5.high.to_numpy(float); cl=m5.close.to_numpy(float); out=[]
    for _,r in opps.iterrows():
        et=pd.Timestamp(r.entry_dt); entry=float(r.entry_price); tp=float(r.tp_usd); sl=float(r.sl_usd); h=int(r.horizon_m15); end=et+pd.Timedelta(minutes=15*h)
        si=np.searchsorted(times,np.datetime64(et),side="right"); ei=np.searchsorted(times,np.datetime64(end),side="right")
        if ei<=si or ei>=len(m5) or m5.time.iloc[ei-1] < end-pd.Timedelta(minutes=5): continue
        tp_px=entry-tp; sl_px=entry+sl
        tp_hit=np.where(lo[si:ei]<=tp_px)[0]; sl_hit=np.where(hi[si:ei]>=sl_px)[0]
        ft=int(tp_hit[0]) if len(tp_hit) else None; fs=int(sl_hit[0]) if len(sl_hit) else None
        if fs is not None and (ft is None or fs<=ft): ai=si+fs; res=(m5.time.iloc[ai],sl_px,"SL",-sl)
        elif ft is not None: ai=si+ft; res=(m5.time.iloc[ai],tp_px,"TP",tp)
        else: ai=ei-1; ep=float(cl[ai]); res=(m5.time.iloc[ai],ep,"TIMEOUT",entry-ep)
        d=r.to_dict(); d.update(exit_dt=res[0],exit_price=res[1],exit_reason=res[2],result_usd=float(res[3]),is_win=res[3]>0,is_loss=res[3]<0); out.append(d)
    return pd.DataFrame(out)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--candle-dir",default=""); ap.add_argument("--start",default="2026-06-02 15:00:00"); ap.add_argument("--end",default=""); args=ap.parse_args()
    src=Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir(); base=src/"FX_OUTPUTS"/"gold_v3"; out=base/"106c"; out.mkdir(parents=True,exist_ok=True)
    p45=Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py"); p50q=base/"50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"/"gold_v3_50_rolling_prior_60d_q70_state.csv"
    blockers=[]; checks=[]
    for name,p in [("stage45",p45),("stage50_q70",p50q),("m15",src/"goldsharp_m15.csv"),("m5",src/"goldsharp_m5.csv"),("h4",src/"goldsharp_h4.csv")]:
        checks.append(ok(f"{name}_present",p.exists(),str(p),"exists"))
        if not p.exists(): blockers.append({"blocker_id":f"{name}_missing","reason":"missing","detail":str(p),"severity":"BLOCKER"})
    opps=pd.DataFrame(); ev=pd.DataFrame()
    if not blockers:
        st45=load_stage45(p45); m15,m5=st45.prepare(src,"closed",60,0.70); q=read_csv(p50q)
        if not q.empty:
            q["m15_time_jst"]=pd.to_datetime(q["m15_time_jst"],errors="coerce"); q=q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
            m15=m15.drop(columns=["m15_atr28_q","is_high_vol"],errors="ignore"); m15=m15.merge(q[["m15_time_jst","atr28_q70","high_vol_pass"]],left_on="time",right_on="m15_time_jst",how="left")
            m15["m15_atr28_q"]=pd.to_numeric(m15["atr28_q70"],errors="coerce"); m15["is_high_vol"]=m15["high_vol_pass"].fillna(False).astype(bool)
        start=pd.Timestamp(args.start); end=pd.Timestamp(args.end) if args.end else pd.to_datetime(m15["time"],errors="coerce").max()
        win=m15[(pd.to_datetime(m15["time"],errors="coerce")>=start)&(pd.to_datetime(m15["time"],errors="coerce")<=end)&(m15["is_high_vol"].fillna(False).astype(bool))].copy()
        rows=[]
        for _,r in win.iterrows():
            for pid,tp,sl,h in HV_PROFILES:
                rows.append({"entry_dt":r.time,"jst_dt":r.jst_dt,"entry_month":r.entry_month,"profile_id":pid,"candidate_label":f"INDEPENDENT_HV_SHORT__{pid}","tp_usd":tp,"sl_usd":sl,"horizon_m15":h,"entry_price":r.close,"h4_ret4":r.h4_ret4,"m15_atr28":r.m15_atr28,"m15_atr28_q":r.m15_atr28_q,"is_high_vol":r.is_high_vol,"jst_hour":r.jst_hour,"jst_weekday":r.jst_weekday})
        opps=pd.DataFrame(rows)
        if not opps.empty: opps["h4_bucket"]=pd.cut(pd.to_numeric(opps["h4_ret4"],errors="coerce"),bins=[-999,-0.02,-0.01,0,0.01,0.02,999],labels=["lt_-2pct","-2_to_-1pct","-1_to_0pct","0_to_1pct","1_to_2pct","gt_2pct"])
        ev=evaluate_short(opps,m5)
        if not ev.empty: ev["h4_bucket"]=pd.cut(pd.to_numeric(ev["h4_ret4"],errors="coerce"),bins=[-999,-0.02,-0.01,0,0.01,0.02,999],labels=["lt_-2pct","-2_to_-1pct","-1_to_0pct","0_to_1pct","1_to_2pct","gt_2pct"])
        checks.append(ok("independent_hv_short_opportunities_positive",len(opps)>0,len(opps),">0","WARN"))
    for c in checks:
        if c["result"]!="PASS" and c["severity"]=="BLOCKER": blockers.append({"blocker_id":c["check_id"],"reason":"validation_failed","detail":c,"severity":"BLOCKER"})
    status=READY if not blockers else BLOCKED
    prof=metrics(ev,["profile_id"]) if not ev.empty else pd.DataFrame(); weekday=metrics(ev,["jst_weekday"]) if not ev.empty else pd.DataFrame(); hour=metrics(ev,["jst_hour"]) if not ev.empty else pd.DataFrame(); h4m=metrics(ev,["h4_bucket"]) if not ev.empty else pd.DataFrame()
    opps.to_csv(out/"independent_high_vol_short_proxy_opportunities.csv",index=False,encoding="utf-8-sig"); ev.to_csv(out/"independent_high_vol_short_proxy_evaluated_trades.csv",index=False,encoding="utf-8-sig")
    prof.to_csv(out/"profile_metrics.csv",index=False,encoding="utf-8-sig"); weekday.to_csv(out/"weekday_metrics.csv",index=False,encoding="utf-8-sig"); hour.to_csv(out/"hour_metrics.csv",index=False,encoding="utf-8-sig"); h4m.to_csv(out/"h4_bucket_metrics.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out/"validation.csv",index=False,encoding="utf-8-sig"); pd.DataFrame(blockers).to_csv(out/"blockers.csv",index=False,encoding="utf-8-sig")
    summary=dict(status=status,independent_high_vol_short_proxy_ready=status==READY,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,safety="audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",pool_policy=POOL_POLICY,window_start=args.start,window_end=str(end) if 'end' in locals() else "",independent_high_vol_m15_rows=int(len(opps)/len(HV_PROFILES)) if len(HV_PROFILES) else 0,proxy_opportunity_rows=int(len(opps)),evaluated_trade_rows=int(len(ev)),blocker_count=len(blockers))
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    paste=["GOLD V3 106 PASTE_ME_INDEPENDENT_HIGH_VOL_SHORT_PROXY_SUMMARY"]
    for k,v in summary.items(): paste.append(f"{k}: {v}")
    paste += ["","PROFILE_METRICS",prof.to_string(index=False) if not prof.empty else "NO_EVALUATED_TRADES","","WEEKDAY_METRICS",weekday.to_string(index=False) if not weekday.empty else "NO_EVALUATED_TRADES","","HOUR_METRICS",hour.head(30).to_string(index=False) if not hour.empty else "NO_EVALUATED_TRADES","","H4_BUCKET_METRICS",h4m.to_string(index=False) if not h4m.empty else "NO_EVALUATED_TRADES","","BLOCKERS",pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS","","VALIDATION",pd.DataFrame(checks).to_string(index=False),"","OUTPUTS","paste_me.txt","summary.json","independent_high_vol_short_proxy_opportunities.csv","independent_high_vol_short_proxy_evaluated_trades.csv","profile_metrics.csv","weekday_metrics.csv","hour_metrics.csv","h4_bucket_metrics.csv","validation.csv","blockers.csv","report.md"]
    (out/"paste_me.txt").write_text("\n".join(paste)+"\n",encoding="utf-8"); (out/"report.md").write_text(f"# GOLD V3 106 independent high-vol SHORT proxy\n\nStatus: `{status}`\n\n- proxy rows: `{len(opps)}`\n- evaluated rows: `{len(ev)}`\n- blockers: `{len(blockers)}`\n",encoding="utf-8")
    print(f"[{status}] {out/'paste_me.txt'}"); return 0 if status==READY else 1
if __name__=="__main__": raise SystemExit(main())
