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

STEP = "GOLD_V3_140_CHAMPION_RISK_DAY_GUARD_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)


def read_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pf(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def zero_route_rows(x: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    y = x.copy()
    y["chosen_route_guarded"] = y["chosen_route"].astype(str)
    y.loc[mask, "chosen_route_guarded"] = "NO_ROUTE"
    for c in [
        "rep_trades", "rep_wins", "rep_losses", "rep_win_rate", "rep_profit_factor", "rep_sum_result_usd",
        "worst_trades", "worst_wins", "worst_losses", "worst_win_rate", "worst_profit_factor", "worst_sum_result_usd",
    ]:
        if c in y.columns:
            y.loc[mask, c] = 0
    return y


def summarize(daily: pd.DataFrame, guard_name: str, guard_desc: str, mask: pd.Series) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    x = zero_route_rows(daily, mask)
    x["date"] = pd.to_datetime(x["date"], errors="coerce")
    x = x[x.date.notna()].copy()
    x["month"] = x.date.dt.to_period("M").astype(str)
    for c in ["rep_sum_result_usd", "worst_sum_result_usd", "rep_trades", "worst_trades"]:
        x[c] = pd.to_numeric(x.get(c, 0), errors="coerce").fillna(0)
    monthly_rows = []
    for m, g in x.groupby("month"):
        monthly_rows.append(dict(
            guard_name=guard_name,
            month=m,
            route_days=int((g.chosen_route_guarded != "NO_ROUTE").sum()),
            champion_days=int((g.chosen_route_guarded == "CHAMPION").sum()),
            challenger_days=int((g.chosen_route_guarded == "CHALLENGER").sum()),
            blocked_champion_days=int(((g.chosen_route.astype(str) == "CHAMPION") & (g.chosen_route_guarded == "NO_ROUTE")).sum()),
            rep_trades=int(g.rep_trades.sum()),
            worst_trades=int(g.worst_trades.sum()),
            rep_sum_result_usd=float(g.rep_sum_result_usd.sum()),
            worst_sum_result_usd=float(g.worst_sum_result_usd.sum()),
        ))
    monthly = pd.DataFrame(monthly_rows)
    rep_vals = x.rep_sum_result_usd
    worst_vals = x.worst_sum_result_usd
    june = monthly[monthly.month == "2026-06"].copy() if not monthly.empty else pd.DataFrame()
    result = dict(
        guard_name=guard_name,
        guard_desc=guard_desc,
        route_days=int((x.chosen_route_guarded != "NO_ROUTE").sum()),
        champion_days=int((x.chosen_route_guarded == "CHAMPION").sum()),
        challenger_days=int((x.chosen_route_guarded == "CHALLENGER").sum()),
        blocked_champion_days=int(((x.chosen_route.astype(str) == "CHAMPION") & (x.chosen_route_guarded == "NO_ROUTE")).sum()),
        rep_trades=int(x.rep_trades.sum()),
        worst_trades=int(x.worst_trades.sum()),
        rep_sum_result_usd=float(rep_vals.sum()),
        worst_sum_result_usd=float(worst_vals.sum()),
        rep_daily_pnl_pf=pf(rep_vals),
        worst_daily_pnl_pf=pf(worst_vals),
        negative_months_worst=int((monthly.worst_sum_result_usd < 0).sum()) if not monthly.empty else 0,
        june_worst_sum_result_usd=float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
        june_rep_sum_result_usd=float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
    )
    return result, monthly, x


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "140"
    out.mkdir(parents=True, exist_ok=True)

    s138a = read_json(root / "138a" / "gold_v3_138a_summary.json")
    s139 = read_json(root / "139" / "gold_v3_139_summary.json")
    daily_path = root / "138a" / "gold_v3_138a_selected_daily.csv"
    daily = load_csv(daily_path)
    blockers = []
    if daily.empty:
        blockers.append({"blocker_id": "missing_138a_selected_daily", "path": str(daily_path)})
    required = {"chosen_route", "champion_dedup_trades", "challenger_dedup_trades", "is_high_vol", "date", "rep_sum_result_usd", "worst_sum_result_usd"}
    if not daily.empty and not required.issubset(set(daily.columns)):
        blockers.append({"blocker_id": "selected_daily_missing_required_columns", "missing": sorted(required - set(daily.columns))})

    summary_df = pd.DataFrame()
    selected_monthly = pd.DataFrame()
    selected_daily = pd.DataFrame()

    if not blockers:
        x = daily.copy()
        x["date"] = pd.to_datetime(x["date"], errors="coerce")
        x = x[x.date.notna()].copy()
        x["is_high_vol"] = x["is_high_vol"].astype(str).str.lower().isin(["true", "1"])
        for c in ["champion_dedup_trades", "challenger_dedup_trades", "rep_sum_result_usd", "worst_sum_result_usd", "rep_trades", "worst_trades"]:
            x[c] = pd.to_numeric(x.get(c, 0), errors="coerce").fillna(0)
        champ = x.chosen_route.astype(str) == "CHAMPION"
        guards = []
        guards.append(("BASELINE_NO_GUARD", "No champion risk guard", pd.Series([False] * len(x), index=x.index)))
        for n in [3, 5, 8, 10, 12, 15]:
            guards.append((f"BLOCK_CHAMPION_DEDUP_GE_{n}", f"Block champion days when champion_dedup_trades >= {n}", champ & (x.champion_dedup_trades >= n)))
            guards.append((f"BLOCK_CHAMPION_HIGHVOL_DEDUP_GE_{n}", f"Block champion high-vol days when champion_dedup_trades >= {n}", champ & x.is_high_vol & (x.champion_dedup_trades >= n)))
            guards.append((f"BLOCK_CHAMPION_LOWVOL_DEDUP_GE_{n}", f"Block champion non-high-vol days when champion_dedup_trades >= {n}", champ & (~x.is_high_vol) & (x.champion_dedup_trades >= n)))
        for n in [5, 8, 10, 15, 20]:
            guards.append((f"BLOCK_CHAMPION_CHALLENGER_AVAILABLE_GE_{n}", f"Block champion days when challenger_dedup_trades >= {n}", champ & (x.challenger_dedup_trades >= n)))
            guards.append((f"BLOCK_CHAMPION_HIGHVOL_CHALLENGER_AVAILABLE_GE_{n}", f"Block champion high-vol days when challenger_dedup_trades >= {n}", champ & x.is_high_vol & (x.challenger_dedup_trades >= n)))
        guards.append(("BLOCK_ALL_CHAMPION_HIGHVOL", "Block all champion high-vol days", champ & x.is_high_vol))
        guards.append(("BLOCK_ALL_CHAMPION_LOWVOL", "Block all champion non-high-vol days", champ & (~x.is_high_vol)))

        rows = []
        monthly_all = []
        guarded_daily_cache = {}
        for name, desc, mask in guards:
            row, mon, gd = summarize(x, name, desc, mask)
            rows.append(row)
            monthly_all.append(mon)
            guarded_daily_cache[name] = gd
        summary_df = pd.DataFrame(rows)
        if not summary_df.empty:
            # Do not reward over-blocking too much: prefer fewer negative months, then worst total, then fewer blocked champion days.
            summary_df["score"] = summary_df.worst_sum_result_usd + summary_df.worst_daily_pnl_pf * 100 - summary_df.negative_months_worst * 400 - summary_df.blocked_champion_days * 5 + summary_df.june_worst_sum_result_usd * 0.2
            summary_df = summary_df.sort_values(["negative_months_worst", "worst_sum_result_usd", "worst_daily_pnl_pf", "blocked_champion_days"], ascending=[True, False, False, True]).reset_index(drop=True)
        save(summary_df, out / "gold_v3_140_champion_risk_guard_summary.csv")
        save(pd.concat(monthly_all, ignore_index=True) if monthly_all else pd.DataFrame(), out / "gold_v3_140_champion_risk_guard_monthly_all.csv")
        if not summary_df.empty:
            selected_name = str(summary_df.iloc[0].guard_name)
            selected_daily = guarded_daily_cache.get(selected_name, pd.DataFrame())
            selected_monthly = pd.concat(monthly_all, ignore_index=True)
            selected_monthly = selected_monthly[selected_monthly.guard_name.astype(str) == selected_name].copy()
        save(selected_daily, out / "gold_v3_140_selected_guarded_daily.csv")
        save(selected_monthly, out / "gold_v3_140_selected_guarded_monthly.csv")

    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "CHAMPION_RISK_GUARD_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "CHAMPION_RISK_GUARD_READY_NO_CONFIG"
    elif str(selected.iloc[0].guard_name) == "BASELINE_NO_GUARD":
        decision = "CHAMPION_RISK_GUARD_NO_IMPROVING_GUARD_FOUND"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "CHAMPION_RISK_GUARD_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "CHAMPION_RISK_GUARD_READY_NO_NEGATIVE_WORST_MONTHS"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "source_138a_decision": s138a.get("decision", ""),
        "source_138a_selected_route_config": s138a.get("selected_route_config", ""),
        "source_139_decision": s139.get("decision", ""),
        "selected_guard_name": str(selected.iloc[0].guard_name) if not selected.empty else "",
        "selected_guard_desc": str(selected.iloc[0].guard_desc) if not selected.empty else "",
        "selected_blocked_champion_days": int(selected.iloc[0].blocked_champion_days) if not selected.empty else 0,
        "selected_worst_sum_result_usd": float(selected.iloc[0].worst_sum_result_usd) if not selected.empty else 0.0,
        "selected_worst_daily_pnl_pf": float(selected.iloc[0].worst_daily_pnl_pf) if not selected.empty else 0.0,
        "selected_negative_months_worst": int(selected.iloc[0].negative_months_worst) if not selected.empty else 0,
        "selected_june_worst_sum_result_usd": float(selected.iloc[0].june_worst_sum_result_usd) if not selected.empty else 0.0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_140_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_140_decision.csv")

    lines = ["GOLD V3 140 PASTE_ME_CHAMPION_RISK_DAY_GUARD_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP30_CHAMPION_RISK_GUARDS", summary_df.head(30).to_string(index=False) if not summary_df.empty else "NO_GUARD_ROWS"]
    lines += ["", "SELECTED_GUARDED_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "SELECTED_GUARDED_DAILY_TAIL", selected_daily.tail(40).to_string(index=False) if not selected_daily.empty else "NO_SELECTED_DAILY"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_guard_name": summary["selected_guard_name"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
