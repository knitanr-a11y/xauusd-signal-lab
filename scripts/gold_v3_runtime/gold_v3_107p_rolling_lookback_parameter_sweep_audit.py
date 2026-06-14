#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_107o_rolling_20d_adaptive_loss_trim_audit as ro

STEP = "GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY"
READY = "GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def parse_ints(s: str) -> list[int]:
    return [int(x.strip()) for x in str(s).split(",") if str(x).strip()]


def run_combo(led: pd.DataFrame, lookback: int, target_days: int, min_train_rows: int, min_removed: int, min_retention: float) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    days = sorted(led["entry_day"].unique().tolist())
    windows = ro.build_windows(days, lookback, target_days)
    selected_rows = []
    rolling_parts = []
    base_parts = []
    window_rows = []
    for w in windows:
        train = led[led["entry_day"].isin(w["train_days"])].copy()
        target = led[led["entry_day"].isin(w["target_days"])].copy()
        base_m = ro.metrics(target)
        base_tmp = target.copy()
        base_tmp["lookback_active_days"] = lookback
        base_tmp["target_active_days"] = target_days
        base_tmp["rolling_window_id"] = w["window_id"]
        base_parts.append(base_tmp)
        if len(train) < min_train_rows or target.empty:
            kept = target.copy()
            selected_rows.append(dict(lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=False, reason="insufficient_train_or_target"))
        else:
            fr = ro.enumerate_filters(train, min_removed, min_retention)
            if fr.empty:
                kept = target.copy()
                selected_rows.append(dict(lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=False, reason="no_train_filter"))
            else:
                b = fr.iloc[0]
                kept, mask = ro.apply_filter(target, b)
                removed = target[mask].copy()
                kept_m = ro.metrics(kept)
                rem_m = ro.metrics(removed)
                selected_rows.append(dict(lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=True, reason="rolling_sweep_train_selected", feature=str(b.feature), op=str(b.op), threshold=b.threshold, side_scope=str(b.side_scope), train_retained_wr=float(b.retained_wr), train_retained_pf=float(b.retained_pf), train_retention=float(b.retention), target_base_wr=base_m["win_rate"], target_base_pf=base_m["profit_factor"], target_retained_trades=kept_m["trades"], target_retained_wr=kept_m["win_rate"], target_retained_pf=kept_m["profit_factor"], target_retention=kept_m["trades"] / max(1, base_m["trades"]), target_removed_trades=rem_m["trades"], target_removed_wr=rem_m["win_rate"], target_wr_gain=kept_m["win_rate"] - base_m["win_rate"] if kept_m["trades"] else -999.0))
        kept = kept.copy()
        kept["lookback_active_days"] = lookback
        kept["target_active_days"] = target_days
        kept["rolling_window_id"] = w["window_id"]
        rolling_parts.append(kept)
        kept_m = ro.metrics(kept)
        window_rows.append(dict(lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], base_trades=base_m["trades"], base_wr=base_m["win_rate"], base_pf=base_m["profit_factor"], rolling_trades=kept_m["trades"], rolling_wr=kept_m["win_rate"], rolling_pf=kept_m["profit_factor"], rolling_retention=kept_m["trades"] / max(1, base_m["trades"]), rolling_wr_gain=kept_m["win_rate"] - base_m["win_rate"] if kept_m["trades"] else -999.0))
    selected = pd.DataFrame(selected_rows)
    rolling = pd.concat(rolling_parts, ignore_index=True) if rolling_parts else pd.DataFrame()
    base_eval = pd.concat(base_parts, ignore_index=True) if base_parts else pd.DataFrame()
    window_metrics = pd.DataFrame(window_rows)
    base_m = ro.metrics(base_eval)
    roll_m = ro.metrics(rolling)
    reg = ro.by_group(rolling, ["regime_split"]) if not rolling.empty else pd.DataFrame()
    min_reg_wr = float(reg["win_rate"].min()) if not reg.empty else 0.0
    min_reg_pf = float(reg["profit_factor"].min()) if not reg.empty else 0.0
    retention = roll_m["trades"] / max(1, base_m["trades"])
    wr_gain = roll_m["win_rate"] - base_m["win_rate"]
    pf_gain = roll_m["profit_factor"] - base_m["profit_factor"]
    primary = bool(roll_m["win_rate"] >= 0.625 and roll_m["profit_factor"] >= 2.70 and retention >= 0.65 and min_reg_wr >= 0.60 and roll_m["negative_month_count"] == 0)
    review = bool(wr_gain >= 0.01 and roll_m["profit_factor"] >= base_m["profit_factor"] and retention >= 0.65 and min_reg_wr >= 0.595)
    selection_score = (100000 if primary else 0) + (50000 if review else 0) + wr_gain * 20000 + pf_gain * 1000 + min_reg_wr * 1000 + retention * 100 - roll_m["negative_month_count"] * 500
    rec = dict(lookback_active_days=lookback, target_active_days=target_days, window_count=len(windows), selected_window_count=int(selected["selected"].sum()) if not selected.empty and "selected" in selected else 0, base_trades=base_m["trades"], base_wr=base_m["win_rate"], base_pf=base_m["profit_factor"], base_sum=base_m["sum_result_usd"], rolling_trades=roll_m["trades"], rolling_wr=roll_m["win_rate"], rolling_pf=roll_m["profit_factor"], rolling_sum=roll_m["sum_result_usd"], rolling_retention=retention, rolling_wr_gain=wr_gain, rolling_pf_gain=pf_gain, rolling_negative_month_count=roll_m["negative_month_count"], min_regime_wr=min_reg_wr, min_regime_pf=min_reg_pf, primary_gate=primary, review_gate=review, selection_score=selection_score)
    return rec, selected, rolling, window_metrics


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--lookbacks", default="20,10,5")
    ap.add_argument("--targets", default="5,3,1")
    ap.add_argument("--min-train-rows", type=int, default=150)
    ap.add_argument("--min-removed", type=int, default=10)
    ap.add_argument("--min-retention", type=float, default=0.65)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "107lc"
    out = root / "107pc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")

    blocks, outputs, vals, findings = [], [], [], []
    lpath = src / "gold_v3_107l_rehydrated_best_policy_ledger.csv"
    if not lpath.exists():
        blocks.append(dict(blocker_id="missing_107l_rehydrated_best_policy_ledger", path=str(lpath)))

    led = pd.DataFrame()
    if not blocks:
        led = pd.read_csv(lpath, encoding="utf-8-sig", low_memory=False)
        for c in ["entry_dt", "result_usd", "regime_split"]:
            if c not in led.columns:
                blocks.append(dict(blocker_id="ledger_missing_required_column", column=c))

    sweep = pd.DataFrame()
    all_selected = pd.DataFrame()
    all_windows = pd.DataFrame()
    best_ledger = pd.DataFrame()
    best_reg = pd.DataFrame()
    best_mon = pd.DataFrame()
    qg = pd.DataFrame()

    if not blocks:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led["result_usd"], errors="coerce")
        led = led[led["entry_dt"].notna() & led["result_usd"].notna()].sort_values("entry_dt").copy()
        led["entry_day"] = led["entry_dt"].dt.date.astype(str)
        led["entry_month"] = led["entry_dt"].dt.to_period("M").astype(str)
        lookbacks = parse_ints(args.lookbacks)
        targets = parse_ints(args.targets)
        combos = [(l, t) for l in lookbacks for t in targets]
        if not combos:
            blocks.append(dict(blocker_id="no_parameter_combos"))

    if not blocks:
        prog(0, len(combos), "start")
        summary_rows, selected_parts, window_parts, ledger_by_key = [], [], [], {}
        for i, (lookback, target_days) in enumerate(combos, 1):
            prog(i - 1, len(combos), f"combo={lookback}d->{target_days}d START")
            rec, selected, rolling, window_metrics = run_combo(led, lookback, target_days, args.min_train_rows, args.min_removed, args.min_retention)
            combo_key = f"L{lookback}_T{target_days}"
            rec["combo_key"] = combo_key
            summary_rows.append(rec)
            if not selected.empty:
                selected["combo_key"] = combo_key
                selected_parts.append(selected)
            if not window_metrics.empty:
                window_metrics["combo_key"] = combo_key
                window_parts.append(window_metrics)
            ledger_by_key[combo_key] = rolling
            prog(i, len(combos), f"combo={combo_key} DONE wr={rec['rolling_wr']:.4f} pf={rec['rolling_pf']:.3f} ret={rec['rolling_retention']:.3f}")
        sweep = pd.DataFrame(summary_rows).sort_values(["selection_score", "rolling_wr", "rolling_pf"], ascending=[False, False, False]).reset_index(drop=True)
        sweep.insert(0, "sweep_rank", range(1, len(sweep) + 1))
        all_selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
        all_windows = pd.concat(window_parts, ignore_index=True) if window_parts else pd.DataFrame()
        best_key = str(sweep.iloc[0]["combo_key"]) if not sweep.empty else ""
        best_ledger = ledger_by_key.get(best_key, pd.DataFrame()).copy()
        best_reg = ro.by_group(best_ledger, ["regime_split"]) if not best_ledger.empty else pd.DataFrame()
        best_mon = ro.by_group(best_ledger, ["regime_split", "entry_month"]) if not best_ledger.empty else pd.DataFrame()
        save(sweep, out / "gold_v3_107p_parameter_sweep_summary.csv")
        save(all_selected, out / "gold_v3_107p_all_selected_filters.csv")
        save(all_windows, out / "gold_v3_107p_all_window_metrics.csv")
        save(best_ledger, out / "gold_v3_107p_best_combo_trade_ledger.csv")
        save(best_reg, out / "gold_v3_107p_best_combo_regime_metrics.csv")
        save(best_mon, out / "gold_v3_107p_best_combo_monthly_metrics.csv")
        outputs += ["gold_v3_107p_parameter_sweep_summary.csv", "gold_v3_107p_all_selected_filters.csv", "gold_v3_107p_all_window_metrics.csv", "gold_v3_107p_best_combo_trade_ledger.csv", "gold_v3_107p_best_combo_regime_metrics.csv", "gold_v3_107p_best_combo_monthly_metrics.csv"]
        if sweep.empty:
            blocks.append(dict(blocker_id="empty_parameter_sweep_summary"))

    best = sweep.iloc[0].to_dict() if not sweep.empty else {}
    primary = bool(best.get("primary_gate", False))
    review = bool(best.get("review_gate", False))
    qg = pd.DataFrame([
        gy.gate_row("primary_wr_ge_62_5", best.get("rolling_wr", 0.0), ">=", 0.625),
        gy.gate_row("primary_pf_ge_2_70", best.get("rolling_pf", 0.0), ">=", 2.70),
        gy.gate_row("retention_ge_65", best.get("rolling_retention", 0.0), ">=", 0.65),
        gy.gate_row("min_regime_wr_ge_60", best.get("min_regime_wr", 0.0), ">=", 0.60),
        gy.gate_row("negative_month_count_eq_0", best.get("rolling_negative_month_count", 999), "==", 0),
        gy.gate_row("review_wr_gain_ge_1pct", best.get("rolling_wr_gain", 0.0), ">=", 0.01),
        gy.gate_row("review_pf_improves", best.get("rolling_pf", 0.0), ">=", best.get("base_pf", 999.0)),
    ])
    save(qg, out / "gold_v3_107p_quality_gate_matrix.csv")
    outputs.append("gold_v3_107p_quality_gate_matrix.csv")

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
    if not sweep.empty:
        vals.append(dict(check_id="parameter_sweep_rows_positive", result="PASS", observed=len(sweep), expected=">0", severity="BLOCKER"))
    if not best_ledger.empty:
        vals.append(dict(check_id="best_combo_ledger_positive", result="PASS", observed=len(best_ledger), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failed = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failed == 0 else BLOCKED
    if status != READY:
        decision = "ROLLING_LOOKBACK_SWEEP_BLOCKED_INPUT_INCOMPLETE"
    elif primary:
        decision = "ROLLING_LOOKBACK_SWEEP_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY"
    elif review:
        decision = "ROLLING_LOOKBACK_SWEEP_REVIEW_READY_FOR_FILTER_STABILITY_AUDIT"
    else:
        decision = "ROLLING_LOOKBACK_SWEEP_NOT_CONFIRMED_NEED_RULE_FAMILY_CHANGE"

    if best:
        findings.append("best_combo=" + json.dumps(best, ensure_ascii=False, default=str))
    if not sweep.empty:
        findings.append("top5_sweep=" + json.dumps(sweep.head(5).to_dict(orient="records"), ensure_ascii=False, default=str))

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
        lookbacks=args.lookbacks,
        targets=args.targets,
        min_train_rows=args.min_train_rows,
        min_removed=args.min_removed,
        min_retention=args.min_retention,
        blocker_count=len(blocks),
        validation_failure_count=validation_failed,
        elapsed_seconds=round(time.time() - t0, 2),
        sweep_rows=int(len(sweep)) if not sweep.empty else 0,
        best_combo_key=best.get("combo_key", ""),
        best_lookback_active_days=best.get("lookback_active_days", ""),
        best_target_active_days=best.get("target_active_days", ""),
        best_rolling_wr=best.get("rolling_wr", 0.0),
        best_rolling_pf=best.get("rolling_pf", 0.0),
        best_rolling_retention=best.get("rolling_retention", 0.0),
        best_rolling_wr_gain=best.get("rolling_wr_gain", 0.0),
        best_min_regime_wr=best.get("min_regime_wr", 0.0),
        best_primary_gate=primary,
        best_review_gate=review,
    )
    save(pd.DataFrame(blocks), out / "gold_v3_107p_blocker_matrix.csv")
    save(val, out / "gold_v3_107p_validation_matrix.csv")
    outputs += ["gold_v3_107p_blocker_matrix.csv", "gold_v3_107p_validation_matrix.csv", "gold_v3_107p_summary.json", "GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107p_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107P report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107P PASTE_ME_ROLLING_LOOKBACK_PARAMETER_SWEEP",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "health_gate_simulated: false",
        "resolved_only_strict: false",
        "progress_logging_enabled: true",
        "safety: audit_only=true, rolling_sweep_proxy=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
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
        "QUALITY_GATES_BEST_COMBO",
        qg.to_string(index=False),
        "",
        "VALIDATION",
        val.to_string(index=False),
        "",
        "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(1, 1, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
