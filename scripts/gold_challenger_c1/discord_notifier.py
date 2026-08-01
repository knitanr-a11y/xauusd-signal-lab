from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Mapping

from .discord_delivery import chart, discord_settings, message, send
from .shadow_common import (
    CANDIDATE_ID, CONTRACT_VERSION, load_config, lock_instance, logger_for,
    now_utc, read_csv_records, read_json, state_root, write_json,
)

NOTIFIER_VERSION = "2026-08-01-discord-v1"


def accepted_count(runtime: Mapping[str, Any]) -> int:
    try:
        return int(runtime.get("counters", {}).get("accepted_trades", 0))
    except (AttributeError, TypeError, ValueError):
        return 0


def last_accepted_candidate(root: Path) -> dict[str, str]:
    for row in reversed(read_csv_records(root / "outputs" / "shadow_candidate_ledger.csv")):
        if str(row.get("status", "")).upper() == "ACCEPTED":
            return row
    return {}


def default_notifier_state(runtime: Mapping[str, Any]) -> dict[str, Any]:
    count = accepted_count(runtime)
    return {
        "candidate_id": CANDIDATE_ID,
        "contract_version": CONTRACT_VERSION,
        "notifier_version": NOTIFIER_VERSION,
        "startup_policy": "NO_BACKFILL_BASELINE_CURRENT_ACCEPTED_COUNT",
        "baseline_accepted_trades": count,
        "last_seen_accepted_trades": count,
        "sent_entry_notifications": 0,
        "last_sent_at_utc": None,
        "last_error": None,
        "started_at_utc": now_utc(),
    }


def validate(config_path: Path) -> None:
    settings = discord_settings(load_config(config_path))
    print(json.dumps({"status": "READY", "webhook_source": "V19_LOCAL_CONFIG", "username": settings["username"]}, ensure_ascii=False, indent=2))


def test(config_path: Path) -> None:
    settings = discord_settings(load_config(config_path))
    send(
        str(settings["webhook_url"]),
        str(settings["username"]),
        "✅ **GOLD Challenger C1 Shadow Discord接続テスト**\n観測専用通知です。実注文は行いません。",
    )
    print("Discord test notification sent.")


def loop(config_path: Path) -> None:
    config = load_config(config_path)
    settings = discord_settings(config)
    root = state_root(config)
    runtime_path = root / "runtime_state.json"
    if not runtime_path.exists():
        raise FileNotFoundError("Challenger runtime_state.json is missing")
    logger = logger_for(root, "gold_challenger_c1_discord", "discord_notifier.log")
    lock = lock_instance(root, "discord_notifier.lock", "Challenger Discord notifier is already running")
    runtime = read_json(runtime_path)
    status = default_notifier_state(runtime)
    status_path = root / "discord_notifier_state.json"
    write_json(status_path, status)
    seen = accepted_count(runtime)
    delay = max(2, int(settings.get("poll_seconds", config.get("poll_seconds", 10))))
    logger.info("READY; no-backfill baseline accepted_trades=%s", seen)
    try:
        while True:
            try:
                runtime = read_json(runtime_path)
                current = accepted_count(runtime)
                if current < seen:
                    logger.warning("accepted_trades moved backwards: %s -> %s", seen, current)
                    seen = current
                elif current > seen:
                    if current - seen != 1:
                        logger.warning("Missed %s entries; delayed Discord alerts suppressed", current - seen)
                        seen = current
                    else:
                        event = last_accepted_candidate(root)
                        if not event:
                            raise RuntimeError("Accepted counter advanced but no accepted candidate row was found")
                        image = None
                        try:
                            image = chart(config, event, root)
                        except Exception:
                            logger.exception("Chart generation failed; sending text only")
                        send(str(settings["webhook_url"]), str(settings["username"]), message(event), image)
                        seen = current
                        status["sent_entry_notifications"] = int(status["sent_entry_notifications"]) + 1
                        status["last_sent_at_utc"] = now_utc()
                        status["last_error"] = None
                        logger.info("Sent Challenger entry alert count=%s MT5=%s", current, event.get("decision_dt"))
                status["last_seen_accepted_trades"] = seen
                write_json(status_path, status)
            except Exception as exc:
                status["last_error"] = {"at_utc": now_utc(), "message": str(exc)}
                write_json(status_path, status)
                logger.exception("Notifier iteration failed")
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        lock.close()


def status(config_path: Path) -> None:
    root = state_root(load_config(config_path))
    path = root / "discord_notifier_state.json"
    value = read_json(path) if path.exists() else {"status": "NOT_STARTED", "path": str(path)}
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GOLD Challenger C1 observation-only Discord notifier")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("command", choices=["validate", "test", "loop", "status"])
    args = parser.parse_args(argv)
    try:
        {"validate": validate, "test": test, "loop": loop, "status": status}[args.command](args.config)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
