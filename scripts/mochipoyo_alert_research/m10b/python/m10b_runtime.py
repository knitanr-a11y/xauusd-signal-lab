from __future__ import annotations
import argparse,bisect,csv,hashlib,io,json,math,os,shutil,subprocess,sys,time,zipfile
from datetime import UTC,datetime,timedelta
from pathlib import Path
from typing import Any

THIS=Path(__file__).resolve(); ROOT=THIS.parents[4]; MR=THIS.parents[2]
for d in (MR/"m9v"/"python",MR/"m9y"/"python",MR/"m9p"/"python",MR/"m10a"/"python"):
    if str(d) not in sys.path: sys.path.insert(0,str(d))
import m9v_core as v, m9v_core_v2 as v2, m9y_core as y
import run_gold_dynamic_core_reproduction_audit as p
import payoff_rules as pay

STAGE="M10B_GOLD_MULTI_TIMEFRAME_PAYOFF_FRESH_PROSPECTIVE_SHADOW"
VER="M10B_RUNTIME_V1_APPEND_SAFE_PREFIX"
CONTRACT=ROOT/"config"/"mochipoyo_alert_research"/"m10b_gold_multitimeframe_payoff_fresh_prospective_shadow_contract_20260725.json"
ARMS={"B0_M5_ENTRY_NATIVE":("M5",0.0),"B1_M5_RUNNER75":("M5",0.75),"B2_H1_ENTRY_NATIVE":("H1",0.0),"B3_H1_RUNNER50":("H1",0.5),"B4_H4_ENTRY_NATIVE":("H4",0.0)}
BR={"M5":"S1_M5","H1":"S3_H1","H4":"S4_H4"}
LAG={"M1":0,"M5":600,"M15":1800,"H1":7200,"H4":28800,"D1":172800}
class E(RuntimeError): pass
def pt(s): return datetime.strptime(s,p.TIME_FORMAT)
def ft(d): return d.strftime(p.TIME_FORMAT)
def js(path):
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise E(f"JSON object required: {path}")
    return x
def atom(path,x):
    path.parent.mkdir(parents=True,exist_ok=True); t=path.with_suffix(path.suffix+".tmp");t.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8");t.replace(path)
def fsha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()
def csha(c): return hashlib.sha256(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def valid(c):
    if c.get("project")!="MOCHIPOYO_ALERT_RESEARCH" or c.get("stage")!=STAGE or c.get("status")!="DESIGN_FROZEN_NOT_STARTED": raise E("unexpected M10B contract")
    if c.get("data",{}).get("historical_backfill") is not False or set(c.get("data",{}).get("live_file_map",{}))!={"M1","M5","M15","H1","H4","D1"}: raise E("unsafe M10B data contract")
    if set(c.get("arms",{}))!=set(ARMS): raise E("M10B arm mismatch")
    s=c.get("safety",{})
    if s.get("audit_only") is not True: raise E("audit_only required")
    for k in ("discord_send","mt5_order","live_ready","final_signal","entry_gate_enabled","historical_backfill","m7c_reset","m8c_reset","m9v_reset","m9y_reset","automatic_live_promotion"):
        if s.get(k) is not False: raise E(f"unsafe flag {k}")
def env():
    l=Path(os.environ.get("LOCALAPPDATA",""))/"xauusd_signal_lab"/"mochipoyo_alert_research"; mp=l/"outputs"/"M8B"/"LATEST"/"06_symbol_metadata.json"
    if not mp.is_file(): raise E(f"M8B metadata missing: {mp}")
    m=js(mp); root=Path(str(m.get("mt5_files_root",""))); point=float(m.get("symbols",{}).get("XAUUSD",{}).get("point","nan"))
    if not root.is_dir() or not math.isfinite(point): raise E(f"MT5 root/point unavailable: {root} {point}")
    return l,root,point
def stable_feed(latest):
    sp=latest/"01_summary.json"; lp=latest/"02_branch_candidate_ledger.csv"
    for n in range(5):
        try:
            a=sp.read_bytes();b=lp.read_bytes();c=sp.read_bytes()
            if a!=c: raise OSError
            return json.loads(a.decode()),list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
        except Exception:
            if n==4: raise E("cannot obtain stable M9V feed")
            time.sleep(.25)
def metrics(rows):
    r=[x for x in rows if x.get("weighted_return_bps") is not None]
    if not r:return {"accepted_count":len(rows),"resolved_count":0,"open_count":len(rows),"win_rate":None,"profit_factor_bps":None,"net_bps":0.0,"average_win_bps":None,"average_loss_bps":None,"payoff_ratio":None,"max_drawdown_bps":0.0,"max_losing_streak":0,"tail_le_minus_100_fraction":None}
    r=sorted(r,key=lambda x:pt(x["actual_entry_time"])); vals=[float(x["weighted_return_bps"]) for x in r];w=[x for x in vals if x>0];lo=[x for x in vals if x<0];eq=pk=dd=0.;st=ms=0
    for z in vals:
        eq+=z;pk=max(pk,eq);dd=max(dd,pk-eq);st=st+1 if z<0 else 0;ms=max(ms,st)
    aw=sum(w)/len(w) if w else None;al=sum(lo)/len(lo) if lo else None;gl=abs(sum(lo))
    return {"accepted_count":len(rows),"resolved_count":len(r),"open_count":len(rows)-len(r),"win_rate":sum(z>0 for z in vals)/len(vals),"profit_factor_bps":None if gl==0 else sum(w)/gl,"net_bps":sum(vals),"average_win_bps":aw,"average_loss_bps":al,"payoff_ratio":None if aw is None or al in (None,0) else aw/abs(al),"max_drawdown_bps":dd,"max_losing_streak":ms,"tail_le_minus_100_fraction":sum(z<=-100 for z in vals)/len(vals)}
def norm(rows,branch):
    out=[]
    for r in rows:
        if r.get("branch")!=branch or not (r.get("native_exit_time") or "").strip():continue
        out.append({"trade_id":r.get("candidate_id"),"proxy_entry_time":r["proxy_primary_time"],"turn_entry_time":r["turn_entry_time"],"exit_time":r["native_exit_time"],"return_bps":r.get("return_bps")})
    return out
def arm(name,rows):
    share=ARMS[name][1]; acc=[];skip=[]; until=None;open_=False;aid=None
    for r in sorted(rows,key=lambda x:pt(x["actual_entry_time"])):
        et=pt(r["actual_entry_time"])
        if open_ or (until is not None and et<until):skip.append({"arm":name,"active_trade_id":aid,"skipped_trade_id":r.get("trade_id"),"skipped_actual_entry_time":r["actual_entry_time"],"reason":"ONE_POSITION_ACTIVE"});continue
        nr=float(r["native_return_bps"]); nx=pt(r["exit_time"]); wr=None;ex=nx;used=False
        if share>0 and r.get("runner_eligible") is True:
            if r.get("runner_exit_time") and r.get("runner_return_bps") is not None:
                used=True;ex=pt(r["runner_exit_time"]);wr=(1-share)*nr+share*float(r["runner_return_bps"])
            else: ex=None
        else: wr=nr
        a={**r,"arm":name,"arm_trade_id":f"{name}_T{len(acc)+1:06d}","runner_share":share,"runner_used":used,"weighted_return_bps":wr,"effective_exit_time":ft(ex) if ex else None};acc.append(a);aid=a["arm_trade_id"];open_=ex is None;until=ex
    return acc,skip
def loadbars(root,c):
    out={}
    for tf,fn in c["data"]["live_file_map"].items():out[tf]=p.load_bars(root/fn)
    return out
def audit(root,point,c,rt,l,m9vp,m9vlatest):
    valid(c)
    if rt.get("stage")!=STAGE or rt.get("runtime_contract_version")!=VER or rt.get("contract_sha256")!=csha(c) or rt.get("reset_allowed") is not False or rt.get("historical_backfill_allowed") is not False: raise E("M10B runtime integrity failed")
    m9v=js(m9vp)
    if m9v.get("stage")!=v.STAGE or m9v.get("runtime_contract_version")!=v2.RUNTIME_CONTRACT_VERSION or rt.get("m9v_runtime_manifest_sha256")!=fsha(m9vp) or rt.get("m9v_prospective_start_server_time")!=m9v.get("prospective_start_server_time"):raise E("M9V immutable upstream mismatch")
    for tf,fn in c["data"]["live_file_map"].items():
        fr=rt["frozen_row_prefixes"].get(tf)
        if not isinstance(fr,dict) or v2.prefix_fingerprint_rows(root/fn,int(fr.get("row_count",0)))!=fr:raise E(f"frozen pre-start rows changed: {tf}")
    sm,feed=stable_feed(m9vlatest)
    if sm.get("stage")!=v.STAGE or sm.get("status")!="PASS_FRESH_PROSPECTIVE_AUDIT_ONLY" or sm.get("prospective_start_server_time")!=m9v.get("prospective_start_server_time"):raise E("M9V feed mismatch")
    if sm.get("guardrails",{}).get("historical_backfill") is not False:raise E("unsafe M9V feed")
    start=pt(rt["prospective_start_server_time"]); feed=[r for r in feed if r.get("branch") in set(BR.values()) and r.get("proxy_primary_time") and pt(r["proxy_primary_time"])>start]
    bars=loadbars(root,c)
    b5=norm(feed,"S1_M5");b1=norm(feed,"S3_H1");b4=norm(feed,"S4_H4")
    e5=pay.build_m5_reclaim(b5,bars["M1"],bars["M5"],point=point)
    e1=pay.build_htf_reclaim(b1,bars["M1"],bars["H1"],bars["M5"],signal_delta=timedelta(hours=1),confirm_delta=timedelta(minutes=5),offset_atr=.05,wait_minutes=30,point=point,confirm_name="M5")
    e4=pay.build_htf_reclaim(b4,bars["M1"],bars["H4"],bars["M15"],signal_delta=timedelta(hours=4),confirm_delta=timedelta(minutes=15),offset_atr=0.,wait_minutes=60,point=point,confirm_name="M15")
    r5=pay.build_runner_meta(e5,bars["M1"],bars["M5"],context_bars=(bars["M15"],),context_deltas=(timedelta(minutes=15),))
    r1=pay.build_runner_meta(e1,bars["M1"],bars["H1"],context_bars=(bars["H4"],bars["D1"]),context_deltas=(timedelta(hours=4),timedelta(days=1)))
    src={"B0_M5_ENTRY_NATIVE":r5,"B1_M5_RUNNER75":r5,"B2_H1_ENTRY_NATIVE":r1,"B3_H1_RUNNER50":r1,"B4_H4_ENTRY_NATIVE":e4};arms={};ov=[]
    for n in ARMS:
        arms[n],s=arm(n,src[n]);ov+=s
    return {"start_server_time":ft(start),"latest_server_open":{tf:ft(x[-1].time) for tf,x in bars.items()},"upstream_resolved_post_start":{"S1_M5":len(b5),"S3_H1":len(b1),"S4_H4":len(b4)},"entries":{"M5":e5,"H1":e1,"H4":e4},"skipped_reclaim":{"M5":len(b5)-len(e5),"H1":len(b1)-len(e1),"H4":len(b4)-len(e4)},"arms":arms,"arm_metrics":{n:metrics(x) for n,x in arms.items()},"overlaps":ov}
def initialize():
    l,root,point=env(); c=js(CONTRACT);valid(c);rd=l/"m10b_runtime";rp=rd/"m10b_runtime_manifest.json";lock=rd/"m10b_shadow_loop.lock"
    if lock.exists():raise E("M10B loop lock exists")
    if rp.exists():raise E("M10B runtime already exists; never reinitialize/reset")
    vp=l/"m9v_runtime"/"m9v_runtime_manifest.json";yp=l/"m9y_runtime"/"m9y_runtime_manifest.json"
    if not vp.is_file() or not yp.is_file():raise E("M9V/M9Y runtime anchor missing")
    vr=js(vp);yr=js(yp)
    if vr.get("stage")!=v.STAGE or vr.get("runtime_contract_version")!=v2.RUNTIME_CONTRACT_VERSION or vr.get("reset_allowed") is not False:raise E("M9V runtime unsafe")
    if yr.get("stage")!=y.STAGE or yr.get("runtime_contract_version")!=y.RUNTIME_CONTRACT_VERSION or yr.get("reset_allowed") is not False:raise E("M9Y runtime unsafe")
    def snap():
        return {tf:v.tail_snapshot(root/fn) for tf,fn in c["data"]["live_file_map"].items()}
    a=snap();time.sleep(2);b=snap()
    if a!=b:raise E("live CSV changed during M10B start freeze")
    latest={tf:pt(x["last_server_open"]) for tf,x in b.items()};start=latest["M1"]
    for tf,t in latest.items():
        lag=(start-t).total_seconds()
        if lag<0 or lag>LAG[tf]:raise E(f"{tf} lag invalid: {lag}s")
    if start<=pt(vr["prospective_start_server_time"]) or start<=pt(yr["prospective_start_server_time"]):raise E("M10B start must be strictly after M9V and M9Y")
    pref={tf:v2.prefix_fingerprint_rows(root/fn,int(b[tf]["row_count"])) for tf,fn in c["data"]["live_file_map"].items()};now=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rt={"project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"runtime_status":"FROZEN_FRESH_START","runtime_contract_version":VER,"created_at_utc":now,"prospective_start_server_time":ft(start),"contract_sha256":csha(c),"contract_path":str(CONTRACT),"data_root":str(root),"frozen_row_prefixes":pref,"m9v_runtime_manifest_sha256":fsha(vp),"m9v_prospective_start_server_time":vr["prospective_start_server_time"],"m9y_runtime_manifest_sha256_at_freeze":fsha(yp),"m9y_prospective_start_server_time":yr["prospective_start_server_time"],"m9v_upstream_read_only":True,"m9y_output_dependency":False,"pre_start_primary_candidate_eligibility":False,"historical_backfill_allowed":False,"reset_allowed":False,"audit_only":True,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False,"entry_gate_enabled":False}
    atom(rp,rt);atom(rd/"m10b_runtime_start_receipt.json",{"status":"PASS","stage":"M10B_FRESH_START_INITIALIZATION_AUDIT_ONLY","created_at_utc":now,"prospective_start_server_time":ft(start),"m9v_start":vr["prospective_start_server_time"],"m9y_start":yr["prospective_start_server_time"],"historical_backfill_allowed":False,"reset_allowed":False,"audit_only":True})
    print(f"[M10B INIT PASS] fresh start={ft(start)}");return 0
def once():
    l,root,point=env();c=js(CONTRACT);rp=l/"m10b_runtime"/"m10b_runtime_manifest.json"
    if not rp.is_file():raise E("M10B runtime missing; run BAT01 once first")
    r=audit(root,point,c,js(rp),l,l/"m9v_runtime"/"m9v_runtime_manifest.json",l/"outputs"/"M9V"/"LATEST");out=l/"outputs"/"M10B";stamp=datetime.now(UTC).strftime("%Y%m%d_%H%M%S");a=out/"archive"/stamp;a.mkdir(parents=True,exist_ok=False)
    review=c["review_gates"];cnt={n:len(x) for n,x in r["arms"].items()}
    s={"project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"status":"PASS_FRESH_PROSPECTIVE_AUDIT_ONLY","built_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),"prospective_start_server_time":r["start_server_time"],"latest_server_open":r["latest_server_open"],"native_base_materialization":"RESOLVED_ONLY; open upstream candidates are not counted until native EXIT resolves. Entry acceptance is reconstructed only from bars closed by the entry decision.","upstream_resolved_post_start":r["upstream_resolved_post_start"],"entry_candidate_counts":{k:len(v) for k,v in r["entries"].items()},"skipped_reclaim_counts":r["skipped_reclaim"],"arm_metrics":r["arm_metrics"],"review_readiness":{"M5_operational":cnt["B0_M5_ENTRY_NATIVE"]>=review["M5_operational_accepted"],"M5_interim":cnt["B0_M5_ENTRY_NATIVE"]>=review["M5_interim_accepted"],"M5_formal":cnt["B0_M5_ENTRY_NATIVE"]>=review["M5_formal_accepted"],"H1_operational":cnt["B2_H1_ENTRY_NATIVE"]>=review["H1_operational_accepted"],"H1_interim":cnt["B2_H1_ENTRY_NATIVE"]>=review["H1_interim_accepted"],"H1_formal":cnt["B2_H1_ENTRY_NATIVE"]>=review["H1_formal_accepted"],"H4_descriptive":cnt["B4_H4_ENTRY_NATIVE"]>=review["H4_descriptive_checkpoint_accepted"],"automatic_live_promotion":False},"guardrails":{"audit_only":True,"historical_backfill":False,"pre_start_primary_candidate_eligibility":False,"future_outcome_used_in_entry_gate":False,"m9v_modified_or_reset":False,"m9y_modified_or_reset":False,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False}}
    (a/"00_READ_ME_FIRST.txt").write_text("M10B fresh audit-only payoff shadow. Resolved-only native materialization; entry logic remains causal. No backfill/reset/live promotion.\n",encoding="utf-8");p.dump_json(a/"01_summary.json",s)
    for i,tf in enumerate(("M5","H1","H4"),2):p.write_csv(a/f"{i:02d}_{tf.lower()}_entry_candidates.csv",r["entries"][tf])
    for i,n in enumerate(ARMS,5):p.write_csv(a/f"{i:02d}_{n}_ledger.csv",r["arms"][n])
    p.write_csv(a/"10_overlap_skip_metadata.csv",r["overlaps"]);p.dump_json(a/"11_runtime_manifest_copy.json",js(rp));p.dump_json(a/"12_data_quality.json",{"data_root":str(root),"point":point,"closed_rows_contract":True,"prefix_integrity_verified":True,"latest_server_open":r["latest_server_open"]})
    (a/"13_audit.log").write_text("\n".join(["status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",f"start={r['start_server_time']}",*(f"{k}={v}" for k,v in cnt.items()),"native_base_materialization=resolved_only","future_outcome_used_in_entry_gate=false","historical_backfill=false","m9v_modified_or_reset=false","m9y_modified_or_reset=false","discord_send=false","mt5_order=false","live_ready=false","final_signal=false",""]),encoding="utf-8")
    names=[x.name for x in a.iterdir() if x.is_file()]
    with zipfile.ZipFile(a/"99_UPLOAD_PACKAGE.zip","w",zipfile.ZIP_DEFLATED) as z:
        for n in sorted(names):z.write(a/n,n)
    latest=out/"LATEST";shutil.rmtree(latest,ignore_errors=True);shutil.copytree(a,latest);print("[M10B PASS] "+" ".join(f"{k}={v}" for k,v in cnt.items()));print("[M10B OUTPUT]",latest);return 0
def forever():
    l,_,_=env();rd=l/"m10b_runtime";lock=rd/"m10b_shadow_loop.lock";stop=rd/"STOP_M10B_SHADOW_LOOP";rp=rd/"m10b_runtime_manifest.json"
    if not rp.is_file():raise E("M10B runtime missing")
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    except FileExistsError:raise E("M10B loop lock exists")
    stop.unlink(missing_ok=True);cycles=0
    try:
        while not stop.exists():
            cycles+=1;rc=once()
            if rc!=0:return rc
            deadline=time.monotonic()+60
            while time.monotonic()<deadline and not stop.exists():time.sleep(1)
        print(f"[M10B LOOP STOPPED] cycles={cycles}");return 0
    finally:lock.unlink(missing_ok=True)
def stop():
    l,_,_=env();f=l/"m10b_runtime"/"STOP_M10B_SHADOW_LOOP";f.parent.mkdir(parents=True,exist_ok=True);f.write_text("operator stop requested\n",encoding="utf-8");print("[M10B STOP REQUESTED]",f);return 0
def main():
    ap=argparse.ArgumentParser();ap.add_argument("mode",choices=("init","once","forever","stop"));m=ap.parse_args().mode
    try:return {"init":initialize,"once":once,"forever":forever,"stop":stop}[m]()
    except Exception as e:print(f"[M10B {m.upper()} BLOCKED] {type(e).__name__}: {e}",file=sys.stderr);print("[SAFE] collector/M7C/M8C/M9V/M9Y unchanged.",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
