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

STEP = "GOLD_V3_142_INTRADAY_CHALLENGER_EVENT_CAP_AUDIT_ONLY"
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
    x["result_usd"] = pd.to_numeric(x.result_usd, errors="coerce")
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


def dedup_at_entry(df: pd.DataFrame) -> tuple[dict | None, dict | None, dict]:
    if df.empty:
        return None, None, dict(raw_rows=0, side_conflict=False)
    h = df.copy()
    side_conflict = bool("side" in h.columns and h.side.astype(str).nunique() > 1)
    for c in ["feature_score", "score", "ledger_score", "result_usd"]:
        h[c] = pd.to_numeric(h[c], errors="coerce") if c in h.columns else 0.0
    rep = h.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False]).iloc[0].to_dict()
    worst = h.sort_values("result_usd", ascending=True).iloc[0].to_dict()
    return rep, worst, dict(raw_rows=int(len(df)), side_conflict=side_conflict)


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


def progress(out_dir: Path, done: int, total: int, route_config: str, started: float) -> None:
    pct = (done / total * 100.0) if total else 100.0
    elapsed = time.time() - started
    msg = f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {route_config} elapsed={elapsed:.1f}s"
    print(msg, flush=True)
    (out_dir / "progress.txt").write_text(msg + "\n", encoding="utf-8")
    (out_dir / "progress.json").write_text(json.dumps({
        "done": done,
        "total": total,
        "percent": pct,
        "route_config": route_config,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(led: pd.DataFrame, champion_key: str, challenger_key: str, start: pd.Timestamp, end: pd.Timestamp, vol_col: str, vol_q: float, min_hist: int, champion_block_after: int, challenger_running_min: int, challenger_daily_cap: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hv_map = daily_high_vol_map(led, vol_col, vol_q, min_hist)
    champ = led[led.policy_key.astype(str) == champion_key].copy()
    chal = led[led.policy_key.astype(str) == challenger_key].copy()
    rows, reps, worsts = [], [], []
    route_config = f"INTRADAY_CAP|{vol_col}|Q{vol_q}|BLOCK_CHAMPION_GE_{champion_block_after}|CHAL_RUNNING_GE_{challenger_running_min}|CHAL_CAP_{challenger_daily_cap}"

    for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
        cday = champ[champ.entry_date == day].copy()
        hday = chal[chal.entry_date == day].copy()
        times = sorted(set(cday.entry_dt.tolist()) | set(hday.entry_dt.tolist()))
        c_seen = 0
        h_seen = 0
        h_taken = 0
        is_hv = bool(hv_map.get(day, False))
        if not times:
            rows.append(dict(route_config=route_config, date=str(day.date()), entry_dt="", chosen_route="NO_ROUTE", is_high_vol=is_hv, champion_running_count=0, challenger_running_count=0, challenger_taken_count=0, rep_trades=0, worst_trades=0, rep_sum_result_usd=0.0, worst_sum_result_usd=0.0))
            continue
        for t in times:
            cg = cday[cday.entry_dt == t].copy()
            hg = hday[hday.entry_dt == t].copy()
            c_rep, c_worst, _ = dedup_at_entry(cg)
            h_rep, h_worst, hdiag = dedup_at_entry(hg)
            has_c = c_rep is not None
            has_h = h_rep is not None
            chosen = "NO_ROUTE"
            rep = None
            worst = None
            if has_c:
                c_seen += 1
                if c_seen < champion_block_after:
                    chosen = "CHAMPION"
                    rep = c_rep
                    worst = c_worst
            elif has_h:
                h_seen += 1
                if is_hv and h_seen >= challenger_running_min and h_taken < challenger_daily_cap and not hdiag.get("side_conflict", False):
                    chosen = "CHALLENGER"
                    rep = h_rep
                    worst = h_worst
                    h_taken += 1
            if rep is not None:
                rz = dict(rep)
                rz.update(route_config=route_config, route_day=str(day.date()), chosen_route=chosen, running_count=c_seen if chosen == "CHAMPION" else h_seen, challenger_taken_count=h_taken)
                reps.append(rz)
                wz = dict(worst)
                wz.update(route_config=route_config, route_day=str(day.date()), chosen_route=chosen, running_count=c_seen if chosen == "CHAMPION" else h_seen, challenger_taken_count=h_taken)
                worsts.append(wz)
            rec = dict(route_config=route_config, date=str(day.date()), entry_dt=str(t), chosen_route=chosen, is_high_vol=is_hv, champion_running_count=c_seen, challenger_running_count=h_seen, challenger_taken_count=h_taken, champion_has_entry=has_c, challenger_has_entry=has_h)
            if rep is not None:
                rec.update(metrics(pd.DataFrame([rep]), "rep_"))
                rec.update(metrics(pd.DataFrame([worst]), "worst_"))
            else:
                rec.update(metrics(pd.DataFrame(), "rep_"))
                rec.update(metrics(pd.DataFrame(), "worst_"))
            rows.append(rec)
    daily = pd.DataFrame(rows)
    repdf = pd.DataFrame(reps)
    worstdf = pd.DataFrame(worsts)
    return daily, repdf, worstdf


def summarize(daily: pd.DataFrame, rep: pd.DataFrame, worst: pd.DataFrame, cfg: dict) -> tuple[dict, pd.DataFrame]:
    d = daily.copy()
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d = d[d.date.notna()].copy()
    d["month"] = d.date.dt.to_period("M").astype(str)
    for c in ["rep_sum_result_usd", "worst_sum_result_usd", "rep_trades", "worst_trades"]:
        d[c] = pd.to_numeric(d.get(c, 0), errors="coerce").fillna(0)
    mrows = []
    for m, g in d.groupby("month"):
        r = rep[rep.route_day.isin(g.date.dt.date.astype(str))] if not rep.empty else pd.DataFrame()
        w = worst[worst.route_day.isin(g.date.dt.date.astype(str))] if not worst.empty else pd.DataFrame()
        row = dict(month=m, route_config=cfg["route_config"], route_events=int((g.chosen_route != "NO_ROUTE").sum()), champion_events=int((g.chosen_route == "CHAMPION").sum()), challenger_events=int((g.chosen_route == "CHALLENGER").sum()), no_route_events=int((g.chosen_route == "NO_ROUTE").sum()))
        row.update(metrics(r, "rep_")); row.update(metrics(w, "worst_")); mrows.append(row)
    mon = pd.DataFrame(mrows)
    june = mon[mon.month == "2026-06"].copy() if not mon.empty else pd.DataFrame()
    out = dict(
        **cfg,
        route_events=int((daily.chosen_route != "NO_ROUTE").sum()),
        champion_events=int((daily.chosen_route == "CHAMPION").sum()),
        challenger_events=int((daily.chosen_route == "CHALLENGER").sum()),
        rep_trades=int(len(rep)),
        worst_trades=int(len(worst)),
        rep_sum_result_usd=float(pd.to_numeric(rep.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not rep.empty else 0.0,
        worst_sum_result_usd=float(pd.to_numeric(worst.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not worst.empty else 0.0,
        rep_pf=pf(rep.result_usd) if not rep.empty else 0.0,
        worst_pf=pf(worst.result_usd) if not worst.empty else 0.0,
        negative_months_worst=int((mon.worst_sum_result_usd < 0).sum()) if not mon.empty else 0,
        june_worst_sum_result_usd=float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
        june_rep_sum_result_usd=float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
    )
    return out, mon


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
    out = root / "142"
    out.mkdir(parents=True, exist_ok=True)

    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    s141 = read_json(root / "141" / "gold_v3_141_summary.json")
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    vol_col = str(s141.get("selected_route_config", "INTRADAY|d1_atr28|Q0.5")).split("|")[1] if "|" in str(s141.get("selected_route_config", "")) else "d1_atr28"
    vol_q = float(s141.get("selected_route_config", "Q0.5").split("|Q")[-1].split("|")[0]) if "|Q" in str(s141.get("selected_route_config", "")) else 0.5
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    led = load_csv(led_path)
    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not led.empty and vol_col not in led.columns:
        blockers.append({"blocker_id": "missing_vol_col", "vol_col": vol_col})

    summary_df = pd.DataFrame(); selected_daily = pd.DataFrame(); selected_monthly = pd.DataFrame()
    total_configs = 0
    completed_configs = 0
    if not blockers:
        led["entry_dt"] = pd.to_datetime(led.entry_dt, errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led["entry_date"] = led.entry_dt.dt.normalize()
        start = pd.Timestamp(args.start); end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        configs = []
        for cb in [2, 3, 4]:
            for cr in [1, 3, 5, 8]:
                for cap in [1, 2, 3, 5, 8]:
                    configs.append((cb, cr, cap))
        total_configs = len(configs)
        progress(out, 0, total_configs, "START", t0)
        rows = []; monthlies = []; cache = {}
        for idx, (cb, cr, cap) in enumerate(configs, start=1):
            route_config = f"INTRADAY_CAP|{vol_col}|Q{vol_q}|BLOCK_CHAMPION_GE_{cb}|CHAL_RUNNING_GE_{cr}|CHAL_CAP_{cap}"
            daily, rep, worst = evaluate(led, champion, challenger, start, end, vol_col, vol_q, args.min_history_days, cb, cr, cap)
            cfg = dict(route_config=route_config, champion_block_after=cb, challenger_running_min=cr, challenger_daily_cap=cap, vol_col=vol_col, vol_q=vol_q)
            s, mon = summarize(daily, rep, worst, cfg)
            rows.append(s); monthlies.append(mon); cache[cfg["route_config"]] = (daily, mon)
            completed_configs = idx
            progress(out, completed_configs, total_configs, route_config, t0)
        summary_df = pd.DataFrame(rows)
        if not summary_df.empty:
            summary_df["score"] = summary_df.worst_sum_result_usd + summary_df.worst_pf * 100 - summary_df.negative_months_worst * 400 + summary_df.june_worst_sum_result_usd * 0.2 - summary_df.route_events * 0.5
            summary_df = summary_df.sort_values(["negative_months_worst", "worst_sum_result_usd", "worst_pf", "route_events"], ascending=[True, False, False, True]).reset_index(drop=True)
            selected_key = str(summary_df.iloc[0].route_config)
            selected_daily, selected_monthly = cache.get(selected_key, (pd.DataFrame(), pd.DataFrame()))
        save(summary_df, out / "gold_v3_142_intraday_challenger_event_cap_summary.csv")
        save(pd.concat(monthlies, ignore_index=True) if monthlies else pd.DataFrame(), out / "gold_v3_142_intraday_challenger_event_cap_monthly_all.csv")
        save(selected_daily, out / "gold_v3_142_selected_intraday_cap_daily.csv")
        save(selected_monthly, out / "gold_v3_142_selected_intraday_cap_monthly.csv")

    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "INTRADAY_CHALLENGER_CAP_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "INTRADAY_CHALLENGER_CAP_READY_NO_CONFIG"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "INTRADAY_CHALLENGER_CAP_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "INTRADAY_CHALLENGER_CAP_READY_NO_NEGATIVE_WORST_MONTHS"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "progress_total_configs": total_configs,
        "progress_completed_configs": completed_configs,
        "progress_output": str(out / "progress.txt"),
        "source_141_decision": s141.get("decision", ""),
        "source_141_selected_route_config": s141.get("selected_route_config", ""),
        "champion_policy_key": champion,
        "challenger_policy_key": challenger,
        "selected_route_config": str(selected.iloc[0].route_config) if not selected.empty else "",
        "selected_champion_block_after": int(selected.iloc[0].champion_block_after) if not selected.empty else 0,
        "selected_challenger_running_min": int(selected.iloc[0].challenger_running_min) if not selected.empty else 0,
        "selected_challenger_daily_cap": int(selected.iloc[0].challenger_daily_cap) if not selected.empty else 0,
        "selected_route_events": int(selected.iloc[0].route_events) if not selected.empty else 0,
        "selected_champion_events": int(selected.iloc[0].champion_events) if not selected.empty else 0,
        "selected_challenger_events": int(selected.iloc[0].challenger_events) if not selected.empty else 0,
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
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_142_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_142_decision.csv")
    lines = ["GOLD V3 142 PASTE_ME_INTRADAY_CHALLENGER_EVENT_CAP_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP30_INTRADAY_CHALLENGER_CAP_CONFIGS", summary_df.head(30).to_string(index=False) if not summary_df.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_INTRADAY_CAP_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "SELECTED_INTRADAY_CAP_DAILY_TAIL", selected_daily.tail(60).to_string(index=False) if not selected_daily.empty else "NO_SELECTED_DAILY"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_route_config": summary["selected_route_config"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
