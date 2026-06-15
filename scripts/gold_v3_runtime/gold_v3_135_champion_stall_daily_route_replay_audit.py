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

STEP = "GOLD_V3_135_CHAMPION_STALL_DAILY_ROUTE_REPLAY_AUDIT_ONLY"
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
    return pd.DataFrame(reps), pd.DataFrame(worsts), dict(raw_rows=int(n), dedup_trades=u, side_conflict_times=int(side_conflicts), duplicate_ratio=float((n-u)/n) if n else 0.0)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--stall-days", type=int, default=3)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "135"
    out.mkdir(parents=True, exist_ok=True)

    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    led = load_csv(led_path)
    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not champion or not challenger:
        blockers.append({"blocker_id": "missing_champion_or_challenger", "champion": champion, "challenger": challenger})

    daily_rows = []
    route_rep_all, route_worst_all = [], []
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end_exclusive)

    if not blockers:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        led["entry_date"] = led.entry_dt.dt.normalize()
        champ = led[led.policy_key.astype(str) == champion].copy()
        chal = led[led.policy_key.astype(str) == challenger].copy()
        last_champion_date = None
        for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
            c_raw = champ[champ.entry_date == day].copy()
            h_raw = chal[chal.entry_date == day].copy()
            c_rep, c_worst, c_diag = dedup(c_raw)
            h_rep, h_worst, h_diag = dedup(h_raw)
            if not c_rep.empty:
                chosen = "CHAMPION"
                last_champion_date = day
                r_rep, r_worst = c_rep, c_worst
            else:
                days_since = None if last_champion_date is None else int((day - last_champion_date).days)
                if days_since is not None and days_since >= args.stall_days and not h_rep.empty and h_diag.get("side_conflict_times", 0) == 0:
                    chosen = "CHALLENGER"
                    r_rep, r_worst = h_rep, h_worst
                else:
                    chosen = "NO_ROUTE"
                    r_rep, r_worst = pd.DataFrame(), pd.DataFrame()
            if not r_rep.empty:
                z = r_rep.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; route_rep_all.append(z)
            if not r_worst.empty:
                z = r_worst.copy(); z["route_day"] = str(day.date()); z["chosen_route"] = chosen; route_worst_all.append(z)
            days_since = None if last_champion_date is None else int((day - last_champion_date).days)
            rec = dict(
                date=str(day.date()),
                chosen_route=chosen,
                days_since_last_champion="" if days_since is None else days_since,
                champion_raw_rows=int(len(c_raw)), champion_dedup_trades=int(len(c_rep)), champion_dup_ratio=c_diag.get("duplicate_ratio", 0.0), champion_side_conflicts=c_diag.get("side_conflict_times", 0),
                challenger_raw_rows=int(len(h_raw)), challenger_dedup_trades=int(len(h_rep)), challenger_dup_ratio=h_diag.get("duplicate_ratio", 0.0), challenger_side_conflicts=h_diag.get("side_conflict_times", 0),
            )
            rec.update(metrics(c_rep, "champion_rep_")); rec.update(metrics(h_rep, "challenger_rep_")); rec.update(metrics(r_rep, "route_rep_")); rec.update(metrics(r_worst, "route_worst_"))
            daily_rows.append(rec)

    daily = pd.DataFrame(daily_rows)
    save(daily, out / "gold_v3_135_daily_stall_route_replay.csv")
    route_rep = pd.concat(route_rep_all, ignore_index=True) if route_rep_all else pd.DataFrame()
    route_worst = pd.concat(route_worst_all, ignore_index=True) if route_worst_all else pd.DataFrame()
    save(route_rep, out / "gold_v3_135_route_rep_rows.csv")
    save(route_worst, out / "gold_v3_135_route_worst_rows.csv")

    monthly = pd.DataFrame()
    if not daily.empty:
        d = daily.copy(); d["month"] = pd.to_datetime(d.date).dt.to_period("M").astype(str)
        agg = []
        for m, g in d.groupby("month"):
            rep_m = route_rep[route_rep.route_day.isin(g.date.astype(str))].copy() if not route_rep.empty else pd.DataFrame()
            worst_m = route_worst[route_worst.route_day.isin(g.date.astype(str))].copy() if not route_worst.empty else pd.DataFrame()
            row = dict(month=m, route_days=int((g.chosen_route != "NO_ROUTE").sum()), champion_days=int((g.chosen_route == "CHAMPION").sum()), challenger_days=int((g.chosen_route == "CHALLENGER").sum()), no_route_days=int((g.chosen_route == "NO_ROUTE").sum()))
            row.update(metrics(rep_m, "rep_")); row.update(metrics(worst_m, "worst_")); agg.append(row)
        monthly = pd.DataFrame(agg)
    save(monthly, out / "gold_v3_135_monthly_stall_route_replay.csv")

    challenger_days = int((daily.chosen_route == "CHALLENGER").sum()) if not daily.empty else 0
    champion_days = int((daily.chosen_route == "CHAMPION").sum()) if not daily.empty else 0
    negative_months = int((monthly.worst_sum_result_usd < 0).sum()) if not monthly.empty and "worst_sum_result_usd" in monthly.columns else 0
    june = monthly[monthly.month == "2026-06"].copy() if not monthly.empty and "month" in monthly.columns else pd.DataFrame()

    status = BLOCKED if blockers else READY
    if blockers:
        decision = "STALL_DAILY_ROUTE_REPLAY_BLOCKED_INPUT_MISSING"
    elif negative_months > 0:
        decision = "STALL_DAILY_ROUTE_REPLAY_REVIEW_NEGATIVE_MONTHS"
    elif challenger_days > 0:
        decision = "STALL_DAILY_ROUTE_REPLAY_READY_CHALLENGER_USED_ON_STALL_DAYS"
    else:
        decision = "STALL_DAILY_ROUTE_REPLAY_READY_NO_CHALLENGER_USAGE"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "start": args.start,
        "end_exclusive": args.end_exclusive,
        "stall_days": args.stall_days,
        "champion_policy_key": champion,
        "challenger_policy_key": challenger,
        "champion_route_days": champion_days,
        "challenger_route_days": challenger_days,
        "negative_months_by_worst_case": negative_months,
        "route_rep_trades_total": int(len(route_rep)),
        "route_worst_trades_total": int(len(route_worst)),
        "route_rep_sum_result_usd_total": float(pd.to_numeric(route_rep.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not route_rep.empty else 0.0,
        "route_worst_sum_result_usd_total": float(pd.to_numeric(route_worst.get("result_usd", pd.Series(dtype=float)), errors="coerce").sum()) if not route_worst.empty else 0.0,
        "june_challenger_days": int(june.iloc[0].challenger_days) if not june.empty else 0,
        "june_rep_sum_result_usd": float(june.iloc[0].rep_sum_result_usd) if not june.empty else 0.0,
        "june_worst_sum_result_usd": float(june.iloc[0].worst_sum_result_usd) if not june.empty else 0.0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_135_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_135_decision.csv")
    lines = ["GOLD V3 135 PASTE_ME_CHAMPION_STALL_DAILY_ROUTE_REPLAY_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "MONTHLY_STALL_ROUTE_REPLAY", monthly.to_string(index=False) if not monthly.empty else "NO_MONTHLY_ROWS"]
    lines += ["", "DAILY_STALL_ROUTE_REPLAY_TAIL", daily.tail(40).to_string(index=False) if not daily.empty else "NO_DAILY_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
