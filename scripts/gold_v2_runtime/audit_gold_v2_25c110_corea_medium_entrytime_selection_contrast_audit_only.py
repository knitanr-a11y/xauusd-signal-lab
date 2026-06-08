#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C110_COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c110_corea_medium_entrytime_selection_contrast_audit_only"
INPUTS = ["25c109_summary.json", "25c109_primary_replay_targets.csv", "25c109_target_load_matrix.csv"]
EXPECTED_STATUS = "COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_READY_AUDIT_ONLY_LIVE_BLOCKED"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
EXCLUDE_PAT = ["exit_time", "top_exit_time", "close_time", "outcome", "result", "win", "loss", "hit", "mae", "mfe", "realized", "profit", "profit_r", "selected_profit", "selected_profit_r", "top_profit", "top_profit_r", "pnl", "selected", "top_candidate", "top_variant", "top_direction", "final_sot", "arbitration", "priority", "chosen", "prefer", "hash", "path", "file", "report", "status", "reason"]
PREFERRED = {
    "CoreA": ("gold_v2_13b_corea_selected_source_rows.csv", "gold_v2_13b_corea_source_cluster_ledger_normalized.csv"),
    "MEDIUM": ("gold_v2_13d_medium_selected_after_internal_priority.csv", "gold_v2_13d_medium_source_rows_with_manifest_match.csv"),
}


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p

def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root(), files_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found: return found[0]
    return None

def resolve(raw: str) -> Path | None:
    p=Path(str(raw))
    if p.exists(): return p
    return find_file(p.name)

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x,"isoformat") else x

def write_json(p: Path, obj: dict[str, Any]) -> None: p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
def read_json(p: Path|None)->dict[str,Any]:
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
def read_csv(p: Path|None)->pd.DataFrame: return pd.read_csv(p) if p and p.exists() else pd.DataFrame()
def inventory(paths: dict[str, Path|None])->pd.DataFrame:
    rows=[]
    for n,p in paths.items():
        r={"filename":n,"exists":bool(p and p.exists()),"path":str(p) if p else ""}
        if p and p.exists(): r.update({"bytes":p.stat().st_size,"sha256":sha256_file(p)})
        rows.append(r)
    return pd.DataFrame(rows)
def md(df:pd.DataFrame,n:int=80)->str:
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("")
    lines=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ")[:500] for c in d.columns)+" |")
    return "\n".join(lines)
def allowed_col(c:str)->bool:
    low=c.lower()
    if any(p in low for p in EXCLUDE_PAT): return False
    if re.search(r"is_.*selected", low): return False
    return True

def pick_pair(component:str, primary:pd.DataFrame, load:pd.DataFrame)->tuple[Path|None,Path|None,str,str]:
    pref_sel,pref_uni=PREFERRED[component]
    sel_path=None; uni_path=None; sel_name=pref_sel; uni_name=pref_uni
    psel=primary[primary["component"].eq(component)] if not primary.empty else pd.DataFrame()
    if not psel.empty:
        pref=psel[psel["relative_path"].astype(str).str.endswith(pref_sel)]
        row=(pref.iloc[0] if not pref.empty else psel.iloc[0])
        sel_path=resolve(str(row.get("relative_path",""))); sel_name=Path(str(row.get("relative_path",pref_sel))).name
    uni_path=find_file(pref_uni)
    if not uni_path and not load.empty and sel_path:
        sub=load[(load["component"].eq(component)) & (load["readable"].astype(bool))].copy()
        sub=sub[sub["relative_path"].astype(str).apply(lambda x: Path(x).name != sel_path.name)]
        sub=sub[sub["rows"].fillna(0).astype(float) >= 0]
        if not sub.empty:
            sub=sub.sort_values(["rows","risk_score"], ascending=[False,False])
            uni_path=resolve(str(sub.iloc[0].get("relative_path",""))); uni_name=Path(str(sub.iloc[0].get("relative_path",pref_uni))).name
    return sel_path,uni_path,sel_name,uni_name

def contrast(component:str, sel_path:Path|None, uni_path:Path|None)->tuple[dict[str,Any],pd.DataFrame,pd.DataFrame]:
    base={"component":component,"selected_path":str(sel_path) if sel_path else "","universe_path":str(uni_path) if uni_path else "","selected_readable":bool(sel_path and sel_path.exists()),"universe_readable":bool(uni_path and uni_path.exists())}
    if not (sel_path and uni_path and sel_path.exists() and uni_path.exists()):
        return {**base,"selected_rows":0,"universe_rows":0,"entry_signature_columns":0,"selected_rows_with_no_universe_match":0,"selected_rows_with_unique_universe_match":0,"selected_rows_with_ambiguous_universe_match":0,"ambiguous_match_ratio":None,"selected_signature_groups":0,"selected_signature_groups_with_multiple_selected_rows":0}, pd.DataFrame(), pd.DataFrame()
    sel=pd.read_csv(sel_path); uni=pd.read_csv(uni_path)
    common=[c for c in sel.columns if c in uni.columns and allowed_col(c)]
    # avoid exact row-id/date-only overfitting by keeping but flagging in output, not excluding entry_time here.
    sig=common
    if not sig:
        return {**base,"selected_rows":len(sel),"universe_rows":len(uni),"entry_signature_columns":0,"selected_rows_with_no_universe_match":len(sel),"selected_rows_with_unique_universe_match":0,"selected_rows_with_ambiguous_universe_match":0,"ambiguous_match_ratio":1.0,"selected_signature_groups":0,"selected_signature_groups_with_multiple_selected_rows":0}, pd.DataFrame(), pd.DataFrame({"component":[component],"column":[]})
    uni_counts=uni.groupby(sig, dropna=False).size().reset_index(name="universe_match_count")
    joined=sel.merge(uni_counts,on=sig,how="left")
    joined["universe_match_count"]=joined["universe_match_count"].fillna(0).astype(int)
    no=int((joined["universe_match_count"]==0).sum()); uniq=int((joined["universe_match_count"]==1).sum()); amb=int((joined["universe_match_count"]>1).sum())
    sel_groups=sel.groupby(sig,dropna=False).size().reset_index(name="selected_group_rows")
    multi=int((sel_groups["selected_group_rows"]>1).sum())
    ambiguous=joined[joined["universe_match_count"]!=1].copy()
    # add row index for tracing
    ambiguous.insert(0,"selected_row_number_1based", ambiguous.index+1)
    cols_df=pd.DataFrame({"component":component,"entry_signature_column":sig,"is_time_column":["time" in c.lower() for c in sig],"is_id_like_column":[any(t in c.lower() for t in ["id","candidate","origin","variant"]) for c in sig]})
    summary={**base,"selected_rows":int(len(sel)),"universe_rows":int(len(uni)),"entry_signature_columns":int(len(sig)),"selected_rows_with_no_universe_match":no,"selected_rows_with_unique_universe_match":uniq,"selected_rows_with_ambiguous_universe_match":amb,"ambiguous_match_ratio":float(amb/len(sel)) if len(sel) else None,"selected_signature_groups":int(len(sel_groups)),"selected_signature_groups_with_multiple_selected_rows":multi,"universe_rows_in_selected_signature_groups":int(joined["universe_match_count"].sum()),"universe_rows_not_in_selected_signature_groups":None}
    return summary, ambiguous.head(500), cols_df

def main()->int:
    created=datetime.now(timezone.utc).isoformat(); out=out_dir(); paths={n:find_file(n) for n in INPUTS}
    inv=inventory(paths); s109=read_json(paths["25c109_summary.json"]); primary=read_csv(paths["25c109_primary_replay_targets.csv"]); load=read_csv(paths["25c109_target_load_matrix.csv"])
    inputs_ok=bool(inv["exists"].all()) if not inv.empty else False; upstream_ok=s109.get("status")==EXPECTED_STATUS
    summaries=[]; ambs=[]; cols=[]; pair_rows=[]
    for comp in ["CoreA","MEDIUM"]:
        sel,uni,seln,unin=pick_pair(comp,primary,load)
        pair_rows.append({"component":comp,"selected_name":seln,"selected_path":str(sel) if sel else "","selected_readable":bool(sel and sel.exists()),"universe_name":unin,"universe_path":str(uni) if uni else "","universe_readable":bool(uni and uni.exists())})
        sm,amb,cd=contrast(comp,sel,uni); summaries.append(sm)
        if not amb.empty: ambs.append(amb.assign(component=comp))
        if not cd.empty: cols.append(cd)
    summary_df=pd.DataFrame(summaries); amb_df=pd.concat(ambs,ignore_index=True) if ambs else pd.DataFrame(); col_df=pd.concat(cols,ignore_index=True) if cols else pd.DataFrame(); pair_df=pd.DataFrame(pair_rows)
    pairs_ok=bool(pair_df["selected_readable"].all() and pair_df["universe_readable"].all()) if not pair_df.empty else False
    any_amb=bool((summary_df.get("selected_rows_with_ambiguous_universe_match",pd.Series(dtype=int)).fillna(0)>0).any()) if not summary_df.empty else False
    any_no=bool((summary_df.get("selected_rows_with_no_universe_match",pd.Series(dtype=int)).fillna(0)>0).any()) if not summary_df.empty else False
    if not (inputs_ok and upstream_ok and pairs_ok): status="COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif any_amb or any_no: status="COREA_MEDIUM_ENTRYTIME_SELECTION_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
    else: status="COREA_MEDIUM_ENTRYTIME_SELECTION_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    decision=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_25c109_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["pairs_readable",pairs_ok,True,"PASS" if pairs_ok else "FAIL"],
        ["any_ambiguous_match",any_amb,False,"BLOCKED" if any_amb else "PASS"],
        ["any_no_match",any_no,False,"BLOCKED" if any_no else "PASS"],
        ["corea_medium_live_evaluator_allowed",False,False,"PASS"],
        ["final_signal_allowed",False,False,"PASS"],
        ["source_recovery_approved",False,False,"PASS"],
        ["a002_used",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blockers=pd.DataFrame([
        ["B110-001","inputs/pairs","CLOSED" if inputs_ok and upstream_ok and pairs_ok else "OPEN","HARD","25C109 inputs and selected/universe pairs must be readable."],
        ["B110-002","entry-time uniqueness","OPEN" if any_amb or any_no else "REVIEW","HARD","Selected rows are not uniquely identified by entry-time signature." if any_amb or any_no else "Selected rows map uniquely; human review required for time/id overfit."],
        ["B110-003","CoreA/MEDIUM live evaluator","OPEN","HARD","Live remains blocked until full entry-time replay is proven."],
        ["B110-004","source recovery","OPEN","HARD","No source recovery approval."],
        ["B110-005","A002","CLOSED_FOR_MAIN_PATH","INFO","A002 is auxiliary-only and not used."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"upstream_25c109_ok":upstream_ok,"inputs_present":inputs_ok,"pairs_readable":pairs_ok,"any_ambiguous_match":any_amb,"any_no_match":any_no,"corea_medium_live_evaluator_allowed":False,"final_signal_allowed":False,"a002_used":False,"external_actions":ACTIONS}
    pair_df.to_csv(out/"25c110_pair_inventory.csv",index=False,encoding="utf-8-sig")
    summary_df.to_csv(out/"25c110_entrytime_contrast_summary.csv",index=False,encoding="utf-8-sig")
    amb_df.to_csv(out/"25c110_ambiguous_selected_rows.csv",index=False,encoding="utf-8-sig")
    col_df.to_csv(out/"25c110_entry_signature_columns.csv",index=False,encoding="utf-8-sig")
    decision.to_csv(out/"25c110_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blockers.to_csv(out/"25c110_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"25c110_summary.json",summary)
    report="\n".join(["# GOLD V2 25C110 CoreA/MEDIUM entry-time selection contrast audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Decision matrix",md(decision),"","## Pair inventory",md(pair_df),"","## Entry-time contrast summary",md(summary_df),"","## Entry signature columns",md(col_df),"","## Ambiguous/no-match selected rows",md(amb_df),"","## Blockers",md(blockers),"","## Safety","- audit_only: true","- entry-time contrast only; no OHLC replay","- A002 not used","- source recovery not approved","- live evaluator/final signal/external actions remain OFF","- NO_SIGNAL must not notify Discord"])
    (out/"GOLD_V2_25C110_COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    zip_path=fx_outputs()/f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p,arcname=p.name)
    print(json.dumps({"status":status,"output_dir":str(out),"zip":str(zip_path)},ensure_ascii=False,indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__=="__main__": raise SystemExit(main())
