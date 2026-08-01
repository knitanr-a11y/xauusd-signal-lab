from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.gold_uncovered_v1 import source_audit


HEADER = "time,open,high,low,close,tick_volume,spread,real_volume\n"


def write_candles(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "".join(rows), encoding="utf-8")


def candle(time: str, close: str = "100.5") -> str:
    return f"{time},100,101,99,{close},10,2,0\n"


def test_inspect_csv_accepts_valid_source(tmp_path: Path) -> None:
    path = tmp_path / "m1.csv"
    write_candles(
        path,
        [
            candle("2026.01.01 00:00:00"),
            candle("2026.01.01 00:01:00"),
        ],
    )
    report = source_audit.inspect_csv(path)
    assert report["schema_ok"]
    assert report["strictly_increasing"]
    assert report["rows"] == 2
    assert report["malformed_row_count"] == 0
    assert report["invalid_ohlc_row_count"] == 0


def test_inspect_csv_blocks_duplicate_time(tmp_path: Path) -> None:
    path = tmp_path / "m1.csv"
    write_candles(
        path,
        [
            candle("2026.01.01 00:00:00"),
            candle("2026.01.01 00:00:00"),
        ],
    )
    report = source_audit.inspect_csv(path)
    assert not report["strictly_increasing"]
    assert report["duplicate_time_count"] == 1


def test_overlap_detects_exact_and_mismatch(tmp_path: Path) -> None:
    old = tmp_path / "old.csv"
    sharp = tmp_path / "sharp.csv"
    write_candles(
        old,
        [
            candle("2026.01.01 00:00:00"),
            candle("2026.01.01 00:01:00"),
        ],
    )
    write_candles(
        sharp,
        [
            candle("2026.01.01 00:01:00"),
            candle("2026.01.01 00:02:00"),
        ],
    )
    exact = source_audit.compare_overlap(old, sharp)
    assert exact["exact_overlap"]
    assert exact["overlap_rows"] == 1

    write_candles(
        sharp,
        [
            candle("2026.01.01 00:01:00", close="100.6"),
            candle("2026.01.01 00:02:00"),
        ],
    )
    mismatch = source_audit.compare_overlap(old, sharp)
    assert not mismatch["exact_overlap"]
    assert mismatch["mismatch_rows"] == 1
    assert mismatch["first_mismatch"]["time"] == "2026-01-01 00:01:00"


def test_main_passes_complete_independent_source_set(tmp_path: Path, monkeypatch) -> None:
    search_root = tmp_path / "terminals"
    terminal = search_root / "ABC"
    historical_specs = {}
    sharp_specs = {}

    for timeframe in ("M1", "M5", "M15", "H1", "H4"):
        relative = Path("MQL5") / "Files" / "gold_v3_2023_2026" / f"gold_v3_2023_2026_{timeframe.lower()}.csv"
        path = terminal / relative
        rows = [
            candle("2026.01.01 00:00:00"),
            candle("2026.01.01 00:01:00"),
        ]
        write_candles(path, rows)
        inspection = source_audit.inspect_csv(path)
        historical_specs[timeframe] = {
            "relative_suffix": str(relative),
            "expected_sha256": inspection["sha256"],
            "expected_rows": 2,
            "expected_first_time": "2026-01-01 00:00:00",
            "expected_last_time": "2026-01-01 00:01:00",
        }

    for timeframe in ("M1", "M5", "H1", "H4"):
        filename = f"goldsharp_{timeframe.lower()}.csv"
        path = terminal / "MQL5" / "Files" / filename
        write_candles(
            path,
            [
                candle("2026.01.01 00:01:00"),
                candle("2026.01.01 00:02:00"),
            ],
        )
        sharp_specs[timeframe] = {"filename": filename}

    sharp_specs["M15"] = {"filename": "goldsharp_m15.csv", "required": False}
    historical_specs["D1"] = {
        "relative_suffix": str(Path("MQL5") / "Files" / "gold_v3_2023_2026" / "gold_v3_2023_2026_d1.csv"),
        "required": False,
    }
    sharp_specs["D1"] = {"filename": "goldsharp_d1.csv", "required": False}

    reference = {
        "search_root": str(search_root),
        "historical_sources": historical_specs,
        "sharp_sources": sharp_specs,
    }
    reference_path = tmp_path / "reference.json"
    output_path = tmp_path / "output.json"
    reference_path.write_text(json.dumps(reference), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "source_audit",
            "--reference",
            str(reference_path),
            "--output",
            str(output_path),
        ],
    )
    assert source_audit.main() == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["issues"] == []
    assert all(report["overlap_checks"][tf]["exact_overlap"] for tf in ("M1", "M5", "H1", "H4"))
