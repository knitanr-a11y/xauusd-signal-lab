#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply immediate-ledger hardening to GOLD strict7 and BTC strict5 Discord notifiers.

This local patcher is intentionally small and text-based because the target
notifier files are large.  It changes the notification ledger behavior from
"append all rows at the end" to "append each row immediately after successful
Discord send or explicit preview/dry-run mark".

Run once from repository root:
  python scripts/apply_immediate_discord_ledger_patch.py

The patch is idempotent.  It does not change signal conditions, filters,
Discord webhooks, MT5 settings, or order sending code.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GOLD = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_discord_notifier_from_csv.py"
BTC = REPO_ROOT / "scripts" / "btc_strict_5_signals" / "run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[SKIP] {label}: already patched")
        return text
    if old not in text:
        raise SystemExit(f"[ERROR] pattern not found for {label}")
    return text.replace(old, new, 1)


def patch_gold() -> None:
    path = GOLD
    text = read(path)
    original = text

    old_append = '''def append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n'''
    new_append = '''def append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n'''
    text = replace_once(text, old_append, new_append, "gold durable append helper")

    text = replace_once(
        text,
        '''    send_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n''',
        '''    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n''',
        "gold ledger_errors variable",
    )

    old_block = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_rows.append({\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            })\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n    append_ledger(ledger_csv, ledger_rows)\n'''
    new_block = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_row = {\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            }\n            try:\n                append_ledger_row_durable(ledger_csv, ledger_row)\n                ledger_rows.append(ledger_row)\n                notified_keys.add(key)\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n'''
    text = replace_once(text, old_block, new_block, "gold immediate ledger append block")

    text = replace_once(
        text,
        '''        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n''',
        '''        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 else "SEND_OR_LEDGER_ERROR_SUMMARY_WRITTEN",\n''',
        "gold summary cycle_ok",
    )

    text = replace_once(
        text,
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "dry_run": bool(args.dry_run),\n''',
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "ledger_append_mode": "immediate_after_each_successful_send_or_mark",\n        "dry_run": bool(args.dry_run),\n''',
        "gold summary ledger error fields",
    )

    text = replace_once(
        text,
        '''            "ledger_append_requires_send_success_or_mark_dry_run": True,\n''',
        '''            "ledger_append_requires_send_success_or_mark_dry_run": True,\n            "ledger_append_immediate_after_successful_send": True,\n''',
        "gold safety immediate ledger flag",
    )

    text = replace_once(
        text,
        '''    return 0 if len(send_errors) == 0 else 1\n''',
        '''    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 else 1\n''',
        "gold return code",
    )

    if text != original:
        write(path, text)
        print(f"[OK] patched {path}")
    else:
        print(f"[OK] no changes needed {path}")


def patch_btc() -> None:
    path = BTC
    text = read(path)
    original = text

    old_append = '''def append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n'''
    new_append = '''def append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n'''
    text = replace_once(text, old_append, new_append, "btc durable append helper")

    text = replace_once(
        text,
        '''    send_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n''',
        '''    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n''',
        "btc ledger_errors variable",
    )

    old_block = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            ledger_rows.append(ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score))\n    append_ledger(ledger_csv, ledger_rows)\n    summary = {\n'''
    new_block = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            row_to_write = ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score)\n            try:\n                append_ledger_row_durable(ledger_csv, row_to_write)\n                ledger_rows.append(row_to_write)\n                notified_keys.add(key)\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n    summary = {\n'''
    text = replace_once(text, old_block, new_block, "btc immediate ledger append block")

    text = replace_once(
        text,
        '''        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n''',
        '''        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 else "SEND_OR_LEDGER_ERROR_SUMMARY_WRITTEN",\n''',
        "btc summary cycle_ok",
    )

    text = replace_once(
        text,
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "openai_called": False,\n''',
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "openai_called": False,\n''',
        "btc summary ledger error fields",
    )

    text = replace_once(
        text,
        '''        "ledger_rows_appended": int(len(ledger_rows)),\n        "d1_used": False,\n''',
        '''        "ledger_rows_appended": int(len(ledger_rows)),\n        "ledger_append_mode": "immediate_after_each_successful_send_or_mark",\n        "d1_used": False,\n''',
        "btc summary ledger mode",
    )

    text = replace_once(
        text,
        '''            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n''',
        '''            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n            "ledger_append_immediate_after_successful_send": True,\n''',
        "btc safety immediate ledger flag",
    )

    text = replace_once(
        text,
        '''    return 0 if len(send_errors) == 0 else 1\n''',
        '''    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 else 1\n''',
        "btc return code",
    )

    if text != original:
        write(path, text)
        print(f"[OK] patched {path}")
    else:
        print(f"[OK] no changes needed {path}")


def main() -> int:
    patch_gold()
    patch_btc()
    print("[DONE] immediate Discord ledger patch applied. Restart GOLD/BTC notifier BATs after pulling and running this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
