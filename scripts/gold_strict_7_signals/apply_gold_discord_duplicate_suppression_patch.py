#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch GOLD strict-7 Discord notifier to suppress repeated notifications per candle.

Problem fixed:
- After a GOLD strict-7 signal is detected, Discord notification can repeat every
  minute until a new candle arrives if the notification ledger is not seen soon
  enough or if the live row timestamp shifts inside the same M5 candle.

Patch strategy:
1. Normalize notification_key time to a stable 5-minute candle bucket.
2. Read old ledger keys and also their normalized forms for backward compatibility.
3. Add an independent JSON seen-state file beside the CSV ledger.
4. Mark a key in both CSV ledger and JSON state immediately after successful
   Discord send or explicit dry-run mark.

Run once from repository root:
  python scripts\gold_strict_7_signals\apply_gold_discord_duplicate_suppression_patch.py

Then restart the GOLD Discord notification BAT.

Safety:
- Does not change GOLD strict-7 signal conditions.
- Does not change TP/SL.
- Does not call MT5/order_send.
- Does not affect GOLD autotrade, which already has its own order ledger.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_discord_notifier_from_csv.py"


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
        'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v8_wall_clock_guard_send_error_summary"\n',
        'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard"\nDEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/gold/strict_7/discord_notification_seen_keys.json")\n',
        "schema version and seen-state default",
    )

    old_key_block = '''def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:\n    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    return set(df["notification_key"].dropna().astype(str).tolist())\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n'''
    new_key_block = '''def notification_bucket_time_text(value: Any) -> str:\n    ts = pd.to_datetime(value, errors="coerce")\n    if pd.isna(ts):\n        return time_text(value)\n    # Live CSVs can update a forming M5 candle more than once before the next\n    # candle arrives.  Use a stable 5-minute bucket so the same candle is one\n    # notification key even if the raw timestamp shifts by one minute.\n    return pd.Timestamp(ts).floor("5min").strftime("%Y-%m-%d %H:%M:%S")\n\n\ndef notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:\n    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, notification_bucket_time_text(row.get("close_time"))])\n\n\ndef normalize_notification_key(key: Any) -> str:\n    text = clean_str(key)\n    parts = text.split("|")\n    if len(parts) >= 5 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT7":\n        parts[4] = notification_bucket_time_text(parts[4])\n        return "|".join(parts[:5])\n    return text\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    keys: set[str] = set()\n    for value in df["notification_key"].dropna().astype(str).tolist():\n        raw = clean_str(value)\n        if raw:\n            keys.add(raw)\n            keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef load_seen_state_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        with open(windows_long_path(path), "r", encoding="utf-8") as f:\n            obj = json.load(f)\n    except Exception:\n        return set()\n    rows = obj.get("seen", []) if isinstance(obj, dict) else []\n    keys: set[str] = set()\n    if isinstance(rows, list):\n        for row in rows:\n            key = row.get("notification_key") if isinstance(row, dict) else row\n            raw = clean_str(key)\n            if raw:\n                keys.add(raw)\n                keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef mark_seen_state_key(path: Path, key: str, row: pd.Series, spec: GoldStrictSignalSpec) -> None:\n    mkdirp(path.parent)\n    existing: list[dict[str, Any]] = []\n    if path.exists():\n        try:\n            with open(windows_long_path(path), "r", encoding="utf-8") as f:\n                obj = json.load(f)\n            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):\n                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]\n        except Exception:\n            existing = []\n    normalized = normalize_notification_key(key)\n    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}\n    by_key[normalized] = {\n        "notified_at": now_str(),\n        "notification_key": normalized,\n        "strategy_id": spec.strategy_id,\n        "direction": spec.direction,\n        "entry_time": time_text(row.get("close_time")),\n        "bucket_time": notification_bucket_time_text(row.get("close_time")),\n        "schema_version": SCHEMA_VERSION,\n    }\n    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at")))[-1000:]\n    tmp = path.with_suffix(path.suffix + ".tmp")\n    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:\n        json.dump({"schema_version": SCHEMA_VERSION, "updated_at": now_str(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n    os.replace(windows_long_path(tmp), windows_long_path(path))\n\n\ndef append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n'''
    text = replace_once(text, old_key_block, new_key_block, "stable candle key + seen-state + durable ledger")

    text = replace_once(
        text,
        '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n',
        '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n    p.add_argument("--seen-state-json", type=Path, default=DEFAULT_SEEN_STATE_JSON)\n',
        "seen-state CLI arg",
    )

    text = replace_once(
        text,
        '''    ledger_csv = resolve_path(args.ledger_csv)\n    env_file = resolve_path(args.env_file)\n''',
        '''    ledger_csv = resolve_path(args.ledger_csv)\n    seen_state_json = resolve_path(args.seen_state_json)\n    env_file = resolve_path(args.env_file)\n''',
        "resolve seen-state path",
    )

    text = replace_once(
        text,
        '''    notified_keys = load_notified_keys(ledger_csv)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n''',
        '''    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n''',
        "load seen-state keys",
    )

    text = replace_once(
        text,
        '''    print(f"ledger_csv: {ledger_csv}", flush=True)\n''',
        '''    print(f"ledger_csv: {ledger_csv}", flush=True)\n    print(f"seen_state_json: {seen_state_json}", flush=True)\n''',
        "print seen-state path",
    )

    text = replace_once(
        text,
        '''    send_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n''',
        '''    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n''',
        "error lists",
    )

    old_ledger_block = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_rows.append({\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            })\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n    append_ledger(ledger_csv, ledger_rows)\n'''
    new_ledger_block = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_row = {\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            }\n            try:\n                append_ledger_row_durable(ledger_csv, ledger_row)\n                ledger_rows.append(ledger_row)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n            try:\n                mark_seen_state_key(seen_state_json, key, row, spec)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                seen_state_errors.append(err)\n                print(f"Seen-state append error after send/mark: {err}", flush=True)\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n'''
    text = replace_once(text, old_ledger_block, new_ledger_block, "immediate ledger and seen-state marking")

    text = replace_once(
        text,
        '''        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n''',
        '''        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n''',
        "summary cycle_ok",
    )

    text = replace_once(
        text,
        '''        "ledger_csv": str(ledger_csv),\n        "ai_tag_rules_json": str(rules_path),\n''',
        '''        "ledger_csv": str(ledger_csv),\n        "seen_state_json": str(seen_state_json),\n        "ai_tag_rules_json": str(rules_path),\n''',
        "summary seen-state path",
    )

    text = replace_once(
        text,
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "dry_run": bool(args.dry_run),\n''',
        '''        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key",\n        "dry_run": bool(args.dry_run),\n''',
        "summary duplicate guard fields",
    )

    text = replace_once(
        text,
        '''            "ledger_append_requires_send_success_or_mark_dry_run": True,\n''',
        '''            "ledger_append_requires_send_success_or_mark_dry_run": True,\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_5min_candle_bucket": True,\n''',
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
