from __future__ import annotations

from pathlib import Path
from typing import Any
import os

import numpy as np
import pandas as pd

COST = 22.5
MINUTES = {"H4": 240, "M15": 15, "M5": 5, "M1": 1}
M1_SOURCE_ID = "H4_M15_M1__EMA_STACK_SLOPE_ADX18__ANTICIPATE_BELOW_050__TWO_BAR_REVERSAL__BASE__LONG__SETUP_ATR050__UPPER_TREND_END"
M5_SOURCE_ID = "H4_M15_M5__EMA_STACK_SLOPE_ADX18__ANTICIPATE_BELOW_050__TWO_BAR_REVERSAL__BASE__LONG__MICRO_SWING5__UPPER_TREND_END"


def expand_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser()


def _read_ohlc_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        header = handle.readline()
    delimiters = [",", ";", "\t"]
    delimiter = max(delimiters, key=header.count)
    if header.count(delimiter) == 0:
        raise ValueError(f"{path}: unable to detect CSV delimiter from header {header.strip()!r}")
    d = pd.read_csv(path, sep=delimiter, encoding="utf-8-sig")
    d.columns = [str(column).strip().lower().lstrip("\ufeff") for column in d.columns]
    aliases = {
        "datetime": "time",
        "date_time": "time",
        "<date>": "time",
        "<time>": "time",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
    }
    d = d.rename(columns={column: aliases.get(column, column) for column in d.columns})
    return d


def load_csv(path: Path, tf: str) -> pd.DataFrame:
    d = _read_ohlc_csv(path)
    required = {"time", "open", "high", "low", "close"}
    missing = required - set(d.columns)
    if missing:
        raise ValueError(
            f"{path}: missing columns {sorted(missing)}; detected columns={list(d.columns)}"
        )
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="raise")
    for c in ["open", "high", "low", "close"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    d["close_time"] = d["time"] + pd.to_timedelta(MINUTES[tf], unit="m")
    d.attrs["source_audit"] = {
        "path": str(path),
        "delimiter": "TAB" if delimiter == "\t" else delimiter,
        "columns": list(d.columns),
        "rows": int(len(d)),
        "first_time": str(d["time"].iloc[0]) if len(d) else None,
        "last_time": str(d["time"].iloc[-1]) if len(d) else None,
    }
    return add_features(d)


def wild(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_features(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    d["atr14"] = wild(tr, 14)
    d["ema20"] = d.close.ewm(span=20, adjust=False, min_periods=20).mean()
    d["ema50"] = d.close.ewm(span=50, adjust=False, min_periods=50).mean()
    d["slope"] = (d.ema20 - d.ema20.shift(3)) / d.atr14
    absd = d.close.diff().abs()
    d["eff20"] = (d.close - d.close.shift(20)).abs() / absd.rolling(20).sum().replace(0, np.nan)
    up = d.high.diff(); down = -d.low.diff()
    pdm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=d.index)
    mdm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=d.index)
    pdi = 100 * wild(pdm, 14) / d.atr14; mdi = 100 * wild(mdm, 14) / d.atr14
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    d["adx14"] = wild(dx, 14)
    rng = (d.high - d.low).replace(0, np.nan)
    d["body_atr"] = (d.close - d.open) / d.atr14
    d["close_pos"] = (d.close - d.low) / rng
    d["p5h"] = d.high.shift().rolling(5).max()
    d["p5l"] = d.low.shift().rolling(5).min()
    d["donchian20h"] = d.high.rolling(20).max()
    d["ret3_atr"] = (d.close - d.close.shift(3)) / d.atr14
    d["ret6_atr"] = (d.close - d.close.shift(6)) / d.atr14
    d["range5_atr"] = (d.high.rolling(5).max() - d.low.rolling(5).min()) / d.atr14
    return d


def h4_long_trend(h4: pd.DataFrame) -> np.ndarray:
    return ((h4.close > h4.ema20) & (h4.ema20 > h4.ema50) & (h4.slope > 0) & (h4.adx14 >= 18)).fillna(False).to_numpy(bool)


def two_bar_long(d: pd.DataFrame) -> np.ndarray:
    return ((d.close.shift(1) < d.open.shift(1)) & (d.close > d.open) & (d.close > d.high.shift(1)) &
            (d.body_atr >= 0.10) & (d.close_pos >= 0.60)).fillna(False).to_numpy(bool)


def next_false(mask: np.ndarray) -> np.ndarray:
    out = np.full(len(mask), -1, dtype=np.int64); nx = -1
    for i in range(len(mask) - 1, -1, -1):
        out[i] = nx
        if mask[i]: nx = i
    return out


def exact_m1_index(m1: pd.DataFrame, t: pd.Timestamp) -> int:
    times = pd.DatetimeIndex(m1.time)
    i = int(times.searchsorted(t, side="left"))
    return i if i < len(times) and times[i] == t else -1


def simulate_source_long(m1: pd.DataFrame, entry_idx: int, stop: float, trend_exit_idx: int, max_hold: int = 1440) -> dict[str, Any]:
    entry = float(m1.open.iloc[entry_idx]); latest = len(m1) - 1
    max_end = entry_idx + max_hold
    scheduled = trend_exit_idx > entry_idx and trend_exit_idx <= max_end
    intended_end = trend_exit_idx if scheduled else max_end
    scan_end = min(intended_end - (1 if scheduled else 0), latest)
    for j in range(entry_idx, scan_end + 1):
        if m1.low.iloc[j] <= stop:
            return {"status": "CLOSED", "exit_idx": j, "exit_time": m1.time.iloc[j], "exit_price": stop, "reason": "SL"}
    if intended_end <= latest:
        px = float(m1.open.iloc[intended_end]) if scheduled else float(m1.close.iloc[intended_end])
        return {"status": "CLOSED", "exit_idx": intended_end, "exit_time": m1.time.iloc[intended_end], "exit_price": px, "reason": "H4_TREND_END" if scheduled else "MAX"}
    return {"status": "OPEN", "exit_idx": -1, "exit_time": pd.NaT, "exit_price": np.nan, "reason": "OPEN"}


def build_source_ledger(trigger_tf: str, h4: pd.DataFrame, m15: pd.DataFrame, trigger: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    source_id = M1_SOURCE_ID if trigger_tf == "M1" else M5_SOURCE_ID
    all_tc = pd.DatetimeIndex(trigger.close_time)
    sct = pd.DatetimeIndex(m15.close_time); uct = pd.DatetimeIndex(h4.close_time); m1t = pd.DatetimeIndex(m1.time)
    sidx = np.searchsorted(sct.values.astype("datetime64[m]"), all_tc.values.astype("datetime64[m]"), side="right") - 1
    uidx = np.searchsorted(uct.values.astype("datetime64[m]"), all_tc.values.astype("datetime64[m]"), side="right") - 1
    eidx = np.searchsorted(m1t.values.astype("datetime64[m]"), all_tc.values.astype("datetime64[m]"), side="left")
    valid_entry = (eidx < len(m1))
    safe = np.minimum(eidx, len(m1) - 1)
    valid_entry &= m1t.values.astype("datetime64[m]")[safe] == all_tc.values.astype("datetime64[m]")
    minute_int = all_tc.values.astype("datetime64[m]").astype(np.int64)
    valid = (sidx >= 0) & (uidx >= 0) & valid_entry & ((minute_int % 15) != 0)
    t = trigger.loc[valid].copy().reset_index().rename(columns={"index": "original_trigger_idx"})
    t["setup_idx"] = sidx[valid]; t["upper_idx"] = uidx[valid]; t["m1_entry_idx"] = eidx[valid]
    micro = two_bar_long(t)
    trend = h4_long_trend(h4); h4_end = next_false(~trend)
    rows = []
    for ti in range(len(t)):
        if not micro[ti]: continue
        tc = pd.Timestamp(t.close_time.iloc[ti]); si = int(t.setup_idx.iloc[ti]); ui = int(t.upper_idx.iloc[ti])
        if not trend[ui]: continue
        setup_atr = float(m15.atr14.iloc[si]); level = float(m15.donchian20h.iloc[si])
        if not np.isfinite(setup_atr) or setup_atr <= 0 or not np.isfinite(level): continue
        if not (m15.close.iloc[si] > m15.ema20.iloc[si] > m15.ema50.iloc[si]): continue
        distance = (level - float(t.close.iloc[ti])) / setup_atr
        if distance < 0 or distance > 0.50: continue
        ei = int(t.m1_entry_idx.iloc[ti]); entry = float(m1.open.iloc[ei])
        if trigger_tf == "M1":
            stop = entry - 0.50 * setup_atr
        else:
            stop = float(t.p5l.iloc[ti]) - 0.10 * float(t.atr14.iloc[ti])
        if not np.isfinite(stop) or stop >= entry: continue
        next_ui = h4_end[ui]
        trend_exit_idx = exact_m1_index(m1, pd.Timestamp(h4.close_time.iloc[next_ui])) if next_ui >= 0 else -1
        rows.append({"source": "M1_TWO_BAR" if trigger_tf == "M1" else "M5_TWO_BAR", "source_config_id": source_id,
                     "trigger_idx": int(t.original_trigger_idx.iloc[ti]), "setup_idx": si, "upper_idx": ui, "decision_time": tc,
                     "entry_idx": ei, "entry_price": entry, "source_stop": stop, "setup_atr": setup_atr,
                     "breakout_level": level, "distance_to_level_atr": distance, "trend_exit_idx": trend_exit_idx})
    raw = pd.DataFrame(rows)
    if raw.empty: return raw
    accepted = []; blocked_idx = -1
    for _, r in raw.sort_values("entry_idx").iterrows():
        if int(r.entry_idx) <= blocked_idx: continue
        sim = simulate_source_long(m1, int(r.entry_idx), float(r.source_stop), int(r.trend_exit_idx))
        rec = r.to_dict(); rec.update({f"source_{k}": v for k, v in sim.items()}); accepted.append(rec)
        blocked_idx = int(sim["exit_idx"]) if sim["status"] == "CLOSED" else len(m1) + 1
    return pd.DataFrame(accepted).reset_index(drop=True)
