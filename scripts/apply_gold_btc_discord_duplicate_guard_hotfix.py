#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Emergency hotfix: suppress repeated GOLD/BTC Discord notifications.

Run from repository root:
  python scripts\apply_gold_btc_discord_duplicate_guard_hotfix.py

Then restart these BATs:
  scripts\gold_strict_7_signals\run_gold_strict_7_discord_notify_forever_aligned.bat
  scripts\run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat

This version is robust to partial previous patches.  It replaces function ranges
instead of requiring one huge exact old-text match.
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


def replace_literal(text: str, old: str, new: str, label: str, *, required: bool = True) -> str:
    if old in text:
        print(f"[PATCH] {label}")
        return text.replace(old, new, 1)
    if new in text:
        print(f"[SKIP] {label}: already patched")
        return text
    if required:
        raise SystemExit(f"[ERROR] pattern not found for {label}")
    print(f"[SKIP] {label}: old pattern not found")
    return text


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        if replacement.strip() in text:
            print(f"[SKIP] {label}: already patched")
            return text
        raise SystemExit(f"[ERROR] start marker not found for {label}: {start_marker!r}")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"[ERROR] end marker not found for {label}: {end_marker!r}")
    print(f"[PATCH] {label}")
    return text[:start] + replacement + text[end:]


def ensure_after(text: str, anchor: str, insert: str, label: str) -> str:
    if insert.strip() in text:
        print(f"[SKIP] {label}: already present")
        return text
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit(f"[ERROR] anchor not found for {label}: {anchor!r}")
    pos = idx + len(anchor)
    print(f"[PATCH] {label}")
    return text[:pos] + insert + text[pos:]


def replace_or_insert_seen_arg(text: str, label_prefix: str, arg_line: str) -> str:
    if "--seen-state-json" in text:
        print(f"[SKIP] {label_prefix} seen-state arg: already present")
        return text
    return replace_literal(text, arg_line, arg_line + '    p.add_argument("--seen-state-json", type=Path, default=DEFAULT_SEEN_STATE_JSON)\n', f"{label_prefix} seen-state arg")


def patch_gold() -> None:
    path = GOLD
    text = read(path)

    # Schema/default can already be partially patched from a failed prior run.
    if 'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v8_wall_clock_guard_send_error_summary"' in text:
        text = replace_literal(
            text,
            'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v8_wall_clock_guard_send_error_summary"\n',
            'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard"\n',
            "GOLD schema version",
        )
    elif 'SCHEMA_VERSION = "gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard"' in text:
        print("[SKIP] GOLD schema version: already v9")
    else:
        raise SystemExit("[ERROR] GOLD schema version not recognized")
    text = ensure_after(
        text,
        'DEFAULT_AI_TAG_RULES_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json")\n',
        'DEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/gold/strict_7/discord_notification_seen_keys.json")\n',
        "GOLD seen-state default",
    )

    gold_dup_block = '''def notification_bucket_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return time_text(value)
    return pd.Timestamp(ts).floor("5min").strftime("%Y-%m-%d %H:%M:%S")


def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, notification_bucket_time_text(row.get("close_time"))])


def normalize_notification_key(key: Any) -> str:
    text = clean_str(key)
    parts = text.split("|")
    if len(parts) >= 5 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT7":
        parts[4] = notification_bucket_time_text(parts[4])
        return "|".join(parts[:5])
    return text


def load_notified_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except Exception:
        return set()
    if "notification_key" not in df.columns:
        return set()
    keys: set[str] = set()
    for value in df["notification_key"].dropna().astype(str).tolist():
        raw = clean_str(value)
        if raw:
            keys.add(raw)
            keys.add(normalize_notification_key(raw))
    return keys


def load_seen_state_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return set()
    rows = obj.get("seen", []) if isinstance(obj, dict) else []
    keys: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            key = row.get("notification_key") if isinstance(row, dict) else row
            raw = clean_str(key)
            if raw:
                keys.add(raw)
                keys.add(normalize_notification_key(raw))
    return keys


def mark_seen_state_key(path: Path, key: str, row: pd.Series, spec: GoldStrictSignalSpec) -> None:
    mkdirp(path.parent)
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            with open(windows_long_path(path), "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):
                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]
        except Exception:
            existing = []
    normalized = normalize_notification_key(key)
    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}
    by_key[normalized] = {
        "notified_at": now_str(),
        "notification_key": normalized,
        "strategy_id": spec.strategy_id,
        "direction": spec.direction,
        "entry_time": time_text(row.get("close_time")),
        "bucket_time": notification_bucket_time_text(row.get("close_time")),
        "schema_version": SCHEMA_VERSION,
    }
    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at")))[-1000:]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "updated_at": now_str(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(windows_long_path(tmp), windows_long_path(path))


def append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass


def append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        append_ledger_row_durable(path, row)


'''
    text = replace_between(text, "def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:", "def calc_prices(row: pd.Series, spec: GoldStrictSignalSpec)", gold_dup_block, "GOLD duplicate helper function range")

    text = replace_or_insert_seen_arg(text, "GOLD", '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n')
    text = replace_literal(text, '    ledger_csv = resolve_path(args.ledger_csv)\n    env_file = resolve_path(args.env_file)\n', '    ledger_csv = resolve_path(args.ledger_csv)\n    seen_state_json = resolve_path(args.seen_state_json)\n    env_file = resolve_path(args.env_file)\n', "GOLD resolve seen-state", required=False)
    if "seen_state_json = resolve_path(args.seen_state_json)" not in text:
        raise SystemExit("[ERROR] GOLD failed to insert seen_state_json resolver")
    text = replace_literal(text, '    notified_keys = load_notified_keys(ledger_csv)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n', '    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    signals, freshness_guard = collect_signals(ctx, specs, args)\n', "GOLD load both duplicate states", required=False)
    text = replace_literal(text, '    print(f"ledger_csv: {ledger_csv}", flush=True)\n', '    print(f"ledger_csv: {ledger_csv}", flush=True)\n    print(f"seen_state_json: {seen_state_json}", flush=True)\n', "GOLD print seen-state", required=False)
    text = replace_literal(text, '    send_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n', '    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    skipped_duplicates = 0\n', "GOLD error lists", required=False)

    old_mark_start = '        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:\n'
    old_mark_end = '    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"\n'
    new_mark = '''        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:
            ledger_row = {
                "notified_at": now_str(),
                "schema_version": SCHEMA_VERSION,
                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},
            }
            try:
                append_ledger_row_durable(ledger_csv, ledger_row)
                ledger_rows.append(ledger_row)
                notified_keys.add(key)
                notified_keys.add(normalize_notification_key(key))
            except Exception as exc:
                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}
                ledger_errors.append(err)
                print(f"Ledger append error after send/mark: {err}", flush=True)
            try:
                mark_seen_state_key(seen_state_json, key, row, spec)
                notified_keys.add(key)
                notified_keys.add(normalize_notification_key(key))
            except Exception as exc:
                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}
                seen_state_errors.append(err)
                print(f"Seen-state append error after send/mark: {err}", flush=True)

'''
    text = replace_between(text, old_mark_start, old_mark_end, new_mark, "GOLD immediate duplicate-state mark")
    text = text.replace('    append_ledger(ledger_csv, ledger_rows)\n', '')

    text = replace_literal(text, '        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n', '        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n', "GOLD summary cycle_ok", required=False)
    text = replace_literal(text, '        "ledger_csv": str(ledger_csv),\n        "ai_tag_rules_json": str(rules_path),\n', '        "ledger_csv": str(ledger_csv),\n        "seen_state_json": str(seen_state_json),\n        "ai_tag_rules_json": str(rules_path),\n', "GOLD summary seen-state", required=False)
    text = replace_literal(text, '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "dry_run": bool(args.dry_run),\n', '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key",\n        "dry_run": bool(args.dry_run),\n', "GOLD summary duplicate fields", required=False)
    text = replace_literal(text, '            "ledger_append_requires_send_success_or_mark_dry_run": True,\n', '            "ledger_append_requires_send_success_or_mark_dry_run": True,\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_5min_candle_bucket": True,\n', "GOLD safety flags", required=False)
    text = replace_literal(text, '    return 0 if len(send_errors) == 0 else 1\n', '    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else 1\n', "GOLD return code", required=False)

    write(path, text)
    verify(path, [
        'v9_candle_bucket_duplicate_guard', 'DEFAULT_SEEN_STATE_JSON', '--seen-state-json',
        'load_seen_state_keys(seen_state_json)', 'notification_key_uses_5min_candle_bucket',
        'duplicate_guard_mode', 'append_ledger_row_durable', 'mark_seen_state_key(seen_state_json',
    ], "GOLD")


def patch_btc() -> None:
    path = BTC
    text = read(path)

    if 'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v4_wall_clock_guard_send_error_summary"' in text:
        text = replace_literal(
            text,
            'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v4_wall_clock_guard_send_error_summary"\n',
            'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard"\n',
            "BTC schema version",
        )
    elif 'SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard"' in text:
        print("[SKIP] BTC schema version: already v5")
    else:
        raise SystemExit("[ERROR] BTC schema version not recognized")
    text = ensure_after(
        text,
        'DEFAULT_LEDGER_CSV = Path("data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_ledger.csv")\n',
        'DEFAULT_SEEN_STATE_JSON = Path("data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_seen_keys.json")\n',
        "BTC seen-state default",
    )

    btc_dup_block = '''def notification_bucket_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean_str(value)
    return pd.Timestamp(ts).floor("15min").strftime("%Y-%m-%d %H:%M:%S")


def normalize_notification_key(key: Any) -> str:
    text = clean_str(key)
    parts = text.split("|")
    if len(parts) >= 7 and parts[0] == DEFAULT_SYMBOL and parts[1] == "STRICT5":
        parts[6] = notification_bucket_time_text(parts[6])
        return "|".join(parts[:7])
    return text


def load_notified_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except Exception:
        return set()
    if "notification_key" not in df.columns:
        return set()
    keys: set[str] = set()
    for value in df["notification_key"].dropna().astype(str).tolist():
        raw = clean_str(value)
        if raw:
            keys.add(raw)
            keys.add(normalize_notification_key(raw))
    return keys


def load_seen_state_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return set()
    rows = obj.get("seen", []) if isinstance(obj, dict) else []
    keys: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            key = row.get("notification_key") if isinstance(row, dict) else row
            raw = clean_str(key)
            if raw:
                keys.add(raw)
                keys.add(normalize_notification_key(raw))
    return keys


def mark_seen_state_key(path: Path, key: str, row: pd.Series, filter_variant: str) -> None:
    mkdirp(path.parent)
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            with open(windows_long_path(path), "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict) and isinstance(obj.get("seen"), list):
                existing = [x for x in obj.get("seen", []) if isinstance(x, dict)]
        except Exception:
            existing = []
    normalized = normalize_notification_key(key)
    by_key = {normalize_notification_key(x.get("notification_key")): x for x in existing if clean_str(x.get("notification_key"))}
    by_key[normalized] = {
        "notified_at_utc": utc_now_text(),
        "notification_key": normalized,
        "filter_variant": filter_variant,
        "strategy_id": clean_str(row.get("strategy_id")),
        "direction": clean_str(row.get("direction")),
        "signal_time": clean_str(row.get("signal_time")),
        "bucket_time": notification_bucket_time_text(row.get("signal_time")),
        "schema_version": SCHEMA_VERSION,
    }
    rows = sorted(by_key.values(), key=lambda x: clean_str(x.get("notified_at_utc")))[-1000:]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(windows_long_path(tmp), "w", encoding="utf-8", newline="") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "updated_at_utc": utc_now_text(), "seen": rows}, f, ensure_ascii=False, indent=2, default=str)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(windows_long_path(tmp), windows_long_path(path))


def append_ledger_row_durable(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass


def append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        append_ledger_row_durable(path, row)


def notification_key(row: pd.Series, filter_variant: str) -> str:
    return "|".join([
        DEFAULT_SYMBOL,
        "STRICT5",
        "OFFICIAL_NUMERIC_AI_TAGS",
        filter_variant,
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        notification_bucket_time_text(row.get("signal_time")),
    ])


'''
    text = replace_between(text, "def load_notified_keys(path: Path) -> set[str]:", "def id_time_text(value: Any) -> str:", btc_dup_block, "BTC duplicate helper function range")
    text = replace_or_insert_seen_arg(text, "BTC", '    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)\n')
    text = replace_literal(text, '    ledger_csv = resolve_repo_path(args.ledger_csv)\n    env_file = resolve_repo_path(args.env_file)\n', '    ledger_csv = resolve_repo_path(args.ledger_csv)\n    seen_state_json = resolve_repo_path(args.seen_state_json)\n    env_file = resolve_repo_path(args.env_file)\n', "BTC resolve seen-state", required=False)
    if "seen_state_json = resolve_repo_path(args.seen_state_json)" not in text:
        raise SystemExit("[ERROR] BTC failed to insert seen_state_json resolver")
    text = replace_literal(text, '    notified_keys = load_notified_keys(ledger_csv)\n    ledger_rows: list[dict[str, Any]] = []\n', '    notified_keys = load_notified_keys(ledger_csv) | load_seen_state_keys(seen_state_json)\n    ledger_rows: list[dict[str, Any]] = []\n', "BTC load both duplicate states", required=False)
    text = replace_literal(text, '    send_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n', '    send_errors: list[dict[str, Any]] = []\n    ledger_errors: list[dict[str, Any]] = []\n    seen_state_errors: list[dict[str, Any]] = []\n    for _, row in preview.iterrows():\n', "BTC error lists", required=False)

    old_mark_start = '        if (args.send_discord and discord_sent) or args.mark_preview_notified:\n'
    old_mark_end = '    summary = {\n'
    new_mark = '''        if (args.send_discord and discord_sent) or args.mark_preview_notified:
            lr = ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path, ai_score=ai_score)
            try:
                append_ledger_row_durable(ledger_csv, lr)
                ledger_rows.append(lr)
                notified_keys.add(key)
                notified_keys.add(normalize_notification_key(key))
            except Exception as exc:
                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}
                ledger_errors.append(err)
                print(f"Ledger append error after send/mark: {err}", flush=True)
            try:
                mark_seen_state_key(seen_state_json, key, row, args.filter_variant)
                notified_keys.add(key)
                notified_keys.add(normalize_notification_key(key))
            except Exception as exc:
                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}
                seen_state_errors.append(err)
                print(f"Seen-state append error after send/mark: {err}", flush=True)
'''
    text = replace_between(text, old_mark_start, old_mark_end, new_mark, "BTC immediate duplicate-state mark")
    text = text.replace('    append_ledger(ledger_csv, ledger_rows)\n', '')
    if '    summary = {\n' not in text:
        text = text.replace(new_mark, new_mark + '    summary = {\n')

    text = replace_literal(text, '        "cycle_ok": bool(len(send_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",\n', '        "cycle_ok": bool(len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0),\n        "reason": "OK" if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else "SEND_OR_DUPLICATE_STATE_ERROR_SUMMARY_WRITTEN",\n', "BTC summary cycle_ok", required=False)
    text = replace_literal(text, '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "openai_called": False,\n', '        "discord_send_error_rows": int(len(send_errors)),\n        "discord_send_errors": send_errors,\n        "ledger_append_error_rows": int(len(ledger_errors)),\n        "ledger_append_errors": ledger_errors,\n        "seen_state_error_rows": int(len(seen_state_errors)),\n        "seen_state_errors": seen_state_errors,\n        "duplicate_guard_mode": "ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key",\n        "openai_called": False,\n', "BTC summary duplicate fields", required=False)
    text = replace_literal(text, '        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv)},\n', '        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv), "seen_state_json": str(seen_state_json)},\n', "BTC summary output seen-state", required=False)
    text = replace_literal(text, '            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n', '            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),\n            "seen_state_duplicate_guard_enabled": True,\n            "notification_key_uses_15min_candle_bucket": True,\n', "BTC safety flags", required=False)
    text = replace_literal(text, '    return 0 if len(send_errors) == 0 else 1\n', '    return 0 if len(send_errors) == 0 and len(ledger_errors) == 0 and len(seen_state_errors) == 0 else 1\n', "BTC return code", required=False)

    write(path, text)
    verify(path, [
        'v5_m15_bucket_duplicate_guard', 'DEFAULT_SEEN_STATE_JSON', '--seen-state-json',
        'load_seen_state_keys(seen_state_json)', 'notification_key_uses_15min_candle_bucket',
        'duplicate_guard_mode', 'append_ledger_row_durable', 'mark_seen_state_key(seen_state_json',
    ], "BTC")


def verify(path: Path, required: list[str], label: str) -> None:
    text = read(path)
    missing = [x for x in required if x not in text]
    if missing:
        raise SystemExit(f"[ERROR] {label} verification failed missing: {missing}")
    print(f"[OK] {label} patched and verified: {path}")


def main() -> int:
    patch_gold()
    patch_btc()
    print("[DONE] GOLD/BTC Discord duplicate guard hotfix applied. Restart Discord notification BATs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
