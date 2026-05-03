from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btc_mtf_extra_edge_trades.csv"
DEFAULT_RUNNER_CSV = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results"
DEFAULT_RULE_PREFIX = "BTC_SCALP_H1_M5_REENTRY_rr2.0_risk0.8"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def parse_time_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def profit_factor(r: pd.Series) -> float | None:
    r = pd.to_numeric(r, errors="coerce").dropna()
    gross_win = float(r[r > 0].sum())
    gross_loss = float(abs(r[r < 0].sum()))
    if gross_loss <= 0:
        return None
    return gross_win / gross_loss


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str):
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def max_drawdown_r(r: pd.Series) -> float:
    r = pd.to_numeric(r, errors="coerce").fillna(0.0)
    if r.empty:
        return 0.0
    eq = r.cumsum()
    peak = eq.cummax()
    return float(abs((eq - peak).min()))


def summarize(df: pd.DataFrame, *, name: str) -> dict[str, Any]:
    if df.empty:
        return {
            "name": name,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_dd_r": 0.0,
        }
    r = pd.to_numeric(df["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    return {
        "name": name,
        "trades": int(len(df)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(df)),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(df["result"]),
        "max_dd_r": max_drawdown_r(r),
    }


def summarize_group(df: pd.DataFrame, group_col: str, *, sort_col: str = "total_r") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if group_col not in df.columns:
        return pd.DataFrame()
    for key, g in df.groupby(group_col, dropna=False):
        rows.append(summarize(g.sort_values("entry_time"), name=str(key)))
    out = pd.DataFrame(rows)
    if not out.empty and sort_col in out.columns:
        out = out.sort_values(sort_col, ascending=False, kind="mergesort")
    return out


def load_candidate_trades(path: Path, rule_prefix: str) -> pd.DataFrame:
    df = read_csv(path)
    df = parse_time_columns(df, ["signal_time", "entry_time", "exit_time"])
    if "rule_name" not in df.columns:
        raise ValueError(f"Missing rule_name in {path}")
    out = df[df["rule_name"].astype(str).str.startswith(rule_prefix)].copy()
    if out.empty:
        available = sorted(df["rule_name"].astype(str).unique().tolist())[:20]
        raise ValueError(f"No trades found for rule_prefix={rule_prefix}. First available rules={available}")
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    if "entry_hour" not in out.columns:
        out["entry_hour"] = out["entry_time"].dt.hour
    out["entry_date"] = out["entry_time"].dt.date.astype(str)
    out["entry_month"] = out["entry_time"].dt.to_period("M").astype(str)
    out["entry_dow"] = out["entry_time"].dt.day_name()
    out["result"] = np.where(out["r"] > 0, "win", np.where(out["r"] < 0, "loss", "breakeven"))
    return out.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def normalize_runner_trades(path: Path) -> pd.DataFrame:
    df = read_csv(path)
    time_candidates = ["entry_time", "time", "signal_time"]
    for col in time_candidates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    label_cols = [c for c in ["strategy_label", "portfolio_rank", "signal_model", "rule_name"] if c in df.columns]
    if not label_cols:
        return pd.DataFrame()

    mask = pd.Series(False, index=df.index)
    for col in label_cols:
        mask = mask | df[col].astype(str).str.contains("BTC_RUNNER", case=False, na=False)
    if "symbol_group" in df.columns:
        mask = mask & df["symbol_group"].astype(str).str.upper().eq("BTC")
    elif "symbol" in df.columns:
        mask = mask & df["symbol"].astype(str).str.upper().str.contains("BTC", na=False)

    out = df[mask].copy()
    if out.empty:
        return out
    if "entry_time" not in out.columns:
        for col in ["time", "signal_time"]:
            if col in out.columns:
                out["entry_time"] = out[col]
                break
    out = out.dropna(subset=["entry_time"]).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    if "side" not in out.columns:
        out["side"] = ""
    return out


def add_runner_overlap(candidate: pd.DataFrame, runner: pd.DataFrame, tolerance_minutes: int) -> pd.DataFrame:
    out = candidate.copy()
    out["overlap_btc_runner"] = False
    out["nearest_runner_time"] = pd.NaT
    out["nearest_runner_minutes"] = np.nan

    if runner.empty:
        return out

    runner_times = runner["entry_time"].dropna().sort_values().to_numpy(dtype="datetime64[ns]")
    tol = pd.Timedelta(minutes=tolerance_minutes)

    for idx, row in out.iterrows():
        t = row["entry_time"]
        if pd.isna(t):
            continue
        diffs = np.abs(runner_times - np.datetime64(t))
        if len(diffs) == 0:
            continue
        nearest_pos = int(np.argmin(diffs))
        nearest_diff = pd.Timedelta(diffs[nearest_pos])
        nearest_time = pd.Timestamp(runner_times[nearest_pos])
        out.at[idx, "nearest_runner_time"] = nearest_time
        out.at[idx, "nearest_runner_minutes"] = float(nearest_diff.total_seconds() / 60.0)
        if nearest_diff <= tol:
            out.at[idx, "overlap_btc_runner"] = True
    return out


def apply_filters(df: pd.DataFrame, *, exclude_hours: set[int], exclude_sides: set[str]) -> pd.DataFrame:
    out = df.copy()
    if exclude_hours:
        out = out[~out["entry_hour"].isin(exclude_hours)].copy()
    if exclude_sides:
        out = out[~out["side"].astype(str).str.upper().isin(exclude_sides)].copy()
    return out.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def build_filter_ideas(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base = summarize(df, name="base")
    rows.append({"filter_name": "base", "excluded": "", **base})

    hour_stats = summarize_group(df, "entry_hour", sort_col="total_r")
    bad_hours = hour_stats[(hour_stats["trades"] >= 3) & ((hour_stats["total_r"] < 0) | (hour_stats["pf"].fillna(0) < 1.0))]
    for hour in bad_hours["name"].astype(int).tolist():
        filtered = apply_filters(df, exclude_hours={hour}, exclude_sides=set())
        rows.append({"filter_name": f"exclude_hour_{hour}", "excluded": f"hour={hour}", **summarize(filtered, name=f"exclude_hour_{hour}")})

    # Greedy hour removal: remove worst hours while not deleting too many trades.
    excluded: set[int] = set()
    current = df.copy()
    for step in range(1, 5):
        hs = summarize_group(current, "entry_hour", sort_col="total_r")
        hs = hs[hs["trades"] >= 3].sort_values(["total_r", "pf"], ascending=[True, True], kind="mergesort")
        if hs.empty:
            break
        worst_hour = int(hs.iloc[0]["name"])
        if float(hs.iloc[0]["total_r"]) >= 0 and float(hs.iloc[0]["pf"] or 0) >= 1.0:
            break
        excluded.add(worst_hour)
        current = apply_filters(df, exclude_hours=excluded, exclude_sides=set())
        if len(current) < max(30, int(len(df) * 0.65)):
            break
        rows.append({"filter_name": f"greedy_exclude_bad_hours_step{step}", "excluded": ",".join(map(str, sorted(excluded))), **summarize(current, name=f"greedy_step{step}")})

    for side in sorted(df["side"].astype(str).str.upper().dropna().unique().tolist()):
        filtered = apply_filters(df, exclude_hours=set(), exclude_sides={side})
        rows.append({"filter_name": f"exclude_side_{side}", "excluded": f"side={side}", **summarize(filtered, name=f"exclude_side_{side}")})

    return pd.DataFrame(rows).sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], kind="mergesort")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame, *, max_rows: int = 30) -> None:
    print("\n" + "=" * 130)
    print(title)
    print("=" * 130)
    if df.empty:
        print("No data.")
    else:
        print(df.head(max_rows).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze BTC MTF candidate quality, runner overlap, and improvement filters.")
    parser.add_argument("--candidate-trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--runner-trades-csv", type=Path, default=DEFAULT_RUNNER_CSV)
    parser.add_argument("--rule-prefix", default=DEFAULT_RULE_PREFIX)
    parser.add_argument("--overlap-minutes", type=int, default=60)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    candidate_csv = resolve_path(args.candidate_trades_csv)
    runner_csv = resolve_path(args.runner_trades_csv)
    out_dir = resolve_path(args.out_dir)

    cand = load_candidate_trades(candidate_csv, args.rule_prefix)
    runner = normalize_runner_trades(runner_csv)
    cand = add_runner_overlap(cand, runner, args.overlap_minutes)

    overall = pd.DataFrame(
        [
            summarize(cand, name="candidate_all"),
            summarize(cand[cand["overlap_btc_runner"]], name=f"overlap_runner_within_{args.overlap_minutes}m"),
            summarize(cand[~cand["overlap_btc_runner"]], name=f"non_overlap_runner_within_{args.overlap_minutes}m"),
        ]
    )
    by_month = summarize_group(cand, "entry_month", sort_col="name").sort_values("name", kind="mergesort")
    by_hour = summarize_group(cand, "entry_hour", sort_col="total_r")
    by_side = summarize_group(cand, "side", sort_col="total_r")
    by_dow = summarize_group(cand, "entry_dow", sort_col="total_r")
    filter_ideas = build_filter_ideas(cand)

    base_name = args.rule_prefix.replace(".", "p")
    out_overall = out_dir / f"{base_name}_quality_overall.csv"
    out_month = out_dir / f"{base_name}_quality_by_month.csv"
    out_hour = out_dir / f"{base_name}_quality_by_hour.csv"
    out_side = out_dir / f"{base_name}_quality_by_side.csv"
    out_dow = out_dir / f"{base_name}_quality_by_dow.csv"
    out_filter = out_dir / f"{base_name}_quality_filter_ideas.csv"
    out_trades = out_dir / f"{base_name}_quality_trades_with_overlap.csv"

    write_csv(out_overall, overall)
    write_csv(out_month, by_month)
    write_csv(out_hour, by_hour)
    write_csv(out_side, by_side)
    write_csv(out_dow, by_dow)
    write_csv(out_filter, filter_ideas)
    write_csv(out_trades, cand)

    print("Candidate trades CSV:", candidate_csv)
    print("Runner trades CSV:", runner_csv)
    print("Rule prefix:", args.rule_prefix)
    print("Candidate trades:", len(cand), cand["entry_time"].min(), "to", cand["entry_time"].max())
    print("Runner trades loaded:", len(runner))
    print("Overlap minutes:", args.overlap_minutes)
    print("Saved:", out_overall)
    print("Saved:", out_month)
    print("Saved:", out_hour)
    print("Saved:", out_side)
    print("Saved:", out_dow)
    print("Saved:", out_filter)
    print("Saved:", out_trades)

    display = ["name", "trades", "wins", "losses", "win_rate", "total_r", "avg_r", "pf", "max_consecutive_losses", "max_dd_r"]
    print_table("OVERALL / RUNNER OVERLAP", overall[display])
    print_table("MONTHLY", by_month[display], max_rows=50)
    print_table("BY HOUR", by_hour[display], max_rows=30)
    print_table("BY SIDE", by_side[display], max_rows=10)
    filter_display = ["filter_name", "excluded", "trades", "win_rate", "total_r", "avg_r", "pf", "max_consecutive_losses", "max_dd_r"]
    print_table("FILTER IDEAS", filter_ideas[filter_display], max_rows=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
