#!/usr/bin/env python3
"""Probe official Binance derivatives archive paths without downloading full datasets."""
from __future__ import annotations
import json
from pathlib import Path
import urllib.error
import urllib.request

URLS = {
    "mark_2020_01": "https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip",
    "mark_2022_12": "https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2022-12.zip",
    "premium_2020_01": "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip",
    "premium_2022_12": "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1m/BTCUSDT-1m-2022-12.zip",
    "index_2020_01": "https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip",
    "index_2022_12": "https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2022-12.zip",
    "metrics_2020_01_01": "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-01-01.zip",
    "metrics_2021_01_01": "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2021-01-01.zip",
    "metrics_2022_01_01": "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2022-01-01.zip",
    "book_depth_2022_01_01": "https://data.binance.vision/data/futures/um/daily/bookDepth/BTCUSDT/BTCUSDT-bookDepth-2022-01-01.zip",
    "liquidation_2022_01_01": "https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2022-01-01.zip"
}


def probe(url: str) -> dict[str, object]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "btc-ai-v1-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return {
                "available": response.status == 200,
                "status": response.status,
                "content_length": response.headers.get("Content-Length"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified")
            }
    except urllib.error.HTTPError as exc:
        return {"available": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "status": None, "error": repr(exc)}


def main() -> None:
    result = {name: {"url": url, **probe(url)} for name, url in URLS.items()}
    Path("artifacts/binance_derivatives_archive_probe").mkdir(parents=True, exist_ok=True)
    out = Path("artifacts/binance_derivatives_archive_probe/probe_result.json")
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
