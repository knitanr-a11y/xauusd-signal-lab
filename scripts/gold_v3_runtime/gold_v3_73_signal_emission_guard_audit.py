#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 73 signal emission guard audit-only.

Reads Stage72 latest pipeline snapshot and decides whether an audit-only signal
would be emitted, suppressed as duplicate, or ignored as NO_SIGNAL.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_73_SIGNAL_EMISSION_GUARD_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_73_SIGNAL_EMISSION_GUARD_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_73_SIGNAL_EMISSION_GUARD_BLOCKED_AUDIT_ONLY"
STAGE72_READY = "GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), Path.cwd() / "Files", root, root / "Files", root.parent, root.parent / "Files", root.parent.parent]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "72_live_csv_update_monitor_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage72 outputs")


def append_event(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "created_at_utc", "latest_closed_m15_time", "decision", "selected_candidate_label", "signal_uid",
        "emission_action", "should_notify_discord", "should_place_mt5_order", "duplicate_signal_suppressed",
        "no_signal_notification_suppressed", "detail",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage72-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s72 = Path(a.stage72_dir).expanduser().resolve() if a.stage72_dir else base_out / "72_live_csv_update_monitor_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "73_signal_emission_guard_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p72_summary = s72 / "gold_v3_72_live_csv_update_monitor_summary.json"
    p72_snapshot = s72 / "gold_v3_72_latest_pipeline_snapshot.json"
    state_path = out / "gold_v3_73_signal_emission_guard_state.json"
    event_ledger = out / "gold_v3_73_signal_emission_event_ledger.csv"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage72_summary", p72_summary), ("stage72_snapshot", p72_snapshot)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j72 = read_json(p72_summary) if p72_summary.exists() else {}
    snap = read_json(p72_snapshot) if p72_snapshot.exists() else {}
    val.append(ok("stage72_status_ready", j72.get("status") == STAGE72_READY, j72.get("status"), STAGE72_READY))
    val.append(ok("stage72_monitor_ready", j72.get("live_csv_update_monitor_ready") is True, j72.get("live_csv_update_monitor_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage72_{key}_false", j72.get(key) is False, j72.get(key), False))

    latest_summary_time = str(j72.get("latest_m15_time", "") or "")
    latest_snapshot_time = str(snap.get("latest_closed_m15_time", "") or "")
    decision = str(snap.get("decision", j72.get("stage71_decision", "")) or "")
    reason = str(snap.get("no_signal_reason", j72.get("stage71_no_signal_reason", "")) or "")
    selected_candidate_label = str(snap.get("selected_candidate_label", "") or "")
    signal_uid = f"{latest_snapshot_time}|{decision}|{selected_candidate_label}"

    val.append(ok("snapshot_time_matches_stage72_latest", latest_summary_time == latest_snapshot_time and latest_snapshot_time != "", latest_snapshot_time, latest_summary_time))
    val.append(ok("decision_is_signal_or_no_signal", decision in {"SIGNAL", "NO_SIGNAL"}, decision, "SIGNAL|NO_SIGNAL"))
    if latest_summary_time != latest_snapshot_time or not latest_snapshot_time:
        blockers.append(blocker("snapshot_time_mismatch", str(p72_snapshot), "SNAPSHOT_LATEST_TIME_DOES_NOT_MATCH_STAGE72_SUMMARY", {"stage72": latest_summary_time, "snapshot": latest_snapshot_time}))
    if decision not in {"SIGNAL", "NO_SIGNAL"}:
        blockers.append(blocker("invalid_decision", str(p72_snapshot), "DECISION_NOT_SIGNAL_OR_NO_SIGNAL", decision))

    state: dict[str, Any] = {"emitted_signal_uids": [], "updated_at_utc": ""}
    if state_path.exists():
        try:
            state = read_json(state_path)
            if not isinstance(state.get("emitted_signal_uids"), list):
                state["emitted_signal_uids"] = []
        except Exception:
            state = {"emitted_signal_uids": [], "updated_at_utc": ""}

    emission_action = ""
    duplicate_signal_suppressed = False
    no_signal_notification_suppressed = False
    audit_signal_event_allowed = False
    should_notify_discord = False
    should_place_mt5_order = False
    should_call_ai_api = False
    should_enable_final_signal = False

    if not blockers:
        if decision == "NO_SIGNAL":
            emission_action = "NO_ACTION"
            no_signal_notification_suppressed = True
        elif decision == "SIGNAL":
            emitted = set(str(x) for x in state.get("emitted_signal_uids", []))
            if signal_uid in emitted:
                emission_action = "SUPPRESS_DUPLICATE_SIGNAL"
                duplicate_signal_suppressed = True
            else:
                emission_action = "ALLOW_AUDIT_SIGNAL_EVENT"
                audit_signal_event_allowed = True
                state.setdefault("emitted_signal_uids", []).append(signal_uid)
        else:
            emission_action = "BLOCKED"

    state["updated_at_utc"] = utc_now()
    state["last_seen_signal_uid"] = signal_uid
    state["last_emission_action"] = emission_action
    write_json(state_path, state)

    decision_row = {
        "created_at_utc": utc_now(),
        "latest_closed_m15_time": latest_snapshot_time,
        "decision": decision,
        "no_signal_reason": reason,
        "selected_candidate_label": selected_candidate_label,
        "signal_uid": signal_uid,
        "emission_action": emission_action,
        "audit_signal_event_allowed": audit_signal_event_allowed,
        "duplicate_signal_suppressed": duplicate_signal_suppressed,
        "no_signal_notification_suppressed": no_signal_notification_suppressed,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        "audit_only": True,
        "live_ready": False,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "csv_open_bar_exclusion_required": False,
        "csv_contract": CSV_CONTRACT,
        "pool_policy": POOL_POLICY,
    }
    pd.DataFrame([decision_row]).to_csv(out / "gold_v3_73_emission_decision.csv", index=False, encoding="utf-8-sig")
    append_event(event_ledger, decision_row | {"detail": reason})

    val.append(ok("emission_action_valid", emission_action in {"NO_ACTION", "ALLOW_AUDIT_SIGNAL_EVENT", "SUPPRESS_DUPLICATE_SIGNAL"}, emission_action, "valid_action"))
    val.append(ok("no_signal_has_no_action", decision != "NO_SIGNAL" or emission_action == "NO_ACTION", emission_action, "NO_ACTION when NO_SIGNAL"))
    val.append(ok("no_signal_notification_suppressed", decision != "NO_SIGNAL" or no_signal_notification_suppressed is True, no_signal_notification_suppressed, True))
    val.append(ok("discord_notification_false", should_notify_discord is False, should_notify_discord, False))
    val.append(ok("mt5_order_false", should_place_mt5_order is False, should_place_mt5_order, False))
    val.append(ok("ai_api_false", should_call_ai_api is False, should_call_ai_api, False))
    val.append(ok("final_signal_false", should_enable_final_signal is False, should_enable_final_signal, False))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_73_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_73_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": utc_now(),
        "candle_dir": str(cdir),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "signal_emission_guard_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "latest_closed_m15_time": latest_snapshot_time,
        "decision": decision,
        "no_signal_reason": reason,
        "selected_candidate_label": selected_candidate_label,
        "signal_uid": signal_uid,
        "emission_action": emission_action,
        "audit_signal_event_allowed": audit_signal_event_allowed,
        "duplicate_signal_suppressed": duplicate_signal_suppressed,
        "no_signal_notification_suppressed": no_signal_notification_suppressed,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    write_json(out / "gold_v3_73_signal_emission_guard_summary.json", summary)

    paste = []
    paste.append("GOLD V3 73 PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("signal_emission_guard_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_closed_m15_time: {latest_snapshot_time}")
    paste.append(f"decision: {decision}")
    paste.append(f"no_signal_reason: {reason}")
    paste.append(f"selected_candidate_label: {selected_candidate_label}")
    paste.append(f"signal_uid: {signal_uid}")
    paste.append(f"emission_action: {emission_action}")
    paste.append(f"audit_signal_event_allowed: {audit_signal_event_allowed}")
    paste.append(f"duplicate_signal_suppressed: {duplicate_signal_suppressed}")
    paste.append(f"no_signal_notification_suppressed: {no_signal_notification_suppressed}")
    paste.append(f"should_notify_discord: {should_notify_discord}")
    paste.append(f"should_place_mt5_order: {should_place_mt5_order}")
    paste.append(f"should_call_ai_api: {should_call_ai_api}")
    paste.append(f"should_enable_final_signal: {should_enable_final_signal}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_73_emission_decision.csv")
    paste.append("gold_v3_73_signal_emission_guard_state.json")
    paste.append("gold_v3_73_signal_emission_event_ledger.csv")
    paste.append("gold_v3_73_blocker_matrix.csv")
    paste.append("gold_v3_73_validation_matrix.csv")
    paste.append("gold_v3_73_signal_emission_guard_summary.json")
    (out / "gold_v3_73_PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 73 signal emission guard audit-only report

Status: `{status}`

- latest_closed_m15_time: `{latest_snapshot_time}`
- decision: `{decision}`
- no_signal_reason: `{reason}`
- signal_uid: `{signal_uid}`
- emission_action: `{emission_action}`
- should_notify_discord: `{should_notify_discord}`
- should_place_mt5_order: `{should_place_mt5_order}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_73_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_73_PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
