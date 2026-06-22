#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 read-only live-candle ML shadow cycle."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from gold_v3_289_live_features import EXTERNAL_FILES,GOLD_FILES,read_candles
from gold_v3_289_candidates import detect_candidates
from gold_v3_289_state import evaluate_shadow_eligibility,import_base_resolved,load_runtime_state,load_trade_ledger,resolve_shadow_observations,update_runtime_state

READY="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_READY_AUDIT_ONLY"
PARTIAL="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY"
BLOCKED="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT="open/in-progress candles are not written to CSV; latest row is closed"
POOL_POLICY="candidate pool is not manually pruned; fixed Stage280/281/286 contracts decide"

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def save(df,path): path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False,encoding="utf-8-sig")
def args():
 p=argparse.ArgumentParser(); p.add_argument("--candle-dir",default=""); p.add_argument("--output-dir",default=""); p.add_argument("--base-resolved-csv",default=""); p.add_argument("--lookback-hours",type=int,default=96); p.add_argument("--replay-existing",action="store_true"); return p.parse_args()
def candle_dir(value):
 root=Path(__file__).resolve().parents[2]
 for d in ([Path(value)] if value else [])+[Path.cwd(),Path.cwd()/"Files",root,root/"Files",root.parent,root.parent/"Files",root.parent.parent]:
  d=d.expanduser().resolve()
  if all((d/n).exists() for n in GOLD_FILES.values()): return d
 raise FileNotFoundError("goldsharp_m1/m5/m15/h1/h4/d1.csv not found")
def paste(summary,checks):
 keys=["status","ready","live_ready","latest_candle_time","stage280_threshold","stage281_threshold","stage286_external_live_m15_ready","base_portfolio_state_connected","base_resolved_count","detected_candidate_count","new_detected_candidate_count","new_decision_count","cumulative_decision_count","shadow_ledger_rows","blocker_count"]
 lines=["GOLD V3 289 PASTE_ME_LIVE_CANDLE_ML_SAFE_SHADOW"]+[f"{k}: {str(summary.get(k,'' )).lower() if isinstance(summary.get(k),bool) else summary.get(k,'')}" for k in keys]
 lines += ["source_csv_mutated: false","contract_mutated: false","manual_candidate_demotion_or_removal: false","open_asof_allowed: false",f"csv_contract: {CSV_CONTRACT}","csv_open_bar_exclusion_required: false","safety: audit_only=true, mt5=false, discord=false, ai_api=false, final_signal=false, partial_close=false",f"pool_policy: {POOL_POLICY}","","BLOCKERS"]
 lines += summary["blockers"] or ["NO_BLOCKERS"]
 lines += ["","VALIDATION",pd.DataFrame(checks).to_string(index=False),"","OUTPUTS","gold_v3_289_detected_live_candle_candidates.csv","gold_v3_289_decision_ledger.csv","gold_v3_289_shadow_trade_ledger.csv","gold_v3_289_latest_decisions.csv","gold_v3_289_summary.json"]
 return "\n".join(lines)+"\n"

def main():
 a=args(); blockers=[]
 try: cdir=candle_dir(a.candle_dir)
 except Exception as e: print(f"[{BLOCKED}] {e}"); return 1
 out=Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir/"FX_OUTPUTS"/"gold_v3"/"289c"; out.mkdir(parents=True,exist_ok=True)
 checks=[]
 for tf,name in GOLD_FILES.items():
  ok=(cdir/name).exists(); checks.append({"check":f"{tf}_closed_csv_present","passed":ok,"detail":str(cdir/name)})
  if not ok: blockers.append(f"MISSING_{name}")
 external=all((cdir/n).exists() for n in EXTERNAL_FILES.values()); checks.append({"check":"stage286_external_live_m15_present","passed":external,"detail":",".join(EXTERNAL_FILES.values())})
 try: candidates,meta=detect_candidates(cdir,a.lookback_hours)
 except Exception as e: candidates,meta=pd.DataFrame(),{}; blockers.append(f"CANDIDATE_DETECTION_ERROR:{e!r}")
 save(candidates,out/"gold_v3_289_detected_live_candle_candidates.csv")
 latest=pd.Timestamp(read_candles(cdir/GOLD_FILES["M5"],4).time.max()); state,boot=load_runtime_state(out/"gold_v3_289_runtime_state.json",latest,a.replay_existing); watermark=pd.to_datetime(state.get("last_processed_m5_time"),errors="coerce")
 new=candidates[candidates.entry_dt>watermark].copy() if len(candidates) and pd.notna(watermark) else candidates.copy()
 ledger_path=out/"gold_v3_289_shadow_trade_ledger.csv"; ledger=resolve_shadow_observations(load_trade_ledger(ledger_path),cdir)
 base_path=Path(a.base_resolved_csv).expanduser().resolve() if a.base_resolved_csv else out/"gold_v3_289_base_resolved_import.csv"; base_ready=base_path.exists()
 try: base=import_base_resolved(base_path if base_ready else None)
 except Exception as e: base=pd.DataFrame(columns=["entry_dt","exit_dt","pnl","source"]); base_ready=False; blockers.append(f"BASE_LEDGER_ERROR:{e!r}")
 cycle,ledger=evaluate_shadow_eligibility(new,ledger,base,base_state_ready=base_ready); save(ledger,ledger_path)
 decisions_path=out/"gold_v3_289_decision_ledger.csv"; old=pd.read_csv(decisions_path,encoding="utf-8-sig") if decisions_path.exists() and decisions_path.stat().st_size else pd.DataFrame(); decisions=pd.concat([old,cycle],ignore_index=True).drop_duplicates("candidate_id",keep="last") if len(cycle) else old; save(decisions,decisions_path); save(decisions.sort_values("entry_dt").tail(20) if len(decisions) else pd.DataFrame(),out/"gold_v3_289_latest_decisions.csv"); update_runtime_state(out/"gold_v3_289_runtime_state.json",state,latest)
 status=BLOCKED if blockers else (READY if external and base_ready else PARTIAL)
 summary={"status":status,"ready":status==READY,"live_ready":False,"created_at_utc":now(),"csv_contract":CSV_CONTRACT,"csv_open_bar_exclusion_required":False,"source_csv_mutated":False,"manual_candidate_queue_used":False,"audit_only":True,"mt5_execution_enabled":False,"discord_live_enabled":False,"final_signal_enabled":False,"latest_candle_time":meta.get("latest_candle_time",""),"stage280_threshold":meta.get("stage280_threshold",""),"stage281_threshold":meta.get("stage281_threshold",""),"stage286_external_live_m15_ready":external,"base_portfolio_state_connected":base_ready,"base_resolved_count":len(base),"detected_candidate_count":len(candidates),"new_detected_candidate_count":len(new),"new_decision_count":len(cycle),"cumulative_decision_count":len(decisions),"shadow_ledger_rows":len(ledger),"runtime_state_bootstrapped":boot,"watermark_before_cycle":str(watermark),"blocker_count":len(blockers),"blockers":blockers}
 (out/"gold_v3_289_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding="utf-8"); save(pd.DataFrame(checks),out/"gold_v3_289_validation.csv"); (out/"paste_me.txt").write_text(paste(summary,checks),encoding="utf-8"); print(f"[{status}] {out/'paste_me.txt'}"); return 0 if status in {READY,PARTIAL} else 1
if __name__=="__main__": raise SystemExit(main())
