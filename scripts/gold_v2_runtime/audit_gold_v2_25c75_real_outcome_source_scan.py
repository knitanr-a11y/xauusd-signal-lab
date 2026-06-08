#!/usr/bin/env python
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C75_REAL_OUTCOME_SOURCE_SCAN"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
HANDOFF_DIR = "gold_v2_25c74_a002_final_handoff"
OUT_DIR = "gold_v2_25c75_real_outcome_source_scan"
TIME_COLS = ["entry_time", "signal_time", "time", "datetime", "open_time", "entry_datetime"]
OUTCOME_COLS = ["profit", "pnl", "net_profit", "net_pnl", "outcome", "result", "trade_result", "win_loss", "is_win", "label"]


def root() -> Path:
    r = Path(__file__).resolve().parents[2]
    return r.parents[1] / "FX_OUTPUTS"


def read_csv(p: Path, usecols=None) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(p, encoding=enc, keep_default_na=False, usecols=usecols)
        except Exception:
            pass
    return pd.read_csv(p, usecols=usecols)


def header(p: Path) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with open(p, encoding=enc, newline="") as f:
                return next(csv.reader(f))
        except Exception:
            pass
    return []


def first(cols: list[str], names: list[str]) -> str:
    m = {c.lower().strip(): c for c in cols}
    for n in names:
        if n in m:
            return m[n]
    return ""


def write_csv(p: Path, df: pd.DataFrame) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def main() -> int:
    base = root()
    out = base / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    ledger = read_csv(base / LEDGER_DIR / "05_25c66_dry_run_event_ledger.csv")
    with open(base / HANDOFF_DIR / "02_25c74_summary.json", encoding="utf-8-sig") as f:
        h74 = json.load(f)
    times = set(ledger["entry_time"].astype(str))
    rows = []
    for p in base.rglob("*.csv"):
        if OUT_DIR in p.parts:
            continue
        cols = header(p)
        if not cols:
            continue
        tcol = first(cols, TIME_COLS)
        ocols = [c for c in cols if c.lower().strip() in OUTCOME_COLS]
        if not tcol or not ocols:
            continue
        try:
            df = read_csv(p, usecols=[tcol] + ocols)
            vals = set(df[tcol].astype(str))
            match_count = len(vals.intersection(times))
            exact = times.issubset(vals)
            var_cols = []
            for c in ocols:
                if df[c].astype(str).nunique(dropna=True) > 1:
                    var_cols.append(c)
            category = "FULL_REAL_OUTCOME_SOURCE" if exact and var_cols else ("FULL_FIXED_OUTCOME_SOURCE" if exact else "PARTIAL_OUTCOME_SOURCE")
            rows.append({
                "relative_path": str(p.relative_to(base)),
                "time_column": tcol,
                "outcome_columns": ";".join(ocols),
                "varying_outcome_columns": ";".join(var_cols),
                "rows": len(df),
                "match_count": match_count,
                "match_ratio": round(match_count / 772, 6),
                "exact_coverage": exact,
                "category": category,
            })
        except Exception as e:
            rows.append({"relative_path": str(p.relative_to(base)), "time_column": tcol, "outcome_columns": ";".join(ocols), "varying_outcome_columns": "", "rows": 0, "match_count": 0, "match_ratio": 0, "exact_coverage": False, "category": "READ_ERROR", "error": str(e)[:120]})
    cand = pd.DataFrame(rows)
    if cand.empty:
        cand = pd.DataFrame(columns=["relative_path", "time_column", "outcome_columns", "varying_outcome_columns", "rows", "match_count", "match_ratio", "exact_coverage", "category"])
    cand = cand.sort_values(["category", "match_count"], ascending=[True, False]).reset_index(drop=True)
    full_real = cand[cand["category"].eq("FULL_REAL_OUTCOME_SOURCE")].copy()
    partial = cand[cand["category"].eq("PARTIAL_OUTCOME_SOURCE")].copy()
    category_counts = cand.groupby("category", dropna=False).agg(files=("relative_path", "size"), max_match=("match_count", "max")).reset_index() if not cand.empty else pd.DataFrame()
    requirement = pd.DataFrame([
        {"requirement": "772 entry_time coverage", "status": "PASS" if len(full_real) else "MISSING"},
        {"requirement": "profit/pnl/outcome/result-like column", "status": "PASS" if len(cand) else "MISSING"},
        {"requirement": "non-uniform outcome values", "status": "PASS" if len(full_real) else "MISSING"},
        {"requirement": "no recomputation", "status": "PASS"},
    ])
    next_step = "25C76_REAL_OUTCOME_MAPPING" if len(full_real) else "PROVIDE_REAL_OUTCOME_SOURCE_FILE"
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": "REAL_OUTCOME_SOURCE_FOUND" if len(full_real) else "REAL_OUTCOME_SOURCE_NOT_FOUND",
        "input_25c74_status": h74.get("status"),
        "ledger_events": 772,
        "candidate_files": int(len(cand)),
        "full_real_sources": int(len(full_real)),
        "partial_sources": int(len(partial)),
        "best_real_source": str(full_real.iloc[0]["relative_path"]) if len(full_real) else "",
        "best_partial_source": str(partial.sort_values("match_count", ascending=False).iloc[0]["relative_path"]) if len(partial) else "",
        "ready_for_real_outcome_mapping": bool(len(full_real)),
        "next_recommended_step": next_step,
        "condition_changed": False,
        "source_recovery_executed": False,
        "total_stop_rows": 0,
    }
    write_csv(out / "03_25c75_candidate_files.csv", cand)
    write_csv(out / "04_25c75_full_real_outcome_sources.csv", full_real)
    write_csv(out / "05_25c75_partial_sources.csv", partial.head(100))
    write_csv(out / "06_25c75_category_counts.csv", category_counts)
    write_csv(out / "07_25c75_required_source_matrix.csv", requirement)
    with open(out / "02_25c75_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    (out / "01_25c75_REAL_OUTCOME_SOURCE_SCAN.md").write_text("# GOLD V2 25C75 real outcome source scan\n\n" + json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
