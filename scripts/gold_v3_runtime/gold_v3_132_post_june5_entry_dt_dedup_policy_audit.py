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

STEP = "GOLD_V3_132_POST_JUNE5_ENTRY_DT_DEDUP_POLICY_AUDIT_ONLY"
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


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, first_entry_dt="", last_entry_dt="", long_trades=0, short_trades=0)
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x.get("result_usd"), errors="coerce")
    x = x[x.result_usd.notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, first_entry_dt="", last_entry_dt="", long_trades=0, short_trades=0)
    side = x["side"].astype(str) if "side" in x.columns else pd.Series(["UNKNOWN"] * len(x))
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd),
        sum_result_usd=float(x.result_usd.sum()),
        first_entry_dt=str(x.entry_dt.min()) if "entry_dt" in x.columns and len(x) else "",
        last_entry_dt=str(x.entry_dt.max()) if "entry_dt" in x.columns and len(x) else "",
        long_trades=int((side == "LONG").sum()),
        short_trades=int((side == "SHORT").sum()),
    )


def sort_for_representative(g: pd.DataFrame) -> pd.DataFrame:
    x = g.copy()
    for c in ["feature_score", "score", "ledger_score", "result_usd"]:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")
        else:
            x[c] = 0.0
    return x.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False])


def dedup_policy(g: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    reps = []
    worst = []
    conflict_times = 0
    multirow_times = 0
    max_rows_same_time = 0
    for entry_dt, h in g.groupby("entry_dt"):
        max_rows_same_time = max(max_rows_same_time, len(h))
        if len(h) > 1:
            multirow_times += 1
        if "side" in h.columns and h.side.astype(str).nunique() > 1:
            conflict_times += 1
        reps.append(sort_for_representative(h).iloc[0].to_dict())
        w = h.copy()
        w["result_usd"] = pd.to_numeric(w["result_usd"], errors="coerce")
        worst.append(w.sort_values("result_usd", ascending=True).iloc[0].to_dict())
    rep_df = pd.DataFrame(reps)
    worst_df = pd.DataFrame(worst)
    diag = dict(
        raw_rows=int(len(g)),
        unique_entry_times=int(g.entry_dt.nunique()),
        multirow_entry_times=int(multirow_times),
        side_conflict_entry_times=int(conflict_times),
        max_rows_same_entry_dt=int(max_rows_same_time),
        duplicate_ratio=float((len(g) - g.entry_dt.nunique()) / len(g)) if len(g) else 0.0,
    )
    return rep_df, worst_df, diag


def rank_score(row) -> float:
    p = float(row.rep_profit_factor)
    if math.isinf(p):
        p = 10.0
    wp = float(row.worst_profit_factor)
    if math.isinf(wp):
        wp = 10.0
    return (
        float(row.rep_win_rate) * 10000.0
        + min(p, 10.0) * 700.0
        + min(wp, 10.0) * 300.0
        + int(row.rep_trades) * 15.0
        + float(row.rep_sum_result_usd) * 0.2
        + float(row.worst_sum_result_usd) * 0.1
        - float(row.duplicate_ratio) * 1000.0
        - int(row.side_conflict_entry_times) * 500.0
    )


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start-after", default="2026-06-05 15:15:00")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-dedup-trades", type=int, default=3)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "132"
    out.mkdir(parents=True, exist_ok=True)

    start_after = pd.Timestamp(args.start_after)
    end = pd.Timestamp(args.end_exclusive)

    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    bal_path = root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv"
    led = load_csv(led_path)
    bal = load_csv(bal_path)
    best_key = current_best_policy(bal)

    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not best_key:
        blockers.append({"blocker_id": "missing_current_best_policy_key", "path": str(bal_path)})

    ranked = pd.DataFrame()
    top_rep_rows = pd.DataFrame()
    top_worst_rows = pd.DataFrame()
    current = pd.DataFrame()

    if not blockers:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led["result_usd"], errors="coerce")
        after = led[(led.entry_dt > start_after) & (led.entry_dt < end) & led.result_usd.notna()].copy()
        save(after, out / "gold_v3_132_post_june5_raw_rows.csv")

        rows = []
        rep_all = []
        worst_all = []
        for key, g in after.groupby(after.policy_key.astype(str)):
            rep, worst, diag = dedup_policy(g)
            rep["policy_key"] = key
            worst["policy_key"] = key
            rep_all.append(rep)
            worst_all.append(worst)
            rm = metrics(rep)
            wm = metrics(worst)
            rec = dict(policy_key=key, is_current_best=(key == best_key), **diag)
            rec.update({f"rep_{k}": v for k, v in rm.items()})
            rec.update({f"worst_{k}": v for k, v in wm.items()})
            rec["rep_pf_ge_1_5"] = bool(rm["profit_factor"] >= 1.5)
            rec["worst_pf_ge_1_0"] = bool(wm["profit_factor"] >= 1.0)
            rec["no_side_conflict"] = bool(diag["side_conflict_entry_times"] == 0)
            rec["qualified"] = bool(rm["trades"] >= args.min_dedup_trades and wm["trades"] >= args.min_dedup_trades and wm["profit_factor"] >= 1.0 and diag["side_conflict_entry_times"] == 0)
            rows.append(rec)
        ranked = pd.DataFrame(rows)
        if not ranked.empty:
            ranked["rank_score"] = ranked.apply(rank_score, axis=1)
            ranked = ranked.sort_values(["qualified", "rank_score", "worst_profit_factor", "rep_profit_factor", "rep_trades"], ascending=[False, False, False, False, False]).reset_index(drop=True)
        save(ranked, out / "gold_v3_132_entry_dt_dedup_policy_ranking.csv")
        save(ranked.head(25), out / "gold_v3_132_top25_entry_dt_dedup_policy_ranking.csv")

        reps = pd.concat(rep_all, ignore_index=True) if rep_all else pd.DataFrame()
        worsts = pd.concat(worst_all, ignore_index=True) if worst_all else pd.DataFrame()
        if not ranked.empty:
            top_key = str(ranked[ranked.qualified].iloc[0].policy_key) if bool(ranked.qualified.any()) else str(ranked.iloc[0].policy_key)
            top_rep_rows = reps[reps.policy_key.astype(str) == top_key].copy() if not reps.empty else pd.DataFrame()
            top_worst_rows = worsts[worsts.policy_key.astype(str) == top_key].copy() if not worsts.empty else pd.DataFrame()
            current = ranked[ranked.policy_key.astype(str) == best_key].copy()
        save(top_rep_rows, out / "gold_v3_132_top_policy_rep_entry_dt_rows.csv")
        save(top_worst_rows, out / "gold_v3_132_top_policy_worst_entry_dt_rows.csv")

    qualified = ranked[ranked.qualified].copy() if not ranked.empty and "qualified" in ranked.columns else pd.DataFrame()
    top = qualified.head(1).copy() if not qualified.empty else pd.DataFrame()
    top_key = str(top.iloc[0].policy_key) if not top.empty else ""
    current_rows = int(current.iloc[0].rep_trades) if not current.empty else 0

    if blockers:
        status = BLOCKED
        decision = "ENTRY_DT_DEDUP_POLICY_AUDIT_BLOCKED_INPUT_MISSING"
    elif top.empty:
        status = READY
        decision = "NO_QUALIFIED_ENTRY_DT_DEDUP_POLICY_AFTER_JUNE5"
    elif top_key != best_key and current_rows == 0:
        status = READY
        decision = "DEDUP_ALTERNATIVE_POLICY_FOUND_CURRENT_BEST_STALE"
    elif top_key != best_key:
        status = READY
        decision = "DEDUP_ALTERNATIVE_POLICY_FOUND_CURRENT_BEST_WEAKER"
    else:
        status = READY
        decision = "CURRENT_BEST_REMAINS_TOP_AFTER_DEDUP"

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
        "current_best_dedup_trades_after": current_rows,
        "policy_count_after": int(ranked.policy_key.nunique()) if not ranked.empty and "policy_key" in ranked.columns else 0,
        "qualified_policy_count_after": int(ranked.qualified.sum()) if not ranked.empty and "qualified" in ranked.columns else 0,
        "top_policy_key_after_dedup": top_key,
        "top_policy_rep_trades": int(top.iloc[0].rep_trades) if not top.empty else 0,
        "top_policy_rep_win_rate": float(top.iloc[0].rep_win_rate) if not top.empty else 0.0,
        "top_policy_rep_profit_factor": float(top.iloc[0].rep_profit_factor) if not top.empty else 0.0,
        "top_policy_rep_sum_result_usd": float(top.iloc[0].rep_sum_result_usd) if not top.empty else 0.0,
        "top_policy_worst_win_rate": float(top.iloc[0].worst_win_rate) if not top.empty else 0.0,
        "top_policy_worst_profit_factor": float(top.iloc[0].worst_profit_factor) if not top.empty else 0.0,
        "top_policy_worst_sum_result_usd": float(top.iloc[0].worst_sum_result_usd) if not top.empty else 0.0,
        "top_policy_multirow_entry_times": int(top.iloc[0].multirow_entry_times) if not top.empty else 0,
        "top_policy_side_conflict_entry_times": int(top.iloc[0].side_conflict_entry_times) if not top.empty else 0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_132_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_132_decision.csv")

    lines = ["GOLD V3 132 PASTE_ME_POST_JUNE5_ENTRY_DT_DEDUP_POLICY_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "CURRENT_BEST_IN_DEDUP_RANKING", current.to_string(index=False) if not current.empty else "CURRENT_BEST_HAS_NO_ROWS_AFTER_CUTOFF"]
    lines += ["", "TOP25_DEDUP_POLICY_RANKING", ranked.head(25).to_string(index=False) if not ranked.empty else "NO_POLICY_ROWS"]
    lines += ["", "TOP_POLICY_REP_ENTRY_DT_ROWS", top_rep_rows.to_string(index=False) if not top_rep_rows.empty else "NO_TOP_REP_ROWS"]
    lines += ["", "TOP_POLICY_WORST_ENTRY_DT_ROWS", top_worst_rows.to_string(index=False) if not top_worst_rows.empty else "NO_TOP_WORST_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "top_policy_key_after_dedup": top_key, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
