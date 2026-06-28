from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

FILE_BY_TF = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
EXIT_CHANGED = 0
EXIT_ERROR = 2
EXIT_UNCHANGED = 10


def has_files(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in FILE_BY_TF.values())


def find_live_dir(output_dir: Path) -> Path:
    configured = os.environ.get("GML1_LIVE_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if not has_files(path):
            raise FileNotFoundError(f"GML1_LIVE_DIR is invalid: {path}")
        return path

    for filename in ("latest_status.json", "live_state.json"):
        path = output_dir / filename
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        value = payload.get("live_dir")
        if value:
            candidate = Path(value).expanduser().resolve()
            if has_files(candidate):
                return candidate

    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        raise FileNotFoundError("APPDATA unavailable and GML1_LIVE_DIR is not set")
    root = Path(appdata) / "MetaQuotes" / "Terminal"
    matches = []
    if root.is_dir():
        for terminal in root.iterdir():
            candidate = terminal / "MQL5" / "Files"
            if has_files(candidate):
                matches.append(candidate.resolve())
    if not matches:
        raise FileNotFoundError("No MT5 MQL5\\Files directory contains all goldsharp CSVs")
    if len(matches) > 1:
        raise ValueError(
            "Multiple live CSV directories found; set GML1_LIVE_DIR: "
            + " | ".join(map(str, matches))
        )
    return matches[0]


def signatures(root: Path) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for timeframe, name in FILE_BY_TF.items():
        stat = (root / name).stat()
        result[timeframe] = {"size": int(stat.st_size), "mtime_ns": int(stat.st_mtime_ns)}
    return result


def saved_signatures(state_path: Path) -> dict[str, Any] | None:
    if not state_path.is_file():
        return None
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return payload.get("input_signatures")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    try:
        live_dir = find_live_dir(output_dir)
        current = signatures(live_dir)
        previous = saved_signatures(output_dir / "live_state.json")
        if previous == current:
            return EXIT_UNCHANGED
        print(json.dumps({"status": "CHANGED", "live_dir": str(live_dir)}))
        return EXIT_CHANGED
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
