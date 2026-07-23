from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
CUT_OFF = {
    "XAUUSD": datetime.strptime("2026.07.15 12:30:00", TIME_FORMAT),
    "BTCUSD": datetime.strptime("2026.07.15 11:15:00", TIME_FORMAT),
}
M15_FILES = {"XAUUSD": "goldsharp_m15.csv", "BTCUSD": "btcusdsharp_m15.csv"}
M1_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
TURN_LOOKBACK = 5
LONG_EXIT_RCI9 = 78.333333333333
SHORT_EXIT_RCI9 = -75.0

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from feature_snapshot_builder import MINIMUM_WARMUP_BARS, build_feature_payload, load_indicator_series
from alert_trigger_signature_audit import flatten_features


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bps(delta: float, reference: float) -> float:
    if reference == 0:
        raise RuntimeError("zero price reference")
    return delta / reference * 10000.0


def load_m1(path: Path) -> list[dict[str, Any]]:
    raw = read_csv(path)
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if not raw or list(raw[0].keys()) != expected:
        raise RuntimeError(f"unexpected/empty M1 file: {path}")
    out = []
    previous = None
    for r in raw:
        t = datetime.strptime(r["time"], TIME_FORMAT)
        if previous is not None and t <= previous:
            raise RuntimeError(f"M1 time not strictly increasing: {path.name} {r['time']}")
        previous = t
        out.append({
            "time": t, "time_text": r["time"], "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]), "tick_volume": float(r["tick_volume"]),
            "spread": int(r["spread"]),
        })
    return out


def rank_average(values: list[float]) -> list[float]:
    pairs = sorted((v, i) for i, v in enumerate(values))
    ranks = [0.0] * len(values)
    j = 0
    while j < len(pairs):
        k = j + 1
        while k < len(pairs) and pairs[k][0] == pairs[j][0]:
            k += 1
        avg = (j + 1 + k) / 2.0
        for m in range(j, k):
            ranks[pairs[m][1]] = avg
        j = k
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    den = math.sqrt(sum(v*v for v in dx) * sum(v*v for v in dy))
    return None if den == 0 else sum(a*b for a,b in zip(dx,dy)) / den


def rci(closes: list[float], idx: int, period: int) -> float | None:
    if idx - period + 1 < 0:
        return None
    corr = pearson([float(i+1) for i in range(period)], rank_average(closes[idx-period+1:idx+1]))
    return None if corr is None else corr * 100.0


def bucket_start(t: datetime, minutes: int) -> datetime:
    md = t.hour * 60 + t.minute
    sm = (md // minutes) * minutes
    return t.replace(hour=sm // 60, minute=sm % 60, second=0, microsecond=0)


def aggregate(rows: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    groups: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[bucket_start(r["time"], minutes)].append(r)
    bars = []
    for start in sorted(groups):
        g = groups[start]
        bars.append({
            "start": start, "end": start + timedelta(minutes=minutes), "open": g[0]["open"],
            "high": max(x["high"] for x in g), "low": min(x["low"] for x in g), "close": g[-1]["close"],
            "m1_rows": len(g),
        })
    return bars


def asof_rci_features(bars: list[dict[str, Any]], boundary: datetime, prefix: str, direction: str) -> dict[str, Any]:
    idx = None
    for i, bar in enumerate(bars):
        if bar["end"] <= boundary:
            idx = i
        else:
            break
    if idx is None or idx < 19:
        raise RuntimeError(f"insufficient closed {prefix} history before {boundary.strftime(TIME_FORMAT)}")
    closes = [b["close"] for b in bars]
    r9, r14, r18 = rci(closes, idx, 9), rci(closes, idx, 14), rci(closes, idx, 18)
    p9, p2 = rci(closes, idx-1, 9), rci(closes, idx-2, 9)
    d1 = None if r9 is None or p9 is None else r9-p9
    pd = None if p9 is None or p2 is None else p9-p2
    acc = None if d1 is None or pd is None else d1-pd
    sign = 1.0 if direction == "LONG" else -1.0
    return {
        f"{prefix}_rci9": r9, f"{prefix}_rci14": r14, f"{prefix}_rci18": r18,
        f"{prefix}_directional_rci9": None if r9 is None else sign*r9,
        f"{prefix}_directional_rci9_delta1": None if d1 is None else sign*d1,
        f"{prefix}_directional_rci9_acceleration": None if acc is None else sign*acc,
    }


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def trade_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price-entry, entry) if direction == "LONG" else bps(entry-exit_price, entry)


def excursions(direction: str, entry: float, rows: list[dict[str, Any]], point: float) -> tuple[float,float]:
    fav, adv = [], []
    for row in rows:
        if direction == "LONG":
            fav.append(bps(row["high"]-entry, entry)); adv.append(bps(row["low"]-entry, entry))
        else:
            ah = row["high"] + row["spread"]*point; al = row["low"] + row["spread"]*point
            fav.append(bps(entry-al, entry)); adv.append(bps(entry-ah, entry))
    return max(fav), min(adv)


def is_turn_candidate(direction: str, rows: list[dict[str, Any]], idx: int, signal_bid: float) -> bool:
    if idx < 1:
        return False
    prev, cur = rows[idx-1], rows[idx]
    hist = rows[max(0, idx-TURN_LOOKBACK):idx]
    if len(hist) < TURN_LOOKBACK:
        return False
    if direction == "LONG":
        return prev["low"] <= min(r["low"] for r in hist) and prev["low"] < signal_bid and cur["close"] > prev["close"]
    return prev["high"] >= max(r["high"] for r in hist) and prev["high"] > signal_bid and cur["close"] < prev["close"]


def pullback_depth(direction: str, signal_bid: float, rows: list[dict[str, Any]]) -> float:
    if direction == "LONG":
        return bps(signal_bid-min(r["low"] for r in rows), signal_bid)
    return bps(max(r["high"] for r in rows)-signal_bid, signal_bid)


def pf(vals: list[float]) -> float | None:
    wins = sum(v for v in vals if v > 0)
    losses = abs(sum(v for v in vals if v < 0))
    return None if losses == 0 else wins/losses


def metrics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return {
        "count": len(vals), "win_rate": sum(v>0 for v in vals)/len(vals) if vals else None,
        "profit_factor_bps": pf(vals) if vals else None, "net_bps": sum(vals),
        "mean_bps": statistics.fmean(vals) if vals else None,
        "median_bps": statistics.median(vals) if vals else None,
    }


def replay_one(ticker: str, files_root: Path, built_at: str) -> tuple[list[dict[str,Any]], list[dict[str,Any]]]:
    series = load_indicator_series(files_root / M15_FILES[ticker])
    cutoff = CUT_OFF[ticker]
    signals: list[dict[str,Any]] = []
    pairs: list[dict[str,Any]] = []
    state = "IDLE"
    open_primary: dict[str,Any] | None = None
    seq = 0
    for current_index in range(MINIMUM_WARMUP_BARS, len(series.bars)):
        current_bar = series.bars[current_index]
        if current_bar.server_open >= cutoff:
            break
        selected_index = current_index - 1
        payload = build_feature_payload(
            series, selected_index=selected_index, ticker=ticker, timeframe="M15",
            source_filename=M15_FILES[ticker], decision_time_utc=current_bar.server_open,
            selected_utc_close=current_bar.server_open, selected_offset_hours=0.0, built_at_utc=built_at,
        )
        f = flatten_features(series, selected_index, payload)
        rci9 = float(f["rci9"])
        transition = None
        if state == "IDLE":
            if bool(f.get("rci9_turn_up")) and f.get("ema_alignment") == "BULLISH_STACK":
                transition = "PRIMARY_LONG"; state_after = "ACTIVE_LONG"
            elif bool(f.get("rci9_turn_down")) and f.get("ema_alignment") == "BEARISH_STACK":
                transition = "PRIMARY_SHORT"; state_after = "ACTIVE_SHORT"
            else:
                continue
        elif state == "ACTIVE_LONG":
            if rci9 >= LONG_EXIT_RCI9:
                transition = "LONG_EXIT"; state_after = "IDLE"
            else:
                continue
        else:
            if rci9 <= SHORT_EXIT_RCI9:
                transition = "SHORT_EXIT"; state_after = "IDLE"
            else:
                continue
        seq += 1
        row = {
            "replay_signal_id": f"{ticker}_{seq:06d}", "ticker": ticker, "server_open": current_bar.server_open.strftime(TIME_FORMAT),
            "transition": transition, "state_before": state, "state_after": state_after,
            "selected_feature_bar_server_open": series.bars[selected_index].server_open.strftime(TIME_FORMAT),
            "rci9": rci9, "rci9_delta1": f.get("rci9_delta1"), "rci9_turn_up": f.get("rci9_turn_up"),
            "rci9_turn_down": f.get("rci9_turn_down"), "ema_alignment": f.get("ema_alignment"),
            "current_m15_high_low_close_used": False, "future_used_for_candidate_generation": False,
            "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        }
        signals.append(row)
        if transition.startswith("PRIMARY_"):
            direction = "LONG" if transition == "PRIMARY_LONG" else "SHORT"
            open_primary = {**row, "direction": direction}
        else:
            if open_primary is None:
                raise RuntimeError(f"exit without open primary: {ticker} {row['server_open']}")
            pairs.append({
                "proxy_trade_id": f"{ticker}_T{len(pairs)+1:06d}", "ticker": ticker, "direction": open_primary["direction"],
                "entry_server_open": open_primary["server_open"], "exit_server_open": row["server_open"],
                "entry_signal_id": open_primary["replay_signal_id"], "exit_signal_id": row["replay_signal_id"],
                "entry_rci9": open_primary["rci9"], "entry_rci9_delta1": open_primary["rci9_delta1"],
                "entry_ema_alignment": open_primary["ema_alignment"], "exit_rci9": row["rci9"],
            })
            open_primary = None
        state = state_after
    return signals, pairs


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not meta_path.is_file():
        print("[M9C BLOCKED] M8B symbol metadata missing"); return 2
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print("[M9C BLOCKED] MT5 Files root unavailable"); return 2
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        all_signals, all_pairs = [], []
        for ticker in ("XAUUSD","BTCUSD"):
            sig, pairs = replay_one(ticker, files_root, built_at)
            all_signals.extend(sig); all_pairs.extend(pairs)

        m1 = {t: load_m1(files_root / M1_FILES[t]) for t in ("XAUUSD","BTCUSD")}
        m1_idx = {t: {r["time_text"]:i for i,r in enumerate(m1[t])} for t in m1}
        derived = {t: {name: aggregate(m1[t], mins) for name,mins in {"m5":5,"h1":60,"h4":240}.items()} for t in m1}
        resolved, turns = [], []
        point = {t: float(meta["symbols"][t]["point"]) for t in ("XAUUSD","BTCUSD")}
        for p in all_pairs:
            t=p["ticker"]; a=p["entry_server_open"]; z=p["exit_server_open"]
            if a not in m1_idx[t] or z not in m1_idx[t]:
                continue
            ai, zi = m1_idx[t][a], m1_idx[t][z]
            if zi <= ai: continue
            direction=p["direction"]; e=execution_entry(direction,m1[t][ai],point[t]); x=execution_exit(direction,m1[t][zi],point[t])
            mfe,mae=excursions(direction,e,m1[t][ai:zi+1],point[t])
            row={**p,"entry_exec_price":e,"exit_exec_price":x,"return_bps":trade_return(direction,e,x),
                 "mfe_bps":mfe,"mae_bps":mae,"holding_minutes_clock":int((m1[t][zi]["time"]-m1[t][ai]["time"]).total_seconds()/60)}
            for tf in ("m5","h1","h4"):
                row.update(asof_rci_features(derived[t][tf], m1[t][ai]["time"], f"signal_{tf}", direction))
            zone=float(row["signal_m5_directional_rci9"])
            row["signal_m5_directional_rci9_zone"]="GE_80" if zone>=80 else "50_TO_80" if zone>=50 else "MINUS50_TO_50" if zone>-50 else "LE_MINUS50"
            resolved.append(row)

            signal_bid=m1[t][ai]["open"]
            first=None
            for i in range(ai+1,zi):
                if i+1>=zi: break
                if is_turn_candidate(direction,m1[t],i,signal_bid):
                    ei=i+1; te=execution_entry(direction,m1[t][ei],point[t]); tmfe,tmae=excursions(direction,te,m1[t][ei:zi+1],point[t])
                    first={**p,"turn_confirmation_time":m1[t][i]["time_text"],"turn_entry_time":m1[t][ei]["time_text"],
                           "initial_pullback_depth_bps":pullback_depth(direction,signal_bid,m1[t][ai:i+1]),
                           "minutes_to_first_turn":int((m1[t][ei]["time"]-m1[t][ai]["time"]).total_seconds()/60),
                           "return_from_first_turn_bps":trade_return(direction,te,x),"mfe_from_first_turn_bps":tmfe,"mae_from_first_turn_bps":tmae,
                           "signal_m5_directional_rci9":row["signal_m5_directional_rci9"],"signal_m5_directional_rci9_zone":row["signal_m5_directional_rci9_zone"]}
                    for tf in ("m5","h1","h4"):
                        first.update(asof_rci_features(derived[t][tf], m1[t][ei]["time"], f"turn_{tf}", direction))
                    h1=float(first["turn_h1_directional_rci9_delta1"])>0; h4=float(first["turn_h4_directional_rci9_delta1"])>0
                    first["turn_htf_state"]="H1_AND_H4_WITH_TRADE" if h1 and h4 else "H1_ONLY_WITH_TRADE" if h1 else "H4_ONLY_WITH_TRADE" if h4 else "NEITHER_WITH_TRADE"
                    break
            if first: turns.append(first)
    except Exception as exc:
        print(f"[M9C BLOCKED] {exc}"); return 2

    def group(rows,key,retkey):
        out=[]
        for label in sorted({str(r[key]) for r in rows}):
            g=[r for r in rows if str(r[key])==label]; m=metrics(g,retkey)
            out.append({"grouping":key,"group":label,**m})
        return out

    td=[]
    for t,d in sorted({(r["ticker"],r["direction"]) for r in resolved}):
        g=[r for r in resolved if r["ticker"]==t and r["direction"]==d]
        td.append({"ticker":t,"direction":d,**metrics(g,"return_bps")})
    summary={
        "project":"MOCHIPOYO_ALERT_RESEARCH","stage":"M9C_FROZEN_PROXY_HISTORICAL_REPLAY","status":"PASS_EXPLORATORY_ONLY",
        "run_at_utc":built_at,"audit_only":True,"population_tier":"TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "signal_count":len(all_signals),"paired_trade_count":len(all_pairs),"m1_resolved_trade_count":len(resolved),
        "first_turn_count":len(turns),"m1_resolved_metrics":metrics(resolved,"return_bps"),
        "first_turn_metrics":metrics(turns,"return_from_first_turn_bps"),
        "cutoffs":{k:v.strftime(TIME_FORMAT) for k,v in CUT_OFF.items()},
        "formula":{"PRIMARY_LONG":"IDLE AND rci9_turn_up AND BULLISH_STACK","PRIMARY_SHORT":"IDLE AND rci9_turn_down AND BEARISH_STACK",
                   "LONG_EXIT":f"ACTIVE_LONG AND rci9>={LONG_EXIT_RCI9}","SHORT_EXIT":f"ACTIVE_SHORT AND rci9<={SHORT_EXIT_RCI9}"},
        "guardrails":{"source_truth":False,"formula_tuned_on_replay":False,"threshold_promotable":False,"m8c_reset":False,"m7c_changed":False}
    }
    quality={
        "m15_feature_engine":"existing feature_snapshot_builder + alert_trigger_signature_audit.flatten_features",
        "minimum_warmup_bars":MINIMUM_WARMUP_BARS,"current_m15_high_low_close_used":False,"future_used_for_candidate_generation":False,
        "exact_m1_entry_exit_required_for_outcome":True,"nearest_m1_fallback_used":False,"historical_spread_used":True,
        "commission":"NOT_MODELED","swap":"NOT_MODELED","mt5_files_root":str(files_root)
    }
    out_root=local_root/"outputs"/"M9C"; stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"); arc=out_root/"archive"/stamp
    arc.mkdir(parents=True,exist_ok=False)
    dump_json(arc/"01_summary.json",summary); write_csv(arc/"02_replay_signal_ledger.csv",all_signals); write_csv(arc/"03_replay_trade_pairs.csv",all_pairs)
    write_csv(arc/"04_m1_resolved_trade_outcomes.csv",resolved); write_csv(arc/"05_first_turn_context.csv",turns)
    write_csv(arc/"06_m5_zone_summary.csv",group(turns,"signal_m5_directional_rci9_zone","return_from_first_turn_bps"))
    write_csv(arc/"07_turn_htf_summary.csv",group(turns,"turn_htf_state","return_from_first_turn_bps")); write_csv(arc/"08_ticker_direction_summary.csv",td)
    dump_json(arc/"09_data_quality.json",quality)
    (arc/"00_READ_ME_FIRST.txt").write_text("M9C frozen M7C proxy historical replay. Tier B is NOT genuine Mochipoyo source truth. Formula is not tuned on replay results.\n",encoding="utf-8")
    (arc/"10_audit.log").write_text(f"status=PASS_EXPLORATORY_ONLY\nsignals={len(all_signals)}\npaired_trades={len(all_pairs)}\nm1_resolved={len(resolved)}\nfirst_turn={len(turns)}\npopulation_tier=TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH\n",encoding="utf-8")
    names=["00_READ_ME_FIRST.txt","01_summary.json","02_replay_signal_ledger.csv","03_replay_trade_pairs.csv","04_m1_resolved_trade_outcomes.csv","05_first_turn_context.csv","06_m5_zone_summary.csv","07_turn_htf_summary.csv","08_ticker_direction_summary.csv","09_data_quality.json","10_audit.log"]
    with zipfile.ZipFile(arc/"99_UPLOAD_PACKAGE.zip","w",zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(arc/n,n)
    latest=out_root/"LATEST"; shutil.rmtree(latest,ignore_errors=True); shutil.copytree(arc,latest)
    print(f"[M9C PASS] signals={len(all_signals)} paired={len(all_pairs)} m1_resolved={len(resolved)} first_turn={len(turns)}")
    print("[M9C OUTPUT]",latest); return 0


if __name__ == "__main__":
    raise SystemExit(main())
