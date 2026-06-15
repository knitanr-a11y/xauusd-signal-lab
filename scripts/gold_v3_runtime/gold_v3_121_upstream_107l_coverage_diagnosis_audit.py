#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_121_UPSTREAM_107L_COVERAGE_DIAGNOSIS_AUDIT_ONLY"
READY = STEP + "_READY"

TARGET = pd.Timestamp("2026-06-15")

OHLC_NAMES = [
    "gold#_m15.csv", "goldsharp_m15.csv", "candles_history_M15.csv",
    "gold#_m5.csv", "goldsharp_m5.csv", "candles_history_M5.csv",
    "gold#_h1.csv", "goldsharp_h1.csv", "candles_history_H1.csv",
]

LEDGER_PATTERNS = [
    "107*/*.csv", "109*/*.csv", "117*/*.csv",
]


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def detect_sep(path: Path) -> str:
    s = path.read_text(encoding="utf-8-sig", errors="ignore")[:4096]
    return ";" if s.count(";") >= s.count(",") else ","


def find_time_col(cols) -> str:
    names = ["entry_dt", "time", "datetime", "date", "timestamp", "dt"]
    low = {str(c).strip().lower(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    for c in cols:
        cl = str(c).strip().lower()
        if any(n in cl for n in names):
            return c
    return ""


def csv_time_coverage(path: Path) -> dict:
    row = {"path": str(path), "exists": path.exists(), "rows": 0, "time_col": "", "min_dt": "", "max_dt": "", "error": ""}
    if not path.exists():
        return row | {"error": "missing"}
    try:
        sep = detect_sep(path)
        df = pd.read_csv(path, sep=sep, encoding="utf-8-sig", low_memory=False)
        row["rows"] = int(len(df))
        col = find_time_col(df.columns)
        row["time_col"] = col
        if not col:
            row["error"] = "missing_time_column"
            return row
        t = pd.to_datetime(df[col], errors="coerce").dropna()
        if len(t):
            row["min_dt"] = str(t.min())
            row["max_dt"] = str(t.max())
        else:
            row["error"] = "all_time_parse_failed"
    except Exception as e:
        row["error"] = str(e)
    return row


def scan_scripts(repo: Path) -> pd.DataFrame:
    runtime = repo / "scripts" / "gold_v3_runtime"
    rows = []
    needles = ["107lc", "gold_v3_107l_rehydrated_best_policy_ledger", "107l", "rehydrated_best_policy"]
    if not runtime.exists():
        return pd.DataFrame([{"path": str(runtime), "match_count": 0, "matches": "runtime_missing"}])
    for p in sorted(runtime.glob("*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = []
        for n in needles:
            if n in text:
                hits.append(n)
        if hits:
            lines = []
            for i, line in enumerate(text.splitlines(), 1):
                if any(n in line for n in needles):
                    lines.append(f"L{i}:{line.strip()[:180]}")
            rows.append({"path": str(p), "match_count": len(lines), "matches": " || ".join(lines[:20])})
    return pd.DataFrame(rows)


def scan_ledgers(root: Path) -> pd.DataFrame:
    rows = []
    seen = set()
    for pat in LEDGER_PATTERNS:
        for p in root.glob(pat):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            if p.suffix.lower() != ".csv":
                continue
            name = p.name.lower()
            if not any(x in name for x in ["ledger", "trade", "selected", "family", "portfolio", "107l", "107q", "109"]):
                continue
            cov = csv_time_coverage(p)
            cov["relative"] = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
            rows.append(cov)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["max_dt_parsed"] = pd.to_datetime(df["max_dt"], errors="coerce")
    return df.sort_values(["max_dt_parsed", "relative"], ascending=[False, True]).drop(columns=["max_dt_parsed"])


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--target", default="2026-06-15")
    args = ap.parse_args()

    target = pd.Timestamp(args.target)
    repo = Path(__file__).resolve().parents[2]
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "121"
    out.mkdir(parents=True, exist_ok=True)

    ohlc_rows = [csv_time_coverage(mt5 / name) | {"name": name} for name in OHLC_NAMES]
    ohlc = pd.DataFrame(ohlc_rows)
    save(ohlc, out / "gold_v3_121_ohlc_coverage.csv")

    ledgers = scan_ledgers(root)
    save(ledgers, out / "gold_v3_121_ledger_coverage.csv")

    writers = scan_scripts(repo)
    save(writers, out / "gold_v3_121_107l_writer_discovery.csv")

    p107l = root / "107lc" / "gold_v3_107l_rehydrated_best_policy_ledger.csv"
    cov107l = csv_time_coverage(p107l)
    max107l = pd.to_datetime(cov107l.get("max_dt", ""), errors="coerce")
    ohlc_max = pd.to_datetime(ohlc["max_dt"], errors="coerce").max() if not ohlc.empty else pd.NaT

    if pd.notna(max107l) and max107l >= target:
        decision = "107L_REACHES_TARGET_RERUN_STAGE120"
        next_action = "Rerun Stage120 and review FX_OUTPUTS/gold_v3/119/paste_me.txt"
    elif pd.notna(ohlc_max) and ohlc_max >= target:
        decision = "OHLC_REACHES_TARGET_BUT_107L_STALE_REGENERATE_107L_CHAIN_REQUIRED"
        next_action = "Use writer discovery to rerun the script that creates 107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv, then rerun Stage120"
    else:
        decision = "OHLC_DOES_NOT_REACH_TARGET_UPDATE_MT5_CSV_FIRST"
        next_action = "Update/export MT5 CSV through target date, then regenerate 107L chain and rerun Stage120"

    summary = {
        "step": STEP,
        "status": READY,
        "ready": True,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "target": str(target),
        "observed_107l_max_dt": cov107l.get("max_dt", ""),
        "observed_ohlc_max_dt": str(ohlc_max) if pd.notna(ohlc_max) else "",
        "writer_candidate_count": int(len(writers)),
        "ledger_files_scanned": int(len(ledgers)) if not ledgers.empty else 0,
        "next_action": next_action,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_json(out / "gold_v3_121_summary.json", summary | {"cov107l": cov107l})
    save(pd.DataFrame([summary]), out / "gold_v3_121_decision.csv")

    lines = ["GOLD V3 121 PASTE_ME_UPSTREAM_107L_COVERAGE_DIAGNOSIS"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "107L_COVERAGE", json.dumps(cov107l, ensure_ascii=False, indent=2)]
    lines += ["", "TOP_LEDGER_COVERAGE", ledgers.head(30).to_string(index=False) if not ledgers.empty else "NO_LEDGER_ROWS"]
    lines += ["", "WRITER_DISCOVERY", writers.to_string(index=False) if not writers.empty else "NO_WRITER_CANDIDATES_FOUND"]
    lines += ["", "OUTPUTS", str(out / "gold_v3_121_summary.json"), str(out / "gold_v3_121_ohlc_coverage.csv"), str(out / "gold_v3_121_ledger_coverage.csv"), str(out / "gold_v3_121_107l_writer_discovery.csv")]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": READY, "ready": True, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
