from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
RUNNER = SCRIPT_DIR / "run_m7c_prospective_shadow.py"
EPISODE_BUILDER = SCRIPT_DIR / "build_episodes_once.py"
ALIGNMENT_BUILDER = SCRIPT_DIR / "build_mt5_closed_bar_alignment_once.py"
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "config"
    / "mochipoyo_alert_research"
    / "m7c_prospective_shadow_manifest_v1.json"
)


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
            "Run one M7C prospective shadow audit cycle using the existing local "
            "Mochipoyo .env and SQLite layout."
        )
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=local / "logs")
    parser.add_argument(
        "--refresh-upstream-if-stale",
        action="store_true",
        help=(
            "When new raw alerts exist, rebuild only the existing M3 episode and M4 "
            "alignment derived tables, then retry M7C."
        ),
    )
    return parser.parse_args()


def run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def shadow_command(
    *,
    db: Path,
    mt5_root: Path,
    manifest: Path,
    output_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        str(RUNNER),
        "--database",
        str(db),
        "--mt5-files-root",
        str(mt5_root),
        "--manifest",
        str(manifest),
        "--output-dir",
        str(output_dir),
    ]


def main() -> int:
    args = parse_args()
    if not args.env.is_file():
        print("[ERROR] Local Mochipoyo .env was not found.")
        print("Run run_configure_mt5_csv_root.bat first.")
        return 2
    env = load_env(args.env)
    mt5_root_text = env.get("MT5_FILES_ROOT", "").strip()
    if not mt5_root_text:
        print("[ERROR] MT5_FILES_ROOT is not configured in the local Mochipoyo .env.")
        return 2
    mt5_root = Path(mt5_root_text)

    if not args.db.is_file():
        print("[ERROR] Mochipoyo SQLite database was not found.")
        return 2
    if not mt5_root.is_dir():
        print("[ERROR] Configured MT5 Files folder does not exist.")
        return 2
    if not args.manifest.is_file():
        print("[ERROR] Frozen M7C manifest was not found.")
        return 2
    if not RUNNER.is_file():
        print("[ERROR] M7C runner was not found.")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = shadow_command(
        db=args.db,
        mt5_root=mt5_root,
        manifest=args.manifest,
        output_dir=args.output_dir,
    )
    exit_code = run(command)
    if exit_code != 3 or not args.refresh_upstream_if_stale:
        return exit_code

    print("[INFO] New raw alerts made M3/M4 stale. Refreshing derived audit tables only.")
    for script, label in (
        (EPISODE_BUILDER, "M3 episode rebuild"),
        (ALIGNMENT_BUILDER, "M4 closed-bar alignment rebuild"),
    ):
        if not script.is_file():
            print(f"[ERROR] Required {label} script was not found: {script}")
            return 2
        code = run(
            [
                sys.executable,
                str(script),
                "--env",
                str(args.env),
                "--db",
                str(args.db),
            ]
        )
        if code != 0:
            print(f"[ERROR] {label} failed with exit code {code}. M7C was not rerun.")
            return code

    print("[INFO] M3/M4 refresh passed. Retrying the unchanged M7C shadow manifest.")
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
