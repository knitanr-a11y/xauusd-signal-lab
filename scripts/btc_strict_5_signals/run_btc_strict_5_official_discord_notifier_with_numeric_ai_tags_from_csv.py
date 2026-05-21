#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC strict 5 official notifier entrypoint.

The original notifier body is kept next to this file as:
    _run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv_original.py

This entrypoint executes that body after applying a narrow, in-memory cleanup
for duplicate summary keys left by the duplicate-guard hotfix. No local patch
step is required.
"""
from __future__ import annotations

from pathlib import Path

_ORIGINAL = Path(__file__).with_name("_run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv_original.py")


def _clean_source(text: str) -> str:
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
        '        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key",\n'
        '        "ledger_append_error_rows": int(len(ledger_errors)),\n'
        '        "ledger_append_errors": ledger_errors,\n',
        '        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key",\n',
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
        "ledger_append_error_rows summary key": text.count('"ledger_append_error_rows": int(len(ledger_errors)),') == 1,
        "ledger_append_errors summary key": text.count('"ledger_append_errors": ledger_errors,') == 1,
        "summary_errors_ok includes seen_state_errors": "summary_errors_ok = len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0" in text,
        "return code uses summary_errors_ok": "return 0 if summary_errors_ok else 1" in text,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("BTC notifier cleanup verification failed: " + ", ".join(failed))


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
