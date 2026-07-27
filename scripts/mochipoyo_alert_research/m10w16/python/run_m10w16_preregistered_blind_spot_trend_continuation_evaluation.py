from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10A_PY = MR / "m10a" / "python"
if str(M10A_PY) not in sys.path:
    sys.path.insert(0, str(M10A_PY))
import frozen_core as frozen

STAGE = "M10W16_PREREGISTERED_BLIND_SPOT_TREND_CONTINUATION_EVALUATION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w15_blind_spot_trend_continuation_hypothesis_preregistration_20260728.json"
TIME_FORMAT = frozen.TIME_FORMAT
POINT = frozen.POINT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_and_load(data_root: Path) -> tuple[dict[str, list[frozen.Bar]], dict[str, str]]:
    bars: dict[str, list[frozen.Bar]] = {}
    hashes: dict[str, str] = {}
    for timeframe in ("M1", "M15", "H1", "H4", "D1"):
        filename, expected_hash = frozen.EXPECTED_FILES[timeframe]
        path = data_root / filename
        if not path.is_file():
            raise RuntimeError(f"missing frozen GOLD file: {path}")
        actual_hash = frozen.sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"frozen SHA256 mismatch {timeframe}: {actual_hash} expected={expected_hash}")
        bars[timeframe] = frozen.load_bars(path)
        hashes[timeframe] = actual_hash
    return bars, hashes


def macd_line_hist(bars: list[frozen.Bar]) -> tuple[list[float], list[float]]:
    closes = [float(bar.close) for bar in bars]
    fast = frozen.ema(closes, 6)
    slow = frozen.ema(closes, 13)
    line = [(a - b) / max(abs(close), 1e-12) * 10000.0 for a, b, close in zip(fast, slow, closes)]
    signal = frozen.ema(line, 4)
    hist = [a - b for a, b in zip(line, signal)]
    return line, hist


def build_candidates(bars: dict[str, list[frozen.Bar]], direction: str) -> list[dict[str, Any]]:
    m15, h1, h4, d1 = bars["M15"], bars["H1"], bars["H4"], bars["D1"]
    _, m15_hist = macd_line_hist(m15)
    h1_line, _ = macd_line_hist(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_e20, h4_e30 = frozen.ema(h4_closes, 20), frozen.ema(h4_closes, 30)
    d1_closes = [float(bar.close) for bar in d1]
    d1_e20, d1_e30, d1_e40 = frozen.ema(d1_closes, 20), frozen.ema(d1_closes, 30), frozen.ema(d1_closes, 40)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]
    rows: list[dict[str, Any]] = []
    for i in range(1, len(m15) - 1):
        decision = m15[i + 1].time
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if min(ih1, ih4, id1) < 0:
            continue
        if direction == "SHORT":
            regime = d1_e20[id1] < d1_e30[id1] < d1_e40[id1] and h4_e20[ih4] < h4_e30[ih4] and h1_line[ih1] < 0
            trigger = m15_hist[i - 1] > 0 and m15_hist[i] <= 0
            family = "BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS"
        else:
            regime = d1_e20[id1] > d1_e30[id1] > d1_e40[id1] and h4_e20[ih4] > h4_e30[ih4] and h1_line[ih1] > 0
            trigger = m15_hist[i - 1] < 0 and m15_hist[i] >= 0
            family = "BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS"
        if not (regime and trigger):
            continue
        rows.append({
            "family": family,
            "direction": direction,
            "decision_time": decision.strftime(TIME_FORMAT),
            "entry_time": decision.strftime(TIME_FORMAT),
            "scheduled_exit_time": (decision + HORIZON).strftime(TIME_FORMAT),
            "m15_trigger_source_open": m15[i].time.strftime(TIME_FORMAT),
            "h1_source_open": h1[ih1].time.strftime(TIME_FORMAT),
            "h4_source_open": h4[ih4].time.strftime(TIME_FORMAT),
            "d1_source_open": d1[id1].time.strftime(TIME_FORMAT),
            "m15_hist_previous_bps": float(m15_hist[i - 1]),
            "m15_hist_current_bps": float(m15_hist[i]),
            "h1_macd_line_bps": float(h1_line[ih1]),
        })
    return rows


def directional_bps(direction: str, entry_exec: float, exit_exec: float) -> float:
    raw = (exit_exec - entry_exec) if direction == "LONG" else (entry_exec - exit_exec)
    return raw / max(abs(entry_exec), 1e-12) * 10000.0


def build_ledger(candidates: list[dict[str, Any]], m1: list[frozen.Bar]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest = m1[-1].time
    active_until: datetime | None = None
    active_id: str | None = None
    trades: list[dict[str, Any]] = []
    skips: list[dict[str, Any]] = []
    seq = 0
    for row in sorted(candidates, key=lambda x: x["decision_time"]):
        decision = datetime.strptime(str(row["decision_time"]), TIME_FORMAT)
        if active_until is not None and decision < active_until:
            skips.append({"active_trade_id":active_id,"skipped_decision_time":row["decision_time"],"reason":"ONE_POSITION_ACTIVE"})
            continue
        entry_bar = by_time.get(decision)
        if entry_bar is None:
            trades.append({**row,"trade_id":None,"status":"ENTRY_DATA_GAP","actual_return_bps":None,"fixed0p20_return_bps":None})
            continue
        exit_time = decision + HORIZON
        exit_bar = by_time.get(exit_time)
        seq += 1
        trade_id = f"{row['family']}_T{seq:06d}"
        active_until = exit_time
        active_id = trade_id
        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({**row,"trade_id":trade_id,"status":status,"actual_return_bps":None,"fixed0p20_return_bps":None})
            continue
        direction = str(row["direction"])
        if direction == "LONG":
            actual_entry = float(entry_bar.open) + int(entry_bar.spread) * POINT
            actual_exit = float(exit_bar.open)
            fixed_entry = float(entry_bar.open) + FIXED_SPREAD_USD
            fixed_exit = float(exit_bar.open)
        else:
            actual_entry = float(entry_bar.open)
            actual_exit = float(exit_bar.open) + int(exit_bar.spread) * POINT
            fixed_entry = float(entry_bar.open)
            fixed_exit = float(exit_bar.open) + FIXED_SPREAD_USD
        trades.append({
            **row,
            "trade_id":trade_id,
            "status":"RESOLVED",
            "entry_spread_points":int(entry_bar.spread),
            "exit_spread_points":int(exit_bar.spread),
            "actual_return_bps":directional_bps(direction, actual_entry, actual_exit),
            "fixed0p20_return_bps":directional_bps(direction, fixed_entry, fixed_exit),
        })
    return trades, skips


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count":0,"win_rate":None,"profit_factor":None,"net_bps":0.0,"average_win_bps":None,"average_loss_bps":None,"payoff_ratio":None,"max_drawdown_bps":0.0,"max_losing_streak":0}
    positives=[v for v in values if v>0]
    negatives=[v for v in values if v<0]
    gross_win=sum(positives); gross_loss=abs(sum(negatives))
    pf = None if gross_loss == 0 else gross_win/gross_loss
    avg_win = sum(positives)/len(positives) if positives else None
    avg_loss = sum(negatives)/len(negatives) if negatives else None
    equity=peak=dd=0.0; streak=max_streak=0
    for v in values:
        equity += v; peak=max(peak,equity); dd=max(dd,peak-equity)
        if v<0: streak+=1; max_streak=max(max_streak,streak)
        else: streak=0
    return {"count":len(values),"win_rate":sum(v>0 for v in values)/len(values),"profit_factor":pf,"net_bps":sum(values),"average_win_bps":avg_win,"average_loss_bps":avg_loss,"payoff_ratio":None if avg_win is None or avg_loss is None else avg_win/abs(avg_loss),"max_drawdown_bps":dd,"max_losing_streak":max_streak}


def split_name(year: int) -> str | None:
    if year in (2023, 2024): return "TRAIN_2023_2024"
    if year == 2025: return "VALIDATION_2025"
    if year == 2026: return "TEST_2026"
    return None


def metric_blocks(trades: list[dict[str, Any]]) -> dict[str, Any]:
    resolved=[row for row in trades if row.get("status")=="RESOLVED"]
    groups: dict[str,list[dict[str,Any]]] = {"TRAIN_2023_2024":[],"VALIDATION_2025":[],"TEST_2026":[],"ALL":resolved}
    for row in resolved:
        year=datetime.strptime(str(row["entry_time"]),TIME_FORMAT).year
        name=split_name(year)
        if name: groups[name].append(row)
    out: dict[str,Any]={}
    for name,rows in groups.items():
        actual=[float(r["actual_return_bps"]) for r in rows]
        fixed=[float(r["fixed0p20_return_bps"]) for r in rows]
        out[name]={
            "actual":metrics(actual),
            "fixed0p20":metrics(fixed),
            "actual_plus1bps_cost":metrics([v-1.0 for v in actual]),
            "actual_plus2bps_cost":metrics([v-2.0 for v in actual]),
        }
    return out


def pf_value(block: dict[str,Any]) -> float:
    pf=block.get("profit_factor")
    return float("inf") if pf is None and block.get("count",0)>0 else (float(pf) if pf is not None else 0.0)


def classify(blocks: dict[str,Any], gates: dict[str,Any]) -> str:
    split_names=("TRAIN_2023_2024","VALIDATION_2025","TEST_2026")
    counts=[int(blocks[n]["actual"]["count"]) for n in split_names]
    if min(counts) < 20:
        return "INSUFFICIENT_DENSITY"
    pfs=[pf_value(blocks[n]["actual"]) for n in split_names]
    all_pf=pf_value(blocks["ALL"]["actual"])
    fixed_pf=pf_value(blocks["ALL"]["fixed0p20"])
    cost2_pf=pf_value(blocks["ALL"]["actual_plus2bps_cost"])
    nets=[float(blocks[n]["actual"]["net_bps"]) for n in split_names]
    if min(pfs) <= 1.0 or fixed_pf <= 1.0 or cost2_pf <= 1.0:
        return "REJECT"
    strong=gates["STRONG_CANDIDATE"]
    if min(pfs)>=float(strong["minimum_pf_each_split"]) and all_pf>=float(strong["minimum_all_pf"]) and fixed_pf>=float(strong["minimum_fixed0p20_all_pf"]) and cost2_pf>=float(strong["minimum_extra2bps_all_pf"]) and min(nets)>0:
        return "STRONG_CANDIDATE"
    robust=gates["ROBUST_CANDIDATE"]
    if min(pfs)>=float(robust["minimum_pf_each_split"]) and all_pf>=float(robust["minimum_all_pf"]) and fixed_pf>=float(robust["minimum_fixed0p20_all_pf"]) and cost2_pf>=float(robust["minimum_extra2bps_all_pf"]) and min(nets)>0:
        return "ROBUST_CANDIDATE"
    return "WEAK_OR_INCONSISTENT"


def main() -> int:
    local_root=Path(os.environ.get("LOCALAPPDATA", ""))/"xauusd_signal_lab"/"mochipoyo_alert_research"
    output_root=local_root/"outputs"/"M10W16"
    try:
        contract=load_json(CONTRACT)
        if contract.get("status") != "HYPOTHESES_FROZEN_BEFORE_OUTCOME_EVALUATION":
            raise RuntimeError("M10W15 preregistration contract is not frozen")
        data_root=resolve_data_root(local_root)
        if not data_root.is_dir(): raise RuntimeError(f"frozen GOLD data root unavailable: {data_root}")
        bars,hashes=verify_and_load(data_root)
        candidate_sets={
            "BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS":build_candidates(bars,"SHORT"),
            "BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS":build_candidates(bars,"LONG"),
        }
        ledgers={}; skips={}; results={}
        gates=contract["frozen_evaluation"]["decision_tiers"]
        for name,candidates in candidate_sets.items():
            ledger,overlap=build_ledger(candidates,bars["M1"])
            ledgers[name]=ledger; skips[name]=overlap
            blocks=metric_blocks(ledger)
            results[name]={
                "candidate_count":len(candidates),
                "accepted_rows":len(ledger),
                "resolved_count":sum(r.get("status")=="RESOLVED" for r in ledger),
                "entry_gap_count":sum(r.get("status")=="ENTRY_DATA_GAP" for r in ledger),
                "exit_gap_count":sum(r.get("status")=="EXIT_DATA_GAP" for r in ledger),
                "overlap_skip_count":len(overlap),
                "metrics":blocks,
                "classification":classify(blocks,gates),
            }
        summary={
            "project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,
            "status":"PASS_PREREGISTERED_BLIND_SPOT_TREND_CONTINUATION_EVALUATION_AUDIT_ONLY",
            "built_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope":"XAUUSD_GOLD_ONLY","verified_sha256":hashes,
            "preregistration_contract":str(CONTRACT.relative_to(ROOT)),
            "formula_refit_after_results":False,"results":results,
            "interpretation":{"historical_support_is_final_support":False,"advance_to_fresh_shadow_only_if_classification":["ROBUST_CANDIDATE","STRONG_CANDIDATE"],"do_not_tune_failed_family_from_this_result":True},
            "safety":contract["safety"],
        }
        stamp=datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive=output_root/"archive"/stamp; archive.mkdir(parents=True,exist_ok=False)
        (archive/"00_READ_ME_FIRST.txt").write_text("M10W16 evaluates exactly the two M10W15 preregistered GOLD blind-spot hypotheses. No formula tuning after outcomes. Existing forward monitors are untouched.\n",encoding="utf-8")
        (archive/"01_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        write_csv(archive/"02_BSC1_short_candidates.csv",candidate_sets["BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS"])
        write_csv(archive/"03_BSC1_short_ledger.csv",ledgers["BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS"])
        write_csv(archive/"04_BSC1_short_overlap.csv",skips["BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS"])
        write_csv(archive/"05_BLC1_long_candidates.csv",candidate_sets["BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS"])
        write_csv(archive/"06_BLC1_long_ledger.csv",ledgers["BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS"])
        write_csv(archive/"07_BLC1_long_overlap.csv",skips["BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS"])
        (archive/"08_audit.log").write_text("\n".join([
            "status=PASS_PREREGISTERED_BLIND_SPOT_TREND_CONTINUATION_EVALUATION_AUDIT_ONLY",
            f"BSC1_classification={results['BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS']['classification']}",
            f"BLC1_classification={results['BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS']['classification']}",
            "formula_refit_after_results=false","existing_forward_modified=false","threshold_rescue=false","automatic_live_promotion=false","",
        ]),encoding="utf-8")
        latest=output_root/"LATEST"
        if latest.exists(): shutil.rmtree(latest)
        shutil.copytree(archive,latest)
        package=latest/"99_UPLOAD_PACKAGE.zip"
        names=["00_READ_ME_FIRST.txt","01_summary.json","02_BSC1_short_candidates.csv","03_BSC1_short_ledger.csv","04_BSC1_short_overlap.csv","05_BLC1_long_candidates.csv","06_BLC1_long_ledger.csv","07_BLC1_long_overlap.csv","08_audit.log"]
        with zipfile.ZipFile(package,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names: zf.write(latest/name,arcname=name)
        print(f"[M10W16 PASS] BSC1={results['BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS']['classification']} BLC1={results['BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS']['classification']}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W16 BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
        print("[SAFE] No existing forward monitor/start/threshold was modified.",file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
