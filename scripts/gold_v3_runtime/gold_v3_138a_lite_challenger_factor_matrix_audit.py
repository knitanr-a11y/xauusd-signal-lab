#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_138A_LITE_CHALLENGER_FACTOR_MATRIX_AUDIT_ONLY"
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


def metrics(df: pd.DataFrame, prefix: str = "") -> dict:
    if df is None or df.empty or "result_usd" not in df.columns:
        base = dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0)
        return {prefix + k: v for k, v in base.items()}
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
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
    )
    return {prefix + k: v for k, v in base.items()}


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), dict(raw_rows=0, dedup_trades=0, side_conflicts=0, duplicate_ratio=0.0)
    reps = []
    worsts = []
    side_conflicts = 0
    for _, g in df.groupby("entry_dt"):
        if "side" in g.columns and g.side.astype(str).nunique() > 1:
            side_conflicts += 1
        h = g.copy()
        for c in ["feature_score", "score", "ledger_score", "result_usd"]:
            h[c] = pd.to_numeric(h[c], errors="coerce") if c in h.columns else 0.0
        reps.append(h.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False]).iloc[0].to_dict())
        worsts.append(h.sort_values("result_usd", ascending=True).iloc[0].to_dict())
    raw = len(df)
    unique = int(df.entry_dt.nunique())
    return pd.DataFrame(reps), pd.DataFrame(worsts), dict(raw_rows=int(raw), dedup_trades=unique, side_conflicts=int(side_conflicts), duplicate_ratio=float((raw - unique) / raw) if raw else 0.0)


def daily_high_vol_map(led: pd.DataFrame, vol_col: str, q: float, min_history_days: int) -> dict:
    x = led[["entry_date", vol_col]].copy()
    x[vol_col] = pd.to_numeric(x[vol_col], errors="coerce")
    d = x.groupby("entry_date", as_index=False)[vol_col].median().sort_values("entry_date")
    vals = []
    out = {}
    for r in d.itertuples(index=False):
        day = r[0]
        v = r[1]
        hist = pd.Series(vals).dropna()
        th = float(hist.quantile(q)) if len(hist) >= min_history_days else math.nan
        out[day] = bool(pd.notna(v) and pd.notna(th) and float(v) >= th)
        vals.append(v)
    return out


def apply_factor_filter(df: pd.DataFrame, side_filter: str, direction_filter: str, session_filter: str) -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    if side_filter == "SHORT_ONLY":
        x = x[x.side.astype(str) == "SHORT"].copy()
    elif side_filter == "LONG_ONLY":
        x = x[x.side.astype(str) == "LONG"].copy()
    if direction_filter == "SIDE_WITH_H4" and not x.empty:
        side = x.side.astype(str)
        h4_up = x.get("h4_up", pd.Series([False] * len(x), index=x.index)).astype(str).str.lower().isin(["true", "1"])
        x = x[((side == "LONG") & h4_up) | ((side == "SHORT") & (~h4_up))].copy()
    if session_filter == "SESSION_7_15" and not x.empty and "condition" in x.columns:
        x = x[x.condition.astype(str).str.contains("session_7_15", na=False)].copy()
    return x


def evaluate_config(led: pd.DataFrame, champion_key: str, challenger_key: str, start: pd.Timestamp, end: pd.Timestamp, vol_col: str, q: float, min_history_days: int, min_day_trades: int, side_filter: str, direction_filter: str, session_filter: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hv_map = daily_high_vol_map(led, vol_col, q, min_history_days)
    champ = led[led.policy_key.astype(str) == champion_key].copy()
    chal = led[led.policy_key.astype(str) == challenger_key].copy()
    daily_rows = []
    rep_rows = []
    worst_rows = []
    route_config = f"FILL_ONLY|{vol_col}|Q{q}|MIN{min_day_trades}|{side_filter}|{direction_filter}|{session_filter}"

    for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
        c_raw = champ[champ.entry_date == day].copy()
        h_raw = chal[chal.entry_date == day].copy()
        h_raw = apply_factor_filter(h_raw, side_filter, direction_filter, session_filter)
        c_rep, c_worst, _ = dedup(c_raw)
        h_rep, h_worst, h_diag = dedup(h_raw)
        is_hv = bool(hv_map.get(day, False))
        has_champion = len(c_rep) > 0
        can_challenge = (not has_champion) and is_hv and len(h_rep) >= min_day_trades and h_diag.get("side_conflicts", 0) == 0
        if can_challenge:
            chosen = "CHALLENGER"
            r_rep = h_rep.copy()
            r_worst = h_worst.copy()
        elif has_champion:
            chosen = "CHAMPION"
            r_rep = c_rep.copy()
            r_worst = c_worst.copy()
        else:
            chosen = "NO_ROUTE"
            r_rep = pd.DataFrame()
            r_worst = pd.DataFrame()
        if not r_rep.empty:
            z = r_rep.copy()
            z["route_day"] = str(day.date())
            z["chosen_route"] = chosen
            z["route_config"] = route_config
            rep_rows.append(z)
        if not r_worst.empty:
            z = r_worst.copy()
            z["route_day"] = str(day.date())
            z["chosen_route"] = chosen
            z["route_config"] = route_config
            worst_rows.append(z)
        rec = dict(
            route_config=route_config,
            date=str(day.date()),
            chosen_route=chosen,
            is_high_vol=is_hv,
            champion_dedup_trades=int(len(c_rep)),
            challenger_dedup_trades=int(len(h_rep)),
        )
        rec.update(metrics(r_rep, "rep_"))
        rec.update(metrics(r_worst, "worst_"))
        daily_rows.append(rec)

    daily = pd.DataFrame(daily_rows)
    rep = pd.concat(rep_rows, ignore_index=True) if rep_rows else pd.DataFrame()
    worst = pd.concat(worst_rows, ignore_index=True) if worst_rows else pd.DataFrame()
    return daily, rep, worst


def summarize_config(daily: pd.DataFrame, rep: pd.DataFrame, worst: pd.DataFrame, meta: dict) -> tuple[dict, pd.DataFrame]:
    d = daily.copy()
    d["month"] = pd.to_datetime(d.date).dt.to_period("M").astype(str)
    month_rows = []
    for m, g in d.groupby("month"):
        r = rep[rep.route_day.isin(g.date.astype(str))] if not rep.empty else pd.DataFrame()
        w = worst[worst.route_day.isin(g.date.astype(str))] if not worst.empty else pd.DataFrame()
        row = dict(
            route_config=str(meta["route_config"]),
            month=m,
            route_days=int((g.chosen_route != "NO_ROUTE").sum()),
            champion_days=int((g.chosen_route == "CHAMPION").sum()),
            challenger_days=int((g.chosen_route == "CHALLENGER").sum()),
            high_vol_days=int(g.is_high_vol.astype(bool).sum()),
        )
        row.update(metrics(r, "rep_"))
        row.update(metrics(w, "worst_"))
        month_rows.append(row)
    monthly = pd.DataFrame(month_rows)
    june = monthly[monthly.month == "2026-06"].copy() if not monthly.empty else pd.DataFrame()
    result = dict(
        **meta,
        route_days=int((daily.chosen_route != "NO_ROUTE").sum()),
        champion_days=int((daily.chosen_route == "CHAMPION").sum()),
        challenger_days=int((daily.chosen_route == "CHALLENGER").sum()),
        high_vol_days=int(daily.is_high_vol.astype(bool).sum()),
        rep_trades=int(len(rep)),
        worst_trades=int(len(worst)),
        rep_sum_result_usd=float(pd.to_numeric(rep.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not rep.empty else 0.0,
        worst_sum_result_usd=float(pd.to_numeric(worst.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not worst.empty else 0.0,
        rep_pf=pf(rep.result_usd) if not rep.empty else 0.0,
        worst_pf=pf(worst.result_usd) if not worst.empty else 0.0,
        negative_months_worst=int((monthly.worst_sum_result_usd < 0).sum()) if not monthly.empty else 0,
        june_challenger_days=int(june.iloc[0].challenger_days) if not june.empty else 0,
        june_rep_sum_result_usd=float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
        june_worst_sum_result_usd=float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
    )
    return result, monthly


def progress(out_dir: Path, done: int, total: int, route_config: str, started: float) -> None:
    pct = (done / total * 100.0) if total else 100.0
    msg = f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {route_config} elapsed={time.time()-started:.1f}s"
    print(msg, flush=True)
    (out_dir / "progress.txt").write_text(msg + "\n", encoding="utf-8")
    (out_dir / "progress.json").write_text(json.dumps({"done": done, "total": total, "percent": pct, "route_config": route_config, "elapsed_seconds": round(time.time()-started, 1)}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    started = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-history-days", type=int, default=30)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "138a"
    out.mkdir(parents=True, exist_ok=True)

    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    champion_key = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger_key = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    led = load_csv(led_path)
    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not champion_key or not challenger_key:
        blockers.append({"blocker_id": "missing_champion_or_challenger"})

    summary_df = pd.DataFrame()
    selected_daily = pd.DataFrame()
    selected_monthly = pd.DataFrame()

    if not blockers:
        led["entry_dt"] = pd.to_datetime(led.entry_dt, errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led["entry_date"] = led.entry_dt.dt.normalize()
        start = pd.Timestamp(args.start)
        end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()

        combos = list(product(
            ["m15_atr28", "d1_atr28"],
            [0.5, 0.7],
            [5, 8],
            ["ALL", "SHORT_ONLY"],
            ["ANY", "SIDE_WITH_H4"],
            ["ANY", "SESSION_7_15"],
        ))
        combos = [c for c in combos if c[0] in led.columns]
        total = len(combos)
        summaries = []
        monthly_all = []
        selected_key = ""
        selected_cache = {}

        progress(out, 0, total, "START", started)
        for i, (vol_col, q, min_day_trades, side_filter, direction_filter, session_filter) in enumerate(combos, start=1):
            route_config = f"FILL_ONLY|{vol_col}|Q{q}|MIN{min_day_trades}|{side_filter}|{direction_filter}|{session_filter}"
            daily, rep, worst = evaluate_config(led, champion_key, challenger_key, start, end, vol_col, q, args.min_history_days, min_day_trades, side_filter, direction_filter, session_filter)
            meta = dict(route_config=route_config, route_mode="FILL_ONLY", vol_col=vol_col, vol_q=q, min_day_trades=min_day_trades, side_filter=side_filter, direction_filter=direction_filter, session_filter=session_filter)
            row, monthly = summarize_config(daily, rep, worst, meta)
            summaries.append(row)
            monthly_all.append(monthly)
            selected_cache[route_config] = (daily, monthly)
            progress(out, i, total, route_config, started)

        summary_df = pd.DataFrame(summaries)
        if not summary_df.empty:
            summary_df["score"] = summary_df.worst_sum_result_usd + summary_df.worst_pf * 100.0 - summary_df.negative_months_worst * 400.0 + summary_df.june_worst_sum_result_usd * 0.5 - summary_df.challenger_days * 1.0
            summary_df = summary_df.sort_values(["negative_months_worst", "worst_sum_result_usd", "worst_pf", "june_worst_sum_result_usd"], ascending=[True, False, False, False]).reset_index(drop=True)
            selected_key = str(summary_df.iloc[0].route_config)
            selected_daily, selected_monthly = selected_cache.get(selected_key, (pd.DataFrame(), pd.DataFrame()))

        save(summary_df, out / "gold_v3_138a_lite_factor_matrix_summary.csv")
        save(pd.concat(monthly_all, ignore_index=True) if monthly_all else pd.DataFrame(), out / "gold_v3_138a_lite_factor_matrix_monthly_all.csv")
        save(selected_daily, out / "gold_v3_138a_selected_daily.csv")
        save(selected_monthly, out / "gold_v3_138a_selected_monthly.csv")

    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "LITE_FACTOR_MATRIX_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "LITE_FACTOR_MATRIX_READY_NO_CONFIG"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "LITE_FACTOR_MATRIX_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "LITE_FACTOR_MATRIX_READY_NO_NEGATIVE_WORST_MONTHS"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "progress_total_configs": int(len(summary_df)) if not summary_df.empty else 0,
        "progress_completed_configs": int(len(summary_df)) if not summary_df.empty else 0,
        "progress_output": str(out / "progress.txt"),
        "champion_policy_key": champion_key,
        "challenger_policy_key": challenger_key,
        "selected_route_config": str(selected.iloc[0].route_config) if not selected.empty else "",
        "selected_route_mode": str(selected.iloc[0].route_mode) if not selected.empty else "",
        "selected_vol_col": str(selected.iloc[0].vol_col) if not selected.empty else "",
        "selected_vol_q": float(selected.iloc[0].vol_q) if not selected.empty else 0.0,
        "selected_min_day_trades": int(selected.iloc[0].min_day_trades) if not selected.empty else 0,
        "selected_side_filter": str(selected.iloc[0].side_filter) if not selected.empty else "",
        "selected_direction_filter": str(selected.iloc[0].direction_filter) if not selected.empty else "",
        "selected_session_filter": str(selected.iloc[0].session_filter) if not selected.empty else "",
        "selected_challenger_days": int(selected.iloc[0].challenger_days) if not selected.empty else 0,
        "selected_worst_sum_result_usd": float(selected.iloc[0].worst_sum_result_usd) if not selected.empty else 0.0,
        "selected_worst_pf": float(selected.iloc[0].worst_pf) if not selected.empty else 0.0,
        "selected_negative_months_worst": int(selected.iloc[0].negative_months_worst) if not selected.empty else 0,
        "selected_june_worst_sum_result_usd": float(selected.iloc[0].june_worst_sum_result_usd) if not selected.empty else 0.0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - started, 2),
    }
    (out / "gold_v3_138a_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_138a_decision.csv")

    lines = ["GOLD V3 138A PASTE_ME_LITE_CHALLENGER_FACTOR_MATRIX_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP20_LITE_FACTOR_CONFIGS", summary_df.head(20).to_string(index=False) if not summary_df.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "SELECTED_DAILY_TAIL", selected_daily.tail(40).to_string(index=False) if not selected_daily.empty else "NO_SELECTED_DAILY"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_route_config": summary["selected_route_config"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
