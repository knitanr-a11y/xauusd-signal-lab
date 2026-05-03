from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ABC_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "goldsharp_xm_kiwami_gold_abc_v3_backtest_trades.csv"
DEFAULT_EDGE_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "gold_candle_indicator_edge_trades.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_abc_extra_overlap_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "gold_abc_extra_overlap_trades.csv"
DEFAULT_OUT_OVERLAP = PROJECT_ROOT / "data" / "results" / "gold_abc_extra_overlap_pairs.csv"

DEFAULT_EXTRA_RULES = [
    "gold_trend_rsi_stoch_rebound_rr1.5_risk1.5",
    "gold_trend_bb_candle_reject_rr1.5_risk1.5",
    "gold_trend_bb_candle_reject_rr2.0_risk1.0",
]
DEFAULT_COUNTER_RULE = "gold_counter_exhaustion_candle_rr1.2_risk0.8"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def normalize_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["signal_time", "entry_time", "jst_entry_time", "exit_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    if "entry_time" not in out.columns and "jst_entry_time" in out.columns:
        out["entry_time"] = out["jst_entry_time"]
    if "jst_entry_time" not in out.columns and "entry_time" in out.columns:
        out["jst_entry_time"] = out["entry_time"]
    return out


def read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    out = normalize_time_columns(df)

    if "side" not in out.columns:
        raise ValueError(f"Missing side column: {path}")
    if "r" not in out.columns:
        raise ValueError(f"Missing r column: {path}")

    out["side"] = out["side"].astype(str).str.upper().str.strip()
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    if "result" not in out.columns:
        out["result"] = np.where(out["r"] > 0, "win", np.where(out["r"] < 0, "loss", "breakeven"))
    out["result"] = out["result"].astype(str).str.lower().str.strip()

    if "signal_idx" in out.columns:
        out["signal_idx"] = pd.to_numeric(out["signal_idx"], errors="coerce")
    if "entry_idx" in out.columns:
        out["entry_idx"] = pd.to_numeric(out["entry_idx"], errors="coerce")

    out = out.dropna(subset=["r", "side"]).copy()
    if "entry_time" in out.columns:
        out = out.dropna(subset=["entry_time"]).copy()
    return out.reset_index(drop=True)


def prepare_abc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["signal_family"] = "gold_abc_v3"
    out["strategy_label"] = "GOLD_ABC_V3"
    if "combined_signal_source" in out.columns:
        out["rule_name"] = "abc_" + out["combined_signal_source"].astype(str)
    elif "source" in out.columns:
        out["rule_name"] = "abc_" + out["source"].astype(str)
    elif "rule_name" not in out.columns:
        out["rule_name"] = "abc_v3"
    out["priority_abc_first"] = 1
    out["priority_extra_first"] = 2
    out["priority_high_quality_first"] = 2
    return out


def prepare_extra(df: pd.DataFrame, *, extra_rules: list[str], counter_rule: str) -> pd.DataFrame:
    selected_parts: list[pd.DataFrame] = []

    extra = df[df["rule_name"].astype(str).isin(extra_rules)].copy()
    if not extra.empty:
        extra["signal_family"] = "gold_extra_candle_indicator"
        extra["strategy_label"] = np.select(
            [
                extra["rule_name"].eq("gold_trend_rsi_stoch_rebound_rr1.5_risk1.5"),
                extra["rule_name"].eq("gold_trend_bb_candle_reject_rr1.5_risk1.5"),
                extra["rule_name"].eq("gold_trend_bb_candle_reject_rr2.0_risk1.0"),
            ],
            ["GOLD_EXTRA_HIGH_RSI_STOCH", "GOLD_EXTRA_BB_BALANCE", "GOLD_EXTRA_BB_WIDTH"],
            default="GOLD_EXTRA_OTHER",
        )
        selected_parts.append(extra)

    counter_buy = df[df["rule_name"].astype(str).eq(counter_rule) & df["side"].eq("BUY")].copy()
    if not counter_buy.empty:
        counter_buy["signal_family"] = "gold_counter_buy_only"
        counter_buy["strategy_label"] = "GOLD_COUNTER_BUY_ONLY"
        selected_parts.append(counter_buy)

    if selected_parts:
        out = pd.concat(selected_parts, ignore_index=True, sort=False)
    else:
        out = pd.DataFrame(columns=df.columns)

    if not out.empty:
        out["priority_abc_first"] = 2
        out["priority_extra_first"] = 1
        # high-quality first: rsi/stoch -> bb balance -> counter buy -> bb width -> abc
        out["priority_high_quality_first"] = np.select(
            [
                out["strategy_label"].eq("GOLD_EXTRA_HIGH_RSI_STOCH"),
                out["strategy_label"].eq("GOLD_EXTRA_BB_BALANCE"),
                out["strategy_label"].eq("GOLD_COUNTER_BUY_ONLY"),
                out["strategy_label"].eq("GOLD_EXTRA_BB_WIDTH"),
            ],
            [1, 2, 3, 4],
            default=5,
        )
    return out.reset_index(drop=True)


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
    sort_cols = [col for col in ["entry_time", "entry_idx", "signal_time", "signal_idx"] if col in df.columns]
    ordered = df.sort_values(sort_cols, kind="mergesort").copy() if sort_cols else df.copy()
    r = pd.to_numeric(ordered["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = ordered[ordered["side"].eq("BUY")]
    sell = ordered[ordered["side"].eq("SELL")]

    trades_per_month = None
    if "entry_time" in ordered.columns and ordered["entry_time"].notna().any():
        months = max(1.0, (pd.Timestamp(ordered["entry_time"].max()) - pd.Timestamp(ordered["entry_time"].min())).days / 30.4375)
        trades_per_month = float(len(ordered) / months)

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
        "trades_per_month": trades_per_month,
    }


def signal_key_columns(df: pd.DataFrame, *, mode: str) -> list[str]:
    if mode == "idx" and {"signal_idx", "side"}.issubset(df.columns) and df["signal_idx"].notna().any():
        return ["signal_idx", "side"]
    if {"signal_time", "side"}.issubset(df.columns) and df["signal_time"].notna().any():
        return ["signal_time", "side"]
    if {"entry_time", "side"}.issubset(df.columns) and df["entry_time"].notna().any():
        return ["entry_time", "side"]
    raise ValueError("Cannot build overlap key. Need signal_idx/side, signal_time/side, or entry_time/side.")


def make_key_set(df: pd.DataFrame, key_cols: list[str]) -> set[tuple[object, ...]]:
    if df.empty:
        return set()
    return set(tuple(row[col] for col in key_cols) for _, row in df[key_cols].iterrows())


def dedupe_signals(df: pd.DataFrame, *, key_cols: list[str], priority_col: str, label: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["dedupe_variant"] = label
    out["_order"] = np.arange(len(out))
    sort_cols = key_cols + [priority_col, "_order"]
    out = out.sort_values(sort_cols, kind="mergesort")
    out = out.groupby(key_cols, as_index=False, dropna=False).head(1).copy()
    out = out.drop(columns=["_order"])
    final_sort = [col for col in ["entry_time", "entry_idx", "signal_time", "signal_idx"] if col in out.columns]
    if final_sort:
        out = out.sort_values(final_sort, kind="mergesort")
    return out.reset_index(drop=True)


def build_overlap_pairs(abc: pd.DataFrame, extra: pd.DataFrame, *, key_cols: list[str]) -> pd.DataFrame:
    if abc.empty or extra.empty:
        return pd.DataFrame()
    abc_cols = list(dict.fromkeys(key_cols + ["entry_time", "rule_name", "strategy_label", "r", "result", "exit_reason", "bars_held"]))
    extra_cols = list(dict.fromkeys(key_cols + ["entry_time", "rule_name", "strategy_label", "r", "result", "exit_reason", "bars_held"]))
    abc_subset = abc[[col for col in abc_cols if col in abc.columns]].copy()
    extra_subset = extra[[col for col in extra_cols if col in extra.columns]].copy()
    merged = pd.merge(abc_subset, extra_subset, on=key_cols, how="inner", suffixes=("_abc", "_extra"))
    if not merged.empty:
        merged["r_diff_extra_minus_abc"] = pd.to_numeric(merged["r_extra"], errors="coerce") - pd.to_numeric(merged["r_abc"], errors="coerce")
    return merged


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze overlap between GOLD ABC v3 and candidate extra candle/indicator signals.")
    parser.add_argument("--abc-trades-csv", type=Path, default=DEFAULT_ABC_TRADES_CSV)
    parser.add_argument("--edge-trades-csv", type=Path, default=DEFAULT_EDGE_TRADES_CSV)
    parser.add_argument("--extra-rules", default=",".join(DEFAULT_EXTRA_RULES))
    parser.add_argument("--counter-rule", default=DEFAULT_COUNTER_RULE)
    parser.add_argument("--overlap-key", choices=["time", "idx"], default="time")
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--out-overlap", type=Path, default=DEFAULT_OUT_OVERLAP)
    args = parser.parse_args()

    abc_path = resolve_path(args.abc_trades_csv)
    edge_path = resolve_path(args.edge_trades_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    out_overlap = resolve_path(args.out_overlap)

    extra_rules = [x.strip() for x in args.extra_rules.split(",") if x.strip()]

    abc_raw = read_trades(abc_path)
    edge_raw = read_trades(edge_path)
    abc = prepare_abc(abc_raw)
    extra = prepare_extra(edge_raw, extra_rules=extra_rules, counter_rule=args.counter_rule)

    key_cols = signal_key_columns(pd.concat([abc, extra], ignore_index=True, sort=False), mode=args.overlap_key)
    abc_keys = make_key_set(abc, key_cols)
    extra_keys = make_key_set(extra, key_cols)
    overlap_keys = abc_keys & extra_keys
    union_keys = abc_keys | extra_keys

    combined_raw = pd.concat([abc, extra], ignore_index=True, sort=False)
    abc_first = dedupe_signals(combined_raw, key_cols=key_cols, priority_col="priority_abc_first", label="abc_first")
    extra_first = dedupe_signals(combined_raw, key_cols=key_cols, priority_col="priority_extra_first", label="extra_first")
    high_quality_first = dedupe_signals(combined_raw, key_cols=key_cols, priority_col="priority_high_quality_first", label="high_quality_first")

    abc_unique = abc[~abc.apply(lambda row: tuple(row[col] for col in key_cols) in extra_keys, axis=1)].copy()
    extra_unique = extra[~extra.apply(lambda row: tuple(row[col] for col in key_cols) in abc_keys, axis=1)].copy()
    overlap_pairs = build_overlap_pairs(abc, extra, key_cols=key_cols)

    summary_rows: list[dict[str, object]] = []
    summary_rows.append(summarize(abc, group_name="single", group_value="ABC_V3", description="Existing GOLD ABC v3 trades."))
    summary_rows.append(summarize(extra, group_name="single", group_value="ALL_EXTRA_SELECTED", description="All selected extra rules including counter BUY only."))
    for label, group in extra.groupby("strategy_label", dropna=False):
        summary_rows.append(summarize(group.copy(), group_name="extra_rule", group_value=str(label), description="Selected extra signal rule."))
    summary_rows.append(summarize(abc_first, group_name="combined_deduped", group_value="ABC_FIRST", description="ABC + extra combined; duplicates keep ABC first."))
    summary_rows.append(summarize(extra_first, group_name="combined_deduped", group_value="EXTRA_FIRST", description="ABC + extra combined; duplicates keep extra first."))
    summary_rows.append(summarize(high_quality_first, group_name="combined_deduped", group_value="HIGH_QUALITY_FIRST", description="ABC + extra combined; duplicates prefer high-quality extra first."))
    summary_rows.append(summarize(abc_unique, group_name="unique_only", group_value="ABC_UNIQUE_ONLY", description="ABC trades not overlapping selected extra signals."))
    summary_rows.append(summarize(extra_unique, group_name="unique_only", group_value="EXTRA_UNIQUE_ONLY", description="Selected extra trades not overlapping ABC."))

    summary = pd.DataFrame(summary_rows)
    summary["abc_count"] = len(abc)
    summary["extra_count"] = len(extra)
    summary["overlap_count"] = len(overlap_keys)
    summary["union_count"] = len(union_keys)
    summary["overlap_rate_vs_abc"] = len(overlap_keys) / len(abc_keys) if abc_keys else None
    summary["overlap_rate_vs_extra"] = len(overlap_keys) / len(extra_keys) if extra_keys else None
    summary["overlap_key_cols"] = ",".join(key_cols)

    out_all = pd.concat(
        [
            abc.assign(output_set="single_abc"),
            extra.assign(output_set="single_extra"),
            abc_first.assign(output_set="combined_abc_first"),
            extra_first.assign(output_set="combined_extra_first"),
            high_quality_first.assign(output_set="combined_high_quality_first"),
        ],
        ignore_index=True,
        sort=False,
    )

    write_csv(out_summary, summary)
    write_csv(out_trades, out_all)
    write_csv(out_overlap, overlap_pairs)

    print("ABC trades CSV:", abc_path)
    print("Edge trades CSV:", edge_path)
    print("Extra rules:", extra_rules)
    print("Counter BUY-only rule:", args.counter_rule)
    print("Overlap key columns:", key_cols)
    print("ABC trades:", len(abc))
    print("Extra trades:", len(extra))
    print("Overlap count:", len(overlap_keys))
    print("Union count:", len(union_keys))
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
    print_table("GOLD ABC/EXTRA OVERLAP SUMMARY", summary[display_cols])

    if not overlap_pairs.empty and {"r_abc", "r_extra"}.issubset(overlap_pairs.columns):
        comparison = pd.DataFrame(
            [
                {
                    "overlap_pairs": len(overlap_pairs),
                    "abc_total_r_on_overlap": float(pd.to_numeric(overlap_pairs["r_abc"], errors="coerce").sum()),
                    "extra_total_r_on_overlap": float(pd.to_numeric(overlap_pairs["r_extra"], errors="coerce").sum()),
                    "extra_minus_abc_total_r": float(pd.to_numeric(overlap_pairs["r_diff_extra_minus_abc"], errors="coerce").sum()),
                    "extra_better_count": int((pd.to_numeric(overlap_pairs["r_diff_extra_minus_abc"], errors="coerce") > 0).sum()),
                    "abc_better_count": int((pd.to_numeric(overlap_pairs["r_diff_extra_minus_abc"], errors="coerce") < 0).sum()),
                    "same_r_count": int((pd.to_numeric(overlap_pairs["r_diff_extra_minus_abc"], errors="coerce") == 0).sum()),
                }
            ]
        )
        print_table("OVERLAP ABC VS EXTRA R COMPARISON", comparison)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
