from __future__ import annotations

import bisect
import json
import math
import os
import shutil
import sys
import time
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (
    MR / "common" / "python",
    MR / "m10a" / "python",
    MR / "m10w22" / "python",
    MR / "m10w25" / "python",
    MR / "m10w26" / "python",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import bounded_csv_source_adapter as adapter
import frozen_core as c
import run_high_atr_bullish_new_causal_information_availability_audit as feature_core
import run_m10w25_neither_prefix_causal_live_parity_audit as coverage_core
import m10w26_runtime as common

STAGE = "M10W34_SNDX1_LOW_ATR_CAUSAL_NEITHER_FRESH_PROSPECTIVE_SHADOW"
RUNTIME_VERSION = "M10W34_RUNTIME_V1_PRESTART_CAUSAL_ENGINE_AND_IMPLEMENTATION_FROZEN"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w34_sndx1_fresh_prospective_shadow_contract_20260728.json"
TIME_FORMAT = adapter.TIME_FORMAT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20
ATR_BOUNDARY = 0.33
EXPECTED_FILE_MAP = dict(adapter.FILE_MAP)

class M10W34Error(RuntimeError):
    pass

utc_text = common.utc_text
utc_stamp = common.utc_stamp
parse_time = common.parse_time
fmt_time = common.fmt_time
load_json = common.load_json
atomic_json = common.atomic_json
canonical_sha = common.canonical_sha
load_bars = common.load_bars
prefix_fingerprint = common.prefix_fingerprint
snapshot_info = common.snapshot_info
selected_index = common.selected_index
directional_bps = common.directional_bps
metrics = common.metrics
summarize = common.summarize
write_csv = common.write_csv

def runtime_paths(local_root: Path) -> dict[str, Path]:
    directory = local_root / "m10w34_runtime"
    return {
        "directory": directory,
        "runtime": directory / "m10w34_runtime_manifest.json",
        "state": directory / "m10w34_runtime_state.json",
        "receipt": directory / "m10w34_runtime_start_receipt.json",
        "prestart": directory / "m10w34_prestart_causal_engine_audit.json",
        "lock": directory / "m10w34_shadow_loop.lock",
        "stop": directory / "STOP_M10W34_SHADOW_LOOP",
        "log": local_root / "logs" / "m10w34" / "m10w34_private_snapshot_forever.log",
        "loop_status": local_root / "logs" / "m10w34" / "latest_m10w34_shadow_loop_status.json",
    }

def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH" or contract.get("stage") != STAGE:
        raise M10W34Error("unexpected project or stage")
    if contract.get("status") != "DESIGN_FROZEN_NOT_STARTED" or contract.get("scope") != "XAUUSD_GOLD_ONLY":
        raise M10W34Error("unexpected contract status or scope")
    data = contract.get("data", {})
    if data.get("live_file_map") != EXPECTED_FILE_MAP or data.get("historical_backfill") is not False:
        raise M10W34Error("unsafe data contract")
    target = contract.get("target_regime", {})
    if target != {
        "D1": "EMA20>EMA30>EMA40",
        "H4": "EMA20>EMA30",
        "H1_MACD": "TORYS line(6,13)>0",
        "H1_ATR_percentile100": "<0.33",
        "causal_coverage_class": "NEITHER",
    }:
        raise M10W34Error("target regime changed")
    candidate = contract.get("candidate", {})
    if candidate.get("family") != "SNDX1_LONG_DUAL_SCALE_NORMALIZED_EXPANSION" or candidate.get("direction") != "LONG":
        raise M10W34Error("unexpected family or direction")
    if candidate.get("formula") != [
        "m5_range3_over_h1_atr14 >= 0.40",
        "m1_range5_over_h1_atr14 >= 0.20",
        "m1_ret5_over_h1_atr14 > 0.0",
        "m1_close_location >= 0.60",
    ]:
        raise M10W34Error("SNDX1 formula changed")
    if int(candidate.get("horizon_minutes", -1)) != 240:
        raise M10W34Error("horizon changed")
    if candidate.get("one_position_per_arm") is not True or candidate.get("nearest_m1_fallback") is not False:
        raise M10W34Error("unsafe execution semantics")
    coverage = contract.get("causal_coverage", {})
    expected = ["LONG_M5_S1","LONG_M15_S2","LONG_H1_S3","LONG_H4_S4","SHORT_M10P_C056_G013","SHORT_M10P2_C0212"]
    if coverage.get("required_class") != "NEITHER" or coverage.get("families") != expected:
        raise M10W34Error("causal coverage changed")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise M10W34Error("audit_only required")
    for key in (
        "discord_send","mt5_order","live_ready","final_signal","entry_gate_enabled",
        "historical_backfill","existing_forward_modified","existing_threshold_refit",
        "runtime_reset","start_reset","manual_lock_or_journal_deletion","automatic_live_promotion",
    ):
        if safety.get(key) is not False:
            raise M10W34Error(f"unsafe flag: {key}")

def implementation_paths() -> dict[str, Path]:
    stage = MR / "m10w34"
    return {
        "m10w34_runtime": THIS,
        "m10w34_operator": stage / "python" / "run_m10w34_private_snapshot.py",
        "m10w34_bat01_initialize": stage / "bat" / "01_initialize_fresh_start_once.bat",
        "m10w34_bat02_once": stage / "bat" / "02_run_shadow_once.bat",
        "m10w34_bat03_forever": stage / "bat" / "03_run_shadow_forever.bat",
        "m10w34_bat04_stop": stage / "bat" / "04_stop_shadow_forever.bat",
        "m10w31_feature_core": MR / "m10w31" / "python" / "run_scale_normalized_causal_information_audit.py",
        "m10w25_coverage_core": MR / "m10w25" / "python" / "run_m10w25_neither_prefix_causal_live_parity_audit.py",
        "m10w22_feature_core": MR / "m10w22" / "python" / "run_high_atr_bullish_new_causal_information_availability_audit.py",
        "m10a_frozen_core": MR / "m10a" / "python" / "frozen_core.py",
        "m10a_payoff_rules": MR / "m10a" / "python" / "payoff_rules.py",
        "m10w26_common_runtime": MR / "m10w26" / "python" / "m10w26_runtime.py",
        "bounded_csv_adapter": MR / "common" / "python" / "bounded_csv_source_adapter.py",
        "bounded_csv_integrity": MR / "common" / "python" / "bounded_csv_journal_integrity.py",
    }

def implementation_sha256s() -> dict[str, str]:
    output: dict[str, str] = {}
    for name, path in implementation_paths().items():
        if not path.is_file():
            raise M10W34Error(f"required implementation missing: {name}: {path}")
        output[name] = adapter.sha256_file(path)
    return output

def verify_implementation_freeze(runtime_payload: dict[str, Any]) -> None:
    expected = runtime_payload.get("implementation_sha256")
    if not isinstance(expected, dict) or set(expected) != set(implementation_paths()):
        raise M10W34Error("frozen implementation inventory missing or changed")
    current = implementation_sha256s()
    if current != expected:
        changed = sorted(name for name in current if current.get(name) != expected.get(name))
        raise M10W34Error(f"implementation changed after start freeze: {changed}")

def target_context(bars: dict[str, list[c.Bar]]) -> dict[str, Any]:
    h1, h4, d1 = bars["H1"], bars["H4"], bars["D1"]
    h1_line = feature_core.macd_line_bps(h1)
    h1_atrp = feature_core.atr_percentile100(h1)
    h1_atr = feature_core.pay.wilder_atr14(h1)
    h4_closes = [float(bar.close) for bar in h4]
    d1_closes = [float(bar.close) for bar in d1]
    return {
        "h1_close_times": [bar.time + timedelta(hours=1) for bar in h1],
        "h4_close_times": [bar.time + timedelta(hours=4) for bar in h4],
        "d1_close_times": [bar.time + timedelta(days=1) for bar in d1],
        "h1_line": h1_line,
        "h1_atrp": h1_atrp,
        "h1_atr": h1_atr,
        "h4_e20": c.ema(h4_closes,20),
        "h4_e30": c.ema(h4_closes,30),
        "d1_e20": c.ema(d1_closes,20),
        "d1_e30": c.ema(d1_closes,30),
        "d1_e40": c.ema(d1_closes,40),
    }

def target_regime(decision: datetime, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    ih1 = selected_index(context["h1_close_times"], decision)
    ih4 = selected_index(context["h4_close_times"], decision)
    id1 = selected_index(context["d1_close_times"], decision)
    if min(ih1,ih4,id1) < 0 or context["h1_atrp"][ih1] is None or context["h1_atr"][ih1] is None:
        return False, {"available":False}
    atr = float(context["h1_atr"][ih1])
    if not math.isfinite(atr) or atr <= 0:
        return False, {"available":False}
    d1_bull = context["d1_e20"][id1] > context["d1_e30"][id1] > context["d1_e40"][id1]
    h4_bull = context["h4_e20"][ih4] > context["h4_e30"][ih4]
    h1_positive = context["h1_line"][ih1] > 0
    atrp = float(context["h1_atrp"][ih1])
    return d1_bull and h4_bull and h1_positive and atrp < ATR_BOUNDARY, {
        "available":True,
        "d1_bullish_stack":d1_bull,
        "h4_ema20_gt_ema30":h4_bull,
        "h1_macd_line_bps":float(context["h1_line"][ih1]),
        "h1_atr_pct100":atrp,
        "h1_atr14_usd":atr,
        "h1_source_open":fmt_time(context["h1_close_times"][ih1]-timedelta(hours=1)),
        "h4_source_open":fmt_time(context["h4_close_times"][ih4]-timedelta(hours=4)),
        "d1_source_open":fmt_time(context["d1_close_times"][id1]-timedelta(days=1)),
    }

def sndx1_features(decision: datetime, bars: dict[str, list[c.Bar]], h1_atr_usd: float) -> dict[str, Any] | None:
    m1, m5 = bars["M1"], bars["M5"]
    m1_ct = [bar.time + timedelta(minutes=1) for bar in m1]
    m5_ct = [bar.time + timedelta(minutes=5) for bar in m5]
    i1 = bisect.bisect_right(m1_ct, decision)-1
    i5 = bisect.bisect_right(m5_ct, decision)-1
    if i1 < 4 or i5 < 3:
        return None
    if h1_atr_usd <= 0 or not math.isfinite(h1_atr_usd):
        return None
    last1 = m1[i1]
    shape1 = feature_core.bar_shape(last1)
    close_location = shape1["close_location"]
    m5_range3 = max(float(m5[j].high) for j in range(i5-2,i5+1)) - min(float(m5[j].low) for j in range(i5-2,i5+1))
    m1_range5 = max(float(m1[j].high) for j in range(i1-4,i1+1)) - min(float(m1[j].low) for j in range(i1-4,i1+1))
    m1_ret5 = float(m1[i1].close) - float(m1[i1-4].open)
    values = {
        "m5_range3_over_h1_atr14":m5_range3/h1_atr_usd,
        "m1_range5_over_h1_atr14":m1_range5/h1_atr_usd,
        "m1_ret5_over_h1_atr14":m1_ret5/h1_atr_usd,
        "m1_close_location":close_location,
        "m1_source_open":fmt_time(last1.time),
        "m5_source_open":fmt_time(m5[i5].time),
    }
    values["formula_pass"] = (
        values["m5_range3_over_h1_atr14"] >= 0.40
        and values["m1_range5_over_h1_atr14"] >= 0.20
        and values["m1_ret5_over_h1_atr14"] > 0.0
        and close_location is not None and float(close_location) >= 0.60
    )
    return values

def build_candidates(bars: dict[str, list[c.Bar]], start: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    long_bins, long_diag = coverage_core.build_prefix_causal_long_bins(bars)
    short_bins, short_diag = coverage_core.build_short_bins(bars)
    bins = {**long_bins, **short_bins}
    context = target_context(bars)
    decisions = sorted({bar.time for bar in bars["M1"] if bar.time > start and bar.time.minute % 15 == 0 and bar.time.second == 0})
    candidates: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for decision in decisions:
        regime_pass, regime = target_regime(decision, context)
        presence = {family: coverage_core.floor_m15(decision) in family_bins for family, family_bins in bins.items()}
        coverage_class = coverage_core.coverage_class(presence)
        feature = sndx1_features(decision, bars, float(regime.get("h1_atr14_usd", math.nan))) if regime.get("available") else None
        formula_pass = bool(feature and feature.get("formula_pass"))
        eligible = regime_pass and coverage_class == "NEITHER" and formula_pass
        row: dict[str, Any] = {
            "decision_time":fmt_time(decision),
            "target_regime_pass":regime_pass,
            "causal_coverage_class":coverage_class,
            "SNDX1_formula_pass":formula_pass,
            "eligible_candidate":eligible,
            **{f"presence_{family}":value for family,value in presence.items()},
            **{f"regime_{key}":value for key,value in regime.items()},
        }
        if feature:
            row.update(feature)
        audit_rows.append(row)
        if eligible:
            candidates.append({
                **row,
                "candidate_id":f"M10W34_{decision.strftime('%Y%m%d_%H%M%S')}",
                "family":"SNDX1_LONG_DUAL_SCALE_NORMALIZED_EXPANSION",
                "direction":"LONG",
                "entry_time":fmt_time(decision),
                "scheduled_exit_time":fmt_time(decision+HORIZON),
            })
    diagnostics = {
        "long_family":long_diag,
        "short_family":short_diag,
        "decision_grid_count_after_start":len(decisions),
        "target_regime_count_after_start":sum(bool(row["target_regime_pass"]) for row in audit_rows),
        "causal_neither_count_after_start":sum(row["causal_coverage_class"]=="NEITHER" for row in audit_rows),
        "sndx1_formula_count_after_start":sum(bool(row["SNDX1_formula_pass"]) for row in audit_rows),
        "eligible_candidate_count_after_start":len(candidates),
        "future_reference":False,
    }
    return candidates,audit_rows,diagnostics

def verify_runtime(local_root: Path, snapshot_root: Path, point: float, contract: dict[str, Any], runtime: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_contract(contract)
    if runtime.get("project")!="MOCHIPOYO_ALERT_RESEARCH" or runtime.get("stage")!=STAGE:
        raise M10W34Error("unexpected runtime")
    if runtime.get("runtime_contract_version")!=RUNTIME_VERSION or runtime.get("runtime_status")!="FROZEN_FRESH_START":
        raise M10W34Error("runtime version/status changed")
    if runtime.get("contract_sha256")!=canonical_sha(contract):
        raise M10W34Error("contract changed after start")
    if runtime.get("historical_backfill_allowed") is not False or runtime.get("reset_allowed") is not False or runtime.get("audit_only") is not True:
        raise M10W34Error("unsafe runtime flags")
    source_root, observed_point = adapter.source_environment(local_root)
    if str(source_root)!=str(runtime.get("source_root","")):
        raise M10W34Error("source root changed")
    if abs(float(runtime.get("point","nan"))-point)>1e-12 or abs(observed_point-point)>1e-12:
        raise M10W34Error("point changed")
    receipt = load_json(adapter.receipt_path(local_root))
    if receipt.get("status")!="PASS_MIGRATION_READY_FOR_REVIEW":
        raise M10W34Error("adapter migration receipt not PASS")
    current = snapshot_info(snapshot_root)
    for timeframe,filename in EXPECTED_FILE_MAP.items():
        frozen = runtime.get("frozen_row_prefixes",{}).get(timeframe)
        if not isinstance(frozen,dict):
            raise M10W34Error(f"missing frozen prefix: {timeframe}")
        observed = prefix_fingerprint(snapshot_root/filename,int(frozen.get("row_count",0)))
        if observed != frozen:
            raise M10W34Error(f"pre-start rows changed: {timeframe}")
    start = parse_time(str(runtime.get("prospective_start_server_time","")))
    if start not in {bar.time for bar in c.load_bars(snapshot_root/EXPECTED_FILE_MAP["M1"])}:
        raise M10W34Error("immutable start anchor missing")
    verify_implementation_freeze(runtime)
    return current

def build_ledger(candidates: list[dict[str, Any]], m1: list[c.Bar], point: float) -> tuple[list[dict[str, Any]],list[dict[str, Any]]]:
    return common.build_ledger(candidates,m1,point)

def initialize(snapshot_root: Path, point: float) -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA",""))/"xauusd_signal_lab"/"mochipoyo_alert_research"
    paths = runtime_paths(local_root)
    contract = load_json(CONTRACT)
    validate_contract(contract)
    if paths["lock"].exists():
        raise M10W34Error("loop lock exists")
    protected = (paths["runtime"],paths["state"],paths["receipt"])
    if any(path.exists() for path in protected):
        raise M10W34Error("runtime already exists; reinitialize/reset forbidden")
    source_root,observed_point = adapter.source_environment(local_root)
    if abs(point-observed_point)>1e-12:
        raise M10W34Error("initializer point mismatch")
    receipt = load_json(adapter.receipt_path(local_root))
    if receipt.get("status")!="PASS_MIGRATION_READY_FOR_REVIEW":
        raise M10W34Error("adapter migration receipt not PASS")
    first=snapshot_info(snapshot_root)
    time.sleep(1.0)
    second=snapshot_info(snapshot_root)
    if first!=second:
        raise M10W34Error("private snapshot changed during freeze")
    start=parse_time(str(second["M1"]["last_server_open"]))
    frozen_impl=implementation_sha256s()
    bars=load_bars(snapshot_root)
    candidates,decisions,diag=build_candidates(bars,start)
    if candidates or decisions:
        raise M10W34Error(f"prestart dry run produced rows: decisions={len(decisions)} candidates={len(candidates)}")
    if int(diag.get("short_family",{}).get("source_timing_violation_count",-1))!=0:
        raise M10W34Error("short-family causal timing audit failed")
    expected_long={"LONG_M5_S1","LONG_M15_S2","LONG_H1_S3","LONG_H4_S4"}
    if set(diag.get("long_family",{}))!=expected_long:
        raise M10W34Error("long-family causal audit incomplete")
    for family,row in diag["long_family"].items():
        if row.get("future_exit_reference") is not False or row.get("completed_pair_required") is not False:
            raise M10W34Error(f"unsafe causal diagnostic: {family}")
    prestart={
        "project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,
        "status":"PASS_PRESTART_CAUSAL_ENGINE_AUDIT_START_NOT_YET_FROZEN",
        "prospective_start_candidate_server_time":fmt_time(start),
        "runtime_contract_version":RUNTIME_VERSION,
        "implementation_sha256":frozen_impl,
        "private_snapshot":second,
        "long_family_diagnostics":diag["long_family"],
        "short_family_diagnostics":diag["short_family"],
        "post_start_decision_count_in_dry_run":0,
        "post_start_candidate_count_in_dry_run":0,
        "formula_change":False,"threshold_change":False,"future_reference":False,
        "runtime_or_existing_start_modified_by_audit":False,
        "discord_send":False,"mt5_order":False,
    }
    atomic_json(paths["prestart"],prestart)
    prefixes={tf:prefix_fingerprint(snapshot_root/fn,int(second[tf]["row_count"])) for tf,fn in EXPECTED_FILE_MAP.items()}
    now=utc_text()
    runtime={
        "project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,
        "runtime_status":"FROZEN_FRESH_START","runtime_contract_version":RUNTIME_VERSION,
        "created_at_utc":now,"prospective_start_server_time":fmt_time(start),
        "contract_sha256":canonical_sha(contract),"contract_path":str(CONTRACT),
        "implementation_sha256":frozen_impl,"prestart_causal_engine_audit":str(paths["prestart"]),
        "source_root":str(source_root),"point":point,
        "frozen_row_prefixes":prefixes,"initial_private_snapshot":second,
        "private_snapshot_model":"M10W34_ONLY_VERIFIED_COPY_UNDER_BOUNDED_ADAPTER_UPDATE_LOCK",
        "pre_start_candidate_eligibility":False,"historical_backfill_allowed":False,
        "reset_allowed":False,"restart_safe":True,"audit_only":True,
        "discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False,"entry_gate_enabled":False,
    }
    state={"project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"status":"INITIALIZED_NO_CYCLE_YET","created_at_utc":now,"prospective_start_server_time":fmt_time(start),"cycle_count":0,"reset_allowed":False}
    start_receipt={"status":"PASS","stage":"M10W34_FRESH_START_INITIALIZATION_AUDIT_ONLY","created_at_utc":now,"prospective_start_server_time":fmt_time(start),"runtime_manifest":str(paths["runtime"]),"contract_sha256":runtime["contract_sha256"],"runtime_contract_version":RUNTIME_VERSION,"historical_backfill_allowed":False,"reset_allowed":False,"audit_only":True,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False}
    try:
        atomic_json(paths["runtime"],runtime)
        atomic_json(paths["state"],state)
        atomic_json(paths["receipt"],start_receipt)
        verify_implementation_freeze(load_json(paths["runtime"]))
    except Exception:
        for path in protected:
            path.unlink(missing_ok=True)
        raise
    if not all(path.is_file() for path in protected):
        for path in protected:
            path.unlink(missing_ok=True)
        raise M10W34Error("incomplete runtime transaction")
    print("[M10W34 PRESTART ENGINE PASS] six causal coverage families and SNDX1 feature engine verified")
    print(f"[M10W34 INIT PASS] fresh start={fmt_time(start)}")
    return 0

def once(snapshot_root: Path, point: float) -> int:
    local_root=Path(os.environ.get("LOCALAPPDATA",""))/"xauusd_signal_lab"/"mochipoyo_alert_research"
    paths=runtime_paths(local_root)
    if not paths["runtime"].is_file():
        raise M10W34Error("runtime missing; run BAT01 exactly once")
    contract=load_json(CONTRACT)
    runtime=load_json(paths["runtime"])
    current=verify_runtime(local_root,snapshot_root,point,contract,runtime)
    start=parse_time(str(runtime["prospective_start_server_time"]))
    bars=load_bars(snapshot_root)
    candidates,decisions,diag=build_candidates(bars,start)
    trades,overlaps=build_ledger(candidates,bars["M1"],point)
    sm=summarize(candidates,trades,overlaps)
    gates=contract["review_gates"]
    resolved=int(sm["resolved_count"])
    actual_pf=sm["actual"].get("profit_factor")
    cost2_pf=sm["actual_plus2bps_cost"].get("profit_factor")
    review={
        "operational":resolved>=int(gates["operational_resolved"]),
        "interim":resolved>=int(gates["interim_resolved"]),
        "formal":resolved>=int(gates["formal_resolved"]),
        "actual_pf_above_review_floor":actual_pf is not None and float(actual_pf)>=float(gates["minimum_actual_profit_factor_for_review"]),
        "actual_plus2bps_pf_above_review_floor":cost2_pf is not None and float(cost2_pf)>=float(gates["minimum_actual_plus2bps_profit_factor_for_review"]),
        "automatic_live_promotion":False,
    }
    output_root=local_root/"outputs"/"M10W34"
    archive=output_root/"archive"/utc_stamp()
    archive.mkdir(parents=True,exist_ok=False)
    summary={
        "project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"status":"PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "built_at_utc":utc_text(),"prospective_start_server_time":fmt_time(start),
        "latest_server_open":{tf:details["last_server_open"] for tf,details in current.items()},
        "SNDX1_CAUSAL_NEITHER":sm,"review_readiness":review,
        "frozen_rule":{
            "target_regime":"D1 bullish; H4 EMA20>EMA30; H1 MACD line>0; H1 ATR pct100<0.33",
            "causal_coverage_class":"NEITHER",
            "SNDX1":"m5_range3/H1ATR>=0.40 AND m1_range5/H1ATR>=0.20 AND m1_ret5/H1ATR>0 AND m1_close_location>=0.60",
            "horizon_minutes":240,"one_position":True,"formula_or_threshold_changed":False,
        },
        "causal_coverage_diagnostics":diag,
        "guardrails":{"audit_only":True,"historical_backfill":False,"pre_start_candidate_eligibility":False,"nearest_m1_fallback":False,"existing_forward_modified":False,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False,"automatic_live_promotion":False},
    }
    (archive/"00_READ_ME_FIRST.txt").write_text("M10W34 is an independent audit-only fresh prospective SNDX1 shadow inside low-ATR bullish prefix-causal NEITHER windows. Existing monitors remain unchanged.\n",encoding="utf-8")
    (archive/"01_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_csv(archive/"02_candidate_ledger.csv",candidates)
    write_csv(archive/"03_trade_ledger.csv",trades)
    write_csv(archive/"04_overlap_skip_ledger.csv",overlaps)
    write_csv(archive/"05_post_start_decision_audit.csv",decisions)
    (archive/"06_causal_coverage_diagnostics.json").write_text(json.dumps(diag,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (archive/"07_runtime_manifest_copy.json").write_text(paths["runtime"].read_text(encoding="utf-8"),encoding="utf-8")
    receipt=snapshot_root/"00_snapshot_receipt.json"
    if receipt.is_file():
        shutil.copy2(receipt,archive/"08_private_snapshot_receipt.json")
    (archive/"09_data_quality.json").write_text(json.dumps({"private_snapshot_root":str(snapshot_root),"point":point,"closed_rows_contract":True,"prefix_integrity_verified":True,"exact_m1_entry_only":True,"exact_m1_exit_only":True,"nearest_m1_fallback":False,"historical_backfill":False,"current_snapshot":current},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (archive/"10_audit.log").write_text("\n".join(["status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",f"prospective_start_server_time={fmt_time(start)}",f"candidates={len(candidates)}",f"accepted={sm['accepted_count']}",f"resolved={resolved}",f"open={sm['open_count']}",f"overlap_skips={len(overlaps)}","causal_coverage_class=NEITHER","historical_backfill=false","existing_forward_modified=false","discord_send=false","mt5_order=false",""]),encoding="utf-8")
    with zipfile.ZipFile(archive/"99_UPLOAD_PACKAGE.zip","w",zipfile.ZIP_DEFLATED) as package:
        for path in sorted(p for p in archive.iterdir() if p.is_file()):
            package.write(path,path.name)
    latest=output_root/"LATEST"
    shutil.rmtree(latest,ignore_errors=True)
    shutil.copytree(archive,latest)
    old=load_json(paths["state"]) if paths["state"].is_file() else {"cycle_count":0}
    atomic_json(paths["state"],{"project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"status":"PASS_FRESH_PROSPECTIVE_AUDIT_ONLY","prospective_start_server_time":fmt_time(start),"last_cycle_at_utc":utc_text(),"cycle_count":int(old.get("cycle_count",0))+1,"candidate_count":len(candidates),"accepted_count":int(sm["accepted_count"]),"resolved_count":resolved,"open_count":int(sm["open_count"]),"reset_allowed":False})
    print(f"[M10W34 PASS] CANDIDATES={len(candidates)} ACCEPTED={sm['accepted_count']} RESOLVED={resolved} OPEN={sm['open_count']}")
    print(f"[M10W34 OUTPUT] {latest}")
    return 0

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("initialize","once"))
    parser.add_argument("--snapshot-root",type=Path,required=True)
    parser.add_argument("--point",type=float,required=True)
    args=parser.parse_args()
    try:
        raise SystemExit(initialize(args.snapshot_root,args.point) if args.mode=="initialize" else once(args.snapshot_root,args.point))
    except Exception as exc:
        print(f"[M10W34 BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
        print("[SAFE] No existing runtime/start/monitor, Discord, or MT5 order was modified.",file=sys.stderr)
        raise SystemExit(2)
