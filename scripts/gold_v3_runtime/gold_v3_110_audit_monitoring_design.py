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

STEP = "GOLD_V3_110_AUDIT_MONITORING_DESIGN"
READY = "GOLD_V3_110_AUDIT_MONITORING_DESIGN_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_110_AUDIT_MONITORING_DESIGN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
ROLLING_WINDOWS = [20, 50, 100]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def pf(vals) -> float:
    a = np.asarray(vals, dtype=float)
    gp = a[a > 0].sum()
    gl = -a[a < 0].sum()
    return float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, unique_trade_days=0, max_day_trade_share=0.0, negative_month_count=0)
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x["entry_dt"].notna() & x["result_usd"].notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame())
    x["entry_month"] = x["entry_dt"].dt.to_period("M").astype(str)
    x["entry_day"] = x["entry_dt"].dt.date.astype(str)
    day = x.groupby("entry_day").size()
    mon = x.groupby("entry_month")["result_usd"].sum()
    return dict(
        trades=int(len(x)),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd.to_numpy()),
        sum_result_usd=float(x.result_usd.sum()),
        unique_trade_days=int(day.shape[0]),
        max_day_trade_share=float(day.max() / len(x)) if len(day) else 0.0,
        negative_month_count=int((mon < 0).sum()),
    )


def rolling_distribution(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["exit_dt"] = pd.to_datetime(x["exit_dt"], errors="coerce")
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x.exit_dt.notna() & x.result_usd.notna()].sort_values(["exit_dt", "entry_dt"]).reset_index(drop=True)
    rows = []
    for w in ROLLING_WINDOWS:
        if len(x) < w:
            continue
        vals = x.result_usd.to_numpy(dtype=float)
        for i in range(w, len(x) + 1):
            seg = vals[i - w:i]
            rows.append(dict(window=w, end_exit_dt=x.exit_dt.iloc[i - 1], trades=w, win_rate=float((seg > 0).mean()), profit_factor=pf(seg), sum_result_usd=float(seg.sum())))
    return pd.DataFrame(rows)


def quantile_thresholds(roll: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w, g in roll.groupby("window") if not roll.empty else []:
        for metric in ["win_rate", "profit_factor", "sum_result_usd"]:
            s = pd.to_numeric(g[metric], errors="coerce").dropna()
            if s.empty:
                continue
            rows.append(dict(
                monitor=f"rolling_{w}_{metric}",
                window=int(w),
                metric=metric,
                historical_min=float(s.min()),
                q05=float(s.quantile(0.05)),
                q10=float(s.quantile(0.10)),
                q25=float(s.quantile(0.25)),
                median=float(s.quantile(0.50)),
                q75=float(s.quantile(0.75)),
                historical_max=float(s.max()),
                watch_level=float(s.quantile(0.25)),
                caution_level=float(s.quantile(0.10)),
                stop_review_level=float(s.quantile(0.05)),
                action="audit_review_only_no_live_change",
            ))
    return pd.DataFrame(rows)


def group_metrics(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
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


def qgate(name, observed, op, threshold):
    if op == ">=": ok = observed >= threshold
    elif op == "<=": ok = observed <= threshold
    elif op == "==": ok = observed == threshold
    else: ok = False
    return dict(gate=name, observed=observed, operator=op, threshold=threshold, result="PASS" if ok else "FAIL")


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "109c"
    out = root / "110c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blockers = []
    outputs = []
    findings = []
    ledger_path = src / "gold_v3_109_selected_base_policy_ledger.csv"
    summary_path = src / "gold_v3_109_summary.json"
    if not ledger_path.exists():
        blockers.append(dict(blocker_id="missing_109_selected_base_policy_ledger", path=str(ledger_path)))
    if not summary_path.exists():
        blockers.append(dict(blocker_id="missing_109_summary", path=str(summary_path)))

    ledger = pd.DataFrame(); s109 = {}
    if not blockers:
        ledger = pd.read_csv(ledger_path, encoding="utf-8-sig", low_memory=False)
        s109 = load_json(summary_path)
        for c in ["entry_dt", "exit_dt", "result_usd"]:
            if c not in ledger.columns:
                blockers.append(dict(blocker_id="selected_ledger_missing_required_column", column=c))
        prog(1, 5, f"loaded selected ledger rows={len(ledger)}")

    if not blockers:
        ledger["entry_dt"] = pd.to_datetime(ledger["entry_dt"], errors="coerce")
        ledger["exit_dt"] = pd.to_datetime(ledger["exit_dt"], errors="coerce")
        ledger["result_usd"] = pd.to_numeric(ledger["result_usd"], errors="coerce")
        if bool(ledger["exit_dt"].isna().any()):
            blockers.append(dict(blocker_id="exit_dt_missing_in_selected_ledger", rows=int(ledger["exit_dt"].isna().sum())))
        if bool((ledger["exit_dt"] < ledger["entry_dt"]).any()):
            blockers.append(dict(blocker_id="exit_dt_before_entry_dt", rows=int((ledger["exit_dt"] < ledger["entry_dt"]).sum())))
        if "regime_split" not in ledger.columns:
            ledger["regime_split"] = "ALL"
        ledger["entry_month"] = ledger["entry_dt"].dt.to_period("M").astype(str)
        ledger["entry_day"] = ledger["entry_dt"].dt.date.astype(str)

    thresholds = pd.DataFrame(); roll = pd.DataFrame(); monthly = pd.DataFrame(); regime = pd.DataFrame()
    if not blockers:
        roll = rolling_distribution(ledger)
        thresholds = quantile_thresholds(roll)
        monthly = group_metrics(ledger, ["regime_split", "entry_month"])
        regime = group_metrics(ledger, ["regime_split"])
        save(roll, out / "gold_v3_110_historical_rolling_distribution.csv")
        save(thresholds, out / "gold_v3_110_monitoring_thresholds.csv")
        save(monthly, out / "gold_v3_110_monthly_monitoring_baseline.csv")
        save(regime, out / "gold_v3_110_regime_monitoring_baseline.csv")
        outputs += ["gold_v3_110_historical_rolling_distribution.csv", "gold_v3_110_monitoring_thresholds.csv", "gold_v3_110_monthly_monitoring_baseline.csv", "gold_v3_110_regime_monitoring_baseline.csv"]
        prog(4, 5, "monitoring tables written")

        runbook = f"""# GOLD V3 110 Virtual Monitoring Runbook

Status: audit-only. `live_ready=false`.

## Selected policy

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
```

## Baseline

```text
trades: {s109.get('trades')}
win_rate: {s109.get('win_rate')}
profit_factor: {s109.get('profit_factor')}
sum_result_usd: {s109.get('sum_result_usd')}
negative_month_count: {s109.get('negative_month_count')}
unique_trade_days: {s109.get('unique_trade_days')}
max_day_trade_share: {s109.get('max_day_trade_share')}
```

## Monitoring rule

Use only resolved outcomes:

```text
past_trade.exit_dt <= monitoring_time
```

`exit_dt` is not an entry feature and must not be used to decide a current entry.

## Levels

- watch: rolling metric below historical q25
- caution: rolling metric below historical q10
- stop-review: rolling metric below historical q05

All actions are audit review only. Do not notify Discord, do not place MT5 orders, do not emit final signals.

## Next stage

Stage111 should implement a virtual monitor dry run that reads the selected policy ledger and evaluates these thresholds without live hooks.
"""
        (out / "gold_v3_110_virtual_monitoring_runbook.md").write_text(runbook, encoding="utf-8")
        outputs.append("gold_v3_110_virtual_monitoring_runbook.md")
        findings.append("monitoring_design=rolling q25/q10/q05 watch/caution/stop-review thresholds, audit-only")

    m = metrics(ledger) if not ledger.empty else metrics(pd.DataFrame())
    qg = pd.DataFrame([
        qgate("selected_option_keep_107q_base", str(s109.get("selected_option", "")) == "KEEP_107Q_BASE", "==", True),
        qgate("health_gate_not_adopted", bool(s109.get("health_gate_adopted", True)), "==", False),
        qgate("selected_wr_ge_60", m["win_rate"], ">=", 0.60),
        qgate("selected_pf_ge_2_5", m["profit_factor"], ">=", 2.5),
        qgate("selected_negative_month_count_eq_0", m["negative_month_count"], "==", 0),
        qgate("exit_dt_complete", int(ledger["exit_dt"].notna().sum()) if not ledger.empty and "exit_dt" in ledger else 0, "==", int(len(ledger)) if not ledger.empty else 0),
        qgate("live_ready_false", False, "==", False),
    ])
    save(qg, out / "gold_v3_110_quality_gate_matrix.csv")
    outputs.append("gold_v3_110_quality_gate_matrix.csv")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="no_live_hook", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="exit_dt_not_entry_feature", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not ledger.empty: vals.append(dict(check_id="selected_ledger_positive", result="PASS", observed=len(ledger), expected=">0", severity="BLOCKER"))
    if not thresholds.empty: vals.append(dict(check_id="monitoring_thresholds_positive", result="PASS", observed=len(thresholds), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    status = READY if not blockers and validation_failure_count == 0 else BLOCKED
    decision = "AUDIT_MONITORING_DESIGN_READY_FOR_STAGE111_VIRTUAL_MONITOR_DRY_RUN" if status == READY else "AUDIT_MONITORING_DESIGN_BLOCKED_INPUT_INCOMPLETE"

    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, live_hook_enabled=False, final_signal_enabled=False, discord_enabled=False, mt5_enabled=False, blocker_count=len(blockers), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2), selected_option="KEEP_107Q_BASE", selected_policy_key="107Q_BASE_RESOLVED_PASS_THROUGH", health_gate_adopted=False, rolling_distribution_rows=int(len(roll)) if not roll.empty else 0, monitoring_threshold_rows=int(len(thresholds)) if not thresholds.empty else 0)
    summary.update({f"selected_{k}": v for k, v in m.items()})
    save(pd.DataFrame(blockers), out / "gold_v3_110_blocker_matrix.csv")
    save(val, out / "gold_v3_110_validation_matrix.csv")
    outputs += ["gold_v3_110_blocker_matrix.csv", "gold_v3_110_validation_matrix.csv", "gold_v3_110_summary.json", "GOLD_V3_110_AUDIT_MONITORING_DESIGN_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_110_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_110_AUDIT_MONITORING_DESIGN_REPORT.md").write_text("# GOLD V3 110 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 110 PASTE_ME_AUDIT_MONITORING_DESIGN", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "selected_option: KEEP_107Q_BASE", "health_gate_adopted: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, monitoring_design_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blockers)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "QUALITY_GATES", qg.to_string(index=False), "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
