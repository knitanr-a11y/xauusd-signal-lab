#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from gold_v3_289_feature_core import GOLD_FILES,read_candles
from gold_v3_290_admission import evaluate_intents
from gold_v3_290_base_health import load_base_intent
from gold_v3_290_candidates import detect_addition_intents
from gold_v3_290_exact_parity_gate import require_exact_parity
from gold_v3_290_io import read_csv_optional,write_csv,write_json
from gold_v3_290_ledger import import_bootstrap,load_ledger
from gold_v3_290_readiness_gate import check_readiness
from gold_v3_290_updates import UPDATE_COLUMNS,apply_updates,load_updates

BLOCKED="GOLD_V3_290_LIVE_SAFE_PORTFOLIO_SIGNAL_BLOCKED"; READY="GOLD_V3_290_LIVE_SAFE_PORTFOLIO_SIGNAL_READY"; NO_SIGNAL="GOLD_V3_290_LIVE_SAFE_PORTFOLIO_NO_SIGNAL"
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def args():
    p=argparse.ArgumentParser(); p.add_argument("--candle-dir",required=True); p.add_argument("--output-dir",default=""); p.add_argument("--bootstrap-ledger",required=True); p.add_argument("--base-resolved-health-ledger",required=True); p.add_argument("--exact-parity-report",required=True); p.add_argument("--bootstrap-state-start",default="2026-01-01 00:00:00"); p.add_argument("--authorization",required=True); p.add_argument("--lookback-hours",type=int,default=96); p.add_argument("--max-lag-seconds",type=int,default=120); return p.parse_args()
def load_runtime_state(path,latest_close):
    if path.exists(): return json.loads(path.read_text(encoding="utf-8")),False
    state={"initialized_at_utc":now(),"last_processed_planned_entry_dt":str(pd.Timestamp(latest_close)),"bootstrap_mode":"LATEST_ONLY"}; write_json(path,state); return state,True
def main():
    a=args(); cdir=Path(a.candle_dir).expanduser().resolve(); out=Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir/"FX_OUTPUTS"/"gold_v3"/"290_live_safe_portfolio"; out.mkdir(parents=True,exist_ok=True)
    bootstrap_path=Path(a.bootstrap_ledger).expanduser().resolve(); base_history_path=Path(a.base_resolved_health_ledger).expanduser().resolve(); parity_path=Path(a.exact_parity_report).expanduser().resolve()
    try: parity=require_exact_parity(parity_path)
    except Exception as exc:
        write_csv(out/"gold_v3_290_final_signal.csv",pd.DataFrame()); write_json(out/"gold_v3_290_summary.json",{"status":BLOCKED,"live_signal_ready":False,"created_at_utc":now(),"blockers":["EXACT_HISTORICAL_ADMISSION_REPLAY_NOT_PASS"],"detail":repr(exc),"mt5_order_enabled":False,"discord_enabled":False}); return 2
    readiness=check_readiness(cdir,bootstrap_path,base_history_path,a.authorization); readiness["exact_historical_admission_replay"]="PASS"; write_json(out/"gold_v3_290_readiness_report.json",readiness)
    if not readiness["live_signal_ready"]:
        write_csv(out/"gold_v3_290_final_signal.csv",pd.DataFrame()); write_json(out/"gold_v3_290_summary.json",{"status":BLOCKED,"live_signal_ready":False,"created_at_utc":now(),"blockers":readiness["blockers"],"mt5_order_enabled":False,"discord_enabled":False}); return 2
    m1=read_candles(cdir/GOLD_FILES["M1"],10,timeframe="M1",require_spread=True); latest_close=pd.Timestamp(m1.time.max())+pd.Timedelta(minutes=1); state_path=out/"gold_v3_290_runtime_state.json"; runtime_state,boot=load_runtime_state(state_path,latest_close)
    ledger_path=out/"gold_v3_290_live_signal_ledger.csv"; decision_path=out/"gold_v3_290_decision_ledger.csv"; update_path=out/"gold_v3_290_execution_updates.csv"
    if not update_path.exists(): write_csv(update_path,pd.DataFrame(columns=UPDATE_COLUMNS))
    ledger=load_ledger(ledger_path); updates=load_updates(update_path); ledger,applied=apply_updates(ledger,updates,latest_close); write_csv(ledger_path,ledger); write_csv(out/"gold_v3_290_applied_updates_latest.csv",applied)
    if boot:
        write_csv(out/"gold_v3_290_final_signal.csv",pd.DataFrame()); write_json(out/"gold_v3_290_summary.json",{"status":NO_SIGNAL,"reason":"INITIAL_WATERMARK_SET","latest_m1_close":str(latest_close),"mt5_order_enabled":False,"discord_enabled":False}); return 0
    additions,meta=detect_addition_intents(cdir,a.lookback_hours,external_ready=True); base=load_base_intent(cdir,base_history_path,ledger); intents=pd.concat([base,additions],ignore_index=True,sort=False) if len(base) or len(additions) else pd.DataFrame(); watermark=pd.to_datetime(runtime_state.get("last_processed_planned_entry_dt"),errors="coerce")
    if len(intents): intents["planned_entry_dt"]=pd.to_datetime(intents.planned_entry_dt,errors="coerce"); intents=intents[intents.planned_entry_dt>watermark].copy(); intents["intent_lag_seconds"]=(latest_close-intents.planned_entry_dt).dt.total_seconds()
    old_decisions=read_csv_optional(decision_path); seen=set(old_decisions.candidate_id.astype(str)) if len(old_decisions) and "candidate_id" in old_decisions else set()
    if len(intents): intents=intents[~intents.candidate_id.astype(str).isin(seen)].copy()
    bootstrap=import_bootstrap(bootstrap_path,start=a.bootstrap_state_start); cycle,ledger=evaluate_intents(intents,ledger,bootstrap,a.max_lag_seconds); decisions=pd.concat([old_decisions,cycle],ignore_index=True,sort=False) if len(cycle) else old_decisions; write_csv(decision_path,decisions); write_csv(ledger_path,ledger)
    accepted=cycle[cycle.final_signal.astype(bool)].copy() if len(cycle) and "final_signal" in cycle else pd.DataFrame(); final=accepted.sort_values(["planned_entry_dt","priority"]).tail(1) if len(accepted) else pd.DataFrame(); write_csv(out/"gold_v3_290_final_signal.csv",final)
    runtime_state["last_processed_planned_entry_dt"]=str(latest_close); runtime_state["updated_at_utc"]=now(); runtime_state["bootstrap_state_start"]=a.bootstrap_state_start; write_json(state_path,runtime_state); status=READY if len(final) else NO_SIGNAL; write_json(out/"gold_v3_290_summary.json",{"status":status,"live_signal_ready":True,"created_at_utc":now(),"latest_m1_close":str(latest_close),"new_intent_count":int(len(intents)),"new_decision_count":int(len(cycle)),"final_signal_count":int(len(final)),"model_meta":meta,"exact_parity_status":parity.get("status"),"mt5_order_enabled":False,"discord_enabled":False,"shadow_exit_simulation_used":False}); return 0
if __name__=="__main__": raise SystemExit(main())
