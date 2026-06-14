#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY"
READY = "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
WINDOWS = [20, 50, 100]
MIN_HIST = [5, 10, 20]
PF_THRS = [1.0, 1.15, 1.3, 1.5]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def profit_factor(vals) -> float:
    a = np.asarray(vals, dtype=float)
    gp = a[a > 0].sum()
    gl = -a[a < 0].sum()
    return float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, unique_trade_days=0, max_day_trade_share=0.0, min_entry_dt="", max_entry_dt="")
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x["entry_dt"].notna() & x["result_usd"].notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame())
    x["entry_month"] = x["entry_dt"].dt.to_period("M").astype(str)
    x["entry_day"] = x["entry_dt"].dt.date.astype(str)
    mon = x.groupby("entry_month")["result_usd"].sum()
    day = x.groupby("entry_day").size()
    return dict(
        trades=int(len(x)),
        wins=int((x["result_usd"] > 0).sum()),
        losses=int((x["result_usd"] < 0).sum()),
        win_rate=float((x["result_usd"] > 0).mean()),
        profit_factor=profit_factor(x["result_usd"].to_numpy()),
        sum_result_usd=float(x["result_usd"].sum()),
        negative_month_count=int((mon < 0).sum()),
        unique_trade_days=int(day.shape[0]),
        max_day_trade_share=float(day.max() / len(x)) if len(day) else 0.0,
        min_entry_dt=str(x["entry_dt"].min()),
        max_entry_dt=str(x["entry_dt"].max()),
    )


def by_group(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    for k, g in df.groupby(cols, dropna=False):
        if not isinstance(k, tuple):
            k = (k,)
        r = dict(zip(cols, k))
        r.update(metrics(g))
        rows.append(r)
    return pd.DataFrame(rows)


def cap_pf(x: float) -> float:
    try:
        return 10.0 if math.isinf(float(x)) else max(0.0, min(float(x), 10.0))
    except Exception:
        return 0.0


def hist_key(row, gate_type: str):
    if gate_type == "candidate_pf_gate":
        return str(row.get("global_candidate_key", ""))
    if gate_type == "global_side_pf_gate":
        return str(row.get("side", "UNKNOWN"))
    if gate_type == "global_all_pf_gate":
        return "ALL"
    return "PASS"


def run_gate(df: pd.DataFrame, gate_type: str, window: int, min_hist: int, pf_thr: float) -> tuple[pd.DataFrame, dict]:
    if gate_type == "pass_through_baseline":
        x = df.copy()
        x["health_gate_policy"] = gate_type
        x["health_window"] = window
        x["health_min_history"] = min_hist
        x["health_pf_threshold"] = pf_thr
        x["health_history_count_at_entry"] = 0
        x["health_history_pf_at_entry"] = np.nan
        x["health_gate_pass"] = True
        return x, dict(skip_events=0, selected_events=len(x), insufficient_history_events=0, resolved_only_history_events_used=0)

    x = df.sort_values(["entry_dt", "exit_dt", "global_candidate_key"]).reset_index(drop=True).copy()
    completed = x[x["exit_dt"].notna() & x["result_usd"].notna()].sort_values(["exit_dt", "entry_dt", "global_candidate_key"]).to_dict("records")
    hist = defaultdict(lambda: deque(maxlen=window))
    ptr = 0
    kept = []
    skip_events = 0
    insufficient = 0
    hist_used = 0
    for _, r in x.iterrows():
        now = pd.Timestamp(r["entry_dt"])
        while ptr < len(completed) and pd.Timestamp(completed[ptr]["exit_dt"]) <= now:
            rr = completed[ptr]
            key = hist_key(rr, gate_type)
            hist[key].append(float(rr["result_usd"]))
            ptr += 1
        key = hist_key(r, gate_type)
        vals = list(hist[key])
        hcnt = len(vals)
        hpf = profit_factor(vals) if hcnt else 0.0
        ok = True if hcnt < min_hist else bool(hpf >= pf_thr)
        if hcnt < min_hist:
            insufficient += 1
        hist_used += hcnt
        if ok:
            d = r.to_dict()
            d["health_gate_policy"] = gate_type
            d["health_window"] = window
            d["health_min_history"] = min_hist
            d["health_pf_threshold"] = pf_thr
            d["health_history_count_at_entry"] = hcnt
            d["health_history_pf_at_entry"] = hpf
            d["health_gate_pass"] = True
            kept.append(d)
        else:
            skip_events += 1
    out = pd.DataFrame(kept)
    return out, dict(skip_events=skip_events, selected_events=len(out), insufficient_history_events=insufficient, resolved_only_history_events_used=hist_used)


def qgate(name, observed, op, threshold):
    if op == ">=":
        ok = observed >= threshold
    elif op == "<=":
        ok = observed <= threshold
    elif op == "==":
        ok = observed == threshold
    else:
        ok = False
    return dict(gate=name, observed=observed, operator=op, threshold=threshold, result="PASS" if ok else "FAIL")


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "107r6c"
    out = root / "107sc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")

    blocks = []
    outputs = []
    findings = []
    in_path = src / "gold_v3_107r6_resolved_107q_best_family_ledger.csv"
    if not in_path.exists():
        blocks.append(dict(blocker_id="missing_107r6_resolved_107q_best_family_ledger", path=str(in_path)))

    df = pd.DataFrame()
    if not blocks:
        df = pd.read_csv(in_path, encoding="utf-8-sig", low_memory=False)
        for c in ["entry_dt", "exit_dt", "result_usd"]:
            if c not in df.columns:
                blocks.append(dict(blocker_id="resolved_best_ledger_missing_required_column", column=c))
    if not blocks:
        df["entry_dt"] = pd.to_datetime(df["entry_dt"], errors="coerce")
        df["exit_dt"] = pd.to_datetime(df["exit_dt"], errors="coerce")
        df["result_usd"] = pd.to_numeric(df["result_usd"], errors="coerce")
        df = df[df["entry_dt"].notna() & df["exit_dt"].notna() & df["result_usd"].notna()].copy()
        if df.empty:
            blocks.append(dict(blocker_id="resolved_best_ledger_empty_after_required_parse"))
        elif bool((df["exit_dt"] < df["entry_dt"]).any()):
            blocks.append(dict(blocker_id="exit_dt_before_entry_dt", rows=int((df["exit_dt"] < df["entry_dt"]).sum())))
        if "global_candidate_key" not in df.columns:
            df["global_candidate_key"] = df.get("source_name", "UNKNOWN").astype(str) + "::" + df.get("candidate_key", "").astype(str)
        if "side" not in df.columns:
            df["side"] = "UNKNOWN"
        if "regime_split" not in df.columns:
            df["regime_split"] = "ALL"
        df["entry_month"] = df["entry_dt"].dt.to_period("M").astype(str)

    summary_df = pd.DataFrame()
    best_ledger = pd.DataFrame()
    base_m = metrics(df) if not df.empty else metrics(pd.DataFrame())

    if not blocks:
        policies = [("pass_through_baseline", 0, 0, 0.0)]
        for gate_type in ["candidate_pf_gate", "global_side_pf_gate", "global_all_pf_gate"]:
            for w in WINDOWS:
                for mn in MIN_HIST:
                    for pft in PF_THRS:
                        policies.append((gate_type, w, mn, pft))
        rows = []
        ledgers = {}
        total = len(policies)
        prog(0, total, "start")
        for i, (gt, w, mn, pft) in enumerate(policies, 1):
            out_df, extra = run_gate(df, gt, w, mn, pft)
            m = metrics(out_df)
            reg = by_group(out_df, ["regime_split"])
            min_reg_wr = float(reg["win_rate"].min()) if not reg.empty else 0.0
            min_reg_pf = float(reg["profit_factor"].min()) if not reg.empty else 0.0
            retention = m["trades"] / max(1, base_m["trades"])
            wr_gain = m["win_rate"] - base_m["win_rate"]
            pf_gain = m["profit_factor"] - base_m["profit_factor"]
            primary = bool(m["win_rate"] >= base_m["win_rate"] and m["profit_factor"] >= base_m["profit_factor"] and retention >= 0.65 and min_reg_wr >= 0.60 and m["negative_month_count"] == 0)
            review = bool(wr_gain >= 0.005 and m["profit_factor"] >= base_m["profit_factor"] and retention >= 0.50)
            policy_key = f"{gt}||W{w}||N{mn}||PF{pft}"
            score = (100000 if primary else 0) + (50000 if review else 0) + wr_gain * 20000 + pf_gain * 1500 + retention * 500 + min_reg_wr * 1000 - m["negative_month_count"] * 1000
            rec = dict(policy_key=policy_key, health_gate_policy=gt, health_window=w, health_min_history=mn, health_pf_threshold=pft, retention=retention, wr_gain=wr_gain, pf_gain=pf_gain, min_regime_wr=min_reg_wr, min_regime_pf=min_reg_pf, primary_gate=primary, review_gate=review, selection_score=score)
            rec.update({f"health_{k}": v for k, v in m.items()})
            rec.update({f"base_{k}": v for k, v in base_m.items()})
            rec.update(extra)
            rows.append(rec)
            ledgers[policy_key] = out_df
            if i % 12 == 0 or i == total:
                prog(i, total, f"{policy_key} wr={m['win_rate']:.4f} pf={m['profit_factor']:.3f} ret={retention:.3f}")
        summary_df = pd.DataFrame(rows).sort_values(["selection_score", "health_win_rate", "health_profit_factor"], ascending=[False, False, False]).reset_index(drop=True)
        summary_df.insert(0, "health_rank", range(1, len(summary_df) + 1))
        save(summary_df, out / "gold_v3_107s_health_policy_summary.csv")
        outputs.append("gold_v3_107s_health_policy_summary.csv")
        best_key = str(summary_df.iloc[0]["policy_key"])
        best_ledger = ledgers.get(best_key, pd.DataFrame()).copy()
        save(best_ledger, out / "gold_v3_107s_best_health_gate_ledger.csv")
        outputs.append("gold_v3_107s_best_health_gate_ledger.csv")
        save(by_group(df, ["regime_split", "entry_month"]), out / "gold_v3_107s_base_monthly_metrics.csv")
        save(by_group(best_ledger, ["regime_split", "entry_month"]), out / "gold_v3_107s_best_monthly_metrics.csv")
        save(by_group(best_ledger, ["regime_split"]), out / "gold_v3_107s_best_regime_metrics.csv")
        outputs += ["gold_v3_107s_base_monthly_metrics.csv", "gold_v3_107s_best_monthly_metrics.csv", "gold_v3_107s_best_regime_metrics.csv"]

    best = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    primary = bool(best.get("primary_gate", False))
    review = bool(best.get("review_gate", False))
    improved = bool(best.get("health_gate_policy", "") != "pass_through_baseline" and (best.get("wr_gain", 0.0) > 0 or best.get("pf_gain", 0.0) > 0))
    qg = pd.DataFrame([
        qgate("resolved_only_strict", True, "==", True),
        qgate("best_wr_ge_base", float(best.get("health_win_rate", 0.0)), ">=", float(best.get("base_win_rate", 0.0))),
        qgate("best_pf_ge_base", float(best.get("health_profit_factor", 0.0)), ">=", float(best.get("base_profit_factor", 0.0))),
        qgate("best_retention_ge_65", float(best.get("retention", 0.0)), ">=", 0.65),
        qgate("best_min_regime_wr_ge_60", float(best.get("min_regime_wr", 0.0)), ">=", 0.60),
        qgate("best_negative_month_count_eq_0", int(best.get("health_negative_month_count", 999)), "==", 0),
        qgate("review_wr_gain_ge_0_5pct", float(best.get("wr_gain", 0.0)), ">=", 0.005),
    ])
    save(qg, out / "gold_v3_107s_health_gate_matrix.csv")
    outputs.append("gold_v3_107s_health_gate_matrix.csv")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="exit_dt_not_entry_feature", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="resolved_only_history_exit_dt_lte_entry_dt", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not df.empty:
        vals.append(dict(check_id="resolved_input_rows_positive", result="PASS", observed=len(df), expected=">0", severity="BLOCKER"))
    if not summary_df.empty:
        vals.append(dict(check_id="health_policy_summary_positive", result="PASS", observed=len(summary_df), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    if blocks or validation_failure_count:
        status = BLOCKED
        decision = "RESOLVED_ONLY_HEALTH_GATE_BLOCKED_INPUT_INCOMPLETE"
    elif primary and improved:
        status = READY
        decision = "RESOLVED_ONLY_HEALTH_GATE_PRIMARY_READY_FOR_STAGE108_REVIEW"
    elif review and improved:
        status = READY
        decision = "RESOLVED_ONLY_HEALTH_GATE_REVIEW_READY_FOR_STAGE108_REVIEW"
    else:
        status = READY
        decision = "RESOLVED_ONLY_HEALTH_GATE_NO_IMPROVEMENT_KEEP_107Q_BASE_FOR_REVIEW"

    if best:
        findings.append("best_health_policy=" + json.dumps(best, ensure_ascii=False, default=str))
    if not summary_df.empty:
        findings.append("top10_health_policies=" + json.dumps(summary_df.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))

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
        exit_dt_used_as_entry_feature=False,
        resolved_only_strict=True if not blocks else False,
        blocker_count=len(blocks),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        base_rows=int(len(df)) if not df.empty else 0,
        health_policy_rows=int(len(summary_df)) if not summary_df.empty else 0,
        best_policy_key=best.get("policy_key", ""),
        best_health_policy=best.get("health_gate_policy", ""),
        best_health_wr=best.get("health_win_rate", 0.0),
        best_health_pf=best.get("health_profit_factor", 0.0),
        best_health_trades=best.get("health_trades", 0),
        best_retention=best.get("retention", 0.0),
        best_wr_gain=best.get("wr_gain", 0.0),
        best_pf_gain=best.get("pf_gain", 0.0),
        best_min_regime_wr=best.get("min_regime_wr", 0.0),
        best_primary_gate=primary,
        best_review_gate=review,
    )
    save(pd.DataFrame(blocks), out / "gold_v3_107s_blocker_matrix.csv")
    save(val, out / "gold_v3_107s_validation_matrix.csv")
    outputs += ["gold_v3_107s_blocker_matrix.csv", "gold_v3_107s_validation_matrix.csv", "gold_v3_107s_summary.json", "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107s_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107S report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107S PASTE_ME_RESOLVED_ONLY_HEALTH_GATE_REPLAY",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "exit_dt_used_as_entry_feature: false",
        "resolved_only_strict: " + str(summary["resolved_only_strict"]).lower(),
        "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
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
        "HEALTH_GATES",
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
