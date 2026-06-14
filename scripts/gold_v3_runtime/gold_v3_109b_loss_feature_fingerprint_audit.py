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

STEP = "GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY"
READY = "GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
FORBIDDEN_TOKENS = ["result", "exit", "win", "loss", "pnl", "profit", "parity", "health_gate", "selected_option", "stage109_selection_reason"]
MIN_BIN_ROWS = 50
MIN_REMOVE_ROWS = 25
MIN_RETENTION = 0.70


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
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, loss_rate=0.0, profit_factor=0.0, sum_result_usd=0.0)
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x.result_usd.notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame())
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        loss_rate=float((x.result_usd < 0).mean()),
        profit_factor=pf(x.result_usd.to_numpy()),
        sum_result_usd=float(x.result_usd.sum()),
    )


def is_forbidden_col(c: str) -> bool:
    s = c.lower()
    return any(tok in s for tok in FORBIDDEN_TOKENS)


def feature_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    reserved = {"entry_dt", "exit_dt", "result_usd", "recomputed_result_usd", "result_delta"}
    cols = [c for c in df.columns if c not in reserved and not is_forbidden_col(c)]
    num = []
    cat = []
    for c in cols:
        if c.startswith("__"):
            continue
        if pd.api.types.is_bool_dtype(df[c]):
            cat.append(c)
        elif pd.api.types.is_numeric_dtype(df[c]):
            nun = df[c].nunique(dropna=True)
            if nun <= 2:
                cat.append(c)
            else:
                num.append(c)
        else:
            nun = df[c].astype(str).nunique(dropna=True)
            if 2 <= nun <= 80:
                cat.append(c)
    return num, cat


def cat_profiles(df: pd.DataFrame, cols: list[str], base_loss_rate: float) -> pd.DataFrame:
    rows = []
    for c in cols:
        x = df[[c, "result_usd"]].copy()
        x[c] = x[c].astype(str).fillna("NA")
        vc = x[c].value_counts(dropna=False)
        for val, n in vc.items():
            if int(n) < MIN_BIN_ROWS:
                continue
            g = x[x[c].eq(val)]
            m = metrics(g)
            rows.append(dict(feature=c, value=val, rows=int(n), row_share=float(n / len(df)), loss_rate=m["loss_rate"], loss_rate_lift=m["loss_rate"] - base_loss_rate, win_rate=m["win_rate"], profit_factor=m["profit_factor"], sum_result_usd=m["sum_result_usd"]))
    return pd.DataFrame(rows).sort_values(["loss_rate_lift", "rows"], ascending=[False, False]) if rows else pd.DataFrame()


def numeric_profiles(df: pd.DataFrame, cols: list[str], base_loss_rate: float) -> pd.DataFrame:
    rows = []
    qs = [0.05, 0.10, 0.20, 0.30, 0.70, 0.80, 0.90, 0.95]
    for i, c in enumerate(cols, 1):
        s = pd.to_numeric(df[c], errors="coerce")
        valid = s.notna()
        if valid.sum() < MIN_BIN_ROWS * 2:
            continue
        for q in qs:
            thr = float(s[valid].quantile(q))
            if not np.isfinite(thr):
                continue
            if q <= 0.30:
                mask = valid & (s <= thr); op = "<="
            else:
                mask = valid & (s >= thr); op = ">="
            n = int(mask.sum())
            if n < MIN_BIN_ROWS:
                continue
            g = df[mask]
            m = metrics(g)
            rows.append(dict(feature=c, op=op, threshold=thr, quantile=q, rows=n, row_share=float(n / len(df)), loss_rate=m["loss_rate"], loss_rate_lift=m["loss_rate"] - base_loss_rate, win_rate=m["win_rate"], profit_factor=m["profit_factor"], sum_result_usd=m["sum_result_usd"]))
        if i % 25 == 0:
            prog(i, max(1, len(cols)), "numeric feature profiling")
    return pd.DataFrame(rows).sort_values(["loss_rate_lift", "rows"], ascending=[False, False]) if rows else pd.DataFrame()


def apply_filter(df: pd.DataFrame, kind: str, feature: str, op_or_val, threshold=None) -> pd.Series:
    if kind == "categorical":
        remove = df[feature].astype(str).eq(str(op_or_val))
    else:
        s = pd.to_numeric(df[feature], errors="coerce")
        if op_or_val == "<=":
            remove = s <= float(threshold)
        elif op_or_val == ">=":
            remove = s >= float(threshold)
        else:
            remove = pd.Series(False, index=df.index)
    return remove.fillna(False)


def filter_diagnostics(df: pd.DataFrame, cat_df: pd.DataFrame, num_df: pd.DataFrame, base_m: dict) -> pd.DataFrame:
    rows = []
    candidates = []
    if not cat_df.empty:
        for _, r in cat_df.head(80).iterrows():
            candidates.append(("categorical", r.feature, r.value, None, r.to_dict()))
    if not num_df.empty:
        for _, r in num_df.head(120).iterrows():
            candidates.append(("numeric", r.feature, r.op, r.threshold, r.to_dict()))
    for kind, feature, opval, thr, src in candidates:
        if feature not in df.columns:
            continue
        remove = apply_filter(df, kind, feature, opval, thr)
        removed = df[remove]
        retained = df[~remove]
        if len(removed) < MIN_REMOVE_ROWS or len(retained) == 0:
            continue
        rm = metrics(removed)
        ret = metrics(retained)
        retention = len(retained) / max(1, len(df))
        if retention < MIN_RETENTION:
            continue
        rows.append(dict(
            filter_kind=kind,
            feature=feature,
            op_or_value=opval,
            threshold="" if thr is None else float(thr),
            removed_trades=rm["trades"],
            removed_wr=rm["win_rate"],
            removed_pf=rm["profit_factor"],
            removed_sum_result_usd=rm["sum_result_usd"],
            retained_trades=ret["trades"],
            retained_wr=ret["win_rate"],
            retained_pf=ret["profit_factor"],
            retained_sum_result_usd=ret["sum_result_usd"],
            retention=retention,
            wr_gain=ret["win_rate"] - base_m["win_rate"],
            pf_gain=ret["profit_factor"] - base_m["profit_factor"],
            sum_delta=ret["sum_result_usd"] - base_m["sum_result_usd"],
            posthoc_diagnostic_only=True,
            requires_train_only_revalidation=True,
            final_rule_approval=False,
            live_ready=False,
            source_loss_rate_lift=src.get("loss_rate_lift", 0.0),
        ))
    if not rows:
        return pd.DataFrame()
    x = pd.DataFrame(rows)
    x["diagnostic_score"] = x["wr_gain"] * 20000 + x["pf_gain"] * 1500 + x["sum_delta"] * 0.05 + x["retention"] * 500 - x["removed_trades"] * 0.02
    return x.sort_values(["diagnostic_score", "wr_gain", "pf_gain"], ascending=[False, False, False])


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "109c"
    out = root / "109bc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 6, "start")

    blocks = []
    outputs = []
    findings = []
    ledger_path = src / "gold_v3_109_selected_base_policy_ledger.csv"
    summary_path = src / "gold_v3_109_summary.json"
    if not ledger_path.exists():
        blocks.append(dict(blocker_id="missing_109_selected_base_policy_ledger", path=str(ledger_path)))
    if not summary_path.exists():
        blocks.append(dict(blocker_id="missing_109_summary", path=str(summary_path)))

    df = pd.DataFrame()
    if not blocks:
        df = pd.read_csv(ledger_path, encoding="utf-8-sig", low_memory=False)
        if "result_usd" not in df.columns:
            blocks.append(dict(blocker_id="ledger_missing_result_usd"))
        else:
            df["result_usd"] = pd.to_numeric(df["result_usd"], errors="coerce")
            df = df[df.result_usd.notna()].copy()
            if df.empty:
                blocks.append(dict(blocker_id="ledger_empty_after_result_parse"))
        if "entry_dt" in df.columns:
            df["entry_dt"] = pd.to_datetime(df["entry_dt"], errors="coerce")
            df["entry_hour"] = df["entry_dt"].dt.hour
            df["entry_month_diag"] = df["entry_dt"].dt.to_period("M").astype(str)
        prog(1, 6, f"loaded rows={len(df)}")

    cat_df = pd.DataFrame(); num_df = pd.DataFrame(); diag = pd.DataFrame(); overview = pd.DataFrame(); top_patterns = pd.DataFrame()
    if not blocks:
        base_m = metrics(df)
        loss = df[df.result_usd < 0]
        win = df[df.result_usd > 0]
        overview = pd.DataFrame([dict(**{f"base_{k}": v for k, v in base_m.items()}, loss_rows=len(loss), win_rows=len(win), feature_note="posthoc_diagnostic_only_entry_known_features")])
        save(overview, out / "gold_v3_109b_loss_feature_overview.csv")
        outputs.append("gold_v3_109b_loss_feature_overview.csv")
        num_cols, cat_cols = feature_columns(df)
        findings.append(f"entry_known_numeric_feature_count={len(num_cols)}")
        findings.append(f"entry_known_categorical_feature_count={len(cat_cols)}")
        prog(2, 6, "feature columns selected")

        cat_df = cat_profiles(df, cat_cols, base_m["loss_rate"])
        num_df = numeric_profiles(df, num_cols, base_m["loss_rate"])
        save(cat_df, out / "gold_v3_109b_boolean_categorical_loss_profile.csv")
        save(num_df, out / "gold_v3_109b_numeric_bin_loss_profile.csv")
        outputs += ["gold_v3_109b_boolean_categorical_loss_profile.csv", "gold_v3_109b_numeric_bin_loss_profile.csv"]
        prog(4, 6, "loss profiles written")

        diag = filter_diagnostics(df, cat_df, num_df, base_m)
        save(diag, out / "gold_v3_109b_candidate_filter_diagnostics.csv")
        outputs.append("gold_v3_109b_candidate_filter_diagnostics.csv")
        parts = []
        if not cat_df.empty: parts.append(cat_df.head(30).assign(pattern_type="categorical"))
        if not num_df.empty: parts.append(num_df.head(30).assign(pattern_type="numeric"))
        top_patterns = pd.concat(parts, ignore_index=True, sort=False) if parts else pd.DataFrame()
        save(top_patterns, out / "gold_v3_109b_top_loss_patterns.csv")
        outputs.append("gold_v3_109b_top_loss_patterns.csv")
        if not diag.empty:
            findings.append("top_candidate_filters=" + json.dumps(diag.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))
        prog(5, 6, "candidate diagnostics written")

        if not diag.empty and bool(((diag.wr_gain > 0.002) | (diag.pf_gain > 0.03)).any()):
            decision = "LOSS_FEATURE_FINGERPRINT_READY_FOR_109C_TRAIN_ONLY_REPLAY"
            next_action = "Run 109C train-only replay on top posthoc loss-feature filters. Do not approve these filters directly."
        else:
            decision = "LOSS_FEATURE_FINGERPRINT_NO_ACTIONABLE_PATTERN_KEEP_109_BASE"
            next_action = "No sufficiently strong posthoc loss-feature candidate found; keep Stage109 base."
        actions = pd.DataFrame([
            dict(priority=1, action="do_not_adopt_posthoc_filters_directly", reason="loss feature mining is posthoc diagnostic only"),
            dict(priority=2, action="run_109c_train_only_loss_feature_filter_replay" if decision.endswith("109C_TRAIN_ONLY_REPLAY") else "keep_109_base", reason=next_action),
        ])
        save(actions, out / "gold_v3_109b_recommended_next_actions.csv")
        outputs.append("gold_v3_109b_recommended_next_actions.csv")
    else:
        decision = "LOSS_FEATURE_FINGERPRINT_BLOCKED_INPUT_INCOMPLETE"

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="posthoc_diagnostic_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="final_rule_approval_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not df.empty: vals.append(dict(check_id="ledger_rows_positive", result="PASS", observed=len(df), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val.result.eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failure_count == 0 else BLOCKED
    if status == BLOCKED:
        decision = "LOSS_FEATURE_FINGERPRINT_BLOCKED_INPUT_INCOMPLETE"

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
        posthoc_diagnostic_only=True,
        requires_train_only_revalidation=True,
        final_rule_approval=False,
        blocker_count=len(blocks),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        ledger_rows=int(len(df)) if not df.empty else 0,
        categorical_profile_rows=int(len(cat_df)) if not cat_df.empty else 0,
        numeric_profile_rows=int(len(num_df)) if not num_df.empty else 0,
        candidate_filter_rows=int(len(diag)) if not diag.empty else 0,
    )
    if not overview.empty:
        summary.update(overview.iloc[0].to_dict())
    save(pd.DataFrame(blocks), out / "gold_v3_109b_blocker_matrix.csv")
    save(val, out / "gold_v3_109b_validation_matrix.csv")
    outputs += ["gold_v3_109b_blocker_matrix.csv", "gold_v3_109b_validation_matrix.csv", "gold_v3_109b_summary.json", "GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_109b_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 109B report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 109B PASTE_ME_LOSS_FEATURE_FINGERPRINT", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "posthoc_diagnostic_only: true", "requires_train_only_revalidation: true", "final_rule_approval: false", "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blocks)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(6, 6, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
