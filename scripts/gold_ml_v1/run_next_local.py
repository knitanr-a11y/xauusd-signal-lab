from __future__ import annotations

import argparse
import json
import locale
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ACTION_CONFIG = Path("config/gold_ml_v1/next_local_action.json")
LOCAL_PATHS_CONFIG = Path("config/gold_ml_v1/local_runtime_paths.local.json")
OUTPUT_DIR = Path("outputs/gold_ml_v1/next_action")
STATUS_FILE = OUTPUT_DIR / "LATEST_NEXT_ACTION.txt"
CONSOLE_LOG_FILE = OUTPUT_DIR / "FULL_CONSOLE_LOG.txt"
PASTE_ME_OUTPUT_FILE = OUTPUT_DIR / "PASTE_ME_GOLD_ML_V1.txt"
PASTE_ME_ROOT_FILE = Path("PASTE_ME_GOLD_ML_V1.txt")
COST_OUTPUT_DIR = Path("outputs/gold_ml_v1/cost_stress_raw_reconstructed")


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
        "BATCH023_ZIP": str(
            Path.home()
            / "Downloads"
            / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
        ),
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


def write_status(repo_root: Path, lines: list[str]) -> Path:
    output_dir = repo_root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = repo_root / STATUS_FILE
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_console_log(repo_root: Path, text: str) -> Path:
    output_dir = repo_root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = repo_root / CONSOLE_LOG_FILE
    path.write_text(text, encoding="utf-8", errors="replace")
    return path


def tail_text(path: Path, maximum_lines: int) -> list[str]:
    if not path.exists():
        return [f"[FILE NOT CREATED] {path}"]
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [f"[FILE READ ERROR] {path}: {type(exc).__name__}: {exc}"]
    if len(lines) > maximum_lines:
        omitted = len(lines) - maximum_lines
        return [f"[... {omitted} earlier lines omitted ...]", *lines[-maximum_lines:]]
    return lines


def write_paste_me(
    repo_root: Path,
    exit_code: int,
    action_id: str = "UNKNOWN",
    runner: str = "",
    error: str = "",
) -> Path:
    sections: list[tuple[str, Path, int]] = [
        ("NEXT ACTION STATUS", repo_root / STATUS_FILE, 80),
        ("CAPTURED CONSOLE OUTPUT", repo_root / CONSOLE_LOG_FILE, 140),
        (
            "COST STRESS LATEST SUMMARY",
            repo_root / COST_OUTPUT_DIR / "LATEST_RUN_SUMMARY.txt",
            180,
        ),
        (
            "COST STRESS ERROR TRACE",
            repo_root / COST_OUTPUT_DIR / "COST_STRESS_RUN_ERROR.txt",
            140,
        ),
    ]
    lines = [
        "GOLD_ML_V1 PASTE ME",
        "Copy everything in this file and paste it into ChatGPT.",
        f"generated_local={datetime.now().isoformat(timespec='seconds')}",
        f"exit_code={exit_code}",
        f"action_id={action_id}",
        f"runner={runner}",
        f"error={error}",
        f"repo_root={repo_root}",
        "",
    ]
    for title, path, limit in sections:
        lines.extend(
            [
                "=" * 72,
                title,
                f"source_file={path}",
                "=" * 72,
                *tail_text(path, limit),
                "",
            ]
        )
    text = "\n".join(lines).rstrip() + "\n"
    output_dir = repo_root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = repo_root / PASTE_ME_OUTPUT_FILE
    root_path = repo_root / PASTE_ME_ROOT_FILE
    output_path.write_text(text, encoding="utf-8")
    root_path.write_text(text, encoding="utf-8")
    return root_path


def validate_required_paths(
    required: list[dict[str, Any]], mapping: dict[str, str]
) -> list[str]:
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


def run_subprocess_with_log(
    command: list[str], repo_root: Path, log_path: Path
) -> int:
    encoding = locale.getpreferredencoding(False) or "utf-8"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log_handle:
        log_handle.write(f"command={command}\n")
        log_handle.write(f"cwd={repo_root}\n")
        log_handle.flush()
        process = subprocess.Popen(
            command,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=encoding,
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log_handle.write(line)
            log_handle.flush()
        return int(process.wait())


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
        write_console_log(repo_root, message + "\n")
        paste_path = write_paste_me(repo_root, 0, action_id=action_id)
        print(f"PASTE_ME: {paste_path}")
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

    command = ["cmd", "/d", "/c", str(runner), *arguments]
    print(f"Action: {action_id}")
    print(f"Runner: {runner}")
    completed_return_code = run_subprocess_with_log(
        command, repo_root, repo_root / CONSOLE_LOG_FILE
    )

    lines = header + resolved_paths + [
        f"runner={runner}",
        f"command={command}",
        f"status={'PASS' if completed_return_code == 0 else 'FAIL'}",
        f"exit_code={completed_return_code}",
    ]
    write_status(repo_root, lines)
    paste_path = write_paste_me(
        repo_root,
        completed_return_code,
        action_id=action_id,
        runner=str(runner),
    )
    print(f"PASTE_ME: {paste_path}")
    return completed_return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    config: dict[str, Any] = {}
    try:
        config = load_json(repo_root / ACTION_CONFIG)
        return run_action(repo_root, config)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(f"[ERROR] {error}", file=sys.stderr)
        write_console_log(repo_root, f"[ERROR] {error}\n")
        write_status(
            repo_root,
            [
                "GOLD_ML_V1 NEXT ACTION",
                f"time_local={datetime.now().isoformat(timespec='seconds')}",
                f"action_id={config.get('action_id', 'UNKNOWN')}",
                "status=FAIL",
                "exit_code=4",
                f"error={error}",
            ],
        )
        paste_path = write_paste_me(
            repo_root,
            4,
            action_id=str(config.get("action_id", "UNKNOWN")),
            runner=str(config.get("runner", "")),
            error=error,
        )
        print(f"PASTE_ME: {paste_path}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
