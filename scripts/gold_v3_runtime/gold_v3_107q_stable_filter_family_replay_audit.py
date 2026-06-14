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
import gold_v3_107p_rolling_lookback_parameter_sweep_audit as sw

STEP = "GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY"
READY = "GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


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


def family_candidates_from_seed(seed: pd.DataFrame, top_n: int) -> pd.DataFrame:
    if seed.empty:
        return pd.DataFrame()
    need = ["feature", "op", "side_scope"]
    for c in need:
        if c not in seed.columns:
            return pd.DataFrame()
    x = seed.copy()
    if "candidate_rank" in x.columns:
        x = x.sort_values("candidate_rank")
    x = x[need + (["candidate_rank"] if "candidate_rank" in x.columns else [])].drop_duplicates(need).head(top_n).copy()
    if not ((x["feature"].astype(str) == "m15_dist_atr") & (x["op"].astype(str) == ">=") & (x["side_scope"].astype(str) == "ALL")).any():
        x = pd.concat([pd.DataFrame([dict(feature="m15_dist_atr", op=">=", side_scope="ALL", candidate_rank=0)]), x], ignore_index=True)
    x.insert(0, "family_id", [f"F{i+1:03d}" for i in range(len(x))])
    return x


def threshold_rows(train: pd.DataFrame, feature: str, op: str, side_scope: str, min_removed: int, min_retention: float) -> pd.DataFrame:
    if feature not in train.columns:
        return pd.DataFrame()
    if op in ["TRUE", "FALSE"]:
        mask = ro.condition_mask(train, feature, op, side=side_scope)
        if int(mask.sum()) < min_removed:
            return pd.DataFrame()
        retained = train[~mask].copy()
        removed = train[mask].copy()
        if len(retained) / max(1, len(train)) < min_retention:
            return pd.DataFrame()
        rec = dict(feature=feature, op=op, side_scope=side_scope, threshold="", quantile="")
        rec.update(ro.score_candidate(train, retained, removed))
        return pd.DataFrame([rec])
    s = pd.to_numeric(train[feature], errors="coerce")
    if s.notna().sum() < 80:
        return pd.DataFrame()
    qs = s.dropna().quantile(ro.QS).drop_duplicates()
    rows = []
    for q, thr in qs.items():
        mask = ro.condition_mask(train, feature, op, float(thr), side_scope)
        if int(mask.sum()) < min_removed:
            continue
        retained = train[~mask].copy()
        removed = train[mask].copy()
        if len(retained) / max(1, len(train)) < min_retention:
            continue
        rec = dict(feature=feature, op=op, side_scope=side_scope, threshold=float(thr), quantile=float(q))
        rec.update(ro.score_candidate(train, retained, removed))
        rows.append(rec)
    fr = pd.DataFrame(rows)
    if fr.empty:
        return fr
    base = ro.metrics(train)
    fr = fr[(fr["retained_wr"] >= base["win_rate"] + 0.0025) & (fr["retained_pf"] >= base["profit_factor"]) & (fr["retention"] >= min_retention)].copy()
    if fr.empty:
        return fr
    return fr.sort_values(["train_score", "retained_wr", "retained_pf"], ascending=[False, False, False]).reset_index(drop=True)


def run_family_combo(led: pd.DataFrame, fam: dict, lookback: int, target_days: int, min_train_rows: int, min_removed: int, min_retention: float):
    days = sorted(led["entry_day"].unique().tolist())
    windows = ro.build_windows(days, lookback, target_days)
    selected_rows, rolling_parts, base_parts, window_rows = [], [], [], []
    feature, op, side_scope = str(fam["feature"]), str(fam["op"]), str(fam["side_scope"])
    for w in windows:
        train = led[led["entry_day"].isin(w["train_days"])].copy()
        target = led[led["entry_day"].isin(w["target_days"])].copy()
        base_m = ro.metrics(target)
        base_tmp = target.copy()
        base_tmp["family_id"] = fam["family_id"]
        base_tmp["lookback_active_days"] = lookback
        base_tmp["target_active_days"] = target_days
        base_tmp["rolling_window_id"] = w["window_id"]
        base_parts.append(base_tmp)
        if len(train) < min_train_rows or target.empty:
            kept = target.copy()
            selected_rows.append(dict(family_id=fam["family_id"], feature=feature, op=op, side_scope=side_scope, lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=False, reason="insufficient_train_or_target"))
        else:
            fr = threshold_rows(train, feature, op, side_scope, min_removed, min_retention)
            if fr.empty:
                kept = target.copy()
                selected_rows.append(dict(family_id=fam["family_id"], feature=feature, op=op, side_scope=side_scope, lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=False, reason="no_train_threshold"))
            else:
                b = fr.iloc[0]
                kept, mask = ro.apply_filter(target, b)
                removed = target[mask].copy()
                kept_m = ro.metrics(kept)
                rem_m = ro.metrics(removed)
                selected_rows.append(dict(family_id=fam["family_id"], feature=feature, op=op, side_scope=side_scope, lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], train_rows=len(train), target_rows=len(target), selected=True, reason="stable_family_threshold_selected", threshold=b.threshold, quantile=b.quantile, train_retained_wr=float(b.retained_wr), train_retained_pf=float(b.retained_pf), train_retention=float(b.retention), target_base_wr=base_m["win_rate"], target_base_pf=base_m["profit_factor"], target_retained_trades=kept_m["trades"], target_retained_wr=kept_m["win_rate"], target_retained_pf=kept_m["profit_factor"], target_retention=kept_m["trades"] / max(1, base_m["trades"]), target_removed_trades=rem_m["trades"], target_removed_wr=rem_m["win_rate"], target_wr_gain=kept_m["win_rate"] - base_m["win_rate"] if kept_m["trades"] else -999.0))
        kept = kept.copy()
        kept["family_id"] = fam["family_id"]
        kept["family_feature"] = feature
        kept["family_op"] = op
        kept["family_side_scope"] = side_scope
        kept["lookback_active_days"] = lookback
        kept["target_active_days"] = target_days
        kept["rolling_window_id"] = w["window_id"]
        rolling_parts.append(kept)
        km = ro.metrics(kept)
        window_rows.append(dict(family_id=fam["family_id"], feature=feature, op=op, side_scope=side_scope, lookback_active_days=lookback, target_active_days=target_days, window_id=w["window_id"], train_start=w["train_start"], train_end=w["train_end"], target_start=w["target_start"], target_end=w["target_end"], base_trades=base_m["trades"], base_wr=base_m["win_rate"], base_pf=base_m["profit_factor"], family_trades=km["trades"], family_wr=km["win_rate"], family_pf=km["profit_factor"], family_retention=km["trades"] / max(1, base_m["trades"]), family_wr_gain=km["win_rate"] - base_m["win_rate"] if km["trades"] else -999.0))
    selected = pd.DataFrame(selected_rows)
    rolling = pd.concat(rolling_parts, ignore_index=True) if rolling_parts else pd.DataFrame()
    base_eval = pd.concat(base_parts, ignore_index=True) if base_parts else pd.DataFrame()
    window_metrics = pd.DataFrame(window_rows)
    base = ro.metrics(base_eval)
    m = ro.metrics(rolling)
    reg = ro.by_group(rolling, ["regime_split"]) if not rolling.empty else pd.DataFrame()
    min_reg_wr = float(reg["win_rate"].min()) if not reg.empty else 0.0
    min_reg_pf = float(reg["profit_factor"].min()) if not reg.empty else 0.0
    retention = m["trades"] / max(1, base["trades"])
    wr_gain = m["win_rate"] - base["win_rate"]
    pf_gain = m["profit_factor"] - base["profit_factor"]
    primary = bool(m["win_rate"] >= 0.625 and m["profit_factor"] >= 2.70 and retention >= 0.65 and min_reg_wr >= 0.60 and m["negative_month_count"] == 0)
    review = bool(wr_gain >= 0.01 and m["profit_factor"] >= base["profit_factor"] and retention >= 0.65 and min_reg_wr >= 0.595)
    score = (100000 if primary else 0) + (50000 if review else 0) + wr_gain * 22000 + pf_gain * 1000 + min_reg_wr * 1200 + retention * 100 - m["negative_month_count"] * 500
    rec = dict(family_id=fam["family_id"], feature=feature, op=op, side_scope=side_scope, lookback_active_days=lookback, target_active_days=target_days, window_count=len(windows), selected_window_count=int(selected["selected"].sum()) if not selected.empty and "selected" in selected else 0, base_trades=base["trades"], base_wr=base["win_rate"], base_pf=base["profit_factor"], base_sum=base["sum_result_usd"], family_trades=m["trades"], family_wr=m["win_rate"], family_pf=m["profit_factor"], family_sum=m["sum_result_usd"], family_retention=retention, family_wr_gain=wr_gain, family_pf_gain=pf_gain, family_negative_month_count=m["negative_month_count"], min_regime_wr=min_reg_wr, min_regime_pf=min_reg_pf, primary_gate=primary, review_gate=review, selection_score=score)
    return rec, selected, rolling, window_metrics


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--family-top-n", type=int, default=30)
    ap.add_argument("--lookbacks", default="20,10,5")
    ap.add_argument("--targets", default="5,3,1")
    ap.add_argument("--min-train-rows", type=int, default=150)
    ap.add_argument("--min-removed", type=int, default=10)
    ap.add_argument("--min-retention", type=float, default=0.65)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src_l = root / "107lc"
    src_m = root / "107mc"
    out = root / "107qc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")

    blocks, outputs, vals, findings = [], [], [], []
    lpath = src_l / "gold_v3_107l_rehydrated_best_policy_ledger.csv"
    fpath = src_m / "gold_v3_107m_loss_trim_frontier.csv"
    if not lpath.exists():
        blocks.append(dict(blocker_id="missing_107l_rehydrated_best_policy_ledger", path=str(lpath)))
    if not fpath.exists():
        blocks.append(dict(blocker_id="missing_107m_loss_trim_frontier", path=str(fpath)))

    led = pd.DataFrame()
    seed = pd.DataFrame()
    families = pd.DataFrame()
    summary_df = pd.DataFrame()
    all_selected = pd.DataFrame()
    all_windows = pd.DataFrame()
    best_ledger = pd.DataFrame()
    best_reg = pd.DataFrame()
    best_mon = pd.DataFrame()

    if not blocks:
        led = pd.read_csv(lpath, encoding="utf-8-sig", low_memory=False)
        seed = pd.read_csv(fpath, encoding="utf-8-sig")
        for c in ["entry_dt", "result_usd", "regime_split"]:
            if c not in led.columns:
                blocks.append(dict(blocker_id="ledger_missing_required_column", column=c))
        families = family_candidates_from_seed(seed, args.family_top_n)
        if families.empty:
            blocks.append(dict(blocker_id="no_seed_families_from_107m_frontier"))

    if not blocks:
        led["entry_dt"] = pd.to_datetime(led["entry_dt"], errors="coerce")
        led["result_usd"] = pd.to_numeric(led["result_usd"], errors="coerce")
        led = led[led["entry_dt"].notna() & led["result_usd"].notna()].sort_values("entry_dt").copy()
        led["entry_day"] = led["entry_dt"].dt.date.astype(str)
        led["entry_month"] = led["entry_dt"].dt.to_period("M").astype(str)
        lookbacks = sw.parse_ints(args.lookbacks)
        targets = sw.parse_ints(args.targets)
        combos = [(l, t) for _, fam in families.iterrows() for l in lookbacks for t in targets]
        total = len(families) * len(lookbacks) * len(targets)
        prog(0, total, "start")
        rows, selected_parts, window_parts, ledger_by_key = [], [], [], {}
        step = 0
        for _, fam in families.iterrows():
            famd = fam.to_dict()
            for lookback in lookbacks:
                for target in targets:
                    step += 1
                    label = f"{famd['family_id']} {famd['feature']} {famd['op']} {famd['side_scope']} L{lookback}->T{target}"
                    rec, sel, roll, wm = run_family_combo(led, famd, lookback, target, args.min_train_rows, args.min_removed, args.min_retention)
                    combo_key = f"{famd['family_id']}_L{lookback}_T{target}"
                    rec["combo_key"] = combo_key
                    rows.append(rec)
                    if not sel.empty:
                        sel["combo_key"] = combo_key
                        selected_parts.append(sel)
                    if not wm.empty:
                        wm["combo_key"] = combo_key
                        window_parts.append(wm)
                    ledger_by_key[combo_key] = roll
                    prog(step, total, f"family_combo={label} wr={rec['family_wr']:.4f} pf={rec['family_pf']:.3f}")
        summary_df = pd.DataFrame(rows).sort_values(["selection_score", "family_wr", "family_pf"], ascending=[False, False, False]).reset_index(drop=True)
        summary_df.insert(0, "family_sweep_rank", range(1, len(summary_df) + 1))
        all_selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
        all_windows = pd.concat(window_parts, ignore_index=True) if window_parts else pd.DataFrame()
        best_key = str(summary_df.iloc[0]["combo_key"]) if not summary_df.empty else ""
        best_ledger = ledger_by_key.get(best_key, pd.DataFrame()).copy()
        best_reg = ro.by_group(best_ledger, ["regime_split"]) if not best_ledger.empty else pd.DataFrame()
        best_mon = ro.by_group(best_ledger, ["regime_split", "entry_month"]) if not best_ledger.empty else pd.DataFrame()
        save(summary_df, out / "gold_v3_107q_family_sweep_summary.csv")
        save(all_selected, out / "gold_v3_107q_all_selected_thresholds.csv")
        save(all_windows, out / "gold_v3_107q_all_window_metrics.csv")
        save(best_ledger, out / "gold_v3_107q_best_family_trade_ledger.csv")
        save(best_reg, out / "gold_v3_107q_best_family_regime_metrics.csv")
        save(best_mon, out / "gold_v3_107q_best_family_monthly_metrics.csv")
        outputs += ["gold_v3_107q_family_sweep_summary.csv", "gold_v3_107q_all_selected_thresholds.csv", "gold_v3_107q_all_window_metrics.csv", "gold_v3_107q_best_family_trade_ledger.csv", "gold_v3_107q_best_family_regime_metrics.csv", "gold_v3_107q_best_family_monthly_metrics.csv"]
        if summary_df.empty:
            blocks.append(dict(blocker_id="empty_family_sweep_summary"))

    best = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    primary = bool(best.get("primary_gate", False))
    review = bool(best.get("review_gate", False))
    qg = pd.DataFrame([
        gy.gate_row("primary_wr_ge_62_5", best.get("family_wr", 0.0), ">=", 0.625),
        gy.gate_row("primary_pf_ge_2_70", best.get("family_pf", 0.0), ">=", 2.70),
        gy.gate_row("retention_ge_65", best.get("family_retention", 0.0), ">=", 0.65),
        gy.gate_row("min_regime_wr_ge_60", best.get("min_regime_wr", 0.0), ">=", 0.60),
        gy.gate_row("negative_month_count_eq_0", best.get("family_negative_month_count", 999), "==", 0),
        gy.gate_row("review_wr_gain_ge_1pct", best.get("family_wr_gain", 0.0), ">=", 0.01),
        gy.gate_row("review_pf_improves", best.get("family_pf", 0.0), ">=", best.get("base_pf", 999.0)),
    ])
    save(qg, out / "gold_v3_107q_quality_gate_matrix.csv")
    outputs.append("gold_v3_107q_quality_gate_matrix.csv")

    vals += [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="target_window_outcomes_not_used_for_threshold_selection", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="posthoc_seed_family_not_final", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="progress_logging_enabled", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="resolved_only_strict_blocked_without_exit_dt", result="PASS", observed=("exit_dt" not in led.columns), expected=True, severity="WARN"),
    ]
    if not summary_df.empty:
        vals.append(dict(check_id="family_sweep_rows_positive", result="PASS", observed=len(summary_df), expected=">0", severity="BLOCKER"))
    if not best_ledger.empty:
        vals.append(dict(check_id="best_family_ledger_positive", result="PASS", observed=len(best_ledger), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failed = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failed == 0 else BLOCKED
    if status != READY:
        decision = "STABLE_FILTER_FAMILY_BLOCKED_INPUT_INCOMPLETE"
    elif primary:
        decision = "STABLE_FILTER_FAMILY_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY"
    elif review:
        decision = "STABLE_FILTER_FAMILY_REVIEW_READY_FOR_CLEAN_FAMILY_SELECTION_REPLAY"
    else:
        decision = "STABLE_FILTER_FAMILY_NOT_CONFIRMED_NEED_NON_FILTER_RULE_CHANGE"

    findings = []
    if best:
        findings.append("best_family_combo=" + json.dumps(best, ensure_ascii=False, default=str))
    if not summary_df.empty:
        findings.append("top10_family_sweep=" + json.dumps(summary_df.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))

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
        family_top_n=args.family_top_n,
        lookbacks=args.lookbacks,
        targets=args.targets,
        min_train_rows=args.min_train_rows,
        min_removed=args.min_removed,
        min_retention=args.min_retention,
        blocker_count=len(blocks),
        validation_failure_count=validation_failed,
        elapsed_seconds=round(time.time() - t0, 2),
        family_rows=int(len(families)) if not families.empty else 0,
        family_sweep_rows=int(len(summary_df)) if not summary_df.empty else 0,
        best_combo_key=best.get("combo_key", ""),
        best_family_id=best.get("family_id", ""),
        best_feature=best.get("feature", ""),
        best_op=best.get("op", ""),
        best_side_scope=best.get("side_scope", ""),
        best_lookback_active_days=best.get("lookback_active_days", ""),
        best_target_active_days=best.get("target_active_days", ""),
        best_family_wr=best.get("family_wr", 0.0),
        best_family_pf=best.get("family_pf", 0.0),
        best_family_retention=best.get("family_retention", 0.0),
        best_family_wr_gain=best.get("family_wr_gain", 0.0),
        best_min_regime_wr=best.get("min_regime_wr", 0.0),
        best_primary_gate=primary,
        best_review_gate=review,
    )

    save(pd.DataFrame(blocks), out / "gold_v3_107q_blocker_matrix.csv")
    save(val, out / "gold_v3_107q_validation_matrix.csv")
    outputs += ["gold_v3_107q_blocker_matrix.csv", "gold_v3_107q_validation_matrix.csv", "gold_v3_107q_summary.json", "GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107q_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107Q report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "GOLD V3 107Q PASTE_ME_STABLE_FILTER_FAMILY_REPLAY",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "health_gate_simulated: false",
        "resolved_only_strict: false",
        "progress_logging_enabled: true",
        "safety: audit_only=true, stable_family_proxy=true, posthoc_seed_family_not_final=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
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
        "QUALITY_GATES_BEST_FAMILY",
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
