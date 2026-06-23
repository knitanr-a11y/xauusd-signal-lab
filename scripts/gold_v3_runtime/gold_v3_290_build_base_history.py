from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    p=argparse.ArgumentParser(); p.add_argument("--stage67",required=True); p.add_argument("--stage53",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    h=pd.read_csv(a.stage67,encoding="utf-8-sig"); c=pd.read_csv(a.stage53,encoding="utf-8-sig")
    need_h={"opportunity_id","candidate_key","result_usd_after_close"}; need_c={"opportunity_id","close_time_jst","result_usd"}
    if not need_h.issubset(h.columns) or not need_c.issubset(c.columns): raise ValueError("required resolved history columns missing")
    h["p1"]=pd.to_numeric(h.result_usd_after_close,errors="coerce"); c["p2"]=pd.to_numeric(c.result_usd,errors="coerce"); c["exit_dt"]=pd.to_datetime(c.close_time_jst,errors="coerce")
    x=h[["opportunity_id","candidate_key","p1"]].drop_duplicates("opportunity_id",keep="last").merge(c[["opportunity_id","exit_dt","p2"]].drop_duplicates("opportunity_id",keep="last"),on="opportunity_id",how="inner").dropna()
    if x.empty or not np.isclose(x.p1,x.p2,rtol=0,atol=1e-8).all(): raise ValueError("resolved outcome mismatch")
    out=x.rename(columns={"p2":"pnl"})[["opportunity_id","candidate_key","exit_dt","pnl"]].sort_values(["exit_dt","candidate_key"])
    path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True); out.to_csv(path,index=False,encoding="utf-8-sig"); return 0

if __name__=="__main__": raise SystemExit(main())
