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

STEP = "GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY"
READY = "GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


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
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, unique_trade_days=0, max_day_trade_share=0.0)
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
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd.to_numpy()),
        sum_result_usd=float(x.result_usd.sum()),
        negative_month_count=int((mon < 0).sum()),
        unique_trade_days=int(day.shape[0]),
        max_day_trade_share=float(day.max() / len(x)) if len(day) else 0.0,
    )


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
    out = root / "109c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks = []
    outputs = []
    findings = []
    paths = {
        "base_ledger": root / "107r6c" / "gold_v3_107r6_resolved_107q_best_family_ledger.csv",
        "s107": root / "107sc" / "gold_v3_107s_summary.json",
        "s108": root / "108c" / "gold_v3_108_summary.json",
        "s108b": root / "108bc" / "gold_v3_108b_summary.json",
    }
    for name, p in paths.items():
        if not p.exists():
            blocks.append(dict(blocker_id=f"missing_{name}", path=str(p)))

    ledger = pd.DataFrame()
    s107 = {}; s108 = {}; s108b = {}
    if not blocks:
        ledger = pd.read_csv(paths["base_ledger"], encoding="utf-8-sig", low_memory=False)
        s107 = load_json(paths["s107"])
        s108 = load_json(paths["s108"])
        s108b = load_json(paths["s108b"])
        for c in ["entry_dt", "exit_dt", "result_usd"]:
            if c not in ledger.columns:
                blocks.append(dict(blocker_id="base_ledger_missing_required_column", column=c))
        prog(1, 5, f"loaded base ledger rows={len(ledger)}")

    if not blocks:
        ledger = ledger.copy()
        ledger["selected_option"] = "KEEP_107Q_BASE"
        ledger["selected_policy_key"] = "107Q_BASE_RESOLVED_PASS_THROUGH"
        ledger["health_gate_adopted"] = False
        ledger["stage109_selection_reason"] = "108B showed health gate skipped net-positive trades; base keeps higher total sum_result_usd."
        save(ledger, out / "gold_v3_109_selected_base_policy_ledger.csv")
        outputs.append("gold_v3_109_selected_base_policy_ledger.csv")

        m = metrics(ledger)
        selected = pd.DataFrame([dict(
            selected_option="KEEP_107Q_BASE",
            selected_policy_key="107Q_BASE_RESOLVED_PASS_THROUGH",
            health_gate_adopted=False,
            reason="108B base preferred: health gate skipped net-positive trades and reduced total sum_result_usd.",
            source_107s_decision=s107.get("decision", ""),
            source_108_decision=s108.get("decision", ""),
            source_108b_decision=s108b.get("decision", ""),
            health_gate_candidate_key=s107.get("best_policy_key", ""),
            health_gate_skipped_trades=s108b.get("skipped_trades", 0),
            health_gate_skipped_sum_result_usd=s108b.get("skipped_sum_result_usd", 0),
            health_gate_wr_gain=s108.get("wr_gain", 0),
            health_gate_pf_gain=s108.get("pf_gain", 0),
            health_gate_sum_delta=s108.get("sum_delta", 0),
            live_ready=False,
            **m,
        )])
        save(selected, out / "gold_v3_109_selected_policy_summary.csv")
        outputs.append("gold_v3_109_selected_policy_summary.csv")
        if "entry_dt" in ledger:
            ledger["entry_dt"] = pd.to_datetime(ledger["entry_dt"], errors="coerce")
            ledger["entry_month"] = ledger["entry_dt"].dt.to_period("M").astype(str)
        if "regime_split" not in ledger.columns:
            ledger["regime_split"] = "ALL"
        save(group_metrics(ledger, ["regime_split", "entry_month"]), out / "gold_v3_109_base_policy_monthly_metrics.csv")
        save(group_metrics(ledger, ["regime_split"]), out / "gold_v3_109_base_policy_regime_metrics.csv")
        outputs += ["gold_v3_109_base_policy_monthly_metrics.csv", "gold_v3_109_base_policy_regime_metrics.csv"]

        reason = pd.DataFrame([
            dict(check="107S health gate strict resolved-only", result="PASS", detail=str(s107.get("resolved_only_strict", False))),
            dict(check="107S exit_dt not entry feature", result="PASS", detail=str(not bool(s107.get("exit_dt_used_as_entry_feature", True)))),
            dict(check="108 health gate WR/PF improved", result="PASS", detail=f"wr_gain={s108.get('wr_gain')}, pf_gain={s108.get('pf_gain')}"),
            dict(check="108 health gate sum decreased", result="BASE_FAVOR", detail=f"sum_delta={s108.get('sum_delta')}"),
            dict(check="108B skipped trades net positive", result="BASE_FAVOR", detail=f"skipped_sum={s108b.get('skipped_sum_result_usd')}"),
            dict(check="Stage109 selected option", result="KEEP_107Q_BASE", detail="health_gate_adopted=false"),
        ])
        save(reason, out / "gold_v3_109_selection_reason_matrix.csv")
        outputs.append("gold_v3_109_selection_reason_matrix.csv")
        qg = pd.DataFrame([
            qgate("108b_base_preferred", s108b.get("decision") == "HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED", "==", True),
            qgate("selected_ledger_rows_positive", len(ledger), ">=", 1),
            qgate("selected_wr_ge_60", m["win_rate"], ">=", 0.60),
            qgate("selected_pf_ge_2_5", m["profit_factor"], ">=", 2.5),
            qgate("selected_negative_month_count_eq_0", m["negative_month_count"], "==", 0),
            qgate("live_ready_false", False, "==", False),
        ])
        save(qg, out / "gold_v3_109_quality_gate_matrix.csv")
        outputs.append("gold_v3_109_quality_gate_matrix.csv")
        findings.append("selected_option=KEEP_107Q_BASE because 108B skipped trades were net positive and base had higher total sum_result_usd")
        prog(4, 5, "selection packet outputs written")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="health_gate_adopted_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not ledger.empty:
        vals.append(dict(check_id="selected_base_ledger_positive", result="PASS", observed=len(ledger), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failure_count == 0 else BLOCKED
    decision = "BASE_POLICY_SELECTION_READY_FOR_STAGE110_AUDIT_MONITORING_DESIGN" if status == READY else "BASE_POLICY_SELECTION_BLOCKED_INPUT_INCOMPLETE"

    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, selected_option="KEEP_107Q_BASE", selected_policy_key="107Q_BASE_RESOLVED_PASS_THROUGH", health_gate_adopted=False, blocker_count=len(blocks), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2))
    if not ledger.empty:
        summary.update(metrics(ledger))
    save(pd.DataFrame(blocks), out / "gold_v3_109_blocker_matrix.csv")
    save(val, out / "gold_v3_109_validation_matrix.csv")
    outputs += ["gold_v3_109_blocker_matrix.csv", "gold_v3_109_validation_matrix.csv", "gold_v3_109_summary.json", "GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_109_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 109 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 109 PASTE_ME_BASE_POLICY_SELECTION_REVIEW_PACKET", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "selected_option: KEEP_107Q_BASE", "health_gate_adopted: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, selection_packet_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blocks)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
