from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ACTION_CONFIG = Path("config/gold_ml_v1/next_local_action.json")
LOCAL_PATHS_CONFIG = Path("config/gold_ml_v1/local_runtime_paths.local.json")
OUTPUT_DIR = Path("outputs/gold_ml_v1/next_action")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def detect_mql5_files(repo_root: Path) -> Path | None:
    for candidate in [repo_root, *repo_root.parents]:
        if candidate.name.lower() == "files" and candidate.parent.name.lower() == "mql5":
            return candidate
    return None


def load_local_overrides(repo_root: Path) -> dict[str, str]:
    path = repo_root / LOCAL_PATHS_CONFIG
    if not path.exists():
        return {}
    raw = load_json(path)
    return {str(key): str(value) for key, value in raw.items()}


def placeholders(repo_root: Path, overrides: dict[str, str]) -> dict[str, str]:
    mql5_files = detect_mql5_files(repo_root)
    defaults = {
        "REPO_ROOT": str(repo_root),
        "USER_HOME": str(Path.home()),
        "MQL5_FILES": str(mql5_files) if mql5_files else "",
        "RAW_HISTORY_DIR": str(mql5_files / "gold_v3_2023_2026") if mql5_files else "",
        "BATCH023_ZIP": str(Path.home() / "Downloads" / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"),
    }
    defaults.update(overrides)
    return defaults


def expand(value: str, mapping: dict[str, str]) -> str:
    expanded = os.path.expandvars(value)
    for key, replacement in mapping.items():
        expanded = expanded.replace("{" + key + "}", replacement)
    return expanded


def resolve_existing_fallback(value: str, mapping: dict[str, str]) -> str:
    options = [expand(item.strip(), mapping) for item in value.split("||")]
    for option in options:
        if Path(option).exists():
            return option
    return options[0]


def write_status(repo_root: Path, lines: list[str]) -> None:
    output_dir = repo_root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "LATEST_NEXT_ACTION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_required_paths(required: list[dict[str, Any]], mapping: dict[str, str]) -> list[str]:
    resolved: list[str] = []
    missing: list[str] = []
    for item in required:
        label = str(item.get("label", "path"))
        raw_value = str(item["path"])
        value = resolve_existing_fallback(raw_value, mapping)
        resolved.append(f"{label}={value}")
        if not Path(value).exists():
            missing.append(f"{label}: {value}")
    if missing:
        raise FileNotFoundError("Required local paths are missing: " + "; ".join(missing))
    return resolved


def run_action(repo_root: Path, config: dict[str, Any]) -> int:
    overrides = load_local_overrides(repo_root)
    mapping = placeholders(repo_root, overrides)
    action_id = str(config.get("action_id", "UNKNOWN"))
    mode = str(config.get("mode", "status_only"))
    title = str(config.get("title", action_id))
    message = str(config.get("message", ""))

    header = [
        "GOLD_ML_V1 NEXT ACTION",
        f"time_local={datetime.now().isoformat(timespec='seconds')}",
        f"action_id={action_id}",
        f"mode={mode}",
        f"title={title}",
    ]

    print("=" * 60)
    print(title)
    print("=" * 60)

    if mode == "status_only":
        print(message)
        lines = header + ["status=PASS", "exit_code=0", f"message={message}"]
        write_status(repo_root, lines)
        return 0

    if mode != "bat":
        raise ValueError(f"Unsupported action mode: {mode}")

    required = config.get("required_paths", [])
    resolved_paths = validate_required_paths(required, mapping)
    runner = Path(expand(str(config["runner"]), mapping))
    if not runner.is_absolute():
        runner = repo_root / runner
    if not runner.exists():
        raise FileNotFoundError(f"Runner BAT not found: {runner}")

    arguments: list[str] = []
    for raw_argument in config.get("arguments", []):
        arguments.append(resolve_existing_fallback(str(raw_argument), mapping))

    command = ["cmd", "/c", str(runner), *arguments]
    print(f"Action: {action_id}")
    print(f"Runner: {runner}")
    completed = subprocess.run(command, cwd=str(repo_root), check=False)

    lines = header + resolved_paths + [
        f"runner={runner}",
        f"command={command}",
        f"status={'PASS' if completed.returncode == 0 else 'FAIL'}",
        f"exit_code={completed.returncode}",
    ]
    write_status(repo_root, lines)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        config = load_json(repo_root / ACTION_CONFIG)
        return run_action(repo_root, config)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(f"[ERROR] {error}", file=sys.stderr)
        write_status(
            repo_root,
            [
                "GOLD_ML_V1 NEXT ACTION",
                f"time_local={datetime.now().isoformat(timespec='seconds')}",
                "status=FAIL",
                "exit_code=4",
                f"error={error}",
            ],
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
