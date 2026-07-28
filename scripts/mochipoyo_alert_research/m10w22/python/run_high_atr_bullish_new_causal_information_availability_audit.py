from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m10a" / "python",):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import payoff_rules as pay

STAGE = "M10W22_HIGH_ATR_BULLISH_NEW_CAUSAL_INFORMATION_AVAILABILITY_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w22_high_atr_bullish_new_causal_information_availability_contract_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
POINT = c.POINT


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


def verify_and_load(data_root: Path) -> tuple[dict[str, list[c.Bar]], dict[str, str], dict[str, Path]]:
    bars: dict[str, list[c.Bar]] = {}
    hashes: dict[str, str] = {}
    paths: dict[str, Path] = {}
    for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1"):
        filename, expected_hash = c.EXPECTED_FILES[timeframe]
        path = data_root / filename
        if not path.is_file():
            raise RuntimeError(f"missing frozen GOLD file: {path}")
        actual_hash = c.sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"frozen SHA256 mismatch {timeframe}: {actual_hash} expected={expected_hash}")
        bars[timeframe] = c.load_bars(path)
        hashes[timeframe] = actual_hash
        paths[timeframe] = path
    return bars, hashes, paths


def atr_percentile100(bars: list[c.Bar]) -> list[float | None]:
    atr = pay.wilder_atr14(bars)
    out: list[float | None] = [None] * len(atr)
    for i in range(99, len(atr)):
        window = atr[i - 99:i + 1]
        if any(value is None or not math.isfinite(float(value)) for value in window):
            continue
        current = float(atr[i])
        vals = [float(value) for value in window if value is not None]
        out[i] = sum(value <= current for value in vals) / len(vals)
    return out


def macd_line_bps(bars: list[c.Bar]) -> list[float]:
    closes = [float(bar.close) for bar in bars]
    fast = c.ema(closes, 6)
    slow = c.ema(closes, 13)
    return [(a - b) / max(abs(close), 1e-12) * 10000.0 for a, b, close in zip(fast, slow, closes)]


def safe_ratio(num: float, den: float) -> float | None:
    return None if den <= 0 or not math.isfinite(den) else num / den


def bar_shape(bar: c.Bar) -> dict[str, float | None]:
    rng = float(bar.high - bar.low)
    if rng <= 0:
        return {"body_ratio":None,"close_location":None,"lower_wick_ratio":None,"upper_wick_ratio":None}
    body = abs(float(bar.close - bar.open))
    lower = float(min(bar.open, bar.close) - bar.low)
    upper = float(bar.high - max(bar.open, bar.close))
    return {
        "body_ratio":body / rng,
        "close_location":float(bar.close - bar.low) / rng,
        "lower_wick_ratio":lower / rng,
        "upper_wick_ratio":upper / rng,
    }


def real_volume_nonzero_fraction(path: Path) -> dict[str, Any]:
    total = 0
    nonzero = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "real_volume" not in (reader.fieldnames or []):
            return {"field_present":False,"row_count":0,"nonzero_count":0,"nonzero_fraction":None}
        for row in reader:
            total += 1
            try:
                value = float(row.get("real_volume", "0") or 0)
            except ValueError:
                value = 0.0
            if value != 0.0:
                nonzero += 1
    return {"field_present":True,"row_count":total,"nonzero_count":nonzero,"nonzero_fraction":nonzero / total if total else None}


def qsorted(values: list[float], q: float) -> float:
    return c.quantile_sorted(sorted(values), q)


def feature_summary(rows: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    vals = [float(row[feature]) for row in rows if row.get(feature) is not None and math.isfinite(float(row[feature]))]
    total = len(rows)
    if not vals:
        return {"feature":feature,"row_count":total,"available_count":0,"missing_count":total,"available_fraction":0.0,"unique_count":0,"variance":None,"min":None,"p05":None,"p25":None,"p50":None,"p75":None,"p95":None,"max":None}
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return {
        "feature":feature,
        "row_count":total,
        "available_count":len(vals),
        "missing_count":total-len(vals),
        "available_fraction":len(vals)/total if total else None,
        "unique_count":len(set(vals)),
        "variance":variance,
        "min":min(vals),"p05":qsorted(vals,0.05),"p25":qsorted(vals,0.25),"p50":qsorted(vals,0.50),"p75":qsorted(vals,0.75),"p95":qsorted(vals,0.95),"max":max(vals),
    }


def build_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    m1,m5,m15,h1,h4,d1=(bars[k] for k in ("M1","M5","M15","H1","H4","D1"))
    h1_line=macd_line_bps(h1)
    h1_atrp=atr_percentile100(h1)
    h4_close=[float(b.close) for b in h4]
    h4_e20,h4_e30=c.ema(h4_close,20),c.ema(h4_close,30)
    d1_close=[float(b.close) for b in d1]
    d1_e20,d1_e30,d1_e40=c.ema(d1_close,20),c.ema(d1_close,30),c.ema(d1_close,40)
    h1_ct=[b.time+timedelta(hours=1) for b in h1]
    h4_ct=[b.time+timedelta(hours=4) for b in h4]
    d1_ct=[b.time+timedelta(days=1) for b in d1]
    m5_ct=[b.time+timedelta(minutes=5) for b in m5]
    m1_ct=[b.time+timedelta(minutes=1) for b in m1]

    rows: list[dict[str, Any]]=[]
    for decision_bar in m15[1:]:
        decision=decision_bar.time
        ih1=bisect.bisect_right(h1_ct,decision)-1
        ih4=bisect.bisect_right(h4_ct,decision)-1
        id1=bisect.bisect_right(d1_ct,decision)-1
        i5=bisect.bisect_right(m5_ct,decision)-1
        i1=bisect.bisect_right(m1_ct,decision)-1
        if min(ih1,ih4,id1,i5,i1) < 0 or h1_atrp[ih1] is None:
            continue
        regime=(d1_e20[id1]>d1_e30[id1]>d1_e40[id1] and h4_e20[ih4]>h4_e30[ih4] and h1_line[ih1]>0 and float(h1_atrp[ih1])>=0.67)
        if not regime:
            continue
        if i5 < 19 or i1 < 4 or i5 < 3:
            continue
        last5=m5[i5]
        shape5=bar_shape(last5)
        vol_mean=sum(float(m5[j].tick_volume) for j in range(i5-19,i5+1))/20.0
        m5_ret3=(float(m5[i5].close)/max(abs(float(m5[i5-3].close)),1e-12)-1.0)*10000.0
        m5_range3=(max(float(m5[j].high) for j in range(i5-2,i5+1))-min(float(m5[j].low) for j in range(i5-2,i5+1)))/max(abs(float(m5[i5].close)),1e-12)*10000.0
        last1=m1[i1]
        shape1=bar_shape(last1)
        m1_ret5=(float(m1[i1].close)/max(abs(float(m1[i1-4].open)),1e-12)-1.0)*10000.0
        m1_up_count=sum(float(m1[j].close)>float(m1[j].open) for j in range(i1-4,i1+1))
        m1_range5=(max(float(m1[j].high) for j in range(i1-4,i1+1))-min(float(m1[j].low) for j in range(i1-4,i1+1)))/max(abs(float(m1[i1].close)),1e-12)*10000.0
        spread_bps=(int(last1.spread)*POINT)/max(abs(float(last1.close)),1e-12)*10000.0
        rows.append({
            "decision_time":decision.strftime(TIME_FORMAT),"year":decision.year,
            "h1_atr_pct100":float(h1_atrp[ih1]),
            "m5_tick_volume_ratio20":safe_ratio(float(last5.tick_volume),vol_mean),
            "m5_body_ratio":shape5["body_ratio"],"m5_close_location":shape5["close_location"],"m5_lower_wick_ratio":shape5["lower_wick_ratio"],"m5_upper_wick_ratio":shape5["upper_wick_ratio"],
            "m5_ret3_bps":m5_ret3,"m5_range3_bps":m5_range3,
            "m1_ret5_bps":m1_ret5,"m1_up_close_count5":m1_up_count,"m1_close_location":shape1["close_location"],"m1_range5_bps":m1_range5,"last_closed_m1_spread_bps":spread_bps,
            "m5_source_open":last5.time.strftime(TIME_FORMAT),"m1_source_open":last1.time.strftime(TIME_FORMAT),
        })
    return rows


def main() -> int:
    local_root=Path(os.environ.get("LOCALAPPDATA",""))/"xauusd_signal_lab"/"mochipoyo_alert_research"
    output_root=local_root/"outputs"/"M10W22"
    try:
        contract=load_json(CONTRACT)
        if contract.get("stage")!=STAGE or contract.get("status")!="DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W22 contract")
        data_root=resolve_data_root(local_root)
        bars,hashes,paths=verify_and_load(data_root)
        rows=build_rows(bars)
        if not rows:
            raise RuntimeError("no target-regime rows")
        features=["h1_atr_pct100","m5_tick_volume_ratio20","m5_body_ratio","m5_close_location","m5_lower_wick_ratio","m5_upper_wick_ratio","m5_ret3_bps","m5_range3_bps","m1_ret5_bps","m1_up_close_count5","m1_close_location","m1_range5_bps","last_closed_m1_spread_bps"]
        groups: dict[str,list[dict[str,Any]]]={"ALL":rows}
        for year in (2023,2024,2025,2026):
            groups[str(year)]=[row for row in rows if int(row["year"])==year]
        summaries=[]
        for group_name,items in groups.items():
            for feature in features:
                summaries.append({"group":group_name,**feature_summary(items,feature)})
        real_volume={"M1":real_volume_nonzero_fraction(paths["M1"]),"M5":real_volume_nonzero_fraction(paths["M5"])}
        year_counts={str(y):sum(int(r["year"])==y for r in rows) for y in (2023,2024,2025,2026)}
        degenerate=[r for r in summaries if r["group"]=="ALL" and (int(r["unique_count"])<=1 or (r["variance"] is not None and float(r["variance"])==0.0))]
        summary={
            "project":"MOCHIPOYO_ALERT_RESEARCH","stage":STAGE,"status":"PASS_OUTCOME_BLIND_CAUSAL_INFORMATION_AVAILABILITY_AUDIT","built_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),"scope":"XAUUSD_GOLD_ONLY",
            "target_regime":contract["target_regime"],"target_regime_decision_count":len(rows),"year_counts":year_counts,"verified_sha256":hashes,
            "real_volume_availability":real_volume,"degenerate_features":degenerate,
            "all_feature_summary":{r["feature"]:r for r in summaries if r["group"]=="ALL"},
            "interpretation":{"trade_outcomes_read":False,"future_return_computed":False,"pf_or_pnl_computed":False,"feature_profit_ranking":False,"threshold_selection":False,"entry_formula_created":False,"next":"Review availability/variability only. If viable, preregister at most three microstructure families before any outcome evaluation."},
            "guardrails":contract["safety"],
        }
        stamp=datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive=output_root/"archive"/stamp
        archive.mkdir(parents=True,exist_ok=False)
        (archive/"00_READ_ME_FIRST.txt").write_text("M10W22 outcome-blind causal-information availability audit. No future return, PF/PnL, win/loss labels, or outcome correlation are computed.\n",encoding="utf-8")
        (archive/"01_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        write_csv(archive/"02_target_regime_causal_feature_rows.csv",rows)
        write_csv(archive/"03_feature_availability_and_quantiles.csv",summaries)
        (archive/"04_real_volume_availability.json").write_text(json.dumps(real_volume,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"05_data_quality.json").write_text(json.dumps({"data_root":str(data_root),"verified_sha256":hashes,"closed_rows_contract":True,"time_basis":"MT5_SERVER_TIME","lower_tf_nominal_close_le_decision":True,"trade_outcomes_read":False,"future_return_computed":False,"pf_or_pnl_computed":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"06_audit.log").write_text("\n".join(["status=PASS_OUTCOME_BLIND_CAUSAL_INFORMATION_AVAILABILITY_AUDIT",f"target_regime_rows={len(rows)}","trade_outcomes_read=false","future_return_computed=false","pf_or_pnl_computed=false","feature_profit_ranking=false","threshold_selection=false","entry_formula_created=false","M10W19_modified=false",""]),encoding="utf-8")
        latest=output_root/"LATEST"
        if latest.exists(): shutil.rmtree(latest)
        shutil.copytree(archive,latest)
        package=latest/"99_UPLOAD_PACKAGE.zip"
        names=["00_READ_ME_FIRST.txt","01_summary.json","02_target_regime_causal_feature_rows.csv","03_feature_availability_and_quantiles.csv","04_real_volume_availability.json","05_data_quality.json","06_audit.log"]
        with zipfile.ZipFile(package,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names: zf.write(latest/name,arcname=name)
        print(f"[M10W22 PASS] target_regime_rows={len(rows)} years={year_counts}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W22 BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
        print("[SAFE] No outcome analysis, threshold selection, monitor modification or forward backfill was attempted.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
