from __future__ import annotations

import argparse, hashlib, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

BCR02_SHA="5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2"
M15_SHA="b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
START=pd.Timestamp("2026-07-20T15:00:00Z")
END=pd.Timestamp("2026-07-30T01:30:00Z")
OFFSET=pd.Timedelta(hours=3)


def sha(path: Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def rci(x: np.ndarray)->float:
    n=len(x); ranks=pd.Series(x).rank(method="average").to_numpy(float)
    d=np.arange(1,n+1,dtype=float)-ranks
    return float((1-6*np.square(d).sum()/(n*(n*n-1)))*100)


def features(c: pd.DataFrame)->pd.DataFrame:
    c=c.copy(); cl=c.close.astype(float); hi=c.high.astype(float); lo=c.low.astype(float)
    for n in (9,14,18):
        c[f"rci{n}"]=cl.rolling(n,min_periods=n).apply(rci,raw=True)
        c[f"rci{n}_delta1"]=c[f"rci{n}"].diff()
        prev=c[f"rci{n}_delta1"].shift()
        c[f"rci{n}_turn_up"]=c[f"rci{n}_delta1"].gt(0)&prev.le(0)
        c[f"rci{n}_turn_down"]=c[f"rci{n}_delta1"].lt(0)&prev.ge(0)
    for n in (20,30,40): c[f"ema{n}"]=cl.ewm(span=n,adjust=False).mean()
    c["ema_alignment"]=np.select([
        (c.ema20>c.ema30)&(c.ema30>c.ema40),
        (c.ema20<c.ema30)&(c.ema30<c.ema40)],
        ["BULLISH_STACK","BEARISH_STACK"],default="MIXED")
    c["ema20_minus_ema30_bps"]=(c.ema20-c.ema30)/cl*10000
    c["ema30_minus_ema40_bps"]=(c.ema30-c.ema40)/cl*10000
    pc=cl.shift(); tr=pd.concat([hi-lo,(hi-pc).abs(),(lo-pc).abs()],axis=1).max(axis=1)
    c["atr14"]=tr.rolling(14,min_periods=14).mean(); c["atr50"]=tr.rolling(50,min_periods=50).mean()
    lr=np.log(cl/cl.shift()); c["realized_vol_32_bps"]=lr.rolling(32,min_periods=32).std(ddof=0)*10000
    c["realized_vol_96_bps"]=lr.rolling(96,min_periods=96).std(ddof=0)*10000
    c["bb_width20_bps"]=4*cl.rolling(20,min_periods=20).std(ddof=0)/cl.rolling(20,min_periods=20).mean()*10000
    c["rolling_high_50"]=hi.rolling(50,min_periods=50).max(); c["rolling_low_50"]=lo.rolling(50,min_periods=50).min()
    return c


def event_class(t: str|None,state: str)->str:
    m={"PRIMARY_LONG":"PRIMARY_LONG_EVENT","PRIMARY_SHORT":"PRIMARY_SHORT_EVENT",
       "LONG_EXIT":"VALID_LONG_EXIT_EVENT","SHORT_EXIT":"VALID_SHORT_EXIT_EVENT",
       "REENTRY_LONG":"REENTRY_EVENT","REENTRY_SHORT":"REENTRY_EVENT",
       "OPPOSITE_ALERT_IGNORED":"OPPOSITE_EVENT_IGNORED","OPPOSITE_EXIT_IGNORED":"OPPOSITE_EVENT_IGNORED"}
    if t in m:return m[t]
    return {"IDLE":"IDLE_NON_EVENT_CONTROL","ACTIVE_LONG":"ACTIVE_LONG_NON_EVENT_CONTROL",
            "ACTIVE_SHORT":"ACTIVE_SHORT_NON_EVENT_CONTROL"}[state]


def build(bcr02: Path,m15: Path,out: Path)->None:
    if sha(bcr02)!=BCR02_SHA or sha(m15)!=M15_SHA: raise RuntimeError("input SHA mismatch")
    with zipfile.ZipFile(bcr02) as z:
        led=pd.read_csv(z.open("02_canonical_source_event_ledger.csv"))
        seed=pd.read_csv(z.open("03_state_seed_history.csv"))
    led["dt"]=pd.to_datetime(led.bar_time_utc,utc=True); btc=led[led.ticker.eq("BTCUSD")].sort_values("dt")
    if len(btc)!=76 or btc.dt.duplicated().any(): raise RuntimeError("BTC ledger mismatch")
    seed["dt"]=pd.to_datetime(seed.bar_time_utc,utc=True)
    s=seed[(seed.ticker.eq("BTCUSD"))&(seed.dt<START)].sort_values("dt").iloc[-1]
    state=str(s.source_state_after); event_by={r.dt:r for r in btc.itertuples(index=False)}
    rows=[]
    for dt in pd.date_range(START,END,freq="15min"):
        e=event_by.get(dt); before=state
        if e is None: trans=None; after=before; rid=np.nan
        else:
            if str(e.source_state_before)!=before: raise RuntimeError("state parity failure")
            trans=str(e.source_transition); after=str(e.source_state_after); rid=int(e.raw_alert_id); state=after
        server=(dt+OFFSET).tz_localize(None); prev=server-pd.Timedelta(minutes=15)
        rows.append(dict(decision_time_utc=dt.strftime("%Y-%m-%dT%H:%M:%SZ"),current_server_open=server,
                         expected_previous_closed_server_open=prev,source_state_before=before,
                         source_transition=trans,source_state_after=after,raw_alert_id=rid,
                         event_class=event_class(trans,before)))
    u=pd.DataFrame(rows)
    c=pd.read_csv(m15); c["server_open"]=pd.to_datetime(c.time); c=features(c); ci=c.set_index("server_open")
    u["current_bar_present"]=u.current_server_open.isin(ci.index)
    u["exact_previous_closed_bar_present"]=u.expected_previous_closed_server_open.isin(ci.index)
    u["gap_adjacent"]=~(u.current_bar_present&u.exact_previous_closed_bar_present)
    u["current_open"]=u.current_server_open.map(ci.open)
    for col in ["close","rci9","rci9_delta1","rci9_turn_up","rci9_turn_down","rci14","rci18",
                "ema20","ema30","ema40","ema_alignment","ema20_minus_ema30_bps","ema30_minus_ema40_bps",
                "atr14","atr50","realized_vol_32_bps","realized_vol_96_bps","bb_width20_bps",
                "rolling_high_50","rolling_low_50"]:
        u[("closed_" if col=="close" else "")+col]=u.expected_previous_closed_server_open.map(ci[col])
    u["feature_eligible_core"]=u.current_bar_present&u.exact_previous_closed_bar_present&u[[
        "rci18","ema40","atr50","realized_vol_96_bps","rolling_high_50","rolling_low_50"]].notna().all(axis=1)
    checks=dict(rows=len(u),events=int(u.raw_alert_id.notna().sum()),unique_times=int(u.decision_time_utc.nunique()),
                gap_adjacent=int(u.gap_adjacent.sum()),event_gap_adjacent=int(u.loc[u.raw_alert_id.notna(),"gap_adjacent"].sum()),
                eligible=int(u.feature_eligible_core.sum()),outcomes_opened=False,current_high_low_close_used=False)
    if checks!={"rows":907,"events":76,"unique_times":907,"gap_adjacent":2,"event_gap_adjacent":0,
               "eligible":905,"outcomes_opened":False,"current_high_low_close_used":False}: raise RuntimeError(checks)
    out.mkdir(parents=True,exist_ok=True); u.to_csv(out/"decision_window_ledger.csv",index=False,encoding="utf-8-sig")
    (out/"integrity_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
    summary={"status":"READY_OUTCOME_BLIND_DECISION_UNIVERSE_AND_CONTROL_WINDOWS",**checks,
             "bcr02_sha256":BCR02_SHA,"m15_sha256":M15_SHA,"candidate_formula_designed":False}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--bcr02",type=Path,required=True); p.add_argument("--m15",type=Path,required=True); p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(); build(a.bcr02,a.m15,a.out); return 0

if __name__=="__main__": raise SystemExit(main())
