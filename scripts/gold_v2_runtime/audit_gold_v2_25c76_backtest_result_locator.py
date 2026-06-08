#!/usr/bin/env python
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C76_BACKTEST_RESULT_LOCATOR"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c76_backtest_result_locator"
TEXT_EXTS = {".md", ".py", ".txt", ".json", ".bat", ".csv"}
KEYWORDS = ["backtest", "trade", "trades", "ledger", "profit", "pnl", "outcome", "result", "win_loss", "closed", "rr125", "top_ledgers"]
TIME_COLS = ["entry_time", "signal_time", "time", "datetime", "open_time", "entry_datetime"]
OUTCOME_COLS = ["profit", "pnl", "net_profit", "net_pnl", "outcome", "result", "trade_result", "win_loss", "is_win", "label", "rr"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1]


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


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


def text_sniff(path: Path, max_hits: int = 8) -> list[dict]:
    rows = []
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with open(path, encoding=enc, errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    low = line.lower()
                    hit = [k for k in KEYWORDS if k in low]
                    if hit:
                        rows.append({"path": str(path), "line": i, "keywords": ";".join(hit), "text": line.strip()[:240]})
                        if len(rows) >= max_hits:
                            return rows
            return rows
        except Exception:
            continue
    return rows


def main() -> int:
    repo = repo_root()
    files = files_root()
    fx = fx_outputs()
    out = fx / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    ledger = read_csv(fx / LEDGER_DIR / "05_25c66_dry_run_event_ledger.csv")
    times = set(ledger["entry_time"].astype(str))

    text_hits = []
    for base in [repo / "docs", repo / "scripts"]:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS:
                name_hit = [k for k in KEYWORDS if k in p.name.lower()]
                if name_hit:
                    text_hits.append({"path": str(p), "line": 0, "keywords": ";".join(name_hit), "text": "FILENAME_MATCH"})
                text_hits.extend(text_sniff(p, 5))
    text_df = pd.DataFrame(text_hits)

    csv_rows = []
    for p in fx.rglob("*.csv"):
        if OUT_DIR in p.parts:
            continue
        name_low = p.name.lower()
        name_score = sum(1 for k in KEYWORDS if k in name_low)
        cols = header(p)
        if not cols:
            continue
        tcol = first(cols, TIME_COLS)
        ocols = [c for c in cols if c.lower().strip() in OUTCOME_COLS]
        if not (name_score or tcol or ocols):
            continue
        match_count = 0
        exact = False
        var_cols = []
        row_count = 0
        try:
            use = [tcol] + ocols if tcol else ocols
            df = read_csv(p, usecols=use if use else None)
            row_count = len(df)
            if tcol:
                vals = set(df[tcol].astype(str))
                match_count = len(vals.intersection(times))
                exact = times.issubset(vals)
            for c in ocols:
                if df[c].astype(str).nunique(dropna=True) > 1:
                    var_cols.append(c)
        except Exception:
            pass
        path_str = str(p.relative_to(fx))
        csv_rows.append({
            "relative_path": path_str,
            "name_score": name_score,
            "rows": row_count,
            "time_column": tcol,
            "outcome_columns": ";".join(ocols),
            "varying_outcome_columns": ";".join(var_cols),
            "entry_time_match_count": match_count,
            "entry_time_match_ratio": round(match_count / 772, 6),
            "exact_772_coverage": exact,
            "looks_like_backtest_result": bool(("backtest" in path_str.lower() or "trade" in path_str.lower() or "result" in path_str.lower()) and ocols),
        })
    csv_df = pd.DataFrame(csv_rows)
    if csv_df.empty:
        csv_df = pd.DataFrame(columns=["relative_path", "name_score", "rows", "time_column", "outcome_columns", "varying_outcome_columns", "entry_time_match_count", "entry_time_match_ratio", "exact_772_coverage", "looks_like_backtest_result"])
    csv_df = csv_df.sort_values(["exact_772_coverage", "entry_time_match_count", "name_score"], ascending=[False, False, False]).reset_index(drop=True)
    full = csv_df[(csv_df["exact_772_coverage"] == True) & (csv_df["varying_outcome_columns"].astype(str) != "")].copy()
    partial = csv_df[(csv_df["entry_time_match_count"] > 0) & ~(csv_df.index.isin(full.index))].copy()
    likely_backtest = csv_df[csv_df["looks_like_backtest_result"] == True].copy()

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "ledger_events": 772,
        "doc_script_hits": int(len(text_df)),
        "csv_candidates": int(len(csv_df)),
        "full_varying_sources": int(len(full)),
        "partial_sources": int(len(partial)),
        "likely_backtest_result_files": int(len(likely_backtest)),
        "best_full_source": str(full.iloc[0]["relative_path"]) if len(full) else "",
        "best_partial_source": str(partial.iloc[0]["relative_path"]) if len(partial) else "",
        "next_recommended_step": "25C77_BIND_BACKTEST_RESULT_SOURCE" if len(full) else "REVIEW_LOCATOR_OUTPUT_OR_PROVIDE_BACKTEST_FILE",
    }
    write_csv(out / "03_25c76_doc_script_keyword_hits.csv", text_df)
    write_csv(out / "04_25c76_csv_candidate_inventory.csv", csv_df)
    write_csv(out / "05_25c76_full_varying_sources.csv", full)
    write_csv(out / "06_25c76_partial_sources.csv", partial.head(200))
    write_csv(out / "07_25c76_likely_backtest_result_files.csv", likely_backtest.head(200))
    with open(out / "02_25c76_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    (out / "01_25c76_BACKTEST_RESULT_LOCATOR.md").write_text("# GOLD V2 25C76 backtest result locator\n\n" + json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
