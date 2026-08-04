from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .shadow_common import EXPECTED_BASE_HASHES, normalize_name, parse_dt, path_value, read_json, sha256_file


def resolve_data_sources(config: Mapping[str, Any]) -> dict[str, list[Path]]:
    source_cfg = config.get("data_sources")
    if not isinstance(source_cfg, dict):
        raise ValueError("data_sources config is missing")
    inherited: dict[str, Any] = {}
    if source_cfg.get("inherit_from_v19", True):
        v19_config = read_json(path_value(str(config["v19"]["local_config_path"])))
        inherited = v19_config.get("data_sources", {})
        if not isinstance(inherited, dict):
            inherited = {}
    result: dict[str, list[Path]] = {}
    for timeframe in ("M1", "M5", "H1", "H4"):
        explicit = source_cfg.get(timeframe)
        values = explicit if isinstance(explicit, list) and explicit else inherited.get(timeframe)
        if not isinstance(values, list) or not values:
            raise ValueError(f"No {timeframe} source paths are configured")
        paths = [path_value(str(value)) for value in values]
        missing = [str(path) for path in paths if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing {timeframe} sources: {missing}")
        result[timeframe] = paths
    return result


def validate_base_sources(sources: Mapping[str, list[Path]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for timeframe, expected in EXPECTED_BASE_HASHES.items():
        matches: list[str] = []
        observed: dict[str, str] = {}
        for path in sources[timeframe]:
            digest = sha256_file(path)
            observed[str(path)] = digest
            if digest == expected:
                matches.append(str(path))
        if len(matches) != 1:
            raise RuntimeError(
                f"DATA_V3_BASE_SOURCE_MISMATCH {timeframe}: expected exactly one source with SHA256 {expected}; observed={observed}"
            )
        report[timeframe] = {"expected_sha256": expected, "matched_path": matches[0], "observed": observed}
    return report


def _peek_last_line(path: Path) -> tuple[list[str], list[str]]:
    with path.open("rb") as handle:
        header_bytes = handle.readline()
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - 131072))
        tail = handle.read()
    header_text = header_bytes.decode("utf-8-sig", "strict").strip("\r\n")
    lines = [line for line in tail.decode("utf-8-sig", "strict").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Empty candle source: {path}")
    delimiter = ";" if header_text.count(";") >= max(header_text.count(","), header_text.count("\t")) else "," if header_text.count(",") >= header_text.count("\t") else "\t"
    return next(csv.reader([header_text], delimiter=delimiter)), next(csv.reader([lines[-1]], delimiter=delimiter))


def peek_last_timestamp(path: Path) -> pd.Timestamp:
    try:
        header, row = _peek_last_line(path)
        values = {normalize_name(key): value for key, value in zip(header, row)}
        if "date" in values and "time" in values and len(str(values["time"])) <= 12:
            raw = f"{values['date']} {values['time']}"
        else:
            raw = values.get("time") or values.get("datetime") or values.get("timestamp")
        parsed = parse_dt(raw)
        if parsed is None:
            raise ValueError("timestamp parse failed")
        return parsed
    except Exception:
        from .data_io import read_candle
        frame = read_candle(path)
        return pd.Timestamp(frame.time.iloc[-1])


def peek_latest_m1(sources: Mapping[str, list[Path]]) -> pd.Timestamp:
    return max(peek_last_timestamp(path) for path in sources["M1"])


def load_m1(sources: Mapping[str, list[Path]]) -> pd.DataFrame:
    from .data_io import read_union
    return read_union(sources["M1"])


def load_wave_data(sources: Mapping[str, list[Path]]) -> dict[str, pd.DataFrame]:
    from .data_io import derive_m15_from_m1, read_union
    data = {timeframe: read_union(sources[timeframe]) for timeframe in ("M1", "H1", "H4")}
    m1 = data["M1"]
    m15 = derive_m15_from_m1(m1)
    closed_through = pd.Timestamp(m1.time.iloc[-1]) + pd.Timedelta(minutes=1)
    data["M15"] = m15[m15.time + pd.Timedelta(minutes=15) <= closed_through].reset_index(drop=True)
    if data["M15"].empty:
        raise RuntimeError("No complete M15 bars can be derived from the full M1 union")
    return data


def research_timeline(data: Mapping[str, pd.DataFrame], score_ledger: pd.DataFrame) -> pd.DataFrame:
    from .candidate_engine import build_candidates
    from .contracts import ALLOWED_ENTRY_COLUMNS
    from .wave_state import build_wave_ledger

    router = score_ledger.copy()
    m1_index = pd.Index(pd.to_datetime(data["M1"].time))
    reproduced_idx = m1_index.get_indexer(pd.DatetimeIndex(router.entry_time))
    if (reproduced_idx < 0).any():
        first = pd.Timestamp(router.entry_time.iloc[int(np.flatnonzero(reproduced_idx < 0)[0])])
        raise RuntimeError(f"V19_SCORE_ENTRY_NOT_IN_DATA_V3_M1: {first}")
    if "entry_idx" in router.columns:
        mismatch = router.entry_idx.to_numpy(int) != reproduced_idx
        if mismatch.any():
            first = int(np.flatnonzero(mismatch)[0])
            raise RuntimeError(
                f"V19_SCORE_ENTRY_INDEX_MISMATCH at {router.entry_time.iloc[first]} "
                f"v19={int(router.entry_idx.iloc[first])} data_v3={int(reproduced_idx[first])}"
            )
    router["entry_idx"] = reproduced_idx.astype(int)
    wave = build_wave_ledger(router, dict(data))
    entry = pd.DataFrame(
        {
            "decision_dt": pd.to_datetime(wave.entry_time),
            "origin_id": wave.origin_id.astype(int),
            "entry_idx": wave.entry_idx.astype(int),
            "chosen_side": wave.chosen_side.astype(str),
            "chosen_rank": wave.chosen_rank.astype(float),
            "wave_state": wave.wave_state.astype(str),
            "episode_id": 0,
            "previous_decision_dt": pd.to_datetime(wave.entry_time).shift(),
        }
    ).loc[:, ALLOWED_ENTRY_COLUMNS]
    candidates, timeline = build_candidates(entry.copy())
    if len(candidates):
        timeline = timeline.merge(
            candidates[["decision_dt", "origin_id", "candidate_id"]],
            on=["decision_dt", "origin_id"],
            how="left",
            validate="one_to_one",
        )
    else:
        timeline["candidate_id"] = np.nan
    return timeline.sort_values(["decision_dt", "origin_id"]).reset_index(drop=True)
