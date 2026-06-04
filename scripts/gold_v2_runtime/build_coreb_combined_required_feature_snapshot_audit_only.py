#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEF = ROOT / "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json"
READY = "FROZEN_COREB_COMBINED_EVALUATOR_DEFINITION_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"
OUT_NAME = "gold_v2_coreb_combined_required_feature_snapshot.csv"

M15_NAMES = ["goldsharp_m15.csv", "gold#_m15.csv", "xauusd_m15.csv", "gold_m15.csv", "candles_history_M15.csv"]
M5_NAMES = ["goldsharp_m5.csv", "gold#_m5.csv", "xauusd_m5.csv", "gold_m5.csv", "candles_history_M5.csv", "M5_backtest.csv"]

TIME_CANDIDATES = ["time", "datetime", "date", "timestamp", "open_time", "Time", "Date", "DATE", "Gmt time"]
COLMAP = {
    "open": ["open", "Open", "OPEN", "o"],
    "high": ["high", "High", "HIGH", "h"],
    "low": ["low", "Low", "LOW", "l"],
    "close": ["close", "Close", "CLOSE", "c"],
}


def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent


def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_combined_required_feature_snapshot_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def find_file(names: list[str]) -> Path | None:
    roots = [files_dir(), files_dir() / "FX_OUTPUTS", ROOT]
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            direct = root / name
            if direct.exists():
                return direct
        for name in names:
            hits = list(root.rglob(name))
            if hits:
                return hits[0]
    return None


def read_csv_any(path: Path) -> pd.DataFrame:
    last = None
    for kw in [{"sep": None, "engine": "python"}, {"sep": ","}, {"sep": ";"}, {"sep": "\t"}]:
        try:
            df = pd.read_csv(path, **kw)
            if len(df.columns) > 1:
                return df
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV_READ_FAILED {path}: {last}")


def normalize_ohlc(path: Path, timeframe: str) -> pd.DataFrame:
    raw = read_csv_any(path)
    cols = list(raw.columns)
    time_col = None
    for c in TIME_CANDIDATES:
        if c in cols:
            time_col = c
            break
    if time_col is None:
        time_col = cols[0]
    out = pd.DataFrame()
    out["time"] = pd.to_datetime(raw[time_col], errors="coerce")
    for target, candidates in COLMAP.items():
        src = next((c for c in candidates if c in cols), None)
        if src is None:
            raise RuntimeError(f"OHLC_COLUMN_MISSING {target} in {path}")
        out[target] = pd.to_numeric(raw[src], errors="coerce")
    out = out.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
    out = out.drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    out["source_timeframe"] = timeframe
    return out


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean().replace(0, np.nan)


def add_base_features(df: pd.DataFrame, fields: set[str]) -> pd.DataFrame:
    res = df.copy()
    atr = atr14(res)
    res["atr14_candidate"] = atr
    need_windows: set[int] = set()
    for f in fields:
        for pat in [r"(?:abs_)?ret_(\d+)_atr", r"range_(\d+)_atr", r"dist_low_(\d+)_atr", r"dist_high_(\d+)_atr", r"donch_pos_(\d+)"]:
            m = re.fullmatch(pat, f)
            if m:
                need_windows.add(int(m.group(1)))
    for f in fields:
        m = re.fullmatch(r"compression_range_(\d+)_(\d+)", f)
        if m:
            need_windows.add(int(m.group(1))); need_windows.add(int(m.group(2)))
    range_cache: dict[int, pd.Series] = {}
    for n in sorted(need_windows):
        hi = res["high"].rolling(n, min_periods=n).max()
        lo = res["low"].rolling(n, min_periods=n).min()
        rng = (hi - lo) / atr
        range_cache[n] = rng
        if f"range_{n}_atr" in fields:
            res[f"range_{n}_atr"] = rng
        if f"dist_low_{n}_atr" in fields:
            res[f"dist_low_{n}_atr"] = (res["close"] - lo) / atr
        if f"dist_high_{n}_atr" in fields:
            res[f"dist_high_{n}_atr"] = (hi - res["close"]) / atr
        if f"donch_pos_{n}" in fields:
            den = (hi - lo).replace(0, np.nan)
            res[f"donch_pos_{n}"] = (res["close"] - lo) / den
        if f"ret_{n}_atr" in fields or f"abs_ret_{n}_atr" in fields:
            ret = (res["close"] - res["close"].shift(n)) / atr
            if f"ret_{n}_atr" in fields:
                res[f"ret_{n}_atr"] = ret
            if f"abs_ret_{n}_atr" in fields:
                res[f"abs_ret_{n}_atr"] = ret.abs()
    for f in fields:
        m = re.fullmatch(r"compression_range_(\d+)_(\d+)", f)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            res[f] = range_cache[a] / range_cache[b].replace(0, np.nan)
        m = re.fullmatch(r"ema(\d+)_slope_(\d+)_atr", f)
        if m:
            span, lag = int(m.group(1)), int(m.group(2))
            ema = res["close"].ewm(span=span, adjust=False, min_periods=span).mean()
            res[f] = (ema - ema.shift(lag)) / atr
    if "upper_wick_atr" in fields:
        res["upper_wick_atr"] = (res["high"] - res[["open", "close"]].max(axis=1)) / atr
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m15-csv", default=None)
    ap.add_argument("--m5-csv", default=None)
    args = ap.parse_args()
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    if not DEF.exists():
        summary = {"created_utc": created, "status": "COREB_COMBINED_DEFINITION_MISSING", "audit_only": True, "final_signal_allowed": False, "step13_allowed": False}
        write_json(out / "gold_v2_coreb_combined_required_feature_snapshot_summary.json", summary)
        return 2
    definition = read_json(DEF)
    required = sorted({str(x).strip() for x in definition.get("required_fields", []) if str(x).strip()})
    if definition.get("status") != READY or not required:
        summary = {"created_utc": created, "status": "COREB_COMBINED_DEFINITION_NOT_READY", "audit_only": True, "definition_status": definition.get("status"), "required_field_count": len(required), "final_signal_allowed": False, "step13_allowed": False}
        write_json(out / "gold_v2_coreb_combined_required_feature_snapshot_summary.json", summary)
        return 2
    m15_path = Path(args.m15_csv) if args.m15_csv else find_file(M15_NAMES)
    m5_path = Path(args.m5_csv) if args.m5_csv else find_file(M5_NAMES)
    if not m15_path or not m15_path.exists() or not m5_path or not m5_path.exists():
        summary = {"created_utc": created, "status": "OHLC_SOURCE_MISSING", "audit_only": True, "m15_csv": str(m15_path) if m15_path else None, "m5_csv": str(m5_path) if m5_path else None, "final_signal_allowed": False, "step13_allowed": False}
        write_json(out / "gold_v2_coreb_combined_required_feature_snapshot_summary.json", summary)
        return 2
    m15 = normalize_ohlc(m15_path, "M15")
    m5 = normalize_ohlc(m5_path, "M5")
    base_fields = {f for f in required if not f.startswith("m5_")}
    m5_inner_fields = {f[3:] for f in required if f.startswith("m5_")}
    m15f = add_base_features(m15, base_fields)
    m5f = add_base_features(m5, m5_inner_fields)
    m5_cols = ["time"] + sorted(m5_inner_fields)
    m5_join = m5f[m5_cols].copy().rename(columns={c: f"m5_{c}" for c in m5_cols if c != "time"})
    merged = pd.merge_asof(m15f.sort_values("time"), m5_join.sort_values("time"), on="time", direction="backward")
    out_cols = ["time", "open", "high", "low", "close"] + required
    for c in required:
        if c not in merged.columns:
            merged[c] = np.nan
    snapshot = merged[out_cols].copy()
    complete_mask = snapshot[required].notna().all(axis=1)
    snapshot["coreb_combined_required_fields_complete"] = complete_mask
    snapshot_path = out / OUT_NAME
    snapshot.to_csv(snapshot_path, index=False, encoding="utf-8-sig")
    schema_rows = []
    for f in required:
        nonnull = int(snapshot[f].notna().sum())
        schema_rows.append({"field": f, "present": f in snapshot.columns, "non_null_count": nonnull, "missing_count": int(len(snapshot)-nonnull)})
    pd.DataFrame(schema_rows).to_csv(out / "gold_v2_coreb_combined_required_feature_schema.csv", index=False, encoding="utf-8-sig")
    missing = [r["field"] for r in schema_rows if r["non_null_count"] == 0]
    status = "COREB_COMBINED_REQUIRED_FEATURE_SNAPSHOT_READY_CANDIDATE_FORMULA_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED" if not missing else "COREB_COMBINED_REQUIRED_FEATURE_SNAPSHOT_BLOCKED_ZERO_VALUE_FIELDS"
    summary = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "formula_source_status": "CANDIDATE_FORMULA_NOT_SOURCE_VALIDATED",
        "formula_engine": "candidate rolling ATR14 / rolling Donchian / EMA slopes / merge_asof M5 to M15",
        "definition_id": definition.get("definition_id"),
        "entry_logic": definition.get("entry_logic"),
        "m15_csv": str(m15_path),
        "m5_csv": str(m5_path),
        "row_count": int(len(snapshot)),
        "complete_row_count": int(complete_mask.sum()),
        "required_field_count": int(len(required)),
        "zero_value_field_count": int(len(missing)),
        "zero_value_fields": missing,
        "snapshot_csv": str(snapshot_path),
        "feature_schema_csv": str(out / "gold_v2_coreb_combined_required_feature_schema.csv"),
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "important_note": "This snapshot is candidate-formula audit only. It is not proof of parity with exploration features and must not be connected to live/final signals.",
        "output_dir": str(out),
    }
    write_json(out / "gold_v2_coreb_combined_required_feature_snapshot_summary.json", summary)
    report = ["# GOLD V2 CoreB combined required feature snapshot audit-only report", ""] + [f"- {k}: `{v}`" for k, v in summary.items() if k != "zero_value_fields"]
    report += ["", "## zero_value_fields"] + [f"- `{x}`" for x in missing]
    (out / "GOLD_V2_COREB_COMBINED_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not missing else 2

if __name__ == "__main__":
    raise SystemExit(main())
