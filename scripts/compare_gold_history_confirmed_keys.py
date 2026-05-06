from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_CONFIRMED = PROJECT_ROOT / "data" / "results" / "gold_current_rules_confirmed_trades.csv"
DEFAULT_OUT_DETAIL = PROJECT_ROOT / "data" / "results" / "gold_history_confirmed_key_diff.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_history_confirmed_key_diff_summary.csv"

GOLD_LABELS = ["GOLD_ABC_V3", "GOLD_EXTRA_HIGH_RSI_STOCH", "GOLD_EXTRA_BB_BALANCE"]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_any_csv(path: Path) -> pd.DataFrame:
    path = resolve_path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if len(df.columns) == 1:
        df = pd.read_csv(path, sep=";")
    return df.copy()


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def normalize(df: pd.DataFrame, *, source: str) -> pd.DataFrame:
    label_col = find_col(df, ["strategy_label", "label", "rule_name", "model", "signal_model"])
    time_col = find_col(df, ["signal_time", "time", "entry_time", "open_time"])
    side_col = find_col(df, ["side", "direction", "signal_side"])
    r_col = find_col(df, ["r", "R", "pnl_r", "result_r", "realized_r"])
    result_col = find_col(df, ["result", "outcome", "exit_reason"])
    if label_col is None or time_col is None or side_col is None:
        raise ValueError(f"Could not find required columns for {source}: label={label_col}, time={time_col}, side={side_col}")

    out = pd.DataFrame()
    out["source"] = source
    out["strategy_label"] = df[label_col].astype(str)
    out["signal_time"] = pd.to_datetime(df[time_col], errors="coerce")
    out["side"] = df[side_col].astype(str).str.upper()
    if r_col:
        out["r"] = pd.to_numeric(df[r_col], errors="coerce")
    elif result_col:
        result = df[result_col].astype(str).str.lower()
        out["r"] = result.map(lambda x: 1.0 if "win" in x or "tp" in x else -1.0 if "loss" in x or "sl" in x else 0.0)
    else:
        out["r"] = pd.NA
    out = out.dropna(subset=["signal_time"])
    out = out[out["strategy_label"].isin(GOLD_LABELS)].copy()
    out["key"] = out["strategy_label"] + "|" + out["signal_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + out["side"]
    return out


def summarize_detail(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, g in detail.groupby("strategy_label", dropna=False):
        for status, sg in g.groupby("match_status", dropna=False):
            rows.append(
                {
                    "strategy_label": label,
                    "match_status": status,
                    "rows": int(len(sg)),
                    "history_r_sum": float(pd.to_numeric(sg.get("history_r"), errors="coerce").sum()) if "history_r" in sg else 0.0,
                    "confirmed_r_sum": float(pd.to_numeric(sg.get("confirmed_r"), errors="coerce").sum()) if "confirmed_r" in sg else 0.0,
                    "first_time": sg["signal_time"].min(),
                    "last_time": sg["signal_time"].max(),
                }
            )
    return pd.DataFrame(rows).sort_values(["strategy_label", "match_status"], kind="mergesort")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare GOLD history and confirmed-live detector by exact strategy/time/side key.")
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--confirmed-trades-csv", type=Path, default=DEFAULT_CONFIRMED)
    parser.add_argument("--out-detail", type=Path, default=DEFAULT_OUT_DETAIL)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    history = normalize(read_any_csv(args.history_csv), source="history")
    confirmed = normalize(read_any_csv(args.confirmed_trades_csv), source="confirmed")

    if args.start:
        start = pd.to_datetime(args.start, errors="coerce")
        history = history[history["signal_time"] >= start]
        confirmed = confirmed[confirmed["signal_time"] >= start]
    if args.end:
        end = pd.to_datetime(args.end, errors="coerce")
        history = history[history["signal_time"] <= end]
        confirmed = confirmed[confirmed["signal_time"] <= end]

    if not args.start and not args.end and not confirmed.empty:
        start = confirmed["signal_time"].min()
        end = confirmed["signal_time"].max()
        history = history[(history["signal_time"] >= start) & (history["signal_time"] <= end)]

    h = history.rename(columns={"r": "history_r"})[["key", "strategy_label", "signal_time", "side", "history_r"]]
    c = confirmed.rename(columns={"r": "confirmed_r"})[["key", "strategy_label", "signal_time", "side", "confirmed_r"]]
    detail = h.merge(c[["key", "confirmed_r"]], on="key", how="outer", indicator=True)

    # Recover fields for confirmed-only rows.
    c_fields = c[["key", "strategy_label", "signal_time", "side"]].rename(
        columns={"strategy_label": "confirmed_strategy_label", "signal_time": "confirmed_signal_time", "side": "confirmed_side"}
    )
    detail = detail.merge(c_fields, on="key", how="left")
    detail["strategy_label"] = detail["strategy_label"].fillna(detail["confirmed_strategy_label"])
    detail["signal_time"] = detail["signal_time"].fillna(detail["confirmed_signal_time"])
    detail["side"] = detail["side"].fillna(detail["confirmed_side"])
    detail = detail.drop(columns=["confirmed_strategy_label", "confirmed_signal_time", "confirmed_side"], errors="ignore")
    detail["match_status"] = detail["_merge"].map({"both": "both", "left_only": "history_only", "right_only": "confirmed_only"})
    detail = detail.drop(columns=["_merge"]).sort_values(["strategy_label", "signal_time", "side"], kind="mergesort")

    summary = summarize_detail(detail)
    out_detail = resolve_path(args.out_detail)
    out_summary = resolve_path(args.out_summary)
    out_detail.parent.mkdir(parents=True, exist_ok=True)
    detail.to_csv(out_detail, index=False, encoding="utf-8-sig")
    summary.to_csv(out_summary, index=False, encoding="utf-8-sig")

    print("History rows:", len(history), "Confirmed rows:", len(confirmed))
    print("Overlap range:", confirmed["signal_time"].min() if not confirmed.empty else None, "->", confirmed["signal_time"].max() if not confirmed.empty else None)
    print("\n" + "=" * 140)
    print("GOLD HISTORY VS CONFIRMED KEY DIFF SUMMARY")
    print("=" * 140)
    print(summary.to_string(index=False))
    print("\nWrote detail :", out_detail)
    print("Wrote summary:", out_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
