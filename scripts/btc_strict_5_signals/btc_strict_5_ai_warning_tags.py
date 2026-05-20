#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human-facing AI warning tags for BTC strict 5 notifications.

These tags are derived from completed BTC strict-5 backtest AI review and
subsequent deterministic diagnostics. They are warning/context only.
They must not be treated as an AI approval/rejection call at notification time.

Important:
- A_FILTER_CANDIDATE / official numeric filters are already applied before
  official notifications are generated.
- WATCH tags remain useful as human caution labels in Discord.
- This module does not call AI and does not read live data.
"""
from __future__ import annotations

from typing import Any

BTC_SELL_DONCH96 = "BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200_TP1900_SL400_H20H_CD0"
BTC_SELL_DONCH32 = "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0"
BTC_BUY_RSI40 = "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0"
BTC_SELL_DONCH64 = "BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06_TP2400_SL600_H6H_CD0"
BTC_BUY_CCI = "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0"

OFFICIAL_FILTERED_TAGS_BY_STRATEGY: dict[str, list[str]] = {
    BTC_BUY_CCI: ["against_h4_context"],
    BTC_BUY_RSI40: ["against_h4_context"],
}

WATCH_TAGS_BY_STRATEGY: dict[str, list[str]] = {
    BTC_SELL_DONCH96: [
        "against_h4_context",
        "high_volatility_chase",
        "m15_signal_candle_large",
        "btc_fast_reversal_after_break",
    ],
    BTC_SELL_DONCH32: [
        "btc_large_wick_reversal",
        "poor_pullback_structure",
        "range_edge_entry",
    ],
    BTC_BUY_RSI40: [
        "high_volatility_chase",
        "m15_signal_candle_large",
    ],
    BTC_SELL_DONCH64: [
        "poor_pullback_structure",
        "near_recent_low",
        "range_edge_entry",
    ],
    BTC_BUY_CCI: [
        "high_volatility_chase",
        "m15_signal_candle_large",
    ],
}

TAG_JA: dict[str, str] = {
    "against_h4_context": "H4環境に逆らう形",
    "high_volatility_chase": "高ボラ追いかけ",
    "m15_signal_candle_large": "M15シグナル足が大きすぎる",
    "btc_fast_reversal_after_break": "BTC特有のブレイク後急反転",
    "btc_large_wick_reversal": "大ヒゲ反転リスク",
    "poor_pullback_structure": "押し戻り構造が弱い",
    "range_edge_entry": "レンジ端エントリーリスク",
    "near_recent_low": "直近安値付近でのSELLリスク",
}


def unique_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag and tag not in seen:
            out.append(tag)
            seen.add(tag)
    return out


def risk_watch_tags(strategy_id: str) -> list[str]:
    return unique_tags(WATCH_TAGS_BY_STRATEGY.get(str(strategy_id), []))


def official_filtered_tags(strategy_id: str) -> list[str]:
    return unique_tags(OFFICIAL_FILTERED_TAGS_BY_STRATEGY.get(str(strategy_id), []))


def format_tags(tags: list[str]) -> str:
    if not tags:
        return "なし"
    return ", ".join(f"{tag}({TAG_JA.get(tag, '要確認')})" for tag in tags)


def build_ai_warning_section(strategy_id: str, *, filter_variant: str, risk_level: str = "WATCH") -> list[str]:
    watch_tags = risk_watch_tags(strategy_id)
    hard_filtered = official_filtered_tags(strategy_id)
    lines = [
        "AI評価:",
        f"過去AI評価タグ警告: {'⚠️ ' + risk_level if watch_tags else 'なし'}",
        f"警戒タグ: {format_tags(watch_tags)}",
        f"公式フィルター済みタグ: {format_tags(hard_filtered)}",
        f"filter_variant: {filter_variant}",
        "AI注記: 通知時点ではAIによる新規判定は行わない。これはバックテストAI評価で蓄積した注意タグの表示。",
    ]
    return lines


def warning_summary(strategy_id: str, *, filter_variant: str) -> dict[str, Any]:
    watch = risk_watch_tags(strategy_id)
    hard = official_filtered_tags(strategy_id)
    return {
        "strategy_id": strategy_id,
        "filter_variant": filter_variant,
        "risk_watch_tags": watch,
        "official_filtered_tags": hard,
        "has_warning": bool(watch),
        "note": "warning tags are historical AI-review hypotheses; official filtered tags are already applied before notification",
    }
