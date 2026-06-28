from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WinRateSummary:
    trades: int
    wins: int
    losses_or_flat: int
    win_rate: float | None
    source: str
    available: bool = True
    reason: str | None = None

    def display(self) -> str:
        if not self.available or self.win_rate is None:
            suffix = f"（{self.reason}）" if self.reason else ""
            return f"N/A{suffix}"
        return f"{self.win_rate * 100:.2f}%（{self.wins}/{self.trades}）"


def _empty(source: str, reason: str) -> WinRateSummary:
    return WinRateSummary(
        trades=0,
        wins=0,
        losses_or_flat=0,
        win_rate=None,
        source=source,
        available=False,
        reason=reason,
    )


def _summary(values: pd.Series, source: str) -> WinRateSummary:
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric[np.isfinite(numeric.to_numpy(float))]
    trades = int(len(numeric))
    if trades == 0:
        return _empty(source, "resolved trades are unavailable")
    wins = int((numeric > 0).sum())
    return WinRateSummary(
        trades=trades,
        wins=wins,
        losses_or_flat=trades - wins,
        win_rate=wins / trades,
        source=source,
    )


def load_historical_win_rates(
    results_dir: Path,
    comps: Iterable[str],
) -> dict[str, WinRateSummary]:
    requested = tuple(comps)
    paths = [
        results_dir / f"research_challenger_local_{year}.csv"
        for year in (2024, 2025, 2026)
    ]
    missing = [path.name for path in paths if not path.is_file()]
    source = "historical auto-execution replay 2024-2026 partial"
    if missing:
        reason = "missing " + ", ".join(missing)
        return {comp: _empty(source, reason) for comp in requested}

    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_csv(path)
        required = {"comp", "r"}
        absent = sorted(required - set(frame.columns))
        if absent:
            reason = f"{path.name} missing columns: {', '.join(absent)}"
            return {comp: _empty(source, reason) for comp in requested}
        frames.append(frame[["comp", "r"]].copy())
    combined = pd.concat(frames, ignore_index=True)
    return {
        comp: _summary(combined.loc[combined["comp"].eq(comp), "r"], source)
        for comp in requested
    }


def load_live_win_rates(
    ledger: pd.DataFrame,
    comps: Iterable[str],
) -> dict[str, WinRateSummary]:
    requested = tuple(comps)
    source = "live MT5 closed orders"
    if ledger.empty or not {"comp", "trade_state", "live_result"}.issubset(
        ledger.columns
    ):
        return {
            comp: _empty(source, "no closed live orders yet") for comp in requested
        }

    closed = ledger[ledger["trade_state"].eq("CLOSED")].copy()
    result: dict[str, WinRateSummary] = {}
    for comp in requested:
        values = closed.loc[closed["comp"].eq(comp), "live_result"].astype(str)
        trades = int(len(values))
        if trades == 0:
            result[comp] = _empty(source, "no closed live orders yet")
            continue
        wins = int(values.eq("WIN").sum())
        result[comp] = WinRateSummary(
            trades=trades,
            wins=wins,
            losses_or_flat=trades - wins,
            win_rate=wins / trades,
            source=source,
        )
    return result
