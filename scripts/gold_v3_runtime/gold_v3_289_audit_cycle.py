#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only Stage289 cycle over the existing MT5 closed-candle CSVs."""
from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from gold_v3_289_artifacts import validate_model_bundle
from gold_v3_289_candidates import detect_candidates,model_dir
from gold_v3_289_live_features import EXTERNAL_FILES,GOLD_FILES,read_candles
from gold_v3_289_state import evaluate_shadow_eligibility,import_base_resolved,load_runtime_state,load_trade_ledger,resolve_shadow_observations,update_runtime_state
READY="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_READY_AUDIT_ONLY"
PARTIAL="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY"
BLOCKED="GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_BLOCKED_AUDIT_ONLY"
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding="utf-8-sig")
def parse_args():
 p=argparse.ArgumentParser(); p.add_argument("--candle-dir",default=""); p.add_argument("--output-dir",default=""); p.add_argument("--base-resolved-csv",default=""); p.add_argument("--lookback-hours",type=int,default=96); p.add_argument("--replay-existing",action="store_true"); return p.parse_args()
def find_candle_dir(value):
 root=Path(__file__).resolve().parents[2]
 for d in ([Path(value)] if value else [])+[Path.cwd(),Path.cwd()/"Files",root,root/"Files",root.parent,root.parent/"Files",root.parent.parent]:
  d=d.expanduser().resolve()
  if all((d/n).exists() for n in GOLD_FILES.values()): return d
 raise FileNotFoundError("goldsharp_m1/m5/m15/h1/h4/d1.csv not found")
def base_path(value,out):
 for v in [value,os.environ.get("GOLD_V3_BASE_RESOLVED_CSV","")]:
  if str(v).strip(): return Path(str(v)).expanduser().resolve()
 p=out/"gold_v3_289_base_resolved_import.csv"; return p if p.exists() else None
def validate_inputs(cdir):
 checks=[]; blockers=[]
 for tf,name in GOLD_FILES.items():
  try:
   d=read_candles(cdir/name,4,timeframe=tf,require_spread=True); checks.append({"check":f"{tf}_csv","passed":True,"latest":str(d.time.max()),"separator":d.attrs.get("separator"),"dropped_incomplete":d.attrs.get("rows_dropped_incomplete",0)})
  except Exception as e: blockers.append(f"INVALID_{name}:{e!r}"); checks.append({"check":f"{tf}_csv","passed":False,"detail":repr(e)})
 ext=True
 for key,name in EXTERNAL_FILES.items():
  try: read_candles(cdir/name,4,timeframe="M15",require_spread=False); checks.append({"check":f"{key}_csv","passed":True})
  except Exception as e: ext=False; checks.append({"check":f"{key}_csv","passed":False,"detail":repr(e)})
 return checks,blockers,ext
def finish(out,summary,checks):
 (out/"gold_v3_289_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding="utf-8"); save(pd.DataFrame(checks),out/"gold_v3_289_validation.csv")
 lines=["GOLD V3 289 PASTE_ME_LIVE_CANDLE_ML_SAFE_SHADOW"]+[f"{k}: {v}" for k,v in summary.items() if k!="blockers"]+["","BLOCKERS"]+(summary.get("blockers") or ["NO_BLOCKERS"]); (out/"paste_me.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
def main():
 a=parse_args()
 try: cdir=find_candle_dir(a.candle_dir)
 except Exception as e: print(f"[{BLOCKED}] {e}"); return 1
 out=Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir/"FX_OUTPUTS"/"gold_v3"/"289c"; out.mkdir(parents=True,exist_ok=True)
 checks,blockers,external_ready=validate_inputs(cdir); candidates=pd.DataFrame(); meta={}
 try: bundle=validate_model_bundle(model_dir()); checks.append({"check":"model_bundle","passed":True})
 except Exception as e: blockers.append(f"MODEL_BUNDLE_INVALID:{e!r}"); checks.append({"check":"model_bundle","passed":False,"detail":repr(e)}); bundle=None
 if not blockers:
  try: candidates,meta=detect_candidates(cdir,a.lookback_hours,stage286_external_ready=external_ready)
  except Exception as e: blockers.append(f"CANDIDATE_DETECTION_ERROR:{e!r}")
 save(candidates,out/"gold_v3_289_detected_live_candle_candidates.csv")
 if blockers:
  summary={"status":BLOCKED,"ready":False,"live_ready":False,"created_at_utc":now(),"detected_candidate_count":len(candidates),"stage286_external_live_m15_ready":external_ready,"blocker_count":len(blockers),"blockers":blockers}; finish(out,summary,checks); return 1
 latest=pd.Timestamp(read_candles(cdir/GOLD_FILES["M5"],4,timeframe="M5",require_spread=True).time.max()); state,boot=load_runtime_state(out/"gold_v3_289_runtime_state.json",latest,a.replay_existing); watermark=pd.to_datetime(state.get("last_processed_m5_time"),errors="coerce")
 new=candidates[candidates.entry_dt>watermark].copy() if len(candidates) and pd.notna(watermark) else candidates.copy(); ledger_path=out/"gold_v3_289_shadow_trade_ledger.csv"; ledger=resolve_shadow_observations(load_trade_ledger(ledger_path),cdir)
 bp=base_path(a.base_resolved_csv,out); base_ready=bp is not None and bp.exists()
 try: base=import_base_resolved(bp if base_ready else None)
 except Exception as e: base=pd.DataFrame(columns=["entry_dt","exit_dt","pnl","source"]); base_ready=False; blockers.append(f"BASE_LEDGER_ERROR:{e!r}")
 if not base_ready: blockers.append("BASE_PORTFOLIO_STATE_NOT_CONNECTED")
 cycle,ledger=evaluate_shadow_eligibility(new,ledger,base,base_state_ready=base_ready); save(ledger,ledger_path)
 dp=out/"gold_v3_289_decision_ledger.csv"; old=pd.read_csv(dp,encoding="utf-8-sig") if dp.exists() and dp.stat().st_size else pd.DataFrame(); decisions=pd.concat([old,cycle],ignore_index=True).drop_duplicates("candidate_id",keep="last") if len(cycle) else old; save(decisions,dp); save(decisions.sort_values("entry_dt").tail(20) if len(decisions) else pd.DataFrame(),out/"gold_v3_289_latest_decisions.csv"); update_runtime_state(out/"gold_v3_289_runtime_state.json",state,latest)
 status=READY if external_ready and base_ready else PARTIAL; summary={"status":status,"ready":status==READY,"live_ready":False,"created_at_utc":now(),"latest_candle_time":meta.get("latest_candle_time",""),"model_bundle_status":bundle["status"],"stage286_external_live_m15_ready":external_ready,"base_portfolio_state_connected":base_ready,"base_resolved_csv":str(bp) if bp else "","base_resolved_count":len(base),"detected_candidate_count":len(candidates),"new_detected_candidate_count":len(new),"new_decision_count":len(cycle),"cumulative_decision_count":len(decisions),"shadow_ledger_rows":len(ledger),"blocker_count":len(blockers),"blockers":blockers}; finish(out,summary,checks); return 0
if __name__=="__main__": raise SystemExit(main())
