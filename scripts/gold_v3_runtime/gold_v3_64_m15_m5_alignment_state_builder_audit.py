#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 64 M15/M5 alignment state builder audit-only.

Verifies that M15 closed timestamps align to M5 timestamps inside overlap range.
CSV contract: open/in-progress candles are not written to CSV.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_BLOCKED_AUDIT_ONLY"
STAGE63_READY = "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_READY_AUDIT_ONLY"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "63_h4_closed_bar_live_state_builder_audit_only").exists():
            return d
    raise FileNotFoundError("Stage63 output directory not found. Pass --candle-dir.")


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage63-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def modulo_ok(ts: pd.Series, minutes: int) -> bool:
    if ts.dropna().empty:
        return False
    return bool(((ts.dropna().dt.minute % minutes) == 0).all())


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s63 = Path(a.stage63_dir).expanduser().resolve() if a.stage63_dir else g / "63_h4_closed_bar_live_state_builder_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "64_m15_m5_alignment_state_builder_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p63s = s63 / "gold_v3_63_h4_closed_bar_state_summary.json"
    m15_path = cdir / "goldsharp_m15.csv"
    m5_path = cdir / "goldsharp_m5.csv"

    val: list[dict[str, Any]] = []
    val.append(ok("stage63_summary_present", p63s.exists(), str(p63s), "exists"))
    val.append(ok("m15_csv_present", m15_path.exists(), str(m15_path), "exists"))
    val.append(ok("m5_csv_present", m5_path.exists(), str(m5_path), "exists"))
    if not p63s.exists() or not m15_path.exists() or not m5_path.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_64_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j63 = read_json(p63s)
    val.append(ok("stage63_status_ready", j63.get("status") == STAGE63_READY, j63.get("status"), STAGE63_READY))
    val.append(ok("stage63_h4_state_ready", j63.get("h4_closed_bar_state_ready") is True, j63.get("h4_closed_bar_state_ready"), True))
    val.append(ok("csv_closed_only_contract_inherited", j63.get("csv_contains_open_bar_by_contract") is False, j63.get("csv_contains_open_bar_by_contract"), False))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage63_{key}_false", j63.get(key) is False, j63.get(key), False))

    m15, m15_sep = read_csv_auto(m15_path)
    m5, m5_sep = read_csv_auto(m5_path)
    m15_time_col = detect_time_column(m15)
    m5_time_col = detect_time_column(m5)
    m15_ts = parse_times(m15[m15_time_col])
    m5_ts = parse_times(m5[m5_time_col])

    m15_rows = int(len(m15))
    m5_rows = int(len(m5))
    m15_parseable = int(m15_ts.notna().sum())
    m5_parseable = int(m5_ts.notna().sum())
    m15_mono = bool(m15_ts.dropna().is_monotonic_increasing) if m15_parseable else False
    m5_mono = bool(m5_ts.dropna().is_monotonic_increasing) if m5_parseable else False
    m15_dups = int(m15_ts.dropna().duplicated().sum()) if m15_parseable else 0
    m5_dups = int(m5_ts.dropna().duplicated().sum()) if m5_parseable else 0
    m15_grid_ok = modulo_ok(m15_ts, 15)
    m5_grid_ok = modulo_ok(m5_ts, 5)

    m15_valid = pd.Series(m15_ts.dropna().sort_values().unique())
    m5_valid = pd.Series(m5_ts.dropna().sort_values().unique())
    m5_set = set(m5_valid.tolist())
    if len(m15_valid) and len(m5_valid):
        m5_min, m5_max = m5_valid.iloc[0], m5_valid.iloc[-1]
        m15_min, m15_max = m15_valid.iloc[0], m15_valid.iloc[-1]
        overlap_m15 = m15_valid[(m15_valid >= m5_min) & (m15_valid <= m5_max)]
        aligned_mask = overlap_m15.apply(lambda x: x in m5_set)
        aligned_count = int(aligned_mask.sum())
        overlap_count = int(len(overlap_m15))
        missing_count = int(overlap_count - aligned_count)
        latest_m15 = m15_valid.iloc[-1]
        latest_m5 = m5_valid.iloc[-1]
        latest_m15_covered_by_m5_range = bool(latest_m15 <= latest_m5)
        latest_m15_has_exact_m5 = bool(latest_m15 in m5_set)
        latest_delta_minutes = float((latest_m5 - latest_m15).total_seconds() / 60.0)
    else:
        m5_min = m5_max = m15_min = m15_max = latest_m15 = latest_m5 = pd.NaT
        overlap_count = aligned_count = missing_count = 0
        latest_m15_covered_by_m5_range = False
        latest_m15_has_exact_m5 = False
        latest_delta_minutes = float("nan")

    detail = pd.DataFrame({
        "m15_time": overlap_m15 if len(m15_valid) and len(m5_valid) else [],
    })
    if not detail.empty:
        detail["has_matching_m5_time"] = detail["m15_time"].apply(lambda x: x in m5_set)
        detail["within_m5_range"] = True
    detail.to_csv(out / "gold_v3_64_m15_m5_alignment_detail.csv", index=False, encoding="utf-8-sig")

    inv = pd.DataFrame([
        {"artifact_id": "m15_csv", "path": str(m15_path), "separator": m15_sep, "rows": m15_rows, "columns": "|".join(map(str, m15.columns)), "time_column": m15_time_col, "parseable_rows": m15_parseable, "duplicate_timestamp_count": m15_dups, "monotonic_increasing": m15_mono, "time_grid_minutes": 15, "time_grid_ok": m15_grid_ok, "min_time": str(m15_min), "max_time": str(m15_max)},
        {"artifact_id": "m5_csv", "path": str(m5_path), "separator": m5_sep, "rows": m5_rows, "columns": "|".join(map(str, m5.columns)), "time_column": m5_time_col, "parseable_rows": m5_parseable, "duplicate_timestamp_count": m5_dups, "monotonic_increasing": m5_mono, "time_grid_minutes": 5, "time_grid_ok": m5_grid_ok, "min_time": str(m5_min), "max_time": str(m5_max)},
    ])
    inv.to_csv(out / "gold_v3_64_csv_inventory.csv", index=False, encoding="utf-8-sig")

    state = pd.DataFrame([{
        "state_id": "m15_m5_alignment_state",
        "m15_csv": str(m15_path),
        "m5_csv": str(m5_path),
        "m15_rows": m15_rows,
        "m5_rows": m5_rows,
        "m15_time_column": m15_time_col,
        "m5_time_column": m5_time_col,
        "m15_min_time": str(m15_min),
        "m15_max_time": str(m15_max),
        "m5_min_time": str(m5_min),
        "m5_max_time": str(m5_max),
        "overlap_m15_count": overlap_count,
        "aligned_m15_to_m5_count": aligned_count,
        "missing_m15_matching_m5_count": missing_count,
        "alignment_ratio": aligned_count / overlap_count if overlap_count else 0.0,
        "latest_m15_time": str(latest_m15),
        "latest_m5_time": str(latest_m5),
        "latest_m5_minus_m15_minutes": latest_delta_minutes,
        "latest_m15_covered_by_m5_range": latest_m15_covered_by_m5_range,
        "latest_m15_has_exact_m5": latest_m15_has_exact_m5,
        "csv_contains_open_bar_by_contract": False,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "final_signal_enabled": False,
    }])
    state.to_csv(out / "gold_v3_64_m15_m5_alignment_state.csv", index=False, encoding="utf-8-sig")

    val.append(ok("m15_csv_has_rows", m15_rows > 0, m15_rows, ">0"))
    val.append(ok("m5_csv_has_rows", m5_rows > 0, m5_rows, ">0"))
    val.append(ok("m15_timestamps_parseable", m15_parseable == m15_rows and m15_rows > 0, f"{m15_parseable}/{m15_rows}", "all_rows"))
    val.append(ok("m5_timestamps_parseable", m5_parseable == m5_rows and m5_rows > 0, f"{m5_parseable}/{m5_rows}", "all_rows"))
    val.append(ok("m15_monotonic_increasing", m15_mono, m15_mono, True))
    val.append(ok("m5_monotonic_increasing", m5_mono, m5_mono, True))
    val.append(ok("m15_duplicate_timestamp_zero", m15_dups == 0, m15_dups, 0))
    val.append(ok("m5_duplicate_timestamp_zero", m5_dups == 0, m5_dups, 0))
    val.append(ok("m15_time_grid_15min", m15_grid_ok, m15_grid_ok, True))
    val.append(ok("m5_time_grid_5min", m5_grid_ok, m5_grid_ok, True))
    val.append(ok("m15_m5_overlap_has_rows", overlap_count > 0, overlap_count, ">0"))
    val.append(ok("all_overlap_m15_have_matching_m5", missing_count == 0 and overlap_count > 0, missing_count, 0))
    val.append(ok("latest_m15_covered_by_m5_range", latest_m15_covered_by_m5_range, latest_m15_covered_by_m5_range, True))
    val.append(ok("latest_m15_has_exact_m5", latest_m15_has_exact_m5, latest_m15_has_exact_m5, True))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_64_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "m15_m5_alignment_state_ready": failed.empty,
        "m15_rows": m15_rows,
        "m5_rows": m5_rows,
        "overlap_m15_count": overlap_count,
        "aligned_m15_to_m5_count": aligned_count,
        "missing_m15_matching_m5_count": missing_count,
        "alignment_ratio": aligned_count / overlap_count if overlap_count else 0.0,
        "latest_m15_time": str(latest_m15),
        "latest_m5_time": str(latest_m5),
        "latest_m5_minus_m15_minutes": latest_delta_minutes,
        "csv_contains_open_bar_by_contract": False,
        "csv_open_bar_exclusion_required": False,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_64_alignment_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 64 PASTE_ME_M15_M5_ALIGNMENT_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("m15_m5_alignment_state_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("csv_contract: open/in-progress candles are not written to CSV")
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append(f"m15_rows: {m15_rows}")
    paste.append(f"m5_rows: {m5_rows}")
    paste.append(f"m15_time_column: {m15_time_col}")
    paste.append(f"m5_time_column: {m5_time_col}")
    paste.append(f"overlap_m15_count: {overlap_count}")
    paste.append(f"aligned_m15_to_m5_count: {aligned_count}")
    paste.append(f"missing_m15_matching_m5_count: {missing_count}")
    paste.append(f"alignment_ratio: {aligned_count / overlap_count if overlap_count else 0.0:.6f}")
    paste.append(f"latest_m15_time: {latest_m15}")
    paste.append(f"latest_m5_time: {latest_m5}")
    paste.append(f"latest_m5_minus_m15_minutes: {latest_delta_minutes}")
    paste.append("")
    paste.append("M15_M5_ALIGNMENT_STATE")
    paste.append(state.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_64_m15_m5_alignment_state.csv")
    paste.append("gold_v3_64_m15_m5_alignment_detail.csv")
    paste.append("gold_v3_64_csv_inventory.csv")
    paste.append("gold_v3_64_validation_matrix.csv")
    paste.append("gold_v3_64_alignment_summary.json")
    (out / "gold_v3_64_PASTE_ME_M15_M5_ALIGNMENT_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    (out / "GOLD_V3_64_REPORT.md").write_text(f"# GOLD V3 64 M15/M5 alignment state builder audit-only report\n\nStatus: `{status}`\n\nCSV contract: open/in-progress candles are not written to CSV.\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_64_PASTE_ME_M15_M5_ALIGNMENT_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
