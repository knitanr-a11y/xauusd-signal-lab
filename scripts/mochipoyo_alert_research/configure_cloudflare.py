from __future__ import annotations

import argparse
import getpass
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def default_local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if not base:
        base = os.environ.get("TEMP", "").strip()
    if not base:
        base = tempfile.gettempdir()
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def normalize_events_url(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("Worker URL is required")
    parts = urlsplit(text)
    if parts.scheme.lower() != "https":
        raise ValueError("Worker URL must use https://")
    if not parts.netloc:
        raise ValueError("Worker URL is missing a host name")
    if parts.username or parts.password:
        raise ValueError("Worker URL must not contain embedded credentials")
    if parts.query or parts.fragment:
        raise ValueError("Worker URL must not contain query parameters or a fragment")
    path = parts.path.rstrip("/")
    if not path.endswith("/events"):
        path = f"{path}/events" if path else "/events"
    return urlunsplit(("https", parts.netloc, path, "", ""))


def validate_token(value: str) -> str:
    token = value.strip()
    if not token:
        raise ValueError("READ_TOKEN is required")
    if "\n" in token or "\r" in token:
        raise ValueError("READ_TOKEN must be a single line")
    return token


def write_env(path: Path, events_url: str, read_token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "# Mochipoyo Cloudflare read-only collector. Local secret file; never commit.\n"
        f"MOCHIPOYO_EVENTS_URL={events_url}\n"
        f"MOCHIPOYO_READ_TOKEN={read_token}\n"
    )
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8", newline="\n")
    temp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the local-only Cloudflare configuration for Mochipoyo Stage M1."
    )
    parser.add_argument("--env", type=Path, default=default_local_root() / ".env")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_path = args.env.expanduser().resolve()
    print("=" * 60)
    print("Mochipoyo Cloudflare local configuration")
    print("This writes only to the local PC. Nothing is sent to GitHub.")
    print("READ_TOKEN input is hidden and is never printed.")
    print("=" * 60)
    print(f"Local config: {env_path}")

    if env_path.exists() and not args.force:
        answer = input("A local configuration already exists. Replace it? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("No changes were made.")
            return 0

    try:
        events_url = normalize_events_url(
            input("Paste the Worker URL (root URL or /events URL): ")
        )
        read_token = validate_token(getpass.getpass("Paste READ_TOKEN (hidden): "))
        write_env(env_path, events_url, read_token)
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled. No configuration was written.")
        return 1
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 2

    print("\n[PASS] Local Cloudflare configuration was saved.")
    print(f"Config path : {env_path}")
    print(f"Database    : {env_path.parent / 'mochipoyo_alerts.sqlite3'}")
    print("Worker URL and READ_TOKEN were not displayed.")
    print("Discord send: OFF | MT5 orders: OFF | live_ready: OFF | final_signal: OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
