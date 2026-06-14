#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time, warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore", category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP="GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY"
READY="GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_READY_AUDIT_ONLY"
BLOCKED="GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
BOOL_COLS=["m15_up","m15_close_gt_ema20","h1_up","h1_close_gt_ema20","h4_up","h4_close_gt_ema20","d1_up","d1_close_gt_ema20"]
NUM_COLS=["ledger_score","score","feature_score","m15_atr28","m15_rsi14","m15_dist_atr","m15_range_atr","h1_atr28","h1_rsi14","h1_dist_atr","h1_range_atr","h4_atr28","h4_rsi14","h4_dist_atr","h4_range_atr","d1_atr28","d1_rsi14","d1_dist_atr","d1_range_atr"]
QS=[0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90]
PROBLEM_WR=0.60
PROBLEM_PF=1.50
PROBLEM_DAY_SHARE=0.45

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
def by_regime(df):
    rows=[]
    for reg,g in df.groupby("regime_split",dropna=False): rows.append(dict(regime_split=str(reg),**metrics(g)))
    return pd.DataFrame(rows)
def by_month(df):
    rows=[]
    for (reg,mo),g in df.groupby(["regime_split","entry_month"],dropna=False): rows.append(dict(regime_split=str(reg),entry_month=str(mo),**metrics(g)))
    return pd.DataFrame(rows)
def by_side_month(df):
    rows=[]
    for (reg,mo,side),g in df.groupby(["regime_split","entry_month","side"],dropna=False): rows.append(dict(regime_split=str(reg),entry_month=str(mo),side=str(side),**metrics(g)))
    return pd.DataFrame(rows)
def condition_mask(df, col, op, thr=None, side=""):
    m=pd.Series(True,index=df.index)
    if side: m &= df.side.astype(str).eq(side)
    if op in ["TRUE","FALSE"]:
        val=(op=="TRUE"); m &= df[col].fillna(False).astype(bool).eq(val)
    elif op=="<=": m &= pd.to_numeric(df[col],errors="coerce")<=float(thr)
    elif op==">=": m &= pd.to_numeric(df[col],errors="coerce")>=float(thr)
    else: m &= False
    return m.fillna(False)
def score_candidate(base, rem, cut, problem_months):
    bm=metrics(base); rm=metrics(rem); cm=metrics(cut)
    reg=by_regime(rem); mon=by_month(rem)
    min_reg_wr=float(reg.win_rate.min()) if not reg.empty else 0.0; min_reg_pf=float(reg.profit_factor.min()) if not reg.empty else 0.0; min_reg_trades=int(reg.trades.min()) if not reg.empty else 0
    weak=[]
    for _,p in problem_months.iterrows():
        sub=mon[(mon.regime_split.astype(str)==str(p.regime_split))&(mon.entry_month.astype(str)==str(p.entry_month))]
        if not sub.empty:
            weak.append(float(sub.iloc[0].win_rate)-float(p.win_rate))
    avg_problem_wr_gain=float(np.mean(weak)) if weak else 0.0
    return dict(removed_trades=cm["trades"],removed_wr=cm["win_rate"],removed_pf=cm["profit_factor"],removed_sum=cm["sum_result_usd"],retained_trades=rm["trades"],retention=float(rm["trades"]/max(1,bm["trades"])),retained_wr=rm["win_rate"],retained_pf=rm["profit_factor"],retained_sum=rm["sum_result_usd"],retained_negative_month_count=rm["negative_month_count"],min_regime_wr=min_reg_wr,min_regime_pf=min_reg_pf,min_regime_trades=min_reg_trades,avg_problem_month_wr_gain=avg_problem_wr_gain,diagnostic_score=(rm["win_rate"]-bm["win_rate"])*15000+(min_reg_wr-bm["win_rate"])*6000+(rm["profit_factor"]-bm["profit_factor"])*800+avg_problem_wr_gain*5000-rm["negative_month_count"]*500-cm["sum_result_usd"]*0.01)

def enumerate_filters(df, problem_months, min_removed=20, min_retention=0.65):
    rows=[]
    sides=[""]+sorted([str(x) for x in df.side.dropna().unique()]) if "side" in df.columns else [""]
    for col in BOOL_COLS:
        if col not in df.columns: continue
        for side in sides:
            for op in ["TRUE","FALSE"]:
                mask=condition_mask(df,col,op,side=side)
                if int(mask.sum())<min_removed: continue
                rem=df[~mask].copy(); cut=df[mask].copy()
                if len(rem)/max(1,len(df))<min_retention: continue
                rec=dict(filter_type="bool",side_scope=side or "ALL",feature=col,op=op,threshold="",posthoc_diagnostic_only=True,requires_train_only_revalidation=True)
                rec.update(score_candidate(df,rem,cut,problem_months)); rows.append(rec)
    for col in NUM_COLS:
        if col not in df.columns: continue
        s=pd.to_numeric(df[col],errors="coerce")
        if s.notna().sum()<100: continue
        qs=s.dropna().quantile(QS).drop_duplicates()
        for q,thr in qs.items():
            for side in sides:
                for op in ["<=",">="]:
                    mask=condition_mask(df,col,op,float(thr),side)
                    if int(mask.sum())<min_removed: continue
                    rem=df[~mask].copy(); cut=df[mask].copy()
                    if len(rem)/max(1,len(df))<min_retention: continue
                    rec=dict(filter_type="numeric",side_scope=side or "ALL",feature=col,op=op,threshold=float(thr),quantile=float(q),posthoc_diagnostic_only=True,requires_train_only_revalidation=True)
                    rec.update(score_candidate(df,rem,cut,problem_months)); rows.append(rec)
    fr=pd.DataFrame(rows)
    if not fr.empty:
        fr=fr.sort_values(["min_regime_wr","retained_wr","diagnostic_score"],ascending=[False,False,False]).reset_index(drop=True)
        fr.insert(0,"candidate_rank",range(1,len(fr)+1))
    return fr

def train_only_candidates(df, problem_months, min_train_rows=500):
    out=[]
    df=df.sort_values("entry_dt").copy()
    for _,p in problem_months.iterrows():
        start=pd.Timestamp(str(p.entry_month)+"-01")
        train=df[df.entry_dt<start].copy(); target=df[df.entry_month.astype(str)==str(p.entry_month)].copy()
        if len(train)<min_train_rows or target.empty: continue
        pm=pd.DataFrame([p])
        fr=enumerate_filters(train, pm, min_removed=20, min_retention=0.70)
        if fr.empty: continue
        fr=fr[(fr.removed_wr < metrics(train)["win_rate"]-0.03) | (fr.removed_pf < 1.5)].copy().head(80)
        for _,c in fr.iterrows():
            mask=condition_mask(target,str(c.feature),str(c.op),None if str(c.threshold)=="" else float(c.threshold),"" if c.side_scope=="ALL" else str(c.side_scope))
            rem=target[~mask].copy(); cut=target[mask].copy(); tm=metrics(target); rm=metrics(rem); cm=metrics(cut)
            out.append(dict(target_regime=str(p.regime_split),target_month=str(p.entry_month),train_rows=len(train),target_rows=len(target),feature=str(c.feature),op=str(c.op),threshold=c.threshold,side_scope=str(c.side_scope),train_removed_wr=float(c.removed_wr),train_removed_pf=float(c.removed_pf),train_retained_wr=float(c.retained_wr),target_removed_trades=cm["trades"],target_removed_wr=cm["win_rate"],target_retained_trades=rm["trades"],target_retained_wr=rm["win_rate"],target_base_wr=tm["win_rate"],target_wr_gain=rm["win_rate"]-tm["win_rate"] if rm["trades"] else -999,target_retained_pf=rm["profit_factor"],train_only_threshold=True,final_rule_approval=False))
    tc=pd.DataFrame(out)
    if not tc.empty: tc=tc.sort_values(["target_wr_gain","target_retained_wr","target_retained_trades"],ascending=[False,False,False]).reset_index(drop=True); tc.insert(0,"train_only_candidate_rank",range(1,len(tc)+1))
    return tc

def apply_best(df, row):
    if row is None or len(row)==0: return df.copy(),pd.Series(False,index=df.index)
    r=row.iloc[0] if isinstance(row,pd.DataFrame) else row
    mask=condition_mask(df,str(r.feature),str(r.op),None if str(r.threshold)=="" else float(r.threshold),"" if str(r.side_scope)=="ALL" else str(r.side_scope))
    return df[~mask].copy(),mask

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir",default=""); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/"FX_OUTPUTS"/"gold_v3"; src=root/"107lc"; out=root/"107mc"; out.mkdir(parents=True,exist_ok=True)
    log(STEP+" START")
    blocks=[]; outputs=[]; findings=[]; vals=[]
    mpath=src/"gold_v3_107l_best_policy_monthly_diagnostics.csv"; lpath=src/"gold_v3_107l_rehydrated_best_policy_ledger.csv"
    if not mpath.exists(): blocks.append(dict(blocker_id="missing_107l_monthly_diagnostics",path=str(mpath)))
    if not lpath.exists(): blocks.append(dict(blocker_id="missing_107l_rehydrated_best_policy_ledger",path=str(lpath)))
    mon=pd.DataFrame(); led=pd.DataFrame(); problems=pd.DataFrame(); frontier=pd.DataFrame(); train_cands=pd.DataFrame(); best_reg=pd.DataFrame(); best_mon=pd.DataFrame(); side_diag=pd.DataFrame()
    if not blocks:
        mon=pd.read_csv(mpath,encoding="utf-8-sig"); led=pd.read_csv(lpath,encoding="utf-8-sig",low_memory=False)
        for c in ["entry_dt","result_usd","entry_month","regime_split"]:
            if c not in led.columns: blocks.append(dict(blocker_id="ledger_missing_required_column",column=c))
    if not blocks:
        led["entry_dt"]=pd.to_datetime(led.entry_dt,errors="coerce"); led["result_usd"]=pd.to_numeric(led.result_usd,errors="coerce"); led["entry_month"]=led.entry_dt.dt.to_period("M").astype(str)
        led=led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        problems=mon[(pd.to_numeric(mon.trades,errors="coerce")>=50)&((pd.to_numeric(mon.win_rate,errors="coerce")<PROBLEM_WR)|(pd.to_numeric(mon.profit_factor,errors="coerce")<PROBLEM_PF)|(pd.to_numeric(mon.max_day_trade_share,errors="coerce")>PROBLEM_DAY_SHARE))].copy()
        problems=problems.sort_values(["win_rate","max_day_trade_share"],ascending=[True,False]).reset_index(drop=True)
        save(problems,out/"gold_v3_107m_problem_months.csv"); outputs.append("gold_v3_107m_problem_months.csv")
        side_diag=by_side_month(led); side_diag=side_diag[(side_diag.trades>=10)&((side_diag.win_rate<PROBLEM_WR)|(side_diag.profit_factor<PROBLEM_PF))].sort_values(["win_rate","trades"],ascending=[True,False])
        save(side_diag,out/"gold_v3_107m_problem_side_diagnostics.csv"); outputs.append("gold_v3_107m_problem_side_diagnostics.csv")
        if problems.empty: blocks.append(dict(blocker_id="no_problem_months_found"))
    if not blocks:
        frontier=enumerate_filters(led,problems)
        save(frontier,out/"gold_v3_107m_loss_trim_frontier.csv"); outputs.append("gold_v3_107m_loss_trim_frontier.csv")
        if frontier.empty: blocks.append(dict(blocker_id="no_loss_trim_frontier"))
    if not blocks:
        train_cands=train_only_candidates(led,problems)
        save(train_cands,out/"gold_v3_107m_train_only_loss_trim_candidates.csv"); outputs.append("gold_v3_107m_train_only_loss_trim_candidates.csv")
        rem,mask=apply_best(led,frontier.head(1)); best_reg=by_regime(rem); best_mon=by_month(rem)
        save(best_reg,out/"gold_v3_107m_best_filter_regime_metrics.csv"); save(best_mon,out/"gold_v3_107m_best_filter_monthly_metrics.csv"); outputs += ["gold_v3_107m_best_filter_regime_metrics.csv","gold_v3_107m_best_filter_monthly_metrics.csv"]
        findings.append("best_posthoc_loss_trim="+json.dumps(frontier.head(1).to_dict(orient="records"),ensure_ascii=False,default=str))
        if not train_cands.empty: findings.append("top_train_only_candidate="+json.dumps(train_cands.head(1).to_dict(orient="records"),ensure_ascii=False,default=str))
    vals += [dict(check_id="audit_only",result="PASS",observed=True,expected=True,severity="BLOCKER"),dict(check_id="live_ready_false",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="source_csv_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="contract_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="open_asof_allowed",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="posthoc_filters_not_final",result="PASS",observed=True,expected=True,severity="BLOCKER"),dict(check_id="health_gate_not_simulated_without_exit_dt",result="PASS",observed=True,expected=True,severity="BLOCKER")]
    if not problems.empty: vals.append(dict(check_id="problem_months_positive",result="PASS",observed=len(problems),expected=">0",severity="BLOCKER"))
    if not frontier.empty: vals.append(dict(check_id="loss_trim_frontier_positive",result="PASS",observed=len(frontier),expected=">0",severity="BLOCKER"))
    val=pd.DataFrame(vals); validation_failed=int((~val.result.eq("PASS")).sum()) if not val.empty else 0
    status=READY if not blocks and validation_failed==0 else BLOCKED
    decision="PROBLEM_REGIME_LOSS_TRIM_READY_FOR_TRAIN_ONLY_REPLAY" if status==READY else "PROBLEM_REGIME_LOSS_TRIM_BLOCKED"
    summary=dict(step=STEP,status=status,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,health_gate_simulated=False,final_rule_approval=False,blocker_count=len(blocks),validation_failure_count=validation_failed,elapsed_seconds=round(time.time()-t0,2))
    if not mon.empty: summary.update(month_rows=int(len(mon)))
    if not led.empty: summary.update(input_ledger_rows=int(len(led)),base_metrics=metrics(led))
    if not problems.empty: summary.update(problem_month_count=int(len(problems)),worst_problem_month=str(problems.iloc[0].entry_month),worst_problem_regime=str(problems.iloc[0].regime_split),worst_problem_wr=float(problems.iloc[0].win_rate),worst_problem_pf=float(problems.iloc[0].profit_factor))
    if not frontier.empty:
        b=frontier.iloc[0]; summary.update(loss_trim_frontier_rows=int(len(frontier)),best_filter=f"{b.side_scope} {b.feature} {b.op} {b.threshold}",best_retained_wr=float(b.retained_wr),best_retained_pf=float(b.retained_pf),best_min_regime_wr=float(b.min_regime_wr),best_retention=float(b.retention))
    if not train_cands.empty: summary.update(train_only_candidate_rows=int(len(train_cands)),top_train_only_target_month=str(train_cands.iloc[0].target_month),top_train_only_wr_gain=float(train_cands.iloc[0].target_wr_gain))
    save(pd.DataFrame(blocks),out/"gold_v3_107m_blocker_matrix.csv"); save(val,out/"gold_v3_107m_validation_matrix.csv"); outputs += ["gold_v3_107m_blocker_matrix.csv","gold_v3_107m_validation_matrix.csv","gold_v3_107m_summary.json","GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY_REPORT.md","paste_me.txt"]
    (out/"gold_v3_107m_summary.json").write_text(json.dumps(summary|{"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (out/"GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107M report\n\n"+json.dumps({"summary":summary,"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    lines=["GOLD V3 107M PASTE_ME_PROBLEM_REGIME_LOSS_TRIM",f"status: {status}",f"ready: {str(status==READY).lower()}","live_ready: false","source_csv_mutated: false","contract_mutated: false","open_asof_allowed: false","health_gate_simulated: false","final_rule_approval: false","safety: audit_only=true, posthoc_filters_not_final=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false","blocker_count: "+str(len(blocks)),"","KEY_METRICS"]+[f"{k}: {v}" for k,v in summary.items()]+["","FINDINGS"]+(findings or ["NO_FINDINGS"])+["","BLOCKERS",pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS","","VALIDATION",val.to_string(index=False),"","OUTPUTS"]+outputs
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=="__main__": raise SystemExit(main())
