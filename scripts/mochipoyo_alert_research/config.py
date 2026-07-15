from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class CollectorConfig:
    events_url: str
    read_token: str
    local_root: Path
    env_path: Path
    database_path: Path
    logs_dir: Path


def default_local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if not base:
        base = os.environ.get("TEMP", "").strip()
    if not base:
        base = tempfile.gettempdir()
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def default_env_path() -> Path:
    return default_local_root() / ".env"


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            raise ValueError(f"{path}:{number}: invalid environment variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def merged_environment(dotenv: Mapping[str, str]) -> dict[str, str]:
    merged = dict(dotenv)
    merged.update({key: value for key, value in os.environ.items()})
    return merged


def load_config(
    env_path: Path | None = None,
    database_path: Path | None = None,
    *,
    require_remote: bool = True,
) -> CollectorConfig:
    resolved_env = (env_path or default_env_path()).expanduser().resolve()
    env = merged_environment(read_dotenv(resolved_env))
    root_raw = env.get("MOCHIPOYO_LOCAL_ROOT", "").strip()
    local_root = (
        Path(root_raw).expanduser().resolve()
        if root_raw
        else resolved_env.parent
    )
    events_url = env.get("MOCHIPOYO_EVENTS_URL", "").strip()
    read_token = env.get("MOCHIPOYO_READ_TOKEN", "").strip()
    if require_remote:
        missing = []
        if not events_url:
            missing.append("MOCHIPOYO_EVENTS_URL")
        if not read_token:
            missing.append("MOCHIPOYO_READ_TOKEN")
        if missing:
            raise ValueError(
                "Missing required local configuration: " + ", ".join(missing)
            )
        if not events_url.lower().startswith("https://"):
            raise ValueError("MOCHIPOYO_EVENTS_URL must use https://")
    db_path = (
        database_path.expanduser().resolve()
        if database_path is not None
        else local_root / "mochipoyo_alerts.sqlite3"
    )
    return CollectorConfig(
        events_url=events_url,
        read_token=read_token,
        local_root=local_root,
        env_path=resolved_env,
        database_path=db_path,
        logs_dir=local_root / "logs",
    )
