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

SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_connection_test_confirmation.json"


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def confirm_connection_test_alert(
    connection,
    *,
    raw_alert_id: int,
    confirmed_at_utc: str,
) -> dict[str, object]:
    row = connection.execute(
        """
        SELECT cloudflare_id, ticker, event, message, fired_at_utc
        FROM raw_alerts
        WHERE cloudflare_id = ?
        """,
        (raw_alert_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"raw alert {raw_alert_id} does not exist")

    message = "" if row["message"] is None else str(row["message"]).strip()
    if raw_alert_id != 1:
        raise RuntimeError("this confirmation is locked to raw alert ID 1")
    if str(row["ticker"]) != "XAUUSD" or str(row["event"]) != "LONG":
        raise RuntimeError("raw alert ID 1 is not the expected XAUUSD LONG alert")
    if not message.lower().startswith("test "):
        raise RuntimeError(
            "raw alert ID 1 is not explicitly marked as a test in its message"
        )

    reason = (
        "User confirmed that raw alert ID 1 alone was used for "
        "TradingView/Cloudflare connection verification."
    )
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """
            INSERT INTO raw_alert_annotations (
                raw_alert_id, annotation_type, confirmed_by, reason, created_at_utc
            ) VALUES (?, 'CONNECTION_TEST', 'USER', ?, ?)
            ON CONFLICT(raw_alert_id) DO UPDATE SET
                annotation_type = excluded.annotation_type,
                confirmed_by = excluded.confirmed_by,
                reason = excluded.reason
            """,
            (raw_alert_id, reason, confirmed_at_utc),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    annotation_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM raw_alert_annotations
            WHERE annotation_type = 'CONNECTION_TEST'
            """
        ).fetchone()[0]
        or 0
    )
    return {
        "status": "PASS",
        "stage": "M3_CONNECTION_TEST_ALERT_CONFIRMATION",
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": True,
        "annotation_table_modified": True,
        "raw_alerts_modified": False,
        "episodes_modified": False,
        "episode_events_modified": False,
        "anomalies_modified": False,
        "future_entry_fields_used": False,
        "confirmed_at_utc": confirmed_at_utc,
        "confirmed_raw_alert": {
            "raw_alert_id": int(row["cloudflare_id"]),
            "ticker": str(row["ticker"]),
            "event": str(row["event"]),
            "fired_at_utc": str(row["fired_at_utc"]),
            "message": message,
            "annotation_type": "CONNECTION_TEST",
            "confirmed_by": "USER",
            "reason": reason,
        },
        "connection_test_alert_count": annotation_count,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record the user-confirmed ID1 connection-test annotation."
    )
    parser.add_argument("--env", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--raw-alert-id", type=int, default=1)
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

    report_path = config.logs_dir / REPORT_NAME
    try:
        result = confirm_connection_test_alert(
            connection,
            raw_alert_id=args.raw_alert_id,
            confirmed_at_utc=utc_now_text(),
        )
        result["database_path"] = str(config.database_path)
        result["report_path"] = str(report_path)
        atomic_write_json(report_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] Connection-test confirmation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
