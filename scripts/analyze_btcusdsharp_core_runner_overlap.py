from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CORE_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_mixed_sl_avg_spread_trades.csv"
DEFAULT_RUNNER_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_value_width_edge_trades.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btcusdsharp_core_runner_overlap_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btcusdsharp_core_runner_overlap_trades.csv"
DEFAULT_OUT_OVERLAP = PROJECT_ROOT / "data" / "results" / "btcusdsharp_core_runner_overlap_pairs.csv"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    required = ["signal_idx", "entry_idx", "signal_time", "entry_time", "side", "r", "result"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    out = df.copy()
    out["signal_idx"] = pd.to_numeric(out["signal_idx"], errors="coerce")
    out["entry_idx"] = pd.to_numeric(out["entry_idx"], errors="coerce")
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    out["signal_time"] = pd.to_datetime(out["signal_time"], errors="coerce")
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["signal_idx", "entry_idx", "signal_time", "entry_time", "r"]).copy()
    out["signal_idx"] = out["signal_idx"].astype(int)
    out["entry_idx"] = out["entry_idx"].astype(int)
    out["side"] = out["side"].astype(str).str.upper().str.strip()
    return out.sort_values(["entry_idx", "signal_idx"], kind="mergesort").reset_index(drop=True)


def prepare_core(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["notify_tier"].isin(["HIGH", "STANDARD"])].copy()
    out["signal_family"] = "core_high_standard"
    out["strategy_label"] = "BTC_CORE_HIGH_STANDARD"
    out["priority_core_first"] = 1
    out["priority_runner_first"] = 2
    if "sl_mode" not in out.columns:
        out["sl_mode"] = "swing_sl"
    if "rule_name" not in out.columns:
        out["rule_name"] = out["notify_tier"].astype(str)
    return out


def prepare_runner(df: pd.DataFrame, *, runner_rule_name: str) -> pd.DataFrame:
    out = df[df["rule_name"].astype(str).eq(runner_rule_name)].copy()
    out["notify_tier"] = "RUNNER"
    out["signal_family"] = "value_width_runner"
    out["strategy_label"] = "BTC_RUNNER_RR2_RISK1"
    out["priority_core_first"] = 2
    out["priority_runner_first"] = 1
    if "sl_mode" not in out.columns:
        out["sl_mode"] = "fixed_atr_sl"
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


def summarize(df: pd.DataFrame, *, group_name: str, group_value: str, description: str) -> dict[str, object]:
    if df.empty:
        return {
            "group_name": group_name,
            "group_value": group_value,
            "description": description,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "buy_win_rate": None,
            "sell_win_rate": None,
            "trades_per_month": None,
        }
    ordered = df.sort_values(["entry_idx", "signal_idx"], kind="mergesort").copy()
    r = pd.to_numeric(ordered["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = ordered[ordered["side"].eq("BUY")]
    sell = ordered[ordered["side"].eq("SELL")]
    months = max(1.0, (pd.Timestamp(ordered["entry_time"].max()) - pd.Timestamp(ordered["entry_time"].min())).days / 30.4375)
    return {
        "group_name": group_name,
        "group_value": group_value,
        "description": description,
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(ordered),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(ordered["result"]),
        "buy_trades": int(len(buy)),
        "sell_trades": int(len(sell)),
        "buy_win_rate": float((buy["r"] > 0).sum() / len(buy)) if len(buy) else None,
        "sell_win_rate": float((sell["r"] > 0).sum() / len(sell)) if len(sell) else None,
        "trades_per_month": float(len(ordered) / months),
    }


def dedupe_signals(df: pd.DataFrame, *, priority_col: str, label: str) -> pd.DataFrame:
    out = df.copy()
    out["dedupe_variant"] = label
    out["_order"] = np.arange(len(out))
    out = out.sort_values(["signal_idx", "side", priority_col, "_order"], kind="mergesort")
    out = out.groupby(["signal_idx", "side"], as_index=False, dropna=False).head(1).copy()
    out = out.drop(columns=["_order"])
    return out.sort_values(["entry_idx", "signal_idx"], kind="mergesort").reset_index(drop=True)


def build_overlap_pairs(core: pd.DataFrame, runner: pd.DataFrame) -> pd.DataFrame:
    core_cols = [
        "signal_idx",
        "side",
        "entry_idx",
        "entry_time",
        "notify_tier",
        "r",
        "result",
        "exit_reason",
        "bars_held",
    ]
    runner_cols = [
        "signal_idx",
        "side",
        "entry_idx",
        "entry_time",
        "rule_name",
        "r",
        "result",
        "exit_reason",
        "bars_held",
    ]
    core_subset = core[[col for col in core_cols if col in core.columns]].copy()
    runner_subset = runner[[col for col in runner_cols if col in runner.columns]].copy()
    merged = pd.merge(
        core_subset,
        runner_subset,
        on=["signal_idx", "side"],
        how="inner",
        suffixes=("_core", "_runner"),
    )
    if not merged.empty:
        merged["r_diff_runner_minus_core"] = pd.to_numeric(merged["r_runner"], errors="coerce") - pd.to_numeric(
            merged["r_core"], errors="coerce"
        )
    return merged.sort_values(["entry_idx_core", "signal_idx"], kind="mergesort").reset_index(drop=True) if not merged.empty else merged


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze overlap between BTC core HIGH/STANDARD and value-width runner signals.")
    parser.add_argument("--core-trades-csv", type=Path, default=DEFAULT_CORE_TRADES_CSV)
    parser.add_argument("--runner-trades-csv", type=Path, default=DEFAULT_RUNNER_TRADES_CSV)
    parser.add_argument("--runner-rule-name", default="trend_pull_runner_rr2.0_risk1.0")
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--out-overlap", type=Path, default=DEFAULT_OUT_OVERLAP)
    args = parser.parse_args()

    core_path = resolve_path(args.core_trades_csv)
    runner_path = resolve_path(args.runner_trades_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    out_overlap = resolve_path(args.out_overlap)

    core_raw = read_trades(core_path)
    runner_raw = read_trades(runner_path)
    core = prepare_core(core_raw)
    runner = prepare_runner(runner_raw, runner_rule_name=args.runner_rule_name)

    combined_raw = pd.concat([core, runner], ignore_index=True, sort=False)
    core_first = dedupe_signals(combined_raw, priority_col="priority_core_first", label="core_first")
    runner_first = dedupe_signals(combined_raw, priority_col="priority_runner_first", label="runner_first")

    overlap_pairs = build_overlap_pairs(core, runner)
    overlap_count = int(len(overlap_pairs))
    core_signal_keys = set(zip(core["signal_idx"], core["side"]))
    runner_signal_keys = set(zip(runner["signal_idx"], runner["side"]))
    union_count = len(core_signal_keys | runner_signal_keys)

    summary_rows: list[dict[str, object]] = []
    summary_rows.append(
        summarize(
            core,
            group_name="single",
            group_value="CORE_HIGH_STANDARD",
            description="BTC core notifications only: HIGH + STANDARD from mixed SL average-spread backtest.",
        )
    )
    summary_rows.append(
        summarize(
            runner,
            group_name="single",
            group_value="RUNNER_RR2_RISK1",
            description="Value-width runner only: trend_pull_runner_rr2.0_risk1.0.",
        )
    )
    summary_rows.append(
        summarize(
            core_first,
            group_name="combined_deduped",
            group_value="CORE_FIRST",
            description="Core and runner combined; duplicate signal_idx/side keeps core trade first.",
        )
    )
    summary_rows.append(
        summarize(
            runner_first,
            group_name="combined_deduped",
            group_value="RUNNER_FIRST",
            description="Core and runner combined; duplicate signal_idx/side keeps runner trade first.",
        )
    )
    summary_rows.append(
        summarize(
            core[~core.apply(lambda row: (row["signal_idx"], row["side"]) in runner_signal_keys, axis=1)].copy(),
            group_name="unique_only",
            group_value="CORE_UNIQUE_ONLY",
            description="Core trades that do not overlap with runner on signal_idx/side.",
        )
    )
    summary_rows.append(
        summarize(
            runner[~runner.apply(lambda row: (row["signal_idx"], row["side"]) in core_signal_keys, axis=1)].copy(),
            group_name="unique_only",
            group_value="RUNNER_UNIQUE_ONLY",
            description="Runner trades that do not overlap with core on signal_idx/side.",
        )
    )

    summary = pd.DataFrame(summary_rows)
    summary["core_count"] = len(core)
    summary["runner_count"] = len(runner)
    summary["overlap_count"] = overlap_count
    summary["union_count"] = union_count
    summary["overlap_rate_vs_core"] = overlap_count / len(core) if len(core) else None
    summary["overlap_rate_vs_runner"] = overlap_count / len(runner) if len(runner) else None

    out_all = pd.concat(
        [
            core.assign(output_set="single_core"),
            runner.assign(output_set="single_runner"),
            core_first.assign(output_set="combined_core_first"),
            runner_first.assign(output_set="combined_runner_first"),
        ],
        ignore_index=True,
        sort=False,
    )

    write_csv(out_summary, summary)
    write_csv(out_trades, out_all)
    write_csv(out_overlap, overlap_pairs)

    print("Core trades CSV:", core_path)
    print("Runner trades CSV:", runner_path)
    print("Runner rule:", args.runner_rule_name)
    print("Core HIGH/STANDARD trades:", len(core))
    print("Runner trades:", len(runner))
    print("Overlap signal_idx/side:", overlap_count)
    print("Union signal_idx/side:", union_count)
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)
    print("Saved overlap pairs:", out_overlap)

    display_cols = [
        "group_name",
        "group_value",
        "trades",
        "buy_trades",
        "sell_trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "trades_per_month",
        "overlap_count",
        "union_count",
    ]
    print_table("BTCUSD# CORE/RUNNER OVERLAP SUMMARY", summary[display_cols])

    if not overlap_pairs.empty:
        overlap_summary = pd.DataFrame(
            [
                {
                    "overlap_count": overlap_count,
                    "core_total_r_on_overlap": float(pd.to_numeric(overlap_pairs["r_core"], errors="coerce").sum()),
                    "runner_total_r_on_overlap": float(pd.to_numeric(overlap_pairs["r_runner"], errors="coerce").sum()),
                    "runner_minus_core_total_r": float(overlap_pairs["r_diff_runner_minus_core"].sum()),
                    "runner_better_count": int((overlap_pairs["r_diff_runner_minus_core"] > 0).sum()),
                    "core_better_count": int((overlap_pairs["r_diff_runner_minus_core"] < 0).sum()),
                    "same_r_count": int((overlap_pairs["r_diff_runner_minus_core"] == 0).sum()),
                }
            ]
        )
        print_table("OVERLAP CORE VS RUNNER R COMPARISON", overlap_summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
