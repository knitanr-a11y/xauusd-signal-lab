#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for applying AI-tag numeric rules to a current signal row.

These utilities do not call AI. They only evaluate deterministic numeric rules
that were generated from historical AI-review tags and pre-entry features.

Important wording:
- A rule HIT means "the current signal numerically resembles a past AI-review tag".
- It is not a direct loss-probability prediction.
- Notification text therefore separates good-sign tags, stronger caution tags,
  reference-only tags, and historical tag-combination tendency.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "ai_tag_numeric_rule_utils_v5_tag_combo_display"

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
            "combo_rules": [],
        }
    with open(windows_long_path(p), "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"rules JSON must be an object: {p}")
    if "rules" not in obj or not isinstance(obj.get("rules"), list):
        raise ValueError(f"rules JSON missing list field 'rules': {p}")
    if "combo_rules" in obj and not isinstance(obj.get("combo_rules"), list):
        raise ValueError(f"rules JSON field 'combo_rules' must be a list when present: {p}")
    obj["rules_path"] = str(p)
    obj.setdefault("combo_rules", [])
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
        "複合警告": "COMBO_STRONG_CAUTION",
        "複合注意": "COMBO_CAUTION",
        "複合好機": "COMBO_POSITIVE_SUPPORT",
        "複合好機候補": "COMBO_POSITIVE_WATCH",
        "複合参考": "COMBO_REFERENCE",
        "STRONG_CAUTION": "STRONG_CAUTION",
        "CAUTION": "CAUTION",
        "REFERENCE_CAUTION": "REFERENCE_CAUTION",
        "REFERENCE_ONLY": "REFERENCE_ONLY",
        "POSITIVE_SUPPORT": "POSITIVE_SUPPORT",
        "POSITIVE_WATCH": "POSITIVE_WATCH",
        "COMBO_STRONG_CAUTION": "COMBO_STRONG_CAUTION",
        "COMBO_CAUTION": "COMBO_CAUTION",
        "COMBO_POSITIVE_SUPPORT": "COMBO_POSITIVE_SUPPORT",
        "COMBO_POSITIVE_WATCH": "COMBO_POSITIVE_WATCH",
        "COMBO_REFERENCE": "COMBO_REFERENCE",
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


def combo_tags_from_rule(rule: dict[str, Any]) -> list[str]:
    raw = rule.get("combo_tags", rule.get("tags", []))
    if isinstance(raw, str):
        parts = [x.strip() for x in raw.replace("+", ",").replace("|", ",").split(",")]
    elif isinstance(raw, list):
        parts = [str(x).strip() for x in raw]
    else:
        parts = []
    tags = sorted({canonical_tag(x) for x in parts if canonical_tag(x)})
    return tags


def combo_rule_matches(hit_tags: set[str], rule: dict[str, Any]) -> tuple[bool, list[str]]:
    tags = combo_tags_from_rule(rule)
    if len(tags) < 2:
        return False, tags
    return set(tags).issubset(hit_tags), tags


def combo_sort_key(combo: dict[str, Any]) -> tuple[int, int, float]:
    level = normalize_display_level(combo.get("display_level") or combo.get("warning_level"))
    order = {
        "COMBO_POSITIVE_SUPPORT": 0,
        "COMBO_POSITIVE_WATCH": 1,
        "COMBO_STRONG_CAUTION": 2,
        "COMBO_CAUTION": 3,
        "COMBO_REFERENCE": 4,
    }.get(level, 4)
    n = int(safe_float(combo.get("sample_count")) or 0)
    avg_delta = abs(safe_float(combo.get("avg_r_delta")) or 0.0)
    return (order, -n, -avg_delta)


def combo_level_prefix(level: str) -> str:
    if level == "COMBO_POSITIVE_SUPPORT":
        return "✅ 複合好機"
    if level == "COMBO_POSITIVE_WATCH":
        return "複合好機候補"
    if level == "COMBO_STRONG_CAUTION":
        return "⚠️ 複合警告"
    if level == "COMBO_CAUTION":
        return "複合注意"
    return "複合参考"


def format_pct(value: Any) -> str:
    x = safe_float(value)
    return "N/A" if x is None else f"{x:.0%}"


def pf_text(value: Any) -> str:
    x = safe_float(value)
    if x is None:
        return "N/A"
    if x >= 900:
        return "∞"
    return f"{x:.2f}"


def format_combo_line(combo: dict[str, Any]) -> str:
    level = normalize_display_level(combo.get("display_level") or combo.get("warning_level")) or "COMBO_REFERENCE"
    tags = combo.get("matched_tags") if isinstance(combo.get("matched_tags"), list) else combo_tags_from_rule(combo)
    tag_text = " + ".join(tag_japanese_name(str(t)) for t in tags)
    sample_count = int(safe_float(combo.get("sample_count")) or 0)
    win_rate = combo.get("win_rate")
    pf = combo.get("pf")
    avg_r = combo.get("avg_r")
    base_wr = combo.get("baseline_win_rate")
    base_pf = combo.get("baseline_pf")
    base_avg = combo.get("baseline_avg_r")
    avg_delta = safe_float(combo.get("avg_r_delta"))
    wr_delta = safe_float(combo.get("win_rate_delta"))
    pieces = [f"{combo_level_prefix(level)}: {tag_text}"]
    pieces.append(f"過去類似={sample_count}件")
    pieces.append(f"勝率={format_pct(win_rate)}")
    pieces.append(f"PF={pf_text(pf)}")
    if safe_float(avg_r) is not None:
        pieces.append(f"avgR={float(avg_r):+.2f}")
    if safe_float(base_avg) is not None or safe_float(base_wr) is not None or safe_float(base_pf) is not None:
        base_parts = []
        if safe_float(base_wr) is not None:
            base_parts.append(f"勝率{format_pct(base_wr)}")
        if safe_float(base_pf) is not None:
            base_parts.append(f"PF{pf_text(base_pf)}")
        if safe_float(base_avg) is not None:
            base_parts.append(f"avgR{float(base_avg):+.2f}")
        if base_parts:
            pieces.append("戦略平均=" + "/".join(base_parts))
    delta_parts = []
    if wr_delta is not None:
        delta_parts.append(f"勝率差{wr_delta:+.0%}")
    if avg_delta is not None:
        delta_parts.append(f"avgR差{avg_delta:+.2f}")
    if delta_parts:
        pieces.append("差分=" + "/".join(delta_parts))
    reason = clean_str(combo.get("reason"))
    if reason:
        pieces.append(reason)
    return " / ".join(pieces)


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

    hit_tags = sorted({canonical_tag(h.get("tag_name")) for h in hits if canonical_tag(h.get("tag_name"))})
    hit_tag_set = set(hit_tags)
    combo_hits: list[dict[str, Any]] = []
    combo_checked = 0
    for combo in rules_obj.get("combo_rules", []):
        if not isinstance(combo, dict):
            continue
        if clean_str(combo.get("strategy_id")) != sid:
            continue
        combo_checked += 1
        ok, tags = combo_rule_matches(hit_tag_set, combo)
        if ok:
            ch = dict(combo)
            ch["matched_tags"] = tags
            ch["display_level"] = normalize_display_level(ch.get("display_level") or ch.get("warning_level")) or "COMBO_REFERENCE"
            combo_hits.append(ch)

    positive_hits = [h for h in hits if clean_str(h.get("warning_level")) in {"POSITIVE_SUPPORT", "POSITIVE_WATCH"}]
    strong_hits = [h for h in hits if clean_str(h.get("warning_level")) == "STRONG_CAUTION"]
    caution_hits = [h for h in hits if clean_str(h.get("warning_level")) == "CAUTION"]
    ref_caution_hits = [h for h in hits if clean_str(h.get("warning_level")) == "REFERENCE_CAUTION"]
    ref_hits = [h for h in hits if clean_str(h.get("warning_level")) == "REFERENCE_ONLY"]
    combo_positive = [h for h in combo_hits if clean_str(h.get("display_level")) in {"COMBO_POSITIVE_SUPPORT", "COMBO_POSITIVE_WATCH"}]
    combo_strong = [h for h in combo_hits if clean_str(h.get("display_level")) == "COMBO_STRONG_CAUTION"]
    combo_caution = [h for h in combo_hits if clean_str(h.get("display_level")) == "COMBO_CAUTION"]
    combo_ref = [h for h in combo_hits if clean_str(h.get("display_level")) == "COMBO_REFERENCE"]
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
        "reference_caution_count": int(len(ref_caution_hits)),
        "reference_count": int(len(ref_hits)),
        "hit_tags": hit_tags,
        "hits": hits,
        "combo_rules_checked": int(combo_checked),
        "combo_hit_count": int(len(combo_hits)),
        "combo_positive_count": int(len(combo_positive)),
        "combo_strong_caution_count": int(len(combo_strong)),
        "combo_caution_count": int(len(combo_caution)),
        "combo_reference_count": int(len(combo_ref)),
        "combo_hits": combo_hits,
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
    ref_caution = int(score.get("reference_caution_count", 0) or 0)
    ref = int(score.get("reference_count", 0) or 0)
    header_parts = []
    if positive:
        header_parts.append(f"✅ 好材料 {positive}件")
    if strong:
        header_parts.append(f"⚠️ 強め注意 {strong}件")
    if caution:
        header_parts.append(f"注意 {caution}件")
    if ref_caution:
        header_parts.append(f"参考注意 {ref_caution}件")
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

    combo_hits = sorted([c for c in score.get("combo_hits", []) if isinstance(c, dict)], key=combo_sort_key)
    if combo_hits:
        combo_positive = int(score.get("combo_positive_count", 0) or 0)
        combo_strong = int(score.get("combo_strong_caution_count", 0) or 0)
        combo_caution = int(score.get("combo_caution_count", 0) or 0)
        combo_ref = int(score.get("combo_reference_count", 0) or 0)
        combo_parts = []
        if combo_positive:
            combo_parts.append(f"✅ 複合好機 {combo_positive}件")
        if combo_strong:
            combo_parts.append(f"⚠️ 複合警告 {combo_strong}件")
        if combo_caution:
            combo_parts.append(f"複合注意 {combo_caution}件")
        if combo_ref:
            combo_parts.append(f"複合参考 {combo_ref}件")
        lines.append("タグ組み合わせ: " + " / ".join(combo_parts))
        for combo in combo_hits[:3]:
            lines.append("- " + format_combo_line(combo))
        if len(combo_hits) > 3:
            lines.append(f"- 組み合わせほか {len(combo_hits) - 3}件")
    elif int(score.get("combo_rules_checked", 0) or 0) > 0:
        lines.append("タグ組み合わせ: 目立つ複合傾向なし")

    lines.append("注: AIタグは過去レビュー類似の注意/好材料ラベルで、勝敗確定ではありません。")
    return lines
