#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_02B_LABEL_GRID_CONTRACT_AUDIT_ONLY"
OUT_NAME = "02b_label_grid_contract_audit_only"
EXPECTED_01B_STATUS = "GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY"
UNIT = "XAUUSD_GOLD_HASH_PRICE_DISTANCE_USD_NOT_PIPS"
SAME_BAR_PRIORITY = "SL_FIRST"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PROFILES = [
    {"profile_id": "USDPRICE_TP10_SL5_H28", "tp": 10.0, "sl": 5.0, "h": 28},
    {"profile_id": "USDPRICE_TP20_SL10_H28", "tp": 20.0, "sl": 10.0, "h": 28},
    {"profile_id": "USDPRICE_TP30_SL10_H32", "tp": 30.0, "sl": 10.0, "h": 32},
    {"profile_id": "USDPRICE_TP50_SL20_H48", "tp": 50.0, "sl": 20.0, "h": 48},
    {"profile_id": "USDPRICE_TP80_SL30_H64", "tp": 80.0, "sl": 30.0, "h": 64},
    {"profile_id": "USDPRICE_TP100_SL40_H96", "tp": 100.0, "sl": 40.0, "h": 96},
    {"profile_id": "USDPRICE_TP120_SL50_H96", "tp": 120.0, "sl": 50.0, "h": 96},
    {"profile_id": "USDPRICE_TP150_SL60_H128", "tp": 150.0, "sl": 60.0, "h": 128},
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def v3_output_root() -> Path:
    return files_root() / "FX_OUTPUTS" / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def upstream01b_dir() -> Path:
    return v3_output_root() / "01b_candle_gap_session_policy_audit"


def canonical_dir() -> Path:
    return v3_output_root() / "01_candle_normalization_time_audit" / "canonical_candles"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception:
        pass
    return x.isoformat() if hasattr(x, "isoformat") else x


def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(p: Path) -> dict[str, Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for p in paths:
        rows.append({"path": str(p), "filename": p.name, "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0, "sha256": sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def load_candles(tf: str) -> pd.DataFrame:
    p = canonical_dir() / f"gold_v3_gold_hash_2025_primary_{tf}.csv"
    df = pd.read_csv(p)
    df["t"] = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    return df


def profile_df() -> pd.DataFrame:
    rows = []
    for p in PROFILES:
        rows.append({
            "profile_id": p["profile_id"],
            "tp_price_distance_usd": p["tp"],
            "sl_price_distance_usd": p["sl"],
            "horizon_m15_bars": p["h"],
            "horizon_minutes": p["h"] * 15,
            "price_distance_unit": UNIT,
        })
    return pd.DataFrame(rows)


def build_base_entries(m15: pd.DataFrame, m5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m5_times = set(m5["t"].dropna())
    m5_open = dict(zip(m5["t"], m5["open"]))
    rows = []
    excl = []
    for _, r in m15.iterrows():
        feature_open = r["t"]
        if pd.isna(feature_open):
            excl.append({"feature_bar_open_utc": "", "entry_time_utc": "", "reason": "invalid_m15_time"})
            continue
        entry = feature_open + pd.Timedelta(minutes=15)
        if entry not in m5_times:
            excl.append({"feature_bar_open_utc": str(feature_open), "entry_time_utc": str(entry), "reason": "expected_session_or_market_stop_entry_exclusion"})
            continue
        rows.append({"feature_bar_open_utc": str(feature_open), "entry_time_utc": str(entry), "entry_price": float(m5_open[entry])})
    return pd.DataFrame(rows), pd.DataFrame(excl)


def expand_grid(base: pd.DataFrame, profiles: pd.DataFrame, m5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    last_m5 = m5["t"].max()
    rows = []
    excl = []
    for _, b in base.iterrows():
        entry = pd.to_datetime(b["entry_time_utc"], utc=True)
        entry_price = float(b["entry_price"])
        for _, p in profiles.iterrows():
            horizon_minutes = int(p["horizon_minutes"])
            horizon_end = entry + pd.Timedelta(minutes=horizon_minutes)
            if horizon_end > last_m5:
                excl.append({"feature_bar_open_utc": b["feature_bar_open_utc"], "entry_time_utc": b["entry_time_utc"], "profile_id": p["profile_id"], "reason": "insufficient_m5_lookahead_window_for_profile"})
                continue
            for direction in ["LONG", "SHORT"]:
                tp_dist = float(p["tp_price_distance_usd"])
                sl_dist = float(p["sl_price_distance_usd"])
                if direction == "LONG":
                    tp_price = entry_price + tp_dist
                    sl_price = entry_price - sl_dist
                else:
                    tp_price = entry_price - tp_dist
                    sl_price = entry_price + sl_dist
                strategy_id = f"GOLD_V3_LABEL_BASE_M15_CLOSE_M5_FIRST_TOUCH_{p['profile_id']}"
                rows.append({
                    "profile_id": p["profile_id"],
                    "strategy_id": strategy_id,
                    "price_distance_unit": UNIT,
                    "feature_timeframe": "M15",
                    "evaluation_timeframe": "M5",
                    "feature_bar_open_utc": b["feature_bar_open_utc"],
                    "entry_time_utc": b["entry_time_utc"],
                    "direction": direction,
                    "entry_price_source": "native_m5_open_at_entry_time",
                    "entry_price": entry_price,
                    "tp_price_distance_usd": tp_dist,
                    "sl_price_distance_usd": sl_dist,
                    "tp_price": tp_price,
                    "sl_price": sl_price,
                    "horizon_m15_bars": int(p["horizon_m15_bars"]),
                    "horizon_minutes": horizon_minutes,
                    "horizon_end_utc": str(horizon_end),
                    "same_bar_priority": SAME_BAR_PRIORITY,
                    "outcome": "NOT_EVALUATED_CONTRACT_ONLY",
                    "ai_api_called": False,
                })
    return pd.DataFrame(rows), pd.DataFrame(excl)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = [
        upstream01b_dir() / "gold_v3_01b_summary.json",
        canonical_dir() / "gold_v3_gold_hash_2025_primary_m15.csv",
        canonical_dir() / "gold_v3_gold_hash_2025_primary_m5.csv",
    ]
    inv_df = input_inventory(paths)
    summary01b = read_json(paths[0])
    inputs_ok = bool(inv_df["exists"].all())
    upstream_ok = summary01b.get("status") == EXPECTED_01B_STATUS
    m15 = load_candles("m15") if inputs_ok else pd.DataFrame()
    m5 = load_candles("m5") if inputs_ok else pd.DataFrame()
    profiles = profile_df()
    base_df, base_excl_df = build_base_entries(m15, m5) if inputs_ok else (pd.DataFrame(), pd.DataFrame())
    grid_df, profile_excl_df = expand_grid(base_df, profiles, m5) if inputs_ok and not base_df.empty else (pd.DataFrame(), pd.DataFrame())
    outcome_counts = grid_df["outcome"].value_counts().to_dict() if not grid_df.empty else {}
    direction_counts = grid_df["direction"].value_counts().to_dict() if not grid_df.empty else {}
    profile_counts = grid_df["profile_id"].value_counts().to_dict() if not grid_df.empty else {}
    base_excl_counts = base_excl_df["reason"].value_counts().to_dict() if not base_excl_df.empty else {}
    profile_excl_counts = profile_excl_df["reason"].value_counts().to_dict() if not profile_excl_df.empty else {}
    if not (inputs_ok and upstream_ok):
        status = "GOLD_V3_02B_LABEL_GRID_CONTRACT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif base_df.empty or grid_df.empty:
        status = "GOLD_V3_02B_LABEL_GRID_CONTRACT_BLOCKED_AUDIT_ONLY"
    else:
        status = "GOLD_V3_02B_LABEL_GRID_CONTRACT_READY_WITH_SESSION_EXCLUSIONS_AUDIT_ONLY"
    audit_summary = pd.DataFrame([
        ["source_m15_rows", len(m15)],
        ["source_m5_rows", len(m5)],
        ["tp_sl_profiles", len(profiles)],
        ["base_entry_universe_rows", len(base_df)],
        ["base_session_excluded_rows", len(base_excl_df)],
        ["grid_contract_rows", len(grid_df)],
        ["profile_excluded_rows", len(profile_excl_df)],
        ["unique_entry_time_count", grid_df["entry_time_utc"].nunique() if not grid_df.empty else 0],
        ["long_count", int(direction_counts.get("LONG", 0))],
        ["short_count", int(direction_counts.get("SHORT", 0))],
        ["outcome_not_evaluated_count", int(outcome_counts.get("NOT_EVALUATED_CONTRACT_ONLY", 0))],
        ["zip_output_created", False],
        ["ai_api_called", False],
    ], columns=["metric", "value"])
    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_01b_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["base_entry_universe_nonempty", len(base_df) > 0, True, "PASS" if len(base_df) > 0 else "FAIL"],
        ["grid_contract_rows_nonempty", len(grid_df) > 0, True, "PASS" if len(grid_df) > 0 else "FAIL"],
        ["outcomes_evaluated", False, False, "PASS"],
        ["features_created", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["tp_sl_unit_is_pips", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-02B-001", "01B inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "01B ready status and canonical M15/M5 required."],
        ["G3-02B-002", "session/market-stop entries", "CLOSED_AS_EXCLUDED", "INFO", "Missing M5 entry opens are excluded, not shifted."],
        ["G3-02B-003", "profile lookahead windows", "REVIEW" if len(profile_excl_df) else "CLOSED", "INFO", "Late entries can be excluded per profile horizon."],
        ["G3-02B-004", "outcome evaluation", "CLOSED_BLOCKED_BY_POLICY", "HARD", "02B is contract-only; no outcomes evaluated."],
        ["G3-02B-005", "TP/SL unit", "CLOSED", "HARD", "TP/SL are XAUUSD/GOLD# USD price distances, not pips."],
        ["G3-02B-006", "zip output", "CLOSED_DISABLED", "INFO", "ZIP output disabled."],
        ["G3-02B-007", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "price_distance_unit": UNIT,
        "tp_sl_unit_is_pips": False,
        "profiles": profiles.to_dict(orient="records"),
        "source_m15_rows": int(len(m15)),
        "source_m5_rows": int(len(m5)),
        "base_entry_universe_rows": int(len(base_df)),
        "grid_contract_rows": int(len(grid_df)),
        "base_excluded_counts": base_excl_counts,
        "profile_excluded_counts": profile_excl_counts,
        "direction_counts": direction_counts,
        "outcome_counts": outcome_counts,
        "profile_counts": profile_counts,
        "labels_evaluated": False,
        "features_created": False,
        "signals_generated": False,
        "zip_output_created": False,
        "external_actions": ACTIONS,
    }
    inv_df.to_csv(out / "gold_v3_02b_input_inventory.csv", index=False, encoding="utf-8-sig")
    profiles.to_csv(out / "gold_v3_02b_tp_sl_profile_grid.csv", index=False, encoding="utf-8-sig")
    base_df.to_csv(out / "gold_v3_02b_base_entry_universe.csv", index=False, encoding="utf-8-sig")
    grid_df.to_csv(out / "gold_v3_02b_entry_grid_contract_only.csv", index=False, encoding="utf-8-sig")
    base_excl_df.to_csv(out / "gold_v3_02b_excluded_base_entries.csv", index=False, encoding="utf-8-sig")
    profile_excl_df.to_csv(out / "gold_v3_02b_excluded_profile_entries.csv", index=False, encoding="utf-8-sig")
    audit_summary.to_csv(out / "gold_v3_02b_audit_summary.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_02b_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_02b_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_02b_summary.json", summary)
    report = "\n".join([
        "# GOLD V3 02B label grid contract audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Unit",
        f"TP/SL unit: `{UNIT}`",
        "",
        "## Audit summary",
        md(audit_summary),
        "",
        "## TP/SL profile grid",
        md(profiles),
        "",
        "## Decision matrix",
        md(decision_df),
        "",
        "## Base exclusions",
        md(pd.DataFrame([{"reason": k, "count": v} for k, v in base_excl_counts.items()])),
        "",
        "## Profile exclusions",
        md(pd.DataFrame([{"reason": k, "count": v} for k, v in profile_excl_counts.items()])),
        "",
        "## Blockers",
        md(blocker_df),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- TP/SL are USD price-distance values, not pips.",
        "- No features, no evaluated labels/outcomes, no candidates, no signals.",
        "- No ZIP output.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_02B_LABEL_GRID_CONTRACT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, features, evaluated labels, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
