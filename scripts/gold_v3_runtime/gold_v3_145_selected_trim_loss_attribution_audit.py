#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_145_SELECTED_TRIM_LOSS_ATTRIBUTION_AUDIT_ONLY"
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


def progress(out_dir: Path, done: int, total: int, label: str, started: float) -> None:
    pct = done / total * 100.0 if total else 100.0
    msg = f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {label} elapsed={time.time()-started:.1f}s"
    print(msg, flush=True)
    (out_dir / "progress.txt").write_text(msg + "\n", encoding="utf-8")
    (out_dir / "progress.json").write_text(json.dumps({"done": done, "total": total, "percent": pct, "label": label, "elapsed_seconds": round(time.time()-started, 1)}, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_trim_config(trim_config: str) -> tuple[str, float, str]:
    # RUNNING_SCORE|feature_score|Q0.7|CHAMPION_ONLY
    parts = str(trim_config).split("|")
    score_col = parts[1] if len(parts) > 1 else "feature_score"
    m = re.search(r"Q([0-9.]+)", str(trim_config))
    q = float(m.group(1)) if m else 0.7
    scope = parts[3] if len(parts) > 3 else "CHAMPION_ONLY"
    return score_col, q, scope


def apply_score_trim(events: pd.DataFrame, score_col: str, q: float, scope: str, min_history_events: int) -> pd.DataFrame:
    e = events.copy()
    e["entry_dt"] = pd.to_datetime(e["entry_dt"], errors="coerce")
    e = e[e.entry_dt.notna()].sort_values("entry_dt").reset_index(drop=True)
    kept, ths, hist = [], [], []
    for r in e.itertuples(index=False):
        route = str(getattr(r, "chosen_route"))
        applies = scope == "ALL" or (scope == "CHALLENGER_ONLY" and route == "CHALLENGER") or (scope == "CHAMPION_ONLY" and route == "CHAMPION")
        score = getattr(r, score_col) if hasattr(r, score_col) else math.nan
        score = float(score) if pd.notna(score) else math.nan
        if not applies:
            kept.append(True); ths.append(math.nan); continue
        clean = pd.Series(hist).dropna()
        th = float(clean.quantile(q)) if len(clean) >= min_history_events else math.nan
        keep = True if math.isnan(th) else (pd.notna(score) and score >= th)
        kept.append(bool(keep)); ths.append(th); hist.append(score)
    e["score_trim_score_col"] = score_col
    e["score_trim_q"] = q
    e["score_trim_scope"] = scope
    e["score_trim_threshold"] = ths
    e["kept_after_score_trim"] = kept
    e["chosen_route_score_trimmed"] = e["chosen_route"].where(e["kept_after_score_trim"], "NO_ROUTE")
    e["rep_result_usd_trimmed"] = pd.to_numeric(e.get("rep_result_usd", 0), errors="coerce").fillna(0).where(e["kept_after_score_trim"], 0.0)
    e["worst_result_usd_trimmed"] = pd.to_numeric(e.get("worst_result_usd", 0), errors="coerce").fillna(0).where(e["kept_after_score_trim"], 0.0)
    return e


def monthly_attribution(trimmed: pd.DataFrame, trim_config: str) -> pd.DataFrame:
    x = trimmed.copy()
    x["date"] = pd.to_datetime(x["date"], errors="coerce")
    x = x[x.date.notna()].copy()
    x["month"] = x.date.dt.to_period("M").astype(str)
    rows = []
    for m, g in x.groupby("month"):
        kept = g[g.kept_after_score_trim].copy()
        for_route = {}
        for route in ["CHAMPION", "CHALLENGER", "NO_ROUTE"]:
            rg = g[g.chosen_route_score_trimmed.astype(str) == route].copy()
            for_route[f"{route.lower()}_events"] = int(len(rg))
            for_route[f"{route.lower()}_rep_sum"] = float(pd.to_numeric(rg.get("rep_result_usd_trimmed", 0), errors="coerce").fillna(0).sum())
            for_route[f"{route.lower()}_worst_sum"] = float(pd.to_numeric(rg.get("worst_result_usd_trimmed", 0), errors="coerce").fillna(0).sum())
        row = dict(
            trim_config=trim_config,
            month=m,
            route_events=int((g.chosen_route_score_trimmed.astype(str) != "NO_ROUTE").sum()),
            dropped_events=int((~g.kept_after_score_trim).sum()),
            rep_sum_result_usd=float(pd.to_numeric(g.rep_result_usd_trimmed, errors="coerce").fillna(0).sum()),
            worst_sum_result_usd=float(pd.to_numeric(g.worst_result_usd_trimmed, errors="coerce").fillna(0).sum()),
            negative_month=bool(pd.to_numeric(g.worst_result_usd_trimmed, errors="coerce").fillna(0).sum() < 0),
        )
        row.update(for_route)
        if row["worst_sum_result_usd"] < 0:
            if row["champion_worst_sum"] < 0 and row["challenger_worst_sum"] < 0:
                cause = "BOTH_CHAMPION_AND_CHALLENGER"
            elif row["champion_worst_sum"] < 0:
                cause = "CHAMPION_DOMINANT"
            elif row["challenger_worst_sum"] < 0:
                cause = "CHALLENGER_DOMINANT"
            else:
                cause = "MIXED_OFFSET"
        else:
            cause = "NON_NEGATIVE"
        row["negative_month_cause"] = cause
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--min-history-events", type=int, default=30)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "145"
    out.mkdir(parents=True, exist_ok=True)
    progress(out, 0, 1, "START", t0)

    s144 = read_json(root / "144" / "gold_v3_144_summary.json")
    trim_config = str(s144.get("selected_trim_config", ""))
    events_path = root / "143" / "gold_v3_143_base_142_selected_events_with_scores.csv"
    events = load_csv(events_path)
    blockers = []
    if events.empty:
        blockers.append({"blocker_id": "missing_143_base_events", "path": str(events_path)})
    if not trim_config:
        blockers.append({"blocker_id": "missing_144_selected_trim_config"})

    trimmed = pd.DataFrame(); monthly = pd.DataFrame(); neg_months = pd.DataFrame(); neg_events = pd.DataFrame(); route_totals = pd.DataFrame()
    if not blockers:
        score_col, q, scope = parse_trim_config(trim_config)
        if score_col not in events.columns:
            blockers.append({"blocker_id": "score_col_missing_in_base_events", "score_col": score_col})
        else:
            trimmed = apply_score_trim(events, score_col, q, scope, args.min_history_events)
            monthly = monthly_attribution(trimmed, trim_config)
            neg_months = monthly[monthly.negative_month].copy()
            kept = trimmed[trimmed.kept_after_score_trim].copy()
            neg_events = kept[pd.to_numeric(kept.worst_result_usd_trimmed, errors="coerce").fillna(0) < 0].copy()
            if not neg_events.empty:
                neg_events["month"] = pd.to_datetime(neg_events.date).dt.to_period("M").astype(str)
                neg_events = neg_events.sort_values("worst_result_usd_trimmed", ascending=True)
            totals = []
            for route, g in trimmed.groupby(trimmed.chosen_route_score_trimmed.astype(str)):
                vals = pd.to_numeric(g.worst_result_usd_trimmed, errors="coerce").fillna(0)
                totals.append(dict(
                    chosen_route_score_trimmed=route,
                    events=int(len(g)),
                    rep_sum_result_usd=float(pd.to_numeric(g.rep_result_usd_trimmed, errors="coerce").fillna(0).sum()),
                    worst_sum_result_usd=float(vals.sum()),
                    worst_pf=pf(vals[vals != 0]),
                    negative_events=int((vals < 0).sum()),
                ))
            route_totals = pd.DataFrame(totals)
            save(trimmed, out / "gold_v3_145_selected_trim_reconstructed_events.csv")
            save(monthly, out / "gold_v3_145_selected_trim_monthly_attribution.csv")
            save(neg_months, out / "gold_v3_145_negative_months_attribution.csv")
            save(neg_events, out / "gold_v3_145_negative_kept_events.csv")
            save(route_totals, out / "gold_v3_145_route_totals.csv")

    status = BLOCKED if blockers else READY
    if blockers:
        decision = "SELECTED_TRIM_LOSS_ATTRIBUTION_BLOCKED_INPUT_MISSING"
    elif not neg_months.empty:
        cc = neg_months.negative_month_cause.value_counts().to_dict()
        if cc.get("CHALLENGER_DOMINANT", 0) >= cc.get("CHAMPION_DOMINANT", 0):
            decision = "NEGATIVE_MONTHS_REMAIN_MAINLY_CHALLENGER_AFTER_CHAMPION_TRIM"
        else:
            decision = "NEGATIVE_MONTHS_REMAIN_MAINLY_CHAMPION_AFTER_CHAMPION_TRIM"
    else:
        decision = "NO_NEGATIVE_MONTHS_AFTER_SELECTED_TRIM"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "source_144_decision": s144.get("decision", ""),
        "source_144_selected_trim_config": trim_config,
        "progress_total_configs": 1,
        "progress_completed_configs": 1 if not blockers else 0,
        "progress_output": str(out / "progress.txt"),
        "kept_route_events": int((trimmed.chosen_route_score_trimmed.astype(str) != "NO_ROUTE").sum()) if not trimmed.empty else 0,
        "kept_champion_events": int((trimmed.chosen_route_score_trimmed.astype(str) == "CHAMPION").sum()) if not trimmed.empty else 0,
        "kept_challenger_events": int((trimmed.chosen_route_score_trimmed.astype(str) == "CHALLENGER").sum()) if not trimmed.empty else 0,
        "dropped_events": int((~trimmed.kept_after_score_trim).sum()) if not trimmed.empty else 0,
        "worst_sum_result_usd": float(monthly.worst_sum_result_usd.sum()) if not monthly.empty else 0.0,
        "worst_pf": pf(trimmed.worst_result_usd_trimmed[trimmed.kept_after_score_trim]) if not trimmed.empty else 0.0,
        "negative_month_count": int(len(neg_months)) if not neg_months.empty else 0,
        "negative_kept_event_count": int(len(neg_events)) if not neg_events.empty else 0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    progress(out, 1, 1, "DONE", t0)
    (out / "gold_v3_145_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_145_decision.csv")
    lines = ["GOLD V3 145 PASTE_ME_SELECTED_TRIM_LOSS_ATTRIBUTION_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "ROUTE_TOTALS", route_totals.to_string(index=False) if not route_totals.empty else "NO_ROUTE_TOTALS"]
    lines += ["", "NEGATIVE_MONTHS_ATTRIBUTION", neg_months.to_string(index=False) if not neg_months.empty else "NO_NEGATIVE_MONTHS"]
    lines += ["", "NEGATIVE_KEPT_EVENTS_TOP40", neg_events.head(40).to_string(index=False) if not neg_events.empty else "NO_NEGATIVE_KEPT_EVENTS"]
    lines += ["", "MONTHLY_ATTRIBUTION", monthly.to_string(index=False) if not monthly.empty else "NO_MONTHLY_ATTRIBUTION"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
