from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import Any

import pandas as pd

from live_data import FILE_BY_TF
from live_position import LiveM1Engine
from live_proposals_h1 import bstate_proposals
from live_proposals_m15 import acore_proposals, p18_proposals, w024_proposals
from live_admission import process_component
from live_store import DeferredRun, json_value, position_to_state


def has_live_files(path: Path) -> bool:
    return path.is_dir() and all(
        (path / filename).is_file() for filename in FILE_BY_TF.values()
    )


def find_live_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not has_live_files(path):
            raise FileNotFoundError(
                f"Live directory is missing one or more goldsharp CSVs: {path}"
            )
        return path

    configured = os.environ.get("GML1_LIVE_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if not has_live_files(path):
            raise FileNotFoundError(f"GML1_LIVE_DIR is invalid: {path}")
        return path

    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        raise FileNotFoundError(
            "APPDATA is unavailable; pass --live-dir or set GML1_LIVE_DIR"
        )
    terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
    matches: list[Path] = []
    if terminal_root.is_dir():
        for terminal in terminal_root.iterdir():
            candidate = terminal / "MQL5" / "Files"
            if has_live_files(candidate):
                matches.append(candidate.resolve())

    if not matches:
        raise FileNotFoundError(
            "No MT5 MQL5\\Files directory containing all goldsharp CSVs was found"
        )
    if len(matches) > 1:
        raise ValueError(
            "Multiple live CSV directories found; set GML1_LIVE_DIR explicitly: "
            + " | ".join(map(str, matches))
        )
    return matches[0]


def signatures(root: Path) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for timeframe, filename in FILE_BY_TF.items():
        stat = (root / filename).stat()
        result[timeframe] = {
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
        }
    return result


def acquire_lock(path: Path, stale_seconds: int = 900) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        age = max(0.0, time.time() - path.stat().st_mtime)
        if age <= stale_seconds:
            raise RuntimeError(
                f"BUSY: live one-shot lock exists ({age:.1f}s old): {path}"
            )
        path.unlink(missing_ok=True)

    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        payload = {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "created_epoch": time.time(),
        }
        os.write(descriptor, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(descriptor)


def ready_source_times(
    probe: dict[str, dict[str, pd.Timestamp]],
) -> tuple[pd.Timestamp, pd.Timestamp, list[str]]:
    m15_h4_limit = probe["H4"]["close"] + pd.Timedelta(hours=3, minutes=45)
    h1_d1_limit = probe["D1"]["close"] + pd.Timedelta(hours=23)
    ready_m15 = min(
        probe["M15"]["close"],
        probe["M1"]["open"],
        m15_h4_limit,
    )
    ready_h1 = min(
        probe["H1"]["close"],
        probe["M1"]["open"],
        h1_d1_limit,
    )
    waiting: list[str] = []
    if ready_m15 < probe["M15"]["close"]:
        if probe["M1"]["open"] < probe["M15"]["close"]:
            waiting.append("M15_WAIT_M1_ENTRY_ROW")
        if m15_h4_limit < probe["M15"]["close"]:
            waiting.append("M15_WAIT_H4_ASOF")
    if ready_h1 < probe["H1"]["close"]:
        if probe["M1"]["open"] < probe["H1"]["close"]:
            waiting.append("H1_WAIT_M1_ENTRY_ROW")
        if h1_d1_limit < probe["H1"]["close"]:
            waiting.append("H1_WAIT_D1_ASOF")
    return pd.Timestamp(ready_m15), pd.Timestamp(ready_h1), waiting


def processable_through(frame: pd.DataFrame, ready_time: pd.Timestamp) -> pd.Timestamp:
    eligible = frame.loc[
        frame["bar_close_time"] <= pd.Timestamp(ready_time),
        "bar_close_time",
    ]
    if eligible.empty:
        raise DeferredRun("No source bar is processable with current synchronized coverage")
    return pd.Timestamp(eligible.iloc[-1])


def earliest_m1_needed(
    state: dict[str, Any] | None,
    ready_m15: pd.Timestamp,
    ready_h1: pd.Timestamp,
) -> pd.Timestamp:
    if state is None:
        return min(ready_m15, ready_h1) - pd.Timedelta(hours=96)
    timestamps = [
        pd.Timestamp(state["last_processed"]["M15"]),
        pd.Timestamp(state["last_processed"]["H1"]),
    ]
    for payload in state.get("open_parent_positions", {}).values():
        if payload and payload.get("decision_time"):
            timestamps.append(pd.Timestamp(payload["decision_time"]))
    return min(timestamps) - pd.Timedelta(hours=2)


def has_open_position(state: dict[str, Any]) -> bool:
    return any(
        payload is not None
        for payload in state.get("open_parent_positions", {}).values()
    )


def observed_times(
    probe: dict[str, dict[str, pd.Timestamp]],
) -> dict[str, dict[str, str]]:
    return {
        timeframe: {
            key: value.strftime("%Y-%m-%d %H:%M:%S")
            for key, value in values.items()
        }
        for timeframe, values in probe.items()
    }


def latest_closed_from_probe(
    probe: dict[str, dict[str, pd.Timestamp]],
) -> dict[str, str]:
    return {
        timeframe: values["close"].strftime("%Y-%m-%d %H:%M:%S")
        for timeframe, values in probe.items()
    }


def hydrate_state(
    bars: dict[str, pd.DataFrame],
    engine: LiveM1Engine,
    latest_m15: pd.Timestamp,
    latest_h1: pd.Timestamp,
    now_text: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    hydration_start = min(latest_m15, latest_h1) - pd.Timedelta(hours=72)
    proposals = {
        "A_CORE": acore_proposals(bars, hydration_start),
        "P18": p18_proposals(bars, hydration_start),
        "W024A": w024_proposals(bars, hydration_start),
    }
    for comp in ("A_CORE", "P18", "W024A"):
        proposals[comp] = proposals[comp][
            proposals[comp]["bar_close_time"] <= latest_m15
        ].copy()

    b_events, due, origin = bstate_proposals(
        bars,
        hydration_start,
        latest_h1,
        None,
        None,
    )
    proposals["B_STATE"] = b_events

    positions: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for comp in ("A_CORE", "B_STATE", "P18", "W024A"):
        _, _, active, _ = process_component(
            comp,
            proposals[comp],
            None,
            engine,
            now_text,
        )
        if active is not None:
            active["candidate_key"] = None
        positions[comp] = position_to_state(active)
        counts[comp] = len(proposals[comp])

    return {
        "pending_reentry_due": json_value(due),
        "pending_origin": json_value(origin),
        "open_parent_positions": positions,
    }, counts
