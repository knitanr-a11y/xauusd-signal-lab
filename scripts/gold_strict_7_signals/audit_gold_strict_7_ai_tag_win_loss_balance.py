#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Audit whether GOLD strict-7 AI tags are actually loss-only or also appear on wins.

This is a research/diagnostic script. It does not call AI, MT5, Discord, or order_send.

Main questions answered:
1. For each historical AI-review tag, how often did it appear on wins vs losses?
2. Are the current "risk" tags really loss-heavy, or do they also appear often on wins?
3. Which positive/win tags, if available in the AI-review ledger, are associated with wins?
4. Which tags should be shown as strong warning, reference-only, or positive support?

Inputs default to:
  data/runtime_logs/trade_ai_review_backtest_gold_strict_7/trade_feature_snapshot.csv
  data/runtime_logs/trade_ai_review_backtest_gold_strict_7/trade_ai_review_ledger.jsonl

Outputs default to:
  data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit.csv
  data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from gold_strict_7_signal_specs import get_signal_specs, validate_signal_specs

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AI_REVIEW_DIR = Path("data/runtime_logs/trade_ai_review_backtest_gold_strict_7")
DEFAULT_OUTPUT_CSV = Path("data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit.csv")
DEFAULT_OUTPUT_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit_summary.json")
SCHEMA_VERSION = "gold_strict_7_ai_tag_win_loss_balance_audit_v1"

RISK_TAG_KEYS = [
    "possible_risk_tags",
    "risk_tags",
    "execution_issue_tags",
    "system_issue_tags",
]

POSITIVE_TAG_KEYS = [
    "positive_tags",
    "possible_positive_tags",
    "good_tags",
    "strength_tags",
    "favorable_tags",
    "winning_reason_tags",
    "success_tags",
    "supporting_tags",
]

NON_INFORMATIVE_TAGS = {
    "", "-", "none", "null", "n/a", "na", "unknown", "unclear",
    "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag",
}

OUTPUT_COLUMNS = [
    "strategy_id",
    "tag_group",
    "tag_name",
    "tag_role",
    "strategy_trade_count",
    "strategy_win_count",
    "strategy_loss_count",
    "strategy_win_rate",
    "strategy_avg_r",
    "strategy_pf",
    "tag_hit_count",
    "tag_win_count",
    "tag_loss_count",
    "tag_breakeven_count",
    "tag_win_rate",
    "tag_loss_rate",
    "tag_avg_r",
    "tag_pf",
    "wins_with_tag_rate",
    "losses_with_tag_rate",
    "tag_absent_count",
    "tag_absent_win_rate",
    "tag_absent_avg_r",
    "tag_absent_pf",
    "loss_lift_vs_win_presence",
    "avg_r_delta_vs_absent",
    "pf_delta_vs_absent",
    "false_warning_win_count",
    "false_warning_win_rate_among_tag_hits",
    "wins_without_tag_count",
    "losses_without_tag_count",
    "verdict",
    "display_level_suggestion",
]


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


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    mkdirp(p.parent)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    mkdirp(p.parent)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not Path(path).exists():
        return rows
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def canonical_tag(tag: Any) -> str:
    return clean_str(tag).lower().replace(" ", "_").replace("-", "_")


def is_informative_tag(tag: str) -> bool:
    return canonical_tag(tag) not in NON_INFORMATIVE_TAGS


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def profit_factor(values: pd.Series) -> float | None:
    r = pd.to_numeric(values, errors="coerce").dropna()
    if r.empty:
        return None
    wins = float(r[r > 0].sum())
    losses = abs(float(r[r < 0].sum()))
    if losses <= 1e-12:
        return None if wins <= 1e-12 else 999.0
    return wins / losses


def win_count(df: pd.DataFrame) -> int:
    if "outcome" in df.columns:
        return int(df["outcome"].astype(str).str.upper().eq("WIN").sum())
    return int((pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce") > 0).sum())


def loss_count(df: pd.DataFrame) -> int:
    if "outcome" in df.columns:
        return int(df["outcome"].astype(str).str.upper().eq("LOSS").sum())
    return int((pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce") < 0).sum())


def breakeven_count(df: pd.DataFrame) -> int:
    if "outcome" in df.columns:
        return int(df["outcome"].astype(str).str.upper().eq("BREAKEVEN").sum())
    return int((pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce") == 0).sum())


def metrics(df: pd.DataFrame) -> dict[str, Any]:
    n = int(len(df))
    w = win_count(df)
    l = loss_count(df)
    b = breakeven_count(df)
    r = pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce")
    return {
        "count": n,
        "win_count": w,
        "loss_count": l,
        "breakeven_count": b,
        "win_rate": None if n <= 0 else float(w / n),
        "loss_rate": None if n <= 0 else float(l / n),
        "avg_r": None if r.dropna().empty else float(r.mean()),
        "pf": profit_factor(r),
    }


def normalize_tag_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # JSON list encoded as string sometimes appears in logs.
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [canonical_tag(x) for x in parsed if is_informative_tag(canonical_tag(x))]
            except Exception:
                pass
        values = [x.strip() for x in text.replace(";", ",").split(",")]
        return [canonical_tag(x) for x in values if is_informative_tag(canonical_tag(x))]
    if isinstance(value, list):
        return [canonical_tag(x) for x in value if is_informative_tag(canonical_tag(x))]
    return []


def explode_review_tags(rows: list[dict[str, Any]]) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        seen: set[tuple[str, str, str]] = set()
        for json_key in RISK_TAG_KEYS:
            tags = normalize_tag_list(row.get(json_key, []))
            group = "risk" if "risk" in json_key else ("execution" if "execution" in json_key else "system")
            for tag in tags:
                key = (tag, group, "risk")
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "trade_id": clean_str(row.get("trade_id")),
                    "order_key": clean_str(row.get("order_key")),
                    "payload_key": clean_str(row.get("payload_key")),
                    "strategy_id": clean_str(row.get("strategy_id")),
                    "symbol": clean_str(row.get("symbol")),
                    "tag_name": tag,
                    "tag_group": group,
                    "tag_role": "risk",
                    "source_json_key": json_key,
                })
        for json_key in POSITIVE_TAG_KEYS:
            tags = normalize_tag_list(row.get(json_key, []))
            for tag in tags:
                key = (tag, "positive", "positive")
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "trade_id": clean_str(row.get("trade_id")),
                    "order_key": clean_str(row.get("order_key")),
                    "payload_key": clean_str(row.get("payload_key")),
                    "strategy_id": clean_str(row.get("strategy_id")),
                    "symbol": clean_str(row.get("symbol")),
                    "tag_name": tag,
                    "tag_group": "positive",
                    "tag_role": "positive",
                    "source_json_key": json_key,
                })
    return pd.DataFrame(out)


def strict7_strategy_ids() -> list[str]:
    validate_signal_specs()
    return [spec.strategy_id for spec in get_signal_specs()]


def ensure_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for k in ["trade_id", "order_key", "payload_key", "strategy_id"]:
        if k not in out.columns:
            out[k] = ""
        out[k] = out[k].fillna("").astype(str)
    if "profit_r" not in out.columns:
        raise SystemExit("feature snapshot must have profit_r column for win/loss tag audit")
    if "outcome" not in out.columns:
        r = pd.to_numeric(out["profit_r"], errors="coerce")
        out["outcome"] = "BREAKEVEN"
        out.loc[r > 0, "outcome"] = "WIN"
        out.loc[r < 0, "outcome"] = "LOSS"
    return out


def classify_verdict(*, tag_role: str, tag_m: dict[str, Any], absent_m: dict[str, Any], wins_with_rate: float | None, losses_with_rate: float | None, min_sample: int) -> tuple[str, str]:
    n = int(tag_m.get("count", 0) or 0)
    if n < min_sample:
        return "sample_too_small", "参考"
    tag_avg = safe_float(tag_m.get("avg_r"))
    absent_avg = safe_float(absent_m.get("avg_r"))
    tag_pf = safe_float(tag_m.get("pf"))
    absent_pf = safe_float(absent_m.get("pf"))
    tag_wr = safe_float(tag_m.get("win_rate"))
    loss_presence = losses_with_rate or 0.0
    win_presence = wins_with_rate or 0.0
    role = clean_str(tag_role)
    if role == "positive":
        if tag_avg is not None and tag_avg > 0 and tag_wr is not None and tag_wr >= 0.45 and win_presence >= loss_presence * 1.2:
            return "positive_tag_seems_useful", "好材料"
        if tag_avg is not None and tag_avg <= 0:
            return "positive_tag_not_reliable_yet", "参考"
        return "positive_tag_watch", "好材料候補"
    # risk/execution/system tags
    if tag_avg is not None and absent_avg is not None and tag_avg >= absent_avg and win_presence >= loss_presence * 0.8:
        return "not_loss_specific_also_on_wins", "参考注意"
    if tag_avg is not None and tag_avg < 0 and loss_presence >= win_presence * 1.5:
        return "loss_heavy_warning", "強め注意"
    if tag_pf is not None and absent_pf is not None and tag_pf < absent_pf and loss_presence > win_presence:
        return "moderate_loss_warning", "注意"
    return "mixed_reference_only", "参考注意"


def audit(feature_df: pd.DataFrame, tag_df: pd.DataFrame, min_sample: int) -> pd.DataFrame:
    keys = ["trade_id", "order_key", "payload_key"]
    feature = ensure_keys(feature_df)
    allowed = set(strict7_strategy_ids())
    feature = feature[feature["strategy_id"].astype(str).isin(allowed)].copy()
    tag = tag_df.copy()
    for k in keys + ["strategy_id"]:
        if k not in tag.columns:
            tag[k] = ""
        tag[k] = tag[k].fillna("").astype(str)
    tag = tag[tag["strategy_id"].astype(str).isin(allowed)].copy()
    rows: list[dict[str, Any]] = []
    for strategy_id, base in feature.groupby("strategy_id", dropna=False):
        strategy_id = clean_str(strategy_id)
        if not strategy_id or base.empty:
            continue
        base_m = metrics(base)
        total_wins = int(base_m["win_count"])
        total_losses = int(base_m["loss_count"])
        sdf = tag[tag["strategy_id"] == strategy_id].copy()
        if sdf.empty:
            continue
        for (tag_group, tag_role, tag_name), tdf in sdf.groupby(["tag_group", "tag_role", "tag_name"], dropna=False):
            tag_group = clean_str(tag_group)
            tag_role = clean_str(tag_role)
            tag_name = clean_str(tag_name)
            if not tag_name:
                continue
            tagged_keys = tdf[keys].drop_duplicates().assign(_tag_hit=True)
            work = base.merge(tagged_keys, on=keys, how="left")
            hit_mask = work["_tag_hit"].eq(True)
            hit_df = work[hit_mask].copy()
            absent_df = work[~hit_mask].copy()
            tag_m = metrics(hit_df)
            absent_m = metrics(absent_df)
            tag_w = int(tag_m["win_count"])
            tag_l = int(tag_m["loss_count"])
            wins_with_rate = None if total_wins <= 0 else float(tag_w / total_wins)
            losses_with_rate = None if total_losses <= 0 else float(tag_l / total_losses)
            verdict, display = classify_verdict(
                tag_role=tag_role,
                tag_m=tag_m,
                absent_m=absent_m,
                wins_with_rate=wins_with_rate,
                losses_with_rate=losses_with_rate,
                min_sample=min_sample,
            )
            rows.append({
                "strategy_id": strategy_id,
                "tag_group": tag_group,
                "tag_name": tag_name,
                "tag_role": tag_role,
                "strategy_trade_count": int(base_m["count"]),
                "strategy_win_count": total_wins,
                "strategy_loss_count": total_losses,
                "strategy_win_rate": base_m["win_rate"],
                "strategy_avg_r": base_m["avg_r"],
                "strategy_pf": base_m["pf"],
                "tag_hit_count": int(tag_m["count"]),
                "tag_win_count": tag_w,
                "tag_loss_count": tag_l,
                "tag_breakeven_count": int(tag_m["breakeven_count"]),
                "tag_win_rate": tag_m["win_rate"],
                "tag_loss_rate": tag_m["loss_rate"],
                "tag_avg_r": tag_m["avg_r"],
                "tag_pf": tag_m["pf"],
                "wins_with_tag_rate": wins_with_rate,
                "losses_with_tag_rate": losses_with_rate,
                "tag_absent_count": int(absent_m["count"]),
                "tag_absent_win_rate": absent_m["win_rate"],
                "tag_absent_avg_r": absent_m["avg_r"],
                "tag_absent_pf": absent_m["pf"],
                "loss_lift_vs_win_presence": None if wins_with_rate in (None, 0.0) or losses_with_rate is None else float(losses_with_rate / wins_with_rate),
                "avg_r_delta_vs_absent": None if tag_m["avg_r"] is None or absent_m["avg_r"] is None else float(tag_m["avg_r"] - absent_m["avg_r"]),
                "pf_delta_vs_absent": None if tag_m["pf"] is None or absent_m["pf"] is None else float(tag_m["pf"] - absent_m["pf"]),
                "false_warning_win_count": tag_w if tag_role != "positive" else 0,
                "false_warning_win_rate_among_tag_hits": tag_m["win_rate"] if tag_role != "positive" else None,
                "wins_without_tag_count": int(total_wins - tag_w),
                "losses_without_tag_count": int(total_losses - tag_l),
                "verdict": verdict,
                "display_level_suggestion": display,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return out.sort_values(
        ["strategy_id", "tag_role", "display_level_suggestion", "tag_hit_count", "loss_lift_vs_win_presence"],
        ascending=[True, True, True, False, False],
        kind="mergesort",
    ).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit GOLD strict-7 AI tags against wins and losses.")
    p.add_argument("--ai-review-dir", type=Path, default=DEFAULT_AI_REVIEW_DIR)
    p.add_argument("--feature-snapshot-csv", type=Path, default=None)
    p.add_argument("--ai-review-jsonl", type=Path, default=None)
    p.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    p.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    p.add_argument("--min-sample", type=int, default=5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    ai_dir = resolve(args.ai_review_dir)
    feature_csv = resolve(args.feature_snapshot_csv) if args.feature_snapshot_csv else ai_dir / "trade_feature_snapshot.csv"
    review_jsonl = resolve(args.ai_review_jsonl) if args.ai_review_jsonl else ai_dir / "trade_ai_review_ledger.jsonl"
    output_csv = resolve(args.output_csv)
    output_json = resolve(args.output_json)
    if not feature_csv.exists():
        raise SystemExit(f"feature snapshot CSV not found: {feature_csv}")
    if not review_jsonl.exists():
        raise SystemExit(f"AI review JSONL not found: {review_jsonl}")
    feature_df = read_csv(feature_csv)
    review_rows = read_jsonl(review_jsonl)
    tag_df = explode_review_tags(review_rows)
    result = audit(feature_df, tag_df, min_sample=int(args.min_sample))
    write_csv(result, output_csv)
    by_verdict = result["verdict"].value_counts().to_dict() if not result.empty else {}
    positive_rows = int((result.get("tag_role", pd.Series(dtype=str)) == "positive").sum()) if not result.empty else 0
    risk_rows = int((result.get("tag_role", pd.Series(dtype=str)) != "positive").sum()) if not result.empty else 0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "input_feature_snapshot_csv": str(feature_csv),
        "input_ai_review_jsonl": str(review_jsonl),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "rows": {
            "feature_rows": int(len(feature_df)),
            "ai_review_rows": int(len(review_rows)),
            "tag_rows_exploded": int(len(tag_df)),
            "audit_rows": int(len(result)),
            "risk_or_issue_tag_rows": risk_rows,
            "positive_tag_rows": positive_rows,
        },
        "verdict_counts": by_verdict,
        "positive_tag_keys_checked": POSITIVE_TAG_KEYS,
        "risk_tag_keys_checked": RISK_TAG_KEYS,
        "interpretation": {
            "loss_heavy_warning": "risk tag appears much more often on losses than wins and has negative/weak R profile",
            "not_loss_specific_also_on_wins": "risk tag also appears frequently on winners, so do not treat as a strong warning",
            "positive_tag_seems_useful": "positive tag appears more supportive of wins and can be shown as a good sign",
        },
        "safety": {"ai_called": False, "mt5_calls": False, "order_send": False, "discord_send": False},
    }
    write_json(output_json, summary)
    print(json.dumps({
        "cycle_ok": True,
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "audit_rows": int(len(result)),
        "verdict_counts": by_verdict,
        "positive_tag_rows": positive_rows,
        "risk_or_issue_tag_rows": risk_rows,
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
