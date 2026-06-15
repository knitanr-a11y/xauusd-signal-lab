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

STEP = "GOLD_V3_144_RECENCY_PRESERVING_SCORE_TRIM_SELECTION_AUDIT_ONLY"
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


def progress(out_dir: Path, done: int, total: int, label: str, started: float) -> None:
    pct = (done / total * 100.0) if total else 100.0
    msg = f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {label} elapsed={time.time()-started:.1f}s"
    print(msg, flush=True)
    (out_dir / "progress.txt").write_text(msg + "\n", encoding="utf-8")
    (out_dir / "progress.json").write_text(json.dumps({"done": done, "total": total, "percent": pct, "label": label, "elapsed_seconds": round(time.time()-started, 1)}, ensure_ascii=False, indent=2), encoding="utf-8")


def num(df: pd.DataFrame, col: str, default=0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series([default] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--min-route-events", type=int, default=150)
    ap.add_argument("--min-challenger-events", type=int, default=50)
    ap.add_argument("--min-june-route-events", type=int, default=5)
    ap.add_argument("--min-june-worst", type=float, default=1.0)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "144"
    out.mkdir(parents=True, exist_ok=True)

    s143 = read_json(root / "143" / "gold_v3_143_summary.json")
    summary_path = root / "143" / "gold_v3_143_running_score_trim_summary.csv"
    monthly_path = root / "143" / "gold_v3_143_running_score_trim_monthly_all.csv"
    events_path = root / "143" / "gold_v3_143_selected_score_trim_events.csv"
    summary = load_csv(summary_path)
    monthly = load_csv(monthly_path)
    blockers = []
    if summary.empty:
        blockers.append({"blocker_id": "missing_143_score_trim_summary", "path": str(summary_path)})
    if monthly.empty:
        blockers.append({"blocker_id": "missing_143_score_trim_monthly_all", "path": str(monthly_path)})
    required = {"trim_config", "route_events", "challenger_events", "worst_sum_result_usd", "worst_pf", "negative_months_worst", "june_worst_sum_result_usd"}
    if not summary.empty and not required.issubset(set(summary.columns)):
        blockers.append({"blocker_id": "summary_missing_required_columns", "missing": sorted(required - set(summary.columns))})

    ranked = pd.DataFrame()
    selected_monthly = pd.DataFrame()
    selected_events = pd.DataFrame()
    baseline = {}
    completed = 0
    total = int(len(summary)) if not summary.empty else 0
    progress(out, 0, total, "START", t0)

    if not blockers:
        x = summary.copy()
        for c in ["route_events", "champion_events", "challenger_events", "dropped_events", "rep_sum_result_usd", "worst_sum_result_usd", "rep_pf", "worst_pf", "negative_months_worst", "june_worst_sum_result_usd", "june_rep_sum_result_usd"]:
            x[c] = num(x, c)
        base_rows = x[x.trim_config.astype(str) == "BASELINE_NO_TRIM"].copy()
        if base_rows.empty:
            base_rows = x.head(1).copy()
        b = base_rows.iloc[0]
        baseline = {
            "baseline_trim_config": str(b.trim_config),
            "baseline_route_events": int(b.route_events),
            "baseline_challenger_events": int(b.challenger_events),
            "baseline_worst_sum_result_usd": float(b.worst_sum_result_usd),
            "baseline_worst_pf": float(b.worst_pf),
            "baseline_negative_months_worst": int(b.negative_months_worst),
            "baseline_june_worst_sum_result_usd": float(b.june_worst_sum_result_usd),
        }
        # Bring June route/challenger/dropped event counts from monthly table, because 143 summary intentionally only carried June PnL.
        m = monthly.copy()
        for c in ["route_events", "champion_events", "challenger_events", "dropped_events", "rep_sum_result_usd", "worst_sum_result_usd"]:
            m[c] = num(m, c)
        june = m[m.month.astype(str) == "2026-06"].copy() if "month" in m.columns else pd.DataFrame()
        june_cols = ["trim_config", "route_events", "champion_events", "challenger_events", "dropped_events", "rep_sum_result_usd", "worst_sum_result_usd"]
        if not june.empty:
            june = june[june_cols].rename(columns={
                "route_events": "june_route_events",
                "champion_events": "june_champion_events",
                "challenger_events": "june_challenger_events",
                "dropped_events": "june_dropped_events",
                "rep_sum_result_usd": "june_month_rep_sum_result_usd",
                "worst_sum_result_usd": "june_month_worst_sum_result_usd",
            })
            x = x.merge(june, on="trim_config", how="left")
        else:
            x["june_route_events"] = 0
            x["june_challenger_events"] = 0
            x["june_month_worst_sum_result_usd"] = 0.0
        for c in ["june_route_events", "june_champion_events", "june_challenger_events", "june_dropped_events", "june_month_rep_sum_result_usd", "june_month_worst_sum_result_usd"]:
            x[c] = num(x, c)

        strict = (
            (x.trim_config.astype(str) != "BASELINE_NO_TRIM")
            & (x.route_events >= args.min_route_events)
            & (x.challenger_events >= args.min_challenger_events)
            & (x.june_route_events >= args.min_june_route_events)
            & (x.june_month_worst_sum_result_usd >= args.min_june_worst)
            & (x.negative_months_worst <= baseline["baseline_negative_months_worst"])
            & (x.worst_sum_result_usd >= baseline["baseline_worst_sum_result_usd"])
        )
        relaxed = (
            (x.trim_config.astype(str) != "BASELINE_NO_TRIM")
            & (x.route_events >= args.min_route_events)
            & (x.june_route_events >= args.min_june_route_events)
            & (x.june_month_worst_sum_result_usd >= 0)
            & (x.negative_months_worst <= baseline["baseline_negative_months_worst"])
            & (x.worst_sum_result_usd >= baseline["baseline_worst_sum_result_usd"])
        )
        x["constraint_tier"] = "REJECTED"
        x.loc[relaxed, "constraint_tier"] = "RELAXED_PASS"
        x.loc[strict, "constraint_tier"] = "STRICT_PASS"
        x["recency_preserving_score"] = (
            x.worst_sum_result_usd
            + x.worst_pf * 100.0
            - x.negative_months_worst * 400.0
            + x.june_month_worst_sum_result_usd * 1.0
            + x.june_route_events * 5.0
            - x.dropped_events * 0.1
        )
        tier_order = {"STRICT_PASS": 0, "RELAXED_PASS": 1, "REJECTED": 2}
        x["tier_order"] = x.constraint_tier.map(tier_order).fillna(9)
        ranked = x.sort_values(["tier_order", "negative_months_worst", "worst_sum_result_usd", "worst_pf", "june_month_worst_sum_result_usd"], ascending=[True, True, False, False, False]).reset_index(drop=True)
        for idx, r in ranked.iterrows():
            completed = idx + 1
            progress(out, completed, total, str(r.trim_config), t0)
        save(ranked, out / "gold_v3_144_recency_preserving_score_trim_ranking.csv")
        if not ranked.empty:
            sel_key = str(ranked.iloc[0].trim_config)
            selected_monthly = monthly[monthly.trim_config.astype(str) == sel_key].copy()
            # events file in 143 contains only 143's original selected config, so do not claim selected events unless it matches.
            ev = load_csv(events_path)
            if not ev.empty and s143.get("selected_trim_config", "") == sel_key:
                selected_events = ev.copy()
            save(selected_monthly, out / "gold_v3_144_selected_recency_preserving_monthly.csv")
            save(selected_events, out / "gold_v3_144_selected_recency_preserving_events_if_available.csv")

    selected = ranked.head(1).copy() if not ranked.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "RECENCY_PRESERVING_SELECTION_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "RECENCY_PRESERVING_SELECTION_READY_NO_CONFIG"
    elif str(selected.iloc[0].constraint_tier) == "STRICT_PASS" and int(selected.iloc[0].negative_months_worst) == 0:
        decision = "RECENCY_PRESERVING_SELECTION_READY_NO_NEGATIVE_WORST_MONTHS"
    elif str(selected.iloc[0].constraint_tier) == "STRICT_PASS":
        decision = "RECENCY_PRESERVING_SELECTION_REVIEW_STRICT_PASS_NEGATIVE_MONTHS_REMAIN"
    elif str(selected.iloc[0].constraint_tier) == "RELAXED_PASS":
        decision = "RECENCY_PRESERVING_SELECTION_REVIEW_RELAXED_PASS_ONLY"
    else:
        decision = "RECENCY_PRESERVING_SELECTION_NO_ACCEPTABLE_TRIM_FOUND"

    summary_out = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "source_143_decision": s143.get("decision", ""),
        "source_143_selected_trim_config": s143.get("selected_trim_config", ""),
        "selection_reason": "Do not select trims that erase June/recency; require June route presence and baseline non-degradation.",
        "min_route_events": args.min_route_events,
        "min_challenger_events": args.min_challenger_events,
        "min_june_route_events": args.min_june_route_events,
        "min_june_worst": args.min_june_worst,
        **baseline,
        "progress_total_configs": total,
        "progress_completed_configs": completed,
        "progress_output": str(out / "progress.txt"),
        "selected_trim_config": str(selected.iloc[0].trim_config) if not selected.empty else "",
        "selected_constraint_tier": str(selected.iloc[0].constraint_tier) if not selected.empty else "",
        "selected_score_col": str(selected.iloc[0].score_col) if not selected.empty and "score_col" in selected.columns else "",
        "selected_q": float(selected.iloc[0].q) if not selected.empty and "q" in selected.columns else 0.0,
        "selected_scope": str(selected.iloc[0].scope) if not selected.empty and "scope" in selected.columns else "",
        "selected_route_events": int(selected.iloc[0].route_events) if not selected.empty else 0,
        "selected_champion_events": int(selected.iloc[0].champion_events) if not selected.empty else 0,
        "selected_challenger_events": int(selected.iloc[0].challenger_events) if not selected.empty else 0,
        "selected_dropped_events": int(selected.iloc[0].dropped_events) if not selected.empty else 0,
        "selected_worst_sum_result_usd": float(selected.iloc[0].worst_sum_result_usd) if not selected.empty else 0.0,
        "selected_worst_pf": float(selected.iloc[0].worst_pf) if not selected.empty else 0.0,
        "selected_negative_months_worst": int(selected.iloc[0].negative_months_worst) if not selected.empty else 0,
        "selected_june_route_events": int(selected.iloc[0].june_route_events) if not selected.empty else 0,
        "selected_june_challenger_events": int(selected.iloc[0].june_challenger_events) if not selected.empty else 0,
        "selected_june_worst_sum_result_usd": float(selected.iloc[0].june_month_worst_sum_result_usd) if not selected.empty else 0.0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (out / "gold_v3_144_summary.json").write_text(json.dumps(summary_out | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary_out]), out / "gold_v3_144_decision.csv")
    lines = ["GOLD V3 144 PASTE_ME_RECENCY_PRESERVING_SCORE_TRIM_SELECTION_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary_out.items()]
    lines += ["", "TOP30_RECENCY_PRESERVING_RANKING", ranked.head(30).to_string(index=False) if not ranked.empty else "NO_RANKING_ROWS"]
    lines += ["", "SELECTED_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_trim_config": summary_out["selected_trim_config"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
