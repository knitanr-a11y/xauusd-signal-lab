from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.gold_shadow_operational_research_v1.collect_operational_snapshot import collect


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_read_only_collection_and_overlap(tmp_path: Path) -> None:
    v19 = tmp_path / "v19"
    c1 = tmp_path / "c1"
    p75 = tmp_path / "p75"
    for root in (v19, c1, p75):
        root.mkdir()
        (root / "runtime_state.json").write_text(json.dumps({"formal_status": "RUNNING", "cursor": "2026-08-01 10:00:00"}), encoding="utf-8")
    write_csv(v19 / "shadow_trade_ledger.csv", [{"trade_id": "v1", "entry_dt": "2026-08-01 10:00:00", "exit_dt": "2026-08-01 11:00:00", "side": "LONG", "pnl": 20}])
    write_csv(c1 / "shadow_trade_ledger.csv", [{"trade_id": "c1", "entry_dt": "2026-08-01 10:10:00", "exit_dt": "2026-08-01 10:40:00", "side": "SHORT", "pnl": -10}])
    write_csv(p75 / "trade_results.csv", [{"trade_id": "p1", "entry_time": "2026-08-01 12:00:00", "exit_time": "2026-08-01 12:30:00", "direction": "LONG", "net_usd": 6.25}])
    for root, name, when, side in (
        (v19, "entry_events.csv", "2026-08-01 10:00:00", "LONG"),
        (c1, "entry_events.csv", "2026-08-01 10:10:00", "SHORT"),
        (p75, "entry_events.csv", "2026-08-01 12:00:00", "LONG"),
    ):
        write_csv(root / name, [{"trade_id": root.name, "entry_time": when, "side": side}])

    config = {
        "research_id": "GOLD_SHADOW_OPERATIONAL_RESEARCH_V1",
        "contract_version": "2026-08-03-v1",
        "output_root": str(tmp_path / "output"),
        "systems": [
            {"system_id": "V19", "state_root": str(v19), "required": True},
            {"system_id": "CHALLENGER_C1", "state_root": str(c1), "required": False},
            {"system_id": "P75_STATE_SURVIVAL", "state_root": str(p75), "required": True},
        ],
        "freshness_warning_minutes": 999999,
        "proximity_windows_minutes": [0, 15, 60],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for root in (v19, c1, p75) for path in root.iterdir()}
    summary = collect(config_path)
    after = {path: (path.stat().st_size, path.stat().st_mtime_ns) for root in (v19, c1, p75) for path in root.iterdir()}
    assert before == after
    assert summary["source_integrity_atomic"] is True
    assert summary["normalized_entry_rows"] == 3
    assert summary["normalized_trade_rows"] == 3
    assert summary["naive_combined_metrics"]["net_usd"] == 16.25
    overlap_path = Path(summary["snapshot_dir"]) / "pairwise_overlap.csv"
    rows = list(csv.DictReader(overlap_path.open(encoding="utf-8")))
    row = next(item for item in rows if item["left_system"] == "CHALLENGER_C1" and item["right_system"] == "V19" and item["overlap_type"] == "ENTRY_WITHIN_15M")
    assert row["count"] == "1"
    assert row["opposite_side"] == "1"


def test_missing_optional_system_is_not_zero_performance(tmp_path: Path) -> None:
    root = tmp_path / "v19"
    root.mkdir()
    (root / "runtime_state.json").write_text(json.dumps({"status": "RUNNING"}), encoding="utf-8")
    config = {
        "research_id": "GOLD_SHADOW_OPERATIONAL_RESEARCH_V1",
        "contract_version": "2026-08-03-v1",
        "output_root": str(tmp_path / "output"),
        "systems": [
            {"system_id": "V19", "state_root": str(root), "required": True},
            {"system_id": "CHALLENGER_C1", "state_root": str(tmp_path / "missing"), "required": False},
        ],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    summary = collect(config_path)
    c1 = next(item for item in summary["systems"] if item["system_id"] == "CHALLENGER_C1")
    assert c1["availability"] == "NOT_AVAILABLE"
    assert "CHALLENGER_C1" in summary["per_system_metrics"]
    assert summary["per_system_metrics"]["CHALLENGER_C1"]["availability"] == "NOT_AVAILABLE"
    assert summary["per_system_metrics"]["CHALLENGER_C1"]["resolved_trades"] is None
