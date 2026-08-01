from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
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


def list_files(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of the configured GOLD V19 runtime")
    parser.add_argument("--config", required=True, type=Path, help="Challenger local_config.json")
    args = parser.parse_args()

    challenger_path = args.config.resolve()
    report: dict[str, Any] = {
        "mode": "READ_ONLY",
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
        report["v19_state_files"] = list_files(state_root)
        report["expected_paths"] = {
            "runtime_state": str(state_root / "runtime_state.json"),
            "runtime_health": str(state_root / "runtime_health.json"),
            "score_ledger": str(state_root / "outputs" / "shadow_score_ledger.csv"),
            "trade_ledger": str(state_root / "outputs" / "shadow_trade_ledger.csv"),
            "score_history": str(state_root / "score_history.csv.gz"),
            "pending_scores": str(state_root / "pending_scores.csv.gz"),
        }
        report["expected_path_exists"] = {
            name: Path(path).exists() for name, path in report["expected_paths"].items()
        }
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
