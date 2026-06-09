#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 15 audit-only replay execution.

This stage executes an audit-only, row-level replay from GOLD V3 Stage 14
approved replay-plan preview rows against the GOLD V3 Stage 05 label-feature
join artifact. It recalculates true row-filtered trade frequency, win rate,
profit factor, drawdown, monthly stability, and overlap diagnostics for the
approved audit-only candidates.

This is not final candidate approval, not threshold finalization, not model
training, not signal generation, not live evaluation, and not deployment.
It does not create ZIP output and does not call Discord, MT5, AI API, live hook,
live evaluator, or final signal code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd


STEP = "GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION"
UPSTREAM14_READY_STATUS = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY"
UPSTREAM05_READY_STATUS = "GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_BLOCKED_AUDIT_ONLY"
EXCEPTION_STATUS = "GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_EXCEPTION_AUDIT_ONLY"

UPSTREAM14_NAME = "14_human_ranking_decision_intake_audit_only"
UPSTREAM05_NAME = "05_label_feature_join_walkforward_split_audit_only"
OUT_NAME = "15_audit_only_replay_execution"

APPROVE_FOR_REPLAY = "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY"
EXPECTED_APPROVED_ROWS = 7
EXPECTED_APPROVED_ENTRY_FAMILIES = 3

FALSE_FLAGS = {
    "auto_approval": False,
    "final_candidate_approval": False,
    "threshold_finalization": False,
    "model_training": False,
    "signals_generated": False,
    "zip_output_created": False,
    "ai_api_called": False,
    "discord_enabled": False,
    "mt5_enabled": False,
    "live_hook_enabled": False,
    "live_evaluator_enabled": False,
    "final_signal_enabled": False,
    "gold_v2_live_sot_used": False,
    "quarantined_legacy_artifacts_read": False,
}

REQUIRED_BASE_COLS = [
    "entry_time_utc",
    "entry_month",
    "profile_id",
    "direction",
    "label_outcome",
    "label_price_distance_result_usd",
]

OPTIONAL_LEDGER_COLS = [
    "feature_bar_open_utc",
    "first_touch_time_utc",
    "first_touch_bar_offset_m5",
    "window_m5_bars",
    "timeout_close_price",
]

INPUT_INVENTORY_FIELDS = ["input_label", "path", "required", "exists", "size_bytes", "sha256"]
DECISION_FIELDS = ["decision_key", "value", "detail"]
BLOCKER_FIELDS = ["blocker_id", "blocker_name", "status", "detail"]

CANDIDATE_METRIC_FIELDS = [
    "plan_row_number",
    "source_rank",
    "candidate_group_id",
    "entry_family_key",
    "profile_id",
    "direction",
    "feature_column",
    "rule_expression_preview",
    "rule_parse_status",
    "rule_parse_detail",
    "risk_note",
    "approved_for_next_audit_only_replay",
    "rows_replayed",
    "unique_entry_times",
    "calendar_days_in_trade_span",
    "active_entry_dates",
    "trades_per_calendar_day_true",
    "trades_per_active_day_true",
    "tp_count",
    "sl_count",
    "timeout_count",
    "other_outcome_count",
    "win_count_result_positive",
    "loss_count_result_negative",
    "breakeven_count_result_zero",
    "win_rate_result_positive",
    "tp_rate",
    "avg_result_usd",
    "median_result_usd",
    "sum_result_usd",
    "gross_profit_usd",
    "gross_loss_abs_usd",
    "profit_factor",
    "max_drawdown_usd",
    "max_consecutive_losses",
    "best_trade_usd",
    "worst_trade_usd",
    "first_entry_time_utc",
    "last_entry_time_utc",
    "true_metric_scope",
    "not_final_approval",
]

FAMILY_METRIC_FIELDS = [
    "candidate_group_id",
    "entry_family_key",
    "feature_column",
    "rule_expression_preview",
    "direction",
    "profile_count",
    "profiles",
    "plan_rows",
    "family_is_shared_entry_condition",
    "profile_level_rows_total",
    "unique_entry_times_family",
    "calendar_days_in_family_span",
    "active_entry_dates_family",
    "profile_level_trades_per_calendar_day_true",
    "unique_entry_times_per_calendar_day_true",
    "best_profile_by_profit_factor",
    "best_profile_profit_factor",
    "best_profile_win_rate",
    "best_profile_trades_per_calendar_day",
    "best_profile_rows_replayed",
    "family_note",
]

MONTHLY_FIELDS = [
    "plan_row_number",
    "source_rank",
    "candidate_group_id",
    "entry_family_key",
    "profile_id",
    "direction",
    "entry_month",
    "rows_replayed",
    "tp_count",
    "sl_count",
    "timeout_count",
    "win_count_result_positive",
    "loss_count_result_negative",
    "win_rate_result_positive",
    "avg_result_usd",
    "sum_result_usd",
    "gross_profit_usd",
    "gross_loss_abs_usd",
    "profit_factor",
]

OVERLAP_FIELDS = [
    "entry_family_key",
    "candidate_group_id",
    "feature_column",
    "rule_expression_preview",
    "direction",
    "profile_count",
    "profiles",
    "unique_entry_times",
    "profile_level_rows",
    "max_profiles_same_entry_time",
    "entry_times_with_multiple_profiles",
    "overlap_note",
]

LEDGER_PREFIX_FIELDS = [
    "plan_row_number",
    "source_rank",
    "candidate_group_id",
    "entry_family_key",
    "profile_id",
    "direction",
    "feature_column",
    "rule_expression_preview",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_default() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root(repo_root: Path) -> Path:
    return repo_root.parents[1] if len(repo_root.parents) >= 2 else repo_root.parent


def v3_root_candidates(repo_root: Path) -> list[Path]:
    primary = files_root(repo_root) / "FX_OUTPUTS" / "gold_v3"
    legacy = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3"
    out: list[Path] = []
    for p in [primary, legacy]:
        if p not in out:
            out.append(p)
    return out


def select_v3_root(repo_root: Path) -> tuple[Path, str]:
    for p in v3_root_candidates(repo_root):
        if (p / UPSTREAM14_NAME / "gold_v3_14_summary.json").exists() or (p / UPSTREAM14_NAME / "gold_v3_14_replay_plan_preview.csv").exists():
            return p, "selected_existing_stage14_root"
    return v3_root_candidates(repo_root)[0], "selected_primary_gold_v3_root_no_stage14_inputs_found"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b=""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = clean_json(obj)
    with path.open("w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def clean_json(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json(v) for v in x]
    if isinstance(x, (pd.Timestamp,)):
        return x.isoformat()
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def inventory_rows(items: Sequence[tuple[str, Path, bool]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, path, required in items:
        rows.append({
            "input_label": label,
            "path": str(path),
            "required": required,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() else "",
        })
    return rows


def md(value: Any) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "/")


def md_table(rows: Sequence[dict[str, Any]], fields: Sequence[str], limit: int = 80) -> str:
    if not rows:
        return "_No rows._"
    fields = list(fields)
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in list(rows)[:limit]:
        out.append("| " + " | ".join(md(row.get(f, ""))[:500] for f in fields) + " |")
    return "\n".join(out)


def parse_rule_expression(expr: Any, feature_column: str) -> tuple[str, str, tuple[str, float | None, float | None]]:
    text = str(expr or "").strip()
    feature = str(feature_column or "").strip()
    if not text or not feature:
        return "INVALID", "missing rule expression or feature column", ("invalid", None, None)

    num = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

    range_pattern = re.compile(rf"^\s*({num})\s*<=\s*([A-Za-z_][A-Za-z0-9_]*)\s*<=\s*({num})\s*$")
    lower_pattern = re.compile(rf"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*>=\s*({num})\s*$")
    upper_pattern = re.compile(rf"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*<=\s*({num})\s*$")
    rev_lower_pattern = re.compile(rf"^\s*({num})\s*<=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
    rev_upper_pattern = re.compile(rf"^\s*({num})\s*>=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")

    m = range_pattern.match(text)
    if m:
        lo, feat, hi = float(m.group(1)), m.group(2), float(m.group(3))
        if feat != feature:
            return "INVALID", f"expression feature {feat} does not match feature_column {feature}", ("invalid", None, None)
        return "VALID", "range expression parsed", ("range", lo, hi)

    m = lower_pattern.match(text)
    if m:
        feat, lo = m.group(1), float(m.group(2))
        if feat != feature:
            return "INVALID", f"expression feature {feat} does not match feature_column {feature}", ("invalid", None, None)
        return "VALID", "lower-bound expression parsed", ("lower", lo, None)

    m = upper_pattern.match(text)
    if m:
        feat, hi = m.group(1), float(m.group(2))
        if feat != feature:
            return "INVALID", f"expression feature {feat} does not match feature_column {feature}", ("invalid", None, None)
        return "VALID", "upper-bound expression parsed", ("upper", None, hi)

    m = rev_lower_pattern.match(text)
    if m:
        lo, feat = float(m.group(1)), m.group(2)
        if feat != feature:
            return "INVALID", f"expression feature {feat} does not match feature_column {feature}", ("invalid", None, None)
        return "VALID", "reverse lower-bound expression parsed", ("lower", lo, None)

    m = rev_upper_pattern.match(text)
    if m:
        hi, feat = float(m.group(1)), m.group(2)
        if feat != feature:
            return "INVALID", f"expression feature {feat} does not match feature_column {feature}", ("invalid", None, None)
        return "VALID", "reverse upper-bound expression parsed", ("upper", None, hi)

    return "INVALID", f"unsupported expression syntax: {text}", ("invalid", None, None)


def apply_rule(df: pd.DataFrame, feature: str, parsed: tuple[str, float | None, float | None]) -> pd.Series:
    kind, lo, hi = parsed
    s = pd.to_numeric(df[feature], errors="coerce")
    if kind == "range":
        return s.ge(float(lo)) & s.le(float(hi))
    if kind == "lower":
        return s.ge(float(lo))
    if kind == "upper":
        return s.le(float(hi))
    return pd.Series(False, index=df.index)


def parse_dt_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce")


def calendar_days_from_times(s: pd.Series) -> int:
    dt = parse_dt_series(s).dropna()
    if dt.empty:
        return 0
    return int((dt.max().date() - dt.min().date()).days) + 1


def active_dates_from_times(s: pd.Series) -> int:
    dt = parse_dt_series(s).dropna()
    if dt.empty:
        return 0
    return int(dt.dt.date.nunique())


def profit_factor_display(gross_profit: float, gross_loss_abs: float) -> str:
    if gross_loss_abs > 0:
        return f"{gross_profit / gross_loss_abs:.10g}"
    if gross_profit > 0:
        return "INF_NO_LOSS"
    return ""


def profit_factor_sort_value(display: str) -> float:
    if str(display).startswith("INF"):
        return 1e12
    try:
        return float(display)
    except Exception:
        return -1.0


def max_consecutive_losses(results: Iterable[float]) -> int:
    best = 0
    cur = 0
    for x in results:
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def metrics_for_ledger(part: pd.DataFrame) -> dict[str, Any]:
    n = int(len(part))
    if n == 0:
        return {
            "rows_replayed": 0,
            "unique_entry_times": 0,
            "calendar_days_in_trade_span": 0,
            "active_entry_dates": 0,
            "trades_per_calendar_day_true": 0.0,
            "trades_per_active_day_true": 0.0,
            "tp_count": 0,
            "sl_count": 0,
            "timeout_count": 0,
            "other_outcome_count": 0,
            "win_count_result_positive": 0,
            "loss_count_result_negative": 0,
            "breakeven_count_result_zero": 0,
            "win_rate_result_positive": 0.0,
            "tp_rate": 0.0,
            "avg_result_usd": 0.0,
            "median_result_usd": 0.0,
            "sum_result_usd": 0.0,
            "gross_profit_usd": 0.0,
            "gross_loss_abs_usd": 0.0,
            "profit_factor": "",
            "max_drawdown_usd": 0.0,
            "max_consecutive_losses": 0,
            "best_trade_usd": 0.0,
            "worst_trade_usd": 0.0,
            "first_entry_time_utc": "",
            "last_entry_time_utc": "",
        }

    work = part.copy()
    work["_entry_dt"] = parse_dt_series(work["entry_time_utc"])
    work = work.sort_values(["_entry_dt", "entry_time_utc"], kind="mergesort")
    res = pd.to_numeric(work["label_price_distance_result_usd"], errors="coerce").fillna(0.0)
    gross_profit = float(res[res > 0].sum())
    gross_loss_abs = float(-res[res < 0].sum())
    pf = profit_factor_display(gross_profit, gross_loss_abs)
    cum = res.cumsum()
    peak = cum.cummax()
    dd = peak - cum
    cal_days = calendar_days_from_times(work["entry_time_utc"])
    active_days = active_dates_from_times(work["entry_time_utc"])

    return {
        "rows_replayed": n,
        "unique_entry_times": int(work["entry_time_utc"].astype(str).nunique()),
        "calendar_days_in_trade_span": cal_days,
        "active_entry_dates": active_days,
        "trades_per_calendar_day_true": round(n / cal_days, 10) if cal_days else 0.0,
        "trades_per_active_day_true": round(n / active_days, 10) if active_days else 0.0,
        "tp_count": int((work["label_outcome"].astype(str) == "TP").sum()),
        "sl_count": int((work["label_outcome"].astype(str) == "SL").sum()),
        "timeout_count": int((work["label_outcome"].astype(str) == "TIMEOUT").sum()),
        "other_outcome_count": int((~work["label_outcome"].astype(str).isin(["TP", "SL", "TIMEOUT"])).sum()),
        "win_count_result_positive": int((res > 0).sum()),
        "loss_count_result_negative": int((res < 0).sum()),
        "breakeven_count_result_zero": int((res == 0).sum()),
        "win_rate_result_positive": round(float((res > 0).sum() / n), 10) if n else 0.0,
        "tp_rate": round(float((work["label_outcome"].astype(str) == "TP").sum() / n), 10) if n else 0.0,
        "avg_result_usd": round(float(res.mean()), 10),
        "median_result_usd": round(float(res.median()), 10),
        "sum_result_usd": round(float(res.sum()), 10),
        "gross_profit_usd": round(gross_profit, 10),
        "gross_loss_abs_usd": round(gross_loss_abs, 10),
        "profit_factor": pf,
        "max_drawdown_usd": round(float(dd.max()), 10) if len(dd) else 0.0,
        "max_consecutive_losses": max_consecutive_losses(res.tolist()),
        "best_trade_usd": round(float(res.max()), 10),
        "worst_trade_usd": round(float(res.min()), 10),
        "first_entry_time_utc": str(work["_entry_dt"].min()) if work["_entry_dt"].notna().any() else "",
        "last_entry_time_utc": str(work["_entry_dt"].max()) if work["_entry_dt"].notna().any() else "",
    }


def load_stage05_join_rows(path: Path, feature_columns: Sequence[str]) -> tuple[pd.DataFrame, list[str]]:
    header = pd.read_csv(path, nrows=0)
    available = set(header.columns)
    needed = list(dict.fromkeys(REQUIRED_BASE_COLS + list(feature_columns) + [c for c in OPTIONAL_LEDGER_COLS if c in available]))
    missing = [c for c in REQUIRED_BASE_COLS + list(feature_columns) if c not in available]
    if missing:
        return pd.DataFrame(), missing
    return pd.read_csv(path, usecols=needed), []


def build_replay(
    plan_rows: Sequence[dict[str, str]],
    data: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    metric_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    parse_errors: list[str] = []

    for plan in plan_rows:
        plan_no = str(plan.get("plan_row_number", "")).strip()
        source_rank = str(plan.get("source_rank", "")).strip()
        group = str(plan.get("candidate_group_id", "")).strip()
        family = str(plan.get("entry_family_key", "")).strip()
        profile = str(plan.get("profile_id", "")).strip()
        direction = str(plan.get("direction", "")).strip()
        feature = str(plan.get("feature_column", "")).strip()
        expr = str(plan.get("rule_expression_preview", "")).strip()

        parse_status, parse_detail, parsed = parse_rule_expression(expr, feature)
        if parse_status != "VALID":
            parse_errors.append(f"plan_row={plan_no} rank={source_rank}: {parse_detail}")

        if parse_status == "VALID" and feature in data.columns:
            mask = data["profile_id"].astype(str).eq(profile)
            mask &= data["direction"].astype(str).eq(direction)
            mask &= apply_rule(data, feature, parsed)
            part = data[mask].copy()
        else:
            part = data.iloc[0:0].copy()

        if not part.empty:
            part = part.sort_values(["entry_time_utc"], kind="mergesort").copy()
            for _, r in part.iterrows():
                ledger = {
                    "plan_row_number": plan_no,
                    "source_rank": source_rank,
                    "candidate_group_id": group,
                    "entry_family_key": family,
                    "profile_id": profile,
                    "direction": direction,
                    "feature_column": feature,
                    "rule_expression_preview": expr,
                }
                for c in list(REQUIRED_BASE_COLS) + [feature] + [x for x in OPTIONAL_LEDGER_COLS if x in part.columns]:
                    ledger[c] = r.get(c, "")
                ledger_rows.append(ledger)

        m = metrics_for_ledger(part)
        metric = {
            "plan_row_number": plan_no,
            "source_rank": source_rank,
            "candidate_group_id": group,
            "entry_family_key": family,
            "profile_id": profile,
            "direction": direction,
            "feature_column": feature,
            "rule_expression_preview": expr,
            "rule_parse_status": parse_status,
            "rule_parse_detail": parse_detail,
            "risk_note": "absolute/shared family risk must be interpreted from Stage 14; true replay metrics only",
            "approved_for_next_audit_only_replay": True,
            **m,
            "true_metric_scope": "GOLD V3 Stage05 label-feature row replay; row-level rule filter; no live deployment",
            "not_final_approval": True,
        }
        metric_rows.append(metric)

        if not part.empty:
            work = part.copy()
            if "entry_month" not in work.columns:
                work["entry_month"] = parse_dt_series(work["entry_time_utc"]).dt.strftime("%Y-%m")
            for month, x in work.groupby("entry_month", dropna=False):
                mm = metrics_for_ledger(x)
                monthly_rows.append({
                    "plan_row_number": plan_no,
                    "source_rank": source_rank,
                    "candidate_group_id": group,
                    "entry_family_key": family,
                    "profile_id": profile,
                    "direction": direction,
                    "entry_month": month,
                    "rows_replayed": mm["rows_replayed"],
                    "tp_count": mm["tp_count"],
                    "sl_count": mm["sl_count"],
                    "timeout_count": mm["timeout_count"],
                    "win_count_result_positive": mm["win_count_result_positive"],
                    "loss_count_result_negative": mm["loss_count_result_negative"],
                    "win_rate_result_positive": mm["win_rate_result_positive"],
                    "avg_result_usd": mm["avg_result_usd"],
                    "sum_result_usd": mm["sum_result_usd"],
                    "gross_profit_usd": mm["gross_profit_usd"],
                    "gross_loss_abs_usd": mm["gross_loss_abs_usd"],
                    "profit_factor": mm["profit_factor"],
                })

    metric_rows.sort(key=lambda r: (profit_factor_sort_value(str(r.get("profit_factor", ""))), float(r.get("win_rate_result_positive", 0.0)), float(r.get("trades_per_calendar_day_true", 0.0))), reverse=True)
    return metric_rows, ledger_rows, monthly_rows, [], parse_errors


def build_family_metrics(candidate_metrics: Sequence[dict[str, Any]], ledger_rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    family_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_metrics:
        by_family[str(row.get("entry_family_key", ""))].append(row)

    ledger_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger_rows:
        ledger_by_family[str(row.get("entry_family_key", ""))].append(row)

    for family_key, metrics in by_family.items():
        profiles = sorted({str(r.get("profile_id", "")) for r in metrics if str(r.get("profile_id", "")).strip()})
        best = max(metrics, key=lambda r: (profit_factor_sort_value(str(r.get("profit_factor", ""))), float(r.get("win_rate_result_positive", 0.0)), float(r.get("trades_per_calendar_day_true", 0.0)))) if metrics else {}
        ledger = ledger_by_family.get(family_key, [])
        ledger_df = pd.DataFrame(ledger)
        if not ledger_df.empty:
            profile_level_rows = int(len(ledger_df))
            unique_entry = int(ledger_df["entry_time_utc"].astype(str).nunique())
            cal_days = calendar_days_from_times(ledger_df["entry_time_utc"])
            active_days = active_dates_from_times(ledger_df["entry_time_utc"])
            profile_level_tpd = round(profile_level_rows / cal_days, 10) if cal_days else 0.0
            unique_tpd = round(unique_entry / cal_days, 10) if cal_days else 0.0
            entry_counts = ledger_df.groupby("entry_time_utc")["profile_id"].nunique()
            max_profiles_same_entry = int(entry_counts.max()) if len(entry_counts) else 0
            multi_entry_times = int((entry_counts > 1).sum()) if len(entry_counts) else 0
        else:
            profile_level_rows = 0
            unique_entry = 0
            cal_days = 0
            active_days = 0
            profile_level_tpd = 0.0
            unique_tpd = 0.0
            max_profiles_same_entry = 0
            multi_entry_times = 0

        group = str(metrics[0].get("candidate_group_id", "")) if metrics else ""
        feature = str(metrics[0].get("feature_column", "")) if metrics else ""
        expr = str(metrics[0].get("rule_expression_preview", "")) if metrics else ""
        direction = str(metrics[0].get("direction", "")) if metrics else ""
        shared = len(profiles) > 1 or "GROUP_H1_ATR56_HIGH_VOL" in group or "h1_atr56" in family_key
        note = "shared entry family; profiles are TP/SL/horizon comparisons, not independent entry ideas" if shared else "unique entry family"

        family_rows.append({
            "candidate_group_id": group,
            "entry_family_key": family_key,
            "feature_column": feature,
            "rule_expression_preview": expr,
            "direction": direction,
            "profile_count": len(profiles),
            "profiles": ";".join(profiles),
            "plan_rows": len(metrics),
            "family_is_shared_entry_condition": shared,
            "profile_level_rows_total": profile_level_rows,
            "unique_entry_times_family": unique_entry,
            "calendar_days_in_family_span": cal_days,
            "active_entry_dates_family": active_days,
            "profile_level_trades_per_calendar_day_true": profile_level_tpd,
            "unique_entry_times_per_calendar_day_true": unique_tpd,
            "best_profile_by_profit_factor": best.get("profile_id", ""),
            "best_profile_profit_factor": best.get("profit_factor", ""),
            "best_profile_win_rate": best.get("win_rate_result_positive", ""),
            "best_profile_trades_per_calendar_day": best.get("trades_per_calendar_day_true", ""),
            "best_profile_rows_replayed": best.get("rows_replayed", ""),
            "family_note": note,
        })

        overlap_rows.append({
            "entry_family_key": family_key,
            "candidate_group_id": group,
            "feature_column": feature,
            "rule_expression_preview": expr,
            "direction": direction,
            "profile_count": len(profiles),
            "profiles": ";".join(profiles),
            "unique_entry_times": unique_entry,
            "profile_level_rows": profile_level_rows,
            "max_profiles_same_entry_time": max_profiles_same_entry,
            "entry_times_with_multiple_profiles": multi_entry_times,
            "overlap_note": note,
        })

    family_rows.sort(key=lambda r: (profit_factor_sort_value(str(r.get("best_profile_profit_factor", ""))), float(r.get("best_profile_win_rate") or 0.0), float(r.get("best_profile_trades_per_calendar_day") or 0.0)), reverse=True)
    return family_rows, overlap_rows


def decision_rows(
    selected_root: Path,
    root_reason: str,
    status: str,
    plan_rows: int,
    candidate_metrics: Sequence[dict[str, Any]],
    family_metrics: Sequence[dict[str, Any]],
    parse_errors: Sequence[str],
) -> list[dict[str, Any]]:
    candidates_ge_2 = sum(1 for r in candidate_metrics if float(r.get("trades_per_calendar_day_true", 0.0) or 0.0) >= 2.0)
    families_ge_2 = sum(1 for r in family_metrics if float(r.get("unique_entry_times_per_calendar_day_true", 0.0) or 0.0) >= 2.0)
    return [
        {"decision_key": "selected_gold_v3_output_root", "value": str(selected_root), "detail": root_reason},
        {"decision_key": "status", "value": status, "detail": "audit-only replay execution status"},
        {"decision_key": "stage14_approved_plan_rows", "value": plan_rows, "detail": "expected 7 from Stage 14 approval"},
        {"decision_key": "candidate_metric_rows", "value": len(candidate_metrics), "detail": "must equal approved plan rows"},
        {"decision_key": "approved_entry_family_count", "value": len(family_metrics), "detail": "h1_atr56 profiles are not independent entry ideas"},
        {"decision_key": "parse_error_rows", "value": len(parse_errors), "detail": "; ".join(parse_errors[:10])},
        {"decision_key": "candidates_meeting_2_trades_per_calendar_day_true", "value": candidates_ge_2, "detail": "row-level Stage05 replay frequency"},
        {"decision_key": "families_meeting_2_unique_entries_per_calendar_day_true", "value": families_ge_2, "detail": "family-level unique entry-time frequency"},
        {"decision_key": "replay_executed", "value": status == READY_STATUS, "detail": "audit-only replay only; not live replay"},
        {"decision_key": "final_candidate_approval", "value": False, "detail": "blocked by policy"},
        {"decision_key": "threshold_finalization", "value": False, "detail": "blocked by policy"},
        {"decision_key": "model_training", "value": False, "detail": "blocked by policy"},
        {"decision_key": "signals_generated", "value": False, "detail": "blocked by policy"},
        {"decision_key": "zip_output_created", "value": False, "detail": "disabled"},
        {"decision_key": "external_actions", "value": False, "detail": "Discord/MT5/AI/live all OFF"},
        {"decision_key": "quarantined_legacy_artifacts_read", "value": False, "detail": "GOLD V2 / old GOLD / DISC8 not read or used"},
    ]


def blocker_rows(
    stage14_ok: bool,
    stage05_ok: bool,
    replay_plan_ok: bool,
    feature_source_ok: bool,
    parse_errors: Sequence[str],
    metrics_ok: bool,
) -> list[dict[str, Any]]:
    return [
        {"blocker_id": "G3-15-001", "blocker_name": "stage-14 approved replay plan", "status": "CLOSED" if stage14_ok and replay_plan_ok else "OPEN_BLOCKER", "detail": "Stage 14 READY and approved replay-plan preview rows present"},
        {"blocker_id": "G3-15-002", "blocker_name": "stage-05 replay source", "status": "CLOSED" if stage05_ok else "OPEN_BLOCKER", "detail": "Stage 05 label-feature join READY; no V2/old GOLD/DISC8 source used"},
        {"blocker_id": "G3-15-003", "blocker_name": "feature columns", "status": "CLOSED" if feature_source_ok else "OPEN_BLOCKER", "detail": "all replay-plan feature columns are present in Stage 05 join rows"},
        {"blocker_id": "G3-15-004", "blocker_name": "rule parsing", "status": "CLOSED" if not parse_errors else "OPEN_BLOCKER", "detail": "all Stage 14 rule expressions parsed" if not parse_errors else "; ".join(parse_errors[:10])},
        {"blocker_id": "G3-15-005", "blocker_name": "audit-only replay metrics", "status": "CLOSED" if metrics_ok else "OPEN_BLOCKER", "detail": "candidate/family metrics and trade ledger written" if metrics_ok else "metrics incomplete"},
        {"blocker_id": "G3-15-006", "blocker_name": "final approval", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "Stage 15 does not approve final candidates"},
        {"blocker_id": "G3-15-007", "blocker_name": "threshold finalization", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "Stage 15 does not finalize thresholds"},
        {"blocker_id": "G3-15-008", "blocker_name": "model training", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "Stage 15 does not train models"},
        {"blocker_id": "G3-15-009", "blocker_name": "signal/live", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "signal generation/live hook/live evaluator/final signal remain OFF"},
        {"blocker_id": "G3-15-010", "blocker_name": "zip output", "status": "CLOSED_DISABLED", "detail": "ZIP output disabled"},
        {"blocker_id": "G3-15-011", "blocker_name": "external actions", "status": "CLOSED", "detail": "Discord/MT5/AI API/live integrations remain OFF"},
        {"blocker_id": "G3-15-012", "blocker_name": "quarantined legacy artifacts", "status": "CLOSED", "detail": "GOLD V2 / old GOLD / DISC8 remain quarantined and are not read"},
    ]


def report(summary: dict[str, Any], candidate_metrics: Sequence[dict[str, Any]], family_metrics: Sequence[dict[str, Any]], blockers: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# GOLD V3 15 audit-only replay execution report",
        "",
        f"Created UTC: `{summary.get('created_at_utc', '')}`",
        f"Status: `{summary.get('status', '')}`",
        "",
        "## Scope",
        "",
        "This stage executed audit-only row-level replay from Stage 14 approved replay-plan rows against GOLD V3 Stage 05 label-feature join rows.",
        "",
        "No final candidate approval, threshold finalization, model training, signal generation, ZIP output, AI API call, Discord notification, MT5 order, live hook, live evaluator, or final signal action was performed.",
        "",
        "## Counts",
        "",
    ]
    for key in [
        "stage14_replay_plan_rows",
        "approved_replay_plan_rows",
        "stage05_join_rows",
        "candidate_metric_rows",
        "family_metric_rows",
        "trade_ledger_rows",
        "monthly_metric_rows",
        "parse_error_rows",
        "candidates_meeting_2_trades_per_calendar_day_true",
        "families_meeting_2_unique_entries_per_calendar_day_true",
    ]:
        lines.append(f"- {key}: `{summary.get(key, '')}`")

    lines += [
        "",
        "## Candidate metrics",
        "",
        md_table(candidate_metrics, [
            "source_rank",
            "candidate_group_id",
            "profile_id",
            "feature_column",
            "rows_replayed",
            "trades_per_calendar_day_true",
            "win_rate_result_positive",
            "profit_factor",
            "max_drawdown_usd",
            "sum_result_usd",
        ], limit=40),
        "",
        "## Family metrics",
        "",
        md_table(family_metrics, [
            "candidate_group_id",
            "profile_count",
            "profiles",
            "unique_entry_times_per_calendar_day_true",
            "best_profile_by_profit_factor",
            "best_profile_profit_factor",
            "best_profile_win_rate",
            "family_note",
        ], limit=40),
        "",
        "## Blockers",
        "",
        md_table(blockers, BLOCKER_FIELDS, limit=80),
        "",
        "## Safety",
        "",
        "`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` allowed this audit-only replay only. The result is not final approval and not live approval.",
        "",
        "GOLD V2, old GOLD, and DISC8 artifacts were not read or used.",
        "",
        "`GROUP_H1_ATR56_HIGH_VOL` rows share the same h1_atr56 entry family and are interpreted as TP/SL/horizon profile comparisons, not independent entry ideas.",
        "",
    ]
    return "\n".join(lines)


def write_all_outputs(
    output_dir: Path,
    inventory: Sequence[dict[str, Any]],
    candidate_metrics: Sequence[dict[str, Any]],
    family_metrics: Sequence[dict[str, Any]],
    ledger_rows: Sequence[dict[str, Any]],
    monthly_rows: Sequence[dict[str, Any]],
    overlap_rows: Sequence[dict[str, Any]],
    decisions: Sequence[dict[str, Any]],
    blockers: Sequence[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "gold_v3_15_input_inventory.csv", inventory, INPUT_INVENTORY_FIELDS)
    write_csv(output_dir / "gold_v3_15_replay_candidate_metrics.csv", candidate_metrics, CANDIDATE_METRIC_FIELDS)
    write_csv(output_dir / "gold_v3_15_replay_family_metrics.csv", family_metrics, FAMILY_METRIC_FIELDS)
    ledger_fields = list(dict.fromkeys(LEDGER_PREFIX_FIELDS + REQUIRED_BASE_COLS + OPTIONAL_LEDGER_COLS + sorted({str(row.get("feature_column", "")) for row in ledger_rows if str(row.get("feature_column", "")).strip()})))
    write_csv(output_dir / "gold_v3_15_replay_trade_ledger.csv", ledger_rows, ledger_fields)
    write_csv(output_dir / "gold_v3_15_replay_monthly_metrics.csv", monthly_rows, MONTHLY_FIELDS)
    write_csv(output_dir / "gold_v3_15_replay_overlap_audit.csv", overlap_rows, OVERLAP_FIELDS)
    write_csv(output_dir / "gold_v3_15_decision_matrix.csv", decisions, DECISION_FIELDS)
    write_csv(output_dir / "gold_v3_15_blocker_matrix.csv", blockers, BLOCKER_FIELDS)
    write_json(output_dir / "gold_v3_15_summary.json", summary)
    (output_dir / "GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md").write_text(report(summary, candidate_metrics, family_metrics, blockers), encoding="utf-8")


def empty_summary(selected_root: Path, root_reason: str, status: str, blocked_reason: str) -> dict[str, Any]:
    return {
        "created_at_utc": utc_now(),
        "step": STEP,
        "status": status,
        "blocked_reason": blocked_reason,
        "selected_gold_v3_output_root": str(selected_root),
        "path_resolution_note": root_reason,
        "stage14_status": "",
        "stage05_status": "",
        "stage14_replay_plan_rows": 0,
        "approved_replay_plan_rows": 0,
        "stage05_join_rows": 0,
        "candidate_metric_rows": 0,
        "family_metric_rows": 0,
        "trade_ledger_rows": 0,
        "monthly_metric_rows": 0,
        "parse_error_rows": 0,
        "audit_only_replay_executed": False,
        "replay_executed": False,
        "true_metric_source": "GOLD V3 Stage05 label-feature join rows",
        **FALSE_FLAGS,
    }


def run(repo_root: Path) -> int:
    repo_root = repo_root.resolve()
    selected_root, root_reason = select_v3_root(repo_root)
    stage14_dir = selected_root / UPSTREAM14_NAME
    stage05_dir = selected_root / UPSTREAM05_NAME
    output_dir = selected_root / OUT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "stage14_summary": stage14_dir / "gold_v3_14_summary.json",
        "stage14_replay_plan_preview": stage14_dir / "gold_v3_14_replay_plan_preview.csv",
        "stage14_human_decision_intake": stage14_dir / "gold_v3_14_human_decision_intake_template.csv",
        "stage05_summary": stage05_dir / "gold_v3_05_summary.json",
        "stage05_label_feature_join_rows": stage05_dir / "gold_v3_05_label_feature_join_rows.csv",
        "stage05_walkforward_fold_matrix": stage05_dir / "gold_v3_05_walkforward_fold_matrix.csv",
    }
    inventory = inventory_rows([
        ("gold_v3_14_summary", paths["stage14_summary"], True),
        ("gold_v3_14_replay_plan_preview", paths["stage14_replay_plan_preview"], True),
        ("gold_v3_14_human_decision_intake", paths["stage14_human_decision_intake"], True),
        ("gold_v3_05_summary", paths["stage05_summary"], True),
        ("gold_v3_05_label_feature_join_rows", paths["stage05_label_feature_join_rows"], True),
        ("gold_v3_05_walkforward_fold_matrix", paths["stage05_walkforward_fold_matrix"], True),
    ])

    missing = [r["input_label"] for r in inventory if r["required"] and not r["exists"]]
    if missing:
        reason = "missing required inputs: " + ", ".join(map(str, missing))
        blockers = blocker_rows(False, False, False, False, [reason], False)
        decisions = decision_rows(selected_root, root_reason, BLOCKED_STATUS, 0, [], [], [reason])
        summary = empty_summary(selected_root, root_reason, BLOCKED_STATUS, reason)
        write_all_outputs(output_dir, inventory, [], [], [], [], [], decisions, blockers, summary)
        print("[GOLD_V3_15] BLOCKED: " + reason)
        return 2

    s14 = read_json(paths["stage14_summary"])
    s05 = read_json(paths["stage05_summary"])
    stage14_status = str(s14.get("status", ""))
    stage05_status = str(s05.get("status", ""))
    stage14_ok = stage14_status == UPSTREAM14_READY_STATUS
    stage05_ok = stage05_status == UPSTREAM05_READY_STATUS

    replay_plan = read_csv(paths["stage14_replay_plan_preview"])
    approved_plan = [r for r in replay_plan if str(r.get("human_decision", "")).strip() == APPROVE_FOR_REPLAY]
    replay_plan_ok = stage14_ok and len(approved_plan) > 0

    feature_columns = sorted({str(r.get("feature_column", "")).strip() for r in approved_plan if str(r.get("feature_column", "")).strip()})
    data, missing_cols = load_stage05_join_rows(paths["stage05_label_feature_join_rows"], feature_columns)
    feature_source_ok = stage05_ok and not missing_cols and not data.empty

    if not (stage14_ok and stage05_ok and replay_plan_ok and feature_source_ok):
        reasons = []
        if not stage14_ok:
            reasons.append(f"stage14 status is not READY: {stage14_status}")
        if not stage05_ok:
            reasons.append(f"stage05 status is not READY: {stage05_status}")
        if not replay_plan_ok:
            reasons.append("approved replay-plan rows are missing")
        if missing_cols:
            reasons.append("missing Stage05 columns: " + ", ".join(missing_cols))
        if data.empty:
            reasons.append("Stage05 join rows could not be loaded or are empty")
        reason = "; ".join(reasons) or "input checks failed"
        blockers = blocker_rows(stage14_ok, stage05_ok, replay_plan_ok, feature_source_ok, [reason], False)
        decisions = decision_rows(selected_root, root_reason, BLOCKED_STATUS, len(approved_plan), [], [], [reason])
        summary = empty_summary(selected_root, root_reason, BLOCKED_STATUS, reason)
        summary.update({
            "stage14_status": stage14_status,
            "stage05_status": stage05_status,
            "stage14_replay_plan_rows": len(replay_plan),
            "approved_replay_plan_rows": len(approved_plan),
            "stage05_join_rows": int(s05.get("joined_rows", 0) or len(data)),
        })
        write_all_outputs(output_dir, inventory, [], [], [], [], [], decisions, blockers, summary)
        print("[GOLD_V3_15] BLOCKED: " + reason)
        return 2

    candidate_metrics, ledger_rows, monthly_rows, _, parse_errors = build_replay(approved_plan, data)
    family_metrics, overlap_rows = build_family_metrics(candidate_metrics, ledger_rows)
    metrics_ok = len(candidate_metrics) == len(approved_plan) and not parse_errors

    status = READY_STATUS if metrics_ok else BLOCKED_STATUS
    blockers = blocker_rows(stage14_ok, stage05_ok, replay_plan_ok, feature_source_ok, parse_errors, metrics_ok)
    decisions = decision_rows(selected_root, root_reason, status, len(approved_plan), candidate_metrics, family_metrics, parse_errors)

    candidates_ge_2 = sum(1 for r in candidate_metrics if float(r.get("trades_per_calendar_day_true", 0.0) or 0.0) >= 2.0)
    families_ge_2 = sum(1 for r in family_metrics if float(r.get("unique_entry_times_per_calendar_day_true", 0.0) or 0.0) >= 2.0)

    top = candidate_metrics[0] if candidate_metrics else {}
    summary = {
        "created_at_utc": utc_now(),
        "step": STEP,
        "status": status,
        "blocked_reason": "" if status == READY_STATUS else "; ".join(parse_errors),
        "selected_gold_v3_output_root": str(selected_root),
        "path_resolution_note": root_reason,
        "stage14_status": stage14_status,
        "stage05_status": stage05_status,
        "stage14_replay_plan_rows": len(replay_plan),
        "approved_replay_plan_rows": len(approved_plan),
        "expected_approved_replay_plan_rows": EXPECTED_APPROVED_ROWS,
        "stage05_join_rows": int(s05.get("joined_rows", 0) or len(data)),
        "candidate_metric_rows": len(candidate_metrics),
        "family_metric_rows": len(family_metrics),
        "expected_approved_entry_family_count": EXPECTED_APPROVED_ENTRY_FAMILIES,
        "trade_ledger_rows": len(ledger_rows),
        "monthly_metric_rows": len(monthly_rows),
        "overlap_audit_rows": len(overlap_rows),
        "parse_error_rows": len(parse_errors),
        "candidates_meeting_2_trades_per_calendar_day_true": candidates_ge_2,
        "families_meeting_2_unique_entries_per_calendar_day_true": families_ge_2,
        "top_candidate_by_pf_then_winrate": top,
        "audit_only_replay_executed": status == READY_STATUS,
        "replay_executed": status == READY_STATUS,
        "replay_execution_scope": "audit-only row-level replay from Stage05 label-feature join; not live replay",
        "true_metric_source": "GOLD V3 Stage05 label-feature join rows",
        "final_candidate_approval": False,
        "threshold_finalization": False,
        "model_training": False,
        "signals_generated": False,
        "zip_output_created": False,
        "old_gold_disc8_quarantined": True,
        **FALSE_FLAGS,
    }

    write_all_outputs(output_dir, inventory, candidate_metrics, family_metrics, ledger_rows, monthly_rows, overlap_rows, decisions, blockers, summary)
    print(json.dumps({
        "status": status,
        "candidate_metric_rows": len(candidate_metrics),
        "family_metric_rows": len(family_metrics),
        "trade_ledger_rows": len(ledger_rows),
        "candidates_meeting_2_trades_per_calendar_day_true": candidates_ge_2,
        "families_meeting_2_unique_entries_per_calendar_day_true": families_ge_2,
        "output_dir": str(output_dir),
        "final_candidate_approval": False,
        "signals_generated": False,
        "zip_output_created": False,
    }, ensure_ascii=True, indent=2))
    return 0 if status == READY_STATUS else 2


def write_exception(repo_root: Path, exc: BaseException) -> None:
    try:
        selected_root, root_reason = select_v3_root(repo_root.resolve())
    except Exception:
        selected_root, root_reason = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3", "exception_fallback_repo_root_files"
    output_dir = selected_root / OUT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    reason = f"{exc.__class__.__name__}: {exc}"
    inventory: list[dict[str, Any]] = []
    blockers = blocker_rows(False, False, False, False, [reason], False)
    decisions = decision_rows(selected_root, root_reason, EXCEPTION_STATUS, 0, [], [], [reason])
    summary = empty_summary(selected_root, root_reason, EXCEPTION_STATUS, reason)
    write_all_outputs(output_dir, inventory, [], [], [], [], [], decisions, blockers, summary)
    (output_dir / "gold_v3_15_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_default()
    try:
        return run(repo_root)
    except Exception as exc:
        write_exception(repo_root, exc)
        print("[GOLD_V3_15] EXCEPTION. See selected FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_exception.txt", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
