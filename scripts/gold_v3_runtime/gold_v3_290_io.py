from __future__ import annotations
import json,os
from pathlib import Path
import pandas as pd

def _replace(path: Path, writer) -> None:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    writer(temp); os.replace(temp,path)

def write_json(path: Path,value: dict) -> None:
    _replace(path,lambda temp: temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8"))

def write_csv(path: Path,frame: pd.DataFrame) -> None:
    _replace(path,lambda temp: frame.to_csv(temp,index=False,encoding="utf-8-sig"))

def read_csv_optional(path: Path,columns=None) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size==0: return pd.DataFrame(columns=columns or [])
    return pd.read_csv(path,encoding="utf-8-sig")

def require_columns(frame: pd.DataFrame,required: set[str],label: str) -> None:
    missing=sorted(required-set(frame.columns))
    if missing: raise ValueError(f"{label} missing columns: {missing}")
