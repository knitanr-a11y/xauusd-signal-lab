from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "BCR02_CANONICAL_SOURCE_EVENT_LEDGER"
VERSION = "1.0.0"
PROSPECTIVE_START_UTC = "2026-07-20T14:54:15Z"
EXPECTED_BCR01_MEMBERS = [
    "00_READ_ME_FIRST.txt",
    "01_snapshot_summary.json",
    "02_source_schema_manifest.json",
    "03_collector_state.csv",
    "04_raw_alerts_manifest.csv",
    "05_raw_alerts_payloads.jsonl",
    "06_raw_alert_annotations.csv",
    "07_collection_runs.csv",
    "08_integrity_checks.json",
    "09_runtime_file_observation.json",
]
OUTPUT_MEMBERS = [
    "00_READ_ME_FIRST.txt",
    "01_ledger_summary.json",
    "02_canonical_source_event_ledger.csv",
    "03_state_seed_history.csv",
    "04_m7c_parity_audit.csv",
    "05_integrity_checks.json",
    "06_input_manifest.json",
]


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    os.replace(temporary, path)


def parse_csv_bytes(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def read_bcr01(
    package: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    if not package.is_file():
        raise FileNotFoundError(f"BCR01 package not found: {package}")
    with zipfile.ZipFile(package, "r") as archive:
        names = archive.namelist()
        if names != EXPECTED_BCR01_MEMBERS:
            raise RuntimeError(f"BCR01 ZIP layout mismatch: {names}")
        summary = json.loads(archive.read("01_snapshot_summary.json"))
        checks = json.loads(archive.read("08_integrity_checks.json"))
        alerts = parse_csv_bytes(archive.read("04_raw_alerts_manifest.csv"))
        annotations = parse_csv_bytes(archive.read("06_raw_alert_annotations.csv"))
    if summary.get("status") != "READY_OUTCOME_BLIND_SOURCE_SNAPSHOT":
        raise RuntimeError(f"BCR01 status not ready: {summary.get('status')}")
    if summary.get("version") != "1.0.1":
        raise RuntimeError(f"BCR01 version must be 1.0.1: {summary.get('version')}")
    if summary.get("outcomes_opened") is not False:
        raise RuntimeError("BCR01 outcomes_opened must be false")
    if checks.get("outcome_tables_read") is not False:
        raise RuntimeError("BCR01 outcome_tables_read must be false")
    if checks.get("performance_interpretation_performed") is not False:
        raise RuntimeError("BCR01 performance interpretation must be false")
    if checks.get("cursor_equals_max_raw_id") is not True:
        raise RuntimeError("BCR01 cursor/max raw id mismatch")
    return summary, checks, alerts, annotations


def parse_m7c(package: Path | None) -> tuple[str | None, list[dict[str, str]]]:
    if package is None:
        return None, []
    if not package.is_file():
        raise FileNotFoundError(f"M7C package not found: {package}")
    with zipfile.ZipFile(package, "r") as archive:
        target = "latest_m7c_source_event_comparisons.csv"
        if target not in archive.namelist():
            raise RuntimeError(f"M7C package missing {target}")
        rows = parse_csv_bytes(archive.read(target))
    return sha256_path(package), rows


def role_for(state: str, event: str) -> tuple[str, str, str]:
    if state == "IDLE":
        if event == "LONG":
            return "PRIMARY_LONG", "PRIMARY_ALERT", "ACTIVE_LONG"
        if event == "SHORT":
            return "PRIMARY_SHORT", "PRIMARY_ALERT", "ACTIVE_SHORT"
        if event in {"LONG_EXIT", "SHORT_EXIT"}:
            return "EXIT_WHILE_IDLE_IGNORED", "EXIT_WHILE_IDLE_IGNORED", "IDLE"
    elif state == "ACTIVE_LONG":
        if event == "LONG":
            return "REENTRY_LONG", "REENTRY_ALERT", state
        if event == "SHORT":
            return "OPPOSITE_ALERT_IGNORED", "OPPOSITE_ALERT_IGNORED", state
        if event == "LONG_EXIT":
            return "LONG_EXIT", "EXIT_ALERT", "IDLE"
        if event == "SHORT_EXIT":
            return "OPPOSITE_EXIT_IGNORED", "OPPOSITE_EXIT_IGNORED", state
    elif state == "ACTIVE_SHORT":
        if event == "SHORT":
            return "REENTRY_SHORT", "REENTRY_ALERT", state
        if event == "LONG":
            return "OPPOSITE_ALERT_IGNORED", "OPPOSITE_ALERT_IGNORED", state
        if event == "SHORT_EXIT":
            return "SHORT_EXIT", "EXIT_ALERT", "IDLE"
        if event == "LONG_EXIT":
            return "OPPOSITE_EXIT_IGNORED", "OPPOSITE_EXIT_IGNORED", state
    raise RuntimeError(
        f"unsupported state/event combination: state={state} event={event}"
    )


def seconds_between(later: str, earlier: str) -> float:
    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    return (parse(later) - parse(earlier)).total_seconds()


def build_ledger(
    alerts: list[dict[str, str]], annotations: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    connection_tests = {
        int(row["raw_alert_id"])
        for row in annotations
        if row.get("annotation_type") == "CONNECTION_TEST"
    }
    normalized = sorted(alerts, key=lambda row: int(row["cloudflare_id"]))
    ids = [int(row["cloudflare_id"]) for row in normalized]
    if not ids:
        raise RuntimeError("raw alert input is empty")
    if ids != list(range(min(ids), max(ids) + 1)):
        raise RuntimeError("raw alert IDs are not contiguous")

    state = {"BTCUSD": "IDLE", "XAUUSD": "IDLE"}
    all_rows: list[dict[str, Any]] = []
    for raw in normalized:
        raw_id = int(raw["cloudflare_id"])
        ticker = raw["ticker"]
        event = raw["event"]
        before = state[ticker]
        if raw_id in connection_tests:
            transition = "EXCLUDED_CONNECTION_TEST"
            role = "EXCLUDED_CONNECTION_TEST"
            after = before
            excluded = True
        else:
            transition, role, after = role_for(before, event)
            state[ticker] = after
            excluded = False
        all_rows.append(
            {
                "raw_alert_id": raw_id,
                "event_key": raw["event_key"],
                "payload_sha256": raw["payload_sha256"],
                "ticker": ticker,
                "event": event,
                "exchange_name": raw["exchange_name"],
                "timeframe": raw["timeframe"],
                "bar_time_utc": raw["bar_time_utc"],
                "fired_at_utc": raw["fired_at_utc"],
                "received_at_utc": raw["received_at_utc"],
                "downloaded_at_utc": raw["downloaded_at_utc"],
                "source_open": raw["open_price"],
                "source_high": raw["high_price"],
                "source_low": raw["low_price"],
                "source_close": raw["close_price"],
                "source_state_before": before,
                "source_transition": transition,
                "source_state_after": after,
                "event_role": role,
                "excluded_connection_test": excluded,
                "supported_by_m7c_v1": role in {"PRIMARY_ALERT", "EXIT_ALERT"},
                "fired_minus_bar_seconds": seconds_between(
                    raw["fired_at_utc"], raw["bar_time_utc"]
                ),
                "received_minus_fired_seconds": seconds_between(
                    raw["received_at_utc"], raw["fired_at_utc"]
                ),
                "downloaded_minus_received_seconds": seconds_between(
                    raw["downloaded_at_utc"], raw["received_at_utc"]
                ),
            }
        )

    seed = [row for row in all_rows if row["bar_time_utc"] < PROSPECTIVE_START_UTC]
    research = [
        row
        for row in all_rows
        if row["bar_time_utc"] >= PROSPECTIVE_START_UTC
        and not row["excluded_connection_test"]
    ]
    checks = {
        "raw_alert_rows": len(all_rows),
        "raw_alert_id_min": min(ids),
        "raw_alert_id_max": max(ids),
        "raw_alert_ids_contiguous": True,
        "connection_test_ids": sorted(connection_tests),
        "state_seed_rows": len(seed),
        "research_rows": len(research),
        "research_raw_id_min": min(row["raw_alert_id"] for row in research),
        "research_raw_id_max": max(row["raw_alert_id"] for row in research),
        "final_state": state,
        "outcomes_opened": False,
        "performance_interpretation_performed": False,
    }
    return seed, research, checks


def parity_rows(
    research: list[dict[str, Any]], comparisons: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ledger = {int(row["raw_alert_id"]): row for row in research}
    output: list[dict[str, Any]] = []
    for source in comparisons:
        raw_id = int(source["raw_alert_id"])
        row = ledger.get(raw_id)
        if row is None:
            raise RuntimeError(f"M7C comparison raw id missing from ledger: {raw_id}")
        fields = {
            "ticker": row["ticker"] == source["ticker"],
            "source_decision_time_utc": row["bar_time_utc"]
            == source["source_decision_time_utc"],
            "source_transition": row["source_transition"]
            == source["source_transition"],
            "source_state_before": row["source_state_before"]
            == source["source_state_before"],
            "source_state_after": row["source_state_after"]
            == source["source_state_after"],
            "event_role": row["event_role"] == source["event_role"],
        }
        output.append(
            {
                "raw_alert_id": raw_id,
                **{f"{key}_match": value for key, value in fields.items()},
                "all_match": all(fields.values()),
            }
        )
    mismatches = [row for row in output if not row["all_match"]]
    return output, {
        "m7c_comparison_rows": len(output),
        "m7c_parity_mismatches": mismatches,
        "m7c_parity_all_match": not mismatches,
        "m7c_comparison_raw_id_min": min(
            (row["raw_alert_id"] for row in output), default=None
        ),
        "m7c_comparison_raw_id_max": max(
            (row["raw_alert_id"] for row in output), default=None
        ),
    }


def build(bcr01_zip: Path, output_root: Path, m7c_zip: Path | None = None) -> Path:
    bcr01_summary, bcr01_checks, alerts, annotations = read_bcr01(bcr01_zip)
    m7c_sha, comparisons = parse_m7c(m7c_zip)
    seed, research, checks = build_ledger(alerts, annotations)
    parity, parity_checks = parity_rows(research, comparisons)
    if comparisons and not parity_checks["m7c_parity_all_match"]:
        raise RuntimeError(
            f"M7C parity mismatch: {parity_checks['m7c_parity_mismatches'][:5]}"
        )
    checks.update(parity_checks)

    transition_counts: dict[str, int] = {}
    ticker_counts: dict[str, int] = {}
    supported_counts: dict[str, int] = {}
    for row in research:
        transition = row["source_transition"]
        ticker = row["ticker"]
        transition_counts[transition] = transition_counts.get(transition, 0) + 1
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        if row["supported_by_m7c_v1"]:
            supported_counts[ticker] = supported_counts.get(ticker, 0) + 1

    snapshot_id = (
        f"BCR02_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        f"_RAW{checks['research_raw_id_min']}-{checks['research_raw_id_max']}"
    )
    staging = output_root / (snapshot_id + "_STAGING")
    run_dir = output_root / snapshot_id
    if staging.exists():
        shutil.rmtree(staging)
    if run_dir.exists():
        raise FileExistsError(f"output exists: {run_dir}")
    staging.mkdir(parents=True, exist_ok=False)

    ledger_columns = [
        "raw_alert_id",
        "event_key",
        "payload_sha256",
        "ticker",
        "event",
        "exchange_name",
        "timeframe",
        "bar_time_utc",
        "fired_at_utc",
        "received_at_utc",
        "downloaded_at_utc",
        "source_open",
        "source_high",
        "source_low",
        "source_close",
        "source_state_before",
        "source_transition",
        "source_state_after",
        "event_role",
        "excluded_connection_test",
        "supported_by_m7c_v1",
        "fired_minus_bar_seconds",
        "received_minus_fired_seconds",
        "downloaded_minus_received_seconds",
    ]
    parity_columns = [
        "raw_alert_id",
        "ticker_match",
        "source_decision_time_utc_match",
        "source_transition_match",
        "source_state_before_match",
        "source_state_after_match",
        "event_role_match",
        "all_match",
    ]
    write_csv(staging / "02_canonical_source_event_ledger.csv", ledger_columns, research)
    write_csv(staging / "03_state_seed_history.csv", ledger_columns, seed)
    write_csv(staging / "04_m7c_parity_audit.csv", parity_columns, parity)
    write_json(staging / "05_integrity_checks.json", checks)
    write_json(
        staging / "06_input_manifest.json",
        {
            "bcr01_zip_path": str(bcr01_zip.resolve()),
            "bcr01_zip_sha256": sha256_path(bcr01_zip),
            "bcr01_snapshot_id": bcr01_summary["snapshot_id"],
            "bcr01_raw_alert_max": bcr01_checks["raw_alert_id_max"],
            "m7c_zip_path": str(m7c_zip.resolve()) if m7c_zip else None,
            "m7c_zip_sha256": m7c_sha,
            "prospective_start_utc": PROSPECTIVE_START_UTC,
        },
    )
    summary = {
        "stage": STAGE,
        "version": VERSION,
        "status": "READY_CANONICAL_SOURCE_EVENT_LEDGER_OUTCOME_BLIND",
        "snapshot_id": snapshot_id,
        "generated_at_utc": utc_now(),
        "research_rows": len(research),
        "state_seed_rows": len(seed),
        "ticker_counts": ticker_counts,
        "supported_m7c_v1_counts": supported_counts,
        "transition_counts": transition_counts,
        "m7c_parity_rows": parity_checks["m7c_comparison_rows"],
        "m7c_parity_all_match": parity_checks["m7c_parity_all_match"],
        "outcomes_opened": False,
        "performance_interpretation_performed": False,
        "candidate_formula_designed": False,
    }
    write_json(staging / "01_ledger_summary.json", summary)
    write_text(
        staging / "00_READ_ME_FIRST.txt",
        "BCR02 canonical source event ledger — outcome blind\n\n"
        f"Status: {summary['status']}\n"
        f"Research rows: {summary['research_rows']}\n"
        "State was seeded from pre-prospective source events after excluding "
        "user-confirmed connection tests.\n"
        "No outcome or performance table was opened.\n",
    )
    os.replace(staging, run_dir)
    package = run_dir / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in OUTPUT_MEMBERS:
            archive.write(run_dir / name, name)
    with zipfile.ZipFile(package, "r") as archive:
        if archive.namelist() != OUTPUT_MEMBERS:
            raise RuntimeError(f"BCR02 ZIP layout mismatch: {archive.namelist()}")
    return package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bcr01-zip", type=Path, required=True)
    parser.add_argument("--m7c-zip", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        package = build(args.bcr01_zip, args.output_root, args.m7c_zip)
    except Exception as exc:
        print(f"[BCR02] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"[BCR02] READY: {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
