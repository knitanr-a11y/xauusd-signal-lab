from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "config"
    / "mochipoyo_alert_research"
    / "m7b_frozen_trigger_kernel_manifest_v1.json"
)
RUNNER = SCRIPT_DIR / "frozen_trigger_kernel_validation.py"


def default_local_root() -> Path:
    base = (
        os.environ.get("LOCALAPPDATA", "").strip()
        or os.environ.get("TEMP", "").strip()
        or tempfile.gettempdir()
    )
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen Mochipoyo M7B trigger-kernel validation once using the "
            "same local .env and SQLite layout as the prior Mochipoyo stages."
        )
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=local / "logs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env(args.env)
    mt5_root_text = env.get("MT5_FILES_ROOT", "").strip()

    if not args.env.is_file():
        print("[ERROR] Local Mochipoyo .env was not found.")
        print("Run run_configure_mt5_csv_root.bat first.")
        return 2
    if not mt5_root_text:
        print("[ERROR] MT5_FILES_ROOT is not configured in the local Mochipoyo .env.")
        return 2

    mt5_root = Path(mt5_root_text)
    if not mt5_root.is_dir():
        print("[ERROR] Configured MT5 Files folder does not exist.")
        return 2
    if not args.db.is_file():
        print("[ERROR] Mochipoyo SQLite database was not found.")
        return 2
    if not args.manifest.is_file():
        print("[ERROR] Frozen M7B manifest was not found.")
        return 2
    if not RUNNER.is_file():
        print("[ERROR] Frozen M7B validation runner was not found.")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(RUNNER),
        "--database",
        str(args.db),
        "--mt5-files-root",
        str(mt5_root),
        "--manifest",
        str(args.manifest),
        "--output-dir",
        str(args.output_dir),
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        print(
            "[SAFE] M7B stopped without changing raw alerts, SQLite derived stages, "
            "MT5 CSVs, Discord settings, or MT5 order settings."
        )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
