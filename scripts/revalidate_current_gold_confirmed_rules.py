from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_latest_signal_payload_from_csv import add_indicators, detect_gold_signal
from confirmed_time_join import join_h1_confirmed_for_gold_m15
from search_btc_mtf_extra_edges import max_consecutive_losses, max_drawdown_r, profit_factor
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD_M15_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_m15.csv"
DEFAULT_GOLD_H1_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_h1.csv"
DEFAULT_GOLD_M5_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_m5.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_current_rules_confirmed_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "gold_current_rules_confirmed_trades.csv"

ADOPTED_LABELS = {
    "GOLD_ABC_V3",
    "GOLD_EXTRA_HIGH_RSI_STOCH",
    "GOLD_EXTRA_BB_BALANCE",
}
EXCLUDED_LABELS = {"GOLD_COUNTER_BUY_ONLY"}


@dataclass(frozen=True)
class GoldConfig:
    horizon_m15_bars: int
    cooldown_bars: int
    inbar_priority: str
    point_size: float
    use_spread: bool


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def spread_price(row: pd.Series, *, point_size: float, use_spread: bool) -> float:
    if not use_spread:
        return 0.0
    try:
        return max(0.0, float(row.get("spread", 0.0) or 0.0) * point_size)
    except Exception:
        return 0.0


def max_consecutive_by_bool(loss_flags: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for is_loss in loss_flags.astype(bool):
        if is_loss:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def first_m5_index_at_or_after(m5: pd.DataFrame, target_time: pd.Timestamp) -> int | None:
    idx = m5.index[m5["time"] >= target_time].tolist()
    if not idx:
        return None
    return int(idx[0])


def simulate_gold_trade(
    *,
    signal_idx: int,
    signal_row: pd.Series,
    signal: dict[str, Any],
    m5: pd.DataFrame,
    cfg: GoldConfig,
) -> dict[str, Any] | None:
    signal_time = pd.Timestamp(signal_row["time"])
    entry_time = signal_time + pd.Timedelta(minutes=15)
    entry_idx = first_m5_index_at_or_after(m5, entry_time)
    if entry_idx is None:
        return None

    entry_row = m5.iloc[entry_idx]
    side = str(signal.get("side", "")).upper()
    rr = float(signal.get("rr", 1.5))
    risk_atr = float(signal.get("risk_atr", 1.5))
    atr = float(signal_row.get("atr14", np.nan))
    if side not in {"BUY", "SELL"} or not np.isfinite(atr) or atr <= 0:
        return None

    spread = spread_price(entry_row, point_size=cfg.point_size, use_spread=cfg.use_spread)
    entry_mid = float(entry_row["open"])
    risk = atr * risk_atr
    if risk <= 0:
        return None

    if side == "BUY":
        entry = entry_mid + spread / 2.0
        sl = entry - risk
        tp = entry + rr * risk
    else:
        entry = entry_mid - spread / 2.0
        sl = entry + risk
        tp = entry - rr * risk

    max_m5_bars = max(1, int(cfg.horizon_m15_bars * 3))
    last_idx = min(entry_idx + max_m5_bars - 1, len(m5) - 1)
    exit_idx = last_idx
    exit_row = m5.iloc[exit_idx]
    exit_spread = spread_price(exit_row, point_size=cfg.point_size, use_spread=cfg.use_spread)
    exit_mid = float(exit_row["close"])
    exit_price = exit_mid - exit_spread / 2.0 if side == "BUY" else exit_mid + exit_spread / 2.0
    r_value = (exit_price - entry) / risk if side == "BUY" else (entry - exit_price) / risk
    exit_reason = "timeout"

    for j in range(entry_idx, last_idx + 1):
        row = m5.iloc[j]
        cur_spread = spread_price(row, point_size=cfg.point_size, use_spread=cfg.use_spread)
        high_mid = float(row["high"])
        low_mid = float(row["low"])
        bid_high = high_mid - cur_spread / 2.0
        bid_low = low_mid - cur_spread / 2.0
        ask_high = high_mid + cur_spread / 2.0
        ask_low = low_mid + cur_spread / 2.0

        if side == "BUY":
            hit_tp = bid_high >= tp
            hit_sl = bid_low <= sl
        else:
            hit_tp = ask_low <= tp
            hit_sl = ask_high >= sl

        if hit_tp and hit_sl:
            exit_idx = j
            if cfg.inbar_priority.upper() == "TP":
                exit_price = tp
                exit_reason = "tp_same_bar"
                r_value = rr
            else:
                exit_price = sl
                exit_reason = "sl_same_bar"
                r_value = -1.0
            break
        if hit_sl:
            exit_idx = j
            exit_price = sl
            exit_reason = "sl"
            r_value = -1.0
            break
        if hit_tp:
            exit_idx = j
            exit_price = tp
            exit_reason = "tp"
            r_value = rr
            break

    label = str(signal.get("strategy_label", ""))
    return {
        "strategy_label": label,
        "signal_model": signal.get("signal_model"),
        "abc_source": signal.get("abc_source", ""),
        "side": side,
        "signal_idx": int(signal_idx),
        "signal_time": signal_time,
        "entry_idx_m5": int(entry_idx),
        "entry_time": m5.at[entry_idx, "time"],
        "exit_idx_m5": int(exit_idx),
        "exit_time": m5.at[exit_idx, "time"],
        "entry_price": float(entry),
        "entry_mid_price": float(entry_mid),
        "entry_spread_price": float(spread),
        "tp": float(tp),
        "sl": float(sl),
        "risk": float(risk),
        "rr": rr,
        "risk_atr": risk_atr,
        "atr14_m15": atr,
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "bars_held_m5": int(exit_idx - entry_idx + 1),
        "r": float(r_value),
        "result": "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven",
        "jst_hour_plus6": int((signal_time + pd.Timedelta(hours=6)).hour),
        "h1_time": signal_row.get("h1_time", pd.NaT),
        "h1_close_time": signal_row.get("h1_close_time", pd.NaT),
    }


def summarize_trades(trades: pd.DataFrame, *, label: str) -> dict[str, Any]:
    if trades.empty:
        return {
            "strategy_label": label,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_dd_r": 0.0,
            "buy_trades": 0,
            "sell_trades": 0,
            "trades_per_month": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = trades[trades["side"] == "BUY"]
    sell = trades[trades["side"] == "SELL"]
    span_days = max(1, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days)
    months = max(1.0, span_days / 30.4375)
    return {
        "strategy_label": label,
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(trades)),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(trades["result"]),
        "max_dd_r": max_drawdown_r(r),
        "buy_trades": int(len(buy)),
        "sell_trades": int(len(sell)),
        "buy_win_rate": float((buy["r"] > 0).sum() / len(buy)) if len(buy) else None,
        "sell_win_rate": float((sell["r"] > 0).sum() / len(sell)) if len(sell) else None,
        "trades_per_month": float(len(trades) / months),
    }


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Revalidate current GOLD adopted labels with confirmed-time H1 join and M5 first-touch outcomes.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_GOLD_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_GOLD_H1_CSV)
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_GOLD_M5_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--horizon-m15-bars", type=int, default=32, help="Outcome horizon in M15 bars. Default 32 = 8 hours.")
    parser.add_argument("--cooldown-bars", type=int, default=0, help="Cooldown in M15 bars after exit. Default 0 to audit raw current detector output.")
    parser.add_argument("--min-start-idx", type=int, default=220)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--use-spread", action="store_true", help="Apply half-spread entry/exit execution using CSV spread column.")
    parser.add_argument("--include-excluded", action="store_true", help="Also include GOLD_COUNTER_BUY_ONLY for diagnostics.")
    args = parser.parse_args()

    m15_raw = read_ohlc_live_csv(resolve_path(args.m15_csv))
    h1_raw = read_ohlc_live_csv(resolve_path(args.h1_csv))
    m5 = read_ohlc_live_csv(resolve_path(args.m5_csv))
    m15 = add_indicators(m15_raw)
    h1 = add_indicators(h1_raw)
    ctx = join_h1_confirmed_for_gold_m15(m15, h1)

    print("Rows:", "M5", len(m5), "M15", len(m15), "H1", len(h1))
    print("Ranges:")
    for name, df in [("M5", m5), ("M15", m15), ("H1", h1)]:
        print(f"  {name}: {df['time'].min()} -> {df['time'].max()}")
    print("Confirmed-time join: H1 close_time <= M15 close_time")
    print("Outcome:", f"M5 first-touch / horizon_m15_bars={args.horizon_m15_bars} / inbar_priority={args.inbar_priority} / use_spread={args.use_spread}")

    cfg = GoldConfig(
        horizon_m15_bars=args.horizon_m15_bars,
        cooldown_bars=args.cooldown_bars,
        inbar_priority=args.inbar_priority,
        point_size=args.point_size,
        use_spread=bool(args.use_spread),
    )

    trades: list[dict[str, Any]] = []
    blocked_until = -1
    allowed = set(ADOPTED_LABELS)
    if args.include_excluded:
        allowed |= EXCLUDED_LABELS

    for idx in range(max(args.min_start_idx, 0), len(ctx) - 1):
        if idx <= blocked_until:
            continue
        row = ctx.iloc[idx]
        signal = detect_gold_signal(row)
        if signal is None:
            continue
        label = str(signal.get("strategy_label", ""))
        if label not in allowed:
            continue
        trade = simulate_gold_trade(signal_idx=idx, signal_row=row, signal=signal, m5=m5, cfg=cfg)
        if trade is None:
            continue
        trades.append(trade)
        if args.cooldown_bars > 0:
            # Convert M5 exit time back to the latest M15 index at or before exit_time, then add cooldown.
            exit_time = pd.Timestamp(trade["exit_time"])
            m15_exit_idx_candidates = ctx.index[ctx["time"] <= exit_time].tolist()
            if m15_exit_idx_candidates:
                blocked_until = int(m15_exit_idx_candidates[-1]) + args.cooldown_bars

    trades_df = pd.DataFrame(trades)
    summaries = []
    for label in sorted(allowed):
        label_trades = trades_df[trades_df["strategy_label"] == label] if not trades_df.empty else pd.DataFrame()
        summaries.append(summarize_trades(label_trades, label=label))
    summaries.append(summarize_trades(trades_df, label="ALL_ADOPTED" if not args.include_excluded else "ALL_INCLUDED"))
    summary_df = pd.DataFrame(summaries)

    write_csv(resolve_path(args.out_summary), summary_df)
    write_csv(resolve_path(args.out_trades), trades_df)

    print("\n" + "=" * 140)
    print("CURRENT GOLD RULES CONFIRMED SUMMARY")
    print("=" * 140)
    print(summary_df.to_string(index=False))
    print("\nSaved summary:", resolve_path(args.out_summary))
    print("Saved trades :", resolve_path(args.out_trades))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
