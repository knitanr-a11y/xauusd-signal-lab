#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time, warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore", category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP="GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY"
READY="GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_READY_AUDIT_ONLY"
BLOCKED="GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
MODES=["shadow_history","traded_only"]
MIN_HIST=[0,5,10,20,30]
MIN_WR=[0.0,0.50,0.55,0.60]
MIN_PF=[0.0,1.0,1.3,1.5]
LOOKBACK=[0,20,50,100]
REQ_FRONTIER=["policy_key","regime_split","regime_group","oos_trades","oos_wins","oos_losses","oos_win_rate","oos_profit_factor","oos_sum_result_usd","oos_unique_trade_days","oos_max_day_trade_share","regime_pass_60","regime_pass_65","regime_score"]

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
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0,unique_trade_days=0,date_span_days=0,max_day_trades=0,max_day_trade_share=0.0,business_day_trade_rate=0.0,active_trade_day_rate=0.0,min_entry_dt="",max_entry_dt="")
    x=df.copy()
    x["entry_dt"]=pd.to_datetime(x["entry_dt"],errors="coerce")
    x["result_usd"]=pd.to_numeric(x["result_usd"],errors="coerce")
    x=x[x["entry_dt"].notna() & x["result_usd"].notna()].copy()
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0,unique_trade_days=0,date_span_days=0,max_day_trades=0,max_day_trade_share=0.0,business_day_trade_rate=0.0,active_trade_day_rate=0.0,min_entry_dt="",max_entry_dt="")
    mon=x.groupby(x["entry_dt"].dt.to_period("M").astype(str))["result_usd"].sum()
    day=x.groupby(x["entry_dt"].dt.date).size().reset_index(name="n")
    mn=x["entry_dt"].min().date(); mx=x["entry_dt"].max().date()
    span=(mx-mn).days+1; bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,"D")))
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()),unique_trade_days=int(len(day)),date_span_days=int(span),max_day_trades=int(day.n.max()),max_day_trade_share=float(day.n.max()/len(x)),business_day_trade_rate=float(len(x)/bd) if bd else 0.0,active_trade_day_rate=float(len(x)/len(day)) if len(day) else 0.0,min_entry_dt=str(mn),max_entry_dt=str(mx))
def bs(s): return s.astype(str).str.lower().isin(["true","1","yes"])

def aggregate_balanced(per):
    rows=[]
    for key,gp in per.groupby("policy_key"):
        b=gp.sort_values("regime_score",ascending=False).groupby("regime_group").head(1)
        have25=bool((b.regime_group=="2025").any()); have26=bool((b.regime_group=="2026_HIGHVOL").any())
        rec=dict(policy_key=str(key),regime_count=int(b.regime_group.nunique()),have_2025=have25,have_2026_highvol=have26,min_wr=float(b.oos_win_rate.min()),min_pf=float(b.oos_profit_factor.min()),min_trades=int(b.oos_trades.min()),min_unique_days=int(b.oos_unique_trade_days.min()),max_day_trade_share=float(b.oos_max_day_trade_share.max()),sum_trades=int(b.oos_trades.sum()),avg_wr=float(b.oos_win_rate.mean()),all_regime_pass_60=bool(have25 and have26 and bs(b.regime_pass_60).all()),all_regime_pass_65=bool(have25 and have26 and bs(b.regime_pass_65).all()))
        rec["balanced_score"]=rec["min_wr"]*15000+cap(rec["min_pf"])*1000+rec["min_trades"]*0.5+rec["sum_trades"]*0.1-rec["max_day_trade_share"]*1000
        rows.append(rec)
    bal=pd.DataFrame(rows)
    if bal.empty: return bal,pd.DataFrame()
    bal=bal.sort_values(["all_regime_pass_65","all_regime_pass_60","balanced_score"],ascending=[False,False,False]).reset_index(drop=True)
    best_key=str(bal.iloc[0].policy_key)
    best_rows=per[per.policy_key.astype(str)==best_key].sort_values("regime_score",ascending=False).groupby("regime_group").head(1).copy()
    return bal,best_rows

def parity_rows(frontier_rows, led):
    out=[]
    for _,fr in frontier_rows.iterrows():
        reg=str(fr.regime_split); x=led[led.regime_split.astype(str)==reg].copy(); m=metrics(x)
        fpf=float(fr.oos_profit_factor); mpf=float(m["profit_factor"])
        rec=dict(regime_split=reg,ledger_rows=len(x),frontier_trades=int(fr.oos_trades),rehydrated_trades=m["trades"],frontier_wins=int(fr.oos_wins),rehydrated_wins=m["wins"],frontier_losses=int(fr.oos_losses),rehydrated_losses=m["losses"],frontier_wr=float(fr.oos_win_rate),rehydrated_wr=m["win_rate"],wr_abs_diff=abs(float(fr.oos_win_rate)-m["win_rate"]),frontier_pf=fpf,rehydrated_pf=mpf,pf_abs_diff=0.0 if math.isinf(fpf) and math.isinf(mpf) else abs(fpf-mpf),frontier_sum=float(fr.oos_sum_result_usd),rehydrated_sum=m["sum_result_usd"],sum_abs_diff=abs(float(fr.oos_sum_result_usd)-m["sum_result_usd"]),frontier_unique_days=int(fr.oos_unique_trade_days),rehydrated_unique_days=m["unique_trade_days"])
        rec["metric_match"]=bool(rec["frontier_trades"]==rec["rehydrated_trades"] and rec["frontier_wins"]==rec["rehydrated_wins"] and rec["frontier_losses"]==rec["rehydrated_losses"] and rec["frontier_unique_days"]==rec["rehydrated_unique_days"] and rec["wr_abs_diff"]<=1e-12 and rec["pf_abs_diff"]<=1e-9 and rec["sum_abs_diff"]<=1e-6)
        out.append(rec)
    return pd.DataFrame(out)

def monthly_rows(led):
    if led.empty: return pd.DataFrame()
    x=led.copy(); x["entry_dt"]=pd.to_datetime(x.entry_dt,errors="coerce"); x["result_usd"]=pd.to_numeric(x.result_usd,errors="coerce")
    x=x[x.entry_dt.notna() & x.result_usd.notna()].copy(); x["entry_month"]=x.entry_dt.dt.to_period("M").astype(str)
    rows=[]
    for (reg,mon),g in x.groupby(["regime_split","entry_month"]):
        m=metrics(g); rows.append(dict(regime_split=reg,entry_month=mon,**m))
    return pd.DataFrame(rows).sort_values(["regime_split","entry_month"]) if rows else pd.DataFrame()

def health_ok(hist,min_hist,min_wr,min_pf,lookback):
    if hist is None or hist.empty: return min_hist==0
    h=hist.sort_values("exit_dt").copy()
    if lookback and len(h)>lookback: h=h.tail(lookback)
    if len(h)<min_hist: return min_hist==0
    m=metrics(h); return bool(m["win_rate"]>=min_wr and m["profit_factor"]>=min_pf)
def simulate(led,mode,min_hist,min_wr,min_pf,lookback):
    cand=led.sort_values("entry_dt").copy(); accepted=[]; rows=[]
    for _,r in cand.iterrows():
        now=pd.Timestamp(r.entry_dt)
        if mode=="shadow_history":
            hist=cand[pd.to_datetime(cand.exit_dt,errors="coerce")<=now].copy()
        else:
            hist=pd.DataFrame(accepted)
            if not hist.empty: hist=hist[pd.to_datetime(hist.exit_dt,errors="coerce")<=now].copy()
        ok=health_ok(hist,min_hist,min_wr,min_pf,lookback)
        rr=r.to_dict(); rr.update(health_pass=bool(ok),health_history_count=int(len(hist)),health_mode=mode,min_history=min_hist,min_wr=min_wr,min_pf=min_pf,lookback_resolved=lookback)
        rows.append(rr)
        if ok: accepted.append(r.to_dict())
    state=pd.DataFrame(rows); passed=state[state.health_pass].copy() if not state.empty else pd.DataFrame()
    return passed,state

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir",default=""); ap.add_argument("--policy-key",default=""); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/"FX_OUTPUTS"/"gold_v3"; src=root/"107k2c"; out=root/"107lc"; out.mkdir(parents=True,exist_ok=True)
    log(STEP+" START")
    blocks=[]; outputs=[]; vals=[]; findings=[]; decision="INPUT_BLOCKED"
    fpath=src/"gold_v3_107k2_regime_frontier.csv"; lpath=src/"gold_v3_107k2_all_regime_ledgers.csv"
    if not fpath.exists(): blocks.append(dict(blocker_id="missing_107k2_regime_frontier",path=str(fpath)))
    if not lpath.exists(): blocks.append(dict(blocker_id="missing_107k2_all_regime_ledgers",path=str(lpath)))
    per=pd.DataFrame(); led=pd.DataFrame(); bal=pd.DataFrame(); best_rows=pd.DataFrame(); best_led=pd.DataFrame(); parity=pd.DataFrame(); exit_pre=pd.DataFrame(); health_frontier=pd.DataFrame()
    if not blocks:
        per=pd.read_csv(fpath,encoding="utf-8-sig"); miss=[c for c in REQ_FRONTIER if c not in per.columns]
        if miss: blocks.append(dict(blocker_id="frontier_missing_required_columns",missing_columns=",".join(miss),path=str(fpath)))
    if not blocks:
        led=pd.read_csv(lpath,encoding="utf-8-sig",low_memory=False)
        if "policy_key" not in led.columns or "regime_split" not in led.columns: blocks.append(dict(blocker_id="ledger_missing_policy_or_regime_columns",path=str(lpath)))
    if not blocks:
        bal,best_rows=aggregate_balanced(per)
        if args.policy_key:
            o=bal[bal.policy_key.astype(str)==args.policy_key].copy()
            if o.empty: blocks.append(dict(blocker_id="policy_key_override_not_found",policy_key=args.policy_key))
            else:
                bal=pd.concat([o,bal[bal.policy_key.astype(str)!=args.policy_key]],ignore_index=True)
                best_rows=per[per.policy_key.astype(str)==args.policy_key].sort_values("regime_score",ascending=False).groupby("regime_group").head(1).copy()
    if not blocks:
        save(bal,out/"gold_v3_107l_balanced_policy_summary.csv"); save(best_rows,out/"gold_v3_107l_best_policy_regime_rows.csv")
        outputs+=["gold_v3_107l_balanced_policy_summary.csv","gold_v3_107l_best_policy_regime_rows.csv"]
        if bal.empty: blocks.append(dict(blocker_id="no_balanced_policy_summary_rows"))
        elif not (bool(bal.iloc[0].all_regime_pass_65) or bool(bal.iloc[0].all_regime_pass_60)):
            blocks.append(dict(blocker_id="no_balanced_60_or_65_policy_found",best_policy_key=str(bal.iloc[0].policy_key)))
    if not blocks:
        key=str(bal.iloc[0].policy_key)
        best_led=led[led.policy_key.astype(str)==key].copy()
        best_led["entry_dt"]=pd.to_datetime(best_led.entry_dt,errors="coerce"); best_led["result_usd"]=pd.to_numeric(best_led.result_usd,errors="coerce")
        best_led=best_led[best_led.entry_dt.notna() & best_led.result_usd.notna()].sort_values("entry_dt").copy()
        save(best_led,out/"gold_v3_107l_rehydrated_best_policy_ledger.csv"); outputs.append("gold_v3_107l_rehydrated_best_policy_ledger.csv")
        mon=monthly_rows(best_led); save(mon,out/"gold_v3_107l_best_policy_monthly_diagnostics.csv"); outputs.append("gold_v3_107l_best_policy_monthly_diagnostics.csv")
        parity=parity_rows(best_rows,best_led); save(parity,out/"gold_v3_107l_rehydration_metric_parity.csv"); outputs.append("gold_v3_107l_rehydration_metric_parity.csv")
        if parity.empty or not parity.metric_match.all(): blocks.append(dict(blocker_id="rehydration_metric_mismatch",detail="recomputed metrics differ from 107K2 frontier"))
    if not blocks:
        has_exit="exit_dt" in best_led.columns
        non_null=int(pd.to_datetime(best_led.exit_dt,errors="coerce").notna().sum()) if has_exit else 0
        exit_pre=pd.DataFrame([dict(check_id="exit_dt_column_present",result="PASS" if has_exit else "BLOCKED",observed=has_exit,expected=True,severity="BLOCKER"),dict(check_id="exit_dt_complete_for_selected_ledger",result="PASS" if has_exit and non_null==len(best_led) else "BLOCKED",observed=f"{non_null}/{len(best_led)}",expected=f"{len(best_led)}/{len(best_led)}",severity="BLOCKER"),dict(check_id="resolved_only_rule_required",result="PASS",observed="health history must use exit_dt <= current entry_dt",expected="exit_dt <= current entry_dt",severity="BLOCKER")])
        save(exit_pre,out/"gold_v3_107l_exit_dt_precondition_matrix.csv"); outputs.append("gold_v3_107l_exit_dt_precondition_matrix.csv")
        if not has_exit or non_null!=len(best_led):
            blocks.append(dict(blocker_id="missing_exit_dt_for_resolved_only_health_gate",reason="Rolling health gate cannot be simulated live-faithfully without exit_dt.",selected_policy_key=str(bal.iloc[0].policy_key),selected_rows=int(len(best_led)),non_null_exit_dt=non_null))
            decision="REGIME_REHYDRATION_READY_HEALTH_GATE_BLOCKED_EXIT_DT_REQUIRED"
    if not blocks:
        best_led["exit_dt"]=pd.to_datetime(best_led.exit_dt,errors="coerce")
        rows=[]; pass_ledgers=[]; scopes=[("ALL_REGIMES",best_led.copy())]+[(str(r),g.copy()) for r,g in best_led.groupby("regime_split")]
        for scope,x in scopes:
            for mode in MODES:
                for mh in MIN_HIST:
                    for mw in MIN_WR:
                        for mpf in MIN_PF:
                            for lb in LOOKBACK:
                                acc,state=simulate(x,mode,mh,mw,mpf,lb); m=metrics(acc)
                                rec=dict(scope=scope,health_mode=mode,min_history=mh,min_wr=mw,min_pf=mpf,lookback_resolved=lb,**{f"gated_{k}":v for k,v in m.items()})
                                rec["primary_60_gate"]=bool(m["win_rate"]>=0.60 and m["profit_factor"]>=1.5 and m["trades"]>=30 and m["unique_trade_days"]>=4 and m["max_day_trade_share"]<=0.45)
                                rec["primary_65_gate"]=bool(m["win_rate"]>=0.65 and m["profit_factor"]>=1.5 and m["trades"]>=30 and m["unique_trade_days"]>=4 and m["max_day_trade_share"]<=0.45)
                                rec["review_score"]=m["win_rate"]*15000+cap(m["profit_factor"])*900+m["trades"]*0.25-m["negative_month_count"]*500-m["max_day_trade_share"]*1200
                                rows.append(rec)
                                if rec["primary_60_gate"] or rec["primary_65_gate"]:
                                    tmp=acc.copy(); tmp["health_scope"]=scope; tmp["health_mode"]=mode; tmp["min_history"]=mh; tmp["min_wr"]=mw; tmp["min_pf"]=mpf; tmp["lookback_resolved"]=lb; pass_ledgers.append(tmp)
        health_frontier=pd.DataFrame(rows).sort_values(["primary_65_gate","primary_60_gate","review_score"],ascending=[False,False,False]) if rows else pd.DataFrame()
        save(health_frontier,out/"gold_v3_107l_health_gate_frontier.csv"); outputs.append("gold_v3_107l_health_gate_frontier.csv")
        p65=int(health_frontier.primary_65_gate.sum()) if not health_frontier.empty else 0; p60=int(health_frontier.primary_60_gate.sum()) if not health_frontier.empty else 0
        decision="REGIME_REHYDRATION_AND_HEALTH_GATE_READY_FOR_107M" if (p65 or p60) else "REGIME_REHYDRATION_READY_HEALTH_GATE_NO_PASSING_CONFIG"
        if pass_ledgers and not health_frontier.empty:
            allp=pd.concat(pass_ledgers,ignore_index=True); b=health_frontier.iloc[0]
            mask=(allp.health_scope.astype(str)==str(b.scope))&(allp.health_mode.astype(str)==str(b.health_mode))&(pd.to_numeric(allp.min_history)==int(b.min_history))&(pd.to_numeric(allp.min_wr)==float(b.min_wr))&(pd.to_numeric(allp.min_pf)==float(b.min_pf))&(pd.to_numeric(allp.lookback_resolved)==int(b.lookback_resolved))
            save(allp[mask].copy(),out/"gold_v3_107l_best_health_gate_ledger.csv"); outputs.append("gold_v3_107l_best_health_gate_ledger.csv")
        dec=pd.DataFrame([dict(decision=decision,primary_65_health_gate_count=p65,primary_60_health_gate_count=p60,next_stage="107M_MULTI_REGIME_ROLLING_HEALTH_GATE_AUDIT_ONLY" if (p65 or p60) else "107M_HEALTH_GATE_REVIEW_OR_EXIT_DT_SOURCE_AUDIT_ONLY")])
        save(dec,out/"gold_v3_107l_next_action_decision.csv"); outputs.append("gold_v3_107l_next_action_decision.csv")
        findings.append("next_action_decision="+json.dumps(dec.to_dict(orient="records"),ensure_ascii=False,default=str))
    vals += [dict(check_id="audit_only",result="PASS",observed=True,expected=True,severity="BLOCKER"),dict(check_id="live_ready_false",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="source_csv_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="contract_mutated",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="manual_candidate_demotion_or_removal",result="PASS",observed=False,expected=False,severity="BLOCKER"),dict(check_id="open_asof_allowed",result="PASS",observed=False,expected=False,severity="BLOCKER")]
    if not per.empty: vals.append(dict(check_id="regime_frontier_positive",result="PASS",observed=len(per),expected=">0",severity="BLOCKER"))
    if not best_led.empty: vals.append(dict(check_id="best_policy_ledger_positive",result="PASS",observed=len(best_led),expected=">0",severity="BLOCKER"))
    if not parity.empty: vals.append(dict(check_id="rehydration_metric_parity",result="PASS" if parity.metric_match.all() else "FAIL",observed=bool(parity.metric_match.all()),expected=True,severity="BLOCKER"))
    val=pd.DataFrame(vals); validation_failed=int((~val.result.eq("PASS")).sum()) if not val.empty else 0
    status=READY if not blocks and validation_failed==0 else BLOCKED
    if decision=="INPUT_BLOCKED":
        ids={b.get("blocker_id") for b in blocks}
        if "missing_exit_dt_for_resolved_only_health_gate" in ids: decision="REGIME_REHYDRATION_READY_HEALTH_GATE_BLOCKED_EXIT_DT_REQUIRED"
        elif "rehydration_metric_mismatch" in ids: decision="REGIME_REHYDRATION_METRIC_MISMATCH_BLOCKED"
        elif "no_balanced_60_or_65_policy_found" in ids: decision="NO_BALANCED_POLICY_FOUND_IN_107K2_FRONTIER"
    summary=dict(step=STEP,status=status,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=validation_failed,elapsed_seconds=round(time.time()-t0,2))
    if not bal.empty: summary.update(balanced_policy_rows=len(bal),all_regime_pass_65_count=int(bs(bal.all_regime_pass_65).sum()),all_regime_pass_60_count=int(bs(bal.all_regime_pass_60).sum()),best_policy_key=str(bal.iloc[0].policy_key),best_min_wr=float(bal.iloc[0].min_wr),best_min_pf=float(bal.iloc[0].min_pf),best_min_trades=int(bal.iloc[0].min_trades),best_sum_trades=int(bal.iloc[0].sum_trades),best_avg_wr=float(bal.iloc[0].avg_wr))
    if not best_led.empty: summary.update(best_policy_rehydrated_rows=len(best_led))
    if not parity.empty: summary.update(rehydration_metric_parity_pass=bool(parity.metric_match.all()))
    if not health_frontier.empty: summary.update(health_frontier_rows=len(health_frontier),primary_65_health_gate_count=int(health_frontier.primary_65_gate.sum()),primary_60_health_gate_count=int(health_frontier.primary_60_gate.sum()))
    save(pd.DataFrame(blocks),out/"gold_v3_107l_blocker_matrix.csv"); save(val,out/"gold_v3_107l_validation_matrix.csv")
    outputs+=["gold_v3_107l_blocker_matrix.csv","gold_v3_107l_validation_matrix.csv","gold_v3_107l_summary.json","GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY_REPORT.md","paste_me.txt"]
    (out/"gold_v3_107l_summary.json").write_text(json.dumps(summary|{"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (out/"GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107L report\n\n"+json.dumps({"summary":summary,"findings":findings,"blockers":blocks},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    lines=["GOLD V3 107L PASTE_ME_REGIME_REHYDRATION_AND_HEALTH_GATE",f"status: {status}",f"ready: {str(status==READY).lower()}","live_ready: false","source_csv_mutated: false","contract_mutated: false","manual_candidate_demotion_or_removal: false","open_asof_allowed: false","csv_contract: "+gy.CONTRACT,"csv_open_bar_exclusion_required: false","safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false","pool_policy: "+gy.POOL_POLICY,"resolved_only_health_gate_rule: exit_dt <= current entry_dt","blocker_count: "+str(len(blocks)),"","KEY_METRICS"]+[f"{k}: {v}" for k,v in summary.items()]+["","FINDINGS"]+(findings or ["NO_FINDINGS"])+["","BLOCKERS",pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS","","VALIDATION",val.to_string(index=False),"","EXIT_DT_PRECONDITION",exit_pre.to_string(index=False) if not exit_pre.empty else "NOT_EVALUATED","","OUTPUTS"]+outputs
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=="__main__": raise SystemExit(main())
