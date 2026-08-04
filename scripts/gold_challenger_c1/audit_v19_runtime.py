from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
from collections import deque
from pathlib import Path
from typing import Any, TextIO


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in {"webhook_url", "token", "secret", "password"}:
                result[str(key)] = "<REDACTED>"
            else:
                result[str(key)] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def relevant_files(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    keep_names = {
        "runtime_state.json",
        "runtime_health.json",
        "score_history.csv.gz",
        "pending_scores.csv.gz",
        "shadow_score_ledger.csv",
        "shadow_trade_ledger.csv",
        "score_history_invalid_gap_ledger.csv",
        "discord_notifier_state.json",
    }
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or "venv" in {part.lower() for part in path.parts}:
            continue
        if path.name.lower() in keep_names or path.suffix.lower() in {".log"}:
            found.append(str(path.relative_to(root)))
    return sorted(found)


def discover_candidates() -> list[str]:
    roots = [
        expand_path(r"%LOCALAPPDATA%\xauusd_signal_lab"),
        Path(r"C:\gold-v19-shadow"),
    ]
    wanted = {
        "runtime_state.json",
        "runtime_health.json",
        "shadow_score_ledger.csv",
        "shadow_trade_ledger.csv",
        "score_history.csv.gz",
        "pending_scores.csv.gz",
    }
    found: set[str] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.name.lower() in wanted:
                found.add(str(path.resolve()))
    return sorted(found)


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def inspect_table(path: Path, tail_rows: int = 3) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        return report
    report["bytes"] = path.stat().st_size
    with _open_text(path) as handle:
        header_line = handle.readline()
        if not header_line:
            report["empty"] = True
            return report
        delimiter = ";" if header_line.count(";") >= max(header_line.count(","), header_line.count("\t")) else "," if header_line.count(",") >= header_line.count("\t") else "\t"
        header = next(csv.reader([header_line.rstrip("\r\n")], delimiter=delimiter))
        first: list[str] | None = None
        tail: deque[list[str]] = deque(maxlen=tail_rows)
        rows = 0
        for row in csv.reader(handle, delimiter=delimiter):
            if not row or not any(str(cell).strip() for cell in row):
                continue
            rows += 1
            if first is None:
                first = row
            tail.append(row)
    report.update(
        {
            "delimiter": delimiter,
            "columns": header,
            "row_count": rows,
            "first_row": first,
            "last_rows": list(tail),
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of the configured GOLD V19 runtime")
    parser.add_argument("--config", required=True, type=Path, help="Challenger local_config.json")
    args = parser.parse_args()

    challenger_path = args.config.resolve()
    report: dict[str, Any] = {
        "mode": "READ_ONLY_COMPACT_SCHEMA_AUDIT",
        "challenger_config_path": str(challenger_path),
        "challenger_config_exists": challenger_path.exists(),
    }
    try:
        challenger = read_json(challenger_path)
        report["challenger_config"] = redact(challenger)
        v19_value = challenger.get("v19", {}).get("local_config_path")
        if not isinstance(v19_value, str) or not v19_value:
            raise ValueError("v19.local_config_path is missing")
        v19_config_path = expand_path(v19_value)
        report["v19_config_path"] = str(v19_config_path)
        report["v19_config_exists"] = v19_config_path.exists()
        if not v19_config_path.exists():
            report["discovered_runtime_files"] = discover_candidates()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2

        v19_config = read_json(v19_config_path)
        report["v19_config"] = redact(v19_config)
        state_value = v19_config.get("state_dir")
        if not isinstance(state_value, str) or not state_value:
            raise ValueError("V19 state_dir is missing")
        state_root = expand_path(state_value)
        report["v19_state_root"] = str(state_root)
        report["v19_state_root_exists"] = state_root.exists()
        report["v19_relevant_files"] = relevant_files(state_root)

        runtime_state = state_root / "runtime_state.json"
        runtime_health = state_root / "runtime_health.json"
        report["runtime_state"] = redact(read_json(runtime_state)) if runtime_state.exists() else {"exists": False}
        report["runtime_health"] = redact(read_json(runtime_health)) if runtime_health.exists() else {"exists": False}

        table_paths = {
            "score_history": state_root / "score_history.csv.gz",
            "pending_scores": state_root / "pending_scores.csv.gz",
            "invalid_gap_ledger": state_root / "outputs" / "score_history_invalid_gap_ledger.csv",
            "legacy_score_ledger": state_root / "outputs" / "shadow_score_ledger.csv",
            "legacy_trade_ledger": state_root / "outputs" / "shadow_trade_ledger.csv",
        }
        report["tables"] = {name: inspect_table(path) for name, path in table_paths.items()}
        report["discovered_runtime_files"] = discover_candidates()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["discovered_runtime_files"] = discover_candidates()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
