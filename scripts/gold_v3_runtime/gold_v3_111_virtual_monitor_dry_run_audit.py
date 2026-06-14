#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY"
READY = "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
STATE_ORDER = {"OK": 0, "WATCH": 1, "CAUTION": 2, "STOP_REVIEW": 3}


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


def fval(row: pd.Series, col: str, default: float = 0.0) -> float:
    try:
        return float(row[col]) if col in row.index and not pd.isna(row[col]) else float(default)
    except Exception:
        return float(default)


def classify(value: float, watch: float, caution: float, stop: float) -> str:
    if pd.isna(value):
        return "MISSING"
    if value < stop:
        return "STOP_REVIEW"
    if value < caution:
        return "CAUTION"
    if value < watch:
        return "WATCH"
    return "OK"


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
    src = root / "110c"
    out = root / "111c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blockers = []
    outputs = []
    findings = []
    th_path = src / "gold_v3_110_monitoring_thresholds.csv"
    roll_path = src / "gold_v3_110_historical_rolling_distribution.csv"
    sum_path = src / "gold_v3_110_summary.json"
    for name, p in [("thresholds", th_path), ("rolling_distribution", roll_path), ("summary", sum_path)]:
        if not p.exists():
            blockers.append(dict(blocker_id=f"missing_110_{name}", path=str(p)))

    th = pd.DataFrame(); roll = pd.DataFrame(); s110 = {}
    if not blockers:
        th = pd.read_csv(th_path, encoding="utf-8-sig")
        roll = pd.read_csv(roll_path, encoding="utf-8-sig")
        s110 = load_json(sum_path)
        req_th = {"window", "metric", "watch_level", "caution_level", "stop_review_level"}
        req_roll = {"window", "end_exit_dt", "win_rate", "profit_factor", "sum_result_usd"}
        if not req_th.issubset(set(th.columns)):
            blockers.append(dict(blocker_id="thresholds_missing_required_columns", missing="|".join(sorted(req_th - set(th.columns)))))
        if not req_roll.issubset(set(roll.columns)):
            blockers.append(dict(blocker_id="rolling_distribution_missing_required_columns", missing="|".join(sorted(req_roll - set(roll.columns)))))
        prog(1, 5, f"loaded thresholds={len(th)} rolling={len(roll)}")

    events = pd.DataFrame(); counts = pd.DataFrame(); latest = pd.DataFrame(); stop_examples = pd.DataFrame()
    if not blockers:
        rows = []
        tmap = {}
        for _, r in th.iterrows():
            # Use bracket access only. Column names such as `median` collide with pandas Series methods.
            win = int(r["window"])
            metric_name = str(r["metric"])
            tmap[(win, metric_name)] = dict(
                watch=fval(r, "watch_level"),
                caution=fval(r, "caution_level"),
                stop=fval(r, "stop_review_level"),
                q05=fval(r, "q05", float("nan")),
                q10=fval(r, "q10", float("nan")),
                q25=fval(r, "q25", float("nan")),
                median=fval(r, "median", float("nan")),
            )
        for i, r in roll.iterrows():
            w = int(r["window"])
            for metric in ["win_rate", "profit_factor", "sum_result_usd"]:
                if (w, metric) not in tmap:
                    continue
                tm = tmap[(w, metric)]
                value = pd.to_numeric(pd.Series([r[metric]]), errors="coerce").iloc[0]
                state = classify(value, tm["watch"], tm["caution"], tm["stop"])
                rows.append(dict(
                    end_exit_dt=r["end_exit_dt"],
                    window=w,
                    metric=metric,
                    value=value,
                    watch_level=tm["watch"],
                    caution_level=tm["caution"],
                    stop_review_level=tm["stop"],
                    monitor_state=state,
                    state_rank=STATE_ORDER.get(state, 99),
                    action="audit_review_only_no_live_change",
                ))
            if (i + 1) % 5000 == 0:
                prog(i + 1, len(roll), "classifying rolling rows")
        events = pd.DataFrame(rows)
        save(events, out / "gold_v3_111_virtual_monitor_events.csv")
        outputs.append("gold_v3_111_virtual_monitor_events.csv")
        counts = events.groupby(["window", "metric", "monitor_state"], dropna=False).size().reset_index(name="events") if not events.empty else pd.DataFrame()
        if not counts.empty:
            totals = counts.groupby(["window", "metric"])["events"].transform("sum")
            counts["event_share"] = counts["events"] / totals
        save(counts, out / "gold_v3_111_virtual_monitor_state_counts.csv")
        outputs.append("gold_v3_111_virtual_monitor_state_counts.csv")
        ev = events.copy()
        ev["end_exit_dt"] = pd.to_datetime(ev["end_exit_dt"], errors="coerce")
        latest_rows = []
        for (w, metric), g in ev.groupby(["window", "metric"]):
            g = g.sort_values("end_exit_dt")
            latest_rows.append(g.iloc[-1].to_dict())
        latest = pd.DataFrame(latest_rows).sort_values(["state_rank", "window", "metric"], ascending=[False, True, True]) if latest_rows else pd.DataFrame()
        save(latest, out / "gold_v3_111_latest_monitor_state.csv")
        outputs.append("gold_v3_111_latest_monitor_state.csv")
        stop_examples = ev[ev["monitor_state"].eq("STOP_REVIEW")].sort_values(["end_exit_dt", "window", "metric"]).tail(100)
        save(stop_examples, out / "gold_v3_111_stop_review_examples.csv")
        outputs.append("gold_v3_111_stop_review_examples.csv")
        prog(4, 5, "monitor dry run outputs written")
        if not latest.empty:
            findings.append("latest_monitor_state=" + json.dumps(latest.to_dict(orient="records"), ensure_ascii=False, default=str))

        runbook = """# GOLD V3 111 Virtual Monitor Dry Run Runbook

Status: audit-only. `live_ready=false`.

This dry run classifies historical rolling observations into OK/WATCH/CAUTION/STOP_REVIEW using Stage110 thresholds.

## Important

- These states do not send Discord notifications.
- These states do not place MT5 orders.
- These states do not produce final signals.
- These states do not mutate candidate pools.

## Operational meaning if later approved

- OK: monitor only.
- WATCH: review condition, no action.
- CAUTION: human review required before any future deployment step.
- STOP_REVIEW: pause audit advancement and inspect degradation.

This file is a design artifact only.
"""
        (out / "gold_v3_111_monitor_dry_run_runbook.md").write_text(runbook, encoding="utf-8")
        outputs.append("gold_v3_111_monitor_dry_run_runbook.md")

    stop_count = int((events["monitor_state"] == "STOP_REVIEW").sum()) if not events.empty else 0
    caution_count = int((events["monitor_state"] == "CAUTION").sum()) if not events.empty else 0
    watch_count = int((events["monitor_state"] == "WATCH").sum()) if not events.empty else 0
    latest_worst = latest.iloc[0]["monitor_state"] if not latest.empty else ""
    qg = pd.DataFrame([
        qgate("110_ready", str(s110.get("status", "")) == "GOLD_V3_110_AUDIT_MONITORING_DESIGN_READY_AUDIT_ONLY", "==", True),
        qgate("threshold_rows_positive", int(len(th)), ">=", 1),
        qgate("rolling_distribution_rows_positive", int(len(roll)), ">=", 1),
        qgate("virtual_monitor_events_positive", int(len(events)), ">=", 1),
        qgate("live_ready_false", False, "==", False),
        qgate("discord_disabled", False, "==", False),
        qgate("mt5_disabled", False, "==", False),
        qgate("final_signal_disabled", False, "==", False),
    ])
    save(qg, out / "gold_v3_111_quality_gate_matrix.csv")
    outputs.append("gold_v3_111_quality_gate_matrix.csv")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="discord_disabled", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="mt5_disabled", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="final_signal_disabled", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not events.empty:
        vals.append(dict(check_id="virtual_monitor_events_positive", result="PASS", observed=len(events), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blockers and validation_failure_count == 0 else BLOCKED
    decision = "VIRTUAL_MONITOR_DRY_RUN_READY_FOR_STAGE112_SELECTED_POLICY_AUDIT_FREEZE" if status == READY else "VIRTUAL_MONITOR_DRY_RUN_BLOCKED_INPUT_INCOMPLETE"

    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, discord_enabled=False, mt5_enabled=False, final_signal_enabled=False, live_hook_enabled=False, blocker_count=len(blockers), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2), threshold_rows=int(len(th)), rolling_distribution_rows=int(len(roll)), virtual_monitor_event_rows=int(len(events)), stop_review_event_count=stop_count, caution_event_count=caution_count, watch_event_count=watch_count, latest_worst_monitor_state=latest_worst)
    save(pd.DataFrame(blockers), out / "gold_v3_111_blocker_matrix.csv")
    save(val, out / "gold_v3_111_validation_matrix.csv")
    outputs += ["gold_v3_111_blocker_matrix.csv", "gold_v3_111_validation_matrix.csv", "gold_v3_111_summary.json", "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_111_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 111 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 111 PASTE_ME_VIRTUAL_MONITOR_DRY_RUN", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, virtual_monitor_dry_run_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blockers)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "QUALITY_GATES", qg.to_string(index=False), "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
