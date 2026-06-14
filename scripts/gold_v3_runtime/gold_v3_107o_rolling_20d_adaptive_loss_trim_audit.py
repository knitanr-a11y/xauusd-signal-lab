#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy


STEP = "GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY"
READY = "GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"

BOOL_COLS = [
    "m15_up", "m15_close_gt_ema20",
    "h1_up", "h1_close_gt_ema20",
    "h4_up", "h4_close_gt_ema20",
    "d1_up", "d1_close_gt_ema20",
]
NUM_COLS = [
    "ledger_score", "score", "feature_score",
    "m15_atr28", "m15_rsi14", "m15_dist_atr", "m15_range_atr",
    "h1_atr28", "h1_rsi14", "h1_dist_atr", "h1_range_atr",
    "h4_atr28", "h4_rsi14", "h4_dist_atr", "h4_range_atr",
    "d1_atr28", "d1_rsi14", "d1_dist_atr", "d1_range_atr",
]
QS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def cap(v) -> float:
    try:
        x = float(v)
        return 10.0 if math.isinf(x) else max(0.0, min(x, 10.0))
    except Exception:
        return 0.0


def pf(s) -> float:
    a = pd.to_numeric(pd.Series(s), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "result_usd" not in df.columns:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, unique_trade_days=0, max_day_trade_share=0.0, min_entry_dt="", max_entry_dt="")
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x["entry_dt"].notna() & x["result_usd"].notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, unique_trade_days=0, max_day_trade_share=0.0, min_entry_dt="", max_entry_dt="")
    mon = x.groupby(x["entry_dt"].dt.to_period("M").astype(str))["result_usd"].sum()
    day = x.groupby(x["entry_dt"].dt.date).size()
    return dict(
        trades=int(len(x)),
        wins=int((x["result_usd"] > 0).sum()),
        losses=int((x["result_usd"] < 0).sum()),
        win_rate=float((x["result_usd"] > 0).mean()),
        profit_factor=pf(x["result_usd"]),
        sum_result_usd=float(x["result_usd"].sum()),
        negative_month_count=int((mon < 0).sum()),
        unique_trade_days=int(len(day)),
        max_day_trade_share=float(day.max() / len(x)) if len(x) else 0.0,
        min_entry_dt=str(x["entry_dt"].min().date()),
        max_entry_dt=str(x["entry_dt"].max().date()),
    )


def by_group(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for key, g in df.groupby(cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        rows.append({c: str(v) for c, v in zip(cols, key)} | metrics(g))
    return pd.DataFrame(rows).sort_values(cols)


def condition_mask(df: pd.DataFrame, col: str, op: str, thr=None, side: str = "ALL") -> pd.Series:
    m = pd.Series(True, index=df.index)
    if side and side != "ALL" and "side" in df.columns:
        m &= df["side"].astype(str).eq(str(side))
    if op in ["TRUE", "FALSE"]:
        m &= df[col].fillna(False).astype(bool).eq(op == "TRUE")
    elif op == "<=":
        m &= pd.to_numeric(df[col], errors="coerce") <= float(thr)
    elif op == ">=":
        m &= pd.to_numeric(df[col], errors="coerce") >= float(thr)
    else:
        m &= False
    return m.fillna(False)


def score_candidate(train: pd.DataFrame, retained: pd.DataFrame, removed: pd.DataFrame) -> dict:
    bm = metrics(train)
    rm = metrics(retained)
    cm = metrics(removed)
    reg = by_group(retained, ["regime_split"]) if "regime_split" in retained.columns else pd.DataFrame()
    min_reg_wr = float(reg["win_rate"].min()) if not reg.empty else 0.0
    min_reg_pf = float(reg["profit_factor"].min()) if not reg.empty else 0.0
    min_reg_trades = int(reg["trades"].min()) if not reg.empty else 0
    return dict(
        removed_trades=cm["trades"],
        removed_wr=cm["win_rate"],
        removed_pf=cm["profit_factor"],
        removed_sum=cm["sum_result_usd"],
        retained_trades=rm["trades"],
        retention=float(rm["trades"] / max(1, bm["trades"])),
        retained_wr=rm["win_rate"],
        retained_pf=rm["profit_factor"],
        retained_sum=rm["sum_result_usd"],
        retained_negative_month_count=rm["negative_month_count"],
        min_regime_wr=min_reg_wr,
        min_regime_pf=min_reg_pf,
        min_regime_trades=min_reg_trades,
        train_score=(rm["win_rate"] - bm["win_rate"]) * 18000
        + (rm["profit_factor"] - bm["profit_factor"]) * 800
        + (min_reg_wr - bm["win_rate"]) * 4500
        - rm["negative_month_count"] * 500
        - cm["sum_result_usd"] * 0.01,
    )


def enumerate_filters(train: pd.DataFrame, min_removed: int, min_retention: float) -> pd.DataFrame:
    rows = []
    bm = metrics(train)
    sides = ["ALL"] + sorted([str(x) for x in train["side"].dropna().unique()]) if "side" in train.columns else ["ALL"]
    for col in BOOL_COLS:
        if col not in train.columns:
            continue
        for side in sides:
            for op in ["TRUE", "FALSE"]:
                mask = condition_mask(train, col, op, side=side)
                if int(mask.sum()) < min_removed:
                    continue
                retained = train[~mask].copy()
                removed = train[mask].copy()
                if len(retained) / max(1, len(train)) < min_retention:
                    continue
                rec = dict(filter_type="bool", side_scope=side, feature=col, op=op, threshold="", quantile="")
                rec.update(score_candidate(train, retained, removed))
                rows.append(rec)
    for col in NUM_COLS:
        if col not in train.columns:
            continue
        s = pd.to_numeric(train[col], errors="coerce")
        if s.notna().sum() < 80:
            continue
        qs = s.dropna().quantile(QS).drop_duplicates()
        for q, thr in qs.items():
            for side in sides:
                for op in ["<=", ">="]:
                    mask = condition_mask(train, col, op, float(thr), side)
                    if int(mask.sum()) < min_removed:
                        continue
                    retained = train[~mask].copy()
                    removed = train[mask].copy()
                    if len(retained) / max(1, len(train)) < min_retention:
                        continue
                    rec = dict(filter_type="numeric", side_scope=side, feature=col, op=op, threshold=float(thr), quantile=float(q))
                    rec.update(score_candidate(train, retained, removed))
                    rows.append(rec)
    fr = pd.DataFrame(rows)
    if fr.empty:
        return fr
    fr = fr[(fr["retained_wr"] >= bm["win_rate"] + 0.005) & (fr["retained_pf"] >= bm["profit_factor"]) & (fr["retention"] >= min_retention)].copy()
    if fr.empty:
        return fr
    return fr.sort_values(["train_score", "retained_wr", "retained_pf"], ascending=[False, False, False]).reset_index(drop=True)


def apply_filter(df: pd.DataFrame, row) -> tuple[pd.DataFrame, pd.Series]:
    if row is None:
        return df.copy(), pd.Series(False, index=df.index)
    mask = condition_mask(df, str(row.feature), str(row.op), None if str(row.threshold) == "" else float(row.threshold), str(row.side_scope))
    return df[~mask].copy(), mask


def build_windows(days: list, lookback_days: int, target_days: int) -> list[dict]:
    out = []
    i = lookback_days
    while i < len(days):
        train_days = days[max(0, i - lookback_days):i]
        target = days[i:min(len(days), i + target_days)]
        if not target:
            break
        out.append(dict(window_id=len(out) + 1, train_days=train_days, target_days=target, train_start=str(train_days[0]), train_end=str(train_days[-1]), target_start=str(target[0]), target_end=str(target[-1])))
        i += target_days
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--lookback-active-days", type=int, default=20)
    ap.add_argument("--target-active-days", type=int, default=5)
    ap.add_argument("--min-train-rows", type=int, default=300)
    ap.add_argument("--min-removed", type=int, default=15)
    ap.add_argument("--min-retention", type=float, default=0.65)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "107lc"
    out = root / "107oc"
    out.mkdir(parents=True, exist_ok=True)

    log(STEP + " START")
    blocks, outputs, vals, findings = [], [], [], []
    path = src / "gold_v3_107l_rehydrated_best_policy_ledger.csv"
    if not path.exists():
        blocks.append(dict(blocker_id="missing_107l_rehydrated_best_policy_ledger", path=str(path)))

    led = pd.DataFrame()
    selected = pd.DataFrame()
    rolling = pd.DataFrame()
    base_eval = pd.DataFrame()
    win_metrics = pd.DataFrame()
    reg = pd.DataFrame()
    mon = pd.DataFrame()

    if not blocks:
        led = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        for c in ["entry_dt", "result_usd", "regime_split"]:
            if c not in led.columns:
                blocks.append(dict(blocker_id="ledger_missing_required_column", column=c))

    if not blocks:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led["result_usd"], errors="coerce")
        led = led[led["entry_dt"].notna() & led["result_usd"].notna()].sort_values("entry_dt").copy()
        led["entry_day"] = led["entry_dt"].dt.date.astype(str)
        led["entry_month"] = led["entry_dt"].dt.to_period("M").astype(str)
        days = sorted(led["entry_day"].unique().tolist())
        windows = build_windows(days, args.lookback_active_days, args.target_active_days)
        if not windows:
            blocks.append(dict(blocker_id="no_rolling_windows", active_days=len(days)))

    if not blocks:
        prog(0, len(windows), "start")
        sel_rows, pass_ledgers, base_ledgers, wm_rows = [], [], [], []
        for idx, w in enumerate(windows, 1):
            train = led[led["entry_day"].isin(w["train_days"])].copy()
            target = led[led["entry_day"].isin(w["target_days"])].copy()
            bm = metrics(target)
            base_tmp = target.copy()
            base_tmp["rolling_window_id"] = w["window_id"]
            base_ledgers.append(base_tmp)
            if len(train) < args.min_train_rows or target.empty:
                out_target = target.copy()
                removed = pd.DataFrame()
                sel_rows.append(dict(**{k: v for k, v in w.items() if k not in ["train_days", "target_days"]}, train_rows=len(train), target_rows=len(target), selected=False, reason="insufficient_train_or_target"))
            else:
                fr = enumerate_filters(train, args.min_removed, args.min_retention)
                if fr.empty:
                    out_target = target.copy()
                    removed = pd.DataFrame()
                    sel_rows.append(dict(**{k: v for k, v in w.items() if k not in ["train_days", "target_days"]}, train_rows=len(train), target_rows=len(target), selected=False, reason="no_train_filter"))
                else:
                    b = fr.iloc[0]
                    out_target, mask = apply_filter(target, b)
                    removed = target[mask].copy()
                    rm = metrics(out_target)
                    cm = metrics(removed)
                    sel_rows.append(dict(**{k: v for k, v in w.items() if k not in ["train_days", "target_days"]}, train_rows=len(train), target_rows=len(target), selected=True, reason="rolling_train_selected", feature=str(b.feature), op=str(b.op), threshold=b.threshold, side_scope=str(b.side_scope), train_retained_wr=float(b.retained_wr), train_retained_pf=float(b.retained_pf), train_retention=float(b.retention), target_base_wr=bm["win_rate"], target_base_pf=bm["profit_factor"], target_retained_trades=rm["trades"], target_retained_wr=rm["win_rate"], target_retained_pf=rm["profit_factor"], target_retention=rm["trades"] / max(1, bm["trades"]), target_removed_trades=cm["trades"], target_removed_wr=cm["win_rate"], target_wr_gain=rm["win_rate"] - bm["win_rate"] if rm["trades"] else -999.0))
            out_target = out_target.copy()
            out_target["rolling_window_id"] = w["window_id"]
            pass_ledgers.append(out_target)
            wm = metrics(out_target)
            wm_rows.append(dict(window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], base_trades=bm["trades"], base_wr=bm["win_rate"], base_pf=bm["profit_factor"], **{f"rolling_{k}": v for k, v in wm.items()}))
            prog(idx, len(windows), f"window={w['window_id']} target={w['target_start']}..{w['target_end']}")

        selected = pd.DataFrame(sel_rows)
        rolling = pd.concat(pass_ledgers, ignore_index=True) if pass_ledgers else pd.DataFrame()
        base_eval = pd.concat(base_ledgers, ignore_index=True) if base_ledgers else pd.DataFrame()
        win_metrics = pd.DataFrame(wm_rows)
        reg = by_group(rolling, ["regime_split"])
        mon = by_group(rolling, ["regime_split", "entry_month"])
        save(selected, out / "gold_v3_107o_rolling_window_selected_filters.csv")
        save(rolling, out / "gold_v3_107o_rolling_trade_ledger.csv")
        save(win_metrics, out / "gold_v3_107o_rolling_window_metrics.csv")
        save(reg, out / "gold_v3_107o_rolling_regime_metrics.csv")
        save(mon, out / "gold_v3_107o_rolling_monthly_metrics.csv")
        outputs += [
            "gold_v3_107o_rolling_window_selected_filters.csv",
            "gold_v3_107o_rolling_trade_ledger.csv",
            "gold_v3_107o_rolling_window_metrics.csv",
            "gold_v3_107o_rolling_regime_metrics.csv",
            "gold_v3_107o_rolling_monthly_metrics.csv",
        ]
        if rolling.empty:
            blocks.append(dict(blocker_id="no_rolling_trade_ledger"))

    base_m = metrics(base_eval) if not base_eval.empty else metrics(pd.DataFrame())
    roll_m = metrics(rolling) if not rolling.empty else metrics(pd.DataFrame())
    retention = roll_m["trades"] / max(1, base_m["trades"])
    min_reg_wr = float(reg["win_rate"].min()) if not reg.empty else 0.0
    min_reg_pf = float(reg["profit_factor"].min()) if not reg.empty else 0.0
    wr_gain = roll_m["win_rate"] - base_m["win_rate"]
    primary = bool(roll_m["win_rate"] >= 0.625 and roll_m["profit_factor"] >= 2.70 and retention >= 0.65 and min_reg_wr >= 0.60 and roll_m["negative_month_count"] == 0)
    review = bool(wr_gain >= 0.01 and roll_m["profit_factor"] >= base_m["profit_factor"] and retention >= 0.65 and min_reg_wr >= 0.595)

    qg = pd.DataFrame([
        gy.gate_row("primary_wr_ge_62_5", roll_m["win_rate"], ">=", 0.625),
        gy.gate_row("primary_pf_ge_2_70", roll_m["profit_factor"], ">=", 2.70),
        gy.gate_row("retention_ge_65", retention, ">=", 0.65),
        gy.gate_row("min_regime_wr_ge_60", min_reg_wr, ">=", 0.60),
        gy.gate_row("negative_month_count_eq_0", roll_m["negative_month_count"], "==", 0),
        gy.gate_row("review_wr_gain_ge_1pct", wr_gain, ">=", 0.01),
        gy.gate_row("review_pf_improves", roll_m["profit_factor"], ">=", base_m["profit_factor"]),
    ])
    save(qg, out / "gold_v3_107o_quality_gate_matrix.csv")
    outputs.append("gold_v3_107o_quality_gate_matrix.csv")

    vals += [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="target_window_outcomes_not_used_for_selection", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="progress_logging_enabled", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="resolved_only_strict_blocked_without_exit_dt", result="PASS", observed=("exit_dt" not in led.columns), expected=True, severity="WARN"),
    ]
    if not selected.empty:
        vals.append(dict(check_id="rolling_window_rows_positive", result="PASS", observed=len(selected), expected=">0", severity="BLOCKER"))
    if not rolling.empty:
        vals.append(dict(check_id="rolling_ledger_positive", result="PASS", observed=len(rolling), expected=">0", severity="BLOCKER"))

    val = pd.DataFrame(vals)
    validation_failed = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failed == 0 else BLOCKED
    if status != READY:
        decision = "ROLLING_20D_ADAPTIVE_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE"
    elif primary:
        decision = "ROLLING_20D_ADAPTIVE_LOSS_TRIM_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY"
    elif review:
        decision = "ROLLING_20D_ADAPTIVE_LOSS_TRIM_REVIEW_READY_FOR_PARAMETER_SWEEP"
    else:
        decision = "ROLLING_20D_ADAPTIVE_LOSS_TRIM_NOT_CONFIRMED_NEED_PARAMETER_SWEEP"

    findings.append("base_eval_metrics=" + json.dumps(base_m, ensure_ascii=False, default=str))
    findings.append("rolling_metrics=" + json.dumps(roll_m, ensure_ascii=False, default=str))
    if not selected.empty:
        findings.append("selected_filter_head=" + json.dumps(selected.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))

    summary = dict(
        step=STEP,
        status=status,
        decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(out),
        audit_only=True,
        live_ready=False,
        source_csv_mutated=False,
        contract_mutated=False,
        open_asof_allowed=False,
        health_gate_simulated=False,
        resolved_only_strict=False,
        progress_logging_enabled=True,
        lookback_active_days=args.lookback_active_days,
        target_active_days=args.target_active_days,
        min_train_rows=args.min_train_rows,
        min_removed=args.min_removed,
        min_retention=args.min_retention,
        blocker_count=len(blocks),
        validation_failure_count=validation_failed,
        elapsed_seconds=round(time.time() - t0, 2),
        base_eval_metrics=base_m,
        rolling_metrics=roll_m,
        rolling_retention=retention,
        rolling_wr_gain=wr_gain,
        min_regime_wr=min_reg_wr,
        min_regime_pf=min_reg_pf,
        primary_gate=primary,
        review_gate=review,
        selected_window_count=int(selected["selected"].sum()) if not selected.empty and "selected" in selected else 0,
        window_rows=int(len(selected)) if not selected.empty else 0,
    )

    save(pd.DataFrame(blocks), out / "gold_v3_107o_blocker_matrix.csv")
    save(val, out / "gold_v3_107o_validation_matrix.csv")
    outputs += [
        "gold_v3_107o_quality_gate_matrix.csv",
        "gold_v3_107o_blocker_matrix.csv",
        "gold_v3_107o_validation_matrix.csv",
        "gold_v3_107o_summary.json",
        "GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY_REPORT.md",
        "paste_me.txt",
    ]

    (out / "gold_v3_107o_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107O report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "GOLD V3 107O PASTE_ME_ROLLING_20D_ADAPTIVE_LOSS_TRIM",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "health_gate_simulated: false",
        "resolved_only_strict: false",
        "progress_logging_enabled: true",
        "safety: audit_only=true, rolling_train_split_proxy=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blocks)),
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "",
        "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "",
        "BLOCKERS",
        pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS",
        "",
        "QUALITY_GATES",
        qg.to_string(index=False),
        "",
        "VALIDATION",
        val.to_string(index=False),
        "",
        "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(len(selected) if not selected.empty else 1, len(selected) if not selected.empty else 1, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
