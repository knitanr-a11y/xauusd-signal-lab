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

STEP = "GOLD_V3_137_HIGH_VOL_ROUTE_DAILY_COUNT_GUARD_AUDIT_ONLY"
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


def pf_from_daily(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def summarize_daily(d: pd.DataFrame, config: str, min_chal_day_trades: int) -> dict:
    x = d.copy()
    x["date"] = pd.to_datetime(x["date"], errors="coerce")
    x = x[x.date.notna()].copy()
    x["month"] = x.date.dt.to_period("M").astype(str)
    for c in ["rep_trades", "worst_trades", "rep_sum_result_usd", "worst_sum_result_usd", "challenger_dedup_trades", "high_vol_days"]:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0)
    x["chosen_route_guarded"] = x["chosen_route"].astype(str)
    mask_drop = (x.chosen_route_guarded == "CHALLENGER") & (pd.to_numeric(x.get("challenger_dedup_trades", 0), errors="coerce").fillna(0) < min_chal_day_trades)
    x.loc[mask_drop, "chosen_route_guarded"] = "NO_ROUTE"
    for c in ["rep_trades", "rep_wins", "rep_losses", "rep_sum_result_usd", "worst_trades", "worst_wins", "worst_losses", "worst_sum_result_usd"]:
        if c in x.columns:
            x.loc[mask_drop, c] = 0
    monthly_rows = []
    for m, g in x.groupby("month"):
        monthly_rows.append(dict(
            route_config=config,
            min_challenger_day_trades=min_chal_day_trades,
            month=m,
            route_days=int((g.chosen_route_guarded != "NO_ROUTE").sum()),
            champion_days=int((g.chosen_route_guarded == "CHAMPION").sum()),
            challenger_days=int((g.chosen_route_guarded == "CHALLENGER").sum()),
            rep_trades=int(pd.to_numeric(g.get("rep_trades", 0), errors="coerce").fillna(0).sum()),
            worst_trades=int(pd.to_numeric(g.get("worst_trades", 0), errors="coerce").fillna(0).sum()),
            rep_sum_result_usd=float(pd.to_numeric(g.get("rep_sum_result_usd", 0), errors="coerce").fillna(0).sum()),
            worst_sum_result_usd=float(pd.to_numeric(g.get("worst_sum_result_usd", 0), errors="coerce").fillna(0).sum()),
        ))
    mon = pd.DataFrame(monthly_rows)
    rep_vals = pd.to_numeric(x.get("rep_sum_result_usd", 0), errors="coerce").fillna(0)
    worst_vals = pd.to_numeric(x.get("worst_sum_result_usd", 0), errors="coerce").fillna(0)
    mode_name = str(x["mode"].iloc[0]) if "mode" in x.columns and len(x) else ""
    vol_col = str(x["vol_col"].iloc[0]) if "vol_col" in x.columns and len(x) else ""
    q = float(pd.to_numeric(x["q"].iloc[0], errors="coerce")) if "q" in x.columns and len(x) else 0.0
    june = mon[mon.month == "2026-06"].copy() if not mon.empty else pd.DataFrame()
    return dict(
        route_config=config,
        mode_name=mode_name,
        vol_col=vol_col,
        q=q,
        min_challenger_day_trades=min_chal_day_trades,
        route_days=int((x.chosen_route_guarded != "NO_ROUTE").sum()),
        champion_days=int((x.chosen_route_guarded == "CHAMPION").sum()),
        challenger_days=int((x.chosen_route_guarded == "CHALLENGER").sum()),
        dropped_challenger_days=int(mask_drop.sum()),
        high_vol_days=int(pd.to_numeric(x.get("is_high_vol", False), errors="coerce").fillna(0).astype(bool).sum()) if "is_high_vol" in x.columns else 0,
        rep_trades=int(pd.to_numeric(x.get("rep_trades", 0), errors="coerce").fillna(0).sum()),
        worst_trades=int(pd.to_numeric(x.get("worst_trades", 0), errors="coerce").fillna(0).sum()),
        rep_sum_result_usd=float(rep_vals.sum()),
        worst_sum_result_usd=float(worst_vals.sum()),
        rep_daily_pnl_pf=pf_from_daily(rep_vals),
        worst_daily_pnl_pf=pf_from_daily(worst_vals),
        negative_months_worst=int((mon.worst_sum_result_usd < 0).sum()) if not mon.empty else 0,
        june_challenger_days=int(june.iloc[0].challenger_days) if not june.empty else 0,
        june_worst_sum_result_usd=float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
        june_rep_sum_result_usd=float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
    ), mon, x


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--min-challenger-day-trades", default="1,3,5,8")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "137"
    out.mkdir(parents=True, exist_ok=True)

    daily_path = root / "136" / "gold_v3_136_all_daily_route_configs.csv"
    s136 = read_json(root / "136" / "gold_v3_136_summary.json")
    daily = load_csv(daily_path)
    blockers = []
    if daily.empty:
        blockers.append({"blocker_id": "missing_136_all_daily_route_configs", "path": str(daily_path)})
    if "route_config" not in daily.columns:
        blockers.append({"blocker_id": "136_daily_missing_route_config"})

    min_vals = []
    for part in str(args.min_challenger_day_trades).split(","):
        part = part.strip()
        if part:
            min_vals.append(int(part))

    summaries = []
    monthly_all = []
    guarded_daily_by_key = {}
    if not blockers:
        for config, g in daily.groupby(daily.route_config.astype(str)):
            for mv in min_vals:
                s, mon, gd = summarize_daily(g, config, mv)
                summaries.append(s)
                monthly_all.append(mon)
                guarded_daily_by_key[f"{config}|MIN_DAY_TRADES_{mv}"] = gd
    summary_df = pd.DataFrame(summaries)
    monthly_df = pd.concat(monthly_all, ignore_index=True) if monthly_all else pd.DataFrame()
    if not summary_df.empty:
        summary_df["safe_fill_mode"] = summary_df["mode_name"].astype(str).isin(["HIGHVOL_FILL_ONLY", "STALL3_HIGHVOL_FILL"])
        summary_df["june_positive"] = summary_df["june_worst_sum_result_usd"] > 0
        summary_df["score"] = summary_df["worst_sum_result_usd"] + summary_df["worst_daily_pnl_pf"] * 100.0 - summary_df["negative_months_worst"] * 300.0 + summary_df["june_worst_sum_result_usd"] * 0.25 - summary_df["dropped_challenger_days"] * 2.0
        summary_df = summary_df.sort_values(["safe_fill_mode", "negative_months_worst", "worst_sum_result_usd", "worst_daily_pnl_pf", "june_positive"], ascending=[False, True, False, False, False]).reset_index(drop=True)
    save(summary_df, out / "gold_v3_137_high_vol_route_daily_count_guard_summary.csv")
    save(monthly_df, out / "gold_v3_137_high_vol_route_daily_count_guard_monthly.csv")

    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    selected_key = ""
    selected_daily = pd.DataFrame()
    selected_monthly = pd.DataFrame()
    if not selected.empty:
        selected_key = f"{selected.iloc[0].route_config}|MIN_DAY_TRADES_{int(selected.iloc[0].min_challenger_day_trades)}"
        selected_daily = guarded_daily_by_key.get(selected_key, pd.DataFrame())
        selected_monthly = monthly_df[(monthly_df.route_config.astype(str) == str(selected.iloc[0].route_config)) & (monthly_df.min_challenger_day_trades.astype(int) == int(selected.iloc[0].min_challenger_day_trades))].copy()
    save(selected_daily, out / "gold_v3_137_selected_guarded_daily_rows.csv")
    save(selected_monthly, out / "gold_v3_137_selected_guarded_monthly_rows.csv")

    status = BLOCKED if blockers else READY
    if blockers:
        decision = "DAILY_COUNT_GUARD_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "DAILY_COUNT_GUARD_READY_NO_CONFIG"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "DAILY_COUNT_GUARD_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "DAILY_COUNT_GUARD_READY_NO_NEGATIVE_WORST_MONTHS"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "source_stage136_decision": s136.get("decision", ""),
        "selected_guarded_route_key": selected_key,
        "selected_route_config": str(selected.iloc[0].route_config) if not selected.empty else "",
        "selected_mode_name": str(selected.iloc[0].mode_name) if not selected.empty else "",
        "selected_vol_col": str(selected.iloc[0].vol_col) if not selected.empty else "",
        "selected_q": float(selected.iloc[0].q) if not selected.empty else 0.0,
        "selected_min_challenger_day_trades": int(selected.iloc[0].min_challenger_day_trades) if not selected.empty else 0,
        "selected_challenger_days": int(selected.iloc[0].challenger_days) if not selected.empty else 0,
        "selected_dropped_challenger_days": int(selected.iloc[0].dropped_challenger_days) if not selected.empty else 0,
        "selected_worst_sum_result_usd": float(selected.iloc[0].worst_sum_result_usd) if not selected.empty else 0.0,
        "selected_worst_daily_pnl_pf": float(selected.iloc[0].worst_daily_pnl_pf) if not selected.empty else 0.0,
        "selected_negative_months_worst": int(selected.iloc[0].negative_months_worst) if not selected.empty else 0,
        "selected_june_challenger_days": int(selected.iloc[0].june_challenger_days) if not selected.empty else 0,
        "selected_june_worst_sum_result_usd": float(selected.iloc[0].june_worst_sum_result_usd) if not selected.empty else 0.0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_137_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_137_decision.csv")

    lines = ["GOLD V3 137 PASTE_ME_HIGH_VOL_ROUTE_DAILY_COUNT_GUARD_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP30_DAILY_COUNT_GUARD_CONFIGS", summary_df.head(30).to_string(index=False) if not summary_df.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_GUARDED_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY_ROWS"]
    lines += ["", "SELECTED_GUARDED_DAILY_TAIL", selected_daily.tail(40).to_string(index=False) if not selected_daily.empty else "NO_SELECTED_DAILY_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_guarded_route_key": selected_key, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
