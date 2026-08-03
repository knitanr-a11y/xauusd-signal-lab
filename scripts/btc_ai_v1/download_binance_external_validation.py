#!/usr/bin/env python3
"""Download and audit Binance BTCUSDT USD-M perpetual 1-minute data.

This script is intentionally independent from the XM BTCUSD# source. It downloads
one calendar year of official Binance monthly archives, verifies the published
SHA256 checksum for every kline archive, streams the rows into one gzip CSV, and
writes an audit manifest. Funding-rate archives are downloaded when available and
kept as raw ZIP files for a later schema-frozen ingestion stage.

No trading, order submission, or candidate evaluation is performed here.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

BASE_URL = "https://data.binance.vision/data/futures/um/monthly"
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
KLINE_HEADER = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, path: Path, *, required: bool = True) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "btc-ai-v1-research/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        return True
    except urllib.error.HTTPError as exc:
        if not required and exc.code == 404:
            return False
        raise RuntimeError(f"download failed: {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download failed: {url}: {exc.reason}") from exc


def parse_checksum(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"empty checksum file: {path}")
    token = text.split()[0].lower()
    if len(token) != 64 or any(ch not in "0123456789abcdef" for ch in token):
        raise RuntimeError(f"invalid SHA256 checksum format: {path}: {token!r}")
    return token


def utc_iso(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return dt.datetime.fromtimestamp(timestamp_ms / 1000, tz=dt.timezone.utc).isoformat()


def is_numeric_timestamp(value: str) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def process_year(year: int, output_dir: Path) -> None:
    if year < 2019 or year > 2100:
        raise ValueError(f"unsupported year: {year}")

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "_work"
    funding_dir = output_dir / "funding_rate_raw_zips"
    work_dir.mkdir(parents=True, exist_ok=True)
    funding_dir.mkdir(parents=True, exist_ok=True)

    merged_path = output_dir / f"{SYMBOL}_USD_M_PERP_1m_{year}.csv.gz"
    monthly_manifest_path = output_dir / f"monthly_manifest_{year}.csv"
    audit_path = output_dir / f"audit_manifest_{year}.json"

    rows = 0
    first_open_ms: int | None = None
    last_open_ms: int | None = None
    duplicate_timestamps = 0
    non_ascending_timestamps = 0
    gap_count = 0
    max_gap_minutes = 0
    min_price: float | None = None
    max_price: float | None = None
    total_base_volume = 0.0
    total_quote_volume = 0.0
    total_trades = 0
    total_taker_buy_base = 0.0
    monthly_records: list[dict[str, object]] = []
    funding_records: list[dict[str, object]] = []

    with gzip.open(merged_path, "wt", encoding="utf-8", newline="", compresslevel=6) as gz:
        writer = csv.writer(gz)
        writer.writerow(KLINE_HEADER)

        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            filename = f"{SYMBOL}-{INTERVAL}-{ym}.zip"
            zip_url = f"{BASE_URL}/klines/{SYMBOL}/{INTERVAL}/{filename}"
            checksum_url = f"{zip_url}.CHECKSUM"
            zip_path = work_dir / filename
            checksum_path = work_dir / f"{filename}.CHECKSUM"

            print(f"[kline] downloading {ym}", flush=True)
            download(zip_url, zip_path, required=True)
            download(checksum_url, checksum_path, required=True)
            expected_sha = parse_checksum(checksum_path)
            actual_sha = sha256_file(zip_path)
            if actual_sha != expected_sha:
                raise RuntimeError(
                    f"checksum mismatch for {filename}: expected {expected_sha}, actual {actual_sha}"
                )

            month_rows = 0
            month_first: int | None = None
            month_last: int | None = None
            with zipfile.ZipFile(zip_path) as archive:
                csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(csv_names) != 1:
                    raise RuntimeError(f"expected one CSV in {filename}, found {csv_names}")
                with archive.open(csv_names[0], "r") as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                    reader = csv.reader(text)
                    for row in reader:
                        if not row:
                            continue
                        if not is_numeric_timestamp(row[0]):
                            # Some newer archives contain a header. Preserve one canonical header only.
                            continue
                        if len(row) < 12:
                            raise RuntimeError(f"short kline row in {filename}: {row}")
                        row = row[:12]
                        open_ms = int(row[0])
                        if open_ms > 10_000_000_000_000:  # defensive microsecond normalization
                            open_ms //= 1000
                            row[0] = str(open_ms)
                            close_ms = int(row[6]) // 1000
                            row[6] = str(close_ms)

                        if last_open_ms is not None:
                            delta = open_ms - last_open_ms
                            if delta == 0:
                                duplicate_timestamps += 1
                            elif delta < 0:
                                non_ascending_timestamps += 1
                            elif delta > 60_000:
                                gap_count += 1
                                max_gap_minutes = max(max_gap_minutes, delta // 60_000 - 1)
                        if first_open_ms is None:
                            first_open_ms = open_ms
                        last_open_ms = open_ms
                        if month_first is None:
                            month_first = open_ms
                        month_last = open_ms

                        low = float(row[3])
                        high = float(row[2])
                        min_price = low if min_price is None else min(min_price, low)
                        max_price = high if max_price is None else max(max_price, high)
                        total_base_volume += float(row[5])
                        total_quote_volume += float(row[7])
                        total_trades += int(float(row[8]))
                        total_taker_buy_base += float(row[9])

                        writer.writerow(row)
                        rows += 1
                        month_rows += 1

            monthly_records.append(
                {
                    "month": ym,
                    "rows": month_rows,
                    "first_open_utc": utc_iso(month_first),
                    "last_open_utc": utc_iso(month_last),
                    "archive_sha256": actual_sha,
                    "checksum_verified": True,
                    "source_url": zip_url,
                }
            )
            zip_path.unlink(missing_ok=True)
            checksum_path.unlink(missing_ok=True)

            funding_name = f"{SYMBOL}-fundingRate-{ym}.zip"
            funding_url = f"{BASE_URL}/fundingRate/{SYMBOL}/{funding_name}"
            funding_checksum_url = f"{funding_url}.CHECKSUM"
            funding_zip = funding_dir / funding_name
            funding_checksum = funding_dir / f"{funding_name}.CHECKSUM"
            funding_available = download(funding_url, funding_zip, required=False)
            funding_verified = False
            funding_sha: str | None = None
            if funding_available:
                checksum_available = download(funding_checksum_url, funding_checksum, required=False)
                funding_sha = sha256_file(funding_zip)
                if checksum_available:
                    expected_funding_sha = parse_checksum(funding_checksum)
                    if funding_sha != expected_funding_sha:
                        raise RuntimeError(
                            f"funding checksum mismatch for {funding_name}: "
                            f"expected {expected_funding_sha}, actual {funding_sha}"
                        )
                    funding_verified = True
            funding_records.append(
                {
                    "month": ym,
                    "available": funding_available,
                    "checksum_verified": funding_verified,
                    "archive_sha256": funding_sha,
                    "source_url": funding_url,
                }
            )

    with monthly_manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(monthly_records[0].keys()))
        writer.writeheader()
        writer.writerows(monthly_records)

    merged_sha = sha256_file(merged_path)
    expected_minutes = int(
        (
            dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
            - dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        ).total_seconds()
        // 60
    )
    coverage = rows / expected_minutes if expected_minutes else 0.0
    audit = {
        "research_track": "BTC_AI_V1_EXTERNAL_VALIDATION",
        "source": "Binance public data archive",
        "market": "USD-M perpetual futures",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "calendar_year": year,
        "time_semantics": "UTC",
        "rows": rows,
        "expected_calendar_minutes": expected_minutes,
        "calendar_minute_coverage": coverage,
        "first_open_time_ms": first_open_ms,
        "first_open_utc": utc_iso(first_open_ms),
        "last_open_time_ms": last_open_ms,
        "last_open_utc": utc_iso(last_open_ms),
        "duplicate_timestamps": duplicate_timestamps,
        "non_ascending_timestamps": non_ascending_timestamps,
        "gap_count": gap_count,
        "max_missing_minutes_between_rows": max_gap_minutes,
        "min_price": min_price,
        "max_price": max_price,
        "total_base_volume": total_base_volume,
        "total_quote_volume": total_quote_volume,
        "total_trades": total_trades,
        "total_taker_buy_base_volume": total_taker_buy_base,
        "taker_buy_base_share": (
            total_taker_buy_base / total_base_volume if total_base_volume > 0 else None
        ),
        "merged_file": merged_path.name,
        "merged_file_sha256": merged_sha,
        "monthly_kline_archives": monthly_records,
        "monthly_funding_archives": funding_records,
        "research_use": "independent external validation and causal feature research only",
        "xm_btcusd_source_modified": False,
        "trading_authorized": False,
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    if duplicate_timestamps or non_ascending_timestamps:
        raise RuntimeError(
            f"timestamp integrity failure: duplicates={duplicate_timestamps}, "
            f"non_ascending={non_ascending_timestamps}"
        )
    print(json.dumps(audit, indent=2, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        process_year(args.year, args.output_dir)
    except Exception as exc:  # noqa: BLE001 - fail closed with visible reason
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
