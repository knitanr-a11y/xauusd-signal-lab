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

STEP = "GOLD_V3_143_RUNNING_SCORE_TRIM_AUDIT_ONLY"
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


def metrics_from_values(vals, prefix: str = "") -> dict:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        base = dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0)
    else:
        base = dict(
            trades=int(len(a)),
            wins=int((a > 0).sum()),
            losses=int((a < 0).sum()),
            win_rate=float((a > 0).mean()),
            profit_factor=pf(a),
            sum_result_usd=float(a.sum()),
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
    vals, out = [], {}
    for r in d.itertuples(index=False):
        day = r[0]; v = r[1]
        hist = pd.Series(vals).dropna()
        th = float(hist.quantile(q)) if len(hist) >= min_history_days else math.nan
        out[day] = bool(pd.notna(v) and pd.notna(th) and float(v) >= th)
        vals.append(v)
    return out


def parse_142_config(s142: dict) -> dict:
    key = str(s142.get("selected_route_config", "INTRADAY_CAP|d1_atr28|Q0.5|BLOCK_CHAMPION_GE_3|CHAL_RUNNING_GE_3|CHAL_CAP_1"))
    parts = key.split("|")
    vol_col = parts[1] if len(parts) > 1 else "d1_atr28"
    q = 0.5
    m = re.search(r"Q([0-9.]+)", key)
    if m:
        q = float(m.group(1))
    return dict(
        route_config=key,
        vol_col=vol_col,
        vol_q=q,
        champion_block_after=int(s142.get("selected_champion_block_after", 3)),
        challenger_running_min=int(s142.get("selected_challenger_running_min", 3)),
        challenger_daily_cap=int(s142.get("selected_challenger_daily_cap", 1)),
    )


def progress(out_dir: Path, done: int, total: int, label: str, started: float) -> None:
    pct = (done / total * 100.0) if total else 100.0
    msg = f"[PROGRESS] config {done}/{total} ({pct:.1f}%) {label} elapsed={time.time()-started:.1f}s"
    print(msg, flush=True)
    (out_dir / "progress.txt").write_text(msg + "\n", encoding="utf-8")
    (out_dir / "progress.json").write_text(json.dumps({"done": done, "total": total, "percent": pct, "label": label, "elapsed_seconds": round(time.time()-started, 1)}, ensure_ascii=False, indent=2), encoding="utf-8")


def build_base_events(led: pd.DataFrame, champion: str, challenger: str, start: pd.Timestamp, end: pd.Timestamp, cfg: dict, min_hist: int) -> pd.DataFrame:
    hv_map = daily_high_vol_map(led, cfg["vol_col"], cfg["vol_q"], min_hist)
    champ = led[led.policy_key.astype(str) == champion].copy()
    chal = led[led.policy_key.astype(str) == challenger].copy()
    rows = []
    for day in pd.date_range(start=start.normalize(), end=(end - pd.Timedelta(days=1)).normalize(), freq="D"):
        cday = champ[champ.entry_date == day].copy()
        hday = chal[chal.entry_date == day].copy()
        times = sorted(set(cday.entry_dt.tolist()) | set(hday.entry_dt.tolist()))
        c_seen = 0; h_seen = 0; h_taken = 0
        is_hv = bool(hv_map.get(day, False))
        for t in times:
            cg = cday[cday.entry_dt == t].copy()
            hg = hday[hday.entry_dt == t].copy()
            c_rep, c_worst, _ = dedup_at_entry(cg)
            h_rep, h_worst, hdiag = dedup_at_entry(hg)
            has_c = c_rep is not None
            has_h = h_rep is not None
            chosen = "NO_ROUTE"; rep = None; worst = None
            if has_c:
                c_seen += 1
                if c_seen < cfg["champion_block_after"]:
                    chosen = "CHAMPION"; rep = c_rep; worst = c_worst
            elif has_h:
                h_seen += 1
                if is_hv and h_seen >= cfg["challenger_running_min"] and h_taken < cfg["challenger_daily_cap"] and not hdiag.get("side_conflict", False):
                    chosen = "CHALLENGER"; rep = h_rep; worst = h_worst; h_taken += 1
            if rep is None:
                continue
            row = dict(
                date=str(day.date()),
                entry_dt=pd.Timestamp(t),
                chosen_route=chosen,
                is_high_vol=is_hv,
                champion_running_count=c_seen,
                challenger_running_count=h_seen,
                challenger_taken_count=h_taken,
                rep_result_usd=float(pd.to_numeric(pd.Series([rep.get("result_usd")]), errors="coerce").iloc[0]),
                worst_result_usd=float(pd.to_numeric(pd.Series([worst.get("result_usd")]), errors="coerce").iloc[0]),
            )
            for c in ["feature_score", "score", "ledger_score"]:
                row[c] = float(pd.to_numeric(pd.Series([rep.get(c)]), errors="coerce").fillna(math.nan).iloc[0]) if c in rep else math.nan
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    score_cols = [c for c in ["feature_score", "score", "ledger_score"] if c in out.columns]
    if score_cols:
        out["max_score"] = out[score_cols].max(axis=1, skipna=True)
    out = out.sort_values("entry_dt").reset_index(drop=True)
    return out


def apply_score_trim(events: pd.DataFrame, score_col: str, q: float, scope: str, min_history_events: int) -> pd.DataFrame:
    e = events.copy().sort_values("entry_dt").reset_index(drop=True)
    kept = []
    thresholds = []
    hist = []
    for r in e.itertuples(index=False):
        route = str(getattr(r, "chosen_route"))
        applies = scope == "ALL" or (scope == "CHALLENGER_ONLY" and route == "CHALLENGER") or (scope == "CHAMPION_ONLY" and route == "CHAMPION")
        score = getattr(r, score_col)
        score = float(score) if pd.notna(score) else math.nan
        if not applies:
            kept.append(True); thresholds.append(math.nan); continue
        clean = pd.Series(hist).dropna()
        th = float(clean.quantile(q)) if len(clean) >= min_history_events else math.nan
        ok = True if math.isnan(th) else (pd.notna(score) and score >= th)
        kept.append(bool(ok)); thresholds.append(th)
        hist.append(score)
    e["score_trim_score_col"] = score_col
    e["score_trim_q"] = q
    e["score_trim_scope"] = scope
    e["score_trim_threshold"] = thresholds
    e["kept_after_score_trim"] = kept
    e["chosen_route_score_trimmed"] = e["chosen_route"].where(e["kept_after_score_trim"], "NO_ROUTE")
    e["rep_result_usd_trimmed"] = e["rep_result_usd"].where(e["kept_after_score_trim"], 0.0)
    e["worst_result_usd_trimmed"] = e["worst_result_usd"].where(e["kept_after_score_trim"], 0.0)
    return e


def summarize_trim(trimmed: pd.DataFrame, cfg_label: str, score_col: str, q: float, scope: str) -> tuple[dict, pd.DataFrame]:
    x = trimmed.copy()
    x["month"] = pd.to_datetime(x["date"]).dt.to_period("M").astype(str)
    mrows = []
    for m, g in x.groupby("month"):
        mrows.append(dict(
            trim_config=cfg_label,
            month=m,
            route_events=int((g.chosen_route_score_trimmed != "NO_ROUTE").sum()),
            champion_events=int((g.chosen_route_score_trimmed == "CHAMPION").sum()),
            challenger_events=int((g.chosen_route_score_trimmed == "CHALLENGER").sum()),
            dropped_events=int((~g.kept_after_score_trim).sum()),
            rep_sum_result_usd=float(g.rep_result_usd_trimmed.sum()),
            worst_sum_result_usd=float(g.worst_result_usd_trimmed.sum()),
        ))
    mon = pd.DataFrame(mrows)
    june = mon[mon.month == "2026-06"].copy() if not mon.empty else pd.DataFrame()
    return dict(
        trim_config=cfg_label,
        score_col=score_col,
        q=q,
        scope=scope,
        route_events=int((x.chosen_route_score_trimmed != "NO_ROUTE").sum()),
        champion_events=int((x.chosen_route_score_trimmed == "CHAMPION").sum()),
        challenger_events=int((x.chosen_route_score_trimmed == "CHALLENGER").sum()),
        dropped_events=int((~x.kept_after_score_trim).sum()),
        rep_sum_result_usd=float(x.rep_result_usd_trimmed.sum()),
        worst_sum_result_usd=float(x.worst_result_usd_trimmed.sum()),
        rep_pf=pf(x.rep_result_usd_trimmed[x.kept_after_score_trim]),
        worst_pf=pf(x.worst_result_usd_trimmed[x.kept_after_score_trim]),
        negative_months_worst=int((mon.worst_sum_result_usd < 0).sum()) if not mon.empty else 0,
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
    ap.add_argument("--min-history-events", type=int, default=30)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "143"
    out.mkdir(parents=True, exist_ok=True)

    s133 = read_json(root / "133" / "gold_v3_133_summary.json")
    s142 = read_json(root / "142" / "gold_v3_142_summary.json")
    champion = str(s133.get("champion_policy_key", "density_safe||100||Q0.6"))
    challenger = str(s133.get("selected_challenger_policy_key", "density_safe||100||Q0.35"))
    cfg142 = parse_142_config(s142)
    led_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    led = load_csv(led_path)
    blockers = []
    if led.empty:
        blockers.append({"blocker_id": "missing_107k2_all_regime_ledgers", "path": str(led_path)})
    if not led.empty and cfg142["vol_col"] not in led.columns:
        blockers.append({"blocker_id": "missing_vol_col", "vol_col": cfg142["vol_col"]})

    summary_df = pd.DataFrame(); selected_monthly = pd.DataFrame(); selected_events = pd.DataFrame(); base_events = pd.DataFrame()
    completed_configs = 0; total_configs = 0
    if not blockers:
        led["entry_dt"] = pd.to_datetime(led.entry_dt, errors="coerce")
        led["result_usd"] = pd.to_numeric(led.get("result_usd"), errors="coerce")
        led = led[led.entry_dt.notna() & led.result_usd.notna()].copy()
        led["entry_date"] = led.entry_dt.dt.normalize()
        start = pd.Timestamp(args.start); end = pd.Timestamp(args.end_exclusive)
        led = led[(led.entry_dt >= start) & (led.entry_dt < end)].copy()
        base_events = build_base_events(led, champion, challenger, start, end, cfg142, args.min_history_days)
        save(base_events, out / "gold_v3_143_base_142_selected_events_with_scores.csv")
        score_cols = [c for c in ["feature_score", "score", "ledger_score", "max_score"] if c in base_events.columns and base_events[c].notna().any()]
        if not score_cols:
            blockers.append({"blocker_id": "no_score_columns_available"})
        else:
            configs = [("BASELINE_NO_TRIM", "max_score", 0.0, "NONE")]
            for sc in score_cols:
                for q in [0.50, 0.60, 0.70, 0.80]:
                    for scope in ["ALL", "CHALLENGER_ONLY", "CHAMPION_ONLY"]:
                        configs.append((f"RUNNING_SCORE|{sc}|Q{q}|{scope}", sc, q, scope))
            total_configs = len(configs)
            progress(out, 0, total_configs, "START", t0)
            rows = []; monthlies = []; cache = {}
            for idx, (label, sc, q, scope) in enumerate(configs, start=1):
                if label == "BASELINE_NO_TRIM":
                    tmp = base_events.copy()
                    tmp["score_trim_score_col"] = sc
                    tmp["score_trim_q"] = q
                    tmp["score_trim_scope"] = scope
                    tmp["score_trim_threshold"] = math.nan
                    tmp["kept_after_score_trim"] = True
                    tmp["chosen_route_score_trimmed"] = tmp["chosen_route"]
                    tmp["rep_result_usd_trimmed"] = tmp["rep_result_usd"]
                    tmp["worst_result_usd_trimmed"] = tmp["worst_result_usd"]
                else:
                    tmp = apply_score_trim(base_events, sc, q, scope, args.min_history_events)
                s, mon = summarize_trim(tmp, label, sc, q, scope)
                rows.append(s); monthlies.append(mon); cache[label] = (tmp, mon)
                completed_configs = idx
                progress(out, completed_configs, total_configs, label, t0)
            summary_df = pd.DataFrame(rows)
            if not summary_df.empty:
                summary_df["score_rank"] = summary_df.worst_sum_result_usd + summary_df.worst_pf * 100 - summary_df.negative_months_worst * 400 + summary_df.june_worst_sum_result_usd * 0.2 - summary_df.route_events * 0.25
                summary_df = summary_df.sort_values(["negative_months_worst", "worst_sum_result_usd", "worst_pf", "route_events"], ascending=[True, False, False, True]).reset_index(drop=True)
                key = str(summary_df.iloc[0].trim_config)
                selected_events, selected_monthly = cache.get(key, (pd.DataFrame(), pd.DataFrame()))
            save(summary_df, out / "gold_v3_143_running_score_trim_summary.csv")
            save(pd.concat(monthlies, ignore_index=True) if monthlies else pd.DataFrame(), out / "gold_v3_143_running_score_trim_monthly_all.csv")
            save(selected_events, out / "gold_v3_143_selected_score_trim_events.csv")
            save(selected_monthly, out / "gold_v3_143_selected_score_trim_monthly.csv")

    selected = summary_df.head(1).copy() if not summary_df.empty else pd.DataFrame()
    status = BLOCKED if blockers else READY
    if blockers:
        decision = "RUNNING_SCORE_TRIM_BLOCKED_INPUT_MISSING"
    elif selected.empty:
        decision = "RUNNING_SCORE_TRIM_READY_NO_CONFIG"
    elif str(selected.iloc[0].trim_config) == "BASELINE_NO_TRIM":
        decision = "RUNNING_SCORE_TRIM_NO_IMPROVING_TRIM_FOUND"
    elif int(selected.iloc[0].negative_months_worst) > 0:
        decision = "RUNNING_SCORE_TRIM_REVIEW_NEGATIVE_MONTHS_REMAIN"
    else:
        decision = "RUNNING_SCORE_TRIM_READY_NO_NEGATIVE_WORST_MONTHS"

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "audit_only": True,
        "review_only": True,
        "source_142_decision": s142.get("decision", ""),
        "source_142_selected_route_config": s142.get("selected_route_config", ""),
        "trim_is_replacement": False,
        "trim_uses_future_result": False,
        "trim_threshold_mode": "running_quantile_from_prior_visible_events",
        "progress_total_configs": total_configs,
        "progress_completed_configs": completed_configs,
        "progress_output": str(out / "progress.txt"),
        "base_event_count": int(len(base_events)) if not base_events.empty else 0,
        "champion_policy_key": champion,
        "challenger_policy_key": challenger,
        "selected_trim_config": str(selected.iloc[0].trim_config) if not selected.empty else "",
        "selected_score_col": str(selected.iloc[0].score_col) if not selected.empty else "",
        "selected_q": float(selected.iloc[0].q) if not selected.empty else 0.0,
        "selected_scope": str(selected.iloc[0].scope) if not selected.empty else "",
        "selected_route_events": int(selected.iloc[0].route_events) if not selected.empty else 0,
        "selected_champion_events": int(selected.iloc[0].champion_events) if not selected.empty else 0,
        "selected_challenger_events": int(selected.iloc[0].challenger_events) if not selected.empty else 0,
        "selected_dropped_events": int(selected.iloc[0].dropped_events) if not selected.empty else 0,
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
    (out / "gold_v3_143_summary.json").write_text(json.dumps(summary | {"blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save(pd.DataFrame([summary]), out / "gold_v3_143_decision.csv")
    lines = ["GOLD V3 143 PASTE_ME_RUNNING_SCORE_TRIM_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "TOP30_RUNNING_SCORE_TRIM_CONFIGS", summary_df.head(30).to_string(index=False) if not summary_df.empty else "NO_CONFIG_ROWS"]
    lines += ["", "SELECTED_SCORE_TRIM_MONTHLY", selected_monthly.to_string(index=False) if not selected_monthly.empty else "NO_SELECTED_MONTHLY"]
    lines += ["", "SELECTED_SCORE_TRIM_EVENTS_TAIL", selected_events.tail(80).to_string(index=False) if not selected_events.empty else "NO_SELECTED_EVENTS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "selected_trim_config": summary["selected_trim_config"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
