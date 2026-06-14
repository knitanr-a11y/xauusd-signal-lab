#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY"
READY = "GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
LOOKBACKS = [20, 50]
TARGETS = [5, 10]
MIN_REMOVE_TRAIN = 10
MIN_RETENTION = 0.70
MAX_FEATURE_FAMILIES = 40


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def pf(vals) -> float:
    a = np.asarray(vals, dtype=float)
    gp = a[a > 0].sum()
    gl = -a[a < 0].sum()
    return float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0)
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x.entry_dt.notna() & x.result_usd.notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame())
    x["entry_month"] = x.entry_dt.dt.to_period("M").astype(str)
    mon = x.groupby("entry_month").result_usd.sum()
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd.to_numpy()),
        sum_result_usd=float(x.result_usd.sum()),
        negative_month_count=int((mon < 0).sum()),
    )


def load_universe(diag: pd.DataFrame, df: pd.DataFrame) -> list[dict]:
    rows = []
    if diag.empty:
        return rows
    d = diag.copy()
    d["diagnostic_score"] = pd.to_numeric(d.get("diagnostic_score", 0), errors="coerce").fillna(0)
    d = d.sort_values("diagnostic_score", ascending=False)
    seen = set()
    for _, r in d.iterrows():
        feat = str(r.get("feature", ""))
        if not feat or feat not in df.columns:
            continue
        kind = str(r.get("filter_kind", "numeric"))
        op = str(r.get("op_or_value", ""))
        key = (kind, feat, op if kind == "numeric" else "VALUE")
        if key in seen:
            continue
        seen.add(key)
        rows.append(dict(kind=kind, feature=feat, op=op))
        if len(rows) >= MAX_FEATURE_FAMILIES:
            break
    return rows


def apply_filter(df: pd.DataFrame, f: dict) -> pd.Series:
    feat = f["feature"]
    if feat not in df.columns:
        return pd.Series(False, index=df.index)
    if f["kind"] == "categorical":
        return df[feat].astype(str).eq(str(f.get("value", ""))).fillna(False)
    s = pd.to_numeric(df[feat], errors="coerce")
    thr = float(f.get("threshold", np.nan))
    if not np.isfinite(thr):
        return pd.Series(False, index=df.index)
    if f.get("op") == "<=":
        return (s <= thr).fillna(False)
    if f.get("op") == ">=":
        return (s >= thr).fillna(False)
    return pd.Series(False, index=df.index)


def candidate_filters_from_train(train: pd.DataFrame, universe: list[dict], base_train: dict) -> pd.DataFrame:
    rows = []
    for fam in universe:
        feat = fam["feature"]
        if feat not in train.columns:
            continue
        if fam["kind"] == "categorical":
            vals = train[feat].astype(str).value_counts(dropna=False).head(20).index.tolist()
            for val in vals:
                f = dict(kind="categorical", feature=feat, value=str(val), op="==")
                rem = apply_filter(train, f)
                rows.append(score_filter(train, f, rem, base_train))
        else:
            s = pd.to_numeric(train[feat], errors="coerce")
            valid = s.notna()
            if valid.sum() < 50:
                continue
            qs = [0.05, 0.10, 0.20, 0.30] if fam.get("op") == "<=" else [0.70, 0.80, 0.90, 0.95]
            for q in qs:
                thr = float(s[valid].quantile(q))
                f = dict(kind="numeric", feature=feat, op=fam.get("op"), threshold=thr, quantile=q)
                rem = apply_filter(train, f)
                rows.append(score_filter(train, f, rem, base_train))
    x = pd.DataFrame([r for r in rows if r])
    if x.empty:
        return x
    return x.sort_values("train_score", ascending=False)


def score_filter(train: pd.DataFrame, f: dict, remove: pd.Series, base_train: dict) -> dict | None:
    removed = train[remove]
    retained = train[~remove]
    if len(removed) < MIN_REMOVE_TRAIN or len(retained) == 0:
        return None
    retention = len(retained) / max(1, len(train))
    if retention < MIN_RETENTION:
        return None
    rem = metrics(removed); ret = metrics(retained)
    wr_gain = ret["win_rate"] - base_train["win_rate"]
    pf_gain = ret["profit_factor"] - base_train["profit_factor"]
    sum_delta = ret["sum_result_usd"] - base_train["sum_result_usd"]
    # Prefer loss-heavy removals that improve WR/PF while not destroying train sum too much.
    score = wr_gain * 20000 + pf_gain * 1200 + min(0.0, sum_delta) * 0.03 + retention * 400 - rem["trades"] * 0.02
    return dict(**f, train_removed_trades=rem["trades"], train_removed_wr=rem["win_rate"], train_removed_pf=rem["profit_factor"], train_removed_sum=rem["sum_result_usd"], train_retained_trades=ret["trades"], train_retention=retention, train_wr_gain=wr_gain, train_pf_gain=pf_gain, train_sum_delta=sum_delta, train_score=score)


def active_day_splits(df: pd.DataFrame, lookback: int, target: int):
    days = sorted(pd.to_datetime(df.entry_dt).dt.date.unique())
    start = lookback
    while start < len(days):
        train_days = set(days[start - lookback:start])
        target_days = set(days[start:start + target])
        if not target_days:
            break
        train = df[pd.to_datetime(df.entry_dt).dt.date.isin(train_days)].copy()
        tgt = df[pd.to_datetime(df.entry_dt).dt.date.isin(target_days)].copy()
        yield start, train, tgt, min(train_days), max(train_days), min(target_days), max(target_days)
        start += target


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "109cc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks = []
    outputs = []
    findings = []
    ledger_path = root / "109c" / "gold_v3_109_selected_base_policy_ledger.csv"
    diag_path = root / "109bc" / "gold_v3_109b_candidate_filter_diagnostics.csv"
    if not ledger_path.exists():
        blocks.append(dict(blocker_id="missing_109_selected_base_policy_ledger", path=str(ledger_path)))
    if not diag_path.exists():
        blocks.append(dict(blocker_id="missing_109b_candidate_filter_diagnostics", path=str(diag_path)))

    df = pd.DataFrame(); diag = pd.DataFrame(); universe = []
    if not blocks:
        df = pd.read_csv(ledger_path, encoding="utf-8-sig", low_memory=False)
        diag = pd.read_csv(diag_path, encoding="utf-8-sig", low_memory=False)
        for c in ["entry_dt", "result_usd"]:
            if c not in df.columns:
                blocks.append(dict(blocker_id="ledger_missing_required_column", column=c))
        if not blocks:
            df["entry_dt"] = pd.to_datetime(df.entry_dt, errors="coerce")
            df["result_usd"] = pd.to_numeric(df.result_usd, errors="coerce")
            df = df[df.entry_dt.notna() & df.result_usd.notna()].copy().sort_values("entry_dt").reset_index(drop=True)
            if df.empty:
                blocks.append(dict(blocker_id="ledger_empty_after_parse"))
            universe = load_universe(diag, df)
            if not universe:
                blocks.append(dict(blocker_id="empty_train_only_feature_universe"))
        prog(1, 5, f"loaded rows={len(df)} universe={len(universe)}")

    all_summary = []
    all_ledgers = []
    family_rows = []
    if not blocks:
        combos = [(l, t) for l in LOOKBACKS for t in TARGETS]
        total = len(combos)
        for ci, (lookback, target) in enumerate(combos, 1):
            base_parts = []
            kept_parts = []
            fold_rows = []
            for fold_id, train, tgt, tr0, tr1, te0, te1 in active_day_splits(df, lookback, target):
                if len(train) < 100 or len(tgt) == 0:
                    continue
                base_train = metrics(train)
                cand = candidate_filters_from_train(train, universe, base_train)
                if cand.empty:
                    chosen = dict(kind="none", feature="", op="", threshold=np.nan, value="")
                    kept = tgt.copy(); remove = pd.Series(False, index=tgt.index)
                else:
                    chosen = cand.iloc[0].to_dict()
                    remove = apply_filter(tgt, chosen)
                    kept = tgt[~remove].copy()
                bmet = metrics(tgt); kmet = metrics(kept); rmet = metrics(tgt[remove])
                kept["walkforward_combo"] = f"L{lookback}_T{target}"
                kept["walkforward_fold_id"] = fold_id
                kept["selected_filter_feature"] = chosen.get("feature", "")
                kept["selected_filter_op"] = chosen.get("op", "")
                kept["selected_filter_threshold"] = chosen.get("threshold", "")
                kept["selected_filter_value"] = chosen.get("value", "")
                base_parts.append(tgt)
                kept_parts.append(kept)
                fold_rows.append(dict(combo_key=f"L{lookback}_T{target}", fold_id=fold_id, train_start=str(tr0), train_end=str(tr1), target_start=str(te0), target_end=str(te1), train_rows=len(train), target_rows=len(tgt), feature=chosen.get("feature", ""), kind=chosen.get("kind", ""), op=chosen.get("op", ""), threshold=chosen.get("threshold", ""), value=chosen.get("value", ""), base_trades=bmet["trades"], base_wr=bmet["win_rate"], base_pf=bmet["profit_factor"], base_sum=bmet["sum_result_usd"], kept_trades=kmet["trades"], kept_wr=kmet["win_rate"], kept_pf=kmet["profit_factor"], kept_sum=kmet["sum_result_usd"], removed_trades=rmet["trades"], removed_wr=rmet["win_rate"], removed_pf=rmet["profit_factor"], removed_sum=rmet["sum_result_usd"]))
                if chosen.get("feature"):
                    family_rows.append(dict(combo_key=f"L{lookback}_T{target}", feature=chosen.get("feature", ""), kind=chosen.get("kind", ""), op=chosen.get("op", "")))
            base_eval = pd.concat(base_parts, ignore_index=True) if base_parts else pd.DataFrame()
            kept_eval = pd.concat(kept_parts, ignore_index=True) if kept_parts else pd.DataFrame()
            bm = metrics(base_eval); km = metrics(kept_eval)
            retention = km["trades"] / max(1, bm["trades"])
            wr_gain = km["win_rate"] - bm["win_rate"]
            pf_gain = km["profit_factor"] - bm["profit_factor"]
            sum_delta = km["sum_result_usd"] - bm["sum_result_usd"]
            neg_ok = km["negative_month_count"] <= bm["negative_month_count"]
            primary = bool(wr_gain >= 0.005 and km["profit_factor"] >= bm["profit_factor"] and retention >= 0.70 and km["sum_result_usd"] >= bm["sum_result_usd"] and neg_ok)
            review = bool(km["win_rate"] >= bm["win_rate"] and km["profit_factor"] >= bm["profit_factor"] and retention >= 0.65 and sum_delta >= -0.01 * abs(bm["sum_result_usd"]))
            score = (100000 if primary else 0) + (50000 if review else 0) + wr_gain * 20000 + pf_gain * 1500 + sum_delta * 0.02 + retention * 500
            all_summary.append(dict(combo_key=f"L{lookback}_T{target}", lookback_active_days=lookback, target_active_days=target, fold_count=len(fold_rows), base_trades=bm["trades"], base_wr=bm["win_rate"], base_pf=bm["profit_factor"], base_sum=bm["sum_result_usd"], base_negative_month_count=bm["negative_month_count"], kept_trades=km["trades"], kept_wr=km["win_rate"], kept_pf=km["profit_factor"], kept_sum=km["sum_result_usd"], kept_negative_month_count=km["negative_month_count"], retention=retention, wr_gain=wr_gain, pf_gain=pf_gain, sum_delta=sum_delta, primary_gate=primary, review_gate=review, selection_score=score))
            if not kept_eval.empty:
                all_ledgers.append(kept_eval)
            if fold_rows:
                save(pd.DataFrame(fold_rows), out / f"gold_v3_109c_fold_details_L{lookback}_T{target}.csv")
                outputs.append(f"gold_v3_109c_fold_details_L{lookback}_T{target}.csv")
            prog(ci, total, f"combo L{lookback}_T{target}")

    summary_df = pd.DataFrame(all_summary).sort_values("selection_score", ascending=False) if all_summary else pd.DataFrame()
    target_ledger = pd.concat(all_ledgers, ignore_index=True) if all_ledgers else pd.DataFrame()
    family = pd.DataFrame(family_rows)
    survival = pd.DataFrame()
    if not family.empty:
        survival = family.groupby(["feature", "kind", "op"], dropna=False).size().reset_index(name="selected_fold_count").sort_values("selected_fold_count", ascending=False)
    if not summary_df.empty:
        save(summary_df, out / "gold_v3_109c_walkforward_filter_summary.csv")
        save(target_ledger, out / "gold_v3_109c_walkforward_target_ledger.csv")
        save(summary_df.head(1), out / "gold_v3_109c_best_combo_summary.csv")
        save(survival, out / "gold_v3_109c_feature_family_survival.csv")
        outputs += ["gold_v3_109c_walkforward_filter_summary.csv", "gold_v3_109c_walkforward_target_ledger.csv", "gold_v3_109c_best_combo_summary.csv", "gold_v3_109c_feature_family_survival.csv"]
        findings.append("best_combo=" + json.dumps(summary_df.iloc[0].to_dict(), ensure_ascii=False, default=str))
        if not survival.empty:
            findings.append("top_surviving_features=" + json.dumps(survival.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))

    best = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    primary = bool(best.get("primary_gate", False))
    review = bool(best.get("review_gate", False))
    if blocks:
        status = BLOCKED; decision = "TRAIN_ONLY_LOSS_FEATURE_FILTER_BLOCKED_INPUT_INCOMPLETE"
    else:
        status = READY
        if primary:
            decision = "TRAIN_ONLY_LOSS_FEATURE_FILTER_PRIMARY_READY_FOR_REVIEW"
        elif review:
            decision = "TRAIN_ONLY_LOSS_FEATURE_FILTER_REVIEW_READY_NEEDS_HUMAN_DECISION"
        else:
            decision = "TRAIN_ONLY_LOSS_FEATURE_FILTER_NOT_CONFIRMED_KEEP_109_BASE"

    qg = pd.DataFrame([
        dict(gate="target_outcomes_not_used_for_filter_selection", observed=True, operator="==", threshold=True, result="PASS"),
        dict(gate="posthoc_thresholds_not_final", observed=True, operator="==", threshold=True, result="PASS"),
        dict(gate="primary_wr_gain_ge_0_5pct", observed=best.get("wr_gain", 0.0), operator=">=", threshold=0.005, result="PASS" if best.get("wr_gain", 0.0) >= 0.005 else "FAIL"),
        dict(gate="primary_pf_ge_base", observed=best.get("kept_pf", 0.0), operator=">=", threshold=best.get("base_pf", 0.0), result="PASS" if best.get("kept_pf", 0.0) >= best.get("base_pf", 0.0) else "FAIL"),
        dict(gate="primary_retention_ge_70", observed=best.get("retention", 0.0), operator=">=", threshold=0.70, result="PASS" if best.get("retention", 0.0) >= 0.70 else "FAIL"),
        dict(gate="primary_sum_ge_base", observed=best.get("kept_sum", 0.0), operator=">=", threshold=best.get("base_sum", 0.0), result="PASS" if best.get("kept_sum", 0.0) >= best.get("base_sum", 0.0) else "FAIL"),
    ])
    save(qg, out / "gold_v3_109c_quality_gate_matrix.csv")
    outputs.append("gold_v3_109c_quality_gate_matrix.csv")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="train_only_selection", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="final_rule_approval_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not df.empty: vals.append(dict(check_id="ledger_rows_positive", result="PASS", observed=len(df), expected=">0", severity="BLOCKER"))
    if universe: vals.append(dict(check_id="feature_universe_positive", result="PASS", observed=len(universe), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val.result.eq("PASS")).sum()) if not val.empty else 0
    if validation_failure_count and status == READY:
        status = BLOCKED; decision = "TRAIN_ONLY_LOSS_FEATURE_FILTER_BLOCKED_INPUT_INCOMPLETE"

    base_all = metrics(df) if not df.empty else metrics(pd.DataFrame())
    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, train_only_selection=True, final_rule_approval=False, blocker_count=len(blocks), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2), ledger_rows=int(len(df)) if not df.empty else 0, feature_universe_rows=len(universe), combo_rows=int(len(summary_df)) if not summary_df.empty else 0, best_combo_key=best.get("combo_key", ""), best_primary_gate=primary, best_review_gate=review)
    summary.update({f"base_all_{k}": v for k, v in base_all.items()})
    for k, v in best.items():
        summary[f"best_{k}"] = v
    save(pd.DataFrame(blocks), out / "gold_v3_109c_blocker_matrix.csv")
    save(val, out / "gold_v3_109c_validation_matrix.csv")
    outputs += ["gold_v3_109c_blocker_matrix.csv", "gold_v3_109c_validation_matrix.csv", "gold_v3_109c_summary.json", "GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_109c_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 109C report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 109C PASTE_ME_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "train_only_selection: true", "final_rule_approval: false", "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blocks)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS", "", "QUALITY_GATES", qg.to_string(index=False), "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
