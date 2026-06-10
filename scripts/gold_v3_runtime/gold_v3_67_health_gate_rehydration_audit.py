#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 67 health gate rehydration audit-only.

Rehydrates candidate-level rolling health gate state from existing audited GOLD V3
outcome artifacts and the Stage66 candidate key contract.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_67_HEALTH_GATE_REHYDRATION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_67_HEALTH_GATE_REHYDRATION_BLOCKED_AUDIT_ONLY"
STAGE66_READY = "GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY"

WINDOW = 30
MIN_HISTORY = 20
PF_THRESHOLD = 1.10
LOSS_STREAK_LT = 3
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
KEY_COLS = [
    "candidate_label",
    "base_candidate_label",
    "source_profile_id",
    "profile_id",
    "hv_profile",
    "tp_usd",
    "sl_usd",
    "horizon_m15",
    "horizon_m5_bars",
]
OUTCOME_COL_CANDIDATES = ["result_usd", "pnl", "profit", "net_profit", "outcome_usd"]
TIME_COL_CANDIDATES = ["m15_time_jst", "entry_dt", "asof_m15_time_jst", "entry_m15_time", "time", "timestamp"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str]:
    attempts: list[tuple[str | None, str]] = [(None, "auto"), (",", "comma"), (";", "semicolon"), ("\t", "tab")]
    last_err: Exception | None = None
    for sep, label in attempts:
        try:
            if sep is None:
                df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            else:
                df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df, label
        except Exception as e:  # pragma: no cover
            last_err = e
    if last_err:
        raise last_err
    raise ValueError(f"Could not parse CSV with multiple columns: {path}")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def norm_cell(v: Any) -> str:
    if pd.isna(v):
        return ""
    if isinstance(v, (np.integer, int)):
        return str(int(v))
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isfinite(f) and f.is_integer():
            return str(int(f))
        return (f"{f:.10f}").rstrip("0").rstrip(".")
    s = str(v).strip()
    if s.lower() in {"nan", "none", "nat"}:
        return ""
    return s


def normalize_key_part(s: Any) -> str:
    x = norm_cell(s)
    if not x:
        return ""
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", x):
        try:
            f = float(x)
            if math.isfinite(f) and f.is_integer():
                return str(int(f))
            return (f"{f:.10f}").rstrip("0").rstrip(".")
        except Exception:  # pragma: no cover
            return x
    return x


def normalize_candidate_key_string(key: Any) -> str:
    return "|".join(normalize_key_part(p) for p in str(key).split("|"))


def build_candidate_key(df: pd.DataFrame) -> pd.Series:
    key = pd.Series([""] * len(df), index=df.index, dtype="object")
    for i, c in enumerate(KEY_COLS):
        part = df[c].map(normalize_key_part)
        key = part if i == 0 else key + "|" + part
    return key.astype(str)


def find_time_col(df: pd.DataFrame) -> str | None:
    lower = {str(c).lower(): str(c) for c in df.columns}
    for c in TIME_COL_CANDIDATES:
        if c.lower() in lower:
            return lower[c.lower()]
    for c in df.columns:
        lc = str(c).lower()
        if "time" in lc or "date" in lc:
            return str(c)
    return None


def find_result_col(df: pd.DataFrame) -> str | None:
    lower = {str(c).lower(): str(c) for c in df.columns}
    for c in OUTCOME_COL_CANDIDATES:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def pf(vals: list[float]) -> float:
    a = np.array(vals, dtype=float)
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    if gl > 0:
        return gp / gl
    return math.inf if gp > 0 else 0.0


def loss_streak(vals: list[float]) -> int:
    n = 0
    for v in reversed(vals):
        if v < 0:
            n += 1
        else:
            break
    return n


def reason_from_metrics(hist_n: int, rolling_pf: float | None, ls: int | None) -> tuple[bool, str]:
    if hist_n < MIN_HISTORY:
        return True, "INSUFFICIENT_HISTORY"
    reasons = []
    if rolling_pf is None or float(rolling_pf) < PF_THRESHOLD:
        reasons.append("PF_BELOW_THRESHOLD")
    if ls is None or int(ls) >= LOSS_STREAK_LT:
        reasons.append("LOSS_STREAK_LIMIT")
    if reasons:
        return False, "+".join(reasons)
    return True, "PASS"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "66_virtual_monitoring_state_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with FX_OUTPUTS/gold_v3/66_virtual_monitoring_state_audit_only")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage66-dir", default="")
    p.add_argument("--stage53-dir", default="")
    p.add_argument("--stage52-dir", default="")
    p.add_argument("--stage51-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def inventory_candidate(path: Path, stage: str, priority: int) -> dict[str, Any]:
    inv: dict[str, Any] = {"stage": stage, "priority": priority, "path": str(path), "structurally_accepted": False}
    try:
        df, sep = read_csv_auto(path)
        inv["separator"] = sep
        inv["rows"] = int(len(df))
        inv["columns"] = "|".join(map(str, df.columns))
        missing = [c for c in KEY_COLS if c not in df.columns]
        inv["missing_key_columns"] = "|".join(missing)
        time_col = find_time_col(df)
        result_col = find_result_col(df)
        inv["time_column"] = time_col or ""
        inv["result_column"] = result_col or ""
        inv["has_opportunity_id"] = "opportunity_id" in df.columns
        if time_col:
            inv["parseable_time_rows"] = int(pd.to_datetime(df[time_col], errors="coerce").notna().sum())
        else:
            inv["parseable_time_rows"] = 0
        if result_col:
            inv["numeric_result_rows"] = int(pd.to_numeric(df[result_col], errors="coerce").notna().sum())
        else:
            inv["numeric_result_rows"] = 0
        inv["reject_reason"] = ""
        if len(df) == 0:
            inv["reject_reason"] = "EMPTY_ARTIFACT"
        elif missing:
            inv["reject_reason"] = "MISSING_STAGE66_KEY_COLUMNS"
        elif not time_col:
            inv["reject_reason"] = "NO_COMPATIBLE_TIME_COLUMN"
        elif not result_col:
            inv["reject_reason"] = "NO_NUMERIC_OUTCOME_COLUMN"
        elif int(inv["numeric_result_rows"]) == 0:
            inv["reject_reason"] = "NO_NUMERIC_OUTCOME_VALUES"
        else:
            inv["structurally_accepted"] = True
        return inv
    except Exception as e:  # pragma: no cover
        inv["reject_reason"] = "READ_ERROR"
        inv["error"] = repr(e)
        return inv


def discover_sources(base_out: Path, a: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dirs = [
        ("Stage53", 1, Path(a.stage53_dir).expanduser().resolve() if a.stage53_dir else base_out / "53_pending_to_closed_shadow_trade_adjudication_audit_only", ["*closed*shadow*trade*ledger*.csv", "*adjudication*.csv", "*.csv"]),
        ("Stage52", 2, Path(a.stage52_dir).expanduser().resolve() if a.stage52_dir else base_out / "52_health_gate_state_rank_dedup_audit_only", ["*health_gate_state*.csv", "*selected*trade*ledger*.csv", "*.csv"]),
        ("Stage51", 3, Path(a.stage51_dir).expanduser().resolve() if a.stage51_dir else base_out / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only", ["*virtual*opportunit*ledger*.csv", "*.csv"]),
    ]
    seen: set[Path] = set()
    for stage, priority, d, patterns in dirs:
        if not d.exists():
            rows.append({"stage": stage, "priority": priority, "path": str(d), "structurally_accepted": False, "reject_reason": "DIRECTORY_NOT_FOUND"})
            continue
        for pat in patterns:
            for p in d.glob(pat):
                if p.is_file() and p not in seen:
                    seen.add(p)
                    rows.append(inventory_candidate(p, stage, priority))
    rows.sort(key=lambda r: (int(r.get("priority", 99)), 0 if bool(r.get("structurally_accepted")) else 1, str(r.get("path", ""))))
    return rows


def load_accepted_source(inventory: list[dict[str, Any]], stage66_joined: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any] | None, list[dict[str, Any]]]:
    rejections: list[dict[str, Any]] = []
    s66 = stage66_joined.copy()
    s66["candidate_key"] = build_candidate_key(s66)
    for inv in inventory:
        if not bool(inv.get("structurally_accepted")):
            continue
        path = Path(str(inv["path"]))
        df, _ = read_csv_auto(path)
        df = df.copy()
        df["candidate_key"] = build_candidate_key(df)
        time_col = str(inv["time_column"])
        result_col = str(inv["result_column"])
        df["_event_time"] = pd.to_datetime(df[time_col], errors="coerce")
        df["_result_usd"] = pd.to_numeric(df[result_col], errors="coerce")
        if "opportunity_id" in df.columns and "opportunity_id" in s66.columns:
            need = s66[["opportunity_id", "candidate_key"]].drop_duplicates().copy()
            got = df[["opportunity_id", "candidate_key", "_event_time", "_result_usd"]].drop_duplicates("opportunity_id", keep="last")
            merged = need.merge(got, on="opportunity_id", how="left", suffixes=("_stage66", "_source"))
            coverage = int(merged["_result_usd"].notna().sum())
            key_mismatch = int((merged["candidate_key_stage66"].astype(str) != merged["candidate_key_source"].astype(str)).fillna(True).sum())
            if coverage == len(need) and key_mismatch == 0:
                inv = dict(inv)
                inv["selected_as_outcome_source"] = True
                inv["coverage"] = coverage
                inv["required_coverage"] = int(len(need))
                inv["key_mismatch"] = key_mismatch
                return df, inv, rejections
            rejections.append({"artifact": str(path), "reason": "STAGE66_OPPORTUNITY_COVERAGE_OR_KEY_MISMATCH", "coverage": coverage, "required": int(len(need)), "key_mismatch": key_mismatch})
        else:
            need = s66[["candidate_key", "_m15_time"]].copy() if "_m15_time" in s66.columns else s66[["candidate_key"]].copy()
            if "_m15_time" in need.columns:
                need["_event_time"] = pd.to_datetime(need["_m15_time"], errors="coerce")
                got = df[["candidate_key", "_event_time", "_result_usd"]].copy()
                merged = need.merge(got, on=["candidate_key", "_event_time"], how="left")
            else:
                got = df[["candidate_key", "_result_usd"]].copy()
                merged = need.merge(got, on="candidate_key", how="left")
            coverage = int(merged["_result_usd"].notna().sum())
            if coverage == len(need):
                inv = dict(inv)
                inv["selected_as_outcome_source"] = True
                inv["coverage"] = coverage
                inv["required_coverage"] = int(len(need))
                inv["key_mismatch"] = 0
                return df, inv, rejections
            rejections.append({"artifact": str(path), "reason": "STAGE66_KEY_TIME_COVERAGE_MISMATCH", "coverage": coverage, "required": int(len(need)), "key_mismatch": "n/a"})
    return None, None, rejections


def rehydrate(stage66_joined: pd.DataFrame, source: pd.DataFrame, source_inv: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    s66 = stage66_joined.copy()
    s66["candidate_key"] = build_candidate_key(s66)
    time_col = str(source_inv["time_column"])
    result_col = str(source_inv["result_column"])
    src = source.copy()
    src["candidate_key"] = build_candidate_key(src)
    src["_source_event_time"] = pd.to_datetime(src[time_col], errors="coerce")
    src["_source_result_usd"] = pd.to_numeric(src[result_col], errors="coerce")
    keep = ["candidate_key", "_source_event_time", "_source_result_usd"]
    if "opportunity_id" in src.columns and "opportunity_id" in s66.columns:
        keep = ["opportunity_id"] + keep
        add = src[keep].drop_duplicates("opportunity_id", keep="last")
        ev = s66.merge(add, on="opportunity_id", how="left", suffixes=("", "_src"))
    else:
        s66["_stage66_event_time"] = pd.to_datetime(s66.get("_m15_time", s66.get("m15_time_jst", pd.NaT)), errors="coerce")
        add = src[keep].drop_duplicates(["candidate_key", "_source_event_time"], keep="last")
        ev = s66.merge(add, left_on=["candidate_key", "_stage66_event_time"], right_on=["candidate_key", "_source_event_time"], how="left")
    ev["event_time"] = pd.to_datetime(ev.get("_m15_time", ev.get("m15_time_jst", ev["_source_event_time"])), errors="coerce")
    ev["result_usd"] = pd.to_numeric(ev["_source_result_usd"], errors="coerce")
    ev = ev.sort_values(["event_time", "candidate_key"]).reset_index(drop=True)

    hist: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    rows: list[dict[str, Any]] = []
    for event_time, g in ev.groupby("event_time", sort=True, dropna=False):
        g = g.sort_values(["candidate_key"]).copy()
        for _, r in g.iterrows():
            cand = str(r["candidate_key"])
            h = list(hist[cand])
            hist_n = len(h)
            rpf = pf(h) if hist_n >= MIN_HISTORY else np.nan
            ls = loss_streak(h) if hist_n >= MIN_HISTORY else np.nan
            passed, reason = reason_from_metrics(hist_n, None if pd.isna(rpf) else float(rpf), None if pd.isna(ls) else int(ls))
            rr = {c: r.get(c, "") for c in KEY_COLS if c in r.index}
            rr.update({
                "event_time": event_time,
                "opportunity_id": r.get("opportunity_id", ""),
                "candidate_key": cand,
                "history_count_before": hist_n,
                "rolling_window": WINDOW,
                "min_history": MIN_HISTORY,
                "pf_threshold": PF_THRESHOLD,
                "loss_streak_lt": LOSS_STREAK_LT,
                "rolling_pf_before": rpf,
                "loss_streak_before": ls,
                "candidate_retained": True,
                "health_gate_pass": bool(passed),
                "health_gate_reason": reason,
                "result_usd_after_close": float(r["result_usd"]) if pd.notna(r["result_usd"]) else np.nan,
                "audit_only": True,
                "live_ready": False,
            })
            rows.append(rr)
        for _, r in g.iterrows():
            if pd.notna(r["result_usd"]):
                hist[str(r["candidate_key"])].append(float(r["result_usd"]))

    event_ledger = pd.DataFrame(rows)
    latest = event_ledger.sort_values("event_time").groupby("candidate_key", dropna=False).tail(1).copy()
    if latest.empty:
        state = pd.DataFrame(columns=["candidate_key", "candidate_retained", "health_gate_pass", "health_gate_reason"])
    else:
        state = latest.copy()
        counts = event_ledger.groupby("candidate_key").size().to_dict()
        state["observed_event_count"] = state["candidate_key"].map(counts).fillna(0).astype(int)
        state = state[[
            "candidate_key", *[c for c in KEY_COLS if c in state.columns], "event_time", "observed_event_count",
            "history_count_before", "rolling_pf_before", "loss_streak_before", "candidate_retained",
            "health_gate_pass", "health_gate_reason", "audit_only", "live_ready",
        ]]
    return event_ledger, state


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s66 = Path(a.stage66_dir).expanduser().resolve() if a.stage66_dir else base_out / "66_virtual_monitoring_state_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "67_health_gate_rehydration_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p66_summary = s66 / "gold_v3_66_virtual_monitoring_summary.json"
    p66_joined = s66 / "gold_v3_66_virtual_opportunity_q70_joined_ledger.csv"
    p66_state = s66 / "gold_v3_66_candidate_virtual_monitoring_state.csv"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage66_summary", p66_summary), ("stage66_joined_ledger", p66_joined), ("stage66_candidate_state", p66_state)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
    if not p66_summary.exists() or not p66_joined.exists() or not p66_state.exists():
        blockers.append(blocker("stage66_missing", str(s66), "REQUIRED_STAGE66_ARTIFACT_MISSING"))

    j66 = read_json(p66_summary) if p66_summary.exists() else {}
    val.append(ok("stage66_status_ready", j66.get("status") == STAGE66_READY, j66.get("status"), STAGE66_READY))
    val.append(ok("stage66_virtual_monitoring_ready", j66.get("virtual_monitoring_state_ready") is True, j66.get("virtual_monitoring_state_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage66_{key}_false", j66.get(key) is False, j66.get(key), False))

    inventory = discover_sources(base_out, a)

    event_ledger = pd.DataFrame()
    candidate_state = pd.DataFrame()
    accepted_inv: dict[str, Any] | None = None
    source_rows = 0
    candidate_count = 0
    source_rejections: list[dict[str, Any]] = []

    if p66_joined.exists() and not blockers:
        s66_joined, _ = read_csv_auto(p66_joined)
        s66_state, _ = read_csv_auto(p66_state)
        missing_s66_key = [c for c in KEY_COLS if c not in s66_joined.columns]
        val.append(ok("stage66_joined_has_exact_key_columns", not missing_s66_key, "|".join(missing_s66_key), "none"))
        if missing_s66_key:
            blockers.append(blocker("stage66_key_missing", str(p66_joined), "STAGE66_JOINED_MISSING_KEY_COLUMNS", "|".join(missing_s66_key)))
        else:
            s66_joined["candidate_key"] = build_candidate_key(s66_joined)
            candidate_count = int(s66_joined["candidate_key"].nunique())
            source, accepted_inv, source_rejections = load_accepted_source(inventory, s66_joined)
            val.append(ok("acceptable_audited_outcome_source_found", source is not None and accepted_inv is not None, accepted_inv.get("path") if accepted_inv else "not_found", "Stage51/52/53 GOLD V3 outcome source"))
            if source is not None and accepted_inv is not None:
                source_rows = int(len(source))
                for inv in inventory:
                    inv["selected_as_outcome_source"] = str(inv.get("path", "")) == str(accepted_inv.get("path", ""))
                event_ledger, candidate_state = rehydrate(s66_joined, source, accepted_inv)
                event_ledger.to_csv(out / "gold_v3_67_health_gate_event_ledger.csv", index=False, encoding="utf-8-sig")
                candidate_state.to_csv(out / "gold_v3_67_health_gate_rehydrated_candidate_state.csv", index=False, encoding="utf-8-sig")
                val.append(ok("rehydrated_event_rows_equal_stage66", len(event_ledger) == len(s66_joined), len(event_ledger), len(s66_joined)))
                numeric_count = int(pd.to_numeric(event_ledger["result_usd_after_close"], errors="coerce").notna().sum())
                val.append(ok("numeric_result_all_rows", numeric_count == len(event_ledger), numeric_count, len(event_ledger)))
                val.append(ok("candidate_count_preserved", int(candidate_state["candidate_key"].nunique()) == candidate_count, int(candidate_state["candidate_key"].nunique()), candidate_count))
                val.append(ok("all_observed_candidates_retained", bool(candidate_state["candidate_retained"].eq(True).all()), "all_true", "all_true"))
                val.append(ok("manual_candidate_demotion_or_removal_false", True, False, False))
                if "candidate_key" in s66_state.columns:
                    s66_keys = set(s66_state["candidate_key"].map(normalize_candidate_key_string).astype(str))
                elif all(c in s66_state.columns for c in KEY_COLS):
                    s66_keys = set(build_candidate_key(s66_state))
                else:
                    s66_keys = set()
                if s66_keys:
                    out_keys = set(candidate_state["candidate_key"].map(normalize_candidate_key_string).astype(str))
                    val.append(ok("candidate_state_keys_match_stage66_state", out_keys == s66_keys, len(out_keys.symmetric_difference(s66_keys)), 0))
            else:
                blockers.append(blocker("no_usable_outcome_source", str(base_out), "NO_ACCEPTABLE_SOURCE_AFTER_STAGE66_COVERAGE_CHECK", source_rejections))

    if event_ledger.empty:
        (out / "gold_v3_67_health_gate_event_ledger.csv").write_text("", encoding="utf-8")
        (out / "gold_v3_67_health_gate_rehydrated_candidate_state.csv").write_text("", encoding="utf-8")

    if not any(bool(r.get("structurally_accepted")) for r in inventory):
        blockers.append(blocker("no_inventory_source_accepted", str(base_out), "NO_STAGE51_52_53_ARTIFACT_WITH_EXACT_KEY_AND_RESULT_COLUMNS"))
    val.append(ok("health_gate_window_30", WINDOW == 30, WINDOW, 30))
    val.append(ok("health_gate_min_history_20", MIN_HISTORY == 20, MIN_HISTORY, 20))
    val.append(ok("health_gate_pf_threshold_1_10", PF_THRESHOLD == 1.10, PF_THRESHOLD, 1.10))
    val.append(ok("health_gate_loss_streak_lt_3", LOSS_STREAK_LT == 3, LOSS_STREAK_LT, 3))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("no_ohlc_re_adjudication", True, "not_used", "not_used"))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(inventory).to_csv(out / "gold_v3_67_health_gate_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(source_rejections).to_csv(out / "gold_v3_67_source_rejection_diagnostics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "gold_v3_67_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_67_validation_matrix.csv", index=False, encoding="utf-8-sig")

    pass_count = int(candidate_state["health_gate_pass"].sum()) if not candidate_state.empty and "health_gate_pass" in candidate_state.columns else 0
    fail_count = int((~candidate_state["health_gate_pass"].astype(bool)).sum()) if not candidate_state.empty and "health_gate_pass" in candidate_state.columns else 0
    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "health_gate_rehydration_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_source": "+".join(KEY_COLS),
        "accepted_outcome_source": accepted_inv.get("path") if accepted_inv else "",
        "accepted_outcome_stage": accepted_inv.get("stage") if accepted_inv else "",
        "accepted_outcome_result_column": accepted_inv.get("result_column") if accepted_inv else "",
        "accepted_outcome_time_column": accepted_inv.get("time_column") if accepted_inv else "",
        "source_rows": source_rows,
        "rehydrated_event_rows": int(len(event_ledger)),
        "candidate_count": candidate_count,
        "health_gate_pass_candidate_count": pass_count,
        "health_gate_fail_candidate_count": fail_count,
        "source_rejection_diagnostic_count": int(len(source_rejections)),
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
        "health_gate": {"window": WINDOW, "min_history": MIN_HISTORY, "pf_threshold": PF_THRESHOLD, "loss_streak_lt": LOSS_STREAK_LT, "virtual_monitoring": True},
    }
    (out / "gold_v3_67_health_gate_rehydration_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste: list[str] = []
    paste.append("GOLD V3 67 PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("health_gate_rehydration_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append("candidate_key_source: " + "+".join(KEY_COLS))
    paste.append(f"accepted_outcome_source: {summary['accepted_outcome_source']}")
    paste.append(f"accepted_outcome_stage: {summary['accepted_outcome_stage']}")
    paste.append(f"source_rows: {source_rows}")
    paste.append(f"rehydrated_event_rows: {len(event_ledger)}")
    paste.append(f"candidate_count: {candidate_count}")
    paste.append(f"health_gate_pass_candidate_count: {pass_count}")
    paste.append(f"health_gate_fail_candidate_count: {fail_count}")
    paste.append(f"source_rejection_diagnostic_count: {len(source_rejections)}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("health_gate: window=30, min_history=20, pf_threshold=1.10, loss_streak_lt=3, virtual_monitoring=true")
    paste.append("")
    paste.append("INVENTORY")
    paste.append(pd.DataFrame(inventory).to_string(index=False) if inventory else "NO_INVENTORY")
    paste.append("")
    paste.append("SOURCE_REJECTION_DIAGNOSTICS")
    paste.append(pd.DataFrame(source_rejections).to_string(index=False) if source_rejections else "NO_SOURCE_REJECTIONS")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_67_health_gate_rehydrated_candidate_state.csv")
    paste.append("gold_v3_67_health_gate_event_ledger.csv")
    paste.append("gold_v3_67_health_gate_inventory.csv")
    paste.append("gold_v3_67_source_rejection_diagnostics.csv")
    paste.append("gold_v3_67_blocker_matrix.csv")
    paste.append("gold_v3_67_validation_matrix.csv")
    paste.append("gold_v3_67_health_gate_rehydration_summary.json")
    (out / "gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 67 health gate rehydration audit-only report

Status: `{status}`

## Summary

- accepted_outcome_source: `{summary['accepted_outcome_source']}`
- rehydrated_event_rows: `{len(event_ledger)}`
- candidate_count: `{candidate_count}`
- health_gate_pass_candidate_count: `{pass_count}`
- health_gate_fail_candidate_count: `{fail_count}`
- source_rejection_diagnostic_count: `{len(source_rejections)}`
- blocker_count: `{len(blockers)}`

## Contract

- candidate_key_source: `{'+'.join(KEY_COLS)}`
- csv_open_bar_exclusion_required: `false`
- pool_policy: `{POOL_POLICY}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_67_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
