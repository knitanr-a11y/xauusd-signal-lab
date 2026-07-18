from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from mochipoyo_alert_research.config import load_config  # noqa: E402
from mochipoyo_alert_research.db import open_database, utc_now_text  # noqa: E402
from mochipoyo_alert_research.episode_builder import rebuild_episodes  # noqa: E402

SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_episode_build_result.json"


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild Mochipoyo source-alert episodes from immutable raw alerts."
    )
    parser.add_argument("--env", type=Path)
    parser.add_argument("--db", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.env, args.db, require_remote=False)
        config.local_root.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        connection = open_database(config.database_path, SCHEMA_PATH)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    built_at_utc = utc_now_text()
    report_path = config.logs_dir / REPORT_NAME
    try:
        result = rebuild_episodes(connection, built_at_utc=built_at_utc)
        by_ticker_direction = [
            dict(row)
            for row in connection.execute(
                """
                SELECT ticker, direction, episode_status, COUNT(*) AS episode_count
                FROM episodes
                GROUP BY ticker, direction, episode_status
                ORDER BY ticker, direction, episode_status
                """
            ).fetchall()
        ]
        anomaly_reasons = [
            dict(row)
            for row in connection.execute(
                """
                SELECT reason, COUNT(*) AS anomaly_count
                FROM episode_build_anomalies
                GROUP BY reason
                ORDER BY reason
                """
            ).fetchall()
        ]
        excluded_alerts = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    a.raw_alert_id,
                    a.annotation_type,
                    a.confirmed_by,
                    a.reason,
                    a.created_at_utc,
                    r.ticker,
                    r.event,
                    r.message
                FROM raw_alert_annotations a
                JOIN raw_alerts r ON r.cloudflare_id = a.raw_alert_id
                WHERE a.annotation_type = 'CONNECTION_TEST'
                ORDER BY a.raw_alert_id
                """
            ).fetchall()
        ]
        payload = {
            "status": "PASS_EMPTY_RAW" if result.raw_alert_count == 0 else "PASS",
            "stage": "M3_EPISODE_BUILD",
            "audit_only": True,
            "dry_run": True,
            "live_ready": False,
            "final_signal": False,
            "discord_send": False,
            "mt5_order": False,
            "future_entry_fields_used": False,
            "built_at_utc": built_at_utc,
            "raw_alert_count": result.raw_alert_count,
            "eligible_raw_alert_count": result.eligible_raw_alert_count,
            "excluded_connection_test_count": result.excluded_connection_test_count,
            "episode_count": result.episode_count,
            "closed_episode_count": result.closed_episode_count,
            "open_episode_count": result.open_episode_count,
            "reentry_count": result.reentry_count,
            "anomaly_count": result.anomaly_count,
            "ignored_opposite_count": result.ignored_opposite_count,
            "latest_raw_id": result.latest_raw_id,
            "excluded_alerts": excluded_alerts,
            "by_ticker_direction": by_ticker_direction,
            "anomaly_reasons": anomaly_reasons,
            "database_path": str(config.database_path),
            "report_path": str(report_path),
        }
        atomic_write_json(report_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] Episode build failed: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
