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
- transient Discord/webhook failures are retried before returning ERROR

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
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


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


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding=encoding, newline="") as f:
        f.write(text)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


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
    df = read_csv(send_ledger_csv)
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
            return {"ok": True, "status": int(resp.status), "body": body, "exception_type": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        retry_after = None
        try:
            retry_after = e.headers.get("Retry-After")
        except Exception:
            retry_after = None
        return {"ok": False, "status": int(e.code), "body": body, "retry_after": retry_after, "exception_type": "HTTPError"}
    except Exception as e:
        return {"ok": False, "status": None, "body": repr(e), "retry_after": None, "exception_type": type(e).__name__}


def is_transient_discord_error(result: dict[str, Any]) -> bool:
    if result.get("ok"):
        return False
    status = result.get("status")
    if status is None:
        return True
    try:
        return int(status) in TRANSIENT_STATUS_CODES
    except Exception:
        return True


def retry_sleep_seconds(base_sleep: float, attempt_index: int, result: dict[str, Any]) -> float:
    retry_after = result.get("retry_after")
    if retry_after not in (None, ""):
        try:
            return max(0.0, float(retry_after))
        except Exception:
            pass
    # attempt_index is 1-based. Keep this small enough for live use, but avoid
    # hammering Discord during 503/504/429 windows.
    return max(0.0, float(base_sleep)) * float(attempt_index)


def post_discord_with_retries(
    webhook_url: str,
    content: str,
    username: str | None,
    *,
    retry_count: int,
    retry_sleep_sec: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    total_attempts = max(1, int(retry_count) + 1)
    final_result: dict[str, Any] = {"ok": False, "status": None, "body": "not attempted"}

    for attempt in range(1, total_attempts + 1):
        result = post_discord(webhook_url, content, username=username)
        final_result = result
        attempts.append(
            {
                "attempt": attempt,
                "ok": bool(result.get("ok")),
                "status": result.get("status"),
                "body": result.get("body"),
                "exception_type": result.get("exception_type"),
                "transient": is_transient_discord_error(result),
            }
        )
        if result.get("ok"):
            break
        if attempt >= total_attempts:
            break
        if not is_transient_discord_error(result):
            break
        time.sleep(retry_sleep_seconds(retry_sleep_sec, attempt, result))

    final_result = dict(final_result)
    final_result["attempt_count"] = len(attempts)
    return final_result, attempts


def append_send_ledger(rows: list[dict[str, Any]], send_ledger_csv: Path) -> None:
    if not rows:
        return
    send_ledger_csv.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if send_ledger_csv.exists():
        old = read_csv(send_ledger_csv)
        all_cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
        out = pd.concat([old.reindex(columns=all_cols), new.reindex(columns=all_cols)], ignore_index=True)
    else:
        out = new
    write_csv(out, send_ledger_csv)


def load_input_rows(input_csv: Path, symbol: str | None, max_rows: int) -> pd.DataFrame:
    df = read_csv(input_csv)
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
    p.add_argument("--discord-retry-count", type=int, default=3, help="Retry transient Discord failures this many times after the first attempt.")
    p.add_argument("--discord-retry-sleep-seconds", type=float, default=2.0, help="Base sleep seconds for transient Discord retries.")
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
            "discord_attempt_count": 0,
            "discord_attempts": [],
            "message": message,
        }
        if args.send and (args.allow_duplicates or not duplicate):
            send_rows.append(rec)
        records.append(rec)

    write_text(preview_txt, ("\n\n" + "=" * 40 + "\n\n").join(messages_for_txt).strip() + "\n")

    webhook_url = args.webhook_url or os.environ.get(args.webhook_env)
    sent_ledger_rows: list[dict[str, Any]] = []

    if args.send:
        if not webhook_url:
            for rec in records:
                if rec["send_status"] == "PENDING":
                    rec["send_status"] = "ERROR_NO_WEBHOOK_URL"
            write_text(preview_json, json.dumps({"source": str(input_csv), "records": records}, ensure_ascii=False, indent=2))
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
            all_attempts: list[dict[str, Any]] = []
            final_error_result: dict[str, Any] | None = None
            for part_i, part in enumerate(parts, start=1):
                result, attempts = post_discord_with_retries(
                    webhook_url,
                    part,
                    username=args.username,
                    retry_count=int(args.discord_retry_count),
                    retry_sleep_sec=float(args.discord_retry_sleep_seconds),
                )
                for attempt in attempts:
                    all_attempts.append({"part": part_i, **attempt})
                if not result.get("ok"):
                    final_error_result = result
                    rec_by_key[key]["send_status"] = "ERROR_DISCORD_POST"
                    rec_by_key[key]["discord_status_code"] = result.get("status")
                    rec_by_key[key]["discord_response"] = result.get("body")
                    rec_by_key[key]["discord_attempt_count"] = len(all_attempts)
                    rec_by_key[key]["discord_attempts"] = all_attempts
                    break
                if part_i < len(parts):
                    time.sleep(args.sleep_seconds)
            else:
                rec_by_key[key]["sent"] = True
                rec_by_key[key]["send_status"] = "SENT"
                rec_by_key[key]["discord_status_code"] = 204
                rec_by_key[key]["discord_response"] = ""
                rec_by_key[key]["discord_attempt_count"] = len(all_attempts)
                rec_by_key[key]["discord_attempts"] = all_attempts
                sent_ledger_rows.append({
                    "sent_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z"),
                    "payload_id": rec.get("payload_id"),
                    "payload_key": key,
                    "symbol": rec.get("symbol"),
                    "direction": rec.get("direction"),
                    "entry_time": rec.get("entry_time"),
                    "message": rec.get("message"),
                    "discord_attempt_count": len(all_attempts),
                })
            if final_error_result is not None:
                # Preserve per-attempt details in preview_json; do not append to
                # send ledger because Discord delivery was not confirmed.
                pass
            time.sleep(args.sleep_seconds)

        append_send_ledger(sent_ledger_rows, send_ledger_csv)
        records = list(rec_by_key.values())
    else:
        for rec in records:
            if rec["duplicate_existing"] and not args.allow_duplicates:
                rec["send_status"] = "DRY_RUN_DUPLICATE_WOULD_SKIP"
            else:
                rec["send_status"] = "DRY_RUN_WOULD_SEND"

    write_text(preview_json, json.dumps({"source": str(input_csv), "records": records}, ensure_ascii=False, indent=2))

    total = len(records)
    duplicates = sum(1 for r in records if r["duplicate_existing"])
    sent = sum(1 for r in records if r["sent"])
    would_send = sum(1 for r in records if r["send_status"] == "DRY_RUN_WOULD_SEND")
    errors = sum(1 for r in records if str(r["send_status"]).startswith("ERROR"))
    max_attempts = max([int(r.get("discord_attempt_count") or 0) for r in records] + [0])

    safe_print("send_mochipoyo_discord_messages")
    safe_print(f"source: {input_csv}")
    safe_print(f"rows: {total}")
    safe_print(f"send: {args.send}")
    safe_print(f"duplicates_existing: {duplicates}")
    safe_print(f"dry_run_would_send: {would_send}")
    safe_print(f"sent: {sent}")
    safe_print(f"errors: {errors}")
    safe_print(f"max_discord_attempts: {max_attempts}")
    safe_print(f"discord_retry_count: {int(args.discord_retry_count)}")
    safe_print(f"discord_retry_sleep_seconds: {float(args.discord_retry_sleep_seconds)}")
    safe_print(f"send_ledger_csv: {send_ledger_csv}")
    safe_print(f"preview_txt: {preview_txt}")
    safe_print(f"preview_json: {preview_json}")
    safe_print("preview_last: omitted from console; open preview_txt for the full UTF-8 message.")
    safe_print("done")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
