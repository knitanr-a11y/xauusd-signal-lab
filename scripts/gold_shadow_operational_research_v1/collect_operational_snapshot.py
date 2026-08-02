from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

RESEARCH_ID = "GOLD_SHADOW_OPERATIONAL_RESEARCH_V1"
CONTRACT_VERSION = "2026-08-03-v1"
TEXT_SUFFIXES = {".json", ".csv"}
TIME_KEYS_ENTRY = (
    "entry_dt", "entry_time", "entry_datetime", "accepted_entry_dt", "planned_entry_dt",
    "decision_dt", "decision_time", "signal_dt", "signal_time", "time", "timestamp",
)
TIME_KEYS_EXIT = (
    "exit_dt", "exit_time", "exit_datetime", "close_dt", "close_time", "resolved_at",
)
SIDE_KEYS = ("side", "direction", "chosen_side", "signal", "selected_side", "action")
ID_KEYS = ("trade_id", "entry_id", "candidate_key", "candidate_id", "origin_id", "id")
PNL_KEYS = ("net_usd", "pnl", "pnl_usd", "net_profit", "profit", "realized_pnl", "m1_net_usd")
STATUS_KEYS = ("formal_status", "runtime_status", "status", "stage")
CURSOR_KEYS = ("cursor", "last_processed_decision_time", "last_processed_time", "last_signal_time")


def expand_path(value: str, base: Path | None = None) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute() and base is not None:
        expanded = base / expanded
    return expanded.resolve()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value).strip().lower().replace("-", "_")).strip("_")


def normalize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {normalize_key(key): value for key, value in record.items()}


def first_present(record: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", "nan", "NaN", "NaT"):
            return value
    return None


def parse_time(value: Any) -> dt.datetime | None:
    if value in (None, "", "nan", "NaN", "NaT"):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    candidates = [text]
    if "T" not in text and " " in text:
        candidates.append(text.replace(" ", "T", 1))
    for candidate in candidates:
        try:
            result = dt.datetime.fromisoformat(candidate)
            return result.replace(tzinfo=None) if result.tzinfo else result
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def parse_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def file_snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def discover_files(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        lowered = str(path).lower()
        if "discord_charts" in lowered or "venv" in lowered:
            continue
        if "local_config" in path.name.lower() or "webhook" in path.name.lower():
            continue
        files.append(path)
    return sorted(files)


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [normalize_record(row) for row in csv.DictReader(handle)]


def flatten_json_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [normalize_record(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("records", "rows", "trades", "entries", "events", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [normalize_record(item) for item in nested if isinstance(item, dict)]
    return []


def classify_file(path: Path) -> set[str]:
    name = path.name.lower()
    categories: set[str] = set()
    if "discord" in name:
        categories.add("discord")
    if any(token in name for token in ("trade", "result", "resolved")):
        categories.add("trade")
    if any(token in name for token in ("entry", "candidate", "event")) and "discord" not in name:
        categories.add("entry")
    if any(token in name for token in ("state", "status", "summary", "report")):
        categories.add("state")
    return categories


def record_to_entry(system_id: str, source: Path, record: Mapping[str, Any], row_index: int) -> dict[str, Any] | None:
    entry_time = parse_time(first_present(record, TIME_KEYS_ENTRY))
    if entry_time is None:
        return None
    side = str(first_present(record, SIDE_KEYS) or "UNKNOWN").upper()
    trade_id = str(first_present(record, ID_KEYS) or f"{source.name}:{row_index}")
    return {
        "system_id": system_id,
        "trade_id": trade_id,
        "entry_time": entry_time.isoformat(sep=" "),
        "side": side,
        "source_file": source.name,
        "source_row": row_index,
    }


def record_to_trade(system_id: str, source: Path, record: Mapping[str, Any], row_index: int) -> dict[str, Any] | None:
    entry_time = parse_time(first_present(record, TIME_KEYS_ENTRY))
    exit_time = parse_time(first_present(record, TIME_KEYS_EXIT))
    if entry_time is None and exit_time is None:
        return None
    side = str(first_present(record, SIDE_KEYS) or "UNKNOWN").upper()
    trade_id = str(first_present(record, ID_KEYS) or f"{source.name}:{row_index}")
    pnl = parse_float(first_present(record, PNL_KEYS))
    return {
        "system_id": system_id,
        "trade_id": trade_id,
        "entry_time": entry_time.isoformat(sep=" ") if entry_time else "",
        "exit_time": exit_time.isoformat(sep=" ") if exit_time else "",
        "side": side,
        "pnl_usd": "" if pnl is None else pnl,
        "resolved": bool(exit_time is not None),
        "source_file": source.name,
        "source_row": row_index,
    }


def state_summary(files: list[Path]) -> dict[str, Any]:
    result: dict[str, Any] = {"status": None, "cursor": None, "state_files": []}
    for path in files:
        if path.suffix.lower() != ".json" or "state" not in classify_file(path):
            continue
        try:
            value = read_json(path)
        except Exception:
            continue
        if not isinstance(value, dict):
            continue
        normalized = normalize_record(value)
        result["state_files"].append(path.name)
        if result["status"] is None:
            result["status"] = first_present(normalized, STATUS_KEYS)
        if result["cursor"] is None:
            result["cursor"] = first_present(normalized, CURSOR_KEYS)
        counters = value.get("statistics") or value.get("counters")
        if isinstance(counters, dict):
            result.setdefault("counters", {}).update(counters)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def compute_drawdown(trades: list[dict[str, Any]]) -> dict[str, float | int]:
    resolved = [row for row in trades if row.get("resolved") and parse_float(row.get("pnl_usd")) is not None]
    resolved.sort(key=lambda row: parse_time(row.get("exit_time")) or dt.datetime.max)
    equity = peak = max_dd = 0.0
    for row in resolved:
        equity += float(row["pnl_usd"])
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {"resolved_trades": len(resolved), "net_usd": equity, "max_drawdown_usd": max_dd}


def overlap_rows(entries: list[dict[str, Any]], trades: list[dict[str, Any]], windows: list[int]) -> list[dict[str, Any]]:
    systems = sorted({row["system_id"] for row in entries} | {row["system_id"] for row in trades})
    rows: list[dict[str, Any]] = []
    by_system_entries = {system: [r for r in entries if r["system_id"] == system] for system in systems}
    for index, left in enumerate(systems):
        for right in systems[index + 1:]:
            left_entries = by_system_entries[left]
            right_entries = by_system_entries[right]
            for window in windows:
                matches = 0
                same_side = 0
                opposite_side = 0
                seen: set[tuple[str, str]] = set()
                for a in left_entries:
                    a_time = parse_time(a["entry_time"])
                    if a_time is None:
                        continue
                    for b in right_entries:
                        b_time = parse_time(b["entry_time"])
                        if b_time is None or abs((a_time - b_time).total_seconds()) > window * 60:
                            continue
                        key = (a["trade_id"], b["trade_id"])
                        if key in seen:
                            continue
                        seen.add(key)
                        matches += 1
                        if a["side"] == b["side"] and a["side"] != "UNKNOWN":
                            same_side += 1
                        elif a["side"] != "UNKNOWN" and b["side"] != "UNKNOWN":
                            opposite_side += 1
                rows.append({
                    "left_system": left,
                    "right_system": right,
                    "overlap_type": f"ENTRY_WITHIN_{window}M",
                    "count": matches,
                    "same_side": same_side,
                    "opposite_side": opposite_side,
                })

            concurrent = 0
            for a in [r for r in trades if r["system_id"] == left]:
                a_start, a_end = parse_time(a.get("entry_time")), parse_time(a.get("exit_time"))
                if a_start is None or a_end is None:
                    continue
                for b in [r for r in trades if r["system_id"] == right]:
                    b_start, b_end = parse_time(b.get("entry_time")), parse_time(b.get("exit_time"))
                    if b_start is None or b_end is None:
                        continue
                    if max(a_start, b_start) < min(a_end, b_end):
                        concurrent += 1
            rows.append({
                "left_system": left,
                "right_system": right,
                "overlap_type": "RESOLVED_HOLDING_INTERVAL",
                "count": concurrent,
                "same_side": "",
                "opposite_side": "",
            })
    return rows


def duplicate_incidents(entries: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    for kind, records in (("ENTRY", entries), ("TRADE", trades)):
        seen: dict[tuple[str, str], int] = {}
        for row in records:
            key = (row["system_id"], row["trade_id"])
            seen[key] = seen.get(key, 0) + 1
        for (system, trade_id), count in seen.items():
            if count > 1:
                incidents.append({"system_id": system, "incident": f"DUPLICATE_{kind}_ID", "detail": trade_id, "count": count})
    return incidents


def collect(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    if config.get("research_id") != RESEARCH_ID or config.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Operational research config mismatch")
    output_root = expand_path(str(config["output_root"]), config_path.parent)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = output_root / "snapshots" / stamp
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    manifest_rows: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    pre_stats: dict[str, tuple[int, int]] = {}

    for system in config.get("systems", []):
        system_id = str(system["system_id"])
        root = expand_path(str(system["state_root"]), config_path.parent)
        required = bool(system.get("required", False))
        files = discover_files(root)
        if not files:
            statuses.append({"system_id": system_id, "availability": "NOT_AVAILABLE", "state_root": str(root), "required": required})
            incidents.append({"system_id": system_id, "incident": "STATE_ROOT_NOT_AVAILABLE", "detail": str(root), "count": 1})
            continue
        summary = state_summary(files)
        latest_mtime = max(path.stat().st_mtime for path in files)
        freshness_minutes = max(0.0, (dt.datetime.now().timestamp() - latest_mtime) / 60.0)
        status = {
            "system_id": system_id,
            "availability": "AVAILABLE",
            "state_root": str(root),
            "required": required,
            "file_count": len(files),
            "latest_file_age_minutes": freshness_minutes,
            **summary,
        }
        statuses.append(status)
        if freshness_minutes > float(config.get("freshness_warning_minutes", 30)):
            incidents.append({"system_id": system_id, "incident": "STALE_RUNTIME_FILES", "detail": f"{freshness_minutes:.1f} minutes", "count": 1})

        for path in files:
            snap = file_snapshot(path)
            pre_stats[str(path)] = (snap["size"], snap["mtime_ns"])
            categories = ",".join(sorted(classify_file(path)))
            manifest_rows.append({"system_id": system_id, **snap, "categories": categories})
            try:
                records = read_csv_rows(path) if path.suffix.lower() == ".csv" else flatten_json_records(read_json(path))
            except Exception as exc:
                incidents.append({"system_id": system_id, "incident": "SOURCE_PARSE_ERROR", "detail": f"{path.name}: {exc}", "count": 1})
                continue
            category = classify_file(path)
            for row_index, record in enumerate(records, start=1):
                if "entry" in category:
                    normalized = record_to_entry(system_id, path, record, row_index)
                    if normalized:
                        entries.append(normalized)
                if "trade" in category:
                    normalized_trade = record_to_trade(system_id, path, record, row_index)
                    if normalized_trade:
                        trades.append(normalized_trade)

    incidents.extend(duplicate_incidents(entries, trades))
    windows = sorted({int(value) for value in config.get("proximity_windows_minutes", [0, 15, 60])})
    overlaps = overlap_rows(entries, trades, windows)

    source_changed = False
    for path_text, before in pre_stats.items():
        path = Path(path_text)
        try:
            after = (path.stat().st_size, path.stat().st_mtime_ns)
        except FileNotFoundError:
            source_changed = True
            incidents.append({"system_id": "GLOBAL", "incident": "SOURCE_DISAPPEARED_DURING_COLLECTION", "detail": path_text, "count": 1})
            continue
        if before != after:
            source_changed = True
            incidents.append({"system_id": "GLOBAL", "incident": "SOURCE_CHANGED_DURING_COLLECTION", "detail": path_text, "count": 1})

    per_system_metrics: dict[str, Any] = {}
    for system in statuses:
        system_id = system["system_id"]
        if system.get("availability") != "AVAILABLE":
            per_system_metrics[system_id] = {"availability": "NOT_AVAILABLE", "resolved_trades": None, "net_usd": None, "max_drawdown_usd": None}
        else:
            per_system_metrics[system_id] = {"availability": "AVAILABLE", **compute_drawdown([r for r in trades if r["system_id"] == system_id])}
    combined_metrics = compute_drawdown(trades)
    summary = {
        "research_id": RESEARCH_ID,
        "contract_version": CONTRACT_VERSION,
        "collected_at_local": dt.datetime.now().isoformat(),
        "snapshot_dir": str(snapshot_dir),
        "source_integrity_atomic": not source_changed,
        "systems": statuses,
        "normalized_entry_rows": len(entries),
        "normalized_trade_rows": len(trades),
        "per_system_metrics": per_system_metrics,
        "naive_combined_metrics": combined_metrics,
        "overlap_rows": len(overlaps),
        "incident_count": len(incidents),
        "interpretation": "READ_ONLY_OBSERVATION_ONLY_NO_PORTFOLIO_POLICY",
    }

    write_csv(snapshot_dir / "source_manifest.csv", manifest_rows, ["system_id", "path", "size", "mtime_ns", "sha256", "categories"])
    write_json(snapshot_dir / "system_status.json", statuses)
    write_csv(snapshot_dir / "normalized_entries.csv", entries, ["system_id", "trade_id", "entry_time", "side", "source_file", "source_row"])
    write_csv(snapshot_dir / "normalized_trades.csv", trades, ["system_id", "trade_id", "entry_time", "exit_time", "side", "pnl_usd", "resolved", "source_file", "source_row"])
    write_csv(snapshot_dir / "pairwise_overlap.csv", overlaps, ["left_system", "right_system", "overlap_type", "count", "same_side", "opposite_side"])
    write_csv(snapshot_dir / "operational_incidents.csv", incidents, ["system_id", "incident", "detail", "count"])
    write_json(snapshot_dir / "summary.json", summary)

    zip_path = output_root / f"GOLD_SHADOW_OPERATIONAL_SNAPSHOT_{stamp}.zip"
    summary["zip_path"] = str(zip_path)
    write_json(snapshot_dir / "summary.json", summary)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(snapshot_dir.iterdir()):
            archive.write(path, arcname=path.name)
    return summary


def latest(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    output_root = expand_path(str(config["output_root"]), config_path.parent)
    snapshots = sorted((output_root / "snapshots").glob("*/summary.json")) if (output_root / "snapshots").exists() else []
    return read_json(snapshots[-1]) if snapshots else {"status": "NO_SNAPSHOT", "output_root": str(output_root)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only GOLD Shadow operational research collector")
    parser.add_argument("command", choices=("collect", "latest"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        value = collect(args.config.resolve()) if args.command == "collect" else latest(args.config.resolve())
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
