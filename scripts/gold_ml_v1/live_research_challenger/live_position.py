from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from live_data import POINT, TF_DELTA


@dataclass(frozen=True)
class PositionContract:
    direction: str
    target_r: float
    horizon_hours: int
    hit_exit_time: str
    time_exit_time: str


CONTRACTS = {
    "A_CORE": PositionContract("LONG", 1.0, 6, "close", "close"),
    "B_STATE": PositionContract("LONG", 1.0, 48, "open", "open"),
    "P18": PositionContract("LONG", 1.0, 12, "close", "close"),
    "W024A": PositionContract("SHORT", 1.5, 6, "close", "close"),
}


class LiveM1Engine:
    def __init__(self, frame: pd.DataFrame):
        self.times = pd.DatetimeIndex(frame["bar_open_time"]).asi8
        self.opens = frame["open"].to_numpy(float)
        self.highs = frame["high"].to_numpy(float)
        self.lows = frame["low"].to_numpy(float)
        self.closes = frame["close"].to_numpy(float)
        self.spreads = frame["spread"].to_numpy(float)
        self.latest_close = pd.Timestamp(self.times[-1] + int(TF_DELTA["M1"].value))

    @staticmethod
    def _stored_time(value: int, mode: str) -> pd.Timestamp:
        offset = int(TF_DELTA["M1"].value) if mode == "close" else 0
        return pd.Timestamp(value + offset)

    def evaluate(
        self,
        decision: pd.Timestamp,
        atr: float,
        contract: PositionContract,
    ) -> dict[str, Any]:
        decision = pd.Timestamp(decision)
        base: dict[str, Any] = {
            "decision_time": decision,
            "direction": contract.direction,
            "atr": float(atr),
            "target_r": contract.target_r,
            "horizon_hours": contract.horizon_hours,
            "horizon_end_time": decision + pd.Timedelta(hours=contract.horizon_hours),
        }
        if not np.isfinite(atr) or atr <= 0:
            return {**base, "position_state": "INVALID_ATR", "outcome": "NOT_EVALUATED"}

        start = int(np.searchsorted(self.times, decision.value, side="left"))
        if start >= len(self.times) or int(self.times[start]) != decision.value:
            return {**base, "position_state": "ENTRY_M1_MISSING", "outcome": "NOT_EVALUATED"}

        available_end = min(pd.Timestamp(base["horizon_end_time"]), self.latest_close)
        end = int(np.searchsorted(self.times, available_end.value, side="left"))

        if contract.direction == "LONG":
            entry = float(self.opens[start] + self.spreads[start] * POINT)
            stop = entry - atr
            target = entry + contract.target_r * atr
            stop_hits = np.flatnonzero(self.lows[start:end] <= stop)
            target_hits = np.flatnonzero(self.highs[start:end] >= target)
        elif contract.direction == "SHORT":
            entry = float(self.opens[start])
            stop = entry + atr
            target = entry - contract.target_r * atr
            ask_high = self.highs[start:end] + self.spreads[start:end] * POINT
            ask_low = self.lows[start:end] + self.spreads[start:end] * POINT
            stop_hits = np.flatnonzero(ask_high >= stop)
            target_hits = np.flatnonzero(ask_low <= target)
        else:
            raise ValueError(f"Unsupported direction: {contract.direction}")

        base.update(
            {
                "entry_price": entry,
                "stop_price": float(stop),
                "target_price": float(target),
                "latest_observed_close_time": self.latest_close,
            }
        )

        if len(stop_hits) and (not len(target_hits) or int(stop_hits[0]) <= int(target_hits[0])):
            index = start + int(stop_hits[0])
            return {
                **base,
                "position_state": "RESOLVED",
                "outcome": "SL",
                "exit_time": self._stored_time(int(self.times[index]), contract.hit_exit_time),
                "exit_price": float(stop),
                "r": -1.0,
                "current_r": -1.0,
            }

        if len(target_hits):
            index = start + int(target_hits[0])
            return {
                **base,
                "position_state": "RESOLVED",
                "outcome": "TP",
                "exit_time": self._stored_time(int(self.times[index]), contract.hit_exit_time),
                "exit_price": float(target),
                "r": float(contract.target_r),
                "current_r": float(contract.target_r),
            }

        if end <= start:
            return {
                **base,
                "position_state": "OPEN",
                "outcome": "OPEN",
                "exit_time": pd.NaT,
                "r": np.nan,
                "current_r": 0.0,
            }

        index = end - 1
        if pd.Timestamp(base["horizon_end_time"]) <= self.latest_close:
            if contract.direction == "LONG":
                exit_price = float(self.closes[index])
                r_value = float((exit_price - entry) / atr)
            else:
                exit_price = float(self.closes[index] + self.spreads[index] * POINT)
                r_value = float((entry - exit_price) / atr)
            return {
                **base,
                "position_state": "RESOLVED",
                "outcome": "TIME",
                "exit_time": self._stored_time(int(self.times[index]), contract.time_exit_time),
                "exit_price": exit_price,
                "r": r_value,
                "current_r": r_value,
            }

        if contract.direction == "LONG":
            current_price = float(self.closes[index])
            current_r = float((current_price - entry) / atr)
        else:
            current_price = float(self.closes[index] + self.spreads[index] * POINT)
            current_r = float((entry - current_price) / atr)
        return {
            **base,
            "position_state": "OPEN",
            "outcome": "OPEN",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "r": np.nan,
            "current_price": current_price,
            "current_r": current_r,
        }
