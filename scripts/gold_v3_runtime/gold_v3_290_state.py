from __future__ import annotations
import numpy as np
import pandas as pd

def state_at(time,ledger,bootstrap):
    """Return only information resolved or already active at the supplied time."""
    t=pd.Timestamp(time)
    if len(ledger):
        closed=ledger[
            ledger.status.astype(str).eq("CLOSED")
            & pd.to_datetime(ledger.exit_dt,errors="coerce").le(t)
        ].copy()
        live=closed[["candidate_id","source","planned_entry_dt","exit_dt","pnl"]].rename(columns={"planned_entry_dt":"entry_dt"})
    else:
        live=pd.DataFrame(columns=["candidate_id","source","entry_dt","exit_dt","pnl"])
    hist=bootstrap[pd.to_datetime(bootstrap.exit_dt,errors="coerce").le(t)].copy()
    resolved=pd.concat([hist,live],ignore_index=True).drop_duplicates("candidate_id",keep="last")
    if len(resolved):
        resolved=resolved.sort_values(["exit_dt","entry_dt"],kind="mergesort")
    values=pd.to_numeric(resolved.pnl,errors="coerce").dropna().to_numpy(float) if len(resolved) else np.array([],float)
    curve=np.cumsum(values)
    equity=float(values.sum()) if len(values) else 0.0
    peak=float(max(0.0,curve.max())) if len(curve) else 0.0
    if len(ledger):
        entries=pd.to_datetime(ledger.planned_entry_dt,errors="coerce")
        active=ledger[ledger.status.astype(str).isin(["PENDING_FILL","OPEN"]) & entries.le(t)]
        observed=ledger[entries.le(t)]
    else:
        active=pd.DataFrame(); observed=pd.DataFrame()
    added=observed[observed.source.astype(str).ne("BASE")] if len(observed) else pd.DataFrame()
    losses=resolved[(resolved.source.astype(str)!="BASE") & (resolved.pnl<0)] if len(resolved) else pd.DataFrame()
    bases=resolved[resolved.source.astype(str).eq("BASE")].sort_values("exit_dt") if len(resolved) else pd.DataFrame()
    return {
        "equity":equity,
        "peak":peak,
        "dd":peak-equity,
        "active_count":int(len(active)),
        "last_candidate_entry":pd.to_datetime(added.planned_entry_dt,errors="coerce").max() if len(added) else pd.NaT,
        "last_candidate_loss_exit":pd.to_datetime(losses.exit_dt,errors="coerce").max() if len(losses) else pd.NaT,
        "last_base_exit":bases.exit_dt.iloc[-1] if len(bases) else pd.NaT,
        "last_base_pnl":float(bases.pnl.iloc[-1]) if len(bases) else np.nan,
        "resolved_count":int(len(resolved)),
    }
