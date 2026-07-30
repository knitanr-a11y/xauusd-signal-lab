from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

EXPECTED_INPUT_SHA256 = "b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
EXPECTED_INPUT_ROWS = 30_661
DEFAULT_INPUT = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv")
PACKAGE_NAME = "BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip"
FIXED_ZIP_DT = (2026, 7, 30, 0, 0, 0)
M15 = pd.Timedelta(minutes=15)

MACHINES = (
    ("TRACK_B_B3_L32_D025_W04_BREAK_RETEST_REACCEL", 32, 0.25, 4),
    ("TRACK_B_B3_L32_D025_W08_BREAK_RETEST_REACCEL", 32, 0.25, 8),
    ("TRACK_B_B3_L32_D050_W04_BREAK_RETEST_REACCEL", 32, 0.50, 4),
    ("TRACK_B_B3_L32_D050_W08_BREAK_RETEST_REACCEL", 32, 0.50, 8),
    ("TRACK_B_B3_L64_D025_W04_BREAK_RETEST_REACCEL", 64, 0.25, 4),
    ("TRACK_B_B3_L64_D025_W08_BREAK_RETEST_REACCEL", 64, 0.25, 8),
    ("TRACK_B_B3_L64_D050_W04_BREAK_RETEST_REACCEL", 64, 0.50, 4),
    ("TRACK_B_B3_L64_D050_W08_BREAK_RETEST_REACCEL", 64, 0.50, 8),
)

FORBIDDEN_OUTPUT_COLUMNS = {
    "return",
    "win_loss",
    "pf",
    "pnl",
    "mfe",
    "mae",
    "future_exit_result",
    "entry_price",
    "exit_price",
}


@dataclass(frozen=True)
class MachineSpec:
    machine_id: str
    lookback: int
    displacement_atr: float
    retest_deadline: int


@dataclass
class RuntimeState:
    state: str = "IDLE"
    direction: str | None = None
    breakout_idx: int | None = None
    breakout_time: pd.Timestamp | None = None
    level: float | None = None
    frozen_atr: float | None = None
    retest_idx: int | None = None
    retest_time: pd.Timestamp | None = None
    entry_idx: int | None = None
    entry_time: pd.Timestamp | None = None
    breakout_origin_time: pd.Timestamp | None = None
    retest_origin_time: pd.Timestamp | None = None

    def clear(self) -> None:
        self.__dict__.update(RuntimeState().__dict__)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _prefix_candidates(raw: bytes, expected_rows: int) -> Iterable[bytes]:
    lines = raw.splitlines(keepends=True)
    need = expected_rows + 1
    if len(lines) < need:
        return ()
    prefix = b"".join(lines[:need])
    candidates = [prefix]
    if prefix.endswith(b"\r\n"):
        candidates.append(prefix[:-2])
    elif prefix.endswith((b"\n", b"\r")):
        candidates.append(prefix[:-1])
    return candidates


def resolve_frozen_input(source: Path, work_dir: Path, allow_prefix_rehydrate: bool) -> tuple[Path, dict[str, Any]]:
    if not source.exists():
        raise FileNotFoundError(f"BCR13 input not found: {source}")
    actual_sha = sha256_file(source)
    if actual_sha == EXPECTED_INPUT_SHA256:
        return source, {
            "source_path": str(source),
            "source_sha256": actual_sha,
            "frozen_sha256": actual_sha,
            "prefix_rehydrated": False,
        }
    if not allow_prefix_rehydrate:
        raise ValueError(
            "Input SHA mismatch. Supply the exact frozen snapshot or rerun with "
            "--allow-prefix-rehydrate for an append-only source; a prefix is accepted only if its SHA exactly matches."
        )
    raw = source.read_bytes()
    work_dir.mkdir(parents=True, exist_ok=True)
    for candidate in _prefix_candidates(raw, EXPECTED_INPUT_ROWS):
        if sha256_bytes(candidate) == EXPECTED_INPUT_SHA256:
            out = work_dir / "frozen_btc_m15_snapshot.csv"
            out.write_bytes(candidate)
            return out, {
                "source_path": str(source),
                "source_sha256": actual_sha,
                "frozen_sha256": EXPECTED_INPUT_SHA256,
                "prefix_rehydrated": True,
                "prefix_rows": EXPECTED_INPUT_ROWS,
            }
    raise ValueError(
        "Input SHA mismatch and no exact append-only prefix reproduced the frozen SHA. "
        "No nearest file, row interpolation, or similar-file fallback is permitted."
    )


def read_m15(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [str(c).strip().lower().lstrip("\ufeff") for c in df.columns]
    aliases = {"datetime": "time", "date_time": "time", "timestamp": "time"}
    df = df.rename(columns={c: aliases.get(c, c) for c in df.columns})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required M15 columns: {missing}; got {list(df.columns)}")
    df = df[required].copy()
    df["time"] = pd.to_datetime(df["time"], errors="raise")
    if getattr(df["time"].dt, "tz", None) is not None:
        raise ValueError("BCR13 requires naive MT5 broker-server timestamps, not timezone-aware timestamps")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
    if len(df) != EXPECTED_INPUT_ROWS:
        raise ValueError(f"Frozen row-count mismatch: expected {EXPECTED_INPUT_ROWS}, got {len(df)}")
    if df["time"].duplicated().any():
        dup = df.loc[df["time"].duplicated(), "time"].iloc[0]
        raise ValueError(f"Duplicate M15 open timestamp: {dup}")
    if not df["time"].is_monotonic_increasing:
        raise ValueError("M15 rows are not strictly increasing by time; no implicit sorting is permitted")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("OHLC integrity failure: high below open/close/low")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("OHLC integrity failure: low above open/close/high")
    return add_causal_features(df)


def add_causal_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    gap = out["time"].diff().ne(M15)
    gap.iloc[0] = True
    out["segment_id"] = gap.cumsum().astype(int)
    out["segment_pos"] = out.groupby("segment_id").cumcount().astype(int)
    out["atr14"] = np.nan
    for _, idx in out.groupby("segment_id", sort=False).groups.items():
        positions = np.asarray(list(idx), dtype=int)
        h = out.loc[positions, "high"].to_numpy(float)
        l = out.loc[positions, "low"].to_numpy(float)
        c = out.loc[positions, "close"].to_numpy(float)
        tr = np.empty(len(positions), dtype=float)
        tr[0] = h[0] - l[0]
        if len(positions) > 1:
            prev = c[:-1]
            tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - prev), np.abs(l[1:] - prev)])
        atr = np.full(len(positions), np.nan, dtype=float)
        if len(positions) >= 14:
            atr[13] = float(np.mean(tr[:14]))
            for k in range(14, len(positions)):
                atr[k] = (atr[k - 1] * 13.0 + tr[k]) / 14.0
        out.loc[positions, "atr14"] = atr
        for lookback in (32, 64):
            highs = pd.Series(h, index=positions).rolling(lookback, min_periods=lookback).max().shift(1)
            lows = pd.Series(l, index=positions).rolling(lookback, min_periods=lookback).min().shift(1)
            out.loc[positions, f"upper_{lookback}"] = highs.to_numpy()
            out.loc[positions, f"lower_{lookback}"] = lows.to_numpy()
    return out


def _bars_between(later: pd.Timestamp, earlier: pd.Timestamp) -> int:
    seconds = (later - earlier).total_seconds()
    return int(round(seconds / 900.0))


def _breakout_flags(df: pd.DataFrame, j: int, spec: MachineSpec) -> tuple[bool, bool, float, float, float]:
    if j <= 0:
        return False, False, math.nan, math.nan, math.nan
    atr = float(df.at[j - 1, "atr14"])
    upper = float(df.at[j, f"upper_{spec.lookback}"])
    lower = float(df.at[j, f"lower_{spec.lookback}"])
    if not (math.isfinite(atr) and atr > 0 and math.isfinite(upper) and math.isfinite(lower)):
        return False, False, atr, upper, lower
    o = float(df.at[j, "open"])
    c = float(df.at[j, "close"])
    long_flag = c >= upper + spec.displacement_atr * atr and c > o and c - o >= 0.25 * atr
    short_flag = c <= lower - spec.displacement_atr * atr and c < o and o - c >= 0.25 * atr
    return bool(long_flag), bool(short_flag), atr, upper, lower


def _is_retest(df: pd.DataFrame, j: int, state: RuntimeState) -> bool:
    a = float(state.frozen_atr)
    level = float(state.level)
    if state.direction == "LONG":
        return float(df.at[j, "low"]) <= level + 0.25 * a and float(df.at[j, "close"]) >= level - 0.25 * a
    return float(df.at[j, "high"]) >= level - 0.25 * a and float(df.at[j, "close"]) <= level + 0.25 * a


def _is_invalidated(df: pd.DataFrame, j: int, state: RuntimeState) -> bool:
    a = float(state.frozen_atr)
    level = float(state.level)
    c = float(df.at[j, "close"])
    return c < level - 0.50 * a if state.direction == "LONG" else c > level + 0.50 * a


def _is_reacceleration(df: pd.DataFrame, j: int, state: RuntimeState) -> bool:
    assert state.retest_idx is not None
    if j <= state.retest_idx:
        return False
    a = float(state.frozen_atr)
    level = float(state.level)
    o = float(df.at[j, "open"])
    c = float(df.at[j, "close"])
    if state.direction == "LONG":
        prior_max = float(df.loc[state.retest_idx : j - 1, "high"].max())
        return c >= level + 0.25 * a and c > o and c - o >= 0.25 * a and c > prior_max
    prior_min = float(df.loc[state.retest_idx : j - 1, "low"].min())
    return c <= level - 0.25 * a and c < o and o - c >= 0.25 * a and c < prior_min


def _transition(transitions: list[dict[str, Any]], spec: MachineSpec, t: pd.Timestamp, old: str, new: str, event: str, direction: str | None, detail: str = "") -> None:
    transitions.append({
        "machine_id": spec.machine_id,
        "boundary_time": t.isoformat(sep=" "),
        "state_before": old,
        "state_after": new,
        "event": event,
        "direction": direction or "",
        "detail": detail,
    })


def replay_machine(df: pd.DataFrame, spec: MachineSpec) -> dict[str, Any]:
    times = list(pd.to_datetime(df["time"]))
    time_to_idx = {t: i for i, t in enumerate(times)}
    state = RuntimeState()
    counts: Counter[str] = Counter()
    transitions: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    closed_holdings: list[int] = []
    pending_ages: list[int] = []
    entry_months: Counter[str] = Counter()
    active_intervals = 0
    eligible_intervals = max(0, len(df) - 1)
    entry_count = 0
    closed_by_direction: Counter[str] = Counter()
    open_by_direction: Counter[str] = Counter()

    for i in range(1, len(df)):
        t = times[i]
        exact_prev = t - M15
        j = time_to_idx.get(exact_prev)
        entered_this_boundary = False
        exited_this_boundary = False

        if j is None:
            counts["decision_boundary_missing_exact_previous"] += 1
            if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
                counts["active_decision_unavailable_gap"] += 1
            elif state.state != "IDLE":
                last_j = i - 1
                if state.state in {"LONG_RETEST_SEEN", "SHORT_RETEST_SEEN"} and state.retest_time is not None:
                    age = _bars_between(times[last_j], state.retest_time)
                    if 1 <= age <= 4 and _is_reacceleration(df, last_j, state):
                        counts["reacceleration"] += 1
                        counts["no_trade_exact_entry_missing"] += 1
                        old = state.state
                        _transition(transitions, spec, t, old, "IDLE", "NO_TRADE_EXACT_ENTRY_MISSING", state.direction)
                        pending_ages.append(_bars_between(times[last_j], state.breakout_time))
                        state.clear()
                    else:
                        counts["cancel_gap_in_sequence"] += 1
                        old = state.state
                        _transition(transitions, spec, t, old, "IDLE", "CANCEL_GAP_IN_SEQUENCE", state.direction)
                        if state.breakout_time is not None:
                            pending_ages.append(_bars_between(times[last_j], state.breakout_time))
                        state.clear()
                else:
                    counts["cancel_gap_in_sequence"] += 1
                    old = state.state
                    _transition(transitions, spec, t, old, "IDLE", "CANCEL_GAP_IN_SEQUENCE", state.direction)
                    if state.breakout_time is not None:
                        pending_ages.append(_bars_between(times[i - 1], state.breakout_time))
                    state.clear()
            if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
                active_intervals += 1
            continue

        if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
            assert state.entry_time is not None and state.level is not None and state.frozen_atr is not None
            c_prev = float(df.at[j, "close"])
            fail = c_prev < state.level - 0.50 * state.frozen_atr if state.direction == "LONG" else c_prev > state.level + 0.50 * state.frozen_atr
            if fail:
                holding = _bars_between(t, state.entry_time)
                closed_holdings.append(holding)
                closed_by_direction[state.direction] += 1
                episodes.append({
                    "machine_id": spec.machine_id,
                    "direction": state.direction,
                    "breakout_time": state.breakout_origin_time.isoformat(sep=" "),
                    "retest_time": state.retest_origin_time.isoformat(sep=" "),
                    "reacceleration_time": times[state.entry_idx - 1].isoformat(sep=" ") if state.entry_idx else "",
                    "entry_time": state.entry_time.isoformat(sep=" "),
                    "exit_time": t.isoformat(sep=" "),
                    "holding_bars": holding,
                    "endpoint_open": False,
                    "exit_reason": "STRUCTURAL_THESIS_FAILURE",
                })
                counts["exit_structural_thesis_failure"] += 1
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "EXIT_STRUCTURAL_THESIS_FAILURE", direction)
                state.clear()
                exited_this_boundary = True
            if not exited_this_boundary:
                active_intervals += 1
            continue

        if state.state in {"LONG_BREAKOUT_ARMED", "SHORT_BREAKOUT_ARMED"}:
            assert state.breakout_time is not None
            age = _bars_between(times[j], state.breakout_time)
            if _is_invalidated(df, j, state):
                counts["cancel_preentry_invalidation"] += 1
                pending_ages.append(age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_PREENTRY_INVALIDATION", direction)
                state.clear()
            elif age > spec.retest_deadline:
                counts["cancel_retest_expired"] += 1
                pending_ages.append(age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_RETEST_EXPIRED", direction)
                state.clear()
            elif 1 <= age <= spec.retest_deadline and _is_retest(df, j, state):
                counts["retest"] += 1
                old = state.state
                state.retest_idx = j
                state.retest_time = times[j]
                state.retest_origin_time = times[j]
                state.state = "LONG_RETEST_SEEN" if state.direction == "LONG" else "SHORT_RETEST_SEEN"
                _transition(transitions, spec, t, old, state.state, "RETEST", state.direction)
            elif age == spec.retest_deadline:
                counts["cancel_retest_expired"] += 1
                pending_ages.append(age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_RETEST_EXPIRED", direction)
                state.clear()

        if state.state in {"LONG_RETEST_SEEN", "SHORT_RETEST_SEEN"}:
            assert state.retest_time is not None and state.breakout_time is not None
            age_after_retest = _bars_between(times[j], state.retest_time)
            total_age = _bars_between(times[j], state.breakout_time)
            if _is_invalidated(df, j, state):
                counts["cancel_preentry_invalidation"] += 1
                pending_ages.append(total_age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_PREENTRY_INVALIDATION", direction)
                state.clear()
            elif age_after_retest > 4:
                counts["cancel_reacceleration_expired"] += 1
                pending_ages.append(total_age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_REACCELERATION_EXPIRED", direction)
                state.clear()
            elif 1 <= age_after_retest <= 4 and _is_reacceleration(df, j, state):
                counts["reacceleration"] += 1
                counts["entry"] += 1
                counts[f"entry_{state.direction.lower()}"] += 1
                entry_count += 1
                entry_months[t.strftime("%Y-%m")] += 1
                old = state.state
                state.entry_idx = i
                state.entry_time = t
                state.state = "ACTIVE_LONG" if state.direction == "LONG" else "ACTIVE_SHORT"
                _transition(transitions, spec, t, old, state.state, "ENTRY_EXACT_NEXT_OPEN", state.direction)
                entered_this_boundary = True
            elif age_after_retest == 4:
                counts["cancel_reacceleration_expired"] += 1
                pending_ages.append(total_age)
                old = state.state
                direction = state.direction
                _transition(transitions, spec, t, old, "IDLE", "CANCEL_REACCELERATION_EXPIRED", direction)
                state.clear()

        if state.state == "IDLE" and not entered_this_boundary:
            long_flag, short_flag, atr, upper, lower = _breakout_flags(df, j, spec)
            if long_flag and short_flag:
                counts["simultaneous_breakout_conflict"] += 1
                _transition(transitions, spec, t, "IDLE", "IDLE", "SIMULTANEOUS_BREAKOUT_NO_TRANSITION", None)
            elif long_flag or short_flag:
                direction = "LONG" if long_flag else "SHORT"
                counts["breakout"] += 1
                counts[f"breakout_{direction.lower()}"] += 1
                state.state = "LONG_BREAKOUT_ARMED" if direction == "LONG" else "SHORT_BREAKOUT_ARMED"
                state.direction = direction
                state.breakout_idx = j
                state.breakout_time = times[j]
                state.breakout_origin_time = times[j]
                state.level = upper if direction == "LONG" else lower
                state.frozen_atr = atr
                _transition(transitions, spec, t, "IDLE", state.state, "BREAKOUT_ARMED", direction)

        if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
            active_intervals += 1

    endpoint_open = 0
    if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
        endpoint_open = 1
        open_by_direction[state.direction] += 1
        episodes.append({
            "machine_id": spec.machine_id,
            "direction": state.direction,
            "breakout_time": state.breakout_origin_time.isoformat(sep=" "),
            "retest_time": state.retest_origin_time.isoformat(sep=" "),
            "reacceleration_time": times[state.entry_idx - 1].isoformat(sep=" ") if state.entry_idx else "",
            "entry_time": state.entry_time.isoformat(sep=" "),
            "exit_time": "",
            "holding_bars": _bars_between(times[-1] + M15, state.entry_time),
            "endpoint_open": True,
            "exit_reason": "ENDPOINT_OPEN_NOT_FORCE_CLOSED",
        })

    closed = len(closed_holdings)
    distinct_months = len(entry_months)
    max_month_share = max(entry_months.values(), default=0) / entry_count if entry_count else 0.0
    p90 = float(np.percentile(closed_holdings, 90)) if closed_holdings else math.inf
    max_holding = max(closed_holdings, default=math.inf)
    occupancy = active_intervals / eligible_intervals if eligible_intervals else 0.0
    state_integrity = (
        entry_count == closed + endpoint_open
        and endpoint_open <= 1
        and not any(e["holding_bars"] < 0 for e in episodes)
        and len({(e["entry_time"], e["machine_id"]) for e in episodes}) == len(episodes)
    )
    gate_checks = {
        "minimum_closed_episodes_total": closed >= 50,
        "minimum_closed_episodes_each_direction": closed_by_direction["LONG"] >= 20 and closed_by_direction["SHORT"] >= 20,
        "minimum_entry_months": distinct_months >= 6,
        "maximum_single_month_entry_share": max_month_share <= 0.35,
        "maximum_p90_holding_bars": p90 <= 384,
        "maximum_holding_bars": max_holding <= 1500,
        "maximum_endpoint_open_episodes": endpoint_open <= 1,
        "state_integrity_required": state_integrity,
        "fallback_used_allowed": True,
    }
    pass_capability = all(gate_checks.values())
    metrics = {
        "machine_id": spec.machine_id,
        "lookback_L": spec.lookback,
        "breakout_displacement_D_ATR": spec.displacement_atr,
        "retest_deadline_W_bars": spec.retest_deadline,
        "breakouts": counts["breakout"],
        "retests": counts["retest"],
        "reaccelerations": counts["reacceleration"],
        "entries": entry_count,
        "closed_episodes": closed,
        "closed_long": closed_by_direction["LONG"],
        "closed_short": closed_by_direction["SHORT"],
        "endpoint_open_episodes": endpoint_open,
        "endpoint_open_long": open_by_direction["LONG"],
        "endpoint_open_short": open_by_direction["SHORT"],
        "distinct_entry_months": distinct_months,
        "maximum_single_month_entry_share": max_month_share,
        "holding_p50_bars": float(np.percentile(closed_holdings, 50)) if closed_holdings else None,
        "holding_p90_bars": None if math.isinf(p90) else p90,
        "holding_max_bars": None if math.isinf(max_holding) else int(max_holding),
        "position_occupancy": occupancy,
        "pending_age_p90_bars": float(np.percentile(pending_ages, 90)) if pending_ages else None,
        "pending_age_max_bars": max(pending_ages, default=None),
        "gap_cancel_count": counts["cancel_gap_in_sequence"],
        "exact_entry_missing_count": counts["no_trade_exact_entry_missing"],
        "active_gap_count": counts["active_decision_unavailable_gap"],
        "simultaneous_conflict_count": counts["simultaneous_breakout_conflict"],
        "state_integrity": state_integrity,
        "fallback_or_interpolation_used": False,
        "capability_pass": pass_capability,
    }
    return {
        "spec": spec,
        "counts": counts,
        "metrics": metrics,
        "gate_checks": gate_checks,
        "transitions": transitions,
        "episodes": episodes,
        "monthly": dict(sorted(entry_months.items())),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    bad = FORBIDDEN_OUTPUT_COLUMNS.intersection({c.lower() for c in columns})
    if bad:
        raise AssertionError(f"Forbidden BCR13 output columns: {sorted(bad)}")
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 12)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _deterministic_zip(output_dir: Path, members: list[Path]) -> Path:
    zip_path = output_dir / PACKAGE_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(members, key=lambda p: p.name):
            info = zipfile.ZipInfo(path.name, date_time=FIXED_ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path


def validate_contract(contract_path: Path) -> dict[str, Any]:
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if payload["frozen_input"]["BTC_M15_sha256"] != EXPECTED_INPUT_SHA256:
        raise ValueError("BCR12 contract input SHA does not match implementation constant")
    actual = [(m["id"], int(m["L"]), float(m["D"]), int(m["W"])) for m in payload["grammar"]["machines"]]
    if actual != list(MACHINES):
        raise ValueError("BCR12 frozen eight-machine grammar mismatch")
    if payload["authorization"].get("B3_outcome_access") is not False:
        raise ValueError("BCR12 contract unexpectedly permits B3 outcome access")
    return payload


def build_once(input_path: Path, contract_path: Path, output_dir: Path, allow_prefix_rehydrate: bool) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="bcr13_input_") as td:
        frozen_path, input_meta = resolve_frozen_input(input_path, Path(td), allow_prefix_rehydrate)
        contract = validate_contract(contract_path)
        df = read_m15(frozen_path)

    results = [replay_machine(df, MachineSpec(*m)) for m in MACHINES]
    machine_rows = [r["metrics"] for r in results]
    event_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    for r in results:
        mid = r["spec"].machine_id
        for event, count in sorted(r["counts"].items()):
            event_rows.append({"machine_id": mid, "event": event, "count": count})
        for month, count in r["monthly"].items():
            monthly_rows.append({"machine_id": mid, "entry_month": month, "entries": count})
        transitions.extend(r["transitions"])
        episodes.extend(r["episodes"])
        for check, passed in r["gate_checks"].items():
            gate_rows.append({"machine_id": mid, "gate_check": check, "passed": bool(passed)})

    machine_columns = list(machine_rows[0].keys())
    _write_csv(output_dir / "bcr13_machine_metrics.csv", machine_rows, machine_columns)
    _write_csv(output_dir / "bcr13_event_counts.csv", event_rows, ["machine_id", "event", "count"])
    _write_csv(output_dir / "bcr13_monthly_entries.csv", monthly_rows, ["machine_id", "entry_month", "entries"])
    _write_csv(output_dir / "bcr13_gate_checks.csv", gate_rows, ["machine_id", "gate_check", "passed"])
    _write_csv(output_dir / "bcr13_transition_ledger.csv", transitions, ["machine_id", "boundary_time", "state_before", "state_after", "event", "direction", "detail"])
    _write_csv(output_dir / "bcr13_episode_ledger.csv", episodes, ["machine_id", "direction", "breakout_time", "retest_time", "reacceleration_time", "entry_time", "exit_time", "holding_bars", "endpoint_open", "exit_reason"])

    summary = {
        "project": "BTC_CANDIDATE_RESEARCH_REDESIGN",
        "stage": "BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT",
        "status": "BCR13_LABEL_FREE_AUDIT_OUTPUT_BUILT_NO_VALUE_FIELDS",
        "branch": "feature/btc-fresh-forward-research",
        "input": input_meta,
        "input_rows": len(df),
        "input_first_time": df["time"].iloc[0].isoformat(sep=" "),
        "input_last_time": df["time"].iloc[-1].isoformat(sep=" "),
        "contract_stage": contract["stage"],
        "machine_count": len(results),
        "all_eight_reported": len(results) == 8,
        "capability_pass_count": sum(bool(r["metrics"]["capability_pass"]) for r in results),
        "capability_fail_count": sum(not bool(r["metrics"]["capability_pass"]) for r in results),
        "outcome_fields_opened": False,
        "value_evaluation_performed": False,
        "candidate_promoted": False,
        "portfolio_selected": False,
        "prospective_start_set": False,
        "shadow_started": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "machine_metrics": machine_rows,
    }
    _json_dump(output_dir / "bcr13_summary.json", _normalize_json_value(summary))

    manifest_files = []
    for path in sorted(output_dir.glob("bcr13_*")):
        manifest_files.append({"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "stage": "BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT",
        "source_sha256": EXPECTED_INPUT_SHA256,
        "contract_sha256": sha256_file(contract_path),
        "files": manifest_files,
        "deterministic_zip_timestamp": FIXED_ZIP_DT,
        "forbidden_value_fields_present": False,
    }
    _json_dump(output_dir / "manifest.json", manifest)
    members = [p for p in output_dir.iterdir() if p.is_file() and p.name != PACKAGE_NAME]
    zip_path = _deterministic_zip(output_dir, members)
    package_sha = sha256_file(zip_path)
    (output_dir / "package_sha256.txt").write_text(f"{package_sha}  {PACKAGE_NAME}\n", encoding="ascii")
    return {"package_path": str(zip_path), "package_sha256": package_sha, "summary": summary}


def build_with_repeat(input_path: Path, contract_path: Path, output_dir: Path, allow_prefix_rehydrate: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="bcr13_repeat_") as td:
        root = Path(td)
        first = build_once(input_path, contract_path, root / "run_a", allow_prefix_rehydrate)
        second = build_once(input_path, contract_path, root / "run_b", allow_prefix_rehydrate)
        if first["package_sha256"] != second["package_sha256"]:
            raise RuntimeError("Deterministic repeat package SHA mismatch")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(root / "run_a", output_dir)
        repeat = {
            "deterministic_repeat_match": True,
            "package_sha256_run_a": first["package_sha256"],
            "package_sha256_run_b": second["package_sha256"],
        }
        _json_dump(output_dir / "deterministic_repeat.json", repeat)
        return {**first, **repeat, "published_output_dir": str(output_dir)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BCR13 outcome-blind B3 density and state-machine audit")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-prefix-rehydrate", action="store_true")
    parser.add_argument("--repeat-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat_check:
        result = build_with_repeat(args.input, args.contract, args.output_dir, args.allow_prefix_rehydrate)
    else:
        result = build_once(args.input, args.contract, args.output_dir, args.allow_prefix_rehydrate)
    print(json.dumps(_normalize_json_value(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
