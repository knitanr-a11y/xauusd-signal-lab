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

STEP = "GOLD_V3_136_HIGH_VOL_CHALLENGER_ROUTE_AUDIT_ONLY"
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
        base = dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, first_entry_dt="", last_entry_dt="")
        return {prefix + k: v for k, v in base.items()}
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x.get("result_usd"), errors="coerce")
    x = x[x.result_usd.notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame(), prefix)
    base = dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd),
        sum_result_usd=float(x.result_usd.sum()),
        first_entry_dt=str(x.entry_dt.min()) if "entry_dt" in x.columns else "",
        last_entry_dt=str(x.entry_dt.max()) if "entry_dt" in x.columns else "",
    )
    return {prefix + k: v for k, v in base.items()}


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), dict(raw_rows=0, dedup_trades=0, side_conflict_times=0, duplicate_ratio=0.0)
    reps, worsts = [], []
    conflicts = 0
    for _, g in df.groupby("entry_dt"):
        if "side" in g.columns and g.side.astype(str).nunique() > 1:
            conflicts += 1
        h = g.copy()
        for c in ["feature_score", "score", "ledger_score", "result_usd"]:
            h[c] = pd.to_numeric(h[c], errors="coerce") if c in h.columns else 0.0
        reps.append(h.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False]).iloc[0].to_dict())
        worsts.append(h.sort_values("result_usd", ascending=True).iloc[0].to_dict())
    n = len(df); u = int(df.entry_dt.nunique())
    return pd.DataFrame(reps), pd.DataFrame(worsts), dict(raw_rows=int(n), dedup_trades=u, side_conflict_times=int(conflicts), duplicate_ratio=float((n-u)/n) if n else 0.0)


def sum_usd(df: pd.DataFrame) -> float:
    if df is None or df.empty or "result_usd" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df.result_usd, errors="coerce").dropna().sum())


def build_daily_vol(led: pd.DataFrame, col: str) -> pd.DataFrame:
    x = led[["entry_date", col]].copy()
    x[col] = pd.to_numeric(x[col], errors="coerce")
    d = x.groupby("entry_date", as_index=False)[col].median().rename(columns={col: "vol_value"})
    d = d.sort_values("entry_date").reset_index(drop=True)
    return d


def add_expanding_threshold(daily_vol: pd.DataFrame, q: float, min_history_days: int) -> pd.DataFrame:
    d = daily_vol.copy()
    thresholds = []
    vals = []
    for v in d.vol_value.tolist():
        clean = pd.Series(vals).dropna()
        thresholds.append(float(clean.quantile(q)) if len(clean) >= min_history_days else math.nan)
        vals.append(v)
    d["vol_threshold"] = thresholds
    d["is_high_vol"] = d.vol_value >= d.vol_threshold
    d.loc[d.vol_threshold.isna(), "is_high_vol"] = False
    return d


def route_one_config(led: pd.DataFrame, champion: str, challenger: str, start: pd.Timestamp, end: pd.Timestamp, vol_col: str, q: float, min_history_days: int, stall_days: int, mode: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    vol = add_expanding_threshold(build_daily_vol(led, vol_col), q, min_history_days)
    vol_map = {r.entry_date: (float(r.vol_value), float(r.vol_threshold) if pd.notna(r.vol_threshold) else math.nan, bool(r.is_high_vol)) for r in vol.itertuples()}
    champ = led[led.policy_key.astype(str) == champion].copy()
    chal = led[led.policy_key.astype(str) == challenger].copy()
    rows, rep_all, worst_all = [], [], []
    last_champ_day = None
    for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
        c_raw = champ[champ.entry_date == day].copy()
        h_raw = chal[chal.entry_date == day].copy()
        c_rep, c_worst, _ = dedup(c_raw)
        h_rep, h_worst, h_diag = dedup(h_raw)
        if not c_rep.empty:
            last_champ_day = day
        days_since = None if last_champ_day is None else int((day - last_champ_day).days)
        vv, th, hv = vol_map.get(day, (math.nan, math.nan, False))
        has_champ = not c_rep.empty
        has_chal = not h_rep.empty and h_diag.get("side_conflict_times", 0) == 0
        use_chal = False
        if mode == "HIGHVOL_OVERRIDE":
            use_chal = hv and has_chal
        elif mode == "HIGHVOL_FILL_ONLY":
            use_chal = (not has_champ) and hv and has_chal
        elif mode == "STALL3_HIGHVOL_FILL":
            use_chal = (not has_champ) and (days_since is not None) and days_since >= stall_days and hv and has_chal
        else:
            use_chal = False
        if use_chal:
            chosen = "CHALLENGER"; r_rep = h_rep; r_worst = h_worst
        elif has_champ:
            chosen = "CHAMPION"; r_rep = c_rep; r_worst = c_worst
        else:
            chosen = "NO_ROUTE"; r_rep = pd.DataFrame(); r_worst = pd.DataFrame()
        if not r_rep.empty:
            z = r_rep.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; z["route_config"] = f"{mode}|{vol_col}|Q{q}"; rep_all.append(z)
        if not r_worst.empty:
            z = r_worst.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; z["route_config"] = f"{mode}|{vol_col}|Q{q}"; worst_all.append(z)
        rec = dict(route_config=f"{mode}|{vol_col}|Q{q}", mode=mode, vol_col=vol_col, q=q, date=str(day.date()), chosen_route=chosen, is_high_vol=hv, vol_value=vv, vol_threshold=th, days_since_last_champion="" if days_since is None else days_since, champion_dedup_trades=int(len(c_rep)), challenger_dedup_trades=int(len(h_rep)))
        rec.update(metrics(r_rep, "rep_")); rec.update(metrics(r_worst, "worst_")); rows.append(rec)
    return pd.DataFrame(rows), (pd.concat(rep_all, ignore_index=True) if rep_all else pd.DataFrame()), (pd.concat(worst_all, ignore_index=True) if worst_all else pd.DataFrame()), vol


def summarize_config(daily: pd.DataFrame, rep: pd.DataFrame, worst: pd.DataFrame) -> dict:
    if daily.empty:
        return {}
    d = daily.copy(); d["month"] = pd.to_datetime(d.date).dt.to_period("M").astype(str)
    monthly = []
    for m, g in d.groupby("month"):
        r = rep[rep.route_day.isin(g.date.astype(str))] if not rep.empty else pd.DataFrame()
        w = worst[worst.route_day.isin(g.date.astype(str))] if not worst.empty else pd.DataFrame()
        row = dict(month=m, route_days=int((g.chosen_route != "NO_ROUTE").sum()), champion_days=int((g.chosen_route == "CHAMPION").sum()), challenger_days=int((g.chosen_route == "CHALLENGER").sum()))
        row.update(metrics(r, "rep_")); row.update(metrics(w, "worst_")); monthly.append(row)
    mon = pd.DataFrame(monthly)
    return dict(
        route_config=str(daily.iloc[0].route_config),
        mode=str(daily.iloc[0].mode),
        vol_col=str(daily.iloc[0].vol_col),
        q=float(daily.iloc[0].q),
        route_days=int((daily.chosen_route != "NO_ROUTE").sum()),
        champion_days=int((daily.chosen_route == "CHAMPION").sum()),
        challenger_days=int((daily.chosen_route == "CHALLENGER").sum()),
        high_vol_days=int(daily.is_high_vol.sum()),
        route_rep_trades=int(len(rep)),
        route_worst_trades=int(len(worst)),
        route_rep_sum_result_usd=sum_usd(rep),
        route_worst_sum_result_usd=sum_usd(worst),
        route_rep_pf=pf(rep.result_usd) if not rep.empty else 0.0,
        route_worst_pf=pf(worst.result_usd) if not worst.empty else 0.0,
        negative_months_worst=int((mon.worst_sum_result_usd < 0).sum()) if not mon.empty else 0,
        june_challenger_days=int(mon[mon.month == "2026-06"].challenger_days.iloc[0]) if not mon.empty and (mon.month == "2026-06").any() else 0,
        june_worst_sum_result_usd=float(mon[mon.month == "2026-06"].worst_sum_result_usd.iloc[0]) if not mon.empty and (mon.month == "2026-06").any() else 0.0,
    )


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-history-days", type=int, default=30)
    ap.add_argument("--stall-days", type=int, default=3)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "136"
    out.mkdir(parents=True, exist_ok=True)

    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    led = load_csv(led_path)
    blockers = []
    if led.empty: blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not champion or not challenger: blockers.append({"blocker_id": "missing_champion_or_challenger"})

    summaries, daily_all = [], []
    best_daily = pd.DataFrame(); best_rep = pd.DataFrame(); best_worst = pd.DataFrame()
    if not blockers:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led["entry_date"] = led.entry_dt.dt.normalize()
        start = pd.Timestamp(args.start); end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        vol_cols = [c for c in ["m15_atr28", "h1_atr28", "h4_atr28", "d1_atr28"] if c in led.columns]
        if not vol_cols:
            blockers.append({"blocker_id": "missing_atr_columns"})
        else:
            modes = ["HIGHVOL_FILL_ONLY", "STALL3_HIGHVOL_FILL", "HIGHVOL_OVERRIDE"]
            qs = [0.50, 0.60, 0.70, 0.80]
            reps_by_config = {}
            worst_by_config = {}
            for col in vol_cols:
                for q in qs:
                    for mode in modes:
                        d, r, w, _ = route_one_config(led, champion, challenger, start, end, col, q, args.min_history_days, args.stall_days, mode)
                        daily_all.append(d)
                        s = summarize_config(d, r, w)
                        if s: summaries.append(s)
                        reps_by_config[s.get("route_config", "")] = r if s else pd.DataFrame()
                        worst_by_config[s.get("route_config", "")] = w if s else pd.DataFrame()
            sm = pd.DataFrame(summaries)
            if not sm.empty:
                sm["safe_fill_mode"] = sm["mode"].isin(["HIGHVOL_FILL_ONLY", "STALL3_HIGHVOL_FILL"])
                sm["score"] = sm.route_worst_sum_result_usd + sm.route_worst_pf * 100.0 - sm.negative_months_worst * 250.0 + sm.june_worst_sum_result_usd * 0.25
                sm = sm.sort_values(["safe_fill_mode", "negative_months_worst", "route_worst_sum_result_usd", "route_worst_pf"], ascending=[False, True, False, False]).reset_index(drop=True)
                best_key = str(sm.iloc[0].route_config)
                best_rep = reps_by_config.get(best_key, pd.DataFrame())
                best_worst = worst_by_config.get(best_key, pd.DataFrame())
                best_daily = pd.concat(daily_all, ignore_index=True)
                best_daily = best_daily[best_daily.route_config.astype(str) == best_key].copy()
            save(sm if not sm.empty else pd.DataFrame(), out / "gold_v3_136_high_vol_route_config_summary.csv")
            save((pd.concat(daily_all, ignore_index=True) if daily_all else pd.DataFrame()), out / "gold_v3_136_all_daily_route_configs.csv")
            save(best_daily, out / "gold_v3_136_selected_route_daily_rows.csv")
            save(best_rep, out / "gold_v3_136_selected_route_rep_rows.csv")
            save(best_worst, out / "gold_v3_136_selected_route_worst_rows.csv")

    summary_df = load_csv(out / "gold_v3_136_high_vol_route_config_summary.csv") if (out / "gold_v3_136_high_vol_route_config_summary.csv").exists() else pd.DataFrame()
    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "HIGH_VOL_ROUTE_AUDIT_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "HIGH_VOL_ROUTE_AUDIT_READY_NO_CONFIG"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "HIGH_VOL_ROUTE_AUDIT_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "HIGH_VOL_ROUTE_AUDIT_READY_NO_NEGATIVE_WORST_MONTHS"

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
        "challenger_policy_key": challenger,
        "min_history_days": args.min_history_days,
        "stall_days": args.stall_days,
        "selected_route_config": str(selected.iloc[0].route_config) if not selected.empty else "",
        "selected_mode": str(selected.iloc[0].mode) if not selected.empty else "",
        "selected_vol_col": str(selected.iloc[0].vol_col) if not selected.empty else "",
        "selected_q": float(selected.iloc[0].q) if not selected.empty else 0.0,
        "selected_challenger_days": int(selected.iloc[0].challenger_days) if not selected.empty else 0,
        "selected_high_vol_days": int(selected.iloc[0].high_vol_days) if not selected.empty else 0,
        "selected_worst_pf": float(selected.iloc[0].route_worst_pf) if not selected.empty else 0.0,
        "selected_worst_sum_result_usd": float(selected.iloc[0].route_worst_sum_result_usd) if not selected.empty else 0.0,
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
    (out / "gold_v3_136_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_136_decision.csv")
    lines = ["GOLD V3 136 PASTE_ME_HIGH_VOL_CHALLENGER_ROUTE_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP20_HIGH_VOL_ROUTE_CONFIGS", summary_df.head(20).to_string(index=False) if not summary_df.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_ROUTE_DAILY_TAIL", best_daily.tail(40).to_string(index=False) if not best_daily.empty else "NO_SELECTED_DAILY_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_route_config": summary.get("selected_route_config", ""), "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
