from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_CONFIRMED = PROJECT_ROOT / "data" / "results" / "gold_current_rules_confirmed_trades.csv"
DEFAULT_OUT_MATCHES = PROJECT_ROOT / "data" / "results" / "gold_history_confirmed_fuzzy_matches.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_history_confirmed_fuzzy_summary.csv"

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
    if label_col is None or time_col is None or side_col is None:
        raise ValueError(f"Could not find required columns for {source}: label={label_col}, time={time_col}, side={side_col}")
    out = pd.DataFrame()
    out["source"] = source
    out["strategy_label"] = df[label_col].astype(str)
    out["time"] = pd.to_datetime(df[time_col], errors="coerce")
    out["side"] = df[side_col].astype(str).str.upper()
    out["r"] = pd.to_numeric(df[r_col], errors="coerce") if r_col else pd.NA
    out = out.dropna(subset=["time"])
    out = out[out["strategy_label"].isin(GOLD_LABELS)].copy()
    out = out.sort_values(["strategy_label", "side", "time"], kind="mergesort").reset_index(drop=True)
    out["row_id"] = range(len(out))
    return out


def match_for_tolerance(history: pd.DataFrame, confirmed: pd.DataFrame, *, tolerance_min: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    used_confirmed: set[int] = set()
    rows: list[dict[str, Any]] = []
    tolerance = pd.Timedelta(minutes=tolerance_min)

    for _, h in history.iterrows():
        cands = confirmed[
            (confirmed["strategy_label"] == h["strategy_label"])
            & (confirmed["side"] == h["side"])
            & (~confirmed["row_id"].isin(used_confirmed))
        ].copy()
        if cands.empty:
            rows.append({**h.to_dict(), "match_status": "history_only", "confirmed_row_id": "", "confirmed_time": pd.NaT, "confirmed_r": pd.NA, "time_diff_min": pd.NA})
            continue
        cands["abs_diff"] = (cands["time"] - h["time"]).abs()
        cands = cands[cands["abs_diff"] <= tolerance].sort_values("abs_diff", kind="mergesort")
        if cands.empty:
            rows.append({**h.to_dict(), "match_status": "history_only", "confirmed_row_id": "", "confirmed_time": pd.NaT, "confirmed_r": pd.NA, "time_diff_min": pd.NA})
            continue
        best = cands.iloc[0]
        used_confirmed.add(int(best["row_id"]))
        rows.append(
            {
                **h.to_dict(),
                "match_status": "matched",
                "confirmed_row_id": int(best["row_id"]),
                "confirmed_time": best["time"],
                "confirmed_r": best["r"],
                "time_diff_min": (best["time"] - h["time"]).total_seconds() / 60.0,
            }
        )

    for _, c in confirmed[~confirmed["row_id"].isin(used_confirmed)].iterrows():
        rows.append(
            {
                "source": "history",
                "strategy_label": c["strategy_label"],
                "time": pd.NaT,
                "side": c["side"],
                "r": pd.NA,
                "row_id": "",
                "match_status": "confirmed_only",
                "confirmed_row_id": int(c["row_id"]),
                "confirmed_time": c["time"],
                "confirmed_r": c["r"],
                "time_diff_min": pd.NA,
            }
        )

    detail = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for label, g in detail.groupby("strategy_label", dropna=False):
        for status, sg in g.groupby("match_status", dropna=False):
            summary_rows.append(
                {
                    "tolerance_min": tolerance_min,
                    "strategy_label": label,
                    "match_status": status,
                    "rows": int(len(sg)),
                    "history_r_sum": float(pd.to_numeric(sg["r"], errors="coerce").sum()),
                    "confirmed_r_sum": float(pd.to_numeric(sg["confirmed_r"], errors="coerce").sum()),
                    "avg_time_diff_min": float(pd.to_numeric(sg["time_diff_min"], errors="coerce").mean()) if status == "matched" else None,
                }
            )
    summary = pd.DataFrame(summary_rows)
    return detail, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Fuzzy compare GOLD history vs confirmed-live detector by label/side/time tolerance.")
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--confirmed-trades-csv", type=Path, default=DEFAULT_CONFIRMED)
    parser.add_argument("--tolerances-min", default="0,15,30,60,240", help="Comma-separated tolerances in minutes.")
    parser.add_argument("--out-matches", type=Path, default=DEFAULT_OUT_MATCHES)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    args = parser.parse_args()

    history = normalize(read_any_csv(args.history_csv), source="history")
    confirmed = normalize(read_any_csv(args.confirmed_trades_csv), source="confirmed")
    if not confirmed.empty:
        start = confirmed["time"].min()
        end = confirmed["time"].max()
        history = history[(history["time"] >= start) & (history["time"] <= end)].copy()

    all_details = []
    all_summaries = []
    for tol in [int(x.strip()) for x in args.tolerances_min.split(",") if x.strip()]:
        detail, summary = match_for_tolerance(history, confirmed, tolerance_min=tol)
        detail["tolerance_min"] = tol
        all_details.append(detail)
        all_summaries.append(summary)

    details = pd.concat(all_details, ignore_index=True) if all_details else pd.DataFrame()
    summaries = pd.concat(all_summaries, ignore_index=True) if all_summaries else pd.DataFrame()

    out_matches = resolve_path(args.out_matches)
    out_summary = resolve_path(args.out_summary)
    out_matches.parent.mkdir(parents=True, exist_ok=True)
    details.to_csv(out_matches, index=False, encoding="utf-8-sig")
    summaries.to_csv(out_summary, index=False, encoding="utf-8-sig")

    print("History rows in confirmed range:", len(history))
    print("Confirmed rows:", len(confirmed))
    print("Confirmed range:", confirmed["time"].min() if not confirmed.empty else None, "->", confirmed["time"].max() if not confirmed.empty else None)
    print("\n" + "=" * 140)
    print("GOLD HISTORY VS CONFIRMED FUZZY SUMMARY")
    print("=" * 140)
    print(summaries.to_string(index=False))
    print("\nWrote matches:", out_matches)
    print("Wrote summary:", out_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
