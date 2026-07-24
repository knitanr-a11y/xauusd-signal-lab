from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import m9v_core as legacy

# Re-export the stable v1 research implementation. Only runtime-prefix/bootstrap
# semantics are changed in v2.
M9VContractError = legacy.M9VContractError
STAGE = legacy.STAGE
TIME_FORMAT = legacy.TIME_FORMAT
TIMEFRAME_SECONDS = legacy.TIMEFRAME_SECONDS
BRANCH_PRIORITY = legacy.BRANCH_PRIORITY
ARM_BRANCHES = legacy.ARM_BRANCHES
m9p = legacy.m9p
parse_time = legacy.parse_time
fmt_time = legacy.fmt_time
load_json = legacy.load_json
sha256_bytes = legacy.sha256_bytes
tail_snapshot = legacy.tail_snapshot
validate_contract = legacy.validate_contract
replay_episodes = legacy.replay_episodes

RUNTIME_CONTRACT_VERSION = "M9V_RUNTIME_V2_APPEND_SAFE_PREFIX"


def prefix_fingerprint_rows(path: Path, row_count: int) -> dict[str, Any]:
    if row_count <= 0:
        raise M9VContractError(f"invalid frozen prefix row count for {path.name}: {row_count}")
    digest = hashlib.sha256()
    count = 0
    first = last = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != m9p.HEADER:
            raise M9VContractError(f"unexpected header: {path.name}")
        for row in reader:
            if count >= row_count:
                break
            current = parse_time(row["time"])
            if first is None:
                first = current
            last = current
            count += 1
            canonical = "|".join(str(row[name]).strip() for name in m9p.HEADER).encode("utf-8")
            digest.update(canonical + b"\n")
    if count != row_count or first is None or last is None:
        raise M9VContractError(
            f"frozen prefix shortened for {path.name}: expected {row_count} rows, got {count}"
        )
    return {
        "row_count": count,
        "first_server_open": fmt_time(first),
        "last_server_open": fmt_time(last),
        "sha256": digest.hexdigest(),
    }


def validate_runtime_manifest(runtime: dict[str, Any], contract: dict[str, Any], contract_sha256: str) -> None:
    legacy.validate_runtime_manifest(runtime, contract, contract_sha256)
    if runtime.get("runtime_contract_version") != RUNTIME_CONTRACT_VERSION:
        raise M9VContractError(
            "obsolete or unexpected M9V runtime contract; archive invalid v1 start before reinitialization"
        )
    if not isinstance(runtime.get("frozen_row_prefixes"), dict):
        raise M9VContractError("missing v2 frozen_row_prefixes")


def audit(*, data_root: Path, contract: dict[str, Any], runtime: dict[str, Any], point: float) -> dict[str, Any]:
    contract_sha = sha256_bytes(
        json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    validate_runtime_manifest(runtime, contract, contract_sha)
    file_map = contract["data"]["live_file_map"]

    # Verify only rows that physically existed at initialization. Strictly
    # ascending later appends are allowed, even when a timeframe's bar-open
    # timestamp is <= the M1 start timestamp.
    by_filename: dict[str, dict[str, Any]] = {}
    for timeframe, filename in file_map.items():
        path = data_root / str(filename)
        if not path.is_file():
            raise M9VContractError(f"missing live GOLD CSV: {path}")
        frozen = runtime["frozen_row_prefixes"].get(timeframe)
        if not isinstance(frozen, dict):
            raise M9VContractError(f"missing frozen row-prefix fingerprint: {timeframe}")
        current = prefix_fingerprint_rows(path, int(frozen.get("row_count", 0)))
        if current != frozen:
            raise M9VContractError(f"frozen pre-start rows changed after M9V start: {timeframe}")
        by_filename[str(filename)] = frozen

    original_prefix = legacy.prefix_fingerprint
    original_replay = legacy.replay_episodes

    def compatibility_prefix(path: Path, cutoff: Any) -> dict[str, Any]:
        frozen = by_filename.get(path.name)
        if frozen is None:
            raise M9VContractError(f"unexpected M9V file during prefix compatibility check: {path.name}")
        return frozen

    def replay_with_frozen_bootstrap(bars: list[Any], timeframe: str, start: Any):
        episodes, _ = original_replay(bars, timeframe, start)
        frozen = runtime["frozen_row_prefixes"].get(timeframe)
        if not isinstance(frozen, dict):
            return episodes, original_replay(bars, timeframe, start)[1]
        frozen_count = int(frozen["row_count"])
        if len(bars) < frozen_count:
            raise M9VContractError(f"{timeframe} history became shorter than frozen runtime")
        _, frozen_audit = original_replay(bars[:frozen_count], timeframe, start)
        return episodes, frozen_audit

    # v1's audit body is reused after the v2 integrity checks above. The two
    # monkeypatches only adapt its old prefix/bootstrap comparison calls.
    runtime_compat = dict(runtime)
    runtime_compat["prefix_fingerprints"] = dict(runtime["frozen_row_prefixes"])
    legacy.prefix_fingerprint = compatibility_prefix
    legacy.replay_episodes = replay_with_frozen_bootstrap
    try:
        return legacy.audit(data_root=data_root, contract=contract, runtime=runtime_compat, point=point)
    finally:
        legacy.prefix_fingerprint = original_prefix
        legacy.replay_episodes = original_replay
