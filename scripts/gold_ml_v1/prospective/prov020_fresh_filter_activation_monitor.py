#!/usr/bin/env python3
"""Audit-only prospective monitor for GML1-PROV-020 filter activations.

The monitor consumes already-detected GML1-PROV-015 parent events and only
entry-time-known fields. It never reads exits, R, TP/SL outcomes, or future bars.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_PARENT_COLUMNS = ("decision_close_time", "h1_spread_price_div_atr14")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_column(columns: list[str], canonical: str, aliases: dict[str, list[str]]) -> str:
    accepted = [canonical, *aliases.get(canonical, [])]
    found = [name for name in accepted if name in columns]
    if len(found) != 1:
        raise ValueError(f"column resolution failed for {canonical}: found={found} accepted={accepted}")
    return found[0]


def parse_naive(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    if getattr(parsed.dt, "tz", None) is not None:
        raise ValueError(f"{name} must be naive MT5 server time")
    if parsed.isna().any():
        raise ValueError(f"{name} contains NaT")
    return parsed


def load_parent_events(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = pd.read_csv(path)
    aliases = config.get("column_aliases", {})
    resolution = {
        canonical: resolve_column(list(raw.columns), canonical, aliases)
        for canonical in REQUIRED_PARENT_COLUMNS
    }
    optional_hour = ["h1_decision_close_server_hour", *aliases.get("h1_decision_close_server_hour", [])]
    found_hour = [name for name in optional_hour if name in raw.columns]
    if len(found_hour) > 1:
        raise ValueError(f"ambiguous hour columns: {found_hour}")
    if found_hour:
        resolution["h1_decision_close_server_hour"] = found_hour[0]

    frame = pd.DataFrame(index=raw.index)
    frame["decision_close_time"] = parse_naive(raw[resolution["decision_close_time"]], "decision_close_time")
    frame["h1_spread_price_div_atr14"] = pd.to_numeric(
        raw[resolution["h1_spread_price_div_atr14"]], errors="raise"
    )
    if not np.isfinite(frame["h1_spread_price_div_atr14"].to_numpy(dtype=float)).all():
        raise ValueError("non-finite h1_spread_price_div_atr14")
    derived_hour = frame["decision_close_time"].dt.hour.astype(int)
    if "h1_decision_close_server_hour" in resolution:
        supplied_hour = pd.to_numeric(raw[resolution["h1_decision_close_server_hour"]], errors="raise").astype(int)
        if not supplied_hour.between(0, 23).all():
            raise ValueError("server hour outside 0..23")
        mismatch = supplied_hour.ne(derived_hour)
        if mismatch.any():
            sample = frame.loc[mismatch, "decision_close_time"].head(5).astype(str).tolist()
            raise ValueError(f"server-hour mismatch against decision timestamp: {sample}")
        frame["h1_decision_close_server_hour"] = supplied_hour
    else:
        frame["h1_decision_close_server_hour"] = derived_hour

    if frame["decision_close_time"].duplicated().any():
        sample = frame.loc[frame["decision_close_time"].duplicated(False), "decision_close_time"].head(10).tolist()
        raise ValueError(f"duplicate parent decision_close_time: {sample}")
    if not frame["decision_close_time"].is_monotonic_increasing:
        raise ValueError("parent events are not ordered by decision_close_time")
    return frame, resolution


def classify_events(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cutoff = pd.Timestamp(config["fresh_cutoff_mt5_server_close"])
    work = frame.loc[frame["decision_close_time"] > cutoff].copy()
    hour_rule = config["filter_conditions"][0]
    spread_rule = config["filter_conditions"][1]
    lo, hi = int(hour_rule["lower"]), int(hour_rule["upper"])
    threshold = float(spread_rule["threshold"])
    work["hour_condition"] = work["h1_decision_close_server_hour"].between(lo, hi)
    work["spread_condition"] = work["h1_spread_price_div_atr14"] >= threshold
    work["filter_activation"] = work["hour_condition"] & work["spread_condition"]
    work["prov020_expected_emit"] = ~work["filter_activation"]
    work["parent_candidate_id"] = config["parent_candidate_id"]
    work["child_candidate_id"] = config["candidate_id"]
    return work[
        [
            "parent_candidate_id",
            "child_candidate_id",
            "decision_close_time",
            "h1_decision_close_server_hour",
            "h1_spread_price_div_atr14",
            "hour_condition",
            "spread_condition",
            "filter_activation",
            "prov020_expected_emit",
        ]
    ]


def row_to_record(row: pd.Series) -> dict[str, Any]:
    return {
        "parent_candidate_id": str(row["parent_candidate_id"]),
        "child_candidate_id": str(row["child_candidate_id"]),
        "decision_close_time": pd.Timestamp(row["decision_close_time"]).strftime("%Y-%m-%d %H:%M:%S"),
        "h1_decision_close_server_hour": int(row["h1_decision_close_server_hour"]),
        "h1_spread_price_div_atr14": float(row["h1_spread_price_div_atr14"]),
        "hour_condition": bool(row["hour_condition"]),
        "spread_condition": bool(row["spread_condition"]),
        "filter_activation": bool(row["filter_activation"]),
        "prov020_expected_emit": bool(row["prov020_expected_emit"]),
    }


def load_ledger(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = record["decision_close_time"]
            if key in records:
                raise ValueError(f"duplicate ledger key {key} at line {line_number}")
            records[key] = record
    return records


def append_immutable(path: Path, classified: pd.DataFrame) -> tuple[int, int]:
    existing = load_ledger(path)
    to_append: list[dict[str, Any]] = []
    unchanged = 0
    for _, row in classified.iterrows():
        record = row_to_record(row)
        key = record["decision_close_time"]
        if key in existing:
            if existing[key] != record:
                raise ValueError(f"immutable prospective ledger conflict at {key}")
            unchanged += 1
        else:
            to_append.append(record)
    if to_append:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for record in to_append:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return len(to_append), unchanged


def build_summary(
    config: dict[str, Any],
    source: Path,
    classified: pd.DataFrame,
    appended: int,
    unchanged: int,
    ledger_path: Path,
    resolution: dict[str, str],
) -> dict[str, Any]:
    activated = classified[classified["filter_activation"]]
    retained = classified[classified["prov020_expected_emit"]]
    return {
        "monitor_id": config["monitor_id"],
        "status": "AUDIT_ONLY_FRESH_FILTER_ACTIVATION_OBSERVED"
        if len(activated)
        else "AUDIT_ONLY_NO_FRESH_FILTER_ACTIVATION_YET",
        "audit_only": True,
        "candidate_logic_changed": False,
        "candidate_id": config["candidate_id"],
        "parent_candidate_id": config["parent_candidate_id"],
        "fresh_cutoff_mt5_server_close": config["fresh_cutoff_mt5_server_close"],
        "fresh_parent_events": int(len(classified)),
        "fresh_filter_activations": int(len(activated)),
        "fresh_expected_prov020_emits": int(len(retained)),
        "first_activation": None if activated.empty else str(activated["decision_close_time"].min()),
        "last_activation": None if activated.empty else str(activated["decision_close_time"].max()),
        "new_ledger_records": appended,
        "unchanged_existing_records": unchanged,
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "source_column_resolution": resolution,
        "used_entry_time_known_columns_only": [
            "decision_close_time",
            "h1_decision_close_server_hour",
            "h1_spread_price_div_atr14",
        ],
        "forbidden_future_outcome_columns_used": [],
        "ledger_path": str(ledger_path),
        "ledger_sha256": sha256_file(ledger_path) if ledger_path.exists() else None,
        "filter_conditions": config["filter_conditions"],
        "boundaries": config["boundaries"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/gold_ml_v1/prov020_fresh_filter_activation_monitor_20260624.json"),
    )
    parser.add_argument("--parent-events", type=Path, required=True)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("FX_OUTPUTS/gold_ml_v1/prospective/GML1-PROV-020/filter_activation_ledger.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("FX_OUTPUTS/gold_ml_v1/prospective/GML1-PROV-020/filter_activation_summary.json"),
    )
    return parser


def run(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    if config.get("audit_only") is not True:
        raise ValueError("audit_only=true is required")
    if any(config["boundaries"].get(name) is not False for name in ("live_signal", "mt5_order", "discord")):
        raise ValueError("all execution boundaries must remain false")
    parent, resolution = load_parent_events(args.parent_events, config)
    classified = classify_events(parent, config)
    appended, unchanged = append_immutable(args.ledger, classified)
    summary = build_summary(
        config,
        args.parent_events,
        classified,
        appended,
        unchanged,
        args.ledger,
        resolution,
    )
    dump_json(args.summary, summary)
    print(json.dumps({"status": summary["status"], "fresh_filter_activations": summary["fresh_filter_activations"]}))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
