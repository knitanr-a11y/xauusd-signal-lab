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

STEP = "GOLD_V3_131_POST_JUNE5_POLICY_RANKING_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def bools(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def current_best_policy(bal: pd.DataFrame) -> str:
    if bal.empty or "policy_key" not in bal.columns:
        return ""
    b = bal.copy()
    for c in ["all_regime_pass_65", "all_regime_pass_60"]:
        b[c] = bools(b[c]) if c in b.columns else False
    b["balanced_score"] = pd.to_numeric(b.get("balanced_score", 0.0), errors="coerce").fillna(0.0)
    b = b.sort_values(["all_regime_pass_65", "all_regime_pass_60", "balanced_score"], ascending=[False, False, False])
    return str(b.iloc[0].policy_key)


def pf(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def calc_metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(rows=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, unique_entry_times=0, first_entry_dt="", last_entry_dt="", long_rows=0, short_rows=0)
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x.get("result_usd"), errors="coerce")
    y = x[x.result_usd.notna()].copy()
    side = x["side"].astype(str) if "side" in x.columns else pd.Series(["UNKNOWN"] * len(x))
    return dict(
        rows=int(len(x)),
        wins=int((y.result_usd > 0).sum()) if not y.empty else 0,
        losses=int((y.result_usd < 0).sum()) if not y.empty else 0,
        win_rate=float((y.result_usd > 0).mean()) if not y.empty else 0.0,
        profit_factor=pf(y.result_usd) if not y.empty else 0.0,
        sum_result_usd=float(y.result_usd.sum()) if not y.empty else 0.0,
        unique_entry_times=int(x.entry_dt.nunique()) if "entry_dt" in x.columns else 0,
        first_entry_dt=str(x.entry_dt.min()) if "entry_dt" in x.columns and len(x) else "",
        last_entry_dt=str(x.entry_dt.max()) if "entry_dt" in x.columns and len(x) else "",
        long_rows=int((side == "LONG").sum()),
        short_rows=int((side == "SHORT").sum()),
    )


def rank_score(row) -> float:
    p = float(row.profit_factor)
    if math.isinf(p):
        p = 10.0
    return float(row.win_rate) * 12000.0 + min(p, 10.0) * 900.0 + int(row.rows) * 0.25 + int(row.unique_entry_times) * 5.0 + float(row.sum_result_usd) * 0.1


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start-after", default="2026-06-05 15:15:00")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-rows", type=int, default=10)
    ap.add_argument("--min-unique-entry-times", type=int, default=3)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "131"
    out.mkdir(parents=True, exist_ok=True)

    start_after = pd.Timestamp(args.start_after)
    end = pd.Timestamp(args.end_exclusive)

    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    bal_path = root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv"
    best_rows_path = root / "107k2c" / "gold_v3_107k2_best_policy_regime_rows.csv"

    led = load_csv(led_path)
    bal = load_csv(bal_path)
    best_rows = load_csv(best_rows_path)
    best_key = current_best_policy(bal)

    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not best_key:
        blockers.append({"blocker_id": "missing_current_best_policy_key", "path": str(bal_path)})

    after = pd.DataFrame()
    ranked = pd.DataFrame()
    side_rank = pd.DataFrame()
    source_rank = pd.DataFrame()

    if not blockers:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        after = led[(led.entry_dt > start_after) & (led.entry_dt < end)].copy()
        save(after, out / "gold_v3_131_post_june5_all_policy_rows.csv")

        rows = []
        for key, g in after.groupby(after.policy_key.astype(str)):
            rec = dict(policy_key=key, is_current_best=(key == best_key), **calc_metrics(g))
            rec["regime_split_count"] = int(g.regime_split.astype(str).nunique()) if "regime_split" in g.columns else 0
            rec["source_name_count"] = int(g.source_name.astype(str).nunique()) if "source_name" in g.columns else 0
            rec["top_source_name"] = str(g.source_name.astype(str).value_counts().index[0]) if "source_name" in g.columns and len(g) else ""
            rows.append(rec)
        ranked = pd.DataFrame(rows)
        if not ranked.empty:
            ranked["rank_score"] = ranked.apply(rank_score, axis=1)
            ranked["qualified"] = (ranked.rows >= args.min_rows) & (ranked.unique_entry_times >= args.min_unique_entry_times)
            ranked = ranked.sort_values(["qualified", "rank_score", "profit_factor", "win_rate", "rows"], ascending=[False, False, False, False, False]).reset_index(drop=True)
        save(ranked, out / "gold_v3_131_post_june5_policy_ranking.csv")
        save(ranked.head(25), out / "gold_v3_131_post_june5_top25_policy_ranking.csv")

        side_rows = []
        if "side" in after.columns:
            for (key, side), g in after.groupby([after.policy_key.astype(str), after.side.astype(str)]):
                side_rows.append(dict(policy_key=key, side=side, is_current_best=(key == best_key), **calc_metrics(g)))
        side_rank = pd.DataFrame(side_rows)
        if not side_rank.empty:
            side_rank["rank_score"] = side_rank.apply(rank_score, axis=1)
            side_rank = side_rank.sort_values(["rank_score", "profit_factor", "win_rate", "rows"], ascending=[False, False, False, False]).reset_index(drop=True)
        save(side_rank, out / "gold_v3_131_post_june5_policy_side_ranking.csv")

        src_rows = []
        if "source_name" in after.columns:
            for src, g in after.groupby(after.source_name.astype(str)):
                src_rows.append(dict(source_name=src, **calc_metrics(g)))
        source_rank = pd.DataFrame(src_rows)
        if not source_rank.empty:
            source_rank["rank_score"] = source_rank.apply(rank_score, axis=1)
            source_rank = source_rank.sort_values(["rank_score", "profit_factor", "win_rate", "rows"], ascending=[False, False, False, False]).reset_index(drop=True)
        save(source_rank, out / "gold_v3_131_post_june5_source_ranking.csv")

    current = ranked[ranked.policy_key.astype(str) == best_key].copy() if not ranked.empty and "policy_key" in ranked.columns else pd.DataFrame()
    qualified = ranked[ranked.qualified].copy() if not ranked.empty and "qualified" in ranked.columns else pd.DataFrame()
    top = qualified.head(1).copy() if not qualified.empty else pd.DataFrame()
    top_key = str(top.iloc[0].policy_key) if not top.empty else ""

    current_rows = int(current.iloc[0].rows) if not current.empty else 0
    if blockers:
        status = BLOCKED
        decision = "POLICY_RANKING_BLOCKED_INPUT_MISSING"
    elif top_key and top_key != best_key and current_rows == 0:
        status = READY
        decision = "ALTERNATIVE_POLICY_FOUND_CURRENT_BEST_STALE_AFTER_JUNE5"
    elif top_key and top_key != best_key:
        status = READY
        decision = "ALTERNATIVE_POLICY_FOUND_CURRENT_BEST_WEAKER_AFTER_JUNE5"
    elif top_key == best_key:
        status = READY
        decision = "CURRENT_BEST_REMAINS_TOP_AFTER_JUNE5"
    else:
        status = READY
        decision = "NO_QUALIFIED_POLICY_AFTER_JUNE5"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "start_after": str(start_after),
        "end_exclusive": str(end),
        "current_best_policy_key": best_key,
        "current_best_after_rows": current_rows,
        "all_policy_after_rows": int(len(after)),
        "policy_count_after": int(ranked.policy_key.nunique()) if not ranked.empty and "policy_key" in ranked.columns else 0,
        "qualified_policy_count_after": int(ranked.qualified.sum()) if not ranked.empty and "qualified" in ranked.columns else 0,
        "top_policy_key_after": top_key,
        "top_policy_after_rows": int(top.iloc[0].rows) if not top.empty else 0,
        "top_policy_win_rate_after": float(top.iloc[0].win_rate) if not top.empty else 0.0,
        "top_policy_profit_factor_after": float(top.iloc[0].profit_factor) if not top.empty else 0.0,
        "top_policy_sum_result_usd_after": float(top.iloc[0].sum_result_usd) if not top.empty else 0.0,
        "top_policy_first_entry_dt_after": str(top.iloc[0].first_entry_dt) if not top.empty else "",
        "top_policy_last_entry_dt_after": str(top.iloc[0].last_entry_dt) if not top.empty else "",
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_131_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_131_decision.csv")

    lines = ["GOLD V3 131 PASTE_ME_POST_JUNE5_POLICY_RANKING_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "CURRENT_BEST_IN_POST_JUNE5_RANKING", current.to_string(index=False) if not current.empty else "CURRENT_BEST_HAS_NO_ROWS_AFTER_CUTOFF"]
    lines += ["", "TOP25_POLICY_RANKING", ranked.head(25).to_string(index=False) if not ranked.empty else "NO_POLICY_ROWS"]
    lines += ["", "TOP25_POLICY_SIDE_RANKING", side_rank.head(25).to_string(index=False) if not side_rank.empty else "NO_SIDE_ROWS"]
    lines += ["", "SOURCE_RANKING", source_rank.to_string(index=False) if not source_rank.empty else "NO_SOURCE_ROWS"]
    lines += ["", "BEST_POLICY_REGIME_ROWS", best_rows.to_string(index=False) if not best_rows.empty else "NO_BEST_POLICY_REGIME_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "top_policy_key_after": top_key, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
