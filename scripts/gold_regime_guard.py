from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_CSV = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"


def read_history_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path).copy()
    for col in ["entry_time", "jst_entry_time", "signal_time", "exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "entry_time" not in df.columns and "jst_entry_time" in df.columns:
        df["entry_time"] = df["jst_entry_time"]
    if "entry_time" not in df.columns:
        raise ValueError("history csv needs entry_time or jst_entry_time")

    for col in ["symbol_group", "portfolio_rank", "side"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.upper().str.strip()

    if "r" not in df.columns:
        df["r"] = 0.0
    df["r"] = pd.to_numeric(df["r"], errors="coerce").fillna(0.0)

    if "result" not in df.columns:
        df["result"] = "breakeven"
        df.loc[df["r"] > 0, "result"] = "win"
        df.loc[df["r"] < 0, "result"] = "loss"
    df["result"] = df["result"].astype(str).str.lower().str.strip()

    return df.dropna(subset=["entry_time"]).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def infer_symbol_group(row: dict[str, Any]) -> str:
    value = str(row.get("symbol_group", "") or "").upper().strip()
    if value:
        return value
    symbol = str(row.get("symbol", row.get("mt5_symbol", row.get("target_symbol", ""))) or "").upper()
    if "BTC" in symbol or "XBT" in symbol:
        return "BTC"
    if "GOLD" in symbol or "XAU" in symbol:
        return "GOLD"
    return value


def infer_portfolio_rank(row: dict[str, Any]) -> str:
    value = str(row.get("portfolio_rank", "") or "").upper().strip()
    if value:
        return value
    strategy = str(row.get("strategy_label", row.get("signal_model", row.get("model", row.get("source", "")))) or "").upper()
    if "ABC" in strategy or strategy in {"A", "B", "C", "C2"}:
        return "GOLD_ABC"
    return value


def infer_entry_time(row: dict[str, Any]) -> pd.Timestamp | None:
    for col in ["entry_time", "signal_time", "jst_entry_time", "time"]:
        if col in row and row.get(col) not in [None, ""]:
            t = pd.to_datetime(row.get(col), errors="coerce")
            if pd.notna(t):
                return pd.Timestamp(t)
    return None


def evaluate_gold_abc_buy_danger_regime(
    current_signal: dict[str, Any],
    history: pd.DataFrame,
    *,
    last_n: int = 3,
    min_losses: int = 3,
    lookback_days: int = 30,
) -> dict[str, Any]:
    symbol_group = infer_symbol_group(current_signal)
    portfolio_rank = infer_portfolio_rank(current_signal)
    side = str(current_signal.get("side", "") or "").upper().strip()
    current_time = infer_entry_time(current_signal)

    result: dict[str, Any] = {
        "gold_abc_buy_danger_regime": False,
        "warning_only": True,
        "reason": "not_gold_abc_buy_or_insufficient_context",
        "checked": False,
        "current_symbol_group": symbol_group,
        "current_portfolio_rank": portfolio_rank,
        "current_side": side,
        "last_n": last_n,
        "min_losses": min_losses,
        "lookback_days": lookback_days,
        "history_count": int(len(history)),
        "relevant_history_count": 0,
        "recent_relevant_count": 0,
        "recent_loss_count": 0,
        "recent_win_count": 0,
        "recent_total_r": 0.0,
        "recent_entry_times": [],
        "recent_results": [],
        "recent_r_values": [],
    }

    if symbol_group != "GOLD" or portfolio_rank != "GOLD_ABC" or side != "BUY":
        return result
    if current_time is None:
        result["reason"] = "missing_current_time"
        return result

    relevant = history[
        (history["symbol_group"].eq("GOLD"))
        & (history["portfolio_rank"].eq("GOLD_ABC"))
        & (history["side"].eq("BUY"))
        & (history["entry_time"] < current_time)
    ].copy()
    if lookback_days and lookback_days > 0:
        relevant = relevant[relevant["entry_time"] >= current_time - pd.Timedelta(days=lookback_days)].copy()

    recent = relevant.sort_values("entry_time", kind="mergesort").tail(last_n).copy()
    loss_count = int(recent["result"].eq("loss").sum()) if not recent.empty else 0
    win_count = int(recent["result"].eq("win").sum()) if not recent.empty else 0
    danger = len(recent) >= last_n and loss_count >= min_losses

    if danger:
        reason = f"last_{last_n}_gold_abc_buy_within_{lookback_days}d_had_{loss_count}_losses"
    elif len(recent) < last_n:
        reason = f"insufficient_recent_gold_abc_buy_history_{len(recent)}_of_{last_n}"
    else:
        reason = f"recent_gold_abc_buy_losses_{loss_count}_below_{min_losses}"

    result.update(
        {
            "gold_abc_buy_danger_regime": bool(danger),
            "reason": reason,
            "checked": True,
            "relevant_history_count": int(len(relevant)),
            "recent_relevant_count": int(len(recent)),
            "recent_loss_count": loss_count,
            "recent_win_count": win_count,
            "recent_total_r": float(recent["r"].sum()) if not recent.empty else 0.0,
            "recent_entry_times": [pd.Timestamp(x).strftime("%Y-%m-%d %H:%M:%S") for x in recent["entry_time"].tolist()],
            "recent_results": recent["result"].astype(str).tolist(),
            "recent_r_values": [float(x) for x in recent["r"].tolist()],
        }
    )
    return result


def evaluate_from_history_csv(
    current_signal: dict[str, Any],
    history_csv: Path = DEFAULT_HISTORY_CSV,
    **kwargs: Any,
) -> dict[str, Any]:
    history = read_history_csv(history_csv)
    return evaluate_gold_abc_buy_danger_regime(current_signal, history, **kwargs)
