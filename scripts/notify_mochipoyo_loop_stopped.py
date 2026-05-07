#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Send a Discord notification when a Mochipoyo live loop stops.

This script is intended to be called from .bat after the forever loop process
returns. It sends a compact stop alert that includes:
- loop name
- exit code
- stopped time
- summary CSV path
- latest summary row fields, when available

Webhook resolution matches the existing Discord sender:
1. --webhook-url
2. environment variable from --webhook-env, default DISCORD_WEBHOOK_URL
3. .env in current working directory or repository root

It deliberately never prints the webhook URL.
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


def safe_text(text: object) -> str:
    s = str(text)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return s.encode(enc, errors="backslashreplace").decode(enc, errors="replace")


def safe_print(text: object = "") -> None:
    print(safe_text(text))


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding=encoding, newline="") as f:
        f.write(text)


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


def post_discord(webhook_url: str, content: str, username: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"content": content}
    if username:
        payload["username"] = username
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "mochipoyo-loop-stop-notifier/1.0"},
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


def is_transient(result: dict[str, Any]) -> bool:
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
    return max(0.0, float(base_sleep)) * float(attempt_index)


def post_with_retries(webhook_url: str, content: str, username: str | None, retry_count: int, retry_sleep_sec: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    total_attempts = max(1, int(retry_count) + 1)
    final: dict[str, Any] = {"ok": False, "status": None, "body": "not attempted"}
    for attempt in range(1, total_attempts + 1):
        result = post_discord(webhook_url, content, username=username)
        final = result
        attempts.append(
            {
                "attempt": attempt,
                "ok": bool(result.get("ok")),
                "status": result.get("status"),
                "body": result.get("body"),
                "exception_type": result.get("exception_type"),
                "transient": is_transient(result),
            }
        )
        if result.get("ok"):
            break
        if attempt >= total_attempts:
            break
        if not is_transient(result):
            break
        time.sleep(retry_sleep_seconds(retry_sleep_sec, attempt, result))
    final = dict(final)
    final["attempt_count"] = len(attempts)
    return final, attempts


def latest_summary_row(summary_csv: Path) -> dict[str, Any]:
    if not summary_csv.exists():
        return {"summary_read_status": "MISSING_SUMMARY_CSV"}
    try:
        df = pd.read_csv(windows_long_path(summary_csv), encoding="utf-8-sig")
        if df.empty:
            return {"summary_read_status": "EMPTY_SUMMARY_CSV"}
        row = df.iloc[-1].to_dict()
        row["summary_read_status"] = "OK"
        return row
    except Exception as e:
        return {"summary_read_status": "READ_ERROR", "summary_read_error": repr(e)}


def fmt_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def build_message(args: argparse.Namespace, latest: dict[str, Any]) -> str:
    stopped_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    exit_code = int(args.exit_code)
    status_icon = "⚠️" if exit_code != 0 else "ℹ️"
    title = f"{status_icon} Mochipoyo loop stopped"

    fields = [
        f"loop: `{args.loop_name}`",
        f"exit_code: `{exit_code}`",
        f"stopped_at: `{stopped_at}`",
        f"summary_csv: `{args.summary_csv}`",
        f"summary_read_status: `{fmt_value(latest.get('summary_read_status'))}`",
    ]

    interesting = [
        "loop_iteration",
        "started_at",
        "finished_at",
        "returncode",
        "pairs_to_scan",
        "notification_ok_live_rows",
        "ledger_new_candidates",
        "discord_status",
        "order_payload_status",
        "auto_trade_status",
        "auto_trade_order_send_called_count",
        "auto_trade_sent_rows",
        "success",
    ]
    for key in interesting:
        if key in latest:
            fields.append(f"{key}: `{fmt_value(latest.get(key))}`")

    return title + "\n" + "\n".join(fields)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Send Discord notification when Mochipoyo loop stops.")
    p.add_argument("--loop-name", default="mochipoyo_gold_demo_autotrade_forever_aligned")
    p.add_argument("--exit-code", type=int, required=True)
    p.add_argument("--summary-csv", required=True)
    p.add_argument("--webhook-url", default=None)
    p.add_argument("--webhook-env", default="DISCORD_WEBHOOK_URL")
    p.add_argument("--username", default="Mochipoyo Loop Watch")
    p.add_argument("--retry-count", type=int, default=3)
    p.add_argument("--retry-sleep-seconds", type=float, default=2.0)
    p.add_argument("--preview-txt", default=None)
    p.add_argument("--preview-json", default=None)
    p.add_argument("--notify-on-zero", action="store_true", help="Also notify when exit code is 0. By default only non-zero exits notify.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if int(args.exit_code) == 0 and not bool(args.notify_on_zero):
        safe_print("notify_mochipoyo_loop_stopped: skipped because exit_code=0 and --notify-on-zero was not set")
        return 0

    load_local_dotenv()
    webhook_url = args.webhook_url or os.environ.get(args.webhook_env)
    summary_csv = Path(args.summary_csv)
    latest = latest_summary_row(summary_csv)
    message = build_message(args, latest)

    if args.preview_txt:
        write_text(args.preview_txt, message + "\n")

    if not webhook_url:
        result = {"ok": False, "status": None, "body": "ERROR_NO_WEBHOOK_URL", "attempt_count": 0}
        attempts: list[dict[str, Any]] = []
        if args.preview_json:
            write_text(args.preview_json, json.dumps({"message": message, "result": result, "attempts": attempts}, ensure_ascii=False, indent=2))
        safe_print("notify_mochipoyo_loop_stopped")
        safe_print("ERROR: webhook URL was not provided.")
        safe_print(f"Set {args.webhook_env} in .env/env or pass --webhook-url.")
        return 2

    result, attempts = post_with_retries(
        webhook_url,
        message,
        username=args.username,
        retry_count=int(args.retry_count),
        retry_sleep_sec=float(args.retry_sleep_seconds),
    )

    if args.preview_json:
        write_text(args.preview_json, json.dumps({"message": message, "result": result, "attempts": attempts}, ensure_ascii=False, indent=2))

    safe_print("notify_mochipoyo_loop_stopped")
    safe_print(f"loop_name: {args.loop_name}")
    safe_print(f"exit_code: {int(args.exit_code)}")
    safe_print(f"summary_csv: {summary_csv}")
    safe_print(f"sent: {bool(result.get('ok'))}")
    safe_print(f"status: {result.get('status')}")
    safe_print(f"attempt_count: {result.get('attempt_count')}")
    safe_print("done")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
