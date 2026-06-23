from __future__ import annotations
import numpy as np
import pandas as pd

def find_trigger_intent(m5,decision_time,direction,kind,max_wait_minutes=60):
    """Detect a trigger on closed M5 and plan entry at that bar's close."""
    times=m5.time.to_numpy("datetime64[ns]")
    start=max(np.searchsorted(times,np.datetime64(decision_time),side="left"),6)
    limit=np.datetime64(pd.Timestamp(decision_time)+pd.Timedelta(minutes=max_wait_minutes))
    end=min(np.searchsorted(times,limit,side="left"),len(m5))
    h=m5.high.to_numpy(float); l=m5.low.to_numpy(float); c=m5.close.to_numpy(float)
    body=m5.body_signed.to_numpy(float); ema=m5.ema20.to_numpy(float)
    for k in range(start,end):
        signed=direction*body[k]
        if kind=="BRK6":
            ok=((c[k]>h[k-6:k].max()) if direction==1 else (c[k]<l[k-6:k].min())) and signed>=0.20
        elif kind=="EMA20":
            ok=((c[k]>ema[k] and c[k-1]<=ema[k-1] and c[k]>h[k-1]) if direction==1 else (c[k]<ema[k] and c[k-1]>=ema[k-1] and c[k]<l[k-1])) and signed>=(0.15 if direction==1 else 0.12)
        else:
            raise ValueError(kind)
        if ok:
            trigger=pd.Timestamp(times[k])
            return trigger,trigger+pd.Timedelta(minutes=5),float(c[k])
    return pd.NaT,pd.NaT,np.nan
