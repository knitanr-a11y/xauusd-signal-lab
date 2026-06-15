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

STEP = "GOLD_V3_138_CHALLENGER_FACTOR_MATRIX_AUDIT_ONLY"
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


def pf(v) -> float:
    a = pd.to_numeric(pd.Series(v), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame, prefix="") -> dict:
    if df is None or df.empty:
        base = dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0)
        return {prefix + k: v for k, v in base.items()}
    x = df.copy(); x["result_usd"] = pd.to_numeric(x.get("result_usd"), errors="coerce")
    x = x[x.result_usd.notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame(), prefix)
    base = dict(trades=int(len(x)), wins=int((x.result_usd > 0).sum()), losses=int((x.result_usd < 0).sum()), win_rate=float((x.result_usd > 0).mean()), profit_factor=pf(x.result_usd), sum_result_usd=float(x.result_usd.sum()))
    return {prefix + k: v for k, v in base.items()}


def dedup(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), dict(raw_rows=0, dedup_trades=0, side_conflicts=0, duplicate_ratio=0.0)
    reps, worsts = [], []
    side_conflicts = 0
    for _, g in df.groupby("entry_dt"):
        if "side" in g.columns and g.side.astype(str).nunique() > 1:
            side_conflicts += 1
        h = g.copy()
        for c in ["feature_score", "score", "ledger_score", "result_usd"]:
            h[c] = pd.to_numeric(h[c], errors="coerce") if c in h.columns else 0.0
        reps.append(h.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False]).iloc[0].to_dict())
        worsts.append(h.sort_values("result_usd", ascending=True).iloc[0].to_dict())
    n = len(df); u = int(df.entry_dt.nunique())
    return pd.DataFrame(reps), pd.DataFrame(worsts), dict(raw_rows=int(n), dedup_trades=u, side_conflicts=int(side_conflicts), duplicate_ratio=float((n-u)/n) if n else 0.0)


def daily_vol_flags(led: pd.DataFrame, vol_col: str, q: float, min_hist: int) -> dict:
    x = led[["entry_date", vol_col]].copy()
    x[vol_col] = pd.to_numeric(x[vol_col], errors="coerce")
    d = x.groupby("entry_date", as_index=False)[vol_col].median().sort_values("entry_date")
    vals, out = [], {}
    for r in d.itertuples(index=False):
        clean = pd.Series(vals).dropna()
        th = float(clean.quantile(q)) if len(clean) >= min_hist else math.nan
        is_hv = bool(pd.notna(r[1]) and pd.notna(th) and float(r[1]) >= th)
        out[r[0]] = is_hv
        vals.append(r[1])
    return out


def row_filter(df: pd.DataFrame, side_filter: str, direction_filter: str, session_filter: str) -> pd.DataFrame:
    x = df.copy()
    if side_filter == "SHORT_ONLY":
        x = x[x.side.astype(str) == "SHORT"]
    elif side_filter == "LONG_ONLY":
        x = x[x.side.astype(str) == "LONG"]
    if direction_filter != "ANY" and not x.empty:
        side = x.side.astype(str)
        h1_up = x.get("h1_up", pd.Series([False] * len(x))).astype(str).str.lower().isin(["true", "1"])
        h4_up = x.get("h4_up", pd.Series([False] * len(x))).astype(str).str.lower().isin(["true", "1"])
        if direction_filter == "SIDE_WITH_H1":
            x = x[((side == "LONG") & h1_up) | ((side == "SHORT") & (~h1_up))]
        elif direction_filter == "SIDE_WITH_H4":
            x = x[((side == "LONG") & h4_up) | ((side == "SHORT") & (~h4_up))]
        elif direction_filter == "SIDE_WITH_H1_H4":
            x = x[((side == "LONG") & h1_up & h4_up) | ((side == "SHORT") & (~h1_up) & (~h4_up))]
    if session_filter != "ANY" and not x.empty and "condition" in x.columns:
        cond = x.condition.astype(str)
        if session_filter == "SESSION_7_15":
            x = x[cond.str.contains("session_7_15", na=False)]
        elif session_filter == "SESSION_16_22":
            x = x[cond.str.contains("session_16_22", na=False)]
        elif session_filter == "NO_SESSION_FILTER_TAG":
            x = x[~cond.str.contains("session_", na=False)]
    return x


def evaluate_config(led: pd.DataFrame, champion_key: str, challenger_key: str, start: pd.Timestamp, end: pd.Timestamp, vol_col: str, vol_q: float, min_hist: int, min_day_trades: int, side_filter: str, direction_filter: str, session_filter: str, mode: str):
    hv_map = daily_vol_flags(led, vol_col, vol_q, min_hist)
    champ = led[led.policy_key.astype(str) == champion_key].copy()
    chal = led[led.policy_key.astype(str) == challenger_key].copy()
    rows, reps, worsts = [], [], []
    for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
        c_raw = champ[champ.entry_date == day].copy()
        h_raw0 = chal[chal.entry_date == day].copy()
        h_raw = row_filter(h_raw0, side_filter, direction_filter, session_filter)
        c_rep, c_worst, _ = dedup(c_raw)
        h_rep, h_worst, h_diag = dedup(h_raw)
        has_champ = len(c_rep) > 0
        hv = bool(hv_map.get(day, False))
        enough = int(len(h_rep)) >= min_day_trades
        if mode == "FILL_ONLY" and (not has_champ) and hv and enough and h_diag["side_conflicts"] == 0:
            chosen = "CHALLENGER"; r_rep, r_worst = h_rep, h_worst
        elif mode == "OVERRIDE" and hv and enough and h_diag["side_conflicts"] == 0:
            chosen = "CHALLENGER"; r_rep, r_worst = h_rep, h_worst
        elif has_champ:
            chosen = "CHAMPION"; r_rep, r_worst = c_rep, c_worst
        else:
            chosen = "NO_ROUTE"; r_rep, r_worst = pd.DataFrame(), pd.DataFrame()
        key = f"{mode}|{vol_col}|Q{vol_q}|MIN{min_day_trades}|{side_filter}|{direction_filter}|{session_filter}"
        if not r_rep.empty:
            z = r_rep.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; z["route_config"] = key; reps.append(z)
        if not r_worst.empty:
            z = r_worst.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; z["route_config"] = key; worsts.append(z)
        rec = dict(route_config=key, mode=mode, vol_col=vol_col, vol_q=vol_q, min_day_trades=min_day_trades, side_filter=side_filter, direction_filter=direction_filter, session_filter=session_filter, date=str(day.date()), chosen_route=chosen, is_high_vol=hv, champion_trades=int(len(c_rep)), challenger_trades=int(len(h_rep)))
        rec.update(metrics(r_rep, "rep_")); rec.update(metrics(r_worst, "worst_")); rows.append(rec)
    daily = pd.DataFrame(rows); rep = pd.concat(reps, ignore_index=True) if reps else pd.DataFrame(); worst = pd.concat(worsts, ignore_index=True) if worsts else pd.DataFrame()
    return daily, rep, worst


def summarize(daily: pd.DataFrame, rep: pd.DataFrame, worst: pd.DataFrame) -> dict:
    d = daily.copy(); d["month"] = pd.to_datetime(d.date).dt.to_period("M").astype(str)
    mon_rows = []
    for m, g in d.groupby("month"):
        r = rep[rep.route_day.isin(g.date.astype(str))] if not rep.empty else pd.DataFrame()
        w = worst[worst.route_day.isin(g.date.astype(str))] if not worst.empty else pd.DataFrame()
        row = dict(month=m, challenger_days=int((g.chosen_route == "CHALLENGER").sum()))
        row.update(metrics(r, "rep_")); row.update(metrics(w, "worst_")); mon_rows.append(row)
    mon = pd.DataFrame(mon_rows)
    june = mon[mon.month == "2026-06"].copy() if not mon.empty else pd.DataFrame()
    first = daily.iloc[0]
    return dict(
        route_config=str(first.route_config), mode=str(first["mode"]), vol_col=str(first.vol_col), vol_q=float(first.vol_q), min_day_trades=int(first.min_day_trades), side_filter=str(first.side_filter), direction_filter=str(first.direction_filter), session_filter=str(first.session_filter),
        route_days=int((daily.chosen_route != "NO_ROUTE").sum()), champion_days=int((daily.chosen_route == "CHAMPION").sum()), challenger_days=int((daily.chosen_route == "CHALLENGER").sum()), high_vol_days=int(daily.is_high_vol.sum()),
        rep_trades=int(len(rep)), worst_trades=int(len(worst)), rep_sum_result_usd=float(pd.to_numeric(rep.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not rep.empty else 0.0, worst_sum_result_usd=float(pd.to_numeric(worst.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not worst.empty else 0.0,
        rep_pf=pf(rep.result_usd) if not rep.empty else 0.0, worst_pf=pf(worst.result_usd) if not worst.empty else 0.0,
        negative_months_worst=int((mon.worst_sum_result_usd < 0).sum()) if not mon.empty else 0,
        june_challenger_days=int(june.iloc[0].challenger_days) if not june.empty else 0,
        june_worst_sum_result_usd=float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
        june_rep_sum_result_usd=float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
    ), mon


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-history-days", type=int, default=30)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "138"; out.mkdir(parents=True, exist_ok=True)
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    led = load_csv(led_path)
    blockers = []
    if led.empty: blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    summaries, monthly_all = [], []
    selected_daily = pd.DataFrame(); selected_monthly = pd.DataFrame()
    if not blockers:
        led["entry_dt"] = pd.to_datetime(led.entry_dt, errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy(); led["entry_date"] = led.entry_dt.dt.normalize()
        start = pd.Timestamp(args.start); end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        vol_cols = [c for c in ["m15_atr28", "h1_atr28", "h4_atr28", "d1_atr28"] if c in led.columns]
        if not vol_cols: blockers.append({"blocker_id": "missing_vol_cols"})
        for vol_col in vol_cols:
            for vol_q in [0.5, 0.6, 0.7, 0.8]:
                for min_day in [3,5,8,10]:
                    for side_filter in ["ALL", "SHORT_ONLY", "LONG_ONLY"]:
                        for direction_filter in ["ANY", "SIDE_WITH_H1", "SIDE_WITH_H4", "SIDE_WITH_H1_H4"]:
                            for session_filter in ["ANY", "SESSION_7_15", "SESSION_16_22", "NO_SESSION_FILTER_TAG"]:
                                for mode in ["FILL_ONLY", "OVERRIDE"]:
                                    daily, rep, worst = evaluate_config(led, champion, challenger, start, end, vol_col, vol_q, args.min_history_days, min_day, side_filter, direction_filter, session_filter, mode)
                                    s, mon = summarize(daily, rep, worst); summaries.append(s); monthly_all.append(mon.assign(route_config=s["route_config"]))
        sm = pd.DataFrame(summaries)
        if not sm.empty:
            sm["safe_mode"] = sm["mode"].eq("FILL_ONLY")
            sm["score"] = sm.worst_sum_result_usd + sm.worst_pf * 100 - sm.negative_months_worst * 400 + sm.june_worst_sum_result_usd * 0.5 - (sm.challenger_days * 1.0)
            sm = sm.sort_values(["safe_mode", "negative_months_worst", "worst_sum_result_usd", "worst_pf", "june_worst_sum_result_usd"], ascending=[False, True, False, False, False]).reset_index(drop=True)
        save(sm, out / "gold_v3_138_factor_matrix_summary.csv")
        monthly_df = pd.concat(monthly_all, ignore_index=True) if monthly_all else pd.DataFrame(); save(monthly_df, out / "gold_v3_138_factor_matrix_monthly.csv")
        if not sm.empty:
            sel_key = str(sm.iloc[0].route_config)
            selected_monthly = monthly_df[monthly_df.route_config.astype(str) == sel_key].copy()
            save(selected_monthly, out / "gold_v3_138_selected_factor_monthly.csv")
            # recompute selected daily for readable paste
            r = sm.iloc[0]
            selected_daily, _, _ = evaluate_config(led, champion, challenger, start, end, r.vol_col, float(r.vol_q), args.min_history_days, int(r.min_day_trades), r.side_filter, r.direction_filter, r.session_filter, r["mode"])
            save(selected_daily, out / "gold_v3_138_selected_factor_daily.csv")
    sm = load_csv(out / "gold_v3_138_factor_matrix_summary.csv") if (out / "gold_v3_138_factor_matrix_summary.csv").exists() else pd.DataFrame()
    sel = sm.head(1).copy() if not sm.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers: decision = "FACTOR_MATRIX_BLOCKED_INPUT_MISSING"
    elif sel.empty: decision = "FACTOR_MATRIX_READY_NO_CONFIG"
    elif int(sel.iloc[0].negative_months_worst) > 0: decision = "FACTOR_MATRIX_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else: decision = "FACTOR_MATRIX_READY_NO_NEGATIVE_WORST_MONTHS"
    summary = {
        "step": STEP, "status": status, "ready": status == READY, "decision": decision, "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), "output_dir": str(out), "audit_only": True, "review_only": True,
        "champion_policy_key": champion, "challenger_policy_key": challenger,
        "selected_route_config": str(sel.iloc[0].route_config) if not sel.empty else "", "selected_mode": str(sel.iloc[0]["mode"]) if not sel.empty else "", "selected_vol_col": str(sel.iloc[0].vol_col) if not sel.empty else "", "selected_vol_q": float(sel.iloc[0].vol_q) if not sel.empty else 0.0,
        "selected_min_day_trades": int(sel.iloc[0].min_day_trades) if not sel.empty else 0, "selected_side_filter": str(sel.iloc[0].side_filter) if not sel.empty else "", "selected_direction_filter": str(sel.iloc[0].direction_filter) if not sel.empty else "", "selected_session_filter": str(sel.iloc[0].session_filter) if not sel.empty else "",
        "selected_challenger_days": int(sel.iloc[0].challenger_days) if not sel.empty else 0, "selected_worst_sum_result_usd": float(sel.iloc[0].worst_sum_result_usd) if not sel.empty else 0.0, "selected_worst_pf": float(sel.iloc[0].worst_pf) if not sel.empty else 0.0, "selected_negative_months_worst": int(sel.iloc[0].negative_months_worst) if not sel.empty else 0, "selected_june_worst_sum_result_usd": float(sel.iloc[0].june_worst_sum_result_usd) if not sel.empty else 0.0,
        "source_csv_mutated": False, "contract_mutated": False, "open_asof_allowed": False, "candidate_pool_removed": False, "f002_exclusion_bypassed": False, "blocker_count": len(blockers), "elapsed_seconds": round(time.time() - t0, 2)}
    (out / "gold_v3_138_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_138_decision.csv")
    lines = ["GOLD V3 138 PASTE_ME_CHALLENGER_FACTOR_MATRIX_AUDIT"] + [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP30_FACTOR_CONFIGS", sm.head(30).to_string(index=False) if not sm.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_FACTOR_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "SELECTED_FACTOR_DAILY_TAIL", selected_daily.tail(40).to_string(index=False) if not selected_daily.empty else "NO_SELECTED_DAILY"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_route_config": summary["selected_route_config"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
