from __future__ import annotations
import argparse, csv, json, shutil, zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_START = "2026-07-20T14:54:15Z"
MATCHED = {"EXACT_MATCH", "EARLY_1_BAR", "LATE_1_BAR"}
REQ = {
    "report": "latest_m7c_prospective_shadow.json",
    "source": "latest_m7c_source_event_comparisons.csv",
    "decisions": "latest_m7c_proxy_decisions.csv",
    "signals": "latest_m7c_proxy_signals.csv",
    "extras": "latest_m7c_extra_proxy_signals.csv",
}

def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
def z(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")
def rows(p):
    with p.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def dump(p, x):
    with p.open("w", encoding="utf-8") as f: json.dump(x, f, ensure_ascii=False, indent=2); f.write("\n")
def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None
def b(v): return str(v).lower() in {"1", "true", "yes"}
def req_state(t): return {"PRIMARY_LONG":"IDLE","PRIMARY_SHORT":"IDLE","LONG_EXIT":"ACTIVE_LONG","SHORT_EXIT":"ACTIVE_SHORT"}.get(t)

def write_csv(p, data, fields):
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader()
        for r in data: w.writerow({k:r.get(k,"") for k in fields})

def contract_errors(report):
    e=[]
    if report.get("prospective_start_utc") != EXPECTED_START: e.append("prospective_start_utc mismatch")
    if report.get("readiness",{}).get("formal_review_state") != "READY_FOR_MANUAL_REPRODUCTION_REVIEW": e.append("formal gate not ready")
    if any(v is not True for v in report.get("readiness",{}).get("formal_review_requirements",{}).values()): e.append("formal gate requirements not all true")
    for k in ("audit_only","closed_m15_features_only","current_m15_open_only"):
        if report.get(k) is not True: e.append(f"{k} must be true")
    for k in ("future_fields_used","trade_outcome_fields_used","formula_refit_performed","reentry_rule_used","entry_gate_enabled","discord_send","mt5_order","live_ready","final_signal"):
        if report.get(k) is not False: e.append(f"{k} must be false")
    return e

def direct_gap(src, d):
    tr=src["source_transition"]; rs=req_state(tr)
    if not d: return "DECISION_ROW_MISSING", "no frozen decision row"
    if d.get("state_before") != rs: return "STATE_DIVERGENCE", f"proxy={d.get('state_before')} required={rs}"
    if tr=="PRIMARY_LONG":
        why=[]
        if not b(d.get("rci9_turn_up")): why.append("RCI_TURN_UP_FALSE")
        if d.get("ema_alignment")!="BULLISH_STACK": why.append("EMA_NOT_BULLISH_STACK")
        return ("DIRECT_PRIMARY_KERNEL_GAP", "|".join(why)) if why else ("UNEXPLAINED_NO_SIGNAL", "conditions appear satisfied")
    if tr=="PRIMARY_SHORT":
        why=[]
        if not b(d.get("rci9_turn_down")): why.append("RCI_TURN_DOWN_FALSE")
        if d.get("ema_alignment")!="BEARISH_STACK": why.append("EMA_NOT_BEARISH_STACK")
        return ("DIRECT_PRIMARY_KERNEL_GAP", "|".join(why)) if why else ("UNEXPLAINED_NO_SIGNAL", "conditions appear satisfied")
    r=fnum(d.get("rci9"))
    if tr=="LONG_EXIT" and (r is None or r<78.333333333333): return "DIRECT_EXIT_THRESHOLD_GAP", f"rci9={r}; requires >=78.333333333333"
    if tr=="SHORT_EXIT" and (r is None or r>-75): return "DIRECT_EXIT_THRESHOLD_GAP", f"rci9={r}; requires <=-75"
    return "UNEXPLAINED_NO_SIGNAL", "conditions appear satisfied"

def divergence_origins(report, source, signals, extras):
    extra_keys={(r["ticker"],dt(r["proxy_decision_time_utc"]),r["proxy_transition"]):r for r in extras}
    sb, pb, times=defaultdict(list),defaultdict(list),defaultdict(set)
    for r in source:
        t=dt(r["source_decision_time_utc"]); sb[(r["ticker"],t)].append(r); times[r["ticker"]].add(t)
    for r in signals:
        t=dt(r["proxy_decision_time_utc"]); pb[(r["ticker"],t)].append(r); times[r["ticker"]].add(t)
    out={}
    for ticker in times:
        ss=ps=report.get("bootstrap_states",{}).get(ticker); origin=None
        for t in sorted(times[ticker]):
            out[(ticker,t)]=dict(origin) if origin else None
            eq_before=ss==ps; se=sb.get((ticker,t),[]); pe=pb.get((ticker,t),[])
            for r in se: ss=r.get("source_state_after") or ss
            for r in pe: ps=r.get("state_after") or ps
            if ss==ps: origin=None; continue
            if not eq_before: continue
            if se and not pe:
                r=se[-1]; origin={"type":"SOURCE_ONLY_EVENT","time":z(t),"raw_alert_id":r.get("raw_alert_id",""),"transition":r.get("source_transition",""),"classification":r.get("classification","")}
            elif pe and not se:
                r=pe[-1]; x=extra_keys.get((ticker,t,r.get("proxy_transition","")))
                origin={"type":"EXTRA_PROXY_SIGNAL" if x else "PROXY_ONLY_SIGNAL","time":z(t),"raw_alert_id":"","transition":r.get("proxy_transition",""),"classification":x.get("classification","") if x else ""}
            else:
                origin={"type":"SIMULTANEOUS_STATE_DIVERGENCE","time":z(t),"raw_alert_id":se[-1].get("raw_alert_id","") if se else "","transition":"","classification":se[-1].get("classification","") if se else ""}
    return out

def state_gap(origin):
    if origin and origin.get("type")=="SOURCE_ONLY_EVENT" and origin.get("classification")=="MISSED": return "STATE_DIVERGENCE_AFTER_PRIOR_MISSED_SOURCE"
    if origin and origin.get("type")=="EXTRA_PROXY_SIGNAL": return "STATE_DIVERGENCE_AFTER_PRIOR_EXTRA_PROXY"
    return "STATE_DIVERGENCE_OTHER"

def package(folder):
    names=["00_READ_ME_FIRST.txt","01_summary.json","02_status.json","03_source_matched.csv","04_missed_source.csv","05_unsupported_reentry.csv","06_extra_candidates.csv","07_pending_source_arrival_grace.csv","08_audit.log"]
    with zipfile.ZipFile(folder/"99_UPLOAD_PACKAGE.zip","w",zipfile.ZIP_DEFLATED) as q:
        for n in names: q.write(folder/n,n)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input-dir",required=True); ap.add_argument("--output-root",required=True); ap.add_argument("--commit",default=""); a=ap.parse_args()
    inp=Path(a.input_dir).resolve(); root=Path(a.output_root).resolve()
    missing=[n for n in REQ.values() if not (inp/n).is_file()]
    if missing: print(f"[M8A BLOCKED] missing={missing}"); return 2
    report=json.loads((inp/REQ["report"]).read_text(encoding="utf-8")); err=contract_errors(report)
    source=rows(inp/REQ["source"]); decisions=rows(inp/REQ["decisions"]); signals=rows(inp/REQ["signals"]); extras=rows(inp/REQ["extras"])
    dm={(r["ticker"],dt(r["decision_time_utc"])):r for r in decisions}; origins=divergence_origins(report,source,signals,extras)
    matched=[]; missed=[]; reentry=[]
    for r in source:
        c=r.get("classification","")
        if c in MATCHED: x=dict(r); x["normalized_classification"]="SOURCE_MATCHED"; matched.append(x); continue
        if c=="UNSUPPORTED_REENTRY_NOT_SCORED": x=dict(r); x["normalized_classification"]="UNSUPPORTED_REENTRY"; reentry.append(x); continue
        if c!="MISSED": err.append(f"unexpected source classification={c}"); continue
        t=dt(r["source_decision_time_utc"]); d=dm.get((r["ticker"],t)); gap,detail=direct_gap(r,d); o=origins.get((r["ticker"],t)) if gap=="STATE_DIVERGENCE" else None
        if gap=="STATE_DIVERGENCE": gap=state_gap(o)
        x=dict(r); x.update({"normalized_classification":"MISSED_SOURCE","gap_class":gap,"gap_detail":detail,"proxy_state_before_at_source":d.get("state_before","") if d else "","proxy_emitted_transition_at_source":d.get("emitted_transition","") if d else "","rci9_at_source":d.get("rci9","") if d else "","rci9_turn_up_at_source":d.get("rci9_turn_up","") if d else "","rci9_turn_down_at_source":d.get("rci9_turn_down","") if d else "","ema_alignment_at_source":d.get("ema_alignment","") if d else "","divergence_origin_type":o.get("type","") if o else "","divergence_origin_time_utc":o.get("time","") if o else "","divergence_origin_raw_alert_id":o.get("raw_alert_id","") if o else "","divergence_origin_transition":o.get("transition","") if o else "","divergence_origin_classification":o.get("classification","") if o else ""}); missed.append(x)
    extra=[]; pending=[]
    for r in extras:
        x=dict(r); x["m8b_outcome_evaluated"]="false"
        if r.get("classification")=="FINALIZED_EXTRA_PROXY_SIGNAL": x["normalized_classification"]="EXTRA_CANDIDATE"; extra.append(x)
        elif r.get("classification")=="PENDING_SOURCE_ARRIVAL_GRACE": x["normalized_classification"]="PENDING_SOURCE_ARRIVAL_GRACE"; pending.append(x)
        else: err.append(f"unexpected extra classification={r.get('classification','')}")
    supported=int(report.get("comparison_summary",{}).get("supported_source_event_count",0)); scored=int(report.get("comparison_summary",{}).get("scored_source_event_count",0))
    if supported != len(matched)+len(missed): err.append("supported count mismatch")
    if scored != len(matched)+len(missed): err.append("scored count mismatch")
    bad={"UNEXPLAINED_NO_SIGNAL","DECISION_ROW_MISSING","STATE_DIVERGENCE_OTHER"}; unexpl=[r for r in missed if r["gap_class"] in bad]
    status="PASS" if not err and not unexpl else "BLOCKED"; now=datetime.now(timezone.utc); rid=now.strftime("%Y%m%d_%H%M%S"); arc=root/"archive"/rid; latest=root/"LATEST"; arc.mkdir(parents=True)
    summary={"project":"MOCHIPOYO_ALERT_RESEARCH","stage":"M8A_COVERAGE_GAP_AUDIT","status":status,"run_at_utc":z(now),"prospective_start_utc":report.get("prospective_start_utc"),"formal_review_state":report.get("readiness",{}).get("formal_review_state"),"automatic_reproduction_claim":False,"audit_only":True,"future_outcomes_used":False,"formula_refit_performed":False,"threshold_change_performed":False,"source_matched_count":len(matched),"missed_source_count":len(missed),"unsupported_reentry_count":len(reentry),"extra_candidate_count":len(extra),"pending_source_arrival_grace_count":len(pending),"source_matched_class_counts":dict(sorted(Counter(r["classification"] for r in matched).items())),"missed_by_ticker":dict(sorted(Counter(r["ticker"] for r in missed).items())),"missed_by_transition":dict(sorted(Counter(r["source_transition"] for r in missed).items())),"missed_gap_class_counts":dict(sorted(Counter(r["gap_class"] for r in missed).items())),"manual_review_findings":{"exact_proprietary_formula_reproduction_claimed":False,"supported_source_recall_exact":report.get("comparison_summary",{}).get("exact_recall"),"supported_source_recall_within_one_m15":report.get("comparison_summary",{}).get("within_one_bar_recall"),"primary_kernel_direct_gap_when_required_state_matched_count":sum(r["gap_class"]=="DIRECT_PRIMARY_KERNEL_GAP" for r in missed)}}
    stat={"status":status,"contract_errors":err,"unexplained_raw_alert_ids":[r.get("raw_alert_id") for r in unexpl],"outcome_fields_used":False,"m7c_formula_changed":False,"m7c_threshold_changed":False,"m7c_runtime_manifest_changed":False,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False,"entry_gate_enabled":False,"next_stage_if_pass":"M8B_EXTRA_SIGNAL_OUTCOME_AUDIT"}
    dump(arc/"01_summary.json",summary); dump(arc/"02_status.json",stat)
    sf=list(source[0])+["normalized_classification"]; write_csv(arc/"03_source_matched.csv",matched,sf)
    mf=list(source[0])+["normalized_classification","gap_class","gap_detail","proxy_state_before_at_source","proxy_emitted_transition_at_source","rci9_at_source","rci9_turn_up_at_source","rci9_turn_down_at_source","ema_alignment_at_source","divergence_origin_type","divergence_origin_time_utc","divergence_origin_raw_alert_id","divergence_origin_transition","divergence_origin_classification"]; write_csv(arc/"04_missed_source.csv",missed,mf); write_csv(arc/"05_unsupported_reentry.csv",reentry,sf)
    ef=list(extras[0])+["normalized_classification","m8b_outcome_evaluated"]; write_csv(arc/"06_extra_candidates.csv",extra,ef); write_csv(arc/"07_pending_source_arrival_grace.csv",pending,ef)
    readme=f"MOCHIPOYO M8A Coverage Gap Audit\nStage: M8A_COVERAGE_GAP_AUDIT\nRun UTC: {z(now)}\nCommit: {a.commit or 'not supplied'}\n\nRun result: {status}\nNormal submission: 99_UPLOAD_PACKAGE.zip\n\nM8A is audit-only. No future outcome, formula refit, source-matched suppression, Discord, MT5, live-ready, final-signal or entry-gate activation.\nPending source-arrival-grace rows are excluded from M8B until finalized.\n"
    (arc/"00_READ_ME_FIRST.txt").write_text(readme,encoding="utf-8"); (arc/"08_audit.log").write_text(f"status={status}\nmissed_gap_class_counts={json.dumps(summary['missed_gap_class_counts'],sort_keys=True)}\ncontract_errors={json.dumps(err)}\n",encoding="utf-8"); package(arc)
    if latest.exists(): shutil.rmtree(latest)
    shutil.copytree(arc,latest)
    print(f"[M8A {status}] source_matched={len(matched)} missed={len(missed)} reentry={len(reentry)} extras={len(extra)} pending_grace={len(pending)}"); print(f"[M8A OUTPUT] {latest}"); print(f"[M8A UPLOAD] {latest/'99_UPLOAD_PACKAGE.zip'}")
    return 0 if status=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
