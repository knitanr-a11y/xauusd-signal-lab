#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for applying AI-tag numeric rules to a current signal row.

These utilities do not call AI. They only evaluate deterministic numeric rules
that were generated from historical AI-review tags and pre-entry features.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "ai_tag_numeric_rule_utils_v1"


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
    return None


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
    ok = op_match(value, op, threshold)
    return ok, {"feature": feature, "op": op, "threshold": threshold, "value": value, "ok": ok, "aliases": aliases}


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


def score_signal_row(
    row: dict[str, Any] | pd.Series,
    rules_obj: dict[str, Any],
    *,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    sid = clean_str(strategy_id or (row.get("strategy_id") if isinstance(row, pd.Series) else row.get("strategy_id")))
    hits: list[dict[str, Any]] = []
    checked = 0
    for rule in rules_obj.get("rules", []):
        if not isinstance(rule, dict):
            continue
        if clean_str(rule.get("strategy_id")) != sid:
            continue
        checked += 1
        ok, details = rule_matches(row, rule)
        if ok:
            hit = dict(rule)
            hit["matched_conditions"] = details
            hits.append(hit)
    return {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": sid,
        "rules_path": rules_obj.get("rules_path", ""),
        "rules_schema_version": rules_obj.get("schema_version", ""),
        "rules_cycle_ok": bool(rules_obj.get("cycle_ok", True)),
        "rules_checked": int(checked),
        "hit_count": int(len(hits)),
        "hits": hits,
    }


def format_score_for_discord(score: dict[str, Any]) -> list[str]:
    if not score.get("rules_path"):
        return ["個別AIタグ推定: 未使用", "AIタグ数値ルール: 未指定"]
    if not score.get("rules_cycle_ok", True):
        return ["個別AIタグ推定: 未使用", f"AIタグ数値ルール: 読み込みNG ({score.get('rules_path')})"]
    hits = score.get("hits", [])
    if not hits:
        return [
            "個別AIタグ推定: なし",
            f"AIタグ数値ルール: checked={score.get('rules_checked', 0)} hit=0",
        ]
    lines = [
        f"個別AIタグ推定: ⚠️ HIT {len(hits)}件",
        f"AIタグ数値ルール: checked={score.get('rules_checked', 0)} hit={len(hits)}",
    ]
    for hit in hits[:5]:
        tag = clean_str(hit.get("tag_name"), "unknown_tag")
        severity = clean_str(hit.get("severity"), "WATCH")
        action = clean_str(hit.get("action"), "WARN")
        precision = hit.get("tag_precision", "")
        recall = hit.get("tag_recall", "")
        conds = []
        for c in hit.get("matched_conditions", []):
            val = c.get("value")
            val_text = "N/A" if val is None else f"{float(val):.4f}"
            conds.append(f"{c.get('feature')}={val_text} {c.get('op')} {c.get('threshold')}")
        lines.append(f"- {tag} / {severity} / {action} / precision={precision} recall={recall}")
        if conds:
            lines.append("  根拠: " + " AND ".join(conds))
    if len(hits) > 5:
        lines.append(f"- ほか {len(hits) - 5}件")
    return lines
