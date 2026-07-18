from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "mochipoyo_alert_research" / "mt5_csv_contract.py"
spec = importlib.util.spec_from_file_location("mt5_csv_contract", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(module.EXPECTED_HEADER)
        writer.writerows(rows)


def test_inventory_and_offset_scoring(tmp_path: Path) -> None:
    csv_path = tmp_path / "goldsharp_m1.csv"
    start = datetime(2026, 7, 15, 12, 0)
    rows = []
    for index in range(10):
        timestamp = start + timedelta(minutes=index)
        price = 4000.0 + index
        rows.append([
            timestamp.strftime(module.TIME_FORMAT), price, price + 0.5,
            price - 0.5, price + 0.1, 10, 20, 0,
        ])
    write_csv(csv_path, rows)
    inventory = module.inspect_csv(csv_path, ticker="XAUUSD", timeframe="M1")
    assert inventory.row_count == 10
    assert inventory.strictly_ascending is True
    assert inventory.expected_cadence_ratio == 1.0

    bars = module.load_m1_bars(csv_path)
    alerts = [
        {
            "ticker": "XAUUSD",
            "fired_at_utc": f"2026-07-15T09:0{i}:00Z",
            "close_price": 4000.1 + i,
        }
        for i in range(6)
    ]
    scores = module.score_offsets(alerts, {"XAUUSD": bars}, candidate_offsets=[2, 3, 4])
    assert scores[0]["offset_hours"] == 3
    selected = module.provisional_offset(scores)
    assert selected["status"] == "PROVISIONAL"
    assert selected["offset_hours"] == 3


def test_provisional_offset_refuses_small_sample() -> None:
    scores = [{
        "offset_hours": 3,
        "matched_m1_count": 2,
        "price_range_hit_count": 2,
        "price_range_hit_ratio": 1.0,
        "median_range_distance_bps": 0.0,
        "median_close_distance_bps": 0.1,
    }]
    result = module.provisional_offset(scores)
    assert result["status"] == "INSUFFICIENT_SAMPLE"
    assert result["offset_hours"] is None
