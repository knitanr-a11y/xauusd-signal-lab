from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

TIMEFRAME_MINUTES: Mapping[str, int] = {
    "m1": 1,
    "m5": 5,
    "m15": 15,
    "h1": 60,
    "h4": 240,
    "d1": 1440,
}

PARITY_KEY_COLUMNS: tuple[str, ...] = (
    "candidate_key",
    "event_type",
    "direction",
    "anchor_time",
    "decision_time",
    "entry_time",
    "entry_price_source_time",
    "state_version",
)


class LiveReproducibilityError(RuntimeError):
    """Raised when a candidate cannot be reproduced from closed bars only."""


@dataclass(frozen=True)
class CandidateEvent:
    candidate_key: str
    event_type: str
    direction: str
    anchor_time: pd.Timestamp
    decision_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry_price_source_time: pd.Timestamp
    state_version: str
    anchor_price: float | None = None
    threshold_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def candidate_key(
    event_type: str,
    direction: str,
    anchor_time: pd.Timestamp,
    decision_time: pd.Timestamp,
) -> str:
    """Create a deterministic candidate key without using row indices."""
    raw = "|".join(
        [
            str(event_type).strip().upper(),
            str(direction).strip().upper(),
            pd.Timestamp(anchor_time).isoformat(),
            pd.Timestamp(decision_time).isoformat(),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()[:24]


def attach_source_close_time(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    if "time" not in df.columns:
        raise LiveReproducibilityError("time column is required")
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], errors="raise")
    expected = out["time"] + pd.to_timedelta(TIMEFRAME_MINUTES[timeframe], unit="m")
    if "source_close_time" in out.columns:
        actual = pd.to_datetime(out["source_close_time"], errors="raise")
        if not actual.equals(expected):
            bad = int((actual != expected).sum())
            raise LiveReproducibilityError(
                f"source_close_time contract mismatch for {timeframe}: {bad} rows"
            )
    out["source_close_time"] = expected
    return out


def closed_rows_asof(df: pd.DataFrame, decision_time: pd.Timestamp) -> pd.DataFrame:
    if "source_close_time" not in df.columns:
        raise LiveReproducibilityError("source_close_time column is required")
    t = pd.Timestamp(decision_time)
    out = df[pd.to_datetime(df["source_close_time"]) <= t].copy()
    if (pd.to_datetime(out["source_close_time"]) > t).any():
        raise LiveReproducibilityError("future source row leaked into closed_rows_asof")
    return out


def assert_event_source_known(
    events: pd.DataFrame,
    source_close_columns: Sequence[str] = ("source_close_time",),
) -> None:
    if events.empty:
        return
    if "decision_time" not in events.columns:
        raise LiveReproducibilityError("events need decision_time")
    decision = pd.to_datetime(events["decision_time"], errors="raise")
    for col in source_close_columns:
        if col not in events.columns:
            continue
        source_close = pd.to_datetime(events[col], errors="coerce")
        invalid = source_close.notna() & (source_close > decision)
        if invalid.any():
            first = events.loc[invalid].iloc[0]
            raise LiveReproducibilityError(
                f"lookahead detected in {col}: source={first[col]} decision={first['decision_time']}"
            )


def normalize_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        out = events.copy()
        for col in PARITY_KEY_COLUMNS:
            if col not in out.columns:
                out[col] = pd.Series(dtype="object")
        return out.sort_values(list(PARITY_KEY_COLUMNS)).reset_index(drop=True)
    missing = [c for c in PARITY_KEY_COLUMNS if c not in events.columns]
    if missing:
        raise LiveReproducibilityError(f"event parity columns missing: {missing}")
    out = events.copy()
    for col in (
        "anchor_time",
        "decision_time",
        "entry_time",
        "entry_price_source_time",
    ):
        out[col] = pd.to_datetime(out[col], errors="raise")
    if out["candidate_key"].duplicated().any():
        dups = out.loc[out["candidate_key"].duplicated(keep=False), "candidate_key"].tolist()
        raise LiveReproducibilityError(f"duplicate candidate_key: {dups[:5]}")
    if (out["entry_time"] < out["decision_time"]).any():
        raise LiveReproducibilityError("entry_time earlier than decision_time")
    if (out["entry_price_source_time"] != out["entry_time"]).any():
        raise LiveReproducibilityError(
            "entry_price_source_time must equal the M1 OPEN entry_time"
        )
    return out.sort_values(list(PARITY_KEY_COLUMNS)).reset_index(drop=True)


def assert_batch_streaming_parity(
    batch_events: pd.DataFrame,
    streaming_events: pd.DataFrame,
    numeric_columns: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    left = normalize_events(batch_events)
    right = normalize_events(streaming_events)
    if len(left) != len(right):
        only_batch = sorted(set(left["candidate_key"]) - set(right["candidate_key"]))
        only_stream = sorted(set(right["candidate_key"]) - set(left["candidate_key"]))
        raise LiveReproducibilityError(
            f"event count mismatch batch={len(left)} streaming={len(right)} "
            f"only_batch={only_batch[:5]} only_stream={only_stream[:5]}"
        )
    if len(left) == 0:
        return {
            "status": "PASS",
            "events": 0,
            "candidate_key_duplicates": 0,
            "tolerance": float(tolerance),
        }
    for col in PARITY_KEY_COLUMNS:
        if not left[col].equals(right[col]):
            mismatch = np.flatnonzero((left[col] != right[col]).to_numpy())
            i = int(mismatch[0]) if len(mismatch) else 0
            raise LiveReproducibilityError(
                f"parity mismatch in {col}: batch={left.iloc[i][col]} "
                f"streaming={right.iloc[i][col]}"
            )
    for col in numeric_columns:
        if len(left) == 0:
            continue
        if col not in left.columns or col not in right.columns:
            raise LiveReproducibilityError(f"numeric parity column missing: {col}")
        a = pd.to_numeric(left[col], errors="raise").to_numpy(float)
        b = pd.to_numeric(right[col], errors="raise").to_numpy(float)
        if not np.allclose(a, b, rtol=0.0, atol=tolerance, equal_nan=True):
            i = int(np.flatnonzero(~np.isclose(a, b, rtol=0.0, atol=tolerance, equal_nan=True))[0])
            raise LiveReproducibilityError(
                f"numeric parity mismatch in {col}: batch={a[i]} streaming={b[i]}"
            )
    return {
        "status": "PASS",
        "events": int(len(left)),
        "candidate_key_duplicates": 0,
        "tolerance": float(tolerance),
    }


def assert_prefix_invariance(
    full_events: pd.DataFrame,
    prefix_detector: Callable[[pd.Timestamp], pd.DataFrame],
    checkpoints: Iterable[pd.Timestamp],
    numeric_columns: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    full = normalize_events(full_events)
    checked = 0
    for checkpoint in checkpoints:
        t = pd.Timestamp(checkpoint)
        expected = full[full["decision_time"] <= t].copy()
        actual = prefix_detector(t)
        assert_batch_streaming_parity(
            expected,
            actual,
            numeric_columns=numeric_columns,
            tolerance=tolerance,
        )
        checked += 1
    return {"status": "PASS", "checkpoints": checked}


def require_entry_m1(
    events: pd.DataFrame,
    m1: pd.DataFrame,
    entry_price_column: str = "open",
) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    if "time" not in m1.columns or entry_price_column not in m1.columns:
        raise LiveReproducibilityError("M1 time/open columns are required")
    price = m1.set_index(pd.to_datetime(m1["time"]))[entry_price_column]
    out = events.copy()
    out["entry_price"] = pd.to_datetime(out["entry_time"]).map(price)
    out["entry_price_source_time"] = out["entry_time"]
    return out[out["entry_price"].notna()].copy().reset_index(drop=True)


def serialize_state_snapshot(path: str | Path, state: Mapping[str, Any]) -> None:
    import json

    def default(value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return {"__timestamp__": value.isoformat()}
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)

    Path(path).write_text(
        json.dumps(dict(state), ensure_ascii=False, sort_keys=True, default=default),
        encoding="utf-8",
    )


def load_state_snapshot(path: str | Path) -> dict[str, Any]:
    import json

    def hook(value: dict[str, Any]) -> Any:
        if set(value) == {"__timestamp__"}:
            return pd.Timestamp(value["__timestamp__"])
        return value

    return json.loads(Path(path).read_text(encoding="utf-8"), object_hook=hook)
