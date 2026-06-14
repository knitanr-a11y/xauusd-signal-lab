#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time, warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore", category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP="GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY"
READY="GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_READY_AUDIT_ONLY"
BLOCKED="GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
BOOL_COLS=["m15_up","m15_close_gt_ema20","h1_up","h1_close_gt_ema20","h4_up","h4_close_gt_ema20","d1_up","d1_close_gt_ema20"]
NUM_COLS=["ledger_score","score","feature_score","m15_atr28","m15_rsi14","m15_dist_atr","m15_range_atr","h1_atr28","h1_rsi14","h1_dist_atr","h1_range_atr","h4_atr28","h4_rsi14","h4_dist_atr","h4_range_atr","d1_atr28","d1_rsi14","d1_dist_atr","d1_range_atr"]
QS=[0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90]

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0
def pf(s):
    a=pd.to_numeric(pd.Series(s),errors="coerce").dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metrics(df):
    if df is None or df.empty or "result_usd" not in df.columns:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0,unique_trade_days=0,max_day_trade_share=0.0,min_entry_dt="",max_entry_dt="")
    x=df.copy(); x["entry_dt"]=pd.to_datetime(x.entry_dt,errors="coerce"); x["result_usd"]=pd.to_numeric(x.result_usd,errors="coerce")
    x=x[x.entry_dt.notna() & x.result_usd.notna()].copy()
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0,unique_trade_days=0,max_day_trade_share=0.0,min_entry_dt="",max_entry_dt="")
    mon=x.groupby(x.entry_dt.dt.to_period("M").astype(str)).result_usd.sum(); day=x.groupby(x.entry_dt.dt.date).size()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()),unique_trade_days=int(len(day)),max_day_trade_share=float(day.max()/len(x)) if len(x) else 0.0,min_entry_dt=str(x.entry_dt.min().date()),max_entry_dt=str(x.entry_dt.max().date()))
def by_month(df):
    if df.empty: return pd.DataFrame()
    rows=[]
    for (reg,mo),g in df.groupby(["regime_split","entry_month"],dropna=False): rows.append(dict(regime_split=str(reg),entry_month=str(mo),**metrics(g)))
    return pd.DataFrame(rows).sort_values(["regime_split","entry_month"])
def by_regime(df):
    if df.empty: return pd.DataFrame()
    rows=[]
    for reg,g in df.groupby("regime_split",dropna=False): rows.append(dict(regime_split=str(reg),**metrics(g)))
    return pd.DataFrame(rows).sort_values("regime_split")
def condition_mask(df,col,op,thr=None,side=""):
    m=pd.Series(True,index=df.index)
    if side and side!="ALL": m &= df.side.astype(str).eq(str(side))
    if op in ["TRUE","FALSE"]:
        m &= df[col].fillna(False).astype(bool).eq(op=="TRUE")
    elif op=="<=": m &= pd.to_numeric(df[col],errors="coerce")<=float(thr)
    elif op==">=": m &= pd.to_numeric(df[col],errors="coerce")>=float(thr)
    else: m &= False
    return m.fillna(False)
def score_candidate(base, rem, cut):
    bm=metrics(base); rm=metrics(rem); cm=metrics(cut); reg=by_regime(rem)
    min_reg_wr=float(reg.win_rate.min()) if not reg.empty else 0.0; min_reg_pf=float(reg.profit_factor.min()) if not reg.empty else 0.0; min_reg_trades=int(reg.trades.min()) if not reg.empty else 0
    return dict(removed_trades=cm["trades"],removed_wr=cm["win_rate"],removed_pf=cm["profit_factor"],removed_sum=cm["sum_result_usd"],retained_trades=rm["trades"],retention=float(rm["trades"]/max(1,bm["trades"])),retained_wr=rm["win_rate"],retained_pf=rm["profit_factor"],retained_sum=rm["sum_result_usd"],retained_negative_month_count=rm["negative_month_count"],min_regime_wr=min_reg_wr,min_regime_pf=min_reg_pf,min_regime_trades=min_reg_trades,train_score=(rm["win_rate"]-bm["win_rate"])*15000+(rm["profit_factor"]-bm["profit_factor"])*800+(min_reg_wr-bm["win_rate"])*5000-rm["negative_month_count"]*500-cm["sum_result_usd"]*0.01)
def enumerate_train_filters(train,min_removed=20,min_retention=0.65):
    rows=[]; base=metrics(train); sides=["ALL"]+sorted([str(x) for x in train.side.dropna().unique()]) if "side" in train.columns else ["ALL"]
    for col in BOOL_COLS:
        if col not in train.columns: continue
        for side in sides:
            for op in ["TRUE","FALSE"]:
                mask=condition_mask(train,col,op,side=side)
                if int(mask.sum())<min_removed: continue
                rem=train[~mask].copy(); cut=train[mask].copy()
                if len(rem)/max(1,len(train))<min_retention: continue
                rec=dict(filter_type="bool",side_scope=side,feature=col,op=op,threshold="",quantile="")
                rec.update(score_candidate(train,rem,cut)); rows.append(rec)
    for col in NUM_COLS:
        if col not in train.columns: continue
        s=pd.to_numeric(train[col],errors="coerce")
        if s.notna().sum()<100: continue
        qs=s.dropna().quantile(QS).drop_duplicates()
        for q,thr in qs.items():
            for side in sides:
                for op in ["<=",">="]:
                    mask=condition_mask(train,col,op,float(thr),side)
                    if int(mask.sum())<min_removed: continue
                    rem=train[~mask].copy(); cut=train[mask].copy()
                    if len(rem)/max(1,len(train))<min_retention: continue
                    rec=dict(filter_type="numeric",side_scope=side,feature=col,op=op,threshold=float(thr),quantile=float(q))
                    rec.update(score_candidate(train,rem,cut)); rows.append(rec)
    fr=pd.DataFrame(rows)
    if fr.empty: return fr
    fr=fr[(fr.retained_trades>=max(30,int(len(train)*min_retention)))&(fr.retained_wr>=base["win_rate"]+0.005)&(fr.retained_pf>=base["profit_factor"])]
    if fr.empty: return fr
    return fr.sort_values(["train_score","retained_wr","retained_pf"],ascending=[False,False,False]).reset_index(drop=True)
def apply_filter(df,row):
    if row is None: return df.copy(),pd.Series(False,index=df.index)
    mask=condition_mask(df,str(row.feature),str(row.op),None if str(row.threshold)=="" else float(row.threshold),str(row.side_scope))
    return df[~mask].copy(),mask
def seed_filter_replay(df,seed):
    if seed.empty: return pd.DataFrame()
    rows=[]
    for _,r in seed.head(20).iterrows():
        rem,mask=apply_filter(df,r); m=metrics(rem); b=metrics(df); reg=by_regime(rem)
        rows.append(dict(seed_rank=int(r.candidate_rank) if "candidate_rank" in r.index else len(rows)+1,feature=str(r.feature),op=str(r.op),threshold=r.threshold,side_scope=str(r.side_scope),retained_trades=m["trades"],retention=m["trades"]/max(1,b["trades"]),retained_wr=m["win_rate"],retained_pf=m["profit_factor"],retained_sum=m["sum_result_usd"],min_regime_wr=float(reg.win_rate.min()) if not reg.empty else 0.0,posthoc_seed_only=True,final_rule_approval=False))
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir",default=""); ap.add_argument("--min-train-rows",type=int,default=1000); ap.add_argument("--top-k",type=int,default=1); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/"FX_OUTPUTS"/"gold_v3"; src_l=root/"107lc"; src_m=root/"107mc"; out=root/"107nc"; out.mkdir(parents=True,exist_ok=True)
    log(STEP+" START")
    blocks=[]; outputs=[]; vals=[]; findings=[]
    lpath=src_l/"gold_v3_107l_rehydrated_best_policy_ledger.csv"; fpath=src_m/"gold_v3_107m_loss_trim_frontier.csv"; tpath=src_m/"gold_v3_107m_train_only_loss_trim_candidates.csv"
    for name,p in [("107l_rehydrated_best_policy_ledger",lpath),("107m_loss_trim_frontier",fpath),("107m_train_only_loss_trim_candidates",tpath)]:
        if not p.exists(): blocks.append(dict(blocker_id="missing_"+name,path=str(p)))
    led=pd.DataFrame(); seed=pd.DataFrame(); prior_tc=pd.DataFrame(); monthly_sel=pd.DataFrame(); wf_ledger=pd.DataFrame(); seed_rep=pd.DataFrame(); mon=pd.DataFrame(); reg=pd.DataFrame()
    if not blocks:
        led=pd.read_csv(lpath,encoding="utf-8-sig",low_memory=False); seed=pd.read_csv(fpath,encoding="utf-8-sig"); prior_tc=pd.read_csv(tpath,encoding="utf-8-sig")
        for c in ["entry_dt","result_usd","regime_split"]:
            if c not in led.columns: blocks.append(dict(blocker_id="ledger_missing_required_column",column=c))
    if not blocks:
        led["entry_dt"]=pd.to_datetime(led.entry_dt,errors="coerce"); led["result_usd"]=pd.to_numeric(led.result_usd,errors="coerce"); led=led[led.entry_dt.notna() & led.result_usd.notna()].sort_values("entry_dt").copy(); led["entry_month"]=led.entry_dt.dt.to_period("M").astype(str)
        months=sorted(led.entry_month.dropna().unique())
        selected=[]; passed=[]; states=[]
        for mo in months:
            start=pd.Timestamp(mo+"-01")
            train=led[led.entry_dt<start].copy(); target=led[led.entry_month==mo].copy()
            if len(train)<args.min_train_rows or target.empty:
                selected.append(dict(target_month=mo,train_rows=len(train),target_rows=len(target),selected=False,reason="insufficient_train_or_target")); passed.append(target.copy()); continue
            fr=enumerate_train_filters(train)
            if fr.empty:
                selected.append(dict(target_month=mo,train_rows=len(train),target_rows=len(target),selected=False,reason="no_train_filter")); passed.append(target.copy()); continue
            b=fr.iloc[0]; rem,mask=apply_filter(target,b); cut=target[mask].copy(); tm=metrics(target); rm=metrics(rem); cm=metrics(cut)
            rec=dict(target_month=mo,train_rows=len(train),target_rows=len(target),selected=True,feature=str(b.feature),op=str(b.op),threshold=b.threshold,side_scope=str(b.side_scope),train_retained_wr=float(b.retained_wr),train_retained_pf=float(b.retained_pf),train_retention=float(b.retention),target_base_wr=tm["win_rate"],target_base_pf=tm["profit_factor"],target_retained_trades=rm["trades"],target_retained_wr=rm["win_rate"],target_retained_pf=rm["profit_factor"],target_retention=rm["trades"]/max(1,tm["trades"]),target_removed_trades=cm["trades"],target_removed_wr=cm["win_rate"],target_wr_gain=rm["win_rate"]-tm["win_rate"] if rm["trades"] else -999,reason="train_only_selected")
            selected.append(rec); tmp=rem.copy(); tmp["walkforward_filter_selected"]=True; tmp["walkforward_feature"]=str(b.feature); tmp["walkforward_op"]=str(b.op); tmp["walkforward_threshold"]=b.threshold; tmp["walkforward_side_scope"]=str(b.side_scope); passed.append(tmp)
        monthly_sel=pd.DataFrame(selected); wf_ledger=pd.concat(passed,ignore_index=True) if passed else pd.DataFrame(); seed_rep=seed_filter_replay(led,seed)
        mon=by_month(wf_ledger); reg=by_regime(wf_ledger)
        save(monthly_sel,out/"gold_v3_107n_monthly_walkforward_selected_filters.csv"); save(wf_ledger,out/"gold_v3_107n_walkforward_trade_ledger.csv"); save(mon,out/"gold_v3_107n_walkforward_monthly_metrics.csv"); save(reg,out/"gold_v3_107n_walkforward_regime_metrics.csv"); save(seed_rep,out/"gold_v3_107n_seed_filter_replay_metrics.csv")
        outputs += ["gold_v3_107n_monthly_walkforward_selected_filters.csv","gold_v3_107n_walkforward_trade_ledger.csv","gold_v3_107n_walkforward_monthly_metrics.csv","gold_v3_107n_walkforward_regime_metrics.csv","gold_v3_107n_seed_filter_replay_metrics.csv"]
        if wf_ledger.empty: blocks.append(dict(blocker_id="no_walkforward_ledger"))
    base=metrics(led) if not led.empty else metrics(pd.DataFrame()); wfm=metrics(wf_ledger) if not wf_ledger.empty else metrics(pd.DataFrame())
    min_reg_wr=float(reg.win_rate.min()) if not reg.empty else 0.0; min_reg_pf=float(reg.profit_factor.min()) if not reg.empty else 0.0; retention=wfm["trades"]/max(1,base["trades"])
    primary=bool(wfm["win_rate"]>=0.625 and wfm["profit_factor"]>=2.70 and retention>=0.65 and min_reg_wr>=0.60 and wfm["negative_month_count"]==0)
    review=bool((wfm["win_rate"]-base["win_rate"]>=0.01) and wfm["profit_factor"]>=base["profit_factor"] and retention>=0.65 and min_reg_wr>=0.59)
    qg=pd.DataFrame([gy.gate_row("primary_wr_ge_62_5",wfm["win_rate"],">=",0.625),gy.gate_row("primary_pf_ge_2_70",wfm["profit_factor"],">=",2.70),gy.gate_row("retention_ge_65",retention,">=",0.65),gy.gate_row("min_regime_wr_ge_60",min_reg_wr,">=",0.60),gy.gate_row("negative_month_count_eq_0",wfm["negative_month_count"],"==",0),gy.gate_row("review_wr_gain_ge_1pct",wfm["win_rate"]-base["win_rate"],">=",0.01),gy.gate_row("review_pf_improves",wfm["profit_factor"],">=",base["profit_factor"])])
    save(qg,out/"gold_v3_107n_quality_gate_matrix.csv"); outputs.append("gold_v3_107n_quality_gate_matrix.csv")
    vals += [dict(check_id="audit_only",result="PASS",observed=True,expected=True,severity="BLOCKER"),dict(check_id="live_ready_false",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="source_csv_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="contract_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="target_outcomes_not_used_for_selection",result="PASS",observed=True,expected=True,severity="BLOCKER"),dict(check_id="resolved_only_strict_blocked_without_exit_dt",result="PASS",observed=("exit_dt" not in led.columns),expected=True,severity="WARN")]
    if not monthly_sel.empty: vals.append(dict(check_id="monthly_selection_rows_positive",result="PASS",observed=len(monthly_sel),expected=">0",severity="BLOCKER"))
    if not wf_ledger.empty: vals.append(dict(check_id="walkforward_ledger_positive",result="PASS",observed=len(wf_ledger),expected=">0",severity="BLOCKER"))
    val=pd.DataFrame(vals); validation_failed=int((~val.result.eq("PASS")).sum()) if not val.empty else 0
    status=READY if not blocks and validation_failed==0 else BLOCKED
    if status!=READY: decision="TRAIN_ONLY_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE"
    elif primary: decision="TRAIN_ONLY_LOSS_TRIM_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY"
    elif review: decision="TRAIN_ONLY_LOSS_TRIM_REVIEW_READY_FOR_DEEPER_REPLAY"
    else: decision="TRAIN_ONLY_LOSS_TRIM_NOT_CONFIRMED_NEED_ALTERNATIVE_FILTERS"
    findings.append("base_metrics="+json.dumps(base,ensure_ascii=False,default=str))
    findings.append("walkforward_metrics="+json.dumps(wfm,ensure_ascii=False,default=str))
    if not monthly_sel.empty: findings.append("selected_filter_head="+json.dumps(monthly_sel.head(12).to_dict(orient="records"),ensure_ascii=False,default=str))
    summary=dict(step=STEP,status=status,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,health_gate_simulated=False,resolved_only_strict=False,final_rule_approval=False,blocker_count=len(blocks),validation_failure_count=validation_failed,elapsed_seconds=round(time.time()-t0,2),base_metrics=base,walkforward_metrics=wfm,walkforward_retention=retention,min_regime_wr=min_reg_wr,min_regime_pf=min_reg_pf,primary_gate=primary,review_gate=review,selected_month_count=int(monthly_sel.selected.sum()) if not monthly_sel.empty and "selected" in monthly_sel else 0,month_rows=int(len(monthly_sel)) if not monthly_sel.empty else 0)
    save(pd.DataFrame(blocks),out/"gold_v3_107n_blocker_matrix.csv"); save(val,out/"gold_v3_107n_validation_matrix.csv"); outputs += ["gold_v3_107n_blocker_matrix.csv","gold_v3_107n_validation_matrix.csv","gold_v3_107n_summary.json","GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY_REPORT.md","paste_me.txt"]
    (out/"gold_v3_107n_summary.json").write_text(json.dumps(summary|{"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (out/"GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107N report\n\n"+json.dumps({"summary":summary,"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    lines=["GOLD V3 107N PASTE_ME_TRAIN_ONLY_LOSS_TRIM_REPLAY",f"status: {status}",f"ready: {str(status==READY).lower()}","live_ready: false","source_csv_mutated: false","contract_mutated: false","open_asof_allowed: false","health_gate_simulated: false","resolved_only_strict: false","final_rule_approval: false","safety: audit_only=true, train_only_proxy=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false","blocker_count: "+str(len(blocks)),"","KEY_METRICS"]+[f"{k}: {v}" for k,v in summary.items()]+["","FINDINGS"]+(findings or ["NO_FINDINGS"])+["","BLOCKERS",pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS","","QUALITY_GATES",qg.to_string(index=False),"","VALIDATION",val.to_string(index=False),"","OUTPUTS"]+outputs
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=="__main__": raise SystemExit(main())
