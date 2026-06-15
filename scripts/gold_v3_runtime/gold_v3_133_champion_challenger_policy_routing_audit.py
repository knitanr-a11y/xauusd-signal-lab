#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_133_CHAMPION_CHALLENGER_POLICY_ROUTING_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)


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


def fnum(x, default=0.0) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return default


def inum(x, default=0) -> int:
    try:
        return int(float(x))
    except Exception:
        return default


def route_score(row) -> float:
    return (
        fnum(row.worst_profit_factor) * 900.0
        + fnum(row.rep_profit_factor) * 500.0
        + fnum(row.worst_win_rate) * 4000.0
        + fnum(row.rep_win_rate) * 2500.0
        + inum(row.rep_trades) * 25.0
        + fnum(row.worst_sum_result_usd) * 0.25
        + fnum(row.rep_sum_result_usd) * 0.15
        - fnum(row.duplicate_ratio) * 500.0
        - inum(row.side_conflict_entry_times) * 1000.0
    )


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--min-dedup-trades", type=int, default=10)
    ap.add_argument("--min-worst-pf", type=float, default=1.2)
    ap.add_argument("--min-rep-pf", type=float, default=1.5)
    ap.add_argument("--max-duplicate-ratio", type=float, default=0.75)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "133"
    out.mkdir(parents=True, exist_ok=True)

    r132_path = root / "132" / "gold_v3_132_entry_dt_dedup_policy_ranking.csv"
    bal_path = root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv"
    best_rows_path = root / "107k2c" / "gold_v3_107k2_best_policy_regime_rows.csv"

    r132 = load_csv(r132_path)
    bal = load_csv(bal_path)
    best_rows = load_csv(best_rows_path)
    champion = current_best_policy(bal)

    blockers = []
    if r132.empty:
        blockers.append({"blocker_id": "missing_132_dedup_ranking", "path": str(r132_path)})
    if not champion:
        blockers.append({"blocker_id": "missing_champion_policy", "path": str(bal_path)})

    candidates = pd.DataFrame()
    champion_row = pd.DataFrame()
    challenger = pd.DataFrame()
    if not blockers:
        x = r132.copy()
        for c in ["rep_trades", "worst_trades", "rep_profit_factor", "worst_profit_factor", "rep_win_rate", "worst_win_rate", "rep_sum_result_usd", "worst_sum_result_usd", "duplicate_ratio", "side_conflict_entry_times"]:
            if c in x.columns:
                x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0)
        if "policy_key" not in x.columns:
            blockers.append({"blocker_id": "132_ranking_missing_policy_key"})
        else:
            champion_row = x[x.policy_key.astype(str) == champion].copy()
            x["is_champion"] = x.policy_key.astype(str) == champion
            x["stable_challenger_candidate"] = (
                (~x.is_champion)
                & (x.rep_trades >= args.min_dedup_trades)
                & (x.worst_trades >= args.min_dedup_trades)
                & (x.worst_profit_factor >= args.min_worst_pf)
                & (x.rep_profit_factor >= args.min_rep_pf)
                & (x.duplicate_ratio <= args.max_duplicate_ratio)
                & (x.side_conflict_entry_times == 0)
            )
            x["route_score"] = x.apply(route_score, axis=1)
            candidates = x.sort_values(["stable_challenger_candidate", "route_score", "worst_profit_factor", "rep_profit_factor", "rep_trades"], ascending=[False, False, False, False, False]).reset_index(drop=True)
            challenger = candidates[candidates.stable_challenger_candidate].head(1).copy()

    champion_after_trades = 0 if champion_row.empty else inum(champion_row.iloc[0].rep_trades)
    champion_stale = champion_after_trades == 0
    challenger_key = "" if challenger.empty else str(challenger.iloc[0].policy_key)

    if blockers:
        status = BLOCKED
        decision = "ROUTING_AUDIT_BLOCKED_INPUT_MISSING"
    elif champion_stale and challenger_key:
        status = READY
        decision = "KEEP_CHAMPION_AND_ADD_STABLE_CHALLENGER_ROUTE_AUDIT_ONLY"
    elif champion_stale and not challenger_key:
        status = READY
        decision = "KEEP_CHAMPION_NO_STABLE_CHALLENGER_FOUND"
    elif not champion_stale and challenger_key:
        status = READY
        decision = "KEEP_CHAMPION_CHALLENGER_AVAILABLE_BUT_NOT_NEEDED"
    else:
        status = READY
        decision = "KEEP_CHAMPION_ONLY"

    bal_subset = pd.DataFrame()
    if not bal.empty and "policy_key" in bal.columns:
        keys = [k for k in [champion, challenger_key] if k]
        bal_subset = bal[bal.policy_key.astype(str).isin(keys)].copy()
    save(candidates, out / "gold_v3_133_champion_challenger_candidates.csv")
    save(candidates.head(25), out / "gold_v3_133_top25_routing_candidates.csv")
    save(champion_row, out / "gold_v3_133_champion_row.csv")
    save(challenger, out / "gold_v3_133_selected_challenger_row.csv")
    save(bal_subset, out / "gold_v3_133_champion_challenger_historical_policy_rows.csv")

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "champion_policy_key": champion,
        "champion_after_dedup_trades": champion_after_trades,
        "champion_stale_after_june5": bool(champion_stale),
        "min_dedup_trades": args.min_dedup_trades,
        "min_worst_pf": args.min_worst_pf,
        "min_rep_pf": args.min_rep_pf,
        "max_duplicate_ratio": args.max_duplicate_ratio,
        "stable_challenger_count": int(candidates.stable_challenger_candidate.sum()) if not candidates.empty and "stable_challenger_candidate" in candidates.columns else 0,
        "selected_challenger_policy_key": challenger_key,
        "selected_challenger_rep_trades": int(challenger.iloc[0].rep_trades) if not challenger.empty else 0,
        "selected_challenger_rep_win_rate": float(challenger.iloc[0].rep_win_rate) if not challenger.empty else 0.0,
        "selected_challenger_rep_profit_factor": float(challenger.iloc[0].rep_profit_factor) if not challenger.empty else 0.0,
        "selected_challenger_worst_win_rate": float(challenger.iloc[0].worst_win_rate) if not challenger.empty else 0.0,
        "selected_challenger_worst_profit_factor": float(challenger.iloc[0].worst_profit_factor) if not challenger.empty else 0.0,
        "selected_challenger_duplicate_ratio": float(challenger.iloc[0].duplicate_ratio) if not challenger.empty else 0.0,
        "selected_challenger_side_conflict_entry_times": int(challenger.iloc[0].side_conflict_entry_times) if not challenger.empty else 0,
        "routing_rule_draft": "Keep champion. Only expose challenger when champion has zero recent dedup rows and challenger passes stable audit thresholds.",
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_133_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_133_decision.csv")

    lines = ["GOLD V3 133 PASTE_ME_CHAMPION_CHALLENGER_POLICY_ROUTING_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "CHAMPION_ROW", champion_row.to_string(index=False) if not champion_row.empty else "CHAMPION_HAS_NO_POST_JUNE5_DEDUP_ROWS"]
    lines += ["", "SELECTED_CHALLENGER_ROW", challenger.to_string(index=False) if not challenger.empty else "NO_STABLE_CHALLENGER_SELECTED"]
    lines += ["", "TOP25_ROUTING_CANDIDATES", candidates.head(25).to_string(index=False) if not candidates.empty else "NO_CANDIDATES"]
    lines += ["", "HISTORICAL_POLICY_ROWS", bal_subset.to_string(index=False) if not bal_subset.empty else "NO_HISTORICAL_ROWS"]
    lines += ["", "CURRENT_BEST_REGIME_ROWS", best_rows.to_string(index=False) if not best_rows.empty else "NO_CURRENT_BEST_REGIME_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_challenger_policy_key": challenger_key, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
