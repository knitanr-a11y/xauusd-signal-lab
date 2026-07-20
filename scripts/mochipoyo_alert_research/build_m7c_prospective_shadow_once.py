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
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(
        description="Run one organized M7C prospective shadow audit cycle."
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=local / "m7c_runtime" / "m7c_prospective_shadow_manifest_runtime.json",
    )
    parser.add_argument("--output-dir", type=Path, default=local / "logs" / "m7c")
    parser.add_argument(
        "--derived-output-dir", type=Path, default=local / "logs" / "derived"
    )
    parser.add_argument("--refresh-upstream-if-stale", action="store_true")
    return parser.parse_args()


def run(command: list[str]) -> int:
    return int(subprocess.run(command, cwd=REPO_ROOT, check=False).returncode)


def shadow_command(
    *, db: Path, mt5_root: Path, manifest: Path, output_dir: Path
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


def relocate_episode_report(local_root: Path, derived_dir: Path) -> None:
    source = local_root / "logs" / "latest_episode_build_result.json"
    if not source.exists():
        return
    derived_dir.mkdir(parents=True, exist_ok=True)
    target = derived_dir / source.name
    target.unlink(missing_ok=True)
    source.replace(target)


def main() -> int:
    args = parse_args()
    if not args.env.is_file():
        print("[ERROR] Local Mochipoyo .env was not found.")
        return 2
    env = load_env(args.env)
    mt5_root_text = env.get("MT5_FILES_ROOT", "").strip()
    if not mt5_root_text:
        print("[ERROR] MT5_FILES_ROOT is not configured in the local Mochipoyo .env.")
        return 2
    mt5_root = Path(mt5_root_text)

    for path, label in (
        (args.db, "Mochipoyo SQLite database"),
        (mt5_root, "configured MT5 Files folder"),
        (args.manifest, "local runtime M7C manifest"),
        (RUNNER, "M7C runner"),
    ):
        exists = path.is_dir() if label == "configured MT5 Files folder" else path.is_file()
        if not exists:
            print(f"[ERROR] {label} was not found: {path}")
            if label == "local runtime M7C manifest":
                print("Run run_initialize_m7c_prospective_shadow_runtime_once.bat first.")
            return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.derived_output_dir.mkdir(parents=True, exist_ok=True)
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
    if not EPISODE_BUILDER.is_file() or not ALIGNMENT_BUILDER.is_file():
        print("[ERROR] Required M3/M4 builder script was not found.")
        return 2

    episode_code = run(
        [
            sys.executable,
            str(EPISODE_BUILDER),
            "--env",
            str(args.env),
            "--db",
            str(args.db),
        ]
    )
    if episode_code != 0:
        print(f"[ERROR] M3 episode rebuild failed with exit code {episode_code}.")
        return episode_code
    relocate_episode_report(args.env.expanduser().resolve().parent, args.derived_output_dir)

    alignment_output = args.derived_output_dir / "latest_mt5_closed_bar_alignment_result.json"
    alignment_code = run(
        [
            sys.executable,
            str(ALIGNMENT_BUILDER),
            "--env",
            str(args.env),
            "--db",
            str(args.db),
            "--output",
            str(alignment_output),
        ]
    )
    if alignment_code != 0:
        print(f"[ERROR] M4 alignment rebuild failed with exit code {alignment_code}.")
        return alignment_code

    print("[INFO] M3/M4 refresh passed. Retrying the unchanged runtime M7C manifest.")
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
