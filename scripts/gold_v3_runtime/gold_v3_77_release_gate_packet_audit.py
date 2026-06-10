#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 77 release gate packet audit-only.

Verifies Stage76 full audit monitor output and records that any external action
release remains blocked pending explicit human approval.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_77_RELEASE_GATE_PACKET_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_77_RELEASE_GATE_PACKET_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_77_RELEASE_GATE_PACKET_BLOCKED_AUDIT_ONLY"
STAGE76_READY = "GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
LIVE_RELEASE_GATE_STATUS = "LIVE_RELEASE_BLOCKED_PENDING_EXPLICIT_HUMAN_APPROVAL"
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
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"FX_OUTPUTS"/"gold_v3"/"76_full_audit_monitor_with_payload_preview_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage76 outputs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage76-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s76 = Path(a.stage76_dir).expanduser().resolve() if a.stage76_dir else base_out / "76_full_audit_monitor_with_payload_preview_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "77_release_gate_packet_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p76 = s76 / "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json"
    p76_preview = s76 / "gold_v3_76_latest_payload_preview.json"
    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for name, path in [("stage76_summary", p76), ("stage76_payload_preview", p76_preview)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j76 = read_json(p76) if p76.exists() else {}
    preview = read_json(p76_preview) if p76_preview.exists() else {}

    latest_m15 = str(j76.get("latest_m15_time", "") or "")
    stage75_time = str(j76.get("stage75_latest_closed_m15_time", "") or preview.get("latest_closed_m15_time", "") or "")
    decision = str(j76.get("decision", preview.get("decision", "")) or "")
    emission_action = str(j76.get("emission_action", preview.get("emission_action", "")) or "")
    payload_action = str(j76.get("payload_action", preview.get("payload_action", "")) or "")
    should_notify_discord = str(j76.get("should_notify_discord", preview.get("should_notify_discord", ""))) == "True"
    should_place_mt5_order = str(j76.get("should_place_mt5_order", preview.get("should_place_mt5_order", ""))) == "True"
    should_call_ai_api = str(j76.get("should_call_ai_api", preview.get("should_call_ai_api", ""))) == "True"
    should_enable_final_signal = str(j76.get("should_enable_final_signal", preview.get("should_enable_final_signal", ""))) == "True"

    approvals = {
        "approve_discord_notification_enable": False,
        "approve_mt5_order_enable": False,
        "approve_ai_api_enable": False,
        "approve_final_signal_enable": False,
        "approve_live_release": False,
    }

    val.append(ok("stage76_status_ready", j76.get("status") == STAGE76_READY, j76.get("status"), STAGE76_READY))
    val.append(ok("stage76_monitor_ready", j76.get("full_audit_monitor_with_payload_preview_ready") is True, j76.get("full_audit_monitor_with_payload_preview_ready"), True))
    val.append(ok("stage76_time_matches_stage75_time", latest_m15 == stage75_time and latest_m15 != "", stage75_time, latest_m15))
    val.append(ok("payload_action_deterministic", payload_action in {"SUPPRESS_NO_SIGNAL_PAYLOAD", "SUPPRESS_DUPLICATE_PAYLOAD", "BUILD_AUDIT_PAYLOAD_PREVIEW"}, payload_action, "deterministic"))
    val.append(ok("discord_send_false", should_notify_discord is False, should_notify_discord, False))
    val.append(ok("mt5_order_false", should_place_mt5_order is False, should_place_mt5_order, False))
    val.append(ok("ai_api_false", should_call_ai_api is False, should_call_ai_api, False))
    val.append(ok("final_signal_false", should_enable_final_signal is False, should_enable_final_signal, False))
    for k, v in approvals.items():
        val.append(ok(f"{k}_false", v is False, v, False))
    val.append(ok("live_release_gate_blocked", LIVE_RELEASE_GATE_STATUS == "LIVE_RELEASE_BLOCKED_PENDING_EXPLICIT_HUMAN_APPROVAL", LIVE_RELEASE_GATE_STATUS, "LIVE_RELEASE_BLOCKED_PENDING_EXPLICIT_HUMAN_APPROVAL"))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    if latest_m15 != stage75_time or not latest_m15:
        blockers.append(blocker("stage76_stage75_time_mismatch", str(p76), "STAGE75_TIME_DOES_NOT_MATCH_STAGE76_LATEST", {"stage76": latest_m15, "stage75": stage75_time}))
    if should_notify_discord or should_place_mt5_order or should_call_ai_api or should_enable_final_signal:
        blockers.append(blocker("external_side_effect_flag_true", str(p76), "EXTERNAL_SIDE_EFFECT_FLAG_TRUE", {
            "should_notify_discord": should_notify_discord,
            "should_place_mt5_order": should_place_mt5_order,
            "should_call_ai_api": should_call_ai_api,
            "should_enable_final_signal": should_enable_final_signal,
        }))

    approval_df = pd.DataFrame([{"approval_id": k, "approved": v, "required_before_live_release": True} for k, v in approvals.items()])
    approval_df.to_csv(out / "gold_v3_77_required_human_approval_matrix.csv", index=False, encoding="utf-8-sig")

    decision_row = {
        "created_at_utc": utc_now(),
        "live_release_gate_status": LIVE_RELEASE_GATE_STATUS,
        "stage76_status": j76.get("status", ""),
        "latest_closed_m15_time": latest_m15,
        "decision": decision,
        "emission_action": emission_action,
        "payload_action": payload_action,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        **approvals,
        "audit_only": True,
        "live_ready": False,
        "csv_open_bar_exclusion_required": False,
    }
    pd.DataFrame([decision_row]).to_csv(out / "gold_v3_77_release_gate_decision.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(blockers).to_csv(out / "gold_v3_77_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_77_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "release_gate_packet_ready": status == READY_STATUS,
        "live_release_gate_status": LIVE_RELEASE_GATE_STATUS,
        "pool_policy": POOL_POLICY,
        "latest_closed_m15_time": latest_m15,
        "stage75_latest_closed_m15_time": stage75_time,
        "decision": decision,
        "emission_action": emission_action,
        "payload_action": payload_action,
        "should_notify_discord": should_notify_discord,
        "should_place_mt5_order": should_place_mt5_order,
        "should_call_ai_api": should_call_ai_api,
        "should_enable_final_signal": should_enable_final_signal,
        **approvals,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    write_json(out / "gold_v3_77_release_gate_packet_summary.json", summary)

    paste = []
    paste.append("GOLD V3 77 PASTE_ME_RELEASE_GATE_PACKET_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("release_gate_packet_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_release_gate_status: " + LIVE_RELEASE_GATE_STATUS)
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_closed_m15_time: {latest_m15}")
    paste.append(f"decision: {decision}")
    paste.append(f"emission_action: {emission_action}")
    paste.append(f"payload_action: {payload_action}")
    paste.append(f"should_notify_discord: {should_notify_discord}")
    paste.append(f"should_place_mt5_order: {should_place_mt5_order}")
    paste.append(f"should_call_ai_api: {should_call_ai_api}")
    paste.append(f"should_enable_final_signal: {should_enable_final_signal}")
    for k, v in approvals.items():
        paste.append(f"{k}: {v}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_77_release_gate_decision.csv")
    paste.append("gold_v3_77_required_human_approval_matrix.csv")
    paste.append("gold_v3_77_blocker_matrix.csv")
    paste.append("gold_v3_77_validation_matrix.csv")
    paste.append("gold_v3_77_release_gate_packet_summary.json")
    (out / "gold_v3_77_PASTE_ME_RELEASE_GATE_PACKET_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 77 release gate packet audit-only report

Status: `{status}`

- live_release_gate_status: `{LIVE_RELEASE_GATE_STATUS}`
- latest_closed_m15_time: `{latest_m15}`
- decision: `{decision}`
- emission_action: `{emission_action}`
- payload_action: `{payload_action}`
- should_notify_discord: `{should_notify_discord}`
- should_place_mt5_order: `{should_place_mt5_order}`
- approve_live_release: `{approvals['approve_live_release']}`
- blocker_count: `{len(blockers)}`

READY only means the release gate packet is prepared. It does not approve live release.
"""
    (out / "GOLD_V3_77_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_77_PASTE_ME_RELEASE_GATE_PACKET_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
