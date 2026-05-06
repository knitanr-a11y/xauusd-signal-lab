#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Send Mochipoyo notification messages to Discord safely.

Default behavior is dry-run only. Messages are sent only when --send is passed.

Safety:
- payload_key based duplicate-send prevention
- send ledger CSV
- webhook URL from --webhook-url, environment variable, or local .env
- no AI review
- no order placement

Console output is deliberately summary-only. Full Discord messages are written to
UTF-8 preview files instead of being printed to Windows cmd.exe, which avoids
cp932/emoji mojibake and crashes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

from format_mochipoyo_discord_messages import format_row, val  # type: ignore

DISCORD_LIMIT = 2000


def safe_text(text: object) -> str:
    s = str(text)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return s.encode(enc, errors="backslashreplace").decode(enc, errors="replace")


def safe_print(text: object = "") -> None:
    print(safe_text(text))


def parse_dotenv_line(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    key, value = s.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
        value = value[1:-1]
    return key, value


def load_dotenv_file(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return {}
    loaded: dict[str, str] = {}
    try:
        for line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
            parsed = parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            loaded[key] = value
            os.environ.setdefault(key, value)
    except Exception as e:
        safe_print(f"WARNING: failed to read .env file: {dotenv_path} ({e!r})")
    return loaded


def load_local_dotenv() -> dict[str, str]:
    """Load .env from current working directory, then repo root fallback.

    This is intentionally tiny and dependency-free. Explicit --webhook-url and
    already-set environment variables still take precedence over .env values.
    """
    loaded: dict[str, str] = {}
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        loaded.update(load_dotenv_file(path))
    return loaded


def make_payload_key(row: pd.Series) -> str:
    if "payload_key" in row.index and pd.notna(row.get("payload_key")) and str(row.get("payload_key")):
        return str(row.get("payload_key"))
    fields = [
        "symbol", "candidate_name", "entry_time", "pair_name", "candidate_rank", "direction", "entry_price",
        "source_filter_name",
    ]
    return "|".join(str(row.get(c, "")) for c in fields)


def load_sent_keys(send_ledger_csv: Path) -> set[str]:
    if not send_ledger_csv.exists():
        return set()
    df = pd.read_csv(send_ledger_csv, encoding="utf-8-sig")
    if "payload_key" not in df.columns:
        return set()
    return set(df["payload_key"].dropna().astype(str).tolist())


def split_message(msg: str, limit: int = DISCORD_LIMIT) -> list[str]:
    if len(msg) <= limit:
        return [msg]
    chunks: list[str] = []
    cur = ""
    for line in msg.splitlines():
        add = line if not cur else "\n" + line
        if len(cur) + len(add) <= limit:
            cur += add
        else:
            if cur:
                chunks.append(cur)
            if len(line) <= limit:
                cur = line
            else:
                for i in range(0, len(line), limit):
                    part = line[i:i + limit]
                    if len(part) == limit:
                        chunks.append(part)
                    else:
                        cur = part
    if cur:
        chunks.append(cur)
    return chunks


def post_discord(webhook_url: str, content: str, username: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"content": content}
    if username:
        payload["username"] = username
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "mochipoyo-signal-bot/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": int(resp.status), "body": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": int(e.code), "body": body}
    except Exception as e:
        return {"ok": False, "status": None, "body": repr(e)}


def append_send_ledger(rows: list[dict[str, Any]], send_ledger_csv: Path) -> None:
    if not rows:
        return
    send_ledger_csv.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if send_ledger_csv.exists():
        old = pd.read_csv(send_ledger_csv, encoding="utf-8-sig")
        all_cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
        out = pd.concat([old.reindex(columns=all_cols), new.reindex(columns=all_cols)], ignore_index=True)
    else:
        out = new
    out.to_csv(send_ledger_csv, index=False, encoding="utf-8-sig")


def load_input_rows(input_csv: Path, symbol: str | None, max_rows: int) -> pd.DataFrame:
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    if symbol and "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
        df = df.sort_values("entry_time")
    if max_rows > 0:
        df = df.tail(max_rows)
    return df.reset_index(drop=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Safely send Mochipoyo Discord notifications.")
    p.add_argument("--input-csv", required=True, help="Payload/enriched payload/ledger CSV")
    p.add_argument("--send-ledger-csv", default="data/results/mochipoyo/live_dryrun/mochipoyo_discord_send_ledger.csv")
    p.add_argument("--preview-txt", default="data/results/mochipoyo/live_dryrun/mochipoyo_discord_send_preview.txt")
    p.add_argument("--preview-json", default="data/results/mochipoyo/live_dryrun/mochipoyo_discord_send_preview.json")
    p.add_argument("--symbol", default=None, help="Optional GOLD or BTC filter")
    p.add_argument("--max-rows", type=int, default=5)
    p.add_argument("--style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--webhook-url", default=None)
    p.add_argument("--webhook-env", default="DISCORD_WEBHOOK_URL")
    p.add_argument("--username", default="Mochipoyo Signal")
    p.add_argument("--send", action="store_true", help="Actually send to Discord. Without this, dry-run only.")
    p.add_argument("--allow-duplicates", action="store_true", help="Allow sending payload_key already in send ledger.")
    p.add_argument("--sleep-seconds", type=float, default=1.0)
    args = p.parse_args()

    load_local_dotenv()

    input_csv = Path(args.input_csv)
    send_ledger_csv = Path(args.send_ledger_csv)
    preview_txt = Path(args.preview_txt)
    preview_json = Path(args.preview_json)

    df = load_input_rows(input_csv, args.symbol, args.max_rows)
    sent_keys = load_sent_keys(send_ledger_csv)

    records: list[dict[str, Any]] = []
    messages_for_txt: list[str] = []
    send_rows: list[dict[str, Any]] = []

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        payload_key = make_payload_key(row)
        duplicate = payload_key in sent_keys
        message = format_row(row, args.style)
        messages_for_txt.append(message)
        rec = {
            "index": i,
            "payload_id": val(row, "payload_id"),
            "payload_key": payload_key,
            "symbol": val(row, "symbol"),
            "direction": val(row, "direction"),
            "entry_time": val(row, "entry_time"),
            "duplicate_existing": bool(duplicate),
            "send_requested": bool(args.send),
            "sent": False,
            "send_status": "DRY_RUN" if not args.send else "PENDING",
            "discord_status_code": None,
            "discord_response": None,
            "message": message,
        }
        if args.send and (args.allow_duplicates or not duplicate):
            send_rows.append(rec)
        records.append(rec)

    preview_txt.parent.mkdir(parents=True, exist_ok=True)
    preview_txt.write_text(("\n\n" + "=" * 40 + "\n\n").join(messages_for_txt).strip() + "\n", encoding="utf-8")
    preview_json.parent.mkdir(parents=True, exist_ok=True)

    webhook_url = args.webhook_url or os.environ.get(args.webhook_env)
    sent_ledger_rows: list[dict[str, Any]] = []

    if args.send:
        if not webhook_url:
            for rec in records:
                if rec["send_status"] == "PENDING":
                    rec["send_status"] = "ERROR_NO_WEBHOOK_URL"
            preview_json.write_text(json.dumps({"source": str(input_csv), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
            safe_print("send_mochipoyo_discord_messages")
            safe_print("ERROR: --send was specified but webhook URL was not provided.")
            safe_print(f"Use --webhook-url, set environment variable {args.webhook_env}, or add it to .env.")
            safe_print(f"preview_txt: {preview_txt}")
            safe_print(f"preview_json: {preview_json}")
            return 2

        rec_by_key = {str(r["payload_key"]): r for r in records}
        for rec in send_rows:
            key = str(rec["payload_key"])
            parts = split_message(str(rec["message"]))
            for part_i, part in enumerate(parts, start=1):
                result = post_discord(webhook_url, part, username=args.username)
                if not result.get("ok"):
                    rec_by_key[key]["send_status"] = "ERROR_DISCORD_POST"
                    rec_by_key[key]["discord_status_code"] = result.get("status")
                    rec_by_key[key]["discord_response"] = result.get("body")
                    break
                if part_i < len(parts):
                    time.sleep(args.sleep_seconds)
            else:
                rec_by_key[key]["sent"] = True
                rec_by_key[key]["send_status"] = "SENT"
                rec_by_key[key]["discord_status_code"] = 204
                rec_by_key[key]["discord_response"] = ""
                sent_ledger_rows.append({
                    "sent_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z"),
                    "payload_id": rec.get("payload_id"),
                    "payload_key": key,
                    "symbol": rec.get("symbol"),
                    "direction": rec.get("direction"),
                    "entry_time": rec.get("entry_time"),
                    "message": rec.get("message"),
                })
            time.sleep(args.sleep_seconds)

        append_send_ledger(sent_ledger_rows, send_ledger_csv)
        records = list(rec_by_key.values())
    else:
        for rec in records:
            if rec["duplicate_existing"] and not args.allow_duplicates:
                rec["send_status"] = "DRY_RUN_DUPLICATE_WOULD_SKIP"
            else:
                rec["send_status"] = "DRY_RUN_WOULD_SEND"

    preview_json.write_text(json.dumps({"source": str(input_csv), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(records)
    duplicates = sum(1 for r in records if r["duplicate_existing"])
    sent = sum(1 for r in records if r["sent"])
    would_send = sum(1 for r in records if r["send_status"] == "DRY_RUN_WOULD_SEND")
    errors = sum(1 for r in records if str(r["send_status"]).startswith("ERROR"))

    safe_print("send_mochipoyo_discord_messages")
    safe_print(f"source: {input_csv}")
    safe_print(f"rows: {total}")
    safe_print(f"send: {args.send}")
    safe_print(f"duplicates_existing: {duplicates}")
    safe_print(f"dry_run_would_send: {would_send}")
    safe_print(f"sent: {sent}")
    safe_print(f"errors: {errors}")
    safe_print(f"send_ledger_csv: {send_ledger_csv}")
    safe_print(f"preview_txt: {preview_txt}")
    safe_print(f"preview_json: {preview_json}")
    safe_print("preview_last: omitted from console; open preview_txt for the full UTF-8 message.")
    safe_print("done")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
