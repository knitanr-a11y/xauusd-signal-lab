from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

RAW = "RAW_RECONSTRUCTED"
BRIDGE = "WARMUP_BRIDGE_EXACT"
POINT = 0.01
TIME_COLS = ("decision_close_time", "entry_time", "exit_time")
CORE_REGISTRY_COLS = {
    "candidate_id",
    "decision_close_time",
    "entry_time",
    "exit_time",
    "r_value",
    "direction",
    "trade_core_source",
}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    spread_multiplier: float
    slippage_points_per_side: int


@dataclass(frozen=True)
class Lineage:
    lineage_id: str
    horizon_minutes: int
    stored_exit_time: str
    direction: str


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def backup_output(path: Path) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not any(path.iterdir()):
        path.mkdir(parents=True, exist_ok=True)
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.parent / f"{path.name}_previous_{stamp}"
    number = 1
    while backup.exists():
        backup = path.parent / f"{path.name}_previous_{stamp}_{number}"
        number += 1
    shutil.move(str(path), str(backup))
    path.mkdir(parents=True, exist_ok=True)
    return backup


def make_scenario_id(spread: float, slip: int) -> str:
    return f"SPREAD_{spread:.1f}X_SLIP_{slip}PTS".replace(".", "_")


def scenarios_from(config: dict[str, Any]) -> list[Scenario]:
    grid = config["scenario_grid"]
    if grid.get("grid_type") != "FULL_CARTESIAN_PRODUCT":
        raise ValueError("Scenario grid must be FULL_CARTESIAN_PRODUCT")
    spreads = [float(value) for value in grid["spread_multipliers"]]
    slips = [int(value) for value in grid["fixed_slippage_points_per_side"]]
    if spreads != sorted(set(spreads)) or slips != sorted(set(slips)):
        raise ValueError("Scenario values must be sorted and unique")
    if any(value < 1 for value in spreads) or any(value < 0 for value in slips):
        raise ValueError("Invalid spread/slippage grid")
    result = [Scenario(make_scenario_id(spread, slip), spread, slip) for spread in spreads for slip in slips]
    if grid["baseline_scenario_id"] not in {item.scenario_id for item in result}:
        raise ValueError("Baseline scenario is not in grid")
    return result


def validate_config(config: dict[str, Any]) -> tuple[list[str], dict[str, Lineage]]:
    if config.get("audit_only") is not True or config.get("new_exploration") is not False:
        raise ValueError("audit-only contract mismatch")
    if any(bool(value) for value in config["execution_switches"].values()):
        raise ValueError("All execution/promotion switches must remain false")
    pool = config["candidate_pool"]
    candidates = [str(value) for value in pool["frozen_accumulated_ids"]]
    if len(candidates) != 9 or len(set(candidates)) != 9:
        raise ValueError("Frozen pool must contain nine unique IDs")
    if pool.get("silent_add_remove_replace_relabel") != "forbidden":
        raise ValueError("Candidate mutation guard missing")
    population = config["population_contract"]
    if population.get("primary") != RAW or population.get("secondary_separate_only") != BRIDGE:
        raise ValueError("Population contract mismatch")
    if population.get("bridge_primary_population_use") != "forbidden":
        raise ValueError("Bridge primary use must be forbidden")

    mapping: dict[str, Lineage] = {}
    for lineage_id, item in config["lineages"].items():
        lineage = Lineage(
            str(lineage_id),
            int(item["horizon_minutes"]),
            str(item["stored_exit_time"]),
            str(item["direction"]),
        )
        if (
            lineage.horizon_minutes <= 0
            or lineage.stored_exit_time not in {"M1_BAR_OPEN", "M1_BAR_CLOSE"}
            or lineage.direction != "LONG"
        ):
            raise ValueError(f"Invalid lineage: {lineage_id}")
        for candidate_id in item["candidate_ids"]:
            candidate_id = str(candidate_id)
            if candidate_id in mapping:
                raise ValueError(f"Duplicate lineage membership: {candidate_id}")
            mapping[candidate_id] = lineage
    if set(mapping) != set(candidates):
        raise ValueError("Lineage IDs do not match frozen pool")
    if set(config["expected_provenance"]["candidate_source_counts"]) != set(candidates):
        raise ValueError("Expected count IDs mismatch")
    scenarios_from(config)
    return candidates, mapping


def verify_raw(raw_dir: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for filename, expected in config["expected_provenance"]["raw_sha256"].items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        match = actual == expected
        rows.append(
            {
                "filename": filename,
                "bytes": path.stat().st_size,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "sha256_match": match,
            }
        )
        if not match:
            raise RuntimeError(f"Raw SHA256 mismatch: {filename}")
    return rows


def verify_bridge(bridge_dir: Path, config: dict[str, Any], candidates: list[str]) -> dict[str, Any]:
    metadata_path = bridge_dir / "local_run_metadata.json"
    summary_path = bridge_dir / "warmup_bridge_summary.json"
    parity_path = bridge_dir / "warmup_bridge_parity_report.csv"
    metadata = load_json(metadata_path)
    summary = load_json(summary_path)
    if metadata.get("status") != "PASS" or int(metadata.get("exit_code", -1)) != 0:
        raise RuntimeError("Warmup bridge metadata is not PASS/0")
    expected_zip = config["expected_provenance"]["batch023_zip_sha256"]
    if metadata.get("batch023_zip_sha256") != expected_zip:
        raise RuntimeError("Batch023 ZIP provenance mismatch")
    raw_audit = metadata.get("raw_audit", [])
    if len(raw_audit) != 6 or not all(bool(item.get("sha256_match")) for item in raw_audit):
        raise RuntimeError("Warmup bridge raw hash audit mismatch")
    reports = {str(item["candidate_id"]): item for item in summary.get("reports", [])}
    if (
        summary.get("status") != "PASS"
        or set(reports) != set(candidates)
        or not all(bool(reports[candidate].get("pass")) for candidate in candidates)
    ):
        raise RuntimeError("Warmup bridge summary mismatch")
    parity = pd.read_csv(parity_path)
    if (
        set(parity["candidate_id"].astype(str)) != set(candidates)
        or not parity["pass"].astype(str).str.lower().isin({"true", "1"}).all()
    ):
        raise RuntimeError("Warmup bridge parity CSV mismatch")
    return {
        "metadata_file": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "summary_file": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "parity_file": str(parity_path),
        "parity_sha256": sha256_file(parity_path),
        "batch023_zip_sha256": expected_zip,
    }


def load_registries(
    bridge_dir: Path,
    config: dict[str, Any],
    candidates: list[str],
    lineage_by_candidate: dict[str, Lineage],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    expected = config["expected_provenance"]["candidate_source_counts"]
    frames: list[pd.DataFrame] = []
    audits: list[dict[str, Any]] = []
    for candidate_id in candidates:
        path = bridge_dir / f"{candidate_id}_warmup_bridge_core_registry.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        missing = sorted(CORE_REGISTRY_COLS - set(frame.columns))
        if missing:
            raise ValueError(f"{path.name} missing core columns: {missing}")
        for column in TIME_COLS:
            frame[column] = pd.to_datetime(frame[column], errors="raise")
        frame["candidate_id"] = frame["candidate_id"].astype(str)
        if set(frame["candidate_id"]) != {candidate_id} or frame["decision_close_time"].duplicated().any():
            raise RuntimeError(f"Registry identity/time mismatch: {candidate_id}")
        sources = set(frame["trade_core_source"].astype(str))
        if not sources.issubset({RAW, BRIDGE}) or set(frame["direction"].astype(str)) != {"LONG"}:
            raise RuntimeError(f"Registry source/direction mismatch: {candidate_id}")
        counts = frame["trade_core_source"].value_counts().to_dict()
        wanted_record = expected[candidate_id]
        actual = {
            RAW: int(counts.get(RAW, 0)),
            BRIDGE: int(counts.get(BRIDGE, 0)),
            "TOTAL": int(len(frame)),
        }
        wanted = {
            RAW: int(wanted_record[RAW]),
            BRIDGE: int(wanted_record[BRIDGE]),
            "TOTAL": int(wanted_record["TOTAL"]),
        }
        if actual != wanted:
            raise RuntimeError(f"Source-count mismatch {candidate_id}: {actual}")
        frame["lineage_id"] = lineage_by_candidate[candidate_id].lineage_id
        frames.append(frame)
        audits.append(
            {
                "candidate_id": candidate_id,
                "file": str(path),
                "sha256": sha256_file(path),
                "registry_contract": "WARMUP_BRIDGE_CORE",
                "raw_rows": actual[RAW],
                "bridge_rows": actual[BRIDGE],
                "total_rows": actual["TOTAL"],
            }
        )
    combined = pd.concat(frames, ignore_index=True)
    if set(combined["candidate_id"]) != set(candidates):
        raise RuntimeError("Combined registry candidate mismatch")
    return combined, audits
