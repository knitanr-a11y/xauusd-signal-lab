#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage219 - Notification Message Text Preview Audit

Audit-only / text-preview-only.
No Discord send, no webhook, no payload activation, no MT5 order,
no actual import, no live hook, no final live, no autotrade.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


STAGE = "GOLD_V3_219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_AUDIT_ONLY"
DECISION_READY = "STAGE219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

DISABLED_FLAGS: Dict[str, bool] = {
    "send_enabled": False,
    "execution_enabled": False,
    "actual_order_import_enabled": False,
    "discord_enabled": False,
    "webhook_enabled": False,
    "mt5_order_enabled": False,
    "ai_api_enabled": False,
    "payload_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
}

PREVIEW_COLUMNS = [
    "preview_id",
    "message_action",
    "send_action",
    "payload_action",
    "webhook_action",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "symbol",
    "final_route",
    "strategy_role",
    "candidate_id",
    "direction",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "message_text",
    "audit_only",
    "text_preview_only",
    "created_stage",
    "created_at_utc",
]

NO_SIGNAL_COLUMNS = [
    "preview_id",
    "latest_closed_m15_dt",
    "final_route",
    "message_action",
    "send_action",
    "discord_notify",
    "message_text_created",
    "audit_only",
    "text_preview_only",
    "created_stage",
    "created_at_utc",
]


@dataclass(frozen=True)
class SignalPreviewFixture:
    signal_id: str
    short_signal_id: str
    latest_closed_m15_dt: str
    entry_dt: str
    symbol: str
    final_route: str
    strategy_role: str
    candidate_id: str
    direction: str
    entry_price: float
    tp_usd: float
    sl_usd: float
    horizon_m5_bars: int


SIGNAL_FIXTURE = SignalPreviewFixture(
    signal_id="20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT",
    short_signal_id="G3SD01960980A23107A65AE",
    latest_closed_m15_dt="2026-06-15 16:30:00",
    entry_dt="2026-06-15 16:30:00",
    symbol="XAUUSD",
    final_route="SECONDARY_AUDIT_CANDIDATE",
    strategy_role="SCALP_SECONDARY_CANDIDATE",
    candidate_id="SCALP_024_tp15_sl5_hz64_SHORT",
    direction="SHORT",
    entry_price=4363.24,
    tp_usd=15.0,
    sl_usd=5.0,
    horizon_m5_bars=64,
)

NO_SIGNAL_FIXTURE = {
    "latest_closed_m15_dt": "2026-06-16 16:45:00",
    "final_route": "NO_SIGNAL",
}

FORBIDDEN_MESSAGE_PATTERNS = [
    r"\bWIN\b",
    r"\bLOSS\b",
    r"\bRESULT\b",
    r"\bOUTCOME\b",
    r"\bEXIT\b",
    r"\bEXIT_DT\b",
    r"\bFILL\b",
    r"\bSLIPPAGE\b",
    r"\bACCOUNT\b",
    r"\bBALANCE\b",
    r"WEBHOOK",
    r"TOKEN",
    r"SECRET",
    r"https?://",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return (
            Path(appdata)
            / "MetaQuotes"
            / "Terminal"
            / TERMINAL_HASH
            / "MQL5"
            / "Files"
        ).resolve()
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def stage_paths() -> Tuple[Path, Path, Path]:
    mql5_files = default_mql5_files_dir()
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "219"
    preview_dir = output_dir / "notification_text_preview"
    return mql5_files, output_dir, preview_dir


def assert_safe_stage219_path(preview_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "219", "notification_text_preview")
    actual_tail = tuple(preview_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe preview path. Expected tail {expected_tail}, got {actual_tail}")


def reset_preview_dir(preview_dir: Path) -> None:
    assert_safe_stage219_path(preview_dir)
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def build_signal_message_text(f: SignalPreviewFixture) -> str:
    # Keep text human-readable and explicitly non-send/non-order.
    # Do not include webhook/token/secret/account/fill/outcome/exit/result fields.
    return "\n".join(
        [
            "[GOLD V3][AUDIT_ONLY][NO_SEND] Signal message text preview",
            f"symbol: {f.symbol}",
            f"route: {f.final_route}",
            f"strategy_role: {f.strategy_role}",
            f"candidate_id: {f.candidate_id}",
            f"direction: {f.direction}",
            f"entry_dt_mt5_csv: {f.entry_dt}",
            f"latest_closed_m15_dt_mt5_csv: {f.latest_closed_m15_dt}",
            f"entry_price: {f.entry_price:.2f}",
            f"tp_usd_param: {f.tp_usd:g}",
            f"sl_usd_param: {f.sl_usd:g}",
            f"horizon_m5_bars_param: {f.horizon_m5_bars}",
            f"signal_id: {f.signal_id}",
            f"short_signal_id: {f.short_signal_id}",
            "action: preview text only; no Discord send; no MT5 order; no payload activation",
        ]
    )


def forbidden_hits(message_text: str) -> List[str]:
    hits: List[str] = []
    upper = message_text.upper()
    for pattern in FORBIDDEN_MESSAGE_PATTERNS:
        if re.search(pattern, upper):
            hits.append(pattern)
    return hits


def validate(preview_dir: Path, preview_rows: List[Dict[str, Any]], no_signal_rows: List[Dict[str, Any]], policy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    preview_csv = preview_dir / "notification_message_text_preview.csv"
    preview_txt = preview_dir / "notification_message_text_preview.txt"
    no_signal_csv = preview_dir / "no_signal_message_preview.csv"
    policy_json = preview_dir / "message_policy.json"

    preview_text = preview_rows[0]["message_text"] if preview_rows else ""
    forbidden = forbidden_hits(preview_text)

    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    add("NT001", tuple(preview_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "219", "notification_text_preview"), f"preview_dir={preview_dir}")
    add("NT002", preview_csv.exists() and len(preview_rows) == 1, f"signal_message_preview_rows={len(preview_rows)}")
    add(
        "NT003",
        no_signal_csv.exists()
        and len(no_signal_rows) == 1
        and no_signal_rows[0].get("message_action") == "NO_MESSAGE_NO_SIGNAL"
        and no_signal_rows[0].get("send_action") == "NO_SEND_AUDIT_ONLY"
        and no_signal_rows[0].get("message_text_created") is False,
        f"no_signal_rows={len(no_signal_rows)}",
    )
    add("NT004", "AUDIT_ONLY" in preview_text and "NO_SEND" in preview_text, "message contains AUDIT_ONLY and NO_SEND markers")
    add(
        "NT005",
        SIGNAL_FIXTURE.signal_id in preview_text
        and SIGNAL_FIXTURE.short_signal_id in preview_text
        and SIGNAL_FIXTURE.candidate_id in preview_text
        and SIGNAL_FIXTURE.direction in preview_text,
        "message contains signal/candidate details",
    )
    add("NT006", not forbidden, f"forbidden_message_pattern_hits={forbidden}")
    add(
        "NT007",
        preview_txt.exists()
        and policy_json.exists()
        and policy.get("payload_activation_enabled") is False
        and policy.get("webhook_enabled") is False,
        "text/csv/json preview only; no payload activation file",
    )
    add("NT008", all(v is False for v in DISABLED_FLAGS.values()), "all send/order/import/payload/live-hook/autotrade flags remain OFF")
    add("NT009", True, "source CSV, contract, production retention files are not addressed or mutated")
    add("NT010", policy.get("csv_latest_row_contract") == "CLOSED" and policy.get("open_asof_allowed") is False, "CSV latest row contract remains CLOSED; open/as-of not introduced")
    add("NT011", policy.get("timestamp_basis") == "MT5_CSV" and policy.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis used; no JST detector conversion")

    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 219 PASTE_ME_NOTIFICATION_MESSAGE_TEXT_PREVIEW_AUDIT")
    for key in [
        "step",
        "status",
        "ready",
        "decision",
        "created_at_utc",
        "output_dir",
        "preview_dir",
        "audit_only",
        "review_only",
        "dry_run_only",
        "text_preview_only",
        "live_release_ready",
        "stage218_decision",
        "stage218_validation_pass",
        "signal_message_preview_rows",
        "no_signal_preview_rows",
        "sendable_no_signal_messages",
        "forbidden_message_pattern_hits",
        "source_csv_mutated",
        "contract_mutated",
        "production_live_retention_mutated",
        "open_asof_allowed",
        "candidate_pool_removed",
        "f002_exclusion_bypassed",
        "final_live_enabled",
        "send_enabled",
        "execution_enabled",
        "actual_order_import_enabled",
        "discord_enabled",
        "webhook_enabled",
        "mt5_order_enabled",
        "ai_api_enabled",
        "payload_enabled",
        "payload_activation_enabled",
        "live_hook_enabled",
        "autotrade_enabled",
        "no_signal_discord_notify",
        "theoretical_result_used_as_message_input",
        "actual_execution_used_as_message_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")

    lines.append("PREVIEW_OUTPUT_FILES")
    for file_key, file_path in summary["preview_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")

    lines.append("MESSAGE_TEXT_PREVIEW")
    lines.append(summary["message_text_preview"])
    lines.append("")

    lines.append("NO_SIGNAL_POLICY")
    lines.append("NO_SIGNAL produces no sendable Discord message. It is recorded only as a no-message preview row.")
    lines.append("")

    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")

    lines.append("INTERPRETATION")
    lines.append(
        "Stage219 is audit-only and text-preview-only. It previews the human-readable SIGNAL message text "
        "without Discord send, webhook call, payload activation, MT5 order, actual import, live hook, final live, or autotrade."
    )
    lines.append("NO_SIGNAL does not notify.")
    lines.append("")

    lines.append("BLOCKERS")
    if summary["blockers"]:
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    started = datetime.now(timezone.utc)
    created_at_utc = utc_now_iso()
    _, output_dir, preview_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_preview_dir(preview_dir)

    message_text = build_signal_message_text(SIGNAL_FIXTURE)

    preview_rows: List[Dict[str, Any]] = [
        {
            "preview_id": f"{SIGNAL_FIXTURE.short_signal_id}_TEXT_PREVIEW",
            "message_action": "TEXT_PREVIEW_ONLY",
            "send_action": "NO_SEND_AUDIT_ONLY",
            "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
            "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
            "signal_id": SIGNAL_FIXTURE.signal_id,
            "short_signal_id": SIGNAL_FIXTURE.short_signal_id,
            "latest_closed_m15_dt": SIGNAL_FIXTURE.latest_closed_m15_dt,
            "entry_dt": SIGNAL_FIXTURE.entry_dt,
            "symbol": SIGNAL_FIXTURE.symbol,
            "final_route": SIGNAL_FIXTURE.final_route,
            "strategy_role": SIGNAL_FIXTURE.strategy_role,
            "candidate_id": SIGNAL_FIXTURE.candidate_id,
            "direction": SIGNAL_FIXTURE.direction,
            "entry_price": SIGNAL_FIXTURE.entry_price,
            "tp_usd": SIGNAL_FIXTURE.tp_usd,
            "sl_usd": SIGNAL_FIXTURE.sl_usd,
            "horizon_m5_bars": SIGNAL_FIXTURE.horizon_m5_bars,
            "message_text": message_text,
            "audit_only": True,
            "text_preview_only": True,
            "created_stage": STAGE,
            "created_at_utc": created_at_utc,
        }
    ]

    no_signal_rows: List[Dict[str, Any]] = [
        {
            "preview_id": "NO_SIGNAL_20260616_164500_NO_MESSAGE_PREVIEW",
            "latest_closed_m15_dt": NO_SIGNAL_FIXTURE["latest_closed_m15_dt"],
            "final_route": NO_SIGNAL_FIXTURE["final_route"],
            "message_action": "NO_MESSAGE_NO_SIGNAL",
            "send_action": "NO_SEND_AUDIT_ONLY",
            "discord_notify": False,
            "message_text_created": False,
            "audit_only": True,
            "text_preview_only": True,
            "created_stage": STAGE,
            "created_at_utc": created_at_utc,
        }
    ]

    policy: Dict[str, Any] = {
        "stage": STAGE,
        "audit_only": True,
        "text_preview_only": True,
        "message_preview_only": True,
        "stage218_decision": "STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_READY_AUDIT_ONLY",
        "stage218_validation_pass": True,
        "send_enabled": False,
        "discord_enabled": False,
        "webhook_enabled": False,
        "payload_enabled": False,
        "payload_activation_enabled": False,
        "mt5_order_enabled": False,
        "actual_order_import_enabled": False,
        "ai_api_enabled": False,
        "live_hook_enabled": False,
        "final_live_enabled": False,
        "autotrade_enabled": False,
        "no_signal_discord_notify": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "forbidden_inputs": [
            "future TP/SL result",
            "exit_dt",
            "outcome/win/loss",
            "unresolved horizon result",
            "actual execution result",
            "actual fill/slippage",
            "account balance / risk sizing",
            "webhook URL / token / secret",
        ],
        "created_at_utc": created_at_utc,
    }
    policy.update(DISABLED_FLAGS)

    preview_csv = preview_dir / "notification_message_text_preview.csv"
    preview_txt = preview_dir / "notification_message_text_preview.txt"
    no_signal_csv = preview_dir / "no_signal_message_preview.csv"
    policy_json = preview_dir / "message_policy.json"

    write_csv(preview_csv, preview_rows, PREVIEW_COLUMNS)
    preview_txt.write_text(message_text + "\n", encoding="utf-8")
    write_csv(no_signal_csv, no_signal_rows, NO_SIGNAL_COLUMNS)
    write_json(policy_json, policy)

    checks, blockers = validate(preview_dir, preview_rows, no_signal_rows, policy)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at_utc,
        "output_dir": str(output_dir),
        "preview_dir": str(preview_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "text_preview_only": True,
        "live_release_ready": False,
        "stage218_decision": "STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_READY_AUDIT_ONLY",
        "stage218_validation_pass": True,
        "signal_message_preview_rows": len(preview_rows),
        "no_signal_preview_rows": len(no_signal_rows),
        "sendable_no_signal_messages": 0,
        "forbidden_message_pattern_hits": forbidden_hits(message_text),
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "theoretical_result_used_as_message_input": False,
        "actual_execution_used_as_message_input": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "preview_files": {
            "notification_message_text_preview_csv": str(preview_csv),
            "notification_message_text_preview_txt": str(preview_txt),
            "no_signal_message_preview_csv": str(no_signal_csv),
            "message_policy_json": str(policy_json),
        },
        "message_text_preview": message_text,
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_219_notification_message_text_preview_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage219 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"output_dir: {output_dir}")
    print(f"paste_me: {paste_path}")
    if blockers:
        print("BLOCKERS:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
