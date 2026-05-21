#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emergency hotfix: suppress repeated GOLD/BTC Discord notifications.

Run from repository root:
  python scripts\apply_gold_btc_discord_duplicate_guard_hotfix.py

Then restart these BATs:
  scripts\gold_strict_7_signals\run_gold_strict_7_discord_notify_forever_aligned.bat
  scripts\run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat

What this patches:
- GOLD strict-7 Discord notifier:
  * notification_key uses stable M5 candle bucket time
  * duplicate state is read from both CSV ledger and JSON seen-state
  * successful sends are marked immediately in both CSV ledger and seen-state JSON

- BTC strict-5 official Discord notifier:
  * notification_key uses stable M15 candle bucket time
  * duplicate state is read from both CSV ledger and JSON seen-state
  * successful sends are marked immediately in both CSV ledger and seen-state JSON

Safety:
- No signal conditions changed.
- No TP/SL changed.
- No MT5 order_send code touched.
- No Discord webhook changed.
"""
from __future__ import annotations

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
    print(f"[PATCH] {label}")
    return text.replace(old, new, 1)


def patch_gold() -> None:
    path = GOLD
    text = read(path)
    original = text

    text = replace_once(
        text,
        'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v8_wall_clock_guard_send_error_summary"\n',
        'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard"\nDEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/gold/strict_7/discord_notification_seen_keys.json")\n',
        "GOLD schema + seen-state default",
    )

    old_block = '''def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:\n    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    return set(df["notification_key"].dropna().astype(str).tolist())\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n'''
    new_block = '''def notification_bucket_time_text(value: Any) -> str:\n    ts = pd.to_datetime(value, errors="coerce")\n    if pd.isna(ts):\n        return time_text(value)\n    return pd.Timestamp(ts).floor("5min").strftime("%Y-%m-%d %H:%M:%S")\n\n\ndef notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:\n    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, notification_bucket_time_text(row.get("close_time"))])\n\n\ndef normalize_notification_key(key: Any) -> str:\n    text = clean_str(key)\n    parts = text.split("|")\n    if len(parts) >= 5 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT7":\n        parts[4] = notification_bucket_time_text(parts[4])\n        return "|".join(parts[:5])\n    return text\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    keys: set[str] = set()\n    for value in df["notification_key"].dropna().astype(str).tolist():\n        raw = clean_str(value)\n        if raw:\n            keys.add(raw)\n            keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef load_seen_state_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        with open(windows_long_path(path), "r", encoding="utf-8") as f:\n            obj = json.load(f)\n    except Exception:\n        return set()\n    rows = obj.get("seen", []) if isinstance(obj, dict) else []\n    keys: set[str] = set()\n    if isinstance(rows, list):\n        for row in rows:\n            key = row.get("notification_key") if isinstance(row, dict) else row\n            raw = clean_str(key)\n            if raw:\n                keys.add(raw)\n                keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef mark_seen_state_key(path: Path, key: str, row: pd.Series, spec: GoldStrictSignalSpec) -> None:\n    mkdirp(path.parent)\n    existing: list[dict[str, Any]] = []\n    if path.exists():\n        try:\n            with open(windows_long_path(path), "r", encoding="utf-8") as f:\n                obj = json.load(f)\n            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):\n                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]\n        except Exception:\n            existing = []\n    normalized = normalize_notification_key(key)\n    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}\n    by_key[normalized] = {\n        "notified_at": now_str(),\n        "notification_key": normalized,\n        "strategy_id": spec.strategy_id,\n        "direction": spec.direction,\n        "entry_time": time_text(row.get("close_time")),\n        "bucket_time": notification_bucket_time_text(row.get("close_time")),\n        "schema_version": SCHEMA_VERSION,\n    }\n    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at")))[-1000:]\n    tmp = path.with_suffix(path.suffix + ".tmp")\n    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:\n        json.dump({"schema_version": SCHEMA_VERSION, "updated_at": now_str(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n    os.replace(windows_long_path(tmp), windows_long_path(path))\n\n\ndef append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n'''
    text = replace_once(text, old_block, new_block, "GOLD key/ledger/seen-state block")

    text = replace_once(text, '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n', '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n    p.add_argument("--seen-state-json", type=Path, default=DEFAULT_SEEN_STATE_JSON)\n', "GOLD seen-state arg")
    text = replace_once(text, '    ledger_csv = resolve_path(args.ledger_csv)\n    env_file = resolve_path(args.env_file)\n', '    ledger_csv = resolve_path(args.ledger_csv)\n    seen_state_json = resolve_path(args.seen_state_json)\n    env_file = resolve_path(args.env_file)\n', "GOLD resolve seen-state")
    text = replace_once(text, '    notified_keys = load_notified_keys(ledger_csv)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n', '    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n', "GOLD load both duplicate states")
    text = replace_once(text, '    print(f"ledger_csv: {ledger_csv}", flush=True)\n', '    print(f"ledger_csv: {ledger_csv}", flush=True)\n    print(f"seen_state_json: {seen_state_json}", flush=True)\n', "GOLD print seen-state")
    text = replace_once(text, '    send_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n', '    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n', "GOLD error lists")

    old_mark = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_rows.append({\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            })\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n    append_ledger(ledger_csv, ledger_rows)\n'''
    new_mark = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n            ledger_row = {\n                "notified_at": now_str(),\n                "schema_version": SCHEMA_VERSION,\n                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},\n            }\n            try:\n                append_ledger_row_durable(ledger_csv, ledger_row)\n                ledger_rows.append(ledger_row)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n            try:\n                mark_seen_state_key(seen_state_json, key, row, spec)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                seen_state_errors.append(err)\n                print(f"Seen-state append error after send/mark: {err}", flush=True)\n\n    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"\n    write_preview_csv(preview_csv, preview_rows)\n'''
    text = replace_once(text, old_mark, new_mark, "GOLD immediate duplicate-state mark")

    text = replace_once(text, '        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n', '        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n', "GOLD summary cycle_ok")
    text = replace_once(text, '        "ledger_csv": str(ledger_csv),\n        "ai_tag_rules_json": str(rules_path),\n', '        "ledger_csv": str(ledger_csv),\n        "seen_state_json": str(seen_state_json),\n        "ai_tag_rules_json": str(rules_path),\n', "GOLD summary seen-state")
    text = replace_once(text, '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "dry_run": bool(args.dry_run),\n', '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key",\n        "dry_run": bool(args.dry_run),\n', "GOLD summary duplicate fields")
    text = replace_once(text, '            "ledger_append_requires_send_success_or_mark_dry_run": True,\n', '            "ledger_append_requires_send_success_or_mark_dry_run": True,\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_5min_candle_bucket": True,\n', "GOLD safety flags")
    text = replace_once(text, '    return 0 if len(send_errors) == 0 else 1\n', '    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else 1\n', "GOLD return code")

    if text != original:
        write(path, text)
    patched = read(path)
    required = [
        'v9_candle_bucket_duplicate_guard',
        'DEFAULT_SEEN_STATE_JSON',
        'notification_key_uses_5min_candle_bucket',
        'duplicate_guard_mode',
        'append_ledger_row_durable',
    ]
    missing = [x for x in required if x not in patched]
    if missing:
        raise SystemExit(f"[ERROR] GOLD verification failed missing: {missing}")
    print(f"[OK] GOLD patched and verified: {path}")


def patch_btc() -> None:
    path = BTC
    text = read(path)
    original = text

    text = replace_once(
        text,
        'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v4_wall_clock_guard_send_error_summary"\n',
        'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard"\nDEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_seen_keys.json")\n',
        "BTC schema + seen-state default",
    )

    old_block = '''def load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    return set(df["notification_key"].dropna().astype(str).tolist())\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    if not rows:\n        return\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        for row in rows:\n            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n\n\ndef notification_key(row: pd.Series, filter_variant: str) -> str:\n    return "|".join([\n        DEFAULT_SYMBOL,\n        "STRICT5",\n        "OFFICIAL_NUMERIC_AI_TAGS",\n        filter_variant,\n        clean_str(row.get("strategy_id")),\n        clean_str(row.get("direction")),\n        clean_str(row.get("signal_time")),\n    ])\n'''
    new_block = '''def notification_bucket_time_text(value: Any) -> str:\n    ts = pd.to_datetime(value, errors="coerce")\n    if pd.isna(ts):\n        return clean_str(value)\n    return pd.Timestamp(ts).floor("15min").strftime("%Y-%m-%d %H:%M:%S")\n\n\ndef normalize_notification_key(key: Any) -> str:\n    text = clean_str(key)\n    parts = text.split("|")\n    if len(parts) >= 7 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT5":\n        parts[6] = notification_bucket_time_text(parts[6])\n        return "|".join(parts[:7])\n    return text\n\n\ndef load_notified_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")\n    except Exception:\n        return set()\n    if "notification_key" not in df.columns:\n        return set()\n    keys: set[str] = set()\n    for value in df["notification_key"].dropna().astype(str).tolist():\n        raw = clean_str(value)\n        if raw:\n            keys.add(raw)\n            keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef load_seen_state_keys(path: Path) -> set[str]:\n    if not path.exists():\n        return set()\n    try:\n        with open(windows_long_path(path), "r", encoding="utf-8") as f:\n            obj = json.load(f)\n    except Exception:\n        return set()\n    rows = obj.get("seen", []) if isinstance(obj, dict) else []\n    keys: set[str] = set()\n    if isinstance(rows, list):\n        for row in rows:\n            key = row.get("notification_key") if isinstance(row, dict) else row\n            raw = clean_str(key)\n            if raw:\n                keys.add(raw)\n                keys.add(normalize_notification_key(raw))\n    return keys\n\n\ndef mark_seen_state_key(path: Path, key: str, row: pd.Series, filter_variant: str) -> None:\n    mkdirp(path.parent)\n    existing: list[dict[str, Any]] = []\n    if path.exists():\n        try:\n            with open(windows_long_path(path), "r", encoding="utf-8") as f:\n                obj = json.load(f)\n            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):\n                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]\n        except Exception:\n            existing = []\n    normalized = normalize_notification_key(key)\n    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}\n    by_key[normalized] = {\n        "notified_at_utc": utc_now_text(),\n        "notification_key": normalized,\n        "filter_variant": filter_variant,\n        "strategy_id": clean_str(row.get("strategy_id")),\n        "direction": clean_str(row.get("direction")),\n        "signal_time": clean_str(row.get("signal_time")),\n        "bucket_time": notification_bucket_time_text(row.get("signal_time")),\n        "schema_version": SCHEMA_VERSION,\n    }\n    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at_utc")))[-1000:]\n    tmp = path.with_suffix(path.suffix + ".tmp")\n    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:\n        json.dump({"schema_version": SCHEMA_VERSION, "updated_at_utc": utc_now_text(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n    os.replace(windows_long_path(tmp), windows_long_path(path))\n\n\ndef append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:\n    mkdirp(path.parent)\n    exists = path.exists()\n    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:\n        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)\n        if not exists:\n            writer.writeheader()\n        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})\n        f.flush()\n        try:\n            os.fsync(f.fileno())\n        except Exception:\n            pass\n\n\ndef append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:\n    for row in rows:\n        append_ledger_row_durable(path, row)\n\n\ndef notification_key(row: pd.Series, filter_variant: str) -> str:\n    return "|".join([\n        DEFAULT_SYMBOL,\n        "STRICT5",\n        "OFFICIAL_NUMERIC_AI_TAGS",\n        filter_variant,\n        clean_str(row.get("strategy_id")),\n        clean_str(row.get("direction")),\n        notification_bucket_time_text(row.get("signal_time")),\n    ])\n'''
    text = replace_once(text, old_block, new_block, "BTC key/ledger/seen-state block")

    text = replace_once(text, '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n', '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n    p.add_argument("--seen-state-json", type=Path, default=DEFAULT_SEEN_STATE_JSON)\n', "BTC seen-state arg")
    text = replace_once(text, '    ledger_csv = resolve_repo_path(args.ledger_csv)\n    env_file = resolve_repo_path(args.env_file)\n', '    ledger_csv = resolve_repo_path(args.ledger_csv)\n    seen_state_json = resolve_repo_path(args.seen_state_json)\n    env_file = resolve_repo_path(args.env_file)\n', "BTC resolve seen-state")
    text = replace_once(text, '    notified_keys = load_notified_keys(ledger_csv)\n    ledger_rows: list[dict[str, Any]] = []\n', '    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    ledger_rows: list[dict[str, Any]] = []\n', "BTC load both duplicate states")
    text = replace_once(text, '    send_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n', '    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n', "BTC error lists")

    old_mark = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            ledger_rows.append(ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score))\n    append_ledger(ledger_csv, ledger_rows)\n'''
    new_mark = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n            lr = ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score)\n            try:\n                append_ledger_row_durable(ledger_csv, lr)\n                ledger_rows.append(lr)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                ledger_errors.append(err)\n                print(f"Ledger append error after send/mark: {err}", flush=True)\n            try:\n                mark_seen_state_key(seen_state_json, key, row, args.filter_variant)\n                notified_keys.add(key)\n                notified_keys.add(normalize_notification_key(key))\n            except Exception as exc:\n                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}\n                seen_state_errors.append(err)\n                print(f"Seen-state append error after send/mark: {err}", flush=True)\n'''
    text = replace_once(text, old_mark, new_mark, "BTC immediate duplicate-state mark")

    text = replace_once(text, '        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n', '        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n', "BTC summary cycle_ok")
    text = replace_once(text, '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "openai_called": False,\n', '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key",\n        "openai_called": False,\n', "BTC summary duplicate fields")
    text = replace_once(text, '        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv)},\n', '        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv), "seen_state_json": str(seen_state_json)},\n', "BTC summary output seen-state")
    text = replace_once(text, '            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n', '            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_15min_candle_bucket": True,\n', "BTC safety flags")
    text = replace_once(text, '    return 0 if len(send_errors) == 0 else 1\n', '    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else 1\n', "BTC return code")

    if text != original:
        write(path, text)
    patched = read(path)
    required = [
        'v5_m15_bucket_duplicate_guard',
        'DEFAULT_SEEN_STATE_JSON',
        'notification_key_uses_15min_candle_bucket',
        'duplicate_guard_mode',
        'append_ledger_row_durable',
    ]
    missing = [x for x in required if x not in patched]
    if missing:
        raise SystemExit(f"[ERROR] BTC verification failed missing: {missing}")
    print(f"[OK] BTC patched and verified: {path}")


def main() -> int:
    patch_gold()
    patch_btc()
    print("[DONE] GOLD/BTC Discord duplicate guard hotfix applied. Restart Discord notification BATs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
