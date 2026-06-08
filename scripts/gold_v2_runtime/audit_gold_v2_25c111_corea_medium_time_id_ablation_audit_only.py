#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C111_COREA_MEDIUM_TIME_ID_ABLATION_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c111_corea_medium_time_id_ablation_audit_only"
INPUTS = ["25c110_summary.json", "25c110_pair_inventory.csv", "25c110_entry_signature_columns.csv", "25c110_entrytime_contrast_summary.csv"]
EXPECTED_STATUS = "COREA_MEDIUM_ENTRYTIME_SELECTION_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
TIME = {"entry_time","top_entry_time","cluster_start","cluster_end","close_time","exit_time"}
MONTH_FOLD = {"entry_month","test_month","fold_id","period","scenario","view"}
IDLIKE = {"cluster_id","candidate_id","origin_id","variant_id","rule_id","component_id","unique_same_direction_origins","unique_same_direction_variants","unique_origins_from_members"}
FEATURE_KEEP = {"atr14","tr_mean_32","range96","range192","trend_eff96","adx14","ret96","regime","is_a","rr","is_b_rr15_fixed","is_c_fixed","signal_abc","same_direction_count","opposite_direction_count","same_direction_score_sum","opposite_direction_score_sum","same_direction_count_from_members","has_opposite_conflict","no_opposite","signal_fixed_abc","signal","signal_trainc_abc","dataset","direction","ruleset","component","component_desc"}


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p
def find_file(name: str) -> Path | None:
    for c in [repo_root()/name, fx_outputs()/name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root(), files_root()]:
        if base.exists():
            found=sorted(base.rglob(name))
            if found: return found[0]
    return None
def resolve(raw:str)->Path|None:
    p=Path(str(raw))
    if p.exists(): return p
    return find_file(p.name)
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()
def clean(x:Any)->Any:
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x,"isoformat") else x
def write_json(p:Path,obj:dict[str,Any])->None: p.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def read_json(p:Path|None)->dict[str,Any]:
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
def read_csv(p:Path|None)->pd.DataFrame: return pd.read_csv(p) if p and p.exists() else pd.DataFrame()
def inventory(paths:dict[str,Path|None])->pd.DataFrame:
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
def norm(c:str)->str: return str(c).lower()
def is_time(c:str)->bool: return norm(c) in TIME or "time" in norm(c)
def is_month_fold(c:str)->bool: return norm(c) in MONTH_FOLD or "month" in norm(c) or "fold" in norm(c)
def is_id(c:str)->bool: return norm(c) in IDLIKE or norm(c).endswith("_id") or "candidate" in norm(c) or "origin" in norm(c) or "variant" in norm(c)
def is_cluster(c:str)->bool: return "cluster" in norm(c)
def variant_cols(component:str, cols:list[str])->dict[str,list[str]]:
    full=cols[:]
    no_time=[c for c in full if not is_time(c)]
    no_time_id=[c for c in no_time if not is_id(c)]
    feature=[c for c in no_time_id if norm(c) in FEATURE_KEEP and not is_month_fold(c) and not is_cluster(c)]
    coarse=feature[:]
    return {"full_25c110_signature":full,"no_time_columns":no_time,"no_time_or_id_columns":no_time_id,"feature_only_no_time_id_cluster_month_fold":feature,"coarse_feature_family_only":coarse}
def coarse_df(df:pd.DataFrame, cols:list[str])->pd.DataFrame:
    out=df[cols].copy()
    for c in cols:
        if pd.api.types.is_numeric_dtype(out[c]):
            s=pd.to_numeric(out[c], errors="coerce")
            # stable coarse bin by rounded magnitude; avoid qcut needing same distribution between selected/universe
            out[c]=s.apply(lambda x: "NA" if pd.isna(x) else f"bin_{math.floor(float(x)/5.0)*5:.0f}")
        else:
            out[c]=out[c].astype(str).fillna("NA")
    return out
def contrast(sel:pd.DataFrame, uni:pd.DataFrame, cols:list[str], component:str, variant:str)->tuple[dict[str,Any], pd.DataFrame]:
    if not cols:
        sm={"component":component,"signature_variant":variant,"signature_columns":0,"selected_rows":len(sel),"universe_rows":len(uni),"selected_unique_matches":0,"selected_ambiguous_matches":0,"selected_no_matches":len(sel),"ambiguous_ratio":1.0 if len(sel) else 0,"no_match_ratio":1.0 if len(sel) else 0,"selected_signature_groups":0,"selected_groups_multi_selected":0}
        return sm,pd.DataFrame()
    sdata=coarse_df(sel, cols) if variant=="coarse_feature_family_only" else sel[cols].copy()
    udata=coarse_df(uni, cols) if variant=="coarse_feature_family_only" else uni[cols].copy()
    ucnt=udata.groupby(cols,dropna=False).size().reset_index(name="universe_match_count")
    joined=sdata.merge(ucnt,on=cols,how="left")
    joined["universe_match_count"]=joined["universe_match_count"].fillna(0).astype(int)
    no=int((joined["universe_match_count"]==0).sum()); uniq=int((joined["universe_match_count"]==1).sum()); amb=int((joined["universe_match_count"]>1).sum())
    sg=sdata.groupby(cols,dropna=False).size().reset_index(name="selected_group_rows")
    multi=int((sg["selected_group_rows"]>1).sum())
    ambrows=joined[joined["universe_match_count"]!=1].copy(); ambrows.insert(0,"selected_row_number_1based",ambrows.index+1); ambrows.insert(0,"signature_variant",variant); ambrows.insert(0,"component",component)
    sm={"component":component,"signature_variant":variant,"signature_columns":len(cols),"selected_rows":len(sel),"universe_rows":len(uni),"selected_unique_matches":uniq,"selected_ambiguous_matches":amb,"selected_no_matches":no,"ambiguous_ratio":float(amb/len(sel)) if len(sel) else 0,"no_match_ratio":float(no/len(sel)) if len(sel) else 0,"selected_signature_groups":len(sg),"selected_groups_multi_selected":multi}
    return sm,ambrows.head(500)

def main()->int:
    created=datetime.now(timezone.utc).isoformat(); out=out_dir(); paths={n:find_file(n) for n in INPUTS}
    inv=inventory(paths); s110=read_json(paths["25c110_summary.json"]); pairs=read_csv(paths["25c110_pair_inventory.csv"]); sigcols=read_csv(paths["25c110_entry_signature_columns.csv"])
    inputs_ok=bool(inv["exists"].all()) if not inv.empty else False; upstream_ok=s110.get("status")==EXPECTED_STATUS
    pair_rows=[]; summaries=[]; sig_rows=[]; ambs=[]
    for _,p in pairs.iterrows():
        comp=str(p.get("component","")); selp=resolve(str(p.get("selected_path",""))); unip=resolve(str(p.get("universe_path","")))
        readable=bool(selp and unip and selp.exists() and unip.exists())
        pair_rows.append({"component":comp,"selected_path":str(selp) if selp else "","universe_path":str(unip) if unip else "","pair_readable":readable})
        if not readable: continue
        sel=pd.read_csv(selp); uni=pd.read_csv(unip)
        cols=sigcols[sigcols["component"].eq(comp)]["entry_signature_column"].dropna().astype(str).tolist()
        # ensure common columns only
        cols=[c for c in cols if c in sel.columns and c in uni.columns]
        variants=variant_cols(comp, cols)
        for v,vc in variants.items():
            sm,amb=contrast(sel,uni,vc,comp,v); summaries.append(sm)
            if not amb.empty: ambs.append(amb)
            for c in vc: sig_rows.append({"component":comp,"signature_variant":v,"column":c,"is_time":is_time(c),"is_id":is_id(c),"is_month_fold":is_month_fold(c),"is_cluster":is_cluster(c)})
    pair_df=pd.DataFrame(pair_rows); sum_df=pd.DataFrame(summaries); sig_df=pd.DataFrame(sig_rows); amb_df=pd.concat(ambs,ignore_index=True) if ambs else pd.DataFrame()
    pairs_ok=bool(pair_df["pair_readable"].all()) if not pair_df.empty else False
    critical=sum_df[sum_df["signature_variant"].isin(["no_time_columns","no_time_or_id_columns","feature_only_no_time_id_cluster_month_fold","coarse_feature_family_only"])] if not sum_df.empty else pd.DataFrame()
    ambiguity=bool(((critical.get("selected_ambiguous_matches",pd.Series(dtype=int)).fillna(0)>0)|(critical.get("selected_no_matches",pd.Series(dtype=int)).fillna(0)>0)).any()) if not critical.empty else True
    feature_rows=critical[critical["signature_variant"].eq("feature_only_no_time_id_cluster_month_fold")]
    feature_unique=not feature_rows.empty and bool(((feature_rows["selected_ambiguous_matches"].fillna(0)==0)&(feature_rows["selected_no_matches"].fillna(0)==0)).all())
    if not (inputs_ok and upstream_ok and pairs_ok): status="COREA_MEDIUM_TIME_ID_ABLATION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif ambiguity: status="COREA_MEDIUM_TIME_ID_ABLATION_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
    elif feature_unique: status="COREA_MEDIUM_FEATURE_ONLY_UNIQUENESS_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    else: status="COREA_MEDIUM_TIME_ID_ABLATION_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
    decision=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_25c110_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["pairs_readable",pairs_ok,True,"PASS" if pairs_ok else "FAIL"],
        ["ablation_ambiguity_or_no_match",ambiguity,False,"BLOCKED" if ambiguity else "PASS"],
        ["feature_only_unique",feature_unique,True,"REVIEW" if feature_unique else "BLOCKED"],
        ["corea_medium_live_evaluator_allowed",False,False,"PASS"],
        ["final_signal_allowed",False,False,"PASS"],
        ["source_recovery_approved",False,False,"PASS"],
        ["a002_used",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blockers=pd.DataFrame([
        ["B111-001","25C110 inputs","CLOSED" if inputs_ok and upstream_ok and pairs_ok else "OPEN","HARD","25C110 outputs and pairs must be readable."],
        ["B111-002","time/id ablation ambiguity","OPEN" if ambiguity else "REVIEW","HARD","Uniqueness breaks after removing time/id/history keys." if ambiguity else "Feature-only uniqueness candidate requires human/asof review."],
        ["B111-003","CoreA/MEDIUM live evaluator","OPEN","HARD","Live remains blocked until full entry-time replay and HTF/asof parity are proven."],
        ["B111-004","source recovery","OPEN","HARD","No source recovery approval."],
        ["B111-005","A002","CLOSED_FOR_MAIN_PATH","INFO","A002 is auxiliary-only and not used."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"upstream_25c110_ok":upstream_ok,"inputs_present":inputs_ok,"pairs_readable":pairs_ok,"ablation_ambiguity_or_no_match":ambiguity,"feature_only_unique":feature_unique,"corea_medium_live_evaluator_allowed":False,"final_signal_allowed":False,"a002_used":False,"external_actions":ACTIONS}
    pair_df.to_csv(out/"25c111_pair_inventory.csv",index=False,encoding="utf-8-sig")
    sum_df.to_csv(out/"25c111_ablation_summary.csv",index=False,encoding="utf-8-sig")
    sig_df.to_csv(out/"25c111_ablation_signature_columns.csv",index=False,encoding="utf-8-sig")
    amb_df.to_csv(out/"25c111_ablation_ambiguous_rows.csv",index=False,encoding="utf-8-sig")
    decision.to_csv(out/"25c111_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blockers.to_csv(out/"25c111_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"25c111_summary.json",summary)
    report="\n".join(["# GOLD V2 25C111 CoreA/MEDIUM time-ID ablation audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Decision matrix",md(decision),"","## Ablation summary",md(sum_df),"","## Ablation signature columns",md(sig_df),"","## Ambiguous/no-match rows",md(amb_df),"","## Blockers",md(blockers),"","## Safety","- audit_only: true","- ablation only; no OHLC replay","- A002 not used","- source recovery not approved","- live evaluator/final signal/external actions remain OFF","- NO_SIGNAL must not notify Discord"])
    (out/"GOLD_V2_25C111_COREA_MEDIUM_TIME_ID_ABLATION_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    zip_path=fx_outputs()/f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p,arcname=p.name)
    print(json.dumps({"status":status,"output_dir":str(out),"zip":str(zip_path)},ensure_ascii=False,indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0
if __name__=="__main__": raise SystemExit(main())
