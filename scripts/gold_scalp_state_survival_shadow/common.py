from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

RUNTIME_LABEL = "GOLD_P75_STATE_SURVIVAL_SHADOW"
CANDIDATE_ID = "CANDLE_STATE_SURVIVAL_DUAL_STRICT_EPISODE_HEALTH_P75_V3"
CONTRACT_VERSION = "2026-08-02-shadow-v1"
RESEARCH_CUTOFF = pd.Timestamp("2026-07-31 19:30:00")
FIXED_SPREAD_USD = 0.30
INITIAL_STOP_USD = 5.0
PARTIAL_TARGET_USD = 5.0
FINAL_TARGET_USD = 10.0
PARTIAL_FRACTION = 0.75
REMAINDER_FRACTION = 0.25
HORIZON_MINUTES = 240

SELECTED_STATE_ACTIONS: dict[str, str] = {
    "S08|UP|LOW|UP|NORM|WEAK": "SHORT",
    "S08|UP|MID|UP|COMP|WEAK": "SHORT",
    "S01|UP|LOW|UP|NORM|WEAK": "LONG",
    "S08|MIXED|LOW|UP|EXP|BULL": "SHORT",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def path_value(value: str | Path, base: Path | None = None) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(str(value))))
    if not expanded.is_absolute() and base is not None:
        expanded = base / expanded
    return expanded.resolve()


def normalize_name(value: Any) -> str:
    return str(value).strip().lower().replace("<", "").replace(">", "").replace("-", "_")


def parse_timestamp(value: Any) -> pd.Timestamp | None:
    if value in (None, "", "nan", "NaN", "NaT"):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    result = pd.Timestamp(parsed)
    if result.tzinfo is not None:
        result = result.tz_localize(None)
    return result


def half_year(value: pd.Timestamp) -> str:
    return f"{value.year}H{1 if value.month <= 6 else 2}"


def month_key(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    os.replace(temporary, path)


def append_csv(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {str(key): "" if value is None else value for key, value in row.items()}
    exists = path.exists() and path.stat().st_size > 0
    fieldnames = list(normalized)
    if exists:
        with path.open("r", encoding="utf-8-sig", newline="") as existing:
            fieldnames = next(csv.reader(existing))
        extra = sorted(set(normalized) - set(fieldnames))
        if extra:
            raise RuntimeError(f"CSV schema change is not allowed for {path}: {extra}")
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(normalized)


def read_csv_records(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{normalize_name(k): v for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = read_json(path)
    if config.get("candidate_id") != CANDIDATE_ID:
        raise ValueError("candidate_id mismatch")
    if config.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("contract_version mismatch")
    if config.get("mt5_orders_enabled", False):
        raise ValueError("MT5 order execution must remain disabled")
    if config.get("final_signal_enabled", False):
        raise ValueError("final_signal must remain disabled")
    return config


def state_root(config: Mapping[str, Any], config_path: Path) -> Path:
    value = config.get("state_dir")
    if not isinstance(value, str) or not value:
        raise ValueError("state_dir is missing")
    root = path_value(value, config_path.parent)
    forbidden = ("gold_v19_shadow", "gold_challenger_c1_shadow")
    lowered = str(root).lower()
    if any(token in lowered for token in forbidden):
        raise ValueError("State Survival Shadow requires its own state directory")
    return root


def logger_for(root: Path, name: str, filename: str) -> logging.Logger:
    (root / "logs").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(f"%(asctime)s %(levelname)s [{RUNTIME_LABEL}] %(message)s")
    for handler in (
        logging.FileHandler(root / "logs" / filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def lock_instance(root: Path, filename: str, message: str):
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError(message) from exc
    return handle


def first_present(source: Mapping[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        if name in source and source[name] not in (None, "", "nan", "NaN", "NaT"):
            return source[name]
    return None
