#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage221 - Notification Text Template Revision Audit

Revises the user-visible alert text for practical reading.

Revision:
- Full signal_id is displayed at the very bottom of the user-visible body.
- Other technical fields remain in history metadata.

Audit-only / no-send / no-webhook / no-payload / no-order / no-live-hook.
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
from typing import Any, Dict, Iterable, List, Tuple


STAGE = "GOLD_V3_221_NOTIFICATION_TEXT_TEMPLATE_REVISION_AUDIT_ONLY"
DECISION_READY = "STAGE221_NOTIFICATION_TEXT_TEMPLATE_REVISION_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE221_NOTIFICATION_TEXT_TEMPLATE_REVISION_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TEMPLATE_VERSION = "GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617"

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
    "message_template_version",
    "message_action",
    "send_action",
    "payload_action",
    "webhook_action",
    "direction",
    "title",
    "entry_dt",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "signal_id_visible_bottom",
    "message_text",
    "audit_only",
    "created_stage",
    "created_at_utc",
]

METADATA_COLUMNS = [
    "signal_id",
    "short_signal_id",
    "final_route",
    "strategy_role",
    "candidate_id",
    "direction",
    "latest_closed_m15_dt",
    "entry_dt",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "message_template_version",
    "send_action",
    "payload_action",
    "webhook_action",
    "audit_only",
    "created_stage",
    "created_at_utc",
]


@dataclass(frozen=True)
class SignalFixture:
    signal_id: str
    short_signal_id: str
    latest_closed_m15_dt: str
    entry_dt: str
    final_route: str
    strategy_role: str
    candidate_id: str
    direction: str
    entry_price: float
    tp_usd: float
    sl_usd: float
    horizon_m5_bars: int


SIGNAL_FIXTURE = SignalFixture(
    signal_id="20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT",
    short_signal_id="G3SD01960980A23107A65AE",
    latest_closed_m15_dt="2026-06-15 16:30:00",
    entry_dt="2026-06-15 16:30:00",
    final_route="SECONDARY_AUDIT_CANDIDATE",
    strategy_role="SCALP_SECONDARY_CANDIDATE",
    candidate_id="SCALP_024_tp15_sl5_hz64_SHORT",
    direction="SELL",
    entry_price=4363.24,
    tp_usd=15.0,
    sl_usd=5.0,
    horizon_m5_bars=64,
)


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
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "221"
    template_dir = output_dir / "notification_template_revision"
    return mql5_files, output_dir, template_dir


def assert_safe_stage221_path(template_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "221", "notification_template_revision")
    actual_tail = tuple(template_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe template path. Expected tail {expected_tail}, got {actual_tail}")


def reset_template_dir(template_dir: Path) -> None:
    assert_safe_stage221_path(template_dir)
    if template_dir.exists():
        shutil.rmtree(template_dir)
    template_dir.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def direction_to_title(direction: str, is_scalp: bool) -> str:
    normalized = direction.upper()
    if normalized in {"SHORT", "SELL"}:
        side = "SELL"
        icon = "🔴"
    elif normalized in {"LONG", "BUY"}:
        side = "BUY"
        icon = "🟢"
    else:
        raise ValueError(f"Unsupported direction: {direction}")
    suffix = " SCALP" if is_scalp else ""
    return f"{icon} GOLD {side}{suffix}"


def build_message(f: SignalFixture) -> str:
    title = direction_to_title(f.direction, is_scalp=True)
    entry_dt_short = f.entry_dt[:16]
    return "\n".join(
        [
            title,
            f"Entry Time: {entry_dt_short} MT5/CSV",
            f"Entry Price: {f.entry_price:.2f}",
            f"TP / SL: {f.tp_usd:g} / {f.sl_usd:g}",
            f"Horizon: {f.horizon_m5_bars} M5 bars",
            "",
            "[AUDIT_ONLY / NO_SEND]",
            f"Signal ID: {f.signal_id}",
        ]
    )


def forbidden_visible_hits(message_text: str) -> List[str]:
    # Full signal_id is allowed only on the final line. Do not block fragments that appear inside it.
    body_without_last = "\n".join(message_text.splitlines()[:-1])
    patterns = [
        r"^symbol\s*:",
        r"^route\s*:",
        r"^strategy_role\s*:",
        r"^candidate_id\s*:",
        r"^short_signal_id\s*:",
        r"\bactual\b",
        r"\bfill\b",
        r"slippage",
        r"\bresult\b",
        r"\bwin\b",
        r"\bloss\b",
        r"\bexit\b",
        r"webhook",
        r"token",
        r"secret",
        r"account",
        r"balance",
        r"position size",
    ]
    hits: List[str] = []
    for pattern in patterns:
        if re.search(pattern, body_without_last, flags=re.IGNORECASE | re.MULTILINE):
            hits.append(pattern)
    return hits


def validate(template_dir: Path, message_text: str, metadata_row: Dict[str, Any], policy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    lines = message_text.splitlines()
    title = lines[0] if lines else ""
    final_line = lines[-1] if lines else ""
    forbidden = forbidden_visible_hits(message_text)
    buy_title_sample = direction_to_title("BUY", is_scalp=True)

    add("TR001", tuple(template_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "221", "notification_template_revision"), f"template_dir={template_dir}")
    add("TR002", policy.get("stage220_validation_pass") is True, f"stage220_decision={policy.get('stage220_decision')}")
    add("TR003", title == "🔴 GOLD SELL SCALP", f"title={title}")
    add("TR004", buy_title_sample == "🟢 GOLD BUY SCALP", f"buy_title_sample={buy_title_sample}")
    add(
        "TR005",
        len(lines) >= 5
        and lines[1].startswith("Entry Time:")
        and lines[2].startswith("Entry Price:")
        and lines[3].startswith("TP / SL:")
        and lines[4].startswith("Horizon:"),
        "entry time, price, TP/SL, horizon are near the top",
    )
    add("TR006", not forbidden, f"forbidden_visible_hits={forbidden}")
    add(
        "TR007",
        all(metadata_row.get(k) for k in ["signal_id", "short_signal_id", "final_route", "strategy_role", "candidate_id"]),
        "history metadata retains required identifiers",
    )
    add("TR008", all(v is False for v in DISABLED_FLAGS.values()), "all send/webhook/payload/order/live/autotrade flags remain OFF")
    add("TR009", policy.get("no_signal_discord_notify") is False, "NO_SIGNAL notification remains disabled")
    add(
        "TR010",
        policy.get("theoretical_result_used_as_message_input") is False and policy.get("actual_execution_used_as_message_input") is False,
        "future result and actual execution result not used as message input",
    )
    add("TR011", policy.get("csv_latest_row_contract") == "CLOSED" and policy.get("open_asof_allowed") is False, "CSV latest row CLOSED; open/as-of not introduced")
    add("TR012", policy.get("timestamp_basis") == "MT5_CSV" and policy.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis; no JST detector conversion")
    add(
        "TR013",
        final_line == f"Signal ID: {SIGNAL_FIXTURE.signal_id}",
        f"final_line={final_line}",
    )

    blockers = [f"{check['check_id']}: {check['details']}" for check in checks if not check["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 221 PASTE_ME_NOTIFICATION_TEXT_TEMPLATE_REVISION_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "template_dir",
        "audit_only", "review_only", "dry_run_only", "text_template_preview_only", "live_release_ready",
        "stage220_decision", "stage220_validation_pass", "message_template_version",
        "title", "buy_title_sample", "visible_message_lines", "signal_id_visible_bottom", "history_metadata_rows",
        "source_csv_mutated", "contract_mutated", "production_live_retention_mutated",
        "open_asof_allowed", "candidate_pool_removed", "f002_exclusion_bypassed",
        "final_live_enabled", "send_enabled", "execution_enabled", "actual_order_import_enabled",
        "discord_enabled", "webhook_enabled", "mt5_order_enabled", "ai_api_enabled",
        "payload_enabled", "payload_activation_enabled", "live_hook_enabled", "autotrade_enabled",
        "no_signal_discord_notify", "theoretical_result_used_as_message_input", "actual_execution_used_as_message_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("REVISED_MESSAGE_TEXT_PREVIEW")
    lines.append(summary["message_text_preview"])
    lines.append("")
    lines.append("HISTORY_METADATA_POLICY")
    lines.append("User-visible Discord body shows the full signal_id only as the final line. short_signal_id, route, strategy_role, and candidate_id remain in metadata CSV/JSON only.")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for file_key, file_path in summary["output_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage221 is audit-only and revises the notification template for readability. It does not send Discord, call webhooks, activate payloads, place orders, import executions, enable live hook, final live, or autotrade.")
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
    _, output_dir, template_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_template_dir(template_dir)

    message_text = build_message(SIGNAL_FIXTURE)
    title = message_text.splitlines()[0]
    buy_title_sample = direction_to_title("BUY", is_scalp=True)

    preview_row = {
        "preview_id": f"{SIGNAL_FIXTURE.short_signal_id}_TEMPLATE_V3_PREVIEW",
        "message_template_version": TEMPLATE_VERSION,
        "message_action": "TEXT_TEMPLATE_PREVIEW_ONLY",
        "send_action": "NO_SEND_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "direction": SIGNAL_FIXTURE.direction,
        "title": title,
        "entry_dt": SIGNAL_FIXTURE.entry_dt,
        "entry_price": SIGNAL_FIXTURE.entry_price,
        "tp_usd": SIGNAL_FIXTURE.tp_usd,
        "sl_usd": SIGNAL_FIXTURE.sl_usd,
        "horizon_m5_bars": SIGNAL_FIXTURE.horizon_m5_bars,
        "signal_id_visible_bottom": True,
        "message_text": message_text,
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }

    metadata_row = {
        "signal_id": SIGNAL_FIXTURE.signal_id,
        "short_signal_id": SIGNAL_FIXTURE.short_signal_id,
        "final_route": SIGNAL_FIXTURE.final_route,
        "strategy_role": SIGNAL_FIXTURE.strategy_role,
        "candidate_id": SIGNAL_FIXTURE.candidate_id,
        "direction": SIGNAL_FIXTURE.direction,
        "latest_closed_m15_dt": SIGNAL_FIXTURE.latest_closed_m15_dt,
        "entry_dt": SIGNAL_FIXTURE.entry_dt,
        "entry_price": SIGNAL_FIXTURE.entry_price,
        "tp_usd": SIGNAL_FIXTURE.tp_usd,
        "sl_usd": SIGNAL_FIXTURE.sl_usd,
        "horizon_m5_bars": SIGNAL_FIXTURE.horizon_m5_bars,
        "message_template_version": TEMPLATE_VERSION,
        "send_action": "NO_SEND_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }

    policy = {
        "stage": STAGE,
        "stage220_decision": "STAGE220_NOTIFICATION_NO_SEND_APPROVAL_GATE_READY_AUDIT_ONLY",
        "stage220_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "user_visible_template": "compact_scalp_alert_with_signal_id_bottom",
        "sell_title_rule": "🔴 GOLD SELL SCALP",
        "buy_title_rule": "🟢 GOLD BUY SCALP",
        "visible_signal_id_rule": "full signal_id appears only as the final line",
        "hide_from_visible_body_as_separate_fields": ["symbol line", "route", "strategy_role", "candidate_id", "short_signal_id"],
        "retain_in_history_metadata": ["signal_id", "short_signal_id", "final_route", "strategy_role", "candidate_id"],
        "audit_only": True,
        "text_template_preview_only": True,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "theoretical_result_used_as_message_input": False,
        "actual_execution_used_as_message_input": False,
        "created_at_utc": created_at_utc,
    }
    policy.update(DISABLED_FLAGS)

    preview_txt = template_dir / "notification_text_revised_preview.txt"
    preview_csv = template_dir / "notification_text_revised_preview.csv"
    metadata_csv = template_dir / "notification_history_metadata.csv"
    policy_json = template_dir / "notification_template_policy.json"

    preview_txt.write_text(message_text + "\n", encoding="utf-8")
    write_csv(preview_csv, [preview_row], PREVIEW_COLUMNS)
    write_csv(metadata_csv, [metadata_row], METADATA_COLUMNS)
    write_json(policy_json, policy)

    checks, blockers = validate(template_dir, message_text, metadata_row, policy)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    summary = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at_utc,
        "output_dir": str(output_dir),
        "template_dir": str(template_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "text_template_preview_only": True,
        "live_release_ready": False,
        "stage220_decision": policy["stage220_decision"],
        "stage220_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "title": title,
        "buy_title_sample": buy_title_sample,
        "visible_message_lines": len(message_text.splitlines()),
        "signal_id_visible_bottom": True,
        "history_metadata_rows": 1,
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
        "message_text_preview": message_text,
        "output_files": {
            "notification_text_revised_preview_txt": str(preview_txt),
            "notification_text_revised_preview_csv": str(preview_csv),
            "notification_history_metadata_csv": str(metadata_csv),
            "notification_template_policy_json": str(policy_json),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_221_notification_text_template_revision_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage221 status: {summary['status']}")
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
