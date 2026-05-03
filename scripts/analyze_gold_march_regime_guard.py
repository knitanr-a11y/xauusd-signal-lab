from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_march_regime_guard_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "gold_march_regime_guard_trades.csv"
DEFAULT_OUT_STREAKS = PROJECT_ROOT / "data" / "results" / "gold_march_regime_guard_streaks.csv"
DEFAULT_OUT_MONTHLY_SIMILARITY = PROJECT_ROOT / "data" / "results" / "gold_march_regime_monthly_similarity.csv"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    out = df.copy()
    for col in ["entry_time", "signal_time", "exit_time", "jst_entry_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    if "entry_time" not in out.columns and "jst_entry_time" in out.columns:
        out["entry_time"] = out["jst_entry_time"]
    required = ["entry_time", "symbol_group", "portfolio_rank", "side", "r", "result"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    out["result"] = out["result"].astype(str).str.lower().str.strip()
    out["side"] = out["side"].astype(str).str.upper().str.strip()
    out = out.dropna(subset=["entry_time", "r"]).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    return out


def profit_factor(r: pd.Series) -> float | None:
    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
    if gross_loss_abs <= 0:
        return None
    return gross_win / gross_loss_abs


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str).str.lower():
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def max_drawdown_r(r: pd.Series) -> float:
    equity = pd.to_numeric(r, errors="coerce").fillna(0).cumsum()
    if equity.empty:
        return 0.0
    dd = equity - equity.cummax()
    return float(abs(dd.min()))


def summarize(df: pd.DataFrame, *, group_name: str, group_value: str) -> dict[str, object]:
    if df.empty:
        return {
            "group_name": group_name,
            "group_value": group_value,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_drawdown_r": 0.0,
        }
    ordered = df.sort_values("entry_time", kind="mergesort")
    r = pd.to_numeric(ordered["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    return {
        "group_name": group_name,
        "group_value": group_value,
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(ordered),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(ordered["result"]),
        "max_drawdown_r": max_drawdown_r(r),
    }


def apply_gold_abc_buy_loss_guard(
    df: pd.DataFrame,
    *,
    last_n: int,
    min_losses: int,
    lookback_days: int | None,
) -> pd.DataFrame:
    out = df.copy()
    out["gold_abc_buy_guard_skip"] = False
    out["gold_abc_buy_guard_reason"] = ""
    out["guard_last_n"] = last_n
    out["guard_min_losses"] = min_losses
    out["guard_lookback_days"] = lookback_days

    for idx, row in out.iterrows():
        is_target = row["symbol_group"] == "GOLD" and row["portfolio_rank"] == "GOLD_ABC" and row["side"] == "BUY"
        if not is_target:
            continue
        prev = out.iloc[:idx]
        prev = prev[(prev["symbol_group"] == "GOLD") & (prev["portfolio_rank"] == "GOLD_ABC") & (prev["side"] == "BUY")]
        if lookback_days is not None:
            prev = prev[prev["entry_time"] >= row["entry_time"] - pd.Timedelta(days=lookback_days)]
        last = prev.tail(last_n)
        loss_count = int(last["result"].eq("loss").sum())
        if len(last) >= last_n and loss_count >= min_losses:
            out.at[idx, "gold_abc_buy_guard_skip"] = True
            out.at[idx, "gold_abc_buy_guard_reason"] = f"last_{last_n}_gold_abc_buy_had_{loss_count}_losses"
    out["after_guard_keep"] = ~out["gold_abc_buy_guard_skip"]
    return out


def build_guard_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.append(summarize(df, group_name="baseline", group_value="FINAL_PORTFOLIO"))
    kept = df[df["after_guard_keep"]].copy()
    skipped = df[df["gold_abc_buy_guard_skip"]].copy()
    rows.append(summarize(kept, group_name="after_guard", group_value="KEEP_ONLY"))
    rows.append(summarize(skipped, group_name="skipped", group_value="GOLD_ABC_BUY_SKIPPED"))

    mar = df[df["entry_time"].dt.strftime("%Y-%m") == "2025-03"].copy()
    rows.append(summarize(mar, group_name="month_baseline", group_value="2025-03"))
    rows.append(summarize(mar[mar["after_guard_keep"]].copy(), group_name="month_after_guard", group_value="2025-03_KEEP_ONLY"))
    rows.append(summarize(mar[mar["gold_abc_buy_guard_skip"]].copy(), group_name="month_skipped", group_value="2025-03_SKIPPED"))

    target = df[(df["symbol_group"] == "GOLD") & (df["portfolio_rank"] == "GOLD_ABC") & (df["side"] == "BUY")].copy()
    rows.append(summarize(target, group_name="target_baseline", group_value="GOLD_ABC_BUY"))
    rows.append(summarize(target[target["after_guard_keep"]].copy(), group_name="target_after_guard", group_value="GOLD_ABC_BUY_KEEP_ONLY"))
    rows.append(summarize(target[target["gold_abc_buy_guard_skip"]].copy(), group_name="target_skipped", group_value="GOLD_ABC_BUY_SKIPPED"))
    return pd.DataFrame(rows)


def find_loss_streaks(df: pd.DataFrame, *, min_streak: int = 4) -> pd.DataFrame:
    ordered = df.sort_values("entry_time", kind="mergesort")
    rows: list[dict[str, object]] = []
    current: list[pd.Series] = []
    for _, row in ordered.iterrows():
        if row["result"] == "loss":
            current.append(row)
        else:
            if len(current) >= min_streak:
                streak_df = pd.DataFrame(current)
                rows.append(
                    {
                        "streak_len": len(streak_df),
                        "start_time": streak_df["entry_time"].iloc[0],
                        "end_time": streak_df["entry_time"].iloc[-1],
                        "total_r": float(streak_df["r"].sum()),
                        "symbols": ",".join(sorted(streak_df["symbol_group"].astype(str).unique())),
                        "ranks": ",".join(sorted(streak_df["portfolio_rank"].astype(str).unique())),
                        "sides": ",".join(sorted(streak_df["side"].astype(str).unique())),
                        "trade_nos": ",".join(streak_df.get("portfolio_trade_no", streak_df.index).astype(str).tolist()),
                    }
                )
            current = []
    if len(current) >= min_streak:
        streak_df = pd.DataFrame(current)
        rows.append(
            {
                "streak_len": len(streak_df),
                "start_time": streak_df["entry_time"].iloc[0],
                "end_time": streak_df["entry_time"].iloc[-1],
                "total_r": float(streak_df["r"].sum()),
                "symbols": ",".join(sorted(streak_df["symbol_group"].astype(str).unique())),
                "ranks": ",".join(sorted(streak_df["portfolio_rank"].astype(str).unique())),
                "sides": ",".join(sorted(streak_df["side"].astype(str).unique())),
                "trade_nos": ",".join(streak_df.get("portfolio_trade_no", streak_df.index).astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows)


def monthly_gold_abc_buy_similarity(df: pd.DataFrame, *, anchor_month: str = "2025-03") -> pd.DataFrame:
    gold_abc_buy = df[(df["symbol_group"] == "GOLD") & (df["portfolio_rank"] == "GOLD_ABC") & (df["side"] == "BUY")].copy()
    if gold_abc_buy.empty:
        return pd.DataFrame()
    gold_abc_buy["entry_month"] = gold_abc_buy["entry_time"].dt.to_period("M").astype(str)
    rows: list[dict[str, object]] = []
    feature_cols = []
    optional_numeric = [
        "signal_atr",
        "risk",
        "signal_macd",
        "h1_macd_delta3",
        "h1_rsi14",
        "h1_adx14",
        "m15_rsi14",
        "m15_stoch14",
        "m15_rci9",
        "m15_bb_pos20",
        "m15_gap20_atr",
        "m15_close_change_3_atr",
    ]
    for col in optional_numeric:
        if col in gold_abc_buy.columns:
            gold_abc_buy[col] = pd.to_numeric(gold_abc_buy[col], errors="coerce")
            feature_cols.append(col)

    for month, group in gold_abc_buy.groupby("entry_month"):
        r = pd.to_numeric(group["r"], errors="coerce")
        row = {
            "month": month,
            "trades": int(len(group)),
            "wins": int((r > 0).sum()),
            "losses": int((r < 0).sum()),
            "win_rate": float((r > 0).mean()) if len(group) else None,
            "total_r": float(r.sum()),
            "max_consecutive_losses": max_consecutive_losses(group["result"]),
        }
        for col in feature_cols:
            row[f"avg_{col}"] = float(group[col].mean()) if group[col].notna().any() else np.nan
        rows.append(row)
    monthly = pd.DataFrame(rows)
    if monthly.empty or anchor_month not in set(monthly["month"]):
        return monthly

    # Similarity is based on available monthly numeric features and performance stress metrics.
    sim_features = [c for c in monthly.columns if c.startswith("avg_")]
    sim_features += ["win_rate", "total_r", "max_consecutive_losses"]
    sim_features = [c for c in sim_features if c in monthly.columns and monthly[c].notna().any()]
    if not sim_features:
        monthly["similarity_to_anchor"] = np.nan
        return monthly

    values = monthly[sim_features].astype(float)
    std = values.std(ddof=0).replace(0, np.nan)
    z = (values - values.mean()) / std
    z = z.fillna(0.0)
    anchor_vec = z.loc[monthly["month"].eq(anchor_month)].iloc[0]
    distances = ((z - anchor_vec) ** 2).sum(axis=1).pow(0.5)
    monthly["distance_to_anchor"] = distances
    monthly["similarity_to_anchor"] = 1.0 / (1.0 + distances)
    monthly["anchor_month"] = anchor_month
    return monthly.sort_values("similarity_to_anchor", ascending=False, kind="mergesort").reset_index(drop=True)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze whether March-like GOLD ABC BUY losing regime can be guarded.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--out-streaks", type=Path, default=DEFAULT_OUT_STREAKS)
    parser.add_argument("--out-monthly-similarity", type=Path, default=DEFAULT_OUT_MONTHLY_SIMILARITY)
    parser.add_argument("--last-n", type=int, default=3)
    parser.add_argument("--min-losses", type=int, default=3)
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--anchor-month", default="2025-03")
    args = parser.parse_args()

    trades_csv = resolve_path(args.trades_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    out_streaks = resolve_path(args.out_streaks)
    out_monthly_similarity = resolve_path(args.out_monthly_similarity)

    trades = read_trades(trades_csv)
    guarded = apply_gold_abc_buy_loss_guard(
        trades,
        last_n=args.last_n,
        min_losses=args.min_losses,
        lookback_days=args.lookback_days,
    )
    summary = build_guard_summary(guarded)
    streaks = find_loss_streaks(trades, min_streak=4)
    monthly_similarity = monthly_gold_abc_buy_similarity(trades, anchor_month=args.anchor_month)

    write_csv(out_summary, summary)
    write_csv(out_trades, guarded)
    write_csv(out_streaks, streaks)
    write_csv(out_monthly_similarity, monthly_similarity)

    print("Trades CSV:", trades_csv)
    print("Guard:", f"skip GOLD ABC BUY if last {args.last_n} GOLD ABC BUY within {args.lookback_days} days have >= {args.min_losses} losses")
    print("Rows:", len(trades))
    print("Skipped rows:", int(guarded["gold_abc_buy_guard_skip"].sum()))
    print("Saved summary:", out_summary)
    print("Saved guarded trades:", out_trades)
    print("Saved streaks:", out_streaks)
    print("Saved monthly similarity:", out_monthly_similarity)

    display_cols = [
        "group_name",
        "group_value",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "max_drawdown_r",
    ]
    print_table("GOLD MARCH REGIME GUARD SUMMARY", summary[display_cols])
    print_table("LOSS STREAKS", streaks)
    if not monthly_similarity.empty:
        print_table("GOLD ABC BUY MONTHLY SIMILARITY TO ANCHOR", monthly_similarity.head(12))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
