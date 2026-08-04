from __future__ import annotations
from pathlib import Path
from typing import Iterable
import hashlib
import pandas as pd

REQUIRED = {"time", "open", "high", "low", "close", "tick_volume", "spread"}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""): h.update(block)
    return h.hexdigest()

def read_candle(path: Path, expected_sha256: str | None = None) -> pd.DataFrame:
    path=Path(path)
    if expected_sha256 and sha256_file(path)!=expected_sha256:
        raise RuntimeError(f"SOURCE_HASH_MISMATCH: {path}")
    try:
        df=pd.read_csv(path)
        if len(df.columns)==1: df=pd.read_csv(path,sep=";")
    except Exception:
        df=pd.read_csv(path,sep=None,engine="python")
    df.columns=[str(c).strip().lower() for c in df.columns]
    missing=sorted(REQUIRED-set(df.columns))
    if missing: raise ValueError(f"{path}: missing {missing}")
    df["time"]=pd.to_datetime(df["time"],format="%Y.%m.%d %H:%M:%S",errors="raise")
    for c in ["open","high","low","close","tick_volume","spread","real_volume"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="raise")
    if df.time.duplicated().any(): raise ValueError(f"DUPLICATE_TIMESTAMP: {path}")
    if not df.time.is_monotonic_increasing: raise ValueError(f"NOT_ASCENDING: {path}")
    bad=(df.high<df[["open","close"]].max(axis=1))|(df.low>df[["open","close"]].min(axis=1))|(df.high<df.low)
    if bad.any(): raise ValueError(f"INVALID_OHLC: {path}: {int(bad.sum())}")
    return df

def read_union(paths: Iterable[Path], expected_hashes: dict[str,str] | None=None, keep: str="last") -> pd.DataFrame:
    frames=[]
    for rank,p in enumerate(map(Path,paths)):
        exp=(expected_hashes or {}).get(p.name)
        d=read_candle(p,exp); d["_source_rank"]=rank; frames.append(d)
    if not frames: raise ValueError("No source paths")
    x=pd.concat(frames,ignore_index=True)
    dup=x[x.duplicated("time",keep=False)]
    if len(dup):
        cols=[c for c in ["open","high","low","close","tick_volume","spread","real_volume"] if c in dup]
        conflicts=dup.groupby("time")[cols].nunique(dropna=False)
        if ((conflicts>1).any(axis=1)).any(): raise ValueError("SOURCE_MERGE_MISMATCH")
    x=x.sort_values(["time","_source_rank"]).drop_duplicates("time",keep=keep)
    x=x.sort_values("time").drop(columns="_source_rank").reset_index(drop=True)
    if x.time.duplicated().any() or not x.time.is_monotonic_increasing: raise ValueError("UNION_TIME_FAILURE")
    return x

def derive_m15_from_m1(m1: pd.DataFrame) -> pd.DataFrame:
    d=m1.copy(); d["bucket"]=d.time.dt.floor("15min"); g=d.groupby("bucket",sort=True)
    out=pd.DataFrame({
        "time":g.open.first().index,
        "open":g.open.first().to_numpy(), "high":g.high.max().to_numpy(),
        "low":g.low.min().to_numpy(), "close":g.close.last().to_numpy(),
        "tick_volume":g.tick_volume.sum().to_numpy(), "spread":g.spread.min().to_numpy(),
    })
    if "real_volume" in d: out["real_volume"]=g.real_volume.sum().to_numpy()
    return out
