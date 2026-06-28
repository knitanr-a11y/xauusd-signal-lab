from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from raw_engine import LIVE_FILENAMES, RAW_FILENAMES, read_bars


def inspect_csv_set(root: Path, live_mode: bool) -> dict[str, object]:
    names = LIVE_FILENAMES if live_mode else RAW_FILENAMES
    files: dict[str, object] = {}
    for timeframe, filename in names.items():
        path = root / filename
        if not path.is_file():
            files[timeframe] = {"exists": False, "path": str(path)}
            continue
        frame = read_bars(root, timeframe, live=live_mode)
        files[timeframe] = {
            "exists": True,
            "path": str(path),
            "rows": int(len(frame)),
            "first_open_time": frame["bar_open_time"].iloc[0].isoformat(sep=" "),
            "last_open_time": frame["bar_open_time"].iloc[-1].isoformat(sep=" "),
            "last_close_time": frame["bar_close_time"].iloc[-1].isoformat(sep=" "),
        }
    return {
        "root": str(root),
        "mode": "live" if live_mode else "historical",
        "files": files,
        "passed": all(item.get("exists", False) for item in files.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-dir", type=Path, required=True)
    parser.add_argument("--live-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report: dict[str, object] = {
        "historical": inspect_csv_set(args.historical_dir.resolve(), False)
    }
    if args.live_dir:
        report["live"] = inspect_csv_set(args.live_dir.resolve(), True)
    report["passed"] = bool(
        report["historical"]["passed"]
        and ("live" not in report or report["live"]["passed"])
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
