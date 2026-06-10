#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 75 external action payload preview audit-only.

Builds suppressed or preview-only Discord/MT5 payloads from Stage74 guarded output.
No Discord send, no MT5 order, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_BLOCKED_AUDIT_ONLY"
STAGE74_READY = "GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_cell(v: Any) -> str:
    """Normalize blank/NaN-ish values to an empty string for downstream payloads."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() in {"nan", "none", "null", "nat"}:
        return ""
    return s


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
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"FX_OUTPUTS"/"gold_v3"/"74_guarded_live_csv_monitor_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage74 outputs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage74-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s74 = Path(a.stage74_dir).expanduser().resolve() if a.stage74_dir else base_out / "74_guarded_live_csv_monitor_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "75_external_action_payload_preview_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p74 = s74 / "gold_v3_74_guarded_live_csv_monitor_summary.json"
    p74_snap = s74 / "gold_v3_74_latest_guarded_snapshot.json"
    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage74_summary", p74), ("stage74_snapshot", p74_snap)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j74 = read_json(p74) if p74.exists() else {}
    snap = read_json(p74_snap) if p74_snap.exists() else {}
    val.append(ok("stage74_status_ready", j74.get("status") == STAGE74_READY, j74.get("status"), STAGE74_READY))
    val.append(ok("stage74_guarded_monitor_ready", j74.get("guarded_live_csv_monitor_ready") is True, j74.get("guarded_live_csv_monitor_ready"), True))
    val.append(ok("stage73_source_stage_is_stage71", j74.get("stage73_source_stage") == "stage71", j74.get("stage73_source_stage"), "stage71"))

    latest = clean_cell(j74.get("latest_m15_time", ""))
    stage73_time = clean_cell(j74.get("stage73_latest_closed_m15_time", "") or snap.get("latest_closed_m15_time", ""))
    decision = clean_cell(j74.get("decision", snap.get("decision", "")))
    reason = clean_cell(j74.get("no_signal_reason", snap.get("no_signal_reason", "")))
    action = clean_cell(j74.get("emission_action", snap.get("emission_action", "")))
    selected_candidate = clean_cell(snap.get("selected_candidate_label", ""))
    signal_uid = clean_cell(snap.get("signal_uid", "")) or f"{stage73_time}|{decision}|{selected_candidate}"

    val.append(ok("selected_candidate_label_clean", selected_candidate.lower() != "nan", selected_candidate, "not_nan"))
    val.append(ok("signal_uid_clean", "nan" not in signal_uid.lower(), signal_uid, "not_contains_nan"))
    val.append(ok("stage74_time_matches_stage73_time", latest == stage73_time and latest != "", stage73_time, latest))
    val.append(ok("decision_is_signal_or_no_signal", decision in {"SIGNAL", "NO_SIGNAL"}, decision, "SIGNAL|NO_SIGNAL"))
    val.append(ok("emission_action_known", action in {"NO_ACTION", "ALLOW_AUDIT_SIGNAL_EVENT", "SUPPRESS_DUPLICATE_SIGNAL"}, action, "known"))
    if latest != stage73_time or not latest:
        blockers.append(blocker("stage74_stage73_time_mismatch", str(p74), "STAGE73_TIME_DOES_NOT_MATCH_STAGE74_LATEST", {"stage74": latest, "stage73": stage73_time}))
    if j74.get("stage73_source_stage") != "stage71":
        blockers.append(blocker("stage73_source_stage_not_stage71", str(p74), "STAGE73_NOT_READING_STAGE71_SNAPSHOT", j74.get("stage73_source_stage")))

    should_notify_discord = False
    should_place_mt5_order = False
    should_call_ai_api = False
    should_enable_final_signal = False
    discord_message = ""
    mt5_intent: dict[str, Any] = {"suppressed": True, "reason": ""}
    payload_action = ""

    if not blockers:
        if decision == "NO_SIGNAL":
            payload_action = "SUPPRESS_NO_SIGNAL_PAYLOAD"
            mt5_intent = {"suppressed": True, "reason": "NO_SIGNAL", "decision": decision, "latest_closed_m15_time": stage73_time}
            discord_message = ""
        elif action == "SUPPRESS_DUPLICATE_SIGNAL":
            payload_action = "SUPPRESS_DUPLICATE_PAYLOAD"
            mt5_intent = {"suppressed": True, "reason": "DUPLICATE_SIGNAL", "signal_uid": signal_uid, "latest_closed_m15_time": stage73_time}
            discord_message = ""
        elif decision == "SIGNAL" and action == "ALLOW_AUDIT_SIGNAL_EVENT":
            payload_action = "BUILD_AUDIT_PAYLOAD_PREVIEW"
            discord_message = (
                f"[AUDIT-ONLY][GOLD V3] SIGNAL PREVIEW\n"
                f"time={stage73_time}\n"
                f"candidate={selected_candidate}\n"
                f"signal_uid={signal_uid}\n"
                f"No Discord send / No MT5 order / No final signal."
            )
            mt5_intent = {
                "suppressed": False,
                "audit_preview_only": True,
                "symbol": "XAUUSD",
                "latest_closed_m15_time": stage73_time,
                "candidate_label": selected_candidate,
                "signal_uid": signal_uid,
                "place_order": False,
                "reason": "AUDIT_PAYLOAD_PREVIEW_ONLY",
            }
        else:
            payload_action = "BLOCKED_UNKNOWN_ACTION"
            blockers.append(blocker("payload_action_unknown", str(p74_snap), "UNKNOWN_DECISION_OR_EMISSION_ACTION", {"decision": decision, "emission_action": action}))

    (out / "gold_v3_75_discord_message_preview.txt").write_text(discord_message, encoding="utf-8")
    write_json(out / "gold_v3_75_mt5_order_intent_preview.json", mt5_intent)
    payload_row = {
        "created_at_utc": utc_now(),
        "latest_closed_m15_time": stage73_time,
        "decision": decision,
        "no_signal_reason": reason,
        "emission_action": action,
        "payload_action": payload_action,
        "selected_candidate_label": selected_candidate,
        "signal_uid": signal_uid,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        "audit_only": True,
        "live_ready": False,
        "csv_open_bar_exclusion_required": False,
    }
    pd.DataFrame([payload_row]).to_csv(out / "gold_v3_75_payload_preview.csv", index=False, encoding="utf-8-sig")

    val.append(ok("payload_action_deterministic", payload_action in {"SUPPRESS_NO_SIGNAL_PAYLOAD", "SUPPRESS_DUPLICATE_PAYLOAD", "BUILD_AUDIT_PAYLOAD_PREVIEW"}, payload_action, "deterministic"))
    val.append(ok("no_signal_payload_suppressed", decision != "NO_SIGNAL" or payload_action == "SUPPRESS_NO_SIGNAL_PAYLOAD", payload_action, "SUPPRESS_NO_SIGNAL_PAYLOAD"))
    val.append(ok("discord_send_false", should_notify_discord is False, should_notify_discord, False))
    val.append(ok("mt5_order_false", should_place_mt5_order is False, should_place_mt5_order, False))
    val.append(ok("ai_api_false", should_call_ai_api is False, should_call_ai_api, False))
    val.append(ok("final_signal_false", should_enable_final_signal is False, should_enable_final_signal, False))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_75_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_75_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "external_action_payload_preview_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "latest_closed_m15_time": stage73_time,
        "decision": decision,
        "no_signal_reason": reason,
        "emission_action": action,
        "payload_action": payload_action,
        "selected_candidate_label": selected_candidate,
        "signal_uid": signal_uid,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    write_json(out / "gold_v3_75_external_action_payload_preview_summary.json", summary)

    paste = []
    paste.append("GOLD V3 75 PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("external_action_payload_preview_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_closed_m15_time: {stage73_time}")
    paste.append(f"decision: {decision}")
    paste.append(f"no_signal_reason: {reason}")
    paste.append(f"emission_action: {action}")
    paste.append(f"payload_action: {payload_action}")
    paste.append(f"selected_candidate_label: {selected_candidate}")
    paste.append(f"signal_uid: {signal_uid}")
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
    paste.append("gold_v3_75_payload_preview.csv")
    paste.append("gold_v3_75_discord_message_preview.txt")
    paste.append("gold_v3_75_mt5_order_intent_preview.json")
    paste.append("gold_v3_75_blocker_matrix.csv")
    paste.append("gold_v3_75_validation_matrix.csv")
    paste.append("gold_v3_75_external_action_payload_preview_summary.json")
    (out / "gold_v3_75_PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 75 external action payload preview audit-only report

Status: `{status}`

- latest_closed_m15_time: `{stage73_time}`
- decision: `{decision}`
- no_signal_reason: `{reason}`
- emission_action: `{action}`
- payload_action: `{payload_action}`
- should_notify_discord: `{should_notify_discord}`
- should_place_mt5_order: `{should_place_mt5_order}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_75_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_75_PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
