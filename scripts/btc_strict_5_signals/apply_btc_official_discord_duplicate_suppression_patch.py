#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch BTC strict-5 official Discord notifier to suppress repeated notifications per M15 candle.

Problem fixed:
- BTC official Discord notification uses only the CSV ledger for duplicate checks.
- If the ledger is not seen/updated as expected, the same signal can be notified
  again on the next minute loop cycle.
- Raw signal_time is used in the key; this patch normalizes it to the M15 candle
  bucket to make duplicate keys stable.

Patch strategy:
1. Normalize notification_key time to a stable 15-minute candle bucket.
2. Read existing CSV ledger keys and their normalized forms.
3. Add an independent JSON seen-state file beside the CSV ledger.
4. Mark a key in both CSV ledger and JSON state immediately after successful
   Discord send or explicit preview mark.

Run once from repository root after pulling:
  python scripts\btc_strict_5_signals\apply_btc_official_discord_duplicate_suppression_patch.py

Then restart the BTC official Discord notification BAT.

Safety:
- Does not change BTC strict-5 signal conditions.
- Does not change TP/SL/filter logic.
- Does not call MT5/order_send.
- Does not affect BTC guarded demo sender, which has its own order ledger.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "scripts" / "btc_strict_5_signals" / "run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py"


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
    print(f"[PATCH] {label}")
    return text.replace(old, new, 1)


def main() -> int:
    text = read(TARGET)
    original = text

    text = replace_once(
        text,
        'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v4_wall_clock_guard_send_error_summary"\n',
        'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard"\nDEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_seen_keys.json")\n',
        "schema version and seen-state default",
    )

    old_block = '''def load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    return set(df["notification_key"].dropna().astype(str).tolist())\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n\n\ndef notification_key(row: pd.Series, filter_variant: str) -> str:\n    return "|".join([\n        DEFAULT_SYMBOL,\n        "STRICT5",\n        "OFFICIAL_NUMERIC_AI_TAGS",\n        filter_variant,\n        clean_str(row.get("strategy_id")),\n        clean_str(row.get("direction")),\n        clean_str(row.get("signal_time")),\n    ])\n'''
    new_block = '''def notification_bucket_time_text(value: Any) -> str:\n    ts = pd.to_datetime(value, errors="coerce")\n    if pd.isna(ts):\n        return clean_str(value)\n    # BTC official strict-5 is M15-based.  Use the stable M15 bucket so the\n    # same candle cannot become multiple notification keys if a timestamp is\n    # slightly refreshed during the minute loop.\n    return pd.Timestamp(ts).floor("15min").strftime("%Y-%m-%d %H:%M:%S")\n\n\ndef normalize_notification_key(key: Any) -> str:\n    text = clean_str(key)\n    parts = text.split("|")\n    if len(parts) >= 7 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT5":\n        parts[6] = notification_bucket_time_text(parts[6])\n        return "|".join(parts[:7])\n    return text\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    keys: set[str] = set()\n    for value in df["notification_key"].dropna().astype(str).tolist():\n        raw = clean_str(value)\n        if raw:\n            keys.add(raw)\n            keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef load_seen_state_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        with open(windows_long_path(path), "r", encoding="utf-8") as f:\n            obj = json.load(f)\n    except Exception:\n        return set()\n    rows = obj.get("seen", []) if isinstance(obj, dict) else []\n    keys: set[str] = set()\n    if isinstance(rows, list):\n        for row in rows:\n            key = row.get("notification_key") if isinstance(row, dict) else row\n            raw = clean_str(key)\n            if raw:\n                keys.add(raw)\n                keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef mark_seen_state_key(path: Path, key: str, row: pd.Series, filter_variant: str) -> None:\n    mkdirp(path.parent)\n    existing: list[dict[str, Any]] = []\n    if path.exists():\n        try:\n            with open(windows_long_path(path), "r", encoding="utf-8") as f:\n                obj = json.load(f)\n            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):\n                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]\n        except Exception:\n            existing = []\n    normalized = normalize_notification_key(key)\n    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}\n    by_key[normalized] = {\n        "notified_at_utc": utc_now_text(),\n        "notification_key": normalized,\n        "filter_variant": filter_variant,\n        "strategy_id": clean_str(row.get("strategy_id")),\n        "direction": clean_str(row.get("direction")),\n        "signal_time": clean_str(row.get("signal_time")),\n        "bucket_time": notification_bucket_time_text(row.get("signal_time")),\n        "schema_version": SCHEMA_VERSION,\n    }\n    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at_utc")))[-1000:]\n    tmp = path.with_suffix(path.suffix + ".tmp")\n    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:\n        json.dump({"schema_version": SCHEMA_VERSION, "updated_at_utc": utc_now_text(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n    os.replace(windows_long_path(tmp), windows_long_path(path))\n\n\ndef append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n\n\ndef notification_key(row: pd.Series, filter_variant: str) -> str:\n    return "|".join([\n        DEFAULT_SYMBOL,\n        "STRICT5",\n        "OFFICIAL_NUMERIC_AI_TAGS",\n        filter_variant,\n        clean_str(row.get("strategy_id")),\n        clean_str(row.get("direction")),\n        notification_bucket_time_text(row.get("signal_time")),\n    ])\n'''
    text = replace_once(text, old_block, new_block, "stable M15 key + seen-state + durable ledger")

    text = replace_once(
        text,
        '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n',
        '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n    p.add_argument("--seen-state-json", type=Path, default=DEFAULT_SEEN_STATE_JSON)\n',
        "seen-state CLI arg",
    )

    text = replace_once(
        text,
        '''    ledger_csv = resolve_repo_path(args.ledger_csv)\n    env_file = resolve_repo_path(args.env_file)\n''',
        '''    ledger_csv = resolve_repo_path(args.ledger_csv)\n    seen_state_json = resolve_repo_path(args.seen_state_json)\n    env_file = resolve_repo_path(args.env_file)\n''',
        "resolve seen-state path",
    )

    text = replace_once(
        text,
        '''    notified_keys = load_notified_keys(ledger_csv)\n    ledger_rows: list[dict[str, Any]] = []\n''',
        '''    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    ledger_rows: list[dict[str, Any]] = []\n''',
        "load seen-state keys",
    )

    text = replace_once(
        text,
        '''    send_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n''',
        '''    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n''',
        "add duplicate-state error lists",
    )

    old_mark = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            ledger_rows.append(ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score))\n    append_ledger(ledger_csv, ledger_rows)\n'''
    new_mark = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            lr = ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score)\n            try:\n                append_ledger_row_durable(ledger_csv, lr)\n                ledger_rows.append(lr)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n            try:\n                mark_seen_state_key(seen_state_json, key, row, args.filter_variant)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                seen_state_errors.append(err)\n                print(f"Seen-state append error after send/mark: {err}", flush=True)\n'''
    text = replace_once(text, old_mark, new_mark, "immediate ledger and seen-state marking")

    text = replace_once(
        text,
        '''        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n''',
        '''        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n''',
        "summary cycle_ok",
    )

    text = replace_once(
        text,
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "openai_called": False,\n''',
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key",\n        "openai_called": False,\n''',
        "summary duplicate guard fields",
    )

    text = replace_once(
        text,
        '''        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv)},\n''',
        '''        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv), "seen_state_json": str(seen_state_json)},\n''',
        "summary output seen-state path",
    )

    text = replace_once(
        text,
        '''            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n''',
        '''            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_15min_candle_bucket": True,\n''',
        "safety duplicate guard flags",
    )

    text = replace_once(
        text,
        '''    return 0 if len(send_errors) == 0 else 1\n''',
        '''    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else 1\n''',
        "return code includes duplicate-state errors",
    )

    if text != original:
        write(TARGET, text)
        print(f"[OK] patched {TARGET}")
    else:
        print(f"[OK] already patched {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
