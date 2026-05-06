from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_CONFIRMED = PROJECT_ROOT / "data" / "results" / "gold_current_rules_confirmed_trades.csv"
DEFAULT_OUT = PROJECT_ROOT / "data" / "results" / "gold_confirmed_vs_history_audit.csv"

GOLD_LABELS = {
    "GOLD_ABC_V3",
    "GOLD_EXTRA_HIGH_RSI_STOCH",
    "GOLD_EXTRA_BB_BALANCE",
    "GOLD_COUNTER_BUY_ONLY",
}


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def read_any_csv(path: Path) -> pd.DataFrame:
    path = resolve_path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if len(df.columns) == 1:
        df = pd.read_csv(path, sep=";")
    return df.copy()


def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    label_col = find_col(df, ["strategy_label", "label", "rule_name", "model", "signal_model"])
    time_col = find_col(df, ["signal_time", "time", "entry_time", "open_time"])
    side_col = find_col(df, ["side", "direction", "signal_side"])
    r_col = find_col(df, ["r", "R", "pnl_r", "result_r", "realized_r"])
    result_col = find_col(df, ["result", "outcome", "exit_reason"])

    out = pd.DataFrame()
    out["source"] = "history"
    out["strategy_label"] = df[label_col].astype(str) if label_col else ""
    out["signal_time"] = pd.to_datetime(df[time_col], errors="coerce") if time_col else pd.NaT
    out["side"] = df[side_col].astype(str).str.upper() if side_col else ""
    if r_col:
        out["r"] = pd.to_numeric(df[r_col], errors="coerce")
    elif result_col:
        result = df[result_col].astype(str).str.lower()
        out["r"] = result.map(lambda x: 1.0 if "win" in x or "tp" in x else -1.0 if "loss" in x or "sl" in x else 0.0)
    else:
        out["r"] = pd.NA
    out["raw_columns_found"] = f"label={label_col};time={time_col};side={side_col};r={r_col};result={result_col}"
    return out


def normalize_confirmed(df: pd.DataFrame) -> pd.DataFrame:
    label_col = find_col(df, ["strategy_label", "label", "rule_name"])
    time_col = find_col(df, ["signal_time", "time", "entry_time"])
    side_col = find_col(df, ["side", "direction"])
    r_col = find_col(df, ["r", "R", "pnl_r"])
    out = pd.DataFrame()
    out["source"] = "confirmed_current_live_detector"
    out["strategy_label"] = df[label_col].astype(str) if label_col else ""
    out["signal_time"] = pd.to_datetime(df[time_col], errors="coerce") if time_col else pd.NaT
    out["side"] = df[side_col].astype(str).str.upper() if side_col else ""
    out["r"] = pd.to_numeric(df[r_col], errors="coerce") if r_col else pd.NA
    out["raw_columns_found"] = f"label={label_col};time={time_col};side={side_col};r={r_col}"
    return out


def summarize(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, g in df.groupby("strategy_label", dropna=False):
        r = pd.to_numeric(g["r"], errors="coerce")
        known = r.dropna()
        wins = int((known > 0).sum()) if len(known) else 0
        losses = int((known < 0).sum()) if len(known) else 0
        gross_win = float(known[known > 0].sum()) if len(known) else 0.0
        gross_loss = float(abs(known[known < 0].sum())) if len(known) else 0.0
        rows.append(
            {
                "source": source_name,
                "strategy_label": label,
                "trades": int(len(g)),
                "wins": wins,
                "losses": losses,
                "win_rate": wins / len(known) if len(known) else None,
                "total_r": float(known.sum()) if len(known) else None,
                "avg_r": float(known.mean()) if len(known) else None,
                "pf": gross_win / gross_loss if gross_loss > 0 else None,
                "first_signal_time": g["signal_time"].min(),
                "last_signal_time": g["signal_time"].max(),
            }
        )
    return pd.DataFrame(rows).sort_values(["source", "strategy_label"], kind="mergesort")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare current GOLD confirmed-live-detector trades against existing history CSV in the overlapping period.")
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--confirmed-trades-csv", type=Path, default=DEFAULT_CONFIRMED)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--labels", default=",".join(sorted(GOLD_LABELS)))
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    labels = {x.strip() for x in args.labels.split(",") if x.strip()}
    hist_raw = read_any_csv(args.history_csv)
    conf_raw = read_any_csv(args.confirmed_trades_csv)
    hist = normalize_history(hist_raw)
    conf = normalize_confirmed(conf_raw)

    hist = hist[hist["strategy_label"].isin(labels)].copy()
    conf = conf[conf["strategy_label"].isin(labels)].copy()

    if args.start:
        start = pd.to_datetime(args.start, errors="coerce")
        hist = hist[hist["signal_time"] >= start]
        conf = conf[conf["signal_time"] >= start]
    if args.end:
        end = pd.to_datetime(args.end, errors="coerce")
        hist = hist[hist["signal_time"] <= end]
        conf = conf[conf["signal_time"] <= end]

    # If no explicit range is supplied, compare using the confirmed detector range to avoid misleading full-history vs partial-M5 comparisons.
    if not args.start and not args.end and not conf.empty:
        start = conf["signal_time"].min()
        end = conf["signal_time"].max()
        hist_overlap = hist[(hist["signal_time"] >= start) & (hist["signal_time"] <= end)].copy()
    else:
        hist_overlap = hist.copy()

    summary = pd.concat(
        [
            summarize(hist_overlap, "history_overlap"),
            summarize(conf, "confirmed_current_live_detector"),
        ],
        ignore_index=True,
    )
    out_path = resolve_path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("History columns found:", hist["raw_columns_found"].iloc[0] if not hist.empty else "no matching history rows")
    print("Confirmed columns found:", conf["raw_columns_found"].iloc[0] if not conf.empty else "no confirmed rows")
    print("History raw rows:", len(hist_raw), "matching GOLD labels:", len(hist))
    print("Confirmed rows:", len(conf))
    if not conf.empty:
        print("Overlap range:", conf["signal_time"].min(), "->", conf["signal_time"].max())
    print("\n" + "=" * 140)
    print("GOLD CONFIRMED VS HISTORY SUMMARY")
    print("=" * 140)
    print(summary.to_string(index=False))
    print("\nWrote:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
