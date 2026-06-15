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

STEP = "GOLD_V3_134_CHAMPION_CHALLENGER_HISTORICAL_ROUTE_REPLAY_AUDIT_ONLY"
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
    if df is None or df.empty:
        return {prefix + k: v for k, v in dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, first_entry_dt="", last_entry_dt="").items()}
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x.get("result_usd"), errors="coerce")
    x = x[x.result_usd.notna()].copy()
    if x.empty:
        return {prefix + k: v for k, v in dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, first_entry_dt="", last_entry_dt="").items()}
    out = dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd),
        sum_result_usd=float(x.result_usd.sum()),
        first_entry_dt=str(x.entry_dt.min()) if "entry_dt" in x.columns and len(x) else "",
        last_entry_dt=str(x.entry_dt.max()) if "entry_dt" in x.columns and len(x) else "",
    )
    return {prefix + k: v for k, v in out.items()}


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), dict(raw_rows=0, unique_entry_times=0, side_conflict_entry_times=0, duplicate_ratio=0.0)
    reps = []
    worst = []
    conflict = 0
    for _, g in df.groupby("entry_dt"):
        if "side" in g.columns and g.side.astype(str).nunique() > 1:
            conflict += 1
        h = g.copy()
        for c in ["feature_score", "score", "ledger_score", "result_usd"]:
            h[c] = pd.to_numeric(h[c], errors="coerce") if c in h.columns else 0.0
        reps.append(h.sort_values(["feature_score", "score", "ledger_score", "result_usd"], ascending=[False, False, False, False]).iloc[0].to_dict())
        worst.append(h.sort_values("result_usd", ascending=True).iloc[0].to_dict())
    n = len(df)
    u = int(df.entry_dt.nunique())
    return pd.DataFrame(reps), pd.DataFrame(worst), dict(raw_rows=int(n), unique_entry_times=u, side_conflict_entry_times=int(conflict), duplicate_ratio=float((n-u)/n) if n else 0.0)


def qualifies(rep: pd.DataFrame, worst: pd.DataFrame, diag: dict, min_trades: int, min_worst_pf: float, min_rep_pf: float, max_dup: float) -> bool:
    rm = metrics(rep, "")
    wm = metrics(worst, "")
    return bool(
        rm["trades"] >= min_trades
        and wm["trades"] >= min_trades
        and rm["profit_factor"] >= min_rep_pf
        and wm["profit_factor"] >= min_worst_pf
        and diag.get("side_conflict_entry_times", 0) == 0
        and diag.get("duplicate_ratio", 1.0) <= max_dup
    )


def month_starts(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    cur = pd.Timestamp(start.year, start.month, 1)
    out = []
    while cur < end:
        out.append(cur)
        cur = cur + pd.offsets.MonthBegin(1)
    return out


def fsum(df: pd.DataFrame) -> float:
    if df.empty or "result_usd" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df.result_usd, errors="coerce").dropna().sum())


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--min-dedup-trades", type=int, default=10)
    ap.add_argument("--min-worst-pf", type=float, default=1.2)
    ap.add_argument("--min-rep-pf", type=float, default=1.5)
    ap.add_argument("--max-duplicate-ratio", type=float, default=0.75)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "134"
    out.mkdir(parents=True, exist_ok=True)

    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    led = load_csv(led_path)
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not champion or not challenger:
        blockers.append({"blocker_id": "missing_champion_or_challenger", "champion": champion, "challenger": challenger})

    rows = []
    route_rep_all = []
    route_worst_all = []
    champion_rep_all = []
    champion_worst_all = []
    challenger_rep_all = []
    challenger_worst_all = []

    if not blockers:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led["result_usd"], errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        start = pd.Timestamp(args.start)
        end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        for m0 in month_starts(start, end):
            m1 = min(m0 + pd.offsets.MonthBegin(1), end)
            mon = str(m0.to_period("M"))
            c_raw = led[(led.policy_key.astype(str) == champion) & (led.entry_dt >= m0) & (led.entry_dt < m1)].copy()
            h_raw = led[(led.policy_key.astype(str) == challenger) & (led.entry_dt >= m0) & (led.entry_dt < m1)].copy()
            c_rep, c_worst, c_diag = dedup(c_raw)
            h_rep, h_worst, h_diag = dedup(h_raw)
            champion_active = len(c_rep) > 0
            challenger_ok = qualifies(h_rep, h_worst, h_diag, args.min_dedup_trades, args.min_worst_pf, args.min_rep_pf, args.max_duplicate_ratio)
            if champion_active:
                chosen = "CHAMPION"
                r_rep = c_rep.copy(); r_worst = c_worst.copy()
            elif challenger_ok:
                chosen = "CHALLENGER"
                r_rep = h_rep.copy(); r_worst = h_worst.copy()
            else:
                chosen = "NO_ROUTE"
                r_rep = pd.DataFrame(); r_worst = pd.DataFrame()
            for df, arr in [(r_rep, route_rep_all), (r_worst, route_worst_all), (c_rep, champion_rep_all), (c_worst, champion_worst_all), (h_rep, challenger_rep_all), (h_worst, challenger_worst_all)]:
                if not df.empty:
                    z = df.copy(); z["route_month"] = mon; arr.append(z)
            rec = dict(
                month=mon,
                chosen_route=chosen,
                champion_active=bool(champion_active),
                challenger_qualified=bool(challenger_ok),
                champion_raw_rows=int(len(c_raw)), champion_dedup_trades=int(len(c_rep)), champion_dup_ratio=float(c_diag.get("duplicate_ratio", 0.0)), champion_side_conflicts=int(c_diag.get("side_conflict_entry_times", 0)),
                challenger_raw_rows=int(len(h_raw)), challenger_dedup_trades=int(len(h_rep)), challenger_dup_ratio=float(h_diag.get("duplicate_ratio", 0.0)), challenger_side_conflicts=int(h_diag.get("side_conflict_entry_times", 0)),
            )
            rec.update(metrics(c_rep, "champion_rep_")); rec.update(metrics(c_worst, "champion_worst_"))
            rec.update(metrics(h_rep, "challenger_rep_")); rec.update(metrics(h_worst, "challenger_worst_"))
            rec.update(metrics(r_rep, "route_rep_")); rec.update(metrics(r_worst, "route_worst_"))
            rows.append(rec)

    monthly = pd.DataFrame(rows)
    save(monthly, out / "gold_v3_134_monthly_route_replay.csv")
    route_rep = pd.concat(route_rep_all, ignore_index=True) if route_rep_all else pd.DataFrame()
    route_worst = pd.concat(route_worst_all, ignore_index=True) if route_worst_all else pd.DataFrame()
    champion_rep = pd.concat(champion_rep_all, ignore_index=True) if champion_rep_all else pd.DataFrame()
    challenger_rep = pd.concat(challenger_rep_all, ignore_index=True) if challenger_rep_all else pd.DataFrame()
    save(route_rep, out / "gold_v3_134_route_rep_rows.csv")
    save(route_worst, out / "gold_v3_134_route_worst_rows.csv")

    route_months = int((monthly.chosen_route != "NO_ROUTE").sum()) if not monthly.empty else 0
    challenger_months = int((monthly.chosen_route == "CHALLENGER").sum()) if not monthly.empty else 0
    champion_months = int((monthly.chosen_route == "CHAMPION").sum()) if not monthly.empty else 0
    negative_route_months = int((monthly.route_worst_sum_result_usd < 0).sum()) if not monthly.empty and "route_worst_sum_result_usd" in monthly.columns else 0
    replaced_active_champion_months = int(((monthly.chosen_route == "CHALLENGER") & (monthly.champion_active)).sum()) if not monthly.empty else 0

    status = BLOCKED if blockers else READY
    if blockers:
        decision = "ROUTE_REPLAY_BLOCKED_INPUT_MISSING"
    elif replaced_active_champion_months > 0:
        decision = "ROUTE_REPLAY_BAD_REPLACED_ACTIVE_CHAMPION"
    elif negative_route_months > 0:
        decision = "ROUTE_REPLAY_REVIEW_NEGATIVE_ROUTE_MONTHS"
    elif challenger_months > 0:
        decision = "ROUTE_REPLAY_READY_CHALLENGER_USED_ONLY_WHEN_CHAMPION_EMPTY"
    else:
        decision = "ROUTE_REPLAY_READY_CHAMPION_ONLY_OR_NO_ROUTE"

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
        "champion_policy_key": champion,
        "challenger_policy_key": challenger,
        "route_months": route_months,
        "champion_months": champion_months,
        "challenger_months": challenger_months,
        "negative_route_months_by_worst_case": negative_route_months,
        "replaced_active_champion_months": replaced_active_champion_months,
        "champion_rep_trades_total": int(len(champion_rep)),
        "challenger_rep_trades_total": int(len(challenger_rep)),
        "route_rep_trades_total": int(len(route_rep)),
        "champion_rep_sum_result_usd_total": fsum(champion_rep),
        "challenger_rep_sum_result_usd_total": fsum(challenger_rep),
        "route_rep_sum_result_usd_total": fsum(route_rep),
        "route_worst_sum_result_usd_total": fsum(route_worst),
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_134_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_134_decision.csv")

    lines = ["GOLD V3 134 PASTE_ME_CHAMPION_CHALLENGER_HISTORICAL_ROUTE_REPLAY_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "MONTHLY_ROUTE_REPLAY", monthly.to_string(index=False) if not monthly.empty else "NO_MONTHLY_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
