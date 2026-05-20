#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Diagnose BTC strict-5 AI hypothesis tags by deterministic exclusion tests.

This script does NOT call AI. It consumes the completed BTC strict-5 backtest AI
review outputs and asks a deterministic question:

    If we removed trades carrying an AI hypothesis tag, would PF / total R /
    drawdown / monthly stability improve for that strategy?

Important:
- This is a diagnostic tool only.
- It must not directly edit signal rules.
- AI tags are hypotheses. A tag becomes a candidate filter only if deterministic
  exclusion stats remain good enough after monthly/DD/nearby logic review.

Expected inputs from run_btc_strict_5_backtest_ai_review_pipeline.py:
- trade_outcome_ledger.csv
- trade_ai_review_ledger.jsonl
- trade_ai_tag_summary.csv

Outputs:
- btc_strict_5_ai_tag_exclusion_summary.csv
- btc_strict_5_ai_tag_exclusion_monthly.csv
- btc_strict_5_ai_tag_trade_flags.csv
- btc_strict_5_ai_tag_exclusion_selected_candidates.csv
- btc_strict_5_ai_tag_exclusion_diagnostics_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AI_REVIEW_DIR = Path("data/research_results/btc_strict_5_backtest_ai_review")
DEFAULT_OUT_DIR = Path("data/research_results/btc_strict_5_backtest_ai_review/ai_tag_exclusion_diagnostics")
SCHEMA_VERSION = "btc_strict_5_ai_tag_exclusion_diagnostics_v1"
TAG_KEYS = [
    ("possible_risk_tags", "risk"),
    ("possible_positive_tags", "positive"),
    ("execution_issue_tags", "execution"),
    ("system_issue_tags", "system"),
]
NON_INFORMATIVE_TAGS = {
    "",
    "-",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "unclear",
    "no_clear_positive_tag",
    "no_positive_tag",
    "no_risk_tag",
    "no_clear_risk_tag",
}


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def clean_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def canonical_tag_name(tag: Any) -> str:
    return clean_str(tag).strip().lower().replace(" ", "_").replace("-", "_")


def is_informative_tag(tag: Any) -> bool:
    return canonical_tag_name(tag) not in NON_INFORMATIVE_TAGS


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [canonical_tag_name(v) for v in value if is_informative_tag(v)]
    if isinstance(value, str):
        # JSON lists should already be lists, but tolerate comma/semicolon strings.
        if value.strip().startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return normalize_list(parsed)
            except Exception:
                pass
        parts = value.replace(";", ",").split(",")
        return [canonical_tag_name(v) for v in parts if is_informative_tag(v)]
    return [canonical_tag_name(value)] if is_informative_tag(value) else []


def profit_factor(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    if len(arr) == 0:
        return 0.0
    pos = float(arr[arr > 0].sum())
    neg_abs = float(-arr[arr < 0].sum())
    if neg_abs <= 1e-12:
        return math.inf if pos > 0 else 0.0
    return pos / neg_abs


def max_drawdown(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    if len(arr) == 0:
        return 0.0
    eq = np.r_[0.0, np.cumsum(arr)]
    dd = np.maximum.accumulate(eq) - eq
    return float(dd.max())


def max_losing_streak(values: pd.Series | np.ndarray | list[float]) -> int:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    best = cur = 0
    for value in arr:
        if value < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def perf(df: pd.DataFrame, *, r_col: str = "profit_r") -> dict[str, Any]:
    if df.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "avg_r": 0.0,
            "pf": 0.0,
            "max_dd_r": 0.0,
            "max_losing_streak": 0,
        }
    r = pd.to_numeric(df[r_col], errors="coerce").dropna()
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r < 0).sum()),
        "win_rate": float((r > 0).mean()) if len(r) else 0.0,
        "total_r": float(r.sum()) if len(r) else 0.0,
        "avg_r": float(r.mean()) if len(r) else 0.0,
        "pf": float(profit_factor(r)),
        "max_dd_r": float(max_drawdown(r)),
        "max_losing_streak": int(max_losing_streak(r)),
    }


def monthly_perf(df: pd.DataFrame, *, strategy_id: str, tag_name: str, variant: str) -> list[dict[str, Any]]:
    if df.empty:
        return []
    work = df.copy()
    time_col = "entry_time" if "entry_time" in work.columns else "signal_time"
    work["_month"] = pd.to_datetime(work[time_col], errors="coerce").dt.strftime("%Y-%m")
    rows: list[dict[str, Any]] = []
    for month, g in work.groupby("_month", dropna=False):
        row = perf(g)
        row.update({"strategy_id": strategy_id, "tag_name": tag_name, "variant": variant, "month": clean_str(month, "UNKNOWN")})
        rows.append(row)
    return rows


def review_trade_id(row: dict[str, Any]) -> str:
    for key in ["trade_id", "order_key", "payload_key"]:
        text = clean_str(row.get(key))
        if text:
            return text
    return ""


def build_trade_tag_table(ai_review_jsonl: Path) -> pd.DataFrame:
    review_rows = read_jsonl(ai_review_jsonl)
    out_rows: list[dict[str, Any]] = []
    for review in review_rows:
        tid = review_trade_id(review)
        strategy_id = clean_str(review.get("strategy_id"))
        direction = clean_str(review.get("direction")).upper()
        symbol = clean_str(review.get("symbol"), "BTC")
        outcome = clean_str(review.get("outcome")).upper()
        profit_r = clean_float(review.get("profit_r"))
        seen: set[tuple[str, str]] = set()
        for key, group in TAG_KEYS:
            for tag in normalize_list(review.get(key)):
                pair = (tag, group)
                if pair in seen:
                    continue
                seen.add(pair)
                out_rows.append({
                    "trade_id": tid,
                    "strategy_id": strategy_id,
                    "direction": direction,
                    "symbol": symbol,
                    "outcome": outcome,
                    "profit_r_review": profit_r,
                    "tag_name": tag,
                    "tag_group": group,
                    "review_key": key,
                })
    return pd.DataFrame(out_rows)


def load_candidate_tags(tag_summary_csv: Path, *, only_should_investigate: bool, min_tag_trades: int) -> pd.DataFrame:
    df = read_csv_auto(tag_summary_csv)
    if df.empty:
        return df
    df["tag_name"] = df["tag_name"].map(canonical_tag_name)
    if only_should_investigate and "should_investigate" in df.columns:
        df = df[df["should_investigate"].map(to_bool)].copy()
    if "trade_count" in df.columns and min_tag_trades > 0:
        df = df[pd.to_numeric(df["trade_count"], errors="coerce").fillna(0) >= min_tag_trades].copy()
    keep_cols = [c for c in [
        "symbol", "strategy_key", "strategy_id", "tag_name", "tag_group", "tag_status", "trade_count",
        "win_rate", "avg_r", "total_r", "profit_factor", "max_losing_streak", "should_investigate",
        "investigation_reason",
    ] if c in df.columns]
    return df[keep_cols].drop_duplicates(["strategy_id", "tag_name", "tag_group"]).reset_index(drop=True)


def prepare_outcomes(trade_outcome_csv: Path) -> pd.DataFrame:
    df = read_csv_auto(trade_outcome_csv)
    if df.empty:
        return df
    if "profit_r" not in df.columns:
        raise ValueError(f"{trade_outcome_csv} missing profit_r")
    if "trade_id" not in df.columns:
        raise ValueError(f"{trade_outcome_csv} missing trade_id")
    if "strategy_id" not in df.columns:
        raise ValueError(f"{trade_outcome_csv} missing strategy_id")
    df["trade_id"] = df["trade_id"].astype(str)
    df["strategy_id"] = df["strategy_id"].astype(str)
    df["profit_r"] = pd.to_numeric(df["profit_r"], errors="coerce")
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    elif "signal_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["signal_time"], errors="coerce")
    else:
        df["entry_time"] = pd.NaT
    return df


def join_trade_flags(outcomes: pd.DataFrame, tag_rows: pd.DataFrame) -> pd.DataFrame:
    if tag_rows.empty:
        out = outcomes.copy()
        out["ai_tags"] = ""
        out["ai_tag_groups"] = ""
        out["ai_tag_count"] = 0
        return out
    grouped = tag_rows.groupby("trade_id").agg(
        ai_tags=("tag_name", lambda s: "|".join(sorted(set(str(x) for x in s if clean_str(x))))),
        ai_tag_groups=("tag_group", lambda s: "|".join(sorted(set(str(x) for x in s if clean_str(x))))),
        ai_tag_count=("tag_name", lambda s: int(len(set(str(x) for x in s if clean_str(x))))),
    ).reset_index()
    out = outcomes.merge(grouped, on="trade_id", how="left")
    out["ai_tags"] = out["ai_tags"].fillna("")
    out["ai_tag_groups"] = out["ai_tag_groups"].fillna("")
    out["ai_tag_count"] = pd.to_numeric(out["ai_tag_count"], errors="coerce").fillna(0).astype(int)
    return out


def simulate_exclusions(
    outcomes: pd.DataFrame,
    tag_rows: pd.DataFrame,
    candidate_tags: pd.DataFrame,
    *,
    min_kept_trades: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []

    for _, cand in candidate_tags.iterrows():
        strategy_id = clean_str(cand.get("strategy_id"))
        tag_name = canonical_tag_name(cand.get("tag_name"))
        tag_group = clean_str(cand.get("tag_group"))
        if not strategy_id or not tag_name:
            continue
        base = outcomes[outcomes["strategy_id"].astype(str).eq(strategy_id)].copy()
        if base.empty:
            continue
        tagged_ids = set(tag_rows[
            tag_rows["strategy_id"].astype(str).eq(strategy_id)
            & tag_rows["tag_name"].astype(str).eq(tag_name)
            & (tag_rows["tag_group"].astype(str).eq(tag_group) if tag_group else True)
        ]["trade_id"].astype(str).tolist())
        if not tagged_ids:
            continue
        removed = base[base["trade_id"].astype(str).isin(tagged_ids)].copy()
        kept = base[~base["trade_id"].astype(str).isin(tagged_ids)].copy()
        base_perf = perf(base)
        removed_perf = perf(removed)
        kept_perf = perf(kept)
        row = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": utc_now_text(),
            "strategy_id": strategy_id,
            "tag_name": tag_name,
            "tag_group": tag_group,
            "tag_status": cand.get("tag_status", ""),
            "tag_should_investigate": to_bool(cand.get("should_investigate")),
            "tag_investigation_reason": cand.get("investigation_reason", ""),
            "baseline_trades": base_perf["trades"],
            "baseline_pf": base_perf["pf"],
            "baseline_total_r": base_perf["total_r"],
            "baseline_avg_r": base_perf["avg_r"],
            "baseline_win_rate": base_perf["win_rate"],
            "baseline_max_dd_r": base_perf["max_dd_r"],
            "baseline_max_losing_streak": base_perf["max_losing_streak"],
            "removed_trades": removed_perf["trades"],
            "removed_pf": removed_perf["pf"],
            "removed_total_r": removed_perf["total_r"],
            "removed_avg_r": removed_perf["avg_r"],
            "removed_win_rate": removed_perf["win_rate"],
            "removed_max_losing_streak": removed_perf["max_losing_streak"],
            "kept_trades": kept_perf["trades"],
            "kept_pf": kept_perf["pf"],
            "kept_total_r": kept_perf["total_r"],
            "kept_avg_r": kept_perf["avg_r"],
            "kept_win_rate": kept_perf["win_rate"],
            "kept_max_dd_r": kept_perf["max_dd_r"],
            "kept_max_losing_streak": kept_perf["max_losing_streak"],
            "kept_ratio": kept_perf["trades"] / base_perf["trades"] if base_perf["trades"] else 0.0,
            "pf_delta": kept_perf["pf"] - base_perf["pf"] if math.isfinite(kept_perf["pf"]) and math.isfinite(base_perf["pf"]) else np.nan,
            "total_r_delta": kept_perf["total_r"] - base_perf["total_r"],
            "avg_r_delta": kept_perf["avg_r"] - base_perf["avg_r"],
            "win_rate_delta": kept_perf["win_rate"] - base_perf["win_rate"],
            "max_dd_delta": kept_perf["max_dd_r"] - base_perf["max_dd_r"],
            "max_losing_streak_delta": kept_perf["max_losing_streak"] - base_perf["max_losing_streak"],
            "removed_trade_ids": "|".join(removed["trade_id"].astype(str).tolist()),
        }
        # Conservative candidate grading. Total R often drops after exclusion if the tag still has net positive R;
        # that is acceptable only for WATCH, not immediate filter.
        if kept_perf["trades"] < min_kept_trades:
            grade = "REJECT_TOO_FEW_KEPT"
        elif kept_perf["pf"] >= base_perf["pf"] and kept_perf["total_r"] >= base_perf["total_r"] and kept_perf["max_dd_r"] <= base_perf["max_dd_r"]:
            grade = "A_FILTER_CANDIDATE"
        elif kept_perf["pf"] >= base_perf["pf"] and kept_perf["max_dd_r"] <= base_perf["max_dd_r"]:
            grade = "B_WATCH_PF_DD_IMPROVES_TOTAL_R_DROPS"
        elif kept_perf["pf"] >= 2.0 and kept_perf["max_dd_r"] < base_perf["max_dd_r"]:
            grade = "C_WATCH_DD_IMPROVES"
        else:
            grade = "D_DO_NOT_FILTER"
        row["diagnostic_grade"] = grade
        row["filter_candidate"] = grade.startswith("A_")
        row["watch_candidate"] = grade.startswith("B_") or grade.startswith("C_")
        summary_rows.append(row)

        monthly_rows.extend(monthly_perf(base, strategy_id=strategy_id, tag_name=tag_name, variant="baseline"))
        monthly_rows.extend(monthly_perf(removed, strategy_id=strategy_id, tag_name=tag_name, variant="removed_tagged"))
        monthly_rows.extend(monthly_perf(kept, strategy_id=strategy_id, tag_name=tag_name, variant="kept_after_exclusion"))
        if row["filter_candidate"] or row["watch_candidate"]:
            selected_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    monthly = pd.DataFrame(monthly_rows)
    selected = pd.DataFrame(selected_rows)
    if not summary.empty:
        summary = summary.sort_values(
            ["filter_candidate", "watch_candidate", "pf_delta", "kept_pf", "removed_total_r"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    if not selected.empty:
        selected = selected.sort_values(
            ["filter_candidate", "diagnostic_grade", "pf_delta", "kept_pf"],
            ascending=[False, True, False, False],
        ).reset_index(drop=True)
    return summary, monthly, selected


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC strict 5 AI tag exclusion diagnostics.")
    p.add_argument("--ai-review-dir", type=Path, default=DEFAULT_AI_REVIEW_DIR)
    p.add_argument("--trade-outcome-csv", type=Path, default=Path(""))
    p.add_argument("--ai-review-jsonl", type=Path, default=Path(""))
    p.add_argument("--tag-summary-csv", type=Path, default=Path(""))
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--only-should-investigate", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--min-tag-trades", type=int, default=5)
    p.add_argument("--min-kept-trades", type=int, default=10)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ai_dir = resolve_repo_path(args.ai_review_dir)
    trade_outcome_csv = resolve_repo_path(args.trade_outcome_csv) if clean_str(args.trade_outcome_csv) else ai_dir / "trade_outcome_ledger.csv"
    ai_review_jsonl = resolve_repo_path(args.ai_review_jsonl) if clean_str(args.ai_review_jsonl) else ai_dir / "trade_ai_review_ledger.jsonl"
    tag_summary_csv = resolve_repo_path(args.tag_summary_csv) if clean_str(args.tag_summary_csv) else ai_dir / "trade_ai_tag_summary.csv"
    out_dir = resolve_repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for path in [trade_outcome_csv, ai_review_jsonl, tag_summary_csv]:
        if not path.exists():
            raise SystemExit(f"required input not found: {path}")

    outcomes = prepare_outcomes(trade_outcome_csv)
    trade_tag_rows = build_trade_tag_table(ai_review_jsonl)
    candidate_tags = load_candidate_tags(
        tag_summary_csv,
        only_should_investigate=bool(args.only_should_investigate),
        min_tag_trades=int(args.min_tag_trades),
    )
    trade_flags = join_trade_flags(outcomes, trade_tag_rows)
    summary, monthly, selected = simulate_exclusions(
        outcomes,
        trade_tag_rows,
        candidate_tags,
        min_kept_trades=int(args.min_kept_trades),
    )

    paths = {
        "trade_flags_csv": out_dir / "btc_strict_5_ai_tag_trade_flags.csv",
        "exclusion_summary_csv": out_dir / "btc_strict_5_ai_tag_exclusion_summary.csv",
        "exclusion_monthly_csv": out_dir / "btc_strict_5_ai_tag_exclusion_monthly.csv",
        "selected_candidates_csv": out_dir / "btc_strict_5_ai_tag_exclusion_selected_candidates.csv",
        "diagnostics_json": out_dir / "btc_strict_5_ai_tag_exclusion_diagnostics_summary.json",
    }
    write_csv(trade_flags, paths["trade_flags_csv"])
    write_csv(summary, paths["exclusion_summary_csv"])
    write_csv(monthly, paths["exclusion_monthly_csv"])
    write_csv(selected, paths["selected_candidates_csv"])

    grade_counts = summary["diagnostic_grade"].value_counts().to_dict() if not summary.empty else {}
    diag = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "inputs": {
            "trade_outcome_csv": str(trade_outcome_csv),
            "ai_review_jsonl": str(ai_review_jsonl),
            "tag_summary_csv": str(tag_summary_csv),
        },
        "outputs": {k: str(v) for k, v in paths.items()},
        "settings": {
            "only_should_investigate": bool(args.only_should_investigate),
            "min_tag_trades": int(args.min_tag_trades),
            "min_kept_trades": int(args.min_kept_trades),
        },
        "rows": {
            "trade_outcomes": int(len(outcomes)),
            "trade_tag_rows": int(len(trade_tag_rows)),
            "candidate_tags": int(len(candidate_tags)),
            "exclusion_summary": int(len(summary)),
            "monthly_rows": int(len(monthly)),
            "selected_candidates": int(len(selected)),
        },
        "grade_counts": grade_counts,
        "safety": {
            "ai_called": False,
            "mt5_calls": False,
            "order_send": False,
            "discord_send": False,
            "runtime_trading_ledger_mutation": False,
            "diagnostic_only": True,
            "ai_tags_are_hypotheses_only": True,
        },
    }
    write_json(paths["diagnostics_json"], diag)
    print(json.dumps(diag, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
