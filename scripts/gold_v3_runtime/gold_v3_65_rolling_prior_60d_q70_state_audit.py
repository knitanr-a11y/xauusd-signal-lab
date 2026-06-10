#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 65 rolling prior-60D Q70 state audit-only.

Computes H4 true-range rolling prior-60D Q70 and asof-attaches it to M15.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_BLOCKED_AUDIT_ONLY"
STAGE64_READY = "GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_READY_AUDIT_ONLY"
MIN_PRIOR_OBS = 20
WINDOW_DAYS = 60


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "64_m15_m5_alignment_state_builder_audit_only").exists():
            return d
    raise FileNotFoundError("Stage64 output directory not found. Pass --candle-dir.")


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str]:
    attempts: list[tuple[str | None, str]] = [(None, "auto"), (";", "semicolon"), (",", "comma"), ("\t", "tab")]
    last_err: Exception | None = None
    for sep, label in attempts:
        try:
            if sep is None:
                df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            else:
                df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df, label
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err
    raise ValueError(f"Could not parse CSV with multiple columns: {path}")


def detect_time_column(df: pd.DataFrame) -> str:
    candidates = []
    for c in df.columns:
        lc = str(c).lower()
        score = 0
        if lc in ["time", "datetime", "date", "dt", "timestamp"]:
            score += 10
        if "time" in lc or "date" in lc or "timestamp" in lc:
            score += 5
        if "jst" in lc or "utc" in lc:
            score += 1
        if score:
            candidates.append((score, str(c)))
    if candidates:
        return sorted(candidates, reverse=True)[0][1]
    return str(df.columns[0])


def parse_times(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, errors="coerce")
    if parsed.notna().sum() == 0:
        parsed = pd.to_datetime(s.str.replace(".", "-", regex=False), errors="coerce")
    return parsed


def detect_ohlc(df: pd.DataFrame) -> dict[str, str]:
    norm = {str(c).strip().lower().replace(" ", "").replace("_", ""): str(c) for c in df.columns}
    aliases = {
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c"],
    }
    out: dict[str, str] = {}
    for k, vals in aliases.items():
        for v in vals:
            if v in norm:
                out[k] = norm[v]
                break
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage64-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s64 = Path(a.stage64_dir).expanduser().resolve() if a.stage64_dir else g / "64_m15_m5_alignment_state_builder_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "65_rolling_prior_60d_q70_state_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p64s = s64 / "gold_v3_64_alignment_summary.json"
    h4_path = cdir / "goldsharp_h4.csv"
    m15_path = cdir / "goldsharp_m15.csv"

    val: list[dict[str, Any]] = []
    val.append(ok("stage64_summary_present", p64s.exists(), str(p64s), "exists"))
    val.append(ok("h4_csv_present", h4_path.exists(), str(h4_path), "exists"))
    val.append(ok("m15_csv_present", m15_path.exists(), str(m15_path), "exists"))
    if not p64s.exists() or not h4_path.exists() or not m15_path.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_65_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j64 = read_json(p64s)
    val.append(ok("stage64_status_ready", j64.get("status") == STAGE64_READY, j64.get("status"), STAGE64_READY))
    val.append(ok("stage64_alignment_ready", j64.get("m15_m5_alignment_state_ready") is True, j64.get("m15_m5_alignment_state_ready"), True))
    val.append(ok("csv_closed_only_contract_inherited", j64.get("csv_contains_open_bar_by_contract") is False, j64.get("csv_contains_open_bar_by_contract"), False))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage64_{key}_false", j64.get(key) is False, j64.get(key), False))

    h4, h4_sep = read_csv_auto(h4_path)
    m15, m15_sep = read_csv_auto(m15_path)
    h4_time_col = detect_time_column(h4)
    m15_time_col = detect_time_column(m15)
    h4["_time"] = parse_times(h4[h4_time_col])
    m15["_time"] = parse_times(m15[m15_time_col])
    ohlc = detect_ohlc(h4)

    h4_rows = int(len(h4))
    m15_rows = int(len(m15))
    h4_parseable = int(h4["_time"].notna().sum())
    m15_parseable = int(m15["_time"].notna().sum())
    h4_mono = bool(h4["_time"].dropna().is_monotonic_increasing) if h4_parseable else False
    m15_mono = bool(m15["_time"].dropna().is_monotonic_increasing) if m15_parseable else False
    h4_dups = int(h4["_time"].dropna().duplicated().sum()) if h4_parseable else 0
    m15_dups = int(m15["_time"].dropna().duplicated().sum()) if m15_parseable else 0
    ohlc_detected = set(ohlc.keys()) == {"open", "high", "low", "close"}

    h4_state = h4.copy()
    if ohlc_detected:
        for k, col in ohlc.items():
            h4_state[f"_{k}"] = pd.to_numeric(h4_state[col], errors="coerce")
        prev_close = h4_state["_close"].shift(1)
        tr = pd.concat([
            h4_state["_high"] - h4_state["_low"],
            (h4_state["_high"] - prev_close).abs(),
            (h4_state["_low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        h4_state["h4_true_range"] = tr
    else:
        h4_state["h4_true_range"] = np.nan

    h4_state = h4_state.sort_values("_time").reset_index(drop=True)
    q70_vals: list[float] = []
    prior_counts: list[int] = []
    for _, row in h4_state.iterrows():
        t = row["_time"]
        if pd.isna(t):
            q70_vals.append(np.nan)
            prior_counts.append(0)
            continue
        start = t - pd.Timedelta(days=WINDOW_DAYS)
        prior = h4_state[(h4_state["_time"] >= start) & (h4_state["_time"] < t)]["h4_true_range"].dropna()
        prior_counts.append(int(len(prior)))
        q70_vals.append(float(prior.quantile(0.70)) if len(prior) >= MIN_PRIOR_OBS else np.nan)
    h4_state["prior_60d_obs"] = prior_counts
    h4_state["prior_60d_q70_true_range"] = q70_vals
    h4_state["q70_state_valid"] = h4_state["prior_60d_q70_true_range"].notna()
    h4_state["is_high_vol_q70"] = np.where(h4_state["q70_state_valid"], h4_state["h4_true_range"] >= h4_state["prior_60d_q70_true_range"], False)
    h4_state["csv_contains_open_bar_by_contract"] = False
    h4_state["csv_open_bar_exclusion_required"] = False

    h4_out = h4_state[["_time", "h4_true_range", "prior_60d_obs", "prior_60d_q70_true_range", "q70_state_valid", "is_high_vol_q70", "csv_contains_open_bar_by_contract", "csv_open_bar_exclusion_required"]].copy()
    h4_out = h4_out.rename(columns={"_time": "h4_time"})
    h4_out.to_csv(out / "gold_v3_65_h4_rolling_prior_60d_q70_state.csv", index=False, encoding="utf-8-sig")

    valid_h4 = h4_out[h4_out["q70_state_valid"]].copy().sort_values("h4_time")
    first_valid_h4_time = valid_h4["h4_time"].iloc[0] if not valid_h4.empty else pd.NaT
    latest_h4 = h4_out.iloc[-1] if not h4_out.empty else None
    latest_h4_valid = bool(latest_h4["q70_state_valid"]) if latest_h4 is not None else False

    m15_sorted = m15[["_time"]].dropna().sort_values("_time").rename(columns={"_time": "m15_time"})
    if not valid_h4.empty and not m15_sorted.empty:
        m15_asof = pd.merge_asof(
            m15_sorted,
            valid_h4[["h4_time", "h4_true_range", "prior_60d_obs", "prior_60d_q70_true_range", "is_high_vol_q70"]],
            left_on="m15_time",
            right_on="h4_time",
            direction="backward",
        )
        m15_asof["after_first_valid_h4_q70"] = m15_asof["m15_time"] >= first_valid_h4_time
        after = m15_asof[m15_asof["after_first_valid_h4_q70"]]
        missing_after_count = int(after["h4_time"].isna().sum())
    else:
        m15_asof = m15_sorted.copy()
        m15_asof["h4_time"] = pd.NaT
        m15_asof["after_first_valid_h4_q70"] = False
        missing_after_count = 0
    m15_asof["live_ready"] = False
    m15_asof["audit_only"] = True
    m15_asof.to_csv(out / "gold_v3_65_m15_asof_q70_state.csv", index=False, encoding="utf-8-sig")

    inv = pd.DataFrame([
        {"artifact_id": "h4_csv", "path": str(h4_path), "separator": h4_sep, "rows": h4_rows, "columns": "|".join(map(str, h4.columns)), "time_column": h4_time_col, "parseable_rows": h4_parseable, "duplicate_timestamp_count": h4_dups, "monotonic_increasing": h4_mono, "ohlc_detected": ohlc_detected, "ohlc_columns": json.dumps(ohlc, ensure_ascii=False)},
        {"artifact_id": "m15_csv", "path": str(m15_path), "separator": m15_sep, "rows": m15_rows, "columns": "|".join(map(str, m15.columns)), "time_column": m15_time_col, "parseable_rows": m15_parseable, "duplicate_timestamp_count": m15_dups, "monotonic_increasing": m15_mono, "ohlc_detected": "n/a", "ohlc_columns": ""},
    ])
    inv.to_csv(out / "gold_v3_65_csv_inventory.csv", index=False, encoding="utf-8-sig")

    valid_q70_count = int(h4_out["q70_state_valid"].sum())
    high_vol_count = int(h4_out["is_high_vol_q70"].sum())
    latest_h4_time = str(latest_h4["h4_time"]) if latest_h4 is not None else ""
    latest_h4_q70 = float(latest_h4["prior_60d_q70_true_range"]) if latest_h4 is not None and pd.notna(latest_h4["prior_60d_q70_true_range"]) else None
    latest_h4_tr = float(latest_h4["h4_true_range"]) if latest_h4 is not None and pd.notna(latest_h4["h4_true_range"]) else None
    latest_h4_is_high_vol = bool(latest_h4["is_high_vol_q70"]) if latest_h4 is not None else False

    val.append(ok("h4_csv_has_rows", h4_rows > 0, h4_rows, ">0"))
    val.append(ok("m15_csv_has_rows", m15_rows > 0, m15_rows, ">0"))
    val.append(ok("h4_timestamps_parseable", h4_parseable == h4_rows and h4_rows > 0, f"{h4_parseable}/{h4_rows}", "all_rows"))
    val.append(ok("m15_timestamps_parseable", m15_parseable == m15_rows and m15_rows > 0, f"{m15_parseable}/{m15_rows}", "all_rows"))
    val.append(ok("h4_monotonic_increasing", h4_mono, h4_mono, True))
    val.append(ok("m15_monotonic_increasing", m15_mono, m15_mono, True))
    val.append(ok("h4_duplicate_timestamp_zero", h4_dups == 0, h4_dups, 0))
    val.append(ok("m15_duplicate_timestamp_zero", m15_dups == 0, m15_dups, 0))
    val.append(ok("h4_ohlc_columns_detected", ohlc_detected, ohlc, "open/high/low/close"))
    val.append(ok("h4_q70_valid_rows_present", valid_q70_count > 0, valid_q70_count, ">0"))
    val.append(ok("latest_h4_q70_state_valid", latest_h4_valid, latest_h4_valid, True))
    val.append(ok("m15_asof_missing_after_first_valid_zero", missing_after_count == 0, missing_after_count, 0))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_65_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
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
        "live_ready": False,
        "rolling_prior_60d_q70_state_ready": failed.empty,
        "window_days": WINDOW_DAYS,
        "min_prior_obs": MIN_PRIOR_OBS,
        "h4_rows": h4_rows,
        "m15_rows": m15_rows,
        "h4_q70_valid_rows": valid_q70_count,
        "h4_high_vol_q70_rows": high_vol_count,
        "first_valid_h4_q70_time": str(first_valid_h4_time),
        "latest_h4_time": latest_h4_time,
        "latest_h4_true_range": latest_h4_tr,
        "latest_h4_prior_60d_q70_true_range": latest_h4_q70,
        "latest_h4_is_high_vol_q70": latest_h4_is_high_vol,
        "m15_asof_missing_after_first_valid_count": missing_after_count,
        "csv_contains_open_bar_by_contract": False,
        "csv_open_bar_exclusion_required": False,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_65_q70_state_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 65 PASTE_ME_Q70_STATE_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("rolling_prior_60d_q70_state_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("csv_contract: open/in-progress candles are not written to CSV")
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append(f"window_days: {WINDOW_DAYS}")
    paste.append(f"min_prior_obs: {MIN_PRIOR_OBS}")
    paste.append(f"h4_rows: {h4_rows}")
    paste.append(f"m15_rows: {m15_rows}")
    paste.append(f"h4_q70_valid_rows: {valid_q70_count}")
    paste.append(f"h4_high_vol_q70_rows: {high_vol_count}")
    paste.append(f"first_valid_h4_q70_time: {first_valid_h4_time}")
    paste.append(f"latest_h4_time: {latest_h4_time}")
    paste.append(f"latest_h4_true_range: {latest_h4_tr}")
    paste.append(f"latest_h4_prior_60d_q70_true_range: {latest_h4_q70}")
    paste.append(f"latest_h4_is_high_vol_q70: {latest_h4_is_high_vol}")
    paste.append(f"m15_asof_missing_after_first_valid_count: {missing_after_count}")
    paste.append("")
    paste.append("LATEST_H4_Q70_STATE")
    paste.append(h4_out.tail(5).to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_65_h4_rolling_prior_60d_q70_state.csv")
    paste.append("gold_v3_65_m15_asof_q70_state.csv")
    paste.append("gold_v3_65_csv_inventory.csv")
    paste.append("gold_v3_65_validation_matrix.csv")
    paste.append("gold_v3_65_q70_state_summary.json")
    (out / "gold_v3_65_PASTE_ME_Q70_STATE_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    (out / "GOLD_V3_65_REPORT.md").write_text(f"# GOLD V3 65 rolling prior-60D Q70 state audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_65_PASTE_ME_Q70_STATE_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
