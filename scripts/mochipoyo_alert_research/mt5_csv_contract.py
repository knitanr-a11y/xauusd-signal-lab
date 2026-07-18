from __future__ import annotations

import csv
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

EXPECTED_HEADER = [
    "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"
]
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
FILE_MAP = {
    "XAUUSD": {
        "M1": "goldsharp_m1.csv",
        "M5": "goldsharp_m5.csv",
        "M15": "goldsharp_m15.csv",
        "H1": "goldsharp_h1.csv",
        "H4": "goldsharp_h4.csv",
        "D1": "goldsharp_d1.csv",
    },
    "BTCUSD": {
        "M1": "btcusdsharp_m1.csv",
        "M5": "btcusdsharp_m5.csv",
        "M15": "btcusdsharp_m15.csv",
        "H1": "btcusdsharp_h1.csv",
        "H4": "btcusdsharp_h4.csv",
        "D1": "btcusdsharp_d1.csv",
    },
}
EXPECTED_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}
TIMEFRAME_SECONDS = EXPECTED_SECONDS.copy()


class CsvContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class CsvInventory:
    ticker: str
    timeframe: str
    filename: str
    path_length: int
    byte_size: int
    row_count: int
    first_time: str
    last_time: str
    strictly_ascending: bool
    expected_cadence_seconds: int
    expected_cadence_count: int
    positive_delta_count: int
    expected_cadence_ratio: float
    common_positive_deltas: list[dict[str, Any]]


def parse_mt5_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def parse_utc(text: str) -> datetime:
    value = text.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def inspect_csv(path: Path, *, ticker: str, timeframe: str) -> CsvInventory:
    if not path.is_file():
        raise CsvContractError(f"missing MT5 CSV: {path.name}")
    count = 0
    first: datetime | None = None
    last: datetime | None = None
    previous: datetime | None = None
    strictly_ascending = True
    deltas: Counter[int] = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise CsvContractError(
                f"unexpected header for {path.name}: {reader.fieldnames!r}"
            )
        for row_index, row in enumerate(reader, start=2):
            count += 1
            try:
                current = parse_mt5_time(row["time"])
                for key in ("open", "high", "low", "close"):
                    float(row[key])
                int(row["tick_volume"])
                int(row["spread"])
                int(row["real_volume"])
            except Exception as exc:
                raise CsvContractError(
                    f"invalid row in {path.name} at CSV line {row_index}"
                ) from exc
            if first is None:
                first = current
            if previous is not None:
                delta = int((current - previous).total_seconds())
                if delta <= 0:
                    strictly_ascending = False
                else:
                    deltas[delta] += 1
            previous = current
            last = current
    if count == 0 or first is None or last is None:
        raise CsvContractError(f"CSV has no data rows: {path.name}")
    expected = EXPECTED_SECONDS[timeframe]
    positive_total = sum(deltas.values())
    expected_count = deltas.get(expected, 0)
    common = [
        {"seconds": seconds, "count": hits}
        for seconds, hits in deltas.most_common(5)
    ]
    return CsvInventory(
        ticker=ticker,
        timeframe=timeframe,
        filename=path.name,
        path_length=len(str(path)),
        byte_size=path.stat().st_size,
        row_count=count,
        first_time=first.strftime(TIME_FORMAT),
        last_time=last.strftime(TIME_FORMAT),
        strictly_ascending=strictly_ascending,
        expected_cadence_seconds=expected,
        expected_cadence_count=expected_count,
        positive_delta_count=positive_total,
        expected_cadence_ratio=(expected_count / positive_total if positive_total else 1.0),
        common_positive_deltas=common,
    )


def load_m1_bars(path: Path) -> dict[datetime, tuple[float, float, float, float]]:
    bars: dict[datetime, tuple[float, float, float, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise CsvContractError(f"unexpected header for {path.name}")
        for row in reader:
            timestamp = parse_mt5_time(row["time"])
            if timestamp in bars:
                raise CsvContractError(f"duplicate M1 timestamp in {path.name}: {row['time']}")
            bars[timestamp] = (
                float(row["open"]), float(row["high"]),
                float(row["low"]), float(row["close"]),
            )
    return bars


def distance_bps(price: float, low: float, high: float) -> float:
    if low <= price <= high:
        return 0.0
    distance = min(abs(price - low), abs(price - high))
    return distance / max(abs(price), 1e-12) * 10000.0


def score_offsets(
    alerts: Iterable[dict[str, Any]],
    m1_by_ticker: dict[str, dict[datetime, tuple[float, float, float, float]]],
    *,
    candidate_offsets: Iterable[int] = range(-1, 6),
    hit_tolerance_bps: float = 1.0,
) -> list[dict[str, Any]]:
    alert_list = [row for row in alerts if row.get("ticker") in m1_by_ticker and row.get("close_price") is not None]
    scores: list[dict[str, Any]] = []
    for offset in candidate_offsets:
        distances: list[float] = []
        close_distances: list[float] = []
        missing = 0
        hits = 0
        per_ticker = Counter()
        per_ticker_hits = Counter()
        for alert in alert_list:
            ticker = str(alert["ticker"])
            event_time = parse_utc(str(alert["fired_at_utc"])).replace(second=0, microsecond=0)
            server_time = event_time + timedelta(hours=offset)
            bar = m1_by_ticker[ticker].get(server_time)
            if bar is None:
                missing += 1
                continue
            _, high, low, close = bar
            price = float(alert["close_price"])
            d_bps = distance_bps(price, low, high)
            c_bps = abs(price - close) / max(abs(price), 1e-12) * 10000.0
            distances.append(d_bps)
            close_distances.append(c_bps)
            per_ticker[ticker] += 1
            if d_bps <= hit_tolerance_bps:
                hits += 1
                per_ticker_hits[ticker] += 1
        matched = len(distances)
        scores.append({
            "offset_hours": offset,
            "alert_count": len(alert_list),
            "matched_m1_count": matched,
            "missing_m1_count": missing,
            "price_range_hit_count": hits,
            "price_range_hit_ratio": (hits / matched if matched else 0.0),
            "median_range_distance_bps": (statistics.median(distances) if distances else None),
            "mean_range_distance_bps": (statistics.fmean(distances) if distances else None),
            "median_close_distance_bps": (statistics.median(close_distances) if close_distances else None),
            "by_ticker": [
                {
                    "ticker": ticker,
                    "matched_m1_count": per_ticker[ticker],
                    "price_range_hit_count": per_ticker_hits[ticker],
                    "price_range_hit_ratio": (
                        per_ticker_hits[ticker] / per_ticker[ticker]
                        if per_ticker[ticker] else 0.0
                    ),
                }
                for ticker in sorted(m1_by_ticker)
            ],
        })
    return sorted(
        scores,
        key=lambda row: (
            -float(row["price_range_hit_ratio"]),
            float("inf") if row["median_range_distance_bps"] is None else float(row["median_range_distance_bps"]),
            float("inf") if row["median_close_distance_bps"] is None else float(row["median_close_distance_bps"]),
        ),
    )


def provisional_offset(scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not scores:
        return {"status": "UNAVAILABLE", "offset_hours": None, "reason": "no scores"}
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None
    matched = int(best["matched_m1_count"])
    ratio = float(best["price_range_hit_ratio"])
    best_hits = int(best["price_range_hit_count"])
    second_hits = int(second["price_range_hit_count"]) if second else -1
    if matched < 5:
        return {
            "status": "INSUFFICIENT_SAMPLE",
            "offset_hours": None,
            "reason": f"only {matched} alerts matched M1 rows",
        }
    if ratio < 0.60:
        return {
            "status": "LOW_CONFIDENCE",
            "offset_hours": None,
            "reason": f"best price-range hit ratio is {ratio:.3f}",
        }
    if second is not None and best_hits <= second_hits:
        return {
            "status": "AMBIGUOUS",
            "offset_hours": None,
            "reason": "top two offsets have the same price-range hit count",
        }
    return {
        "status": "PROVISIONAL",
        "offset_hours": int(best["offset_hours"]),
        "reason": "best M1 price-range agreement; re-evaluate across DST periods",
        "matched_m1_count": matched,
        "price_range_hit_count": best_hits,
        "price_range_hit_ratio": ratio,
    }
