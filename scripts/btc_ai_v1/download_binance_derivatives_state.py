#!/usr/bin/env python3
"""Download checksum-verified Binance derivatives-state archives.

Supported datasets:
- markPriceKlines, premiumIndexKlines, indexPriceKlines: monthly BTCUSDT 1m
- metrics: daily BTCUSDT metrics

The script preserves the source rows, merges one calendar year into gzip CSV and
writes a source/audit manifest. It does not calculate signals or PnL.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
KLINE_DATASETS = {"markPriceKlines", "premiumIndexKlines", "indexPriceKlines"}
KLINE_HEADER = ["open_time_ms","open","high","low","close","volume","close_time_ms","quote_volume","trades","taker_buy_base_volume","taker_buy_quote_volume","ignore"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, path: Path, required: bool = True) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "btc-ai-v1-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, path.open("wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
        return True
    except urllib.error.HTTPError as exc:
        if not required and exc.code == 404:
            return False
        raise RuntimeError(f"download failed {url}: HTTP {exc.code}") from exc


def expected_checksum(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip().split()[0].lower()
    if len(token) != 64:
        raise RuntimeError(f"invalid checksum file {path}")
    return token


def source_files(dataset: str, year: int):
    if dataset in KLINE_DATASETS:
        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            filename = f"{SYMBOL}-1m-{ym}.zip"
            url = f"{BASE}/monthly/{dataset}/{SYMBOL}/1m/{filename}"
            yield ym, filename, url
    elif dataset == "metrics":
        day = dt.date(year, 1, 1)
        end = dt.date(year + 1, 1, 1)
        while day < end:
            ymd = day.isoformat()
            filename = f"{SYMBOL}-metrics-{ymd}.zip"
            url = f"{BASE}/daily/metrics/{SYMBOL}/{filename}"
            yield ymd, filename, url
            day += dt.timedelta(days=1)
    else:
        raise ValueError(dataset)


def normalize_kline(row: list[str]) -> list[str] | None:
    if not row:
        return None
    try:
        ts = int(row[0])
    except ValueError:
        return None
    if ts > 10_000_000_000_000:
        row[0] = str(ts // 1000)
        row[6] = str(int(row[6]) // 1000)
    return row[:12]


def process(dataset: str, year: int, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    work = output_dir / "_work"
    work.mkdir(exist_ok=True)
    merged = output_dir / f"{SYMBOL}_{dataset}_{year}.csv.gz"
    manifest_rows = []
    total_rows = 0
    source_header: list[str] | None = None
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    missing_archives = []

    with gzip.open(merged, "wt", encoding="utf-8", newline="", compresslevel=6) as gz:
        writer = csv.writer(gz)
        header_written = False
        for period, filename, url in source_files(dataset, year):
            zip_path = work / filename
            chk_path = work / f"{filename}.CHECKSUM"
            available = download(url, zip_path, required=False)
            if not available:
                missing_archives.append(period)
                manifest_rows.append({"period": period, "available": False, "rows": 0, "source_url": url})
                continue
            if not download(url + ".CHECKSUM", chk_path, required=False):
                raise RuntimeError(f"checksum file unavailable for {url}")
            actual = sha256(zip_path)
            expected = expected_checksum(chk_path)
            if actual != expected:
                raise RuntimeError(f"checksum mismatch {filename}: {actual} != {expected}")
            rows_this = 0
            with zipfile.ZipFile(zip_path) as archive:
                names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
                if len(names) != 1:
                    raise RuntimeError(f"expected one CSV in {filename}: {names}")
                with archive.open(names[0]) as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
                    for row in reader:
                        if dataset in KLINE_DATASETS:
                            normalized = normalize_kline(row)
                            if normalized is None:
                                continue
                            if not header_written:
                                writer.writerow(KLINE_HEADER)
                                source_header = KLINE_HEADER
                                header_written = True
                            out_row = normalized
                            timestamp = out_row[0]
                        else:
                            if not row:
                                continue
                            is_header = any(ch.isalpha() for ch in row[0]) or row[0].lower() in {"create_time", "symbol"}
                            if source_header is None:
                                if not is_header:
                                    raise RuntimeError(f"metrics first row lacks header in {filename}: {row}")
                                source_header = row
                                writer.writerow(source_header)
                                header_written = True
                                continue
                            if is_header:
                                if row != source_header:
                                    raise RuntimeError(f"metrics schema changed in {filename}: {row} != {source_header}")
                                continue
                            if len(row) != len(source_header):
                                raise RuntimeError(f"metrics row width changed in {filename}: {len(row)} != {len(source_header)}")
                            out_row = row
                            timestamp = row[0]
                        if first_timestamp is None:
                            first_timestamp = timestamp
                        last_timestamp = timestamp
                        writer.writerow(out_row)
                        rows_this += 1
                        total_rows += 1
            manifest_rows.append({"period": period, "available": True, "rows": rows_this, "archive_sha256": actual, "checksum_verified": True, "source_url": url})
            zip_path.unlink(missing_ok=True)
            chk_path.unlink(missing_ok=True)

    manifest = {
        "dataset": dataset,
        "symbol": SYMBOL,
        "year": year,
        "time_semantics": "UTC",
        "source": "official Binance public archive",
        "rows": total_rows,
        "header": source_header,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "missing_archives": missing_archives,
        "merged_file": merged.name,
        "merged_file_sha256": sha256(merged),
        "archives": manifest_rows,
        "research_only": True,
        "trading_authorized": False
    }
    (output_dir / f"manifest_{dataset}_{year}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", choices=sorted(KLINE_DATASETS | {"metrics"}), required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    try:
        process(a.dataset, a.year, a.output_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
