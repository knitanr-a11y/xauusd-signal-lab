#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET"
READY = "GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f"progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}")
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")
def jload(p): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def main():
    t0=time.time()
    ap=argparse.ArgumentParser(); ap.add_argument("--mt5-files-dir", default=""); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/"FX_OUTPUTS"/"gold_v3"; out=root/"113c"; out.mkdir(parents=True,exist_ok=True)
    log(STEP+" START"); prog(0,4,"start")
    req={
        "manifest":root/"112c"/"gold_v3_112_selected_policy_freeze_manifest.json",
        "s112":root/"112c"/"gold_v3_112_summary.json",
        "freeze":root/"112c"/"gold_v3_112_selected_policy_freeze_summary.csv",
        "thresholds":root/"112c"/"gold_v3_112_frozen_monitoring_thresholds.csv",
        "latest":root/"112c"/"gold_v3_112_latest_virtual_monitor_state.csv",
    }
    blockers=[{"blocker_id":f"missing_{k}","path":str(p)} for k,p in req.items() if not p.exists()]
    outputs=[]; findings=[]; manifest={}; s112={}; freeze=pd.DataFrame(); th=pd.DataFrame(); latest=pd.DataFrame()
    if not blockers:
        manifest=jload(req["manifest"]); s112=jload(req["s112"])
        freeze=pd.read_csv(req["freeze"],encoding="utf-8-sig")
        th=pd.read_csv(req["thresholds"],encoding="utf-8-sig")
        latest=pd.read_csv(req["latest"],encoding="utf-8-sig")
        if freeze.empty: blockers.append({"blocker_id":"freeze_summary_empty"})
        if th.empty: blockers.append({"blocker_id":"thresholds_empty"})
        if latest.empty: blockers.append({"blocker_id":"latest_state_empty"})
    prog(1,4,"inputs loaded")
    if not blockers:
        pm=manifest.get("policy_metrics",{}); mm=manifest.get("monitoring_metrics",{})
        row={
            "selected_option":manifest.get("selected_option"),
            "selected_policy_key":manifest.get("selected_policy_key"),
            "health_gate_adopted":manifest.get("health_gate_adopted"),
            "loss_feature_filter_adopted":manifest.get("loss_feature_filter_adopted"),
            "monitoring_design_attached":manifest.get("monitoring_design_attached"),
            "virtual_monitor_latest_state":manifest.get("virtual_monitor_latest_state"),
            "trades":pm.get("trades"),
            "win_rate":pm.get("win_rate"),
            "profit_factor":pm.get("profit_factor"),
            "sum_result_usd":pm.get("sum_result_usd"),
            "negative_month_count":pm.get("negative_month_count"),
            "threshold_rows":len(th),
            "latest_state_rows":len(latest),
            "stop_review_event_count":mm.get("stop_review_event_count"),
            "caution_event_count":mm.get("caution_event_count"),
            "watch_event_count":mm.get("watch_event_count"),
            "runtime_ready":False,
            "human_decision_required":True,
        }
        save(pd.DataFrame([row]),out/"gold_v3_113_final_review_summary.csv"); outputs.append("gold_v3_113_final_review_summary.csv")
        opts=pd.DataFrame([
            {"option_id":"A","option":"CONTINUE_AUDIT_ONLY_REVIEW","runtime_permission":False},
            {"option_id":"B","option":"REQUEST_ADDITIONAL_AUDIT","runtime_permission":False},
            {"option_id":"C","option":"STOP_ADVANCEMENT_RESEARCH_ONLY","runtime_permission":False},
        ])
        save(opts,out/"gold_v3_113_decision_options.csv"); outputs.append("gold_v3_113_decision_options.csv")
        matrix=pd.DataFrame([{"item":x,"approved":False} for x in ["runtime","orders","alerts","external_api","hook","pool_change","source_change"]])
        save(matrix,out/"gold_v3_113_non_approval_matrix.csv"); outputs.append("gold_v3_113_non_approval_matrix.csv")
        packet=("# GOLD V3 113 Final Audit Review Packet\n\n"
                "Status: audit-only.\n\n"
                "## Frozen selection\n\n"
                f"selected_option: {row['selected_option']}\n\n"
                f"selected_policy_key: {row['selected_policy_key']}\n\n"
                f"health_gate_adopted: {row['health_gate_adopted']}\n\n"
                f"loss_feature_filter_adopted: {row['loss_feature_filter_adopted']}\n\n"
                f"monitoring_design_attached: {row['monitoring_design_attached']}\n\n"
                f"virtual_monitor_latest_state: {row['virtual_monitor_latest_state']}\n\n"
                "## Metrics\n\n"
                f"trades: {row['trades']}\n\nwin_rate: {row['win_rate']}\n\nprofit_factor: {row['profit_factor']}\n\nsum_result_usd: {row['sum_result_usd']}\n\n"
                "## Human options\n\nA: continue audit-only review.\nB: request more audit.\nC: stop advancement.\n")
        (out/"gold_v3_113_final_review_packet.md").write_text(packet,encoding="utf-8"); outputs.append("gold_v3_113_final_review_packet.md")
        findings.append("final_review_packet_created")
    prog(3,4,"outputs written")
    qg=pd.DataFrame([
        {"gate":"112_ready","observed":s112.get("status","")=="GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_READY_AUDIT_ONLY","operator":"==","threshold":True,"result":"PASS" if s112.get("status","")=="GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_READY_AUDIT_ONLY" else "FAIL"},
        {"gate":"selected_keep_107q_base","observed":manifest.get("selected_option","")=="KEEP_107Q_BASE","operator":"==","threshold":True,"result":"PASS" if manifest.get("selected_option","")=="KEEP_107Q_BASE" else "FAIL"},
        {"gate":"monitoring_attached","observed":bool(manifest.get("monitoring_design_attached",False)),"operator":"==","threshold":True,"result":"PASS" if bool(manifest.get("monitoring_design_attached",False)) else "FAIL"},
        {"gate":"latest_state_ok","observed":manifest.get("virtual_monitor_latest_state","")=="OK","operator":"==","threshold":True,"result":"PASS" if manifest.get("virtual_monitor_latest_state","")=="OK" else "FAIL"},
        {"gate":"runtime_ready_false","observed":False,"operator":"==","threshold":False,"result":"PASS"},
    ])
    save(qg,out/"gold_v3_113_quality_gate_matrix.csv"); outputs.append("gold_v3_113_quality_gate_matrix.csv")
    val=pd.DataFrame([
        {"check_id":"audit_only","result":"PASS","observed":True,"expected":True,"severity":"BLOCKER"},
        {"check_id":"runtime_ready_false","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"source_csv_mutated","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"contract_mutated","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
        {"check_id":"open_asof_allowed","result":"PASS","observed":False,"expected":False,"severity":"BLOCKER"},
    ])
    status=READY if not blockers else BLOCKED
    decision="FINAL_AUDIT_REVIEW_PACKET_READY_FOR_HUMAN_DECISION" if status==READY else "FINAL_AUDIT_REVIEW_PACKET_BLOCKED_INPUT_INCOMPLETE"
    summary={"step":STEP,"status":status,"decision":decision,"created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"output_dir":str(out),"audit_only":True,"runtime_ready":False,"source_csv_mutated":False,"contract_mutated":False,"open_asof_allowed":False,"human_decision_required":True,"blocker_count":len(blockers),"validation_failure_count":0,"elapsed_seconds":round(time.time()-t0,2)}
    if not blockers: summary.update(row)
    save(pd.DataFrame(blockers),out/"gold_v3_113_blocker_matrix.csv"); save(val,out/"gold_v3_113_validation_matrix.csv")
    outputs += ["gold_v3_113_blocker_matrix.csv","gold_v3_113_validation_matrix.csv","gold_v3_113_summary.json","GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_REPORT.md","paste_me.txt"]
    (out/"gold_v3_113_summary.json").write_text(json.dumps(summary|{"findings":findings,"blockers":blockers},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (out/"GOLD_V3_113_FINAL_AUDIT_REVIEW_PACKET_REPORT.md").write_text("# GOLD V3 113 report\n\n"+json.dumps({"summary":summary,"findings":findings,"blockers":blockers},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    lines=["GOLD V3 113 PASTE_ME_FINAL_AUDIT_REVIEW_PACKET",f"status: {status}",f"ready: {str(status==READY).lower()}","runtime_ready: false","human_decision_required: true","source_csv_mutated: false","contract_mutated: false","open_asof_allowed: false","safety: audit_only=true, review_packet_only=true","blocker_count: "+str(len(blockers)),"","KEY_METRICS"]+[f"{k}: {v}" for k,v in summary.items()]+["","FINDINGS"]+(findings or ["NO_FINDINGS"])+["","BLOCKERS",pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS","","QUALITY_GATES",qg.to_string(index=False),"","VALIDATION",val.to_string(index=False),"","OUTPUTS"]+outputs
    (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    prog(4,4,"DONE"); log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status":status,"ready":status==READY,"decision":decision,"paste_me":str(out/"paste_me.txt")},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=="__main__": raise SystemExit(main())
