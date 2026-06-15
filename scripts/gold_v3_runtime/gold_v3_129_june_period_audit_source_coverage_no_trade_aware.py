#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_129_JUNE_PERIOD_AUDIT_SOURCE_COVERAGE_NO_TRADE_AWARE_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"

SOURCES = [
    ("107GB", "107gbc", "gold_v3_107gb_top_candidate_trade_ledger.csv"),
    ("107GD", "107gdc", "gold_v3_107gd_diversified_portfolio_ledger.csv"),
    ("107GL", "107glc", "gold_v3_107gl_top_vector_trade_ledger.csv"),
    ("107GN", "107gnc", "gold_v3_107gn_top_candidate_trade_ledger.csv"),
    ("107GO", "107goc", "gold_v3_107go_portfolio_ledger.csv"),
]


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def detect_sep(p: Path) -> str:
    try:
        s = p.read_text(encoding="utf-8-sig", errors="ignore")[:4096]
        return ";" if s.count(";") > s.count(",") else ","
    except Exception:
        return ","


def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, sep=detect_sep(p), encoding="utf-8-sig", low_memory=False)


def max_dt(df: pd.DataFrame, preferred: str = "entry_dt") -> pd.Timestamp:
    if df.empty:
        return pd.NaT
    col = preferred if preferred in df.columns else ""
    if not col:
        for c in ["entry_dt", "time", "datetime", "date", "timestamp", "dt", "oos_max_entry_dt"]:
            if c in df.columns:
                col = c
                break
    if not col:
        return pd.NaT
    return pd.to_datetime(df[col], errors="coerce").max()


def min_dt(df: pd.DataFrame, preferred: str = "entry_dt") -> pd.Timestamp:
    if df.empty:
        return pd.NaT
    col = preferred if preferred in df.columns else ""
    if not col:
        for c in ["entry_dt", "time", "datetime", "date", "timestamp", "dt", "oos_min_entry_dt"]:
            if c in df.columns:
                col = c
                break
    if not col:
        return pd.NaT
    return pd.to_datetime(df[col], errors="coerce").min()


def pf(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "result_usd" not in df.columns:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, min_entry_dt="", max_entry_dt="", unique_trade_days=0)
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x.entry_dt.notna() & x.result_usd.notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, min_entry_dt="", max_entry_dt="", unique_trade_days=0)
    mon = x.groupby(x.entry_dt.dt.to_period("M").astype(str))["result_usd"].sum()
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd),
        sum_result_usd=float(x.result_usd.sum()),
        negative_month_count=int((mon < 0).sum()),
        min_entry_dt=str(x.entry_dt.min()),
        max_entry_dt=str(x.entry_dt.max()),
        unique_trade_days=int(x.entry_dt.dt.date.nunique()),
    )


def bools(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def select_best_policy(bal: pd.DataFrame) -> str:
    if bal.empty or "policy_key" not in bal.columns:
        return ""
    b = bal.copy()
    for c in ["all_regime_pass_65", "all_regime_pass_60"]:
        b[c] = bools(b[c]) if c in b.columns else False
    if "balanced_score" not in b.columns:
        b["balanced_score"] = 0.0
    b["balanced_score"] = pd.to_numeric(b["balanced_score"], errors="coerce").fillna(0.0)
    b = b.sort_values(["all_regime_pass_65", "all_regime_pass_60", "balanced_score"], ascending=[False, False, False])
    return str(b.iloc[0].policy_key)


def coverage_row(label: str, path: Path, df: pd.DataFrame) -> dict:
    mn = min_dt(df)
    mx = max_dt(df)
    return dict(label=label, path=str(path), exists=path.exists(), rows=int(len(df)), min_entry_dt=str(mn) if pd.notna(mn) else "", max_entry_dt=str(mx) if pd.notna(mx) else "")


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2026-06-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--require-min-source-max-entry-dt", default="2026-06-15")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "129"
    out.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end_exclusive)
    required = pd.Timestamp(args.require_min_source_max_entry_dt) if args.require_min_source_max_entry_dt else pd.NaT

    source_rows = []
    source_maxes = []
    for label, subdir, fn in SOURCES:
        p = root / subdir / fn
        df = load_csv(p)
        source_rows.append(coverage_row(label, p, df))
        mx = max_dt(df)
        if pd.notna(mx):
            source_maxes.append(mx)
    source_cov = pd.DataFrame(source_rows)
    save(source_cov, out / "gold_v3_129_source_candidate_coverage.csv")
    source_max = max(source_maxes) if source_maxes else pd.NaT

    ohlc_rows = []
    for fn in ["goldsharp_m15.csv", "gold#_m15.csv", "goldsharp_m5.csv", "gold#_m5.csv"]:
        p = mt5 / fn
        df = load_csv(p)
        ohlc_rows.append(coverage_row(fn, p, df))
    ohlc_cov = pd.DataFrame(ohlc_rows)
    save(ohlc_cov, out / "gold_v3_129_ohlc_coverage.csv")
    ohlc_maxes = [pd.to_datetime(x, errors="coerce") for x in ohlc_cov.max_entry_dt.tolist() if str(x)]
    ohlc_max = max([x for x in ohlc_maxes if pd.notna(x)], default=pd.NaT)

    bal_path = root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv"
    all_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    best_rows_path = root / "107k2c" / "gold_v3_107k2_best_policy_regime_rows.csv"
    bal = load_csv(bal_path)
    all_led = load_csv(all_path)
    best_rows = load_csv(best_rows_path)
    best_key = select_best_policy(bal)

    blockers = []
    if pd.isna(ohlc_max) or ohlc_max < required:
        blockers.append({"blocker_id": "ohlc_does_not_reach_required_target", "observed_max_dt": str(ohlc_max) if pd.notna(ohlc_max) else "", "required": str(required)})
    if pd.isna(source_max) or source_max < required:
        blockers.append({"blocker_id": "source_candidate_ledgers_do_not_reach_required_target", "observed_max_dt": str(source_max) if pd.notna(source_max) else "", "required": str(required)})
    if all_led.empty or not best_key:
        blockers.append({"blocker_id": "missing_107k2_best_policy_or_ledger", "best_policy_key": best_key, "all_ledger_rows": int(len(all_led))})

    selected = pd.DataFrame()
    period = pd.DataFrame()
    all_led_max = max_dt(all_led)
    selected_max = pd.NaT
    if not all_led.empty and best_key:
        all_led["entry_dt"] = pd.to_datetime(all_led["entry_dt"], errors="coerce")
        selected = all_led[all_led.policy_key.astype(str) == best_key].copy() if "policy_key" in all_led.columns else pd.DataFrame()
        selected_max = max_dt(selected)
        period = selected[(selected.entry_dt >= start) & (selected.entry_dt < end)].copy() if not selected.empty else pd.DataFrame()
        save(selected, out / "gold_v3_129_selected_best_policy_ledger_from_107k2.csv")
        save(period, out / "gold_v3_129_selected_best_policy_period_rows.csv")

    m = metrics(period)
    direction = pd.DataFrame()
    if not period.empty and "side" in period.columns:
        rows = []
        for side, g in period.groupby(period.side.astype(str)):
            rows.append(dict(side=side, **metrics(g)))
        direction = pd.DataFrame(rows)
    save(direction, out / "gold_v3_129_direction_split.csv")

    no_trade_after_last = bool(not blockers and m["trades"] == 0 and pd.notna(source_max) and source_max >= required)
    status = READY if not blockers else BLOCKED
    if status == READY and no_trade_after_last:
        decision = "PERIOD_AUDIT_READY_CONFIRMED_NO_TRADE"
    elif status == READY:
        decision = "PERIOD_AUDIT_READY_WITH_PERIOD_TRADES"
    else:
        decision = "PERIOD_AUDIT_BLOCKED_SOURCE_OR_POLICY_COVERAGE"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "period_start": str(start),
        "period_end_exclusive": str(end),
        "required_min_source_max_entry_dt": str(required),
        "coverage_basis": "OHLC max and upstream source candidate ledger max. 107K2 selected/filter ledger max is NOT used as coverage because no selected rows may be a valid NO_TRADE outcome.",
        "observed_ohlc_max_dt": str(ohlc_max) if pd.notna(ohlc_max) else "",
        "observed_source_candidate_max_entry_dt": str(source_max) if pd.notna(source_max) else "",
        "observed_107k2_all_regime_ledgers_max_entry_dt": str(all_led_max) if pd.notna(all_led_max) else "",
        "selected_best_policy_key": best_key,
        "selected_best_policy_max_entry_dt": str(selected_max) if pd.notna(selected_max) else "",
        "period_confirmed_no_trade": bool(no_trade_after_last),
        **{f"period_{k}": v for k, v in m.items()},
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "period_restore_auto_adopted": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    write_json(out / "gold_v3_129_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_129_decision.csv")

    lines = ["GOLD V3 129 PASTE_ME_JUNE_PERIOD_AUDIT_SOURCE_COVERAGE_NO_TRADE_AWARE"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "SOURCE_CANDIDATE_COVERAGE", source_cov.to_string(index=False)]
    lines += ["", "OHLC_COVERAGE", ohlc_cov.to_string(index=False)]
    lines += ["", "BEST_POLICY_REGIME_ROWS", best_rows.to_string(index=False) if not best_rows.empty else "NO_BEST_POLICY_REGIME_ROWS"]
    lines += ["", "DIRECTION_SPLIT", direction.to_string(index=False) if not direction.empty else "NO_DIRECTION_ROWS"]
    lines += ["", "PERIOD_ROWS_HEAD", period.head(50).to_string(index=False) if not period.empty else "NO_PERIOD_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
