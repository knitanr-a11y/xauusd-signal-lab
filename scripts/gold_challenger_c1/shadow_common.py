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

CANDIDATE_ID = "GOLD_CHALLENGER_C1_V2_DATA_V3"
CONTRACT_VERSION = "2026-08-01-prospective-shadow-v1"
FIXED_SPREAD = 0.30
TARGET = 20.0
STOP = 10.0
HORIZON_M1 = 480
EXPECTED_BASE_HASHES = {
    "M1": "dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2",
    "M5": "c47c0a136e8a953bf219bfbcb80a79ccacac3afb04a0ed6e825843eba143948d",
    "H1": "fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a",
    "H4": "5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def path_value(value: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(value)))).resolve()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    os.replace(tmp, path)


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
        return [{normalize_name(key): value for key, value in row.items()} for row in csv.DictReader(handle)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_name(value: Any) -> str:
    return str(value).strip().lower().replace("<", "").replace(">", "").replace("-", "_")


def parse_dt(value: Any) -> pd.Timestamp | None:
    if value in (None, "", "nan", "NaN", "NaT"):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    result = pd.Timestamp(parsed)
    if result.tzinfo is not None:
        result = result.tz_localize(None)
    return result


def pick(source: Mapping[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        value = source.get(name)
        if value not in (None, "", "nan", "NaN", "NaT"):
            return value
    return None


def load_config(path: Path) -> dict[str, Any]:
    config = read_json(path)
    if config.get("candidate_id") != CANDIDATE_ID:
        raise ValueError("Challenger candidate_id mismatch")
    if config.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Challenger contract_version mismatch")
    return config


def state_root(config: Mapping[str, Any]) -> Path:
    value = config.get("state_dir")
    if not isinstance(value, str) or not value:
        raise ValueError("state_dir is missing")
    root = path_value(value)
    if "gold_v19_shadow" in str(root).lower():
        raise ValueError("Challenger state_dir must not be the V19 state directory")
    return root


def logger_for(root: Path, name: str, filename: str) -> logging.Logger:
    (root / "logs").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
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
