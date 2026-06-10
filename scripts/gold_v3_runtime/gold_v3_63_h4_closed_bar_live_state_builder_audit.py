#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 63 H4 closed-bar live state builder audit-only.

User-confirmed CSV contract: open/in-progress candles are not written to CSV.
Thus the latest H4 CSV row is treated as the latest available closed H4 bar.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_BLOCKED_AUDIT_ONLY"
STAGE62B_READY = "GOLD_V3_62B_LIVE_READINESS_PLAN_CANONICALIZATION_READY_AUDIT_ONLY"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "62b_live_readiness_plan_canonicalization_audit_only").exists():
            return d
    raise FileNotFoundError("Stage62B output directory not found. Pass --candle-dir.")


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str]:
    attempts: list[tuple[str | None, str]] = [(None, "auto") , (";", "semicolon"), (",", "comma"), ("\t", "tab")]
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
    p.add_argument("--stage62b-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s62b = Path(a.stage62b_dir).expanduser().resolve() if a.stage62b_dir else g / "62b_live_readiness_plan_canonicalization_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "63_h4_closed_bar_live_state_builder_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p62bs = s62b / "gold_v3_62b_plan_canonicalization_summary.json"
    h4_path = cdir / "goldsharp_h4.csv"

    val: list[dict[str, Any]] = []
    val.append(ok("stage62b_summary_present", p62bs.exists(), str(p62bs), "exists"))
    val.append(ok("h4_csv_present", h4_path.exists(), str(h4_path), "exists"))
    if not p62bs.exists() or not h4_path.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_63_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j62b = read_json(p62bs)
    val.append(ok("stage62b_status_ready", j62b.get("status") == STAGE62B_READY, j62b.get("status"), STAGE62B_READY))
    val.append(ok("stage62b_canonicalization_ready", j62b.get("plan_canonicalization_ready") is True, j62b.get("plan_canonicalization_ready"), True))
    val.append(ok("official_next_stage_is_stage63", j62b.get("official_next_stage") == STEP, j62b.get("official_next_stage"), STEP))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage62b_{key}_false", j62b.get(key) is False, j62b.get(key), False))

    df, sep_label = read_csv_auto(h4_path)
    row_count = int(len(df))
    time_col = detect_time_column(df)
    parsed = parse_times(df[time_col])
    parseable_count = int(parsed.notna().sum())
    df2 = df.copy()
    df2["_parsed_time"] = parsed
    valid = df2[df2["_parsed_time"].notna()].copy()
    latest = valid.iloc[-1] if not valid.empty else None
    monotonic = bool(parsed.dropna().is_monotonic_increasing) if parseable_count else False
    duplicate_times = int(parsed.dropna().duplicated().sum()) if parseable_count else 0

    val.append(ok("h4_csv_has_rows", row_count > 0, row_count, ">0"))
    val.append(ok("h4_time_column_detected", bool(time_col), time_col, "detected"))
    val.append(ok("h4_timestamps_parseable", parseable_count == row_count and row_count > 0, f"{parseable_count}/{row_count}", "all_rows"))
    val.append(ok("h4_timestamps_monotonic_increasing", monotonic, monotonic, True))
    val.append(ok("h4_duplicate_timestamp_count_zero", duplicate_times == 0, duplicate_times, 0))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("csv_closed_only_contract_confirmed", True, "open/in-progress candles are not written to CSV", "confirmed_by_user"))

    latest_time = ""
    latest_time_iso = ""
    latest_payload: dict[str, Any] = {}
    if latest is not None:
        latest_time = str(latest[time_col])
        try:
            latest_time_iso = pd.Timestamp(latest["_parsed_time"]).isoformat()
        except Exception:
            latest_time_iso = str(latest["_parsed_time"])
        for c in df.columns:
            v = latest[c]
            if pd.isna(v):
                latest_payload[str(c)] = ""
            elif isinstance(v, (int, float, str, bool)):
                latest_payload[str(c)] = v
            else:
                latest_payload[str(c)] = str(v)

    state = pd.DataFrame([{
        "state_id": "h4_closed_bar_live_state",
        "source_csv": str(h4_path),
        "csv_separator_detected": sep_label,
        "csv_rows": row_count,
        "time_column": time_col,
        "latest_h4_closed_time_raw": latest_time,
        "latest_h4_closed_time_iso": latest_time_iso,
        "csv_contains_open_bar_by_contract": False,
        "csv_open_bar_exclusion_required": False,
        "latest_row_is_closed_by_csv_contract": True if latest is not None else False,
        "live_ready": False,
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "final_signal_enabled": False,
    }])
    state.to_csv(out / "gold_v3_63_h4_closed_bar_live_state.csv", index=False, encoding="utf-8-sig")

    inv = pd.DataFrame([{
        "artifact_id": "h4_csv",
        "path": str(h4_path),
        "exists": h4_path.exists(),
        "csv_separator_detected": sep_label,
        "rows": row_count,
        "columns": "|".join(map(str, df.columns)),
        "time_column": time_col,
        "parseable_timestamp_rows": parseable_count,
        "duplicate_timestamp_count": duplicate_times,
        "monotonic_increasing": monotonic,
        "latest_time_raw": latest_time,
        "latest_time_iso": latest_time_iso,
    }])
    inv.to_csv(out / "gold_v3_63_h4_csv_inventory.csv", index=False, encoding="utf-8-sig")

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_63_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "h4_closed_bar_state_ready": failed.empty,
        "h4_csv_rows": row_count,
        "time_column": time_col,
        "latest_h4_closed_time_raw": latest_time,
        "latest_h4_closed_time_iso": latest_time_iso,
        "csv_contains_open_bar_by_contract": False,
        "csv_open_bar_exclusion_required": False,
        "latest_row_is_closed_by_csv_contract": True if latest is not None else False,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_63_h4_closed_bar_state_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 63 PASTE_ME_H4_CLOSED_BAR_STATE_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("h4_closed_bar_state_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("csv_contract: open/in-progress candles are not written to CSV")
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append(f"h4_csv_rows: {row_count}")
    paste.append(f"time_column: {time_col}")
    paste.append(f"latest_h4_closed_time_raw: {latest_time}")
    paste.append(f"latest_h4_closed_time_iso: {latest_time_iso}")
    paste.append(f"duplicate_timestamp_count: {duplicate_times}")
    paste.append(f"monotonic_increasing: {monotonic}")
    paste.append("")
    paste.append("H4_CLOSED_BAR_LIVE_STATE")
    paste.append(state.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_63_h4_closed_bar_live_state.csv")
    paste.append("gold_v3_63_h4_csv_inventory.csv")
    paste.append("gold_v3_63_validation_matrix.csv")
    paste.append("gold_v3_63_h4_closed_bar_state_summary.json")
    (out / "gold_v3_63_PASTE_ME_H4_CLOSED_BAR_STATE_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    (out / "GOLD_V3_63_REPORT.md").write_text(f"# GOLD V3 63 H4 closed-bar live state builder audit-only report\n\nStatus: `{status}`\n\nCSV contract: open/in-progress candles are not written to CSV. Latest H4 row is treated as closed by CSV contract.\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_63_PASTE_ME_H4_CLOSED_BAR_STATE_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
