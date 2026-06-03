#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a GOLD latest M15 feature snapshot and MEDIUM feature probe.

This is audit-only. It does not send notifications, call external APIs, place
orders, or connect to a live hook.

Purpose:
  1. Show the latest M15 market feature values used by later live-audit rules.
  2. Probe the MEDIUM feature gates without pretending CoreA/CoreB re-generation
     has already been connected.

Important:
  MEDIUM production eligibility requires CoreA/CoreB arbitration. This script
  only reports feature-gate hits as FEATURE_PROBE_ONLY.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


RANGE96_REFINED = {
    "name": "RANGE96_REFINED",
    "direction": "SELL",
    "conditions": {
        "range96_min": 129.6835,
        "trend_eff96_max": 0.355591,
    },
    "notes": "CoreA Reject補助。実シグナル化にはCoreA/CoreB arbitrationが必要。",
}
VOL_TRMEAN32_REFINED = {
    "name": "VOL_TRMEAN32_REFINED",
    "direction": "PROBE",
    "conditions": {
        "tr_mean_32_min": 10.867578,
        "ret96_max": -2.725,
        "range96_min": 176.453,
    },
    "notes": "CoreA Reject補助。実シグナル化にはCoreA/CoreB arbitrationが必要。",
}
TIER2_HVT = {
    "name": "TIER2_HVT",
    "direction": "PROBE",
    "conditions": {
        "trend_eff96_max": 0.4,
        "ret96_max": -25.0,
        "tr_mean_32_min": 10.867578,
    },
    "notes": "Tier2 high-vol trend proxy。signal_ABC/CoreA Reject未接続のためFEATURE_PROBE_ONLY。",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GOLD latest M15 feature snapshot audit probe")
    parser.add_argument("--candles-m15", default=None)
    parser.add_argument("--eval-time", default=None, help="Optional explicit candle time to inspect")
    parser.add_argument("--dataset", default="2026")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_latest_feature_snapshot_audit_only"


def find_default_m15_csv() -> Optional[Path]:
    base = files_dir_from_repo()
    candidates = [
        base / "gold#_m15.csv",
        base / "goldsharp_m15.csv",
        base / "candles_history_M15.csv",
        base / "FX_OUTPUTS" / "gold#_m15.csv",
        base / "FX_OUTPUTS" / "goldsharp_m15.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def detect_col(columns: Sequence[str], names: Sequence[str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in columns}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def detect_time_col(columns: Sequence[str]) -> Optional[str]:
    return detect_col(columns, ["time", "datetime", "date", "open_time", "timestamp", "gmt time", "time_open"]) or (columns[0] if columns else None)


def read_candles(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(path)
    cols = list(df.columns)
    time_col = detect_time_col(cols)
    open_col = detect_col(cols, ["open", "bidopen", "bid_open"])
    high_col = detect_col(cols, ["high", "bidhigh", "bid_high"])
    low_col = detect_col(cols, ["low", "bidlow", "bid_low"])
    close_col = detect_col(cols, ["close", "bidclose", "bid_close"])
    required = {"time": time_col, "open": open_col, "high": high_col, "low": low_col, "close": close_col}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"Missing candle columns {missing} in {path}. columns={cols}")
    out = pd.DataFrame({
        "time": pd.to_datetime(df[time_col], errors="coerce"),
        "open": pd.to_numeric(df[open_col], errors="coerce"),
        "high": pd.to_numeric(df[high_col], errors="coerce"),
        "low": pd.to_numeric(df[low_col], errors="coerce"),
        "close": pd.to_numeric(df[close_col], errors="coerce"),
    })
    out = out.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)
    if out.empty:
        raise ValueError(f"No valid candles in {path}")
    return out


def normalize_ts(value: Any) -> Optional[pd.Timestamp]:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_localize(None) if getattr(ts, "tzinfo", None) is not None else pd.Timestamp(ts)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["close"].shift(1)
    tr1 = out["high"] - out["low"]
    tr2 = (out["high"] - prev_close).abs()
    tr3 = (out["low"] - prev_close).abs()
    out["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["tr_mean_32"] = out["tr"].rolling(32, min_periods=32).mean()
    out["ret96"] = out["close"] - out["close"].shift(96)
    out["range96"] = out["high"].rolling(96, min_periods=96).max() - out["low"].rolling(96, min_periods=96).min()
    out["trend_eff96"] = (out["ret96"].abs() / out["range96"].replace(0, pd.NA)).astype("float64")
    out["range32"] = out["high"].rolling(32, min_periods=32).max() - out["low"].rolling(32, min_periods=32).min()
    out["ret32"] = out["close"] - out["close"].shift(32)
    out["body"] = (out["close"] - out["open"]).abs()
    out["direction_bar"] = out.apply(lambda r: "BUY" if r["close"] > r["open"] else ("SELL" if r["close"] < r["open"] else "FLAT"), axis=1)
    return out


def as_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except Exception:
        return None
    if math.isnan(v):
        return None
    return v


def check_rule(snapshot: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    cond = rule["conditions"]
    checks: Dict[str, bool] = {}
    if "range96_min" in cond:
        checks["range96_min"] = (as_float(snapshot.get("range96")) or float("-inf")) >= float(cond["range96_min"])
    if "range96_max" in cond:
        checks["range96_max"] = (as_float(snapshot.get("range96")) or float("inf")) <= float(cond["range96_max"])
    if "trend_eff96_max" in cond:
        checks["trend_eff96_max"] = (as_float(snapshot.get("trend_eff96")) or float("inf")) <= float(cond["trend_eff96_max"])
    if "ret96_max" in cond:
        checks["ret96_max"] = (as_float(snapshot.get("ret96")) or float("inf")) <= float(cond["ret96_max"])
    if "tr_mean_32_min" in cond:
        checks["tr_mean_32_min"] = (as_float(snapshot.get("tr_mean_32")) or float("-inf")) >= float(cond["tr_mean_32_min"])
    return {
        "name": rule["name"],
        "direction": rule.get("direction"),
        "feature_gate_hit": all(checks.values()) if checks else False,
        "checks": checks,
        "conditions": cond,
        "status": "FEATURE_PROBE_ONLY",
        "notes": rule.get("notes"),
    }


def fmt_value(value: Any) -> str:
    v = as_float(value)
    if v is None:
        return "-"
    return f"{v:.6f}"


def build_report(packet: Dict[str, Any]) -> str:
    snap = packet["snapshot"]
    lines: List[str] = []
    lines.append("# GOLD V2 latest feature snapshot audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {packet['created_utc']}")
    lines.append(f"Status: {packet['status']}")
    lines.append(f"Dataset: {packet['dataset']}")
    lines.append(f"Eval time: {packet['eval_time']}")
    lines.append("")
    lines.append("## Feature snapshot")
    lines.append("")
    for k in ["open", "high", "low", "close", "ret96", "range96", "trend_eff96", "tr_mean_32", "ret32", "range32", "direction_bar"]:
        lines.append(f"- {k}: `{snap.get(k)}`")
    lines.append("")
    lines.append("## MEDIUM feature probes")
    lines.append("")
    for probe in packet["medium_feature_probes"]:
        lines.append(f"### {probe['name']}")
        lines.append(f"- feature_gate_hit: `{probe['feature_gate_hit']}`")
        lines.append(f"- status: `{probe['status']}`")
        lines.append(f"- notes: {probe['notes']}")
        lines.append("- checks:")
        for ck, cv in probe["checks"].items():
            lines.append(f"  - {ck}: `{cv}`")
        lines.append("")
    lines.append("No external notification or order execution is performed.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    candle_path = Path(args.candles_m15).expanduser().resolve() if args.candles_m15 else find_default_m15_csv()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    if candle_path is None or not candle_path.exists():
        print("[ERROR] M15 candle CSV not found. Use --candles-m15.")
        return 2
    try:
        candles = read_candles(candle_path)
        features = compute_features(candles)
    except Exception as exc:
        print(f"[ERROR] failed to compute features: {exc}")
        return 2
    if args.eval_time:
        ts = normalize_ts(args.eval_time)
        if ts is None:
            print(f"[ERROR] invalid --eval-time: {args.eval_time}")
            return 2
        row_df = features[features["time"] == ts]
        if row_df.empty:
            print(f"[ERROR] eval time not found in M15 candles: {args.eval_time}")
            return 2
        row = row_df.iloc[-1]
    else:
        row = features.iloc[-1]
    eval_time = pd.Timestamp(row["time"]).strftime("%Y-%m-%d %H:%M:%S")
    fields = ["open", "high", "low", "close", "tr", "tr_mean_32", "ret96", "range96", "trend_eff96", "range32", "ret32", "body", "direction_bar"]
    snapshot: Dict[str, Any] = {"time": eval_time}
    for k in fields:
        value = row.get(k)
        if isinstance(value, (int, float)) and not pd.isna(value):
            snapshot[k] = float(value)
        elif pd.isna(value):
            snapshot[k] = None
        else:
            snapshot[k] = value
    probes = [check_rule(snapshot, rule) for rule in [RANGE96_REFINED, VOL_TRMEAN32_REFINED, TIER2_HVT]]
    packet = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_FEATURE_SNAPSHOT",
        "dataset": str(args.dataset),
        "eval_time": eval_time,
        "candle_path": str(candle_path),
        "audit_only": True,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "snapshot": snapshot,
        "medium_feature_probes": probes,
        "summary": {
            "any_medium_feature_gate_hit": any(p["feature_gate_hit"] for p in probes),
            "hit_names": [p["name"] for p in probes if p["feature_gate_hit"]],
            "important_note": "FEATURE_PROBE_ONLY. CoreA/CoreB regeneration and arbitration are not yet connected.",
        },
    }
    out_json = output_dir / "gold_v2_latest_feature_snapshot.json"
    out_csv = output_dir / "gold_v2_latest_feature_snapshot.csv"
    out_probe_csv = output_dir / "gold_v2_latest_medium_feature_probes.csv"
    out_report = output_dir / "GOLD_V2_LATEST_FEATURE_SNAPSHOT_AUDIT_ONLY_REPORT.md"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    pd.DataFrame([snapshot]).to_csv(out_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(probes).to_csv(out_probe_csv, index=False, encoding="utf-8-sig")
    out_report.write_text(build_report(packet), encoding="utf-8")
    print(f"[DONE] output_dir={output_dir}")
    print(f"eval_time={eval_time}")
    print(f"ret96={fmt_value(snapshot.get('ret96'))} range96={fmt_value(snapshot.get('range96'))} trend_eff96={fmt_value(snapshot.get('trend_eff96'))} tr_mean_32={fmt_value(snapshot.get('tr_mean_32'))}")
    print(f"medium_feature_hits={packet['summary']['hit_names']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
