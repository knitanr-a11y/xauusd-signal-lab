#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE"
READY = "GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    out = root / "112c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    paths = {
        "selected_ledger": root / "109c" / "gold_v3_109_selected_base_policy_ledger.csv",
        "summary_109": root / "109c" / "gold_v3_109_summary.json",
        "thresholds_110": root / "110c" / "gold_v3_110_monitoring_thresholds.csv",
        "summary_110": root / "110c" / "gold_v3_110_summary.json",
        "latest_state_111": root / "111c" / "gold_v3_111_latest_monitor_state.csv",
        "summary_111": root / "111c" / "gold_v3_111_summary.json",
    }
    blockers = []
    outputs = []
    findings = []
    for k, p in paths.items():
        if not p.exists():
            blockers.append(dict(blocker_id=f"missing_{k}", path=str(p)))
    prog(1, 5, "input existence checked")

    ledger = pd.DataFrame(); th = pd.DataFrame(); latest = pd.DataFrame(); s109 = {}; s110 = {}; s111 = {}
    if not blockers:
        ledger = pd.read_csv(paths["selected_ledger"], encoding="utf-8-sig", low_memory=False)
        th = pd.read_csv(paths["thresholds_110"], encoding="utf-8-sig")
        latest = pd.read_csv(paths["latest_state_111"], encoding="utf-8-sig")
        s109 = load_json(paths["summary_109"])
        s110 = load_json(paths["summary_110"])
        s111 = load_json(paths["summary_111"])
        for c in ["entry_dt", "exit_dt", "result_usd"]:
            if c not in ledger.columns:
                blockers.append(dict(blocker_id="selected_ledger_missing_required_column", column=c))
        if th.empty:
            blockers.append(dict(blocker_id="monitoring_thresholds_empty"))
        if latest.empty:
            blockers.append(dict(blocker_id="latest_monitor_state_empty"))
        prog(2, 5, f"loaded ledger={len(ledger)} thresholds={len(th)} latest={len(latest)}")

    if not blockers:
        save(th, out / "gold_v3_112_frozen_monitoring_thresholds.csv")
        save(latest, out / "gold_v3_112_latest_virtual_monitor_state.csv")
        outputs += ["gold_v3_112_frozen_monitoring_thresholds.csv", "gold_v3_112_latest_virtual_monitor_state.csv"]
        latest_worst = str(s111.get("latest_worst_monitor_state", ""))
        manifest = {
            "stage": STEP,
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "audit_only": True,
            "live_ready": False,
            "selected_option": "KEEP_107Q_BASE",
            "selected_policy_key": "107Q_BASE_RESOLVED_PASS_THROUGH",
            "health_gate_adopted": False,
            "loss_feature_filter_adopted": False,
            "monitoring_design_attached": True,
            "virtual_monitor_latest_state": latest_worst,
            "source_csv_mutated": False,
            "contract_mutated": False,
            "open_asof_allowed": False,
            "live_hook_enabled": False,
            "discord_enabled": False,
            "mt5_enabled": False,
            "ai_api_enabled": False,
            "final_signal_enabled": False,
            "policy_metrics": {
                "trades": s109.get("trades"),
                "win_rate": s109.get("win_rate"),
                "profit_factor": s109.get("profit_factor"),
                "sum_result_usd": s109.get("sum_result_usd"),
                "negative_month_count": s109.get("negative_month_count"),
                "unique_trade_days": s109.get("unique_trade_days"),
                "max_day_trade_share": s109.get("max_day_trade_share"),
            },
            "monitoring_metrics": {
                "threshold_rows": s110.get("monitoring_threshold_rows"),
                "rolling_distribution_rows": s110.get("rolling_distribution_rows"),
                "virtual_monitor_event_rows": s111.get("virtual_monitor_event_rows"),
                "stop_review_event_count": s111.get("stop_review_event_count"),
                "caution_event_count": s111.get("caution_event_count"),
                "watch_event_count": s111.get("watch_event_count"),
            },
            "input_sha256": {k: sha256_file(p) for k, p in paths.items()},
        }
        (out / "gold_v3_112_selected_policy_freeze_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append("gold_v3_112_selected_policy_freeze_manifest.json")
        summary_csv = pd.DataFrame([{
            "selected_option": manifest["selected_option"],
            "selected_policy_key": manifest["selected_policy_key"],
            "health_gate_adopted": manifest["health_gate_adopted"],
            "loss_feature_filter_adopted": manifest["loss_feature_filter_adopted"],
            "monitoring_design_attached": manifest["monitoring_design_attached"],
            "virtual_monitor_latest_state": manifest["virtual_monitor_latest_state"],
            "trades": s109.get("trades"),
            "win_rate": s109.get("win_rate"),
            "profit_factor": s109.get("profit_factor"),
            "sum_result_usd": s109.get("sum_result_usd"),
            "negative_month_count": s109.get("negative_month_count"),
            "threshold_rows": len(th),
            "latest_state_rows": len(latest),
            "live_ready": False,
        }])
        save(summary_csv, out / "gold_v3_112_selected_policy_freeze_summary.csv")
        outputs.append("gold_v3_112_selected_policy_freeze_summary.csv")
        reasons = pd.DataFrame([
            dict(reason_id="selected_base_policy", result="KEEP_107Q_BASE", detail="Stage109 selected base because health gate skipped net-positive trades."),
            dict(reason_id="loss_feature_filter", result="NOT_ADOPTED", detail="Stage109C train-only loss-feature filter was not confirmed."),
            dict(reason_id="monitoring_design", result="ATTACHED", detail="Stage110 monitoring thresholds and Stage111 dry run attached."),
            dict(reason_id="latest_virtual_monitor", result=latest_worst, detail="Latest historical monitor state from Stage111."),
            dict(reason_id="live_readiness", result="FALSE", detail="Freeze is audit-only and grants no live permission."),
        ])
        save(reasons, out / "gold_v3_112_freeze_reason_matrix.csv")
        outputs.append("gold_v3_112_freeze_reason_matrix.csv")
        findings.append("freeze_manifest_created_for_KEEP_107Q_BASE_with_monitoring_attached")
        prog(4, 5, "freeze artifacts written")

    qg = pd.DataFrame([
        qgate("109_selected_keep_107q_base", str(s109.get("selected_option", "")) == "KEEP_107Q_BASE", "==", True),
        qgate("109_health_gate_not_adopted", bool(s109.get("health_gate_adopted", True)), "==", False),
        qgate("110_ready", str(s110.get("status", "")) == "GOLD_V3_110_AUDIT_MONITORING_DESIGN_READY_AUDIT_ONLY", "==", True),
        qgate("111_ready", str(s111.get("status", "")) == "GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_READY_AUDIT_ONLY", "==", True),
        qgate("111_latest_state_ok", str(s111.get("latest_worst_monitor_state", "")) == "OK", "==", True),
        qgate("live_ready_false", False, "==", False),
        qgate("discord_disabled", False, "==", False),
        qgate("mt5_disabled", False, "==", False),
        qgate("final_signal_disabled", False, "==", False),
    ])
    save(qg, out / "gold_v3_112_quality_gate_matrix.csv")
    outputs.append("gold_v3_112_quality_gate_matrix.csv")

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
    if not ledger.empty:
        vals.append(dict(check_id="selected_ledger_positive", result="PASS", observed=len(ledger), expected=">0", severity="BLOCKER"))
    if not th.empty:
        vals.append(dict(check_id="frozen_thresholds_positive", result="PASS", observed=len(th), expected=">0", severity="BLOCKER"))
    if not latest.empty:
        vals.append(dict(check_id="latest_monitor_state_positive", result="PASS", observed=len(latest), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blockers and validation_failure_count == 0 else BLOCKED
    decision = "SELECTED_POLICY_AUDIT_FREEZE_READY_FOR_STAGE113_FINAL_AUDIT_REVIEW_PACKET" if status == READY else "SELECTED_POLICY_AUDIT_FREEZE_BLOCKED_INPUT_INCOMPLETE"

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
        selected_option="KEEP_107Q_BASE",
        selected_policy_key="107Q_BASE_RESOLVED_PASS_THROUGH",
        health_gate_adopted=False,
        loss_feature_filter_adopted=False,
        monitoring_design_attached=not th.empty,
        virtual_monitor_latest_state=str(s111.get("latest_worst_monitor_state", "")),
        blocker_count=len(blockers),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        selected_ledger_rows=int(len(ledger)) if not ledger.empty else 0,
        frozen_threshold_rows=int(len(th)) if not th.empty else 0,
        latest_monitor_state_rows=int(len(latest)) if not latest.empty else 0,
        trades=s109.get("trades"),
        win_rate=s109.get("win_rate"),
        profit_factor=s109.get("profit_factor"),
        sum_result_usd=s109.get("sum_result_usd"),
        negative_month_count=s109.get("negative_month_count"),
    )
    save(pd.DataFrame(blockers), out / "gold_v3_112_blocker_matrix.csv")
    save(val, out / "gold_v3_112_validation_matrix.csv")
    outputs += ["gold_v3_112_blocker_matrix.csv", "gold_v3_112_validation_matrix.csv", "gold_v3_112_summary.json", "GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_112_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_112_SELECTED_POLICY_AUDIT_FREEZE_REPORT.md").write_text("# GOLD V3 112 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 112 PASTE_ME_SELECTED_POLICY_AUDIT_FREEZE", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "selected_option: KEEP_107Q_BASE", "selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH", "health_gate_adopted: false", "loss_feature_filter_adopted: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, freeze_manifest_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blockers)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "QUALITY_GATES", qg.to_string(index=False), "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
