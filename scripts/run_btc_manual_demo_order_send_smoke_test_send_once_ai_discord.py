#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC manual send-once wrapper with AI-history Discord notification.

This wraps run_btc_manual_demo_order_send_smoke_test_send_once.py and adds a
Discord notification step after the guarded sender stage.

Safety:
- Does not modify MT5 sender input payload.
- Does not call AI API.
- Uses existing trade_ai_tag_summary.csv only when present.
- Uses a dedicated BTC Discord send ledger for duplicate prevention.
- If the guarded send is repeat-blocked, Discord is not sent.
- If the guarded send fails, Discord is not sent.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts" / "run_btc_manual_demo_order_send_smoke_test_send_once.py"
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "prepare_btc_payload_for_ai_discord.py"
DISCORD_SCRIPT = REPO_ROOT / "scripts" / "send_mochipoyo_discord_messages.py"
DEFAULT_OUT_DIR = Path("data/r/btc_manual_demo_order_send_smoke_test_send_once")
DEFAULT_SEND_LEDGER = Path("data/runtime_state/btc/manual_demo/multi_ai_history_discord_send_ledger.csv")
SUMMARY_FILENAME = "latest_btc_manual_demo_order_send_smoke_test_send_once_ai_discord_result.json"
BASE_SUMMARY_FILENAME = "latest_btc_manual_demo_order_send_smoke_test_send_once_result.json"


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or default)
    except Exception:
        try:
            return int(float(obj.get(key, default)))
        except Exception:
            return default


def run_cmd(label: str, cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BTC manual send-once and send AI-history Discord notification when safe.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="BTCUSD#")
    p.add_argument("--symbol-candidates", default="BTCUSD#,BTCUSD,BTCUSD.,BTCUSDm,BTCUSDmicro")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="BUY")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--min-distance-usd", type=float, default=100.0)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--magic", type=int, default=26050603)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--allow-repeat-send", action="store_true")
    p.add_argument("--disable-ai-discord", dest="enable_ai_discord", action="store_false")
    p.add_argument("--btc-ai-discord-send-ledger-csv", type=Path, default=DEFAULT_SEND_LEDGER)
    p.add_argument("--ai-history-tag-summary-csv", type=Path, default=Path("data/runtime_logs/trade_ai_review/trade_ai_tag_summary.csv"))
    p.set_defaults(enable_ai_discord=True)
    return p.parse_args()


def build_base_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable, str(BASE_SCRIPT),
        "--out-dir", str(args.out_dir),
        "--symbol", str(args.symbol),
        "--symbol-candidates", str(args.symbol_candidates),
        "--direction", str(args.direction),
        "--fixed-lot", str(args.fixed_lot),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--max-orders", str(args.max_orders),
        "--min-distance-usd", str(args.min_distance_usd),
        "--expected-login", str(args.expected_login),
        "--magic", str(args.magic),
        "--deviation", str(args.deviation),
    ]
    cmd.append("--require-demo-account" if args.require_demo_account else "--no-require-demo-account")
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    if args.send:
        cmd.append("--send")
    if args.allow_repeat_send:
        cmd.append("--allow-repeat-send")
    return cmd


def should_send_discord(base_rc: int, base_summary: dict[str, Any], args: argparse.Namespace) -> tuple[bool, str]:
    if not args.enable_ai_discord:
        return False, "AI_DISCORD_DISABLED"
    if base_rc != 0:
        return False, f"BASE_SCRIPT_FAILED rc={base_rc}"
    if not bool(base_summary.get("cycle_ok", False)):
        return False, "BASE_CYCLE_NOT_OK"
    if not bool(base_summary.get("sender_invoked", False)):
        return False, "SENDER_NOT_INVOKED_REPEAT_BLOCK_OR_SUPPRESSED"
    if not bool(base_summary.get("send_flag_passed_to_sender", False)):
        return False, "SEND_FLAG_NOT_PASSED_TO_SENDER"
    if safe_int(base_summary, "sender_sent_rows", 0) <= 0:
        return False, "NO_SENT_ROWS"
    return True, "OK_TO_SEND_AI_DISCORD"


def read_discord_result(preview_json: Path) -> dict[str, Any]:
    obj = read_json_or_empty(preview_json)
    records = obj.get("records", []) if isinstance(obj.get("records"), list) else []
    sent = sum(1 for r in records if isinstance(r, dict) and bool(r.get("sent")))
    errors = sum(1 for r in records if isinstance(r, dict) and str(r.get("send_status", "")).startswith("ERROR"))
    warnings = sum(1 for r in records if isinstance(r, dict) and str(r.get("ai_history_warning_status", "")).upper() == "WARN")
    return {"records": len(records), "sent": sent, "errors": errors, "warning_rows": warnings, "raw": obj}


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ai_dir = args.out_dir / "ai_history_discord"
    ai_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "base_summary_json": args.out_dir / BASE_SUMMARY_FILENAME,
        "payload_csv": args.out_dir / "payload" / "btc_manual_send_once_order_payloads.csv",
        "discord_input_csv": ai_dir / "btc_ai_discord_input.csv",
        "preview_txt": ai_dir / "btc_ai_history_discord_preview.txt",
        "preview_json": ai_dir / "btc_ai_history_discord_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
    }

    base_rc, base_seconds = run_cmd("btc_manual_send_once_base", build_base_cmd(args))
    base_summary = read_json_or_empty(paths["base_summary_json"])
    ok_to_discord, discord_reason = should_send_discord(base_rc, base_summary, args)

    prepare_rc: int | str = "SKIPPED"
    discord_rc: int | str = "SKIPPED"
    prepare_seconds = 0.0
    discord_seconds = 0.0
    discord_result: dict[str, Any] = {"records": 0, "sent": 0, "errors": 0, "warning_rows": 0}

    if ok_to_discord:
        prepare_rc, prepare_seconds = run_cmd("prepare_btc_payload_for_ai_discord", [
            sys.executable, str(PREPARE_SCRIPT),
            "--input-csv", str(paths["payload_csv"]),
            "--output-csv", str(paths["discord_input_csv"]),
        ])
        if prepare_rc == 0:
            discord_rc, discord_seconds = run_cmd("btc_ai_history_discord_send", [
                sys.executable, str(DISCORD_SCRIPT),
                "--input-csv", str(paths["discord_input_csv"]),
                "--send-ledger-csv", str(args.btc_ai_discord_send_ledger_csv),
                "--preview-txt", str(paths["preview_txt"]),
                "--preview-json", str(paths["preview_json"]),
                "--symbol", "BTC",
                "--max-rows", "1",
                "--style", "compact",
                "--send",
                "--ai-history-tag-summary-csv", str(args.ai_history_tag_summary_csv),
            ])
            discord_result = read_discord_result(paths["preview_json"])
        else:
            discord_reason = f"PREPARE_FAILED rc={prepare_rc}"
    else:
        write_json(paths["preview_json"], {
            "source": "run_btc_manual_demo_order_send_smoke_test_send_once_ai_discord.py",
            "ai_history_warning": {
                "ai_history_warning_enabled": bool(args.enable_ai_discord),
                "ai_history_warning_status": discord_reason,
                "ai_history_warning_rows_warn": 0,
            },
            "records": [],
        })
        write_text(paths["preview_txt"], f"BTC AI Discord: {discord_reason}\n")

    cycle_ok = bool(base_rc == 0 and bool(base_summary.get("cycle_ok", False)) and (not ok_to_discord or (discord_rc == 0 and int(discord_result.get("errors", 0) or 0) == 0)))
    summary = {
        "schema_version": "btc_manual_send_once_ai_discord_v1",
        "cycle_ok": cycle_ok,
        "reason": "BTC_MANUAL_SEND_ONCE_AI_DISCORD_PASS" if cycle_ok else "BTC_MANUAL_SEND_ONCE_AI_DISCORD_FAILED",
        "base_returncode": base_rc,
        "base_cycle_ok": bool(base_summary.get("cycle_ok", False)),
        "base_reason": base_summary.get("reason", ""),
        "send_flag_passed_to_sender": bool(base_summary.get("send_flag_passed_to_sender", False)),
        "sender_sent_rows": safe_int(base_summary, "sender_sent_rows", 0),
        "ai_discord_enabled": bool(args.enable_ai_discord),
        "ai_discord_attempted": bool(ok_to_discord),
        "ai_discord_reason": discord_reason,
        "prepare_returncode": prepare_rc,
        "discord_returncode": discord_rc,
        "discord_records": discord_result.get("records", 0),
        "discord_sent": discord_result.get("sent", 0),
        "discord_errors": discord_result.get("errors", 0),
        "discord_warning_rows": discord_result.get("warning_rows", 0),
        "safety": {
            "mt5_payload_modified": False,
            "ai_api_called": False,
            "discord_duplicate_ledger": str(args.btc_ai_discord_send_ledger_csv),
            "discord_only_after_successful_send": True,
        },
        "paths": {k: str(v) for k, v in paths.items()} | {"btc_ai_discord_send_ledger_csv": str(args.btc_ai_discord_send_ledger_csv)},
        "timing": {
            "base_seconds": base_seconds,
            "prepare_seconds": prepare_seconds,
            "discord_seconds": discord_seconds,
            "total_seconds": round(time.perf_counter() - started, 3),
        },
        "base_summary": base_summary,
    }
    write_json(paths["summary_json"], summary)

    print("=" * 80, flush=True)
    print("BTC manual send-once AI Discord summary", flush=True)
    print(json.dumps({
        "cycle_ok": summary["cycle_ok"],
        "reason": summary["reason"],
        "base_reason": summary["base_reason"],
        "ai_discord_attempted": summary["ai_discord_attempted"],
        "ai_discord_reason": summary["ai_discord_reason"],
        "discord_sent": summary["discord_sent"],
        "discord_errors": summary["discord_errors"],
        "discord_warning_rows": summary["discord_warning_rows"],
        "preview_txt": str(paths["preview_txt"]),
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
