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


def _upper(value: Any) -> str:
    return str(value or "").upper().strip()


def _combined_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in [
        "symbol_group",
        "portfolio_rank",
        "strategy_label",
        "signal_model",
        "model",
        "source",
        "symbol",
        "mt5_symbol",
        "target_symbol",
        "case_db_name",
        "case_db_path",
        "preset",
        "preset_name",
        "payload_source",
    ]:
        value = row.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts).upper()


def flatten_payload_context(payload_or_signal: dict[str, Any]) -> dict[str, Any]:
    """Merge useful top-level payload context into current_signal_snapshot.

    Case-DB review payloads often keep the actual current features under
    current_signal_snapshot, while dataset/preset hints live at the top level.
    This helper lets the guard infer GOLD/ABC without sending outcome labels.
    """
    if not isinstance(payload_or_signal, dict):
        return {}

    current = payload_or_signal.get("current_signal_snapshot") or payload_or_signal.get("current_signal")
    if isinstance(current, dict):
        merged = dict(current)
        for key, value in payload_or_signal.items():
            if key in {"current_signal_snapshot", "current_signal", "similar_winning_cases", "similar_losing_cases"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                merged.setdefault(key, value)
        metadata = payload_or_signal.get("metadata")
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    merged.setdefault(key, value)
        return merged

    return dict(payload_or_signal)


def infer_symbol_group(row: dict[str, Any]) -> str:
    value = _upper(row.get("symbol_group"))
    if value:
        return value
    text = _combined_text(row)
    if "BTC" in text or "XBT" in text:
        return "BTC"
    if "GOLD" in text or "XAU" in text or "KIWAMI" in text or "GOLDSHARP" in text:
        return "GOLD"
    return ""


def infer_portfolio_rank(row: dict[str, Any]) -> str:
    value = _upper(row.get("portfolio_rank"))
    if value:
        return value
    text = _combined_text(row)
    source = _upper(row.get("source"))
    if "ABC" in text or "XM_KIWAMI_GOLD" in text or source in {"A", "B", "C", "C2"}:
        return "GOLD_ABC"
    return ""


def infer_entry_time(row: dict[str, Any]) -> pd.Timestamp | None:
    for col in ["entry_time", "signal_time", "jst_entry_time", "time", "entry_at", "signal_at"]:
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
    current_signal = flatten_payload_context(current_signal)
    symbol_group = infer_symbol_group(current_signal)
    portfolio_rank = infer_portfolio_rank(current_signal)
    side = _upper(current_signal.get("side"))
    current_time = infer_entry_time(current_signal)

    result: dict[str, Any] = {
        "gold_abc_buy_danger_regime": False,
        "warning_only": True,
        "reason": "not_gold_abc_buy_or_insufficient_context",
        "checked": False,
        "current_symbol_group": symbol_group,
        "current_portfolio_rank": portfolio_rank,
        "current_side": side,
        "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S") if current_time is not None else "",
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
