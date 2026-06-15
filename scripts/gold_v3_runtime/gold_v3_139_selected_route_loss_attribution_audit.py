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

STEP = "GOLD_V3_139_SELECTED_ROUTE_LOSS_ATTRIBUTION_AUDIT_ONLY"
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


def metrics_from_daily(g: pd.DataFrame, prefix: str) -> dict:
    if g is None or g.empty:
        return {
            prefix + "days": 0,
            prefix + "rep_trades": 0,
            prefix + "worst_trades": 0,
            prefix + "rep_sum_result_usd": 0.0,
            prefix + "worst_sum_result_usd": 0.0,
            prefix + "negative_worst_days": 0,
            prefix + "negative_rep_days": 0,
        }
    for c in ["rep_trades", "worst_trades", "rep_sum_result_usd", "worst_sum_result_usd"]:
        if c in g.columns:
            g[c] = pd.to_numeric(g[c], errors="coerce").fillna(0)
    return {
        prefix + "days": int(len(g)),
        prefix + "rep_trades": int(g.get("rep_trades", pd.Series(dtype=float)).sum()),
        prefix + "worst_trades": int(g.get("worst_trades", pd.Series(dtype=float)).sum()),
        prefix + "rep_sum_result_usd": float(g.get("rep_sum_result_usd", pd.Series(dtype=float)).sum()),
        prefix + "worst_sum_result_usd": float(g.get("worst_sum_result_usd", pd.Series(dtype=float)).sum()),
        prefix + "negative_worst_days": int((g.get("worst_sum_result_usd", pd.Series(dtype=float)) < 0).sum()),
        prefix + "negative_rep_days": int((g.get("rep_sum_result_usd", pd.Series(dtype=float)) < 0).sum()),
    }


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "139"
    out.mkdir(parents=True, exist_ok=True)

    s138a = read_json(root / "138a" / "gold_v3_138a_summary.json")
    daily_path = root / "138a" / "gold_v3_138a_selected_daily.csv"
    monthly_path = root / "138a" / "gold_v3_138a_selected_monthly.csv"
    daily = load_csv(daily_path)
    monthly = load_csv(monthly_path)
    blockers = []
    if daily.empty:
        blockers.append({"blocker_id": "missing_138a_selected_daily", "path": str(daily_path)})
    if monthly.empty:
        blockers.append({"blocker_id": "missing_138a_selected_monthly", "path": str(monthly_path)})

    route_by_month = pd.DataFrame()
    negative_months = pd.DataFrame()
    negative_days = pd.DataFrame()
    route_totals = pd.DataFrame()
    status = BLOCKED if blockers else READY

    if not blockers:
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
        daily = daily[daily.date.notna()].copy()
        daily["month"] = daily.date.dt.to_period("M").astype(str)
        for c in ["rep_sum_result_usd", "worst_sum_result_usd", "rep_trades", "worst_trades"]:
            if c in daily.columns:
                daily[c] = pd.to_numeric(daily[c], errors="coerce").fillna(0)
        rows = []
        for m, g in daily.groupby("month"):
            row = {"month": m}
            row.update(metrics_from_daily(g[g.chosen_route.astype(str) == "CHAMPION"].copy(), "champion_"))
            row.update(metrics_from_daily(g[g.chosen_route.astype(str) == "CHALLENGER"].copy(), "challenger_"))
            row.update(metrics_from_daily(g[g.chosen_route.astype(str) == "NO_ROUTE"].copy(), "no_route_"))
            row["month_worst_sum_result_usd"] = row["champion_worst_sum_result_usd"] + row["challenger_worst_sum_result_usd"]
            row["month_rep_sum_result_usd"] = row["champion_rep_sum_result_usd"] + row["challenger_rep_sum_result_usd"]
            if row["month_worst_sum_result_usd"] < 0:
                if row["champion_worst_sum_result_usd"] < 0 and row["challenger_worst_sum_result_usd"] < 0:
                    cause = "BOTH_CHAMPION_AND_CHALLENGER"
                elif row["champion_worst_sum_result_usd"] < 0:
                    cause = "CHAMPION_DOMINANT"
                elif row["challenger_worst_sum_result_usd"] < 0:
                    cause = "CHALLENGER_DOMINANT"
                else:
                    cause = "MIXED_SMALL"
            else:
                cause = "NON_NEGATIVE"
            row["negative_month_cause"] = cause
            rows.append(row)
        route_by_month = pd.DataFrame(rows)
        negative_months = route_by_month[route_by_month.month_worst_sum_result_usd < 0].copy()
        negative_days = daily[(daily.chosen_route.astype(str) != "NO_ROUTE") & (daily.worst_sum_result_usd < 0)].copy()
        if not negative_days.empty:
            negative_days = negative_days.sort_values("worst_sum_result_usd", ascending=True)
        route_totals_rows = []
        for route, g in daily.groupby(daily.chosen_route.astype(str)):
            row = {"chosen_route": route}
            row.update(metrics_from_daily(g.copy(), ""))
            route_totals_rows.append(row)
        route_totals = pd.DataFrame(route_totals_rows)

        save(route_by_month, out / "gold_v3_139_route_loss_attribution_by_month.csv")
        save(negative_months, out / "gold_v3_139_negative_months.csv")
        save(negative_days, out / "gold_v3_139_negative_worst_days.csv")
        save(route_totals, out / "gold_v3_139_route_totals.csv")

    if blockers:
        decision = "LOSS_ATTRIBUTION_BLOCKED_INPUT_MISSING"
    elif not negative_months.empty:
        cause_counts = negative_months.negative_month_cause.value_counts().to_dict()
        if cause_counts.get("CHAMPION_DOMINANT", 0) >= cause_counts.get("CHALLENGER_DOMINANT", 0):
            decision = "NEGATIVE_MONTHS_REMAIN_MAINLY_CHAMPION_ATTRIBUTION"
        else:
            decision = "NEGATIVE_MONTHS_REMAIN_MAINLY_CHALLENGER_ATTRIBUTION"
    else:
        decision = "NO_NEGATIVE_MONTHS_IN_SELECTED_ROUTE"

    champion_worst_sum = 0.0
    challenger_worst_sum = 0.0
    champion_neg_months = 0
    challenger_neg_months = 0
    if not route_by_month.empty:
        champion_worst_sum = float(route_by_month.champion_worst_sum_result_usd.sum())
        challenger_worst_sum = float(route_by_month.challenger_worst_sum_result_usd.sum())
        champion_neg_months = int((route_by_month.champion_worst_sum_result_usd < 0).sum())
        challenger_neg_months = int((route_by_month.challenger_worst_sum_result_usd < 0).sum())

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
        "negative_month_count": int(len(negative_months)) if not negative_months.empty else 0,
        "negative_worst_day_count": int(len(negative_days)) if not negative_days.empty else 0,
        "champion_worst_sum_result_usd_total": champion_worst_sum,
        "challenger_worst_sum_result_usd_total": challenger_worst_sum,
        "champion_negative_month_count": champion_neg_months,
        "challenger_negative_month_count": challenger_neg_months,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_139_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_139_decision.csv")

    lines = ["GOLD V3 139 PASTE_ME_SELECTED_ROUTE_LOSS_ATTRIBUTION_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "ROUTE_TOTALS", route_totals.to_string(index=False) if not route_totals.empty else "NO_ROUTE_TOTALS"]
    lines += ["", "NEGATIVE_MONTHS", negative_months.to_string(index=False) if not negative_months.empty else "NO_NEGATIVE_MONTHS"]
    lines += ["", "WORST_NEGATIVE_DAYS_TOP30", negative_days.head(30).to_string(index=False) if not negative_days.empty else "NO_NEGATIVE_DAYS"]
    lines += ["", "ROUTE_BY_MONTH", route_by_month.to_string(index=False) if not route_by_month.empty else "NO_ROUTE_BY_MONTH"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
