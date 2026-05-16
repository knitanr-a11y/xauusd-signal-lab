#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI history warning helper for live Discord notifications.

This module is intentionally conservative:
- It does not block orders.
- It does not change lot size.
- It adds trader-facing warning text only.
- Missing files/columns result in NO_DATA style columns, not exceptions during
  live notification formatting.

Primary input:
- trade_ai_tag_summary.csv from summarize_trade_ai_review_ledger.py
- current notification rows, e.g. notification_ledger_to_send.csv

The warning is hypothesis-based. SUSPECT means investigation candidate, not an
approved strategy filter.
"""
from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

WARNING_STATUS_NONE = "NONE"
WARNING_STATUS_NO_DATA = "NO_DATA"
WARNING_STATUS_WARN = "WARN"

SEVERITY_ORDER = {
    "": 0,
    "NONE": 0,
    "INFO": 1,
    "WATCH": 2,
    "SUSPECT": 3,
}

RISK_TAG_JP = {
    "ema_distance_too_large": "EMA乖離が大きい",
    "entry_after_extended_move": "伸びた後のエントリー",
    "m15_signal_candle_large": "M15足が大きい",
    "near_recent_high": "直近高値付近",
    "near_recent_low": "直近安値付近",
    "range_edge_entry": "レンジ端付近",
    "high_volatility_chase": "高ボラ追いかけ",
    "poor_pullback_structure": "押し戻り構造が弱い",
    "against_h1_context": "H1文脈に逆らう可能性",
    "against_h4_context": "H4文脈に逆らう可能性",
    "macd_late_signal": "MACDが遅れ気味",
}

WATCH_TAGS = {
    "ema_distance_too_large",
    "entry_after_extended_move",
    "m15_signal_candle_large",
    "near_recent_high",
    "range_edge_entry",
    "high_volatility_chase",
    "poor_pullback_structure",
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


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def clean_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    s = str(x).strip()
    return s if s else default


def clean_float(x: Any, default: float | None = None) -> float | None:
    if x is None or x == "":
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        v = float(x)
    except Exception:
        return default
    if not math.isfinite(v):
        return default
    return v


def canonical_tag(tag: Any) -> str:
    return clean_str(tag).lower().replace(" ", "_").replace("-", "_")


def normalize_symbol(x: Any) -> str:
    text = clean_str(x).upper()
    if text.startswith("XAUUSD"):
        return "GOLD"
    if text.startswith("GOLD"):
        return "GOLD"
    if text.startswith("BTC"):
        return "BTC"
    return text


def infer_from_pipe_key(*values: Any) -> dict[str, str]:
    for value in values:
        text = clean_str(value)
        if not text or "|" not in text:
            continue
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 4:
            continue
        return {
            "symbol": normalize_symbol(parts[0]),
            "strategy_id": parts[1],
            "strategy_key": parts[1],
            "candidate_rank": parts[2],
            "direction": parts[3].upper(),
        }
    return {}


def row_value(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            value = clean_str(row.get(name))
            if value:
                return value
    return default


def infer_row_context(row: pd.Series) -> dict[str, str]:
    inferred = infer_from_pipe_key(
        row_value(row, ["order_key"]),
        row_value(row, ["payload_key"]),
        row_value(row, ["signal_key"]),
    )
    symbol = normalize_symbol(row_value(row, ["symbol", "broker_symbol"], inferred.get("symbol", "")))
    strategy_id = row_value(
        row,
        ["strategy_id", "strategy_key", "pair_name", "router_strategy_id", "router_strategy_slot"],
        inferred.get("strategy_id", ""),
    )
    strategy_key = row_value(row, ["strategy_key", "pair_name", "router_strategy_slot"], strategy_id)
    direction = row_value(row, ["direction", "order_type"], inferred.get("direction", "")).upper()
    candidate_rank = row_value(row, ["candidate_rank"], inferred.get("candidate_rank", ""))
    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_key": strategy_key,
        "direction": direction,
        "candidate_rank": candidate_rank,
    }


def prepare_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df.copy()
    df = summary_df.copy()
    for col in ["symbol", "strategy_key", "strategy_id", "tag_name", "tag_group", "tag_status"]:
        if col not in df.columns:
            df[col] = ""
    df["symbol_norm"] = df["symbol"].map(normalize_symbol)
    df["tag_name_norm"] = df["tag_name"].map(canonical_tag)
    df["tag_status_norm"] = df["tag_status"].map(lambda x: clean_str(x).upper())
    for col in ["trade_count", "win_count", "loss_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0
    for col in ["win_rate", "avg_r", "total_r", "profit_factor", "overall_win_rate_diff", "overall_avg_r_diff"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA
    if "should_investigate" not in df.columns:
        df["should_investigate"] = False
    df["should_investigate_bool"] = df["should_investigate"].map(lambda x: clean_str(x).lower() in {"true", "1", "yes"})
    return df


def matching_summary_rows(summary: pd.DataFrame, ctx: dict[str, str]) -> pd.DataFrame:
    if summary.empty:
        return summary.copy()
    symbol = normalize_symbol(ctx.get("symbol"))
    strategy_values = {clean_str(ctx.get("strategy_id")), clean_str(ctx.get("strategy_key"))}
    strategy_values.discard("")
    mask = pd.Series(True, index=summary.index)
    if symbol:
        mask &= summary["symbol_norm"].astype(str).str.upper().eq(symbol)
    if strategy_values:
        mask &= summary["strategy_id"].astype(str).isin(strategy_values) | summary["strategy_key"].astype(str).isin(strategy_values)
    return summary[mask].copy()


def row_has_feature_columns(row: pd.Series) -> bool:
    names = [
        "entry_position_in_m15_range_100_pct",
        "m15_signal_candle_range_atr_ratio",
        "m15_ema20_distance_atr",
        "m15_ema50_distance_atr",
        "m15_ema200_distance_atr",
    ]
    return any(name in row.index and clean_str(row.get(name)) for name in names)


def feature_pattern_warning(row: pd.Series, ctx: dict[str, str]) -> list[str]:
    """Detect the current candidate's own high-risk shape when feature columns exist."""
    direction = clean_str(ctx.get("direction")).upper()
    pos_pct = clean_float(row.get("entry_position_in_m15_range_100_pct"))
    candle_atr = clean_float(row.get("m15_signal_candle_range_atr_ratio"))
    ema_values = [
        clean_float(row.get("m15_ema20_distance_atr")),
        clean_float(row.get("m15_ema50_distance_atr")),
        clean_float(row.get("m15_ema200_distance_atr")),
    ]
    ema_abs_max = max([abs(v) for v in ema_values if v is not None] + [0.0])
    out: list[str] = []
    if direction == "BUY" and pos_pct is not None and pos_pct >= 80 and candle_atr is not None and candle_atr >= 1.5 and ema_abs_max >= 3.0:
        out.append(
            f"H4_M15 BUYでレンジ上側({pos_pct:.1f}%) + M15大足({candle_atr:.2f}ATR) + EMA乖離({ema_abs_max:.1f}ATR)。過去の負け形に近い可能性。"
        )
    elif direction == "BUY" and pos_pct is not None and pos_pct >= 80:
        out.append(f"BUYがM15直近100本レンジ上側({pos_pct:.1f}%)。上を追いかけていないか確認。")
    elif direction == "BUY" and candle_atr is not None and candle_atr >= 1.5:
        out.append(f"BUYでM15足が大きめ({candle_atr:.2f}ATR)。伸びた後の追いかけに注意。")
    return out


def severity_from_rows(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "NONE"
    max_sev = "INFO"
    for _, row in rows.iterrows():
        status = clean_str(row.get("tag_status_norm")).upper()
        investigate = bool(row.get("should_investigate_bool", False))
        if investigate or status == "SUSPECT":
            max_sev = "SUSPECT"
        elif status == "WATCH" and SEVERITY_ORDER.get(max_sev, 0) < SEVERITY_ORDER["WATCH"]:
            max_sev = "WATCH"
        elif status == "NEW" and SEVERITY_ORDER.get(max_sev, 0) < SEVERITY_ORDER["INFO"]:
            max_sev = "INFO"
    return max_sev


def format_tag_line(row: pd.Series) -> str:
    tag = canonical_tag(row.get("tag_name"))
    tag_jp = RISK_TAG_JP.get(tag, tag)
    status = clean_str(row.get("tag_status_norm"), clean_str(row.get("tag_status"))).upper()
    count = int(row.get("trade_count") or 0)
    wins = int(row.get("win_count") or 0)
    losses = int(row.get("loss_count") or 0)
    pf = clean_float(row.get("profit_factor"))
    avg_r = clean_float(row.get("avg_r"))
    bits = [f"{tag_jp}({status})", f"過去{count}件 {wins}勝{losses}敗"]
    if pf is not None:
        bits.append(f"PF {pf:.2f}")
    if avg_r is not None:
        bits.append(f"平均R {avg_r:+.2f}")
    return " / ".join(bits)


def select_relevant_summary_rows(matched: pd.DataFrame, ctx: dict[str, str], *, max_tags: int = 4) -> pd.DataFrame:
    if matched.empty:
        return matched.copy()
    df = matched.copy()
    # Trader-facing warning: focus on risk/execution tags. Positive tags are not
    # shown here because this text is a caution block, not an approval block.
    if "tag_group" in df.columns:
        df = df[df["tag_group"].astype(str).isin(["risk", "execution", "system"])].copy()
    if df.empty:
        return df
    # Show SUSPECT first, then near-sample-lossy WATCH/NEW tags that are useful
    # for manual inspection.
    df["_sev_score"] = df.apply(
        lambda r: 3 if bool(r.get("should_investigate_bool", False)) or clean_str(r.get("tag_status_norm")).upper() == "SUSPECT"
        else 2 if clean_str(r.get("tag_status_norm")).upper() == "WATCH"
        else 1,
        axis=1,
    )
    df["_watch_tag_bonus"] = df["tag_name_norm"].map(lambda t: 1 if t in WATCH_TAGS else 0)
    df["_loss_bias"] = pd.to_numeric(df.get("loss_count", 0), errors="coerce").fillna(0) - pd.to_numeric(df.get("win_count", 0), errors="coerce").fillna(0)
    df = df.sort_values(["_sev_score", "_watch_tag_bonus", "trade_count", "_loss_bias"], ascending=[False, False, False, False])
    return df.head(max_tags).drop(columns=["_sev_score", "_watch_tag_bonus", "_loss_bias"], errors="ignore")


def build_warning_for_row(row: pd.Series, summary: pd.DataFrame, *, max_tags: int = 4) -> dict[str, Any]:
    ctx = infer_row_context(row)
    matched = matching_summary_rows(summary, ctx)
    relevant = select_relevant_summary_rows(matched, ctx, max_tags=max_tags)
    pattern_lines = feature_pattern_warning(row, ctx)
    tag_lines = [format_tag_line(r) for _, r in relevant.iterrows()]

    severity = severity_from_rows(relevant)
    if pattern_lines and SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER["WATCH"]:
        severity = "WATCH"
    if not pattern_lines and not tag_lines:
        if summary.empty:
            return {
                "ai_history_warning_status": WARNING_STATUS_NO_DATA,
                "ai_history_warning_severity": "NONE",
                "ai_history_warning_text": "",
                "ai_history_warning_tags": "",
                "ai_history_warning_reason": "tag summary missing or empty",
            }
        return {
            "ai_history_warning_status": WARNING_STATUS_NONE,
            "ai_history_warning_severity": "NONE",
            "ai_history_warning_text": "",
            "ai_history_warning_tags": "",
            "ai_history_warning_reason": "no matching strategy tag warnings",
        }

    direction = clean_str(ctx.get("direction")).upper()
    strategy = clean_str(ctx.get("strategy_id"), clean_str(ctx.get("strategy_key"), "UNKNOWN_STRATEGY"))
    header = f"AI履歴警告: {severity}"
    if direction:
        header += f" / {direction}"
    if strategy:
        header += f" / {strategy}"
    lines = [header]
    for text in pattern_lines:
        lines.append(f"・{text}")
    for text in tag_lines:
        lines.append(f"・履歴タグ: {text}")
    lines.append("・自動停止ではなく目視確認用。1件だけでルール変更しない。")

    return {
        "ai_history_warning_status": WARNING_STATUS_WARN,
        "ai_history_warning_severity": severity,
        "ai_history_warning_text": " || ".join(lines),
        "ai_history_warning_tags": ";".join(canonical_tag(r.get("tag_name")) for _, r in relevant.iterrows()),
        "ai_history_warning_reason": "matched historical tag summary and/or current feature pattern",
    }


def apply_ai_history_warnings(
    df: pd.DataFrame,
    tag_summary: pd.DataFrame | None,
    *,
    max_tags: int = 4,
) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        for col in [
            "ai_history_warning_status",
            "ai_history_warning_severity",
            "ai_history_warning_text",
            "ai_history_warning_tags",
            "ai_history_warning_reason",
        ]:
            out[col] = ""
        return out
    summary = prepare_summary(tag_summary if tag_summary is not None else pd.DataFrame())
    rows: list[dict[str, Any]] = []
    for _, row in out.iterrows():
        rows.append(build_warning_for_row(row, summary, max_tags=max_tags))
    warn_df = pd.DataFrame(rows)
    for col in warn_df.columns:
        out[col] = warn_df[col].values
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Append AI history warning columns to notification rows.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--tag-summary-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--max-tags", type=int, default=4)
    args = p.parse_args()

    source = read_csv(args.input_csv)
    try:
        summary = read_csv(args.tag_summary_csv)
    except Exception:
        summary = pd.DataFrame()
    out = apply_ai_history_warnings(source, summary, max_tags=int(args.max_tags))
    write_csv(out, args.output_csv)
    print("trade_ai_history_warning")
    print(f"input_csv: {args.input_csv}")
    print(f"tag_summary_csv: {args.tag_summary_csv}")
    print(f"rows_in: {len(source)}")
    print(f"rows_out: {len(out)}")
    if "ai_history_warning_status" in out.columns:
        print(f"warning_counts: {out['ai_history_warning_status'].value_counts(dropna=False).to_dict()}")
    print(f"output_csv: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
