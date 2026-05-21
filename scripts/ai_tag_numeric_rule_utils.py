#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for applying AI-tag numeric rules to a current signal row.

These utilities do not call AI. They only evaluate deterministic numeric rules
that were generated from historical AI-review tags and pre-entry features.

Important wording:
- A rule HIT means "the current signal numerically resembles a past AI-review tag".
- It is not a direct loss-probability prediction.
- Notification text therefore separates good-sign tags, stronger caution tags,
  and reference-only tags.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "ai_tag_numeric_rule_utils_v4_win_loss_balance_display"

HIGH_PRIORITY_TAGS = {
    "poor_pullback_structure",
    "m15_signal_candle_large",
    "macd_late_signal",
    "high_volatility_chase",
    "ema_distance_too_large",
}

MEDIUM_PRIORITY_TAGS = {
    "near_recent_low",
    "near_recent_high",
    "range_edge_entry",
    "against_h1_context",
    "against_h4_context",
    "entry_after_extended_move",
}

LOW_PRIORITY_TAGS = {
    "tp_sl_distance_invalid",
}

TAG_JA = {
    "poor_pullback_structure": "押し戻りの形が弱い",
    "m15_signal_candle_large": "シグナル足が大きすぎる",
    "macd_late_signal": "MACDが遅れ気味",
    "high_volatility_chase": "高ボラ追いかけ気味",
    "ema_distance_too_large": "EMAから離れすぎ",
    "near_recent_low": "直近安値に近い",
    "near_recent_high": "直近高値に近い",
    "range_edge_entry": "レンジ端でのエントリー",
    "against_h1_context": "H1方向と逆らい気味",
    "against_h4_context": "H4方向と逆らい気味",
    "entry_after_extended_move": "伸びた後のエントリー",
    "tp_sl_distance_invalid": "TP/SL距離に注意",
    "gold_fast_mean_reversion": "GOLD短期反発の形",
    "strong_reversal_candle": "反転足が強い",
    "trend_context_aligned": "上位足と合いやすい",
    "clean_pullback_structure": "押し戻りの形が良い",
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


def canonical_tag(value: Any) -> str:
    return clean_str(value).lower().replace(" ", "_").replace("-", "_")


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def fmt_float(value: Any, digits: int = 2, default: str = "N/A") -> str:
    x = safe_float(value)
    return default if x is None else f"{x:.{digits}f}"


def load_rules_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "cycle_ok": False,
            "reason": "RULES_JSON_NOT_FOUND",
            "rules_path": str(p),
            "rules": [],
        }
    with open(windows_long_path(p), "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"rules JSON must be an object: {p}")
    if "rules" not in obj or not isinstance(obj.get("rules"), list):
        raise ValueError(f"rules JSON missing list field 'rules': {p}")
    obj["rules_path"] = str(p)
    return obj


def get_raw(row: dict[str, Any] | pd.Series, name: str) -> Any:
    if isinstance(row, pd.Series):
        return row.get(name) if name in row.index else None
    return row.get(name)


def get_num(row: dict[str, Any] | pd.Series, *names: str) -> float | None:
    for name in names:
        val = safe_float(get_raw(row, name))
        if val is not None:
            return val
    return None


def div0(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or abs(den) <= 1e-12:
        return None
    return num / den


def derived_feature_value(row: dict[str, Any] | pd.Series, feature: str) -> float | None:
    f = clean_str(feature)
    close = get_num(row, "close", "signal_close_price", "entry_price")
    open_ = get_num(row, "open")
    high = get_num(row, "high")
    low = get_num(row, "low")
    rng = get_num(row, "range")
    if rng is None and high is not None and low is not None:
        rng = high - low
    atr = get_num(row, "atr14", "trigger_atr14")

    if f == "entry_position_in_m15_range_100_pct":
        val = get_num(row, "entry_position_in_m15_range_100_pct", "entry_position_pct", "trigger_entry_position_pct")
        if val is not None:
            return val
        cp = get_num(row, "m15_signal_candle_close_pos", "close_pos", "trigger_close_pos")
        if cp is not None:
            return cp * 100.0 if -2.0 <= cp <= 2.0 else cp
        if close is not None and low is not None and rng is not None and abs(rng) > 1e-12:
            return 100.0 * (close - low) / rng

    if f == "m15_signal_candle_body_ratio":
        val = get_num(row, "m15_signal_candle_body_ratio", "body_ratio", "trigger_body_ratio")
        if val is not None:
            return val
        if close is not None and open_ is not None and rng is not None and abs(rng) > 1e-12:
            return abs(close - open_) / rng

    if f == "m15_signal_candle_close_pos":
        val = get_num(row, "m15_signal_candle_close_pos", "close_pos", "trigger_close_pos")
        if val is not None:
            return val
        if close is not None and low is not None and rng is not None and abs(rng) > 1e-12:
            return (close - low) / rng

    if f == "m15_signal_candle_range_atr_ratio":
        val = get_num(row, "m15_signal_candle_range_atr_ratio", "range_atr", "trigger_range_atr", "trigger_range_atr14")
        if val is not None:
            return val
        return div0(rng, atr)

    if f == "m15_ema20_distance_atr":
        e = get_num(row, "ema20")
        return get_num(row, "m15_ema20_distance_atr", "ema20_distance_atr", "trigger_ema20_distance_atr") or div0((close - e) if close is not None and e is not None else None, atr)
    if f == "m15_ema50_distance_atr":
        e = get_num(row, "ema50")
        return get_num(row, "m15_ema50_distance_atr", "ema50_distance_atr", "trigger_ema50_distance_atr") or div0((close - e) if close is not None and e is not None else None, atr)
    if f == "m15_ema200_distance_atr":
        e = get_num(row, "ema200")
        return get_num(row, "m15_ema200_distance_atr", "ema200_distance_atr", "trigger_ema200_distance_atr") or div0((close - e) if close is not None and e is not None else None, atr)

    for tf in ["h1", "h4", "d1"]:
        for ema in ["ema20", "ema50", "ema200"]:
            target = f"{tf}_close_vs_{ema}_atr"
            if f == target:
                direct = get_num(row, target)
                if direct is not None:
                    return direct
                c = get_num(row, f"{tf}_close")
                e = get_num(row, f"{tf}_{ema}")
                a = get_num(row, f"{tf}_atr14")
                return div0((c - e) if c is not None and e is not None else None, a)

    if f in {"m15_recent_large_candle_count_20", "m15_recent_breakout_high_count_20", "m15_recent_breakout_low_count_20"}:
        return None
    return None


def row_value(row: dict[str, Any] | pd.Series, feature: str, aliases: list[str] | None = None) -> float | None:
    names = [feature]
    if aliases:
        names.extend(str(x) for x in aliases if str(x))
    for name in names:
        if isinstance(row, pd.Series):
            if name in row.index:
                val = safe_float(row.get(name))
                if val is not None:
                    return val
        else:
            if name in row:
                val = safe_float(row.get(name))
                if val is not None:
                    return val
    return derived_feature_value(row, feature)


def op_match(value: float | None, op: str, threshold: float) -> bool:
    if value is None:
        return False
    if op == "<=":
        return value <= threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == ">":
        return value > threshold
    raise ValueError(f"unsupported op: {op}")


def condition_matches(row: dict[str, Any] | pd.Series, cond: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    feature = clean_str(cond.get("feature"))
    op = clean_str(cond.get("op"))
    threshold = safe_float(cond.get("threshold"))
    aliases = cond.get("aliases") if isinstance(cond.get("aliases"), list) else []
    if not feature or not op or threshold is None:
        return False, {"feature": feature, "op": op, "threshold": threshold, "value": None, "ok": False, "reason": "INVALID_CONDITION"}
    value = row_value(row, feature, aliases)
    if value is None:
        return False, {"feature": feature, "op": op, "threshold": threshold, "value": None, "ok": False, "reason": "MISSING_FEATURE_VALUE", "aliases": aliases}
    ok = op_match(value, op, threshold)
    return ok, {"feature": feature, "op": op, "threshold": threshold, "value": value, "ok": ok, "reason": "OK" if ok else "NO_MATCH", "aliases": aliases}


def rule_matches(row: dict[str, Any] | pd.Series, rule: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    conditions = rule.get("conditions", [])
    if not isinstance(conditions, list) or not conditions:
        return False, []
    results: list[dict[str, Any]] = []
    for cond in conditions:
        if not isinstance(cond, dict):
            return False, results
        ok, detail = condition_matches(row, cond)
        results.append(detail)
        if not ok:
            return False, results
    return True, results


def rule_evaluable(row: dict[str, Any] | pd.Series, rule: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    conditions = rule.get("conditions", [])
    if not isinstance(conditions, list) or not conditions:
        return False, []
    details: list[dict[str, Any]] = []
    for cond in conditions:
        if not isinstance(cond, dict):
            return False, details
        _ok, detail = condition_matches(row, cond)
        details.append(detail)
        if detail.get("reason") in {"INVALID_CONDITION", "MISSING_FEATURE_VALUE"}:
            return False, details
    return True, details


def normalize_display_level(value: Any) -> str:
    text = clean_str(value)
    mapping = {
        "強め注意": "STRONG_CAUTION",
        "注意": "CAUTION",
        "参考注意": "REFERENCE_CAUTION",
        "参考": "REFERENCE_ONLY",
        "好材料": "POSITIVE_SUPPORT",
        "好材料候補": "POSITIVE_WATCH",
        "STRONG_CAUTION": "STRONG_CAUTION",
        "CAUTION": "CAUTION",
        "REFERENCE_CAUTION": "REFERENCE_CAUTION",
        "REFERENCE_ONLY": "REFERENCE_ONLY",
        "POSITIVE_SUPPORT": "POSITIVE_SUPPORT",
        "POSITIVE_WATCH": "POSITIVE_WATCH",
    }
    return mapping.get(text, "")


def derive_warning_level(rule: dict[str, Any]) -> str:
    explicit = normalize_display_level(rule.get("warning_level") or rule.get("display_warning_level") or rule.get("display_level_suggestion"))
    if explicit:
        return explicit
    tag_role = clean_str(rule.get("tag_role"))
    tag_group = clean_str(rule.get("tag_group"))
    tag = canonical_tag(rule.get("tag_name"))
    tag_avg_r = safe_float(rule.get("tag_avg_r"))
    tag_win_rate = safe_float(rule.get("tag_win_rate"))
    if tag_role == "positive" or tag_group == "positive":
        if tag_avg_r is not None and tag_avg_r > 0 and (tag_win_rate is None or tag_win_rate >= 0.45):
            return "POSITIVE_SUPPORT"
        return "POSITIVE_WATCH"
    verdict = clean_str(rule.get("verdict"))
    if verdict == "not_loss_specific_also_on_wins":
        return "REFERENCE_CAUTION"
    if verdict == "loss_heavy_warning":
        return "STRONG_CAUTION"
    if verdict == "moderate_loss_warning":
        return "CAUTION"
    if verdict in {"mixed_reference_only", "sample_too_small"}:
        return "REFERENCE_ONLY" if verdict == "sample_too_small" else "REFERENCE_CAUTION"

    removed_avg_r = safe_float(rule.get("removed_avg_r"))
    baseline_pf = safe_float(rule.get("baseline_pf"))
    kept_pf = safe_float(rule.get("kept_pf"))
    precision = safe_float(rule.get("tag_precision"))
    pf_improved = baseline_pf is not None and kept_pf is not None and kept_pf > baseline_pf
    removed_negative = removed_avg_r is not None and removed_avg_r < 0
    precision_high = precision is not None and precision >= 0.65
    if tag in HIGH_PRIORITY_TAGS and (removed_negative or pf_improved or precision_high):
        return "STRONG_CAUTION"
    if tag in HIGH_PRIORITY_TAGS:
        return "CAUTION"
    if tag in MEDIUM_PRIORITY_TAGS:
        return "REFERENCE_CAUTION"
    if tag in LOW_PRIORITY_TAGS:
        return "REFERENCE_ONLY"
    return "REFERENCE_CAUTION"


def tag_japanese_name(tag: str) -> str:
    c = canonical_tag(tag)
    jp = TAG_JA.get(c)
    return f"{jp}（{c}）" if jp else c


def score_signal_row(
    row: dict[str, Any] | pd.Series,
    rules_obj: dict[str, Any],
    *,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    sid = clean_str(strategy_id or (row.get("strategy_id") if isinstance(row, pd.Series) else row.get("strategy_id")))
    hits: list[dict[str, Any]] = []
    checked = 0
    evaluable = 0
    skipped_missing_feature = 0
    skipped_invalid_condition = 0
    missing_features: set[str] = set()
    for rule in rules_obj.get("rules", []):
        if not isinstance(rule, dict):
            continue
        if clean_str(rule.get("strategy_id")) != sid:
            continue
        checked += 1
        can_eval, eval_details = rule_evaluable(row, rule)
        if can_eval:
            evaluable += 1
        else:
            reasons = {clean_str(d.get("reason")) for d in eval_details}
            if "MISSING_FEATURE_VALUE" in reasons:
                skipped_missing_feature += 1
                for d in eval_details:
                    if clean_str(d.get("reason")) == "MISSING_FEATURE_VALUE":
                        missing_features.add(clean_str(d.get("feature")))
            else:
                skipped_invalid_condition += 1
            continue
        ok, details = rule_matches(row, rule)
        if ok:
            hit = dict(rule)
            hit["matched_conditions"] = details
            hit["warning_level"] = derive_warning_level(hit)
            hits.append(hit)
    positive_hits = [h for h in hits if clean_str(h.get("warning_level")) in {"POSITIVE_SUPPORT", "POSITIVE_WATCH"}]
    strong_hits = [h for h in hits if clean_str(h.get("warning_level")) == "STRONG_CAUTION"]
    caution_hits = [h for h in hits if clean_str(h.get("warning_level")) in {"CAUTION", "REFERENCE_CAUTION"}]
    ref_hits = [h for h in hits if clean_str(h.get("warning_level")) == "REFERENCE_ONLY"]
    return {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": sid,
        "rules_path": rules_obj.get("rules_path", ""),
        "rules_schema_version": rules_obj.get("schema_version", ""),
        "rules_cycle_ok": bool(rules_obj.get("cycle_ok", True)),
        "rules_checked": int(checked),
        "rules_evaluable": int(evaluable),
        "rules_skipped_missing_feature": int(skipped_missing_feature),
        "rules_skipped_invalid_condition": int(skipped_invalid_condition),
        "missing_features": sorted(x for x in missing_features if x),
        "hit_count": int(len(hits)),
        "positive_count": int(len(positive_hits)),
        "strong_caution_count": int(len(strong_hits)),
        "caution_count": int(len(caution_hits)),
        "reference_count": int(len(ref_hits)),
        "hits": hits,
    }


def hit_sort_key(hit: dict[str, Any]) -> tuple[int, float, float]:
    level = clean_str(hit.get("warning_level"))
    order = {
        "POSITIVE_SUPPORT": 0,
        "POSITIVE_WATCH": 1,
        "STRONG_CAUTION": 2,
        "CAUTION": 3,
        "REFERENCE_CAUTION": 4,
        "REFERENCE_ONLY": 5,
    }.get(level, 4)
    precision = safe_float(hit.get("tag_precision")) or 0.0
    recall = safe_float(hit.get("tag_recall")) or 0.0
    return (order, -precision, -recall)


def format_hit_line(hit: dict[str, Any]) -> str:
    tag = canonical_tag(hit.get("tag_name"))
    level = clean_str(hit.get("warning_level"))
    if level == "POSITIVE_SUPPORT":
        prefix = "✅ 好材料"
    elif level == "POSITIVE_WATCH":
        prefix = "好材料候補"
    elif level == "STRONG_CAUTION":
        prefix = "⚠️ 強め注意"
    elif level == "CAUTION":
        prefix = "注意"
    elif level == "REFERENCE_ONLY":
        prefix = "参考"
    else:
        prefix = "参考注意"
    tag_avg_r = safe_float(hit.get("tag_avg_r"))
    tag_win_rate = safe_float(hit.get("tag_win_rate"))
    tag_pf = safe_float(hit.get("tag_pf"))
    removed_avg_r = safe_float(hit.get("removed_avg_r"))
    kept_pf = safe_float(hit.get("kept_pf"))
    baseline_pf = safe_float(hit.get("baseline_pf"))
    precision = safe_float(hit.get("tag_precision"))
    verdict = clean_str(hit.get("verdict"))
    pieces = [f"{prefix}: {tag_japanese_name(tag)}"]
    if tag_avg_r is not None:
        pieces.append(f"タグ実績avgR={tag_avg_r:.2f}")
    elif removed_avg_r is not None:
        pieces.append(f"過去類似avgR={removed_avg_r:.2f}")
    if tag_win_rate is not None:
        pieces.append(f"勝率={tag_win_rate:.0%}")
    if tag_pf is not None:
        pieces.append(f"PF={tag_pf:.2f}")
    elif baseline_pf is not None and kept_pf is not None:
        pieces.append(f"除外後PF {baseline_pf:.2f}→{kept_pf:.2f}")
    if precision is not None:
        pieces.append(f"タグ一致率={precision:.0%}")
    if verdict == "not_loss_specific_also_on_wins":
        pieces.append("勝ちにも出るため参考扱い")
    return " / ".join(pieces)


def format_score_for_discord(score: dict[str, Any]) -> list[str]:
    if not score.get("rules_path"):
        return ["AIタグ: 未使用（ルールJSON未指定）"]
    if not score.get("rules_cycle_ok", True):
        return ["AIタグ: 未使用（ルールJSON読み込みNG）", f"path: {score.get('rules_path')}"]
    checked = int(score.get("rules_checked", 0) or 0)
    evaluable = int(score.get("rules_evaluable", 0) or 0)
    missing = int(score.get("rules_skipped_missing_feature", 0) or 0)
    hit_count = int(score.get("hit_count", 0) or 0)
    if hit_count <= 0:
        return [
            "AIタグ: 目立つ注意/好材料タグなし",
            f"判定: 評価可 {evaluable}/{checked}・特徴不足 {missing}・HIT 0",
        ]
    hits = sorted([h for h in score.get("hits", []) if isinstance(h, dict)], key=hit_sort_key)
    positive = int(score.get("positive_count", 0) or 0)
    strong = int(score.get("strong_caution_count", 0) or 0)
    caution = int(score.get("caution_count", 0) or 0)
    ref = int(score.get("reference_count", 0) or 0)
    header_parts = []
    if positive:
        header_parts.append(f"✅ 好材料 {positive}件")
    if strong:
        header_parts.append(f"⚠️ 強め注意 {strong}件")
    if caution:
        header_parts.append(f"参考注意 {caution}件")
    if ref:
        header_parts.append(f"参考 {ref}件")
    header = "AIタグ: " + " / ".join(header_parts)
    lines = [
        header,
        f"判定: 評価可 {evaluable}/{checked}・特徴不足 {missing}・HIT {hit_count}",
    ]
    for hit in hits[:6]:
        lines.append("- " + format_hit_line(hit))
        conds = []
        for c in hit.get("matched_conditions", [])[:2]:
            val = c.get("value")
            val_text = "N/A" if val is None else f"{float(val):.4f}"
            conds.append(f"{c.get('feature')}={val_text} {c.get('op')} {fmt_float(c.get('threshold'), 4)}")
        if conds:
            lines.append("  根拠: " + " / ".join(conds))
    if len(hits) > 6:
        lines.append(f"- ほか {len(hits) - 6}件")
    lines.append("注: AIタグは過去レビュー類似の注意/好材料ラベルで、勝敗確定ではありません。")
    return lines
