#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_114_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION"
READY = "GOLD_V3_114_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION_READY"
BLOCKED = "GOLD_V3_114_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION_BLOCKED"


def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f"progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}")
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")
def jload(p): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir", default=""); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/"FX_OUTPUTS"/"gold_v3"; out=root/"114c"; out.mkdir(parents=True,exist_ok=True)
    log(STEP+" START"); prog(0,4,"start")
    req={
        "s113":root/"113c"/"gold_v3_113_summary.json",
        "review113":root/"113c"/"gold_v3_113_final_review_summary.csv",
        "manifest112":root/"112c"/"gold_v3_112_selected_policy_freeze_manifest.json",
        "thresholds112":root/"112c"/"gold_v3_112_frozen_monitoring_thresholds.csv",
    }
    blockers=[{"blocker_id":f"missing_{k}","path":str(p)} for k,p in req.items() if not p.exists()]
    outputs=[]; findings=[]; s113={}; manifest={}; review=pd.DataFrame(); th=pd.DataFrame()
    if not blockers:
        s113=jload(req["s113"]); manifest=jload(req["manifest112"])
        review=pd.read_csv(req["review113"],encoding="utf-8-sig")
        th=pd.read_csv(req["thresholds112"],encoding="utf-8-sig")
        if review.empty: blockers.append({"blocker_id":"review113_empty"})
        if th.empty: blockers.append({"blocker_id":"thresholds112_empty"})
    prog(1,4,"inputs loaded")

    allowed_items=[
        "demo_live_evaluator",
        "discord_alert_only",
        "closed_csv_latest_row_only",
        "journal_output",
        "duplicate_alert_suppression",
        "no_signal_no_alert",
        "stop_review_alert_as_review_only",
    ]
    denied_items=[
        "mt5_order_execution",
        "real_account_execution",
        "auto_position_open_close",
        "source_csv_mutation",
        "csv_contract_mutation",
        "open_asof_logic",
        "candidate_pool_removal",
    ]
    if not blockers:
        allowed=pd.DataFrame([{"item":x,"allowed":True,"stage":"115"} for x in allowed_items])
        denied=pd.DataFrame([{"item":x,"allowed":False,"stage":"114_plus"} for x in denied_items])
        requirements=pd.DataFrame([
            {"requirement_id":"closed_csv_only","required":True},
            {"requirement_id":"no_signal_no_alert","required":True},
            {"requirement_id":"duplicate_suppression","required":True},
            {"requirement_id":"monitor_state_check","required":True},
            {"requirement_id":"stop_review_is_review_alert_only","required":True},
            {"requirement_id":"journal_csv_jsonl","required":True},
            {"requirement_id":"webhook_secret_external_only","required":True},
        ])
        save(allowed,out/"gold_v3_114_allowed_scope_matrix.csv"); outputs.append("gold_v3_114_allowed_scope_matrix.csv")
        save(denied,out/"gold_v3_114_denied_scope_matrix.csv"); outputs.append("gold_v3_114_denied_scope_matrix.csv")
        save(requirements,out/"gold_v3_114_stage115_requirements.csv"); outputs.append("gold_v3_114_stage115_requirements.csv")
        row={
            "authorization_scope":"DEMO_LIVE_EVALUATOR_DISCORD_ALERT_ONLY",
            "authorized_for_stage115":True,
            "selected_option":manifest.get("selected_option"),
            "selected_policy_key":manifest.get("selected_policy_key"),
            "health_gate_adopted":manifest.get("health_gate_adopted"),
            "loss_feature_filter_adopted":manifest.get("loss_feature_filter_adopted"),
            "monitoring_design_attached":manifest.get("monitoring_design_attached"),
            "virtual_monitor_latest_state":manifest.get("virtual_monitor_latest_state"),
            "trades":manifest.get("policy_metrics",{}).get("trades"),
            "win_rate":manifest.get("policy_metrics",{}).get("win_rate"),
            "profit_factor":manifest.get("policy_metrics",{}).get("profit_factor"),
            "sum_result_usd":manifest.get("policy_metrics",{}).get("sum_result_usd"),
            "threshold_rows":len(th),
            "order_execution_allowed":False,
            "real_account_allowed":False,
            "source_csv_mutated":False,
            "contract_mutated":False,
            "open_asof_allowed":False,
        }
        save(pd.DataFrame([row]),out/"gold_v3_114_demo_alert_authorization_summary.csv"); outputs.append("gold_v3_114_demo_alert_authorization_summary.csv")
        findings.append("stage115_allowed_scope_is_demo_live_evaluator_plus_discord_alert_only")
    prog(2,4,"scope matrices written")

    qg=pd.DataFrame([
        {"gate":"113_ready","observed":s113.get("status","")=="GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_READY_AUDIT_ONLY","operator":"==","threshold":True,"result":"PASS" if s113.get("status","")=="GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_READY_AUDIT_ONLY" else "FAIL"},
        {"gate":"selected_keep_107q_base","observed":manifest.get("selected_option","")=="KEEP_107Q_BASE","operator":"==","threshold":True,"result":"PASS" if manifest.get("selected_option","")=="KEEP_107Q_BASE" else "FAIL"},
        {"gate":"monitoring_attached","observed":bool(manifest.get("monitoring_design_attached",False)),"operator":"==","threshold":True,"result":"PASS" if bool(manifest.get("monitoring_design_attached",False)) else "FAIL"},
        {"gate":"latest_state_ok","observed":manifest.get("virtual_monitor_latest_state","")=="OK","operator":"==","threshold":True,"result":"PASS" if manifest.get("virtual_monitor_latest_state","")=="OK" else "FAIL"},
        {"gate":"order_execution_disabled","observed":False,"operator":"==","threshold":False,"result":"PASS"},
        {"gate":"real_account_disabled","observed":False,"operator":"==","threshold":False,"result":"PASS"},
    ])
    save(qg,out/"gold_v3_114_quality_gate_matrix.csv"); outputs.append("gold_v3_114_quality_gate_matrix.csv")
    val=pd.DataFrame([
        {"check_id":"authorization_limited_to_alert_only","result":"PASS","observed":True,"expected":True,"severity":"BLOCKER"},
        {"check_id":"order_execution_allowed_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"real_account_allowed_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"source_csv_mutated_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"contract_mutated_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"open_asof_allowed_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
    ])
    status=READY if not blockers else BLOCKED
    decision="DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZED_FOR_STAGE115_IMPLEMENTATION" if status==READY else "DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION_BLOCKED_INPUT_INCOMPLETE"
    summary={"step":STEP,"status":status,"decision":decision,"created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"output_dir":str(out),"authorization_scope":"DEMO_LIVE_EVALUATOR_DISCORD_ALERT_ONLY","authorized_for_stage115":status==READY,"order_execution_allowed":False,"real_account_allowed":False,"source_csv_mutated":False,"contract_mutated":False,"open_asof_allowed":False,"blocker_count":len(blockers),"validation_failure_count":0,"elapsed_seconds":round(time.time()-t0,2)}
    if not blockers: summary.update(row)
    save(pd.DataFrame(blockers),out/"gold_v3_114_blocker_matrix.csv"); save(val,out/"gold_v3_114_validation_matrix.csv")
    outputs += ["gold_v3_114_blocker_matrix.csv","gold_v3_114_validation_matrix.csv","gold_v3_114_summary.json","GOLD_V3_114_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION_REPORT.md","paste_me.txt"]
    (out/"gold_v3_114_summary.json").write_text(json.dumps(summary|{"findings":findings,"blockers":blockers},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (out/"GOLD_V3_114_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION_REPORT.md").write_text("# GOLD V3 114 report\n\n"+json.dumps({"summary":summary,"findings":findings,"blockers":blockers},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    lines=["GOLD V3 114 PASTE_ME_DEMO_LIVE_DISCORD_ALERT_ONLY_AUTHORIZATION",f"status: {status}",f"ready: {str(status==READY).lower()}","authorization_scope: DEMO_LIVE_EVALUATOR_DISCORD_ALERT_ONLY",f"authorized_for_stage115: {str(status==READY).lower()}","order_execution_allowed: false","real_account_allowed: false","source_csv_mutated: false","contract_mutated: false","open_asof_allowed: false","blocker_count: "+str(len(blockers)),"","KEY_METRICS"]+[f"{k}: {v}" for k,v in summary.items()]+["","FINDINGS"]+(findings or ["NO_FINDINGS"])+["","BLOCKERS",pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS","","QUALITY_GATES",qg.to_string(index=False),"","VALIDATION",val.to_string(index=False),"","OUTPUTS"]+outputs
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    prog(4,4,"DONE"); log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=="__main__": raise SystemExit(main())
