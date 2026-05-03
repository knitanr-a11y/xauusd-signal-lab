from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path


DEFAULT_FILES = [
    r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m5.csv",
    r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv",
    r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_h1.csv",
    r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_h4.csv",
]


def file_mtime_text(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except FileNotFoundError:
        return "missing"


def read_last_csv_row(path: Path) -> tuple[int, dict[str, str] | None]:
    if not path.exists():
        return 0, None
    last: dict[str, str] | None = None
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
            last = row
    return count, last


def snapshot(paths: list[Path]) -> dict[str, tuple[float | None, int, str, str, str]]:
    out: dict[str, tuple[float | None, int, str, str, str]] = {}
    for path in paths:
        if not path.exists():
            out[str(path)] = (None, 0, "missing", "", "")
            continue
        stat = path.stat()
        rows, last = read_last_csv_row(path)
        last_time = "" if last is None else str(last.get("time", ""))
        last_close = "" if last is None else str(last.get("close", ""))
        out[str(path)] = (stat.st_mtime, rows, file_mtime_text(path), last_time, last_close)
    return out


def print_snapshot(title: str, snap: dict[str, tuple[float | None, int, str, str, str]]) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)
    for raw_path, (_mtime, rows, mtime_text, last_time, last_close) in snap.items():
        name = Path(raw_path).name
        print(f"{name}: rows={rows} mtime={mtime_text} last_time={last_time} last_close={last_close}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether BTC CSV files are being exported/updated by the MQL5 EA.")
    parser.add_argument("--files", nargs="*", type=Path, default=[Path(x) for x in DEFAULT_FILES])
    parser.add_argument("--watch", action="store_true", help="Take two snapshots and compare after --seconds.")
    parser.add_argument("--seconds", type=int, default=75, help="Wait seconds for --watch mode. 75 covers at least one minute boundary.")
    args = parser.parse_args()

    paths = [Path(x) for x in args.files]
    before = snapshot(paths)
    print_snapshot("BTC CSV export status", before)

    if not args.watch:
        return 0

    print(f"\nWaiting {args.seconds} seconds for the next MQL5 export slot...")
    time.sleep(args.seconds)
    after = snapshot(paths)
    print_snapshot("BTC CSV export status after wait", after)

    print("\n" + "=" * 100)
    print("Change check")
    print("=" * 100)
    for raw_path, before_values in before.items():
        after_values = after.get(raw_path)
        name = Path(raw_path).name
        if after_values is None:
            print(f"{name}: missing after snapshot")
            continue
        before_mtime, before_rows, _before_mtime_text, before_last_time, before_last_close = before_values
        after_mtime, after_rows, _after_mtime_text, after_last_time, after_last_close = after_values
        mtime_changed = before_mtime != after_mtime
        rows_changed = before_rows != after_rows
        last_time_changed = before_last_time != after_last_time
        last_close_changed = before_last_close != after_last_close
        print(
            f"{name}: "
            f"mtime_changed={mtime_changed} rows_changed={rows_changed} "
            f"last_time_changed={last_time_changed} last_close_changed={last_close_changed}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
