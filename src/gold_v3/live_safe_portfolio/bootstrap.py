from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd

from .state import SQLiteStateStore


def bootstrap_from_selected_ledger(
    store: SQLiteStateStore,
    ledger_csv: str | Path,
    *,
    portfolio: str = "PLUS_STRICT_SAFE",
    start_dt: datetime | None = None,
    through_dt: datetime | None = None,
) -> dict:
    """One-time cutover state rehydration from the accepted audit ledger."""
    df = pd.read_csv(ledger_csv)
    required = {"entry_dt", "exit_dt", "pnl", "source", "portfolio", "priority"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"ledger missing columns: {sorted(missing)}")
    df = df[df["portfolio"] == portfolio].copy()
    df["entry_dt"] = pd.to_datetime(df["entry_dt"])
    df["exit_dt"] = pd.to_datetime(df["exit_dt"])
    if start_dt is not None:
        df = df[df["entry_dt"] >= pd.Timestamp(start_dt)]
    if through_dt is not None:
        df = df[df["exit_dt"] <= pd.Timestamp(through_dt)]
    df = df.sort_values(["exit_dt", "entry_dt"])
    pnl = df["pnl"].astype(float).to_numpy()
    equity_path = pnl.cumsum()
    equity = float(equity_path[-1]) if len(equity_path) else 0.0
    peak = float(max(0.0, equity_path.max())) if len(equity_path) else 0.0
    additions = df[df["source"] != "BASE"].sort_values("entry_dt")
    losses = additions[additions["pnl"].astype(float) < 0].sort_values("exit_dt")
    last_entry = additions.iloc[-1]["entry_dt"].to_pydatetime() if len(additions) else None
    last_loss = losses.iloc[-1]["exit_dt"].to_pydatetime() if len(losses) else None
    last_exit = df.iloc[-1]["exit_dt"].to_pydatetime() if len(df) else None
    ordered = df.sort_values(["entry_dt", "priority"])
    last_processed_entry = ordered.iloc[-1]["entry_dt"].to_pydatetime() if len(ordered) else None
    last_processed_priority = int(ordered.iloc[-1]["priority"]) if len(ordered) else None
    store.replace_state_for_bootstrap(
        equity=equity,
        peak_equity=peak,
        last_candidate_entry_dt=last_entry,
        last_candidate_loss_exit_dt=last_loss,
        last_applied_exit_dt=last_exit,
        last_processed_entry_dt=last_processed_entry,
        last_processed_priority=last_processed_priority,
    )
    return {
        "n": int(len(df)),
        "equity": equity,
        "peak_equity": peak,
        "realized_dd": peak - equity,
        "last_candidate_entry_dt": last_entry,
        "last_candidate_loss_exit_dt": last_loss,
        "last_applied_exit_dt": last_exit,
        "last_processed_entry_dt": last_processed_entry,
        "last_processed_priority": last_processed_priority,
    }
