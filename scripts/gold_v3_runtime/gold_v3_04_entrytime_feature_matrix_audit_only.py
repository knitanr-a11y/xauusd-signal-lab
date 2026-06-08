#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_AUDIT_ONLY"
OUT_NAME = "04_entrytime_feature_matrix_audit_only"
EXPECTED_03_STATUS = "GOLD_V3_03_LABEL_OUTCOME_EVALUATION_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
FORBIDDEN_FEATURE_TOKENS = ["outcome", "profit", "result", "touch", "tp", "sl", "timeout", "future", "label", "horizon"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def v3_output_root() -> Path:
    return files_root() / "FX_OUTPUTS" / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def upstream03_dir() -> Path:
    return v3_output_root() / "03_label_outcome_evaluation_audit_only"


def canonical_dir() -> Path:
    return v3_output_root() / "01_candle_normalization_time_audit" / "canonical_candles"


def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x, "isoformat") else x


def write_json(p: Path, obj: dict[str,Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(p: Path) -> dict[str,Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def md(df: pd.DataFrame, n:int=80) -> str:
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("")
    lines=["| "+" | ".join(map(str,d.columns))+" |", "| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows():
        lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ")[:500] for c in d.columns)+" |")
    return "\n".join(lines)


def input_inventory(paths:list[Path]) -> pd.DataFrame:
    rows=[]
    for p in paths:
        rows.append({"path":str(p),"filename":p.name,"exists":p.exists(),"bytes":p.stat().st_size if p.exists() else 0,"sha256":sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def load_candle(tf:str) -> pd.DataFrame:
    p=canonical_dir()/f"gold_v3_gold_hash_2025_primary_{tf}.csv"
    df=pd.read_csv(p)
    df["t"]=pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    for c in ["open","high","low","close","tick_volume","spread","real_volume"]:
        if c in df.columns: df[c]=pd.to_numeric(df[c], errors="coerce")
        else: df[c]=0.0
    return df.sort_values("t").reset_index(drop=True)


def rsi(series: pd.Series, n:int=14) -> pd.Series:
    d=series.diff(); up=d.clip(lower=0); dn=(-d).clip(lower=0)
    au=up.rolling(n, min_periods=n).mean(); ad=dn.rolling(n, min_periods=n).mean()
    rs=au/ad.replace(0,np.nan)
    return 100 - (100/(1+rs))


def add_features(df: pd.DataFrame, tf: str, close_minutes:int) -> pd.DataFrame:
    x=df.copy()
    prefix=tf.lower()
    x[f"{prefix}_close_time"] = x["t"] + pd.Timedelta(minutes=close_minutes)
    x[f"{prefix}_ret1"] = x["close"].pct_change(1)
    x[f"{prefix}_ret4"] = x["close"].pct_change(4)
    x[f"{prefix}_ret16"] = x["close"].pct_change(16)
    x[f"{prefix}_range"] = x["high"] - x["low"]
    x[f"{prefix}_body"] = x["close"] - x["open"]
    x[f"{prefix}_body_abs"] = x[f"{prefix}_body"].abs()
    x[f"{prefix}_upper_wick"] = x["high"] - x[["open","close"]].max(axis=1)
    x[f"{prefix}_lower_wick"] = x[["open","close"]].min(axis=1) - x["low"]
    tr1=x["high"]-x["low"]; tr2=(x["high"]-x["close"].shift(1)).abs(); tr3=(x["low"]-x["close"].shift(1)).abs()
    x[f"{prefix}_tr"] = pd.concat([tr1,tr2,tr3], axis=1).max(axis=1)
    for n in [5,10,20,50,100]:
        x[f"{prefix}_ema{n}"]=x["close"].ewm(span=n, adjust=False, min_periods=n).mean()
        x[f"{prefix}_dist_ema{n}"]=x["close"]-x[f"{prefix}_ema{n}"]
    for n in [14,28,56]:
        x[f"{prefix}_atr{n}"]=x[f"{prefix}_tr"].rolling(n, min_periods=n).mean()
    x[f"{prefix}_rsi14"]=rsi(x["close"],14)
    keep=[f"{prefix}_close_time"]+[c for c in x.columns if c.startswith(prefix+"_") and c != f"{prefix}_close_time"]
    return x[keep]


def asof_join(base: pd.DataFrame, feat: pd.DataFrame, close_col:str, suffix:str) -> tuple[pd.DataFrame, dict[str,Any]]:
    b=base.sort_values("entry_t").copy()
    f=feat.sort_values(close_col).copy()
    before=len(b)
    out=pd.merge_asof(b, f, left_on="entry_t", right_on=close_col, direction="backward")
    matched=int(out[close_col].notna().sum())
    audit={"suffix":suffix,"base_rows":before,"matched_rows":matched,"missing_rows":before-matched,"match_rate":matched/before if before else 0.0,"close_col":close_col}
    return out, audit


def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[upstream03_dir()/"gold_v3_03_summary.json", upstream03_dir()/"gold_v3_03_evaluated_label_rows.csv", canonical_dir()/"gold_v3_gold_hash_2025_primary_m15.csv", canonical_dir()/"gold_v3_gold_hash_2025_primary_h1.csv", canonical_dir()/"gold_v3_gold_hash_2025_primary_h4.csv", canonical_dir()/"gold_v3_gold_hash_2025_primary_d1.csv"]
    inv_df=input_inventory(paths)
    summary03=read_json(paths[0])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=summary03.get("status")==EXPECTED_03_STATUS
    if inputs_ok:
        labels=pd.read_csv(paths[1], usecols=["feature_bar_open_utc","entry_time_utc"])
        base=labels.drop_duplicates().copy()
        base["feature_bar_t"]=pd.to_datetime(base["feature_bar_open_utc"], utc=True, errors="coerce")
        base["entry_t"]=pd.to_datetime(base["entry_time_utc"], utc=True, errors="coerce")
        m15=load_candle("m15"); h1=load_candle("h1"); h4=load_candle("h4"); d1=load_candle("d1")
        f15=add_features(m15,"m15",15); f1=add_features(h1,"h1",60); f4=add_features(h4,"h4",240); fd=add_features(d1,"d1",1440)
        feat=base.sort_values("entry_t")
        feat,a15=asof_join(feat, f15, "m15_close_time", "m15")
        feat,a1=asof_join(feat, f1, "h1_close_time", "h1")
        feat,a4=asof_join(feat, f4, "h4_close_time", "h4")
        feat,ad=asof_join(feat, fd, "d1_close_time", "d1")
        asof_df=pd.DataFrame([a15,a1,a4,ad])
    else:
        base=pd.DataFrame(); feat=pd.DataFrame(); asof_df=pd.DataFrame()
    feature_cols=[c for c in feat.columns if c not in ["feature_bar_open_utc","entry_time_utc","feature_bar_t","entry_t"] and not c.endswith("_close_time")]
    forbidden=[c for c in feature_cols if any(tok in c.lower() for tok in FORBIDDEN_FEATURE_TOKENS)]
    col_inv=pd.DataFrame([{"feature_column":c,"forbidden_token_hit": any(tok in c.lower() for tok in FORBIDDEN_FEATURE_TOKENS)} for c in feature_cols])
    key_audit=pd.DataFrame([{"metric":"base_entry_rows","value":len(base)}, {"metric":"feature_rows","value":len(feat)}, {"metric":"unique_entry_time","value":feat["entry_time_utc"].nunique() if not feat.empty else 0}, {"metric":"feature_columns","value":len(feature_cols)}, {"metric":"forbidden_feature_columns","value":len(forbidden)}])
    if not (inputs_ok and upstream_ok): status="GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif feat.empty or len(forbidden)>0: status="GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_BLOCKED_AUDIT_ONLY"
    else: status="GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_READY_AUDIT_ONLY"
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_03_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["feature_rows_nonempty",len(feat)>0,True,"PASS" if len(feat)>0 else "FAIL"],
        ["forbidden_feature_columns",len(forbidden),0,"PASS" if len(forbidden)==0 else "FAIL"],
        ["labels_or_outcomes_in_features",False,False,"PASS"],
        ["candidate_selection",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-04-001","03 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","03 ready status and evaluated label rows required."],
        ["G3-04-002","entry-time feature matrix","CLOSED" if len(feat)>0 else "OPEN","HARD","Feature rows must be created for base entries."],
        ["G3-04-003","future/outcome leakage","CLOSED" if len(forbidden)==0 else "OPEN","HARD","No outcome/profit/TP/SL/touch/timeout/future/label columns allowed in features."],
        ["G3-04-004","candidate/signal","CLOSED_BLOCKED_BY_POLICY","HARD","No candidate selection or signals in this step."],
        ["G3-04-005","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-04-006","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"base_entry_rows":int(len(base)),"feature_rows":int(len(feat)),"feature_columns":int(len(feature_cols)),"forbidden_feature_columns":forbidden,"features_created":True,"candidate_selection":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_04_input_inventory.csv",index=False,encoding="utf-8-sig")
    feat.drop(columns=["feature_bar_t","entry_t"],errors="ignore").to_csv(out/"gold_v3_04_entry_feature_rows.csv",index=False,encoding="utf-8-sig")
    col_inv.to_csv(out/"gold_v3_04_feature_column_inventory.csv",index=False,encoding="utf-8-sig")
    asof_df.to_csv(out/"gold_v3_04_asof_join_audit.csv",index=False,encoding="utf-8-sig")
    key_audit.to_csv(out/"gold_v3_04_base_entry_key_audit.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_04_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_04_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_04_summary.json",summary)
    report="\n".join(["# GOLD V3 04 entry-time feature matrix audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Key audit",md(key_audit),"","## Asof join audit",md(asof_df),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Features use entry-time/asof candles only.","- No candidate selection, no signals, no ZIP.","- External actions remain OFF."])
    (out/"GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, candidate selection, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
