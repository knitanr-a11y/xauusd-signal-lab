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

STEP = "GOLD_V3_130_JUNE_FUNNEL_FAILURE_DIAGNOSTIC_AUDIT_ONLY"
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


def norm_time(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if "entry_dt" in x.columns:
        x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    return x[x.get("entry_dt", pd.Series(dtype="datetime64[ns]")).notna()].copy() if "entry_dt" in x.columns else pd.DataFrame()


def period_slice(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    x = norm_time(df)
    if x.empty:
        return x
    return x[(x.entry_dt >= start) & (x.entry_dt < end)].copy()


def after_slice(df: pd.DataFrame, cutoff: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    x = norm_time(df)
    if x.empty:
        return x
    return x[(x.entry_dt > cutoff) & (x.entry_dt < end)].copy()


def pf(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "result_usd" not in df.columns:
        return dict(rows=int(len(df)) if df is not None else 0, trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, unique_entry_times=0, min_entry_dt="", max_entry_dt="")
    x = norm_time(df)
    if x.empty:
        return dict(rows=0, trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, unique_entry_times=0, min_entry_dt="", max_entry_dt="")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    y = x[x.result_usd.notna()].copy()
    return dict(
        rows=int(len(x)),
        trades=int(len(y)),
        wins=int((y.result_usd > 0).sum()) if not y.empty else 0,
        losses=int((y.result_usd < 0).sum()) if not y.empty else 0,
        win_rate=float((y.result_usd > 0).mean()) if not y.empty else 0.0,
        profit_factor=pf(y.result_usd) if not y.empty else 0.0,
        sum_result_usd=float(y.result_usd.sum()) if not y.empty else 0.0,
        unique_entry_times=int(x.entry_dt.nunique()),
        min_entry_dt=str(x.entry_dt.min()) if len(x) else "",
        max_entry_dt=str(x.entry_dt.max()) if len(x) else "",
    )


def side_counts(df: pd.DataFrame, label: str) -> pd.DataFrame:
    x = norm_time(df)
    if x.empty:
        return pd.DataFrame()
    side_col = "side" if "side" in x.columns else "portfolio_side" if "portfolio_side" in x.columns else ""
    if not side_col:
        return pd.DataFrame([dict(stage=label, side="UNKNOWN", **metrics(x))])
    rows = []
    for side, g in x.groupby(x[side_col].astype(str)):
        rows.append(dict(stage=label, side=side, **metrics(g)))
    return pd.DataFrame(rows)


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


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2026-06-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--after", default="2026-06-05 15:15:00")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "130"
    out.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end_exclusive)
    after = pd.Timestamp(args.after)

    rows = []
    side_rows = []
    source_period_total = 0
    source_after_total = 0
    source_unique_after = 0
    for label, subdir, fn in SOURCES:
        p = root / subdir / fn
        df = load_csv(p)
        per = period_slice(df, start, end)
        aft = after_slice(df, after, end)
        source_period_total += int(len(per))
        source_after_total += int(len(aft))
        source_unique_after += int(aft.entry_dt.nunique()) if not aft.empty else 0
        rows.append(dict(stage=label, artifact=fn, path=str(p), period="FULL_PERIOD", **metrics(per)))
        rows.append(dict(stage=label, artifact=fn, path=str(p), period="AFTER_LAST_SELECTED", **metrics(aft)))
        s1 = side_counts(per, label + "_FULL_PERIOD")
        s2 = side_counts(aft, label + "_AFTER_LAST_SELECTED")
        if not s1.empty: side_rows.append(s1)
        if not s2.empty: side_rows.append(s2)

    source_funnel = pd.DataFrame(rows)
    save(source_funnel, out / "gold_v3_130_source_period_funnel.csv")
    side_df = pd.concat(side_rows, ignore_index=True) if side_rows else pd.DataFrame()
    save(side_df, out / "gold_v3_130_source_side_funnel.csv")

    bal = load_csv(root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv")
    all_led = load_csv(root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv")
    best_key = select_best_policy(bal)
    k2_period = period_slice(all_led, start, end)
    k2_after = after_slice(all_led, after, end)
    selected = k2_period[k2_period.policy_key.astype(str) == best_key].copy() if not k2_period.empty and "policy_key" in k2_period.columns else pd.DataFrame()
    selected_after = k2_after[k2_after.policy_key.astype(str) == best_key].copy() if not k2_after.empty and "policy_key" in k2_after.columns else pd.DataFrame()

    health_path = root / "107lc" / "gold_v3_107l_best_health_gate_ledger.csv"
    health = load_csv(health_path)
    health_period = period_slice(health, start, end)
    health_after = after_slice(health, after, end)

    funnel_rows = [
        dict(stage="SOURCE_CANDIDATES_ALL", period="FULL_PERIOD", **metrics(pd.concat([period_slice(load_csv(root/sub/fn), start, end) for _, sub, fn in SOURCES], ignore_index=True))),
        dict(stage="SOURCE_CANDIDATES_ALL", period="AFTER_LAST_SELECTED", rows=source_after_total, trades=source_after_total, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, unique_entry_times=source_unique_after, min_entry_dt="", max_entry_dt=""),
        dict(stage="K2_SCORE_FILTERED_ALL_POLICIES", period="FULL_PERIOD", **metrics(k2_period)),
        dict(stage="K2_SCORE_FILTERED_ALL_POLICIES", period="AFTER_LAST_SELECTED", **metrics(k2_after)),
        dict(stage="K2_SELECTED_BEST_POLICY", period="FULL_PERIOD", **metrics(selected)),
        dict(stage="K2_SELECTED_BEST_POLICY", period="AFTER_LAST_SELECTED", **metrics(selected_after)),
        dict(stage="107L_HEALTH_GATE_FINAL", period="FULL_PERIOD", **metrics(health_period)),
        dict(stage="107L_HEALTH_GATE_FINAL", period="AFTER_LAST_SELECTED", **metrics(health_after)),
    ]
    funnel = pd.DataFrame(funnel_rows)
    save(funnel, out / "gold_v3_130_stage_funnel_summary.csv")

    bottleneck = "UNKNOWN"
    if len(selected) == 0 and len(k2_period) > 0:
        bottleneck = "BEST_POLICY_SELECTION_FILTER_REMOVED_PERIOD_ROWS"
    elif len(selected_after) == 0 and len(k2_after) > 0:
        bottleneck = "BEST_POLICY_NO_ROWS_AFTER_2026_06_05_WHILE_OTHER_K2_POLICIES_HAVE_ROWS"
    elif source_after_total > 0 and len(k2_after) == 0:
        bottleneck = "K2_SCORE_FILTER_REMOVED_ALL_AFTER_2026_06_05_SOURCE_CANDIDATES"
    elif len(selected) > 0 and len(health_period) == 0:
        bottleneck = "HEALTH_GATE_FINAL_UNAVAILABLE_OR_ZERO_CONFIRMED"
    else:
        bottleneck = "NO_SINGLE_BOTTLENECK_DETECTED"

    status = READY
    decision = "JUNE_FUNNEL_DIAGNOSTIC_READY"
    summary = {
        "step": STEP,
        "status": status,
        "ready": True,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "period_start": str(start),
        "period_end_exclusive": str(end),
        "after_cutoff": str(after),
        "best_policy_key": best_key,
        "source_candidate_period_rows": int(source_period_total),
        "source_candidate_after_cutoff_rows": int(source_after_total),
        "k2_all_policy_period_rows": int(len(k2_period)),
        "k2_all_policy_after_cutoff_rows": int(len(k2_after)),
        "k2_selected_best_policy_period_rows": int(len(selected)),
        "k2_selected_best_policy_after_cutoff_rows": int(len(selected_after)),
        "final_health_gate_period_rows": int(len(health_period)),
        "final_health_gate_after_cutoff_rows": int(len(health_after)),
        "final_live_confirmed_signal_count": int(len(health_period)),
        "safe_interpretation": "final/live-confirmed count is zero unless 107L health gate ledger exists and has rows; K2 selected rows are audit/proxy, not final live-ready signals",
        "bottleneck": bottleneck,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "review_only": True,
        "blocker_count": 0,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_json(out / "gold_v3_130_summary.json", summary)
    save(pd.DataFrame([summary]), out / "gold_v3_130_decision.csv")

    lines = ["GOLD V3 130 PASTE_ME_JUNE_FUNNEL_FAILURE_DIAGNOSTIC_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "STAGE_FUNNEL_SUMMARY", funnel.to_string(index=False)]
    lines += ["", "SOURCE_PERIOD_FUNNEL", source_funnel.to_string(index=False)]
    lines += ["", "SOURCE_SIDE_FUNNEL", side_df.to_string(index=False) if not side_df.empty else "NO_SIDE_ROWS"]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": True, "decision": decision, "bottleneck": bottleneck, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
