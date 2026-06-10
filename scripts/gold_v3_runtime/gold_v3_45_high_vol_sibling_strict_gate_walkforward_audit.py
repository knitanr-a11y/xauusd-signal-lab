#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 45 high-vol sibling + rolling health gate walk-forward audit.

Audit-only local runner. Reads goldsharp_m5/m15/h4 CSVs, builds Stage43
honmei candidates plus exploratory high-volatility siblings, applies a strict
per-candidate rolling health gate, and writes CSV/JSON/MD outputs.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json, math, sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_WALKFORWARD_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_WALKFORWARD_READY_AUDIT_ONLY"

R1 = {"rank":"1", "tp":150.0, "sl":60.0, "h":128, "profile":"USDPRICE_TP150_SL60_H128"}
R2 = {"rank":"2", "tp":80.0, "sl":30.0, "h":64, "profile":"USDPRICE_TP80_SL30_H64"}
HV_PROFILES = [("HV_TP180_SL70_H128",180.0,70.0,128),("HV_TP200_SL80_H128",200.0,80.0,128),("HV_TP220_SL90_H128",220.0,90.0,128)]

FALSE_FLAGS = dict(audit_only=True, live_allowed=False, mt5_execution_enabled=False,
    mt5_bat_created=False, discord_live_enabled=False, ai_api_called=False,
    signals_generated=False, final_signal_enabled=False,
    stage41_trading_source_used=False, gold_v2_old_gold_disc8_used=False)


def cat(fid, col, val, rank="ALL", desc=""):
    return {"id":fid,"type":"cat","col":col,"val":str(val),"rank":str(rank),"desc":desc or f"exclude {col}={val}"}

def band(fid, col, lo, hi, rank="ALL", desc=""):
    return {"id":fid,"type":"band","col":col,"lo":float(lo),"hi":float(hi),"rank":str(rank),"desc":desc or f"exclude {col} in [{lo},{hi})"}


def base_candidates():
    sat = cat("GLOBAL_SATURDAY","jst_weekday","Saturday",desc="all packets exclude Saturday")
    return [
      dict(label="R01_P7_R1_ONLY_CD60_PRUNE_015", ranks=["1"], cd=60, pr=1, warn="negative_months_final=1",
           filters=[cat("F015","jst_weekday","Wednesday"),cat("S025","jst_weekday","Friday"),cat("S001","jst_hour",0),band("B07_H4RET4_013598_015292","h4_ret4",0.0135985561,0.015292471),sat]),
      dict(label="R02_P8_R1_ONLY_CD60_PRUNE_015", ranks=["1"], cd=60, pr=2, warn="negative_months_final=1",
           filters=[cat("F015","jst_weekday","Wednesday"),cat("S025","jst_weekday","Friday"),cat("S027","jst_weekday","Saturday"),band("B08_H4RET4_013657_015425","h4_ret4",0.013657835,0.0154251557),sat]),
      dict(label="R03_P1_R1_ONLY_CD60_PRUNE_111", ranks=["1"], cd=60, pr=3, warn="",
           filters=[band("F002","h4_ret4",0.0200540794,0.0375731465,"1"),cat("F003","jst_hour",23),cat("F004","jst_weekday","Friday"),cat("S021","jst_hour",21),cat("S022","jst_hour",22),sat]),
      dict(label="R04_P4_R1_ONLY_CD60_PRUNE_115", ranks=["1"], cd=60, pr=4, warn="",
           filters=[band("F002","h4_ret4",0.0200540794,0.0375731465,"1"),cat("F004","jst_weekday","Friday"),cat("F006","jst_hour",0),cat("S020","jst_hour",21),cat("S022","jst_hour",23),sat]),
      dict(label="R05_P9_MAIN_R1_R2_CD90_PRUNE_133", ranks=["1","2"], cd=90, pr=5, warn="",
           filters=[cat("F003","jst_hour",23),cat("F004","jst_weekday","Friday"),band("F008","m15_atr28",4.1865714286,4.2445,"2"),cat("S023","jst_hour",22),band("S034","h4_ret4",0.0132517647,0.0155591759,"1"),band("B09_R2_M15ATR28_3878714_3998071","m15_atr28",3.878714,3.998071,"2"),sat]),
      dict(label="R06_P11_MAIN_R1_R2_CD90_PRUNE_132", ranks=["1","2"], cd=90, pr=6, warn="",
           filters=[cat("F003","jst_hour",23),cat("F004","jst_weekday","Friday"),band("F007","m15_atr28",3.8709285714,3.9446428571,"2"),band("S034","h4_ret4",0.0132517647,0.0155591759,"1"),cat("S001","jst_hour",0),band("B11_M15ATR28_422839_429071","m15_atr28",4.2283928571,4.2907142857),sat]),
      dict(label="R07_P13_MAIN_R1_R2_CD120_PRUNE_122", ranks=["1","2"], cd=120, pr=7, warn="",
           filters=[band("F002","h4_ret4",0.0200540794,0.0375731465,"1"),cat("F006","jst_hour",0),cat("F012","jst_weekday","Thursday"),band("S030","h4_ret4",0.0085308259,0.0094322678,"1"),band("S035","h4_ret4",0.0143035172,0.0171553656,"1"),band("B13_H4RET4_007518_007783","h4_ret4",0.007518,0.007783),sat]),
      dict(label="R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024", ranks=["1"], cd=90, pr=8, warn="REQUEST_MORE_AUDIT_LOW_FREQUENCY; not Stage36 packet",
           filters=[cat("F004","jst_weekday","Friday"),cat("F006","jst_hour",0),band("S030","h4_ret4",0.013348824,0.0156019094,"1"),cat("S024","jst_weekday","Wednesday")]),
    ]


def add_hv_siblings(cands):
    out = []
    hvf = cat("HV_ROLLING_Q70","is_high_vol",True,desc="m15_atr28 >= rolling prior 60D q70")
    for c in cands:
        for i,(pid,tp,sl,h) in enumerate(HV_PROFILES):
            d = dict(c)
            d["label"] = f"HV_{c['label']}__{pid}"
            d["pr"] = float(c["pr"]) - 0.30 + i*0.03
            d["hv"] = True; d["hv_profile"] = pid; d["hv_tp"] = tp; d["hv_sl"] = sl; d["hv_h"] = h
            d["warn"] = "exploratory high-vol sibling; not Stage36 source candidate"
            d["filters"] = list(c["filters"]) + [hvf]
            out.append(d)
    return out


def read_candles(p: Path):
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    for c in ["time","open","high","low","close"]:
        if c not in df.columns: raise ValueError(f"{p.name}: missing {c}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open","high","low","close"]: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["time","open","high","low","close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)


def atr(df,n):
    pc = df.close.shift(1)
    tr = pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def find_dir(arg):
    cands = [Path(arg)] if arg else []
    root = Path(__file__).resolve().parents[2]
    cands += [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files"]
    for d in cands:
        if (d/"goldsharp_m5.csv").exists() and (d/"goldsharp_m15.csv").exists() and (d/"goldsharp_h4.csv").exists(): return d.resolve()
    raise FileNotFoundError("goldsharp_m5/m15/h4.csv not found. Pass --candle-dir.")


def prepare(cdir, htf_asof, hv_days, hv_q):
    m5=read_candles(cdir/"goldsharp_m5.csv"); m15=read_candles(cdir/"goldsharp_m15.csv"); h4=read_candles(cdir/"goldsharp_h4.csv")
    m15["m15_atr28"] = atr(m15,28)
    win = max(1, int(hv_days)*96)
    m15["m15_atr28_q"] = m15.m15_atr28.shift(1).rolling(win, min_periods=max(28,win//4)).quantile(float(hv_q))
    m15["is_high_vol"] = (m15.m15_atr28 >= m15.m15_atr28_q) & m15.m15_atr28_q.notna()
    h4["h4_ret4"] = h4.close / h4.close.shift(4) - 1.0
    hf = h4[["time","h4_ret4"]].dropna().copy()
    hf["feature_time"] = hf.time + pd.Timedelta(hours=4) if htf_asof == "closed" else hf.time
    m15 = pd.merge_asof(m15.sort_values("time"), hf[["feature_time","h4_ret4"]].sort_values("feature_time"), left_on="time", right_on="feature_time", direction="backward")
    m15["jst_dt"] = m15.time + pd.Timedelta(hours=9)
    m15["jst_hour"] = m15.jst_dt.dt.hour
    m15["jst_weekday"] = m15.jst_dt.dt.day_name()
    m15["entry_month"] = m15.jst_dt.dt.to_period("M").astype(str)
    return m15, m5


def source_rows(m15):
    rows=[]
    r1 = m15[m15.h4_ret4.notna() & (m15.h4_ret4 >= 0.00751699)].copy(); r1["source_rank"]="1"; r1["source_profile_id"]=R1["profile"]; rows.append(r1)
    r2 = m15[m15.m15_atr28.notna() & (m15.m15_atr28 >= 3.59086) & (m15.m15_atr28 <= 4.29321)].copy(); r2["source_rank"]="2"; r2["source_profile_id"]=R2["profile"]; rows.append(r2)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def keep_mask(df, f):
    applies = pd.Series(True, index=df.index) if f["rank"] == "ALL" else df.source_rank.astype(str).eq(f["rank"])
    if f["type"] == "cat": reject = df[f["col"]].astype(str).eq(f["val"])
    else: reject = pd.to_numeric(df[f["col"]], errors="coerce").between(f["lo"], f["hi"], inclusive="left")
    return ~(applies & reject.fillna(False))


def cooldown(df):
    if df.empty: return df
    keep=[]; x=df.sort_values(["candidate_label","entry_dt","priority","source_rank"])
    for _,g in x.groupby("candidate_label", sort=False):
        cd=int(g.cooldown_minutes.iloc[0])*60*1_000_000_000; last=None
        for idx,t in zip(g.index, g.entry_dt.astype("int64")):
            if last is None or int(t) >= last + cd:
                keep.append(idx); last=int(t)
    return df.loc[keep].sort_values(["entry_dt","priority","source_rank"]).reset_index(drop=True)


def opportunities(m15, cands):
    src=source_rows(m15); parts=[]
    for c in cands:
        sub=src[src.source_rank.astype(str).isin(c["ranks"])].copy()
        if sub.empty: continue
        mask=pd.Series(True,index=sub.index)
        for f in c["filters"]: mask &= keep_mask(sub,f)
        sub=sub[mask].copy()
        if sub.empty: continue
        hv=bool(c.get("hv",False))
        if hv:
            sub["profile_id"]=c["hv_profile"]; sub["tp_usd"]=c["hv_tp"]; sub["sl_usd"]=c["hv_sl"]; sub["horizon_m15"]=c["hv_h"]
        else:
            is1=sub.source_rank.astype(str).eq("1")
            sub["profile_id"]=np.where(is1,R1["profile"],R2["profile"]); sub["tp_usd"]=np.where(is1,R1["tp"],R2["tp"]); sub["sl_usd"]=np.where(is1,R1["sl"],R2["sl"]); sub["horizon_m15"]=np.where(is1,R1["h"],R2["h"])
        sub["entry_dt"]=sub.time; sub["entry_price"]=sub.close; sub["candidate_label"]=c["label"]; sub["cooldown_minutes"]=c["cd"]; sub["priority"]=c["pr"]; sub["hv_sibling"]=hv; sub["warning"]=c.get("warn","")
        parts.append(sub[["entry_dt","jst_dt","entry_month","candidate_label","source_rank","source_profile_id","profile_id","tp_usd","sl_usd","horizon_m15","cooldown_minutes","priority","hv_sibling","entry_price","h4_ret4","m15_atr28","m15_atr28_q","is_high_vol","jst_hour","jst_weekday","warning"]])
    return cooldown(pd.concat(parts, ignore_index=True)) if parts else pd.DataFrame()


def evaluate(opps, m5, complete=True):
    if opps.empty: return opps
    m5=m5.sort_values("time").reset_index(drop=True); times=m5.time.values; lo=m5.low.to_numpy(float); hi=m5.high.to_numpy(float); cl=m5.close.to_numpy(float); cache={}; out=[]
    for _,r in opps.iterrows():
        et=pd.Timestamp(r.entry_dt); entry=float(r.entry_price); tp=float(r.tp_usd); sl=float(r.sl_usd); h=int(r.horizon_m15); key=(et.to_datetime64(),tp,sl,h)
        res=cache.get(key)
        if res is None and key not in cache:
            end=et+pd.Timedelta(minutes=15*h); si=np.searchsorted(times, np.datetime64(et), side="right"); ei=np.searchsorted(times, np.datetime64(end), side="right")
            if ei<=si or (complete and m5.time.iloc[ei-1] < end-pd.Timedelta(minutes=5)):
                cache[key]=False; res=False
            else:
                tp_px=entry+tp; sl_px=entry-sl; sl_hit=np.where(lo[si:ei]<=sl_px)[0]; tp_hit=np.where(hi[si:ei]>=tp_px)[0]
                fs=int(sl_hit[0]) if len(sl_hit) else None; ft=int(tp_hit[0]) if len(tp_hit) else None
                if fs is not None and (ft is None or fs<=ft): ai=si+fs; res=(m5.time.iloc[ai],sl_px,"SL",-sl)
                elif ft is not None: ai=si+ft; res=(m5.time.iloc[ai],tp_px,"TP",tp)
                else: ai=ei-1; ep=float(cl[ai]); res=(m5.time.iloc[ai],ep,"TIMEOUT",ep-entry)
                cache[key]=res
        if not res: continue
        d=r.to_dict(); d.update(exit_dt=res[0], exit_price=res[1], exit_reason=res[2], result_usd=float(res[3]), is_win=res[3]>0, is_loss=res[3]<0); out.append(d)
    return pd.DataFrame(out)


def metrics(x):
    if x is None or len(x)==0: return dict(trades=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,avg_result_usd=0.0,max_drawdown_usd=0.0,loss_months=0)
    x=x.sort_values("entry_dt"); gp=x.loc[x.result_usd>0,"result_usd"].sum(); gl=-x.loc[x.result_usd<0,"result_usd"].sum(); pf=gp/gl if gl>0 else (math.inf if gp>0 else 0.0); eq=x.result_usd.cumsum(); mon=x.groupby("entry_month").result_usd.sum()
    return dict(trades=int(len(x)), win_rate=float((x.result_usd>0).mean()), profit_factor=float(pf), sum_result_usd=float(x.result_usd.sum()), avg_result_usd=float(x.result_usd.mean()), max_drawdown_usd=float((eq.cummax()-eq).max()), loss_months=int((mon<0).sum()))


def summarize(df, by):
    rows=[]
    if df.empty: return pd.DataFrame()
    for k,g in df.groupby(by, dropna=False):
        if not isinstance(k,tuple): k=(k,)
        d={c:v for c,v in zip(by,k)}; d.update(metrics(g)); rows.append(d)
    return pd.DataFrame(rows)


def dedup(df, include_hv):
    x=df if include_hv else df[~df.hv_sibling]
    return x.sort_values(["entry_dt","priority","candidate_label"]).groupby("entry_dt",as_index=False).first() if not x.empty else x


def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def loss_streak(vals):
    n=0
    for v in reversed(vals):
        if v<0: n+=1
        else: break
    return n


def health_gate(df, win, min_n, pf_thr, loss_lt, include_hv):
    x=df if include_hv else df[~df.hv_sibling]
    hist=defaultdict(lambda: deque(maxlen=win)); chosen=[]
    for _,g in x.sort_values(["entry_dt","priority","candidate_label"]).groupby("entry_dt",sort=True):
        allowed=[]
        for _,r in g.sort_values(["priority","candidate_label"]).iterrows():
            h=list(hist[r.candidate_label]); ok=True; hp=""; ls=""
            if len(h)>=min_n:
                hp=pf(h); ls=loss_streak(h); ok=(hp>=pf_thr and ls<loss_lt)
            if ok:
                d=r.to_dict(); d["health_history_n"]=len(h); d["health_pf"]=hp; d["health_loss_streak"]=ls; allowed.append(d)
        if allowed: chosen.append(allowed[0])
        for _,r in g.iterrows(): hist[r.candidate_label].append(float(r.result_usd))
    return pd.DataFrame(chosen)


def parse_args(argv):
    p=argparse.ArgumentParser(description=STEP); p.add_argument("--candle-dir",default=""); p.add_argument("--output-dir",default=""); p.add_argument("--start-jst",default="2026-01-01"); p.add_argument("--end-jst",default=""); p.add_argument("--htf-asof",choices=["closed","open"],default="closed"); p.add_argument("--hv-rolling-days",type=int,default=60); p.add_argument("--hv-quantile",type=float,default=0.70); p.add_argument("--health-window",type=int,default=30); p.add_argument("--health-min-history",type=int,default=20); p.add_argument("--strict-pf-threshold",type=float,default=1.10); p.add_argument("--strict-loss-streak-lt",type=int,default=3); p.add_argument("--run-walkforward",action="store_true",default=True); p.add_argument("--allow-incomplete-horizon",action="store_true"); return p.parse_args(argv)


def period(df,start,end):
    x=df.copy();
    if start: x=x[x.jst_dt>=pd.Timestamp(start)]
    if end:
        e=pd.Timestamp(end); e=e+pd.Timedelta(days=1) if len(end)==10 else e; x=x[x.jst_dt<e]
    return x.reset_index(drop=True)


def main(argv):
    a=parse_args(argv); cdir=find_dir(a.candle_dir); out=Path(a.output_dir) if a.output_dir else cdir/"FX_OUTPUTS"/"gold_v3"/"45_high_vol_sibling_strict_gate_walkforward_audit_only"; out.mkdir(parents=True,exist_ok=True)
    m15,m5=prepare(cdir,a.htf_asof,a.hv_rolling_days,a.hv_quantile); cands=base_candidates(); all_cands=cands+add_hv_siblings(cands); opp=evaluate(opportunities(m15,all_cands),m5,complete=not a.allow_incomplete_horizon); opp=period(opp,a.start_jst,a.end_jst)
    if opp.empty: raise RuntimeError("No evaluated opportunities after period/filtering.")
    pd.DataFrame([{k:v for k,v in c.items() if k!="filters"} | {"filters":" || ".join([f['id'] for f in c['filters']])} for c in all_cands]).to_csv(out/"gold_v3_45_hv_sibling_candidate_definitions.csv",index=False,encoding="utf-8-sig")
    opp.to_csv(out/"gold_v3_45_all_candidate_opportunity_ledger.csv",index=False,encoding="utf-8-sig")
    summarize(opp,["candidate_label","hv_sibling"]).to_csv(out/"gold_v3_45_hv_sibling_all_candidate_summary.csv",index=False,encoding="utf-8-sig")
    base=dedup(opp,False); base_gate=health_gate(opp,a.health_window,a.health_min_history,a.strict_pf_threshold,a.strict_loss_streak_lt,False); hv=dedup(opp,True); hv_gate=health_gate(opp,a.health_window,a.health_min_history,a.strict_pf_threshold,a.strict_loss_streak_lt,True)
    exps=[]
    for name,df in [("fixed_8_rank_dedup_no_hv",base),("fixed_8_strict_rolling_health_gate_no_hv",base_gate),("fixed_8_plus_hv_siblings_rank_dedup",hv),("fixed_8_plus_hv_siblings_strict_rolling_health_gate",hv_gate)]:
        d={"experiment":name}; d.update(metrics(df)); exps.append(d)
    pd.DataFrame(exps).to_csv(out/"gold_v3_45_hv_sibling_gate_experiment_summary.csv",index=False,encoding="utf-8-sig")
    hv_gate.to_csv(out/"gold_v3_45_hv_sibling_strict_gate_trade_ledger.csv",index=False,encoding="utf-8-sig")
    summarize(hv_gate,["candidate_label","hv_sibling"]).to_csv(out/"gold_v3_45_hv_sibling_strict_gate_candidate_summary.csv",index=False,encoding="utf-8-sig")
    summarize(hv_gate,["entry_month"]).to_csv(out/"gold_v3_45_hv_sibling_strict_gate_monthly_summary.csv",index=False,encoding="utf-8-sig")
    wf=[]
    if a.run_walkforward:
        selected=health_gate(opp,a.health_window,a.health_min_history,a.strict_pf_threshold,a.strict_loss_streak_lt,True)
        for mo in sorted(opp.entry_month.dropna().unique()):
            d={"test_month":mo,"include_hv_siblings":True}; d.update(metrics(selected[selected.entry_month==mo])); wf.append(d)
    pd.DataFrame(wf).to_csv(out/"gold_v3_45_hv_sibling_rolling_walkforward_monthly_summary.csv",index=False,encoding="utf-8-sig")
    summ=dict(step=STEP,status=READY_STATUS,created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),candle_dir=str(cdir),output_dir=str(out),**FALSE_FLAGS,start_jst=a.start_jst,end_jst=a.end_jst or "DATA_END",htf_asof=a.htf_asof,complete_horizon_only=not a.allow_incomplete_horizon,hv_rule=f"m15_atr28 >= rolling prior {a.hv_rolling_days}D q{a.hv_quantile}",health_gate=dict(window=a.health_window,min_history=a.health_min_history,pf_threshold=a.strict_pf_threshold,loss_streak_lt=a.strict_loss_streak_lt,virtual_monitoring=True),experiment_summary=exps)
    (out/"gold_v3_45_hv_sibling_strict_gate_summary.json").write_text(json.dumps(summ,ensure_ascii=False,indent=2),encoding="utf-8")
    best=metrics(hv_gate)
    (out/"GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_AUDIT_ONLY_REPORT.md").write_text(f"# GOLD V3 45 high-vol sibling strict gate audit-only report\n\nStatus: `{READY_STATUS}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n\n## Main result\n\n- trades: `{best['trades']}`\n- win_rate: `{best['win_rate']:.6f}`\n- profit_factor: `{best['profit_factor']:.6f}`\n- sum_result_usd: `{best['sum_result_usd']:.2f}`\n- max_drawdown_usd: `{best['max_drawdown_usd']:.2f}`\n\n## Safety\n\nThis is not live approval.\n",encoding="utf-8")
    print(f"[{READY_STATUS}] output_dir={out}"); return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
