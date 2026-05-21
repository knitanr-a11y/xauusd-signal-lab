#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD strict 7 notifier entrypoint.

The original notifier body is kept next to this file as:
    _run_gold_strict_7_discord_notifier_from_csv_original.py

This entrypoint executes that body after applying a narrow, in-memory cleanup
for duplicate definitions / duplicate summary keys left by the duplicate-guard
hotfix. No local patch step is required.
"""
from __future__ import annotations

from pathlib import Path

_ORIGINAL = Path(__file__).with_name("_run_gold_strict_7_discord_notifier_from_csv_original.py")


def _remove_repeated_exact_block(text: str, block: str) -> str:
    count = text.count(block)
    if count <= 1:
        return text
    first = text.find(block)
    keep_until = first + len(block)
    return text[:keep_until] + text[keep_until:].replace(block, "")


def _clean_source(text: str) -> str:
    bucket_func = '''\ndef notification_bucket_time_text(value: Any) -> str:\n    ts = pd.to_datetime(value, errors="coerce")\n    if pd.isna(ts):\n        return time_text(value)\n    return pd.Timestamp(ts).floor("5min").strftime("%Y-%m-%d %H:%M:%S")\n'''
    text = _remove_repeated_exact_block(text, bucket_func)

    text = text.replace(
        '    print(f"seen_state_json: {seen_state_json}", flush=True)\n'
        '    print(f"seen_state_json: {seen_state_json}", flush=True)\n',
        '    print(f"seen_state_json: {seen_state_json}", flush=True)\n',
        1,
    )

    text = text.replace(
        '            "seen_state_duplicate_guard_enabled": True,\n'
        '            "notification_key_uses_5min_candle_bucket": True,\n'
        '            "seen_state_duplicate_guard_enabled": True,\n'
        '            "notification_key_uses_5min_candle_bucket": True,\n',
        '            "seen_state_duplicate_guard_enabled": True,\n'
        '            "notification_key_uses_5min_candle_bucket": True,\n',
        1,
    )

    if "    summary_errors_ok = len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0\n" not in text:
        text = text.replace(
            "    summary = {\n",
            "    summary_errors_ok = len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0\n"
            "    summary = {\n",
            1,
        )

    text = text.replace(
        '        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0),\n'
        '        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 else "SEND_OR_LEDGER_ERROR_SUMMARY_WRITTEN",\n',
        '        "cycle_ok": bool(summary_errors_ok),\n'
        '        "reason": "OK" if summary_errors_ok else "SEND_LEDGER_OR_SEEN_STATE_ERROR_SUMMARY_WRITTEN",\n',
        1,
    )

    text = text.replace(
        '        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key",\n'
        '        "ledger_append_error_rows": int(len(ledger_errors)),\n'
        '        "ledger_append_errors": ledger_errors,\n',
        '        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key",\n',
        1,
    )

    text = text.replace(
        "    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 else 1\n",
        "    return 0 if summary_errors_ok else 1\n",
        1,
    )
    return text


def _verify_source(text: str) -> None:
    checks = {
        "notification_bucket_time_text definition": text.count("def notification_bucket_time_text(value: Any) -> str:") == 1,
        "seen_state_json print": text.count('print(f"seen_state_json: {seen_state_json}", flush=True)') == 1,
        "ledger_append_error_rows summary key": text.count('"ledger_append_error_rows": int(len(ledger_errors)),') == 1,
        "ledger_append_errors summary key": text.count('"ledger_append_errors": ledger_errors,') == 1,
        "seen_state_duplicate_guard_enabled safety key": text.count('"seen_state_duplicate_guard_enabled": True,') == 1,
        "notification_key_uses_5min_candle_bucket safety key": text.count('"notification_key_uses_5min_candle_bucket": True,') == 1,
        "summary_errors_ok includes seen_state_errors": "summary_errors_ok = len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0" in text,
        "return code uses summary_errors_ok": "return 0 if summary_errors_ok else 1" in text,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("GOLD notifier cleanup verification failed: " + ", ".join(failed))


def _run() -> None:
    source = _clean_source(_ORIGINAL.read_text(encoding="utf-8"))
    _verify_source(source)
    globals_dict = {
        "__name__": __name__,
        "__file__": str(_ORIGINAL),
        "__package__": None,
        "__cached__": None,
    }
    exec(compile(source, str(_ORIGINAL), "exec"), globals_dict)


_run()
