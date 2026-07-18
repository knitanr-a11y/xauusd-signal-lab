from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from mochipoyo_alert_research.config import load_config  # noqa: E402
from mochipoyo_alert_research.db import (  # noqa: E402
    open_database,
    record_collection_run,
    state_int,
    store_page,
    utc_now_text,
)
from mochipoyo_alert_research.redact import redact_text  # noqa: E402

SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
LATEST_RESULT_NAME = "latest_collection_result.json"
LATEST_ERROR_NAME = "latest_collection_error.json"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_events_url(base_url: str, after_id: int, limit: int) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["after_id"] = str(after_id)
    query["limit"] = str(limit)
    path = parts.path or "/events"
    if not path.rstrip("/").endswith("/events") and path.rstrip("/") != "events":
        path = path.rstrip("/") + "/events"
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), ""))


def request_label(after_id: int, limit: int) -> str:
    return f"<configured-worker>/events?after_id={after_id}&limit={limit}"


def extract_events(payload: Any) -> tuple[list[Any], dict[str, Any]]:
    if isinstance(payload, list):
        return payload, {}
    if not isinstance(payload, dict):
        raise ValueError("Cloudflare response must be a JSON object or array")
    if payload.get("ok") is False:
        message = payload.get("error") or payload.get("message") or "unspecified error"
        raise ValueError(f"Cloudflare response reported ok=false: {message}")
    for key in ("events", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            metadata = {k: v for k, v in payload.items() if k != key}
            return value, metadata
    raise ValueError(
        "Cloudflare response does not contain an event list; "
        f"top_level_keys={sorted(str(key) for key in payload.keys())}"
    )


def _http_failure(code: int, body: str) -> RuntimeError:
    if code in {401, 403}:
        guidance = "READ_TOKEN was rejected. Re-run the local configuration and verify the Worker secret."
    elif code == 404:
        guidance = "The Worker URL or /events path was not found. Re-run the local configuration with the Worker root URL."
    elif code == 429:
        guidance = "Cloudflare rate-limited the request. Wait and retry the one-shot collector."
    elif 500 <= code <= 599:
        guidance = "The Worker or D1 returned a server error. Check the Worker deployment and D1 binding."
    else:
        guidance = "The Worker rejected the request. Check the URL, token, and Worker route."
    compact_body = " ".join(body.split())[:500]
    suffix = f" Response body: {compact_body}" if compact_body else ""
    return RuntimeError(f"Cloudflare HTTP {code}. {guidance}{suffix}")


def fetch_json(url: str, read_token: str, timeout_seconds: float) -> Any:
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {read_token}",
            "User-Agent": "xauusd-signal-lab/mochipoyo-audit-collector",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(raw.decode(charset))
    except HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        raise _http_failure(int(exc.code), body) from exc
    except URLError as exc:
        raise RuntimeError(
            "Cloudflare connection failed. Check the internet connection and Worker URL. "
            f"Reason: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Cloudflare returned a non-JSON response. Check that the configured URL points to the Worker /events endpoint."
        ) from exc


def load_fixture(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect one incremental page of real Mochipoyo alerts."
    )
    parser.add_argument("--env", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--after-id", type=int)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit < 1 or args.limit > 5000:
        print("--limit must be between 1 and 5000", file=sys.stderr)
        return 2
    if args.timeout_seconds <= 0:
        print("--timeout-seconds must be positive", file=sys.stderr)
        return 2

    require_remote = args.fixture is None
    try:
        config = load_config(args.env, args.db, require_remote=require_remote)
        config.local_root.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        connection = open_database(config.database_path, SCHEMA_PATH)
    except Exception as exc:
        print(redact_text(exc), file=sys.stderr)
        return 2

    latest_result_path = config.logs_dir / LATEST_RESULT_NAME
    latest_error_path = config.logs_dir / LATEST_ERROR_NAME
    run_id = uuid.uuid4().hex
    started = utc_now_text()
    after_id_before = (
        int(args.after_id)
        if args.after_id is not None
        else state_int(connection, "last_successful_id", 0)
    )
    if after_id_before < 0:
        print("--after-id must be non-negative", file=sys.stderr)
        connection.close()
        return 2

    source_mode = "FIXTURE" if args.fixture is not None else "CLOUDFLARE"
    request_url = (
        str(args.fixture.resolve())
        if args.fixture is not None
        else build_events_url(config.events_url, after_id_before, args.limit)
    )
    safe_target = (
        str(args.fixture.resolve())
        if args.fixture is not None
        else request_label(after_id_before, args.limit)
    )
    secret_values = (config.read_token, config.events_url, request_url)

    response_count = 0
    inserted_count = 0
    duplicate_count = 0
    max_response_id: int | None = None
    cursor_after = after_id_before
    try:
        payload = (
            load_fixture(args.fixture)
            if args.fixture is not None
            else fetch_json(request_url, config.read_token, args.timeout_seconds)
        )
        events, metadata = extract_events(payload)
        latest_id = metadata.get("latest_id", metadata.get("max_id"))
        if latest_id is not None and int(latest_id) < after_id_before:
            raise ValueError(
                "remote latest_id is behind the local last_successful_id; "
                "manual audit is required"
            )
        stored = store_page(
            connection,
            events,
            after_id_before=after_id_before,
            downloaded_at_utc=utc_now_text(),
        )
        response_count = stored.response_count
        inserted_count = stored.inserted_count
        duplicate_count = stored.duplicate_count
        max_response_id = stored.max_response_id
        cursor_after = stored.cursor_after
        status = "PASS_EMPTY" if response_count == 0 else "PASS"
        finished = utc_now_text()
        record_collection_run(
            connection,
            run_id=run_id,
            started_at_utc=started,
            finished_at_utc=finished,
            after_id_before=after_id_before,
            requested_limit=args.limit,
            response_count=response_count,
            inserted_count=inserted_count,
            duplicate_count=duplicate_count,
            max_response_id=max_response_id,
            cursor_after=cursor_after,
            status=status,
            source_mode=source_mode,
            events_url_redacted=safe_target,
        )
        result = {
            "status": status,
            "audit_only": True,
            "dry_run": True,
            "live_ready": False,
            "final_signal": False,
            "discord_send": False,
            "mt5_order": False,
            "source_mode": source_mode,
            "after_id_before": after_id_before,
            "response_count": response_count,
            "inserted_count": inserted_count,
            "duplicate_count": duplicate_count,
            "cursor_after": cursor_after,
            "database_path": str(config.database_path),
            "diagnostic_path": str(latest_result_path),
        }
        atomic_write_json(latest_result_path, result)
        latest_error_path.unlink(missing_ok=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        finished = utc_now_text()
        safe_error = redact_text(exc, secret_values)
        preserved_cursor = state_int(connection, "last_successful_id", after_id_before)
        try:
            record_collection_run(
                connection,
                run_id=run_id,
                started_at_utc=started,
                finished_at_utc=finished,
                after_id_before=after_id_before,
                requested_limit=args.limit,
                response_count=response_count,
                inserted_count=0,
                duplicate_count=0,
                max_response_id=None,
                cursor_after=preserved_cursor,
                status="FAIL",
                source_mode=source_mode,
                events_url_redacted=safe_target,
                error_type=type(exc).__name__,
                error_message_redacted=safe_error,
            )
        except Exception:
            pass
        error_payload = {
            "status": "FAIL",
            "audit_only": True,
            "dry_run": True,
            "live_ready": False,
            "final_signal": False,
            "discord_send": False,
            "mt5_order": False,
            "source_mode": source_mode,
            "failed_at_utc": finished,
            "error_type": type(exc).__name__,
            "error_message_redacted": safe_error,
            "request_target": safe_target,
            "after_id_before": after_id_before,
            "cursor_preserved_at": preserved_cursor,
            "database_path": str(config.database_path),
            "diagnostic_path": str(latest_error_path),
            "secrets_logged": False,
        }
        try:
            atomic_write_json(latest_error_path, error_payload)
        except Exception:
            pass
        print(f"[ERROR] {safe_error}", file=sys.stderr)
        print(f"[ERROR] Diagnostic: {latest_error_path}", file=sys.stderr)
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
